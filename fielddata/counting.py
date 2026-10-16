"""How many released units each package holds, counted from its loader's systems() table.

This is the single definition of a unit. scripts/facts uses it for units_released, so the facts table and
the loaders cannot disagree. A unit is one battery system in service: a vehicle, a stationary system, a
device. Laboratory reference cells, plant connection points and empty label rows are not units.

Shared units and cells (dedup rule, maintainer, 2026-10-16): every battery, and every cell, that is physically the same as one in
another release is counted once in the totals, under one home release. The other release's row either leaves it out
(its RULES count is net, and its gross count is in GROSS for display) or records it in an overlap_* fact that
scripts/totals.py subtracts. Time outside the home release's span still counts. As of 2026-10-16:
  - zhang2023 / evbattery: 49 shared vehicles, home zhang2023 (more snippets for them, 194,245 against 176,327, and the
    home of their fault labels); evbattery counts 415 of its 464. Neither release states cells.
  - bilfinger2024 / bilfinger2026: VW ID.3 and Tesla Model 3, home bilfinger2024; bilfinger2026 subtracts 322 cells,
    214 channels, 0.1105 MWh and their shared time (overlap_* facts).
  - bilfinger2024 and 2026 / bilfinger2025: 7 vehicles, home the earlier releases; bilfinger2025 counts only its 5 new
    vehicles and their 9,840 cells.
  - m5bat-pbacid / m5bat-2023-04: lead-acid string Pb1 (300 cells), home m5bat-pbacid; m5bat-2023-04 leaves Pb1 out of
    its 1,222 lead-acid cells and subtracts the unit.
  - ppl / pnnl_epri: EPRI_NMC2, home ppl; pnnl_epri counts 11 of 12 systems and states no cells.
  - tumftm / tum_id3_2022: ID1, home tumftm; tum_id3_2022 counts 0 units and subtracts its 216 cells (overlap_cells_liion),
    which tumftm's 7 x 216 already hold. Its 108 cell-voltage channels are new signals and stay.
"""
from __future__ import annotations

import fielddata

# bilfinger2025's vehicles already counted under bilfinger2024 or bilfinger2026 (names from fielddata.loaders._bilfinger.vehicle):
# the ID.3 and Model 3 recordings of 2021 to 2024 are identical to bilfinger2024's, and the Cupra Born carry the same
# licence-plate numbers as bilfinger2026's (scripts/checks/bilfinger2025_screen.py).
BILFINGER_HELD = {"VW ID.3", "Tesla Model 3 SR+", "Cupra 204", "Cupra 213", "Cupra 288", "Cupra 349", "Cupra 397"}

RULES = {
    # package: (how to count, plain-language rule)
    "bilfinger2024": (lambda s: s["vehicle"].dropna().nunique(), "distinct vehicles among vehicle files"),
    "bilfinger2026": (lambda s: s["vehicle"].dropna().nunique(), "distinct vehicles among vehicle files"),
    "bilfinger2025": (lambda s: len(set(s["vehicle"].dropna()) - BILFINGER_HELD), "distinct vehicles among vehicle files, less the VW ID.3, the Tesla Model 3 and the five Cupra Born already counted under bilfinger2024 and bilfinger2026 (maintainer, 2026-10-15)"),
    "cao": (len, "one row per vehicle"),
    "changan": (len, "one RAR per vehicle"),
    "cloverleaf": (lambda s: int((s["kind"] == "pack").sum()), "one battery pack per pack sheet (each with its own serial number, inverter and state of health); the typical-day sheet is not a unit"),
    "deng": (len, "one archive per pack"),
    "evbattery": (lambda s: int((s["snippets"] > 0).sum()) - int(((s["snippets"] > 0) & (s["archive"] == "battery_dataset3.tar.gz")).sum()),
                  "labeled vehicles with at least one snippet, less the 49 dataset 3 vehicles, which are zhang2023 brand 2 vehicles and count there (home release, maintainer, 2026-10-16)"),
    "fei_bus": (len, "one file per bus"),
    "flashbattery-agv": (len, "one row per pack"),
    "ku_leuven_bev": (len, "one row per vehicle"),
    "li2026": (lambda s: 1, "one series string: in each period the current is identical in all 30 eight-cell groups (scripts/checks/source_audit/li2026_xie_schaeffer_zhou2026/check_li2026_audit.py); the paper refers to stations in the plural and gives no count"),
    "m5bat-2023-04": (lambda s: int((s["kind"] == "battery unit").sum()), "battery units; the plant connection point is not a unit"),
    "m5bat-pbacid": (lambda s: 1, "one string; rows are its two data sources"),
    "ppl": (len, "one system"),
    "rwth-android": (len, "one file per device"),
    "rwth-home": (len, "one archive per system"),
    "schaeffer": (len, "one file per system"),
    "tsukuba": (len, "one building microgrid"),
    "tumftm": (len, "one file per vehicle"),
    "xie": (len, "one file per device"),
    "zhang2023": (lambda s: int((s["snippets"] > 0).sum()), "labeled vehicles with at least one snippet"),
    "zhou2026": (len, "one row per vin"),
    "aitio": (len, "one battery per .npz file"),
}


