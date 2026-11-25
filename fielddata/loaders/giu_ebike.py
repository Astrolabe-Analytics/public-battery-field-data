"""Loader for the real-road e-bike pack release (Nour, J., Zenodo 10.5281/zenodo.24138446, CC BY 4.0), data for the paper
"Low-Cost Cell-Level Monitoring of an E-Bike Battery Pack: State-of-Charge Estimation and Fault Detection from
Real-Road Data" (J. A. Nour and M. H. Darweesh, German International University, Egypt; not found in print at intake,
2026-11-20). Admitted in v1.3 (2026-11-24).

One zip, ``ebike-pack-dataset.zip``: five cleaned recordings of one 13S4P pack (52 Samsung INR18650-30Q cells, JK-BMS,
one line per second), the raw log of one ride before a faulty parallel group was replaced
(``raw/jk_001_before_repair.csv``), an overview PNG per cleaned file and a README that defines every column.

``systems()`` lists the one pack, ``recordings()`` the six CSV files, and ``load(recording)`` returns one file as
released (all five cleaned files when ``recording`` is None). Values are unchanged: current is positive in discharge
as released (README), and the raw file keeps its own columns. ``clean`` masks nothing. See ``giu_ebike_SCHEMA.md``.
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd

from fielddata.loaders._base import directory, finish

_PACKAGE = "giu_ebike"
_ARCHIVE = "ebike-pack-dataset.zip"
_ROOT = "ebike-pack-dataset/"
CLEAN = ["1_capacity_test", "2_charge_and_ride_A", "3_ride_B", "4_ride_C", "5_charge_after_rides"]
RAW = "raw/jk_001_before_repair"
RECORDINGS = CLEAN + [RAW]
CELL_COLUMNS = [f"cell{i:02d}" for i in range(1, 14)]


def _zip() -> zipfile.ZipFile:
    return zipfile.ZipFile(directory(_PACKAGE) / _ARCHIVE)


def readme() -> str:
    with _zip() as archive:
        return archive.read(_ROOT + "README.md").decode("utf-8")


def _read(name: str) -> pd.DataFrame:
    if name not in RECORDINGS:
        raise ValueError(f"{_PACKAGE}: unknown recording {name!r}; choose from {RECORDINGS}")
    with _zip() as archive:
        frame = pd.read_csv(io.BytesIO(archive.read(f"{_ROOT}{name}.csv")))
    if name == RAW:
        frame["utc_time"] = pd.to_datetime(frame["utc_time"], utc=True)  # ISO 8601 with Z, as released
    else:
        frame["time"] = pd.to_datetime(frame["time"], format="%Y-%m-%d %H:%M:%S")  # local time, UTC+2 (README); kept naive
    frame.insert(0, "recording", name)
    return frame


def load(recording=None, clean: bool = False) -> pd.DataFrame:
    """One recording as released, or the five cleaned recordings concatenated when ``recording`` is None. The raw
    pre-repair log has different columns and is read only by name (``raw/jk_001_before_repair``)."""
    names = CLEAN if recording is None else [recording]
    frame = pd.concat([_read(n) for n in names], ignore_index=True)
    return finish(frame, _PACKAGE, clean, 0, recording=recording)


def recordings() -> pd.DataFrame:
    """One row per CSV file: rows, first and last timestamp (as released: local time for the cleaned files, UTC for
    the raw file), and the phases it holds."""
    rows = []
    for name in RECORDINGS:
        frame = _read(name)
        t = frame["utc_time"] if name == RAW else frame["time"]
        rows.append({"recording": name, "rows": len(frame), "first": t.min(), "last": t.max(),
                     "time_basis": "UTC" if name == RAW else "local, UTC+2",
                     "phases": "" if name == RAW else ";".join(dict.fromkeys(frame["phase"]))})
    return pd.DataFrame(rows)


def systems() -> pd.DataFrame:
    """The one pack, as the README describes it."""
    return pd.DataFrame([{"unit": "pack", "topology": "13S4P", "cells": 52, "cell_model": "Samsung INR18650-30Q",
                          "bms": "JK-BMS JK_BD6A20S6P", "nominal_v": 48.0, "recordings": len(RECORDINGS)}])
