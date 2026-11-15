"""Tests for the pure parts of copilot/compute.py. Run with: python3 -m unittest tests.test_compute

No server is contacted: every test either uses functions that never call the model
or sets the solver's state so that answer() returns before it would.
"""

import os
import sys
import unittest
from fractions import Fraction
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from copilot import compute  # noqa: E402

OPTIONS = {"A": "5", "B": "9", "C": "10", "D": "12", "E": "14"}


def _no_server(*_args, **_kwargs):
    raise AssertionError("the test contacted the server")


class TestCleaning(unittest.TestCase):
    def test_clean_text_strips_problem_number(self):
        self.assertEqual(compute.clean_text("12. How many apples?"), "How many apples?")
        self.assertEqual(compute.clean_text("3) How many apples?"), "How many apples?")
        self.assertEqual(compute.clean_text("How many apples?"), "How many apples?")

    def test_clean_options(self):
        self.assertEqual(compute.clean_options({"A": "O", "B": " 1 ", "D": "o"}), {"A": "0", "B": "1", "D": "0"})
        self.assertEqual(compute.clean_options(None), {})


class TestMatchValue(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(compute.match_value(12, {"A": "10 cm", "B": "12 cm", "C": "14 cm"}), "B")
        self.assertEqual(compute.match_value(1.5, {"A": "1", "B": "1,5", "C": "2"}), "B")
        self.assertEqual(compute.match_value(Fraction(1, 9), {"A": "1/12", "B": "1/9", "C": "1/6"}), "B")

    def test_words_loosely(self):
        self.assertEqual(compute.match_value("Lluc", {"A": "Marc", "B": "LIuC", "C": "Anna"}), "B")

    def test_ambiguous_or_missing(self):
        self.assertIsNone(compute.match_value(3, {"A": "3", "B": "3 cm", "C": "4"}))
        self.assertIsNone(compute.match_value(7, OPTIONS))


class TestEvaluate(unittest.TestCase):
    def test_computed(self):
        letter, kind, _note = compute._evaluate("3 * 4 - 2", OPTIONS)
        self.assertEqual((letter, kind), ("C", "computed"))

    def test_direct_number(self):
        letter, kind, _note = compute._evaluate("10", OPTIONS)
        self.assertEqual((letter, kind), ("C", "direct"))

    def test_direct_word(self):
        letter, kind, _note = compute._evaluate('"Marc"', {"A": "Anna", "B": "Marc", "C": "Pau"})
        self.assertEqual((letter, kind), ("B", "direct"))

    def test_nomatch(self):
        letter, kind, _note = compute._evaluate("3 * 4 + 1", OPTIONS)
        self.assertEqual((letter, kind), (None, "nomatch"))

    def test_invalid(self):
        letter, kind, _note = compute._evaluate("__import__('os').system('ls')", OPTIONS)
        self.assertEqual((letter, kind), (None, "invalid"))
        letter, kind, _note = compute._evaluate("", OPTIONS)
        self.assertEqual((letter, kind), (None, "invalid"))

    def test_is_literal(self):
        self.assertTrue(compute._is_literal("10"))
        self.assertTrue(compute._is_literal("-3"))
        self.assertTrue(compute._is_literal('"Marc"'))
        self.assertFalse(compute._is_literal("3 * 4"))
        self.assertFalse(compute._is_literal("sum(range(5))"))
        self.assertFalse(compute._is_literal("not ( valid"))


class StateTestCase(unittest.TestCase):
    """Saves and restores the module state that these tests change."""

    def setUp(self):
        self._saved = {key: (dict(value) if isinstance(value, dict) else list(value) if isinstance(value, list)
                             else value) for key, value in compute._state.items()}
        compute._state["answered"] = {letter: 0 for letter in compute.LETTERS}
        compute._state["guessed"] = {letter: 0 for letter in compute.LETTERS}

    def tearDown(self):
        compute._state.clear()
        compute._state.update(self._saved)


class TestGuess(StateTestCase):
    def test_balance_is_deterministic(self):
        with mock.patch.object(compute, "GUESS", "balance"):
            problem = {"id": "kangaroo-2026-07"}
            first = compute._guess(problem, OPTIONS)
            self.assertEqual(compute._guess(problem, OPTIONS), first)
            self.assertIn(first, compute.LETTERS)

    def test_balance_prefers_least_answered(self):
        with mock.patch.object(compute, "GUESS", "balance"):
            compute._state["answered"] = {"A": 3, "B": 2, "C": 0, "D": 4, "E": 1}
            for n in range(10):
                self.assertEqual(compute._guess({"id": f"p{n}"}, OPTIONS), "C")
            compute._state["answered"] = {"A": 1, "B": 1, "C": 1, "D": 1, "E": 1}
            compute._state["guessed"] = {"A": 2, "B": 1, "C": 2, "D": 0, "E": 1}
            self.assertEqual(compute._guess({"id": "x"}, OPTIONS), "D")

    def test_fixed_returns_fallback(self):
        with mock.patch.object(compute, "GUESS", "fixed"):
            self.assertEqual(compute._guess({"id": "x"}, OPTIONS), compute.CONFIG["FALLBACK_ANSWER"])


class TestAnswer(StateTestCase):
    def test_unavailable(self):
        compute._state["warm"] = True
        compute._state["usable"] = False
        with mock.patch.object(compute, "post", _no_server):
            with self.assertRaises(compute.Unavailable):
                compute.answer({"id": "x", "text": "What is 2 + 3?", "options": OPTIONS})

    def test_figure_problem_is_guessed_without_the_server(self):
        compute._state.update({"warm": True, "usable": True, "kinds": ["informed"]})
        problem = {"id": "x", "text": "Look at the picture.", "options": OPTIONS, "text_only": False}
        with mock.patch.object(compute, "post", _no_server):
            letter, timings, info = compute.answer(problem)
        self.assertIn(letter, compute.LETTERS)
        self.assertEqual(info["method"], "guess")
        self.assertEqual(timings["prompt_n"], 0)
        self.assertEqual(compute._state["guessed"][letter], 1)


if __name__ == "__main__":
    unittest.main()
