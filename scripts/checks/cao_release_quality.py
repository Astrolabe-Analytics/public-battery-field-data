"""Check how far the released Cao files went through the cleaning the authors describe (Supplementary Note S5).

What it does: Note S5 says rows with missing or out-of-range values were removed and suspected sensor faults in a
cell's reading were replaced with the median of all cells. For every DTI and QAS vehicle, through the loader with
generic names (values as released), this script counts what is left that such cleaning would remove:
- exact placeholder codes (-1004.8, -1000, -999, 65535) anywhere in vin_2;
- rows with current at or below -900 A (the placeholder stretch near -1,000 A);
- zero cell voltages (cells and rows);
- numerical blow-ups in the model-output columns, values with magnitude above 1e6 in vin_2's two leading columns
  and voltage-deviation block, and in vin_3's leading columns, cell-SOC and SOC-deviation blocks, with the row
  positions where they occur;
- for DTI, the median gap between vin_2's second leading column and the highest cell voltage (row by row).
It also records the row that holds each vehicle's vin_2 voltage-deviation minimum.

Reads: vin_2 and vin_3 of every DTI and QAS vehicle through fielddata.loaders.cao.
Writes: reports/checks/cao_release_quality.csv (one row per vehicle) and reports/checks/cao_release_quality.txt.

Run (about three minutes on six processes):
    python scripts/checks/cao_release_quality.py [--workers 6]
"""
from __future__ import annotations

import argparse
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "reports" / "checks" / "cao_release_quality.csv"
SUMMARY = ROOT / "reports" / "checks" / "cao_release_quality.txt"
CODES = (-1004.8, -1000.0, -999.0, 65535.0)
BLOWUP = 1e6


def check(item) -> dict:
    from fielddata.loaders import cao
    brand, vehicle = item
    v2 = cao.load(brand, vehicle, which="vin_2").to_numpy(float)
    v3 = cao.load(brand, vehicle, which="vin_3").to_numpy(float)
    n = (v2.shape[1] - 5) // 2
    cells, du = v2[:, 2:n + 2], v2[:, n + 2:2 * n + 2]
    current = v2[:, 2 * n + 4]
    model2 = np.hstack([v2[:, :2], du])
    model3 = v3[:, :2 * n + 2]
    blow2 = np.abs(model2) > BLOWUP
    blow3 = np.abs(model3) > BLOWUP
    blow_rows = np.flatnonzero(blow2.any(axis=1) | blow3.any(axis=1))
    zero = cells == 0
    good = ~np.isin(v2, CODES).any(axis=1) & (current > -900) & (np.abs(current) < 1000) & ~zero.any(axis=1)
    gap = (v2[good, 1] - cells[good].max(axis=1)) if brand == "DTI" and good.any() else np.array([np.nan])
    finite_du = np.where(np.isfinite(du), du, np.inf)
    return {
        "brand": brand, "vehicle": vehicle, "rows": len(v2),
        "placeholder_values": int(np.isin(v2, CODES).sum()),
        "current_rows_at_or_below_minus_900": int((current <= -900).sum()),
        "zero_cell_values": int(zero.sum()), "zero_cell_rows": int(zero.any(axis=1).sum()),
        "blowup_values_vin2": int(blow2.sum()), "blowup_values_vin3": int(blow3.sum()), "blowup_rows": int(len(blow_rows)),
        "blowup_first_row": int(blow_rows[0]) if len(blow_rows) else -1, "blowup_min": float(np.min(np.r_[model2[blow2], model3[blow3]])) if len(blow_rows) else float("nan"),
        "dU_min": float(np.nanmin(du)), "dU_min_row": int(np.unravel_index(np.argmin(finite_du), du.shape)[0]),
        "dti_col1_minus_max_cell_median": float(np.median(gap)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    workers = parser.parse_args().workers
    from fielddata.loaders import cao
    units = cao.systems()
    items = [(r.brand, str(r.vehicle)) for r in units.itertuples() if r.brand in {"DTI", "QAS"} and r.vin_2 and r.vin_3]
    with Pool(workers) as pool:
        frame = pd.DataFrame(pool.map(check, items))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT, index=False, lineterminator="\n")
    lines = []
    for brand, g in frame.groupby("brand"):
        b = g[g.blowup_rows > 0]
        lines += [
            f"{brand}: {len(g)} vehicles, {int(g.rows.sum()):,} rows",
            f"  placeholder codes: {int(g.placeholder_values.sum()):,} values in {int((g.placeholder_values > 0).sum())} vehicles",
            f"  current at or below -900 A: {int(g.current_rows_at_or_below_minus_900.sum()):,} rows in {int((g.current_rows_at_or_below_minus_900 > 0).sum())} vehicles",
            f"  zero cell voltages: {int(g.zero_cell_values.sum()):,} values in {int(g.zero_cell_rows.sum()):,} rows of {int((g.zero_cell_rows > 0).sum())} vehicles",
            f"  blow-ups (|value| > 1e6 in model-output columns): {int(b.blowup_rows.sum()):,} rows in {len(b)} vehicles, "
            f"{int(g.blowup_values_vin2.sum()):,} values in vin_2 and {int(g.blowup_values_vin3.sum()):,} in vin_3, minimum {b.blowup_min.min():.3g}; "
            f"first blow-up row is row 0 in {int((b.blowup_first_row == 0).sum())} of them",
            f"  voltage-deviation minimum in the first row: {int((g.dU_min_row == 0).sum())} of {len(g)} vehicles",
        ]
        if brand == "DTI":
            q = g.dti_col1_minus_max_cell_median
            lines.append(f"  vin_2 column 1 minus the highest cell, median per vehicle: {q.quantile(0.1):.0f} to {q.quantile(0.9):.0f} (10th to 90th percentile), fleet median {q.median():.0f}")
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
