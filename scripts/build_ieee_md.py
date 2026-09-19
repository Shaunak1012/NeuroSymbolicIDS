"""
build_ieee_md.py — derive the IEEE conference versions of the paper from the verified text.

WHY THIS EXISTS (2026-09-19)
----------------------------
The paper exists as a body (paper_body.md) and a supplementary (paper_supplementary.md),
both checked number-by-number by verify_draft.py. An IEEE two-column conference paper
has no room for the supplementary and no appendices to point at, so it needs its own
text. Writing that text by hand would put numbers into the paper that no check has
seen. This script assembles it instead: body sections are taken as they are, pointers
into the supplementary are rewritten, sections are renumbered, and the extra sections
(base-paper re-examination, robustness, reproducibility) are built from sentences that
already appear in the verified supplementary. verify_draft.py's subset mode then
confirms that every number in the result appears in the verified text.

  full   docs/target/ieee/paper_ieee_full.md   the 9-page version (CNSM-style budget)

The 6-page version is cut from the full one by hand-picked section drops and lives in
paper_ieee_short.md, built by the same script with --short.

Run:  python scripts/build_ieee_md.py            (full)
      python scripts/build_ieee_md.py --short    (6-page cut)
Then: python scripts/md_to_latex.py --ieee docs/target/ieee/paper_ieee_full.md --compile
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                        # noqa: E402

BODY = os.path.join(paths.ROOT, "docs", "target", "paper_body.md")
OUT_DIR = os.path.join(paths.ROOT, "docs", "target", "ieee")
LF = chr(10)
SECT = chr(0xA7)


def sections(md):
    """Split on '## ' headings -> ordered list of (heading, text)."""
    parts = re.split(r"(?m)^## ", md)
    out = []
    for p in parts[1:]:
        head, _, text = p.partition(LF)
        out.append((head.strip(), text.strip().strip("-").strip()))
    return out


def sub1(text, old, new):
    assert text.count(old) == 1, (old[:60], text.count(old))
    return text.replace(old, new)


def renumber(text, mapping):
    """Section-sign references: body numbering -> IEEE numbering."""
    def f(m):
        a = int(m.group(1))
        return SECT + str(mapping.get(a, a))
    return re.sub(SECT + r"(\d+)", f, text)


ABSTRACT = (
    "Neuro-symbolic intrusion detectors that report gains from injected knowledge tend to share a "
    "property that is rarely stated: the knowledge they add is information the neural network could "
    "not compute from its input. Our own system, a 1D CNN with Logic Tensor Network axioms over "
    "CIC-IDS2017 flow features, did not have this property, and its axioms were worse than the same "
    "trainer run without them in all 17 CNN training runs we paired them with. We argue that symbolic "
    "knowledge can help only to the extent that it lies outside the model's learned feature basis, and "
    "test how far the same condition explains a second failure: every Bot flow is classified as benign "
    "in all 17 runs, although an oracle reaches a PR-AUC of 0.9988 from the same features. We then show "
    "that the benchmark cannot host the experiment published gains rely on, because host-role knowledge "
    "derived from the capture is predictable from the flow features (AUC 0.990-0.994). Re-examining the "
    "neuro-symbolic system our work started from, we find that its reported gain does not appear against "
    "a matched control (+0.55 against +12.13 percentage points). All results are paired on seed under "
    "deterministic training, and the pipeline reproduces from the raw data.")

INDEX_TERMS = ("Intrusion detection, neuro-symbolic learning, zero-day attacks, CIC-IDS2017, "
               "Logic Tensor Networks, reproducibility")

BASE_PAPER = LF.join([
    "## 7 Re-examining the base paper",
    "",
    "Our work started from Bizzarri et al. [8], who trained a Logic Tensor Network on CIC-IDS2017 with a "
    "combined cross-entropy and satisfiability loss and reported better accuracy on unknown attacks. We "
    "re-examined that result with controls it did not have.",
    "",
    "**The gain does not appear against a matched control.** We trained their loss (cross-entropy plus the "
    "satisfiability term at ω = 1) and a matched control with the term switched off (ω = 0), identical "
    "in every other respect, with three deterministic seeds each. The satisfiability term changes "
    "zero-day accuracy by +0.55 percentage points (+0.60, −0.84 and +1.89 on the three seeds), against "
    "the +12.13 they report, and changes macro zero-day PR-AUC by −0.0090, better on 1 seed of 3. "
    "Neither change is consistent in direction.",
    "",
    "**The reported gain is a change of operating point.** Across the five evaluation views, the hybrid "
    "LTN model improves on the 1D CNN by +0.09, +0.15, +0.07 and +2.15 percentage points on the four views "
    "that contain benign traffic, and by +12.13 points on the one view that does not. On the nine known "
    "classes the hybrid model makes 452 false positives against the CNN's 380. The satisfiability term "
    "penalises calling an attack benign, so it moves the decision boundary towards the attack class. Their "
    "zero-day view contains only attack rows, so precision is always 1, accuracy equals recall, and "
    "F1 = 2A/(1+A); a model that flags every flow as an attack would score 100 % on both.",
    "",
    "**One connection, and a coincidental agreement.** Heartbleed is 42.2 % of their zero-day set, and "
    "all 11 Heartbleed flows in CIC-IDS2017 share one 5-tuple and fall within 20 minutes, so the largest "
    "component of the reported zero-day score is one network event. On their zero-day view our CNN "
    "scores 47.85 % against their 48.34 %. They delete payload-less records and we do not; on the "
    "corrected-label release with the attempted, payload-less flows removed, which is the closest "
    "analogue of their filtering, our CNN's view-5 accuracy is 0.69 % (0.82, 0.82 and 0.41 % over three "
    "seeds). Our 47.85 % came from failed connection attempts labelled as attacks.",
    "",
    "**Their class balancing.** Under their rule, every known attack class cut to the size of the "
    "smallest (4,399 training flows each), our CNN's macro zero-day PR-AUC falls from 0.6299 to 0.4699; a "
    "training set of the same size with the natural class mix scores 0.2118, below the balanced one on "
    "every seed. With the natural mix at this size the two slow-rate DoS classes keep only 350 and 369 "
    "training flows and the web attacks are classified as benign instead of being absorbed into them. "
    "Balancing does not account for their zero-day accuracy either: on view 5 our balanced CNN scores "
    "45.10 %, against 47.56 % on our own split.",
])

REPRO = LF.join([
    "## 10 Reproducibility",
    "",
    'Training is deterministic: two full 50-epoch runs with the same seed produce byte-identical output. We ran the whole pipeline from the raw CSVs into an empty directory. It completed 20 of the 26 stages in 6.5 hours, and 72 files are byte-identical to the artifacts behind this paper, including the split, all three CNN seeds with their embeddings, all three autoencoders and every knowledge-graph seed; four differ only at float level and nothing differs otherwise. The six incomplete stages need records from experiments outside the pipeline. Every number in the paper is checked mechanically against the per-run records. Code, configuration and records are released; the dataset and trained weights are not.',
])


def build(short=False):
    body = io.open(BODY, encoding="utf-8").read()
    title = re.search(r"(?m)^# (.+)$", body).group(1).strip()
    # body section -> IEEE section number. Applied to the body text BEFORE the edits below,
    # which write IEEE numbers directly (renumbering afterwards shifted them a second time).
    mapping = {7: 8, 8: 9, 9: 11}
    secs = dict((h, renumber(t, mapping)) for h, t in sections(body))

    intro = secs["1 Introduction"]
    intro = sub1(intro, "The paper makes three contributions around it.",
                 "The paper makes four contributions around it.")
    intro = sub1(intro, "   knowledge artefact cannot host the experiment on which published neuro-symbolic gains depend.",
                 "   knowledge artefact cannot host the experiment on which published neuro-symbolic gains depend." + LF +
                 "4. **A controlled re-examination of the base system (" + SECT + "7).** The satisfiability gain of the "
                 "neuro-symbolic system our work started from does not appear against a matched control, and our "
                 "apparent agreement with its CNN does not survive population matching.")

    setting = secs["2 Setting and measurement"]
    setting = sub1(setting, "(Appendix A)", "(" + SECT + "11)")
    setting = sub1(setting, "a paired bootstrap had reported as significant (p = 0.001; supplementary " + SECT + "E).",
                   "a paired bootstrap had reported as significant (p = 0.001).")

    sym = secs["3 A symbolic pillar that could not help"]
    sym = sub1(sym, "that fusion does not hold across CNN runs (supplementary " + SECT + "D),",
               "that fusion does not hold across CNN runs (" + SECT + "8),")

    mech = secs["4 One principle, two consequences"]
    mech = sub1(mech, " (Appendix C).", ".")

    dur = secs["5 Durability: five attempts to break it"]
    evalb = secs["6 Evaluability: the benchmark cannot supply exogenous knowledge"]

    mag = secs["7 What limits the magnitudes"]
    mag = sub1(mag, " Supplementary " + SECT + "B gives the" + LF + "full analysis.", "")
    mag = sub1(mag, "it (supplementary " + SECT + "D). With it withdrawn,", "it. With it withdrawn,")

    rel = secs["8 Related work"]
    rel = re.sub(r"(?s)Our work started from that paper,.*?like \(Appendix B\)\. ",
                 "Section " + SECT + "7 re-examines that result under a matched control. ", rel)
    rel = sub1(rel, "Supplementary " + SECT + "E checks this work against all ten; two of them, lab-only" + LF +
               "evaluation and the threat model, are not addressed here.",
               "Of the ten, lab-only evaluation is not addressed here, and the threat model only in part" + LF +
               "(" + SECT + "11).")

    lim = secs["9 Limitations and conclusion"]
    lim = sub1(lim, " (Appendix F)", "")
    lim = sub1(lim, " (Appendix A).", ".")
    lim = sub1(lim, "(Appendix H).", "(" + SECT + "10).")

    refs = secs["References"]

    parts = ["# " + title, "", "## Abstract", "", ABSTRACT, "", "## Index Terms", "", INDEX_TERMS, ""]

    def add(num, name, text):
        parts.extend(["## %d %s" % (num, name), "", text, ""])

    add(1, "Introduction", intro)
    add(2, "Setting and measurement", setting)
    add(3, "A symbolic pillar that could not help", sym)
    add(4, "One principle, two consequences", mech)
    add(5, "Durability: five attempts to break it", dur)
    add(6, "Evaluability: the benchmark cannot supply exogenous knowledge", evalb)
    parts.extend([BASE_PAPER, ""])
    add(8, "What limits the magnitudes", mag)
    add(9, "Related work", rel)
    parts.extend([REPRO, ""])
    add(11, "Limitations and conclusion", lim)
    parts.extend(["## References", "", refs, ""])
    md = LF.join(parts)
    if short:
        md = shorten(md)
    os.makedirs(OUT_DIR, exist_ok=True)
    name = "paper_ieee_short.md" if short else "paper_ieee_full.md"
    p = os.path.join(OUT_DIR, name)
    io.open(p, "w", encoding="utf-8", newline="\n").write(md)
    print("wrote %s (%d words)" % (p, len(re.findall(r"\S+", md))))


# The 6-page cut (IEEE ICC) removes whole paragraphs of the full version and rewrites none, so
# every sentence that survives is one the subset check has already verified. Each entry is the
# opening of a paragraph; a missing one stops the build rather than silently cutting less.
SHORT_DROP = [
    "**Their class balancing.**",
    "**Metric resolution.**",
    "The corrected-label experiment is the hardest test",
    "Augmentation failed for a different reason.",
    "**One connection, and a coincidental agreement.**",
    "**What generalises.**",
    "## 10 Reproducibility",
    "Training is deterministic: two full 50-epoch runs",
    "**Open-set recognition and OOD scoring.**",
]
# Edits inside kept sentences: each only deletes words, or follows the section renumbering
# (section 10 is dropped above, so Limitations and conclusion becomes section 10).
SHORT_EDIT = [
    (", and our apparent agreement with its CNN does not survive population matching.", "."),
    (" (" + SECT + "10).*", ".*"),
    ("## 11 Limitations and conclusion", "## 10 Limitations and conclusion"),
    ("(" + SECT + "11)", "(" + SECT + "10)"),
]


def shorten(md):
    paras = md.split(LF + LF)
    keep = []
    for start in SHORT_DROP:
        if sum(p.startswith(start) for p in paras) != 1:
            raise SystemExit("--short: paragraph not found exactly once: %r" % start)
    for p in paras:
        if not any(p.startswith(start) for start in SHORT_DROP):
            keep.append(p)
    md = (LF + LF).join(keep)
    for old, new in SHORT_EDIT:
        if old not in md:
            raise SystemExit("--short: edit target not found: %r" % old)
        md = md.replace(old, new)
    return md


if __name__ == "__main__":
    build(short="--short" in sys.argv)
