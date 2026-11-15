"""T-104: align Catalan embeddings to English ones by orthogonal Procrustes.

bge-small is an English model, so a Catalan problem lands far from its English
twin. With the (cat, eng) pairs we solve, in closed form,

    W = argmin ||cat @ W - eng||_F  subject to  W^T W = I
      = U @ Vt   where  U S Vt = svd(cat^T @ eng)

No centering (the vectors are unit length); mapped vectors are re-normalised.
20% of ids (seed 42) are held out; retrieval is measured cat -> eng against
ALL English vectors, before and after the rotation.

Output: data/ml/procrustes.json (matrix rounded to 5 decimals, <= 4 MB) and
results/alignment-metrics.json. Run with .venv-ml/bin/python.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 4 * 1024 * 1024


def load_pairs(path):
    vectors = json.loads(Path(path).read_text(encoding='utf-8'))['vectors']
    by_id = {}
    for key, vec in vectors.items():
        pid, lang = key.rsplit('|', 1)
        by_id.setdefault(pid, {})[lang] = vec
    eng_ids = sorted(pid for pid, langs in by_id.items() if 'eng' in langs)
    pair_ids = sorted(pid for pid, langs in by_id.items() if 'eng' in langs and 'cat' in langs)
    eng_all = np.array([by_id[pid]['eng'] for pid in eng_ids], dtype=np.float64)
    cat = {pid: np.array(by_id[pid]['cat'], dtype=np.float64) for pid in pair_ids}
    eng = {pid: np.array(by_id[pid]['eng'], dtype=np.float64) for pid in pair_ids}
    return eng_ids, eng_all, pair_ids, cat, eng


def split_ids(ids, fraction=0.2, seed=42):
    ids = sorted(ids)
    order = np.random.default_rng(seed).permutation(len(ids))
    n_hold = int(round(len(ids) * fraction))
    held = sorted(ids[i] for i in order[:n_hold])
    train = sorted(ids[i] for i in order[n_hold:])
    return train, held


def normalize_rows(m):
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return m / norms


def procrustes(source, target):
    """Orthogonal W with source @ W ~= target (rows are paired vectors)."""
    u, _s, vt = np.linalg.svd(source.T @ target)
    return u @ vt


def retrieval(queries, query_ids, eng_all, eng_ids, ks=(1, 5)):
    """Recall@k of each query's own id among all English vectors (cosine)."""
    sims = normalize_rows(queries) @ eng_all.T
    position = {pid: i for i, pid in enumerate(eng_ids)}
    true_idx = np.array([position[pid] for pid in query_ids])
    true_sim = sims[np.arange(len(query_ids)), true_idx]
    rank = (sims > true_sim[:, None]).sum(axis=1)  # 0 = first
    return {f'recall@{k}': round(float((rank < k).mean()), 4) for k in ks} | {
        'mean_rank': round(float(rank.mean() + 1), 2)}


def evaluate(w, ids, cat, eng, eng_all, eng_ids):
    c = np.array([cat[pid] for pid in ids])
    e = np.array([eng[pid] for pid in ids])
    mapped = normalize_rows(c @ w)
    before = retrieval(c, ids, eng_all, eng_ids) | {'mean_pair_cosine': round(float((normalize_rows(c) * e).sum(1).mean()), 4)}
    after = retrieval(mapped, ids, eng_all, eng_ids) | {'mean_pair_cosine': round(float((mapped * e).sum(1).mean()), 4)}
    return {'before': before, 'after': after}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--embeddings', type=Path, default=ROOT / 'data/ml/embeddings.json')
    p.add_argument('--output', type=Path, default=ROOT / 'data/ml/procrustes.json')
    p.add_argument('--metrics', type=Path, default=ROOT / 'results/alignment-metrics.json')
    p.add_argument('--holdout', type=float, default=0.2)
    p.add_argument('--seed', type=int, default=42)
    args = p.parse_args()

    eng_ids, eng_all, pair_ids, cat, eng = load_pairs(args.embeddings)
    eng_all = normalize_rows(eng_all)
    train, held = split_ids(pair_ids, args.holdout, args.seed)
    w = procrustes(np.array([cat[i] for i in train]), np.array([eng[i] for i in train]))
    orth_error = float(np.abs(w.T @ w - np.eye(w.shape[0])).max())

    w_rounded = np.round(w, 5)
    metrics = {
        'heldout': evaluate(w_rounded, held, cat, eng, eng_all, eng_ids),
        'train': evaluate(w_rounded, train, cat, eng, eng_all, eng_ids),
        'retrieval_pool': len(eng_ids),
        'orthogonality_max_error': orth_error,
        'seed': args.seed,
    }
    artifact = {
        'version': 1,
        'method': 'orthogonal-procrustes',
        'dimensions': int(w.shape[0]),
        'source': 'cat->eng, ' + str(args.embeddings.name),
        'train_pairs': len(train),
        'heldout_pairs': len(held),
        'metrics': metrics['heldout'],
        'matrix': [[float(x) for x in row] for row in w_rounded],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, separators=(',', ':')), encoding='utf-8')
    size = args.output.stat().st_size
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    report = {'train_pairs': len(train), 'heldout_pairs': len(held), 'heldout_ids': held,
              'artifact_bytes': size} | metrics
    args.metrics.write_text(json.dumps(report, indent=2), encoding='utf-8')

    print(f'pairs: {len(pair_ids)} (train {len(train)}, held-out {len(held)}), pool {len(eng_ids)} English vectors')
    for split in ('heldout', 'train'):
        b, a = metrics[split]['before'], metrics[split]['after']
        print(f'{split:8s} recall@1 {b["recall@1"]:.4f} -> {a["recall@1"]:.4f}   recall@5 {b["recall@5"]:.4f} -> {a["recall@5"]:.4f}   '
              f'pair cosine {b["mean_pair_cosine"]:.4f} -> {a["mean_pair_cosine"]:.4f}')
    print(f'wrote {args.output} ({size / 1024 / 1024:.2f} MB), {args.metrics}')
    if size > MAX_BYTES:
        print('ERROR: artifact exceeds the 4 MB budget', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
