from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "integration"))
from hist_sim_regression import fit_reference  # noqa: E402


class HistSimReferenceTest(unittest.TestCase):
    def test_indicator_compatibility_contract(self):
        primary = (ROOT / "indicators" / "historical-similarity" / "HIST_SIM.py").read_text()
        fallback = (ROOT / "indicators" / "historical-similarity" / "HIST_SIM_PCT.py").read_text()
        self.assertIn("from fmath import *", primary)
        self.assertIn("math_log(", primary)
        self.assertNotIn("ln(", primary)
        self.assertIn("from fmath import *", fallback)
        self.assertNotIn("math_log(", fallback)

    def test_multi_symbol_snapshot_invariants(self):
        payload = json.loads((ROOT / "docs" / "releases" / "HIST_SIM_V2_0_1_REGRESSION.json").read_text())
        expected = {"US.QCOM", "US.TTWO", "US.ORCL", "US.AAPL", "US.NVDA", "US.TSLA", "US.SPY", "US.QQQ"}
        self.assertEqual({item["code"] for item in payload["symbols"]}, expected)
        for item in payload["symbols"]:
            self.assertTrue(item["full_history_loaded"])
            self.assertEqual(item["candidate_count"], 2450)
            self.assertEqual(len(item["ohlc_sha256"]), 64)
            for mode in ("log", "pct"):
                fit = item[mode]
                self.assertGreaterEqual(fit["selected_anchor_age"], 71)
                self.assertLessEqual(fit["selected_anchor_age"], 2520)
                self.assertLess(fit["source_start"], fit["source_anchor"])
                self.assertLess(fit["source_anchor"], fit["source_end"])
                self.assertGreaterEqual(fit["fit_score"], 0.0)
                self.assertLessEqual(fit["fit_score"], 100.0)
                self.assertTrue(math.isfinite(fit["distance"]))

    def test_reference_engine_evaluates_every_anchor(self):
        n = 2808
        rng = np.random.default_rng(20260901)
        close = 100.0 * np.exp(np.cumsum(rng.normal(0.0002, 0.015, n)))
        dates = pd.bdate_range("2015-07-01", periods=n).strftime("%Y-%m-%d 00:00:00")
        frame = pd.DataFrame({"time_key": dates, "close": close})
        for mode in ("log", "pct"):
            fit, candidates = fit_reference(frame, mode=mode)
            self.assertEqual(candidates, 2450)
            self.assertGreaterEqual(fit.selected_anchor_age, 71)
            self.assertLessEqual(fit.selected_anchor_age, 2520)


if __name__ == "__main__":
    unittest.main()
