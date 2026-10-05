"""Loader for the Tsukuba research-building microgrid data (Scientific Data 2019, figshare 7403954)."""
from __future__ import annotations

import io
import re

import pandas as pd
from fielddata._deflate64 import zipfile  # the per-second CSVs are deflate64-compressed

from fielddata.config import data_root
from fielddata.loaders._base import as_list, concat, directory, finish
from fielddata.registry import PACKAGES

_PACKAGE = "tsukuba"
_VERSIONS = {"raw": "1 Raw_data_per_second.zip", "cleaned": "2 Cleaned_data_per_second.zip"}
# English names translate the released Japanese headers (row 1); the codes (row 2) are the column keys.
NAMES = {
    "10101": "battery_active_power", "10105": "battery_dc_voltage", "10106": "battery_dc_current",
    "10201": "grid_point_voltage", "10203": "grid_point_active_power", "10307": "pv_active_power",
    "12144": "battery_active_power_setpoint", "12152": "battery_soc",
    "20106": "pv1_active_power", "20109": "pv2_active_power", "20112": "pv3_active_power", "20115": "pv4_active_power",
}
_FILE = re.compile(r"(\d{8})-(\d{8})SecCsv\.csv$")
# One raw member is misnamed: its rows run 2015-07-01 00:00:00 to 2015-07-12 23:59:59 (checked by reading it),
# but its name says the span ends 2016-07-12. files() uses the true last day so date-range loads stay correct.
_LAST_DAY_FIX = {"20150701-20160712SecCsv.csv": "2015-07-12"}
# Publisher error code (paper p. 6, Known issues): "error values of -999,999", blank in the cleaned files.
SENTINEL = -999999


def _outer():
    return zipfile.ZipFile(directory(_PACKAGE) / PACKAGES[_PACKAGE]["data_files"][0])


def files(version="raw"):
    """The per-second files of one version ("raw" or "cleaned"): member, first and last day.

    The days come from the member names, except the one misnamed raw member in ``_LAST_DAY_FIX``. The raw
    deposit has 118 files against 119 cleaned: raw 2017-11-13 to 2017-11-24 is not in it (the paper's Table 3
    says 119 raw files), so ``version="raw"`` returns no rows for those 12 days.
    """
    with _outer() as z, zipfile.ZipFile(z.open(_VERSIONS[version])) as inner:
        rows = [{"member": n, "first_day": pd.Timestamp(m.group(1)),
                 "last_day": pd.Timestamp(_LAST_DAY_FIX.get(n.rsplit("/", 1)[-1], m.group(2)))}
                for n in inner.namelist() if (m := _FILE.search(n))]
    return pd.DataFrame(rows).sort_values("first_day").reset_index(drop=True)


def systems():
    """The release is one building microgrid with one lead-acid battery; one row with its file counts."""
    raw, cleaned = files("raw"), files("cleaned")
    return pd.DataFrame([{"unit": "tsukuba", "raw_files": len(raw), "cleaned_files": len(cleaned),
                          "first_day": raw["first_day"].min(), "last_day": raw["last_day"].max()}])


def _read(handle):
    text = io.TextIOWrapper(handle, encoding="cp932", newline="")
    header_ja = text.readline().rstrip("\r\n").split(",")
    codes = [c.strip() for c in text.readline().rstrip("\r\n").split(",")]
    units = [u.strip() for u in text.readline().rstrip("\r\n").split(",")]
    # The cleaned file 20180401-20180412 ends every line with two extra empty fields; unnamed columns are
    # read under placeholder names and dropped when they hold no value.
    names = ["time"] + [c or f"_unnamed{i}" for i, c in enumerate(codes[1:], 1)]
    frame = pd.read_csv(text, header=None, names=names)
    empty = [c for c in names if c.startswith("_unnamed") and frame[c].isna().all()]
    frame = frame.drop(columns=empty)
    text_time = frame["time"].str.lstrip("'")
    frame["time"] = pd.to_datetime(text_time, format="%Y/%m/%d %H:%M:%S", errors="coerce")
    # Two cleaned rows lost their seconds: "2015/11/14 20:13" (file 20151113) and "2017/3/13 0:00" (first row of
    # file 20170313). A row whose time does not parse gets the second implied by its neighbours (previous + 1 s,
    # or next - 1 s for a first row), and only if that second lies in the minute its own text gives.
    bad = frame["time"].isna()
    if bad.any():
        loose = pd.to_datetime(text_time[bad], format="mixed", errors="coerce")
        before, after = frame["time"].shift(1)[bad], frame["time"].shift(-1)[bad]
        implied = (before + pd.Timedelta(seconds=1)).fillna(after - pd.Timedelta(seconds=1))
        ok = implied.notna() & (implied.dt.floor("min") == loose.dt.floor("min"))
        frame.loc[ok[ok].index, "time"] = implied[ok]
    meta = {c: {"name_ja": j.strip(), "unit": u} for c, j, u in zip(codes[1:], header_ja[1:], units[1:]) if c}
    return frame, meta


def load(unit="tsukuba", start=None, end=None, version="raw", clean=False):
    """Load per-second rows between ``start`` and ``end`` (dates), indexed by local time with no zone assigned.

    The paper gives no time zone; its operating times (night charging, 13:00-16:00 peak, p. 3) read as Japan
    local time. ``version`` is "raw" or the publisher's "cleaned" files (errors blanked, timestamps kept, night
    negative PV power set to 0; paper p. 6-7). Columns are renamed from signal codes to English names (see
    ``NAMES``); units and the Japanese headers are in ``attrs["signals"]``. Positive ``battery_active_power`` and
    ``battery_dc_current`` mean discharging (from the data; the paper does not say). ``battery_soc`` is the
    EMS's SOC estimate, voltage-reset about weekly, and can exceed 100 % (paper p. 3, 7). The full span is about 100 million rows, so give a date
    range. ``clean=True`` blanks only the publisher error code -999,999 (``SENTINEL``, paper p. 6); the
    publisher's other removals are in ``version="cleaned"``.
    """
    table = files(version)
    lo = pd.Timestamp(start) if start is not None else table["first_day"].min()
    hi = pd.Timestamp(end) if end is not None else table["last_day"].max()
    pick = table[(table["last_day"] >= lo.normalize()) & (table["first_day"] <= hi)]
    frames, meta = [], {}
    with _outer() as z, zipfile.ZipFile(z.open(_VERSIONS[version])) as inner:
        for member in pick["member"]:
            with inner.open(member) as handle:
                frame, meta = _read(handle)
            masked = 0
            if clean:
                hit = frame.drop(columns="time") == SENTINEL
                masked = int(hit.to_numpy().sum())
                if masked:
                    frame[hit.columns] = frame[hit.columns].astype(float).mask(hit)
            frames.append(finish(frame, _PACKAGE, clean, masked))
    if not frames:  # no file covers the range (for example raw 2017-11-13 to 2017-11-24)
        frames = [finish(pd.DataFrame({"time": pd.Series(dtype="datetime64[ns]"), **{k: pd.Series(dtype=float) for k in NAMES}}),
                         _PACKAGE, clean, 0)]
    out = concat(frames, _PACKAGE, clean, version=version)
    out = out[(out["time"] >= lo) & (out["time"] < hi.normalize() + pd.Timedelta(days=1))]
    out = out.rename(columns=NAMES).set_index("time").sort_index(kind="stable")
    out.attrs.update({"unit": "tsukuba", "version": version, "signals": {NAMES.get(k, k): v for k, v in meta.items()}, "n_rows": len(out)})
    return out
