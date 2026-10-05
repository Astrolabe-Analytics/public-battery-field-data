"""Cloverleaf source-audit data checks (reports/source_audit_2026-10-04/cloverleaf.md, findings 1 and 4).

What it does, through fielddata.loaders.cloverleaf only (raw data, clean=False):
  1a. current sign: on each sheet, the correlation of Ipack with the next-row change of SOC (SOC[t+1] - SOC[t]), and
      the share of rows with Ipack > 0 where SOC rises; positive correlation means positive Ipack = charging;
  1b. time zone: the offset in hours between epoch_ms read as UTC and the released `date` column, tabulated by month;
  4.  the averaging note (row 1 of each sheet) and the units row (row 2) as the loader returns them.
Reads: SNAM/export.xlsx inside the released zip, through the loader.
Writes: prints only.
Run from the repo root: PYTHONPATH=. .venv/Scripts/python.exe <this file>
"""
from __future__ import annotations

import pandas as pd

from fielddata.loaders import cloverleaf

if __name__ == "__main__":
    pd.set_option("display.width", 200)
    sysdf = cloverleaf.systems()
    print(sysdf.to_string())
    for unit in sysdf["unit"]:
        df = cloverleaf.load(unit)
        print(f"\n== {unit}: {len(df)} rows; units row: {df.attrs.get('units')}")
        d_soc = df["SOC"].shift(-1) - df["SOC"]
        ok = df["Ipack"].notna() & d_soc.notna()
        corr = df.loc[ok, "Ipack"].corr(d_soc[ok])
        pos = ok & (df["Ipack"] > 0.5)
        neg = ok & (df["Ipack"] < -0.5)
        print(f"corr(Ipack, next dSOC) = {corr:.3f}; rows Ipack>0.5 A: {int(pos.sum())}, of which SOC rises: "
              f"{int((d_soc[pos] > 0).sum())}, falls: {int((d_soc[pos] < 0).sum())}; rows Ipack<-0.5 A: {int(neg.sum())}, "
              f"of which SOC rises: {int((d_soc[neg] > 0).sum())}, falls: {int((d_soc[neg] < 0).sum())}")
        utc = pd.to_datetime(df["epoch_ms"], unit="ms")
        offset_h = (df.index.to_series().reset_index(drop=True) - utc.reset_index(drop=True)).dt.total_seconds() / 3600
        months = df.index.to_series().dt.to_period("M").reset_index(drop=True)
        print("offset date - UTC(epoch_ms), hours, by month:")
        print(offset_h.groupby(months).agg(["min", "max", "count"]).to_string())
        print("first rows:", df[["epoch_ms"]].head(2).assign(utc=utc.head(2).values).to_string())
