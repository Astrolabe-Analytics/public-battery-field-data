"""Deng source-audit data checks (2026-10-04).

What it does: for every released pack, loads the raw data through the loader
(`fielddata.loaders.deng.load_raw` and `load`, clean=False) and measures
  1. whether `number` is a row counter (0..n-1 in file order) or a vehicle id;
  2. charging sessions (split at gaps > 10 s, as the authors' capacity_extract.py does)
     and the hour of day of session starts, read as the released clock value;
  3. pack_voltage / 90 at 45 to 55 % SOC (all rows, and rows with |I| <= 10 A);
  4. whether available_capacity / available_energy rise with SOC inside a session
     (Pearson r per session) and their ratio to SOC (implied full value);
  5. the authors' Q/dSOC session capacity (Eq. 1, capacity_extract.py filters) and its
     monthly median against the monthly median of available_capacity / (soc/100);
  6. the sign of charge_current.
Reads: the released deng archives through the loader only.
Writes into <out_dir>: deng_packs.csv (one row per pack, written incrementally),
deng_hours.csv (session-start hour histogram), deng_monthly.csv, deng_summary.txt.
Run from the repo root: PYTHONPATH=. .venv/Scripts/python.exe <this file> <out_dir>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fielddata.loaders import deng

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
packs_csv = out / "deng_packs.csv"
done = set(pd.read_csv(packs_csv)["pack"].astype(str)) if packs_csv.exists() else set()

hours_rows, monthly_rows = [], []
if (out / "deng_hours.csv").exists():
    hours_rows = pd.read_csv(out / "deng_hours.csv").to_dict("records")
if (out / "deng_monthly.csv").exists():
    monthly_rows = pd.read_csv(out / "deng_monthly.csv").to_dict("records")

for archive in deng._archives():
    pack = archive.stem
    if pack in done:
        continue
    raw = deng.load_raw(pack)
    num = raw["number"].to_numpy()
    number_is_rowcounter = bool(np.array_equal(num, np.arange(len(raw))))
    frame = deng.load(pack)
    t = frame.index.tz_localize(None)  # released clock value; the loader labels it UTC
    frame = frame.reset_index(drop=True)
    frame["t"] = t
    gap = frame["t"].diff().dt.total_seconds()
    sess = (gap.isna() | (gap > 10)).cumsum()
    frame["sess"] = sess
    g = frame.groupby("sess")
    starts = g["t"].first()
    sizes = g.size()
    for h, n in starts.dt.hour.value_counts().sort_index().items():
        hours_rows.append({"pack": pack, "hour": int(h), "sessions": int(n)})

    mid = frame[(frame["soc"] >= 45) & (frame["soc"] <= 55)]
    low = mid[mid["charge_current"].abs() <= 10]

    # per-session correlation of available_* with soc (sessions >= 100 rows, SOC swing >= 10)
    r_cap, r_en, ratio_cap = [], [], []
    caps = []
    for _, s in g:
        if len(s) < 100:
            continue
        soc = s["soc"].to_numpy()
        if soc[-1] - soc[0] >= 10:
            if s["available_capacity"].std() > 0 and s["soc"].std() > 0:
                r_cap.append(np.corrcoef(soc, s["available_capacity"])[0, 1])
            if s["available_energy"].std() > 0 and s["soc"].std() > 0:
                r_en.append(np.corrcoef(soc, s["available_energy"])[0, 1])
        # authors' Eq. (1) filters (capacity_extract.py): no SOC step > 2 or < -0.1
        d = np.diff(soc)
        if (d > 2).any() or (d < -0.1).any():
            continue
        dsoc = soc[-1] - soc[0]
        if dsoc == 0:
            continue
        sec = (s["t"] - s["t"].iloc[0]).dt.total_seconds().to_numpy()
        q = -np.trapezoid(s["charge_current"].to_numpy(), sec) / 3600
        endrow = s.iloc[-1]
        caps.append({"month": endrow["t"].strftime("%Y-%m"), "dsoc": dsoc, "cap_qdsoc": q / dsoc * 100,
                     "avail_over_soc": endrow["available_capacity"] / (endrow["soc"] / 100) if endrow["soc"] > 0 else np.nan})
    caps = pd.DataFrame(caps)
    good = caps[caps["dsoc"] >= 20] if len(caps) else caps
    if len(good):
        for m, gm in good.groupby("month"):
            monthly_rows.append({"pack": pack, "month": m, "n": len(gm), "median_cap_qdsoc": gm["cap_qdsoc"].median(),
                                 "median_avail_over_soc": gm["avail_over_soc"].median()})
    pos = frame["soc"] > 5
    row = {
        "pack": pack, "rows": len(frame), "number_is_rowcounter": number_is_rowcounter,
        "number_nunique": int(raw["number"].nunique()), "number_monotonic_in_file": bool(raw["number"].is_monotonic_increasing),
        "file_time_sorted": bool(pd.Series(raw["record_time"]).is_monotonic_increasing),
        "sessions": int(len(sizes)), "sessions_ge100": int((sizes >= 100).sum()),
        "vcell_mid_all_median": float((mid["pack_voltage"] / 90).median()), "rows_mid": len(mid),
        "vcell_mid_lowI_median": float((low["pack_voltage"] / 90).median()) if len(low) else np.nan, "rows_mid_lowI": len(low),
        "avgcell_mid_median": float(((mid["max_cell_voltage"] + mid["min_cell_voltage"]) / 2).median()),
        "r_cap_sessions": len(r_cap), "r_cap_median": float(np.median(r_cap)) if r_cap else np.nan,
        "r_cap_frac_gt_0p9": float(np.mean(np.array(r_cap) > 0.9)) if r_cap else np.nan,
        "r_en_median": float(np.median(r_en)) if r_en else np.nan,
        "r_en_frac_gt_0p9": float(np.mean(np.array(r_en) > 0.9)) if r_en else np.nan,
        "avail_cap_over_soc_median": float((frame.loc[pos, "available_capacity"] / (frame.loc[pos, "soc"] / 100)).median()),
        "avail_en_over_soc_median": float((frame.loc[pos, "available_energy"] / (frame.loc[pos, "soc"] / 100)).median()),
        "avail_cap_max": float(frame["available_capacity"].max()), "avail_en_max": float(frame["available_energy"].max()),
        "qdsoc_sessions_dsoc20": int(len(good)), "qdsoc_median": float(good["cap_qdsoc"].median()) if len(good) else np.nan,
        "current_lt0": int((frame["charge_current"] < 0).sum()), "current_eq0": int((frame["charge_current"] == 0).sum()),
        "current_gt0": int((frame["charge_current"] > 0).sum()),
        "first_month_qdsoc_median": float(good.groupby("month")["cap_qdsoc"].median().iloc[0]) if len(good) else np.nan,
        "last_month_qdsoc_median": float(good.groupby("month")["cap_qdsoc"].median().iloc[-1]) if len(good) else np.nan,
    }
    pd.DataFrame([row]).to_csv(packs_csv, mode="a", header=not packs_csv.exists(), index=False)
    pd.DataFrame(hours_rows).to_csv(out / "deng_hours.csv", index=False)
    pd.DataFrame(monthly_rows).to_csv(out / "deng_monthly.csv", index=False)
    print(pack, "done", flush=True)

p = pd.read_csv(packs_csv)
h = pd.DataFrame(hours_rows).groupby("hour")["sessions"].sum()
m = pd.DataFrame(monthly_rows)
lines = [
    f"packs {len(p)}, rows {p['rows'].sum()}",
    f"number is 0..n-1 in file order: {int(p['number_is_rowcounter'].sum())} of {len(p)} packs; file rows time-sorted: {int(p['file_time_sorted'].sum())}",
    f"sessions (gap > 10 s): {p['sessions'].sum()}, with >= 100 rows: {p['sessions_ge100'].sum()}",
    "session-start hour histogram (clock value as released): " + ", ".join(f"{k}:{v}" for k, v in h.items()),
    f"pack_voltage/90 at SOC 45-55 %: median over packs {p['vcell_mid_all_median'].median():.3f} V (range {p['vcell_mid_all_median'].min():.3f} to {p['vcell_mid_all_median'].max():.3f}); |I|<=10 A rows {p['rows_mid_lowI'].sum()}, median over packs with rows {p['vcell_mid_lowI_median'].median():.3f} V",
    f"(max+min cell)/2 at SOC 45-55 %: median over packs {p['avgcell_mid_median'].median():.3f} V",
    f"available_capacity vs soc within sessions (>=100 rows, dSOC >= 10): {p['r_cap_sessions'].sum()} sessions, median r per pack {p['r_cap_median'].min():.3f} to {p['r_cap_median'].max():.3f}, fraction r > 0.9 per pack {p['r_cap_frac_gt_0p9'].min():.3f} to {p['r_cap_frac_gt_0p9'].max():.3f}",
    f"available_energy vs soc: median r per pack {p['r_en_median'].min():.3f} to {p['r_en_median'].max():.3f}, fraction r > 0.9 per pack {p['r_en_frac_gt_0p9'].min():.3f} to {p['r_en_frac_gt_0p9'].max():.3f}",
    f"available_capacity/(soc/100) median per pack {p['avail_cap_over_soc_median'].min():.1f} to {p['avail_cap_over_soc_median'].max():.1f} Ah; available_energy/(soc/100) {p['avail_en_over_soc_median'].min():.2f} to {p['avail_en_over_soc_median'].max():.2f} kWh",
    f"max available_capacity {p['avail_cap_max'].max():.2f} Ah, max available_energy {p['avail_en_max'].max():.2f} kWh",
    f"Q/dSOC sessions (authors' filters, dSOC >= 20): {p['qdsoc_sessions_dsoc20'].sum()}, median per pack {p['qdsoc_median'].min():.1f} to {p['qdsoc_median'].max():.1f} Ah",
    f"monthly medians: Q/dSOC minus available_capacity/(soc/100) at session end: median {(m['median_cap_qdsoc'] - m['median_avail_over_soc']).median():.2f} Ah over {len(m)} pack-months; correlation {m[['median_cap_qdsoc', 'median_avail_over_soc']].corr().iloc[0, 1]:.3f}",
    f"charge_current rows < 0: {p['current_lt0'].sum()}, = 0: {p['current_eq0'].sum()}, > 0: {p['current_gt0'].sum()}",
]
(out / "deng_summary.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
