"""Embed every prepared problem (both languages) for the laptop ML scripts.

Two sources, same output format:
  --port 8082      the board's embedding server (exact Q8 GGUF vectors; forward
                   the port over USB/SSH first). Preferred for final artifacts.
  --local          sentence-transformers BAAI/bge-small-en-v1.5 in fp32 on the
                   laptop. Same model family as the board's GGUF, tiny numeric
                   differences. Used when the board is unreachable.

Output: data/ml/embeddings.json = {"model": ..., "source": ..., "dimensions": 384,
"vectors": {"<id>|<language>": [384 floats]}}. Unit-normalised, no query prefix
(documents, not queries). M3Kang text never leaves this machine.
"""
import argparse
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_CHARS = 1400  # about 512 tokens, matches copilot/embed.py


def load_rows(paths):
    rows = []
    for path in paths:
        for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def normalize(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def embed_server(texts, port, batch=16):
    out = []
    for i in range(0, len(texts), batch):
        chunk = [t[:MAX_CHARS] for t in texts[i:i + batch]]
        req = urllib.request.Request(f'http://127.0.0.1:{port}/v1/embeddings', data=json.dumps({'input': chunk}).encode(),
                                     headers={'Content-Type': 'application/json'})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=120) as r:
            data = json.load(r)['data']
        out.extend(normalize(d['embedding']) for d in sorted(data, key=lambda d: d['index']))
        print(f'  {min(i + batch, len(texts))}/{len(texts)}', end='\r', file=sys.stderr)
    return out


def embed_local(texts):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('BAAI/bge-small-en-v1.5', device='cpu')
    vectors = model.encode([t[:MAX_CHARS] for t in texts], batch_size=32, normalize_embeddings=True, show_progress_bar=True)
    return [[float(x) for x in v] for v in vectors]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--input', nargs='+', default=[ROOT / 'data/train.jsonl', ROOT / 'data/val.jsonl'])
    p.add_argument('--output', type=Path, default=ROOT / 'data/ml/embeddings.json')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--port', type=int)
    g.add_argument('--local', action='store_true')
    args = p.parse_args()
    rows = load_rows(args.input)
    keys, texts = [], []
    for r in rows:
        text = (r.get('text') or '').strip()
        options = r.get('options') or {}
        if options:
            text += '\n' + ' '.join(f'({k}) {v}' for k, v in sorted(options.items()))
        if not text.strip():
            continue
        keys.append(f"{r['id']}|{r['language']}")
        texts.append(text)
    started = time.time()
    vectors = embed_server(texts, args.port) if args.port else embed_local(texts)
    source = f'board llama-server port {args.port} (GGUF Q8)' if args.port else 'laptop sentence-transformers fp32'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'model': 'BAAI/bge-small-en-v1.5', 'source': source, 'dimensions': len(vectors[0]),
                                       'count': len(keys), 'vectors': dict(zip(keys, vectors))}), encoding='utf-8')
    print(f'\n{len(keys)} vectors ({len(vectors[0])}-d) from {source} in {time.time() - started:.0f}s -> {args.output}')


if __name__ == '__main__':
    main()
