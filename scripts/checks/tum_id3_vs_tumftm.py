"""Is the ID.3 in the TUM 2022 powertrain release (tum_id3_2022) the same car as tumftm's ID1 (or ID2)?

What it does: reads the time, hv_soc and hv_battery_voltage columns of every tum_id3_2022 track CSV (no loader exists
yet for that candidate, so the CSVs are read directly, read-only), and loads hv_soc (value_id 900) and
hv_battery_voltage (value_id 1200) for ID1 and ID2 through the tumftm loader. Neither release states a time zone, so
it tries whole-hour offsets from -3 to +3 h. For each vehicle and offset it pairs every tumftm row inside a track's
time window with the nearest track row within 2 s, and reports how many pairs there are and the median absolute
difference. A same-car match shows many pairs and near-zero differences at one offset. All values raw.

Reads: the tum_id3_2022 track CSVs under the data folder, and tumftm through fielddata.loaders.tumftm.
Writes: reports/candidates/tum_id3_2022/overlap_tumftm.txt

Run:
    python scripts/checks/tum_id3_vs_tumftm.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fielddata import fetch  # noqa: E402
from fielddata.loaders import tumftm  # noqa: E402

OUT = ROOT / "reports" / "candidates" / "tum_id3_2022" / "overlap_tumftm.txt"
SIGNALS = {900: "hv_soc", 1200: "hv_battery_voltage"}


def tracks() -> pd.DataFrame:
    folder = fetch.plan_package("tum_id3_2022").destination / "Data" / "Tracks"
    frames = []
    for path in sorted(folder.glob("track_*.csv")):
        header = path.open(encoding="utf-8", errors="replace").readline().strip().split(",")
        use = [c for c in ("time", *SIGNALS.values()) if c in header]
        frame = pd.read_csv(path, usecols=use)
        frame["track"] = path.stem
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    data["time"] = pd.to_datetime(data["time"], unit="ms").astype("datetime64[ns]")  # ms since 1970 (value_definitions.csv), zone not stated
    return data.sort_values("time")


def main() -> int:
    tum = tracks()
    windows = tum.groupby("track")["time"].agg(["min", "max"])
    lines = [f"tum_id3_2022: {len(windows)} tracks, {tum['time'].min()} to {tum['time'].max()} (time column read as UTC-naive)"]
    for unit in ("ID1", "ID2"):
        ref = tumftm.load(unit, value_id=list(SIGNALS), clean=True)
        ref = ref.dropna(subset=["time"])
        lines.append(f"tumftm {unit}: {len(ref):,} rows of hv_soc and hv_battery_voltage, {ref['time'].min()} to {ref['time'].max()}")
        for hours in range(-3, 4):
            for value_id, name in SIGNALS.items():
                side = ref[ref["value_id"] == value_id][["time", "value"]].copy()
                side["time"] = side["time"].astype("datetime64[ns]") + pd.Timedelta(hours=hours)
                inside = pd.concat([side[(side["time"] >= lo) & (side["time"] <= hi)] for lo, hi in windows.itertuples(index=False)])
                if inside.empty:
                    lines.append(f"  offset {hours:+d} h, {name}: no {unit} rows inside the track windows")
                    continue
                paired = pd.merge_asof(inside.sort_values("time"), tum[["time", name]].dropna().sort_values("time"),
                                       on="time", direction="nearest", tolerance=pd.Timedelta(seconds=2)).dropna()
                diff = (paired["value"] - paired[name]).abs()
                lines.append(f"  offset {hours:+d} h, {name}: {len(inside):,} {unit} rows inside track windows, {len(paired):,} paired within 2 s, "
                             f"median |difference| {diff.median():.4g}" if len(paired) else
                             f"  offset {hours:+d} h, {name}: {len(inside):,} {unit} rows inside track windows, none paired within 2 s")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
