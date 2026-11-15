"""/api/map, /api/path and the standalone /map page (T-107) against a synthetic map file."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from copilot.difficulty import Difficulty
from copilot.knowledge import Knowledge, ROOT
from student_app import server as app


def node(pid, b, cluster, x, languages=('eng',)):
    return {'id': pid, 'level': int(b * 8), 'x': x, 'y': 10.0 * cluster, 'cluster': cluster, 'b': b, 'languages': list(languages)}


# A chain sample-1 -> sample-2 -> sample-3 -> sample-4 -> unloaded, plus sample-5 as an island.
NODES = [node('sample-1', 0.0, 0, 0.0), node('sample-2', 0.1, 0, 1.0), node('sample-3', 0.2, 1, 2.0),
         node('sample-4', 0.3, 1, 3.0, ('cat',)), node('unloaded', 0.4, 1, 4.0), node('sample-5', 0.5, 2, 9.0, ('cat',))]
EDGES = [[0, 1, 0.9], [1, 2, 0.8], [2, 3, 0.8], [3, 4, 0.7]]
MAP = {'version': 1, 'k': 5, 'nodes': NODES, 'edges': EDGES,
       'clusters': [{'id': 0, 'size': 2, 'keywords': ['apples']}, {'id': 1, 'size': 3, 'keywords': ['square']},
                    {'id': 2, 'size': 1, 'keywords': ['count']}]}


class Fixture:
    def __init__(self, folder, map_path):
        self.db = Path(folder) / f'practice-{id(self)}.db'
        app.initialize(self.db)
        self.knowledge = Knowledge()
        self.catalog = app.Catalog([ROOT / 'data/sample_problems.jsonl'], Path(folder) / 'images')
        handler = app.make_handler(self.db, self.catalog, self.knowledge, map_path=map_path,
                                   difficulty=Difficulty(Path(folder) / 'none.json', Path(folder) / 'none-model.json'))
        handler.log_message = lambda *args: None
        self.server = app.StudentServer(('127.0.0.1', 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def post(self, route, **data):
        req = urllib.request.Request(f'{self.base}/api/{route}', data=json.dumps({'student': 'Ada', **data}).encode(),
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            return json.load(response)

    def solve(self, pid, correct=True):
        opened = self.post('start', problem=pid)
        problem = self.catalog.problems[opened['problem']['key']]
        steps = self.knowledge.thinking_steps(problem)[0]
        for index, step in enumerate(steps):
            self.post('step', session=opened['session'], index=index, choice=step['answer'])
        if not steps:
            self.post('reflect', session=opened['session'], reflection='I will look for equal groups and check the units.')
        letter = problem['label'] if correct else next(x for x in 'ABCDE' if x != problem['label'])
        return self.post('answer', session=opened['session'], answer=letter)


class MapApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        path = Path(self.temp.name) / 'problem_map.json'
        path.write_text(json.dumps(MAP), encoding='utf-8')
        self.app = Fixture(self.temp.name, path)
        self.assertTrue(self.app.solve('sample-1')['correct'])
        self.assertFalse(self.app.solve('sample-2', correct=False)['correct'])

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def test_map_marks_solved_and_exposed(self):
        data = self.app.post('map')
        self.assertTrue(data['enabled'])
        nodes = {n['id']: n for n in data['nodes']}
        self.assertEqual(set(nodes['sample-1']), {'id', 'level', 'x', 'y', 'cluster', 'b', 'solved', 'exposed', 'languages'})
        self.assertEqual((nodes['sample-1']['solved'], nodes['sample-1']['exposed']), (True, True))
        self.assertEqual((nodes['sample-2']['solved'], nodes['sample-2']['exposed']), (False, True))
        self.assertEqual((nodes['sample-3']['solved'], nodes['sample-3']['exposed']), (False, False))
        self.assertEqual(data['student_b_mean'], 0.0)
        self.assertEqual(len(data['edges']), 4)
        self.assertEqual(data['clusters'][1]['keywords'], ['square'])
        self.assertEqual(self.app.post('map', edges=False)['edges'], [])
        other = self.app.post('map', student='Other')
        self.assertFalse(any(n['solved'] or n['exposed'] for n in other['nodes']))
        self.assertIsNone(other['student_b_mean'])

    def test_path_lists_steps_with_previews_and_frontier(self):
        result = self.app.post('path', goal='unloaded', language='eng')
        self.assertTrue(result['reachable'])
        self.assertEqual([s['id'] for s in result['steps']], ['sample-2', 'sample-3', 'sample-4', 'unloaded'])
        first, catalan, last = result['steps'][0], result['steps'][2], result['steps'][3]
        self.assertEqual(set(first), {'id', 'level', 'b', 'text_preview', 'key', 'cluster',
                                      'skill', 'skill_name', 'category', 'difficulty_label', 'solved'})
        self.assertEqual((first['skill'], first['skill_name'], first['category'], first['difficulty_label'], first['solved']),
                         ('order_of_operations', 'Order of operations', 'apples', 'easy', False))
        self.assertEqual((last['skill'], last['skill_name'], last['category'], last['difficulty_label']), (None, None, 'square', 'medium'))
        self.assertEqual((result['goal_problem']['id'], result['goal_skill'], result['goal_skill_name']), ('unloaded', None, None))
        self.assertEqual(first['key'], 'sample-2|eng')
        self.assertEqual(first['text_preview'], 'What is the value of 2 + 3 × 4?')
        self.assertEqual(catalan['key'], 'sample-4|cat')  # only loaded in Catalan: falls back
        self.assertLessEqual(len(catalan['text_preview']), 90)
        self.assertEqual((last['key'], last['text_preview'], last['b']), (None, None, 0.4))
        self.assertEqual(result['frontier'][0]['id'], 'sample-2')
        self.assertEqual(result['frontier'][0]['via'], 'sample-1')
        self.assertEqual(self.app.post('path', goal='unloaded', language='eng'), result)
        island = self.app.post('path', goal='sample-5')
        self.assertFalse(island['reachable'])
        self.assertEqual(self.app.post('path', goal='sample-1')['steps'], [])

    def test_goal_skill_resolves_a_reachable_stretch_problem(self):
        # Solved: sample-1 (b 0.0) -> target b 0.5; arithmetic is tagged on sample-1 (solved) and sample-4 -> sample-4.
        result = self.app.post('path', goal_skill='arithmetic', language='eng')
        self.assertTrue(result['reachable'])
        self.assertEqual((result['goal'], result['goal_skill'], result['goal_skill_name']),
                         ('sample-4', 'arithmetic', 'Addition and subtraction'))
        self.assertEqual(result['goal_problem']['id'], 'sample-4')
        self.assertEqual(result['goal_problem']['key'], 'sample-4|cat')
        self.assertEqual([s['id'] for s in result['steps']], ['sample-2', 'sample-3', 'sample-4'])
        middle = result['steps'][1]
        self.assertEqual((middle['skill'], middle['category'], middle['difficulty_label'], middle['solved']),
                         ('geometry_measurement', 'square', 'easy', False))
        self.assertEqual([s['difficulty_label'] for s in result['steps']], ['easy', 'easy', 'medium'])
        self.assertEqual(self.app.post('path', goal_skill='arithmetic', language='eng'), result)
        # Every arithmetic node solved: the closest tagged node is still returned (steps empty, reachable).
        self.assertTrue(self.app.solve('sample-4')['correct'])
        again = self.app.post('path', goal_skill='arithmetic')
        self.assertEqual((again['goal'], again['steps'], again['reachable']), ('sample-4', [], True))
        # A known skill with no tagged node on the map: not reachable, with a reason, frontier still listed.
        none = self.app.post('path', goal_skill='patterns')
        self.assertEqual((none['enabled'], none['reachable'], none['goal'], none['goal_problem']), (True, False, None, None))
        self.assertEqual(none['goal_skill_name'], 'Patterns and sequences')
        self.assertIn('tagged', none['reason'])
        self.assertTrue(none['frontier'])
        # An island goal through its skill is unreachable like by problem id.
        island = self.app.post('path', goal_skill='systematic_counting')
        self.assertEqual((island['goal'], island['reachable']), ('sample-5', False))

    def test_unknown_or_missing_goal_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.app.post('path', goal_skill='nope')
        self.assertEqual(caught.exception.code, 400)
        caught.exception.close()
        for body in ({'goal': 'nope'}, {}, {'goal': 7}):
            with self.subTest(body=body), self.assertRaises(urllib.error.HTTPError) as caught:
                self.app.post('path', **body)
            self.assertEqual(caught.exception.code, 400)
            caught.exception.close()

    def test_map_page_and_script_are_served(self):
        for route, mime, marker in (('/map', 'text/html', b'/map.js'), ('/map.js', 'text/javascript', b"post('path'")):
            with urllib.request.urlopen(self.app.base + route) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers['Content-Type'], mime + '; charset=utf-8')
                body = response.read()
            self.assertIn(marker, body)
            # Offline page: no external hosts.
            self.assertNotRegex(body.decode(), r'https?://(?!www\.w3\.org)')
        with urllib.request.urlopen(self.app.base + '/map') as response:
            self.assertIn(b'width=device-width', response.read())


class MapDisabledTests(unittest.TestCase):
    def test_missing_map_file_is_disabled(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Fixture(folder, Path(folder) / 'absent.json')
            try:
                data = fixture.post('map')
                self.assertEqual(data, {'enabled': False, 'nodes': [], 'clusters': [], 'edges': [], 'student_b_mean': None})
                self.assertFalse(fixture.post('path', goal='sample-1')['enabled'])
                self.assertFalse(fixture.post('path', goal_skill='arithmetic')['enabled'])
            finally:
                fixture.close()

    @unittest.skipUnless((ROOT / 'data/ml/problem_map.json').is_file(), 'real map artifact not present')
    def test_real_map_response_stays_small(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Fixture(folder, None)
            try:
                req = urllib.request.Request(fixture.base + '/api/map', data=json.dumps({'student': 'Ada'}).encode(),
                                             headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req) as response:
                    raw = response.read()
                self.assertLess(len(raw), 600 * 1024)
                self.assertTrue(json.loads(raw)['enabled'])
            finally:
                fixture.close()


if __name__ == '__main__':
    unittest.main()
