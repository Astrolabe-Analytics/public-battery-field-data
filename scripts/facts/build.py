"""Build the long-form package facts table and public facts audit."""
from __future__ import annotations

import csv
import json

from _common import FIELDS, OUT, ROOT
from fielddata.registry import PACKAGES

FACTS = ROOT / "fielddata" / "package_facts.csv"
AUDIT = ROOT / "reports" / "FACTS_AUDIT.md"
ESTIMATES = {
    "bilfinger2024": "2-4 h: inspect all vehicle pickle schemas and timestamps.",
    "bilfinger2026": "2-4 h: inspect all vehicle pickle schemas and timestamps.",
    "cao": "1 h: reconcile manufacturer chemistry and locate a source-backed pack rating, if any.",
    "changan": "8-16 h: stream the split raw archive and count cell values for all 300 vehicles.",
    "cloverleaf": "2-3 h: profile all workbook sheets and timestamp boundaries.",
    "evbattery": "4-8 h: bounded pickle-schema and snippet-length scan with cadence evidence.",
    "ku_leuven_bev": "3-5 h: inspect nested archive metadata, telemetry schemas, and timestamps.",
    "m5bat-2023-04": "1-2 h: scan first and last timestamps in ten battery CSV members.",
    "rwth-home": "4-8 h: inspect metadata workbook and one header per monthly schema.",
    "xie": "4-8 h: extract RAR metadata and scan device timestamps and populated channels.",
    "zhang2023": "4-8 h: bounded pickle-schema and snippet-length scan with cadence evidence.",
}


def load_reports() -> list[dict]:
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(OUT.glob("*.json"))]
    if len(reports) != len(PACKAGES):
        raise ValueError(f"expected {len(PACKAGES)} package reports, found {len(reports)}")
    return reports


def main() -> None:
    reports = load_reports()
    rows = []
    for report in reports:
        for field in FIELDS:
            item = report["facts"][field]
            rows.append({
                "package": report["package"], "field": field, "value": item["value"],
                "basis": item["basis"], "source": item["source"],
                "note": item["note"],
            })
    with FACTS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["package", "field", "value", "basis", "source", "note"])
        writer.writeheader()
        writer.writerows(rows)

    by_package = {report["package"]: report for report in reports}
    lines = [
        "# Facts audit", "",
        "Each cell gives the status of the corresponding value in `fielddata/package_facts.csv`: measured from the release, stated by a public source, derived by a stated rule, unavailable from the release, or still open.", "",
        "| Package | " + " | ".join(FIELDS) + " |",
        "|---|" + "---|" * len(FIELDS),
    ]
    for package in sorted(by_package):
        facts = by_package[package]["facts"]
        lines.append("| " + package + " | " + " | ".join(facts[field]["basis"] for field in FIELDS) + " |")
    lines.extend(["", "## Open values", ""])
    for package in sorted(by_package):
        open_items = [(field, item) for field, item in by_package[package]["facts"].items() if item["basis"] == "open"]
        if not open_items:
            continue
        estimate = ESTIMATES.get(package, "1-4 h: inspect the package-specific metadata named below.")
        for field, item in open_items:
            lines.append(f"- `{package}.{field}`: {item['note']} To close: {estimate}")
    overlap = by_package["evbattery"].get("overlap_identifiers", {}).get("value")
    lines.extend(["", "## Cross-package overlap", "", f"EVBattery and Zhang2023 share **{overlap} vehicles**: zhang2023 brand 2 and evbattery dataset 3 are one fleet under different vehicle numbers. The overlap is tested by content (identical snippets) by `scripts/facts/_overlap_scan.py`; see `reports/facts/_cache/zhang2023_evbattery_overlap.json`.", ""])
    AUDIT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {FACTS.relative_to(ROOT)} ({len(rows)} rows)")
    print(f"wrote {AUDIT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
