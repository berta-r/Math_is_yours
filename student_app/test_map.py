"""Problem map loader and stepping-stone paths (python3 -m unittest student_app.test_map)."""
import json
import random
import tempfile
import time
import unittest
from pathlib import Path

from copilot.learning_map import DEFAULT_PATH, LearningMap


def node(pid, b, cluster=0, x=0.0, y=0.0):
    return {'id': pid, 'level': 0, 'x': x, 'y': y, 'cluster': cluster, 'b': b, 'languages': ['eng', 'cat']}


# A chain p0..p9 (b rising by 0.1) plus a shortcut p0-p9 with a big b jump and
# two equal-cost middles m1/m2 between p1 and p3 to exercise tie-breaking.
NODES = [node(f'p{i}', round(0.1 * i, 2), cluster=i // 5, x=10.0 * i, y=5.0) for i in range(10)]
NODES += [node('m2', 0.2), node('m1', 0.2), node('island', 0.5)]
EDGES = [[i, i + 1, 0.9] for i in range(9)] + [[1, 11, 0.8], [11, 3, 0.8], [1, 10, 0.8], [10, 3, 0.8], [0, 9, 0.3]]
MAP = {'version': 1, 'source': {}, 'k': 5, 'nodes': NODES, 'edges': EDGES,
       'clusters': [{'id': 0, 'size': 5, 'keywords': ['a'], 'mean_b': 0.2}, {'id': 1, 'size': 5, 'keywords': ['b'], 'mean_b': 0.7}]}


class MapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, data, name='map.json'):
        path = self.folder / name
        path.write_text(json.dumps(data, separators=(',', ':')))
        return path

    def load(self, data=MAP):
        return LearningMap(self.write(data))

    def test_missing_file_is_disabled(self):
        m = LearningMap(self.folder / 'absent.json')
        self.assertFalse(m.enabled)
        self.assertIsNone(m.node('p0'))
        self.assertEqual(m.neighbors('p0'), [])

    def test_loads_and_queries(self):
        m = self.load()
        self.assertTrue(m.enabled)
        self.assertEqual(m.node('p3')['b'], 0.3)
        self.assertEqual([n['id'] for n in m.neighbors('p1')], ['p0', 'p2', 'm1', 'm2'])
        self.assertEqual(len(m.neighbors('p1', k=2)), 2)
        self.assertEqual(len(m.clusters()), 2)

    def test_path_is_deterministic_and_skips_solved(self):
        m = self.load()
        first = m.path(['p0', 'p1'], 'p4')
        for _ in range(5):
            self.assertEqual(m.path(['p1', 'p0'], 'p4'), first)
        self.assertTrue(first['reachable'])
        self.assertNotIn('p0', first['steps'])
        self.assertNotIn('p1', first['steps'])
        self.assertEqual(first['steps'][-1], 'p4')
        # p1 -> {p2, m1, m2} -> p3 all cost 0.4: smallest id wins
        self.assertEqual(first['steps'], ['m1', 'p3', 'p4'])
        self.assertAlmostEqual(first['cost'], 0.3 + 0.3)

    def test_solved_goal_and_unreachable_goal(self):
        m = self.load()
        self.assertEqual(m.path(['p4'], 'p4')['steps'], [])
        far = m.path(['p0'], 'island')
        self.assertFalse(far['reachable'])
        self.assertIsNone(far['cost'])
        with self.assertRaises(ValueError):
            m.path(['p0'], 'nope')

    def test_max_steps_truncation_reports_remaining(self):
        data = dict(MAP, edges=[e for e in EDGES if e[:2] != [0, 9]])
        m = self.load(data)
        full = m.path(['p0'], 'p9', max_steps=20)
        self.assertEqual(full['remaining'], 0)
        self.assertEqual(len(full['steps']), 9)
        short = m.path(['p0'], 'p9', max_steps=3)
        self.assertEqual(short['steps'], full['steps'][-3:])
        self.assertEqual(short['remaining'], 6)
        self.assertEqual(short['cost'], full['cost'])

    def test_big_jump_shortcut_is_avoided(self):
        # The p0-p9 shortcut (one 0.9 jump) is present in MAP; the squared gap
        # cost makes the nine 0.1 steps cheaper than one jump.
        m = self.load()
        result = m.path(['p0'], 'p9', max_steps=20)
        self.assertEqual(len(result['steps']), 9)
        self.assertAlmostEqual(result['cost'], 9 * (10.0 * 0.01 + 0.1))

    def test_no_solved_starts_from_lowest_b(self):
        m = self.load()
        result = m.path([], 'p2')
        self.assertTrue(result['reachable'])
        self.assertEqual(result['steps'][-1], 'p2')
        self.assertEqual(result['cost'], 0.0)  # p2 is among the 10 easiest seeds

    def test_frontier_orders_by_gap_above_mean(self):
        m = self.load()
        result = m.frontier(['p2', 'p3'], limit=5)  # mean b = 0.25
        ids = [r['id'] for r in result]
        self.assertEqual(ids[0], 'p4')  # gap 0.15, the only neighbour above the mean
        self.assertNotIn('p2', ids)
        self.assertNotIn('p3', ids)
        self.assertEqual(ids[1:], ['m1', 'm2', 'p1'])  # below the mean, then by |gap| and id
        self.assertEqual(m.frontier(['p2', 'p3'], limit=2), result[:2])
        self.assertEqual([r['id'] for r in m.frontier([], limit=3)], ['p0', 'p1', 'm1'])

    def test_validation_errors(self):
        bad_cases = [
            dict(MAP, version=2),
            dict(MAP, nodes=NODES + [node('p0', 0.1)]),
            dict(MAP, edges=EDGES + [[0, 99, 0.5]]),
            dict(MAP, edges=EDGES + [[2, 2, 0.5]]),
            dict(MAP, nodes=NODES[:-1] + [dict(node('island', 0.5), x='a')]),
            dict(MAP, edges=EDGES + [[0, 1]]),
        ]
        for data in bad_cases:
            with self.assertRaises(ValueError):
                self.load(data)
        nan = self.folder / 'nan.json'
        nan.write_text(json.dumps(dict(MAP, nodes=NODES[:-1] + [dict(node('island', 0.5), y=float('nan'))])))
        with self.assertRaises(ValueError):
            LearningMap(nan)
        broken = self.folder / 'broken.json'
        broken.write_text('{not json')
        with self.assertRaises(ValueError):
            LearningMap(broken)
        big = self.folder / 'big.json'
        big.write_text(' ' * (400 * 1024 + 1))
        with self.assertRaises(ValueError):
            LearningMap(big)

    def test_synthetic_2300_nodes_under_100ms(self):
        rng = random.Random(42)
        nodes = [{'id': f'n{i:04d}', 'x': 0, 'y': 0, 'cluster': 0, 'b': round(rng.random(), 3)} for i in range(2300)]
        edges = sorted({tuple(sorted(rng.sample(range(2300), 2))) for _ in range(10000)})
        m = self.load({'version': 1, 'nodes': nodes, 'edges': [[a, b, 0.5] for a, b in edges], 'clusters': []})
        solved = [f'n{i:04d}' for i in range(5)]
        goal = max(nodes, key=lambda n: n['b'])['id']
        started = time.perf_counter()
        result = m.path(solved, goal)
        elapsed = time.perf_counter() - started
        self.assertTrue(result['reachable'])
        self.assertLess(elapsed, 0.1)


@unittest.skipUnless(DEFAULT_PATH.is_file(), 'data/ml/problem_map.json not built')
class RealMapTests(unittest.TestCase):
    def test_far_path_under_100ms(self):
        m = LearningMap()
        self.assertTrue(m.enabled)
        ordered = sorted(m.nodes, key=lambda n: (n['b'], n['id']))
        solved = [n['id'] for n in ordered[:5]]
        goal = ordered[-1]['id']
        started = time.perf_counter()
        result = m.path(solved, goal)
        elapsed = time.perf_counter() - started
        self.assertTrue(result['reachable'])
        self.assertEqual(result['steps'][-1], goal)
        self.assertLessEqual(len(result['steps']), 6)
        self.assertLess(elapsed, 0.1, f'Dijkstra took {elapsed * 1000:.1f} ms')
        self.assertEqual(m.path(solved, goal), result)


if __name__ == '__main__':
    unittest.main()
