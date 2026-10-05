"""Loader for the RWTH Mobile Battery Data Explorer export (33 Android devices, 2026-04).

Raw conventions (see rwth_android_SCHEMA.md for citations and measurements):
- The archive is a portal export with timestamps from 2025-10-24 to 2026-03-31; the cited data paper
  describes 33 devices from 2026-01-14 to 2026-04-15. Timestamps are naive; no zone is stated.
- Units as in data paper Table 1: V, A, Ah, %, C. ``current`` and ``current_avg``: positive = into the
  battery per the data paper, but "definition may differ between manufacturers"; in this export all
  OnePlus and Xiaomi devices report the opposite sign (measured).
- ``state_of_charge``, ``health``, ``cycle_count`` and ``battery_technology`` are reported by the phone.
- ``current_avg`` is -2147.483648 (Integer.MIN_VALUE x 1e-6) on devices that do not provide it, and
  ``nominal_capacity`` is 0 on some devices; ``clean=True`` masks -2147.483648 in the current and charge
  columns (it cannot be a phone current). ``nominal_capacity`` 0 is left as released.
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd

from fielddata.loaders._base import as_list, check_unit, concat, directory, finish, mask_values

_PACKAGE = "rwth-android"
_ARCHIVE = "Dataset_from_Mobile_Battery_Data_Explorer_2026-04.zip"
# Integer.MIN_VALUE x 1e-6: "not provided" from the Android fuel gauge (observed only in current_avg, 10 devices)
_NOT_PROVIDED = -2147.483648


def _names():
    with zipfile.ZipFile(directory(_PACKAGE) / _ARCHIVE) as z:
        return sorted(n for n in z.namelist() if n.endswith(".parquet"))


def systems():
    """One row per device parquet (anonymised file-name hash), with manufacturer, model and technology."""
    rows = []
    with zipfile.ZipFile(directory(_PACKAGE) / _ARCHIVE) as z:
        for name in _names():
            meta = pd.read_parquet(io.BytesIO(z.read(name)), columns=["manufacturer", "model", "battery_technology", "timestamp"])
            rows.append({"unit": name.removesuffix(".parquet"), "manufacturer": meta["manufacturer"].iloc[0],
                         "model": meta["model"].iloc[0], "battery_technology": meta["battery_technology"].iloc[0],
                         "rows": len(meta), "first": meta["timestamp"].min(), "last": meta["timestamp"].max()})
    return pd.DataFrame(rows)


def load(unit=None, clean=False):
    """Load one or more devices, indexed by naive ``timestamp``, with the released columns.

    ``clean=True`` masks only the value -2147.483648 in ``current``, ``current_avg`` and ``charge_counter``.
    """
    names = [n.removesuffix(".parquet") for n in _names()]
    frames = []
    with zipfile.ZipFile(directory(_PACKAGE) / _ARCHIVE) as z:
        for item in as_list(unit, names):
            name = check_unit(item, names, _PACKAGE)
            frame = pd.read_parquet(io.BytesIO(z.read(name + ".parquet")))
            frame["unit"] = name
            rules = {c: (lambda v: v == _NOT_PROVIDED) for c in ("current", "current_avg", "charge_counter")}
            masked = mask_values(frame, rules) if clean else 0
            frames.append(finish(frame.set_index("timestamp").sort_index(kind="stable"), _PACKAGE, clean, masked, unit=name))
    return concat(frames, _PACKAGE, clean)
