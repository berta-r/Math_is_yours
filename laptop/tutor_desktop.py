"""Frozen Windows USB companion. No student data or model inference on the PC."""
import argparse
import ctypes
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import subprocess
import sys
import time
import webbrowser

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from laptop.usb_launcher import Adb, Watcher, RUN_NAME, single_instance


def app_folder():
    return Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent


def install_folder():
    return Path(os.environ['LOCALAPPDATA']) / 'MathIsYours'


def load_config(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if set(data) != {'serial', 'adb', 'port', 'board_port'}:
        raise ValueError('The tutor configuration is incomplete. Run setup again.')
    if not isinstance(data['serial'], str) or not data['serial'] or any(c.isspace() for c in data['serial']):
        raise ValueError('Invalid board serial')
    for key in ('port', 'board_port'):
        if type(data[key]) is not int or not 1024 <= data[key] <= 65526:
            raise ValueError('Invalid tutor port')
    if not Path(data['adb']).is_file():
        raise ValueError('The bundled USB tools are missing. Run setup again.')
    return data


def release_lock(handle):
    if handle:
        kernel = ctypes.WinDLL('kernel32')
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle(handle)


def watch(config):
    data = load_config(config)
    folder = config.parent
    lock = single_instance(data['port'])
    logger = logging.getLogger('kangaroo-desktop')
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(folder/'launcher.log', maxBytes=200000, backupCount=2, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    logger.addHandler(handler)
    watcher = Watcher(Adb(data['adb']), data['serial'], data['port'], data['board_port'])
    previous = None
    (folder/'watcher.pid').write_text(str(os.getpid()))
    try:
        while not (folder/'stop').exists():
            try:
                if (folder/'open-now').exists():
                    (folder/'open-now').unlink()
                    watcher.opened = False
                state = watcher.tick()
            except (OSError, subprocess.TimeoutExpired) as error:
                state = 'Waiting for USB: ' + str(error)
            if state != previous:
                logger.info(state)
                (folder/'status.json').write_text(json.dumps({'message':state, 'url':
                    f'http://127.0.0.1:{watcher.forward_port}' if watcher.opened else None,
                    'pid':os.getpid(), 'updated':time.time()}), encoding='utf-8')
                previous = state
            time.sleep(2)
    finally:
        try:
            watcher.release()
        finally:
            release_lock(lock)
            (folder/'watcher.pid').unlink(missing_ok=True)
            logger.removeHandler(handler)
            handler.close()


def start_watcher(config):
    data = load_config(config)
    try:
        lock = single_instance(data['port'])
    except ValueError:
        (config.parent/'open-now').touch()
        return
    release_lock(lock)
    (config.parent/'stop').unlink(missing_ok=True)
    command = [sys.executable, '--watch', '--config', str(config)]
    if not getattr(sys, 'frozen', False):
        command.insert(1, str(Path(__file__).resolve()))
    subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True)


def disable(folder):
    import winreg
    (folder/'stop').touch()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0,
                            winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as key:
            current = winreg.QueryValueEx(key, RUN_NAME)[0]
            # Remove only the entry pointing to this installation.
            if str(folder).lower() in current.lower():
                winreg.DeleteValue(key, RUN_NAME)
    except FileNotFoundError:
        pass


def settings(config):
    import tkinter as tk
    from tkinter import ttk, messagebox
    root = tk.Tk()
    root.title('Math Tutor')
    root.geometry('510x285')
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=28)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Your Arduino math companion', font=('Segoe UI', 17, 'bold')).pack(anchor='w')
    status = tk.StringVar(value='Connect your Arduino to open your notebook.')
    ttk.Label(frame, textvariable=status, wraplength=440).pack(anchor='w', pady=(18,20))
    def open_tutor():
        try:
            start_watcher(config)
            status.set('Waiting for your Arduino. Your browser will open when it is ready.')
        except (OSError, ValueError) as e:
            messagebox.showerror('Math Tutor', str(e), parent=root)
    def stop():
        disable(config.parent)
        status.set('Automatic opening is off. Your Arduino notebooks are kept. Run setup to enable it again.')
    ttk.Button(frame, text='Open my notebook', command=open_tutor).pack(anchor='w', pady=4)
    ttk.Button(frame, text='Turn off automatic opening', command=stop).pack(anchor='w', pady=4)
    ttk.Label(frame, text='Your maths and progress stay on the Arduino.', foreground='#555555').pack(anchor='w', pady=(18,0))
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--check', type=Path, help='Write a bundled-runtime diagnostic report; no installation changes')
    args = parser.parse_args()
    try:
        if args.check:
            adb_path = app_folder()/'adb/adb.exe'
            adb = Adb(str(adb_path))
            report = {'frozen':bool(getattr(sys,'frozen',False)), 'executable':sys.executable,
                      'bundled_adb':str(adb_path), 'adb_version':adb.run('version').strip(), 'devices':adb.devices()}
            args.check.write_text(json.dumps(report,indent=2), encoding='utf-8')
            return
        config = args.config or install_folder()/'config.json'
        if args.watch:
            watch(config)
        else:
            settings(config)
    except (OSError, ValueError) as error:
        if args.watch:
            # Login launches are silent; an existing watcher owns this port.
            folder = (args.config or install_folder()/'config.json').parent
            with (folder/'launcher.log').open('a',encoding='utf-8') as f:
                f.write(str(error)+'\n')
        else:
            import tkinter.messagebox
            tkinter.messagebox.showerror('Math Tutor', str(error))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
