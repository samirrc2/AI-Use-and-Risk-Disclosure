#!/usr/bin/env python3
"""
build_responses.py -- turn the plain-text reviewer responses into clean PDFs.

The .txt files stay the source of truth: the portal needs plain text, and the letters are
written and verified as text. This only typesets them. No bold, no italics, no colour; the
structure is carried by spacing, bullets and indentation.

Usage:  python build_responses.py
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
           "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
           "^": r"\textasciicircum{}"}


def esc(t):
    out = []
    for ch in t:
        out.append(SPECIAL.get(ch, ch))
    t = "".join(out)
    # keep en dashes in numeric ranges readable, and quote marks upright
    t = re.sub(r"(\d)-(\d)", r"\1--\2", t)
    # straight quotes must alternate: `` opens, '' closes. Replacing both with '' renders the
    # opening one as a closing curly quote.
    out = []
    openq = True
    for ch in t:
        if ch == '"':
            out.append("``" if openq else "''")
            openq = not openq
        else:
            out.append(ch)
    return "".join(out)


PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{mathptmx}   % Times; newtx is not in this TinyTeX
\usepackage[margin=1in]{geometry}
\usepackage[hidelinks]{hyperref}
\usepackage{enumitem}
\usepackage{microtype}
% Almost plain: no italics, no rules. Bold is used on exactly two things, the question heading
% and the "Authors response :" marker, so a reviewer can find their own comment and our reply at
% a glance. Everything else takes its hierarchy from vertical space and indentation.
\setlength{\parindent}{0pt}
\setlength{\parskip}{7pt}
% \textperiodcentered is a middot and read as too small. \textbullet at \large, raised a
% touch so it sits on the text's optical centre rather than the baseline.
\setlist[itemize]{leftmargin=1.6em,labelsep=0.6em,itemsep=4pt,topsep=4pt,parsep=0pt,
                 label=\raisebox{-0.15ex}{\large\textbullet}}
\pagestyle{plain}
\raggedright
\begin{document}
"""


def convert(txt_path, tex_path):
    """Parse the letter into blocks, then join them with blank lines.

    Joining with single newlines silently merged headings into the preceding paragraph, because
    LaTeX needs a blank line to start a new one. Blocks are kept separate all the way through and
    only joined at the end.
    """
    lines = open(txt_path, encoding="utf-8").read().split("\n")
    blocks = []
    head = [l for l in lines[:2] if l.strip()]
    blocks.append("{\\large " + esc(head[0]) + "}")
    if len(head) > 1:
        blocks.append(esc(head[1]))
    blocks.append("\\vspace{4pt}")

    i = 2
    para = []
    items = []

    def flush_para():
        if para:
            blocks.append(esc(" ".join(para)))
            para.clear()

    def flush_items():
        if items:
            blocks.append("\\begin{itemize}\n" + "\n".join(items) + "\n\\end{itemize}")
            items.clear()

    while i < len(lines):
        s_ = lines[i].strip()
        if not s_:
            flush_para()
            i += 1
            continue
        if re.match(r"^Q\d+\.", s_):
            flush_para(); flush_items()
            q = [s_]
            while i + 1 < len(lines) and lines[i + 1].strip() \
                    and not lines[i + 1].lstrip().startswith("- ") \
                    and not lines[i + 1].startswith("Addressed"):
                i += 1
                q.append(lines[i].strip())
            # a rule-free, weight-free heading: extra space above, a touch below
            blocks.append("\\vspace{12pt}\n\\textbf{" + esc(" ".join(q)) + "}")
            i += 1
            continue
        if s_.startswith("Authors response"):
            # The reviewer's comment is quoted in full above; this marks where our reply
            # begins. Extra space above so the two are visually separable without a rule.
            flush_para(); flush_items()
            blocks.append("\\vspace{8pt}\n\\textbf{" + esc(s_) + "}")
            i += 1
            continue
        if s_.startswith("Addressed in"):
            flush_para(); flush_items()
            a = [s_]
            while i + 1 < len(lines) and lines[i + 1].strip() \
                    and not lines[i + 1].lstrip().startswith("- "):
                i += 1
                a.append(lines[i].strip())
            blocks.append(esc(" ".join(a)))
            i += 1
            continue
        if s_.startswith("- "):
            flush_para()
            item = [s_[2:]]
            while i + 1 < len(lines) and lines[i + 1].startswith("  ") \
                    and not lines[i + 1].strip().startswith("- "):
                i += 1
                item.append(lines[i].strip())
            items.append("\\item " + esc(" ".join(item)))
            i += 1
            continue
        flush_items()
        para.append(s_)
        i += 1
    flush_para(); flush_items()
    open(tex_path, "w", encoding="utf-8").write(
        PREAMBLE + "\n\n".join(blocks) + "\n\n\\end{document}\n")


def main():
    tex = shutil.which("pdflatex") or os.path.expanduser(
        "~/Library/TinyTeX/bin/universal-darwin/pdflatex")
    if not os.path.exists(tex) and not shutil.which("pdflatex"):
        sys.exit("pdflatex not found")
    for src in ("response_reviewer_1.txt", "response_reviewer_3.txt"):
        stem = src[:-4]
        convert(os.path.join(HERE, src), os.path.join(HERE, stem + ".tex"))
        for _ in range(2):
            subprocess.run([tex, "-interaction=nonstopmode", stem + ".tex"],
                           cwd=HERE, capture_output=True)
        log = os.path.join(HERE, stem + ".log")
        pages = "?"
        if os.path.exists(log):
            m = re.search(r"\((\d+) pages", open(log, encoding="utf-8", errors="replace").read())
            if m:
                pages = m.group(1)
        for ext in (".aux", ".log", ".out"):
            p = os.path.join(HERE, stem + ext)
            if os.path.exists(p):
                os.remove(p)
        print(f"  {stem}.pdf  {pages} pages")


if __name__ == "__main__":
    main()
