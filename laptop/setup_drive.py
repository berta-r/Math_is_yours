"""Build a read-only USB setup volume as a regular FAT16 image file (stdlib)."""
from datetime import datetime, timezone
from pathlib import Path
import math
import struct


def short_name(name):
    parts=name.upper().split('.')
    if len(parts)>2 or not 1<=len(parts[0])<=8 or (len(parts)==2 and not 1<=len(parts[1])<=3):
        raise ValueError('Setup drive files must use 8.3 names')
    if any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for part in parts for c in part):
        raise ValueError('Unsafe setup drive filename')
    return (parts[0].ljust(8)+(parts[1] if len(parts)==2 else '').ljust(3)).encode('ascii')


def build_image(files, output, size_mb=64):
    """Superfloppy FAT16; only creates the named regular file, never a disk device."""
    output=Path(output)
    if not 16<=size_mb<=128 or output.exists() and (not output.is_file() or output.is_symlink()):
        raise ValueError('Use a regular output image between 16 and 128 MiB')
    if len(files)>100 or len({short_name(name) for name in files})!=len(files):
        raise ValueError('Too many or duplicate FAT filenames')
    sector=512; clustersize=8; sectors=size_mb*1024*1024//sector
    fatsize=1
    while True:
        count=(sectors-1-32-2*fatsize)//clustersize
        required=math.ceil((count+2)*2/sector)
        if required<=fatsize:break
        fatsize=required
    if not 4085<=count<65525:raise ValueError('Image does not fit FAT16')
    clusterbytes=sector*clustersize
    if sum(math.ceil(Path(p).stat().st_size/clusterbytes) for p in files.values())>count:
        raise ValueError('Setup files do not fit on the drive')
    boot=bytearray(sector)
    boot[:11]=b'\xeb\x3c\x90MSDOS5.0'
    struct.pack_into('<HBHBHHBHHHII',boot,11,sector,clustersize,1,2,512,0,0xf8,fatsize,32,64,0,sectors)
    struct.pack_into('<BBBI11s8s',boot,36,0x80,0,0x29,0x4d415448,b'MATHTUTOR  ',b'FAT16   ')
    boot[510:]=b'\x55\xaa'
    fat=bytearray(fatsize*sector)
    struct.pack_into('<HH',fat,0,0xfff8,0xffff)
    root=bytearray(32*sector)
    root[:11]=b'MATHTUTOR  ';root[11]=8
    now=datetime.now(timezone.utc)
    date=((now.year-1980)<<9)|(now.month<<5)|now.day
    clock=(now.hour<<11)|(now.minute<<5)|(now.second//2)
    data_offset=(1+2*fatsize+32)*sector
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('wb') as image:
        image.truncate(sectors*sector)
        next_cluster=2
        for row,(name,path) in enumerate(files.items(),1):
            content=Path(path).read_bytes()
            length=math.ceil(len(content)/clusterbytes)
            first=next_cluster if length else 0
            for cluster in range(next_cluster,next_cluster+length):
                struct.pack_into('<H',fat,cluster*2,cluster+1 if cluster<next_cluster+length-1 else 0xffff)
            image.seek(data_offset+(next_cluster-2)*clusterbytes)
            image.write(content)
            entry=struct.pack('<11sBBBHHHHHHHI',short_name(name),0x20,0,0,clock,date,date,0,clock,date,first,len(content))
            root[row*32:(row+1)*32]=entry
            next_cluster+=length
        image.seek(0);image.write(boot)
        image.write(fat);image.write(fat);image.write(root)
    return {'image':str(output),'size':sectors*sector,'files':list(files),'label':'MATHTUTOR'}