def units(package: str) -> int:
    count, _ = RULES[package]
    return int(count(fielddata.systems(package)))


def rule(package: str) -> str:
    return RULES[package][1]


# Display only (maintainer, 2026-10-16): tables and dashboards show each release's gross unit count, marked with a dagger
# where some of its units also appear in another release. The totals keep counting each unit once (RULES above and
# scripts/totals.py). GROSS holds the releases whose RULES count is net of shared units; for the others with a dagger the
# RULES count is already gross and the totals subtract the shared units.
GROSS = {
    "bilfinger2025": (lambda s: s["vehicle"].dropna().nunique(), "all 12 distinct vehicles, including the VW ID.3 and Tesla Model 3 of bilfinger2024 and the five Cupra Born of bilfinger2026"),
    "pnnl_epri": (lambda s: len(s), "all 12 systems, including EPRI_NMC2, which is ppl's system"),
    "tum_id3_2022": (lambda s: len(s), "its one vehicle, tumftm's ID1"),
    "evbattery": (lambda s: int((s["snippets"] > 0).sum()), "all 464 labeled vehicles with at least one snippet, including the 49 of dataset 3, which are zhang2023 brand 2 vehicles"),
}
SHARED = {  # release: which of its units also appear in another release (one plain sentence, shown under Table 2)
    "evbattery": "Its 49 dataset 3 vehicles are zhang2023 brand 2 vehicles.",
    "bilfinger2026": "Its VW ID.3 and Tesla Model 3 are the bilfinger2024 vehicles.",
    "bilfinger2025": "7 of its 12 vehicles are bilfinger2024 and bilfinger2026 vehicles.",
    "m5bat-2023-04": "Its lead-acid string Pb1 is the m5bat-pbacid string.",
    "pnnl_epri": "EPRI_NMC2 is the ppl system.",
    "tum_id3_2022": "Its vehicle is tumftm's ID1.",
}


def gross_units(package: str) -> int:
    count, _ = GROSS[package]
    return int(count(fielddata.systems(package)))


# Candidate packages (not in the totals): the unit rule each would be counted by if admitted. Decided by maintainer,
# 2026-10-13, for the v1.2 on-deck intake; scripts/checks/ondeck_deltas.py uses these for the proposed deltas.
CANDIDATE_RULES = {
    "pnnl_epri": (lambda s: len(s) - 1, "one per system, EPRI_NMC2 left out (it is the ppl E.W. Brown system, counted once, under ppl)"),
    "beijing_ev": (lambda s: s["vehicle"].nunique(), "one vehicle (the twelve files are days of the same car)"),
    "brazil_star": (lambda s: s["household"].nunique(), "one battery per household"),
    "birds_cubesat": (len, "one battery per satellite"),
    "ved": (lambda s: int((s["battery_signals"] | (s["VehId"] == 439)).sum()), "the 28 vehicles with battery signals: the 27 of the PHEV and EV workbook and vehicle 439, listed as an HEV but carrying battery signals (maintainer, 2026-10-13); the other 356 are held but not units"),
    "shenzhen_charging": (lambda s: 0, "no systems: its 31,449 charging sessions (no vehicle identifier) form a separate charging-sessions group (maintainer, 2026-10-13)"),
    "tongji_rest": (lambda s: int((s["kind"] == "field vehicle").sum()), "the field vehicles with raw segments; feature-only vehicles and laboratory cells are not units"),
    "rise_conbat": (len, "one distinct second-life module id (88); the record's 106 are installation rows, some modules installed twice"),
    "tum_id3_2022": (lambda s: 0, "the same vehicle as tumftm ID1, already counted there: its extra signals belong to that unit"),
    "cell_to_pack": (lambda s: int((s["kind"] == "field pack").sum()), "the 16 field packs; laboratory cells and packs are held but not units"),
    "stanford_ev": (lambda s: 1, "one vehicle"),
}


# v1.2: the admitted candidates are counted by the same rules as every other package
RULES.update(CANDIDATE_RULES)


def candidate_units(package: str) -> int:
    count, _ = CANDIDATE_RULES[package]
    return int(count(fielddata.systems(package)))


def candidate_rule(package: str) -> str:
    return CANDIDATE_RULES[package][1]
