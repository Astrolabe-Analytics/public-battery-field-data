"""Source-audit data checks for li2026 (energy-storage-station cell data, Zenodo 18471156).

What it does: loads every period/battery group through fielddata.loaders.li2026 (raw, clean=False)
and runs the checks listed in reports/source_audit_2026-10-04/li2026.md:
  1a  is the current identical across the 30 groups within a period (one series string)?
  1b  do per-cell voltage offsets and temperature ranks correlate between periods (same cells)?
  1c  how many cell channels per period are live (non-constant, nonzero voltage)?
  2   current sign: does group mean cell voltage fall during long cur > 0 stretches?
  3   which columns exist across all released CSVs (any label or status column)?
  4   voltage and current jumps at file boundaries compared with in-file steps; current step pattern
  6   raw voltage and temperature ranges.
What it reads: the released BatteryData.zip, only through the loader.
What it writes: <out_dir>/li2026_audit_checks.txt (and prints the same text).
Run from the repository root:
  PYTHONPATH=. .venv/Scripts/python.exe <this file> <out_dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fielddata.loaders import li2026 as m

out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
out_dir.mkdir(parents=True, exist_ok=True)
lines: list[str] = []


def say(text=""):
    print(text)
    lines.append(str(text))


sysdf = m.systems()
idx = m._index()
periods = sorted(sysdf["period"].unique())
say(f"li2026 audit checks, raw data (clean=False). Groups: {len(sysdf)}; periods: {periods}")

data = {}
columns = set()
for unit in sysdf["unit"]:
    frame = m.load(unit)
    columns |= set(frame.columns)
    data[unit] = frame.drop(columns="unit")

# 3. columns
other = sorted(c for c in columns if not (c.endswith("_V") or c.endswith("_T") or c in ("cur", "unit")))
say(f"\n[3] Column names across all {len(data)} groups ({len(idx)} files): {len(columns)} distinct; "
    f"columns other than cell_NNN_V, cell_NNN_T, cur, unit: {other if other else 'none'}")

# 1a. current identity across groups
say("\n[1a] Current across the 30 groups within each period (aligned on sample index), compared with battery_01")
for p in periods:
    units = sysdf.loc[sysdf["period"] == p, "unit"].tolist()
    cur = pd.DataFrame({u.split("/")[1]: data[u]["cur"] for u in units})
    ref = cur.iloc[:, 0]
    diff = cur.sub(ref, axis=0).abs()
    identical = (diff.max() == 0).sum()
    corr = cur.corr().to_numpy()[0]
    say(f"  {p}: groups with cur identical to battery_01 at every sample: {identical}/{len(units)}; "
        f"max |cur - cur_battery_01| over all groups = {diff.to_numpy().max():.3f} A; "
        f"median over groups of mean |diff| = {diff.mean().median():.3f} A; "
        f"min correlation with battery_01 = {np.nanmin(corr):.4f}; cur range {cur.min().min():.1f} to {cur.max().max():.1f} A")

# 1b and 1c: per-cell statistics per period
stats = []
for unit, frame in data.items():
    period = unit.split("/")[0]
    vcols = [c for c in frame.columns if c.endswith("_V")]
    tcols = [c for c in frame.columns if c.endswith("_T")]
    v = frame[vcols]
    t = frame[tcols]
    med = v.median(axis=1)
    off = v.sub(med, axis=0).mean()
    trank = t.rank(axis=1).mean()
    for vc, tc in zip(vcols, tcols):
        col = v[vc]
        live = bool(col.nunique(dropna=True) > 1 and (col.fillna(0) != 0).any())
        stats.append({"period": period, "cell": vc[5:8], "v_offset_mV": 1000 * off[vc], "t_rank": trank[tc],
                      "t_mean": t[tc].mean(), "live": live, "v_nan": int(col.isna().sum()),
                      "v_zero": int((col == 0).sum())})
stats = pd.DataFrame(stats)
say("\n[1c] Live voltage channels (more than one distinct value and not all zero), per period")
for p, g in stats.groupby("period"):
    say(f"  {p}: live {int(g['live'].sum())}/{len(g)}; NaN voltage samples {int(g['v_nan'].sum())}; "
        f"zero voltage samples {int(g['v_zero'].sum())}")

say("\n[1b] Correlation between periods of per-cell mean voltage offset from its group median (mV), "
    "mean temperature rank within its group, and mean temperature")
for key in ("v_offset_mV", "t_rank", "t_mean"):
    wide = stats.pivot(index="cell", columns="period", values=key)
    say(f"  {key}: Pearson\n" + wide.corr().round(3).to_string())
    say(f"  {key}: Spearman\n" + wide.corr(method="spearman").round(3).to_string())

# 2. sign convention
say("\n[2] Group mean cell voltage change over stretches of constant current sign (runs of at least 30 samples)")
rows = []
for unit, frame in data.items():
    vmean = frame[[c for c in frame.columns if c.endswith("_V")]].mean(axis=1).to_numpy()
    cur = frame["cur"].to_numpy()
    sign = np.sign(np.where(np.abs(cur) < 5, 0, cur))
    change = np.flatnonzero(np.diff(sign) != 0) + 1
    starts = np.r_[0, change]
    ends = np.r_[change, len(sign)]
    for a, b in zip(starts, ends):
        if b - a >= 30 and sign[a] != 0:
            rows.append({"sign": int(sign[a]), "dv": vmean[b - 1] - vmean[a], "n": b - a})
runs = pd.DataFrame(rows)
for s, g in runs.groupby("sign"):
    say(f"  cur {'> +5 A' if s > 0 else '< -5 A'}: {len(g)} runs; voltage fell in {(g['dv'] < 0).mean():.1%}; "
        f"median change {1000 * g['dv'].median():.1f} mV over median {int(g['n'].median())} samples")

# 4. file boundaries and step pattern
say("\n[4] Jumps at file boundaries compared with in-file sample-to-sample steps")
bj, fj, bc, fc = [], [], [], []
for unit, frame in data.items():
    v = frame[[c for c in frame.columns if c.endswith("_V")]].mean(axis=1)
    dv = v.diff().abs()
    dc = frame["cur"].diff().abs()
    bounds = idx.loc[idx["unit"] == unit, "t0"].to_numpy()[1:]
    mask = dv.index.isin(bounds)
    bj.append(dv[mask].dropna())
    fj.append(dv[~mask].dropna())
    bc.append(dc[mask].dropna())
    fc.append(dc[~mask].dropna())
bj, fj, bc, fc = (pd.concat(x) for x in (bj, fj, bc, fc))
say(f"  boundaries: {len(bj)}; in-file steps: {len(fj)}")
say(f"  |dV| group-mean voltage: in-file median {1000 * fj.median():.2f} mV, p99 {1000 * fj.quantile(.99):.2f} mV; "
    f"boundary median {1000 * bj.median():.2f} mV, p99 {1000 * bj.quantile(.99):.2f} mV; "
    f"share of boundary steps above in-file p99 {(bj > fj.quantile(.99)).mean():.1%}")
say(f"  |dI|: in-file median {fc.median():.2f} A, p99 {fc.quantile(.99):.2f} A; boundary median {bc.median():.2f} A, "
    f"p99 {bc.quantile(.99):.2f} A; share of boundary steps above in-file p99 {(bc > fc.quantile(.99)).mean():.1%}")
allcur = pd.concat([f["cur"] for f in data.values()])
dcur = pd.concat([f["cur"].diff() for f in data.values()]).dropna()
say(f"  current: {allcur.nunique()} distinct values; share of samples with cur exactly 0: {(allcur == 0).mean():.1%}; "
    f"share of consecutive samples with identical cur: {(dcur == 0).mean():.1%}")
say(f"  samples per group summed over periods: {int(sysdf.groupby('battery')['samples'].sum().iloc[0])}; "
    f"1,203 h / that = {1203 * 3600 / sysdf.groupby('battery')['samples'].sum().iloc[0]:.1f} s per sample")

# 6. ranges
say("\n[6] Raw ranges per period")
for p in periods:
    fr = [data[u] for u in sysdf.loc[sysdf["period"] == p, "unit"]]
    v = pd.concat([f[[c for c in f.columns if c.endswith("_V")]].stack() for f in fr])
    t = pd.concat([f[[c for c in f.columns if c.endswith("_T")]].stack() for f in fr])
    say(f"  {p}: voltage {v.min():.3f} to {v.max():.3f} V (outside 2.2 to 3.8 V: {int(((v < 2.2) | (v > 3.8)).sum())}); "
        f"temperature {t.min():.1f} to {t.max():.1f} (outside 0 to 60: {int(((t < 0) | (t > 60)).sum())})")

(out_dir / "li2026_audit_checks.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
