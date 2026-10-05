"""rwth-android source-audit data checks (2026-10-04).

What it does, per device, through the loader only (`fielddata.loaders.rwth_android.systems` and `load`,
raw data, clean=False):
  1. timestamp dtype and zone, first and last timestamp, rows before 2026-01-14 and after 2026-04-15
     (the data paper's period);
  2. sign: median `current` and `current_avg` and the share of positive values when status == 2 (charging)
     and status == 3 (discharging), excluding the value -2147.483648;
  3. units: medians of voltage_cell, |current|, charge_counter, nominal_capacity, temperature_cell;
  4. cells: cell_id.nunique() per file, whether cell_id equals the file hash, and cell_ids shared by files;
  5. cadence: median and 95th percentile of timestamp steps (s);
  6. placeholders: rows where nominal_capacity == 0, and rows equal to -2147.483648 (Integer.MIN_VALUE / 1e6,
     the Android "property not supported" value) in every numeric column.
Reads: the released rwth-android archive through fielddata.loaders.rwth_android.
Writes into <out_dir>: ra_devices.csv, ra_summary.txt.
Run from the repo root: PYTHONPATH=. .venv/Scripts/python.exe <this file> <out_dir>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fielddata.loaders import rwth_android as r

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
INT_MIN = -2147.483648
START, END = pd.Timestamp("2026-01-14"), pd.Timestamp("2026-04-16")

rows, cell_sets = [], {}
for unit in r.systems()["unit"]:
    f = r.load(unit)
    idx = f.index
    step = pd.Series(idx).diff().dt.total_seconds().dropna()
    row = {"unit": unit, "manufacturer": f["manufacturer"].iloc[0], "model": f["model"].iloc[0], "rows": len(f),
           "dtype": str(idx.dtype), "tz": str(getattr(idx, "tz", None)), "first": idx.min(), "last": idx.max(),
           "rows_before_2026_01_14": int((idx < START).sum()), "rows_after_2026_04_15": int((idx >= END).sum()),
           "step_median_s": float(step.median()), "step_p95_s": float(step.quantile(0.95)),
           "cell_id_nunique": int(f["cell_id"].nunique()), "cell_id_is_unit": bool((f["cell_id"] == unit).all()),
           "nominal_capacity_zero_rows": int((f["nominal_capacity"] == 0).sum()),
           "nominal_capacity_median": float(f["nominal_capacity"].median())}
    cell_sets[unit] = set(f["cell_id"].dropna())
    for col in ["current", "current_avg"]:
        v = f[col].where(f[col] != INT_MIN)
        for st, label in [(2, "chg"), (3, "dis")]:
            x = v[f["status"] == st].dropna()
            row[f"{col}_{label}_median"] = float(x.median()) if len(x) else np.nan
            row[f"{col}_{label}_share_pos"] = float((x > 0).mean()) if len(x) else np.nan
            row[f"{col}_{label}_n"] = int(len(x))
    cur = f["current"].where(f["current"] != INT_MIN)
    row["abs_current_median"] = float(cur.abs().median())
    for col in ["voltage_cell", "charge_counter", "temperature_cell"]:
        row[f"{col}_median"] = float(f[col].where(f[col] != INT_MIN).median())
    for col in f.select_dtypes("number").columns:
        n = int((f[col] == INT_MIN).sum())
        if n:
            row[f"intmin_{col}"] = n
    rows.append(row)
    print(unit, "done", flush=True)

d = pd.DataFrame(rows)
d.to_csv(out / "ra_devices.csv", index=False)
shared = sum(1 for a in cell_sets for b in cell_sets if a < b and cell_sets[a] & cell_sets[b])
intmin_cols = [c for c in d.columns if c.startswith("intmin_")]
lines = [
    f"devices {len(d)}, rows {d['rows'].sum()}; index dtype(s) {sorted(set(d['dtype']))}, tz {sorted(set(d['tz']))}",
    f"first timestamp {d['first'].min()}, last {d['last'].max()}",
    f"devices with rows before 2026-01-14: {int((d['rows_before_2026_01_14'] > 0).sum())} ({d['rows_before_2026_01_14'].sum()} rows); after 2026-04-15: {int((d['rows_after_2026_04_15'] > 0).sum())}",
    "devices with rows before 2026-01-14: " + "; ".join(f"{u[:8]} {m} {n} rows, first {fi}" for u, m, n, fi in d.loc[d['rows_before_2026_01_14'] > 0, ['unit', 'model', 'rows_before_2026_01_14', 'first']].itertuples(index=False)),
    f"cell_id: nunique per file {sorted(set(d['cell_id_nunique']))}; equals the file hash in {int(d['cell_id_is_unit'].sum())} files; file pairs sharing a cell_id {shared}",
    f"cadence: median step per device {d['step_median_s'].min():.1f} to {d['step_median_s'].max():.1f} s (median {d['step_median_s'].median():.1f}); p95 {d['step_p95_s'].min():.0f} to {d['step_p95_s'].max():.0f} s",
    f"nominal_capacity == 0 on {int((d['nominal_capacity_zero_rows'] > 0).sum())} devices; device medians {d['nominal_capacity_median'].min():.2f} to {d['nominal_capacity_median'].max():.2f} Ah",
    f"medians: voltage_cell {d['voltage_cell_median'].min():.3f} to {d['voltage_cell_median'].max():.3f} V; |current| {d['abs_current_median'].min():.3f} to {d['abs_current_median'].max():.3f} A; charge_counter {d['charge_counter_median'].min():.3f} to {d['charge_counter_median'].max():.3f} Ah; temperature_cell {d['temperature_cell_median'].min():.1f} to {d['temperature_cell_median'].max():.1f} C",
    "current sign while charging (status 2): devices with median > 0: {} , < 0: {}, no rows: {}".format(int((d['current_chg_median'] > 0).sum()), int((d['current_chg_median'] < 0).sum()), int(d['current_chg_median'].isna().sum())),
    "current sign while discharging (status 3): devices with median > 0: {} , < 0: {}, no rows: {}".format(int((d['current_dis_median'] > 0).sum()), int((d['current_dis_median'] < 0).sum()), int(d['current_dis_median'].isna().sum())),
    "devices whose current is positive while discharging: " + "; ".join(f"{u[:8]} {mf} {m} (chg median {c:.3f} A, dis median {x:.3f} A)" for u, mf, m, c, x in d.loc[d['current_dis_median'] > 0, ['unit', 'manufacturer', 'model', 'current_chg_median', 'current_dis_median']].itertuples(index=False)),
    "current_avg sign: devices with discharging median > 0: {}, < 0: {}, no valid rows: {}".format(int((d['current_avg_dis_median'] > 0).sum()), int((d['current_avg_dis_median'] < 0).sum()), int(d['current_avg_dis_median'].isna().sum())),
    "value -2147.483648 (Integer.MIN_VALUE/1e6) rows per column: " + ", ".join(f"{c.removeprefix('intmin_')}: {int(d[c].fillna(0).sum())} rows on {int(d[c].notna().sum())} devices" for c in intmin_cols),
]
(out / "ra_summary.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
