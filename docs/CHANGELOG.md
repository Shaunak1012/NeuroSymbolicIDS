# Changelog (Living Document)

> Append a dated entry whenever something meaningful changes (code, data, decisions, results). Newest first. Keep entries short; link to detail docs.

## 2026-09-05c (the fusion wall was OVERSTATED — a pre-registered falsifier fired. **Phase 5 complete.**)

### 🔴 `paper_outline.md` §5's "a fitted fuser is structurally impossible here" is RETRACTED

`fitted_fusion.py`. The claim had **never been tested on the real channel set** — it was generalised
from `fusion_beaconlike.py`, a **two-channel special case** (CNN log-odds + the `BeaconLike`
behaviour) returning `[2.35, 0.02]`. **Generalising a blocker from a special case is the same defect
class this project keeps retracting, pointed at a negative claim instead of a positive one.**

Logistic combiner over **CNN** + **autoencoder**, fitted on validation (benign vs *known* attack;
**0 zero-day flows, asserted in code, not assumed**), applied blind to test, seeds 42/43/44.
Achieved FPR **0.0100 exactly on all three** — no tie-block degeneracy.

| channel | macro | Bot | Web BF | XSS |
|---|---:|---:|---:|---:|
| CNN | 0.6399 | 0.0448 | 0.9226 | 0.9524 |
| autoencoder | 0.0970 | 0.1314 | 0.1048 | 0.0547 |
| **fitted (logistic)** | **0.6502** | **0.1007** | 0.9126 | 0.9371 |
| equal-weight rank fusion | 0.5898 | 0.0940 | 0.8401 | 0.8352 |

Coefficients (standardised): **CNN +12.76 / +10.08 / +11.25 · AE +1.53 / +1.86 / +4.27** — both
**positive every seed**, AE holding **17.9 % of absolute weight** on average.

| paired delta | mean | σ | ÷σ | seeds |
|---|---:|---:|---:|---:|
| fitted − equal-weight rank | **+0.0604** | 0.0241 | **2.51** | 3/3 |
| **equal-weight rank − CNN** | **−0.0501** | 0.0116 | **4.34** | 3/3 |
| fitted − CNN | +0.0103 | 0.0129 | 0.80 | 3/3 |
| fitted − CNN (Bot) | +0.0560 | 0.0405 | 1.38 | 3/3 |

**F1, F2 and F3 all FALSIFIED; F4 — the falsifier written down in advance — TRIGGERED.**

### What is refuted and what survives are different things

🔴 **REFUTED**: *"structurally impossible"* · *"the combiner learns to ignore the zero-day-useful
channel"* · *"zero macro change"*. All false for CNN+AE. `[2.35, 0.02]` was a property of
**BeaconLike**, not of fitted fusion.

✅ **SURVIVES, and is now the WHOLE wall**: **the KG cannot be fitted at all** — its burstiness is
defined by streaming the **test** set into windows, so there is **no validation-side score by
construction**, and the channel with the largest measured gain (+0.0527) is the one a combiner
structurally cannot weight. Needs no number; untouched by this run.

🔑 **Why the wall was overstated — the transferable part.** Its premise (*a channel whose value is
specifically on NOVEL classes is invisible to a zero-day-free objective*) is **correct** and simply
**does not apply to the autoencoder**: known attacks are anomalous too, so reconstruction error
separates benign from *known* attacks on validation and that weight transfers. `BeaconLike` genuinely
**is** zero-day-specific (97.6 % of PortScan, **0.0 %** of every other known attack) — which is
exactly why it got 0.02. **The wall applies to zero-day-SPECIFIC channels; the KG is the example.**

⚠️ **Not a headline.** fitted − CNN is **+0.0103 at 0.80σ** — direction 3/3, **magnitude not
established**. It does not replace CNN+KG (+0.0527, magnitude 0.027–0.088).

### 🔴 A qualification of the project's OWN parameter-free result

**Equal-weight rank fusion of CNN+AE loses to the CNN by −0.0501 (3/3, 4.34σ).** Parameter-free
fusion is **not** universally the safe choice: equal weights cannot express *"this channel is worth a
sixth of that one"*, so they help with a comparable partner and harm with a weak one.
**`fusion_multi.py`'s +0.0527 is a result about the KG, not about equal weighting** — and the outline
now says so next to it.

### ✅ PHASE 5 IS COMPLETE

significance ✅ · parameter-free fusion ✅ · n≥6 seeds ✅ · calibration ✅ · latency ✅ ·
**fitted fuser ✅**. Record: `outputs/metadata/fitted_fusion.json`.

## 2026-09-05b (latency measured — Phase 5's last open measurement, and a fifth status-drift defect)

### ⏱️ `latency.py` — per-component, per-batch, two determinism arms

`enhancements.md` #6 scoped this as *"one benchmark — 'X flows/sec on CPU, KG adds Y ms'"*.
**The script deliberately refuses to emit that single number**: the CNN runs at **256 flows/s at
batch 1 and 158,919 at batch 8192, a 620× spread.** A throughput figure without its batch size is
not a claim. Median + IQR over 15 repeats, warm-up discarded, never a mean — latency on a shared
desktop is right-skewed.

| component (batch 8192) | µs/flow | flows/s |
|---|---:|---:|
| `behaviours` | 0.094 | 10.6 M |
| `kg_assign` | 0.059 | 16.9 M |
| `kg_update` (amortised) | 0.519 | — |
| `transform` | 0.680 | 1.4 M |
| **`cnn`** | **6.293** | **158,919** |
| **full detection path** | **7.952** | **125,750** |
| 🔴 **`explain_ig`** | **11,946** | **84** |

**① Detection is not the bottleneck** — the whole test set scores in **0.91 s**. Do not claim
throughput as a contribution.
**② The KG is essentially free** — 0.58 µs/flow, **+9.2 % over the CNN**. That is the answer to
"KG adds Y ms", and it means cost is not the objection to the KG.
**③ 🔴 Explanation costs 1,898× detection.** IG is 32 forward+backward passes per flow.
Explaining all 114,658 flows = **23 min**; explaining **100 alerts = 1.19 s**. **Explain alerts, not
flows** — which composes with Tier 1's alert-budget result instead of fighting it. ⚠️ **The
project's selling point is the expensive half**; an "explainable IDS" claim implying per-flow
explanation is a 4-orders-of-magnitude error.

### 🔴 P3 FALSIFIED — and the reasoning error is the transferable part

Predicted `kg_assign` (200 distances/flow) would dominate `kg_update` (a few edge writes per window).
**The opposite, by 9×** — update 0.519 µs/flow vs assign 0.059. `km.predict` on a batch is one BLAS
matmul; `observe()` is a **Python loop** over ~200 clusters × 6 behaviours doing NetworkX dict
updates. **The prediction reasoned from algorithmic work when the determinant was
vectorised-vs-interpreted execution.** Nothing downstream changes — both are trivial — but the
reasoning was wrong and is recorded as wrong.

### ✅ Determinism costs 2–7 % throughput — the noise-floor fix was nearly free

`cnn` 6.293 → 6.744 µs/flow (1.07×), full path 7.952 → 8.128 (1.02×). ⚠️ **Do not read `kg_update`'s
1.44× as a determinism effect** — it is pure Python, untouched by TF threading, and the OFF arm's
IQR (2.824–4.359) contains the ON median. Run-to-run noise, which is why the script reports IQR.

### 🔑 The `KnowledgeGraph` class is `exec`'d from `kg.py`'s own source, and it earned its keep

`kg.py` cannot be imported (top-to-bottom script), so the class node is located with `ast` and
exec'd from source rather than hand-copied. **The first run then raised `NameError: behavior`** —
a module-scope dependency in `__init__` that a hand-copied class would have silently dropped, leaving
the benchmark measuring a subtly different object. The fix resolves `kg.py`'s module-level names
against the ones `latency.py` already holds, so a *new* dependency is picked up rather than needing
another fix.

### 🔴 NEW CRITICAL ISSUE, raised BY the latency work: the fusion gain is transductive

`fusion_multi.py` fuses with `rankdata(score)/n` — **a global operation over the scored set**, so a
flow's fused score depends on the other 114,657. The project's **only positive result** (CNN+KG
**+0.0527**) is therefore a **transductive** estimate. **Not leakage, not a bug** — but Phase 5's
purpose is deployability and **a streaming IDS cannot compute this score.** How much a frozen-
reference variant would move it is **unmeasured**, and the issue asserts nothing about direction.
🔴 The KG channel is transductive *by construction* (burstiness is defined over test windows), so a
streaming variant is a **design change, not a re-scoring**. Filed in
[KNOWN_ISSUES](KNOWN_ISSUES.md) with the confirming experiment specified.

### 🔴 FIFTH COMPONENT-STATUS DRIFT DEFECT — a different shape from the first four

Non-negotiable #7 was **satisfied**: one Component Status table, in STATUS.md. The drift was *inside*
STATUS. **Calibration is scope for BOTH Phase 5 and Phase 7.5 Tier 1.** `operational.py` delivered it
2026-08-05, Tier 1's row was flipped, and the three Phase-5 sites plus `conference_roadmap.md` were
not — so the project believed it owed a deliverable it had already shipped, and the 2026-08-10
session listed it as outstanding twice. **The single-table rule fixes duplication across FILES and
does nothing about duplication across PHASES.** `paper_outline.md` had it right on 2026-08-10, in a
file nobody reconciled against STATUS.

Also corrected: STATUS's "still open before submission" listed **figures 2–5** (built 2026-08-10) and
**latency**; `conference_roadmap.md` listed Phase 7.5 as **"⬜ not started"** (Tiers 1 & 2 done
2026-08-05) and n≥6 seeds as outstanding (done 2026-08-04). ✅ **Honest limit on the calibration fix:**
`operational.json` persists **scalar ECE per subset**, not per-bin reliability curves — recorded as a
partial rather than rounded up to done.

**Phase 5 now has exactly one item left: the *fitted* fuser, and the deliverable is to write the
blocker as a result.**

## 2026-09-05 (the payload question, answered from the record — and two doc defects it exposed)

### 🔴 DECIDED: payload / raw PCAP is OUT OF SCOPE, not deferred-and-desirable

Asked whether adding payload to the pipeline would improve results. **No — and it was already
measured.** No new runs; the answer came out of `outputs/metadata/bot_failure_analysis.json`.

The **H4 oracle probe** (XGBoost, family-vs-benign, fit/eval split inside the test set) separates
every adequately-powered zero-day family from benign **using the 68 flow features alone**:

| family | oracle PR-AUC (flow features, *with* labels) | CNN, closed-set | chance |
|---|---:|---:|---:|
| Bot | **0.9988** | 0.0321 | 0.0342 |
| Web Attack Brute Force | **0.9999** | 0.9147 | — |
| Web Attack XSS | **0.9984** | 0.9430 | — |

**There is no missing information for payload to supply.** The Bot gap — 0.9988 down to 0.0321 — is
**100 % a closed-set-supervision gap and 0 % a modality gap.**

⚠️ **And the mechanism is basis-agnostic, which is the load-bearing argument.** H3 shows Bot's oracle
top-8 has **0/8 overlap** with the features the 9-known-class task selects (Web BF: 1/8). A closed-set
model trained on payload bytes learns whatever *payload* features separate those same nine classes, so
a novel class is again reachable only through overlap — **the failure relocates, it does not dissolve.**

✅ **Corroborated by the base paper, which *is* the payload version.** Bizzarri et al. use 1500 payload
bytes: we beat them **18–29 pp on all four known-class views** while their 1D CNN's zero-day number
matches ours (**48.34 % vs 47.85 %**). Payload costs known-class performance and buys nothing on
zero-day.

⚠️ **Where payload *would* genuinely help is the wrong place.** It would replace the web families'
**absorption** (~90 % of Web BF/XSS assigned to `DoS slowloris`, a known *attack* class) with real
detection — an **honesty** gain, not a metric one, since those families already score 0.91–0.95.
**All the headroom is in Bot, and Bot is exactly where payload adds no information.** The payload gain
and the performance headroom are in different families.

Recorded in [STATUS.md](STATUS.md) → Open Decisions → *Input modality* (with the full cost side: ~48 GB
of PCAP not held locally, packet→flow alignment through the one field with two documented defects, a
header/User-Agent leakage surface `audit_leakage.py` does not cover, plaintext-2017 ecological
validity, and a forked record). **Revisit only** to test basis-independence of the mechanism — a
separate paper, not a Phase-5 task. It does **not** touch the fusion wall, which is the actual blocker.

### 🔴 The strongest pro-payload sentence in this file was wrong — corrected in place

The 2026-08-02 entry says web attacks are undetectable in flow space because *"what makes them
malicious is payload content, which this feature set lacks."* **Wrong as an information claim**, and
contradicted by a measurement taken the next day — the same file's 2026-08-03 entry already asks
*"given the oracle result proves the information is present in the features"* without anyone
reconciling the two. Annotated in place per the retract-in-place convention, **not rewritten**.

**The narrower statement survives and is the one to cite:** web attacks sit inside the benign region
*of a benign-only reconstruction manifold*, so the AE's 0.0000 recall is a fact about **unsupervised
density modelling**, not about the modality. The same correction is added to
[STATUS.md](STATUS.md)'s already-struck "modality analogue" section — which was struck for the
*modality-analogue mechanism* only, leaving this sub-claim liftable as though it had survived.

### 🔴 `dataset.md` misattributed the botnet for the whole life of the project

Friday-morning Bot was labelled **Mirai**. CIC-IDS2017 used **Ares**, a Python HTTP C2 framework;
Mirai (IoT/telnet) is not in this capture. Labels unaffected — attribution only — but it is exactly the
fact a payload argument turns on: **Ares C2 is plaintext HTTP**, so reasoning about a payload channel
from Mirai's telnet behaviour would be reasoning about the wrong traffic. `docs/archive/` keeps the old
attribution and is deliberately left frozen.

### Also

[paper_outline.md](target/paper_outline.md) §8.3 now **answers** "why not payload?" instead of
conceding it, and states the honesty cost the paper does not get to claim.

**No result changed. No script ran.** Every number above was already in `outputs/metadata/`.

## 2026-08-20 (the live console now shows the Phase-4 knowledge graph)

### 🖥️ `dashboard_server.py` — KG panel, figure grid, and two static routes

The console reported ops state (CPU/RAM, git, processes, log tail, `runs.jsonl`) but nothing about the
KG, which is the largest built artifact in the project. Added, all read fresh per 4 s poll:

- **KG panel** from `outputs/metadata/kg*_report.json`: graph structure (215 nodes / 1190 edges /
  200 clusters / 53 emerging), the burstiness metrics, the lateness-confound table, sample explanation
  paths, and the report's `caveats` rendered verbatim.
- **Figure grid** over `outputs/figures/*.png` (8 figures).
- **`/kg`** serves the interactive `kg_graph.html`; **`/figures/<name>`** serves a tracked figure.
  Path handling is `os.path.basename()` + extension allow-list; traversal verified 404.

### 🔴 Every KG number on the panel carries its across-seed range

Lift renders as `6.1125×` **with** `n=3 seeds: 5.658–6.112`; precision `0.4303` with `0.398–0.430`. The
range is computed from however many `kg*_report.json` files exist, so it widens automatically rather
than needing a doc update. **A console that displays a bare point estimate is a machine for recreating
the retracted "81 % precision" claim** — which was clustering-seed 42 only. `n=1` renders as
"n=1 — provisional", not as a number.

**No result changed.** This is a presentation layer over existing `outputs/metadata/*.json` — it computes
nothing, so it cannot diverge from the record. Detail in [DASHBOARD.md](DASHBOARD.md).

## 2026-08-10d (figures 2–5 built — and one of them caught a statistics error of mine)

### 📊 `paper_figures.py` — all five figures now exist and regenerate from the record

Reads `outputs/metadata/*.json` only: **no training, no scoring, no recomputation**. A figure and the
outline therefore cannot silently diverge — if they disagree, one is stale and it is discoverable.
**Each figure prints its own caveat**, because a figure lifted into a talk loses its paragraph.

### 🔑 A statistics error caught by building fig. 4 — read before citing any ablation number

The first version coloured each ablation rung by |Δ| against the **0.0222** noise floor, and rendered
**`FULL vs CNN+KG` (−0.0218) as noise** — contradicting STATUS, which reports it as established.
Investigating that disagreement showed **the figure was wrong, not the record**:

**0.0222 is the run-to-run SD of an ABSOLUTE number, and over shared seeds that common variance
cancels** — exactly as this project already documents for the data-split SD. Against the **paired**
difference's own SD (0.0013), the effect is **16.3σ across 3/3 seeds**, the tightest in the ablation.

**The correct criterion is direction-consistency across all seeds plus the paired effect size**, and
the two can disagree:

| rung | Δ | paired σ | seeds |
|---|---:|---:|---:|
| CNN + KG vs CNN | +0.0528 | **1.7σ** | **3/3** |
| FULL vs CNN + KG | −0.0218 | **16.3σ** | **3/3** |
| CNN + LTN-ctrl vs CNN | +0.0035 | 0.6σ | 2/3 |
| CNN + LTN-Ax6 vs CNN | −0.0004 | 0.1σ | 2/3 |

**CNN+KG's DIRECTION is certain (3/3) while its MAGNITUDE is not** (1.7σ, spanning 0.027–0.088) —
which is exactly what STATUS already said, now visible on the figure. ⚠️ **This error ran in the
*safe* direction** (it would have discarded a real result rather than inventing one), but it is the
same class as the mistakes that produced false positives here. Recorded in `paper_outline.md §7`.

## 2026-08-10c (the paper's canonical thesis was stale — retracted, respined, outlined)

### 🔴 `conference_roadmap.md §0` — the "killer thesis" is RETRACTED

The canonical thesis statement, unchanged since 2026-06-18 and the thing every write-up decision was
supposed to serve, promised that **"moving the symbolic knowledge from a training-time constraint to
inference-time fusion recovers and exceeds the gain."** **Our own measurements falsify the second
half**, and it had sat there for weeks after they landed:

- The **ablation** (n=3 paired) puts the symbolic pillar at **−0.0004 (n.s.)** alone and shows it
  **significantly HURTS** stacked on the KG (0.6926 → 0.6708, **p<0.0001**).
- The **fusion wall** makes the general claim unreachable under this protocol — validation contains
  no zero-day by construction, so a fitted combiner cannot learn to weight a zero-day channel.
- **Only the KG earns its place**, and a KG is not "symbolic knowledge moved to inference time" in
  the sense the sentence promises.

⚠️ **Retracted in place, not repaired.** Weakening the sentence until it survives would have produced
a thesis nobody measured. **§0b now carries the current spine** (field-metric gap leads, mechanism is
the body, double dissociation demoted to support), with both refuted strong forms listed inline.

### 📋 `docs/target/paper_outline.md` — claim → evidence → caveat

