"""One-time, offline, per-user Windows setup with an explicit setup button."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zipfile

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from laptop.usb_launcher import RUN_NAME, single_instance
from laptop.tutor_desktop import release_lock


def resource_folder():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).parent))


def checked_manifest(payload, manifest):
    expected = manifest['files']
    if not isinstance(expected, dict) or not expected or len(expected) > 5000:
        raise ValueError('Invalid setup manifest')
    with zipfile.ZipFile(payload) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names) or set(names) != set(expected):
            raise ValueError('Setup contents do not match their manifest')
        total = 0
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if (path.is_absolute() or '..' in path.parts or '\\' in info.filename or ':' in info.filename
                    or stat.S_ISLNK(info.external_attr >> 16) or info.is_dir()):
                raise ValueError('Unsafe setup archive path')
            total += info.file_size
            if total > 200*1024*1024:
                raise ValueError('Setup archive exceeds its size limit')
            actual = hashlib.sha256(archive.read(info)).hexdigest()
            if actual != expected[info.filename]:
                raise ValueError('Setup file failed its integrity check: '+info.filename)
    if not {'MathTutor.exe','adb/adb.exe','adb/AdbWinApi.dll','adb/AdbWinUsbApi.dll'} <= set(expected):
        raise ValueError('Setup is missing its bundled runtime or USB tools')


def startup_command(executable, config):
    return subprocess.list2cmdline([str(executable), '--watch', '--config', str(config)])


def register_startup(command, folder):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        try:
            current = winreg.QueryValueEx(key, RUN_NAME)[0]
            if str(folder).lower() not in current.lower():
                raise ValueError('Another application owns the tutor startup name')
        except FileNotFoundError:
            pass
        winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, command)


def create_shortcut(executable, config):
    """Use Windows' own shortcut writer; no extra PC dependencies."""
    menu=Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs'
    menu.mkdir(parents=True,exist_ok=True)
    shortcut=menu/'Math Tutor.lnk'
    def literal(value):return "'"+str(value).replace("'","''")+"'"
    code="$s=(New-Object -ComObject WScript.Shell).CreateShortcut("+literal(shortcut)+"); "
    code+="$s.TargetPath="+literal(executable)+"; $s.Arguments="+literal(subprocess.list2cmdline(['--config',str(config)]))+"; "
    code+="$s.WorkingDirectory="+literal(executable.parent)+"; $s.Description='Open or manage the Arduino Math Tutor'; $s.Save()"
    powershell=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    subprocess.run([str(powershell),'-NoProfile','-NonInteractive','-Command',code],check=True,
                   creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True,text=True,timeout=15)
    return str(shortcut)


def install(payload, manifest, folder, *, startup=True, launch=True):
    checked_manifest(payload, manifest)
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    version = manifest['version']
    if not isinstance(version,str) or not version or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.' for c in version):
        raise ValueError('Invalid build version')
    board = manifest['board']
    if not isinstance(board['serial'],str) or not board['serial'] or any(c.isspace() for c in board['serial']):
        raise ValueError('Invalid board identity')
    port = board.get('port',7013)
    if type(port) is not int or not 1024 <= port <= 65526:
        raise ValueError('Invalid launcher port')
    # Versions are immutable. Never overwrite a running executable.
    release = folder/'releases'/version
    if release.exists():
        for name,digest in manifest['files'].items():
            p = release/name
            if not p.is_file() or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:
                raise ValueError('Existing version differs; rebuild with a new version or repair the installation')
    else:
        release.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='staging-',dir=release.parent) as temporary:
            stage = Path(temporary)/'app'
            stage.mkdir()
            with zipfile.ZipFile(payload) as archive:
                archive.extractall(stage)
            stage.rename(release)
    config_path = folder/'config.json'
    old_port = port
    if config_path.is_file():
        old_port = json.loads(config_path.read_text(encoding='utf-8'))['port']
    # Installed watchers observe this marker. A manually started legacy watcher
    # must be closed in its terminal before setup can take over its mutex.
    (folder/'stop').touch()
    locks=[]
    try:
        for watched_port in sorted({port,old_port}):
            deadline=time.monotonic()+20
            while True:
                try:
                    locks.append(single_instance(watched_port))
                    break
                except ValueError:
                    if time.monotonic()>=deadline:
                        raise ValueError('Close the temporary USB watcher, then run setup again.')
                    time.sleep(.2)
        config = {'serial':board['serial'], 'adb':str(release/'adb/adb.exe'), 'port':port, 'board_port':7011}
        temporary_config=folder/'config.pending'
        temporary_config.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
        temporary_config.replace(config_path)
        executable=release/'MathTutor.exe'
        command=startup_command(executable,config_path)
        if startup:
            register_startup(command,folder)
            create_shortcut(executable,config_path)
        (folder/'installation.json').write_text(json.dumps({'version':version,'executable':str(executable),
            'startup_command':command,'board_serial':board['serial'],'installed':time.time()},indent=2),encoding='utf-8')
        (folder/'stop').unlink(missing_ok=True)
    finally:
        for lock in locks:release_lock(lock)
    if launch:
        subprocess.Popen([str(executable),'--watch','--config',str(config_path)],
                         creationflags=subprocess.CREATE_NO_WINDOW,close_fds=True)
    return {'folder':str(folder),'version':version,'executable':str(executable),
            'startup_registered':startup,'watcher_started':launch}


