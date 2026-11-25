"""What changed from v1.2 to v1.3, for the descriptor update.

What it does: compares reports/totals.json as committed on main before the v1.3 admission (git revision given by
V12_REF) with the current reports/totals.json, and lists every headline number that changed, old and new. It then
copies the new rows of Tables 1, 2 and 3 for li2026_evfault and giu_ebike from the generated table files, and adds
the judgement calls made in the admission.
Reads: reports/totals.json (current and at V12_REF through git), docs/descriptor/TABLE1_sources.md, TABLE2_packages.md,
TABLE3_faults.md. Writes: reports/V13_CHANGES.md.

Run: python scripts/checks/v13_changes.py
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V12_REF = "b05cbdc"  # main before the v1.3 admission (v1.3 intake status note, 2026-11-20)
NEW = ["li2026_evfault", "giu_ebike"]
KEYS = [
    ("loader_count", "Releases", 0), ("released_units_total", "Batteries (units)", 0), ("cells_liion", "Li-ion cells", 0),
    ("cell_channels", "Cell-voltage channels", 0), ("faults", "Faults (Table 3)", 0), ("fault_batteries", "Batteries with a fault", 0),
    ("faults_in_batteries", "Faults in identified batteries", 0), ("charging_fault_labels", "Charging sessions labelled faulty (not counted as faults in v1.3)", 0),
    ("voltage_snapshot_fault_labels", "Voltage snapshots with a labelled cell (not counted as faults)", 0), ("energy_total_mwh", "Energy (MWh)", 2),
    ("energy_stated_mwh", "Energy stated (MWh)", 2), ("energy_computed_mwh", "Energy computed (MWh)", 4),
    ("unit_years", "Unit-years", 1), ("obs_hours", "Observation-hours", 0), ("research_groups", "Research groups", 0),
    ("size_gb", "Data held (GB)", 2), ("files_held", "Files held and verified", 0),
    ("checksum_matches_files", "Publisher-checksum matches: files", 0), ("checksum_matches_members", "Publisher-checksum matches: archive members", 0),
]


def fmt(value, places: int) -> str:
    if value is None:
        return "-"
    return f"{value:,.{places}f}"


def rows_for(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("|") and any(f"| {name} |" in line for name in NEW)]


def main() -> None:
    old = json.loads(subprocess.run(["git", "show", f"{V12_REF}:reports/totals.json"], cwd=ROOT, capture_output=True, text=True,
                                    encoding="utf-8", check=True).stdout)
    new = json.loads((ROOT / "reports" / "totals.json").read_text(encoding="utf-8"))
    lines = ["# v1.3 changes from v1.2", "",
             f"Made by `scripts/checks/v13_changes.py`, comparing `reports/totals.json` at `{V12_REF}` (v1.2 plus the v1.3 intake as candidates) with the current file. "
             "Two releases join: li2026_evfault and giu_ebike. lin_agv stays a candidate until its paper is out.", "",
             "## Headline numbers", "", "| Measure | v1.2 | v1.3 | Change |", "|---|---:|---:|---:|"]
    for key, label, places in KEYS:
        a, b = old.get(key), new.get(key)
        if a is None and b is None:
            continue
        change = "new" if a is None else fmt(b - a, places) if b != a else "0"
        if a is not None and b is not None and b - a > 0:
            change = "+" + change
        lines.append(f"| {label} | {fmt(a, places)} | {fmt(b, places)} | {change} |")
    a, b = old.get("units_by_class", {}), new.get("units_by_class", {})
    lines += ["", "Units by class:", ""]
    for cls in sorted(set(a) | set(b)):
        if a.get(cls) != b.get(cls):
            lines.append(f"- {cls}: {fmt(a.get(cls), 0)} to {fmt(b.get(cls), 0)}")
    for name, path in [("Table 1 (sources)", "docs/descriptor/TABLE1_sources.md"), ("Table 2 (packages)", "docs/descriptor/TABLE2_packages.md"),
                       ("Table 3 (faults)", "docs/descriptor/TABLE3_faults.md")]:
        lines += ["", f"## New rows in {name}", "", f"From `{path}`.", ""] + rows_for(ROOT / path)
    lines += ["", "## Judgement calls to check before the descriptor update", "",
              "- li2026_evfault units and cells are stated, not measured: the release has no vehicle identifiers (ledger V1).",
              "- Fault count definition changed (ledger S1, maintainer, 2026-11-24): shenzhen_charging's 5,680 charging sessions labelled faulty are no longer counted as battery faults. They were 5,680 of v1.2's 6,465. The descriptor should say so, so readers comparing versions are not confused.",
              "- li2026_evfault faults are the paper's vehicle-level counts (Fig. 1D): 171, once per vehicle and fault type, in 87 vehicles. A label can change between fault types as a fault evolves (paper, Supplementary Note 1), so 171 may count one faulty cell under two types; per battery it would be 87 (ledger V1).",
              "- Research groups: li2026_evfault is taken to add no group (its corresponding authors are at RWTH ISEA and Chongqing University, taken as the group of deng and cell_to_pack). giu_ebike adds German International University (Egypt).",
              "- giu_ebike has no paper. Its README names one that was not found in print on 2026-11-20. Its chemistry is inferred (NMC-class) and its energy computed (48 V x 9.44 Ah).",
              "- The repository's docs/descriptor/DESCRIPTOR.md is a v1.1-era template (twenty-three releases). The rebuild refreshed only its filled numbers (DESCRIPTOR_filled.md). The v1.2 Word descriptor is the text to update."]
    (ROOT / "reports" / "V13_CHANGES.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[:40]))


if __name__ == "__main__":
    main()
