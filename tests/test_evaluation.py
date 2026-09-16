"""
Evaluation tests (audit F-07, F-09, and the records behind the write-up).

`metrics.py` is the one function every reported number passes through, so its
contract is tested on synthetic data that needs no artefacts. The record tests
check that the transcriptions and derived records the paper cites still say what
the paper says.

Run:  python -m unittest discover -s tests -v
"""
import json
import os
import subprocess
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import metrics   # noqa: E402
import paths     # noqa: E402


def _toy(seed=0, n_benign=5000, n_bot=300, n_small=40):
    rng = np.random.RandomState(seed)
    y = np.array(["BENIGN"] * n_benign + ["Bot"] * n_bot + ["Heartbleed"] * n_small)
    s = np.r_[rng.randn(n_benign), rng.randn(n_bot) + 1.0, rng.randn(n_small) + 3.0]
    return y, s


class MetricsContract(unittest.TestCase):

    def test_default_threshold_is_fitted_to_the_evaluated_set(self):
        y, s = _toy()
        r = metrics.evaluate(y, s, {"Bot", "Heartbleed"}, fpr=0.01)
        self.assertEqual(r["threshold_source"], "evaluated_set_benign_quantile")
        self.assertAlmostEqual(r["diagnostics"]["achieved_fpr"], 0.01, places=3)

    def test_given_threshold_is_used_and_not_refitted(self):
        """F-07: a threshold fixed on other data must survive into the report."""
        y, s = _toy()
        val_benign = np.random.RandomState(99).randn(5000) + 0.2   # shifted on purpose
        thr = metrics.threshold_from(val_benign, 0.01)
        r = metrics.evaluate(y, s, {"Bot", "Heartbleed"}, fpr=0.01, thr=thr)
        self.assertEqual(r["threshold_source"], "given")
        self.assertEqual(r["threshold"], thr)
        # the achieved FPR is now a measurement, not 0.01 by construction
        self.assertNotAlmostEqual(r["diagnostics"]["achieved_fpr"], 0.01, places=3)

    def test_threshold_does_not_touch_ranking_metrics(self):
        y, s = _toy()
        a = metrics.evaluate(y, s, {"Bot", "Heartbleed"})
        b = metrics.evaluate(y, s, {"Bot", "Heartbleed"}, thr=0.0)
        self.assertEqual(a["macro"]["pr_auc"], b["macro"]["pr_auc"])
        self.assertEqual(a["zeroday_family"]["Bot"]["roc_auc"],
                         b["zeroday_family"]["Bot"]["roc_auc"])

    def test_underpowered_family_is_excluded_from_macro(self):
        y, s = _toy()
        r = metrics.evaluate(y, s, {"Bot", "Heartbleed"})
        self.assertEqual(r["macro"]["excluded"], ["Heartbleed"])
        self.assertEqual(r["macro"]["n_families"], 1)
        self.assertEqual(r["macro"]["pr_auc"], r["zeroday_family"]["Bot"]["pr_auc"])

    def test_each_family_is_scored_against_benign_only(self):
        y, s = _toy()
        r = metrics.evaluate(y, s, {"Bot", "Heartbleed"})
        self.assertAlmostEqual(r["zeroday_family"]["Bot"]["chance_pr_auc"], 300 / 5300)

    def test_saturation_is_flagged(self):
        y = np.array(["BENIGN"] * 1000 + ["Bot"] * 200)
        s = np.zeros(1200)
        s[-50:] = 1.0
        r = metrics.evaluate(y, s, {"Bot"})
        self.assertTrue(r["diagnostics"]["saturated"])


def _load(name):
    p = os.path.join(paths.METADATA, name + ".json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


class Records(unittest.TestCase):
    """The records the paper cites say what the paper says they say."""

    def test_base_paper_transcription_validates(self):
        r = _load("basepaper_audit")
        if r is None:
            self.skipTest("basepaper_audit.json not generated")
        self.assertTrue(r["transcription_validated"])
        self.assertTrue(r["headline_pair_reproduces"])
        self.assertEqual(r["test_size"]["implied_known_test_from_fig3"], 159_160)
        self.assertEqual(len(r["table_ii_inconsistent"]), 3)
        self.assertEqual(r["zero_day_composition"]["families"]["Heartbleed"]["distinct_5tuples"], 1)
        per_view = list(r["hybrid_minus_cnn"]["per_view"].values())
        self.assertEqual(per_view, [0.09, 0.15, 0.07, 2.15, 12.13])

    def test_heldout_k_record_has_a_generator_and_both_variants(self):
        r = _load("ksweep_heldout")
        if r is None:
            self.skipTest("ksweep_heldout.json not generated")
        self.assertEqual(r.get("generated_by"), "scripts/ksweep_heldout.py")
        self.assertAlmostEqual(r["held_out_delta_vs_k200"], 0.0305, places=4)
        self.assertIn("causal", r)

    def test_operational_record_names_the_online_row(self):
        r = _load("operational_best")
        if r is None:
            self.skipTest("operational_best.json not generated")
        op = r["operational_config"]
        self.assertIn(op, r["configs"])
        self.assertTrue(r["configs"][op]["online"])
        offline = [k for k, v in r["configs"].items() if v.get("online") is False]
        self.assertTrue(offline, "the transductive row should be marked offline")


class DraftVerification(unittest.TestCase):
    """The paper's numbers match the records (both the master draft and the split)."""

    def _run(self, env_extra):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", **env_extra)
        p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "verify_draft.py")],
                           cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
        return p.returncode, p.stdout

    def test_master_draft(self):
        rc, out = self._run({})
        self.assertEqual(rc, 0, out[-2000:])

    def test_body_and_supplementary(self):
        rc, out = self._run({"VERIFY_FILES": "docs/target/paper_body.md,"
                                             "docs/target/paper_supplementary.md"})
        self.assertEqual(rc, 0, out[-2000:])


if __name__ == "__main__":
    unittest.main()
