"""Loader for the TUM 2022 Volkswagen ID.3 powertrain release (Wassiliadis et al., mediaTUM 10.14459/2022mp1656313,
CC BY 4.0), the data of eTransportation 12, 100167 (2022). Candidate package: not in the totals.

One ID.3 Pro Performance, 148 drives from 2021-02-11 to 2021-12-08, logged over UDS. It is the same vehicle as tumftm's
ID1 (scripts/checks/tum_id3_vs_tumftm.py: SOC and pack voltage identical at matching timestamps), so maintainer's
decision (2026-10-13) is that its extra signals (pack current, 108 cell voltages and more) belong to that unit, which
is counted once, under tumftm. The release holds each drive as ``Data/Tracks/track_N.csv`` and ``.mat`` (the same
drive in two formats), ``Data/value_definitions.csv`` and ``Data.sha512``. The loader reads the CSVs and changes no
value.

``systems()`` has the one vehicle, ``tracks()`` the 148 drives, ``definitions()`` the signal table, and
``load(unit=None, track=None, columns=None)`` drives as released. See ``tum_id3_2022_SCHEMA.md``.
"""
from __future__ import annotations

import re

import pandas as pd

from fielddata.loaders._base import concat, directory, finish

_PACKAGE = "tum_id3_2022"
VEHICLE = "ID3"
SAME_AS = "tumftm ID1"


def _tracks() -> dict[int, object]:
    folder = directory(_PACKAGE) / "Data" / "Tracks"
    return {int(re.search(r"\d+", p.stem).group()): p for p in sorted(folder.glob("track_*.csv"))}


def tracks() -> pd.DataFrame:
    """One row per drive: number, CSV file and size, columns, rows, first and last time (ms since 1970, UTC)."""
    rows = []
    for number, path in sorted(_tracks().items()):
        header = path.open(encoding="utf-8", errors="replace").readline().strip().split(",")
        time = pd.read_csv(path, usecols=["time"])["time"]
        rows.append({"track": number, "file": path.name, "bytes": path.stat().st_size, "columns": len(header),
                     "rows": len(time), "first": pd.to_datetime(time.min(), unit="ms"), "last": pd.to_datetime(time.max(), unit="ms")})
    return pd.DataFrame(rows)


def systems() -> pd.DataFrame:
    """The one vehicle: drives, first and last time, and the unit it is already counted as."""
    drives = tracks()
    return pd.DataFrame([{"unit": VEHICLE, "vehicle": "VW ID.3 Pro Performance", "same_as": SAME_AS,
                          "tracks": len(drives), "first": drives["first"].min(), "last": drives["last"].max()}])


def definitions() -> pd.DataFrame:
    """Data/value_definitions.csv as released (two note lines above the header)."""
    return pd.read_csv(directory(_PACKAGE) / "Data" / "value_definitions.csv", skiprows=2, encoding="latin-1")


def load(unit=None, track=None, columns=None, clean=False):
    """Drives as released, one row per sample, with a ``track`` column. ``unit`` is accepted for the common
    interface (the only unit is the vehicle). ``columns`` reads only those columns (``time`` is always read).
    Drives differ in their columns. ``clean`` masks nothing."""
    files = _tracks()
    numbers = list(files) if track is None else ([track] if isinstance(track, int) else list(track))
    frames = []
    for number in numbers:
        if number not in files:
            raise ValueError(f"{_PACKAGE}: no track {number}; tracks() lists {len(files)}")
        header = files[number].open(encoding="utf-8", errors="replace").readline().strip().split(",")
        use = None if columns is None else [c for c in dict.fromkeys(["time", *columns]) if c in header]
        frame = pd.read_csv(files[number], usecols=use)
        # concat rather than insert: insert into the wide, fragmented frame raises a PerformanceWarning
        frame = pd.concat([pd.Series(number, index=frame.index, name="track"), frame], axis=1)
        frames.append(finish(frame, _PACKAGE, clean, 0, track=number))
    return concat(frames, _PACKAGE, clean)
