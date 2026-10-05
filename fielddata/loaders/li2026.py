"""Loader for the li2026 energy-storage-station cell data (Zenodo 18471156)."""
from __future__ import annotations

import re
import zipfile

import pandas as pd

from fielddata.loaders._base import as_list, check_unit, concat, directory, finish

_PACKAGE = "li2026"
_ARCHIVE = "BatteryData.zip"
_NAME = re.compile(r"BatteryData/(?P<period>[^/]+)/battery_(?P<battery>\d+)_cells_(?P<first>\d{3})-(?P<last>\d{3})_t_(?P<t0>\d+)-(?P<t1>\d+)\.csv$")


def _index():
    with zipfile.ZipFile(directory(_PACKAGE) / _ARCHIVE) as z:
        rows = [dict(m.groupdict(), member=n) for n in z.namelist() if (m := _NAME.match(n))]
    frame = pd.DataFrame(rows)
    for c in ("battery", "first", "last", "t0", "t1"):
        frame[c] = frame[c].astype(int)
    frame["unit"] = frame["period"] + "/battery_" + frame["battery"].map("{:02d}".format)
    return frame.sort_values(["period", "battery", "t0"])


def systems():
    """One row per recording period and 8-cell battery group. There is no calendar time in the release.

    Three periods (folder names) each hold battery groups 1 to 30 with cells 1 to 240. Within a period the
    current is identical in all 30 groups (one series string); the paper says "stations" and gives no count.
    """
    idx = _index()
    g = idx.groupby("unit")
    return pd.DataFrame({"unit": list(g.groups), "period": g["period"].first().to_numpy(),
                         "battery": g["battery"].first().to_numpy(), "first_cell": g["first"].first().to_numpy(),
                         "last_cell": g["last"].first().to_numpy(), "samples": (g["t1"].max() - g["t0"].min() + 1).to_numpy(),
                         "files": g.size().to_numpy()})


def load(unit, clean=False):
    """Load one or more ``period/battery_NN`` groups, indexed by ``sample`` (the file-name sample index).

    Columns as released: vol_1..vol_8 (V), temp_1..temp_8 (C), cur (A), renamed to the global cell numbers
    ``cell_NNN_V`` and ``cell_NNN_T``. Units are inferred from value ranges (no source states them). ``cur`` is
    the pack current, positive = discharge (paper p. 4). Whether the files are raw or processed is not stated;
    there is no time column, time zone not stated, and no fault labels. ``clean`` has no effect.
    """
    idx = _index()
    frames = []
    with zipfile.ZipFile(directory(_PACKAGE) / _ARCHIVE) as z:
        for item in as_list(unit, idx["unit"].unique()):
            name = check_unit(item, idx["unit"].unique(), _PACKAGE)
            parts = []
            for row in idx[idx["unit"] == name].itertuples():
                part = pd.read_csv(z.open(row.member))
                part.index = pd.RangeIndex(row.t0, row.t0 + len(part), name="sample")
                parts.append(part)
            frame = pd.concat(parts)
            first = int(idx.loc[idx["unit"] == name, "first"].iloc[0])
            frame = frame.rename(columns={**{f"vol_{i}": f"cell_{first + i - 1:03d}_V" for i in range(1, 9)},
                                          **{f"temp_{i}": f"cell_{first + i - 1:03d}_T" for i in range(1, 9)}})
            frame["unit"] = name
            frames.append(finish(frame, _PACKAGE, clean, 0, unit=name))
    return concat(frames, _PACKAGE, clean)
