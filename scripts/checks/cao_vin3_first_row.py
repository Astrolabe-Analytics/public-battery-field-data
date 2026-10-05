"""Check the first row of every Cao vin_3 file: the per-cell state of charge at the filter's start value.

What it does: Function_.py's solvers() starts the authors' filter with SOC[0] = 0.01 * soc[0] and sets every
cell to that value (Xi[0] = SOC[0]), so the first row of vin_3 should hold each cell's state of charge at 1/100
of the onboard state of charge. For every DTI and QAS vehicle this script compares the first row's mean cell
state of charge with the onboard state of charge in the same row, and gives the range of the per-cell state of
charge with and without the first row (percent, through the loader's inferred names, raw values otherwise).

Reads: vin_3 of every DTI and QAS vehicle through fielddata.loaders.cao.
Writes: reports/checks/cao_vin3_first_row.csv (one row per vehicle) and reports/checks/cao_vin3_first_row.txt.

Run (about two minutes on six processes):
    python scripts/checks/cao_vin3_first_row.py [--workers 6]
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

OUT = ROOT / "reports" / "checks" / "cao_vin3_first_row.csv"
SUMMARY = ROOT / "reports" / "checks" / "cao_vin3_first_row.txt"


def check(item) -> dict:
    from fielddata.loaders import cao
    brand, vehicle = item
    frame = cao.load(brand, vehicle, which="vin_3", names="inferred")
    cells = frame[[c for c in frame.columns if c.startswith("cell_soc_")]].to_numpy(float)
    onboard = frame["soc_pct"].to_numpy(float)
    later = cells[1:] if len(cells) > 1 else np.full((1, cells.shape[1]), np.nan)
    return {"brand": brand, "vehicle": vehicle, "rows": len(frame),
            "first_row_ratio": float(cells[0].mean() / onboard[0]) if onboard[0] else float("nan"),
            "min_with_first_row": float(np.nanmin(cells)), "max_with_first_row": float(np.nanmax(cells)),
            "min_without_first_row": float(np.nanmin(later)), "max_without_first_row": float(np.nanmax(later))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    workers = parser.parse_args().workers
    from fielddata.loaders import cao
    units = cao.systems()
    items = [(r.brand, str(r.vehicle)) for r in units.itertuples() if r.brand in {"DTI", "QAS"} and r.vin_3]
    with Pool(workers) as pool:
        frame = pd.DataFrame(pool.map(check, items))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT, index=False, lineterminator="\n")
    lines = []
    for brand, group in frame.groupby("brand"):
        at_start = int(np.isclose(group.first_row_ratio, 0.01, rtol=0.05).sum())
        lines.append(f"{brand}: {len(group)} vehicles; first row at 1/100 of the onboard SOC in {at_start}; per-cell SOC "
                     f"{group.min_without_first_row.min():.4g} to {group.max_without_first_row.max():.4g} percent without the first row, "
                     f"{group.min_with_first_row.min():.4g} to {group.max_with_first_row.max():.4g} with it")
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
