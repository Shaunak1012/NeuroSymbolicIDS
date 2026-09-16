"""
fusion_population.py — is the CNN + KG fusion gain a property of the method, or of
which CNN runs it happened to be paired with?

WHY THIS EXISTS (audit F-01, 2026-09-16)
----------------------------------------
Re-basing the fusion on the deterministic CNN population (c4_log1p_s42/43/44)
instead of the pre-flag one (cnn_paper, _s43, _s44) changed the online result from
a gain to a loss: CNN + causal KG at k=800 went from +0.0633 over its CNN to
-0.1269, 0/3 seeds. Only the CNN channel changed, the standalone CNN macro barely
moved (0.6399 -> 0.6299), and the loss is almost entirely XSS (fused XSS ~0.88 ->
~0.40 on every seed).

Six runs cannot say whether that is a population difference or run-to-run luck.
The record holds more: 11 pre-flag CNN runs (the three reference seeds, seeds
45-47, the seed-42 reproduction and four seed-42 noise-floor re-runs) and 8
deterministic ones (c4_log1p_s42-44, det_verify_a/b, postdet_s45-47). Each CNN run is
fused with each of the three KG seeds, because the pairing of a CNN seed with a KG
seed is arbitrary -- the KG is trained without the CNN.

Nothing is trained. The estimand is the fused macro zero-day PR-AUC minus the same
CNN run's own macro, per (CNN run, KG seed) pair.

⚠️ det_verify_a/b and c4_log1p_s42 are byte-identical re-runs of one configuration.
They are reported, but counted once when summarising the deterministic population.

Run:  python scripts/fusion_population.py
Out:  outputs/metadata/fusion_population.json
"""
import os
import sys
import json

import numpy as np
from scipy.stats import rankdata, mannwhitneyu

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402
import metrics                                      # noqa: E402

PRE_FLAG = ["cnn_paper", "cnn_paper_s43", "cnn_paper_s44", "cnn_paper_s45",
            "cnn_paper_s46", "cnn_paper_s47", "cnn_repro_s42",
            "cnn_noise_r1", "cnn_noise_r2", "cnn_noise_r3", "cnn_noise_r4"]
DETERMINISTIC = ["c4_log1p_s42", "c4_log1p_s43", "c4_log1p_s44",
                 "postdet_s45", "postdet_s46", "postdet_s47",
                 "det_verify_a", "det_verify_b"]
DUPLICATES_OF = {"det_verify_a": "c4_log1p_s42", "det_verify_b": "c4_log1p_s42"}
KG_SEEDS = [42, 43, 44]
KS = [200, 800]
FAMILIES = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]


def load(tag):
    return np.load(os.path.join(paths.PREDICTIONS, "y_prob_%s_test.npy" % tag))


def kg_tag(k, s, causal):
    suf = "_causal" if causal else ""
    if k == 200:
        return ("kg%s" % suf) if s == 42 else ("kg_s%d%s" % (s, suf))
    return "kg_k%d_s%d%s" % (k, s, suf)


def rk(x):
    return rankdata(x) / len(x)