Section-by-section plan in which **every claim carries its number, the script that produced it, and
the limit that must be stated with it.** The third column is the point: this project's recurring
failure is not wrong numbers but **right numbers written without their limits**. *If the caveat
column is empty, the claim is not ready to write.*

- **DO-NOT-WRITE rows are included deliberately** — each is either something believed here at some
  point or the obvious stronger version of a supportable claim: "the published metric carries no
  information" (ρ=+0.568 refutes it), "the conjunction gives 81 % precision" (seed-42 only), the KG's
  "unexplained cluster" mechanism (lift ≤ 1.00×), the (A)/(B) framing, the modality analogue.
- Every quoted figure was **cross-checked against `outputs/metadata/*.json`** rather than copied from
  prose: ρ +0.568 · 67/204 · field noise SD 0.0020 · seed SD 0.0171 (F=1.69, p=0.58) · absolute
  uncertainty 0.0285 · Deep SVDD R1 NOT ESTABLISHED (p=0.256).
- **§7 makes measurement discipline a section, not a footnote** — the §1 claim is itself a
  measurement claim, so our standards have to be visibly higher than the field's.
- **§8 limitations written before a reviewer writes them**, led by the weakest point: single dataset,
  cross-dataset blocked on data availability.
- 4 of 5 figures still to build.

## 2026-08-10b (the noise floor is settled — the threshold stands, and n=3 was the trap)

### 🔴 `noise_postdet.py` — P1 falsified, P2 confirmed, threshold unchanged

Predictions **committed to git before the runs finished**. Population A **verified** to reproduce the
documented floor (SD 0.0222, spread 0.0622) rather than assumed to be the right six runs.

| population | measures | SD (n=6) |
|---|---|---:|
| A pre-flag, seed fixed | nondeterminism only | **0.0222** |
| B pre-flag, seed varies | both | 0.0189 |
| **C post-flag, seed varies** | **seed alone** | **0.0171** |

- 🔴 **P1 FALSIFIED.** Post-flag seed SD is **0.0171**, not the 0.0035 that C4's n=3 suggested.
  **F(5,5)=1.69, p=0.58 — indistinguishable from the nondeterminism floor.** **The ~0.0256 threshold
  stands and C2 stays retracted on its own merits.**
- 🔴 **The lesson, new for this project: n=3 is enough for a MEAN and nowhere near enough for a
  VARIANCE.** Two n=3 SD estimates (0.0031, 0.0039) **agreed with each other**, which felt like
  corroboration and was not. C4's log1p arm drew three seeds within 0.006; **seed 45 returned 0.5882**
  and moved the SD **5×**. ⚠️ **The project's own rule was followed and still gave a wrong number** —
  it is calibrated for means and was applied to a variance. **Sample-size adequacy depends on the
  statistic, not the count.**
- ✅ **Flag-then-confirm worked.** Filed `[OPEN]`/provisional with the confirmation run specified
  rather than acted on. Loosening the threshold to ~0.006 would have flipped **every** "within noise"
  verdict in the project. Round-trip flag → answer: **one session.**
- ✅ **P2 CONFIRMED — the "session effect" is explained and gone.** ρ vs seed number goes from
  **−0.943 pre-flag to −0.086 post-flag**; the monotonic decline tracked **run order**, not seed.
  A claim asserted and withdrawn on 2026-08-03 finally got an experiment. **Post-flag seeds are
  comparable across sessions** (`det_verify_a` == `c4_log1p_s42` to twelve decimals, five days apart).
  ⚠️ Removes a **confound**, not the **uncertainty**.
- ✅ **P3 CONFIRMED** — √(A²+C²) ≈ B within the n=6 consistency band (ratio 0.67).
- ⚠️ **Data-split SD 0.0228 untouched**: an absolute number carries **0.0285**, not 0.0198.

### 🔴 Process: non-negotiable #2 was bypassed twice — the compliant path did not exist

**Caught by the user asking why there was no heartbeat monitor.** Two long jobs ran as
`nohup scripts/<launcher>.sh &`. Root cause: **`run_long.sh` hardcoded the Python interpreter**, so a
multi-step *shell* launcher could not be run through it at all.

- The lapse did not feel like rule-breaking: the bespoke launchers were careful in every way the docs
  warn about, and **having satisfied the *reasons* behind the rule I substituted my own launcher for
  the one the rule names** — CLAUDE.md's own "plausible-but-wrong substitute" mechanism.
- **Cost:** `run_long.sh --watch` emits on every log-growth tick; the `Monitor` armed instead fired
  only on terminal events, so it emitted **nothing for ~50 minutes**. It was alive and working as
  written, but **silence is indistinguishable from a dead monitor** — the "silence is not success"
  rule failed on the **liveness** axis rather than the failure axis.
- **Fixes:** `run_long.sh` now accepts `.sh` launchers (self-tested); monitors on long jobs emit a
  **positive heartbeat on a timer** (epochs + process count + log size).
- ⚠️ **Also mis-sized the machine**: read `cpu_count()`=32 as 32 cores when it is **16 physical /
  32 logical** (Ryzen 9 9950X3D), so three concurrent trainings at `intra=16` were **3× oversubscribed
  on physical cores** and made the user's machine unusable for gaming. **Default to one training at a
  time on a shared machine.**

## 2026-08-10 (the two flagged n=1 results are settled — one dies, one is corrected)

### 🔬 `seed_recheck.py` — resolving Remaining Work #1

Both Tier-C C1 and the Tier-A Bot column were **flagged before publication** on 2026-08-05 (a first,
after five retractions) and are now multi-seeded to n=3. Aggregation reads `runs.jsonl`, not the
logs, so every number is reproducible from the committed record.

- 🔴 **R1 — "Deep SVDD beats the autoencoder on Bot" is DEAD.** Bot across seeds:
  **0.1558 / 0.1275 / 0.1950** = 0.1594 ±0.0339, vs the AE's 0.1291 ±0.0199 (n=6). Delta +0.0304,
  ranges **overlap**, Welch **t=1.43 p=0.256** → **NOT ESTABLISHED**.
  **The pre-registered verdict flips seed by seed: CONFIRMED / FALSIFIED / CONFIRMED.** The same
  unmodified script reports opposite conclusions depending only on which seed ran — the clearest
  demonstration of the n=1 problem this project has produced, because the flip was *observed* rather
  than inferred after a retraction.
