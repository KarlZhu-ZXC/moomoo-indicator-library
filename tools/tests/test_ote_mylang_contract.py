from __future__ import annotations

import unittest
from pathlib import Path


class OteMyLangContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        cls.source = (root / "indicators" / "ote" / "OTE.mylang").read_text(encoding="utf-8")

    def test_direction_shifts_require_opposite_pivot(self):
        self.assertIn("VALIDUP:=HH0 AND HASPL;", self.source)
        self.assertIn("VALIDDN:=LL0 AND HASPH;", self.source)
        self.assertIn("UPSHIFT:=VALIDUP", self.source)
        self.assertIn("DNSHIFT:=VALIDDN", self.source)

    def test_debug_layer_exposes_state(self):
        self.assertIn("DEBUG:=1;", self.source)
        self.assertIn("OTE waiting for HH/LL", self.source)
        self.assertIn("OTE inactive", self.source)


if __name__ == "__main__":
    unittest.main()
