"""Loader for the RWTH home-storage field measurements (Zenodo 10.5281/zenodo.12091223).

Raw conventions (see rwth_home_SCHEMA.md for citations):
- Measured by research loggers at the battery DC poles (BMS self-supply included), not by the BMS.
- ``I_in_A`` and ``P_in_W``: positive = charging, negative = discharging (SI Note 4, SI Fig. 1).
- Before release the authors set outliers outside datasheet-based limits to NaN and linearly interpolated
  gaps up to 5 min (``Interpolated`` = 1) (SI Note 2).
- ``T_Bat_in_C`` is a pack-housing temperature, not comparable across products (SI Notes 2-3).
- ``Time`` has no zone assigned; the sources state none, and the clock has no daylight-saving shifts.
"""
from __future__ import annotations

import io
import re
import zipfile

import pandas as pd

from fielddata.loaders._base import as_list, check_unit, concat, directory, finish

_PACKAGE = "rwth-home"
_MONTH = re.compile(r"(\d{4})_(\d{2})_System_ID_(\d{2})\.csv$")


def _archive(system: str):
    return directory(_PACKAGE) / f"Data_ID_{system}.zip"


def metadata():
    """The released system metadata table (Metadata_Systems.xlsx), as released."""
    with zipfile.ZipFile(directory(_PACKAGE) / "Metadata_and_Code.zip") as z:
        return pd.read_excel(io.BytesIO(z.read("00_Data/00_Metadata/Metadata_Systems.xlsx")))


def _units():
    return sorted(p.stem.removeprefix("Data_ID_") for p in directory(_PACKAGE).glob("Data_ID_*.zip"))


def members(system):
    """Every member name in one system's archive, as stored (for checking that ``months()`` misses none)."""
    name = check_unit(f"{int(system):02d}", _units(), _PACKAGE)
    with zipfile.ZipFile(_archive(name)) as z:
        return z.namelist()


def months(system):
    """The monthly CSV members of one system, oldest first, as (YYYY-MM, member) pairs."""
    name = check_unit(f"{int(system):02d}", _units(), _PACKAGE)
    with zipfile.ZipFile(_archive(name)) as z:
        found = [(f"{m.group(1)}-{m.group(2)}", n) for n in z.namelist() if (m := _MONTH.search(n))]
    return sorted(found)


def systems():
    """One row per home-storage system: archive, bytes and number of monthly files."""
    rows = []
    for u in _units():
        m = months(u)
        rows.append({"unit": u, "archive": _archive(u).name, "bytes": _archive(u).stat().st_size, "months": len(m),
                     "first_month": m[0][0] if m else None, "last_month": m[-1][0] if m else None})
    return pd.DataFrame(rows)


def load(unit, month=None, clean=False):
    """Load one system (1 s rows), all months or the given month(s) "YYYY-MM", indexed by ``Time``.

    Columns as released: P_in_W, V_in_V, I_in_A, T_Bat_in_C, T_Room_in_C, Interpolated. A full system is
    tens of millions of rows; pass ``month`` to read less. ``clean`` has no effect (the authors already set
    outliers to NaN before release).
    """
    name = f"{int(unit):02d}"
    available = months(name)
    wanted = [m for m, _ in available] if month is None else as_list(month, [])
    lookup = dict(available)
    frames = []
    with zipfile.ZipFile(_archive(name)) as z:
        for m in wanted:
            if m not in lookup:
                raise ValueError(f"{_PACKAGE}: system {name} has no month {m}")
            frame = pd.read_csv(z.open(lookup[m]))
            frame["Time"] = pd.to_datetime(frame["Time"], format="%d-%b-%Y %H:%M:%S")
            frames.append(finish(frame, _PACKAGE, clean, 0))
    out = concat(frames, _PACKAGE, clean, unit=name, months=wanted)
    out["unit"] = name
    return out.set_index("Time").sort_index(kind="stable")
