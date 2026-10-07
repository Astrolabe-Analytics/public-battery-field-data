"""aitio: telemetry gaps longer than 30 days, against the paper's filter (raw data).

The paper (accepted manuscript p. 22, data-selection step 4) says: "We removed any batteries that had large gaps in
their telemetry data (over 30 days)." This lists every gap over 30 days in the released files, through
fielddata.loaders.aitio, with whether the battery failed and whether the gap starts before or after its
IN_REPAIR_SYSTEM date. Writes reports/checks/aitio_gaps.csv (one row per gap) and prints a summary.

Run:
    python scripts/checks/aitio_gaps.py
"""
from __future__ import annotations

import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "reports" / "checks" / "aitio_gaps.csv"
LIMIT_S = 30 * 86400


def gaps(item):
    from fielddata.loaders import aitio
    unit, repair = item
    t = aitio._read(unit)[:, 0]
    dt = np.diff(t)
    rows = []
    for k in np.flatnonzero(dt > LIMIT_S):
        start = pd.Timestamp(t[k], unit="s", tz="UTC")
        rows.append({"id": unit, "gap_start_utc": start, "gap_days": dt[k] / 86400,
                     "status": "failed" if repair is not None else "alive",
                     "vs_repair": None if repair is None else ("after repair" if start >= repair else "before repair")})
    return rows


def main() -> None:
    from fielddata.loaders import aitio
    repair = aitio._repair_dates()
    items = [(u, repair.get(u)) for u in aitio.systems()["unit"]]
    with Pool(6) as pool:
        table = pd.DataFrame([r for rows in pool.map(gaps, items) for r in rows])
    table.to_csv(OUT, index=False, lineterminator="\n", float_format="%.4g")
    print(f"gaps over 30 days: {len(table)} in {table.id.nunique()} of {len(items)} batteries")
    alive = table[table.status == "alive"]
    before = table[table.vs_repair == "before repair"]
    after = table[table.vs_repair == "after repair"]
    print(f"  live batteries: {len(alive)} gaps in {alive.id.nunique()} batteries")
    print(f"  failed, before the repair date: {len(before)} gaps in {before.id.nunique()} batteries")
    print(f"  failed, after the repair date: {len(after)} gaps in {after.id.nunique()} batteries")
    within = table[table.vs_repair != "after repair"]
    print(f"  batteries with a gap over 30 days in the record the paper analysed (live, or failed before repair): {within.id.nunique()}")
    print(f"  longest gap: {table.gap_days.max():.1f} days")


if __name__ == "__main__":
    main()
