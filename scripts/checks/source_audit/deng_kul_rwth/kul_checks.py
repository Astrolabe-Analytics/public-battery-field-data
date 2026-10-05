"""ku_leuven_bev source-audit data checks (2026-10-04).

What it does, through the loader only (raw data, clean=False):
  1. lists session files dated outside the paper's collection periods (Table 3: BEV1 2024-07-23 to
     2025-02-18, BEV2 2024-05-08 to 2025-04-30) and compares each file's name date with the
     dates of its own `Timestamp` values;
  2. current sign: per charging session (slow and fast), the SOC change and the share of rows with
     RawBattCurrent132 < 0 and > 0 while charging power flows (ChargeLinePower264 > 0.5 kW for slow,
     FC_dcCurrent > 1 A for fast); and during driving the sign of current when speed is zero vs high;
  3. per vehicle and session type: rows, first and last Timestamp, median time step;
  4. the value 4294967.295 in Odometer3B6 (0xFFFFFFFF / 1000, observed) and other repeated maxima.
Reads: the released ku_leuven_bev archive through fielddata.loaders.ku_leuven_bev.
Writes into <out_dir>: kul_sessions_outside.csv, kul_sign.csv, kul_coverage.csv, kul_summary.txt.
Run from the repo root: PYTHONPATH=. .venv/Scripts/python.exe <this file> <out_dir>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fielddata.loaders import ku_leuven_bev as k

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
PERIOD = {"BEV1": ("2024-07-23", "2025-02-18"), "BEV2": ("2024-05-08", "2025-04-30")}
lines = []

s = k.sessions()
outside_rows, sign_rows, cov_rows = [], [], []
odo_sentinel = {}
for unit in ["BEV1", "BEV2"]:
    lo, hi = (pd.Timestamp(x) for x in PERIOD[unit])
    for stype in ["slow charging", "fast charging", "driving", "parking"]:
        f = k.load(unit, session_type=stype)
        idx = f.index
        step = pd.Series(idx).groupby(f["session"].to_numpy()).diff().dt.total_seconds()
        cov_rows.append({"unit": unit, "type": stype, "files": f["session"].nunique(), "rows": len(f),
                         "first": idx.min(), "last": idx.max(), "median_step_s": float(step.median()),
                         "share_step_1s": float((step == 1).mean())})
        odo = f["Odometer3B6"] if "Odometer3B6" in f else pd.Series(dtype=float)
        odo_sentinel[(unit, stype)] = (int((odo == 4294967.295).sum()), int(odo.notna().sum()))
        files = s[(s["unit"] == unit) & (s["type"] == stype)]
        for row in files.itertuples():
            if row.date < lo or row.date > hi:
                name = row.member.rsplit("/", 1)[-1]
                t = f.index[f["session"] == name]
                outside_rows.append({"unit": unit, "type": stype, "file": name, "file_date": row.date.date(),
                                     "ts_first": t.min(), "ts_last": t.max(), "rows": len(t)})
        if stype in ("slow charging", "fast charging"):
            for name, g in f.groupby("session"):
                if stype == "slow charging":
                    on = g["ChargeLinePower264"] > 0.5
                else:
                    on = g["FC_dcCurrent"] > 1 if "FC_dcCurrent" in g else pd.Series(False, index=g.index)
                cur = g.loc[on, "RawBattCurrent132"].dropna()
                soc = g["SOCave292"].dropna()
                sign_rows.append({"unit": unit, "type": stype, "file": name, "rows_on": int(on.sum()),
                                  "soc_start": soc.iloc[0] if len(soc) else np.nan, "soc_end": soc.iloc[-1] if len(soc) else np.nan,
                                  "cur_lt0": int((cur < 0).sum()), "cur_gt0": int((cur > 0).sum()),
                                  "cur_median": float(cur.median()) if len(cur) else np.nan})
        if stype == "driving":
            moving = f["DI_uiSpeed"] > 80
            cur = f.loc[moving, "RawBattCurrent132"].dropna()
            lines.append(f"{unit} driving, speed > 80 km/h: current rows < 0: {int((cur < 0).sum())}, > 0: {int((cur > 0).sum())}, median {cur.median():.1f} A")
        del f

pd.DataFrame(outside_rows).to_csv(out / "kul_sessions_outside.csv", index=False)
sign = pd.DataFrame(sign_rows)
sign.to_csv(out / "kul_sign.csv", index=False)
cov = pd.DataFrame(cov_rows)
cov.to_csv(out / "kul_coverage.csv", index=False)

o = pd.DataFrame(outside_rows)
for (unit, stype), g in (o.groupby(["unit", "type"]) if len(o) else []):
    agree = (pd.to_datetime(g["ts_first"]).dt.tz_localize(None).dt.normalize() <= pd.to_datetime(g["file_date"])) & (pd.to_datetime(g["file_date"]) <= pd.to_datetime(g["ts_last"]).dt.tz_localize(None).dt.normalize())
    lines.append(f"{unit} {stype}: {len(g)} files dated outside the paper period ({g['file_date'].min()} to {g['file_date'].max()}), "
                 f"{int(agree.sum())} with the file date inside their own Timestamp range, rows {int(g['rows'].sum())}")
for (unit, stype), g in sign.groupby(["unit", "type"]):
    rising = g[(g["soc_end"] - g["soc_start"]) > 1]
    lines.append(f"{unit} {stype}: {len(g)} sessions, {len(rising)} with SOC rising > 1 point; in those, charging-on rows with current < 0: {int(rising['cur_lt0'].sum())}, > 0: {int(rising['cur_gt0'].sum())}; per-session median current range {rising['cur_median'].min():.1f} to {rising['cur_median'].max():.1f} A")
for (unit, stype), (n, m) in odo_sentinel.items():
    lines.append(f"{unit} {stype}: Odometer3B6 == 4294967.295 in {n} of {m} non-null rows")
lines.append(cov.to_string(index=False))
(out / "kul_summary.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