- ⚠️ **R2 — the Tier-A Bot column is REPRODUCIBLE (ρ = +0.770), and the flag's stated reason was
  WRONG.** KNOWN_ISSUES predicted noise-domination like the CNN's (ρ = −0.090); it is the opposite.
  The correlation is **degeneracy, not signal**: **5 of 7 models have Bot SD exactly 0.0000** because
  GaussianNB / LogisticRegression / LinearSVC have **no stochastic component** — the seed changes
  nothing about them — and **2 of 7 sit at exactly the chance value 0.0342**, their tie blocks
  swallowing every Bot flow. Whole-tier lift **0.64×–1.21×**. **Reproducible and meaningless.**
  The conclusion (don't cite Tier-A Bot numbers) is unchanged; the reason is corrected in place.
- 🔴 **R3 — the biggest defect was anticipated by neither flag: k-NN's macro collapses 10× at seed
  44**, 0.4270 → **0.0440** (Web BF 0.6786 → 0.0805, XSS 0.5682 → 0.0173), spread **0.3830**. The
  only thing the seed changes for k-NN is **which 50,000 rows it memorises**, so the subsample
  deviation recorded as "stated not hidden" *dominates the result*. New `[OPEN]` issue.
- ⚠️ **The MLP's "best valid Tier-A result, 0.5360" is a 3-seed mean of 0.4965** — which widens the
  gap to the CNN, so **the conclusion strengthens while the number retracts**. For all three unstable
  models **seed 42 was the highest draw** (observation, not established bias — they were selected for
  instability).
- ✅ **Tier C's actual finding survives**: LOF macro **0.3360 ±0.0135**, so *"benign-only ⇒ collapses
  on web attacks" is a property of reconstruction-error scoring, not of the (B) family* is robust.
- 🔴 **A verdict-design lesson, applied to my own script.** A single boolean would have printed
  *"Bot column is RANKABLE"* — technically true and the most misleading sentence available.
  `seed_recheck.py` reports **reproducibility and informativeness separately**. This is
  `robustness.py`'s "an automated verdict that cries wolf is worse than none", inverted: **a verdict
  that declares victory is the same defect.**

### 🧭 Write-up spine decided — and its strong form refuted the same day (`field_gap.py`)

**Decision (user): the field-metric gap leads, the mechanism is the body**, the double dissociation
demoted to a supporting result. `field_gap.py` puts **all 40 measured methods on one axis** for the
first time (they previously lived in four separate tier sections) and computes the number the
argument turns on — the rank correlation between the field's metric and ours.

- 🔴 **"The published metric carries no information about zero-day detection" is FALSE.**
  **ρ = +0.568 (p=0.0001)**, and still **+0.41** restricted to the field's own ≥0.98 reporting
  regime. It is a real, if weak, proxy. **Do not write the strong form.**
- 🔴 **"Its spread is below its own noise" is also FALSE.** The field metric is *precise* — median
  run-to-run **SD 0.0020**, ~10× below its spread.
- ✅ **What survives is a RESOLUTION failure, and it is enough: 67 of 204 method pairs (33 %) are
  indistinguishable on the field's metric while differing ≥2× on macro zero-day.** Worst case
  `deep_cnn_lstm` vs `ltn_anat_w2p0` — **0.0028 apart on the published number, 18× apart on
  zero-day**; `fusion_cnn_kg` vs `deep_transformer` **0.0006 apart, 6× apart**.
- ⚠️ **`xgboost_oracle` excluded from the correlation** — it trains on ~1,000 zero-day labels, so it
  is an upper bound rather than a method under protocol, and as a lone extreme high-high point
  (FIELD 1.0000 / MACRO 0.9899) it inflates any correlation containing it.
- **Both refutations are hard-coded into the script's output** so the strong form cannot be
  re-derived by accident. **The strong form was measured before it was written** — the first time in
  this project that has happened *before* committing to a framing rather than after retracting one.

### ✅ C4 CLOSED — the transform is now justified on the metric that matters

The last open item from the 2026-07-29 audit. 3 seeds per arm, 50 epochs, determinism on.

| arm | macro zero-day | Bot | Web BF | XSS |
|---|---|---:|---:|---:|
| **log1p** | **0.6299 ± 0.0031** | 0.0321 | 0.9147 | 0.9430 |
| raw | 0.1606 ± 0.0039 | 0.0204 | 0.2953 | 0.1662 |

- ✅ **log1p wins by Δ +0.4693**, ranges do not overlap, Welch **t=163 p<1e-6** — **15×** the ~0.032
  uncertainty an absolute number carries. Worth **5.7× on XSS**, **3.1× on Web BF**.
  ⚠️ **Bot is at/below chance in both arms** (0.0321 / 0.0204 vs chance 0.0342) — not evidence about
  the transform.
- ⚠️ **The conclusion was right and the justification was wrong; those are separate facts.** Had raw
  won, the project would have been running the wrong transform since Phase 0.3 on the strength of a
  metric `metrics.py` forbids. **The re-run was necessary regardless of outcome.** `config.yaml` now
  cites these numbers with the superseded justification kept beside it.
- ✅ **The code change was verified, not asserted.** `c4_log1p_s42` returned **0.629768308213**,
  identical to `det_verify_a`/`det_verify_b` **to twelve decimals** — so the `FEATURE_TRANSFORM`
  override is provably inert at the config default, and determinism reproduces a third time in a new
  session. One training bought a decisive check on my own edit.
- 🟡 **Unexpected by-product: the noise floor may be mostly nondeterminism, not seeds.** SD 0.0222 was
  six runs of *seed 42 with determinism OFF*. C4 ran *three different seeds with determinism ON*,
  twice, and got **SD 0.0031 / 0.0039** — ~6–7× smaller. If confirmed, the dominant variance source
  was never the seed. 🔴 **Not acted on: n=3, one model, and data-split SD 0.0228 still applies to
  absolute numbers. The 0.0256 threshold is unchanged and C2 stays retracted.** New issue opened.

### ⚙️ C4 enabled — `FEATURE_TRANSFORM` override + `c4_transform_ab.sh`

`config.yaml` still justifies `feature_transform: log1p` with *"0.980 vs 0.965 PR-AUC"* — the
**overall binary** metric, inflated by the 17 % duplicate overlap and forbidden by `metrics.py` as an
optimisation target. `cnn_paper.py` gained a `FEATURE_TRANSFORM` env override so the A/B runs
**without editing `config.yaml`**, which would silently switch every other script's arm.

- **The tag now carries a transform suffix** for the same reason it already carries a seed suffix:
  without it, `FEATURE_TRANSFORM=raw` at the default seed would overwrite `cnn_paper.keras`, its
  embeddings and its fusion channel — the reference every other script reads. Behaviour is
  byte-identical when the variable is unset.
- **Explicit `c4_<arm>_s<seed>` tags**, because `cnn_paper.py`'s default tag for seed 43 is
  `cnn_paper_s43`, which **already exists from the pre-determinism-flag era**. Reusing it would put
  two populations under one run name — the defect that cost three wrong-model rows on 2026-08-05.
- **Seed 42 log1p is re-run rather than reused** from `det_verify_a` (0.6297683082). If the code edit
  is inert it must return that value exactly, so one training decisively checks my own change.
- ⚠️ **Process hazard recorded**: the chains re-invoke `scripts/cnn_paper.py` **from disk** per seed,
  so switching git branches mid-run would swap the file underneath the experiment and silently run
  the `raw` arm with the old code. All git work stayed on one branch until the runs finished.

## 2026-08-05 (method tiers B and D — the comparison table is complete)

### 🏗️ Tier B — deep architectures (`deep_zoo.py`)

| model | MACRO zd | Bot | FIELD binary |
|---|---:|---:|---:|
| **deep_cnn_lstm** | **0.6219** | 0.0206 | 0.9854 |
| deep_lstm | 0.3633 | 0.0501 | 0.9914 |
| deep_gru | 0.3029 | 0.0626 | 0.9932 |
| **deep_transformer** | **0.1106** | 0.0609 | 0.9894 |

- ✅ **Only the convolutional front-end matters.** CNN-LSTM lands **0.0031** from the CNN —
  indistinguishable — while pure recurrence *halves* the score. Adding an LSTM on top of a conv stack
  neither helps nor hurts; replacing the stack with recurrence is destructive. Cleaner than "LSTMs
  are bad here."
- **B1 CONFIRMED** (nothing escapes the top tier upward) · **B2 CONFIRMED** (nothing touches Bot —
  best 0.0626 against the KG's 0.3103).
- 🔴 **B3 FALSIFIED, and it was the tier's most confident prediction.** The Transformer was predicted
  to be **best** — self-attention is permutation-equivariant, the only inductive bias here that fits
  68 *unordered* tabular features. **It came last (0.1106), six times worse than CNN-LSTM.**
  ⚠️ Read as *"an untuned Transformer at a 30-epoch budget"*, **not** "attention is unsuited to this
  task": flat Adam 1e-3, no warmup, d=32, 2 blocks, mean-pooled tokens. **A negative result about one
  under-tuned configuration is not one about the architecture class.**
- ⚠️ **Two tier-wide caveats on record.** The recurrent models run over the **feature axis, not
  time** (68 unordered statistics, not timesteps) — this matches what published "LSTM on
  CIC-IDS2017" work does, so it is the right comparison, but it is **not evidence about sequence
  modelling for intrusion detection**. And **budgets are not matched**: `deep_lstm` hit the 30-epoch
  cap without early stopping while `cnn_paper` gets 50.
- 📊 **The field's metric hides the entire tier**: FIELD binary spans **0.9854–0.9932**, and the
  *worst* zero-day model (Transformer, 0.1106) posts 0.9894 while `deep_gru` (macro 0.3029) posts the
  tier's **highest** at 0.9932. Third independent demonstration this session.

### 📐 Tier D — data-split variance (`protocol_variance.py`)

5-fold over the train+val pool with the **test set held fixed** (zero-day is test-only). Model is
`cnn_paper.py`'s verbatim.

- 🔴 **The two variance sources are the SAME SIZE**: training stochasticity **SD 0.0222**, data split
  **SD 0.0228** — **1.03×**. D1 technically confirms but **must not be reported as "data variance is
  larger."** The finding is that a *second, previously unmeasured* uncertainty exists at the same
  magnitude as the one that retracted C2.
- **The consequence differs by case.** Comparing channels on a shared split — every comparison this
  project makes — the data draw is common and **cancels**, so the ~0.0256 threshold stands. Quoting
  an **absolute** number carries **√(0.0228² + 0.0222²) ≈ 0.032**.
- ⚠️ **Fold 5 (0.5802) falls below the CNN's entire n=6 range** [0.5966, 0.6446].
- ✅ **D2 CONFIRMED — SWA does nothing** (0.6218 → 0.6217). It flattens the *known-class* loss surface
  it averages over, which is not what zero-day measures.
- ⬜ **Cross-dataset (Phase 6) BLOCKED** — CIC-IDS2018 is not present locally. Recorded, not skipped.
- 🔴 **A defect caught before it published a wrong number.** The first version used a loosely
  "CNN-like" model (2 conv blocks, plain CE, **plus `class_weight` on top of focal α** — the
  double-weighting KNOWN_ISSUES warns about) while carrying a comment I wrote claiming it matched
  `cnn_paper.py`. Fold 1 returned **0.3244**; that 0.30 gap was an **architecture-and-loss difference
  being reported as data-split variance**, the exact confound the script isolates. After replicating
  the model verbatim, fold 1 returned **0.6218**, in line with the CNN — which is what confirmed the
  fix. **The anomaly forced the check; a wrong model scoring near 0.62 would never have been
  questioned.**
- 🔴 **Downstream cost:** a `pkill` I did not verify had failed, so the wrong-model run kept going and
  wrote **three** rows (`cnn_kfold1/2/3`) into `runs.jsonl`. **Not exact duplicates**, so
  `repair_runs_log.py` would not have caught them — two different models under one run name, with the
  integrity lint passing. Excised by timestamp; safe because `runs.jsonl` is version-controlled.

### ⚠️ Process: four monitoring mechanisms misled in one session

Buffered `tail` (false stall) · bare `grep` in a launcher (false stall, **and the lint check for it
was structurally unable to fire**) · a monitor re-emitting unchanged lines · a duplicate monitor left
running after a relaunch. Plus an unverified `pkill`. **The consistent lesson is that the
verification step is the one that gets skipped** — the same shape as the `script-count` regex that
passed on a wrong count. Rules added: verify a kill actually killed; reconcile a job's monitor when
you stop or relaunch it; test a lint check against the code it is meant to catch.

## 2026-08-05 (method tiers A and C — filling the comparison table)

Two of the four missing-method tiers, run after the base-paper metrics exposed how thin our
comparison table was.

### 📉 Tier A — classic baselines (`baselines_classic.py`)

Decision Tree, k-NN, Naive Bayes, Logistic Regression, linear SVM, RBF-SVM (Nystroem), MLP.

- 🔴 **The clearest protocol-gap evidence in the project.** On the field's binary metric all seven
  score **0.977–0.985** against the CNN's 0.9928; on macro zero-day they span **0.0374 → 0.6049**,
  a 16× spread. **Logistic regression looks 98 % as good as the CNN on the published metric and is
  17× worse on zero-day.** `comparability.py`'s argument, made across seven models instead of one.
- ⚠️ **The two that look competitive are score-degenerate.** `decision_tree` (0.6049) is nominally
  indistinguishable from the CNN, but **50.1 % of test rows share one score** — a depth-limited tree
  emits leaf-purity probabilities. k-NN is 49.8 % tied. **PR-AUC over a half-tied ranking is not
  comparable to a continuous scorer's.** The best *valid* result is the **MLP at 0.5360**, genuinely
  below the CNN. Tie diagnostics are now printed and persisted for every model.
- **T3 FALSIFIED**: k-NN was predicted to be the best Tier-A method on Bot — the only instance-based
  one, working on the same raw-feature substrate the KG clusters. It was not (0.0342 vs 0.0415).
- 🔴 **A bug in my own script, caught by recomputing from the saved arrays.** Scores were cast to
  **float32 on save** while evaluated in float64; GaussianNB's probabilities underflow toward 0/1, so
  the narrower mantissa collapsed distinct values into ties and its reloaded macro read **0.0597
  against a logged 0.1264** — the saved channel no longer reproduced the logged metric. Fixed to
  float64 in three scripts. Same float32-precision class as the 2026-07-27 saturation bug.

### 🧪 Tier C — benign-only anomaly zoo (`anomaly_zoo.py`)

VAE, Deep SVDD, One-Class SVM (SGD), LOF — all trained on benign only.

- 🔴 **C2 FALSIFIED, and it corrects how this project has described the (B) family.** **LOF reaches
  macro 0.3368** (Web BF 0.5592, XSS 0.4131) — a benign-only method that does **not** collapse on web
  attacks, unlike the autoencoder (0.1048 / 0.0547). It lands where **Mahalanobis** does (0.3777).
  Both are density/distance methods; the AE scores by reconstruction. **So "benign-only ⇒ collapses
  on web attacks" is a property of reconstruction-error scoring, not of the (B) family.**
- 🔴 **C1 reads CONFIRMED and must not be cited that way.** Deep SVDD's Bot **0.1558 sits inside the
  autoencoder's own n=3 range [0.1078, 0.1647]**, so at n=1 it is not an established improvement.
  Sixth single-seed near-miss in this project — the difference is that it was checked against an
  existing seed range *before* being written down. Needs `ANOM_SEED=43/44`.
- ✅ **C3** — Deep SVDD did not collapse (score SD 3.20×10⁻²); the degenerate all-to-centre solution
  was guarded against and checked explicitly rather than assumed.

### ⚙️ Determinism confirmed at full scale

**Two complete 50-epoch seed-42 trainings → BYTE-IDENTICAL predictions**, achieved **while three
other jobs competed for CPU** — a stronger test than an idle machine, and the direct answer to the
withdrawn session/environment effect. Reproducibility at full speed; the single-thread fallback is
unnecessary. ⚠️ **The SD 0.0222 floor applies to runs made before the flag and not going forward —
but old and new runs are different populations and must not be pooled.**

### 🔴 A second lint check found structurally unable to fire

`launcher-suppresses-log-growth` **passed** on my own `verify_determinism.sh`, which pipes a training
run through a bare `grep`: the check required `python` and the pipe on the **same physical line**, but
the pipe sat on a backslash continuation. It then produced **exactly the false STALL alarm it exists
to prevent**. Third instance of this class in one day. Fixed by joining continuations, and the check
was verified to fire on the offending file *before* the file was fixed. **Same shape as the
`script-count` regex gap found the same morning: a check that cannot fire is worse than no check.**

## 2026-08-05 (base-paper + literature metrics, ablation, determinism)

### 📊 Our numbers in the base paper's metric set — computed for the first time

`scripts/paper_metrics.py`. **Not one of Bizzarri et al.'s numbers had ever been computed for our
models**, so the capstone had no readable comparison to its own base paper or to the field's 99 %+
claims. Both metric systems now come out of the same runs.

- ✅ **We beat the base paper by 18–29 pp on all four known-class views** (multi-class 15 classes:
  **96.17 % vs 67.52 %**). ⚠️ **A modality advantage, not a method one** — engineered flow features
  are far more separable than raw payload bytes. Not an algorithmic win; do not write it as one.
- 🔴 **We reproduce their 1D CNN's zero-day accuracy almost exactly (47.85 % vs 48.34 %) and cannot
  reproduce the Hybrid-LTN's +12 pp symbolic gain.** Our closest reproduction of their model
  (`ltn_repro`, CE + Ax1/Ax2) scores **47.24 %** — no gain over our own CNN. **This is the project's
  central finding stated on the base paper's own metric**, and in its strongest form: not "our
  variants cost macro PR-AUC" but "*their* reported improvement does not appear."
- 🔴 **Their zero-day metric has no false-positive term.** View 5 contains only attack rows, so
  precision ≡ 1 and **`F1 = 2A/(1+A)` exactly** — which reproduces every published F1 from its
  accuracy to <0.02 pp. Their *"accuracy 48→60 %, F1 65→75 %"* headline is **one result reported
  twice**, and **a model that flags every flow scores 100 % on both.** Our own float32 saturation bug
  did exactly that and was caught only because our metric has a benign side.
- 🔴 **It is also a size-weighted mixture** — the defect `metrics.py` was rewritten to remove.
  Holding the model fixed and changing only the family mix moves the headline **48.32 % → 44.38 %**.
  Their set is Heartbleed+WebBF-dominated (79 %); ours is **Bot**-dominated (46.8 %), the family our
  CNN provably cannot reach (0.0 % detected). **Composition explains ~4 pp, so the missing ~12 pp is
  not explained away by it.**
- **The field's suite is now reported**: CNN accuracy **97.95 %**, precision 99.71 %, recall 96.32 %,
  F1 **97.98 %**, FAR **0.31 %**, ROC-AUC 98.32 %, PR-AUC 99.00 % — in the literature's range, and
  **an easier question asked of the same models**, not a better result than macro 0.64.

### 🔴 Ablation — only the KG earns its place

`scripts/ablation.py`, n=3 paired seeds, parameter-free rank fusion, four predictions pre-registered
and all four confirmed.

- **CNN 0.6399 → CNN+KG 0.6926** (+0.0528, 3/3 seeds, p<0.0001).
- **The symbolic pillar adds nothing alone** (−0.0004, n.s., improving on 1 of 3 seeds) **and
  significantly HURTS stacked on the KG**: FULL 0.6708 vs CNN+KG 0.6926, **−0.0218, p<0.0001**,
  diluting the KG's Bot signal 0.2518 → 0.2043.
- ⚠️ **A trap inside our own result, caught by our own rule**: `CNN+LTN-ctrl vs CNN` returns
  p<0.0001 — and is **noise**. The gap is +0.0035 = **0.16 SD** of the floor, improving on 2 of 3
  seeds. *A flow-level bootstrap cannot rescue a delta below the pipeline's reproducibility.*
- ✅ Implementation independently validated: recomputing macro from raw arrays gives 0.6399 and
  0.6926, exactly matching `metrics.py` and `fusion_kg.py`.

### ⚙️ TF determinism (Phase 7.5 Tier 2 #5)

`scripts/determinism.py`, wired into `cnn_paper` / `ltn_paper` / `autoencoder_paper`.

- Pins `PYTHONHASHSEED`, op-determinism and **fixed** thread counts (intra=16 / inter=2 — *fixed*,
  not minimal). **Whether pinned multi-threading suffices is an empirical claim, so it is tested:**
  `verify_determinism.sh` trains seed 42 twice and requires **byte-identical** output.
- ✅ **Fast verification (50k rows, 2 epochs): BYTE-IDENTICAL.** Reproducibility at full speed — no
  single-thread cost needed. Full-training verification launched.
- ⚠️ **Determinism does not make old and new runs comparable.** Pinning threads changes the reduction
  order, defining a *new* fixed point; the 11 historical seed-42 values are a different population.
  Recorded in `runs.jsonl` as `det_*` fields so the state travels with the numbers.
- ⚠️ Caught in my own launcher: FULL mode would have written two genuinely-trained channels under a
  `smoke` tag, quarantining real runs into the smoke archive *and* stamping the research record with
  rows named "smoke". Fixed to use real tags when it trains for real.

## 2026-08-05 (Phase 7.5 Tier 1 — the metrics that decide whether response is safe)

`scripts/operational.py`. Four predictions pre-registered before running; **all four confirmed.**
No training — evaluation over saved predictions, plus one validation forward pass.

- **1. The ensemble is the deployable baseline.** 11 CNN runs, probability-mean → **0.6356**,
  reproducing the figure STATUS already quoted. Beats the single-run mean (0.6217), **not** the max
  (0.6446) — because the max is the top of 11 draws, not a typical result. **The argument for the
  ensemble is reproducibility, not the delta.** ⚠️ `cnn_auxhead` was caught contaminating the glob on
  the first run: it matches `cnn_*` but is a *different architecture*, so ensembling it would have
  silently answered a different question while being reported as a reproducibility fix.
- **2. 🔴 Calibration works on known classes and does nothing for zero-day.** Fitted on validation
  (zero-day-free by construction, asserted in code): isotonic reaches **ECE 0.0001** on known classes
  while zero-day ECE stays at **0.0387 — 287× worse.** A calibrator learns a score→outcome mapping,
  and for a class the model has never seen that mapping does not hold. **The better the calibration,
  the wider the gap.** Operationally: `p = 0.9` means 90 % for known attacks and nothing for novel
  ones.
- **🔴 Isotonic wins ECE but is unusable as an operating point** — a step function with **74 distinct
  values** over 114,658 flows, so the 1 %-FPR quantile lands in a tie block. The first run thresholded
  on it and achieved **FPR 0.70 against a 0.01 target.** Platt is monotone and continuous and hits
  0.0100 exactly. **Calibrate with isotonic for reporting; threshold with Platt.**
- **3. 🔴 At any deployable alert budget you see only known attacks.** Precision is ~1.000 at every
  budget for every channel — and **zero-day recall is 0.0000 through 10,000 alerts.** Reaching half
  the zero-day flows requires reviewing **32–52 % of all traffic**. The KG and the CNN+KG fusion cut
  that depth by ~20 pp (52 % → 29–32 %), **which is the clearest operational statement of what the KG
  buys — and it is not a PR-AUC delta.**
- **4. 🔴 Abstention does not rescue zero-day (+0.0000 across every non-degenerate coverage).**
  Predicted in advance from the Bot failure analysis: the CNN is **confidently wrong** on Bot (100 %
  argmax BENIGN, p(BENIGN)=0.9984), and **a confidence rule cannot catch confident-and-wrong.**
- ⚠️ **Two methodological errors caught inside the script**, both of which would have produced
  publishable-looking nonsense: thresholding a tie-degenerate score, and defining confidence as
  `|p − 0.5|` when the operating point is 0.000049 (which ranks *confidently benign* flows as most
  confident). **Both were visible only because achieved FPR was printed next to its target.** Also
  tightened P4 to test the best point on the curve rather than the endpoint, and to exclude
  coverages retaining <1,000 benign flows — using the endpoint would have picked the comparison that
  flattered the prediction.

**The Phase-R headline**: automated response is **safe on what this system fires on** and **useless
for novel attacks at any budget a SOC would run.** PR-AUC 0.64 does not show that; this does.

## 2026-08-05 (documentation debt closed — and a lint that could not fire)

No new measurements. This session closed eight drift items left by the previous one, then continued
into Phase 7.5 / ablation / determinism work (logged separately below as it lands).

- **🔴 The previous session never wrote a CHANGELOG entry.** It updated `STATUS.md`, `CLAUDE.md` and
  `KNOWN_ISSUES.md` — but the file whose entire job is the dated record got nothing, so the noise
  floor, C2's retraction and the n=6 sweep existed everywhere except the history. **Backfilled below
  as the 2026-08-04 entry.**
- **🔴 `CLAUDE.md` asserted Phase 4 had not started** — in three places — **two sessions after it was
  built, multi-seeded and completed with explainability.** Fourth occurrence of the component-status
  drift defect, and the worst-placed one: `CLAUDE.md` is auto-loaded into every session, so it was
  the first thing a new session read. Fixed, with a note in place explaining how it survived.
- **`STATUS.md` internal contradictions fixed**: the Component Status row for Explainability said
  `✅ 3 of 3 + faithfulness` in its status column while its Notes column still listed all four
  sub-items as `❌ not built`; Remaining Work #5 still called explainability "the true next in-phase
  work"; #4 still listed n≥6 seeds as outstanding after they were done. Header date and RESUME HERE
  were two sessions stale. The canonical n=3 results table now points at the n=6 table for macro.
- **`KNOWN_ISSUES.md`: C1 and C3 were still tagged `[OPEN]`** although both were closed 2026-08-03 by
  `comparability.py` and `robustness.py`. Marked closed **in place**, with what was measured.
- **🔴 `scripts_reference.md` documented 32 of 41 scripts** — the entire Phase-4 / fusion /
  explainability toolchain (`kg` · `kg_visualize` · `explain` · `fusion_kg` · `fusion_multi` ·
  `comparability` · `robustness` · `significance_seed` · `lint_conventions`) was undocumented while
  the header claimed it was verified against source. **All nine written up from the source**, not
  from memory.
- **🔴 The lint had been passing on a wrong count for two sessions.** `script-count` used the regex
  `(\d+) scripts`, which requires the number to sit directly against the word — but the docs put a
  qualifier between them, so **the check could never fire.** It reported ALL CHECKS PASS over a stale
  count and nine missing entries. **A mechanical check that cannot fire is worse than no check: it
  buys false confidence, and this project converted prose rules into lint checks precisely to stop
  relying on that.** Fixed, plus a new **`undocumented-scripts`** check that verifies *membership*
  rather than arithmetic — because a count can be right while the file is still incomplete.
  ⚠️ Caught en route: the first widened regex over-matched, counting numbered list items followed by
  `python scripts/foo.py` as prose. Constrained to one line and to reject `scripts/`.

**The transferable lesson**, and it is the same shape as the two monitoring false alarms recorded on
2026-08-03: *the check and the thing it checks drift apart silently, and a passing check is
indistinguishable from a working one.* The heartbeat rule was broken by a launcher that suppressed
the signal it watched; the script-count rule was broken by a doc that reworded the string it matched.
**When a convention is made mechanical, the mechanism itself becomes something that can rot.**

## 2026-08-04 (BACKFILLED 2026-08-05 — the noise floor, and the retraction it forced)

> ⚠️ **This entry was written a day late**, reconstructed from the five commits and `STATUS.md`.
> The session labelled its own content `2026-08-03` (it ran past midnight); the commits are dated
> 2026-08-04. Dated by commit here.

### 🔴🔴 Training is not reproducible at fixed seed — the project's most consequential measurement

- Six runs of **seed 42, identical code, idle machine**: 0.6446 · 0.6295 · 0.6366 · 0.6124 · 0.5825 ·
  0.6280 → **mean 0.6223 · SD 0.0222 · range 0.0621 · CV 3.6 %**. TensorFlow on CPU is not
  bit-deterministic and **no determinism flags are set**, so thread scheduling changes float
  accumulation order. `noise_floor.sh`.
- **Every delta must now be expressed as a multiple of this SD.** That ratio, not the raw number,
  decides whether a claim survives.

### 🔴 C2 is RETRACTED — on controlled grounds, hours after passing a significance test

- *"The neural baseline beats the LTN control"* was closed in the CNN's favour **earlier the same
  day** with a paired bootstrap at **p=0.001**. The gap is **+0.0204 = 0.9 SD** — **smaller than
  re-running one model twice.**
- **The bootstrap was arithmetically correct and epistemically empty**: it treated each run's score
  as exact when re-running moves it by up to 0.062. **A paired significance test over per-flow scores
  cannot rescue a delta below the pipeline's own reproducibility.** This is the project's most
  important methodological lesson.
- Two further corrections recorded: **`cnn_paper = 0.6446` is the MAX of 11 runs**, not a typical
  result (mean 0.6217) — the honest reproducible baseline is the **ensemble, 0.6356**, and 0.6446 is
  the number that would otherwise have gone into the paper. And **every n=3 range in the docs is an
  artefact**: the CNN's "tight" 0.0093 spread is **0.4 SD**, less than half a single re-run's noise.

### 🔴 All 7 channels to n=6 — the top tier is INDISTINGUISHABLE

`rigor_n6.sh`, `ltn_ctrl_sweep.sh`. MSP and Mahalanobis were free (post-hoc on already-trained CNN
seeds 45–47). Equal n matters more than the absolute value here, because **asymmetric sampling is how
the C2 confusion arose in the first place.**

| channel | n=6 mean | range |
|---|---:|---|
| CNN | **0.6250** | [0.5966, 0.6446] |
| LTN control | **0.6110** | [0.5824, 0.6505] |
| RandomForest | 0.5985 | [0.5682, 0.6235] |
| MSP | 0.5761 | [0.5053, 0.6289] |
| Mahalanobis | 0.3948 | [0.2295, 0.5782] |
| Autoencoder | 0.1083 | [0.0894, 0.1346] |
| IsolationForest | 0.0681 | [0.0628, 0.0750] |

- Distinguishable only above **~0.0256**. **CNN vs LTN control = +0.0140 → INDISTINGUISHABLE.**
  Not "the CNN wins narrowly" — **they cannot be told apart at achievable precision.** C2's third and
  cleanest refutation.
- ⚠️ **And the gap shrank when a scoring inconsistency was fixed.** LTN control seeds 45–47 were
  scored **raw** while 42–44 were **log-odds** — mixed scoring *within one channel*, which penalises
  the LTN because it was saturated. Rescoring moved it **0.5977 → 0.6110** and cut the CNN's apparent
  lead from +0.0273 to **+0.0140**. The original C2 gap was **partly a scoring artefact**, separately
  from the noise floor. **Third time in one session a comparison was invalid for a reason invisible
  in the numbers** (mixed sessions, mixed CPU load, mixed scoring).
- **NOT overturned**: *"every axiom variant costs macro vs the no-axiom control"* — those gaps are
  0.05–0.13, well above threshold. **Phase 2 is unaffected and sharper: adding axioms hurts, but the
  axiom-free symbolic trainer matches the CNN.**
- **Three tiers, not a ranking**: supervised/closed-set (~0.58–0.63, mutually indistinguishable) ·
  distance (~0.39, unstable) · benign-only (~0.07–0.11). **The double dissociation lives ACROSS
  tiers**, which is why it survives everything — and why the within-tier comparisons this project
  spent months on were always below the noise.

### 🧭 Three claims asserted and withdrawn in one session

*"n=3 understated seed variance 4–5×"*, *"there is a session effect"*, *"C2 must be reopened"* — all
three were **competing explanations for one unmeasured quantity**. A monotonic decline that looked
like environmental drift (ρ = −1.0 across three consecutive runs) **broke at run 4**, exactly as its
1-in-6 probability predicted. **Four training runs settled what hours of observational comparison
could not: measure the variance before explaining it.** The session-effect analysis is kept in
`KNOWN_ISSUES.md` with its withdrawal marked in place.

> **Process note carried forward.** The confound was flagged *one message after* the C2 collapse had
> already been reported as a headline finding. The project's own rule — *"a point-estimate gap is not
> a result"* — was applied rigorously to old claims and not to a new one of my own. **That asymmetry
> is the failure mode worth remembering, more than the confound itself.**

### What survives

| claim | delta | ÷ SD | verdict |
|---|---:|---:|---|
| Double dissociation (XSS) | +0.8977 | **40.4** | ✅ established |
| Double dissociation (Web BF) | +0.8178 | **36.8** | ✅ established |
| Double dissociation (Bot) | +0.0868 | **3.9** | ✅ established |
| CNN+KG fusion | +0.0527 | *paired* | ✅ direction (3/3 seeds); magnitude 0.027–0.088 |
| **C2: CNN vs LTN control** | +0.0204 | **0.9** | 🔴 **RETRACTED** |

**The double dissociation strengthened under every test while C2 collapsed under each one. That was
never about rigour applied — it was effect size relative to a floor nobody had measured.**

### Also added

- **Phase 7.5 — operational readiness**, a planned intermission between Phase 7 and Phase R, which it
  **gates**. Rationale: **PR-AUC is the wrong target for a response engine** — it summarises ranking
  across all thresholds while the engine acts at **one**. A system can post macro 0.69 and still
  auto-block at 40 % precision, and **no metric currently in this project would warn you.**
- `significance_seed.py` — seed-level significance, impossible at n=3 (Wilcoxon floor p=0.25),
  achievable at n=6 (floor p=0.031). ⚠️ Still weak: a non-significant result at n=6 is evidence the
  test is underpowered, not evidence of no effect.

## 2026-08-03 (later: Phase 4 built and completed, first result to beat the baseline)

### Phase 4 — the Knowledge Graph, and then its explainability half

- **KG built** (`kg.py`), n=3. Every design decision forced by the gate measurements rather than the
  spec: **raw-feature clusters** (CNN embeddings and the AE bottleneck were both measured and
  rejected), **corroboration scope** (the spec's "unexplained cluster" detector scores ≤1.00×, at or
  below chance), **growth-only** emerging rule, decay kept. **s_kg causal: macro 0.2488, Bot 0.3103 —
  the best Bot channel measured in this project.** The *online* variant significantly beats the batch
  one, which is the right way round for a deployable IDS.
- **🔴 A mandatory confound control, now permanent in the script.** The causal score rises with
  arrival position and CIC-IDS2017 schedules attacks late, so "later ⇒ suspicious" had to be ruled
  out. **A trivial lateness-only baseline scores Bot 0.1575 — beating the previous best channel
  (autoencoder, 0.1314).** The KG's advantage *survives* (3.2× within-window vs the AE's 1.9×), but
  the global 9.4× is roughly *schedule × cluster signal* and must be quoted with the within-window
  figure. **A real share of apparent zero-day performance on this dataset is recoverable from the
  capture schedule alone** — I could find no published work running this control.
- **Explainability delivered** (`explain.py`), completing Phase 4: Integrated Gradients (with its
  completeness axiom verified as a correctness check), per-axiom SAT, KG reasoning paths, Final Alert
  assembly, and the **Tier-A faithfulness measurement**. Masking the 3 features IG points at drops the
  attack score **20.7× more** than masking 3 random ones. Sufficiency is the weaker half and is
  reported as such — the decision is distributed across more than 10 features.
- **🔬 The qualitative result:** on a Bot flow the CNN calls benign, **both other pillars dissent** —
  Ax6 BeaconLike fires 1.00 → VIOLATED, and the KG flags the cluster as emerging and beacon-dominated.
  No single-pillar system produces that. It is the clearest argument for the architecture, and it is
  not a score.

### 🟢 The first combination to beat the CNN baseline

- **Parameter-free rank fusion, CNN + KG: macro 0.6399 → 0.6926** (+0.0527, paired bootstrap p<0.001,
  seed ranges **disjoint**, survives the lateness control). **Why it works when every fitted fusion
  failed:** the fusion wall applies to *fitted* combiners, which must discover a zero-day channel's
  value from validation data that contains none. A rank-mean **imposes** the weight instead — the
  same structural point as the Phase-2 conclusion, used constructively for the first time.
- **🔴 More channels made it worse.** Five pre-registered subsets: the 2-channel CNN+KG (0.6926) beats
  all 9 channels (0.6664) and every other subset. Equal weighting lets IsolationForest (macro 0.0653)
  outvote nothing useful. **Complementarity, not quantity.** 4 of 5 subsets still beat the baseline.

### Comparability, robustness, and two audit items closed

- **We were never behind the literature.** `comparability.py`: the same CNN scores **0.9928** on the
  field's overall-binary metric and **0.6446** on ours — a **0.3564 gap from protocol alone.**
- **C1 closed**: 17.0 % of test rows are exact train duplicates (PortScan 58.3 %). Deduplication costs
  supervised channels ~0.004 — and **all six zero-day families measure 0.0 % overlap**, so duplication
  inflates *the field's* metric and leaves ours untouched.
- **C3 closed**: regrouping the macro to weight phenomena over labels shifts values ~0.11–0.15 but
  **preserves every meaningful ordering**.
- **Fusion wall tested constructively and it holds**: known-class weighting (legitimate — no zero-day
  information) **hurts Bot by −0.0176**, down-weighting the KG precisely for being good at a family it
  never trained on.

### Process: conventions made mechanical after real lapses

- The heartbeat rule lapsed on **six** jobs, and the same cp1252 bug was fixed **three times** as
  separate incidents. Root cause: each rule has a *plausible-but-wrong substitute* next to it — the
  harness notifies on **completion**, which feels like monitoring but does not cover stalls.
- **`lint_conventions.py`** — mechanical checks, each naming its motivating incident. Found **12 real
  issues** on first run and later caught an incorrect script-count bump mid-commit.
- **`run_long.sh`** — launches *and* arms monitoring in one command. **`CLAUDE.md`** gained an 8-line
  NON-NEGOTIABLES block at the top.
- **⚠️ Two monitoring false alarms, both my own launcher design**, both fixed: a liveness check that
  reported STALLED on a *finished* job, and `seed_sweep.sh` piping through `tail` (which buffers to
  EOF, suppressing the log growth the heartbeat watches). The lint now fails on that pattern.
  *A heartbeat rule is only as good as the launcher preserving the signal it depends on.*
- **⚠️ Two false verdicts printed by my own analysis scripts**, both fixed in code: a 1.3×10⁻⁵ tie
  reported as "conclusions NOT robust", and the fusion-wall test judged on macro instead of Bot,
  inverting its conclusion. An automated verdict that cries wolf is worse than none.

## 2026-08-03 (pre-Phase-4 remediation — and it produced three research results)

Scoped as "fix every discrepancy found by a full workspace/git audit before starting Phase 4."
Fixing them required re-running things, and **the re-runs overturned two documented claims and
answered the project's last open research question.**

### Research outcomes (unplanned — they fell out of the fixes)

- **🔬 "Why does the CNN fail on Bot?" is ANSWERED** (`scripts/bot_failure_analysis.py`, four
  hypotheses pre-registered in the script before running). The failure is **representational, not
  informational**:
  - **100% of Bot flows are classified BENIGN** (all 3 seeds, mean p(BENIGN)=0.9984). Bot is not
    ambiguous to the CNN — it is confidently asserted benign.
  - **Web attacks transfer by absorption into `DoS slowloris`** (89.8% / 92.9% modal class), a known
    *attack* class — so their 0.92–0.95 PR-AUC is misclassification landing on the right side of the
    binary, **not** zero-day detection. This replaces the falsified "modality analogue" story with a
    measured mechanism. (Note it differs from `modality_analysis.py`'s raw-space nearest neighbour,
    DoS Hulk — classifier behaviour ≠ raw proximity.)
  - **0 of 8 feature overlap** between what the known-class task needs and what separates Bot from
    benign. No gradient pressure to represent Bot's signature.
  - **Therefore the CNN's Bot ranking is NOISE**: cross-seed Spearman ρ = **−0.090**, vs 0.68–0.83
    for every other family. RandomForest shows the same (0.068); the **autoencoder does not**
    (0.827). *One cause, four symptoms* — this explains the Phase-4 cluster-purity lottery, the
    Mahalanobis Bot spread, and RF's Bot swing simultaneously.
  - Refuted: Bot is **not** intrinsically hard (oracle PR-AUC 0.9988) and **not** boundary-adjacent
    (it is benign-*interior*).
- **🔴 The (A)/(B) thesis reframing is FALSIFIED in its strong form.** Putting the classical
  baselines on 3 seeds — a *bookkeeping* fix — revealed **RandomForest (an (A)-family method) ties
  the autoencoder on Bot** (0.1311 vs 0.1314, paired bootstrap p=0.88) **while beating it 0.50 on
  macro.** "(B) methods are needed to reach Bot" is dead; so is "no channel sits at both ends of the
  frontier" (RF does). The CNN-vs-AE double dissociation survives and is now *significant*, but it is
  a dissociation between **two models**, not two **families**.
- **✅ Significance tests run** (`scripts/significance.py`, stratified paired bootstrap over test
  flows, B=2000). **C2 is properly closed: the CNN does beat the LTN control** (+0.0204, CI
  [+0.0082, +0.0331], p=0.001) despite the overlapping seed ranges — the paired test cancels
  flow-noise common to both. ⚠️ Flow-level uncertainty only; **seed-level significance is
  unreachable at n=3** (Wilcoxon floor p=0.25 — needs n≥6). The double dissociation is significant
  on all three families (p<0.0005).
- **🔴 First retraction-of-a-retraction: "on macro the CNN beats XGBoost" is n.s. (p=0.80).** The
  2026-07-27 retraction of *"XGBoost ≈ CNN"* compared two point estimates with no test. The original
  claim was right. The downstream note that the "pivot to explanation/adaptivity" framing rested on
  "a tie that isn't there" is **withdrawn — the tie is there.**

### Last Phase-4 gate closed (fourth pass) — 1 of 3 KG criteria works

`scripts/kg_criteria.py` + `scripts/timeline.py`, three predictions pre-registered.

- **✅ Criterion #1 (cluster growth / burstiness) WORKS and is robust** — lift **5.94x**
  [5.66, 6.11] across 3 clustering seeds at **~81% recall** of zero-day flows (42% precision vs a
  7.04% base rate). At a looser threshold it captures **98.9%** of zero-day flows at 3.27x.
- **⚠️ Criterion #3 (behaviour co-occurrence) is WEAK** — flow-level 2.81x at **1.5% recall**;
  cluster-level at or below chance. Structurally coarse: only **24 of 64** behaviour patterns occur
  in benign training data, so p90/p95/p99 thresholds collapse onto the same value. Root cause is in
  the inputs — the five graded behaviours are DoS/scan-shaped and the zero-day families are not.
- **🔴 A FIFTH single-seed artifact, caught BEFORE it entered the docs.** On clustering seed 42 the
  conjunction `burst>=8 AND rarity>=p90` gave **lift 11.57x at 81.4% precision** — the most striking
  number of the session. Multi-seeding first gave **11.57x / 2.37x / 1.73x** and precision
  **0.814 / 0.167 / 0.122**. Do not cite "81% precision." First time this project's multi-seed
  discipline caught an overclaim *before* publication rather than after.
- **🔴 Two silent timestamp defects found and fixed** (`scripts/timeline.py`), both of which would
  have wrecked the adaptive story: CIC-IDS2017 dates are **D/M/YYYY** (naive parsing scatters a
  5-day capture across March/June/July), and the clock is **12-hour with no AM/PM** (observed hours
  {1..5, 8..12} map onto an 08:00-17:00 workday, so 1 PM sorted before 9 AM). The reconstruction is
  **validated against the published capture schedule** — Web BF Thu 09:15-10:00, XSS Thu 10:15-10:35,
  Bot Fri 09:34-12:59, PortScan Fri 13:06-15:23, DDoS Fri 15:56-16:16 — all exact.
- **⚠️ External-validity caveat, mandatory in any write-up:** growth works substantially *because*
  CIC-IDS2017's attacks are scripted into fixed windows. A real network with continuous low-rate C2
  would not produce the signal — and Bot is precisely the family whose real signature is persistence,
  not bursts. Pre-registered as "will work, largely for the wrong reason"; confirmed on both halves.
- **Decision logged (user):** keep the KG **adaptive** — temporal decay stays, with time defined as
  flow-count position in true chronological order.

**Phase 4 is now fully specified by measurement**: raw-feature clusters · corroboration +
explainability scope · growth-rate-only emerging-pattern rule · decay kept. One honest observation
carried forward: *"temporal burstiness of a raw-feature cluster" does not require a knowledge graph*,
so the KG's justification must rest on explanation and corroboration, not on this detection number.

### Phase-4 readiness measured (third pass — "make it ready, don't start it")

`scripts/kg_readiness.py`, four predictions pre-registered. **Two decisive results, one of which
falsified a recommendation this project made earlier the same day.**

- **🚨 The KG's specified zero-day mechanism DOES NOT WORK.** "Unexplained cluster" (weak/no
  `associated_with` edges to a known AttackType) was operationalised honestly — train-labels-only
  criterion, scored against test — and scores **lift ≤ 1.00× over the base rate across 3
  representations × 3 thresholds.** Best result anywhere is exactly chance; everything else is
  **below** it, i.e. anti-correlated. Cause is structural: **118 of 200 clusters contain zero
  known-attack training flows**, because benign traffic is diverse and is half the training set, so
  the criterion flags ~59,000 of ~59,400 benign+zero-day test flows.
  **Consequences:** the KG cannot be a primary detector; the spec's scope contradiction
  (`knowledge_graph.md` "primary zero-day signal" vs `conference_roadmap.md` "corroboration, not
  primary detector") is **resolved empirically in the roadmap's favour**; and the spec's other two
  criteria (**growth rate**, **behaviour co-occurrence**) are now the gating question for any KG
  detection role — still untested.
- **🔴 The AE-bottleneck representation recommendation was measured and REJECTED.** Earlier the same
  day, Open Decisions recorded *"(c) the AE's benign-trained 16-d bottleneck is now the data-backed
  lean"*, reasoning from the AE's reproducible Bot *ranking* (ρ=0.827 vs the CNN's −0.090). Measured
  Bot-purity spread: **52.1 pp — the worst of all options**, versus the CNN's 43.4 pp.
  **Rank stability ≠ cluster stability.** The AE orders Bot flows consistently but its 16-d geometry
  still scatters them across seeds.
- **✅ Raw features are the data-backed choice**: Bot purity **77.6 % (k=200) / 80.6 % (k=400)**,
  competitive with the CNN's good seeds, far above its worst (44.4 %), and with **no training-seed
  lottery** — residual k-means seed sensitivity ~2.6 pp, an order of magnitude below the 28–52 pp
  training lottery. Bot-purity instability appears in **every learned representation** while
  Web BF/XSS stay stable in all of them — consistent with the Bot failure analysis.
- **Behaviour-column guards for Phase 4** (additive; the frozen 7-column `behaviour_matrix()` and
  `BEHAVIOUR_NAMES` are untouched so Phase-2 results remain valid): `BEHAVIOUR_KIND` declares each
  behaviour `graded`/`binary`/`constant`, and `active_behaviour_matrix()` drops the constant-zero
  `RepeatedConnections` column automatically. `BeaconLike` is flagged `binary` — bimodal as an
  `exhibits` edge weight.

### Data-integrity repairs (second pass, same day)

The first pass **documented** these defects but left them in the data, citing the append-only rule.
That reasoning became obsolete the moment `runs.jsonl` went under version control — git supplies
the audit trail the rule was protecting. Repaired via `scripts/repair_runs_log.py` (dry-run by
default, report written, fully revertible):

- **14 rows carried the wrong seed** → 0. `rescore_logits.py` stamped every `_logodds` entry with
  the config default (42); the *code* was fixed 2026-08-02, the *data* never was.
  ⚠️ **Correcting my own correction:** an earlier note in KNOWN_ISSUES said *16* rows — that matched
  `'_s4' in name and seed==42`, which wrongly counts `ltn_ax6_ratio_w1p0_s42{,_logodds}`, whose seed
  *is* correctly 42. True figure is **14**, derived per-row from each tag's own `_s<N>` suffix.
- **26 exact-duplicate rows removed** (97 → 71). ⚠️ **Only exact duplicates** — identical in name,
  params *and* every metric. **8 duplicated names were deliberately preserved** because their
  content genuinely differs: six old-schema/new-schema pairs from the metrics rewrite, plus
  `ltn_repro` (0.4401 vs 0.4853) and `ltn_v2` (0.4908 vs 0.4912), which are **distinct training runs
  with identical configs**. Collapsing those would have destroyed research data; the script asserts
  no run name can disappear and refuses to write if one would.
- **All 71 rows stamped with a schema version** (`v1-blended` 15 / `v2-macro` 56), so pre- and
  post-2026-07-27 records stop being silently comparable.
- ✅ **Verified every published figure reproduces unchanged after the repair.** A metadata repair
  that moved a result would itself have been a bug.

Two further defects in `tracking.py`, found while fixing the above:

- **Every `stamp` was empty** — it defaulted to `""` and no caller ever passed one, so all 97 rows
  had no time information whatsoever. Now auto-populated (UTC ISO-8601).
- **The log was opened without an explicit encoding** — cp1252 on Windows, the same bug class that
  broke `config.py`. Any non-ASCII class name (CIC-IDS2017 labels contain them) would have crashed
  the write or corrupted the read.

And **smoke artifacts no longer pollute the fusion-channel namespace**: `paths.predictions_dir(tag)`
routes any "smoke" tag to `_smoke_archive/` automatically, so the 2026-08-02 hand-cleanup does not
have to be repeated after every `*_SUBSET` run.

### Discrepancies fixed (the original scope)

- **🔴 The entire research record was gitignored.** `outputs/metadata/` was excluded wholesale, so
  `runs.jsonl` — backing every number in STATUS — had no history, no backup, no way to detect a bad
  write, while KNOWN_ISSUES simultaneously treated it as an append-only log that must never be
  rewritten. Now tracked (101 KB), along with the paper split's protocol definition
  (`split_report.txt`, `known_classes.npy`, `zero_day_classes.npy`).
- **🔁 Component status collapsed to a single source of truth.** The duplication had caused the same
  drift error in **three** consecutive sessions. `STATUS.md → "Component Status"` is now canonical;
  `CLAUDE.md`, `roadmap_gap_analysis.md` and `target_architecture.md` are pointers.
  **Critically, STATUS's own table was the stalest of the four** — still calling the autoencoder
  n=1 with "0.0000 recall on web attacks", citing the forbidden "PortScan/DDoS strongly covered",
  claiming the behaviours weren't wired into the LTN, and missing rows for `cnn_paper.py`,
  `baselines.py` and `novelty.py` entirely. It was rewritten *before* being promoted, or the fix
  would have propagated all of it.
- **`kg_precheck.py` persisted nothing** — the numbers blocking all of Phase 4 were prose-only. Now
  writes `kg_precheck.json`; re-ran and **the blocker reproduces exactly** (43.4 pp / 28.3 pp spread).
- **Baselines re-run at n=3 on the current metric schema** (`BASELINE_SEED` added). Closes the
  "n=1 + old schema → not citable" gap, and removes two macro figures (xgboost 0.6372, isolation
  forest 0.0628) that were quoted in STATUS tables with **no logged provenance**. Also documented
  that **XGBoost is deterministic** — seeds 42/43/44 are byte-identical, so its n=3 is n=1 with
  verified reproducibility, not a variance estimate.
- **Legacy artifact namespace collision resolved.** `outputs/metadata/{class_names,zero_day_classes}.npy`
  were temporal-split files sharing basenames with the paper split's, listing **DDoS/PortScan as
  zero-day**. Moved to `outputs/metadata/_legacy_temporal/` (new `paths.METADATA_LEGACY`) with a
  README; `cnn3.py`/`ltn.py`/`eval.py` repointed. Moved, not deleted.
- **KNOWN_ISSUES C5 counts corrected** — understated by ~2×: the seed bug affects **16 rows** (not
  8; the 8 counted distinct *tags*), and duplication is **21 names / 31 redundant rows of 88**.
- Fixed: `config.py` read `config.yaml` with the platform default encoding (cp1252 on Windows →
  `UnicodeDecodeError` on any non-ASCII character); `CLAUDE.md` said "22 scripts" 13 lines above
  saying "26"; unstruck retracted "Mahalanobis 4.3×" and stale "run Phase 3 first" directives in
  STATUS; `config.yaml` now states that its `log1p` justification cites the contaminated metric (C4).
- **Workflow:** this session used a branch + PR, restoring the CONTRIBUTING process the 2026-08-02
  session skipped (its 20 commits were merged locally with no PR ever opened).

## 2026-08-02 (post-merge audit — found and recorded a recurring process defect)

- **Audited what `origin/main` actually serves rather than trusting the merge, and found real drift.**
  Four documents still described pre-Phase-3 state. Most seriously, **`CLAUDE.md`'s component table
  still read "Anomaly pillar: ❌ Not built — decision needed first"** after Phase 3 had been built,
  run and multi-seeded — and `CLAUDE.md` is the file auto-loaded into every session, so it was the
  worst possible place for it. `STATUS.md`'s table had been updated; this one was missed.
  Also: STATUS Open Decisions still asked "run the autoencoder?" (done), Remaining Work called the KG
  an unblocked "next build" (it is blocked), and `scripts_reference.md` documented 22 of 26 scripts.
- **Root-caused it as a process defect and tracked it, rather than just patching the symptom.**
  Component status is written out independently in 4+ files, and the end-of-session checklist said
  "flip component statuses" without naming which ones — so it is satisfied by updating whichever
  table happens to be in front of you. **The same failure has now occurred twice in two sessions**
  (2026-07-29 caught it in the target docs; 2026-08-02 in `CLAUDE.md`).
- **Recorded the fix as an actionable issue:** make STATUS's Component Status the single source of
  truth and reduce the others to pointers, keep `conference_roadmap §1b` as the canonical *phase
  numbering* table, name the exact files in the checklist, and verify with a one-line grep that
  should hit one file rather than four. **Not implemented** — flagged to be done before Phase 4
  starts changing statuses. Interim mitigation added to `CLAUDE.md`: the checklist now names all
  four files explicitly and includes the verification command.

## 2026-08-02 (Phase 3 closed out — canonical results table, docs squared, branch merged)

Housekeeping pass to leave the repository in a clean state before Phase 4 begins in a new session.

- **Established a single canonical results table** (STATUS → "Last Measured Results") and made every
  other document quote it. It replaces a `_TBD_` placeholder that had stood since project start and
  still referenced the superseded `eval.py`/`ltn.py` pipeline. All figures are **n=3 mean with seed
  range**; channels that are n=1 or predate the metrics rewrite (`xgboost`, `random_forest`,
  `isolation_forest`) are explicitly listed as **not citable for comparison** rather than quoted.
- **Added an "established vs retracted" ledger** to the same section, so the status of every
  comparative claim is visible in one place: 2 established, 1 explicitly *not* established
  (CNN vs LTN control — needs a significance test), 3 retracted.
- **Refreshed README** with the Phase-3 results, the double-dissociation finding, and a
  reproducibility note stating plainly that three findings have been retracted after multi-seeding.
  Removed the stale "Mahalanobis 4.3×" row.
- **Marked Phase 3 complete** in `conference_roadmap.md` (both the canonical phase table and the
  build-plan row, with actual vs estimated effort) and in `enhancements.md` item #1, whose stated
  purpose — answer *"why not just an autoencoder?"* — is now discharged with a number.
- **Moved smoke-test artifacts out of the fusion-channel namespace** into
  `outputs/predictions/_smoke_archive/` with an explanatory README. Moved, **not deleted**, per the
  project rule that artifacts are never destroyed. 62 real channels remain, none of them smoke.
- **Tracked the Phase-4 blocker in KNOWN_ISSUES**, which had only been recorded in STATUS — the same
  living-docs drift that made the 2026-07-29 reference-tier audit necessary in the first place.

## 2026-08-02 (Phase-4 blocker — the KG's clustering premise breaks under CNN reseeding)

- **Acted on the warning raised by the train-vs-score decomposition and it broke the pre-check.**
  Extended `scripts/kg_precheck.py` to vary the **CNN seed** (the embedding itself), not just the
  clustering seed, and re-ran.
- **🔴 RETRACTED: "Bot forms a ~90%-pure cluster, stable across 2 seeds."** The two seeds originally
  varied were **clustering** seeds on a **fixed seed-42 embedding** — that measured k-means
  stability, never the stability of the representation the KG would actually be built on.

  | k | family | purity across CNN seeds 42/43/44 | spread |
  |---|---|---|---:|
  | 200 | **Bot** | **87.9% · 86.6% · 44.4%** | **43.4 pp** |
  | 200 | Web BF | 62.4% · 64.9% · 64.8% | 2.5 pp |
  | 200 | XSS | 28.1% · 29.4% · 27.8% | 1.6 pp |
  | 400 | **Bot** | **82.2% · 91.1% · 62.7%** | **28.3 pp** |

  Varying only the *clustering* seed on a fixed embedding gives Bot 87.9% vs 90.5% — spread 2.6 pp.
  **Clustering is stable; the embedding is not.**
- **The instability is specific to Bot.** Web BF and XSS purity move 0.7–2.5 pp across CNN seeds. So
  this is not general seed-sensitivity — the CNN's embedding geometry *with respect to Bot* is a
  seed lottery.
- **Two independent measures agree on which seed is bad.** Seed 44 is worst on both cluster purity
  (44.4%) and Mahalanobis Bot PR-AUC (0.0413, 1.2× ≈ chance), while its classification is
  unremarkable (macro 0.6396 vs 0.6446/0.6353). **Classification is flat across seeds; open-set
  geometry is not.**
- **The KG's value proposition inverts:** it clusters *stably* on web attacks — which the CNN already
  handles at 0.92–0.95, so clustering adds nothing — and *unstably* on Bot, the one family where a
  memory/novelty mechanism would earn its place.
- **Does not kill Phase 4**; kills "clustering CNN embeddings is a solid foundation" as an unexamined
  assumption. Four options recorded (ensemble across seeds · cluster raw features · cluster the AE's
  16-d benign-trained bottleneck · accept and publish the variance). **None implemented, none
  decided** — the representation question should be settled before `kg.py` is written.

## 2026-08-02 (train-vs-score decomposition — and "Mahalanobis 4.3×" is retracted)

- **Added `NOVELTY_SEED` to `novelty.py`** and recomputed MSP + Mahalanobis from all three CNN seeds.
  Free — both are post-hoc functions of a trained CNN, no retraining. Seed-42 outputs reproduced
  **byte-identically**, confirming determinism and leaving the original record intact.
- **Purpose: decompose the double dissociation.** MSP and Mahalanobis are the informative middle
  cases — both computed from an **(A)-trained** model but using **(B)-style** scoring. If they
  pattern with the CNN, the dissociation is driven by *what the model is trained on*; if with the
  autoencoder, by *how the score is computed*.

  | channel | train | score | macro | Bot mean [range] | lift | Web BF | XSS |
  |---|---|---|---:|---|---:|---:|---:|
  | CNN softmax | A | A | 0.6399 | 0.0446 [0.024, 0.059] | 1.3× | 0.9226 | 0.9524 |
  | MSP | A | B | 0.5884 | 0.0448 [0.024, 0.059] | 1.3× | 0.8719 | 0.8485 |
  | Mahalanobis | A | B | 0.3777 | 0.1030 [0.041, 0.147] | 3.0× | 0.5840 | 0.4462 |
  | Autoencoder | B | B | 0.0970 | 0.1314 [0.108, 0.165] | 3.8× | 0.1048 | 0.0547 |

- **Changing the scoring function alone buys nothing.** MSP lands at Bot 0.0448 vs the CNN's 0.0446 —
  indistinguishable. So the Bot failure is *not* "the signal is there but argmax discards it."
- **The dissociation is a monotonic frontier, not a binary split.** Moving A/A → A/B → A/B → B/B, Bot
  rises (0.045 → 0.045 → 0.103 → 0.131) while Web BF and XSS fall monotonically. No channel is at
  both ends. Position on the frontier is governed mainly by **what the model trains on**.
- **🔴 RETRACTED: "Mahalanobis gets 4.3× on Bot, the best Bot channel."** Seed 42 = 0.1467 (4.3×),
  seed 43 = 0.1210 (3.5×), **seed 44 = 0.0413 (1.2×, essentially chance)**. Mean **3.0×**, best-to-worst
  spread **3.6×**. The 4.3× figure was the best of three seeds and has been load-bearing — quoted in
  the thesis reframing, README, CLAUDE.md and KNOWN_ISSUES as the headline evidence that (B) methods
  work on Bot. **Third single-seed overclaim in this project** (after Ax6 and C2). Corrected at every
  forward-looking citation; dated historical entries left intact per retract-in-place.
- **The autoencoder is the better and far more stable (B) channel:** 3.8× [3.2–4.8], spread 1.5×,
  versus Mahalanobis 3.0× [1.2–4.3], spread 3.6×. (Ranges overlap, so "AE > Mahalanobis" is not
  established — but "AE is more reliable" is.)
- **⚠️ New Phase-4 warning: the CNN's classification is seed-stable while its embedding's open-set
  geometry is not.** Across the same three seeds CNN macro moves 0.009 (0.6353–0.6446) while
  Mahalanobis-on-its-embedding swings **3.6×** on Bot. The KG is specified to cluster these
  embeddings, and the Phase-4 pre-check's "Bot forms a ~90%-pure cluster, stable across 2 seeds"
  measured **clustering stability on a fixed seed-42 embedding**, *not* stability of the embedding
  across CNN seeds. Different claims — **re-run that pre-check across CNN seeds before building on it.**

## 2026-08-02 (AE multi-seeded — the (A)/(B) complementarity is established as a double dissociation)

- **Ran autoencoder seeds 43 and 44** (`AE_SEED`, seed-42 artifacts untouched, both exit 0).
  AE n=3: macro mean **0.0970** [0.0894, 0.1014] · Bot mean **0.1314** [0.1078, 0.1647].
- **🎯 CNN vs AE ranges do not overlap on ANY family at n=3 each** — the first cleanly-established
  multi-seeded comparative result in this project. (Contrast C2, where CNN-vs-LTN-control *did*
  overlap and therefore established nothing.)

  | family | CNN (A) mean [range] | AE (B) mean [range] | winner | ratio |
  |---|---|---|---|---|
  | Bot | 0.0446 [0.0241, 0.0591] | **0.1314** [0.1078, 0.1647] | **AE** | **2.9×** |
  | Web BF | **0.9226** [0.9194, 0.9288] | 0.1048 [0.0928, 0.1168] | **CNN** | **8.8×** |
  | XSS | **0.9524** [0.9485, 0.9554] | 0.0547 [0.0468, 0.0615] | **CNN** | **17.4×** |
  | macro | **0.6399** | 0.0970 | **CNN** | 6.6× |

- **This is a double dissociation, which is a stronger claim than "method X is better."** Each method
  wins decisively where the other fails, with non-touching seed ranges — ruling out noise, "the AE is
  just weaker" (it beats the CNN 2.9× on Bot), and "the CNN is just better" (it loses on Bot while
  winning 8.8–17.4× on web attacks). **The complementarity that the falsified modality account was
  invented to explain is itself real** — the pattern survived; only the explanation died.