def main():
    y = np.load(os.path.join(paths.PAPER, "y_test_mc.npy"), allow_pickle=True)
    zd = set(np.load(os.path.join(paths.PAPER, "zero_day_classes.npy"),
                     allow_pickle=True).tolist())
    zd_rows = np.isin(y, list(zd))
    known_atk = ~zd_rows & (y != "BENIGN")

    def ev(sc):
        r = metrics.evaluate(y, sc, zd, fpr=0.01)
        return r["macro"]["pr_auc"], {f: r["zeroday_family"][f]["pr_auc"] for f in FAMILIES}

    out = {"populations": {"pre_flag": PRE_FLAG, "deterministic": DETERMINISTIC},
           "duplicates": DUPLICATES_OF, "cnn": {}, "fusion": {}}

    for tag in PRE_FLAG + DETERMINISTIC:
        s = load(tag)
        m, f = ev(s)
        r = rk(s)
        out["cnn"][tag] = {
            "macro": m, "family": f,
            # where zero-day flows sit relative to the KNOWN attacks, which a
            # benign-only PR-AUC cannot see and a whole-set rank fusion does
            "xss_median_rank": float(np.median(r[y == "Web Attack XSS"])),
            "known_attack_median_rank": float(np.median(r[known_atk])),
        }

    for k in KS:
        for causal in (True, False):
            label = "k=%d %s" % (k, "causal" if causal else "s_kg")
            kg = {s: rk(load(kg_tag(k, s, causal))) for s in KG_SEEDS}
            rows = {}
            for tag in PRE_FLAG + DETERMINISTIC:
                rc = rk(load(tag))
                for s in KG_SEEDS:
                    m, f = ev(0.5 * rc + 0.5 * kg[s])
                    rows["%s|kg%d" % (tag, s)] = {"cnn": tag, "kg_seed": s, "fused_macro": m,
                                                  "delta": m - out["cnn"][tag]["macro"],
                                                  "family": f}
            summary = {}
            for pop, tags in (("pre_flag", PRE_FLAG),
                              ("deterministic", [t for t in DETERMINISTIC if t not in DUPLICATES_OF])):
                d = np.array([v["delta"] for v in rows.values() if v["cnn"] in tags])
                xss = np.array([v["family"]["Web Attack XSS"] for v in rows.values() if v["cnn"] in tags])
                summary[pop] = {"n_pairs": int(len(d)), "n_cnn_runs": len(tags),
                                "delta_mean": float(d.mean()), "delta_sd": float(d.std(ddof=1)),
                                "delta_min": float(d.min()), "delta_max": float(d.max()),
                                "frac_positive": float((d > 0).mean()),
                                "fused_xss_mean": float(xss.mean())}
            # the independent unit is the CNN RUN: average its three KG pairings
            per_run = {t: float(np.mean([v["delta"] for v in rows.values() if v["cnn"] == t]))
                       for t in PRE_FLAG + DETERMINISTIC}
            for pop, tags in (("pre_flag", PRE_FLAG),
                              ("deterministic", [t for t in DETERMINISTIC if t not in DUPLICATES_OF])):
                vals = np.array([per_run[t] for t in tags])
                summary[pop]["per_run_delta"] = {t: per_run[t] for t in tags}
                summary[pop]["runs_positive"] = int((vals > 0).sum())
                summary[pop]["per_run_mean"] = float(vals.mean())
                # the three reference seeds every published fusion number used
                if pop == "pre_flag":
                    ref = ["cnn_paper", "cnn_paper_s43", "cnn_paper_s44"]
                    rest = [t for t in tags if t not in ref]
                    summary[pop]["reference_three_mean"] = float(np.mean([per_run[t] for t in ref]))
                    summary[pop]["other_eight_mean"] = float(np.mean([per_run[t] for t in rest]))
                    summary[pop]["xss_rank_vs_delta_spearman"] = float(
                        __import__("scipy.stats", fromlist=["spearmanr"]).spearmanr(
                            [out["cnn"][t]["xss_median_rank"] for t in tags], vals).statistic)
            a = [v["delta"] for v in rows.values() if v["cnn"] in PRE_FLAG]
            b = [v["delta"] for v in rows.values()
                 if v["cnn"] in DETERMINISTIC and v["cnn"] not in DUPLICATES_OF]
            summary["population_difference"] = {
                "mean_diff": float(np.mean(a) - np.mean(b)),
                "mannwhitney_p": float(mannwhitneyu(a, b, alternative="two-sided").pvalue),
                "note": "pairs share KG seeds, so this p is indicative, not exact"}
            out["fusion"][label] = {"pairs": rows, "summary": summary}

    # report
    print("=" * 100)
    print("CNN + KG FUSION GAIN, BY CNN POPULATION  (delta = fused macro - same CNN run's macro)")
    print("=" * 100)
    for label, v in out["fusion"].items():
        s = v["summary"]
        print("\n%s" % label)
        for pop in ("pre_flag", "deterministic"):
            p = s[pop]
            print("  %-14s %2d CNN runs x 3 KG seeds: delta %+.4f +/- %.4f  [%+.4f, %+.4f]  "
                  "positive %3.0f %%  fused XSS %.3f"
                  % (pop, p["n_cnn_runs"], p["delta_mean"], p["delta_sd"], p["delta_min"],
                     p["delta_max"], 100 * p["frac_positive"], p["fused_xss_mean"]))
        pf = s["pre_flag"]
        print("  pre-flag, per CNN run: %d/%d runs gain | reference three %+.4f vs other eight %+.4f"
              " | spearman(XSS rank, gain) %+.2f"
              % (pf["runs_positive"], pf["n_cnn_runs"], pf["reference_three_mean"],
                 pf["other_eight_mean"], pf["xss_rank_vs_delta_spearman"]))
        dt = s["deterministic"]
        print("  deterministic, per CNN run: %d/%d runs gain" % (dt["runs_positive"], dt["n_cnn_runs"]))
        pd_ = s["population_difference"]
        print("  population difference %+.4f  (Mann-Whitney p = %.2g, indicative)"
              % (pd_["mean_diff"], pd_["mannwhitney_p"]))
    print("\nXSS median rank among ALL test flows (known attacks sit at ~%.2f):"
          % np.median([v["known_attack_median_rank"] for v in out["cnn"].values()]))
    for pop, tags in (("pre_flag", PRE_FLAG), ("deterministic", DETERMINISTIC)):
        print("  %-14s %s" % (pop, " ".join("%.2f" % out["cnn"][t]["xss_median_rank"] for t in tags)))

    p = os.path.join(paths.METADATA, "fusion_population.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("\nwrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
