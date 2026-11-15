"""Prepare a compact skill-relatedness graph; never infer prerequisites.

Embeddings come from a local loopback server or a supplied vector file. An
explicit TF-IDF mode produces an honest keyword baseline without any model.
"""
import argparse
import hashlib
import json
import math
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from copilot.knowledge import Knowledge
from copilot.learning_graph import validate_relations

STOP = set('a an the is are be of to and or in on with for from by as at when while what which each every that this it its your you use using one more same before after how can'.split())


def documents(knowledge):
    return {sid:' '.join([skill['title'], skill['description'], skill.get('common_difficulty',''),
                         skill.get('hint_strategy','')]) for sid, skill in sorted(knowledge.skills.items())}


def digest(texts):
    return hashlib.sha256(json.dumps(texts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def keyword_vectors(texts):
    words = {sid:Counter(w for w in re.findall(r'[a-z]{3,}', text.lower()) if w not in STOP) for sid, text in texts.items()}
    frequency = Counter(word for row in words.values() for word in row)
    vocab = sorted(frequency)
    return {sid:[(1+math.log(row[word])) * math.log(1+len(words)/frequency[word]) if row[word] else 0.0 for word in vocab]
            for sid, row in words.items()}


def make_relations(knowledge, vectors, method, source, neighbors=2, threshold=.08):
    ids = sorted(knowledge.skills)
    if set(vectors) != set(ids):
        raise ValueError('Vectors must include exactly the current skill IDs')
    if not 1 <= neighbors <= min(5, max(1, len(ids)-1)) or not 0 <= threshold < 1:
        raise ValueError('Use 1–5 neighbors and a threshold in [0,1)')
    size = len(vectors[ids[0]])
    unit = {}
    for sid in ids:
        values = vectors[sid]
        if (not isinstance(values, list) or not size or len(values) != size or size > 8192
                or any(type(v) not in (int,float) or not math.isfinite(v) for v in values)):
            raise ValueError('Embeddings must be finite vectors with matching nonempty dimensions (max 8192)')
        length = math.sqrt(sum(v*v for v in values))
        if not length:
            raise ValueError(f'Cannot relate an empty vector for {sid}')
        unit[sid] = [v/length for v in values]
    similarities = {}
    for i, a in enumerate(ids):
        for b in ids[i+1:]:
            similarities[(a,b)] = max(-1.0, min(1.0, sum(x*y for x,y in zip(unit[a],unit[b]))))
    selected = set()
    for sid in ids:
        candidates = [(score, pair) for pair, score in similarities.items() if sid in pair and score > threshold]
        for score, pair in sorted(candidates, key=lambda row: (-row[0], row[1]))[:neighbors]:
            selected.add(pair)
    output = {'version':1, 'method':method, 'source':source, 'source_digest':digest(documents(knowledge)),
              'skill_ids':ids, 'neighbors':neighbors, 'threshold':threshold,
              'related_edges':[{'source':a,'target':b,'weight':round(similarities[(a,b)],6),'kind':'semantic'} for a,b in sorted(selected)]}
    validate_relations(output, knowledge.skills)
    return output


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Embedding redirects are disabled; use the local server directly')


def build(args):
    knowledge = Knowledge()
    texts = documents(knowledge)
    if args.features == 'tfidf':
        if args.vectors:
            raise ValueError('--vectors is for embeddings; do not combine it with --features tfidf')
        vectors, method, source = keyword_vectors(texts), 'keyword-tfidf', 'Authored English skill descriptions; keyword baseline'
    elif args.vectors:
        vectors = json.loads(args.vectors.read_text(encoding='utf-8'))
        method, source = 'embeddings', 'Supplied offline English skill embeddings'
    else:
        if not 1 <= args.port <= 65535:
            raise ValueError('Embedding port must be between 1 and 65535')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        vectors = {}
        for sid, text in texts.items():
            request = urllib.request.Request(f'http://127.0.0.1:{args.port}/v1/embeddings',
                                            data=json.dumps({'input':[text[:1400]]}).encode(),
                                            headers={'Content-Type':'application/json'})
            with opener.open(request, timeout=30) as response:
                vectors[sid] = json.loads(response.read(131072))['data'][0]['embedding']
        method, source = 'embeddings', 'Local loopback embedding server; authored English skill descriptions'
    output = make_relations(knowledge, vectors, method, source, args.neighbors, args.threshold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(f"Saved {len(output['related_edges'])} {method} relationships to {args.output}. Prerequisites and student estimates are unchanged.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features', choices=['embeddings','tfidf'], default='embeddings')
    parser.add_argument('--vectors', type=Path, help='JSON object keyed by skill ID; each value is an embedding vector')
    parser.add_argument('--port', type=int, default=8082)
    parser.add_argument('--neighbors', type=int, default=2)
    parser.add_argument('--threshold', type=float, default=.08)
    parser.add_argument('--output', type=Path, default=ROOT/'data/skill_graph.json')
    args = parser.parse_args()
    try:
        build(args)
    except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
