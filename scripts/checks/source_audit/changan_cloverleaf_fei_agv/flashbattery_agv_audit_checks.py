"""flashbattery-agv source-audit data checks (reports/source_audit_2026-10-04/flashbattery-agv.md, findings 1, 2, 4, 5, 7).

What it does, through fielddata.load('flashbattery-agv') and fielddata.systems only (raw data, clean=False):
  7. the released battery labels;
  1. counter steps between consecutive rows of one pack (sorted by counter): how many are 1 and how many larger;
  2. cycletime unit: rows with cycletime == 0, share of cycletime values that are multiples of 60, and the average
     discharge current dQ / cycletime per row (dQ = step of totaldischarge between consecutive rows of one pack, Ah),
     computed as if cycletime were seconds (dQ * 3600 / t) and as if minutes (dQ * 60 / t);
  4. sentinels named in the paper (date 2000-01-01, -40 C, 215 C), and signs of imputation: consecutive rows with both
     temperatures unchanged, and rows whose totaldischarge is exactly the mean of its two neighbours (linear fill);
  5. whether maxtemperature >= mintemperature in every row (the README.adoc descriptions of the two are swapped).
Reads: dataset.csv through the loader.
Writes: prints only.
Run from the repo root: PYTHONPATH=. .venv/Scripts/python.exe <this file>
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import fielddata

if __name__ == "__main__":
    pd.set_option("display.width", 220)
    sysdf = fielddata.systems("flashbattery-agv")
    print("labels:", sysdf["unit"].tolist())
    print(sysdf.to_string())
    df = fielddata.load("flashbattery-agv").reset_index()
    print("rows:", len(df))
    df = df.sort_values(["unit", "counter"], kind="stable")
    g = df.groupby("unit", sort=False)
    step = g["counter"].diff()
    print("\n[1] counter step between consecutive rows of one pack:")
    print("  step == 1:", int((step == 1).sum()), " step > 1:", int((step > 1).sum()),
          " step == 0:", int((step == 0).sum()), " step < 0:", int((step < 0).sum()))
    print("  step quantiles (5, 25, 50, 75, 95, 99%):", step.quantile([.05, .25, .5, .75, .95, .99]).tolist())
    t = df["cycletime"]
    print("\n[2] cycletime: min", int(t.min()), "max", int(t.max()), "median", float(t.median()))
    print("  rows with cycletime == 0:", int((t == 0).sum()))
    print("  share of cycletime values that are multiples of 60:", round(float((t % 60 == 0).mean()), 4))
    print("  cycletime > 7200:", int((t > 7200).sum()), " > 14400:", int((t > 14400).sum()))
    dq = g["totaldischarge"].diff()
    ok = dq.notna() & (t > 0)
    i_s = dq[ok] * 3600 / t[ok]
    i_m = dq[ok] * 60 / t[ok]
    q = [.05, .25, .5, .75, .95]
    print("  dQ per row (Ah) quantiles:", dq[ok].quantile(q).round(2).tolist(), " dQ < 0 rows:", int((dq < 0).sum()))
    print("  current if seconds (A) quantiles:", i_s.quantile(q).round(2).tolist(),
          " share 5..100 A:", round(float(((i_s >= 5) & (i_s <= 100)).mean()), 4))
    print("  current if minutes (A) quantiles:", i_m.quantile(q).round(3).tolist(),
          " share 5..100 A:", round(float(((i_m >= 5) & (i_m <= 100)).mean()), 4))
    keep = ok & (dq * 3600 / t.where(t > 0) >= 5) & (t <= 120 * 60)
    share = keep[ok].groupby(df.loc[ok, "unit"]).mean().round(3)
    print("  paper Sec. V selection (average current >= 5 A with cycletime in s, cycletime <= 120 min), share kept per pack:",
          share.to_dict(), " all packs:", round(float(keep[ok].mean()), 3))
    next_dq = g["totaldischarge"].diff().shift(-1)
    both = dq.notna() & next_dq.notna()
    print("  share of consecutive equal totaldischarge steps among rows with both steps:",
          round(float((dq[both] == next_dq[both]).mean()), 3))
    print("\n[4] sentinels: date 2000-01-01:", int((df["date"] == pd.Timestamp("2000-01-01")).sum()),
          " min date:", df["date"].min().date(), " max date:", df["date"].max().date())
    for c in ("mintemperature", "maxtemperature"):
        print(f"  {c}: min {df[c].min()} max {df[c].max()}; == -40: {int((df[c] == -40).sum())}; == 215: {int((df[c] == 215).sum())}; "
              f"missing: {int(df[c].isna().sum())}")
    print("  missing values per column:", df.isna().sum().to_dict())
    same_t = (g["mintemperature"].diff() == 0) & (g["maxtemperature"].diff() == 0)
    print("  consecutive rows with both temperatures unchanged:", int(same_t.sum()), "of", int(g["mintemperature"].diff().notna().sum()))
    prev_q = g["totaldischarge"].shift(1)
    next_q = g["totaldischarge"].shift(-1)
    linear = (prev_q.notna() & next_q.notna() & (prev_q != next_q)
              & (df["totaldischarge"] * 2 == prev_q + next_q))
    print("  rows whose totaldischarge is exactly the mean of its neighbours (prev != next):", int(linear.sum()),
          "of", int((prev_q.notna() & next_q.notna()).sum()))
    print("  rows with totaldischarge step 0 (no discharge recorded):", int((dq == 0).sum()))
    print("  totaldischarge integer-valued:", bool((df["totaldischarge"] % 1 == 0).all()),
          "; temperatures integer-valued:", bool(((df["mintemperature"] % 1 == 0) & (df["maxtemperature"] % 1 == 0)).all()))
    print("\n[5] rows with maxtemperature < mintemperature:", int((df["maxtemperature"] < df["mintemperature"]).sum()),
          "; equal:", int((df["maxtemperature"] == df["mintemperature"]).sum()))
