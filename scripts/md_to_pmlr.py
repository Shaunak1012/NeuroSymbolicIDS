"""
md_to_pmlr.py — generate the NeSy PMLR LaTeX submission FROM the markdown.

WHY GENERATE RATHER THAN HAND-CONVERT
--------------------------------------
The markdown is what `verify_draft.py` checks: every quantitative claim in
`nesy_body.md` and `nesy_supplementary.md` is verified against the metadata that
produced it, with zero mismatches and zero stale claims. Hand-converting ~14,000
words into LaTeX would break that chain -- a number retyped in a .tex file is a
number no check has seen. Generating the LaTeX mechanically keeps it traceable,
makes the conversion re-runnable when the paper changes during review, and puts
LaTeX escaping (the part most likely to go wrong by hand) in one tested place.

WHAT IT PRODUCES
----------------
docs/target/nesy_latex/
  main.tex          body, then bibliography, then the supplementary as \\appendix
  refs.bib          the 17 references, transcribed from the VERIFIED list in
                    paper_draft.md (Crossref / arXiv / publisher, 2026-09-09/15)
  nesy2026.cls      the official NeSy 2026 class (anon option for OpenReview)
  figures/*.png     the two submission figures, copied so the folder is
                    self-contained for upload

NeSy's full-paper limit is 10 pages EXCLUDING references and supplementary
material, so the appendix after the bibliography does not count.

⚠️ THIS SCRIPT CANNOT COMPILE, AND DOES NOT PRETEND TO. No TeX distribution is
installed. `--lint` runs a structural check instead -- brace and environment
balance, every citation key in the .bib, every \\ref label defined, every figure
file present, no unmapped non-ASCII and no leftover markdown -- which catches
most errors that would stop pdflatex. It cannot measure the page count; only a
real compile can, and that is the check that matters for the 10-page limit.

Run:  python scripts/md_to_pmlr.py            (generate + lint)
"""
import io
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                          # noqa: E402

SRC_BODY = os.path.join(paths.ROOT, "docs", "target", "nesy_body.md")
SRC_SUPP = os.path.join(paths.ROOT, "docs", "target", "nesy_supplementary.md")
OUT = os.path.join(paths.ROOT, "docs", "target", "nesy_latex")
TEMPLATE_CLS = os.environ.get("NESY_CLS", "")

SHORT_TITLE = "Knowledge the Network Already Has"

# reference number -> bib key; numbering is shared by body and supplementary
CITE = {1: "sharafaldin2018", 2: "engelen2021", 3: "lanvin2023",
        4: "goldschmidt2025", 5: "sommer2010", 6: "arp2022",
        7: "badreddine2022", 8: "bizzarri2024", 9: "bizzarri2025survey",
        10: "cruz2017", 11: "hendrycks2017", 12: "liang2018", 13: "liu2020",
        14: "grov2024", 15: "zhou2024", 16: "kalutharage2025", 17: "hakim2025"}

FIGURES = {"nesy_fig1_thesis": "fig:thesis", "nesy_fig2_mechanism": "fig:mechanism"}

