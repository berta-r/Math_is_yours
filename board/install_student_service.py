#!/usr/bin/env python3
"""Install the student application as an unprivileged systemd boot service.

Run on the UNO Q Linux side. --print-unit is read-only. Models must be installed
using the existing board setup scripts before enabling --local-tutor.
"""
import argparse
from datetime import datetime, timezone
import getpass
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from board.release_data import validate as validate_release_data
SERVICE = '/etc/systemd/system/math-student.service'
DATABASE = '/var/lib/math-student/progress.db'


def unit_text(root, user, port=7011, local_tutor=False, safe_shutdown=False):
    # ExecStart splits words; WorkingDirectory treats quotes as literal path bytes.
    if any(c in str(root) for c in ('\n', '\r', '"', '\\', '%', '$')):
        raise ValueError('Use a deployment path without quotes, backslashes, percent/dollar signs or newlines')
    if not user or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in user):
        raise ValueError('Unsupported service user name')
    dependency = 'After=math-llm.service\nWants=math-llm.service\n' if local_tutor else ''
    return f'''[Unit]
Description=Kangaroo offline student tutor
{dependency}
[Service]
Type=simple
User={user}
WorkingDirectory={root}
StateDirectory=math-student
StateDirectoryMode=0700
ExecStart=/usr/bin/python3 -u "{root}/student_app/server.py" --port {port} --db {DATABASE}{' --local-tutor' if local_tutor else ''}{' --safe-shutdown' if safe_shutdown else ''}
Restart=on-failure
RestartSec=3
TimeoutStopSec=40
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
UMask=0077
MemoryAccounting=true
MemoryMax=256M

[Install]
WantedBy=multi-user.target
'''


def shutdown_units():
    """A fixed root action triggered by one marker; the web app stays unprivileged."""
    return {
        'math-student-poweroff.path': '''[Unit]
Description=Watch for an explicit saved-session shutdown request
After=math-student.service
Wants=math-student.service

[Path]
PathExists=/var/lib/math-student/poweroff.request
Unit=math-student-poweroff.service

[Install]
WantedBy=multi-user.target
''',
        'math-student-poweroff.service': '''[Unit]
Description=Safely power off the tutor after an explicit student request

[Service]
Type=oneshot
ExecStartPre=/usr/bin/rm -f /var/lib/math-student/poweroff.request
ExecStart=/usr/bin/sleep 4
ExecStartPost=/usr/bin/systemctl poweroff
'''}


