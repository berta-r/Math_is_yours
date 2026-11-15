"""Tolerant A–E option parser of prepare_m3kang.py (python3 -m unittest discover -s laptop -p 'test_prepare*.py')."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prepare_m3kang import parse_options  # noqa: E402


def boxes(texts):
    """One OCR row, boxes left to right."""
    return [([[10 * i, 0], [10 * i + 8, 0], [10 * i + 8, 5], [10 * i, 5]], t, 0.9) for i, t in enumerate(texts)]


class ParseOptionsTests(unittest.TestCase):
    def check(self, texts, want):
        self.assertEqual(parse_options(boxes(texts)), want, texts)

    def test_clean_sequence(self):
        self.check(['the text ends here', 'A) 12', 'B) 15', 'C) 18', 'D) 21', 'E) 24'],
                   {'A': '12', 'B': '15', 'C': '18', 'D': '21', 'E': '24'})

    def test_one_marker_lost_is_recovered_from_the_order(self):
        self.check(['A)24cm²2', 'B)27cm2', '30 cm2', 'D)32cm²2', 'E)36cm²'],
                   {'A': '24cm²', 'B': '27cm2', 'C': '30 cm2', 'D': '32cm²', 'E': '36cm²'})
        self.check(['A)', '380 cm', 'B)400cm', '420 cm', 'D)', '440cm', 'E)', '01680cm'],
                   {'A': '380 cm', 'B': '400cm', 'C': '420 cm', 'D': '440cm', 'E': '01680cm'})

    def test_lost_a_marker_starts_before_b(self):
        self.check(['99 m2', 'B)96m²2', '91m2', 'D)84m2', 'E)51m²2'],
                   {'A': '99 m2', 'B': '96m²', 'C': '91m2', 'D': '84m2', 'E': '51m²'})

    def test_markers_split_from_values(self):
        self.check(['A', '80', 'B) 65', '73', 'D', '86', 'E)', '16'],
                   {'A': '80', 'B': '65', 'C': '73', 'D': '86', 'E': '16'})

    def test_missing_values_or_pictures_give_nothing(self):
        self.check(['A)', '40', 'B)25', 'C', '10', 'D', 'E)'], {})
        self.check(['12', '11', 'A)3', 'B)1', 'D)8', 'E)9'], {})
        self.check(['A)', 'B)', 'C)', 'D)', 'E)'], {})
        self.check(['A) 1', 'B) 2', 'C) 3', 'D) 4', 'E) 5', '7'], {})
        self.check(['ADA is here', 'A) 1', 'B) 2', 'C) 3', 'D) 4', 'E) 5', 'a long trailing sentence about something'], {})


if __name__ == '__main__':
    unittest.main()
