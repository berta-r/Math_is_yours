"""Re-read the A–E options of prepared rows whose options are empty (laptop only).

`prepare_m3kang.py` left the options empty when the OCR lost a marker letter. This
runs RapidOCR again on data/images/<id>_<lang>.png for every such row of
data/train.jsonl and data/val.jsonl, parses the boxes with the tolerant parser
of prepare_m3kang.py, and rewrites the JSONL files in place (atomic). The raw OCR
boxes are cached in data/.ocr_boxes.jsonl so a parser change can be re-applied
with --reparse without running the OCR again.

    .venv/bin/python laptop/fill_options.py               # OCR the rows with empty options
    .venv/bin/python laptop/fill_options.py --reparse     # only re-run the parser on cached boxes
    .venv/bin/python laptop/fill_options.py --limit 20    # try a few first
    .venv/bin/python laptop/fill_options.py --strips      # also OCR the upscaled bottom strip of the image

--strips: when the whole-image OCR gives nothing, crop the bottom 30% (then 45%,
then 30% at x3) of the image, upscale it x2 and OCR again; small option digits
that the full-page pass merged or lost are usually read there. Filled rows get
options_source "ocr-strip". Strip boxes are cached under "<key>#strip:<frac>:<scale>".
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prepare_m3kang import parse_options  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_rows(path):
    with open(path, encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_rows(path, rows):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
    os.replace(tmp, path)


def empty(row):
    return not any(v for v in (row.get('options') or {}).values())


STRIPS = ((0.3, 2), (0.45, 2), (0.3, 3))


def strip_image(path, frac, scale):
    """The bottom `frac` of the image, upscaled by `scale`, as an RGB array for the OCR."""
    from PIL import Image
    import numpy as np
    with Image.open(path) as im:
        im = im.convert('RGB')
        w, h = im.size
        crop = im.crop((0, int(h * (1 - frac)), w, h)).resize((int(w * scale), max(1, int(h * frac * scale))), Image.LANCZOS)
        return np.array(crop)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data', default=os.path.join(ROOT, 'data'))
    parser.add_argument('--files', nargs='+', default=['train.jsonl', 'val.jsonl'])
    parser.add_argument('--reparse', action='store_true', help='use cached boxes only; no OCR')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--dry-run', action='store_true', help='report, do not write the JSONL files')
    parser.add_argument('--strips', action='store_true', help='also OCR the upscaled bottom strip when the full image gives nothing')
    args = parser.parse_args(argv)

    boxes_path = os.path.join(args.data, '.ocr_boxes.jsonl')
    cache = {}
    if os.path.exists(boxes_path):
        with open(boxes_path, encoding='utf-8') as stream:
            for line in stream:
                item = json.loads(line)
                cache[item['key']] = item['boxes']
    ocr = None
    if not args.reparse:
        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()
    cache_file = open(boxes_path, 'a', encoding='utf-8')
    report = {'files': {}, 'seconds': 0.0}
    started = time.time()
    done = 0
    for name in args.files:
        path = os.path.join(args.data, name)
        if not os.path.exists(path):
            continue
        rows = load_rows(path)
        stats = {'rows': len(rows), 'empty_before': sum(empty(r) for r in rows), 'filled': 0, 'filled_strip': 0, 'still_empty': 0, 'no_image': 0}
        for row in rows:
            if not empty(row):
                continue
            if args.limit and done >= args.limit:
                break
            key = f"{row['id']}|{row['language']}"
            image = os.path.join(args.data, 'images', f"{row['id']}_{row['language']}.png")
            boxes = cache.get(key)
            if boxes is None:
                if ocr is None or not os.path.exists(image):
                    stats['no_image'] += not os.path.exists(image)
                    continue
                result, _ = ocr(image)
                boxes = [[box, text, float(score)] for box, text, score in (result or [])]
                cache[key] = boxes
                cache_file.write(json.dumps({'key': key, 'boxes': boxes}, ensure_ascii=False) + '\n')
                cache_file.flush()
            done += 1
            options = parse_options(boxes)
            source = 'ocr-refill'
            if not options and args.strips and os.path.exists(image):
                for frac, scale in STRIPS:
                    skey = f'{key}#strip:{frac}:{scale}'
                    sboxes = cache.get(skey)
                    if sboxes is None:
                        if ocr is None:
                            continue
                        result, _ = ocr(strip_image(image, frac, scale))
                        sboxes = [[box, text, float(score)] for box, text, score in (result or [])]
                        cache[skey] = sboxes
                        cache_file.write(json.dumps({'key': skey, 'boxes': sboxes}, ensure_ascii=False) + '\n')
                        cache_file.flush()
                    options = parse_options(sboxes)
                    if options:
                        source = 'ocr-strip'
                        break
            if options:
                row['options'] = options
                row['options_source'] = source
                stats['filled'] += 1
                stats['filled_strip'] += source == 'ocr-strip'
            else:
                stats['still_empty'] += 1
            if done % 50 == 0:
                rate = (time.time() - started) / done
                print(f'  {done} rows, {rate:.2f} s/row, filled {stats["filled"]}', file=sys.stderr, flush=True)
        if not args.dry_run:
            write_rows(path, rows)
        stats['empty_after'] = sum(empty(r) for r in rows)
        report['files'][name] = stats
    cache_file.close()
    report['seconds'] = round(time.time() - started, 1)
    print(json.dumps(report, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
