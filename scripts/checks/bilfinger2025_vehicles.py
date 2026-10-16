"""bilfinger2025: what each recording holds, and whether the GB VW ID.3 is the FTM ID.3 or another vehicle.

What it does, on raw data through the loader: per recording, rows, columns, cell-voltage channels, date span and voltage
range; then, for the VW ID.3 files, the charge between 370 and 445 V (the paper's fixed window for the Volkswagen Group
pack, arXiv 2508.15517v1 p. 20, Table 2) integrated from the released current over the released time, and the spread of
the 108 cell voltages at the top of charge (highest minus lowest cell at the row with the highest pack voltage), with
the cell holding the lowest voltage there. A pack with one defective cell should show that cell far below the others.

Reads: bilfinger2025 through fielddata. Writes: reports/checks/v12/bilfinger2025_vehicles.csv and prints it.

Run:
    python scripts/checks/bilfinger2025_vehicles.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import fielddata  # noqa: E402

OUT = ROOT / "reports" / "checks" / "v12" / "bilfinger2025_vehicles.csv"
TIME = ("time_h", "time_s", "time_min", "time")


def hours(frame: pd.DataFrame) -> pd.Series | None:
    if "time_h" in frame:
        return frame["time_h"].astype(float)
    if "time_s" in frame:
        return frame["time_s"].astype(float) / 3600
    if "time_min" in frame:
        return frame["time_min"].astype(float) / 60
    if "date" in frame:
        d = pd.to_datetime(frame["date"], errors="coerce")
        return (d - d.min()).dt.total_seconds() / 3600
    return None


def main() -> int:
    s = fielddata.systems("bilfinger2025")
    rows = []
    for r in s.itertuples():
        f = fielddata.load("bilfinger2025", unit=r.unit)
        cells = [c for c in f.columns if re.match(r"cell_voltage_\d+$", str(c))]
        row = {"unit": r.unit, "kind": r.kind, "vehicle": r.vehicle, "rows": len(f), "columns": len(f.columns),
               "cell_channels": len(cells), "time_columns": " ".join(c for c in TIME + ("date",) if c in f.columns),
               "first_date": "", "last_date": "", "u_min": np.nan, "u_max": np.nan, "ah_370_445": np.nan,
               "cell_spread_top_mv": np.nan, "lowest_cell_top": "", "lowest_cell_gap_mv": np.nan}
        if "date" in f:
            d = pd.to_datetime(f["date"], errors="coerce").dropna()
            row["first_date"], row["last_date"] = str(d.min()), str(d.max())
        if "U" in f:
            row["u_min"], row["u_max"] = float(f["U"].min()), float(f["U"].max())
        h = hours(f)
        if isinstance(r.vehicle, str) and r.vehicle.startswith("VW ID.3") and h is not None and {"U", "I"} <= set(f.columns):
            w = f[(f["U"] >= 370) & (f["U"] <= 445)]
            hw = h.loc[w.index]
            row["ah_370_445"] = float(np.trapezoid(w["I"].astype(float).abs(), hw)) if len(w) > 1 else np.nan
        if cells and "U" in f:
            top = f.loc[f["U"].idxmax(), cells].astype(float)
            row["cell_spread_top_mv"] = float((top.max() - top.min()) * 1000)
            row["lowest_cell_top"] = top.idxmin()
            row["lowest_cell_gap_mv"] = float((top.drop(top.idxmin()).min() - top.min()) * 1000)
        rows.append(row)
    table = pd.DataFrame(rows)
    table.to_csv(OUT, index=False, lineterminator="\n")
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(table.drop(columns=["kind"]).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
