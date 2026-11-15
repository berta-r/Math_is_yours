# laptop/ml

Laptop-side scripts that turn the prepared M3Kang rows into small JSON artifacts
under `data/ml/` (git-ignored). The board reads those artifacts with pure Python;
it never runs these scripts. Standard library only unless a script says otherwise.

## Error signatures (T-108)

```bash
python3 laptop/ml/signatures.py            # data/train.jsonl + data/val.jsonl (samples if missing)
python3 laptop/ml/signatures.py --input data/sample_problems.jsonl --output /tmp/s.json --report /tmp/r.json
python3 -m unittest laptop.ml.test_signatures
```

- Output: `data/ml/signatures.json` (`{"version": 1, "source", "problems": {id: {"answer_op", "distractors"}}}`),
  about 100 KB, numbers and operation names only, keyed by canonical id. The report
  (coverage, operation histogram, English/Catalan numeral mismatches) goes to
  `results/signatures-report.json` and stdout.
- Only problems whose five options are all numbers (after stripping units such as
  `cm²`, `€`, `%`) get signatures. For each distractor the cheapest naive operation
  over the text's numerals that gives its value is kept: copied number, sum,
  difference, product, exact quotient, double/half, ±1, off-by-one from the answer
  (cost 1); add-all, multiply-all, three-operand combinations, square, ×10, ÷10,
  count of numbers (cost 2). A match is dropped as coincidental when operations of
  that cost reach more than 60% of the integers between the smallest and largest
  option. `answer_op` is recorded only when exactly one operation type reaches the
  correct value at the lowest cost.
- Results and the 30-item spot check: [docs/EXPERIMENTS.md](../../docs/EXPERIMENTS.md#error-signatures-t-108).

**On the board:** `copilot/misconceptions.py` loads the file if present (2 MB cap,
shape validated, malformed file stops the app). After a wrong answer with a
signature, `student_app/server.py` appends one or two sentences in the problem's
language ("That number could come from multiplying 3 by 4. Re-read what the
question asks.") to the response `message`, returns `misconception: {op, answer_op}`,
stores the op in `sessions.misconception` and `learning_events.misconception`, and
starts the next hint at the method rung. BKT is unchanged. A message that would show
the correct value or letter is replaced by a generic one. No file means today's
behaviour. Deployment of `data/ml/*.json` is T-110.
