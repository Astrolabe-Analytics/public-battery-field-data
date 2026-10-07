"""Source-audit data checks for schaeffer (28 portable LFP systems, Zenodo 13715694).

What it does: streams every system through fielddata.loaders.schaeffer.load(system, chunksize=...)
(raw, clean=False) and records, per system: rows, first and last timestamp, finite current extremes and
counts beyond +-1000 A, +-inf and NaN counts per column, timestamp steps, nonzero U_CR / I_CR, exact-zero cell voltages, monthly row
counts and mean |I_Battery|, and 10-minute windows (mean current against the change in SOC_Battery).
These answer the checks in reports/source_audit_2026-10-04/schaeffer.md: the system ID mapping
(system 8 rows and dates, discharge outliers in systems 3, 4 and 16), the current sign, the total row
count and the sampling interval.
What it reads: the released field_data.zip, only through the loader.
What it writes, in <out_dir>: schaeffer_systems.csv (one row per system, appended as each system
finishes; systems already present are skipped on a rerun), schaeffer_monthly.csv, schaeffer_dt.csv
(timestamp-step counts) and schaeffer_audit_checks.txt (the summary, also printed).
Run from the repository root:
  PYTHONPATH=. .venv/Scripts/python.exe <this file> <out_dir>
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from fielddata.loaders import schaeffer as m

out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
out_dir.mkdir(parents=True, exist_ok=True)
sys_csv, month_csv, dt_csv = (out_dir / n for n in ("schaeffer_systems.csv", "schaeffer_monthly.csv", "schaeffer_dt.csv"))
done = set(pd.read_csv(sys_csv)["system"]) if sys_csv.exists() else set()
CELLS = [f"U_Cell_{i}" for i in range(1, 9)]

for system in m.systems()["system"]:
    if system in done:
        continue
    rows = 0
    first = last = prev = None
    imin, imax = np.inf, -np.inf
    below, above, backwards, zero_cells, cr_nonzero = 0, 0, 0, 0, 0
    dts: Counter = Counter()
    infs: Counter = Counter()
    nans: Counter = Counter()
    monthly = []
    windows = []
    for chunk in m.load(system, chunksize=2_000_000):
        ts = chunk["Timestamp"]
        rows += len(chunk)
        first = ts.min() if first is None else min(first, ts.min())
        last = ts.max() if last is None else max(last, ts.max())
        num = chunk.drop(columns="Timestamp")
        infs.update({k: int(v) for k, v in np.isinf(num).sum().items() if v})
        nans.update({k: int(v) for k, v in num.isna().sum().items() if v})
        nans.update({"Timestamp": int(chunk["Timestamp"].isna().sum())})
        cur = chunk["I_Battery"].where(np.isfinite(chunk["I_Battery"]))
        imin, imax = min(imin, cur.min()), max(imax, cur.max())
        below += int((cur < -1000).sum())
        above += int((cur > 1000).sum())
        zero_cells += int((chunk[CELLS] == 0).to_numpy().sum())
        cr_nonzero += int(((chunk["U_CR"].fillna(0) != 0) | (chunk["I_CR"].fillna(0) != 0)).sum())
        step = ts.diff()
        if prev is not None:
            step.iloc[0] = ts.iloc[0] - prev
        prev = ts.iloc[-1]
        sec = step.dt.total_seconds().dropna()
        backwards += int((sec < 0).sum())
        dts.update(np.where(sec > 3600, 3601, np.where(sec < 0, -1, np.round(sec))).astype(int).tolist())
        month = ts.dt.to_period("M")
        monthly.append(pd.DataFrame({"month": month, "abs_i": cur.abs()}).groupby("month")["abs_i"].agg(["size", "sum"]))
        key = ts.dt.floor("10min")
        g = pd.DataFrame({"key": key, "ts": ts, "soc": chunk["SOC_Battery"], "i": cur}).groupby("key")
        w = pd.DataFrame({"n": g.size(), "isum": g["i"].sum(), "t0": g["ts"].min(), "t1": g["ts"].max()})
        idx0 = g["ts"].idxmin()
        idx1 = g["ts"].idxmax()
        w["soc0"] = chunk.loc[idx0.to_numpy(), "SOC_Battery"].to_numpy()
        w["soc1"] = chunk.loc[idx1.to_numpy(), "SOC_Battery"].to_numpy()
        windows.append(w)
    w = pd.concat(windows).reset_index()
    w = w.sort_values("t0").groupby("key").agg(n=("n", "sum"), isum=("isum", "sum"), t0=("t0", "min"),
                                               t1=("t1", "max"), soc0=("soc0", "first"), soc1=("soc1", "last"))
    w["imean"] = w["isum"] / w["n"]
    w["dsoc"] = w["soc1"] - w["soc0"]
    full = w[(w["n"] >= 60) & (w["imean"].abs() > 5) & (w["dsoc"] != 0)]
    agree = float((np.sign(full["imean"]) == np.sign(full["dsoc"])).mean()) if len(full) else np.nan
    corr = float(np.corrcoef(w.loc[w["n"] >= 60, "imean"], w.loc[w["n"] >= 60, "dsoc"])[0, 1]) if (w["n"] >= 60).sum() > 2 else np.nan
    mon = pd.concat(monthly).groupby(level=0).sum()
    mon["system"] = system
    mon["mean_abs_i"] = mon["sum"] / mon["size"]
    mon.reset_index().rename(columns={"size": "rows"})[["system", "month", "rows", "mean_abs_i"]].to_csv(
        month_csv, mode="a", header=not month_csv.exists(), index=False)
    pd.DataFrame({"system": system, "dt_s": list(dts), "count": list(dts.values())}).sort_values("dt_s").to_csv(
        dt_csv, mode="a", header=not dt_csv.exists(), index=False)
    total_dt = sum(dts.values())
    srt = sorted(dts.items())
    cum, med = 0, None
    for k, c in srt:
        cum += c
        if cum >= total_dt / 2:
            med = k
            break
    row = {"system": system, "rows": rows, "first": first, "last": last, "i_min": imin, "i_max": imax,
           "i_below_-1000": below, "i_above_1000": above, "backward_steps": backwards, "zero_cell_values": zero_cells,
           "cr_nonzero_rows": cr_nonzero, "median_dt_s": med, "share_dt_5s": dts.get(5, 0) / total_dt if total_dt else np.nan,
           "inf_counts": ";".join(f"{k}:{v}" for k, v in sorted(infs.items())) or "none",
           "nan_counts": ";".join(f"{k}:{v}" for k, v in sorted(nans.items()) if v) or "none",
           "windows_used": len(full), "sign_agree_share": agree, "corr_imean_dsoc": corr}
    pd.DataFrame([row]).to_csv(sys_csv, mode="a", header=not sys_csv.exists(), index=False)
    print(row, flush=True)

# summary
s = pd.read_csv(sys_csv).sort_values("system")
lines = ["schaeffer audit checks, raw data (clean=False), all 28 systems streamed in full through the loader.", ""]
lines.append(f"[rows] total {int(s['rows'].sum()):,}; per system min {int(s['rows'].min()):,}, max {int(s['rows'].max()):,}")
r8 = s[s["system"] == 8].iloc[0]
lines.append(f"[id] system 8: {int(r8['rows']):,} rows, {r8['first']} to {r8['last']}")
mon = pd.read_csv(month_csv)
m8 = mon[mon["system"] == 8].sort_values("month")
lines.append("[id] system 8 monthly rows and mean |I_Battery| (A):")
lines.append("  " + "; ".join(f"{r.month} {int(r.rows)} {r.mean_abs_i:.2f}" for r in m8.itertuples()))
lines.append("[id] systems with I_Battery < -1000 A: " + ", ".join(
    f"{int(r['system'])} ({int(r['i_below_-1000'])} values, min {r['i_min']:.1f})" for r in s[s["i_below_-1000"] > 0].to_dict("records")))
lines.append("[id] systems with I_Battery > 1000 A: " + (", ".join(
    f"{int(r.system)} ({int(r.i_above_1000)} values, max {r.i_max:.1f})" for r in s[s["i_above_1000"] > 0].itertuples()) or "none"))
lines.append(f"[sign] 10-minute windows with at least 60 rows, |mean I| > 5 A and SOC change: {int(s['windows_used'].sum()):,}; "
             f"share where sign(mean I) = sign(SOC change), weighted over systems: "
             f"{(s['sign_agree_share'] * s['windows_used']).sum() / s['windows_used'].sum():.4f}; per system min "
             f"{s['sign_agree_share'].min():.4f}, median {s['sign_agree_share'].median():.4f}; correlation of mean I with SOC "
             f"change, median over systems {s['corr_imean_dsoc'].median():.3f}, min {s['corr_imean_dsoc'].min():.3f}")
dt = pd.read_csv(dt_csv).groupby("dt_s")["count"].sum()
tot = dt.sum()
cum = dt.sort_index().cumsum()
med = cum.index[cum >= tot / 2][0]
lines.append(f"[cadence] timestamp steps: {int(tot):,}; median {med} s; share exactly 5 s {dt.get(5, 0) / tot:.3f}; "
             f"share 1 to 10 s {dt[(dt.index >= 1) & (dt.index <= 10)].sum() / tot:.3f}; share 60 or 61 s "
             f"{(dt.get(60, 0) + dt.get(61, 0)) / tot:.3f}; steps over 1 h {int(dt.get(3601, 0))}; "
             f"zero steps (repeated timestamps) {int(dt.get(0, 0)):,}; backward steps {int(s['backward_steps'].sum())} "
             f"(systems {s.loc[s['backward_steps'] > 0, 'system'].tolist()})")
lines.append(f"[cadence] median step per system: {s.set_index('system')['median_dt_s'].astype(int).to_dict()}")
lines.append("[non-finite] +-inf values per system and column: " + "; ".join(
    f"{int(r.system)} {r.inf_counts}" for r in s[s["inf_counts"] != "none"].itertuples()))
lines.append("[non-finite] NaN values per system and column: " + ("; ".join(
    f"{int(r.system)} {r.nan_counts}" for r in s[s["nan_counts"] != "none"].itertuples()) or "none"))
lines.append(f"[other] rows with nonzero U_CR or I_CR: {int(s['cr_nonzero_rows'].sum()):,}; exact-zero cell voltages: "
             f"{int(s['zero_cell_values'].sum())}")
lines.append("[per system] " + s[["system", "rows", "first", "last", "i_min", "i_max"]].to_string(index=False).replace("\n", "\n  "))
text = "\n".join(lines)
print(text)
(out_dir / "schaeffer_audit_checks.txt").write_text(text + "\n", encoding="utf-8", newline="\n")
