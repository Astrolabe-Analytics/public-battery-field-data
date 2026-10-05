"""Loader for the KU Leuven BEV energy-dynamics release (KU Leuven RDR 10.48804/8KPDTW).

Raw conventions (see ku_leuven_bev_SCHEMA.md for citations):
- The authors decoded CAN logs (messages every 10 to 20 ms, paper p. 10) and averaged each signal onto a
  1 s grid (paper p. 3, Usage Notes p. 13; data_processing_V1.py ``resample('1S').mean()``).
- Session folders are the authors' classification; parking is "any time during which no charging or
  driving data was collected" (paper p. 7).
- ``Timestamp`` is UTC (paper Table 5).
- ``RawBattCurrent132`` is negative while charging and positive while driving (measured; the paper
  states no sign).
- ``SOCave292`` is the BMS-reported average SOC.
- ``Odometer3B6`` holds 4294967.295 (0xFFFFFFFF x 0.001, a CAN "not available" value) in rows where the
  odometer was not received (observed, not documented); ``clean=True`` masks that value only.
"""
from __future__ import annotations

import io
import re
import zipfile

import pandas as pd

from fielddata.loaders._base import check_unit, concat, directory, finish, mask_values

_PACKAGE = "ku_leuven_bev"
_OUTER = "doi-10.48804-8kpdtw.zip"
_INNER = "BEV energy dynamic data_V2.zip"
# 0xFFFFFFFF scaled by 0.001 km: no odometer frame received (observed in every session type, source audit 2026-10-04)
_ODOMETER_NOT_AVAILABLE = 4294967.295
_SESSION = re.compile(r"/(?P<type>slow charging|fast charging|driving|parking) sessions/(?P<unit>BEV\d)_(?P<date>\d{4}-\d{2}[-_]\d{2})[^/]*\.csv$")


def _inner():
    with zipfile.ZipFile(directory(_PACKAGE) / _OUTER) as outer:
        return zipfile.ZipFile(io.BytesIO(outer.read(_INNER)))


def sessions():
    """One row per released session file: vehicle, session type, date and archive member."""
    with _inner() as z:
        rows = [dict(m.groupdict(), member=n) for n in z.namelist() if (m := _SESSION.search(n))]
    frame = pd.DataFrame(rows)
    # three parking-session file names write the date as YYYY-MM_DD
    frame["date"] = pd.to_datetime(frame["date"].str.replace("_", "-"))
    return frame.sort_values(["unit", "date", "member"]).reset_index(drop=True)


def systems():
    """One row per vehicle (BEV1, BEV2) with its session counts and first and last session dates."""
    s = sessions()
    counts = s.pivot_table(index="unit", columns="type", values="member", aggfunc="count", fill_value=0)
    dates = s.groupby("unit")["date"].agg(["min", "max"]).rename(columns={"min": "first_session", "max": "last_session"})
    return counts.join(dates).reset_index()


def load(unit, session_type=None, clean=False):
    """Load all sessions of one vehicle, or only one session type, indexed by ``Timestamp`` (UTC).

    ``session_type`` is one of "slow charging", "fast charging", "driving", "parking". Columns are the decoded
    CAN signals as released (names end in the CAN message id). A ``session`` column names the source file.
    ``clean=True`` masks only ``Odometer3B6`` == 4294967.295 (0xFFFFFFFF x 0.001 km, not a reading).
    """
    s = sessions()
    name = check_unit(unit, s["unit"].unique(), _PACKAGE)
    s = s[s["unit"] == name]
    if session_type is not None:
        if session_type not in set(s["type"]):
            raise ValueError(f"{_PACKAGE}: session_type must be one of {sorted(set(s['type']))}")
        s = s[s["type"] == session_type]
    frames = []
    with _inner() as z:
        for row in s.itertuples():
            frame = pd.read_csv(io.BytesIO(z.read(row.member)))
            frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], utc=True)
            frame["session"] = row.member.rsplit("/", 1)[-1]
            frame["session_type"] = row.type
            masked = mask_values(frame, {"Odometer3B6": lambda c: c == _ODOMETER_NOT_AVAILABLE}) if clean else 0
            frames.append(finish(frame, _PACKAGE, clean, masked))
    out = concat(frames, _PACKAGE, clean, unit=name, session_type=session_type, sessions=len(frames))
    out["unit"] = name
    return out.set_index("Timestamp").sort_index(kind="stable")
