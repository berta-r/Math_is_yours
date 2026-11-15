"""Cross-lingual alignment: rotate a Catalan embedding into English space.

Loads the orthogonal Procrustes matrix exported by laptop/ml/align.py. If the
file is missing the alignment is disabled and apply() returns the vector
unchanged (re-normalised). Standard library only; one 384x384 matvec in plain
Python loops.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / 'data/ml/procrustes.json'
MAX_BYTES = 4 * 1024 * 1024


def _normalize(vector):
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0 or not math.isfinite(norm):
        return list(vector)
    return [x / norm for x in vector]


def validate_matrix(data):
    if not isinstance(data, dict) or data.get('version') != 1:
        raise ValueError('Alignment needs version 1 metadata')
    if data.get('method') != 'orthogonal-procrustes':
        raise ValueError('Unknown alignment method')
    dims = data.get('dimensions')
    if type(dims) is not int or dims <= 0:
        raise ValueError('Alignment dimensions must be a positive integer')
    matrix = data.get('matrix')
    if not isinstance(matrix, list) or len(matrix) != dims:
        raise ValueError('Alignment matrix must have one row per dimension')
    rows = []
    for row in matrix:
        if not isinstance(row, list) or len(row) != dims:
            raise ValueError('Alignment matrix must be square')
        for x in row:
            if type(x) not in (int, float) or not math.isfinite(x):
                raise ValueError('Alignment matrix values must be finite numbers')
        rows.append([float(x) for x in row])
    return dims, rows


class Alignment:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else DEFAULT_PATH
        self.dimensions = 0
        self.metadata = {}
        self._columns = None
        if not self.path.is_file():
            return
        if self.path.stat().st_size > MAX_BYTES:
            raise ValueError('Alignment matrix exceeds the 4 MB runtime budget')
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f'Invalid alignment file: {self.path}') from error
        self.dimensions, rows = validate_matrix(data)
        # mapped[j] = sum_i v[i] * W[i][j]; store columns for a dot product per output.
        self._columns = [list(col) for col in zip(*rows)]
        self.metadata = {k: data[k] for k in ('version', 'method', 'source', 'train_pairs', 'heldout_pairs', 'metrics') if k in data}

    @property
    def enabled(self):
        return self._columns is not None

    def apply(self, vector):
        """Return the unit-length vector @ W (unchanged but normalised when disabled)."""
        if not self.enabled:
            return _normalize(vector)
        if len(vector) != self.dimensions:
            raise ValueError(f'Expected a {self.dimensions}-dimensional vector, got {len(vector)}')
        mapped = [sum(a * b for a, b in zip(vector, col)) for col in self._columns]
        return _normalize(mapped)
