"""USB deployment checks; no attached board, registry changes or browser required."""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
import socket
import sqlite3
import tarfile
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from laptop.usb_launcher import Watcher, health
from laptop.deploy_student import build_bundle, bundle_files, ROOT

spec = importlib.util.spec_from_file_location('service_installer', ROOT/'board/install_student_service.py')
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


class FakeAdb:
    def __init__(self):
        self.attached = {'board': 'device'}
        self.links = []
        self.calls = []

    def devices(self):
        return self.attached

    def forwards(self):
        return self.links[:]

    def run(self, *args):
        self.calls.append(args)
        if '--remove' in args:
            self.links = [f for f in self.links if not (f[0] == args[1] and f[1] == args[-1])]
        elif '--no-rebind' in args:
            if any(f[1] == args[-2] for f in self.links):
                raise OSError('already forwarded')
            self.links.append((args[1], args[-2], args[-1]))


class WatcherTests(unittest.TestCase):
    def make(self, available=lambda port: True, ready=True):
        adb = FakeAdb()
        self.opened = []
        self.info = {'app':'kangaroo-student', 'status':'ready', 'model':{'state':'unavailable'}} if ready else None
        watcher = Watcher(adb, 'board', probe=lambda port:self.info,
                          open_browser=lambda url:self.opened.append(url), available=available)
        return adb, watcher

    def test_opens_once_after_health_then_once_after_reconnection(self):
        adb, watcher = self.make(ready=False)
        self.assertIn('waiting', watcher.tick())
        self.assertEqual(self.opened, [])
        self.info = {'model':{'state':'ready'}}
        watcher.tick()
        watcher.tick()
        self.assertEqual(self.opened, ['http://127.0.0.1:7011'])
        adb.attached = {}
        watcher.tick()
        self.assertFalse(watcher.opened)
        adb.attached = {'board':'device'}
        watcher.tick()
        self.assertEqual(len(self.opened), 2)

    def test_other_device_or_unauthorized_board_never_opens(self):
        adb, watcher = self.make()
        for attached in [{'phone':'device'}, {'board':'unauthorized'}, {'board':'offline'}]:
            adb.attached = attached
            watcher.tick()
        self.assertEqual(self.opened, [])
        self.assertEqual(adb.calls, [])

    def test_busy_app_port_uses_next_port_without_killing_anything(self):
        adb, watcher = self.make(available=lambda port:port != 7011)
        watcher.tick()
        self.assertEqual(self.opened, ['http://127.0.0.1:7012'])
        self.assertTrue(all('--no-rebind' in call for call in adb.calls))

    def test_foreign_forward_is_not_replaced_or_removed(self):
        adb, watcher = self.make()
        foreign = ('someone-else', 'tcp:7011', 'tcp:8080')
        adb.links = [foreign]
        watcher.tick()
        self.assertEqual(watcher.forward_port, 7012)
        watcher.release()
        self.assertEqual(adb.links, [foreign])

    def test_matching_preexisting_forward_is_preserved_on_exit(self):
        adb, watcher = self.make()
        existing = ('board','tcp:7011','tcp:7011')
        adb.links = [existing]
        watcher.tick()
        watcher.release()
        self.assertEqual(adb.links, [existing])
        self.assertEqual(adb.calls, [])

    def test_full_port_range_reports_problem_without_opening(self):
        _, watcher = self.make(available=lambda port:False)
        with self.assertRaisesRegex(OSError, 'No free local port'):
            watcher.tick()
        self.assertEqual(self.opened, [])

    def test_daemon_forward_loss_reconnects_and_opens_again(self):
        adb, watcher = self.make()
        watcher.tick()
        adb.links = []
        watcher.tick()
        self.assertEqual(len(self.opened), 2)


class ReadinessTests(unittest.TestCase):
    def test_only_expected_application_identity_is_accepted(self):
        payload = {'app':'kangaroo-student','status':'ready','model':{'state':'unavailable'}}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1',0), Handler)
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            self.assertEqual(health(server.server_port), payload)
            payload['app'] = 'unrelated-app'
            self.assertIsNone(health(server.server_port))
            payload['app'], payload['status'] = 'kangaroo-student','starting'
            self.assertIsNone(health(server.server_port))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


class PackagingTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'linux' and shutil.which('systemd-analyze'), 'Needs Linux systemd validation')
    def test_service_is_accepted_by_systemd_with_space_in_release_path(self):
        with tempfile.TemporaryDirectory() as folder:
            unit = Path(folder)/'math-student.service'
            unit.write_text(service.unit_text('/home/arduino/math tutor', 'arduino'), encoding='utf-8')
            checked = subprocess.run(['systemd-analyze', 'verify', str(unit)], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_only_training_images_and_referenced_previews_are_selected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()  # macOS temp folders are symlinks
            images = root/'data/images'
            images.mkdir(parents=True)
            rows = [{'id':'train-one','language':'eng','option_images':['A']},
                    {'id':'train-two','language':'cat'}, {'id':'../escape','language':'eng'}]
            (root/'data/train.jsonl').write_text('\n'.join(json.dumps(p) for p in rows), encoding='utf-8')
            for name in ['train-one_eng.png','train-one_eng_option_A.png','train-one_eng_option_B.png',
                         'train-two_cat.png','validation-only_eng.png','validation-only_eng_option_A.png']:
                (images/name).write_bytes(b'invented fixture')
            (root/'data/escape_eng.png').write_bytes(b'outside images')
            names = {p.relative_to(root).as_posix() for p in bundle_files(root, with_data=True)}
            self.assertIn('data/images/train-one_eng.png', names)
            self.assertIn('data/images/train-one_eng_option_A.png', names)
            self.assertIn('data/images/train-two_cat.png', names)
            self.assertNotIn('data/images/train-one_eng_option_B.png', names)
            self.assertNotIn('data/images/validation-only_eng.png', names)
            self.assertNotIn('data/images/validation-only_eng_option_A.png', names)
            self.assertNotIn('data/escape_eng.png', names)

    def test_data_bundle_carries_ml_content_but_never_credentials_or_models(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()  # macOS temp folders are symlinks
            for name in ['data/train.jsonl', 'data/teaching_annotations.generated.json', 'data/ml/difficulty.json',
                         'data/ml/slm_explanations.json', 'data/ml/thinking_steps_generated.json', 'data/ml/embeddings.json',
                         'data/ml/features.jsonl', 'data/models/model.json', 'data/models/m.gguf', '.env.local']:
                (root/name).parent.mkdir(parents=True, exist_ok=True)
                (root/name).write_text('' if name.endswith('.jsonl') else '{}', encoding='utf-8')
            names = {p.relative_to(root).as_posix() for p in bundle_files(root, with_data=True)}
            for name in ['data/teaching_annotations.generated.json', 'data/ml/difficulty.json',
                         'data/ml/slm_explanations.json', 'data/ml/thinking_steps_generated.json']:
                self.assertIn(name, names)
            self.assertFalse({'data/ml/embeddings.json', 'data/ml/features.jsonl', '.env.local'} & names)
            self.assertFalse(any(n.startswith('data/models/') for n in names))
            self.assertNotIn('data/ml/difficulty.json', {p.relative_to(root).as_posix() for p in bundle_files(root)})
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'bundle.tar.gz'
            build_bundle(ROOT, output, with_data=(ROOT/'data/train.jsonl').is_file())
            with tarfile.open(output) as archive:
                names = archive.getnames()
            self.assertFalse(any(n.startswith('.env') or n.startswith('data/models/') for n in names))

    def test_default_bundle_excludes_private_progress_and_training_data(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'bundle.tar.gz'
            info = build_bundle(ROOT, output)
            with tarfile.open(output) as archive:
                names = archive.getnames()
                manifest = json.load(archive.extractfile('release-manifest.json'))
            self.assertEqual(set(manifest['files']), set(names) - {'release-manifest.json'})
            self.assertFalse(manifest['includes_progress'])
            self.assertTrue(info['sha256'])
            self.assertIn('student_app/server.py', names)
            self.assertIn('board/install_student_service.py', names)
            self.assertIn('data/sample_problems.jsonl', names)
            self.assertNotIn('data/train.jsonl', names)
            self.assertFalse(any(n.endswith(('.db','.gguf','.pyc')) for n in names))
            self.assertFalse(any('test_' in n or '.venv' in n or 'val.jsonl' in n for n in names))
            self.assertTrue(all(not n.startswith('/') and '..' not in n.split('/') for n in names))

    def test_service_preserves_state_and_has_optional_model_dependency(self):
        plain = service.unit_text('/home/arduino/math tutor', 'arduino')
        enabled = service.unit_text('/home/arduino/math tutor', 'arduino', local_tutor=True)
        self.assertIn('User=arduino', plain)
        self.assertIn('StateDirectory=math-student', plain)
        self.assertIn('/var/lib/math-student/progress.db', plain)
        self.assertIn('ProtectSystem=strict', plain)
        self.assertNotIn('Wants=math-llm.service', plain)
        self.assertIn('Wants=math-llm.service', enabled)
        self.assertIn('--local-tutor', enabled)
        shutdown = service.unit_text('/home/arduino/math tutor', 'arduino', local_tutor=True, safe_shutdown=True)
        self.assertIn('--safe-shutdown', shutdown)
        self.assertIn('PathExists=/var/lib/math-student/poweroff.request', service.shutdown_units()['math-student-poweroff.path'])
        self.assertIn('ExecStartPost=/usr/bin/systemctl poweroff', service.shutdown_units()['math-student-poweroff.service'])
        for root in ['/home/user/%bad', '/home/user/\nInjected=1']:
            with self.assertRaises(ValueError):
                service.unit_text(root, 'arduino')

    def test_upgrade_backup_preserves_notebooks_and_previous_unit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            db, unit = root / 'live.db', root / 'math-student.service'
            con = sqlite3.connect(db)
            try:
                con.execute('CREATE TABLE notes (body TEXT)')
                con.execute('INSERT INTO notes VALUES (?)', ('Saved before upgrade',))
                con.commit()
                unit.write_text('previous release', encoding='utf-8')
                folder = service.backup_existing(root, db, unit)
                con.execute('INSERT INTO notes VALUES (?)', ('Later entry',))
                con.commit()
                snapshot = sqlite3.connect(folder / 'progress.db')
                try:
                    self.assertEqual(snapshot.execute('SELECT body FROM notes').fetchall(), [('Saved before upgrade',)])
                finally:
                    snapshot.close()
                self.assertEqual((folder / 'math-student.service').read_text(), 'previous release')
                self.assertEqual(con.execute('SELECT COUNT(*) FROM notes').fetchone()[0], 2)
            finally:
                con.close()


if __name__ == '__main__':
    unittest.main()