- **Honest scope:** both methods remain weak in absolute terms on Bot (0.13 vs 0.045, chance 0.034),
  so "AE wins on Bot" means 3.8× chance vs 1.3× chance — a robust relative difference, not a solved
  problem. And the mechanism is now **openly unknown**, which is where it should stay until measured.
- Also notable and unexplained: on the underpowered families the AE reaches **121.8×** (Infiltration)
  and **125.3×** (Heartbleed) mean lift, versus the CNN's 1.4× and 0.5×. Direction only (n=36, n=11).

## 2026-08-02 (modality test — falsifies the same-day Phase-3 interpretation)

- **Built and ran `scripts/modality_analysis.py`** to test the "modality analogue" account proposed
  hours earlier. **All four predictions were written into the script before it was run**, and the
  design deliberately guarded against circularity three ways: repeat every measurement in **raw
  feature space** (untrained by any model), report **which** known class is nearest (a named,
  falsifiable prediction), and test **per-flow** rather than across only 6 families.
- **🔴 The account was largely falsified — and the guards are what caught it.**
  - **Named mechanism wrong.** Web Brute Force / XSS do **not** sit nearest FTP/SSH-Patator (the
    claimed shared "brute-force authentication" modality). Their nearest known attack in raw space is
    **DoS Hulk — 80% and 96% respectively.** DoS Hulk is an HTTP flood, so any shared modality is
    "HTTP traffic on port 80", not brute force.
  - **Direction backwards.** Median raw distance from the benign manifold: **Bot 7.28**, Web BF 8.86,
    XSS 8.84, BENIGN 6.10, Infiltration 23.25, Heartbleed 34.25. **Bot is closer to benign than the
    web attacks are** — so "the AE catches Bot because Bot is structurally anomalous" cannot hold.
  - **The "categorical split" was a threshold artifact.** It came from recall@1%FPR (Bot 0.0082 vs
    web 0.0000 — both effectively zero). On **lift**, the AE is comparably weak across all powered
    families: **Bot 3.6×, Web BF 4.4×, XSS 5.3×** — web attacks are *higher* than Bot. The AE's
    genuinely large numbers (Heartbleed 103×, Infiltration 145×) are on the two families
    `metrics.py` excludes as underpowered (n=11, n=36).
  - **The best-looking evidence was circular.** `corr(margin, CNN−AE advantage)` = **+0.933 in CNN
    embedding space** but **−0.388 in raw space**. The embedding figure is near-tautological —
    `margin` correlates **+0.863** with the CNN's own log-odds there, restating its decision rather
    than predicting it. Discarded.
