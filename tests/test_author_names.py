"""Every author-year citation written in the docs must match docs/descriptor/citations.csv.

citations.csv is the one place first authors and years are recorded; scripts/facts/check_citations.py
confirms each first author on page 1 of the held paper. This test catches hand-typed names that drift.
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CITE = re.compile(r"\b([A-Z][\wÀ-ſ-]+) et al\.,?(?: \*?[A-Z][^()]*?\*?)? \(?((?:19|20)\d{2})\)?")


def test_author_year_citations_match_the_citation_table():
    rows = list(csv.DictReader((ROOT / "docs" / "descriptor" / "citations.csv").open(encoding="utf-8")))
    known = {(r["first_author"], r["year"]) for r in rows if r["et_al"] == "yes"}
    surnames = {r["first_author"] for r in rows}
    problems = []
    files = [*ROOT.glob("docs/**/*.md"), *ROOT.glob("fielddata/loaders/*_SCHEMA.md"), ROOT / "README.md"]
    for path in files:
        if path.name == "DESCRIPTOR_filled.md":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for name, year in CITE.findall(line):
                if (name, year) not in known:
                    if name in surnames and any(r["first_author"] == name and r["et_al"] != "yes" for r in rows):
                        reason = "paper has three or fewer authors; name them instead of et al."
                    else:
                        reason = "year differs" if name in surnames else "not a first author in citations.csv"
                    problems.append(f"{path.relative_to(ROOT)}:{number}: {name} et al. ({year}): {reason}")
    assert not problems, "\n".join(problems)