# non-ASCII that pdflatex text mode cannot typeset directly
UNICODE = [
    ("\u26a0\ufe0f ", ""), ("\u26a0\ufe0f", ""), ("\u26a0 ", ""), ("\u26a0", ""),
    ("\ufe0f", ""),
    ("\u00a7", r"\S{}"), ("\u00d7", r"$\times$"), ("\u00f7", r"$\div$"),
    ("\u03c1", r"$\rho$"), ("\u03c3", r"$\sigma$"), ("\u0394", r"$\Delta$"),
    ("\u00b5", r"$\mu$"), ("\u00b1", r"$\pm$"), ("\u00b7", r"$\cdot$"),
    ("\u2013", "--"), ("\u2014", "---"), ("\u2192", r"$\rightarrow$"),
    ("\u21d2", r"$\Rightarrow$"), ("\u2212", r"$-$"), ("\u2264", r"$\leq$"),
    ("\u2265", r"$\geq$"), ("\u2248", r"$\approx$"), ("\u2261", r"$\equiv$"),
    ("\u221a", r"$\surd$"), ("\u2153", r"$\frac{1}{3}$"),
    ("\u2154", r"$\frac{2}{3}$"), ("\u201c", "``"), ("\u201d", "''"),
    ("\u2018", "`"), ("\u2019", "'"), ("\u00a0", "~"), ("\u2009", r"\,"),
    ("\u202f", r"\,"), ("\u00c9", r"\'E"), ("\u00e9", r"\'e"),
    ("\u00e1", r"\'a"), ("\u00f8", r"{\o}"), ("\u2713", r"\checkmark{}"),
    ("\u2717", r"$\times$"),
]
SUPERSCRIPT = {"\u2070": "0", "\u00b9": "1", "\u00b2": "2", "\u00b3": "3",
               "\u2074": "4", "\u2075": "5", "\u2076": "6", "\u2077": "7",
               "\u2078": "8", "\u2079": "9"}


