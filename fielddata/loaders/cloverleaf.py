"""Loader for the Cloverleaf second-life battery monitoring workbook (Zenodo 6373656)."""
from __future__ import annotations

import io
import zipfile

import pandas as pd

from fielddata.loaders._base import check_unit, directory, finish

_PACKAGE = "cloverleaf"
_ARCHIVE = "Monitoring data 2nd life battery.zip"
_WORKBOOK = "SNAM/export.xlsx"
# Row 1 of each sheet carries the signal names, row 2 the units; data start at row 3.
_PACK_COLUMNS = ["epoch_ms", "date", "SOH", "SOC", "Vcdif", "Vcavg", "Vcmax", "Vcmin", "Vpack", "Ipack"]


def _sheets():
    with zipfile.ZipFile(directory(_PACKAGE) / _ARCHIVE) as z:
        return pd.read_excel(io.BytesIO(z.read(_WORKBOOK)), sheet_name=None, header=None)


_TYPICAL_DAY = "typical day"


def systems():
    """One row per battery pack: the three HV pack sheets (20,000 s averages), each a unit in the totals.

    The workbook's fourth sheet, a typical day of the same system at 172 s averages, is not a battery and is not
    listed here. Load it with ``typical_day()`` or ``load("typical day")``.
    """
    rows = []
    for name, frame in _sheets().items():
        if name.startswith("SNAM HV"):
            rows.append({"unit": name, "kind": "pack", "averaging_note": str(frame.iloc[0, 1]), "rows": len(frame) - 3})
    return pd.DataFrame(rows)


def typical_day(clean=False):
    """The typical-day sheet: one day (2022-01-01) of the whole system at 172 s averages, with the pack columns."""
    return load(_TYPICAL_DAY, clean=clean)


def load(unit, clean=False):
    """Load one worksheet (a pack from ``systems()`` or "typical day"), indexed by its timestamp column, with the released signal names.

    Only the first ten columns (the time series) are returned; the side tables some sheets carry to the
    right (daily energy and round-trip efficiency summaries) are left out. ``clean`` has no effect.

    Every row is an average over the sheet's window (20,000 s or 172 s, row 1 of the sheet). The publisher defines
    no column: SOH and SOC are presumably BMS estimates; the sign of Ipack is not documented (in the data positive
    Ipack goes with rising SOC, so charging); the time zone of ``date`` is not stated (it equals epoch_ms as UTC on
    the pack sheets and UTC + 1 h on the typical-day sheet). See cloverleaf_SCHEMA.md.
    """
    sheets = _sheets()
    name = check_unit(unit, list(sheets), _PACKAGE)
    body = sheets[name].iloc[3:, :10].copy()
    body.columns = _PACK_COLUMNS
    body = body.dropna(subset=["date"])
    body["date"] = pd.to_datetime(body["date"])
    for column in _PACK_COLUMNS[2:] + ["epoch_ms"]:
        body[column] = pd.to_numeric(body[column], errors="coerce")
    body["unit"] = name
    body = body.set_index("date").sort_index(kind="stable")
    units = dict(zip(_PACK_COLUMNS, sheets[name].iloc[2, :10].tolist()))
    return finish(body, _PACKAGE, clean, 0, unit=name, units={k: v for k, v in units.items() if isinstance(v, str)})
