"""fei_bus source-audit data checks (reports/source_audit_2026-10-04/fei_bus.md, findings 2 and 3).

What it does, through fielddata.load('fei_bus') only (raw data, clean=False), per bus:
  2. the share of rows with SOH(OCV) > 1.05 and with SOH > 1.0, and the Spearman rank correlation of SOH and of
     SOH(OCV) with mileage;
  3. whether mileage is monotonic in release order (number of decreases between consecutive rows, and the largest
     decrease), plus the first and last mileage.
Reads: the four released CSV files, through the loader.
Writes: prints only.
Run from the repo root: PYTHONPATH=. .venv/Scripts/python.exe <this file>
"""
from __future__ import annotations

import pandas as pd

import fielddata


def spearman(a: pd.Series, b: pd.Series) -> float:
    """Spearman rank correlation as the Pearson correlation of average ranks (no scipy needed)."""
    return a.rank().corr(b.rank())


if __name__ == "__main__":
    df = fielddata.load("fei_bus")
    rows = []
    for unit, g in df.groupby("unit", sort=False):
        g = g.reset_index(drop=True)
        d = g["mileage"].diff()
        rows.append({
            "unit": unit, "rows": len(g),
            "share_SOHOCV_gt_1.05": round(float((g["SOH(OCV)"] > 1.05).mean()), 3),
            "share_SOH_gt_1": round(float((g["SOH"] > 1.0).mean()), 3),
            "spearman_SOH_mileage": round(float(spearman(g["SOH"], g["mileage"])), 3),
            "spearman_SOHOCV_mileage": round(float(spearman(g["SOH(OCV)"], g["mileage"])), 3),
            "spearman_SOH_SOHOCV": round(float(spearman(g["SOH"], g["SOH(OCV)"])), 3),
            "mileage_decreases": int((d < 0).sum()), "mileage_increases": int((d > 0).sum()),
            "largest_decrease_km": round(float(-d.min()), 1) if (d < 0).any() else 0.0,
            "first_mileage": float(g["mileage"].iloc[0]), "last_mileage": float(g["mileage"].iloc[-1]),
            "min_mileage": float(g["mileage"].min()), "max_mileage": float(g["mileage"].max()),
        })
    pd.set_option("display.width", 250)
    print(pd.DataFrame(rows).set_index("unit").T.to_string())
