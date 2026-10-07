"""Loader for the BBOXX solar-home-system battery release (Aitio and Howey, Joule 2021; ORA record
uuid:e41d3d4c-f74e-4d76-81fd-0caa77ec6cec).

The release holds 1,027 valve-regulated lead-acid batteries of BBOXX solar home systems. Each battery is one
``<id>.npz`` file inside one of the shipped zips ``set_0.zip`` to ``set_10.zip`` (100 per zip, 27 in
``set_10.zip``). Each file holds one array, ``arr_0``, N x 4 float64. The readme gives the columns: a UNIX
timestamp, then measured current, voltage and temperature; "negative current is charging" and "the recording
frequency is non-uniform in time". The loader reads the files straight from the zips and changes no value.

Columns returned by ``load``: ``time_s`` (UNIX seconds), ``current_A`` (negative = charging, the authors'
convention, kept as released), ``voltage_V`` and ``temperature_degC``, plus ``time`` (``time_s`` as a UTC
timestamp, since UNIX time is UTC by definition) as the index. ``meta_data.csv`` is returned by ``metadata()``.
"""
from __future__ import annotations

import io
import zipfile
from functools import lru_cache

import numpy as np
import pandas as pd

from fielddata.loaders._base import as_list, check_unit, concat, directory, finish, mask_values

_PACKAGE = "aitio"
COLUMNS = ["time_s", "current_A", "voltage_V", "temperature_degC"]
ZIPS = [f"set_{i}.zip" for i in range(11)]
# clean=True masks voltage below 1 V: 168 values in 91 batteries, all brief blips inside normal readings (121 single
# rows, 22 pairs, one run of three; see aitio_SCHEMA.md). A 12 V lead-acid battery cannot read below 1 V and recover
# within a minute, so these are not measurements. Nothing else is masked.
CLEAN_RULES = {"voltage_V": lambda v: v < 1.0}


@lru_cache(maxsize=1)
def _members() -> dict[str, tuple[str, str]]:
    """unit id -> (zip name, member name), from the zips' listings."""
    out = {}
    for zip_name in ZIPS:
        with zipfile.ZipFile(directory(_PACKAGE) / zip_name) as z:
            for member in z.namelist():
                if member.endswith(".npz"):
                    out[member.rsplit("/", 1)[-1][:-4]] = (zip_name, member)
    return out


def metadata() -> pd.DataFrame:
    """``meta_data.csv`` as released: ID, ACTIVATED, IN_REPAIR_SYSTEM, STILL_ALIVE, Lifetime (days).

    The readme describes the columns as UID, activation date, repair date, lifetime and a flag for whether the
    battery entered repair; the released file's flag column is STILL_ALIVE. Dates are parsed (month/day/year).
    """
    frame = pd.read_csv(directory(_PACKAGE) / "meta_data.csv")
    for column in ("ACTIVATED", "IN_REPAIR_SYSTEM"):
        frame[column] = pd.to_datetime(frame[column], format="%m/%d/%Y")
    frame["ID"] = frame["ID"].astype(str)
    return frame


def _repair_dates() -> dict[str, pd.Timestamp]:
    """unit id -> IN_REPAIR_SYSTEM as 00:00 UTC, for batteries with STILL_ALIVE = FALSE."""
    meta = metadata()
    failed = meta[(meta["STILL_ALIVE"] == False) & meta["IN_REPAIR_SYSTEM"].notna()]  # noqa: E712 (boolean as released)
    return {r.ID: pd.Timestamp(r.IN_REPAIR_SYSTEM).tz_localize("UTC") for r in failed.itertuples()}


def systems() -> pd.DataFrame:
    """One row per battery: unit id, the zip and member that hold it, joined with ``metadata()``."""
    members = _members()
    frame = pd.DataFrame([{"unit": unit, "zip": z, "member": m} for unit, (z, m) in members.items()])
    frame = frame.merge(metadata(), left_on="unit", right_on="ID", how="left").drop(columns="ID")
    return frame.sort_values("unit", key=lambda s: s.astype(int)).reset_index(drop=True)


def _read(unit: str) -> np.ndarray:
    zip_name, member = _members()[unit]
    with zipfile.ZipFile(directory(_PACKAGE) / zip_name) as z, z.open(member) as handle:
        with np.load(io.BytesIO(handle.read())) as npz:
            return npz["arr_0"]


def load(unit=None, clean=False, truncate_at_repair=False):
    """Load one battery (or a list of batteries) as released, indexed by UTC time.

    ``clean=True`` masks single values, never rows: voltage below 1 V (brief blips, see ``CLEAN_RULES``). No
    placeholder code is documented. Other low voltage, high temperature or large current can be real fault data
    and is kept.

    ``truncate_at_repair=True`` (default False, also when ``clean=True``) drops each failed battery's rows from
    its IN_REPAIR_SYSTEM date on, keeping rows before 00:00 UTC of that date, the same boundary as Lifetime. This is
    the authors' cut (paper p. 23, step 8: time series "truncated to only include data up to the repair date") and
    reproduces the paper's input; the release itself keeps the post-repair telemetry. Live batteries are unchanged.
    """
    units = as_list(unit, _members())
    repair = _repair_dates() if truncate_at_repair else {}
    frames = []
    for u in units:
        u = check_unit(u, _members(), _PACKAGE)
        frame = pd.DataFrame(_read(u), columns=COLUMNS)
        frame.index = pd.to_datetime(frame["time_s"], unit="s", utc=True).rename("time")
        dropped = 0
        if u in repair:
            keep = frame.index < repair[u]
            dropped = int((~keep).sum())
            frame = frame[keep]
        if len(units) > 1:
            frame.insert(0, "unit", u)
        masked = mask_values(frame, CLEAN_RULES) if clean else 0
        frames.append(finish(frame, _PACKAGE, clean, masked, unit=u, truncate_at_repair=truncate_at_repair,
                             rows_dropped_after_repair=dropped))
    return concat(frames, _PACKAGE, clean, truncate_at_repair=truncate_at_repair,
                  rows_dropped_after_repair=sum(f.attrs["rows_dropped_after_repair"] for f in frames))
