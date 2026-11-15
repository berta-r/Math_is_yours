"""Read prepared M3Kang JSONL and resolve only local problem images."""
import json
from pathlib import Path
from urllib.parse import quote


class Catalog:
    def __init__(self, inputs, images):
        self.problems = {}
        self.images = Path(images).resolve()
        self.sources = [str(Path(path).name) for path in inputs]
        for path in inputs:
            with Path(path).open(encoding="utf-8-sig") as stream:
                for number, line in enumerate(stream, 1):
                    if not line.strip():
                        continue
                    try:
                        p = json.loads(line)
                        if not isinstance(p, dict) or not isinstance(p.get("id"), str) or not p["id"]:
                            raise ValueError("expected a nonempty string id")
                        p["language"] = p.get("language") or "und"
                        if not isinstance(p["language"], str):
                            raise ValueError("language must be a string")
                        p["text"] = p.get("text") or ""
                        if not isinstance(p["text"], str):
                            raise ValueError("text must be a string")
                        options = p.get("options") or {}
                        if not isinstance(options, dict):
                            raise ValueError("options must be an object")
                        p["options"] = {k: str(v) for k, v in options.items() if k in "ABCDE" and len(k) == 1 and v is not None}
                        key = p["id"] + "|" + p["language"]
                        if key in self.problems:
                            raise ValueError("duplicate problem id and language")
                        self.problems[key] = p
                    except (ValueError, TypeError) as error:
                        raise ValueError(f"{path}:{number}: {error}") from error
        if not self.problems:
            raise ValueError("The selected JSONL files contain no problems")

    def resolve(self, key):
        if key in self.problems:
            return key
        matches = [k for k, p in self.problems.items() if p["id"] == key]
        if len(matches) == 1:
            return matches[0]
        raise ValueError("Choose a problem and language from the list")

    def image(self, key, option=None):
        p = self.problems[key]
        if option is not None and (option not in list('ABCDE') or option not in p.get('option_images', [])):
            return None
        suffix = f'_option_{option}' if option else ''
        candidate = (self.images / f"{p['id']}_{p['language']}{suffix}.png").resolve()
        if not candidate.is_relative_to(self.images) or not candidate.is_file():
            return None
        return candidate

    def public(self, key):
        p = self.problems[key]
        has_image = self.image(key) is not None
        return {"key": key, "id": p["id"], "language": p["language"],
                "option_images": {letter: '/api/image?key=' + quote(key, safe='') + '&option=' + letter for letter in 'ABCDE' if self.image(key, letter)},
                "text": p["text"], "options": p["options"], "options_source": p.get("options_source"), "level": p.get("level"),
                "image_url": "/api/image?key=" + quote(key, safe="") if has_image else None,
                "requires_image": p.get("text_only") is False,
                "gradable": p.get("label") in list("ABCDE"),
                "format": "text + image" if has_image and p["text"] else "image" if has_image else "text"}


def default_inputs(root):
    # Teaching defaults to train: leave validation untouched for official evaluation.
    train = Path(root) / "data/train.jsonl"
    return [train if train.is_file() else Path(root) / "data/sample_problems.jsonl"]
