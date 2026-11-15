"""Integration checks: python -m unittest discover -s student_app -v"""
import importlib.util
import json
import base64
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

spec = importlib.util.spec_from_file_location("student_server", Path(__file__).with_name("server.py"))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class PracticeTests(unittest.TestCase):
    def catalog(self):
        return None

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "test.db"
        app.initialize(self.db)
        self.knowledge = app.Knowledge(annotations=[app.ROOT / 'data/teaching_annotations.json'])
        handler = app.make_handler(self.db, self.catalog(), knowledge=self.knowledge, include_diagnostics=False)
        handler.log_message = lambda *args: None
        self.server = app.StudentServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def post(self, action, **body):
        payload = {"student": "Ada", **body}
        req = urllib.request.Request(self.url + "/api/" + action, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as response:
            result = json.load(response)
        if action == 'start':
            self.post('reflect', session=result['session'], reflection='I will compare the quantities first.')
            # Thinking steps gate the answer stage when they exist; answer them correctly.
            problem = {'id': result['problem']['id'], 'language': result['problem']['language']}
            for index, step in enumerate(self.knowledge.thinking_steps(problem)[0]):
                self.post('step', session=result['session'], index=index, choice=step['answer'])
        return result

    def unlock(self, session):
        self.post('hint', session=session)
        self.post('answer', session=session, answer='E')
        self.post('answer', session=session, answer='E')

    def start(self, pid="sample-1"):
        result = self.post("start", problem=pid)
        self.assertNotIn("label", result["problem"])
        return result["session"]

    def test_independent_success_persistence_and_profile_isolation(self):
        session = self.start('sample-4')
        self.assertTrue(self.post("answer", session=session, answer="C")["correct"])
        app.initialize(self.db)
        profile = self.post("profile")
        self.assertEqual(profile["attempts"], 1)
        self.assertEqual(profile["skills"][0]["independent"], 1)
        self.assertEqual(self.post("profile", student="Other")["attempts"], 0)

    def test_hint_and_reopening_never_earn_independent_credit(self):
        session = self.start()
        self.post("hint", session=session)
        session = self.start()
        self.post("answer", session=session, answer="C")
        self.assertEqual(self.post("profile")["skills"][0]["independent"], 0)

    def test_wrong_then_correct_and_revealed_solution(self):
        session = self.start()
        self.assertFalse(self.post("answer", session=session, answer="A")["correct"])
        self.post("answer", session=session, answer="C")
        session = self.start("sample-2")
        self.unlock(session)
        self.post("solution", session=session)
        self.post("answer", session=session, answer="B")
        self.assertTrue(all(s["independent"] == 0 for s in self.post("profile")["skills"]))

    def test_invalid_answer_and_unknown_routes(self):
        session = self.start()
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post("answer", session=session, answer="Z")
        self.assertEqual(ctx.exception.code, 400)
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(self.url + "/../server.py")
        with urllib.request.urlopen(self.url) as response:
            self.assertEqual(response.status, 200)

    def test_reveal_uses_key_and_prevents_independent_credit(self):
        # Start with an id appropriate to either fixture.
        pid = self.post('problems')['problems'][0]['key']
        opened = self.post('start', problem=pid)
        self.assertNotIn('label', opened['problem'])
        self.unlock(opened['session'])
        revealed = self.post('reveal', session=opened['session'])
        self.assertIn(revealed['answer'], 'ABCDE')
        result = self.post('answer', session=opened['session'], answer=revealed['answer'])
        self.assertTrue(result['correct'])
        self.assertTrue(all(s['independent'] == 0 for s in self.post('profile')['skills']))


class MediaTests(PracticeTests):
    def catalog(self):
        folder = Path(self.temp.name)
        self.images = folder / "images"
        self.images.mkdir()
        # An invented one-pixel PNG; no dataset content is committed.
        self.png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
        (self.images / "visual_eng.png").write_bytes(self.png)
        (self.images / "visual_cat.png").write_bytes(self.png)
        (self.images / "visual_eng_option_A.png").write_bytes(self.png)
        rows = [
            {"id":"visual", "language":"eng", "text":"Look at this diagram", "options":{}, "option_images":["A"], "label":"A", "text_only":False},
            {"id":"visual", "language":"cat", "text":"", "label":"A", "text_only":False},
            {"id":"plain", "language":"eng", "text":"Text alone", "options":{"A":"1"}, "label":"A"},
            {"id":"missing", "language":"eng", "text":"Missing diagram", "text_only":False},
            {"id":"../secret", "language":"eng", "text":"Unsafe image name"},
        ]
        path = folder / "problems.jsonl"
        path.write_text('\n'.join(json.dumps(r) for r in rows), encoding='utf-8')
        return app.Catalog([path], self.images)

    # Sample-specific tests belong to PracticeTests, not the media fixture.
    def test_independent_success_persistence_and_profile_isolation(self):
        listing = self.post('problems')['problems']
        self.assertEqual(len(listing), 5)
        self.assertEqual(len({p['key'] for p in listing}), 5)
        english = self.post('start', problem='visual|eng')
        self.post('answer', session=english['session'], answer='A')
        catalan = self.post('start', problem='visual|cat')
        self.post('answer', session=catalan['session'], answer='A')
        profile = self.post('profile')
        self.assertEqual(profile['attempts'], 2)
        self.assertTrue(all(s['evidence'] == 0 for s in profile['skills']))
        self.assertEqual(profile['history'][0]['reason'], 'unclassified')
        self.assertEqual(self.post('profile', student='Other')['attempts'], 0)

    def test_hint_and_reopening_never_earn_independent_credit(self):
        data = self.post('start', problem='visual|eng')
        self.assertFalse(data['has_hints'])
        self.assertFalse(data['has_solution'])
        self.post('hint', session=data['session'])
        with self.assertRaises(urllib.error.HTTPError):
            self.post('solution', session=data['session'])
        self.unlock(data['session'])
        self.post('solution', session=data['session'])
        self.assertNotIn('label', data['problem'])
        self.assertNotIn('answer', data['problem'])

    def test_wrong_then_correct_and_revealed_solution(self):
        mixed = self.post('start', problem='visual|eng')['problem']
        self.assertEqual(mixed['format'], 'text + image')
        with urllib.request.urlopen(self.url + mixed['image_url']) as response:
            self.assertEqual(response.headers['Content-Type'], 'image/png')
            self.assertEqual(response.read(), self.png)
        with urllib.request.urlopen(self.url + mixed['option_images']['A']) as response:
            self.assertEqual(response.read(), self.png)
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(self.url + mixed['image_url'] + '&option=../secret')
        image_only = self.post('start', problem='visual|cat')['problem']
        self.assertEqual(image_only['format'], 'image')
        self.assertEqual(image_only['text'], '')
        text_only = self.post('start', problem='plain')['problem']
        self.assertIsNone(text_only['image_url'])
        self.assertEqual(text_only['options'], {'A':'1'})

    def test_invalid_answer_and_unknown_routes(self):
        data = self.post('start', problem='missing')
        self.assertIsNone(data['problem']['image_url'])
        self.assertTrue(data['problem']['requires_image'])
        self.assertFalse(data['problem']['gradable'])
        with self.assertRaises(urllib.error.HTTPError):
            self.post('answer', session=data['session'], answer='A')
        self.assertEqual(self.post('profile')['attempts'], 0)
        for key in ('../secret|eng', 'unknown'):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(self.url + '/api/image?key=' + quote(key, safe=''))
            self.assertEqual(ctx.exception.code, 404)
        with self.assertRaises(urllib.error.HTTPError):
            self.post('start', problem='visual')  # ambiguous translations


if __name__ == "__main__":
    unittest.main()
