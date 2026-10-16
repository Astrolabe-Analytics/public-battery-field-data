"""Loader for the Beijing battery electric vehicle release (He, Mendeley Data 10.17632/mm9rvfvmrb.3, CC BY 4.0), the
data of Wei, He, Li and Zhao, Journal of Energy Storage 49, 104091 (2022). Candidate package: not in the totals.

One car on public roads in Beijing, recorded on 12 days in 2018 and 2019. The release is one workbook per day in two
folders, ``2018/`` and ``2019/``, named ``<year>.<month>.<day>.xlsx``, each with the columns time, speed, mileage,
voltage, current and soc, one row about every 10 s. ``time`` is a yyyymmddHHMMSS integer and is returned as
released. The loader changes no value.

``systems()`` lists the 12 days (``unit`` is the day, ``vehicle`` is the one car), and ``load(unit=None)`` returns
one day or several as released. See ``beijing_ev_SCHEMA.md``.
"""
from __future__ import annotations

import re

import pandas as pd

from fielddata.loaders._base import as_list, check_unit, concat, directory, finish

_PACKAGE = "beijing_ev"
COLUMNS = ["time", "speed", "mileage", "voltage", "current", "soc"]


def _files() -> dict[str, object]:
    """Day (yyyy-mm-dd) -> workbook path, from the file names."""
    out = {}
    for path in sorted(directory(_PACKAGE).glob("20*/*.xlsx")):
        year, month, day = (int(x) for x in re.fullmatch(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", path.stem).groups())
        out[f"{year:04d}-{month:02d}-{day:02d}"] = path
    return dict(sorted(out.items()))


def _read(path) -> pd.DataFrame:
    return pd.read_excel(path, engine="openpyxl")


def _stamp(value) -> pd.Timestamp:
    return pd.to_datetime(str(int(value)), format="%Y%m%d%H%M%S")


def systems() -> pd.DataFrame:
    """One row per day: the day, the car, the file, its size and row count, and its first and last time."""
    rows = []
    for day, path in _files().items():
        frame = _read(path)
        rows.append({"unit": day, "vehicle": "BEV", "file": f"{path.parent.name}/{path.name}", "bytes": path.stat().st_size,
                     "rows": len(frame), "first": _stamp(frame["time"].min()), "last": _stamp(frame["time"].max()),
                     "mileage_first": int(frame["mileage"].iloc[0]), "mileage_last": int(frame["mileage"].iloc[-1])})
    return pd.DataFrame(rows)


def load(unit=None, clean=False):
    """Load one day (or a list of days) as released. ``clean`` masks nothing: no sentinel code is known."""
    files = _files()
    units = as_list(unit, files)
    frames = []
    for u in units:
        u = check_unit(u, files, _PACKAGE)
        frame = _read(files[u])
        if len(units) > 1:
            frame.insert(0, "unit", u)
        frames.append(finish(frame, _PACKAGE, clean, 0, unit=u))
    return concat(frames, _PACKAGE, clean)
