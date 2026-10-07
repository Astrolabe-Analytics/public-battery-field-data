"""Per-battery table for the aitio package (BBOXX solar home systems, Aitio and Howey 2021), raw data.

What it does: for each of the 1,027 batteries, read through fielddata.loaders.aitio, it records the first and
last timestamp (UTC), span in days, row count, median sampling interval, the number of gaps over 24 h and the
longest gap, voltage, current and temperature minimum / median / maximum, the count of rows with voltage below
1 V, and Ah charged and discharged. It joins meta_data.csv on ID and adds two flags:
- start_vs_activated: the first timestamp is more than 1 day from ACTIVATED;
- span_vs_lifetime: the span differs from Lifetime by more than 7 days.

Ah: current times the interval to the next row, summed separately for negative current (charging, the authors'
convention) and positive current (discharging). Intervals longer than 600 s (ten times the 60 s median) are
gaps and are left out of the sums, so charge is not credited across missing data.

Reads: fielddata.loaders.aitio. Writes: reports/checks/aitio_units.csv (one row per battery; a rerun
skips batteries already recorded) and reports/checks/aitio_totals.txt.

Run (about 10 minutes on six processes):
    python scripts/checks/aitio_units.py [--workers 6]
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

OUT = ROOT / "reports" / "checks"
TABLE = OUT / "aitio_units.csv"
TOTALS = OUT / "aitio_totals.txt"
GAP_FOR_AH_S = 600
NOMINAL_V, NOMINAL_AH = 12.0, 20.0  # per battery, as given for the review sheet


def measure(unit: str) -> dict:
    from fielddata.loaders import aitio
    a = aitio._read(unit)
    t, i, v, temp = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
    dt = np.diff(t)
    usable = dt <= GAP_FOR_AH_S
    step_ah = i[:-1] * dt / 3600
    row = {"id": unit, "first_utc": pd.Timestamp(t.min(), unit="s"), "last_utc": pd.Timestamp(t.max(), unit="s"),
           "span_days": (t.max() - t.min()) / 86400, "rows": len(a),
           "median_dt_s": float(np.median(dt)) if len(dt) else np.nan,
           "gaps_over_24h": int((dt > 86400).sum()), "longest_gap_h": float(dt.max() / 3600) if len(dt) else np.nan,
           "time_increasing": bool((dt > 0).all())}
    for name, x in (("V", v), ("I", i), ("T", temp)):
        row.update({f"{name}_min": float(np.nanmin(x)), f"{name}_median": float(np.nanmedian(x)), f"{name}_max": float(np.nanmax(x))})
    row["rows_V_below_1V"] = int((v < 1).sum())
    row["Ah_charged"] = float(-step_ah[usable & (i[:-1] < 0)].sum())
    row["Ah_discharged"] = float(step_ah[usable & (i[:-1] > 0)].sum())
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    workers = parser.parse_args().workers
    from fielddata.loaders import aitio
    OUT.mkdir(parents=True, exist_ok=True)
    units = list(aitio.systems()["unit"])
    done = pd.read_csv(TABLE, dtype={"id": str}) if TABLE.exists() else pd.DataFrame()
    seen = set(done["id"]) if len(done) else set()
    todo = [u for u in units if u not in seen]
    rows = done.to_dict("records") if len(done) else []
    with Pool(workers) as pool:
        for n, row in enumerate(pool.imap_unordered(measure, todo), 1):
            rows.append(row)
            if n % 50 == 0:
                pd.DataFrame(rows).to_csv(TABLE, index=False, lineterminator="\n")
    table = pd.DataFrame(rows)
    table = table[[c for c in table.columns if c not in ("ACTIVATED", "IN_REPAIR_SYSTEM", "STILL_ALIVE", "Lifetime",
                                                         "flag_start_vs_activated", "flag_span_vs_lifetime")]]
    meta = aitio.metadata().rename(columns={"ID": "id"})
    table = table.merge(meta, on="id", how="left")
    first = pd.to_datetime(table["first_utc"])
    table["flag_start_vs_activated"] = (first - table["ACTIVATED"]).abs() > pd.Timedelta(days=1)
    table["flag_span_vs_lifetime"] = (table["span_days"] - table["Lifetime"]).abs() > 7
    table = table.sort_values("id", key=lambda s: s.astype(int)).reset_index(drop=True)
    table.to_csv(TABLE, index=False, lineterminator="\n", float_format="%.6g")
    failed = table["STILL_ALIVE"] == False  # noqa: E712 (column is boolean as released)
    data_bytes = sum((aitio.directory("aitio") / name).stat().st_size for name in aitio_files())
    lines = [
        f"units (batteries with a data file): {len(table)}",
        f"unit-years (sum of first-to-last spans): {table['span_days'].sum() / 365.25:.3f}",
        f"nominal kWh ({len(table)} x {NOMINAL_V:g} V x {NOMINAL_AH:g} Ah): {len(table) * NOMINAL_V * NOMINAL_AH / 1000:.2f}",
        f"bytes (16 shipped files): {data_bytes:,}",
        f"STILL_ALIVE = FALSE: {int(failed.sum())}",
        f"rows: {int(table['rows'].sum()):,}",
        f"flag start_vs_activated: {int(table['flag_start_vs_activated'].sum())}; flag span_vs_lifetime: {int(table['flag_span_vs_lifetime'].sum())}",
    ]
    TOTALS.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


def aitio_files():
    from fielddata.registry import CANDIDATES
    return CANDIDATES["aitio"]["data_files"]


if __name__ == "__main__":
    main()
