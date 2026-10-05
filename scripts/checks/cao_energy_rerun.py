"""Check that cao's per-vehicle energy cache reproduces when recomputed from scratch.

What it does: compares two copies of the cao energy cache, the one the facts table uses
(reports/facts/_cache/cao_energy_per_vehicle.csv) and one recomputed from the released files by moving the
cache aside and running `python scripts/facts/cao.py --force` until it finishes. It reports the vehicle
count, row counts, the largest per-vehicle kWh difference, the per-brand median kWh, and the total MWh the
facts script derives (median kWh per brand times vehicles per brand, DTI and QAS).

Reads: the two cache CSVs and fielddata.systems("cao") for vehicles per brand.
Writes: reports/checks/cao_energy_rerun.txt.

Reproduce:
    mv reports/facts/_cache/cao_energy_per_vehicle.csv reports/facts/_cache/cao_energy_per_vehicle.old.csv
    python scripts/facts/cao.py --force        (repeat until it stops asking to run again)
    mv reports/facts/_cache/cao_energy_per_vehicle.csv reports/facts/_cache/cao_energy_per_vehicle.rerun-2026-10-02.csv
    mv reports/facts/_cache/cao_energy_per_vehicle.old.csv reports/facts/_cache/cao_energy_per_vehicle.csv
    python scripts/checks/cao_energy_rerun.py [rerun.csv]
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CACHE = ROOT / "reports" / "facts" / "_cache"
OUT = ROOT / "reports" / "checks" / "cao_energy_rerun.txt"


def total_mwh(frame, counts):
    return sum(frame[frame["brand"] == b]["kwh"].median() * counts[b] for b in ("DTI", "QAS")) / 1000


def main():
    import fielddata
    rerun = Path(sys.argv[1]) if len(sys.argv) > 1 else CACHE / "cao_energy_per_vehicle.rerun-2026-10-02.csv"
    old = pd.read_csv(CACHE / "cao_energy_per_vehicle.csv", dtype={"vehicle": str})
    new = pd.read_csv(rerun, dtype={"vehicle": str})
    counts = fielddata.systems("cao")["brand"].value_counts()
    both = old.merge(new, on=["brand", "vehicle"], suffixes=("_old", "_new"))
    lines = [
        f"vehicles: cache {len(old)}, rerun {len(new)}, in both {len(both)}",
        f"row counts identical: {bool((both['rows_old'] == both['rows_new']).all())}",
        f"vehicles with a usable estimate identical: {bool((both['kwh_old'].isna() == both['kwh_new'].isna()).all())}",
        f"largest per-vehicle kWh difference: {(both['kwh_old'] - both['kwh_new']).abs().max():.3g}",
    ]
    for brand in ("DTI", "QAS", "GIS"):
        o, n = old[old["brand"] == brand]["kwh"], new[new["brand"] == brand]["kwh"]
        lines.append(f"{brand}: {len(o)} vehicles, {o.notna().sum()} usable, median kWh cache {o.median():.3f}, rerun {n.median():.3f}")
    lines.append(f"total MWh: cache {total_mwh(old, counts):.2f}, rerun {total_mwh(new, counts):.2f}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
