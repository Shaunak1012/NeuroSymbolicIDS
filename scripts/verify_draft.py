"""
verify_draft.py — check every quantitative claim in the paper draft against the
research record, mechanically.

WHY THIS EXISTS
---------------
`paper_draft.md` was written by transcribing numbers out of `paper_outline.md`,
which was itself transcribed out of `outputs/metadata/*.json`. **Transcription is
where this project's numbers go wrong**, and the record already carries three
defects of the form "a number quoted in a doc with no logged run behind it".

The 2026-09-05 draft quoted the detection path at **125,750 flows/s** when the
record said **125,762**. That was caught **by accident**, while re-deriving
something else — not by any check. A paper is the one artifact where a
transcription slip is unrecoverable after submission, so the check should not
depend on someone happening to look.

WHAT IT DOES
------------
For each claim: pull the value from the JSON that produced it, format it the way
the draft is supposed to state it, and assert that string appears in the draft.
Three outcomes:

  ✅ OK        the record's value appears in the draft
  🔴 MISMATCH  the record's value does NOT appear — the draft is stale or wrong
  ⚠️  UNBACKED  a draft claim with no machine-readable record behind it

**UNBACKED is reported deliberately, not hidden.** Some numbers legitimately have
no JSON (split sizes come from `config.yaml`, the base paper's figures come from
the base paper). Listing them is the point: it is the set a human must check by
hand, and it should be small and stable. A check that silently ignores what it
cannot verify is the "a check that cannot fire is worse than no check" failure
this project has hit twice.

⚠️ **This verifies TRANSCRIPTION, not INTERPRETATION.** It cannot tell you that a
caveat is missing, that a claim overreaches its evidence, or that a paired delta
is being judged against an unpaired floor. Those are review, and this is not a
substitute for it.

Run:  python scripts/verify_draft.py
Exit: 0 if no mismatches, 1 otherwise.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                       # noqa: E402

DRAFT = os.path.join(paths.ROOT, "docs", "target", "paper_draft.md")


def load(name):
    p = os.path.join(paths.METADATA, name + ".json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


REC = {n: load(n) for n in (
    "field_gap", "ablation", "operational", "ood_scores", "noise_postdet",
    "comparability", "kg_criteria", "bot_failure_analysis", "fitted_fusion",
    "latency_determinism_on")}

with open(DRAFT, encoding="utf-8") as f:
    TEXT = f.read()

# The draft uses a Unicode minus in prose and ASCII hyphen in tables; normalise
# both sides rather than requiring the author to remember which is which.
NORM = TEXT.replace("−", "-").replace("–", "-").replace(" ", " ")

OK, BAD, UNBACKED = [], [], []


NOT_QUOTED = []


def chk(label, source, value, fmt="{:.4f}", alt=(), quoted=True, note=""):
    """Assert the record's value, formatted as the draft should state it, is present.

    `alt` lists other renderings the draft is allowed to use for the SAME claim --
    a range ("0.92-0.95") where the draft summarises two family figures, say.
    Without it the checker fires on legitimate prose and becomes noise, and **a
    check that cries wolf is worse than no check** for the same reason a check
    that cannot fire is: both stop being read.

    `quoted=False` marks a record value the draft deliberately does not state.
    Reported separately as informational -- never as a mismatch, because "the
    draft omits this" and "the draft gets this wrong" are different findings.
    """
    if value is None:
        UNBACKED.append((label, note or "record missing"))
        return
    want = fmt.format(value) if "{" in fmt else fmt
    forms = [want] + list(alt)
    hit = next((f for f in forms if f.replace("−", "-") in NORM), None)
    if hit:
        OK.append((label, hit if hit == want else f"{want} (as {hit!r})"))
    elif not quoted:
        NOT_QUOTED.append((label, want))
    else:
        BAD.append((label, want, source))


def unbacked(label, why):
    UNBACKED.append((label, why))


fg = REC["field_gap"]
if fg:
    d = fg["discrimination"]
    chk("field: pairs 2x apart on macro", "field_gap", d["pairs_2x_apart_on_macro"], "{:d}")
    chk("field: comparable pairs", "field_gap", d["pairs_indistinguishable"], "{:d}")
    chk("field: indistinguishable band", "field_gap", d["indistinguishable_band"], "{:.4f}")
    chk("field: run-to-run SD", "field_gap", fg["discrimination"]["field_noise_sd"], "{:.4f}")
    chk("field: n methods", "field_gap", fg["n_methods"], "{:d}")
    chk("field: spearman rho", "field_gap", fg["spearman"]["rho"], "+{:.3f}")

ab = REC["ablation"]
if ab:
    chk("ablation: CNN macro", "ablation", ab["CNN"]["macro_mean"])
    chk("ablation: CNN+KG macro", "ablation", ab["CNN + KG"]["macro_mean"])
    chk("ablation: CNN+KG paired delta", "ablation",
        ab["CNN + KG"]["paired_delta_mean"], "+{:.4f}")
    chk("ablation: FULL macro", "ablation", ab["CNN + LTN-Ax6 + KG (FULL)"]["macro_mean"])
    chk("ablation: LTN-Ax6 paired delta", "ablation",
        ab["CNN + LTN-Ax6"]["paired_delta_mean"], "{:.4f}")

op = REC["operational"]
if op:
    e = op["ensemble"]
    chk("operational: ensemble", "operational", e["ensemble_prob_mean"])
    chk("operational: single-run mean", "operational", e["single_mean"])
    chk("operational: single-run max", "operational", e["single_max"])
    chk("operational: n runs", "operational", e["n_runs"], "{:d}")
    iso = op["calibration"]["methods"]["isotonic"]
    chk("calibration: isotonic ECE known", "operational", iso["ece"]["known-class"])
    chk("calibration: isotonic ECE zero-day", "operational", iso["ece"]["zero-day"])
    chk("calibration: zd/known ratio", "operational", iso["zd_over_known"], "{:.0f}")
    chk("calibration: isotonic distinct values", "operational",
        op["calibration"]["distinct_values"]["isotonic"], "{:d}")
    n = op["n_test"]
    for name, key, alt in (("CNN", "CNN", ()),
                           ("KG fusion", "CNN + KG fusion", ("29-32 %",)),
                           ("KG causal", "KG (causal)", ("29-32 %",))):
        pct = 100.0 * op["zero_day_depth"][key]["0.5"] / n
        chk(f"depth@50%% zero-day, {name}", "operational", pct, "{:.0f} %", alt=alt)

ood = REC["ood_scores"]
if ood:
    chk("OOD: best Bot", "ood_scores", ood["predictions"]["best_bot_value"])
    cnn = ood["scorers"]["cnn_p_attack"]
    # NOTE: ood_scores puts the CNN's Bot at 0.0448 and ablation.json at 0.0446 --
    # different score files averaged over the same 3 seeds. The gap is ~0.0002,
    # roughly 100x below the 0.0222 noise floor, so neither is "right"; the draft
    # quotes the ablation's, because that is the comparison it appears in. Both
    # forms are accepted here so the checker does not force a false choice.
    chk("CNN Bot (n=3)", "ood_scores", cnn["Bot"], alt=("0.0446",))
    chk("CNN Web BF (n=3)", "ood_scores", cnn["Web Attack Brute Force"],
        alt=("0.92-0.95",))
    chk("CNN XSS (n=3)", "ood_scores", cnn["Web Attack XSS"], alt=("0.92-0.95",))

npd = REC["noise_postdet"]
if npd:
    chk("noise: nondeterminism SD", "noise_postdet", npd["A_preflag_fixed_seed"]["sd"])
    chk("noise: seed SD (det on)", "noise_postdet", npd["C_postflag_varying_seed"]["sd"])
    chk("noise: absolute-number uncertainty", "noise_postdet",
        npd["absolute_number_uncertainty"])

cmp_ = REC["comparability"]
if cmp_:
    chk("duplicate rate", "comparability", 100.0 * cmp_["duplicate_rate_overall"], "{:.1f} %")

kgc = REC["kg_criteria"]
if kgc:
    lifts = [r["lift"] for r in kgc["multiseed"]["growth_ge8"]]
    chk("KG growth lift (mean)", "kg_criteria", sum(lifts) / len(lifts), "{:.2f}")
    chk("KG growth lift (min)", "kg_criteria", min(lifts), "{:.2f}")
    chk("KG growth lift (max)", "kg_criteria", max(lifts), "{:.2f}")

bf = REC["bot_failure_analysis"]
if bf:
    r = bf["results"]
    chk("Bot cross-seed rho", "bot_failure_analysis",
        r["H2b_cross_seed_rank_corr"]["cnn_paper"]["Bot"], "{:.3f}")
    chk("Bot oracle PR-AUC", "bot_failure_analysis",
        r["H4_raw_oracle_separability"]["Bot"]["oracle_pr_auc"])
    chk("Web BF oracle PR-AUC", "bot_failure_analysis",
        r["H4_raw_oracle_separability"]["Web Attack Brute Force"]["oracle_pr_auc"])
    chk("XSS oracle PR-AUC", "bot_failure_analysis",
        r["H4_raw_oracle_separability"]["Web Attack XSS"]["oracle_pr_auc"])
    h3 = r.get("H3_feature_overlap") or r.get("H3_feature_neglect")
    chk("Bot feature overlap", "bot_failure_analysis", h3["bot_overlap_n"], "{:d} of 8")
    chk("AE cross-seed rho on Bot", "bot_failure_analysis",
        r["H2b_cross_seed_rank_corr"]["autoencoder"]["Bot"], "{:.3f}")

ff = REC["fitted_fusion"]
if ff:
    m = ff["mean_over_seeds"]
    chk("fitted fusion: fitted macro", "fitted_fusion", m["fitted"]["macro"])
    chk("fitted fusion: CNN macro", "fitted_fusion", m["cnn"]["macro"])
    # The draft states this comparison as a DELTA (-0.0501), never as an absolute,
    # which is the right choice for a paired result -- so the absolute is recorded
    # as not-quoted rather than flagged.
    chk("fitted fusion: rank-equal macro", "fitted_fusion", m["rank_equal"]["macro"],
        quoted=False)
    pd_ = ff["paired_deltas"]
    chk("fitted fusion: fitted - CNN", "fitted_fusion",
        pd_["fitted_minus_cnn"]["mean"], "+{:.4f}")
    chk("fitted fusion: fitted - rank-equal", "fitted_fusion",
        pd_["fitted_minus_rank_equal"]["mean"], "+{:.4f}")
    chk("fitted fusion: rank-equal - CNN", "fitted_fusion",
        pd_["rank_equal_minus_cnn"]["mean"], "{:.4f}")
    chk("fitted fusion: AE weight share", "fitted_fusion",
        100.0 * ff["predictions"]["F1_fitted_ignores_the_anomaly_channel"]
        ["mean_ae_share_of_abs_weight"], "{:.1f} %")

lat = REC["latency_determinism_on"]
if lat:
    c = lat["components"]
    chk("latency: pipeline us/flow", "latency", c["pipeline_detect"]["8192"]["us_per_flow"], "{:.2f}")
    chk("latency: pipeline flows/s", "latency", c["pipeline_detect"]["8192"]["flows_per_s"], "{:,.0f}")
    chk("latency: cnn batch-1 flows/s", "latency", c["cnn"]["1"]["flows_per_s"], "{:,.0f}")
    chk("latency: cnn batch-8192 flows/s", "latency", c["cnn"]["8192"]["flows_per_s"], "{:,.0f}")
    kg = (c["kg_assign"]["8192"]["us_per_flow"] + c["kg_update_per_window"]["us_per_flow"])
    chk("latency: KG total us/flow", "latency", kg, "{:.2f}")
    chk("latency: IG ms/flow", "latency", c["explain_ig_per_flow"]["median_ms"], "{:.2f}")
    chk("latency: IG/detection ratio", "latency",
        lat["predictions"]["P2_explanation_dominates"]["ratio"], "{:,.0f}")

# ---- claims a human must check by hand -------------------------------------
unbacked("split sizes 883,796 / 110,475 / 114,658", "config.yaml + preprocess_paper.py, not a JSON")
unbacked("zero-day family counts 1,956 / 1,507 / 652", "derived from y_test_mc.npy at runtime")
unbacked("base paper 48.34 % / 47.85 % / 47.24 %", "paper_metrics.json + basepaper.pdf - verify by hand")
unbacked("Tier A/B per-method figures", "baselines_classic.json / deep_zoo.json - not itemised here yet")
unbacked("double dissociation SD multiples (40 / 37 / 3.9)", "derived in STATUS from AE + CNN runs")
unbacked("Web BF / XSS correlation r = +0.992", "robustness.json - not itemised here yet")

# ------------------------------------------------------------------ report --
print("=" * 96)
print("DRAFT VERIFICATION - docs/target/paper_draft.md against outputs/metadata/*.json")
print("=" * 96)
for label, want in OK:
    print(f"  OK        {label:44s} {want}")
for label, want in NOT_QUOTED:
    print(f"  not quoted {label:43s} record has {want} - draft omits it (by choice)")
for label, why in UNBACKED:
    print(f"  UNBACKED  {label:44s} {why}")
for label, want, src in BAD:
    print(f"  MISMATCH  {label:44s} record says {want!r} ({src}.json) - NOT in draft")

print("-" * 96)
print(f"{len(OK)} verified · {len(NOT_QUOTED)} not quoted · "
      f"{len(UNBACKED)} unbacked (check by hand) · {len(BAD)} MISMATCHED")
if BAD:
    print("\nA mismatch means the draft disagrees with the record. Fix the DRAFT unless the")
    print("record is stale, in which case re-run the script that produces it.")
print("=" * 96)
sys.exit(1 if BAD else 0)
