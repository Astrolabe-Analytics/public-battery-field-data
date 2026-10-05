"""Source-audit data checks for zhou2026 (Vehicle data.zip, three released vins).

What it does: loads each released vin through fielddata.loaders.zhou2026.load (raw, clean=False) and runs
the checks listed in reports/source_audit_2026-10-04/zhou2026.md:
  2  processing state: duplicate timestamps, timestamp steps, rows the authors' own preprocessing drops
     (SOC <= 0, TotalVoltage <= 0, NaN), share of rows charging, and linear runs in MaxCellVoltage
  4  current sign: share of TotalCurrent < 0 while ChargingStatus == 1, and > 0 while VehicleStatus == 1
     and not charging
  5  medians and ranges of the voltage columns, TotalVoltage, MaxTemp/MinTemp, and the distinct status codes
  6  number of entries in CellTemperatures and CellVoltages per row, against TotalCells (first partition)
All scalar columns are read for every partition of each vin; the per-cell strings only for partition 0.
What it reads: the released Vehicle data.zip, only through the loader.
What it writes: <out_dir>/zhou2026_audit_checks.txt (and prints the same text).
Run from the repository root:
  PYTHONPATH=. .venv/Scripts/python.exe <this file> <out_dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fielddata.loaders import zhou2026 as m

out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
out_dir.mkdir(parents=True, exist_ok=True)
lines: list[str] = []


def say(text=""):
    print(text, flush=True)
    lines.append(str(text))


SCALARS = ["VehicleStatus", "ChargingStatus", "Speed", "Mileage", "TotalVoltage", "TotalCurrent", "SOC",
           "MaxCellVoltage", "MinCellVoltage", "MaxTemp", "MinTemp", "TotalCells", "TotalPacks"]
say("zhou2026 audit checks, raw data (clean=False).")
for vin in m.systems()["unit"]:
    f = m.load(vin, columns=SCALARS)
    n = len(f)
    say(f"\n== {vin}: {n:,} rows, {f.index.min()} to {f.index.max()}")
    ts = f.index.to_series()
    say(f"  [2] unparsable timestamps: {int(ts.isna().sum())}; duplicate timestamps: {int(ts.duplicated().sum()):,} "
        f"({ts.duplicated().mean():.2%}); fully duplicated rows (timestamp and all scalar columns): "
        f"{int(f.reset_index().duplicated().sum()):,}")
    dt = ts.drop_duplicates().diff().dt.total_seconds().dropna()
    bins = [0, 9, 10, 11, 20, 21, 60, 300, 3600, 86400, np.inf]
    say(f"  [2] steps between distinct timestamps: median {dt.median():.0f} s; exactly 10 s {(dt == 10).mean():.1%}; "
        "histogram " + "; ".join(f"{k}: {v}" for k, v in pd.cut(dt, bins, right=False).value_counts().sort_index().items()))
    nan = f[SCALARS].isna().sum()
    say(f"  [2] NaN per column: {nan[nan > 0].to_dict() or 'none'}; SOC <= 0: {int((f['SOC'] <= 0).sum()):,}; "
        f"TotalVoltage <= 0: {int((f['TotalVoltage'] <= 0).sum()):,}")
    mx = f["MaxCellVoltage"].to_numpy(dtype=float)
    tsec = ts.to_numpy().astype("datetime64[s]").astype(np.int64)
    d1 = np.diff(mx)
    same_step = np.diff(tsec)
    lin = (d1[1:] == d1[:-1]) & (d1[1:] != 0) & (same_step[1:] == 10) & (same_step[:-1] == 10)
    say(f"  [2] MaxCellVoltage: rows inside a run of three equal nonzero 10-s steps (linear-interpolation signature): "
        f"{int(lin.sum()):,} of {len(lin):,} ({lin.mean():.2%})")
    vs = f["VehicleStatus"].value_counts(dropna=False).sort_index()
    cs = f["ChargingStatus"].value_counts(dropna=False).sort_index()
    say(f"  [5] VehicleStatus values: {vs.to_dict()}")
    say(f"  [5] ChargingStatus values: {cs.to_dict()}")
    chg = f["ChargingStatus"] == 1
    drv = (f["VehicleStatus"] == 1) & ~chg & (f["Speed"] > 0)
    say(f"  [2] share of rows with ChargingStatus == 1: {chg.mean():.1%}")
    say(f"  [4] ChargingStatus == 1: {int(chg.sum()):,} rows, TotalCurrent < 0 in {(f.loc[chg, 'TotalCurrent'] < 0).mean():.1%}, "
        f"> 0 in {(f.loc[chg, 'TotalCurrent'] > 0).mean():.1%}; median {f.loc[chg, 'TotalCurrent'].median():.1f}")
    say(f"  [4] VehicleStatus == 1, not charging, Speed > 0: {int(drv.sum()):,} rows, TotalCurrent > 0 in "
        f"{(f.loc[drv, 'TotalCurrent'] > 0).mean():.1%}, < 0 in {(f.loc[drv, 'TotalCurrent'] < 0).mean():.1%}; "
        f"median {f.loc[drv, 'TotalCurrent'].median():.1f}")
    # SOC change against current over consecutive 10 s rows while charging
    soc_d = f["SOC"].diff().to_numpy()
    say(f"  [4] consecutive 10-s rows with SOC change: SOC rose with TotalCurrent < -5 in "
        f"{np.mean(soc_d[1:][(same_step == 10) & (f['TotalCurrent'].to_numpy()[1:] < -5) & (soc_d[1:] != 0)] > 0):.1%}; "
        f"SOC fell with TotalCurrent > 5 in "
        f"{np.mean(soc_d[1:][(same_step == 10) & (f['TotalCurrent'].to_numpy()[1:] > 5) & (soc_d[1:] != 0)] < 0):.1%}")
    for c in ("MaxCellVoltage", "MinCellVoltage", "TotalVoltage", "TotalCurrent", "SOC", "MaxTemp", "MinTemp", "Speed", "Mileage"):
        s = f[c]
        say(f"  [5] {c}: median {s.median():g}, 1st percentile {s.quantile(.01):g}, 99th {s.quantile(.99):g}, "
            f"min {s.min():g}, max {s.max():g}")
    say(f"  [5] TotalCells values: {f['TotalCells'].value_counts().to_dict()}; TotalPacks values: "
        f"{f['TotalPacks'].value_counts().to_dict()}")
    del f
    p = m.load(vin, columns=["CellVoltages", "CellTemperatures", "TotalCells", "MaxTemp", "MinTemp",
                             "MaxCellVoltage", "MinCellVoltage"], part=0)
    nv = p["CellVoltages"].astype(str).str.replace(r"^\d+:", "", regex=True).str.count("_") + 1
    nt = p["CellTemperatures"].astype(str).str.replace(r"^\d+:", "", regex=True).str.count("_") + 1
    say(f"  [6] partition 0 ({len(p):,} rows): entries in CellVoltages {nv.value_counts().head(5).to_dict()}; "
        f"in CellTemperatures {nt.value_counts().head(5).to_dict()}; TotalCells {p['TotalCells'].value_counts().head(3).to_dict()}")
    temps = m.expand_cells(p, "CellTemperatures").stack()
    volts = m.expand_cells(p, "CellVoltages").stack()
    say(f"  [6] partition 0: expanded cell temperatures {temps.min():g} to {temps.max():g}; "
        f"expanded cell voltages {volts.min():g} to {volts.max():g}, median {volts.median():g}")
    tw = m.expand_cells(p, "CellTemperatures")
    vw = m.expand_cells(p, "CellVoltages")
    valid = tw.where(tw != 255)
    say(f"  [6] partition 0: probe values equal to 255: {int((tw == 255).to_numpy().sum()):,} of {tw.size:,}; "
        f"MaxTemp equal to 255: {int((p['MaxTemp'] == 255).sum()):,} of {len(p):,}")
    ok = p["MaxTemp"] != 255
    say(f"  [6] partition 0, rows with MaxTemp != 255: max probe value - 40 equals MaxTemp in "
        f"{(valid.max(axis=1)[ok] - 40 == p.loc[ok, 'MaxTemp']).mean():.1%}, equals MaxTemp without offset in "
        f"{(valid.max(axis=1)[ok] == p.loc[ok, 'MaxTemp']).mean():.1%}; min probe value - 40 equals MinTemp in "
        f"{(valid.min(axis=1) - 40 == p['MinTemp']).mean():.1%}")
    say(f"  [6] partition 0: max cell voltage in CellVoltages equals MaxCellVoltage in "
        f"{(vw.max(axis=1) == p['MaxCellVoltage']).mean():.1%}; min equals MinCellVoltage in "
        f"{(vw.min(axis=1) == p['MinCellVoltage']).mean():.1%}")
    del p

(out_dir / "zhou2026_audit_checks.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
