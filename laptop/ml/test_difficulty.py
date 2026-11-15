"""Feature rules and exporter parity; run with .venv-ml/bin/python -m unittest laptop.ml.test_difficulty."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from copilot.difficulty import Difficulty
from laptop.ml.difficulty import STATS, export_model, fit_pair
from laptop.ml.features import build, numeric_value, parse_position, points_for, strip_prefix


def row(pid, lang, level, year, text, options=None, text_only=True):
    return {'id': pid, 'language': lang, 'level': level, 'year': year, 'text_only': text_only,
            'text': text, 'options': options or {}, 'label': 'A'}


class FeatureRules(unittest.TestCase):
    def test_points_by_thirds(self):
        self.assertEqual([points_for(p, 30) for p in (1, 10, 11, 20, 21, 30)], [3, 3, 4, 4, 5, 5])
        self.assertEqual([points_for(p, 24) for p in (8, 9, 16, 17)], [3, 4, 4, 5])
        self.assertIsNone(points_for(None, 30))

    def test_unreliable_paper_is_null(self):
        self.assertIsNone(points_for(3, 11))
        self.assertEqual(points_for(3, 12), 3)
        rows = [row(f'lvl-1_2010_{n}', 'eng', 1, 2010, f'{n}. Problem {n}') for n in (1, 5, 9)]
        self.assertTrue(all(r['points'] is None and r['max_position'] == 9 for r in build(rows)))

    def test_prefix_parsing(self):
        self.assertEqual(parse_position('13. For 3 days'), 13)
        self.assertEqual(parse_position('11.  \nJosep has 4 toys'), 11)
        self.assertEqual(parse_position('  7 . Seven'), 7)
        self.assertIsNone(parse_position('20 Jaume has three pieces'))
        self.assertIsNone(parse_position('The date of next May 5th'))
        self.assertIsNone(parse_position('2015. A year'))
        self.assertEqual(strip_prefix('13. For 3 days'), ' For 3 days')

    def test_build_uses_english_and_catalan_position(self):
        rows = [row('lvl-2_2011_4', 'eng', 2, 2011, 'Without prefix, 2 and 3 apples', {k: f'{i} cm' for i, k in enumerate('ABCDE', 1)}),
                row('lvl-2_2011_4', 'cat', 2, 2011, '4. Sense prefix'),
                row('lvl-2_2011_30', 'cat', 2, 2011, '30. Últim')]
        out = {r['id']: r for r in build(rows)}
        r = out['lvl-2_2011_4']
        self.assertEqual((r['position'], r['max_position'], r['points']), (4, 30, 3))
        self.assertEqual((r['numerals'], r['n_options'], r['numeric_options'], r['option_spread']), (2, 5, True, 0.8))
        self.assertEqual(r['key'], 'lvl-2_2011_4|eng')
        self.assertEqual(out['lvl-2_2011_30']['key'], 'lvl-2_2011_30|cat')

    def test_numeric_options(self):
        self.assertEqual(numeric_value('3,5 cm'), 3.5)
        self.assertEqual(numeric_value('3/4'), 0.75)
        self.assertEqual(numeric_value('25%'), 25)
        self.assertIsNone(numeric_value('15/4/2015'))
        self.assertIsNone(numeric_value('a triangle'))


class ExportParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(42)
        n = 400
        emb = rng.normal(size=(n, 384))
        emb /= np.linalg.norm(emb, axis=1, keepdims=True)
        stats = np.column_stack([rng.integers(0, 8, n), rng.integers(20, 600, n), rng.integers(5, 120, n),
                                 rng.integers(0, 9, n), rng.integers(0, 2, n), rng.choice([0, 5], n),
                                 rng.integers(0, 2, n), np.round(rng.random(n), 6)]).astype(float)
        signal = emb[:, 0] * 8 + stats[:, 2] / 60 + rng.normal(scale=0.5, size=n)
        y = np.where(signal < -0.3, 3, np.where(signal < 1.3, 4, 5))
        cls.emb, cls.stats = emb, stats
        cls.tree, cls.gb = fit_pair(emb, stats, y)
        names = [f'pca_{i}' for i in range(32)] + STATS
        cls.tmp = tempfile.TemporaryDirectory()
        path = Path(cls.tmp.name) / 'model.json'
        path.write_text(json.dumps(export_model(cls.tree, cls.gb, 'tree', names)), encoding='utf-8')
        cls.pure = Difficulty(path=None, model_path=path)
        cls.sample = rng.choice(n, 50, replace=False)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def features(self, i):
        return {'embedding': self.emb[i].tolist(), **dict(zip(STATS, self.stats[i].tolist()))}

    def test_tree_matches_sklearn(self):
        expected = self.tree.proba(self.emb[self.sample], self.stats[self.sample])
        for row_i, i in enumerate(self.sample):
            got = self.pure.evaluate(self.features(i), 'tree')['probabilities']
            np.testing.assert_allclose(got, expected[row_i], atol=1e-6, rtol=0)

    def test_ensemble_matches_sklearn(self):
        expected = self.gb.proba(self.emb[self.sample], self.stats[self.sample])
        for row_i, i in enumerate(self.sample):
            got = self.pure.evaluate(self.features(i), 'ensemble')['probabilities']
            np.testing.assert_allclose(got, expected[row_i], atol=1e-6, rtol=0)

    def test_pca_projection_matches(self):
        i = int(self.sample[0])
        np.testing.assert_allclose(self.pure.vector(self.features(i)),
                                   self.tree.design(self.emb[i:i + 1], self.stats[i:i + 1])[0], atol=1e-9)



if __name__ == '__main__':
    unittest.main()
