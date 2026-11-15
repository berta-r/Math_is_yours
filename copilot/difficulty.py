"""Problem difficulty b in [0, 1] and an Elo-style ability update; standard library only.

Artifacts are built on the laptop by ``laptop/ml/difficulty.py``:

- ``data/ml/difficulty.json`` (budget 1 MB): ``{"version": 1, "scale": ...,
  "problems": {id: {"level", "points", "expected_points", "b", "source"}}}``.
  ``b = (level + (points - 3) / 2) / 8``: level 0-7 is the coarse band and the
  3/4/5-point third of the paper moves the problem within it.
- ``data/ml/difficulty_model.json`` (budget 2 MB): a PCA projection of the 384-d
  bge-small embedding plus a few text statistics, one exported decision tree and
  optionally a gradient-boosted ensemble, evaluated here with plain loops.

Both files are optional. Without them ``b()`` falls back to the level band.

Probability and update (all on the same [0, 1] scale as ``b``):

- ``probability(theta, b) = 1 / (1 + exp(-6 * (theta - b)))``. With scale 6 a
  one-level gap (0.125) gives p ~= 0.68 and a two-level gap p ~= 0.82.
- ``elo_update(theta, b, correct, k=0.08) = clip(theta + k * (correct - p))``.
  K is expressed on the ability scale: one surprising result moves theta by at
  most 0.08, about two thirds of a level, so a run of 3-4 consistent answers is
  needed to cross a level. This is chess Elo's K=32 over its 400-point logistic
  unit (32/400 = 0.08) transposed to this scale.
"""
import json
import math
from pathlib import Path

from .knowledge import ROOT

DIFFICULTY_BUDGET = 1024 * 1024
MODEL_BUDGET = 2 * 1024 * 1024
CLASSES = (3, 4, 5)
SOURCES = ('observed', 'predicted')
MAX_TREE_DEPTH = 64
# Unknown id: the middle of its level band, b = level/8 + 1/16, which equals the
# value of an observed 4-point (middle-third) problem. Unknown level: 0.5.
FALLBACK_OFFSET = 1 / 16
FALLBACK_NO_LEVEL = 0.5


def b_from(level, points):
    """Scale shared with the laptop exporter: (level + (points - 3) / 2) / 8."""
    return (level + (points - 3) / 2) / 8


def probability(theta, b, scale=6.0):
    """Logistic chance of success for ability theta on difficulty b (both in [0, 1])."""
    z = scale * (theta - b)
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def elo_update(theta, b, correct, k=0.08, scale=6.0):
    """New ability after one independent first attempt, clipped to [0, 1]."""
    p = probability(theta, b, scale)
    return min(1.0, max(0.0, theta + k * ((1.0 if correct else 0.0) - p)))


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _load(path, budget, label):
    if path.stat().st_size > budget:
        raise ValueError(f'{label} exceeds the {budget // 1024} KiB runtime budget')
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f'Invalid {label}: {path}') from error


def validate_problems(data):
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('problems'), dict):
        raise ValueError('Difficulty table needs version 1 and a problems object')
    clean = {}
    for pid, row in data['problems'].items():
        if not isinstance(pid, str) or not isinstance(row, dict):
            raise ValueError('Difficulty rows must be objects keyed by problem id')
        level, points, expected, b = row.get('level'), row.get('points'), row.get('expected_points'), row.get('b')
        if type(level) is not int or not 0 <= level <= 7:
            raise ValueError(f'{pid}: level must be an integer 0-7')
        if points is not None and points not in CLASSES:
            raise ValueError(f'{pid}: points must be 3, 4, 5 or null')
        if not _number(expected) or not 3 <= expected <= 5:
            raise ValueError(f'{pid}: expected_points must be in [3, 5]')
        if not _number(b) or not 0 <= b <= 1:
            raise ValueError(f'{pid}: b must be in [0, 1]')
        if row.get('source') not in SOURCES or (row['source'] == 'observed') != (points is not None):
            raise ValueError(f'{pid}: source must be observed exactly when points are known')
        clean[pid] = {'level': level, 'points': points, 'expected_points': float(expected), 'b': float(b),
                      'source': row['source']}
    return clean


def _validate_tree(node, n_features, n_out, depth=0):
    if depth > MAX_TREE_DEPTH or not isinstance(node, dict):
        raise ValueError('Tree nodes must be objects within the depth limit')
    if 'leaf' in node:
        leaf = node['leaf']
        if not isinstance(leaf, list) or len(leaf) != n_out or not all(_number(v) for v in leaf):
            raise ValueError('Tree leaves need one finite value per output')
        return
    feature, threshold = node.get('feature'), node.get('threshold')
    if type(feature) is not int or not 0 <= feature < n_features or not _number(threshold):
        raise ValueError('Tree splits need a known feature index and a finite threshold')
    _validate_tree(node.get('left'), n_features, n_out, depth + 1)
    _validate_tree(node.get('right'), n_features, n_out, depth + 1)


