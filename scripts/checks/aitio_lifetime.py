"""aitio: what meta_data.csv Lifetime measures, the data after the repair date, and rows below 1 V (raw).

What it does, per battery, through fielddata.loaders.aitio:
1. Lifetime against three candidate definitions: ACTIVATED to IN_REPAIR_SYSTEM (failed batteries), ACTIVATED to
   the last record, and ACTIVATED to 2020-09-15 (a fixed cut-off).
2. For failed batteries (STILL_ALIVE = FALSE): whether logging continues after the repair date, for how long, and
   how the 30 days after the repair date compare with the 30 days before it: rows per day, median voltage,
   5th percentile voltage, share of rows below 11.5 V, and Ah discharged per day.
3. Rows with voltage below 1 V: their count, how many form runs of a single row, and the voltage of the rows
   just before and after each.
Writes reports/checks/aitio_lifetime.csv (one row per battery) and aitio_sub1v.csv (one row per
sub-1 V row) and prints a summary.

Run (a few minutes on six processes):
    python scripts/checks/aitio_lifetime.py
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

OUT = ROOT / "reports" / "checks"
CUTOFF = pd.Timestamp("2020-09-15")
DAY = 86400.0


def _window(t, i, v, lo, hi):
    keep = (t >= lo) & (t < hi)
    if not keep.any():
        return {}
    tt, ii, vv = t[keep], i[keep], v[keep]
    days = max((hi - lo) / DAY, 1e-9)
    dt = np.diff(tt, append=tt[-1])
    usable = dt <= 600
    return {"rows_per_day": keep.sum() / days, "V_median": float(np.median(vv)), "V_p05": float(np.percentile(vv, 5)),
            "share_V_below_11_5": float(np.mean(vv < 11.5)),
            "Ah_discharged_per_day": float((ii * dt / 3600)[usable & (ii > 0)].sum() / days)}


def measure(item):
    from fielddata.loaders import aitio
    unit, activated, repair, alive, lifetime = item
    a = aitio._read(unit)
    t, i, v = a[:, 0], a[:, 1], a[:, 2]
    start = pd.Timestamp(activated).timestamp()
    last = t.max()
    row = {"id": unit, "STILL_ALIVE": alive, "Lifetime": lifetime,
           "days_activated_to_last": (last - start) / DAY,
           "days_activated_to_cutoff": (CUTOFF.timestamp() - start) / DAY}
    if not alive:
        rep = pd.Timestamp(repair).timestamp()
        row["days_activated_to_repair"] = (rep - start) / DAY
        row["days_logged_after_repair"] = max(0.0, (last - rep) / DAY)
        row["rows_after_repair"] = int((t >= rep).sum())
        for label, (lo, hi) in {"before": (rep - 30 * DAY, rep), "after": (rep, rep + 30 * DAY)}.items():
            row.update({f"{label}_{k}": x for k, x in _window(t, i, v, lo, hi).items()})
    low = np.flatnonzero(v < 1)
    sub = []
    for k in low:
        prev_v = float(v[k - 1]) if k > 0 else np.nan
        next_v = float(v[k + 1]) if k + 1 < len(v) else np.nan
        single = not ((k > 0 and v[k - 1] < 1) or (k + 1 < len(v) and v[k + 1] < 1))
        sub.append({"id": unit, "row": int(k), "time_s": float(t[k]), "voltage_V": float(v[k]), "current_A": float(i[k]),
                    "temperature_degC": float(a[k, 3]), "prev_V": prev_v, "next_V": next_v, "single_row": single})
    return row, sub


def main() -> None:
    from fielddata.loaders import aitio
    meta = aitio.metadata()
    items = [(r.ID, r.ACTIVATED, r.IN_REPAIR_SYSTEM, bool(r.STILL_ALIVE), int(r.Lifetime)) for r in meta.itertuples()]
    with Pool(6) as pool:
        results = pool.map(measure, items)
    table = pd.DataFrame([r for r, _ in results]).sort_values("id", key=lambda s: s.astype(int))
    sub = pd.DataFrame([s for _, subs in results for s in subs])
    table.to_csv(OUT / "aitio_lifetime.csv", index=False, lineterminator="\n", float_format="%.6g")
    sub.to_csv(OUT / "aitio_sub1v.csv", index=False, lineterminator="\n", float_format="%.6g")

    failed, alive = table[~table.STILL_ALIVE], table[table.STILL_ALIVE]
    print(f"failed {len(failed)}, alive {len(alive)}")
    print("failed: Lifetime == ACTIVATED to repair (within 1 day):", int(((failed.Lifetime - failed.days_activated_to_repair).abs() <= 1).sum()))
    print("failed: Lifetime == ACTIVATED to last record (within 7 days):", int(((failed.Lifetime - failed.days_activated_to_last).abs() <= 7).sum()))
    print("alive: Lifetime == ACTIVATED to last record (within 7 days):", int(((alive.Lifetime - alive.days_activated_to_last).abs() <= 7).sum()))
    print("alive: Lifetime == ACTIVATED to 2020-09-15 (within 1 day):", int(((alive.Lifetime - alive.days_activated_to_cutoff).abs() <= 1).sum()))
    span_minus = table.days_activated_to_last - table.Lifetime
    print(f"span - Lifetime, all: median {span_minus.median():.1f} d, p90 {span_minus.quantile(0.9):.1f} d")
    print(f"failed: logging continues after repair in {int((failed.rows_after_repair > 0).sum())} of {len(failed)}; "
          f"days logged after repair median {failed.days_logged_after_repair.median():.1f}, p90 {failed.days_logged_after_repair.quantile(0.9):.1f}")
    both = failed.dropna(subset=["before_V_median", "after_V_median"])
    for k in ("rows_per_day", "V_median", "V_p05", "share_V_below_11_5", "Ah_discharged_per_day"):
        b, a = both[f"before_{k}"], both[f"after_{k}"]
        print(f"  30 d before vs after repair, {k}: median {b.median():.4g} -> {a.median():.4g}; after higher in {int((a > b).sum())} of {len(both)}")
    print(f"sub-1 V rows: {len(sub)} in {sub.id.nunique() if len(sub) else 0} batteries; single-row {int(sub.single_row.sum()) if len(sub) else 0}; "
          f"neighbours both above 10 V: {int(((sub.prev_V > 10) & (sub.next_V > 10)).sum()) if len(sub) else 0}")
    if len(sub):
        print(sub[["voltage_V", "current_A", "temperature_degC", "prev_V", "next_V"]].describe().round(3).to_string())


if __name__ == "__main__":
    main()
