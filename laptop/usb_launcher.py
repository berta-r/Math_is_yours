"""Connect the installed UNO Q tutor over USB and open its local browser UI.

Standard library only. No models or student data run on the computer. Windows
installation is per-user and explicit; an arbitrary USB device cannot auto-run it.
"""
import argparse
import ctypes
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

APP_ID = 'math-is-yours'
RUN_NAME = 'MathIsYoursUSB'
LOG = logging.getLogger('kangaroo-usb')


def find_adb(explicit=None):
    candidates = [explicit, shutil.which('adb')]
    local = Path(os.environ.get('LOCALAPPDATA', Path.home()))
    candidates.append(local/'Android/Sdk/platform-tools/adb.exe')
    candidates.extend(sorted((local/'Arduino15/packages/arduino/tools/adb').glob('*/adb.exe'), reverse=True))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    raise ValueError('ADB was not found. Install Arduino App Lab or Android platform-tools once, or pass --adb PATH.')


class Adb:
    def __init__(self, executable):
        self.executable = executable

    def run(self, *args):
        result = subprocess.run([self.executable, *args], capture_output=True, text=True,
                                timeout=8, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if result.returncode:
            raise OSError(result.stderr.strip() or 'ADB command failed')
        return result.stdout

    def devices(self):
        result = {}
        for line in self.run('devices').splitlines():
            fields = line.split()
            if len(fields) >= 2 and not line.startswith(('List ', '*')):
                result[fields[0]] = fields[1]
        return result

    def forwards(self):
        return [tuple(line.split()) for line in self.run('forward', '--list').splitlines() if len(line.split()) == 3]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def health(port):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(f'http://127.0.0.1:{port}/api/health', timeout=2) as response:
            data = json.loads(response.read(65536))
        return data if isinstance(data, dict) and data.get('app') == APP_ID and data.get('status') == 'ready' else None
    except (OSError, ValueError):
        return None


def port_available(port):
    with socket.socket() as sock:
        if os.name == 'nt':
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            sock.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


class Watcher:
    def __init__(self, adb, serial, port=7011, board_port=7011, probe=health, open_browser=webbrowser.open, available=port_available):
        self.adb, self.serial = adb, serial
        self.port, self.board_port = port, board_port
        self.probe, self.open_browser, self.available = probe, open_browser, available
        self.forward_port = None
        self.owns_forward = False
        self.opened = False

    def release(self):
        try:
            if self.owns_forward and self.forward_port is not None:
                expected = (self.serial, f'tcp:{self.forward_port}', f'tcp:{self.board_port}')
                if expected in self.adb.forwards():
                    self.adb.run('-s', self.serial, 'forward', '--remove', f'tcp:{self.forward_port}')
        finally:
            self.forward_port, self.owns_forward = None, False

    def connect(self):
        forwards = self.adb.forwards()
        for candidate in range(self.port, min(self.port + 10, 65536)):
            local = f'tcp:{candidate}'
            existing = [f for f in forwards if f[1] == local]
            if existing:
                if existing == [(self.serial, local, f'tcp:{self.board_port}')]:
                    self.forward_port = candidate
                    return
                continue
            if not self.available(candidate):
                continue
            try:
                # Refuse to replace another ADB forward, including during races.
                self.adb.run('-s', self.serial, 'forward', '--no-rebind', local, f'tcp:{self.board_port}')
            except OSError:
                continue
            self.forward_port, self.owns_forward = candidate, True
            return
        raise OSError('No free local port in the selected ten-port range. Close an old tutor or use --port.')

    def tick(self):
        state = self.adb.devices().get(self.serial)
        if state != 'device':
            self.opened = False
            self.release()
            return 'Waiting for the configured board' + (f' ({state})' if state else '')
        if self.forward_port is not None:
            expected = (self.serial, f'tcp:{self.forward_port}', f'tcp:{self.board_port}')
            if expected not in self.adb.forwards():
                self.forward_port, self.owns_forward, self.opened = None, False, False
        if self.forward_port is None:
            self.connect()
        info = self.probe(self.forward_port)
        if not info:
            return 'Board connected; waiting for the student application'
        if not self.opened:
            url = f'http://127.0.0.1:{self.forward_port}'
            if self.open_browser(url) is False:
                raise OSError(f'Could not open a browser. Open {url} manually.')
            self.opened = True
        return f'Tutor open at http://127.0.0.1:{self.forward_port}; model {info.get("model", {}).get("state", "unknown")}'


def installation_dir():
    if os.name != 'nt':
        raise ValueError('Login installation is Windows-only. Use watch or open on other systems.')
    return Path(os.environ['LOCALAPPDATA'])/'MathIsYours'


def install(args):
    import winreg
    folder = installation_dir()
    adb = find_adb(args.adb)
    # An installation launched from .venv should survive removing that checkout.
    interpreter = Path(getattr(sys, '_base_executable', sys.executable)).with_name('pythonw.exe')
    if not interpreter.is_file():
        raise ValueError('This Windows installation needs pythonw.exe next to Python.')
    folder.mkdir(parents=True, exist_ok=True)
    previous_config = folder/'config.json'
    previous_port = args.port
    if previous_config.is_file():
        previous_port = json.loads(previous_config.read_text(encoding='utf-8')).get('port', args.port)
    (folder/'stop').write_text('Restart for updated configuration.\n', encoding='utf-8')
    deadline = time.monotonic() + 30
    for watched_port in {previous_port, args.port}:
        while True:
            try:
                previous_lock = single_instance(watched_port)
                if previous_lock:
                    kernel = ctypes.WinDLL('kernel32')
                    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
                    kernel.CloseHandle(previous_lock)
                break
            except ValueError:
                if time.monotonic() >= deadline:
                    raise ValueError('The previous watcher has not stopped yet. Stop any manual watch command, wait a moment, and run install again.')
                time.sleep(.25)
    target = folder/'usb_launcher.py'
    if Path(__file__).resolve() != target.resolve():
        shutil.copy2(__file__, target)
    config = {'serial':args.serial, 'adb':adb, 'port':args.port, 'board_port':args.board_port}
    config_file = folder/'config.json'
    config_file.write_text(json.dumps(config, indent=2)+'\n', encoding='utf-8')
    command = subprocess.list2cmdline([str(interpreter), str(target), 'watch', '--config', str(config_file)])
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, command)
    # A previous watcher exits when the marker exists; a new install starts afresh.
    (folder/'stop').unlink(missing_ok=True)
    subprocess.Popen([str(interpreter), str(target), 'watch', '--config', str(config_file)],
                     creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True)
    print(f'Installed for this Windows user. The tutor opens after this board connects: {args.serial}')
    print(f'Logs: {folder / "launcher.log"}. Keep this Python installation available.')


