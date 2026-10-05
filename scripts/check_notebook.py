"""Mechanical checks a package notebook must pass before it is committed.

Usage: python scripts/check_notebook.py notebooks/<package>.ipynb

Prints PASS or FAIL followed by the reasons. Exit code 0 on PASS, 1 on FAIL.
Checks are deliberately simple and literal. They catch the failures seen in the cao pilot:
unexecuted cells, duplicated copies, plotting leftovers, explanation cells with nothing above them,
internal wording, and placeholder prose. HTML exports are generated separately by scripts/rebuild.py.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

INTERNAL_WORDS = [
    r"\be-?mail", r"author[- ]email", "astro" + "labe", r"\b" + "la" + r"ne\b", "co" + "work",
    "our " + "questions", "bears " + "on", r"hypothes[ie]s" + r"\.md", "ideas" + r"\.md", "hand" + "off",
]
PUBLIC_REPOSITORY_URL = "https://github.com/" + "astro" + "labe-analytics/public-battery-field-data/"
LEFTOVER_OUTPUT = re.compile(r"^(Text|<matplotlib|\[<matplotlib|<Axes|<Figure size)", re.I)
PLACEHOLDER_PHRASES = [
    r"will be written", r"to be read off", r"\bTBD\b", r"to be filled", r"after the executed output",
    r"pending inspection", r"to be completed", r"to be added",
]
EXTREME_WORDS = re.compile(r"\b(maximum|minimum|\bmax\b|\bmin\b|reaches|reached|highest|lowest|peak|ranges? from)\b", re.I)
RAW_OR_CLEAN = re.compile(r"\b(raw|clean|cleaned|cleaning|unfiltered|as released)\b", re.I)


def main(path: str) -> int:
    nb_path = Path(path)
    problems: list[str] = []
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    cells = nb["cells"]
    md = [c for c in cells if c["cell_type"] == "markdown"]
    code = [c for c in cells if c["cell_type"] == "code"]

    # 1. exactly one title cell
    titles = [c for c in md if "".join(c["source"]).lstrip().startswith("# ")]
    if len(titles) != 1:
        problems.append(f"expected exactly one '# ' title cell, found {len(titles)}")

    # 2. numbered section headings appear once each and in order
    heads = []
    for c in md:
        first = "".join(c["source"]).strip().splitlines()[0] if "".join(c["source"]).strip() else ""
        m = re.match(r"##\s+(\d+)\.\s", first)
        if m:
            heads.append(int(m.group(1)))
    if heads != sorted(set(heads)):
        problems.append(f"section numbers are duplicated or out of order: {heads}")
    if heads and heads != list(range(1, len(heads) + 1)):
        problems.append(f"section numbers are not 1..n: {heads}")
    for c in md:
        text = "".join(c["source"])
        if len(re.findall(r"^##\s+\d+\.", text, flags=re.M)) > 1:
            problems.append("a markdown cell contains more than one section heading")
            break

    # 3. every code cell executed, none errored
    for i, c in enumerate(code):
        outs = c.get("outputs", [])
        if c.get("execution_count") is None:
            problems.append(f"code cell {i} was not executed")
        for o in outs:
            if o.get("output_type") == "error":
                problems.append(f"code cell {i} raised {o.get('ename')}: {str(o.get('evalue'))[:80]}")
            data = o.get("data", {})
            if "image/png" in data or "image/svg+xml" in data:
                continue  # a figure's text/plain companion is not a leftover
            text = "".join(o.get("text", [])) or "".join(data.get("text/plain", []))
            if text and LEFTOVER_OUTPUT.match(text.strip()):
                problems.append(f"code cell {i} has a plotting leftover output: {text.strip()[:60]!r}")

    # 4. each result cell follows a code cell that produced output
    for i in range(1, len(cells)):
        c, prev = cells[i], cells[i - 1]
        if c["cell_type"] == "markdown" and prev["cell_type"] == "code":
            text = "".join(c["source"]).strip()
            if text and not text.startswith("#") and not prev.get("outputs"):
                problems.append(f"markdown cell {i} explains a code cell that produced no output")

    # 5. internal wording
    full = "\n".join("".join(c["source"]) for c in md).lower()
    # Links to this repository's own public address are allowed; the organisation name elsewhere is not.
    full = full.replace(PUBLIC_REPOSITORY_URL, "")
    for pat in INTERNAL_WORDS:
        if re.search(pat, full):
            problems.append(f"internal wording matches /{pat}/ in markdown")

    # 6. prose style: semicolons in markdown
    for i, c in enumerate(md):
        text = "".join(c["source"])
        if ";" in re.sub(r"`[^`]*`", "", text):
            problems.append(f"markdown cell {i} contains a semicolon in prose")
            break

    # 7. no placeholder sentences promising text later
    for i, c in enumerate(md):
        text = "".join(c["source"])
        for pat in PLACEHOLDER_PHRASES:
            if re.search(pat, text, flags=re.I):
                problems.append(f"markdown cell {i} contains a placeholder phrase /{pat}/")
                break

    # 8. a result cell that reports an extreme value says whether it is raw or cleaned
    for i in range(1, len(cells)):
        c, prev = cells[i], cells[i - 1]
        if c["cell_type"] != "markdown" or prev["cell_type"] != "code":
            continue
        text = "".join(c["source"])
        if EXTREME_WORDS.search(text) and re.search(r"\d", text) and not RAW_OR_CLEAN.search(text):
            problems.append(f"markdown cell {i} reports an extreme value without saying raw or cleaned")

    # 9. an in-depth notebook (<package>_in_depth.ipynb) needs the release's basic notebook (<package>.ipynb)
    if nb_path.stem.endswith("_in_depth"):
        basic = nb_path.with_name(nb_path.stem[: -len("_in_depth")] + ".ipynb")
        if not basic.exists():
            problems.append(f"in-depth notebook without its basic notebook {basic.name}")

    if problems:
        print("FAIL")
        for p in problems:
            print(" -", p)
        return 1
    print(f"PASS  {nb_path.name}: {len(cells)} cells, {len(code)} code cells executed, sections {heads}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
