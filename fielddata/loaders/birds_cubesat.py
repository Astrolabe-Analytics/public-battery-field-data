"""Loader for the BIRDS CubeSat electrical power system release (Jara and Lepcha, Mendeley Data 10.17632/8kp25ycf63.1,
CC BY 4.0), described in Jara et al., Data in Brief 45, 108697 (2022). Candidate package: not in the totals.

Four 1U CubeSats of the BIRDS constellation (NEPALISAT, RAAVANA, TSURU, UGUISU), released from the ISS. Each has a
battery of six NiMH cells, 3 in series and 2 in parallel (paper Section 2 and Table 2). The release is one workbook per
satellite and one sheet per high-sampling data collection over one orbit, named for its download date. Every sheet has
the same 37 columns in the same order, with small spelling differences in the headers ("Time Stamp" or "Time stamp",
"Tbatt raw)"), so the loader names the columns by position (COLUMNS) and changes no value. TSURU also has two sheets
named "Test1 w batt" and "Test2 wo batt" that are not dated downloads.

``systems()`` lists the four satellites, ``sheets()`` lists every sheet, and ``load(unit, sheet=None)`` returns one
satellite's sheets as released with a ``sheet`` column. See ``birds_cubesat_SCHEMA.md``.
"""
from __future__ import annotations

import re

import pandas as pd

from fielddata.loaders._base import as_list, check_unit, concat, directory, finish

_PACKAGE = "birds_cubesat"
UNITS = ["NEPALISAT", "RAAVANA", "TSURU", "UGUISU"]
PANELS = ["py", "px", "mz", "mx", "pz"]
COLUMNS = (["time_s"] + [f"T{p}_{k}" for p in PANELS for k in ("raw", "C")] + [f"V{p}_{k}" for p in PANELS for k in ("raw", "mV")]
           + [f"I{p}_{k}" for p in PANELS for k in ("raw", "mA")] + ["Vbat_raw", "Vbat_V", "Ibatt_raw", "Ibatt_mA", "Tbatt_raw", "Tbatt_C"])
BATTERY = {"chemistry": "NiMH", "cells": "6 (3 series, 2 parallel)", "cell_rated_mAh": 2000, "cell_nominal_V": 1.2,
           "pack_nominal_Wh": 14.4, "source": "Jara et al. 2022, Section 2 and Table 2 (Eneloop BK-3MCCE): 3 x 1.2 V x 2 x 2.0 Ah"}
_MONTHS = "January February March April May June July August September October November December".split()


def _path(unit: str):
    return directory(_PACKAGE) / f"{unit}.xlsx"


def _date(unit: str, sheet: str):
    """Download date from the sheet name. TSURU's sheets from March to December name no year: 2021 (the January
    sheets that follow say 2022). Test sheets have no date."""
    words = sheet.replace(",", " ").split()
    month = next((i + 1 for i, m in enumerate(_MONTHS) for w in words if w.lower().startswith(m[:3].lower()) and w.isalpha()), None)
    numbers = [int(w) for w in words if w.isdigit()]
    if month is None or not numbers:
        return pd.NaT
    day = next(n for n in numbers if n <= 31)
    year = next((n for n in numbers if n > 1900), 2021)
    return pd.Timestamp(year, month, day)


def sheets() -> pd.DataFrame:
    """One row per sheet: satellite, sheet name, download date, kind (download or test), rows and time span (s)."""
    rows = []
    for unit in UNITS:
        book = pd.ExcelFile(_path(unit))
        for sheet in book.sheet_names:
            frame = book.parse(sheet)
            seconds = pd.to_numeric(frame.iloc[:, 0], errors="coerce")
            date = _date(unit, sheet)
            rows.append({"unit": unit, "sheet": sheet, "date": date, "kind": "test" if re.match(r"test", sheet, re.I) else "download",
                         "rows": len(frame), "span_s": float(seconds.max() - seconds.min()) if len(frame) else 0.0,
                         "median_step_s": float(seconds.diff().median()) if len(frame) > 1 else None})
    return pd.DataFrame(rows)


def systems() -> pd.DataFrame:
    """One row per satellite: downloads, test sheets, rows, first and last download date, and the battery as stated."""
    table = sheets()
    rows = []
    for unit in UNITS:
        part = table[table["unit"] == unit]
        downloads = part[part["kind"] == "download"]
        rows.append({"unit": unit, "downloads": len(downloads), "test_sheets": int((part["kind"] == "test").sum()),
                     "rows": int(part["rows"].sum()), "first": downloads["date"].min(), "last": downloads["date"].max(),
                     "observed_hours": downloads["span_s"].sum() / 3600, **BATTERY})
    return pd.DataFrame(rows)


def load(unit=None, sheet=None, clean=False):
    """Load one satellite's sheets (all, or the named ones) as released, columns named by position (COLUMNS).

    ``clean`` masks nothing: no sentinel code is known.
    """
    units = as_list(unit, UNITS)
    frames = []
    for u in units:
        u = check_unit(u, UNITS, _PACKAGE)
        book = pd.ExcelFile(_path(u))
        names = book.sheet_names if sheet is None else as_list(sheet, [])
        parts = []
        for name in names:
            part = book.parse(name)
            part.columns = COLUMNS
            part.insert(0, "sheet", name)
            parts.append(part)
        frame = pd.concat(parts, ignore_index=True)
        if len(units) > 1:
            frame.insert(0, "unit", u)
        frames.append(finish(frame, _PACKAGE, clean, 0, unit=u))
    return concat(frames, _PACKAGE, clean)
