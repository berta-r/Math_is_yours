"""Difficulty model from paper position (T-102).

``train``: features.jsonl + embeddings.json -> X = PCA(32) of the English
embedding + [level, text_chars, words, numerals, has_image, n_options,
numeric_options, option_spread]. Target: points (3/4/5). Years 2023-2024 are
held out; 5-fold grouped CV over years checks stability. Two models: one
depth-6 decision tree and a small gradient-boosted ensemble. The final export
is refitted on every labelled row; the better model (hold-out Spearman) gives
the expected points used for rows without observed points.

Writes results/difficulty-metrics.json, data/ml/difficulty_model.json (read by
copilot/difficulty.py in pure Python) and data/ml/difficulty.json (id -> b).

``predict --id <id>``: features, both models' output through the pure-Python
evaluator, and the stored b.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.decomposition import PCA
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import GroupKFold
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from copilot.difficulty import CLASSES, Difficulty, b_from  # noqa: E402

N_COMPONENTS = 32
STATS = ['level', 'text_chars', 'words', 'numerals', 'has_image', 'n_options', 'numeric_options', 'option_spread']
HOLDOUT_YEARS = (2023, 2024)
SCALE = 'b = (level + (expected_points - 3)/2) / 8, in [0,1]'


def r6(value):
    return round(float(value), 6)


def load_features(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def stat_matrix(rows):
    return np.array([[0.0 if r[name] is None else float(r[name]) for name in STATS] for r in rows])


def embedding_matrix(rows, vectors):
    return np.array([vectors[r['key']] for r in rows], dtype=float)


class Model:
    """PCA on the embedding + statistics, then a classifier. Fit/transform kept together."""

    def __init__(self, kind, n_components=N_COMPONENTS):
        self.kind, self.n_components = kind, n_components
        self.pca = PCA(n_components=n_components, random_state=42)
        if kind == 'tree':
            self.clf = DecisionTreeClassifier(max_depth=6, min_samples_leaf=20, random_state=42)
        else:
            self.clf = GradientBoostingClassifier(n_estimators=150, max_depth=3, learning_rate=0.05, random_state=42)

    def design(self, emb, stats, fit=False):
        if fit:
            # Train on the exact 6-decimal projection that is exported, so the
            # board's PCA does not move rows across split thresholds.
            self.pca.fit(emb)
            self.pca.mean_ = np.round(self.pca.mean_, 6)
            self.pca.components_ = np.round(self.pca.components_, 6)
        return np.hstack([self.pca.transform(emb), stats])

    def fit(self, emb, stats, y):
        self.clf.fit(self.design(emb, stats, fit=True), y)
        return self

    def proba(self, emb, stats):
        return self.clf.predict_proba(self.design(emb, stats))


def metrics(proba, y, rows, majority):
    classes = np.array(CLASSES)
    pred = classes[proba.argmax(1)]
    expected = proba @ classes
    rel = np.array([r['position'] / r['max_position'] for r in rows])
    papers = collections.defaultdict(list)
    for i, r in enumerate(rows):
        papers[(r['level'], r['year'])].append(i)
    per_paper = [spearmanr(expected[idx], rel[idx])[0] for idx in papers.values() if len(idx) >= 5]
    per_paper = [v for v in per_paper if np.isfinite(v)]
    return {
        'n': int(len(y)),
        'accuracy': r6((pred == y).mean()),
        'baseline_accuracy': r6((y == majority).mean()),
        'mae_expected': r6(np.abs(expected - y).mean()),
        'mae_argmax': r6(np.abs(pred - y).mean()),
        'baseline_mae': r6(np.abs(majority - y).mean()),
        'spearman_pooled': r6(spearmanr(expected, rel)[0]),
        'spearman_within_paper_mean': r6(np.mean(per_paper)) if per_paper else None,
        'papers': len(per_paper),
    }


def majority_of(y):
    return int(collections.Counter(y.tolist()).most_common(1)[0][0])


def export_tree(tree, leaf_kind='proba'):
    """sklearn tree_ -> nested dicts. 'proba' leaves are normalised class fractions; 'value' is the regression output.

    Leaves are rounded to 6 decimals; thresholds keep full precision because a
    threshold is the midpoint of two neighbouring values and rounding it can
    land exactly on one of them (e.g. option_spread, itself 6-decimal), which
    sends that value down the other branch.
    """
    t = tree.tree_

    def node(i):
        if t.children_left[i] == -1:
            if leaf_kind == 'proba':
                v = t.value[i][0]
                return {'leaf': [r6(x) for x in v / v.sum()]}
            return {'leaf': [r6(t.value[i][0][0])]}
        return {'feature': int(t.feature[i]), 'threshold': float(t.threshold[i]),
                'left': node(t.children_left[i]), 'right': node(t.children_right[i])}
    return node(0)


def export_model(tree_model, gb_model, preferred, feature_names):
    """Both models must share one PCA; ensemble stages are exported per class."""
    out = {'version': 1, 'features': feature_names,
           'pca': {'mean': [r6(v) for v in tree_model.pca.mean_],
                   'components': [[r6(v) for v in comp] for comp in tree_model.pca.components_]},
           'classes': list(CLASSES), 'preferred': preferred,
           'tree': export_tree(tree_model.clf)}
    if gb_model is not None:
        gb = gb_model.clf
        x0 = np.zeros((1, gb.n_features_in_))
        stages = [[export_tree(est, 'value') for est in stage] for stage in gb.estimators_]
        leaf_sum = np.array([[est.predict(x0)[0] for est in stage] for stage in gb.estimators_]).sum(0)
        init = gb.decision_function(x0)[0] - gb.learning_rate * leaf_sum
        out['ensemble'] = {'learning_rate': gb.learning_rate, 'init': [r6(v) for v in init], 'trees': stages}
    return out


def fit_pair(emb, stats, y):
    """Fit the tree and the ensemble on one shared PCA (identical random_state and data)."""
    tree = Model('tree').fit(emb, stats, y)
    gb = Model('gb')
    gb.pca = tree.pca
    gb.clf.fit(tree.design(emb, stats), y)
    return tree, gb


def train(args):
    rows = load_features(args.features)
    vectors = json.loads(Path(args.embeddings).read_text(encoding='utf-8'))['vectors']
    labelled = [r for r in rows if r['points'] is not None]
    emb, stats = embedding_matrix(labelled, vectors), stat_matrix(labelled)
    y = np.array([r['points'] for r in labelled])
    years = np.array([r['year'] for r in labelled])
    hold = np.isin(years, HOLDOUT_YEARS)
    report = {'rows': len(rows), 'labelled': len(labelled), 'holdout_years': list(HOLDOUT_YEARS), 'holdout': {}, 'cv': {}}

    tree, gb = fit_pair(emb[~hold], stats[~hold], y[~hold])
    majority = majority_of(y[~hold])
    hold_rows = [r for r, h in zip(labelled, hold) if h]
    for name, m in (('tree', tree), ('gb', gb)):
        report['holdout'][name] = metrics(m.proba(emb[hold], stats[hold]), y[hold], hold_rows, majority)
    report['holdout']['majority_class'] = majority

    folds = GroupKFold(n_splits=5)
    cv = {'tree': [], 'gb': []}
    for tr, te in folds.split(emb, y, groups=years):
        t_m, g_m = fit_pair(emb[tr], stats[tr], y[tr])
        maj = majority_of(y[tr])
        te_rows = [labelled[i] for i in te]
        cv['tree'].append(metrics(t_m.proba(emb[te], stats[te]), y[te], te_rows, maj))
        cv['gb'].append(metrics(g_m.proba(emb[te], stats[te]), y[te], te_rows, maj))
    for name, folds_m in cv.items():
        keys = [k for k in folds_m[0] if k not in ('n', 'papers') and folds_m[0][k] is not None]
        report['cv'][name] = {k: {'mean': r6(np.mean([f[k] for f in folds_m])), 'std': r6(np.std([f[k] for f in folds_m]))}
                              for k in keys}
        report['cv'][name]['folds'] = folds_m

    h = report['holdout']
    preferred = 'ensemble' if h['gb']['spearman_pooled'] > h['tree']['spearman_pooled'] else 'tree'
    report['preferred'] = preferred

    # Final models on every labelled row.
    tree_all, gb_all = fit_pair(emb, stats, y)
    names = [f'pca_{i}' for i in range(N_COMPONENTS)] + STATS
    model_json = export_model(tree_all, gb_all, preferred, names)
    Path(args.model).parent.mkdir(parents=True, exist_ok=True)
    Path(args.model).write_text(json.dumps(model_json, separators=(',', ':')), encoding='utf-8')
    size = Path(args.model).stat().st_size
    report['model_bytes'] = size

    # Pure-Python check of the export against sklearn on all labelled rows.
    pure = Difficulty(path=None, model_path=args.model)
    all_emb, all_stats = embedding_matrix(rows, vectors), stat_matrix(rows)
    sk_tree = tree_all.proba(all_emb, all_stats)
    sk_gb = gb_all.proba(all_emb, all_stats)
    diffs = {'tree': 0.0, 'ensemble': 0.0}
    expected = {}
    for i, r in enumerate(rows):
        feats = {'embedding': vectors[r['key']], **{k: r[k] for k in STATS}}
        out_t = pure.evaluate(feats, 'tree')
        out_g = pure.evaluate(feats, 'ensemble')
        diffs['tree'] = max(diffs['tree'], float(np.abs(np.array(out_t['probabilities']) - sk_tree[i]).max()))
        diffs['ensemble'] = max(diffs['ensemble'], float(np.abs(np.array(out_g['probabilities']) - sk_gb[i]).max()))
        expected[r['id']] = (out_g if preferred == 'ensemble' else out_t)['expected_points']
    report['export_max_abs_diff'] = {k: float(f'{v:.3g}') for k, v in diffs.items()}

    problems = {}
    for r in rows:
        exp = min(5.0, max(3.0, expected[r['id']]))
        observed = r['points'] is not None
        b = b_from(r['level'], r['points'] if observed else exp)
        problems[r['id']] = {'level': r['level'], 'points': r['points'], 'expected_points': r6(exp),
                             'b': r6(min(1.0, max(0.0, b))), 'source': 'observed' if observed else 'predicted'}
    table = {'version': 1, 'scale': SCALE, 'model': preferred, 'problems': problems}
    Path(args.table).write_text(json.dumps(table, separators=(',', ':')), encoding='utf-8')
    report['table_bytes'] = Path(args.table).stat().st_size
    Path(args.metrics).parent.mkdir(parents=True, exist_ok=True)
    Path(args.metrics).write_text(json.dumps(report, indent=2), encoding='utf-8')

    print(f'labelled rows {len(labelled)}  hold-out {int(hold.sum())} (years {HOLDOUT_YEARS})  train {int((~hold).sum())}')
    print(f'{"":14}{"acc":>7}{"base":>7}{"MAE(E)":>8}{"MAE(arg)":>9}{"MAEbase":>8}{"rho":>7}{"rho/paper":>10}')
    for name in ('tree', 'gb'):
        m = h[name]
        print(f'hold-out {name:5}{m["accuracy"]:7.3f}{m["baseline_accuracy"]:7.3f}{m["mae_expected"]:8.3f}{m["mae_argmax"]:9.3f}'
              f'{m["baseline_mae"]:8.3f}{m["spearman_pooled"]:7.3f}{m["spearman_within_paper_mean"]:10.3f}')
    for name in ('tree', 'gb'):
        c = report['cv'][name]
        print(f'cv5 {name:10}' + ''.join(f'{c[k]["mean"]:{w}.3f}' for k, w in (
            ('accuracy', 7), ('baseline_accuracy', 7), ('mae_expected', 8), ('mae_argmax', 9), ('baseline_mae', 8),
            ('spearman_pooled', 7), ('spearman_within_paper_mean', 10))))
        print(f'    {"± std":10}' + ''.join(f'{c[k]["std"]:{w}.3f}' for k, w in (
            ('accuracy', 7), ('baseline_accuracy', 7), ('mae_expected', 8), ('mae_argmax', 9), ('baseline_mae', 8),
            ('spearman_pooled', 7), ('spearman_within_paper_mean', 10))))
    print(f'preferred {preferred}  model {args.model} {size / 1024:.1f} KiB  table {report["table_bytes"] / 1024:.1f} KiB')
    print(f'pure-Python export max |diff| vs sklearn: {report["export_max_abs_diff"]}')
    print('b by level: n  min  p25  median  p75  max  (observed/predicted)')
    for level in range(8):
        bs = np.array([p['b'] for p in problems.values() if p['level'] == level])
        if len(bs):
            src = collections.Counter(p['source'] for p in problems.values() if p['level'] == level)
            q = np.percentile(bs, [0, 25, 50, 75, 100])
            print(f'  {level}  {len(bs):4d}  ' + '  '.join(f'{v:.3f}' for v in q) + f'  ({src["observed"]}/{src["predicted"]})')


def predict(args):
    rows = {r['id']: r for r in load_features(args.features)}
    if args.id not in rows:
        sys.exit(f'unknown id {args.id}')
    r = rows[args.id]
    vectors = json.loads(Path(args.embeddings).read_text(encoding='utf-8'))['vectors']
    d = Difficulty(path=args.table, model_path=args.model)
    feats = {'embedding': vectors[r['key']], **{k: r[k] for k in STATS}}
    print(json.dumps({k: v for k, v in r.items() if k != 'key'}, ensure_ascii=False))
    for kind in ('tree', 'ensemble'):
        if kind == 'tree' or d.model.get('ensemble'):
            out = d.evaluate(feats, kind)
            print(f'{kind:8} p(3,4,5)=' + ', '.join(f'{p:.3f}' for p in out['probabilities']) +
                  f'  expected {out["expected_points"]:.3f}')
    print(f'stored b {d.b(args.id)}  expected_points {d.expected_points(args.id)}  row {d.problems.get(args.id)}')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--features', default=ROOT / 'data/ml/features.jsonl')
    p.add_argument('--embeddings', default=ROOT / 'data/ml/embeddings.json')
    p.add_argument('--model', default=ROOT / 'data/ml/difficulty_model.json')
    p.add_argument('--table', default=ROOT / 'data/ml/difficulty.json')
    sub = p.add_subparsers(dest='command', required=True)
    t = sub.add_parser('train')
    t.add_argument('--metrics', default=ROOT / 'results/difficulty-metrics.json')
    q = sub.add_parser('predict')
    q.add_argument('--id', required=True)
    args = p.parse_args()
    train(args) if args.command == 'train' else predict(args)


if __name__ == '__main__':
    main()
