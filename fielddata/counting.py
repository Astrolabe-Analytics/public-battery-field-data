"""How many released units each package holds, counted from its loader's systems() table.

This is the single definition of a unit. scripts/facts uses it for units_released, so the facts table and
the loaders cannot disagree. A unit is one battery system in service: a vehicle, a stationary system, a
device. Laboratory reference cells, plant connection points and empty label rows are not units.
"""
from __future__ import annotations

import fielddata

RULES = {
    # package: (how to count, plain-language rule)
    "bilfinger2024": (lambda s: s["vehicle"].dropna().nunique(), "distinct vehicles among vehicle files"),
    "bilfinger2026": (lambda s: s["vehicle"].dropna().nunique(), "distinct vehicles among vehicle files"),
    "cao": (len, "one row per vehicle"),
    "changan": (len, "one RAR per vehicle"),
    "cloverleaf": (lambda s: int((s["kind"] == "pack").sum()), "one battery pack per pack sheet (each with its own serial number, inverter and state of health); the typical-day sheet is not a unit"),
    "deng": (len, "one archive per pack"),
    "evbattery": (lambda s: int((s["snippets"] > 0).sum()), "labeled vehicles with at least one snippet"),
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
}


def units(package: str) -> int:
    count, _ = RULES[package]
    return int(count(fielddata.systems(package)))


def rule(package: str) -> str:
    return RULES[package][1]