- **One prediction held, after correcting my own test design.** The AE *is* a raw-space
  distance-from-benign detector: `corr(d_benign_raw, AE error) = +0.732` on zero-day flows. My first
  pass measured this in embedding space (+0.069) — wrong geometry, since the AE reconstructs raw
  features. Both numbers recorded.
- **Net effect on the thesis:** (A)/(B) complementarity survives as an *empirical pattern*; the
  modality-analogue *explanation* for it does not, and must not go into a paper draft as a mechanism.
  The fusion/router proposal rested on that mechanism and is accordingly no longer motivated as-is.
  The open question is now sharper and more honest: **why is the CNN specifically so bad on Bot**,
  given the oracle result proves the information is present in the features?
- Corrected the Phase-3 interpretation **in place** in STATUS (red box above the original text, which
  is preserved unedited) rather than rewriting it, per the project's retract-in-place convention.
  Full numbers: `outputs/metadata/modality_analysis.json`.

## 2026-08-02 (Phase 3 RUN — the autoencoder result refines the thesis rather than confirming it)

- **Ran `scripts/autoencoder_paper.py` (canonical Phase 3).** Converged cleanly, 50 epochs, exit 0,
  zero attack labels used in training *or* model selection. **n=1 (seed 42) — provisional.**
- **The stated falsification condition was NOT met, so the 2026-07-29 reframing survives on Bot** —
  but it was **too strong as written and is now refined in place, not retracted.** The AE scored
  **Bot PR-AUC 0.1217 (3.6× chance)**, the second-best Bot result ever measured here (behind only
  Mahalanobis at 4.3×). Both top-2 Bot channels are (B)-family, as predicted.
- **But the AE collapses on web attacks**: macro **0.1000** vs the CNN's 0.6399, with **exactly
  0.0000 recall** on Web Brute Force, XSS *and* SQL Injection at 1% FPR — while catching
  **Heartbleed at 1.0000 recall** and **Infiltration at 0.8611**. That is a categorical split, not a
  performance gradient, and it refutes "the project is investing in (A) on a structurally (B)
  problem" as a blanket claim.
- **The refined account — modality analogue, not method family.** Web attacks are *structurally
  normal*: HTTP to port 80, indistinguishable from ordinary browsing in the 68 flow features (what
  makes them malicious is payload content, which this feature set lacks), so a benign-trained
  autoencoder reconstructs them perfectly and 0.0000 recall is the honest expected result. The CNN
  nonetheless scores 0.92–0.96 on them **not** by solving zero-day detection but by
  **within-modality transfer** — Web Brute Force resembles FTP-Patator/SSH-Patator, which *are*
  training classes. Bot has no such analogue (independently established: `BeaconLike` fires on 97.6%
  of PortScan and **0.0% of every other known attack** — no known class beacons), so every
  supervised method sits at 1.5–1.8× and only distance/reconstruction methods win.
  **Governing variable: does the unseen class share a behavioural modality with some known class?**
  Yes → (A) wins. No → (B) wins. Neither family dominates; they are complementary.
  > 🔴 **CORRECTION (2026-09-05) to the parenthesis above — kept in place, not rewritten.**
  > *"what makes them malicious is payload content, which this feature set lacks"* is **wrong as an
  > INFORMATION claim**, and it was already contradicted by a measurement taken the very next day.
  > `bot_failure_analysis.py`'s H4 oracle probe (XGBoost, family-vs-benign, fit/eval split inside the
  > test set) separates the web families from benign **using the 68 flow features alone**:
  > **Web Attack Brute Force 0.9999 · Web XSS 0.9984 · Bot 0.9988** PR-AUC
  > (`outputs/metadata/bot_failure_analysis.json` → `H4_raw_oracle_separability`).
  > The discriminating information **is present in the flow features**; what the feature set lacks is
  > any way to surface it **without labels**.
  > **The narrower statement survives and is the one to cite:** web attacks sit inside the benign
  > region *of a benign-only reconstruction manifold*, so the AE's 0.0000 recall is the honest
  > expected result — a property of unsupervised density modelling, not of the modality.
  > ⚠️ As written, this parenthesis was **the strongest pro-payload sentence in the record**; the
  > 2026-09-05 payload assessment turns on exactly this distinction. n=1 (seed 42) — but at 0.998+
  > with a held-out half, seed sensitivity is not the live risk; the live caveats are that an oracle
  > is an *upper bound given labels*, and that Bot's top-8 includes capture-setup artifacts
  > (`Destination Port` 8080, `Init_Win_bytes_forward` 8192).

