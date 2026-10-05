"""Build the per-vehicle profile of the Cao release that notebooks/cao_in_depth.ipynb reads.

What it does: for every vehicle with a vin_2 file, loads vin_2 through fielddata.loaders.cao (inferred names, raw
values) and records its row count and width, constant and near-constant columns, the minimum, median and maximum
of each block (leading, cells, deviations, trailing), zero and placeholder counts, and rows with an out-of-range
value. This is the loop that used to run inside the notebook, moved here unchanged.

Reads: vin_2 of every vehicle through fielddata.loaders.cao.
Writes: reports/cao_vehicle_profile.csv, one row per vehicle, saved after each vehicle. Vehicles already
recorded are skipped, so a rerun only adds missing vehicles. Six worker processes.

Run:
    python scripts/checks/cao_vehicle_profile.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROFILE = ROOT / "reports" / "cao_vehicle_profile.csv"
COLUMNS = ["brand", "vehicle", "n_rows", "width", "constant_count", "constant_indices", "near_constant_count",
           "near_constant_indices", "leading", "cells", "deviations", "trailing", "zeros", "sentinels",
           "invalid_row_count", "worst_invalid_score", "seconds"]


def values_summary(values):
    if not values.shape[1]:
        return json.dumps({"min": None, "median": None, "max": None})
    return json.dumps({"min": float(values.min().min()), "median": float(values.median().median()), "max": float(values.max().max())})


def profile(brand, vehicle) -> dict:
    from fielddata import load
    started = perf_counter()
    # GIS does not follow the authors' layout, so it has no inferred names
    frame = load("cao", brand=brand, vehicle=vehicle, names="generic" if brand == "GIS" else "inferred", clean=False)
    width = frame.shape[1]
    n = (width - 5) // 2 if (width - 5) % 2 == 0 else 0
    blocks = {"leading": frame.iloc[:, :2], "cells": frame.iloc[:, 2:2 + n], "deviations": frame.iloc[:, 2 + n:2 + 2 * n], "trailing": frame.iloc[:, 2 + n * 2:]}
    constants = np.flatnonzero(frame.nunique(dropna=False).to_numpy() <= 1).tolist()
    near = (frame.max() - frame.min() < 0.01 * frame.median().abs()) | (frame.std() < 1e-3)
    if brand == "DTI":
        cell_bad = ((frame.iloc[:, 2:2 + n] < 1500) | (frame.iloc[:, 2:2 + n] > 5000)).any(axis=1)
        soc_bad = ~frame.soc_pct.between(0, 100 + 1e-9)  # SOC fractions x 100 can carry float noise above 100
    elif brand == "QAS":
        cell_bad = ((frame.iloc[:, 2:2 + n] < 1.5) | (frame.iloc[:, 2:2 + n] > 5)).any(axis=1)
        soc_bad = ~frame.soc_pct.between(0, 100 + 1e-9)  # SOC fractions x 100 can carry float noise above 100
    else:
        cell_bad = pd.Series(False, index=frame.index)
        soc_bad = pd.Series(False, index=frame.index)
    first = frame.columns[0]
    second = frame.columns[1]
    big_current = (frame.current_A.abs() > 1000) if "current_A" in frame else pd.Series(False, index=frame.index)
    big_lead = frame[[first, second]].abs().max(axis=1) > 1e4
    invalid = cell_bad | soc_bad | big_current | big_lead
    score = cell_bad.astype(int) + soc_bad.astype(int) + big_current.astype(int) + big_lead.astype(int)
    sentinels = [-999, -1000, 65535] + ([-1004.8] if brand == "QAS" else [])
    return {"brand": brand, "vehicle": str(vehicle), "n_rows": len(frame), "width": width, "constant_count": len(constants),
            "constant_indices": json.dumps(constants), "near_constant_count": int(near.sum()),
            "near_constant_indices": json.dumps(np.flatnonzero(near.to_numpy()).tolist()),
            **{name: values_summary(values) for name, values in blocks.items()}, "zeros": int((frame == 0).sum().sum()),
            "sentinels": int(sum((frame == value).sum().sum() for value in sentinels)), "invalid_row_count": int(invalid.sum()),
            "worst_invalid_score": int(score.max()), "seconds": perf_counter() - started}


def _profile(item):
    return profile(*item)


def main() -> None:
    from multiprocessing import Pool
    from fielddata import systems
    units = systems("cao")
    profiles = pd.read_csv(PROFILE, dtype={"brand": str, "vehicle": str}) if PROFILE.exists() else pd.DataFrame(columns=COLUMNS)
    done = set(zip(profiles.brand.astype(str), profiles.vehicle.astype(str)))
    todo = [(str(r.brand), str(r.vehicle)) for r in units[units.vin_2].itertuples(index=False) if (str(r.brand), str(r.vehicle)) not in done]
    with Pool(6) as pool:
        for row in pool.imap(_profile, todo):
            profiles = pd.concat([profiles, pd.DataFrame([row])], ignore_index=True)
            profiles.reindex(columns=COLUMNS).to_csv(PROFILE, index=False)
            done.add((row["brand"], row["vehicle"]))
    print(f"{len(done)} vehicles in {PROFILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
