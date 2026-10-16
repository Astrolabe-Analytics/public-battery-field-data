"""Loader for the RISE Conbat second-life BESS release (Fast, Scott, Casanova and MoradiKouchi, Zenodo
10.5281/zenodo.17287096, CC BY 4.0). Candidate package: not in the totals. No paper: data record only.

Telemetry of a battery energy storage system built from second-life VW Passat modules (RISE project "Data-Driven
State-of-Health Prediction for Recycled Batteries in New Applications", funded by the Swedish Energy Agency). The
release is one zip of database exports in 11 collection windows (``1. 230420-230516/`` to ``11. 240501-241104/``) and
a ``BESS/`` sub-collection, each with db-export-cell.csv, -module.csv, -string.csv, -module-info.csv and in some
windows -energy.csv and modules.csv. Layouts change between windows (README: "Always rely on headers present in each
CSV"). ``hour`` is UTC (README). The loader reads the CSVs inside the zip and changes no value.

``windows()`` lists the collection windows and their files, ``systems()`` the distinct modules from the module-info
tables (unit = module id, for example ``H406450-1``, car plus module number), ``installations()`` every installation
row, and ``load(window, level="module", unit=None)`` one window's file as released. See ``rise_conbat_SCHEMA.md``.
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd

from fielddata.loaders._base import directory, finish

_PACKAGE = "rise_conbat"
ARCHIVE = "Data-driven State-of-Health prediction for reused batteries in new applications.zip"
LEVELS = {"cell": "db-export-cell.csv", "module": "db-export-module.csv", "string": "db-export-string.csv",
          "energy": "db-export-energy.csv", "module-info": "db-export-module-info.csv", "modules": "modules.csv"}
# Exports cut off mid-row at about 1,020 MiB (the last row is incomplete; see the schema)
TRUNCATED = {"10. 240226- 240430/db-export-cell.csv", "11. 240501-241104/db-export-cell.csv",
             "11. 240501-241104/db-export-string.csv"}


def _zip() -> zipfile.ZipFile:
    return zipfile.ZipFile(directory(_PACKAGE) / ARCHIVE)


def windows() -> pd.DataFrame:
    """One row per collection window: its folder, the files present and their uncompressed sizes."""
    rows = {}
    with _zip() as archive:
        for info in archive.infolist():
            if info.is_dir() or "/" not in info.filename:
                continue
            folder, name = info.filename.rsplit("/", 1)
            level = next((k for k, v in LEVELS.items() if v == name), name)
            rows.setdefault(folder, {"window": folder})[f"{level}_bytes"] = info.file_size
    out = pd.DataFrame(list(rows.values()))
    out["order"] = out["window"].str.extract(r"(\d+)\.", expand=False).astype(int)
    return out.sort_values(["order", "window"]).drop(columns="order").reset_index(drop=True)


def installations() -> pd.DataFrame:
    """Every installation row of the module-info tables (window 11's table, plus window 1's and the BESS one for
    rows that are not in it): module id, car, model, position, nominal energy and start and end date as released."""
    with _zip() as archive:
        frames = []
        for window in ["11. 240501-241104", "1. 230420-230516", "BESS/9. 240207-240214"]:
            frame = pd.read_csv(io.BytesIO(archive.read(f"{window}/{LEVELS['module-info']}")))
            if "id" not in frame and "module_uuid" in frame:
                frame = frame.rename(columns={"module_uuid": "id"})
            frame.insert(0, "source_window", window)
            frames.append(frame)
    rows = pd.concat(frames, ignore_index=True)
    rows["start_date"] = pd.to_datetime(rows["start_date"], utc=True, format="mixed")
    rows["end_date"] = pd.to_datetime(rows.get("end_date"), utc=True, format="mixed")
    return rows.drop_duplicates(subset=["id", "start_date"]).reset_index(drop=True)


def systems() -> pd.DataFrame:
    """One row per distinct module id: car, model, installation count, first start and last end (blank: still in)."""
    rows = installations()
    out = rows.groupby("id", sort=False).agg(car=("car", "first"), car_model=("car_model", "first"),
                                             installations=("start_date", "size"), first_start=("start_date", "min"),
                                             last_end=("end_date", lambda s: pd.NaT if s.isna().any() else s.max())).reset_index()
    out.insert(0, "unit", out["id"])
    return out


def load(window: str, level: str = "module", unit=None, columns=None, clean=False):
    """One window's file of one level as released. ``unit`` keeps the named module id(s) where the file has a
    ``module_uuid`` column. The last row of the three truncated files may be incomplete and is returned as parsed.
    ``clean`` masks nothing: ``is_filler`` flags are returned for the caller to use."""
    if level not in LEVELS:
        raise ValueError(f"{_PACKAGE}: level must be one of {list(LEVELS)}")
    member = f"{window}/{LEVELS[level]}"
    with _zip() as archive:
        if member not in archive.namelist():
            raise ValueError(f"{_PACKAGE}: no {LEVELS[level]} in window {window!r}; windows() lists the files")
        with archive.open(member) as handle:
            frame = pd.read_csv(handle, usecols=columns, on_bad_lines="warn")
    if unit is not None and "module_uuid" in frame:
        units = [unit] if isinstance(unit, str) else list(unit)
        frame = frame[frame["module_uuid"].isin(units)].reset_index(drop=True)
    return finish(frame, _PACKAGE, clean, 0, window=window, level=level, truncated=member in TRUNCATED)
