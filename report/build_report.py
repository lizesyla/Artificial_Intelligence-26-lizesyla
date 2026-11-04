"""Builds report/report.md from the four <part>/report.md files plus
report/intro.md and report/outro.md.   Usage:  python report/build_report.py"""
import os, re
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
parts = ["social_golfers", "sudoku_solver", "latin_square", "search_trees"]
out = [open(os.path.join(here, "intro.md"), encoding="utf-8").read()]
for p in parts:
    text = open(os.path.join(root, p, "report.md"), encoding="utf-8").read()
    lines = []
    in_code = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        if not in_code and re.match(r"^#{1,5} ", line):
            line = "#" + line                       # one level deeper
        lines.append(line)
    body = "\n".join(lines)
    body = re.sub(r"\]\((?!https?:|\.\./|#)([^)]+)\)", lambda m: f"](../{p}/{m.group(1)})", body)
    out.append("\n---\n\n" + body.strip() + "\n")
out.append(open(os.path.join(here, "outro.md"), encoding="utf-8").read())
note = ("<!-- This file is generated from the four <part>/report.md files; edit those and "
        "rebuild with: python report/build_report.py -->\n")
open(os.path.join(root, "report", "report.md"), "w", encoding="utf-8").write(note + "\n".join(out))
print("ok")
