#!/usr/bin/env python3
"""Add/remove only Math Tutor's read-only setup LUN on the existing UNO Q gadget.

Run installation once with sudo from the board terminal. The ADB and serial
functions are retained. All configuration is reversible via --uninstall.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

GADGET=Path('/sys/kernel/config/usb_gadget/g1')
STATE_DIR=Path('/var/lib/math-tutor-usb')
STATE=STATE_DIR/'gadget-original.json'
IMAGE=STATE_DIR/'MATHTUTOR.img'
PROGRAM=Path('/usr/local/lib/math-tutor-usb/usb_setup_drive.py')
UNIT=Path('/etc/systemd/system/math-tutor-usb-drive.service')
FUNCTION='mass_storage.math_tutor'
FIELDS=('bcdDevice','os_desc/use','os_desc/b_vendor_code','os_desc/qw_sign')


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def verify_image(path):
    path=Path(path)
    if not path.is_file() or path.is_symlink() or not 16*1024*1024<=path.stat().st_size<=128*1024*1024:
        raise ValueError('Use the prepared regular setup image, 16–128 MiB; never a disk device')
    with path.open('rb') as f:boot=f.read(512)
    if boot[510:]!=b'\x55\xaa' or boot[54:62]!=b'FAT16   ' or boot[43:54]!=b'MATHTUTOR  ':
        raise ValueError('Image is not the expected MATHTUTOR FAT16 volume')


def write(path, value):
    Path(path).write_text(str(value)+'\n')


def snapshot(gadget):
    return {'fields':{name:(gadget/name).read_text().strip() for name in FIELDS},
            'udc':(gadget/'UDC').read_text().strip(),
            'os_link_existed':(gadget/'os_desc/c.1').is_symlink()}


def restore(gadget, original, rebind=True):
    write(gadget/'UDC','')
    link=gadget/'configs/c.1'/FUNCTION
    if link.is_symlink():
        if link.resolve()!=(gadget/'functions'/FUNCTION).resolve():
            raise ValueError('Refusing to remove an unexpected USB link')
        link.unlink()
    function=gadget/'functions'/FUNCTION
    if function.exists():function.rmdir()  # ConfigFS removes its virtual children.
    os_link=gadget/'os_desc/c.1'
    if not original['os_link_existed'] and os_link.is_symlink():
        if os_link.resolve()!=(gadget/'configs/c.1').resolve():
            raise ValueError('Unexpected OS descriptor configuration')
        os_link.unlink()
    for name,value in original['fields'].items():
        if name not in FIELDS:raise ValueError('Invalid saved descriptor')
        write(gadget/name,value)
    if rebind and original['udc']:write(gadget/'UDC',original['udc'])


def attach(gadget=GADGET, image=IMAGE, state=STATE):
    verify_image(image)
    if (gadget/'idVendor').read_text().strip()!='0x2341' or (gadget/'idProduct').read_text().strip()!='0x0078':
        raise ValueError('This setup supports the verified Arduino UNO Q gadget only')
    config=gadget/'configs/c.1'
    if not all((config/name).is_symlink() for name in ('ffs.adb','acm.GS0')):
        raise ValueError('Existing Arduino ADB/serial functions are missing')
    if (config/FUNCTION).is_symlink():
        if (gadget/'functions'/FUNCTION/'lun.0/file').read_text().strip()!=str(image):
            raise ValueError('A different setup drive is already attached')
        return
    original=snapshot(gadget)
    if not original['udc']:raise ValueError('Wait for the existing ADB gadget to activate')
    state.parent.mkdir(parents=True,exist_ok=True)
    state.write_text(json.dumps(original,indent=2)+'\n')
    subprocess.run(['modprobe','usb_f_mass_storage'],check=True)
    try:
        write(gadget/'UDC','')
        function=gadget/'functions'/FUNCTION
        function.mkdir()
        lun=function/'lun.0'
        write(lun/'ro','1')
        write(lun/'removable','1')
        write(lun/'cdrom','0')
        write(lun/'file',str(image))
        (config/FUNCTION).symlink_to(function)
        # adbd provides WINUSB and its ADB interface GUID through FunctionFS.
        # Enable delivery of those descriptors so a fresh Windows PC can use
        # its inbox WinUSB driver. A new revision avoids stale OS descriptor cache.
        write(gadget/'os_desc/qw_sign','MSFT100')
        write(gadget/'os_desc/b_vendor_code','1')
        if not (gadget/'os_desc/c.1').exists():(gadget/'os_desc/c.1').symlink_to(config)
        write(gadget/'os_desc/use','1')
        write(gadget/'bcdDevice',f'0x{int(original["fields"]["bcdDevice"],16)+1:04x}')
        write(gadget/'UDC',original['udc'])
    except Exception:
        restore(gadget,original)
        raise


def detach():
    if STATE.is_file() and GADGET.exists():
        restore(GADGET,json.loads(STATE.read_text()))


def unit_text():
    return f'''[Unit]
Description=Math Tutor read-only USB setup drive
Requires=adbd.service
After=adbd.service
PartOf=adbd.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/python3 {PROGRAM} --attach
ExecStop=/usr/bin/python3 {PROGRAM} --detach
TimeoutStartSec=20
TimeoutStopSec=20

[Install]
WantedBy=adbd.service
'''


def install(image, sha):
    verify_image(image)
    if digest(image)!=sha:raise ValueError('Setup image checksum mismatch')
    if 'uno' not in Path('/sys/firmware/devicetree/base/model').read_text().lower():
        raise ValueError('Expected Arduino UNO Q')
    subprocess.run(['modprobe','-n','usb_f_mass_storage'],check=True)
    # Fail before touching USB if the image format is invalid.
    subprocess.run(['/usr/sbin/fsck.fat','-n',str(image)],check=True)
    if UNIT.exists():subprocess.run(['systemctl','stop','math-tutor-usb-drive'],check=True)
    STATE_DIR.mkdir(parents=True,exist_ok=True)
    PROGRAM.parent.mkdir(parents=True,exist_ok=True)
    staged=STATE_DIR/'MATHTUTOR.pending'
    shutil.copyfile(image,staged)
    staged.chmod(0o644)
    staged.replace(IMAGE)
    shutil.copyfile(Path(__file__).resolve(),PROGRAM)
    PROGRAM.chmod(0o755)
    UNIT.write_text(unit_text())
    subprocess.run(['systemd-analyze','verify',str(UNIT)],check=True)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','math-tutor-usb-drive'],check=True)
    try:
        subprocess.run(['systemctl','start','math-tutor-usb-drive'],check=True)
    except subprocess.CalledProcessError:
        subprocess.run(['systemctl','disable','math-tutor-usb-drive'],check=False)
        raise
    print('Read-only MATHTUTOR drive enabled. ADB and serial are retained.')
    print('Rollback: sudo python3 '+str(PROGRAM)+' --uninstall')


def uninstall():
    subprocess.run(['systemctl','disable','--now','math-tutor-usb-drive'],check=True)
    UNIT.unlink(missing_ok=True)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    print('Setup drive disabled; image and logs retained. Arduino tutor data is unchanged.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--install',type=Path)
    mode.add_argument('--attach',action='store_true')
    mode.add_argument('--detach',action='store_true')
    mode.add_argument('--uninstall',action='store_true')
    parser.add_argument('--sha256')
    args=parser.parse_args()
    if os.geteuid()!=0:parser.error('Run this board setup command with sudo in your own terminal')
    try:
        if args.install:
            if not args.sha256:raise ValueError('--sha256 is required for installation')
            install(args.install,args.sha256)
        elif args.attach:attach()
        elif args.detach:detach()
        else:uninstall()
    except (OSError,ValueError,subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__=='__main__':main()
