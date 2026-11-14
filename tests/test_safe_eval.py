"""Tests for copilot/safe_eval.py. Run with: python3 tests/test_safe_eval.py"""

import os
import sys
import time
import unittest
from fractions import Fraction

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from copilot.safe_eval import SafeEvalError, extract_expression, safe_eval  # noqa: E402


class TestSafeEvalValues(unittest.TestCase):
    def test_examples(self):
        self.assertEqual(safe_eval("sum(1 for n in range(10, 100) if n // 10 + n % 10 == 5)"), 5)
        self.assertEqual(safe_eval("math.comb(5, 2) * 2"), 20)

    def test_fraction(self):
        self.assertEqual(safe_eval("Fraction(1,3)+Fraction(1,6)"), Fraction(1, 2))
        self.assertEqual(safe_eval("fractions.Fraction(2, 4)"), Fraction(1, 2))

    def test_subscript_and_slices(self):
        self.assertEqual(safe_eval("sorted([3,1,2])[1]"), 2)
        self.assertEqual(safe_eval("[1, 2, 3, 4][::-1][:2]"), [4, 3])
        self.assertEqual(safe_eval("'abc'[1]"), "b")

    def test_misc(self):
        self.assertEqual(safe_eval("len({x % 7 for x in range(100)})"), 7)
        self.assertEqual(safe_eval("sum(a*b for a, b in zip([1,2],[3,4]))"), 11)
        self.assertEqual(safe_eval("len(list(itertools.permutations(range(5), 2)))"), 20)
        self.assertEqual(safe_eval("sum(1 for t in itertools.product(range(2), repeat=3) if sum(t) == 2)"), 3)
        self.assertEqual(safe_eval("math.factorial(5) if 2 > 1 else 0"), 120)
        self.assertEqual(safe_eval("2**100 % 7"), pow(2, 100, 7))
        self.assertEqual(safe_eval("pow(2, 2026, 10)"), pow(2, 2026, 10))
        self.assertEqual(safe_eval("math.prod(range(1, 6))"), 120)
        self.assertEqual(safe_eval("not (1 < 2 <= 3)"), False)
        self.assertEqual(safe_eval("divmod(17, 5)"), (3, 2))
        self.assertAlmostEqual(safe_eval("math.sqrt(2) * math.pi"), 4.442882938158366)
        self.assertEqual(safe_eval("[n for n in range(5) if n % 2 == 0]"), [0, 2, 4])
        self.assertEqual(safe_eval("range(3)"), [0, 1, 2])

    def test_range_cap_inclusive(self):
        self.assertEqual(safe_eval("sum(1 for _ in range(10**6))"), 10 ** 6)


class TestSafeEvalRejections(unittest.TestCase):
    def assertRejected(self, expr, contains=None):
        with self.assertRaises(SafeEvalError) as cm:
            safe_eval(expr)
        if contains:
            self.assertIn(contains, str(cm.exception))
        return str(cm.exception)

    def test_forbidden(self):
        for expr in [
            "__import__('os')",
            "open('x')",
            "(lambda: 1)()",
            "[].__class__",
            '"a".upper()',
            "math.__dict__",
            "math.os",
            "getattr(math, 'gcd')",
            "eval('1')",
            "f'{1}'",
            "{1: 2}",
            "[x for x in ().__class__.__bases__]",
            "sorted([1], key=lambda x: x)",
            "max(*[1, 2])",
            "b'abc'",
            "type(1)",
            "x",
            "[sum for sum in range(3)]",
            "'%*d' % (10**6, 1)",
        ]:
            with self.subTest(expr=expr):
                self.assertRejected(expr)

    def test_walrus_and_statements(self):
        self.assertRejected("x := 1")         # syntax error at top level in eval mode
        self.assertRejected("(x := 1)", "forbidden")
        self.assertRejected("import os", "syntax error")
        self.assertRejected("x = 1", "syntax error")

    def test_size_limits(self):
        self.assertRejected("range(10**9)", "range too big")
        self.assertRejected("10**10**5", "too big")
        self.assertRejected("pow(3, 10**6)", "too big")
        self.assertRejected("math.factorial(501)", "factorial")
        self.assertRejected("[0] * 10**9", "too big")
        self.assertRejected("'ab' * 10**9", "too big")
        self.assertRejected("list(itertools.product(range(10), repeat=10))", "too big")
        self.assertRejected("math.prod(range(1, 10**5))", "too big")

    def test_runtime_errors(self):
        self.assertRejected("1/0", "runtime error")
        self.assertRejected("int('x')", "runtime error")
        self.assertRejected("", "syntax error")
        self.assertRejected("2 +", "syntax error")


class TestTimeout(unittest.TestCase):
    def test_timeout(self):
        start = time.time()
        try:
            safe_eval("sum(i*i for i in range(10**6))", timeout=0.001)
        except SafeEvalError as exc:
            self.assertEqual(str(exc), "timeout")
        else:
            self.skipTest("expression finished in under 1 ms on this machine")
        self.assertLess(time.time() - start, 1.0)

    def test_nested_loop_timeout(self):
        with self.assertRaises(SafeEvalError) as cm:
            safe_eval("sum(1 for a in range(10**6) for b in range(10**6))", timeout=0.2)
        self.assertEqual(str(cm.exception), "timeout")

    def test_timer_disarmed_after_success(self):
        safe_eval("1+1", timeout=0.05)
        time.sleep(0.1)  # would raise if the alarm were still armed


class TestExtractExpression(unittest.TestCase):
    def test_cases(self):
        cases = {
            "```python\n2+3\n```": "2+3",
            "```\n2+3\n```": "2+3",
            ">>> 2+3": "2+3",
            "Answer: 2+3 # sum": "2+3",
            "2+3.": "2+3",
            "2+3;": "2+3",
            "\n\n  = 2+3\nmore text": "2+3",
            "`2+3`": "2+3",
            "len('a#b')  # comment": "len('a#b')",
            "Here it is:\n```py\nmath.comb(5, 2) * 2\n```\nDone.": "math.comb(5, 2) * 2",
            "": "",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(extract_expression(raw), expected)

    def test_roundtrip(self):
        self.assertEqual(safe_eval(extract_expression("Answer: math.comb(5, 2) * 2.")), 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
