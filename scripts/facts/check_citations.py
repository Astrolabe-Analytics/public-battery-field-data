"""Check every 'stated' fact in fielddata/package_facts.csv against the source it cites.

For each stated value this script (1) checks that the cited DOI or URL is the package's registered
paper or data record, and (2) searches the package's held paper and supplementary PDFs for the value
itself (numbers in common written forms; chemistry names as words). It writes
reports/CITATION_CHECK.md. "Not found" means a person should look: PDF text extraction misses tables
and figures, so it is a prompt to check, not proof of an error. Claims of absence (fault-onset
timestamps, sentinel documentation) and values whose source is a released file are listed separately.

Usage: python scripts/facts/check_citations.py   (needs the data and papers under data_root)
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fielddata.config import data_root  # noqa: E402
from fielddata.registry import PACKAGES  # noqa: E402

FACTS = ROOT / "fielddata" / "package_facts.csv"
OUTPUT = ROOT / "reports" / "CITATION_CHECK.md"
CACHE = ROOT / "data" / "extracts" / "pdftext"
ABSENCE = {"fault_onset_timestamp", "sentinels_documented"}
# Values the text search cannot confirm (dates, table layouts), checked by reading the page named here.
MANUAL = {
    ("tsukuba", "span_unit_years"): "read on sdata201920.pdf p. 4: data per second 'from 1 January 2015 to 24 April 2018'",
}
CHEM_WORDS = {"NMC": ["NMC", "LiNi", "nickel manganese cobalt"], "NCM": ["NCM", "NMC", "LiNi"], "LFP": ["LFP", "LiFePO", "iron phosphate"],
              "LMO": ["LMO", "LiMn2O4", "manganese oxide"], "LTO": ["LTO", "titanate"], "OCSM": ["OCSM"], "OPzV": ["OPzV"],
              "lead-acid": ["lead-acid", "lead acid", "Pb"], "lithium-ion": ["lithium-ion", "Li-ion", "lithium ion"]}


def pages(package: str) -> list[tuple[str, int, str]]:
    import pypdf
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"{package}.json"
    if cached.is_file():
        return [tuple(x) for x in json.loads(cached.read_text(encoding="utf-8"))]
    base = (data_root() / PACKAGES[package]["data_directory"]).parent
    out = []
    for pdf in sorted(list((base / "paper").glob("*.pdf")) + list((base / "supplementary").glob("*.pdf"))):
        try:
            for number, page in enumerate(pypdf.PdfReader(pdf).pages, 1):
                out.append((pdf.parent.name + "/" + pdf.name, number, " ".join((page.extract_text() or "").split())))
        except Exception as exc:  # unreadable PDF
            out.append((pdf.name, 0, f"UNREADABLE {exc}"))
    cached.write_text(json.dumps(out), encoding="utf-8", newline="\n")
    return out


def number_forms(value: float, field: str) -> list[str]:
    forms = set()
    candidates = [value]
    if field == "energy_mwh":
        candidates += [value * 1000]
    for v in candidates:
        if abs(v - round(v)) < 1e-9:
            n = int(round(v))
            forms |= {str(n), f"{n:,}", f"{n:,}".replace(",", " "), f"{n:,}".replace(",", ".")}
        else:
            for digits in (1, 2, 3):
                text = f"{v:.{digits}f}".rstrip("0").rstrip(".")
                forms |= {text, text.replace(".", ",")}
    return sorted(forms, key=len, reverse=True)


def search(texts, terms):
    hits = []
    for name, page, text in texts:
        for term in terms:
            pattern = r"(?<![\d.,])" + re.escape(term) + r"(?![\d])" if term[0].isdigit() else re.escape(term)
            if re.search(pattern, text, flags=0 if term[0].isdigit() else re.I):
                hits.append(f"{name} p.{page}")
                break
    return hits


def main() -> None:
    rows = [r for r in csv.DictReader(FACTS.open(encoding="utf-8")) if r["basis"] == "stated"]
    checked, absence, release_files = [], [], []
    for row in rows:
        package, field, value, source = row["package"], row["field"], row["value"], row["source"]
        if field in ABSENCE:
            absence.append(row)
            continue
        if "released with the data" in source or source.startswith(("fielddata/", "docs/", "Metadata_")):
            release_files.append(row)
            continue
        urls = PACKAGES[package]["urls"]
        registered = [u for u in (urls.get("paper"), urls.get("data")) if u]
        cited = re.findall(r"https?://\S+?(?=[,;\s]|$)", source)
        doi_ok = any(c.rstrip(".,") in registered for c in cited)
        texts = pages(package)
        try:
            terms = number_forms(float(value), field)
            kind = "number"
        except ValueError:
            words = [w for key, ws in CHEM_WORDS.items() if re.search(re.escape(key), value, re.I) for w in ws]
            terms, kind = (words or [value]), "text"
        hits = search(texts, terms) if texts else []
        if not hits and (package, field) in MANUAL:
            hits = [MANUAL[(package, field)]]
        checked.append((package, field, value, source, doi_ok, hits, bool(texts)))
    lines = ["# Citation check of stated facts", "",
             "Generated by `scripts/facts/check_citations.py`. For each value stated by a source: does the cited DOI or URL match the package's registered paper or data record, and can the value be found in the held paper or supplementary PDFs? `not found` is a prompt for a person to look (text extraction misses tables and figures), not proof of an error.", "",
             "| Package | Field | Value | Cited DOI matches registry | Found in held PDFs |", "|---|---|---|---|---|"]
    for package, field, value, source, doi_ok, hits, has_pdf in checked:
        where = ", ".join(sorted(set(hits))[:3]) if hits else ("not found" if has_pdf else "no PDF held")
        lines.append(f"| {package} | {field} | {value} | {'yes' if doi_ok else '**no**'} | {where} |")
    found = sum(1 for c in checked if c[5])
    lines += ["", f"Summary: {len(checked)} stated values checked; {found} found in a held PDF; {sum(1 for c in checked if not c[4])} cite a DOI or URL that is not the package's registered paper or data record.", "",
              "## Values whose source is a released file", ""]
    lines += [f"- {r['package']} {r['field']} = {r['value']} ({r['source']})" for r in release_files]
    lines += ["", "## Claims of absence (not checkable by search)", "",
              f"{len(absence)} values state that a release has no fault-onset timestamp or does not document its sentinel codes. They rest on reading the release and its record; Table 3 and the loader schema files carry the evidence."]
    # First authors: docs/descriptor/citations.csv is the one record of who wrote each paper; confirm each
    # first author's surname on the first two pages of the held paper (or its article PDF).
    lines += ["", "## First authors", "", "| Package | First author in citations.csv | Found on page 1 or 2 of |", "|---|---|---|"]
    bad = 0
    for row in csv.DictReader((ROOT / "docs" / "descriptor" / "citations.csv").open(encoding="utf-8")):
        held = pages(row["package"])
        papers = [t for t in held if t[0].startswith("paper/")] or held
        where = sorted({name for name, page, text in papers if page <= 2 and row["first_author"] in text[:3000]})
        bad += not where
        lines.append(f"| {row['package']} | {row['first_author']} | {', '.join(where) if where else '**not found**'} |")
    lines += ["", f"{bad} first authors not found."]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)}: {len(checked)} checked, {found} found")


if __name__ == "__main__":
    main()
