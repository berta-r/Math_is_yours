"""Read the value of an option ("12 cm", "3/4", "1,5", "25%") and match a computed result to A-E.

Shared by the near-duplicate step (copy the *value* of a known answer, because the
letters can be shuffled between versions of a problem) and the program-of-thought
step (match what Python computed to one of the options).
"""
import re
from fractions import Fraction

LETTERS = "ABCDE"
_NUMBER = re.compile(r"[-−+]?\d+(?:[.,]\d+)?")
_FRACTION = re.compile(r"^\s*([-−+]?\d+)\s*/\s*(\d+)\s*$")
_UNITS = re.compile(r"\s*(cm²|m²|km²|cm³|m³|cm|mm|km|kg|g|m|°|%|€|\$|h|min|s)\s*$")


def normalize_text(s):
    """Lower-case, no spaces, ASCII-ish minus sign: for comparing options as strings."""
    return re.sub(r"\s+", "", str(s)).replace("−", "-").lower()


def parse_number(s):
    """Return the numeric value of an option as a Fraction, or None.

    "12" -> 12, "1,5" -> 3/2, "3/4" -> 3/4, "12 cm" -> 12, "25%" -> 25, "−3" -> -3.
    Text with two separate numbers ("2 and 3", "1:2") is not a single value: None.
    """
    if s is None:
        return None
    text = str(s).strip().replace("−", "-")
    text = _UNITS.sub("", text)
    m = _FRACTION.match(text)
    if m and int(m.group(2)) != 0:
        return Fraction(int(m.group(1)), int(m.group(2)))
    numbers = _NUMBER.findall(text)
    if len(numbers) != 1:
        return None
    rest = _NUMBER.sub("", text).strip()
    if rest and not re.fullmatch(r"[a-zA-Z²³°%€$\s.]*", rest):
        return None  # "2^3", "x=4", "3 and 4" are not plain values
    try:
        return Fraction(numbers[0].replace(",", "."))
    except (ValueError, ZeroDivisionError):
        return None


def to_fraction(value):
    """Turn a Python result (int, float, Fraction, bool, numeric str) into a Fraction, or None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, Fraction)):
        return Fraction(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return Fraction(value).limit_denominator(10 ** 6)
    if isinstance(value, str):
        return parse_number(value)
    return None


def numeric_options(options):
    """{"A": Fraction, ...} for the options that are plain values; {} when any is missing."""
    if not options or len(options) != 5:
        return {}
    parsed = {letter: parse_number(options.get(letter)) for letter in LETTERS}
    if any(v is None for v in parsed.values()):
        return {}
    return parsed


def match_option(value, options, tolerance=Fraction(1, 1000)):
    """Return the single letter whose option equals value, or None.

    Numeric values match numerically (so "1,5" and 1.5 agree); other values match
    as normalised text. If zero or several options match, None.
    """
    if not options:
        return None
    target = to_fraction(value)
    hits = []
    for letter in LETTERS:
        option = options.get(letter)
        if option is None:
            continue
        if target is not None:
            candidate = parse_number(option)
            if candidate is not None:
                scale = max(abs(target), Fraction(1))
                if abs(candidate - target) <= tolerance * scale:
                    hits.append(letter)
                continue
        if normalize_text(option) == normalize_text(value):
            hits.append(letter)
    return hits[0] if len(hits) == 1 else None
