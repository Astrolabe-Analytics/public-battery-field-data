"""Check the facts, Table 3 and the totals against the counting decisions in docs/DECISIONS.md.

What it does:
  1. For every overlap pair in the ledger, the shared units, cells, faults, energy and observation time count only under
     the home release: the other release's row is net of them, or its overlap_* facts are what totals subtract.
  2. reports/totals.json matches the ledger's "Headline numbers" block (units, Li-ion cells, faults, observation-hours,
     energy). A change to a headline number needs the ledger entry and that block updated in the same commit.
  3. Every note in fielddata/package_facts.csv that names another release is consistent with the ledger: in a counting
     field it names the home release of a ledger overlap; elsewhere it is listed in the ledger's mentions-not-overlap.

Reads: docs/DECISIONS.md, fielddata/package_facts.csv, reports/facts/*.json, reports/facts/_cache/*.json,
docs/descriptor/TABLE3_faults.md, reports/totals.json. Writes nothing.

Run:
    python scripts/checks/test_decisions.py     # exit status 1 and a list of failures if any check fails
Also collected by pytest, and run by scripts/rebuild.py. Without docs/DECISIONS.md (the public export leaves it out) it
skips with a short message and exit status 0.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fielddata import counting  # noqa: E402
from fielddata.registry import PACKAGES  # noqa: E402

COUNTING_FIELDS = {"units_released", "cells_liion", "cells_leadacid", "cell_channels_measured", "energy_mwh", "span_unit_years", "obs_hours"}


def ledger() -> dict:
    text = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    blocks = {name: json.loads(body) for name, body in re.findall(r"<!-- ([a-z-]+)\n(.*?)\n-->", text, re.S)}
    return {"headline": blocks["headline-numbers"], "overlaps": blocks["overlaps"], "mentions": blocks["mentions-not-overlap"]}


def facts_csv() -> dict:
    rows = {}
    with (ROOT / "fielddata" / "package_facts.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[(r["package"], r["field"])] = r
    return rows


def facts_json(package: str) -> dict:
    return json.loads((ROOT / "reports" / "facts" / f"{package}.json").read_text(encoding="utf-8"))


def num(value):
    return None if value in ("", None) else float(value)


def table3() -> dict:
    section = (ROOT / "docs" / "descriptor" / "TABLE3_faults.md").read_text(encoding="utf-8").split("## Fault count", 1)[1]
    rows = {}
    for line in section.splitlines():
        cells = [c.strip().strip("*") for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[1].replace(",", "").isdigit():
            rows[cells[0]] = {"faults": int(cells[1].replace(",", "")), "batteries": cells[2], "basis": cells[3]}
    return rows


def check_overlaps(led, rows, t3) -> list[str]:
    bad = []

    def fail(oid, msg):
        bad.append(f"{oid}: {msg}")

    def note(package, field):
        r = rows[(package, field)]
        return r["source"] + " " + r["note"]

    ids = {o["id"] for o in led["overlaps"]}
    if ids != {"O1", "O2", "O3", "O4", "O5", "O6"}:
        fail("ledger", f"expected overlaps O1 to O6, found {sorted(ids)}")
    units = {p: num(rows[(p, "units_released")]["value"]) for p in PACKAGES}

    # O1 zhang2023 / evbattery: evbattery row net of the 49, hours over datasets 1 and 2 only, faults net of the 16
    ev = facts_json("evbattery")
    if units["evbattery"] != ev["units_gross"]["value"] - 49:
        fail("O1", f"evbattery units {units['evbattery']} is not its gross {ev['units_gross']['value']} less 49")
    if "units_gross" in facts_json("zhang2023"):
        fail("O1", "zhang2023 is the home release and must not carry a gross count")
    cache = ROOT / "reports" / "facts" / "_cache"
    kept = [json.loads((cache / f"evbattery__battery_dataset{i}.tar.gz.json").read_text(encoding="utf-8")) for i in (1, 2)]
    hours = sum(k["observation_seconds_union"] for k in kept) / 3600
    if abs(num(rows[("evbattery", "obs_hours")]["value"]) - hours) > 0.5:
        fail("O1", f"evbattery obs_hours {rows[('evbattery', 'obs_hours')]['value']} is not datasets 1 and 2 only ({hours:.1f} h)")
    if sum(k["vehicles"] for k in kept) != units["evbattery"]:
        fail("O1", "evbattery's hours do not cover exactly its counted (unshared) vehicles")
    if "battery_dataset3" not in note("evbattery", "obs_hours") or "zhang2023" not in note("evbattery", "obs_hours"):
        fail("O1", "evbattery obs_hours note does not say dataset 3 is left out for zhang2023")
    if t3.get("evbattery", {}).get("faults") != 32 or "16" not in t3.get("evbattery", {}).get("basis", ""):
        fail("O1", "Table 3 evbattery must count 48 abnormal less the 16 shared (32)")
    for field in ("cells_liion", "energy_mwh"):
        if num(rows[("evbattery", field)]["value"]) is not None:
            fail("O1", f"evbattery {field} is set; the ledger says no cells or energy for the shared fleet")

    # O2 bilfinger2024 / bilfinger2026: overlap_* facts on bilfinger2026
    b26 = facts_json("bilfinger2026")
    o2 = next(o for o in led["overlaps"] if o["id"] == "O2")
    if b26.get("overlap_identifiers", {}).get("value") != o2["shared_units"]:
        fail("O2", "bilfinger2026 overlap_identifiers does not match the ledger")
    if b26.get("overlap_cells_liion", {}).get("value") != o2["cells"]:
        fail("O2", "bilfinger2026 overlap_cells_liion does not match the ledger")
    if abs((b26.get("overlap_energy_mwh", {}).get("value") or 0) - o2["energy_mwh"]) > 1e-9:
        fail("O2", "bilfinger2026 overlap_energy_mwh does not match the ledger")
    if "bilfinger2026" in t3:
        fail("O2", "bilfinger2026 has a Table 3 row; the shared vehicles have no faults")

    # O3 bilfinger2024 and 2026 / bilfinger2025: row holds only the new vehicles
    b25 = facts_json("bilfinger2025")
    if units["bilfinger2025"] != b25["units_gross"]["value"] - 7 or len(counting.BILFINGER_HELD) != 7:
        fail("O3", f"bilfinger2025 units {units['bilfinger2025']} is not its gross {b25['units_gross']['value']} less the 7 held vehicles")
    if num(rows[("bilfinger2025", "cells_liion")]["value"]) != 9840 or abs(num(rows[("bilfinger2025", "energy_mwh")]["value"]) - 0.3726) > 1e-9:
        fail("O3", "bilfinger2025 cells or energy are not those of its 5 new vehicles (9,840 cells, 0.3726 MWh)")
    if any(k.startswith("overlap_") for k in b25):
        fail("O3", "bilfinger2025 carries overlap_* facts; its row is already net")
    if "bilfinger2025" in t3 and "second VW ID.3" not in t3["bilfinger2025"]["basis"]:
        fail("O3", "bilfinger2025's fault must be the second (new) VW ID.3")

    # O4 m5bat-pbacid / m5bat-2023-04
    m = facts_json("m5bat-2023-04")
    if m.get("overlap_identifiers", {}).get("value") != 1:
        fail("O4", "m5bat-2023-04 overlap_identifiers is not 1 (Pb1)")
    if "Pb1" not in note("m5bat-2023-04", "cells_leadacid") or "m5bat-pbacid" not in note("m5bat-2023-04", "cells_leadacid"):
        fail("O4", "m5bat-2023-04 lead-acid cells note does not leave Pb1 to m5bat-pbacid")
    if abs(num(rows[("m5bat-2023-04", "energy_mwh")]["value"]) - (7.78 - 1.066)) > 1e-6:
        fail("O4", "m5bat-2023-04 energy is not the plant rating less Pb1's 1.066 MWh")
    if abs(num(rows[("m5bat-2023-04", "span_unit_years")]["value"]) * 365.25 / 30 - (units["m5bat-2023-04"] - 1)) > 0.01:
        fail("O4", "m5bat-2023-04 time does not cover exactly its units other than Pb1 (30 days each)")
    if "m5bat-2023-04" in t3 or t3.get("m5bat-pbacid", {}).get("faults") != 1:
        fail("O4", "Pb1's fault must count only under m5bat-pbacid")

    # O5 ppl / pnnl_epri
    pn = facts_json("pnnl_epri")
    if units["pnnl_epri"] != pn["units_gross"]["value"] - 1:
        fail("O5", "pnnl_epri units is not its gross less EPRI_NMC2")
    if "EPRI_NMC2" not in note("pnnl_epri", "energy_mwh") or "304 days" not in note("pnnl_epri", "span_unit_years"):
        fail("O5", "pnnl_epri energy or span note does not leave EPRI_NMC2 to ppl")
    if num(rows[("pnnl_epri", "cells_liion")]["value"]) is not None or "pnnl_epri" in t3:
        fail("O5", "pnnl_epri has cells or faults; the ledger has none")

    # O6 tumftm / tum_id3_2022
    t = facts_json("tum_id3_2022")
    if units["tum_id3_2022"] != 0 or t.get("overlap_cells_liion", {}).get("value") != num(rows[("tum_id3_2022", "cells_liion")]["value"]):
        fail("O6", "tum_id3_2022 must count 0 units and subtract all its cells")
    if num(rows[("tum_id3_2022", "energy_mwh")]["value"]) is not None or num(rows[("tum_id3_2022", "span_unit_years")]["value"]) != 0:
        fail("O6", "tum_id3_2022 must add no energy and no time")
    if "tum_id3_2022" in t3:
        fail("O6", "tum_id3_2022 has a Table 3 row")
    return bad


def check_totals(led, rows) -> list[str]:
    bad = []
    totals = json.loads((ROOT / "reports" / "totals.json").read_text(encoding="utf-8"))
    head = led["headline"]
    checks = [("released_units_total", 0), ("cells_liion", 0), ("faults", 0), ("obs_hours", 0), ("energy_total_mwh", 1),
              ("energy_stated_mwh", 2), ("energy_computed_mwh", 2)]
    for key, places in checks:
        got = round(float(totals[key]), places)
        if got != round(float(head[key]), places):
            bad.append(f"totals: {key} is {got:,} in reports/totals.json but {head[key]:,} in docs/DECISIONS.md")
    # every total is net: the totals equal the row sums less the overlap_* facts the ledger names
    units = sum(num(rows[(p, "units_released")]["value"]) or 0 for p in PACKAGES)
    sub = sum(facts_json(p).get("overlap_identifiers", {}).get("value") or 0 for p in ("bilfinger2026", "m5bat-2023-04"))
    if units - sub != totals["released_units_total"]:
        bad.append(f"totals: units {totals['released_units_total']} is not the row sum {units:.0f} less {sub} (bilfinger2026, m5bat-2023-04)")
    cells = sum(num(rows[(p, "cells_liion")]["value"]) or 0 for p in PACKAGES)
    dup = sum(o.get("cells", 0) for o in led["overlaps"])
    if cells - dup != totals["cells_liion"]:
        bad.append(f"totals: Li-ion cells {totals['cells_liion']:.0f} is not the row sum {cells:.0f} less the ledger's {dup} shared cells")
    return bad


def check_mentions(led, rows) -> list[str]:
    bad = []
    homes = {(o["other"], o["home"]) for o in led["overlaps"]}
    allowed = {tuple(m) for m in led["mentions"]}
    names = sorted(PACKAGES, key=len, reverse=True)
    for (package, field), r in rows.items():
        text = r["note"] + " " + r["source"]
        for other in names:
            if other == package or not re.search(r"(?<![\w-])" + re.escape(other) + r"(?![\w-])", text):
                continue
            if field in COUNTING_FIELDS:
                if (package, other) not in homes:
                    bad.append(f"mentions: {package} {field} names {other}, but the ledger has no overlap with {other} as home of {package}'s units")
            elif (package, other, field) not in allowed and (package, other) not in homes:
                bad.append(f"mentions: {package} {field} names {other}, not listed in the ledger")
    return bad


def failures() -> list[str]:
    led, rows = ledger(), facts_csv()
    return check_overlaps(led, rows, table3()) + check_totals(led, rows) + check_mentions(led, rows)


LEDGER = ROOT / "docs" / "DECISIONS.md"
SKIP = "docs/DECISIONS.md not present (the ledger is private and left out of the public export); decisions checks skipped."


def test_decisions():
    if not LEDGER.exists():
        import pytest
        pytest.skip(SKIP)
    found = failures()
    assert not found, "decisions ledger checks failed:\n" + "\n".join(found)


def main() -> int:
    if not LEDGER.exists():
        print(SKIP)
        return 0
    found = failures()
    if found:
        print("DECISIONS CHECK FAILED (docs/DECISIONS.md):", file=sys.stderr)
        for line in found:
            print("  - " + line, file=sys.stderr)
        return 1
    led = ledger()
    print(f"decisions ledger checks passed: {len({o['id'] for o in led['overlaps']})} overlaps, headline numbers, facts-note mentions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