def validate_model(data):
    if not isinstance(data, dict) or data.get('version') != 1:
        raise ValueError('Difficulty model needs version 1 metadata')
    features = data.get('features')
    if not isinstance(features, list) or not features or not all(isinstance(f, str) for f in features):
        raise ValueError('Difficulty model needs a list of feature names')
    if list(data.get('classes') or []) != list(CLASSES):
        raise ValueError('Difficulty model classes must be [3, 4, 5]')
    pca = data.get('pca')
    if not isinstance(pca, dict) or not isinstance(pca.get('mean'), list) or not isinstance(pca.get('components'), list):
        raise ValueError('Difficulty model needs pca.mean and pca.components')
    mean, components = pca['mean'], pca['components']
    if not mean or not all(_number(v) for v in mean):
        raise ValueError('pca.mean must be finite numbers')
    if not components or any(not isinstance(c, list) or len(c) != len(mean) or not all(_number(v) for v in c)
                             for c in components):
        raise ValueError('Each PCA component must match the embedding dimension')
    stats = features[len(components):]
    if len(features) <= len(components) or len(set(stats)) != len(stats):
        raise ValueError('Features must list the PCA components followed by named statistics')
    _validate_tree(data.get('tree'), len(features), len(CLASSES))
    ensemble = data.get('ensemble')
    if ensemble is not None:
        if not isinstance(ensemble, dict) or not _number(ensemble.get('learning_rate')):
            raise ValueError('Ensemble needs a finite learning_rate')
        init, trees = ensemble.get('init'), ensemble.get('trees')
        if not isinstance(init, list) or len(init) != len(CLASSES) or not all(_number(v) for v in init):
            raise ValueError('Ensemble init needs one raw score per class')
        if not isinstance(trees, list) or not trees:
            raise ValueError('Ensemble needs at least one stage')
        for stage in trees:
            if not isinstance(stage, list) or len(stage) != len(CLASSES):
                raise ValueError('Each ensemble stage needs one regression tree per class')
            for tree in stage:
                _validate_tree(tree, len(features), 1)
    if data.get('preferred', 'tree') not in ('tree', 'ensemble') or (data.get('preferred') == 'ensemble' and ensemble is None):
        raise ValueError('preferred must name an exported model')
    return data


def walk(node, x):
    """Leaf values of a nested-dict tree; sklearn convention x[i] <= threshold goes left."""
    while 'leaf' not in node:
        node = node['left'] if x[node['feature']] <= node['threshold'] else node['right']
    return node['leaf']


def softmax(raw):
    top = max(raw)
    exps = [math.exp(v - top) for v in raw]
    total = sum(exps)
    return [v / total for v in exps]


class Difficulty:
    def __init__(self, path=ROOT / 'data/ml/difficulty.json', model_path=ROOT / 'data/ml/difficulty_model.json'):
        self.problems = {}
        self.model = None
        self.metadata = {}
        path = Path(path) if path is not None else None
        model_path = Path(model_path) if model_path is not None else None
        if path is not None and path.is_file():
            data = _load(path, DIFFICULTY_BUDGET, 'difficulty table')
            self.problems = validate_problems(data)
            self.metadata = {key: data[key] for key in ('version', 'scale', 'model') if key in data}
        if model_path is not None and model_path.is_file():
            self.model = validate_model(_load(model_path, MODEL_BUDGET, 'difficulty model'))

    def b(self, problem_id, level=None):
        """Stored difficulty, else the middle of the level band (see FALLBACK_OFFSET)."""
        row = self.problems.get(problem_id)
        if row is not None:
            return row['b']
        if row is None and level is None:
            return FALLBACK_NO_LEVEL
        return min(1.0, max(0.0, level / 8 + FALLBACK_OFFSET))

    def expected_points(self, problem_id):
        row = self.problems.get(problem_id)
        return row['expected_points'] if row is not None else None

    def vector(self, features):
        """Model input: PCA projection of ``features['embedding']`` then the named statistics."""
        if self.model is None:
            raise ValueError('No difficulty model loaded')
        mean, components = self.model['pca']['mean'], self.model['pca']['components']
        embedding = features.get('embedding')
        if not isinstance(embedding, (list, tuple)) or len(embedding) != len(mean):
            raise ValueError(f'embedding must have {len(mean)} values')
        centred = [float(v) - m for v, m in zip(embedding, mean)]
        x = [sum(c * v for c, v in zip(component, centred)) for component in components]
        for name in self.model['features'][len(components):]:
            value = features.get(name)
            x.append(0.0 if value is None else float(value))
        return x

    def tree_proba(self, x):
        leaf = walk(self.model['tree'], x)
        total = sum(leaf) or 1.0
        return [v / total for v in leaf]

    def ensemble_proba(self, x):
        ensemble = self.model['ensemble']
        raw = list(ensemble['init'])
        rate = ensemble['learning_rate']
        for stage in ensemble['trees']:
            for k, tree in enumerate(stage):
                raw[k] += rate * walk(tree, x)[0]
        return softmax(raw)

    def evaluate(self, features, model=None):
        """Class probabilities for 3/4/5 points and their expectation.

        ``features`` holds ``embedding`` (384 floats) and the statistics named in
        the model (``level``, ``text_chars``, ...; missing or null -> 0).
        ``model`` is 'tree', 'ensemble' or None for the exported preference.
        """
        x = self.vector(features)
        choice = model or self.model.get('preferred', 'tree')
        if choice == 'ensemble' and self.model.get('ensemble') is not None:
            proba = self.ensemble_proba(x)
        elif choice in ('tree', 'ensemble'):
            choice, proba = 'tree', self.tree_proba(x)
        else:
            raise ValueError('model must be tree or ensemble')
        expected = sum(p * c for p, c in zip(proba, CLASSES))
        return {'model': choice, 'probabilities': proba, 'expected_points': expected}
