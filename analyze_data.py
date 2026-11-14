"""Quick data analysis to choose a Reason strategy. Laptop only, stdlib."""
import json
import re
import sys
from collections import Counter

NUM = re.compile(r"^\s*[-−+]?\d+([.,]\d+)?\s*(%|cm²?|m²?|cm|m|kg|g|°|€|h|min)?\s*$")
WORD = re.compile(r"[a-zà-ü0-9]+")


def load(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def numeric(p):
    o = p["options"]
    return len(o) == 5 and all(NUM.match(v) for v in o.values())


def num_value(s):
    m = re.search(r"[-−+]?\d+([.,]\d+)?", s)
    return float(m.group(0).replace(",", ".").replace("−", "-")) if m else None


def report(name, rows):
    n = len(rows)
    if not n:
        return
    with_opts = sum(1 for p in rows if p["options"])
    nums = [p for p in rows if numeric(p)]
    print(f"\n== {name}: {n} problems")
    print(f"  options read by OCR:      {with_opts} ({100*with_opts/n:.0f}%)")
    print(f"  text_only:                {sum(p['text_only'] for p in rows)} ({100*sum(p['text_only'] for p in rows)/n:.0f}%)")
    print(f"  all 5 options numeric:    {len(nums)} ({100*len(nums)/n:.0f}%)")
    print(f"  labels: {dict(sorted(Counter(p['label'] for p in rows).items()))}")
    print(f"  levels: {dict(sorted(Counter(p['level'] for p in rows).items()))}")
    # position of the correct value among sorted numeric options
    ranks = Counter()
    for p in nums:
        vals = {k: num_value(v) for k, v in p["options"].items()}
        order = sorted(vals, key=lambda k: vals[k])
        ranks[order.index(p["label"]) + 1] += 1
    if ranks:
        tot = sum(ranks.values())
        print("  rank of correct value (1=smallest): " +
              ", ".join(f"{r}:{100*c/tot:.0f}%" for r, c in sorted(ranks.items())))
    # are options sorted ascending by letter? (Kangaroo usually sorts them)
    asc = sum(1 for p in nums if [num_value(p["options"][l]) for l in "ABCDE"] ==
              sorted(num_value(p["options"][l]) for l in "ABCDE"))
    if nums:
        print(f"  numeric options sorted A<B<..<E: {asc} ({100*asc/len(nums):.0f}%)")


def jaccard(a, b):
    return len(a & b) / max(1, len(a | b))


def duplicates(train, val, lang="eng", thr=0.6):
    tr = [(p, set(WORD.findall(p["text"].lower()))) for p in train if p["language"] == lang]
    hits = same_value = 0
    vs = [p for p in val if p["language"] == lang]
    examples = []
    for p in vs:
        w = set(WORD.findall(p["text"].lower()))
        best, score = max(((q, jaccard(w, ws)) for q, ws in tr), key=lambda t: t[1], default=(None, 0))
        if score >= thr:
            hits += 1
            if p["options"] and best["options"]:
                if p["options"].get(p["label"]) == best["options"].get(best["label"]):
                    same_value += 1
            if len(examples) < 3:
                examples.append((score, p["id"], best["id"]))
    print(f"\n== near-duplicates val->train ({lang}, word Jaccard >= {thr}): {hits}/{len(vs)}, "
          f"same correct value: {same_value}")
    for e in examples:
        print(f"  {e[0]:.2f}  {e[1]}  ~  {e[2]}")


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "data"
    train, val = load(f"{folder}/train.jsonl"), load(f"{folder}/val.jsonl")
    report("train", train)
    report("val", val)
    for lang in sorted({p["language"] for p in val}):
        report(f"val {lang}", [p for p in val if p["language"] == lang])
    report("val text_only", [p for p in val if p["text_only"]])
    duplicates(train, val)
