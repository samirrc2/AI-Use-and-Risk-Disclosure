"""Repair the latexdiff output before it is typeset. Used only by build_tracked.sh.

Two problems, both artefacts of the diff rather than of the manuscript:

1. latexdiff garbles the one-line \keyFont{ \section{Word count:} ... } block. Its nested
   braces confuse the brace matcher, which emits duplicated fragments and an unbalanced
   group, and the build fails. That line is metadata, not prose, so the tracked copy shows
   the current line plainly rather than as a marked-up diff.

2. Every changed table cell is wrapped in \DIFadd/\DIFdel markup, which widens the cell and
   pushes wide tables past the right margin. Tightening the column separation and allowing
   a little extra stretch keeps them inside the text block.

Usage: python3 fix_tracked.py <latexdiff-output.tex> <current-manuscript.tex>
"""
import re
import sys


def main(diff_path: str, current_path: str) -> None:
    s = open(diff_path, encoding="utf-8").read()
    cur = open(current_path, encoding="utf-8").read()

    m = re.search(r"\\keyFont\{ \\section\{Word count:\}.*?\}\s*$", cur, re.M)
    if not m:
        sys.exit("fix_tracked: no word-count line found in the current manuscript")
    clean = m.group(0)

    i = s.index("Word count")
    start = s.rindex("\\DIFdelbegin", 0, i)
    end = s.index("\\end{abstract}", start)
    s = s[:start] + clean + "\n" + s[end:]

    j = s.index("\\begin{document}")
    s = s[:j] + "\\setlength{\\tabcolsep}{3pt}\n\\emergencystretch=3em\n" + s[j:]

    open(diff_path, "w", encoding="utf-8").write(s)
    print("fix_tracked: word-count line de-diffed; table spacing tightened")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
