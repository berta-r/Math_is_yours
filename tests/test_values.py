"""python3 tests/test_values.py: option values and matching, no servers needed."""
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from copilot.values import match_option, numeric_options, parse_number  # noqa: E402

F = Fraction
assert parse_number("12") == 12
assert parse_number("1,5") == F(3, 2)
assert parse_number("1.5") == F(3, 2)
assert parse_number("3/4") == F(3, 4)
assert parse_number("12 cm") == 12
assert parse_number("81 cm²") == 81
assert parse_number("25%") == 25
assert parse_number("−3") == -3
assert parse_number("2 and 3") is None
assert parse_number("1:2") is None
assert parse_number("2^3") is None
assert parse_number("") is None
assert parse_number(None) is None

opts = {"A": "36 cm²", "B": "72 cm²", "C": "81 cm²", "D": "144 cm²", "E": "324 cm²"}
assert numeric_options(opts) == {"A": 36, "B": 72, "C": 81, "D": 144, "E": 324}
assert numeric_options({"A": "x", "B": "1", "C": "2", "D": "3", "E": "4"}) == {}
assert numeric_options({"A": "1"}) == {}
assert numeric_options({}) == {}

assert match_option(81, opts) == "C"
assert match_option(81.0, opts) == "C"
assert match_option(F(81), opts) == "C"
assert match_option("81 cm²", opts) == "C"
assert match_option(80, opts) is None
assert match_option(81.00000001, opts) == "C"
assert match_option(True, opts) is None
assert match_option(None, opts) is None
assert match_option(5, {}) is None
assert match_option(1.5, {"A": "1,5", "B": "2", "C": "3", "D": "4", "E": "5"}) == "A"
assert match_option(F(1, 2), {"A": "1/2", "B": "2", "C": "3", "D": "4", "E": "5"}) == "A"
assert match_option("yes", {"A": "Yes", "B": "No", "C": "1", "D": "2", "E": "3"}) == "A"
assert match_option(2, {"A": "2", "B": "2", "C": "3", "D": "4", "E": "5"}) is None  # ambiguous
print("test_values: ok")
