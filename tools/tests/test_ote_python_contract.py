from __future__ import annotations

import unittest
from pathlib import Path


class OtePythonContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        cls.source = (root / "indicators" / "ote" / "OTE.py").read_text(encoding="utf-8")

    def test_uses_symmetric_confirmed_pivots(self):
        self.assertIn("top_value == h.hhv(length * 2 + 1)", self.source)
        self.assertIn("bottom_value == l.llv(length * 2 + 1)", self.source)
        self.assertNotIn("previous_leg_is_bearish", self.source)

    def test_labels_all_fibonacci_levels(self):
        for label in ("0.000", "0.236", "0.382", "0.500", "0.618", "0.705", "0.786", "1.000"):
            self.assertIn(f'"{label}"', self.source)


if __name__ == "__main__":
    unittest.main()
