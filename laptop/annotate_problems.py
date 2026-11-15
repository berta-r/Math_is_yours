"""Propose problem clusters, then export explicit reviewed skill annotations.

No clustering output is treated as a prerequisite or a mastery observation.
Use English once per id, deterministic k-means, and keep generated files in data/.
"""
import argparse
import csv
import json
import math
import random
import re
import sqlite3
import struct
import sys
import urllib.request
from collections import Counter
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from copilot.knowledge import Knowledge


def normalise(vector):
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


def kmeans(vectors, k, seed=42, iterations=50):
    if not vectors or not 1 <= k <= len(vectors):
        raise ValueError('Cluster count must be between 1 and the number of English problems')
    dimensions = len(vectors[0])
    if not dimensions or any(len(v) != dimensions or any(not math.isfinite(x) for x in v) for v in vectors):
        raise ValueError('Vectors must have matching nonempty dimensions and finite values')
    rng = random.Random(seed)
    centers = [vectors[i][:] for i in rng.sample(range(len(vectors)), k)]
    labels = [-1] * len(vectors)
    for _ in range(iterations):
        new = [min(range(k), key=lambda c: sum((a-b)**2 for a,b in zip(v,centers[c]))) for v in vectors]
        if new == labels:
            break
        labels = new
        for c in range(k):
            members = [v for v, label in zip(vectors, labels) if label == c]
            if members:
                centers[c] = [sum(row[d] for row in members) / len(members) for d in range(dimensions)]
            else:
                centers[c] = vectors[rng.randrange(len(vectors))][:]
    return labels, centers


def text_vectors(problems):
    tokens = [Counter(re.findall(r'[a-z]{3,}', p['text'].lower())) for p in problems]
    counts = Counter(word for row in tokens for word in row)
    vocabulary = [w for w, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:512]]
    return [normalise([row[w] * math.log(1 + len(problems) / counts[w]) for w in vocabulary]) for row in tokens]


def cluster(args):
    canonical = {}
    for line in args.input.read_text(encoding='utf-8-sig').splitlines():
        if line.strip():
            p = json.loads(line)
            if p.get('language') == 'eng':
                canonical[p['id']] = p
    problems = [canonical[pid] for pid in sorted(canonical)]
    if not problems:
        raise ValueError('No English rows in the selected training file')
    if args.features == 'tfidf':
        vectors = text_vectors(problems)
    elif args.vectors:
        cache = json.loads(args.vectors.read_text(encoding='utf-8'))
        vectors = [normalise(cache[p['id']]) for p in problems]
    elif args.index:
        cache = {}
        with closing(sqlite3.connect(f'file:{args.index.resolve().as_posix()}?mode=ro', uri=True)) as con:
            for raw, blob in con.execute('SELECT problem, vec FROM problems'):
                p = json.loads(raw)
                if p.get('language') == 'eng':
                    cache[p['id']] = list(struct.unpack(f'<{len(blob)//4}f', blob))
        vectors = [normalise(cache[p['id']]) for p in problems]
    else:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        vectors = []
        for p in problems:
            request = urllib.request.Request(f'http://127.0.0.1:{args.port}/v1/embeddings', data=json.dumps({'input':[p['text'][:1400]]}).encode(), headers={'Content-Type':'application/json'})
            with opener.open(request, timeout=30) as response:
                vectors.append(normalise(json.load(response)['data'][0]['embedding']))
    labels, centers = kmeans(vectors, args.clusters)
    args.out.mkdir(parents=True, exist_ok=True)
    review = args.out / 'cluster-review.csv'
    if review.exists() and not args.overwrite:
        raise ValueError('Review file already exists. Use a new --out folder or --overwrite to regenerate it.')
    with review.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['id','cluster','text','skills','assessment_skill','status','reviewer'])
        writer.writeheader()
        for p, label in zip(problems, labels):
            writer.writerow({'id':p['id'], 'cluster':label, 'text':p['text'], 'status':'pending'})
    output = {'feature_method':args.features, 'seed':42, 'centroids':centers,
              'assignments':{p['id']:label for p,label in zip(problems,labels)},
              'vectors':{p['id']:vector for p,vector in zip(problems,vectors)},
              'representatives':{str(c):[problems[i]['id'] for i in sorted(
                  (i for i,label in enumerate(labels) if label==c),
                  key=lambda i:sum((a-b)**2 for a,b in zip(vectors[i],centers[c])))[:3]] for c in range(args.clusters)}}
    (args.out / 'clusters.json').write_text(json.dumps(output), encoding='utf-8')
    print(f'Proposed {len(problems)} English problems in {args.clusters} groups ({args.features}). Review {review}. No skill labels accepted automatically.')


def export_review(args):
    knowledge = Knowledge()
    result = json.loads(args.output.read_text(encoding='utf-8')) if args.output.exists() else {'version':1,'problems':{}}
    count = 0
    with args.review.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            if row['status'].strip().lower() != 'reviewed':
                # An explicit pending/rejected row revokes an earlier mapping.
                result['problems'].pop(row['id'], None)
                continue
            if not row.get('reviewer', '').strip():
                raise ValueError(f"{row['id']}: reviewed rows need a reviewer")
            item = {'status':'reviewed', 'skills':[s.strip() for s in row['skills'].split(';') if s.strip()],
                    'assessment_skill':row['assessment_skill'].strip() or None, 'provenance':row['reviewer'].strip()}
            knowledge.validate_annotation(item)
            previous = result['problems'].get(row['id'], {})
            result['problems'][row['id']] = dict(previous, **item)
            count += 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(f'Exported {count} explicitly reviewed mappings to {args.output}; existing scaffolding preserved.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('cluster')
    p.add_argument('--input', type=Path, default=ROOT/'data/train.jsonl')
    p.add_argument('--out', type=Path, default=ROOT/'data/clustering')
    p.add_argument('--features', choices=['embeddings','tfidf'], default='embeddings')
    source = p.add_mutually_exclusive_group()
    source.add_argument('--vectors', type=Path, help='JSON object mapping canonical id to embedding vector')
    source.add_argument('--index', type=Path, help='Existing training SQLite embedding index')
    p.add_argument('--port', type=int, default=8082, help='Local embedding server port')
    p.add_argument('--clusters', type=int, default=8)
    p.add_argument('--overwrite', action='store_true')
    p = sub.add_parser('export')
    p.add_argument('--review', type=Path, required=True)
    p.add_argument('--output', type=Path, default=ROOT/'data/teaching_annotations.json')
    args = parser.parse_args()
    try:
        cluster(args) if args.command == 'cluster' else export_review(args)
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
