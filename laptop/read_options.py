"""Add OCR answer text to already-prepared local JSONL (laptop only).

Usage: .venv/Scripts/python.exe laptop/read_options.py --input data/train.jsonl data/val.jsonl
No download or model-server calls. Official labels are preserved unchanged.
"""
import argparse
import json
import re
from statistics import median
from pathlib import Path

from prepare_m3kang import parse_options


def save_choice_images(image, boxes, output, stem):
    """Crop previews only when OCR locates an unambiguous full A–E sequence.

    These are layout-based previews; preserve the original for comparison.
    """
    import cv2
    import numpy as np
    markers = {}
    for box, text, score in boxes:
        match = re.fullmatch(r'\s*([A-E])\s*[)）.:]?\s*', text, re.IGNORECASE)
        if not match or score < .65:
            continue
        letter = match[1].upper()
        if letter in markers:
            return []
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        markers[letter] = (min(xs), min(ys), max(ys) - min(ys))
    if set(markers) != set('ABCDE'):
        return []
    frame = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return []
    height, width = frame.shape[:2]
    rows = []
    for letter, (x, y, h) in sorted(markers.items(), key=lambda item: item[1][1]):
        if not rows or abs(y - rows[-1][0][1][1]) > h:
            rows.append([])
        rows[-1].append((letter, (x, y, h)))
    ordered = [letter for row in rows for letter, _ in sorted(row, key=lambda item: item[1][0])]
    if ordered != list('ABCDE'):
        return []
    for row_index, row in enumerate(rows):
        row.sort(key=lambda item: item[1][0])
        gaps = [row[i + 1][1][0] - row[i][1][0] for i in range(len(row) - 1)]
        spacing = median(gaps) if gaps else width - row[0][1][0]
        top = max(0, int(min(y - 1.5*h for _, (_, y, h) in row)))
        bottom = height if row_index + 1 == len(rows) else max(top + 1, int(min(y - 1.5*h for _, (_, y, h) in rows[row_index + 1])))
        for index, (letter, (x, y, h)) in enumerate(row):
            left = max(0, int(x - 4))
            right = min(width, int(row[index+1][1][0] - 8 if index + 1 < len(row) else x + spacing - 8))
            if right <= left:
                return []
            if not cv2.imwrite(str(output / f'{stem}_option_{letter}.png'), frame[top:bottom, left:right]):
                raise OSError('Could not save choice preview')
    return list('ABCDE')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, nargs='+', required=True)
    parser.add_argument('--images', type=Path, default=Path('data/images'))
    args = parser.parse_args()
    from rapidocr_onnxruntime import RapidOCR
    # Avoid oversubscribing the laptop's CPU during a small preparation job.
    ocr = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=2)
    for path in args.input:
        original = path.read_bytes()
        rows = [json.loads(line) for line in original.decode('utf-8-sig').splitlines() if line.strip()]
        extracted = 0
        for index, row in enumerate(rows, 1):
            if len(row.get('options', {})) == 5 or len(row.get('option_images', [])) == 5:
                extracted += int(len(row.get('options', {})) == 5)
                continue
            image = args.images / f"{row['id']}_{row['language']}.png"
            if image.is_file():
                boxes, _ = ocr(image.read_bytes())
                options = parse_options(boxes or [])
                if options:
                    row['options'] = options
                    row['options_source'] = 'ocr'
                    extracted += 1
                else:
                    row['option_images'] = save_choice_images(image.read_bytes(), boxes or [], args.images, f"{row['id']}_{row['language']}")
                    if not row['option_images']:
                        # Retry the lower answer area without the large question diagram.
                        import cv2
                        import numpy as np
                        frame = cv2.imdecode(np.frombuffer(image.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            offset = frame.shape[0] // 2
                            retry, _ = ocr(frame[offset:, :])
                            shifted = [([[x, y + offset] for x, y in box], text, score) for box, text, score in (retry or [])]
                            row['option_images'] = save_choice_images(image.read_bytes(), shifted, args.images, f"{row['id']}_{row['language']}")
            print(f'{path.name}: {index}/{len(rows)}; complete text options: {extracted}', flush=True)
        # Replace only after a complete file has been processed successfully.
        temporary = path.with_suffix('.jsonl.tmp')
        temporary.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')
        if path.read_bytes() != original:
            parser.error(f'{path} changed during OCR. The newer source was kept; enriched output is in {temporary}.')
        temporary.replace(path)
        print(f'{path}: extracted text options for {extracted}/{len(rows)} problems; official answer keys unchanged.', flush=True)


if __name__ == '__main__':
    main()
