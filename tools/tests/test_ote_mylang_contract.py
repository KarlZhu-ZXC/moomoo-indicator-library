from __future__ import annotations

import unittest
from pathlib import Path


class OteMyLangContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        cls.source = (root / "indicators" / "ote" / "OTE.mylang").read_text(encoding="utf-8")

    def test_direction_shifts_use_confirmed_hh_ll(self):
        self.assertIn("VALIDUP:=HH0;", self.source)
        self.assertIn("VALIDDN:=LL0;", self.source)
        self.assertIn("UPSHIFT:=VALIDUP;", self.source)
        self.assertIn("DNSHIFT:=VALIDDN;", self.source)

    def test_shift_existence_does_not_use_count_zero(self):
        self.assertNotIn("COUNT(SHIFT0,0)", self.source)
        self.assertIn("HASSHIFT:=SAGE<BARSCOUNT(C);", self.source)

    def test_debug_layer_exposes_state(self):
        self.assertIn("DEBUG:=0;", self.source)
        self.assertIn("OTE waiting for valid HH/LL", self.source)
        self.assertIn("OTE inactive", self.source)

    def test_validation_defaults_do_not_hide_first_grid(self):
        self.assertIn("INVALIDATE:=0;", self.source)

    def test_current_grid_uses_const_broadcast(self):
        self.assertIn("CSAGE:=CONST(SAGE);", self.source)
        self.assertIn("CF618:=CONST(F618);", self.source)
        self.assertIn("CVIS:=CACT AND CURRBARSCOUNT<=CSAGE+1;", self.source)


if __name__ == "__main__":
    unittest.main()
