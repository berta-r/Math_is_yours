"""Build the self-contained Windows setup and FAT16 delivery image on Windows.

Build dependency: PyInstaller in a separate PC environment. No build tools or
packages are installed on the Arduino; frozen PC artifacts are kept in results/.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from laptop.usb_launcher import find_adb
from laptop.setup_drive import build_image


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True)
    parser.add_argument('--adb')
    parser.add_argument('--version',default=datetime.now(timezone.utc).strftime('1.0.%Y%m%d%H%M%S'))
    args=parser.parse_args()
    if os.name!='nt':parser.error('Build the Windows runtime on Windows')
    import tkinter
    tkinter.Tcl()  # Fail early if the build account cannot read Tcl/Tk resources.
    if not args.serial or any(c.isspace() for c in args.serial):parser.error('Use the exact USB serial')
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.' for c in args.version):parser.error('Invalid version')
    build=ROOT/'results/windows-setup'/args.version
    if build.exists():parser.error('This version already exists; choose a new version')
    build.mkdir(parents=True)
    pyinstaller=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed',
                 '--paths',str(ROOT),'--distpath',str(build/'dist'),'--workpath',str(build/'work'),'--specpath',str(build)]
    subprocess.run([*pyinstaller,'--onedir','--name','MathTutor',str(ROOT/'laptop/tutor_desktop.py')],check=True)
    runtime=build/'dist/MathTutor'
    if not (runtime/'_internal/_tcl_data/init.tcl').is_file():
        raise RuntimeError('The GUI runtime was not bundled; do not distribute this build')
    adbdir=Path(find_adb(args.adb)).parent
    (runtime/'adb').mkdir()
    for name in ('adb.exe','AdbWinApi.dll','AdbWinUsbApi.dll','NOTICE.txt','source.properties'):
        shutil.copy2(adbdir/name,runtime/'adb'/name)
    # Preserve licenses for the redistributed runtime and USB tools.
    notices=runtime/'licenses';notices.mkdir()
    for name,source in (('PYTHON.txt',Path(sys.base_prefix)/'LICENSE.txt'),
                        ('TCL.txt',Path(sys.base_prefix)/'tcl/tcl8.6/license.terms'),
                        ('TK.txt',Path(sys.base_prefix)/'tcl/tk8.6/license.terms')):
        if source.is_file():shutil.copy2(source,notices/name)
    distribution=importlib.metadata.distribution('pyinstaller')
    for relative in distribution.files or []:
        if str(relative).endswith(('COPYING.txt','COPYING','LICENSE')):
            source=Path(distribution.locate_file(relative))
            if source.is_file():shutil.copy2(source,notices/('PYINSTALLER-'+source.name))
    (notices/'ABOUT.txt').write_text('Math Tutor companion. Contains CPython, Tcl/Tk, PyInstaller bootloader and Android Debug Bridge. See the included license and adb/NOTICE.txt files. No student data or models are packaged here.\n',encoding='utf-8')
    payload=build/'payload.zip'
    manifest={'version':args.version,'platform':'Windows x64','board':{'serial':args.serial,'port':7013},'files':{}}
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(runtime.rglob('*')):
            if path.is_file():
                name=path.relative_to(runtime).as_posix()
                manifest['files'][name]=hashlib.sha256(path.read_bytes()).hexdigest()
                archive.write(path,name)
    manifest_path=build/'manifest.json';manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    subprocess.run([*pyinstaller,'--onefile','--name','START',
                    '--add-data',str(payload)+os.pathsep+'.','--add-data',str(manifest_path)+os.pathsep+'.',
                    str(ROOT/'laptop/tutor_setup.py')],check=True)
    setup=build/'dist/START.exe'
    readme=build/'README.HTM'
    readme.write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Math Tutor · Start here</title><style>body{font:18px/1.6 system-ui;max-width:680px;margin:70px auto;padding:24px;color:#242b31;background:#faf8f3}h1{font-size:42px;line-height:1.1}li{margin:16px 0}small{color:#555}</style><h1>Your notebook travels with your Arduino.</h1><p>One setup on each Windows 10/11 computer (64-bit).</p><ol><li>Keep the Arduino connected.</li><li>Open <strong>START.EXE</strong> from this drive.</li><li>Click <strong>Set up this computer</strong>. Your browser opens when the Arduino is ready.</li></ol><p>Next time, just plug in the Arduino while signed in to Windows. Your model and progress stay on the board. Python and Arduino App Lab are not required.</p><p>This prototype setup is unsigned; Windows or a managed school computer may require approval. Do not disable security protections. macOS and Linux installers are not included.</p><small>To turn off automatic opening, open the installed MathTutor.exe from %LOCALAPPDATA%\\KangarooTutor\\releases, then choose “Turn off automatic opening”.</small></html>''',encoding='utf-8')
    readme.write_text(readme.read_text(encoding='utf-8').replace('open the installed MathTutor.exe from %LOCALAPPDATA%\\KangarooTutor\\releases, then choose', 'open <strong>Math Tutor</strong> from the Windows Start menu, then choose'),encoding='utf-8')
    versionfile=build/'VERSION.TXT';versionfile.write_text(args.version+'\nUSB serial: '+args.serial+'\n')
    image=build_image({'START.EXE':setup,'README.HTM':readme,'VERSION.TXT':versionfile},build/'MATHTUTOR.img')
    summary={'version':args.version,'setup':str(setup),'setup_sha256':hashlib.sha256(setup.read_bytes()).hexdigest(),
             'setup_bytes':setup.stat().st_size,'runtime_files':len(manifest['files']),
             'image_sha256':hashlib.sha256((build/'MATHTUTOR.img').read_bytes()).hexdigest(),**image}
    (build/'build-report.json').write_text(json.dumps(summary,indent=2)+'\n')
    (ROOT/'results/windows-setup-latest.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
