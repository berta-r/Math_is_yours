#!/usr/bin/env python3
"""Official entry point: answer every problem with one letter, A to E.

    python3 predict.py --input problems.jsonl --output predictions.csv
    python3 predict.py --input problems.jsonl --output predictions.csv --rag 1
    python3 predict.py --input problems.jsonl --output predictions.csv --steps dedup,logprobs,pot

Input: one JSON object per line with at least "id" and "text", plus
"options" ({"A": ..., "E": ...}) and "language" when available.
Output: a CSV with id, language, answer, seconds, status.

Rules: runs offline, at most 60 seconds per problem, deterministic.
"""
import argparse
import csv
import json
import os
import sys

from copilot.pipeline import DEFAULT_STEPS, parse_steps, prepare, solve


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--rag", type=int, default=0, metavar="K", help="add K similar solved problems")
    p.add_argument("--index", default="data/index.db")
    p.add_argument("--steps", default=DEFAULT_STEPS,
                   help=f"pipeline steps, e.g. dedup,logprobs,pot (default from config.env: {DEFAULT_STEPS})")
    args = p.parse_args()
    steps = parse_steps(args.steps)

    index = None
    if args.rag or "dedup" in steps:
        if os.path.exists(args.index):
            from copilot.rag import Index
            index = Index(args.index)
        elif args.rag:
            sys.exit(f"{args.index} not found. Build it first: python3 build_index.py")
        else:
            print(f"warning: {args.index} not found, the dedup step is skipped", file=sys.stderr)
            steps = [s for s in steps if s != "dedup"]

    with open(args.input) as f:
        problems = [json.loads(line) for line in f if line.strip()]

    prepare(steps)  # calibration prompts, outside the per-problem clock
    with open(args.output, "w", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["id", "language", "answer", "seconds", "status"])
        for n, problem in enumerate(problems, 1):
            result = solve(problem, index=index, k=args.rag, steps=steps)
            writer.writerow([problem["id"], problem.get("language", ""), result["answer"],
                             result["seconds"], result["status"]])
            out.flush()
            print(f"[{n}/{len(problems)}] {problem['id']} -> {result['answer']} by {result['method']} "
                  f"in {result['seconds']:.1f} s ({result['status']})", file=sys.stderr)


if __name__ == "__main__":
    main()