- **This makes the fusion wall the central architectural problem rather than a side issue.** Each
  family covers exactly what the other misses, so the system needs a per-flow **router** — and the
  router is precisely what cannot be *fitted*, since any combiner is calibrated on validation data
  containing no zero-day flows (`fusion_beaconlike.py` → `[2.35, 0.02]`).
- **It also gives the Knowledge Graph its first well-motivated job.** "Is this flow in a region with
  no known-class analogue?" is a clustering/density question answerable **without labels**, and the
  Phase-4 pre-check already showed the structure exists (Bot forms a ~90%-pure cluster at k≥200,
  stable across seeds). That is a *routing* signal, not a detection signal.
- **Flagged as interpretation, not measurement.** The modality account explains every prior null and
  is predictive, but has not been measured. Concrete next test: compute each zero-day family's
  embedding distance to the nearest known-class centroid and check it predicts which family wins.

## 2026-08-02 (C2 resolved — CNN baseline is n=3, overlaps the LTN control; Phase 3 built)

- **Added multi-seed support to `cnn_paper.py`** (`CNN_SEED`/`CNN_TAG` env vars, mirroring
  `ltn_paper.py`'s existing `LTN_SEED`/`LTN_TAG` convention). TAG defaults to the original
  `cnn_paper` filenames unchanged at the config seed (42), and to `cnn_paper_s<seed>` otherwise, so a
  differently-seeded run can never overwrite the reference model/scaler/encoder/embeddings. Verified
  by hash before and after: all 9 reference artifacts byte-identical post-run.
- **Ran seeds 43 and 44** in the background with a heartbeat monitor. One false alarm during
  monitoring — see the separate entry below — training itself completed cleanly both times (exit
  code 0). Seed 43: macro 0.6355 (raw) / 0.6353 (log-odds). Seed 44: macro 0.6396 / 0.6396.
- **Found and fixed a real bug in `rescore_logits.py` while rescoring the new seeds**: every
  `_logodds` entry was stamped with the config-default seed (42) regardless of which seed's model was
  actually rescored — wrong on 8 pre-existing rows. Fixed to parse the seed from the tag's `_s<N>`
  suffix. The 8 already-wrong historical rows were deliberately left as-is (append-only log,
  retract-in-place convention) — anything reading them must group by run name, not `params.seed`.
  Cross-checked that STATUS's already-published LTN-control range was unaffected by this bug (it must
  have been read by name originally).
- **C2 resolved: `cnn_paper` is now n=3 (log-odds), mean 0.6399, range 0.6353–0.6446 — and this
  range sits entirely inside the LTN control's n=3 range (0.6029–0.6505).** Stronger evidence for the
  original concern than the single-point check that opened it: not one number falling in an interval,
  but two full 3-seed distributions overlapping almost completely. **Resolved to "no clean winner at
  this n, needs a proper significance test" — not to "CNN confirmed."** The axiom-cost finding
  (Ax6 variants well outside both ranges) is unaffected and survives as the one comparison this data
  can actually support.
- **Built `scripts/autoencoder_paper.py` — canonical Phase 3.** Benign-only, dense encoder/decoder
  (68→48→32→16→32→48→68), trained and model-selected using zero attack labels, scored by
  reconstruction MSE. This is the direct falsification test of the 2026-07-29 thesis reframing: if it
  also lands at chance on Bot, that reframing is wrong and must be retracted in place. Not yet run.
- **Found and documented a Windows Git-Bash monitoring pitfall**: a `ps aux`-based liveness check
  reported the seed-43 training process dead at epoch 2 — no error, no traceback, training had
  actually continued normally and completed minutes later. `ps` enumeration under MSYS2's
  WINPID-mapped process listing can miss a live process for a single poll tick. Fixed the live
  monitor (and recorded the convention) to require sustained **log-growth staleness** across several
  consecutive polls before declaring a job dead or hung; a single `ps` miss is now advisory only.

## 2026-07-29 (thesis reframing — the Phase-2 nulls share one structural cause)

> **Reinterpretation of existing measurements. No new runs. Phase 3 has NOT started** — verified: no
> autoencoder script, no AE model, no AE entry in `runs.jsonl`. Everything this session was
> pre-Phase-3 (documentation, readiness analysis, retrospective audit).

- **Refuted the LOCO fusion fix proposed earlier the same day — before spending any compute on it.**
  Measured how `BeaconLike` actually fires per class: **PortScan 97.6%, every other known attack
  0.0%, BENIGN 22.7%** (each non-PortScan known attack targets a well-known port, so the signal is
  silent on them). A leave-one-class-out rotation is therefore **predictably null**: 7 of 8 folds
  teach the combiner the channel is worthless, and the 1 PortScan fold teaches it the channel is
  valuable *for the wrong reason* (port scanning, not C2 beaconing on 8080). The specifically
  recommended "cheap probe: hold out PortScan first" was **the worst available choice** — the one
  fold guaranteed to produce a false positive and validate an approach that would then fail.
- **The refutation is a better result than the fix would have been:** you cannot manufacture a
  synthetic zero-day that exercises BeaconLike in a Bot-like way, because **no known class in
  CIC-IDS2017 beacons.** LOCO is not broken — the known-class pool does not span the behavioural
  modalities of the unknown classes, so the fusion failure is not repairable by protocol alone.
- **Reframed the Phase-2 nulls as one structural fact rather than five failures.** Prompted by the
  question "if val contains no zero-day by construction, is the training premise flawed?" The
  protocol is **sound** — absence of zero-day from train/val is the *definition* of the problem, and
  putting Bot in validation would make the metric meaningless. What is flawed is the buried
  assumption that **a mechanism fitted on data can transfer to classes absent from that data**. That
  assumption underlies the LTN axioms, the aux head, the fitted fusion, *and* the KG's planned
  `s_kg` path — which is why all four fail identically.
- **Named the split that follows: (A) learn-what-attacks-look-like** (needs attack examples, cannot
  reach novel classes) **vs (B) learn-what-normal-looks-like** (needs only benign, reaches novel
  classes by construction). The project invested in (A) on a structurally (B) problem. **The existing
  Bot evidence already said so:** Mahalanobis **4.3×**, IsolationForest **1.7× while never seeing a
  single attack**, versus the CNN's 1.7× and every LTN variant's noisy 1–2×. The IsolationForest
  observation has been in STATUS since 2026-07-27; its significance was not drawn out until now.
  The oracle result (0.0314 → **0.9764** with ~1,000 labels) confirms this is a *transfer* limit of
  closed-set methods, not an information-theoretic one.
- **Consequence: the Phase-3 autoencoder is promoted from reviewer-objection checkbox to the
  load-bearing next experiment.** It is a pure (B) method, ~1h, and the direct falsification test of
  the reframing — if a benign-only AE also lands at chance on Bot, the (A)/(B) account is wrong and
  the reframing must be retracted in place. LOCO/fusion-repair work is deprioritized accordingly.
- **Proposed thesis statement (not yet adopted):** *"Closed-set supervised learning cannot transfer to
  novel classes regardless of where symbolic knowledge is injected — loss-, representation- and
  inference-level all fail for one shared structural reason. Open-set/distance methods reach the same
  families without labels."* Consistent with conference_roadmap Tier-S #1; sharpens it, not replaces it.

## 2026-07-29 (earlier-phase audit — 5 open concerns + a proposed fix for the fusion wall)

