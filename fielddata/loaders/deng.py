"""Loader for Deng et al. on-road EV charging-data archives.

Raw conventions (see deng_SCHEMA.md for citations):
- Rows exist only while charging; the chargers logged them over CAN every 8 s (paper p. 3).
- ``charge_current`` is negative while charging (paper Eq. (1), p. 3).
- ``soc`` is a BMS estimate (paper pp. 2-3).
- ``available_capacity`` and ``available_energy`` are undocumented BMS fields that rise with
  SOC inside each session (remaining charge and energy), not capacity or SOH estimates.
- ``number`` is a 0..n-1 row counter.
- Timestamps are returned naive: the sources state no time zone (paper Table 1, p. 2).
- The authors removed "sensitive information" before release; the fields are not stated (p. 11).
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from fielddata.config import data_root
from fielddata.registry import PACKAGES

_PACKAGE = "deng"
_COLUMNS = [
    "number",
    "record_time",
    "soc",
    "pack_voltage",
    "charge_current",
    "max_cell_voltage",
    "min_cell_voltage",
    "max_temperature",
    "min_temperature",
    "available_energy",
    "available_capacity",
]


def _clean_impossible_values(frame):
    numeric = frame.drop(columns=["number", "record_time"], errors="ignore").select_dtypes(include="number")
    mask = numeric.abs() > 1_000_000
    for column in numeric.columns:
        if mask[column].any():
            frame[column] = numeric[column].astype(float).mask(mask[column])
    return int(mask.to_numpy().sum())


def _directory():
    return data_root() / PACKAGES[_PACKAGE]["data_directory"]


def _archive_sort_key(path: Path):
    return int(path.stem.removeprefix("#"))


def _archives():
    return sorted(_directory().glob("#*.rar"), key=_archive_sort_key)


def _unrar():
    candidate = Path(r"C:\Program Files\WinRAR\UnRAR.exe")
    if candidate.exists():
        return str(candidate)
    found = shutil.which("UnRAR") or shutil.which("unrar")
    if found:
        return found
    raise RuntimeError("Deng loader requires UnRAR, for example C:\\Program Files\\WinRAR\\UnRAR.exe")


def _archive_for_pack(pack):
    pack_id = str(pack).removeprefix("#")
    path = _directory() / f"#{int(pack_id)}.rar"
    if not path.exists():
        raise ValueError(f"pack not present for deng: {pack}")
    return path


def systems():
    """Return one row per released vehicle battery pack."""
    rows = []
    for archive in _archives():
        rows.append({
            "pack": archive.stem,
            "unit": archive.stem,
            "archive": archive.name,
            "bytes": archive.stat().st_size,
            "chemistry": "NCM",
            "vehicle_model": "BAIC EU500",
            "series_cells": 90,
            "nominal_capacity_Ah": 145,
        })
    return pd.DataFrame(rows)


def load_raw(pack, clean=False):
    """Load one released pack CSV from its RAR archive without cleaning or resampling."""
    archive = _archive_for_pack(pack)
    try:
        unrar = _unrar()
    except RuntimeError:
        unrar = None
    if unrar is None:  # no UnRAR installed: stream the archive with libarchive instead
        import io
        import libarchive
        with libarchive.file_reader(str(archive)) as reader:
            for entry in reader:
                if entry.pathname.lower().endswith(".csv"):
                    frame = pd.read_csv(io.BytesIO(b"".join(entry.get_blocks())), header=0, names=_COLUMNS, skipinitialspace=True)
                    csv_path = Path(entry.pathname)
                    break
    else:
        with tempfile.TemporaryDirectory(prefix="deng-loader-") as scratch:
            target = Path(scratch) / archive.stem.removeprefix("#")
            target.mkdir()
            subprocess.run([unrar, "x", "-inul", "-o+", str(archive), str(target) + "\\"], check=True)
            csv_path = next(target.rglob("*.csv"))
            frame = pd.read_csv(csv_path, header=0, names=_COLUMNS, skipinitialspace=True)
    masked_value_count = _clean_impossible_values(frame) if clean else 0
    frame.attrs = {"package": _PACKAGE, "pack": archive.stem, "archive": archive.name, "source_file": csv_path.name, "n_rows": len(frame), "clean": clean, "masked_value_count": masked_value_count}
    return frame


def load(pack=None, clean=False):
    """Load one or more packs indexed by naive record_time (time zone not stated), preserving released measurement columns."""
    packs = [archive.stem for archive in _archives()] if pack is None else pack
    if isinstance(packs, (str, int)):
        packs = [packs]
    frames = []
    for item in packs:
        frame = load_raw(item, clean=clean)
        frame["record_time"] = pd.to_datetime(frame["record_time"].astype(str), format="%Y%m%d%H%M%S", errors="coerce")  # naive: no zone stated
        frame["pack"] = frame.attrs["pack"]
        frames.append(frame.set_index("record_time").sort_index())
    out = pd.concat(frames, axis=0, sort=False) if len(frames) > 1 else frames[0]
    out.attrs = {"package": _PACKAGE, "packs": [str(p).removeprefix("#") for p in packs], "n_rows": len(out), "clean": clean, "masked_value_count": sum(frame.attrs["masked_value_count"] for frame in frames)}
    return out