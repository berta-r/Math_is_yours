"""Answer from a near-duplicate training problem, without asking the model.

Kangaroo reuses problems: the same text appears at two levels of the same year, or
again a few years later, sometimes with the options in a different order. When the
most similar training problem is almost identical, we copy its *correct value* and
look that value up among the new problem's options. The letter is only copied
directly when the texts (with options) are practically the same and the new
problem's options could not be read.

Costs one embedding call (well under a second). Needs data/index.db.
"""
from .config import CONFIG
from .values import match_option

# Cosine similarity of the full text (problem + options) needed to trust a neighbour
THRESHOLD = float(CONFIG.get("DEDUP_THRESHOLD", "0.92"))
# Above this the texts are the same problem: the letter can be copied when we have no options
LETTER_THRESHOLD = float(CONFIG.get("DEDUP_LETTER_THRESHOLD", "0.98"))


def find_duplicate(problem, index, exclude_id=None, threshold=THRESHOLD):
    """Return (letter, detail) when a near-duplicate settles the answer, else (None, detail)."""
    hits = index.search(problem, k=1, exclude_id=exclude_id)
    if not hits:
        return None, "no-neighbour"
    score, neighbour = hits[0]
    detail = f"{neighbour['id']}:{score:.3f}"
    if score < threshold:
        return None, detail
    label = neighbour.get("label")
    if label not in "ABCDE" or not label:
        return None, detail + ":no-label"
    value = (neighbour.get("options") or {}).get(label)
    if value is not None and problem.get("options"):
        letter = match_option(value, problem["options"])
        if letter:
            return letter, detail + f":value={value}"
        return None, detail + f":value={value}:not-in-options"
    if score >= LETTER_THRESHOLD and not problem.get("options"):
        return label, detail + ":letter-copied"
    return None, detail + ":no-options"
