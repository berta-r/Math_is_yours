"""Per-problem feature table for the difficulty model (T-101).

One row per canonical id (English and Catalan rows share the id). Text
statistics come from the English row, falling back to the Catalan one.

Free difficulty labels: Kangaroo papers are ordered by points, so the problem
number printed at the start of the text (``"13. ..."``) gives its position. With
``max_position`` the largest number seen for the same (level, year) over both
languages, points are 3 for the first third, 4 for the second, 5 for the last.
Papers whose largest observed number is below 12 are too incomplete to locate
the thirds and get ``points = null``.

Output: data/ml/features.jsonl, one JSON object per line. M3Kang-derived, so it
lives under the ignored data/ directory.
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIN_RELIABLE_MAX = 12
PREFIX = re.compile(r'^\s*(\d{1,2})\s*\.')
NUMBER = re.compile(r'\d+(?:[.,]\d+)?')
NUMERIC_OPTION = re.compile(r'^[\s$€£]*([-−]?\d+(?:[.,]\d+)?)(?:\s*/\s*(\d+(?:[.,]\d+)?))?\s*[^\d\s/]{0,12}(?:\s*[^\d\s/]{1,12})?\s*$')


def load_rows(paths):
    rows = []
    for path in paths:
        for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def parse_position(text):
    """Problem number from a leading ``"<n>."`` prefix, else None."""
    m = PREFIX.match(text or '')
    return int(m.group(1)) if m else None


def strip_prefix(text):
    return PREFIX.sub('', text or '', count=1)


def points_for(position, max_position):
    """3/4/5 by thirds of the paper; None without position or on an unreliable paper."""
    if position is None or max_position is None or max_position < MIN_RELIABLE_MAX:
        return None
    if position <= max_position / 3:
        return 3
    if position <= 2 * max_position / 3:
        return 4
    return 5


def numeric_value(option):
    """Float value of an option such as ``"12"``, ``"3,5 cm"``, ``"3/4"``; None if not numeric."""
    m = NUMERIC_OPTION.match(str(option))
    if not m:
        return None
    num = float(m.group(1).replace('−', '-').replace(',', '.'))
    if m.group(2):
        den = float(m.group(2).replace(',', '.'))
        if den == 0:
            return None
        num /= den
    return num


def option_stats(options):
    n = len(options or {})
    values = [numeric_value(v) for _, v in sorted((options or {}).items())]
    numeric = n == 5 and all(v is not None for v in values)
    spread = None
    if numeric:
        hi, lo = max(values), min(values)
        spread = round((hi - lo) / abs(hi), 6) if hi != 0 else None
    return n, numeric, spread


def build(rows, vector_keys=None):
    by_id = collections.defaultdict(dict)
    for r in rows:
        by_id[r['id']][r['language']] = r
    # Max position per paper over both languages.
    paper_max = {}
    for r in rows:
        pos = parse_position(r.get('text'))
        if pos is not None:
            key = (r['level'], r['year'])
            paper_max[key] = max(paper_max.get(key, 0), pos)
    out = []
    for pid in sorted(by_id):
        langs = by_id[pid]
        main = langs.get('eng') or langs.get('cat') or next(iter(langs.values()))
        position = parse_position(main.get('text'))
        if position is None:  # same paper and number in the other language
            for other in langs.values():
                position = parse_position(other.get('text'))
                if position is not None:
                    break
        max_position = paper_max.get((main['level'], main['year']))
        body = strip_prefix(main.get('text'))
        n_options, numeric, spread = option_stats(main.get('options'))
        key = f"{pid}|eng" if 'eng' in langs else f"{pid}|{main['language']}"
        if vector_keys is not None and key not in vector_keys:
            key = next((f'{pid}|{l}' for l in ('eng', 'cat') if f'{pid}|{l}' in vector_keys), None)
        out.append({
            'id': pid, 'level': main['level'], 'year': main['year'],
            'position': position, 'max_position': max_position,
            'points': points_for(position, max_position),
            'text_chars': len(body.strip()), 'words': len(body.split()),
            'numerals': len(NUMBER.findall(body)),
            'has_image': not main.get('text_only', False),
            'n_options': n_options, 'numeric_options': numeric, 'option_spread': spread,
            'key': key,
        })
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--input', nargs='+', default=[ROOT / 'data/train.jsonl', ROOT / 'data/val.jsonl'])
    p.add_argument('--embeddings', type=Path, default=ROOT / 'data/ml/embeddings.json')
    p.add_argument('--output', type=Path, default=ROOT / 'data/ml/features.jsonl')
    args = p.parse_args()
    keys = None
    if args.embeddings.is_file():
        keys = set(json.loads(args.embeddings.read_text(encoding='utf-8'))['vectors'])
    else:
        print(f'warning: {args.embeddings} missing, keys not checked', file=sys.stderr)
    table = build(load_rows(args.input), keys)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in table), encoding='utf-8')
    with_pos = sum(r['position'] is not None for r in table)
    with_pts = [r for r in table if r['points'] is not None]
    print(f'rows {len(table)}  with position {with_pos}  with points {len(with_pts)}  '
          f'numeric options {sum(r["numeric_options"] for r in table)}  missing embedding {sum(r["key"] is None for r in table)}')
    print('points histogram', dict(sorted(collections.Counter(r['points'] for r in with_pts).items())))
    print('level  rows  position  points  3/4/5')
    for level in sorted({r['level'] for r in table}):
        sub = [r for r in table if r['level'] == level]
        c = collections.Counter(r['points'] for r in sub)
        print(f'{level:5d}  {len(sub):4d}  {sum(r["position"] is not None for r in sub):8d}  '
              f'{sum(r["points"] is not None for r in sub):6d}  {c[3]}/{c[4]}/{c[5]}')
    print(f'wrote {args.output}')


if __name__ == '__main__':
    main()
