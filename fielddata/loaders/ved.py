"""Loader for the Vehicle Energy Dataset (VED; Oh, LeBlanc and Peng, IEEE T-ITS 23(4) 3302-3312, 2022,
doi:10.1109/TITS.2020.3035596; data https://github.com/gsoh/VED, Apache 2.0). Candidate package: not in the totals.

383 personal cars in Ann Arbor, Michigan (README), November 2017 to November 2018, logged through OBD-II. Only the
27 plug-in hybrid and electric vehicles carry battery signals (HV Battery Current, SOC and Voltage). The release
is two static workbooks, one per vehicle group, and two solid 7z archives of 54 weekly CSVs (3.2 GB uncompressed).
Reading one week from a solid archive means decompressing all of it, so the loader extracts the weekly CSVs once
(about 20 s, needs ``py7zr``) into ``extracted/`` beside the release's ``data/`` folder. That folder is a local
copy, not part of the release or this repository. No value is changed.

``systems()`` lists the 384 vehicles in the static workbooks, ``weeks()`` the weekly files, and
``load(unit=None, week=None, columns=None)`` returns rows as released. See ``ved_SCHEMA.md``.
"""
from __future__ import annotations

import pandas as pd

from fielddata.loaders._base import as_list, concat, directory, finish

_PACKAGE = "ved"
STATIC = {"ICE&HEV": "VED_Static_Data_ICE&HEV.xlsx", "PHEV&EV": "VED_Static_Data_PHEV&EV.xlsx"}
ARCHIVES = ["VED_DynamicData_Part1.7z", "VED_DynamicData_Part2.7z"]
BATTERY_COLUMNS = ["HV Battery Current[A]", "HV Battery SOC[%]", "HV Battery Voltage[V]"]
# README: "There are 3 pure EV vehicles in the dataset. All of them are 2013 Nissan Leaf with an advertised battery
# capacity of 24 kWh." No rating is stated for the plug-in hybrids.
EV_RATED_KWH = 24.0


def _data():
    return directory(_PACKAGE) / "VED" / "Data"


def _extracted():
    """The weekly CSVs, extracted once from the two archives into extracted/ beside data/."""
    folder = directory(_PACKAGE).parent / "extracted"
    files = sorted(folder.glob("VED_*_week.csv")) if folder.exists() else []
    if len(files) < 54:
        try:
            import py7zr
        except ImportError as error:
            raise ImportError("ved: reading the weekly data needs py7zr (python -m pip install py7zr)") from error
        folder.mkdir(parents=True, exist_ok=True)
        for name in ARCHIVES:
            with py7zr.SevenZipFile(_data() / name) as archive:
                archive.extractall(path=folder)
        files = sorted(folder.glob("VED_*_week.csv"))
    return {f.stem.split("_")[1]: f for f in files}


def systems() -> pd.DataFrame:
    """One row per vehicle in the static workbooks: VehId, type (ICE, HEV, PHEV or EV) and the static columns.

    ``battery_signals`` is True for the PHEV and EV workbook, the vehicles whose rows carry HV battery signals.
    """
    frames = []
    for group, name in STATIC.items():
        frame = pd.read_excel(_data() / name, engine="openpyxl")
        frame = frame.rename(columns={"EngineType": "Vehicle Type"})
        frame.insert(0, "group", group)
        frame["battery_signals"] = group == "PHEV&EV"
        frames.append(frame)
    out = pd.concat(frames, ignore_index=True)
    out.insert(0, "unit", out["VehId"].astype(str))
    out["rated_kwh_stated"] = out["Vehicle Type"].map({"EV": EV_RATED_KWH})
    return out


def weeks() -> list[str]:
    """Week labels (yymmdd of the first day) of the weekly files, from the file names."""
    return list(_extracted())


def load(unit=None, week=None, columns=None, clean=False):
    """Rows of the weekly files as released: all vehicles, or the named VehId(s); all weeks, or the named ones.

    ``columns`` reads only those columns (DayNum and VehId are always read). ``clean`` masks nothing.
    """
    files = _extracted()
    chosen = as_list(week, files)
    wanted = None if unit is None else {int(u) for u in as_list(unit, [])}
    usecols = None if columns is None else list(dict.fromkeys(["DayNum", "VehId", *columns]))
    frames = []
    for w in chosen:
        if w not in files:
            raise ValueError(f"{_PACKAGE}: unknown week {w!r}; weeks() lists {len(files)}")
        frame = pd.read_csv(files[w], usecols=usecols)
        if wanted is not None:
            frame = frame[frame["VehId"].isin(wanted)]
        frame.insert(0, "week", w)
        frames.append(finish(frame.reset_index(drop=True), _PACKAGE, clean, 0, week=w))
    return concat(frames, _PACKAGE, clean)
