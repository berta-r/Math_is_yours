"""T-106: build the problem map (kNN graph, Louvain communities, UMAP layout).

Nodes are canonical problem ids from train + val. Each node's vector is its
English embedding, or the Procrustes-aligned Catalan one when no English text
exists. Edges: undirected union of each node's k=5 cosine nearest neighbours,
weight = cosine. Communities: networkx Louvain (seed 42). Layout: UMAP
(cosine, seed 42) scaled to [0, 1000]. Cluster keywords: top TF-IDF words per
cluster (English texts, stop words removed) as a naming hint.

Difficulty b comes from data/ml/difficulty.json when it exists, otherwise
b = level / 8 + 0.25. Output: data/ml/problem_map.json (<= 400 KB) and
results/map-metrics.json. Run with .venv-ml/bin/python.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from laptop.ml.align import normalize_rows  # noqa: E402

MAX_BYTES = 400 * 1024


def load_rows(paths):
    rows = []
    for path in paths:
        for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def knn_edges(x, k):
    sims = x @ x.T
    np.fill_diagonal(sims, -np.inf)
    edges = {}
    for i in range(len(x)):
        # stable ordering: highest cosine first, lower index on ties
        order = np.lexsort((np.arange(len(x)), -sims[i]))[:k]
        for j in order:
            a, b = (i, int(j)) if i < j else (int(j), i)
            edges[(a, b)] = float(sims[i, j])
    return edges


def cluster_keywords(texts_by_cluster, top=6):
    labels = sorted(texts_by_cluster)
    docs = [' '.join(texts_by_cluster[c]) for c in labels]
    vec = TfidfVectorizer(stop_words='english', token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z]{2,}\b', sublinear_tf=True)
    m = vec.fit_transform(docs)
    vocab = np.array(vec.get_feature_names_out())
    out = {}
    for row, c in enumerate(labels):
        scores = m[row].toarray().ravel()
        order = np.lexsort((vocab, -scores))[:top]
        out[c] = [str(vocab[i]) for i in order if scores[i] > 0]
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--input', nargs='+', type=Path, default=[ROOT / 'data/train.jsonl', ROOT / 'data/val.jsonl'])
    p.add_argument('--embeddings', type=Path, default=ROOT / 'data/ml/embeddings.json')
    p.add_argument('--alignment', type=Path, default=ROOT / 'data/ml/procrustes.json')
    p.add_argument('--difficulty', type=Path, default=ROOT / 'data/ml/difficulty.json')
    p.add_argument('--alignment-metrics', type=Path, default=ROOT / 'results/alignment-metrics.json')
    p.add_argument('--output', type=Path, default=ROOT / 'data/ml/problem_map.json')
    p.add_argument('--metrics', type=Path, default=ROOT / 'results/map-metrics.json')
    p.add_argument('-k', type=int, default=5)
    args = p.parse_args()

    rows = load_rows(args.input)
    vectors = json.loads(args.embeddings.read_text(encoding='utf-8'))['vectors']
    w = np.array(json.loads(args.alignment.read_text(encoding='utf-8'))['matrix'])

    info = {}
    for r in rows:
        node = info.setdefault(r['id'], {'level': r['level'], 'languages': set(), 'eng_text': None})
        node['languages'].add(r['language'])
        if r['language'] == 'eng':
            node['eng_text'] = (r.get('text') or '') + ' ' + ' '.join((r.get('options') or {}).values())
    ids = sorted(pid for pid in info if any(f'{pid}|{lang}' in vectors for lang in ('eng', 'cat')))
    missing = len(info) - len(ids)
    vec_source = Counter()
    x = []
    for pid in ids:
        if f'{pid}|eng' in vectors:
            x.append(vectors[f'{pid}|eng'])
            vec_source['eng'] += 1
        else:
            x.append(np.array(vectors[f'{pid}|cat']) @ w)
            vec_source['cat-aligned'] += 1
    x = normalize_rows(np.array(x, dtype=np.float64))

    if args.difficulty.is_file():
        diff = json.loads(args.difficulty.read_text(encoding='utf-8'))['problems']
        b_source = f'{args.difficulty.name}'
        b = {pid: float(diff[pid]['b']) if pid in diff else info[pid]['level'] / 8 + 0.25 for pid in ids}
        b_missing = sum(pid not in diff for pid in ids)
    else:
        b_source = 'level/8+0.25 (difficulty.json absent)'
        b = {pid: info[pid]['level'] / 8 + 0.25 for pid in ids}
        b_missing = len(ids)

    edges = knn_edges(x, args.k)
    g = nx.Graph()
    g.add_nodes_from(range(len(ids)))
    g.add_weighted_edges_from((a, c, wt) for (a, c), wt in edges.items())
    communities = nx.community.louvain_communities(g, weight='weight', seed=42)
    # stable cluster ids: largest first, then smallest member index
    communities = sorted((sorted(c) for c in communities), key=lambda c: (-len(c), c[0]))
    cluster_of = {}
    for cid, members in enumerate(communities):
        for i in members:
            cluster_of[i] = cid
    modularity = nx.community.modularity(g, [set(c) for c in communities], weight='weight')

    import umap
    xy = umap.UMAP(n_neighbors=15, min_dist=0.1, random_state=42, metric='cosine').fit_transform(x)
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    xy = (xy - lo) / np.where(hi - lo == 0, 1, hi - lo) * 1000

    texts = {}
    for i, pid in enumerate(ids):
        if info[pid]['eng_text']:
            texts.setdefault(cluster_of[i], []).append(info[pid]['eng_text'])
    keywords = cluster_keywords(texts)

    nodes = [{'id': pid, 'level': info[pid]['level'], 'x': round(float(xy[i, 0]), 1), 'y': round(float(xy[i, 1]), 1),
              'cluster': cluster_of[i], 'b': round(b[pid], 3), 'languages': sorted(info[pid]['languages'])}
             for i, pid in enumerate(ids)]
    edge_list = [[a, c, round(wt, 3)] for (a, c), wt in sorted(edges.items())]
    clusters = [{'id': cid, 'size': len(m), 'keywords': keywords.get(cid, []),
                 'mean_b': round(float(np.mean([b[ids[i]] for i in m])), 3),
                 'mean_level': round(float(np.mean([info[ids[i]]['level'] for i in m])), 2)}
                for cid, m in enumerate(communities)]
    artifact = {'version': 1, 'source': {'embeddings': args.embeddings.name, 'alignment': args.alignment.name,
                                         'difficulty': b_source, 'vectors': dict(vec_source)},
                'k': args.k, 'nodes': nodes, 'edges': edge_list, 'clusters': clusters}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
    size = args.output.stat().st_size

    # Cross-lingual check on the T-104 held-out ids.
    position = {pid: i for i, pid in enumerate(ids)}
    eng_ids = [pid for pid in ids if f'{pid}|eng' in vectors]
    eng_x = normalize_rows(np.array([vectors[f'{pid}|eng'] for pid in eng_ids]))
    eng_pos = np.array([position[pid] for pid in eng_ids])
    held = []
    if args.alignment_metrics.is_file():
        held = json.loads(args.alignment_metrics.read_text(encoding='utf-8')).get('heldout_ids', [])
    held = [pid for pid in held if f'{pid}|cat' in vectors and f'{pid}|eng' in vectors and pid in position]
    cross = {}
    if held:
        cat_raw = normalize_rows(np.array([vectors[f'{pid}|cat'] for pid in held]))
        twin_cluster = np.array([cluster_of[position[pid]] for pid in held])
        twin_idx = np.array([eng_ids.index(pid) for pid in held])
        for name, q in (('unaligned', cat_raw), ('aligned', normalize_rows(cat_raw @ w))):
            sims = q @ eng_x.T
            nn = sims.argmax(axis=1)
            same = np.array([cluster_of[eng_pos[j]] for j in nn]) == twin_cluster
            sims_ex = sims.copy()
            sims_ex[np.arange(len(held)), twin_idx] = -np.inf
            nn_ex = sims_ex.argmax(axis=1)
            same_ex = np.array([cluster_of[eng_pos[j]] for j in nn_ex]) == twin_cluster
            cross[name] = {'same_cluster_nn': round(float(same.mean()), 4),
                           'same_cluster_nn_excluding_twin': round(float(same_ex.mean()), 4),
                           'nn_is_twin': round(float((nn == twin_idx).mean()), 4)}
    # baseline: an English vector's nearest other English neighbour in the same cluster
    sims = eng_x @ eng_x.T
    np.fill_diagonal(sims, -np.inf)
    nn = sims.argmax(axis=1)
    eng_baseline = float(np.mean([cluster_of[eng_pos[j]] == cluster_of[eng_pos[i]] for i, j in enumerate(nn)]))

    metrics = {'bytes': size, 'nodes': len(nodes), 'nodes_without_vectors': missing, 'edges': len(edge_list),
               'vector_source': dict(vec_source), 'difficulty_source': b_source, 'nodes_with_fallback_b': b_missing,
               'clusters': len(clusters), 'cluster_sizes': [c['size'] for c in clusters], 'modularity': round(modularity, 4),
               'cluster_keywords': {c['id']: c['keywords'] for c in clusters},
               'cross_lingual_heldout': len(held), 'cross_lingual': cross,
               'english_nn_same_cluster_baseline': round(eng_baseline, 4)}
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    args.metrics.write_text(json.dumps(metrics, indent=2), encoding='utf-8')

    print(f'nodes {len(nodes)} ({dict(vec_source)}), edges {len(edge_list)}, b from {b_source}')
    print(f'clusters {len(clusters)}, sizes {[c["size"] for c in clusters]}, modularity {modularity:.3f}')
    for c in clusters[:5]:
        print(f'  cluster {c["id"]:2d} size {c["size"]:3d} mean_b {c["mean_b"]:.2f} level {c["mean_level"]:.1f}: {", ".join(c["keywords"])}')
    for name, m in cross.items():
        print(f'cross-lingual ({len(held)} held-out, {name}): {m}')
    print(f'English nn same-cluster baseline: {eng_baseline:.4f}')
    print(f'wrote {args.output} ({size / 1024:.1f} KB), {args.metrics}')
    if size > MAX_BYTES:
        print('ERROR: map exceeds the 400 KB budget', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
