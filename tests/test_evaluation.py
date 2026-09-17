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


class Rebase(unittest.TestCase):
    """F-01: the deterministic re-base and the withdrawal of the fusion gain."""

    def test_deterministic_cnn_baseline(self):
        r = _load("rebase_deterministic")
        if r is None:
            self.skipTest("rebase_deterministic.json not generated")
        self.assertEqual(r["cnn_alone"]["new_per_seed"], [0.6298, 0.6269, 0.633])
        self.assertTrue(r["base_paper_views_validation"]["reproduces_paper_metrics"])
        self.assertTrue(all(r["checkpoint_pair_identical"].values()))

    def test_current_code_reproduces_the_deterministic_population(self):
        r = _load("rebase_deterministic")
        if r is None or "reproduction_check" not in r:
            self.skipTest("seed-42 re-run not recorded yet")
        rc = r["reproduction_check"]
        self.assertTrue(rc["predictions_byte_identical"])
        self.assertTrue(rc["loss_curve_identical"])
        self.assertTrue(rc["test_embeddings_byte_identical"])

    def test_online_fusion_does_not_beat_the_deterministic_cnn(self):
        r = _load("rebase_deterministic")
        if r is None:
            self.skipTest("rebase_deterministic.json not generated")
        p = r["fusion"]["CNN + KG k=800 (causal)"]["new_vs_new_cnn"]
        self.assertLess(p["mean_delta"], 0)
        self.assertEqual(p["seeds_better"], 0)

    def test_base_paper_sat_term_matched_control(self):
        """CL-02: with everything else equal, the SAT term does not reproduce the
        base paper's +12.13 pp zero-day gain, and its effect is not consistent."""
        r = _load("rebase_deterministic")
        mc = (r or {}).get("ltn_matched", {}).get("matched_comparison")
        if mc is None:
            self.skipTest("matched LTN comparison not recorded yet")
        self.assertLess(abs(mc["view5_delta"]["mean_delta"]), 2.0)
        self.assertFalse(mc["view5_delta"]["direction_consistent"])
        self.assertFalse(mc["macro_delta"]["direction_consistent"])
        for arm in ("ltn_repro_det", "ltn_repro_ctrl"):
            self.assertEqual(len(r["ltn_matched"][arm]["view5_per_seed"]), 3)

    def test_axioms_are_worse_than_their_control_with_every_cnn_run(self):
        """The robust symbolic result (2026-09-17): same trainer, axioms on vs off,
        negative with every CNN run on disk, alone and with the KG fused."""
        r = _load("ablation_population")
        if r is None:
            self.skipTest("ablation_population.json not generated")
        for rung in ("axioms, alone (Ax6 vs ctrl)", "axioms, on KG (Ax6 vs ctrl)"):
            for pop in ("pre_flag", "deterministic"):
                s = r["summary"][rung][pop]
                with self.subTest(rung=rung, pop=pop):
                    self.assertEqual(s["runs_negative"], s["n_runs"])
        # and the withdrawn abstract rung really does reverse off the reference runs
        self.assertLess(r["summary"]["Ax6 on KG"]["reference_three"]["mean"], 0)
        self.assertEqual(r["summary"]["Ax6 on KG"]["deterministic"]["runs_positive"], 6)

    def test_fusion_gain_is_not_a_property_of_the_method(self):
        """The withdrawal, pinned: the reference three gain, the other eight lose, and
        the gain is explained by where the CNN run ranks XSS."""
        r = _load("fusion_population")
        if r is None:
            self.skipTest("fusion_population.json not generated")
        s = r["fusion"]["k=800 causal"]["summary"]
        self.assertEqual((s["pre_flag"]["runs_positive"], s["pre_flag"]["n_cnn_runs"]), (5, 11))
        self.assertEqual(s["deterministic"]["runs_positive"], 0)
        self.assertGreater(s["pre_flag"]["reference_three_mean"], 0)
        self.assertLess(s["pre_flag"]["other_eight_mean"], 0)
        self.assertGreater(s["pre_flag"]["xss_rank_vs_delta_spearman"], 0.9)


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