def uninstall():
    import winreg
    folder = installation_dir()
    folder.mkdir(parents=True, exist_ok=True)
    (folder/'stop').write_text('Stop the installed watcher.\n', encoding='utf-8')
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, RUN_NAME)
    except FileNotFoundError:
        pass
    print('Automatic opening disabled. The watcher will stop; configuration and logs are kept for inspection.')


def single_instance(port):
    if os.name != 'nt':
        return None
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    ctypes.set_last_error(0)
    handle = kernel.CreateMutexW(None, False, f'Local\\MathIsYoursUSB-{port}')
    if not handle:
        raise OSError('Could not acquire the launcher instance lock')
    if ctypes.get_last_error() == 183:
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle(handle)
        raise ValueError('A tutor launcher is already running for this port range.')
    return handle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['devices', 'open', 'watch', 'install', 'uninstall'])
    parser.add_argument('--serial', help='Exact USB serial from devices; required for opening or installation')
    parser.add_argument('--adb', help='Path to adb.exe; auto-detected from PATH or Arduino/Android installations')
    parser.add_argument('--port', type=int, default=7011)
    parser.add_argument('--board-port', type=int, default=7011)
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    try:
        if args.config:
            for key, value in json.loads(args.config.read_text(encoding='utf-8')).items():
                if key not in ('serial', 'adb', 'port', 'board_port'):
                    raise ValueError('Unexpected launcher configuration key')
                setattr(args, key, value)
        if not all(isinstance(p, int) and 1024 <= p <= 65526 for p in (args.port, args.board_port)):
            raise ValueError('Ports must be integers between 1024 and 65526')
        if args.command == 'uninstall':
            return uninstall()
        adb = Adb(find_adb(args.adb))
        if args.command == 'devices':
            print(json.dumps(adb.devices(), indent=2))
            return
        if not isinstance(args.serial, str) or not args.serial.strip() or any(c.isspace() for c in args.serial):
            raise ValueError('Pass --serial with the exact board serial shown by devices.')
        if args.command == 'install':
            return install(args)
        lock = single_instance(args.port)
        folder = args.config.parent if args.config else None
        if folder:
            handler = RotatingFileHandler(folder/'launcher.log', maxBytes=200000, backupCount=2, encoding='utf-8')
        else:
            handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        LOG.addHandler(handler)
        LOG.setLevel(logging.INFO)
        watcher = Watcher(adb, args.serial, args.port, args.board_port)
        previous = None
        try:
            while not folder or not (folder/'stop').exists():
                try:
                    state = watcher.tick()
                except (OSError, subprocess.TimeoutExpired) as error:
                    state = str(error)
                if state != previous:
                    LOG.info(state)
                    previous = state
                if args.command == 'open' and watcher.opened:
                    # Keep ADB forwarding alive for the newly opened browser.
                    return
                time.sleep(2)
        except KeyboardInterrupt:
            pass
        finally:
            if args.command != 'open' or not watcher.opened:
                try:
                    watcher.release()
                except (OSError, subprocess.TimeoutExpired):
                    pass
            if lock:
                kernel = ctypes.WinDLL('kernel32')
                kernel.CloseHandle.argtypes = [ctypes.c_void_p]
                kernel.CloseHandle(lock)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