def backup_existing(root, database=DATABASE, service=SERVICE):
    """Snapshot existing notebooks before a new process can migrate the schema."""
    database, service = Path(database), Path(service)
    if not database.is_file() and not service.is_file():
        return None
    parent = Path(root) / 'install-backups'
    parent.mkdir(mode=0o700, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-')
    folder = Path(tempfile.mkdtemp(prefix=stamp, dir=parent))
    if database.is_file():
        source = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
        target = sqlite3.connect(folder / 'progress.db')
        try:
            source.backup(target)
            if target.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('Notebook backup failed its integrity check; service was not changed')
        finally:
            target.close()
            source.close()
        (folder / 'progress.db').chmod(0o600)
    if service.is_file():
        (folder / 'math-student.service').write_bytes(service.read_bytes())
    (Path(root) / 'last-install-backup.txt').write_text(str(folder), encoding='utf-8')
    return folder


def main():
    import pwd  # Linux-only installation; unit rendering can be tested on the PC.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user', default=os.environ.get('SUDO_USER') or getpass.getuser())
    parser.add_argument('--port', type=int, default=7011)
    parser.add_argument('--local-tutor', action='store_true')
    parser.add_argument('--safe-shutdown', action='store_true', help='Install the narrowly scoped shutdown path service and enable the UI control')
    parser.add_argument('--allow-data-change', action='store_true', help='Explicitly allow removal of installed training IDs or ML artifacts')
    parser.add_argument('--import-progress', type=Path, help='Optional SQLite snapshot; accepted only if board database does not exist')
    parser.add_argument('--print-unit', action='store_true')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Choose an unprivileged TCP port between 1024 and 65535')
    try:
        account = pwd.getpwnam(args.user)
        if account.pw_uid == 0:
            raise ValueError('The service must run as an unprivileged user; pass --user arduino')
        unit = unit_text(ROOT, args.user, args.port, args.local_tutor, args.safe_shutdown)
        if args.print_unit:
            print(unit)
            return
        if not (ROOT/'student_app/server.py').is_file() or not (ROOT/'knowledge/model.json').is_file():
            raise ValueError('Deploy the complete app, copilot and knowledge folders first')
        if args.local_tutor:
            result = subprocess.run(['systemctl', 'show', 'math-llm.service', '--property=LoadState', '--value'], capture_output=True, text=True, check=True)
            if result.stdout.strip() != 'loaded':
                raise ValueError('math-llm.service is not installed. Complete board setup steps 0-7 first, or omit --local-tutor for stored guidance.')
        if args.import_progress:
            # A failed sudo prompt must not be mistaken for an absent database.
            check = subprocess.run(['sudo', 'python3', '-c',
                                    'from pathlib import Path; print(int(Path(' + repr(DATABASE) + ').exists()))'],
                                   check=True, capture_output=True, text=True)
            if check.stdout.strip() != '0':
                raise ValueError('Board progress already exists; refusing to overwrite it')
            if not args.import_progress.is_file():
                raise ValueError('The requested progress snapshot does not exist')
        validate_release_data(ROOT, SERVICE, args.allow_data_change)
        backup = backup_existing(ROOT)
        if backup:
            print('Existing notebooks and service backed up to ' + str(backup))
        with tempfile.TemporaryDirectory(prefix='math-student-install-') as folder:
            template = Path(folder)/'math-student.service'
            template.write_text(unit, encoding='utf-8')
            # Validate with the actual board systemd before touching its service.
            subprocess.run(['systemd-analyze', 'verify', str(template)], check=True)
            if args.safe_shutdown:
                for name,text in shutdown_units().items():
                    (Path(folder)/name).write_text(text,encoding='utf-8')
                subprocess.run(['systemd-analyze','verify',str(Path(folder)/'math-student-poweroff.path'),str(Path(folder)/'math-student-poweroff.service')],check=True)
            if args.import_progress:
                snapshot = Path(folder)/'progress.db'
                source = sqlite3.connect(f'file:{args.import_progress.resolve().as_posix()}?mode=ro', uri=True)
                target = sqlite3.connect(snapshot)
                try:
                    source.backup(target)
                finally:
                    source.close()
                    target.close()
                subprocess.run(['sudo', 'install', '-d', '-m', '0700', '-o', args.user, '-g', str(account.pw_gid), '/var/lib/math-student'], check=True)
                subprocess.run(['sudo', 'install', '-m', '0600', '-o', args.user, '-g', str(account.pw_gid), str(snapshot), DATABASE], check=True)
            subprocess.run(['sudo', 'install', '-m', '0644', str(template), SERVICE], check=True)
            if args.safe_shutdown:
                for name in shutdown_units():
                    subprocess.run(['sudo','install','-m','0644',str(Path(folder)/name),'/etc/systemd/system/'+name],check=True)
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        subprocess.run(['sudo', 'systemctl', 'enable', 'math-student.service'], check=True)
        subprocess.run(['sudo', 'systemctl', 'restart', 'math-student.service'], check=True)
        if args.safe_shutdown:
            subprocess.run(['sudo','systemctl','enable','--now','math-student-poweroff.path'],check=True)
        subprocess.run(['systemctl', 'status', 'math-student.service', '--no-pager'], check=True)
        print(f'Boot service installed. Progress: {DATABASE}. App: http://127.0.0.1:{args.port}')
        print('Check readiness: curl http://127.0.0.1:%d/api/health' % args.port)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
