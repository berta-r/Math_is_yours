"""Tests for T-104/T-105: .venv-ml/bin/python -m unittest laptop.ml.test_align"""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from copilot.alignment import Alignment
from laptop.ml.align import normalize_rows, procrustes, retrieval


def random_rotation(dim, rng):
    q, r = np.linalg.qr(rng.standard_normal((dim, dim)))
    return q * np.sign(np.diag(r))


class ProcrustesTest(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(42)
        self.dim, n = 32, 400
        self.eng = normalize_rows(rng.standard_normal((n, self.dim)))
        self.rotation = random_rotation(self.dim, rng)
        # cat = eng rotated away, plus small noise; Procrustes must undo the rotation
        self.cat = normalize_rows(self.eng @ self.rotation.T + 0.01 * rng.standard_normal((n, self.dim)))
        self.ids = [f'p{i}' for i in range(n)]

    def test_recovers_rotation(self):
        w = procrustes(self.cat[:300], self.eng[:300])
        self.assertLess(np.abs(w.T @ w - np.eye(self.dim)).max(), 1e-9)
        self.assertLess(np.abs(w - self.rotation).max(), 0.05)
        before = retrieval(self.cat[300:], self.ids[300:], self.eng, self.ids)
        after = retrieval(normalize_rows(self.cat[300:] @ w), self.ids[300:], self.eng, self.ids)
        self.assertLess(before['recall@1'], 0.2)
        self.assertGreaterEqual(after['recall@1'], 0.99)

    def test_stdlib_apply_matches_numpy(self):
        w = procrustes(self.cat, self.eng)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'procrustes.json'
            path.write_text(json.dumps({'version': 1, 'method': 'orthogonal-procrustes', 'dimensions': self.dim,
                                        'matrix': w.tolist()}))
            alignment = Alignment(path)
            self.assertTrue(alignment.enabled)
            for row in self.cat[:20]:
                expected = row @ w
                expected /= np.linalg.norm(expected)
                got = alignment.apply([float(x) for x in row])
                self.assertLess(np.abs(np.array(got) - expected).max(), 1e-6)

    def test_validation_and_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(Alignment(Path(tmp) / 'absent.json').enabled)
            self.assertEqual(Alignment(Path(tmp) / 'absent.json').apply([3.0, 4.0]), [0.6, 0.8])
            bad = Path(tmp) / 'bad.json'
            for matrix, dims in (([[1.0, 0.0]], 2), ([[1.0, 0.0], [0.0]], 2), ([[1.0, float('nan')], [0.0, 1.0]], 2)):
                bad.write_text(json.dumps({'version': 1, 'method': 'orthogonal-procrustes', 'dimensions': dims, 'matrix': matrix}))
                with self.assertRaises(ValueError):
                    Alignment(bad)
            good = Path(tmp) / 'good.json'
            good.write_text(json.dumps({'version': 1, 'method': 'orthogonal-procrustes', 'dimensions': 2,
                                        'matrix': [[0.0, 1.0], [1.0, 0.0]]}))
            with self.assertRaises(ValueError):
                Alignment(good).apply([1.0, 0.0, 0.0])
            self.assertEqual(Alignment(good).apply([2.0, 0.0]), [0.0, 1.0])


if __name__ == '__main__':
    unittest.main()
