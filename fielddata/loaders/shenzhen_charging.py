"""Loader for the Shenzhen public EV charging release (Yang, Tian, Mai and Chung, Mendeley Data 10.17632/c7gg94tmvz.3,
CC BY 4.0), the data of Yang et al., Nature Communications 17, 974 (2026). Candidate package: not in the totals.

Charging records from 30 public charging stations of Shenzhen Auto Electric Power Plant Co. (Autosun), one row per
minute of charging. There is no vehicle identifier, so each charging session (``transaction_id``) is its own unit
and one battery cannot be followed across sessions. Each session carries a fault label (``label``: 1 faulty,
0 normal) set from engineering reports or station over-temperature disconnections (Readme.txt).

Two workbooks, ``processed_data.xlsx`` (all sessions) and ``processed_data_longer_than_30.xlsx`` (sessions longer
than 30 minutes, a subset), with 8 sheets each. Sheet7 repeats sessions of Sheet1 (the same rows), see the schema.
The loader returns rows as released, with a ``sheet`` column, and changes no value. Reading a workbook takes about
two minutes. The rows are kept in memory for the rest of the session.

``systems(file)`` lists distinct sessions, and ``load(unit=None, file="processed_data")`` returns rows.
See ``shenzhen_charging_SCHEMA.md``.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from fielddata.loaders._base import as_list, check_unit, directory, finish

_PACKAGE = "shenzhen_charging"
FILES = {"processed_data": "processed_data.xlsx", "processed_data_longer_than_30": "processed_data_longer_than_30.xlsx"}
COLUMNS = ["id", "transaction_id", "begin_time", "end_time", "total_charging_kwh", "total_charging_min", "current_soc",
           "current_energy_meter_value", "chargingv", "charginga", "out_power", "charging_gun_temperature1",
           "charging_gun_temperature2", "types", "class_judge", "label"]
TYPES = {3: "LFP", 6: "NMC", 4: "LMO", 5: "LCO", 7: "LP"}  # Readme.txt: "03: LFP, 06: NMC, 04: LMO, 05: LCO, 07: LP"


@lru_cache(maxsize=2)
def _rows(file: str) -> pd.DataFrame:
    if file not in FILES:
        raise ValueError(f"{_PACKAGE}: file must be one of {list(FILES)}")
    sheets = pd.read_excel(directory(_PACKAGE) / FILES[file], sheet_name=None, engine="openpyxl")
    frame = pd.concat([part.assign(sheet=name) for name, part in sheets.items()], ignore_index=True)
    frame["transaction_id"] = frame["transaction_id"].astype(str)  # 32-digit ids, kept as text
    return frame[["sheet", *COLUMNS]]


def systems(file: str = "processed_data") -> pd.DataFrame:
    """One row per distinct charging session: sheets it appears in, rows (in its first sheet), battery type code,
    owner code (``class_judge``), fault label, and begin and last end time."""
    rows = _rows(file)
    first = rows.drop_duplicates(subset=["transaction_id", "id"])
    out = first.groupby("transaction_id", sort=False).agg(
        rows=("id", "size"), types=("types", "first"), class_judge=("class_judge", "first"), label=("label", "max"),
        begin=("begin_time", "first"), end=("end_time", "max")).reset_index()
    sheets = rows[["transaction_id", "sheet"]].drop_duplicates().groupby("transaction_id", sort=False)["sheet"].agg(",".join)
    out.insert(1, "sheets", sheets.loc[out["transaction_id"]].values)
    out.insert(0, "unit", out["transaction_id"])
    out["chemistry"] = out["types"].map(TYPES)
    return out


def load(unit=None, file: str = "processed_data", clean=False):
    """Rows as released: all sessions, or the named transaction_id(s). Rows of sessions that appear in two sheets
    are returned twice, once per sheet, as released. ``clean`` masks nothing."""
    rows = _rows(file)
    if unit is not None:
        units = [str(u) for u in as_list(unit, [])]
        known = set(rows["transaction_id"])
        for u in units:
            check_unit(u, known if u in known else [], _PACKAGE)
        rows = rows[rows["transaction_id"].isin(units)]
    return finish(rows.reset_index(drop=True), _PACKAGE, clean, 0, file=file)