> **Findings only. No fixes implemented — all await go-ahead.** Full detail in
> [STATUS.md](STATUS.md) → "Earlier-phase audit"; tracked individually in
> [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

- **Verified no records were lost in the same-day documentation rewrite.** Audited every deleted line
  across 24 files: all 23 dated CHANGELOG headers preserved (+1 new), every retracted claim preserved
  **verbatim inside `~~strikethrough~~`** with its retraction box. Two genuine losses were found and
  restored: the caveat that the **temporal CNN baseline (0.6689) may itself have been hampered by the
  focal-loss bug** (research-relevant — it is the denominator in "LTN 0.4529 vs CNN 0.6689", and a
  clean baseline would make the LTN deficit *larger*; never retrained, still unquantified), and the
  concrete `.gitignore` failure detail. Process note: both losses came from full-file `Write`
  rewrites — avoid that on record-bearing files.
- **🔴 Found 17% duplicate leakage between train and test.** CIC-IDS2017 is duplicate-heavy and the
  paper split is stratified random, so 19,513 / 114,658 test rows have an exact feature-vector twin
  in train — PortScan **58.3%**, SSH-Patator **48.6%**, DoS Hulk 25.3%, BENIGN 6.9%. **All 6 zero-day
  classes measure 0.0%**, so the headline macro zero-day metric is safe; what is contaminated is the
  ~0.98 overall binary PR-AUC. Proposed: report a unique-flows-only variant alongside, rather than
  de-duplicating (which would break base-paper comparability).
- **🔴 Found the reference baseline is single-seed while its comparators are not.** `cnn_paper`
  (0.6446) is n=1; the LTN control is n=3 and spans **0.6029–0.6505** — an interval that *contains*
  0.6446. STATUS's claim "neither variant beats the plain CNN, the neural baseline still wins in
  aggregate" therefore compares a point estimate against a distribution — the same error class that
  produced the Ax6 retraction. Two more CNN seeds would confirm or overturn it.
- **Tested and REFUTED a hypothesis of my own.** Web Brute Force and Web XSS correlate at
  **r = +0.992** across 60 runs, so the macro counts one web signal twice (⅓ Bot, ⅔ web). Predicted
  this biased the metric against Bot-targeted interventions like Ax6. Regrouping to
  `mean(Bot, mean(WebBF, XSS))` **preserved the ordering exactly** (0.4982 > 0.4824 > 0.4596 >
  0.3977) — the macro-cost finding is robust, and now more so. Absolute values shift ~0.15.
- **Found the feature transform was selected on the contaminated metric.** `log1p` is pinned citing
  "0.980 vs 0.965", which is the overall binary number — inflated by the duplicate leakage above and
  explicitly forbidden by `metrics.py` as an optimisation target. Never A/B'd on macro zero-day PR-AUC.
- **Found two `runs.jsonl` metadata defects:** `rescore_logits.py` stamps `seed: 42` on every
  `_logodds` row including s43/s44-derived ones (wrong on 8 rows), and repeated rescoring runs left
  triplicate entries.
- **🔑 Proposed a fix for the fusion wall — Leave-One-Class-Out.** The wall: a fitted combiner cannot
  learn to weight a zero-day-specific signal because validation contains no zero-day flows by
  construction (`[2.35, 0.02]`), and the KG feeds fusion the same way. The fix: **manufacture
  synthetic zero-day from known classes** — hide one known attack class from CNN training, retrain,
  and that class becomes a genuine novel class in validation; fit the combiner there and rotate over
  the 8 known classes. Gives the combiner the missing *regime* ("CNN confused by novelty + what the
  symbolic channel said"), which transfers, unlike a class-specific fact. Does not leak — the 6 real
  zero-day families are never touched. Cheap probe: hold out PortScan only, **1 retrain**; if the
  BeaconLike coefficient moves off 0.02 the approach is alive. Complementary alternative: conformal
  benign-only p-value calibration (Fisher combination), which needs no attack labels at all.
  This would upgrade the result from a dead end to *"inference-time fusion fails naively, and here is
  the protocol that repairs it."*

## 2026-07-29 (documentation audit — reference tier reconciled with reality before Phase 4)

Full read-through of all 27 project `.md` files. The **living tier** (STATUS / CHANGELOG /
KNOWN_ISSUES / DASHBOARD / CLAUDE / CONTRIBUTING) was found current and honest; the **reference
tier** (`docs/*.md`, `docs/implementation/`, `docs/target/`) was frozen at 2026-06-18 and in several
places asserted the *opposite* of confirmed findings. Nothing marked which tier a reader was in.

- **Two substantive findings, not just doc rot:**
  1. **A phase-number collision was about to skip a whole phase.** STATUS called the Knowledge Graph
     "Phase 3" while the canonical roadmap — *and STATUS's own component table, and a comment in
     `cnn_auxhead_paper.py`* — used Phase 3 = **anomaly pillar (benign-only autoencoder)** and
     Phase 4 = KG. The number was reused, not reassigned. The autoencoder (~1h, ranked Tier-1
     "highest leverage", closes the "why not just an autoencoder?" reviewer objection) was on track
     to be silently dropped. Canonical numbering table added to
     [conference_roadmap.md §1b](target/conference_roadmap.md); the autoencoder is now an explicit
     **Open Decision** in STATUS rather than a default.
  2. **`preprocess.py` hardcoded its input path**, bypassing `paths.py` — which still pointed
     `RAW_CSV` at the abandoned `data/raw_csv`. Added `paths.RAW_CSV_FULL` and `paths.PAPER`, marked
     `RAW_CSV` legacy, and pointed the script at the constant. All 22 scripts compile; paths verified.
- **Corrected content that was actively wrong:** README's "Key Results" advertised the **retracted**
  claim that the LTN improves zero-day recall; `artifacts.md` stated `behaviour_thresholds.npy` is
  "NOT generated by any current script" (false since the 2026-06-18 rebuild — the file is on disk);
  `ltn_current.md` still said results were "⏳ pending" for a run that finished, underperformed
  (0.4529 vs 0.6689) and was superseded; `neuro_symbolic.md`'s warning banner described two bugs that
  had been fixed a year of project time earlier.
- **Documented what existed but wasn't written down:** `scripts_reference.md` covered 7 of 22 scripts
  — rewritten to cover all, grouped current / analysis / legacy. `BeaconLike` (the 7th behaviour, the
  Ax6 signal) was absent from the behaviour audit, along with two properties that have already caused
  bugs: `BEHAVIOUR_NAMES` ordering is load-bearing (a `[:5]` slice would have silently dropped it),
  and it is the only **binary**, non-graded behaviour — which matters for fuzzy conjunctions and for
  KG edge weights.
- **Rebuilt KNOWN_ISSUES.md**: fixed duplicated `## High`/`## Medium` headings (the file was two
  interleaved halves), closed 5 stale `[OPEN]` issues, added a `[SUPERSEDED]` tier, and added the
  entire missing 2026-07-27 measurement-defect class (float32 saturation, size-weighted headline,
  ω-collapse, Smart App Control) which previously lived only in STATUS/CHANGELOG. New issues logged:
  `runs.jsonl` mixes two metric schemas (**`random_forest` has never been re-scored on the corrected
  macro metric**), behaviour validation tables are temporal-split, smoke-test artifacts pollute
  `outputs/predictions/`.
- **Applied retract-in-place markers to CHANGELOG**, which had been violating the project's own
  convention: three entries still asserted the Ax6 Bot-lift claim and the beaconing thesis as
  settled. STATUS struck them through; CHANGELOG did not. Newest-first ordering is not sufficient —
  someone citing an entry reads it in place.
- **Banners** added to every frozen reference doc naming what specifically is stale in each and
  pointing at STATUS, plus a superseded banner on the archive doc (which still lists Bot as a
  training class — the exact error CLAUDE.md names as a confirmed failure mode).
- **Phase-4 (KG) readiness audit** — inputs verified against disk, not assumed: embeddings exist for
  all three splits (883,796 / 110,475 / 114,658 × 64), `meta_*.csv` are row-aligned and carry
  IP/port/timestamp, `networkx` + `python-louvain` import cleanly. Split sizes, the 9 known / 6
  zero-day class lists, and every per-family count quoted in the docs were re-derived from the arrays
  rather than copied from STATUS (all matched: 4,183 zero-day test flows, Bot n=1,956).
- **Ran a falsification pre-check on the KG's core assumption** (that zero-day flows cluster
  separately in the CNN embedding space — the space where Bot scores at chance). MiniBatchKMeans,
  k ∈ {50…800} × 2 seeds. **The prediction was half wrong, in the useful direction:** zero-day flows
  do land 100% in benign-dominated clusters, *but they concentrate rather than smear* — **Bot forms a
  ~90%-pure cluster at k≥200, stable across both seeds**, capturing ~34% of Bot. Real structure
  exists to hang a graph on. Recorded with its caveats (n=2 seeds, oracle purity measured with test
  labels = upper bound, geometric not detection metric).
- **Three assumptions in `knowledge_graph.md` were found no longer to hold**, and are now documented
  at the top of that spec as a readiness review: (1) it calls the KG the "primary zero-day signal"
  while `conference_roadmap.md` says "not primary detector" — an unresolved scope contradiction;
  (2) the fusion path a primary detector needs is **already measured to fail** — a non-leaky combiner
  cannot be fit on a val set that by construction contains no zero-day flows, exactly as
  `fusion_beaconlike.py` demonstrated (`[2.35, 0.02]`, zero macro change) — so
  `decision_fusion.md`'s prescribed remedy is impossible and has been struck through with the three
  real options; (3) "temporal decay" has no time axis under a stratified-random split.
- **Identified the single most important untested quantity for Phase 4:** 25 of 50 clusters are
  already >90% benign in training, so the spec's "unexplained by known AttackType ⇒ emerging"
  criterion will fire on ordinary benign clusters as well as on zero-day ones. Its false-positive
  rate is unmeasured and decides whether the mechanism works — measure it before building the graph.

## 2026-07-29 (live local ops dashboard — "open preview" now means real-time, not a static snapshot)

- **Built `scripts/dashboard_server.py`**: a localhost-only (127.0.0.1, not network-exposed) Python HTTP server, stdlib `http.server` + `psutil`. Polls real machine state every 4s — CPU/RAM, git branch + uncommitted-file count, running training processes (matched against known pipeline scripts, reporting PID/CPU/mem/elapsed), the tail of whichever `outputs/*.log` file changed most recently (decoded leniently to survive the mixed UTF-8/UTF-16LE issue below), and the full `runs.jsonl` run history.
- **The Reconnect button reflects genuine connectivity**, not a decorative re-render: if a poll fails, the LIVE badge flips to a red "stalled" state and the button forces an immediate retry.
- Added `.claude/launch.json` (`preview_start` config: `"phase2-dashboard"`) and `docs/DASHBOARD.md` documenting the convention, file responsibilities, and when to update the live server vs. the static Artifact.
- **Superseded the earlier static-Artifact-only dashboard** (a published claude.ai Artifact, `phase2_console.html`) built and validated (colorblind-safe palette via `validate_palette.js`) the same day as the housekeeping below — that snapshot still exists for sharing outside a session, but "open preview" no longer means it.
- Added `psutil==6.1.0` to `requirements.txt`, marked dashboard-only (not part of the ML pipeline). PR #18.

## 2026-07-29 (session-discipline non-negotiables codified into CLAUDE.md — git housekeeping)

- Merged PRs #14–#17 from the previous session's work: a **model-selection convention** (recommend Opus/Sonnet/Haiku per step so the user doesn't overspend on Opus for routine work; explicitly marked as must-not-lapse after it silently stopped appearing mid-session once), a **"state phase back"** onboarding step (forces confirming STATUS.md's state actually landed, not just got read), and four new **working-convention non-negotiables**: provisional-claim discipline (a finding from one run/seed is "n=1, unverified," not fact — directly motivated by the Ax6 Bot-lift retraction below), retract-in-place documentation (strike through, don't silently rewrite — STATUS's 2026-07-27 entries are the reference example), a heartbeat-monitor requirement for any background job expected to run >10–15 min, and the PowerShell mixed-encoding pitfall (now also in [KNOWN_ISSUES.md](KNOWN_ISSUES.md)).
- These are process fixes, not research results — no component status changed.

## 2026-07-27 (ratio-mode fix confirmed — collapse eliminated, Bot question still unresolved)

- **Tested the fix suggested by the collapse diagnosis:** re-ran seeds 42, 43, 44 at ω=1.0 with `LTN_OMEGA_MODE=ratio` instead of `fixed`. Seeds 43 and 44 are the direct test — both collapsed catastrophically under fixed mode (macro 0.0520, 0.0366).
- **Zero collapses across all 3 seeds.** Log-odds macro: 0.6051 / 0.5796 / 0.5914 (mean 0.5920), a tight range with both previously-catastrophic seeds landing comfortably in the working range. Confirms the diagnosed mechanism precisely — adapting the SAT weight to the actual CE magnitude removes the coin-flip dynamic entirely.
- **Also, incidentally, the best Ax6 macro found all session** (mean 0.5920, beats fixed ω=0.5's mean of 0.5090) — though still below the clean no-axiom control's mean (0.6194); the macro cost is real, just smaller and now free of catastrophic risk.
- **Does not resolve the earlier Bot-lift retraction.** Bot lift stays noisy under ratio mode too (0.9x/3.2x/1.3x, mean 1.8x) and doesn't clearly exceed the control's own mean (2.07x) — consistent with the multi-seed retraction from earlier the same day. The fix solves stability, not whether Ax6 reliably helps Bot detection; that remains open, and the evidence so far leans negative. `ratio` mode is now the clearly preferred choice over `fixed` for any future loss-level injection work, since it removes a real failure mode at no measured cost.

## 2026-07-27 (ω=1.0 collapse mechanism diagnosed — free, from existing logs)

- **Diagnosed why `ltn_ax6_w1p0` collapses in 2 of 3 seeds**, using only logs already on disk — no new training. Had to work around a mixed PowerShell/Python encoding issue in the batch logs (header lines UTF-16LE, python's own stdout UTF-8, interleaved in the same file); resolved by locating markers at the raw byte level and decoding each segment with the right codec.
- **The pattern:** in both collapsed seeds, the model's best epoch is 1–2 — it never meaningfully improves beyond random initialization (best val_acc 92.8% / 96.2%), and best-by-val-loss early stopping locks that in within ~10 epochs. The seed that worked kept improving through epoch 3 and reached 99.6% val accuracy. SAT values look similar across all three runs (~0.17–0.26) — visually this doesn't look like the same catastrophe as ω=2.0, but the underlying cause is the same.
- **Mechanism:** `LTN_OMEGA_MODE=fixed` means the SAT weight doesn't adapt to how large CE actually is. Whether SAT or CE dominates the gradient during the first couple of epochs depends on random initialization; if SAT wins that window, the model gets pulled toward satisfying axioms over learning to classify, and early stopping locks in the result before it can recover. ω=1.0 sits right at the edge where this can go either way depending on seed; ω=0.5 has enough margin to avoid it every time (0/3 seeds); ω=2.0 has none (100% reproducible on n=1, now understood as the same dynamic with zero margin rather than a separate failure mode).
- **Suggested fix, untested:** `ratio` omega-mode (already implemented, adapts SAT weight to the actual CE/SAT ratio) or a warmup schedule should remove the coin-flip dynamic, since the failure is specifically "fixed weight doesn't match the actual early-training ratio." Next concrete experiment if this line of investigation continues.

## 2026-07-27 (multi-seed results — the Ax6 headline finding is retracted)

- **Ran 2 additional seeds (43, 44) for `ltn_ctrl_w0`, `ltn_ax6_w0p5`, `ltn_ax6_w1p0`** (n=3 each with seed 42) and log-odds re-scored all 6 new models. This was flagged as necessary before shipping any comparative claim as far back as the aux-head reproducibility gap earlier the same day — it caught a real overclaim within hours of that warning being written.
- **RETRACTED: "Ax6 roughly doubles Bot's lift."** With n=3 seeds, the control's mean Bot lift (2.07x, range 1.5–2.9x) is *higher* than either Ax6 variant's (1.87x / 1.70x, both narrower ranges). The original single-seed comparison (1.5x control vs 2.2x Ax6) pitted the control's worst seed against Ax6's best seed — pure seed luck, not a real effect. Flagged as retracted at every place this session claimed it: the integration-points table, the B2 write-up, and the log-odds re-score entry.
- **What survives, and is now stronger than the single-seed version:** Ax6 robustly costs macro PR-AUC — zero overlap between the control's range (0.60–0.65) and either Ax6 config's, across all 3 seeds. That part of the finding is *more* solid than it looked on n=1, not less.
- **New finding: ω=1.0 is not the "safe zone" it appeared to be.** 2 of 3 new seeds collapsed catastrophically (macro 0.052, 0.037; both early-stopped by epoch 10) — the same failure mode as `ltn_anat_w2p0`'s deterministic ω=2.0 collapse, just triggered stochastically near ω=1.0 rather than always. Seed 42's 0.5316 was the lucky outcome, not representative. ω=0.5 is comparatively more stable (0/3 seeds collapsed) but still consistently below the control on macro.
- **Bot lift is highly seed-sensitive even with zero axioms** — the control alone swings from 1.5x to 2.9x across seeds. Any single-seed claim about Bot detection at this scale (n=1,956 test flows) needs multiple seeds to mean anything.
- Net: the fusion finding and the macro-cost finding both survive this correction; the specific "Ax6 helps Bot" claim does not. If Ax6 is pursued further, the priority is understanding why ω=1.0 collapses 2/3 of the time before drawing more conclusions from single runs at that setting.

## 2026-07-27 (inference-level fusion — the third integration point tested, and why it fails)

- **Checked whether Ax6 generalizes to zero-day families it wasn't designed from** (Heartbleed n=11, Infiltration n=36, SQL Injection n=21) using data already on disk from the earlier Ax6 runs. Mixed and noisy: Heartbleed and Infiltration move in the right direction (0.5x→2.9x, 0.8x→1.4x lift), SQL Injection moves the wrong way (369x→256x) — but at these sample sizes any of these could flip from one or two predictions changing. The only statistically meaningful signal remains Bot up / Web attacks down. Flagging this explicitly: Ax6 was designed by looking directly at Bot's labels (the feature-importance scan in `skyline_oracle.py`), so "Ax6 helps Bot" is a weaker zero-day-generalization claim than it might read as — it's closer to "hand-built rule works on the class it was built for" than evidence of transferable symbolic knowledge.
- **Built and ran `scripts/fusion_beaconlike.py`** — the third of the "three symbolic integration points" from `conference_roadmap.md`, and the one never attempted before this session. Fits a small logistic combiner (CNN's attack log-odds + BeaconLike's raw score) on validation data only — the paper split's val set contains no zero-day flows by construction, so this cannot leak into the zero-day evaluation, unlike the "leaky fusion" already flagged as invalid in earlier entries.
- **Result: fusion changes nothing.** Macro 0.6447 vs the CNN's 0.6446 alone; Bot lift 1.7x, identical to baseline. Fitted coefficients came back `[2.35, 0.02]` — the combiner learned to essentially ignore BeaconLike.
- **This is a real, mechanistic finding, not a failed experiment.** The fusion weights are fit on validation data, which cannot contain the pattern (Bot) that makes BeaconLike valuable — a non-leaky calibration structurally cannot discover the worth of a zero-day-specific signal. This explains why loss-level injection (Ax6) is currently the *only* mechanism, of the three tested, that gets a hand-specified zero-day signature into the model at all: it imposes the constraint directly rather than requiring the data to reveal its value. Reframes the macro cost Ax6 pays from "a flaw to fix with fusion" to "the price of the only lever available" — at least for this signal.

## 2026-07-27 (log-odds re-score — resolves the deferred CE finding, strengthens the control)

- **Retrained `cnn_auxhead_l0.5`** (needed the `model.save` added earlier) and ran `scripts/rescore_logits.py` across all 10 saved models now that TF is unblocked.
- **Corrects the 3 genuinely-saturated runs.** `ltn_ctrl_w0` moves from 0.5937/~1.0x Bot lift to a clean **0.6049/1.5x**; `ltn_repro` and `ltn_v2` similarly move up. ~~The Ax6-vs-same-ω comparison from the previous entry is untouched — neither `ltn_anat_*` nor `ltn_ax6_*` was ever saturated, so "Ax6 roughly doubles Bot lift" still holds exactly.~~
  > 🔴 **RETRACTED later the same day (marked in place 2026-07-29).** The struck sentence is wrong in
  > its *conclusion*, not its premise: it is true that neither side was saturated, so log-odds
  > rescoring didn't disturb the comparison. But the comparison was **single-seed**, and with n=3 the
  > control's mean Bot lift (2.07x) exceeds both Ax6 variants' (1.87x, 1.70x). "Still holds exactly"
  > was reasoning about the wrong threat — it checked for a measurement artefact and concluded
  > robustness, when the actual problem was seed variance. See the multi-seed entry above.
- **Resolves the deferred CE-vs-focal question: false alarm.** `ltn_repro` (CE + base axioms) was flagged as the worst fair-loop variant based on its saturated blended score. Cleanly measured it's mid-pack (macro 0.5751), between the control and the old fixed-ω axiom variants — plain CE isn't demonstrably a poor loss choice here.
- **The clean control is stronger than previously measured**, which raises the bar the axioms have to clear: even with zero axioms, the custom loop already gets 1.5x lift on Bot. Ax6's honest accounting against the *best* baseline is +0.7–1.1x Bot lift for a ~0.07–0.09 macro cost — a real, worthwhile, but not free trade, not a wash against a weak control as it looked before this correction.
- **`ltn_anat_w2p0`'s collapse is confirmed genuine, not a saturation artefact** — PR-AUC is rank-based and threshold-independent, so it only moves under log-odds rescoring when tie blocks were corrupting the ranking (true for the other 3). It stays at 0.0348 here, meaning the ω=2.0 model's weights actually degenerated rather than merely underflowing its output scores.
- **The aux-head retrain didn't reproduce its own Bot number** — 0.8x lift this run vs ~1.0x the first time, same seed and config. Most plausible explanation is ordinary single-seed noise (TF training isn't bit-deterministic across runs even with a fixed seed), which is itself a concrete argument for the still-outstanding multi-seed work before any comparative claim ships.

## 2026-07-27 (Ax6 trained — ~~prediction confirmed~~ 🔴 **RETRACTED**, with a real tradeoff)

> 🔴 **This entry's headline did not survive multi-seeding** (marked in place 2026-07-29). The
> "prediction confirmed" framing rests on **seed 42 only**. What survives from this entry: the
> *tradeoff* (Ax6 costs macro PR-AUC) — which multi-seeding made **stronger**, not weaker — and the
> observation that neither variant beats the plain CNN. What does not survive: that Ax6 helps Bot.

- **TensorFlow unblocked.** Root cause was Windows Smart App Control (`VerifiedAndReputablePolicyState=1` in `HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy`), rejecting TF's unsigned compiled wheels under its "Enterprise signing level" requirement. User turned it off via Windows Security; reversible without reinstall on this build (25H2, build 26200.8875, past the 26200.8116 cutoff). Not a code or environment problem.
- **Ran `ltn_ax6_w0p5` and `ltn_ax6_w1p0`** — identical configs to the earlier `ltn_anat_w0p5`/`w1p0` runs, with Ax6 (`BeaconLike`) now live in the axiom set. ~~**B2's prediction is confirmed: Bot lift roughly doubles at both ω values** (1.1x → 2.2x at ω=0.5; 1.1x → 1.8x at ω=1.0). The axiom-injection mechanism was never the bottleneck — the old axioms simply targeted the wrong signature.~~
  > 🔴 **RETRACTED (marked in place 2026-07-29).** Single seed. With n=3 the no-axiom control's own
  > Bot lift ranges **1.5–2.9× (mean 2.07×)** — *above* both Ax6 variants (1.87×, 1.70×). The
  > comparison quoted here pitted the control's worst seed (1.5×) against Ax6's best (2.2×). The
  > underlying claim "the axiom-injection mechanism was never the bottleneck" is therefore
  > **unsupported** — no mechanism has yet been shown to reliably move Bot.
- **The gain isn't free.** At ω=0.5, Bot's improvement came with Web Brute Force and Web XSS PR-AUC dropping (0.833→0.779, 0.796→0.696), pulling macro down (0.5552→0.5169). At ω=1.0 the tradeoff is milder — Bot still improves while macro is roughly flat. `sat_loss` weights all active axioms uniformly regardless of how many flows each targets, so satisfying one family's constraint pulls slack from the shared decision boundary that the other axioms also depend on.
- **Neither Ax6 variant beats the plain CNN's macro (0.6446).** The neural baseline still wins in aggregate; this is the first symbolic intervention with a measured, targeted effect on the family that was actually stuck, at a real but non-catastrophic cost elsewhere — a genuinely different, more nuanced Phase-2 headline than either "axioms don't help" or "axioms are free."

## 2026-07-27 (targeted Bot axiom — built and validated, training blocked)

- **Designed a first-pass Bot axiom from a median-only glance and got it wrong.** `Bwd Packet Length Mean` looked like a clean separator (benign median 77, Bot median 6), but the full distribution shows Bot's values cluster exactly at the percentile boundary used for the fuzzy ramp — the resulting signal was net anti-correlated with Bot (ROC 0.3995, worse than random). Caught by validating standalone against real labels before spending a training run on it, not by inspection.
- **Replaced with what the full distribution actually supports:** destination-port membership against a small, externally-defined list of well-known service ports (`behavior.WELL_KNOWN_PORTS`) — not data-fitted, not a magnitude ramp (port number isn't ordinal; a magnitude ramp was tried and also failed for the same median-lies reason). Standalone: ROC 0.887, PR-AUC 0.135 on Bot-vs-benign alone (chance 0.034, ~4x lift) — comparable to Mahalanobis.
- **Added `BeaconLike` to `behavior.py`** (vectorized via `np.isin`, not a per-row Python loop), wired into `ltn_paper.py` as **Ax6** (behaviour weight matrix and `sat_loss` now carry 4 columns instead of 3). Fixed `cnn_auxhead_paper.py`'s `BEH` list, which used `BEHAVIOUR_NAMES[:5]` to drop the constant-zero `RepeatedConnections` entry — inserting `BeaconLike` before it in the list would have silently excluded the new behaviour too; now filters by name.
- **Blocked on the same TensorFlow issue** — re-checked before this write-up, still failing on a 5th distinct native DLL. The axiom is built and standalone-validated; its effect on the trained LTN (the actual test of B2's prediction) is not yet measured.

## 2026-07-27 (skyline/oracle — beaconing hypothesis falsified)

- **Ran the skyline/oracle experiment** (`scripts/skyline_oracle.py`, sklearn/xgboost only, unaffected by the TF block): revealed a random 50% of each zero-day family's test flows to XGBoost training (held-out other 50% for eval, no leakage), same hyperparams as `baselines.py`. Bot PR-AUC rose from 0.0314 (never-seen) to **0.9764** (56x chance) with ~1,000 labelled examples. Every family recovers similarly (macro 0.5947 → 0.9899).
- **This falsifies the "Bot's signal is absent from the per-flow representation" claim written into STATUS/CHANGELOG earlier the same day.** That was an untested domain-knowledge hypothesis (Bot = C2 beaconing = a cross-flow phenomenon) presented as a finding without verifying it against the labels. The oracle result shows the information was always in the 68 per-flow features; the near-chance never-seen score is a **zero-day transfer failure of the closed-set classifier**, not an information-theoretic limit.
- **Isolated a Bot-vs-benign-only classifier's feature importances** to find the actual signature: `Bwd Packet Length Mean` 77→6 (near-empty backward payload), `Destination Port` 80→8080, `Init_Win_bytes_forward` 116→8192 — a clean, mundane, single-flow pattern. None of the existing axioms (Ax3 LargePackets∧HighEntropy, Ax4 BurstTraffic, Ax5 ScanProbe) touch it; they're volume/scan-shaped, tuned for DoS/PortScan.
- **Reframes the Phase-2 thesis:** not "symbolic injection is capped by the representation" but "the current axiom set targets the wrong signature for the family that matters." Next step is a targeted axiom test (B2 in STATUS), not host/session-level feature aggregation (C) — deprioritized, no longer well-motivated for Bot specifically (may still help Infiltration/lateral-movement).

## 2026-07-27 (measurement audit — retractions + corrected metrics)

- **Found a float32 softmax saturation defect invalidating 4 of 13 runs.** Scores were `1 - softmax[benign]`; for a confident model `p(benign)` rounds to exactly 1.0, so the score underflows to exactly 0.0 — on `ltn_ctrl_w0`, 99.25% of benign and 51.7% of zero-day flows. The 1%-FPR threshold therefore lands at 0.0 and flags everything (achieved FPR 1.000), producing the bogus "recall=1.0000 for every family" rows and an identical `zd_f1 = 0.1315` across three models (the algebraic predict-all constant at 7% prevalence). Saturated: `ltn_ctrl_w0`, `ltn_repro`, `ltn_v2`, `ltn_anat_w2p0` — i.e. every fair-loop run the control experiment depended on.
- **Found the blended headline metric is a size-weighted mixture** of families whose detectability differs ~30x, so it moves for reasons unrelated to detection quality — and it reorders the model ranking versus a per-family view.
- **Rewrote `metrics.py`:** headline is now per-family PR-AUC + macro-average over adequately powered families (n≥100), with `chance_pr_auc`/`lift` columns; blended demoted to secondary; Heartbleed (n=11), Infiltration (n=36), SQL Injection (n=21) excluded as underpowered instead of reported to 4 dp; added saturation diagnostics (`achieved_fpr`, `largest_tie_frac`) and a `to_logodds` helper.
- **RETRACTED "axioms help at ω=0.5–1.0"** (written earlier the same day). It rested on blended (0.520 > 0.501); on macro it reverses (0.5552 vs 0.5937), and per-family ω=0.5 is worse than the control on both families carrying signal.
- **RETRACTED "XGBoost ≈ CNN (tabular SOTA matches us)"** from Phase 1. On macro the CNN beats XGBoost (0.6446 vs 0.6372) — the tie was an artefact of family sizes. The "pivot the story to explanation/adaptivity" framing was motivated by a tie that isn't there.
- **RETRACTED "unsupervised anomaly is far worse → motivates supervised neuro-symbolic".** IsolationForest is far worse overall (macro 0.063) but scores **0.0571 on Bot — indistinguishable from the CNN's 0.0591**. 884K labelled training flows buy no Bot signal over an unsupervised outlier detector.
- **New central finding: Bot is at chance for every supervised method** (lift 1.0–1.8x); Mahalanobis (0.1467, 4.3x) is the sole exception and is a *distance* method — the open-set-recognition signature. ~~Evidence that the per-flow representation does not contain the Bot signal: Bot is C2 beaconing, whose signature is periodicity *across* flows, destroyed by i.i.d. flow classification. Explains why every symbolic intervention moves the number by only ±0.02, and why Ax3/4/5 (thresholded functions of the same 68 input features) are tautological.~~
  > 🔴 **RETRACTED the same day (marked in place 2026-07-29).** The first sentence stands — Bot *is*
  > at chance for supervised methods, and Mahalanobis *is* the exception. The struck explanation does
  > not: the skyline oracle (`scripts/skyline_oracle.py`) lifted Bot PR-AUC from 0.0314 to **0.9764**
  > with ~1,000 labelled examples, proving the signal **was always present per-flow**. The beaconing/
  > cross-flow story was an untested domain intuition written up as a finding. The correct reading is
  > a **zero-day transfer failure of the closed-set classifier**, not an information-theoretic limit —
  > and consequently Ax3/4/5 are not "tautological", they simply target the wrong signature
  > (volume/scan-shaped, tuned for DoS/PortScan, untouched by Bot's actual pattern).
- Upheld: the ω=2.0 collapse, and the aux head underperforming the plain CNN (0.5744 vs 0.6446, same training method, neither saturated).
- Added `scripts/rescore_logits.py` (recompute scores as `logsumexp(attack_logits) − benign_logit` from saved models) and a missing `model.save` in `cnn_auxhead_paper.py`. **Both blocked**: TensorFlow stopped loading mid-session with `An Application Control policy has blocked this file` across rotating native DLLs; numpy/sklearn/scipy unaffected. Not worked around — machine security control.
- Revised plan: A (fix measurement) → B (skyline/oracle to establish the per-family ceiling) → C (host/session-level aggregation using the IP+timestamp from the dataset upgrade, with a falsifiable prediction that Bot rises above chance).

## 2026-07-27 (Phase 2 — symbolic pillar, fair-loop batch + training-loop speedup)

- **Resolved the training-method confound.** Ran the ω=0 control under the fairness-upgraded custom loop (best-by-val-loss, LR annealing) — it lands at zd PR-AUC 0.501, vs the CNN reference's 0.599. Confirms most of the LTN-vs-CNN gap is the custom loop itself, not the axioms. All LTN numbers must be read relative to 0.501, not 0.599.
- **Failure-anatomy ω-sweep (fixed omega, focal + both axioms):** ω=0.5 → 0.520 PR-AUC, ω=1.0 → 0.513 (both beat the control — axioms genuinely help in this band), ω=2.0 → 0.092 (sharp collapse, SAT overwhelms CE, reproduces the original full-run failure mode). Safe zone ≈ ω∈[0.5, 1.0].
- **Adaptive ratio-mode (`ltn_v2`) undershoots the sweet spot** — nets out at ω_eff≈0.1-equivalent (0.491), close to the control rather than the fixed-sweep optimum. Flagged as a recalibration candidate.
- **`ltn_repro` (CE + base axioms) is the worst fair-loop variant** (0.485, below the control) — isolates plain CE as a poor loss choice for this imbalance, independent of the axiom question.
- **Aux behaviour-prediction head measured** (`scripts/cnn_auxhead_paper.py`, representation-level integration point): 0.497 zd PR-AUC, using the same `model.fit` method as the CNN reference (no loop confound) — still underperforms it, landing in the same band as the SAT variants.
- **Assembled the Phase-2 "three symbolic integration points" table** (loss-level / representation-level / inference-level) per `conference_roadmap.md`. Inference-level (fusion) remains the expected primary performance mechanism — not yet built (Phase 4).
- **Training-loop performance fix:** `ltn_paper.py`'s custom loop ran fully eager (~3,450 raw Python iterations/epoch), starving the CPU's 16 cores behind Python dispatch overhead (~2.6 cores observed). Rewrote the train step under `@tf.function` — required precomputing benign/attack masks as numeric arrays instead of per-batch string comparison (not graph-compatible) — plus explicit `intra_op=16`/`inter_op=2` thread config in both `ltn_paper.py` and `cnn_auxhead_paper.py`. Smoke-tested equivalent, faster per epoch; all Phase-2 results above are from the upgraded loop.
- Full results in `outputs/metadata/runs.jsonl`. Updated STATUS.

## 2026-06-18 (Phase 1 — neural pillar + baselines)

- **Retrained the CNN in-venv on the paper split** (`scripts/cnn_paper.py`) — loadable Keras-2 models, log1p transform, `metrics.py` headline. Early-stopped epoch 25, val-acc 0.997.
- **Fixed a real focal-loss bug** (see KNOWN_ISSUES): Keras passes `y_true` as `(batch,1)`, so `one_hot` broadcast to a `(B,B,n)` garbage tensor → frozen val_loss / random accuracy. Confirmed by controlled race (focal as-is 0.50 vs fixed 0.996 val-acc). Fixed `reshape([-1])` in `cnn_paper.py` + legacy `cnn3.py`. Also fixed callback monitors (`val_sparse_categorical_accuracy`) that had silently disabled early-stopping/checkpointing.
- **Classical baselines** (`scripts/baselines.py`): XGBoost, RandomForest, IsolationForest. **Free novelty channels** (`scripts/novelty.py`): MSP + Mahalanobis.
- **Phase-1 zero-day-only PR-AUC:** xgboost 0.604 · cnn 0.599 · msp 0.587 · mahalanobis 0.583 · rf 0.564 · isolation_forest 0.153. Honest: XGBoost ≈ CNN (pivot to explanation/adaptivity/response); unsupervised anomaly far worse (motivates supervised NSAI). Per-family: CNN catches Web attacks (~0.9) but misses Bot (0.002)/Infiltration.
- 6 fusion channels saved to `outputs/predictions/`. Metrics logged to `runs.jsonl`. xgboost pinned.

## 2026-06-18 (dataset upgrade → full variant with IP/timestamp)

- **Switched from the ML-CVE variant to the full `GeneratedLabelledFlows`** (added `data/raw_csv_full/`, gitignored). Rewrote `scripts/preprocess.py` to ingest the 85-col CSVs, guard the `Infinity`-string quirk (`to_numeric coerce`), and extract a **meta side-table** (`meta_train/test.csv` — Flow ID, Source/Dest IP+Port, Protocol, Timestamp) aligned row-for-row through cleaning.
- **Verified feature parity:** identical 68 features, same 10 constant columns, exact same row counts (train 1,666,532 / test 1,161,344) as ML-CVE → behaviour indices unchanged (Destination Port at 0, etc.).
- **`preprocess_paper.py` now splits on indices** so meta follows each row into paper train/val/test (`data/processed/paper/meta_{train,val,test}.csv`), all aligned.
- **Result:** IP/timestamp available → `RepeatedConnections` + source-level response replay **unblocked**. PortScan test set = 15,881 flows from **1 source IP → 998 distinct dest ports** (canonical scan signature). `config.yaml`: `variant: GeneratedLabelledFlows`, `has_ip_timestamp: true`. Done at the zero-cost window (before any training on the paper split).

## 2026-06-18 (Phase 0 — protocol reset)

- **Built the paper-aligned split** (`scripts/preprocess_paper.py` → `data/processed/paper/`): pools all 5 days, 9 known classes (BENIGN + 8 attacks incl. PortScan/DDoS) stratified 80/10/10 (train 883,796 / val 110,475 / test 114,658), benign under-sampled 1:1 (balanced 50/50), 6 rare classes (Bot, Web×3, Infiltration, Heartbleed) appended to test only. Leakage asserted (no zero-day in train/val). Temporal split kept untouched as secondary hard-mode.
- **Config + scaffolding:** `config.yaml` (all protocol params) + `scripts/config.py`, `scripts/features.py` (shared transform), `scripts/tracking.py` (JSONL run logger). pyyaml pinned.
- **log1p A/B (Phase 0.3):** signed-log1p `sign(x)·log1p(|x|)` beat raw on the paper split (PR-AUC 0.980 vs 0.965) → adopted in config.
- **Data constraint found:** the CSVs are the **MachineLearningCVE** variant — no Flow ID/IP/Timestamp columns → IP-based `RepeatedConnections` and response-replay are limited (documented in config `has_ip_timestamp: false`).
- **Nuance recorded:** overall binary is easy (~0.97) under the paper split since PortScan/DDoS are known; the challenge metric is the **zero-day-only binary** (~4,183 test flows), matching the paper's "6 unknown" metric.

## 2026-06-18 (strategic pivot → conference roadmap)

- **LTN full run completed and underperformed** — PR-AUC 0.4529 vs CNN baseline 0.6689 (−0.22); early-stopped ~epoch 10, val accuracy declined after epoch 2. Root cause: focal CE collapsed to ~0.0005, SAT term dominated ~40:1. Per-family: PortScan 0.36→0.16, DDoS 0.67→0.64.
- **Fusion investigation (post-hoc, no retraining):** leaky logistic fusion (fit on zero-day-labelled test half) reached 0.78 (+0.11) — but the honest **label-free** parameter-free fusion was −0.16. Conclusion: behaviours carry real signal, but supervised transfer to zero-day is the wall. Also found `model_multiclass_best.keras` is **Keras 3** (won't load in our Keras-2.15 venv) → in-venv retrain required.
- **Read the base paper** (`basepaper.pdf`, Bizzarri et al., IEEE). Findings: it uses payload bytes (1500) not flow features; stratified 80/10/10 with **known attacks in test**; zero-day = rare classes only (keeps PortScan/DDoS in training); **balanced data + plain CE + ω=1** (why their SAT stays gentle and ours dominated). Their result: zero-day acc 48→60%. Our protocol was a much harder, misaligned exam.
- **Decided a strategic pivot** to a top-tier-publication plan: protocol reset (paper-aligned split) → retrain in-venv → reproduce paper → fix + extend → multi-pillar fusion → cross-dataset → response engine. Captured in **[conference_roadmap.md](target/conference_roadmap.md)** (plan v1.2 + Tier-S/A/B agenda). Headline thesis: *"when and why neuro-symbolic training fails under imbalance, and the inference-time fusion fix."* Response/IPS engine added as Shaunak's solo final phase. Updated STATUS, enhancements.

## 2026-06-18 (LTN re-grounded)

- **Re-grounded the LTN axioms on behaviours** (`scripts/ltn.py`), fixing the core flaw (label tautologies). Kept Ax1/Ax2 as supervised anchors; replaced Ax3 (was DoS-label) with **LargePackets∧HighEntropy → ¬benign** and Ax4 (was Patator-label) with **BurstTraffic → ¬benign**, weighted per-flow by fuzzy behaviour confidences from `behavior.py` (computed on raw features pre-scaling, shuffled in lockstep with batches). ScanProbe/HighVolume deliberately excluded from training axioms (ScanProbe benign-heavy in training → reserved for KG stage).
- **Added smoke-test hook** (`LTN_SUBSET` / `LTN_EPOCHS` env vars). Smoke test (50k×2) passed end-to-end: no NaNs, behaviour axioms compute & satisfy (Ax3≈0.90, Ax4≈0.78).
- **Launched first full training run** (background, CPU, headless `MPLBACKEND=Agg`, logging to `outputs/ltn_run.log`). Results pending. Baseline to beat: CNN PR-AUC 0.6689.
- Updated [ltn_current.md](implementation/ltn_current.md), STATUS.

## 2026-06-18 (session close)

- **Compute decision recorded:** training stays on **CPU** (Ryzen 9 9950X3D, 62 GB RAM — LTN run estimated ~30–60 min). GPU (RTX 5080) **deferred**: Blackwell needs WSL2 + CUDA 12.8 + newer TF + likely Keras 3 migration — poor ROI now, revisit if training volume grows. Logged in STATUS Open Decisions.
- **STATUS.md prepped for resume:** added a "▶ RESUME HERE" block (next action = re-ground LTN axioms on behaviours) and a "Remaining Work" queue (LTN → RepeatedConnections → KG → Fusion → Explainability → Ablation). No code changed this turn.

## 2026-06-18 (behaviour abstraction rebuilt)

- **Rebuilt `scripts/behavior.py`** from broken/dead to working+validated. Verified the real 68-column feature order via `check.py` (old indices were badly wrong — e.g. old `RATE_FEATURES=[5,6,7]` actually pointed at packet-length fields, old flags pointed at IAT). New module: vectorised, fuzzy `[0,1]` outputs, data-driven percentile thresholds saved to `outputs/metadata/behaviour_thresholds.npy`, built-in validation harness.
- **Two bugs caught by validation and fixed:** (1) flag-count `ProtocolAnomalies` fired 45% on benign / 0% on attacks (matched benign UDP), so the flag approach was **dropped** — flag-count columns are ~0 even for real scans in CIC-IDS2017; (2) replaced it with **`ScanProbe`** (short duration × tiny payload), which scores **0.955 on the zero-day PortScan** vs 0.244 benign.
- **Behaviours:** BurstTraffic, HighVolume, LargePackets, HighEntropy (approx), ScanProbe, RepeatedConnections (unavailable → 0). LargePackets/HighEntropy ~7–8× attack-discriminative; PortScan+DDoS (largest zero-day families) strongly covered. Web Attacks/Bot remain weakly covered (documented limitation).
- Updated [behaviour_abstraction_current.md](implementation/behaviour_abstraction_current.md), STATUS, KNOWN_ISSUES.
- **Next:** re-ground LTN axioms on these behaviours.

## 2026-06-18 (enhancements captured)

- **Captured an enhancement backlog** at [target/enhancements.md](target/enhancements.md) — anomaly-detection baseline, multi-seed variance, cross-dataset eval, active-learning loop, calibration/abstain, latency benchmark, config/orchestration/tests, dataset-label caveat. **Backlog only — nothing scheduled or started.**

## 2026-06-18 (reorg)

- **Repository reorganised to professional layout.** Moved all generated artifacts out of the repo root into `data/processed/`, `models/`, and `outputs/{arrays,embeddings,predictions,metadata,figures}/`. Added [`scripts/paths.py`](../scripts/paths.py) as the single source of path truth and rewired every script (`preprocess`, `cnn3`, `eval`, `ltn`, `behavior`, `check`, `visual`) to import it — no more hardcoded root paths. Verified: all scripts compile; all 28 existing artifacts present at new locations (eval can run without regeneration).
- **Artifact cleanup.** Deleted stale `model_focal.keras` + `behaviour_thresholds.npy`. LTN outputs never existed (script not yet run), so nothing to clear there. Kept valid preprocessing/CNN/eval artifacts (expensive to regenerate).
- **Archived** the original `PROJECT_DOCUMENTATION.md` → `docs/archive/` (superseded by the structured docs).
- **Rewrote `.gitignore`** to directory-based ignores matching the new layout (`outputs/figures/` intentionally tracked).
- Git check: only `.gitignore` + an old `preprocess_friday.py` were ever tracked; no large binaries committed.

## 2026-06-18 (later)

- **Dead code removed.** Deleted `utils/config.py` + `utils/` dir (stale, from abandoned payload pipeline, imported by nothing). Removed the unused `y_train_b`/`y_val_b` binary-split block in `cnn3.py`. **Kept** `behavior.py` and the `fuzzy_*` operators in `ltn.py` — both feed the upcoming behaviour/LTN rework. `model_focal.keras` (stale binary artifact) left in place but gitignored. Updated all doc references.
- **Environment set up.** Installed Python 3.11.9 (winget, user scope) and created `.venv` at repo root. Added pinned `requirements.txt` (Python 3.11 / TF 2.15.1 / Keras 2 / numpy 1.26.4 + KG libs networkx, python-louvain + explainability lib shap). Smoke test passed: all imports work, `tensorflow.keras` (Keras 2) OK, CPU mode (no GPU).
- **Rewrote `.gitignore`** to match the real artifact layout (root-level `*.npy`/`*.keras`/`*.pkl` + large generated CSVs + `.venv/`); the old one referenced the abandoned payload pipeline's paths.
- **Found `utils/config.py` is stale orphaned code** from the abandoned raw-PCAP/payload pipeline (PAYLOAD_LEN=1500, 3 classes). Not imported anywhere. Corrected `scripts_reference.md`; logged in KNOWN_ISSUES.

## 2026-06-18

- **Documentation overhaul.** Created `docs/` (implemented-state docs), `docs/target/` (target-architecture specs + gap analysis), `docs/implementation/` (line-by-line source audits), and dynamic tracking files (`STATUS.md`, `CHANGELOG.md`, `KNOWN_ISSUES.md`). Added root `CLAUDE.md` for session onboarding.
- **Source audit completed** for `cnn3.py`, `behavior.py`, `ltn.py`, `preprocess.py`, `eval.py`:
  - CNN verified ✅ correct (minor: double class-weighting).
  - `behavior.py` found ❌ orphaned/dead (never imported; thresholds never generated; feature indices misaligned). See [audit](implementation/behaviour_abstraction_current.md).
  - `ltn.py` found ⚠️ conceptually wrong (axioms are label tautologies, fuzzy operators unused, not wired to behaviour). See [audit](implementation/ltn_current.md).
- **Correction:** earlier draft docs wrongly listed **Bot** as a training class (index 8) with 9 train classes. Source confirms Bot is a **zero-day/test** class; training has ~8 classes. Fixed in `dataset.md`, `models.md`, `artifacts.md`.
- **Decisions recorded:** KG → NetworkX; Fusion → fixed-weights then logistic; input → flow-feature CSVs. See [STATUS.md](STATUS.md#open-decisions).

<!-- TEMPLATE for new entries:
## YYYY-MM-DD
- **<area>.** <what changed and why>. <link to detail>.
-->
