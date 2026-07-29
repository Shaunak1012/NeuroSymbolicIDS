# Conference Roadmap — Path to a Top-Tier Neuro-Symbolic IDS

> Master plan consolidating the base-paper comparison, the revised build plan (v1.2), and the
> conference-grade research agenda. Personal ambition (Shaunak): submit to a top venue.
> Living intent — revise by consensus as results come in.

## 0. The killer thesis (the spine of the paper)

> **Neuro-symbolic *training* (the SOTA Hybrid-LTN) silently fails under realistic class
> imbalance. We show *when and why* it inverts, and that moving the symbolic knowledge from a
> training-time constraint to *inference-time fusion* recovers and exceeds the gain — while
> adding explanation and closed-loop response.**

This is a contribution, not just a system. Most groups cannot make a "here's where the SOTA
breaks" claim; we can, with receipts (measured below). Everything else serves this spine.

**Framing upgrade (2026-06-18):** the paper is structured as an anatomy of **three symbolic
integration points** — (1) *loss-level* (Hybrid-LTN: reproduced, anatomized, fixed via loss-ratio
normalization), (2) *representation-level* (auxiliary behaviour-prediction head — Phase 2d),
(3) *inference-level* (fusion — the primary performance mechanism). LTN training is **kept, not
replaced**: it is the reproduction anchor and the anatomy-study subject; the performance duty
moves to (2)+(3). Rejected alternatives: switching NSAI frameworks (same loss-injection failure
mode), full concept-bottleneck redesign (scope), post-hoc rule overrides (measured −0.16).

## 1. Base-paper comparison (Bizzarri et al., IEEE — `basepaper.pdf`)

| Dimension | Base paper | Us (current) | Action |
|-----------|-----------|--------------|--------|
| Input | Payload bytes (1500) via Payload-Byte | Flow features (68, CICFlowMeter) | **Stay on flow features** (data local; behaviours depend on them; document deviation) |
| Split | Stratified 80/10/10; **known attacks in test**; zero-day = 5–6 *rare* classes | Temporal; **no known attacks in test**; zero-day = PortScan+DDoS (98% of test attacks) | **Adopt paper-aligned split**; keep temporal as secondary "hard mode" |
| Balance | Benign under-sampled → balanced | Full imbalance + focal + class weights | Reproduce balanced for fidelity; imbalance is where we show the failure |
| Axioms | Ax1+Ax2 only | + behaviour-grounded Ax3/Ax4 | Ours is the novel extension |
| Loss | plain CE + ω·SAT, ω=1, Adamax | focal CE + adaptive ω | **Root cause of our LTN failure**: focal CE → ~0.0005, so SAT dominates 40:1 |
| Metrics | Accuracy + F1 | PR-AUC, ROC-AUC, per-family recall | Ours is more rigorous |
| Result | zero-day acc 48→60%, F1 65→75% | (not comparable until protocol matched) | Reproduce their protocol, then beat it |

Verdict: **not flawed, misaligned.** We ran a harder exam with a broken loss balance on a
different modality. Fix the protocol, then compete.

## 1b. ⚠️ CANONICAL PHASE NUMBERING (added 2026-07-29 — read before using the word "Phase")

**The numbering in §2 below is canonical.** Three incompatible schemes were in circulation and one
of them caused a real scoping error (see the box beneath the table).

| Canonical (this doc) | Content | `roadmap_gap_analysis.md` legacy | Status |
|---|---|---|---|
| **Phase 0** | Protocol reset — paper split, config, tracking | (n/a — predates it) | ✅ done |
| **Phase 1** | Neural pillar + baselines + free novelty | Phase A (partial) | ✅ done |
| **Phase 2** | Symbolic pillar — LTN, axioms, failure anatomy, aux head | Phase A (partial) | ✅ concluded |
| **Phase 3** | **Anomaly pillar — benign-only autoencoder** | (not in that scheme) | ⬜ **decision needed** |
| **Phase 4** | **Knowledge Graph + explainability** | Phase B + D | ⬜ next build |
| **Phase 5** | Fusion + rigor (seeds, significance, calibration, latency) | Phase C + E | ⬜ |
| **Phase 6** | Cross-dataset (CIC-IDS2018) | (not in that scheme) | ⬜ |
| **Phase 7** | Paper + reproducibility artifact | (not in that scheme) | ⬜ |
| **Phase R** | Response engine (solo, last) | (not in that scheme) | ⬜ |

