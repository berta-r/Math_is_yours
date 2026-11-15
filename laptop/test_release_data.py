"""Synthetic release tests; no M3Kang files, board or student records needed."""

import json
from pathlib import Path
import tempfile
import unittest

from board.release_data import installed_root, validate


class ReleaseDataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.old, self.new = self.base / 'old release', self.base / 'new release'
        self.old.mkdir()
        self.new.mkdir()
        self.service = self.base / 'math-student.service'
        self.service.write_text('[Service]\nExecStart=/usr/bin/python3 -u "' +
                                (self.old / 'student_app/server.py').as_posix() +
                                '" --port 7011 --db /var/lib/math-student/progress.db\n', encoding='utf-8')

    def rows(self, root, rows):
        path = root / 'data/train.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')

    def artifact(self, root, name, value=None):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value or {'version': 1}), encoding='utf-8')

    def test_find_quoted_root_and_accept_first_install(self):
        self.assertEqual(installed_root(self.service), self.old)
        self.assertIsNone(validate(self.new, self.base / 'absent.service'))

    def test_superset_training_rows_allowed_without_changing_old_files(self):
        row = {'id': 'a', 'language': 'eng', 'text': 'private training text'}
        self.rows(self.old, [row])
        self.rows(self.new, [row, {'id': 'b', 'language': 'cat'}])
        before = (self.old / 'data/train.jsonl').read_bytes()
        self.assertEqual(validate(self.new, self.service), self.old)
        self.assertEqual((self.old / 'data/train.jsonl').read_bytes(), before)

    def test_drop_language_variant_fails_with_counts_only(self):
        rows = [{'id': 'private-id', 'language': 'eng', 'text': 'PRIVATE CONTENT'},
                {'id': 'private-id', 'language': 'cat'}]
        self.rows(self.old, rows)
        self.rows(self.new, rows[:1])
        with self.assertRaises(ValueError) as raised:
            validate(self.new, self.service)
        self.assertIn('1 installed training rows', str(raised.exception))
        self.assertNotIn('PRIVATE CONTENT', str(raised.exception))
        self.assertNotIn('private-id', str(raised.exception))

    def test_code_only_release_does_not_replace_installed_training_data(self):
        self.rows(self.old, [{'id': 'a'}, {'id': 'b'}])
        with self.assertRaisesRegex(ValueError, '2 installed training rows'):
            validate(self.new, self.service)
        self.assertEqual(validate(self.new, self.service, allow_data_change=True), self.old)

    def test_current_map_and_generated_content_must_remain(self):
        artifacts = ('data/ml/problem_map.json', 'data/ml/difficulty.json',
                     'data/ml/thinking_steps_generated.json', 'data/ml/solutions_generated.json',
                     'data/ml/slm_explanations.json', 'data/ml/signatures.json',
                     'data/teaching_annotations.generated.json')
        for name in artifacts:
            self.artifact(self.old, name)
        for name in artifacts[1:]:
            self.artifact(self.new, name)
        with self.assertRaisesRegex(ValueError, 'data/ml/problem_map.json'):
            validate(self.new, self.service)
        self.artifact(self.new, artifacts[0])
        self.assertEqual(validate(self.new, self.service), self.old)

    def test_laptop_embeddings_and_features_do_not_block_runtime_release(self):
        for name in ('embeddings.json', 'features.json', 'features.jsonl'):
            self.artifact(self.old, 'data/ml/' + name)
        self.assertEqual(validate(self.new, self.service), self.old)

    def test_explicit_override_permits_known_artifact_removals(self):
        self.artifact(self.old, 'data/ml/problem_map.json')
        self.assertEqual(validate(self.new, self.service, allow_data_change=True), self.old)
        self.assertTrue((self.old / 'data/ml/problem_map.json').is_file())

    def test_invalid_training_rows_fail_without_disclosing_content(self):
        self.rows(self.old, [{'id': 'a'}])
        for rows in ([{'id': 'a'}, {'id': 'a'}], [{'id': ['private content']}],
                     [{'id': 'a', 'language': ['private content']}]):
            self.rows(self.new, rows)
            with self.assertRaisesRegex(ValueError, 'training identifier at row') as raised:
                validate(self.new, self.service, allow_data_change=True)
            self.assertNotIn('private content', str(raised.exception))

    def test_default_language_matches_catalog_semantics(self):
        self.rows(self.old, [{'id': 'a', 'language': None}])
        self.rows(self.new, [{'id': 'a', 'language': 'und'}])
        self.assertEqual(validate(self.new, self.service), self.old)

    def test_unit_reset_and_continuation(self):
        self.service.write_text('[Service]\nExecStart=/bin/false\nExecStart=\n'
                                'ExecStart=/usr/bin/python3 -u \\\n "' +
                                (self.old / 'student_app/server.py').as_posix() + '"\n', encoding='utf-8')
        self.assertEqual(installed_root(self.service), self.old)

    def test_unknown_command_requires_explicit_override(self):
        for command in ('/bin/echo "' + (self.old / 'student_app/server.py').as_posix() + '"',
                        '/usr/bin/python3 -c "print(1)"', '/usr/bin/python3 -m student_app.server'):
            self.service.write_text('[Service]\nExecStart=' + command + '\n', encoding='utf-8')
            self.assertIsNone(installed_root(self.service))
            with self.assertRaisesRegex(ValueError, 'Cannot identify'):
                validate(self.new, self.service)
            self.assertIsNone(validate(self.new, self.service, allow_data_change=True))

    def test_unavailable_old_release_does_not_silently_pass(self):
        self.service.write_text('[Service]\nExecStart=/usr/bin/python3 "' +
                                (self.base / 'missing/student_app/server.py').as_posix() + '"\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'directory is unavailable'):
            validate(self.new, self.service)


if __name__ == '__main__':
    unittest.main()
