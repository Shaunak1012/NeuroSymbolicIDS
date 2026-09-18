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


class BotMechanism(unittest.TestCase):
    """Retraction of 2026-09-17: Bot's ranking is not noise across CNN runs, and the
    forest's inconsistency is its default configuration. Absorption is universal."""

    @classmethod
    def setUpClass(cls):
        cls.r = _load("bot_mechanism_recheck")
        cls.b = _load("baselines_tuned")
        if cls.r is None:
            raise unittest.SkipTest("bot_mechanism_recheck.json not generated")

    def test_every_cnn_run_absorbs_bot(self):
        runs = [v for pop in self.r["absorption"].values() for v in pop.values()]
        self.assertEqual(len(runs), 17)
        for v in runs:
            self.assertEqual(v["Bot"]["frac_argmax_BENIGN"], 1.0)
            self.assertEqual(v["Web Attack XSS"]["modal_class"], "DoS slowloris")

    def test_bot_ranking_is_not_noise_over_all_runs(self):
        for pop in ("pre_flag", "deterministic"):
            bot = self.r["all_pairs"][pop]["all"]["Bot"]
            with self.subTest(pop=pop):
                self.assertGreater(bot["median"], 0.5)
                self.assertLess(bot["min"], 0)          # but it is the most variable family
                for fam in ("Web Attack Brute Force", "Web Attack XSS", "BENIGN"):
                    self.assertGreater(self.r["all_pairs"][pop]["all"][fam]["median"], bot["median"])
        self.assertAlmostEqual(self.r["rank_stability"]["CNN, pre-flag reference (log-odds)"]
                               ["Bot"]["mean"], -0.090, places=3)

    def test_forest_inconsistency_is_its_default_configuration(self):
        rs = self.r["rank_stability"]
        self.assertLess(rs["RandomForest, untuned (max_features=sqrt)"]["Bot"]["mean"], 0.1)
        self.assertGreater(rs["RandomForest, tuned (max_features=0.3)"]["Bot"]["mean"], 0.9)
        if self.b is not None:
            rf = self.b["models"]["random_forest"]
            self.assertEqual(rf["selected"]["max_features"], "0.3")
            self.assertTrue(all(run["family"]["Bot"] > 0.0342 for run in rf["runs"]))

    def test_overlap_account_fails_for_the_forest(self):
        """E4 (pre-registered): the tuned forest reaches Bot, yet weights Bot's
        features LESS than the default forest on every seed."""
        fo = self.r.get("forest_overlap")
        if fo is None:
            self.skipTest("run with RECHECK_FOREST=1")
        for t, d in zip(fo["tuned"]["per_seed"], fo["default"]["per_seed"]):
            self.assertTrue(t["refit_reproduces_logged_predictions"])
            self.assertTrue(d["refit_reproduces_logged_predictions"])
            self.assertLess(t["share_on_bot_top8"], d["share_on_bot_top8"])
            self.assertGreater(t["share_on_known_top8"], d["share_on_known_top8"])
        self.assertFalse(self.r["expectations"]["E4_tuned_forest_weights_bot_features_more"])


class SplitVariants(unittest.TestCase):
    """D4 (2026-09-17): what the grouped and chronological splits change."""

    @classmethod
    def setUpClass(cls):
        r = _load("split_variants")
        if r is None or any("per_seed" not in r["splits"][k]["models"].get(m, {})
                            for k in ("random", "grouped", "chronological") for m in ("cnn", "ae")):
            raise unittest.SkipTest("split_variants.json missing or incomplete")
        cls.s = r["splits"]

    def _macros(self, split, model="cnn"):
        return [p["macro"] for p in self.s[split]["models"][model]["per_seed"]]

    def test_grouped_split_has_no_shared_5tuple(self):
        self.assertEqual(self.s["grouped"]["boundary"]["flow_id_overlap"], 0.0)
        self.assertGreater(self.s["grouped"]["boundary"]["exact_duplicates"], 0.15)

    def test_grouping_lowers_the_cnn_on_every_seed(self):
        self.assertLess(max(self._macros("grouped")), min(self._macros("random")))
        g = self.s["grouped"]["models"]["cnn"]
        # not the benign flows that had to move into test
        self.assertLess(abs(g["macro_without_shared_5tuple_benign_mean"] - g["macro_mean"]), 0.005)

    def test_chronological_split_breaks_the_autoencoder_not_the_cnn(self):
        ae_r, ae_c = self.s["random"]["models"]["ae"], self.s["chronological"]["models"]["ae"]
        self.assertLess(ae_c["macro_mean"], 0.6 * ae_r["macro_mean"])
        self.assertLess(ae_c["known_only_pr_auc_mean"], 0.7)
        self.assertGreater(self.s["chronological"]["models"]["cnn"]["known_only_pr_auc_mean"], 0.99)

    def test_double_dissociation_keeps_direction_everywhere(self):
        for split, row in ((k, self.s[k]) for k in ("random", "grouped", "chronological")):
            for fam, v in row["double_dissociation"].items():
                with self.subTest(split=split, family=fam):
                    self.assertTrue(v["direction_consistent"])
                    self.assertEqual(v["cnn_minus_ae_mean"] < 0, fam == "Bot")

    def test_class_balancing_at_equal_size(self):
        """5.4: the base paper's balancing vs a size-matched natural-mix control,
        both on the canonical test set."""
        if not all("per_seed" in self.s.get(k, {}).get("models", {}).get("cnn", {})
                   for k in ("balanced", "subsampled")):
            self.skipTest("balanced / subsampled runs not present")
        b, u, r = self.s["balanced"], self.s["subsampled"], self.s["random"]
        self.assertEqual(b["n_test"], r["n_test"])
        self.assertEqual(u["n_test"], r["n_test"])
        self.assertEqual(sum(b["train_counts"].values()), sum(u["train_counts"].values()))
        self.assertEqual(len({v for k, v in b["train_counts"].items() if k != "BENIGN"}), 1)
        self.assertGreater(min(self._macros("balanced")), max(self._macros("subsampled")))
        self.assertLess(max(self._macros("balanced")), min(self._macros("random")))
        for p in u["models"]["cnn"]["per_seed"]:
            self.assertGreater(p["absorption"]["Web Attack XSS"]["frac_BENIGN"], 0.9)

    def test_view5_collapses_when_attempted_flows_are_excluded(self):
        """6.5: the 47.85 / 48.34 agreement with the base paper does not survive
        the closest analogue of their payload filtering."""
        ie = self.s.get("improved_exclude", {}).get("models", {}).get("cnn", {})
        if "per_seed" not in ie:
            self.skipTest("improved_exclude runs not present")
        for p in ie["per_seed"]:
            self.assertLess(p["absorption"]["_views"]["view5_zero_day_acc"], 5.0)
        for p in self.s["random"]["models"]["cnn"]["per_seed"]:
            self.assertGreater(p["absorption"]["_views"]["view5_zero_day_acc"], 45.0)

    def test_web_families_absorbed_into_slowloris_on_every_split(self):
        for split, row in ((k, self.s[k]) for k in ("random", "grouped", "chronological")):
            for p in row["models"]["cnn"]["per_seed"]:
                with self.subTest(split=split, seed=p["seed"]):
                    self.assertEqual(p["absorption"]["Bot"]["modal_class"], "BENIGN")
                    self.assertEqual(p["absorption"]["Web Attack XSS"]["modal_class"], "DoS slowloris")