> 🔴 **The collision this resolves, and the work it nearly lost.**
> `STATUS.md` was calling the Knowledge Graph **"Phase 3"** while *its own component table* — and this
> roadmap, and a comment in `cnn_auxhead_paper.py` — used **Phase 3 = anomaly pillar / autoencoder**
> and **Phase 4 = KG**. The number was reused, not reassigned by a decision.
>
> **Consequence:** the benign-only autoencoder was on track to be silently skipped. It is not a minor
> item — [enhancements.md](enhancements.md) ranks it **Tier 1, "⭐ highest leverage"**, on the grounds
> that *"reviewers will ask 'why not just an autoencoder?' … Without this, the thesis has an
> unanswered baseline"*, and §3 Tier-S #3 of this document lists it among the
> "baselines that could beat us — included". Estimated cost: **~1 hour.**
>
> **This is now an explicit open decision, not a default.** The one datum that bears on it:
> `IsolationForest` (the unsupervised baseline that *does* exist) scored macro **0.0628** — far worse
> than every supervised channel — *but* **0.0571 on Bot, statistically indistinguishable from the
> CNN's 0.0591.** So the unsupervised family is dreadful overall yet competitive on the one family
> that actually matters. That makes the autoencoder result genuinely unpredictable, which is an
> argument for running it rather than assuming it. Logged in
> [STATUS.md → Open Decisions](../STATUS.md#open-decisions).

## 2. Build plan v1.2 (agreed order)

Each phase ends in a publishable-quality artifact, so stopping early still yields a complete project.

| Phase | Content | Est. |
|-------|---------|------|
| **0 — Protocol reset** | Paper-aligned split (8 major attacks incl. PortScan/DDoS in train; Bot/Web×3/Infiltration/Heartbleed as zero-day; stratified 80/10/10; benign under-sampled). Keep temporal as secondary. Persist **IP/timestamp side-table** (unblocks RepeatedConnections + response replay). `log1p` A/B on heavy-tailed features. **Set up experiment tracking (TensorBoard/MLflow) + `config.yaml` NOW.** Decide corrected-labels (Engelen 2021). | ~1 session |
| **1 — Neural pillar + free novelty** | Retrain CNN in our venv (fixes Keras-3 model mismatch). Add post-hoc **Mahalanobis on embeddings** + **energy/max-logit** novelty scores. Add classical baselines: **XGBoost, Random Forest, Isolation Forest**. | ~2h CPU |
| **2 — Symbolic pillar, done right** | (a) Faithful paper reproduction (Ax1+Ax2, plain CE, ω=1). (b) LTN v2 with **loss-ratio normalization** (SAT scaled to a fixed fraction of CE magnitude — the fix for the diagnosed instability) + ScanProbe axiom, now trainable. (c) **Failure-anatomy grid**: ω × loss-type × balance → phase-transition plot. (d) **Auxiliary behaviour-prediction head** — multi-label head predicting the 6 fuzzy behaviours from the shared embedding (representation-level symbolic injection; doesn't fight CE; makes embeddings behaviour-aware for the KG). | ~3–4h CPU |
| **3 — Anomaly pillar** | Benign-only **autoencoder** → reconstruction-error score (zero-day-legitimate, no attack labels). | ~1h |
| **4 — KG memory + explainability** | NetworkX clusters/decay/emerging patterns as **corroboration + reasoning paths** (not primary detector). HITL becomes a demo. | ~1–2 sessions |
| **5 — Fusion + rigor** | Interpretable logistic fusion over all signals (legitimately trainable under new split). Calibration + **abstain**. Latency benchmark. **3–5 seeds + significance tests.** Full ablation. | ~1 session + reruns |
| **6 — Cross-dataset** | Train 2017 → test **CSE-CIC-IDS2018** (free, AWS Open Data; same CICFlowMeter features → behaviours transfer). **Go/no-go decided at Phase-5 exit.** | ~1 session + download |
| **7 — Paper + artifact** | Reproducibility package, `run_all`, released weights/seeds, venue CFP check. | ~1 session |
| **R — Response engine (SOLO, last)** | Symbolic graduated **response policy** over Final Alerts (ScanProbe→block IP, DDoS→upstream filter, low-conf→escalate). Evaluated by **temporal-replay containment** + **collateral-damage** (benign wrongly blocked) + time-to-containment. Framed as *simulated response on replayed traffic*, never a deployed IPS. | personal track, final |

Full arc: **Detect (CNN + novelty + AE) → Reason (behaviours + LTN) → Remember/Adapt (KG) →
Decide (fusion + abstain) → Explain (3-channel) → Respond (policy engine).**

## 3. Conference-grade agenda ("godly" tier)

Ranked by **conference impact per unit effort.** The paper's spine is Tier-S; modules are the systems story.

### Tier S — do these or it isn't top-tier
1. **Failure-anatomy study as science** — controlled grid (ω × loss × balance), phase-transition figure "zero-day PR-AUC vs CE/SAT loss ratio", with the loss-magnitude explanation. **The headline.**
2. **Statistical honesty as a weapon** — mean±std over 3–5 seeds + **significance tests** (paired bootstrap / Wilcoxon on per-flow scores) + CIs. Disarms "is it noise?".
3. **Baselines that could beat us — included** — XGBoost, Isolation Forest, autoencoder, faithful base-paper Hybrid-LTN. Report honestly where we lose (likely known-attacks to XGBoost) and pivot claim to zero-day + explanation + response.
4. **Reproducibility artifact** — public repo (✓), pinned env (✓), one-command `run_all`, released fusion weights + seeds. Target "Artifacts Evaluated" badge.

### Tier A — makes it memorable
5. **Explanation *faithfulness*, measured** — deletion/insertion curves (remove top-attributed features → confidence should drop). Turns "explainable" from claim to measurement. ~1 day.
6. **Cross-dataset generalization** (Phase 6) — strongest external-validity signal.
7. **Adversarial robustness probe** — can flow-feature perturbation evade? Hypothesis: symbolic axioms degrade more gracefully than the CNN (a scan is structurally short+empty regardless). A hot result if it holds.

### Tier B — adaptive/response story (systems + solo track)
8. **Concept-drift evaluation** for the KG (does adaptive memory help as traffic shifts?).
9. **Response engine** with containment + collateral-damage metrics (Phase R, solo).

**Priority ranking:** #1 > #2 > #3 > #5 > #6 > #4 > #7 > KG/drift > IPS.

**Mindset shift for "godly":** stop asking "what else can we add?"; ask "what would a hostile
reviewer attack, and can I already show the experiment that defends it?" Every Tier-S item is a
pre-emptive strike against a specific reviewer objection. Resist kitchen-sink — a tight paper on
"when does neuro-symbolic IDS training help, and the fusion alternative" beats a sprawling
six-pillar system with weak stats.

## 4. Venue strategy

- **Build to RAID / ACSAC / DSN / ESORICS standard** (realistic-but-prestigious; ~20% accept).
- **Strong-fit fallbacks:** **AISec** (ML+security workshop @ CCS — exactly this genre) and the
  **NeSy** conference (neuro-symbolic home). Also MILCOM-adjacent (the base paper's community).
- Top-4 (S&P/USENIX/CCS/NDSS) is a lottery ticket for this timeline — build one tier up in rigor,
  submit where the deadline aligns at ~80% done.

## 5. Data status (reference)
- All 8 CIC-IDS2017 raw CSVs + processed data are **local** — no re-download for 2017.
- CIC-IDS2018: **free**, AWS Open Data `s3://cse-cic-ids2018` (large; subset needed).
- Corrected labels: Engelen et al. 2021 — adopt or run sensitivity check (pre-empts reviewer criticism).
- Payload-byte modality (paper-faithful) would need ~50 GB PCAPs + tooling — **deferred/out of scope.**

## 6. Scope note
This is ~2–3× the original capstone scope, layered so the team deliverable is safe (complete at
Phase 5) and Phases 6–7 + R are the conference/personal overdrive. The IPS (Phase R) is Shaunak's
solo modification, intentionally last.
