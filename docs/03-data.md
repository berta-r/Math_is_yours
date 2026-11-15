# 03 · Data

> Read this before you touch M3Kang, the JSONL files, OCR, the splits or the index. See also [../data/README.md](../data/README.md) and [../README.md#step-9-prepare-m3kang-on-your-laptop](../README.md#step-9-prepare-m3kang-on-your-laptop).

## M3Kang

- Hugging Face: `qualcomm/M3Kang`. Paper: Torres-Camps et al., 2026, arXiv:2601.16218.
- **License: research use only. Never commit or publish the data, the images or `index.db`.**
- Kangaroo Math Competition problems, the same problem translated into many languages (same `id`).
- Splits: `high_quality` (4 parquet shards) and `standard` (10 shards). Shard 0 of `high_quality` has eng, cat, fra, esp, ind, deu, swh, vie, tur, zho, kor, arb, jpn, lit.
- **Each problem's options A–E are only in the image.** The text has the question but not the options, which is why we run OCR.
- **There's no topic field.** If we need topics (for error analysis or a trainer), we must create them: cluster the embeddings, use keywords, or label by hand.
- The answer distribution isn't uniform: D is the most common (24.6% in `high_quality`).

## Preparation pipeline (laptop)

`laptop/prepare_m3kang.py`:

1. Downloads the requested parquet shards from Hugging Face (`--split`, `--shards`) or reads local ones (`--parquet`).
2. Keeps the requested languages (`--languages`, default `eng,cat`).
3. Runs OCR (RapidOCR, offline) on each image to read the options A–E. The results are cached, so re-runs are fast.
4. Splits train and validation **by problem ID**, so a problem and its translations never end up on both sides (`--val-fraction 0.15`, or `--val-years 2023,2024` to hold out whole years).
5. Writes `data/train.jsonl` and `data/val.jsonl` (no images). With `--save-images`, it also writes `data/images/<id>_<lang>.png`.

Other flags: `--out`, `--no-ocr`, `--limit N`. Requirements: `pip install -r laptop/requirements.txt` (`huggingface_hub`, `pyarrow`, `rapidocr_onnxruntime`), Python ≥ 3.10.

Then copy the files to the board (`scp` or `adb push`). See [05-commands.md](05-commands.md).

## Format (one JSON object per line)

```json
{"id": "lvl-0_2015_13", "language": "eng", "level": 0, "year": 2015, "text_only": true,
 "text": "13. For 3 days, the cat Joy has been catching mice. ...",
 "options": {"A": "12", "B": "15", "C": "18", "D": "20", "E": "24"}, "label": "C"}
```

| Field | Meaning |
| --- | --- |
| `id` | Problem ID: level, year and number. Shared by every translation |
| `language` | M3Kang language code (`eng`, `cat`, `esp`, …) |
| `level` | Difficulty or age level (0 = youngest) |
| `year` | Competition year |
| `text_only` | Whether the problem can be solved without the picture |
| `text` | The question, without the options |
| `options` | `{"A".."E": str}` read by OCR, or `{}` if OCR couldn't read 5 text options (for example when the options are pictures) |
| `label` | Correct letter (missing in the hidden test set) |

`predict.py` needs only `id` and `text`. It uses `options` and `language` when they're there.

## Known OCR problems

See [../README.md#93-what-the-ocr-gets-wrong](../README.md#93-what-the-ocr-gets-wrong). In short: picture options give `{}`, and math symbols and fractions can be misread. `eval.py` reports accuracy **with and without options**, so we can see the cost. Improving the OCR (for example cropping the bottom of the image) is a possible task.

## Files in `data/`

| File | Committed? | Made by |
| --- | --- | --- |
| `sample_problems.jsonl` | ✅ yes (5 made-up problems, for smoke tests) | organizers |
| `README.md` | ✅ yes | organizers |
| `train.jsonl`, `val.jsonl` | ❌ never | `prepare_m3kang.py` |
| `images/*.png` | ❌ never | `prepare_m3kang.py --save-images` |
| `index.db` | ❌ never (it holds the problem text) | `build_index.py` |

Reference size from the organizers: English-only validation set of about 281 problems, retrieval index of about 911 problems (`--only-with-options`), 1,747 English images (71 MB).

## Our dataset choices

Starter UI dataset prepared on 2026-11-14: `high_quality` shard 0, requested `eng,cat`, limited to the first 60 matching rows. Source order yielded **English only**: 52 training and 8 validation records, split by the preparation script's deterministic problem-ID hash (15% target). All 60 original images are saved; 16 records are marked `text_only`. OCR was deliberately skipped, so no parsed options are available: students read A–E from the original images. This is a UI starter subset, not the final evaluation dataset. Cache, JSONL and images are ignored by Git.

Subsequent enrichment with `laptop/read_options.py` adds full OCR text choices for **34/52 training** and **5/8 validation** problems. Full picture-choice previews are available for another **10/52 training** and **1/8 validation** problems. Eight training and two validation problems still require the original image. OCR text/crops are automatic, not fully reviewed. The ordered ID/language/label checksum remained unchanged across enrichment; official answer keys were preserved. No solver accuracy gain is claimed.