def gui(payload, manifest):
    import tkinter as tk
    from tkinter import ttk, messagebox
    root=tk.Tk()
    root.title('Set up Math Tutor')
    root.geometry('560x365')
    root.resizable(False,False)
    frame=ttk.Frame(root,padding=30)
    frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='Plug in. Keep learning.',font=('Segoe UI',20,'bold')).pack(anchor='w')
    ttk.Label(frame,text='Set up this Windows computer once.',font=('Segoe UI',12)).pack(anchor='w',pady=(10,16))
    ttk.Label(frame,text='After setup, connecting your Arduino opens your math notebook.\n\nA small launcher starts when you sign in to Windows.\nYour model, exercises and progress stay on the Arduino.\nNo Python or Arduino App Lab installation is needed.',
              wraplength=495).pack(anchor='w')
    status=tk.StringVar(value='Windows 10/11, 64-bit. Keep the Arduino connected.')
    ttk.Label(frame,textvariable=status,wraplength=495).pack(anchor='w',pady=(16,10))
    def setup():
        button.configure(state='disabled')
        status.set('Setting up this computer…')
        root.update_idletasks()
        try:
            result=install(payload,manifest,Path(os.environ['LOCALAPPDATA'])/'MathIsYours')
        except Exception as error:
            messagebox.showerror('Setup could not finish',str(error),parent=root)
            status.set('Your Arduino notebooks have not been changed.')
            button.configure(state='normal')
            return
        status.set('Ready. Your browser opens when the Arduino is ready. You can close this window.')
        button.configure(text='Done',state='normal',command=root.destroy)
    button=ttk.Button(frame,text='Set up this computer',command=setup)
    button.pack(anchor='w',pady=4)
    root.mainloop()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accept',action='store_true',help='Explicitly accept setup from a terminal or authorized test')
    parser.add_argument('--verify',type=Path,help='Verify payload only and write a report; no installation')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    payload=resource_folder()/'payload.zip'
    manifest=json.loads((resource_folder()/'manifest.json').read_text(encoding='utf-8'))
    try:
        if args.verify:
            checked_manifest(payload,manifest)
            args.verify.write_text(json.dumps({'valid':True,'version':manifest['version'],
                'files':len(manifest['files']),'frozen':bool(getattr(sys,'frozen',False))},indent=2))
        elif args.accept:
            result=install(payload,manifest,Path(os.environ['LOCALAPPDATA'])/'MathIsYours')
            if args.report:args.report.write_text(json.dumps(result,indent=2))
        else:
            gui(payload,manifest)
    except Exception as error:
        if args.report:
            args.report.write_text(json.dumps({'error':str(error)}))
        elif args.verify:
            args.verify.write_text(json.dumps({'valid':False,'error':str(error)}))
        else:
            import tkinter.messagebox
            tkinter.messagebox.showerror('Math Tutor setup',str(error))
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
