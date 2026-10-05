"""Build headline Markdown and descriptor JSON from long-form package facts."""
from __future__ import annotations

import csv
import importlib.util
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fielddata.registry import PACKAGES

FACTS = ROOT / "fielddata" / "package_facts.csv"
VERIFY = ROOT / "reports" / "verify_log_ssd_2026-09.csv"
OUTPUT = ROOT / "reports" / "TOTALS.md"
JSON_OUTPUT = ROOT / "reports" / "totals.json"
BASES = ("measured", "stated", "derived", "not_in_release", "open")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate(rows: list[dict[str, str]]) -> None:
    required = {"package", "field", "value", "basis", "source", "note"}
    if not rows or set(rows[0]) != required:
        raise ValueError("package_facts.csv has the wrong columns")
    if len(rows) != 22 * 14:
        raise ValueError("package_facts.csv must contain 14 facts for each of 22 packages")
    if {row["package"] for row in rows} != set(PACKAGES):
        raise ValueError("package_facts.csv packages do not match registry")
    if any(row["basis"] not in {"measured", "stated", "derived", "not_in_release", "open"} for row in rows):
        raise ValueError("invalid fact basis")


def indexed(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    result: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        result[row["package"]][row["field"]] = row
    return result


def numeric(row: dict[str, str]) -> Decimal | None:
    return Decimal(row["value"]) if row["value"] else None


def coverage(rows: list[dict[str, str]]) -> str:
    counts = Counter(row["basis"] for row in rows)
    return ", ".join(f"{basis} {counts[basis]}" for basis in BASES)


def packages(rows: list[dict[str, str]]) -> str:
    return ", ".join(sorted(row["package"] for row in rows if row["value"]))


def total(rows: list[dict[str, str]]) -> Decimal:
    return sum((numeric(row) for row in rows if numeric(row) is not None), Decimal(0))


def fmt(value: Decimal, places: int = 0) -> str:
    return f"{value:,.{places}f}"


def source_fingerprint() -> str:
    """A content hash of the committed inputs. Unlike a run date or a commit id, it is known before committing and is
    identical for any two runs on the same inputs, on any day or machine (line endings normalized)."""
    import hashlib
    digest = hashlib.sha256()
    for name in ("fielddata/package_facts.csv", "reports/verify_log_ssd_2026-09.csv"):
        digest.update((ROOT / name).read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()[:12]


def license_summary() -> str:
    grouped: dict[str, list[str]] = defaultdict(list)
    for package, entry in PACKAGES.items():
        grouped[entry["license"]].append(package)
    return "\n".join(f"{license}: {', '.join(sorted(grouped[license]))}" for license in sorted(grouped))


def loader_packages() -> list[str]:
    return sorted(package for package in PACKAGES if importlib.util.find_spec(f"fielddata.loaders.{package.replace('-', '_')}") is not None)


def verification_counts(rows: list[dict[str, str]]) -> tuple[int, int, int, int, int]:
    physical_rows = [row for row in rows if " :: " not in row["file"] and row["file"] != "<package>" and not row["status"].lower().startswith("missing")]
    member_rows = [row for row in rows if " :: " in row["file"]]
    physical = {(row["package"], row["file"]) for row in physical_rows}
    referenced_files = {(row["package"], row["file"]) for row in physical_rows if row["expected"]}
    referenced_members = {(row["package"], row["file"]) for row in member_rows if row["expected"]}
    matches_files = sum(row["status"].lower() == "match" for row in physical_rows)
    matches_members = sum(row["status"].lower() == "match" for row in member_rows)
    return len(physical), len(referenced_files), len(referenced_members), matches_files, matches_members


# Releases whose units belong to more than one service class: units per class.
# zhou2026: two NMC passenger cars and one LFP bus (doi:10.1038/s41560-026-02131-5, Supplementary Table 1, p. 16).
MIXED_CLASSES = {"zhou2026": {"passenger EV": 2, "bus": 1}}


def build() -> tuple[str, dict]:
    rows = read_csv(FACTS)
    verify = read_csv(VERIFY)
    validate(rows)
    facts = indexed(rows)
    overlap = int(json.loads((ROOT / "reports" / "facts" / "evbattery.json").read_text(encoding="utf-8"))["overlap_identifiers"]["value"])

    units = [facts[p]["units_released"] for p in sorted(facts)]
    bilfinger_overlap = int(json.loads((ROOT / "reports" / "facts" / "bilfinger2026.json").read_text(encoding="utf-8")).get("overlap_identifiers", {}).get("value") or 0)
    bilfinger_facts = json.loads((ROOT / "reports" / "facts" / "bilfinger2026.json").read_text(encoding="utf-8"))
    # bilfinger2026's row counts all seven vehicles; two are also in bilfinger2024, so totals subtract them once
    bilfinger_dup = {key: Decimal(str(bilfinger_facts.get(f"overlap_{key}", {}).get("value") or 0))
                     for key in ["cells_liion", "cell_channels_measured", "energy_mwh", "span_unit_years"]}
    m5bat_overlap = int(json.loads((ROOT / "reports" / "facts" / "m5bat-2023-04.json").read_text(encoding="utf-8")).get("overlap_identifiers", {}).get("value") or 0)
    units_total = total(units) - Decimal(overlap) - Decimal(bilfinger_overlap) - Decimal(m5bat_overlap)
    application_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for package in sorted(facts):
        if package in MIXED_CLASSES:
            for application, count in MIXED_CLASSES[package].items():
                application_rows[application].append({**facts[package]["units_released"], "value": str(count)})
        else:
            application_rows[facts[package]["application"]["value"]].append(facts[package]["units_released"])

    cells_liion = [facts[p]["cells_liion"] for p in sorted(facts)]
    cells_leadacid = [facts[p]["cells_leadacid"] for p in sorted(facts)]
    channels = [facts[p]["cell_channels_measured"] for p in sorted(facts)]
    spans = [facts[p]["span_unit_years"] for p in sorted(facts)]
    hours = [facts[p]["obs_hours"] for p in sorted(facts)]
    sizes = [facts[p]["size_gb"] for p in sorted(facts)]
    files = [facts[p]["files"] for p in sorted(facts)]
    stated_energy = [facts[p]["energy_mwh"] for p in sorted(facts) if facts[p]["energy_basis"]["value"] == "stated"]
    computed_energy = [facts[p]["energy_mwh"] for p in sorted(facts) if facts[p]["energy_basis"]["value"] == "computed"]
    files_held, files_with_reference, members_with_reference, checksum_matches_files, checksum_matches_members = verification_counts(verify)
    loaders = loader_packages()
    sentinels_documented = sorted(package for package in facts if facts[package]["sentinels_documented"]["value"] == "yes")
    overlap_data = json.loads((ROOT / "reports" / "facts" / "_cache" / "zhang2023_evbattery_overlap.json").read_text(encoding="utf-8"))
    tolerance_n = sum(len(v.get("tolerance_matched", {})) for v in overlap_data["archive_pairs"].values())
    unmatched = overlap_data["overlap_vehicles_counted"] - overlap
    overlap_sentence = (f"Their vehicle numbers do not correspond, so the overlap was tested by content: {overlap_data['identical_snippets']:,} identical snippets "
                        f"confirm {overlap - tolerance_n} vehicles one-to-one between zhang2023 brand 2 and evbattery dataset 3, tolerance matching with agreeing "
                        f"charging-session numbers confirms the other {tolerance_n}, and no snippets are shared between any other archives. "
                        f"All {overlap} are counted once, by subtracting {overlap} from the package sum.")
    if unmatched > 0:
        overlap_sentence += f" The {unmatched} vehicles in each of those archives that could not be matched are counted as distinct."

    lines = [
        "# Headline totals", "",
        f"Generated by `scripts/rebuild.py` | inputs sha256 {source_fingerprint()} (fielddata/package_facts.csv, reports/verify_log_ssd_2026-09.csv)", "",
        "Stated and computed energy are listed separately and then summed. Counts in the final column describe package inputs, not data rows.", "",
        "## Headline", "",
        "| Measure | Value | Packages covered | Input status |",
        "|---|---:|---|---|",
    ]
    units_by_class = {}
    for application in sorted(application_rows):
        selected = application_rows[application]
        value = total(selected)
        note = ""
        if application == "passenger EV":
            value -= Decimal(overlap) + Decimal(bilfinger_overlap)
            note = "; overlap adjustments (EVBattery/Zhang, bilfinger2024/2026) measured 2"
        if application == "grid-scale storage":
            value -= Decimal(m5bat_overlap)
            note = "; overlap adjustment (m5bat-2023-04 Pb1 is m5bat-pbacid) derived 1"
        units_by_class[application] = float(value)
        lines.append(f"| Released units: {application} | {fmt(value)} | {packages(selected)} | {coverage(selected)}{note} |")
    cells_total = total(cells_liion) - bilfinger_dup["cells_liion"]
    channels_total = total(channels) - bilfinger_dup["cell_channels_measured"]
    stated_total = total(stated_energy) - bilfinger_dup["energy_mwh"]
    spans_total = total(spans) - bilfinger_dup["span_unit_years"]
    adjusted = {"Li-ion cells": cells_total, "Measured cell channels": channels_total, "Energy (stated basis), MWh": stated_total,
                "Energy, all packages with a value, MWh": stated_total + total(computed_energy), "Released unit-years": spans_total}
    metrics = [
        ("Released units total", units_total, units, 0),
        ("Li-ion cells", total(cells_liion), cells_liion, 0),
        ("Lead-acid cells", total(cells_leadacid), cells_leadacid, 0),
        ("Measured cell channels", total(channels), channels, 0),
        ("Energy (stated basis), MWh", total(stated_energy), stated_energy, 5),
        ("Energy (computed basis), MWh", total(computed_energy), computed_energy, 5),
        ("Energy, all packages with a value, MWh", total(stated_energy) + total(computed_energy), stated_energy + computed_energy, 5),
        ("Released unit-years", total(spans), spans, 3),
        ("Observation-hours", total(hours), hours, 1),
        ("Held size, decimal GB", total(sizes), sizes, 3),
        ("Released files", total(files), files, 0),
    ]
    for label, value, selected, places in metrics:
        if label in adjusted:
            value = adjusted[label]
        lines.append(f"| {label} | {fmt(value, places)} | {packages(selected)} | {coverage(selected)} |")
    lines.append(f"| Files held and verified | {files_held:,} | all 22 packages | measured 22, stated 0, derived 0, open 0 |")
    lines.append(f"| Physical files with publisher-checksum references | {files_with_reference:,} | verification log | measured 1, stated 0, derived 0, not_in_release 0, open 0 |")
    lines.append(f"| Archive members with publisher-checksum references | {members_with_reference:,} | verification log | measured 1, stated 0, derived 0, not_in_release 0, open 0 |")
    lines.append(f"| Publisher-checksum matches: physical files | {checksum_matches_files:,} | verification log | measured 1, stated 0, derived 0, not_in_release 0, open 0 |")
    lines.append(f"| Publisher-checksum matches: archive members | {checksum_matches_members:,} | verification log | measured 1, stated 0, derived 0, not_in_release 0, open 0 |")
    lines.append(f"| Packages with documented sentinels | {len(sentinels_documented):,} | {', '.join(sentinels_documented)} | stated {len(sentinels_documented)} |")

    data = {
        "title_tail": "a curated and verifiable collection of 22 releases",
        "cells_liion": float(cells_total), "cells_liion_packages": packages(cells_liion),
        "cells_leadacid": float(total(cells_leadacid)), "cells_leadacid_packages": packages(cells_leadacid),
        "cell_channels": float(channels_total), "released_units_total": float(units_total),
        "energy_stated_mwh": float(stated_total), "energy_stated_packages": packages(stated_energy),
        "energy_computed_mwh": float(total(computed_energy)), "energy_computed_packages": packages(computed_energy),
        "energy_total_mwh": float(stated_total + total(computed_energy)),
        "energy_total_package_count": len(stated_energy) + len(computed_energy),
        "units_by_class": units_by_class,
        "unit_years": float(spans_total), "unit_years_packages": packages(spans),
        "obs_hours": float(total(hours)), "obs_hours_packages": packages(hours),
        "size_gb": float(total(sizes)), "files_held": files_held, "files_released": float(total(files)),
        "files_with_reference": files_with_reference,
        "members_with_reference": members_with_reference,
        "checksum_matches_files": checksum_matches_files,
        "checksum_matches_members": checksum_matches_members,
        "sentinels_documented_count": len(sentinels_documented),
        "sentinels_documented_packages": sentinels_documented,
        "zhang_evbattery_overlap": overlap, "bilfinger_overlap": bilfinger_overlap, "m5bat_overlap": m5bat_overlap, "loader_count": len(loaders),
        "zhang_evbattery_overlap_sentence": overlap_sentence,
        "loader_packages": ", ".join(loaders), "license_summary": license_summary(),
    }
    return "\n".join(lines) + "\n", data


def main() -> None:
    markdown, data = build()
    OUTPUT.write_text(markdown, encoding="utf-8")
    JSON_OUTPUT.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    print(f"wrote {JSON_OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
