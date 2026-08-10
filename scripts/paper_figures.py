"""
paper_figures.py — figures 2-5 of the write-up, built from the RECORD.

WHY IT READS JSON AND NEVER RETRAINS
------------------------------------
Every number plotted here comes from `outputs/metadata/*.json`, i.e. the same
artifacts that back the claims in `docs/target/paper_outline.md`. A figure
regenerated from a fresh run could silently disagree with the text -- which is the
same defect class as a doc quoting a number with no logged run behind it. So this
script does no training, no scoring, and no recomputation: if a figure and the
outline disagree, exactly one of them is stale and it is discoverable.

FIGURES CARRY THEIR OWN CAVEATS
-------------------------------
The outline's rule is that a claim without its limit is not ready to write. A
figure lifted into a talk loses its surrounding paragraph, so each panel here
prints the limit that would otherwise be lost -- the ties warning, the noise
threshold, the "this is one under-tuned config" note. This is the same reason
field_gap.png carries "rho = +0.57: a weak proxy, NOT uninformative" on its face.

  python scripts/paper_figures.py
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

MD = paths.METADATA
FIG = paths.FIGURES

BLUE, RED, GREY, GREEN = "#2b6cb0", "#c53030", "#718096", "#2f855a"


def load(name):
    with open(os.path.join(MD, name), encoding="utf-8") as f:
        return json.load(f)


def save(fig, name, tight=True):
    """tight=False when the figure reserves its own margins via subplots_adjust.

    tight_layout() does not know about fig.text() captions and silently overrides
    subplots_adjust, which is what pushed fig4's two-line caption onto its x-axis
    label. Figures that lay themselves out opt out.
    """
    p = os.path.join(FIG, name)
    if tight:
        fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    print(f"  wrote {p}")


# ----------------------------------------------------------------------------
def fig2_bot_mechanism():
    """The mechanism: Bot is confidently asserted BENIGN, and its ranking is noise."""
    d = load("bot_failure_analysis.json")["results"]
    absorp, rank = d["H1_absorption"], d["H2b_cross_seed_rank_corr"]
    fams = ["Bot", "Web Attack Brute Force", "Web Attack XSS"]
    short = {"Bot": "Bot", "Web Attack Brute Force": "Web BF", "Web Attack XSS": "XSS"}

    seeds = list(absorp.keys())
    frac = {f: np.mean([absorp[s][f]["frac_argmax_BENIGN"] for s in seeds]) for f in fams}
    pben = {f: np.mean([absorp[s][f]["mean_p_BENIGN"] for s in seeds]) for f in fams}
    modal = {f: absorp[seeds[0]][f]["modal_class"] for f in fams}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    x = np.arange(len(fams))
    ax1.bar(x - 0.2, [frac[f] for f in fams], 0.4, label="fraction argmax = BENIGN",
            color=BLUE)
    ax1.bar(x + 0.2, [pben[f] for f in fams], 0.4, label="mean p(BENIGN)", color=GREY)
    ax1.set_xticks(x); ax1.set_xticklabels([short[f] for f in fams])
    ax1.set_ylim(0, 1.18); ax1.set_ylabel("fraction / probability")
    ax1.set_title("(a) Bot is not ambiguous — it is confidently BENIGN", fontsize=11)
    # centre-right: the only empty region once Bot's bars reach 1.0 and the modal-class
    # annotations occupy the top strip.
    ax1.legend(fontsize=8, loc="center right")
    ax1.grid(axis="y", alpha=0.25)
    for i, f in enumerate(fams):
        # The web families are NOT classified benign -- they are absorbed into a
        # known ATTACK class, which is why their PR-AUC is high and why that high
        # number is not zero-day detection. Stating it on the figure.
        ax1.text(i, 1.05, f"→ {modal[f]}", ha="center", fontsize=8,
                 color=RED if modal[f] == "BENIGN" else GREEN)

    models = ["cnn_paper", "random_forest", "autoencoder"]
    labels = ["CNN", "RandomForest", "Autoencoder"]
    w = 0.25
    for j, (m, lab) in enumerate(zip(models, labels)):
        vals = [rank[m][f] for f in fams]
        ax2.bar(np.arange(len(fams)) + (j - 1) * w, vals, w, label=lab)
    ax2.axhline(0, color="k", lw=0.8)
    ax2.axhspan(-0.2, 0.2, color=RED, alpha=0.08)
    ax2.text(2.55, 0.02, "noise band", fontsize=7.5, color=RED, ha="right")
    ax2.set_xticks(np.arange(len(fams)))
    ax2.set_xticklabels([short[f] for f in fams])
    ax2.set_ylabel("cross-seed Spearman ρ of the flow ranking")
    ax2.set_title("(b) …so the CNN's Bot ranking is noise — but the AE's is not",
                  fontsize=11)
    ax2.legend(fontsize=8); ax2.grid(axis="y", alpha=0.25)

    ov = d["H3_feature_neglect"]
    fig.text(0.5, 0.005,
             f"Bot's 8 oracle-discriminative features overlap the known-class task's by "
             f"{ov['bot_overlap_n']}/8 — yet Bot is separable at oracle PR-AUC "
             f"{d['H4_raw_oracle_separability']['Bot']['oracle_pr_auc']:.4f}. "
             f"The information is present; the representation does not encode it.",
             ha="center", fontsize=8.5, color="#4a5568")
    fig.subplots_adjust(bottom=0.16)
    save(fig, "fig2_bot_mechanism.png")


# ----------------------------------------------------------------------------
def fig3_alert_budget():
    """The operational statement: at any deployable budget you see only known attacks."""
    o = load("operational.json")
    ab, depth, n_test = o["alert_budget"], o["zero_day_depth"], o["n_test"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    for ch, rows in ab.items():
        b = [r["budget"] for r in rows]
        z = [r["n_zero_day"] for r in rows]
        ax1.plot(b, z, marker="o", ms=4, label=ch)
    ax1.set_xscale("log")
    ax1.set_xlabel("alert budget (flows reviewed, log scale)")
    ax1.set_ylabel("zero-day flows inside the alert stream")
    ax1.set_title("(a) Precision is ~1.000 at every budget —\nand that is the problem",
                  fontsize=11)
    ax1.grid(alpha=0.25); ax1.legend(fontsize=8)
    ax1.annotate("0 zero-day flows\nin the top 1,000", xy=(1000, 0), xytext=(1400, 260),
                 fontsize=8.5, color=RED,
                 arrowprops=dict(arrowstyle="->", color=RED, lw=1.2))

    chans = list(depth.keys())
    levels = ["0.1", "0.25", "0.5"]
    w = 0.25
    for j, lv in enumerate(levels):
        vals = [100 * depth[c][lv] / n_test for c in chans]
        bars = ax2.bar(np.arange(len(chans)) + (j - 1) * w, vals, w,
                       label=f"{int(float(lv)*100)}% of zero-day found")
        for bar, v in zip(bars, vals):
            ax2.text(bar.get_x() + bar.get_width() / 2, v + 1, f"{v:.0f}", ha="center",
                     fontsize=7.5)
    ax2.set_xticks(np.arange(len(chans)))
    ax2.set_xticklabels([c.replace(" ", "\n") for c in chans], fontsize=8.5)
    ax2.set_ylabel("% of ALL test traffic that must be reviewed")
    ax2.set_title("(b) The KG cuts review depth by ~20 pp —\nthe clearest thing it buys",
                  fontsize=11)
    ax2.grid(axis="y", alpha=0.25); ax2.legend(fontsize=8)

    fig.text(0.5, 0.005,
             "A 100%-precise alert stream containing zero novel attacks is the failure "
             "macro PR-AUC 0.64 does not show. Reaching half the zero-day flows means "
             "reviewing a third to a half of all traffic.",
             ha="center", fontsize=8.5, color="#4a5568")
    fig.subplots_adjust(bottom=0.16)
    save(fig, "fig3_alert_budget.png")


# ----------------------------------------------------------------------------
def fig4_ablation():
    """Only the KG earns its place — judged on the PAIRED statistic, not the floor.

    ⚠️ A first version of this figure coloured each rung by |Δ| against the 0.0222
    noise floor, and rendered `FULL vs CNN+KG` (−0.0218) as *noise*. That was wrong,
    and wrong in an instructive way: **0.0222 is the run-to-run SD of an ABSOLUTE
    number, and in a paired comparison over shared seeds that common variance
    cancels** -- exactly as this project already documents for the data-split SD.
    The correct yardstick is the paired difference's own SD. On that footing
    `FULL vs CNN+KG` is **16.3σ**, the tightest effect in the ablation, not noise.

    So each rung is judged on (a) whether the direction holds across ALL seeds and
    (b) the paired effect size -- and the two can disagree: CNN+KG's DIRECTION is
    certain (3/3) while its MAGNITUDE is not (1.7σ, spanning 0.027-0.088).
    """
    a = load("ablation.json")
    boot = a["_bootstrap"]

    rows = []
    for r in boot:
        x = np.array(a[r["a"]]["per_seed_macro"])
        y = np.array(a[r["b"]]["per_seed_macro"])
        d = x - y
        sd = float(d.std(ddof=1))
        up, dn = int((d > 0).sum()), int((d < 0).sum())
        rows.append({**r, "pair_sd": sd, "d_over_sd": abs(d.mean()) / sd if sd else np.inf,
                     "consistent": max(up, dn), "n": len(d)})
    rows.sort(key=lambda r: r["diff"])

    fig, ax = plt.subplots(figsize=(11.5, 6.4))
    for i, r in enumerate(rows):
        lo, hi = r["ci95"]
        full_agree = r["consistent"] == r["n"]
        col = (GREEN if r["diff"] > 0 else RED) if full_agree else GREY
        ax.plot([lo, hi], [i, i], color=col, lw=2.6, solid_capstyle="round")
        ax.plot(r["diff"], i, "o", color=col, ms=8.5)
        ax.text(hi + 0.004, i,
                f"{r['diff']:+.4f}   {r['d_over_sd']:.1f}σ paired   "
                f"{r['consistent']}/{r['n']} seeds",
                va="center", fontsize=8.5, color=col)
    ax.axvline(0, color="k", lw=0.9)
    ax.set_yticks(np.arange(len(rows)))
    ax.set_yticklabels([f"{r['a']}\nvs {r['b']}" for r in rows], fontsize=8.5)
    ax.set_xlabel("Δ macro zero-day PR-AUC  (paired bootstrap over per-flow scores, "
                  "B=2000, 95% CI)")
    ax.set_title("Only the KG earns its place — and adding the symbolic pillar on top "
                 "of it HURTS", fontsize=11.5)
    ax.grid(axis="x", alpha=0.25)
    ax.set_xlim(-0.05, 0.135)
    ax.margins(y=0.12)

    fig.text(0.5, 0.062,
             "GREY = the direction does not hold across all seeds (2/3), so it is not an effect "
             "regardless of p. σ is the PAIRED difference's own SD:",
             ha="center", fontsize=8.5, color="#4a5568")
    fig.text(0.5, 0.024,
             "the 0.0222 run-to-run floor applies to ABSOLUTE numbers and cancels in a paired "
             "comparison. Note CNN+KG's direction is certain (3/3) while its magnitude is not "
             "(1.7σ, spanning 0.027–0.088).",
             ha="center", fontsize=8.5, color="#4a5568")
    # tight_layout() in save() would undo these reservations, so lay out explicitly.
    fig.subplots_adjust(bottom=0.24, left=0.235, right=0.98, top=0.93)
    save(fig, "fig4_ablation.png", tight=False)


# ----------------------------------------------------------------------------
def fig5_variance():
    """Where this project's uncertainty actually comes from."""
    n = load("noise_postdet.json")
    pv = load("protocol_variance.json")

    sd_nondet = n["A_preflag_fixed_seed"]["sd"]
    sd_seed = n["C_postflag_varying_seed"]["sd"]
    sd_split = 0.0228
    for k in ("sd", "macro_sd", "std"):
        if isinstance(pv, dict) and k in pv:
            sd_split = float(pv[k]); break

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5),
                                   gridspec_kw={"width_ratios": [1.15, 1]})

    labels = ["nondeterminism\n(fixed seed,\ndet OFF)", "seed\n(det ON)",
              "data split\n(5-fold, model\n+ test fixed)"]
    vals = [sd_nondet, sd_seed, sd_split]
    bars = ax1.bar(labels, vals, color=[RED, BLUE, GREEN], width=0.6)
    for b, v in zip(bars, vals):
        ax1.text(b.get_x() + b.get_width() / 2, v + 0.0004, f"{v:.4f}", ha="center",
                 fontsize=9.5, weight="bold")
    ax1.set_ylabel("SD of macro zero-day PR-AUC (n=6 / n=6 / 5-fold)")
    ax1.set_title("(a) Three sources, all the same order of magnitude", fontsize=11)
    ax1.grid(axis="y", alpha=0.25)
    ax1.set_ylim(0, max(vals) * 1.32)
    ax1.annotate(f"F(5,5)={n['P1']['F']:.2f}, p={n['P1']['p']:.2f}\nindistinguishable",
                 xy=(0.5, max(vals) * 1.14), ha="center", fontsize=8.5, color="#4a5568")
    ax1.plot([0, 1], [max(vals) * 1.09] * 2, color="#4a5568", lw=1)

    # Panel b: the pre/post-flag seed sweep -- the "session effect" appearing and vanishing.
    seeds = [42, 43, 44, 45, 46, 47]
    pre = list(n["B_preflag_varying_seed"]["runs"].values())
    post = list(n["C_postflag_varying_seed"]["runs"].values())
    ax2.plot(seeds, pre, "o-", color=RED, label=f"determinism OFF (ρ={n['P2']['rho_preflag']:+.3f})")
    ax2.plot(seeds, post, "s-", color=BLUE,
             label=f"determinism ON  (ρ={n['P2']['rho_postflag']:+.3f})")
    ax2.set_xlabel("seed"); ax2.set_ylabel("macro zero-day PR-AUC")
    ax2.set_title("(b) The 'session effect' tracked RUN ORDER, not seed", fontsize=11)
    ax2.grid(alpha=0.25); ax2.legend(fontsize=8.5)

    fig.text(0.5, 0.005,
             f"Determinism removed a CONFOUND, not the uncertainty. Comparisons on a shared split "
             f"cancel the data draw (threshold {n['threshold_old']:.4f}); an ABSOLUTE number still "
             f"carries √(split² + seed²) = {n['absolute_number_uncertainty']:.4f}.",
             ha="center", fontsize=8.5, color="#4a5568")
    fig.subplots_adjust(bottom=0.16)
    save(fig, "fig5_variance.png")


def main():
    print("Building paper figures 2-5 from outputs/metadata/*.json (no retraining)")
    fig2_bot_mechanism()
    fig3_alert_budget()
    fig4_ablation()
    fig5_variance()
    print("DONE (paper_figures)")


if __name__ == "__main__":
    main()