# ---------------------------------------------------------------------------
# inline conversion
# ---------------------------------------------------------------------------
def _escape_text(t):
    """Escape LaTeX specials in plain prose."""
    t = t.replace("\\", r"\textbackslash{}")
    for a, b in (("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                 ("_", r"\_"), ("{", r"\{"), ("}", r"\}")):
        t = t.replace(a, b)
    t = t.replace("~", r"$\sim$").replace("^", r"\^{}")
    t = t.replace("<", r"$<$").replace(">", r"$>$").replace("|", r"$|$")
    return t


def _unicode(t):
    for a, b in UNICODE:
        t = t.replace(a, b)
    return t


def _cite_keys(nums):
    return ",".join(CITE[n] for n in nums)


def _expand_range(a, b):
    return list(range(int(a), int(b) + 1))


def inline(text, in_supp=False):
    """Markdown inline -> LaTeX, with placeholders so generated commands are never re-escaped."""
    store = []

    def hold(latex):
        store.append(latex)
        return "\x00%d\x00" % (len(store) - 1)

    # code spans (held before the unicode pass, so map their contents here)
    text = re.sub(r"`([^`]+)`",
                  lambda m: hold(r"\texttt{%s}" % _unicode(_escape_text(m.group(1)))), text)

    # citations. "Surname et al. [n]" / "A and B [n]" -> \citet (natbib renders the names)
    rng = r"\[(\d+)\]\s*[\u2013-]\s*\[(\d+)\]"
    one_rng = r"\[(\d+)\s*[\u2013-]\s*(\d+)\]"
    author = r"([A-Z][\w'\u2019-]+(?: and [A-Z][\w'\u2019-]+| et al\.))\s+"
    text = re.sub(author + rng, lambda m: hold(r"\citet{%s}" % _cite_keys(
        _expand_range(m.group(2), m.group(3)))), text)
    text = re.sub(author + r"\[(\d+)\]", lambda m: hold(
        r"\citet{%s}" % CITE[int(m.group(2))]), text)
    text = re.sub(rng, lambda m: hold(r"\citep{%s}" % _cite_keys(
        _expand_range(m.group(1), m.group(2)))), text)
    text = re.sub(one_rng, lambda m: hold(r"\citep{%s}" % _cite_keys(
        _expand_range(m.group(1), m.group(2)))), text)
    text = re.sub(r"\[(\d+)\]", lambda m: hold(
        r"\citep{%s}" % CITE[int(m.group(1))]), text)

    # cross-references
    text = re.sub(r"[Ss]upplementary \u00a7([A-H])\b",
                  lambda m: hold(r"Appendix~\ref{apd:%s}" % m.group(1)), text)
    text = re.sub(r"\u00a7(\d+) of the main paper",
                  lambda m: hold(r"Section~\ref{sec:%s}" % m.group(1)), text)
    text = re.sub(r"\bAppendix ([A-H])\b",
                  lambda m: hold(r"Appendix~\ref{apd:%s}" % m.group(1)), text)
    text = re.sub(r"\u00a7(\d+)\s*[\u2013-]\s*\u00a7(\d+)", lambda m: hold(
        r"Sections~\ref{sec:%s}--\ref{sec:%s}" % (m.group(1), m.group(2))), text)
    text = re.sub(r"\u00a7(\d+)", lambda m: hold(r"Section~\ref{sec:%s}" % m.group(1)), text)
    text = re.sub(r"\bFigure ([12])\b", lambda m: hold(
        r"Figure~\ref{%s}" % ("fig:thesis" if m.group(1) == "1" else "fig:mechanism")), text)

    # unicode superscript runs -> one math superscript (2^20, not 2^2^0)
    text = re.sub("[" + "".join(SUPERSCRIPT) + "]+", lambda m: hold(
        "$^{%s}$" % "".join(SUPERSCRIPT[c] for c in m.group(0))), text)

    text = _escape_text(text)

    text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"(?<![\\\w])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\\emph{\1}", text)

    text = _unicode(text)
    # straight double quotes typeset as two closing quotes in pdflatex
    text = re.sub(r'"([^"\x00]+)"', r"``\1''", text)
    text = re.sub("\x00(\\d+)\x00", lambda m: store[int(m.group(1))], text)
    # a placeholder may itself contain placeholders (e.g. nothing today, but be safe)
    text = re.sub("\x00(\\d+)\x00", lambda m: store[int(m.group(1))], text)
    return text


# ---------------------------------------------------------------------------
# block conversion
# ---------------------------------------------------------------------------
def strip_build_notes(md):
    return re.sub(r"(?ms)^> \*\*Build note.*?(?=^[^>]|\Z)", "", md)


def table_to_latex(rows, in_supp):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    header, sep, body = cells[0], cells[1], cells[2:]
    ncol = len(header)
    specs, has_x = [], False
    for j in range(ncol):
        s = sep[j] if j < len(sep) else ""
        longest = max(len(r[j]) if j < len(r) else 0 for r in [header] + body)
        if longest > 28:
            specs.append(r">{\raggedright\arraybackslash}X")
            has_x = True
        elif s.endswith(":") and not s.startswith(":"):
            specs.append("r")
        elif s.startswith(":") and s.endswith(":"):
            specs.append("c")
        else:
            specs.append("l")
    env = "tabularx" if has_x else "tabular"
    width = "{\\linewidth}" if has_x else ""
    out = ["\\begin{center}\\small",
           "\\begin{%s}%s{%s}" % (env, width, "".join(specs)), "\\toprule"]
    out.append(" & ".join("\\textbf{%s}" % inline(h, in_supp) if h else "" for h in header)
               + " \\\\")
    out.append("\\midrule")
    for r in body:
        r = (r + [""] * ncol)[:ncol]
        out.append(" & ".join(inline(c, in_supp) for c in r) + " \\\\")
    out += ["\\bottomrule", "\\end{%s}" % env, "\\end{center}"]
    return "\n".join(out)


def blocks_to_latex(md, in_supp=False):
    lines = md.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()
        if not s or s == "---":
            i += 1
            continue

        # figure: image line, then its "**Figure N.**" caption paragraph
        m = re.match(r"!\[[^\]]*\]\(([^)]+)\)", s)
        if m:
            stem = os.path.splitext(os.path.basename(m.group(1)))[0]
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            cap = []
            while j < n and lines[j].strip():
                cap.append(lines[j].strip())
                j += 1
            caption = re.sub(r"^\*\*Figure \d+\.\*\*\s*", "", " ".join(cap))
            out.append("\\begin{figure}[htbp]\n\\floatconts\n  {%s}\n"
                       "  {\\caption{%s}}\n"
                       "  {\\includegraphics[width=\\linewidth]{figures/%s}}\n"
                       "\\end{figure}" % (FIGURES[stem], inline(caption, in_supp), stem))
            i = j
            continue

        # headings
        hm = re.match(r"^(#{2,4})\s+(.*)$", s)
        if hm:
            level, title = len(hm.group(1)), hm.group(2).strip()
            am = re.match(r"Appendix ([A-H])\s*\u2014\s*(.*)$", title)
            nm = re.match(r"(\d+)\s+(.*)$", title)
            if level == 2 and am:
                out.append("\\section{%s}\\label{apd:%s}"
                           % (inline(am.group(2), in_supp), am.group(1)))
            elif level == 2 and nm:
                out.append("\\section{%s}\\label{sec:%s}"
                           % (inline(nm.group(2), in_supp), nm.group(1)))
            elif level == 2:
                out.append("\\section*{%s}" % inline(title, in_supp))
            elif level == 3:
                out.append("\\subsection{%s}" % inline(title, in_supp))
            else:
                out.append("\\subsubsection{%s}" % inline(title, in_supp))
            i += 1
            continue

        # table
        if s.startswith("|") and i + 1 < n and re.match(r"^\|[ :|-]+\|\s*$", lines[i + 1].strip()):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out.append(table_to_latex(rows, in_supp))
            continue

        # blockquote (a quotation, not a build note -- those are stripped earlier)
        if s.startswith(">"):
            q = []
            while i < n and lines[i].strip().startswith(">"):
                q.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append("\\begin{quote}\n%s\n\\end{quote}" % inline(" ".join(q), in_supp))
            continue

        # lists
        lm = re.match(r"^(\d+\.|-)\s+", s)
        if lm:
            ordered = lm.group(1) != "-"
            items, cur = [], None
            while i < n:
                t = lines[i]
                ts = t.strip()
                im = re.match(r"^(\d+\.|-)\s+(.*)$", ts)
                if im and (im.group(1) != "-") == ordered and not t.startswith("   "):
                    if cur is not None:
                        items.append(cur)
                    cur = im.group(2)
                    i += 1
                elif ts and cur is not None and (t.startswith(" ") or t.startswith("\t")):
                    cur += " " + ts
                    i += 1
                else:
                    break
            if cur is not None:
                items.append(cur)
            env = "enumerate" if ordered else "itemize"
            out.append("\\begin{%s}\n%s\n\\end{%s}" % (env, "\n".join(
                "  \\item %s" % inline(it, in_supp) for it in items), env))
            continue

        # paragraph
        para = []
        while i < n and lines[i].strip() and not re.match(
                r"^(#{2,4}\s|\||>|!\[|(\d+\.|-)\s+|---$)", lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        if para:
            out.append(inline(" ".join(para), in_supp))
        else:
            i += 1
    return "\n\n".join(out)


# ---------------------------------------------------------------------------
BIB = r"""@inproceedings{sharafaldin2018,
  author    = {Sharafaldin, I. and Lashkari, A. H. and Ghorbani, A. A.},
  title     = {Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization},
  booktitle = {Proceedings of the 4th International Conference on Information Systems Security and Privacy (ICISSP)},
  pages     = {108--116},
  year      = {2018}
}
@inproceedings{engelen2021,
  author    = {Engelen, G. and Rimmer, V. and Joosen, W.},
  title     = {Troubleshooting an Intrusion Detection Dataset: the {CICIDS2017} Case Study},
  booktitle = {IEEE Security and Privacy Workshops (SPW)},
  year      = {2021}
}
@inproceedings{lanvin2023,
  author    = {Lanvin, M. and Gimenez, P.-F. and Han, Y. and Majorczyk, F. and M{\'e}, L. and Totel, {\'E}.},
  title     = {Errors in the {CICIDS2017} Dataset and the Significant Differences in Detection Performances It Makes},
  booktitle = {Risks and Security of Internet and Systems (CRiSIS 2022)},
  series    = {Lecture Notes in Computer Science},
  volume    = {13857},
  publisher = {Springer},
  year      = {2023},
  doi       = {10.1007/978-3-031-31108-6_2}
}
@article{goldschmidt2025,
  author  = {Goldschmidt, P. and Chud{\'a}, D.},
  title   = {Network Intrusion Datasets: A Survey, Limitations, and Recommendations},
  journal = {Computers \& Security},
  volume  = {156},
  pages   = {104510},
  year    = {2025}
}
@inproceedings{sommer2010,
  author    = {Sommer, R. and Paxson, V.},
  title     = {Outside the Closed World: On Using Machine Learning for Network Intrusion Detection},
  booktitle = {IEEE Symposium on Security and Privacy},
  pages     = {305--316},
  year      = {2010}
}
@inproceedings{arp2022,
  author    = {Arp, D. and Quiring, E. and Pendlebury, F. and Warnecke, A. and Pierazzi, F. and Wressnegger, C. and Cavallaro, L. and Rieck, K.},
  title     = {Dos and Don'ts of Machine Learning in Computer Security},
  booktitle = {USENIX Security Symposium},
  pages     = {3971--3988},
  year      = {2022}
}
@article{badreddine2022,
  author  = {Badreddine, S. and d'Avila Garcez, A. and Serafini, L. and Spranger, M.},
  title   = {Logic Tensor Networks},
  journal = {Artificial Intelligence},
  volume  = {303},
  pages   = {103649},
  year    = {2022},
  doi     = {10.1016/j.artint.2021.103649}
}
@inproceedings{bizzarri2024,
  author    = {Bizzarri, A. and Jalaian, B. and Riguzzi, F. and Bastian, N. D.},
  title     = {A Neuro-Symbolic Artificial Intelligence Network Intrusion Detection System},
  booktitle = {International Conference on Computer Communications and Networks (ICCCN)},
  year      = {2024}
}
@article{bizzarri2025survey,
  author  = {Bizzarri, A. and Yu, C. and Jalaian, B. and Riguzzi, F. and Bastian, N. D.},
  title   = {Neurosymbolic {AI} for Network Intrusion Detection Systems: A Survey},
  journal = {Journal of Information Security and Applications},
  volume  = {94},
  pages   = {104205},
  year    = {2025}
}
@inproceedings{cruz2017,
  author    = {Cruz, S. and Coleman, C. and Rudd, E. M. and Boult, T. E.},
  title     = {Open Set Intrusion Recognition for Fine-Grained Attack Categorization},
  booktitle = {IEEE International Symposium on Technologies for Homeland Security (HST)},
  year      = {2017}
}
@inproceedings{hendrycks2017,
  author    = {Hendrycks, D. and Gimpel, K.},
  title     = {A Baseline for Detecting Misclassified and Out-of-Distribution Examples in Neural Networks},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2017}
}
@inproceedings{liang2018,
  author    = {Liang, S. and Li, Y. and Srikant, R.},
  title     = {Enhancing the Reliability of Out-of-Distribution Image Detection in Neural Networks},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2018}
}
@inproceedings{liu2020,
  author    = {Liu, W. and Wang, X. and Owens, J. D. and Li, Y.},
  title     = {Energy-Based Out-of-Distribution Detection},
  booktitle = {Advances in Neural Information Processing Systems (NeurIPS)},
  volume    = {33},
  year      = {2020}
}
@inproceedings{grov2024,
  author    = {Grov, G. and Halvorsen, J. and Eckhoff, M. W. and Hansen, B. J. and Eian, M. and Mavroeidis, V.},
  title     = {On the Use of Neurosymbolic {AI} for Defending Against Cyber Attacks},
  booktitle = {Neural-Symbolic Learning and Reasoning (NeSy 2024)},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer},
  pages     = {119--140},
  year      = {2024},
  doi       = {10.1007/978-3-031-71167-1_7}
}
@inproceedings{zhou2024,
  author    = {Zhou, A. and Xu, X. and Raghunathan, R. and Lal, A. and Guan, X. and Yu, B. and Li, B.},
  title     = {{KnowGraph}: Knowledge-Enabled Anomaly Detection via Logical Reasoning on Graph Data},
  booktitle = {Proceedings of the ACM SIGSAC Conference on Computer and Communications Security (CCS)},
  pages     = {168--182},
  year      = {2024},
  doi       = {10.1145/3658644.3690354}
}
@article{kalutharage2025,
  author  = {Kalutharage, C. S. and Liu, X. and Chrysoulas, C.},
  title   = {Neurosymbolic Learning and Domain Knowledge-Driven Explainable {AI} for Enhanced {IoT} Network Attack Detection and Response},
  journal = {Computers \& Security},
  volume  = {151},
  pages   = {104318},
  year    = {2025},
  doi     = {10.1016/j.cose.2025.104318}
}
@misc{hakim2025,
  author        = {Hakim, S. B. and Adil, M. and Velasquez, A. and Xu, S. and Song, H. H.},
  title         = {Neuro-Symbolic {AI} for Cybersecurity: State of the Art, Challenges, and Opportunities},
  year          = {2025},
  eprint        = {2509.06921},
  archivePrefix = {arXiv}
}
"""


def _regions():
    """The markdown regions that are converted: title, abstract, body sections, appendices."""
    body = strip_build_notes(io.open(SRC_BODY, encoding="utf-8").read())
    supp = strip_build_notes(io.open(SRC_SUPP, encoding="utf-8").read())
    title = re.search(r"(?m)^# (.+)$", body).group(1).strip()
    abstract = re.search(r"(?ms)^## Abstract\s*\n(.*?)(?=^---|^## )", body).group(1).strip()
    main = re.search(r"(?ms)^## 1 Introduction.*?(?=^## References)", body).group(0)
    apps = re.search(r"(?ms)^## Appendix A.*\Z", supp).group(0)
    return title, abstract, main, apps


def _converted_source():
    return "\n".join(_regions())


def generate():
    title, abstract, main, apps = _regions()

    os.makedirs(os.path.join(OUT, "figures"), exist_ok=True)
    tex = [
        "% Generated by scripts/md_to_pmlr.py from nesy_body.md + nesy_supplementary.md.",
        "% Do not edit by hand: change the markdown (which verify_draft.py checks) and regenerate.",
        "\\documentclass[anon]{nesy2026} % anonymised submission for OpenReview",
        "",
        "\\usepackage{booktabs}",
        "\\usepackage{tabularx}",
        "",
        "\\title[%s]{%s}" % (inline(SHORT_TITLE), inline(title)),
        "% Author block is suppressed by the anon option; fill in only for the camera-ready.",
        "\\clearauthor{\\Name{Author Name} \\Email{author@example.org}\\\\ \\addr Address}",
        "",
        "\\begin{document}",
        "\\maketitle",
        "",
        "\\begin{abstract}",
        inline(" ".join(abstract.split())),
        "\\end{abstract}",
        "",
        blocks_to_latex(main),
        "",
        "\\bibliography{refs}",
        "",
        "\\appendix",
        "",
        blocks_to_latex(apps, in_supp=True),
        "",
        "\\end{document}",
        "",
    ]
    io.open(os.path.join(OUT, "main.tex"), "w", encoding="utf-8", newline="\n").write("\n".join(tex))
    io.open(os.path.join(OUT, "refs.bib"), "w", encoding="utf-8", newline="\n").write(BIB)
    for stem in FIGURES:
        shutil.copyfile(os.path.join(paths.FIGURES, stem + ".png"),
                        os.path.join(OUT, "figures", stem + ".png"))
    if TEMPLATE_CLS and os.path.exists(TEMPLATE_CLS):
        shutil.copyfile(TEMPLATE_CLS, os.path.join(OUT, "nesy2026.cls"))
    print("wrote %s" % OUT)


# ---------------------------------------------------------------------------
def lint():
    """Structural checks that catch what would stop pdflatex. Not a compile."""
    tex = io.open(os.path.join(OUT, "main.tex"), encoding="utf-8").read()
    bib = io.open(os.path.join(OUT, "refs.bib"), encoding="utf-8").read()
    problems = []
    body = re.sub(r"(?m)%.*$", "", tex.replace(r"\%", ""))
    unesc = re.sub(r"\\[{}]", "", body)
    if unesc.count("{") != unesc.count("}"):
        problems.append("brace imbalance: %d '{' vs %d '}'"
                        % (unesc.count("{"), unesc.count("}")))
    begins = re.findall(r"\\begin\{(\w+\*?)\}", body)
    ends = re.findall(r"\\end\{(\w+\*?)\}", body)
    for e in set(begins) | set(ends):
        if begins.count(e) != ends.count(e):
            problems.append("environment %s: %d begin vs %d end"
                            % (e, begins.count(e), ends.count(e)))
    keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    for grp in re.findall(r"\\cite[pt]?\{([^}]+)\}", body):
        for k in grp.split(","):
            if k.strip() not in keys:
                problems.append("citation key not in refs.bib: %s" % k)
    labels = set(re.findall(r"\\label\{([^}]+)\}", body))
    labels |= set(re.findall(r"\\floatconts\s*\{([^}]+)\}", body))
    for r in re.findall(r"\\ref\{([^}]+)\}", body):
        if r not in labels:
            problems.append("\\ref to undefined label: %s" % r)
    for g in re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", body):
        if not os.path.exists(os.path.join(OUT, g + ".png")):
            problems.append("missing figure file: %s" % g)
    non_ascii = sorted(set(c for c in body if ord(c) > 127))
    if non_ascii:
        # code points only: printing the character itself crashes a cp1252 Windows console
        problems.append("unmapped non-ASCII: %s" % " ".join(
            "U+%04X" % ord(c) for c in non_ascii))
    for pat, what in ((r"\*\*", "markdown bold"), (r"(?<!\\)\[\d+\]", "raw [n] citation"),
                      # the unicode pass maps a leftover section sign to \S{}, so look for
                      # that: every section sign in the prose should have become a \ref
                      (r"\u00a7|\\S\{\}", "unconverted section sign"), (r"^\|", "raw table row"),
                      (r"\x00", "unresolved placeholder")):
        hits = re.findall(pat, body, flags=re.M)
        if hits:
            problems.append("%d leftover %s" % (len(hits), what))
    # every number verify_draft.py checked in the markdown must reach the .tex unchanged
    num = re.compile(r"\d[\d,]*\.\d+|\d{1,3}(?:,\d{3})+")
    src_nums = sorted(num.findall(_converted_source()))
    tex_nums = sorted(num.findall(body))
    if src_nums != tex_nums:
        from collections import Counter
        lost = Counter(src_nums) - Counter(tex_nums)
        gained = Counter(tex_nums) - Counter(src_nums)
        problems.append("numbers differ from the verified markdown: lost %s, gained %s"
                        % (dict(lost), dict(gained)))
    else:
        print("numbers: all %d decimal/grouped figures carried over unchanged" % len(src_nums))
    stats = {"sections": len(re.findall(r"\\section\{", body.split("\\appendix")[0])),
             "appendices": len(re.findall(r"\\section\{", body.split("\\appendix")[-1])),
             "tables": len(re.findall(r"\\begin\{tabularx?\}", body)),
             "figures": len(re.findall(r"\\begin\{figure\}", body)),
             "citations": len(re.findall(r"\\cite[pt]\{", body)),
             "refs": len(re.findall(r"\\ref\{", body))}
    print("structure: %s" % ", ".join("%s %d" % kv for kv in stats.items()))
    if problems:
        print("LINT FAILED (%d):" % len(problems))
        for p in problems:
            print("  - " + p)
        return 1
    print("LINT PASSED - structurally sound. NOT compiled: the page count is unverified.")
    return 0


if __name__ == "__main__":
    generate()
    sys.exit(lint())
