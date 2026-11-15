"""Difficulty loader, fallback and Elo properties; standard library only."""
import json
import tempfile
import unittest
from pathlib import Path

from copilot.difficulty import Difficulty, elo_update, probability

TABLE = {'version': 1, 'scale': 'b = (level + (expected_points - 3)/2) / 8, in [0,1]', 'problems': {
    'lvl-2_2011_4': {'level': 2, 'points': 3, 'expected_points': 3.4, 'b': 0.25, 'source': 'observed'},
    'lvl-7_2020_29': {'level': 7, 'points': None, 'expected_points': 4.6, 'b': 0.975, 'source': 'predicted'}}}
# Two-dimensional "embedding", one PCA component, one statistic.
MODEL = {'version': 1, 'features': ['pca_0', 'level'], 'classes': [3, 4, 5], 'preferred': 'tree',
         'pca': {'mean': [0.5, 0.0], 'components': [[1.0, 0.0]]},
         'tree': {'feature': 1, 'threshold': 3.5,
                  'left': {'leaf': [0.7, 0.2, 0.1]},
                  'right': {'feature': 0, 'threshold': 0.0, 'left': {'leaf': [0.2, 0.5, 0.3]}, 'right': {'leaf': [0.0, 0.25, 0.75]}}},
         'ensemble': {'learning_rate': 0.5, 'init': [0.0, 0.0, 0.0],
                      'trees': [[{'leaf': [1.0]}, {'leaf': [0.0]}, {'feature': 0, 'threshold': 0.0, 'left': {'leaf': [-1.0]}, 'right': {'leaf': [2.0]}}]]}}


class DifficultyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, data):
        path = self.folder / name
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def load(self, table=TABLE, model=MODEL):
        return Difficulty(path=self.write('d.json', table), model_path=self.write('m.json', model))

    def test_loads_stored_values(self):
        d = self.load()
        self.assertEqual(d.b('lvl-2_2011_4'), 0.25)
        self.assertEqual(d.expected_points('lvl-7_2020_29'), 4.6)
        self.assertEqual(d.metadata['version'], 1)

    def test_fallback_for_unknown_id(self):
        d = self.load()
        self.assertAlmostEqual(d.b('unknown', level=4), 4 / 8 + 1 / 16)
        self.assertEqual(d.b('unknown', level=7), 7 / 8 + 1 / 16)
        self.assertEqual(d.b('unknown'), 0.5)
        self.assertIsNone(d.expected_points('unknown'))
        empty = Difficulty(path=self.folder / 'missing.json', model_path=self.folder / 'missing-model.json')
        self.assertEqual(empty.problems, {})
        self.assertIsNone(empty.model)
        self.assertAlmostEqual(empty.b('lvl-2_2011_4', level=2), 0.3125)

    def test_tree_and_ensemble_evaluation(self):
        d = self.load()
        low = d.evaluate({'embedding': [0.9, 0.3], 'level': 2})
        self.assertEqual(low['model'], 'tree')
        for actual, expected in zip(low['probabilities'], [0.7, 0.2, 0.1]):
            self.assertAlmostEqual(actual, expected)
        self.assertAlmostEqual(low['expected_points'], 3.4)
        high = d.evaluate({'embedding': [0.9, 0.3], 'level': 6}, 'tree')
        self.assertEqual(high['probabilities'], [0.0, 0.25, 0.75])
        unknown = d.evaluate({'embedding': [0.1, 0.3], 'level': None}, 'tree')['probabilities']
        for actual, expected in zip(unknown, [0.7, 0.2, 0.1]):
            self.assertAlmostEqual(actual, expected)
        ens = d.evaluate({'embedding': [0.9, 0.3], 'level': 6}, 'ensemble')
        self.assertEqual(ens['model'], 'ensemble')
        self.assertAlmostEqual(sum(ens['probabilities']), 1.0)
        self.assertGreater(ens['probabilities'][2], ens['probabilities'][1])  # raw [0.5, 0, 1]
        with self.assertRaises(ValueError):
            d.evaluate({'embedding': [0.1], 'level': 2})

    def test_validation_errors(self):
        bad_tables = [
            {'version': 2, 'problems': {}},
            {'version': 1, 'problems': []},
            {'version': 1, 'problems': {'x': {'level': 9, 'points': 3, 'expected_points': 3, 'b': 0.1, 'source': 'observed'}}},
            {'version': 1, 'problems': {'x': {'level': 1, 'points': 6, 'expected_points': 3, 'b': 0.1, 'source': 'observed'}}},
            {'version': 1, 'problems': {'x': {'level': 1, 'points': 3, 'expected_points': 3, 'b': 1.5, 'source': 'observed'}}},
            {'version': 1, 'problems': {'x': {'level': 1, 'points': None, 'expected_points': 3, 'b': 0.1, 'source': 'observed'}}},
            {'version': 1, 'problems': {'x': {'level': 1, 'points': 3, 'expected_points': 6, 'b': 0.1, 'source': 'observed'}}},
        ]
        for table in bad_tables:
            with self.assertRaises(ValueError, msg=table):
                self.load(table=table)
        bad_models = []
        for change in ({'classes': [1, 2, 3]}, {'pca': {'mean': [0.5, 0.0], 'components': [[1.0]]}},
                       {'tree': {'feature': 5, 'threshold': 0.0, 'left': {'leaf': [1, 0, 0]}, 'right': {'leaf': [1, 0, 0]}}},
                       {'tree': {'leaf': [1, 0]}}, {'features': ['pca_0']}, {'preferred': 'forest'},
                       {'ensemble': {'learning_rate': 0.1, 'init': [0, 0], 'trees': []}}):
            bad_models.append({**MODEL, **change})
        no_ensemble = {k: v for k, v in MODEL.items() if k != 'ensemble'}
        bad_models.append({**no_ensemble, 'preferred': 'ensemble'})
        for model in bad_models:
            with self.assertRaises(ValueError, msg=model):
                self.load(model=model)
        (self.folder / 'broken.json').write_text('{not json', encoding='utf-8')
        with self.assertRaises(ValueError):
            Difficulty(path=self.folder / 'broken.json', model_path=None)

    def test_budget(self):
        big = self.folder / 'big.json'
        big.write_text(' ' * (1024 * 1024 + 1), encoding='utf-8')
        with self.assertRaises(ValueError):
            Difficulty(path=big, model_path=None)

    def test_probability_properties(self):
        grid = [i / 20 for i in range(21)]
        for b in (0.0, 0.3, 1.0):
            values = [probability(theta, b) for theta in grid]
            self.assertTrue(all(0 < v < 1 for v in values))
            self.assertTrue(all(x < y for x, y in zip(values, values[1:])))
        self.assertEqual(probability(0.4, 0.4), 0.5)
        self.assertGreater(probability(0.5, 0.2), probability(0.5, 0.6))
        self.assertAlmostEqual(probability(0.5, 0.375), 1 / (1 + 2.718281828459045 ** -0.75))
        self.assertEqual(probability(0.7, 0.2), probability(0.7, 0.2))

    def test_elo_properties(self):
        theta = 0.5
        up, down = elo_update(theta, 0.5, True), elo_update(theta, 0.5, False)
        self.assertAlmostEqual(up, 0.54)
        self.assertAlmostEqual(down, 0.46)
        # A harder success moves more than an easy one; never more than k.
        self.assertGreater(elo_update(theta, 0.9, True) - theta, elo_update(theta, 0.1, True) - theta)
        self.assertLessEqual(elo_update(theta, 1.0, True) - theta, 0.08)
        self.assertEqual(elo_update(1.0, 0.0, True), 1.0)
        self.assertEqual(elo_update(0.0, 1.0, False), 0.0)
        self.assertEqual(elo_update(0.99, 1.0, True, k=0.5), 1.0)
        # Monotone in the prior ability and deterministic across repeated runs.
        self.assertLess(elo_update(0.3, 0.5, True), elo_update(0.4, 0.5, True))
        runs = []
        for _ in range(2):
            t = 0.5
            for correct in (True, False, True, True, False, True):
                t = elo_update(t, 0.6, correct)
            runs.append(t)
        self.assertEqual(runs[0], runs[1])
        self.assertTrue(0 <= runs[0] <= 1)


if __name__ == '__main__':
    unittest.main()