class EndToEndReproduction(unittest.TestCase):
    """7.4 (2026-09-18): the run_all execution from the raw CSVs."""

    @classmethod
    def setUpClass(cls):
        cls.rc = _load("repro_compare_sandbox_e2e2")
        p = os.path.join(paths.METADATA, "run_all_sandbox2", "run_all_report.json")
        if cls.rc is None or not os.path.exists(p):
            raise unittest.SkipTest("end-to-end records not present")
        with open(p, encoding="utf-8") as f:
            cls.rr = json.load(f)

    def test_nothing_differed_from_canonical(self):
        self.assertEqual(self.rc["summary"].get("different", 0), 0)
        self.assertGreaterEqual(self.rc["summary"]["identical"], 72)

    def test_the_trained_models_are_byte_identical(self):
        want = {"y_prob_cnn_paper%s_test.npy" % ("" if s == 42 else "_s%d" % s) for s in (42, 43, 44)}
        want |= {"y_prob_autoencoder_paper%s_test.npy" % ("" if s == 42 else "_s%d" % s)
                 for s in (42, 43, 44)}
        seen = {os.path.basename(r["sandbox"]): r["verdict"] for r in self.rc["files"]}
        for f in sorted(want):
            with self.subTest(file=f):
                self.assertEqual(seen.get(f), "identical")

    def test_only_the_external_input_stages_failed(self):
        failed = {s["name"] for s in self.rr["stages"] if not s["ok"]}
        self.assertEqual(failed, {"baselines_tuned", "bot_recheck", "operational",
                                  "field_gap", "figures", "paper_figures"})
        for s in self.rr["stages"]:
            if s["name"] in failed and s["name"] != "paper_figures":
                with self.subTest(stage=s["name"]):
                    self.assertTrue(s["external_inputs"])


class Evasion(unittest.TestCase):
    """6.4 (2026-09-18): the pre-registered, non-adaptive evasion test."""

    @classmethod
    def setUpClass(cls):
        cls.r = _load("evasion")
        if cls.r is None:
            raise unittest.SkipTest("evasion.json not generated")

    def test_predictions_as_recorded(self):
        p = self.r["predictions"]
        self.assertTrue(p["V1_cnn_bot_stays_below_0.08"])
        self.assertTrue(p["V2_each_supervised_model_loses_more_than_noise"]["cnn"])
        self.assertFalse(p["V2_each_supervised_model_loses_more_than_noise"]["rf"])
        self.assertTrue(p["V3_slow10_raises_autoencoder"])

    def test_zero_strength_is_the_unperturbed_score(self):
        res = self.r["results"]
        for model in ("cnn", "ae", "rf"):
            base = res["pad"]["0"][model]["macro_mean"]
            for n, st in (("slow", "1"), ("jitter", "0")):
                with self.subTest(model=model, perturbation=n):
                    self.assertAlmostEqual(res[n][st][model]["macro_mean"], base, places=3)

    def test_every_perturbation_raises_the_anomaly_scorers(self):
        for n, byst in self.r["delta_vs_unperturbed"].items():
            for st, d in byst.items():
                with self.subTest(perturbation=n, strength=st):
                    self.assertGreater(d["ae"], 0)
                    self.assertGreater(d["rf"], 0)


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
