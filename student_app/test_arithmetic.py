"""Behavior and safety checks for the deterministic student arithmetic tool."""

import json
import unittest
from unittest import mock

from copilot.arithmetic import respond


class ArithmeticTests(unittest.TestCase):
    def test_standalone_subtraction_has_exact_answer_and_check(self):
        reply = respond("What is 18 − 6?")
        self.assertEqual(reply["source"], "verified_arithmetic")
        self.assertIn("= 12", reply["message"])
        self.assertIn("12 + (6) = 18", reply["message"])
        self.assertEqual(reply["verification"]["result"], "12")
        self.assertIsNone(reply["state"])

    def test_exact_decimals_fractions_precedence_and_negatives(self):
        cases = {"0.1 + 0.2": "0.3", "1/3 + 1/6": "0.5", "2+3*4": "14",
                 "(2+3)*4": "20", "-3 × -4": "12", "1 ÷ 3": "1/3",
                 "-(2+3)": "-5", "0.000000000001 + 0": "0.000000000001"}
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                reply = respond(expression)
                self.assertEqual(reply["verification"]["result"], expected)

    def test_english_and_catalan_operator_words(self):
        for expression in ("What is 18 minus 6?", "Quant és 18 menys 6?",
                           "Calculate 3 multiplied by 4", "Calcula 3 multiplicat per 4",
                           "24 divided by 2", "24 dividit per 2", "10 més 2", "6 times 2"):
            with self.subTest(expression=expression):
                self.assertEqual(respond(expression)["verification"]["result"], "12")
        self.assertIn("Comprovació", respond("Quant és 18 menys 6?", "cat")["message"])

    def test_wrong_claim_does_not_disclose_correct_final_result(self):
        for question in ("I got 13 for 18-6", "18-6=13", "13 = 18-6",
                         "Em surt 13 per a 18 menys 6"):
            with self.subTest(question=question):
                reply = respond(question)
                self.assertFalse(reply["verification"]["claim_correct"])
                self.assertNotIn("12", reply["message"])
                self.assertIn("8 − 6", reply["message"])
                self.assertIsNotNone(reply["state"])

    def test_explicit_correct_equality_checks_only_arithmetic(self):
        reply = respond("18-6=12", guided=True)
        self.assertTrue(reply["verification"]["claim_correct"])
        self.assertIn("not checked the whole solution", reply["message"])
        self.assertIsNone(reply["state"])

    def test_guided_subtraction_followups_survive_json_serialisation(self):
        reply = respond("What is 18-6?", guided=True)
        self.assertNotIn("12", reply["message"])
        self.assertIn("10 + 8", reply["message"])
        self.assertIn("8 − 6", reply["message"])
        state = json.loads(json.dumps(reply["state"]))
        wrong = respond("3", guided=True, previous=state)
        self.assertFalse(wrong["verification"]["claim_correct"])
        self.assertEqual(wrong["state"], state)
        self.assertNotIn("12", wrong["message"])
        second = respond("I got 2", guided=True, previous=state)
        self.assertIn("10 + 2", second["message"])
        self.assertNotIn("12", second["message"])
        final = respond("12", guided=True, previous=second["state"])
        self.assertEqual(final["verification"]["status"], "complete")
        self.assertIn("not checked the whole solution", final["message"])
        self.assertIsNone(final["state"])

    def test_guided_catalan(self):
        first = respond("Quant és 18 menys 6?", "cat", guided=True)
        self.assertIn("Separa 18", first["message"])
        second = respond("Em surt 2", "cat", guided=True, previous=first["state"])
        self.assertIn("10 + 2", second["message"])
        final = respond("12", "cat", guided=True, previous=second["state"])
        self.assertIn("encara no hem comprovat tota la solució", final["message"])

    def test_guided_nested_arithmetic_and_unary(self):
        first = respond("(2+3)*4", guided=True)
        self.assertNotIn("20", first["message"])
        second = respond("5", guided=True, previous=first["state"])
        self.assertIn("(5) × (4)", second["message"])
        final = respond("20", guided=True, previous=second["state"])
        self.assertEqual(final["verification"]["status"], "complete")
        first = respond("-(2+3)", guided=True)
        second = respond("5", guided=True, previous=first["state"])
        self.assertIsNotNone(second["state"])
        final = respond("-5", guided=True, previous=second["state"])
        self.assertEqual(final["verification"]["status"], "complete")

    def test_explicit_step_equality_followup(self):
        first = respond("18-6", guided=True)
        second = respond("8-6=2", guided=True, previous=first["state"])
        self.assertEqual(second["state"]["step"], 1)
        final = respond("10+2=12", guided=True, previous=second["state"])
        self.assertIsNone(final["state"])

    def test_new_request_does_not_get_misread_as_followup(self):
        first = respond("18-6", guided=True)
        new = respond("8*2=16", guided=True, previous=first["state"])
        self.assertEqual(new["verification"]["expression"], "8*2")
        self.assertTrue(new["verification"]["claim_correct"])

    def test_conceptual_and_ambiguous_questions_are_left_to_slm(self):
        for question in ("Why does subtraction work?", "Why is 18-6 useful?",
                         "There are 18 apples and 6 oranges", "What is x + 2?",
                         "How do I subtract 6 from 18?", "2", "",
                         "Why does subtraction work? " * 10):
            with self.subTest(question=question):
                self.assertIsNone(respond(question))

    def test_division_by_zero_and_malformed_arithmetic(self):
        for expression in ("1/0", "1/(2-2)", "4+", "3..4+2", "2**3", "4//2", "2^3", "2%3", "2+3!"):
            with self.subTest(expression=expression):
                reply = respond(expression)
                self.assertEqual(reply["verification"]["status"], "invalid")
                self.assertIsNone(reply["state"])
        self.assertIn("divide by zero", respond("1/0")["message"])

    def test_no_python_execution_or_unsupported_numeric_syntax(self):
        expressions = ("__import__('os').system('echo bad')", "open('secret')", "(1).__class__",
                       "[1, 2][0]", "True+1", "1e100+2", "0xff+1", "sum([1,2])")
        with mock.patch("builtins.eval", side_effect=AssertionError("eval used")), \
                mock.patch("builtins.exec", side_effect=AssertionError("exec used")):
            for expression in expressions:
                with self.subTest(expression=expression):
                    reply = respond(expression)
                    self.assertTrue(reply is None or reply["verification"]["status"] == "invalid")
            self.assertEqual(respond("18-6")["verification"]["result"], "12")

    def test_bounded_length_depth_nodes_and_intermediates(self):
        cases = ("1+" * 90 + "1", "+" * 20 + "1", "1+" * 15 + "1",
                 "1000000000000*1000000000000/1000000000000",
                 "1000000000001-1", "1/1000000000001", "0.0000000000001+1")
        for expression in cases:
            with self.subTest(expression=expression):
                reply = respond(expression)
                self.assertEqual(reply["verification"]["status"], "invalid")

    def test_malformed_previous_state_is_ignored(self):
        states = ([], {"kind": "arithmetic_v1", "expression": "18-6", "step": 100},
                  {"kind": "arithmetic_v1", "expression": "__import__('os')", "step": 0},
                  {"kind": "arithmetic_v1", "expression": "18-6", "step": True},
                  {"kind": "arithmetic_v1", "expression": [], "step": 0})
        for state in states:
            with self.subTest(state=state):
                self.assertIsNone(respond("2", previous=state))
                self.assertEqual(respond("18-6", previous=state)["verification"]["result"], "12")


if __name__ == "__main__":
    unittest.main()
