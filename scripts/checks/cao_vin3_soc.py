"""Check what vin_3 and the two deviation blocks hold in the Cao release, for every DTI and QAS vehicle.

What it does: the authors' code (MCDL repository, Train_.py) splits vin_2 and vin_3 the same way, 2 leading
columns, N cell columns, N deviation columns, then trailing columns (3 in vin_2, 4 in vin_3). Function_.py
estimates each cell's state of charge as pack SOC plus a per-cell offset (Xi = soc + xi). For each vehicle this
script tests, on rows without placeholder values:
- vin_3: whether the cell-block row mean matches the pack SOC column of vin_2 (correlation and median ratio),
  how closely cell = pack SOC + offset holds (median and 99th percentile absolute error), how much the cells
  differ within a row (median row standard deviation), whether three of its four trailing columns are exact
  copies of vin_2's trailing columns (temperature, SOC, current), and what the extra trailing column holds;
- vin_2: how the deviation block relates to each cell's distance from the row mean and from the authors'
  weighted mode (Function_.py calculate_volt_modepi), as flattened correlations, and the deviation's spread
  across cells (median row standard deviation);
- vin_2 against vin_3: whether the per-cell part of the voltage deviation (each cell minus its row mean)
  correlates with the per-cell part of the SOC deviation, as a flattened correlation.

Reads: vin_2 and vin_3 of every DTI and QAS vehicle through fielddata.loaders.cao.
Writes: reports/checks/cao_vin3_soc_per_vehicle.csv (one row per vehicle, resumable) and
reports/checks/cao_vin3_soc.txt (summary per brand).

Run (about three minutes on six processes; finished vehicles are skipped):
    python scripts/checks/cao_vin3_soc.py [--workers 6]
"""
from __future__ import annotations

import argparse
import csv
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PER_VEHICLE = ROOT / "reports" / "checks" / "cao_vin3_soc_per_vehicle.csv"
SUMMARY = ROOT / "reports" / "checks" / "cao_vin3_soc.txt"
CODES = (-1004.8, -1000.0, -999.0, 65535.0)
FIELDS = ["brand", "vehicle", "rows", "rows_used", "mean_soc_corr", "mean_soc_median_ratio", "offset_error_median",
          "offset_error_p99", "cell_soc_row_std_median", "cell_soc_row_std_p99", "trailing_copies_vin2", "extra_min", "extra_max", "extra_distinct",
          "dev2_corr_with_cell_minus_mean", "dev2_corr_with_cell_minus_modepi", "dev2_row_std_median",
          "dev2_vs_dsoc_corr"]


def modepi_difference(cells: np.ndarray) -> np.ndarray:
    """The authors' calculate_volt_modepi (Function_.py), cell minus the weighted mode, row by row."""
    frame = pd.DataFrame(cells)
    mode, std = frame.mean(axis=1), frame.std(axis=1)
    lam = 1 / std
    pi1 = (1 / (2 * np.pi * frame.pow(3))).mul(lam, axis=0).pow(0.5)
    pi2 = ((-1) * frame.sub(mode, axis=0).pow(2).mul(lam, axis=0) / (2 * frame.mul(mode.pow(2), axis=0))).apply(np.exp)
    weights = pi1 * pi2
    modepi = (weights * frame).sum(axis=1) / weights.sum(axis=1)
    return frame.sub(modepi, axis=0).to_numpy()


def corr(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a.ravel(), b.ravel()
    keep = np.isfinite(a) & np.isfinite(b)
    if keep.sum() < 3 or np.std(a[keep]) == 0 or np.std(b[keep]) == 0:
        return float("nan")
    return float(np.corrcoef(a[keep], b[keep])[0, 1])


def check(item) -> dict:
    from fielddata.loaders import cao
    brand, vehicle = item
    v2 = cao.load(brand, vehicle, which="vin_2", names="generic").to_numpy(dtype=float)
    v3 = cao.load(brand, vehicle, which="vin_3", names="generic").to_numpy(dtype=float)
    n = (v2.shape[1] - 5) // 2
    assert v3.shape == (v2.shape[0], v2.shape[1] + 1), (brand, vehicle, v2.shape, v3.shape)
    cells2, dev2, trail2 = v2[:, 2:n + 2], v2[:, n + 2:2 * n + 2], v2[:, 2 * n + 2:]
    trail2_all, trail3_all = trail2.copy(), v3[:, 2 * n + 2:].copy()
    cells3, off3, trail3 = v3[:, 2:n + 2], v3[:, n + 2:2 * n + 2], v3[:, 2 * n + 2:]
    soc = trail2[:, 1]
    good = (~np.isin(v2, CODES).any(axis=1) & (np.abs(trail2[:, 2]) <= 1000) & (cells2 > 0).all(axis=1)
            & np.isfinite(v3[:, :2 * n + 2]).all(axis=1) & ~np.isin(v3[:, :2 * n + 2], CODES).any(axis=1) & (soc > 0))
    cells2, dev2, cells3, off3, soc = cells2[good], dev2[good], cells3[good], off3[good], soc[good]
    mean3 = cells3.mean(axis=1)
    error = np.abs(cells3 - (soc[:, None] + off3))
    row_std = cells3.std(axis=1)
    distance = cells2 - cells2.mean(axis=1, keepdims=True)
    return {
        "brand": brand, "vehicle": vehicle, "rows": len(v2), "rows_used": int(good.sum()),
        "mean_soc_corr": corr(mean3, soc), "mean_soc_median_ratio": float(np.median(mean3 / soc)),
        "offset_error_median": float(np.median(error)), "offset_error_p99": float(np.percentile(error, 99)),
        "cell_soc_row_std_median": float(np.median(row_std)), "cell_soc_row_std_p99": float(np.percentile(row_std, 99)),
        "trailing_copies_vin2": bool(np.array_equal(trail3_all[:, [0, 1, 3]], trail2_all, equal_nan=True)),
        "extra_min": float(np.nanmin(trail3_all[:, 2])), "extra_max": float(np.nanmax(trail3_all[:, 2])),
        "extra_distinct": int(len(np.unique(trail3_all[:, 2]))),
        "dev2_corr_with_cell_minus_mean": corr(dev2, distance),
        "dev2_corr_with_cell_minus_modepi": corr(dev2, modepi_difference(cells2)),
        "dev2_row_std_median": float(np.median(dev2.std(axis=1))),
        "dev2_vs_dsoc_corr": corr(dev2 - dev2.mean(axis=1, keepdims=True), off3 - off3.mean(axis=1, keepdims=True)),
    }


def summarize(frame: pd.DataFrame) -> list[str]:
    lines = []
    for brand, group in frame.groupby("brand"):
        match = (group.mean_soc_corr >= 0.99) & ((group.mean_soc_median_ratio - 1).abs() <= 0.01)
        q = lambda column, p: group[column].quantile(p)
        lines += [
            f"{brand}: {len(group)} vehicles, {int(group.rows_used.sum()):,} of {int(group.rows.sum()):,} rows used (rows with a placeholder value left out)",
            f"  vin_3 cell mean matches pack SOC (correlation >= 0.99 and median ratio within 1 percent of 1): {int(match.sum())} of {len(group)} vehicles",
            f"    correlation: minimum {group.mean_soc_corr.min():.4f}, median {group.mean_soc_corr.median():.4f}; median ratio: {group.mean_soc_median_ratio.min():.4f} to {group.mean_soc_median_ratio.max():.4f}",
            f"  cell = pack SOC + offset, absolute error: largest per-vehicle median {group.offset_error_median.max():.3g}, largest per-vehicle 99th percentile {group.offset_error_p99.max():.3g}",
            f"  per-cell SOC spread within a row (row standard deviation, median per vehicle): {q('cell_soc_row_std_median', 0):.3g} to {q('cell_soc_row_std_median', 1):.3g}, fleet median {q('cell_soc_row_std_median', 0.5):.3g}",
            f"  vin_3 trailing columns 1, 2 and 4 are exact copies of vin_2's temperature, SOC and current: {int(group.trailing_copies_vin2.sum())} of {len(group)} vehicles",
            f"  vin_3 trailing column 3 (the extra one): {group.extra_min.min():g} to {group.extra_max.max():g}; vehicles where it holds one value: {int((group.extra_distinct == 1).sum())} of {len(group)}",
            f"  vin_2 deviation vs cell minus row mean, correlation: {group.dev2_corr_with_cell_minus_mean.min():.3f} to {group.dev2_corr_with_cell_minus_mean.max():.3f}, median {group.dev2_corr_with_cell_minus_mean.median():.3f} ({int(group.dev2_corr_with_cell_minus_mean.isna().sum())} vehicles undefined)",
            f"  vin_2 deviation vs cell minus the authors' weighted mode, correlation: {group.dev2_corr_with_cell_minus_modepi.min():.3f} to {group.dev2_corr_with_cell_minus_modepi.max():.3f}, median {group.dev2_corr_with_cell_minus_modepi.median():.3f} ({int(group.dev2_corr_with_cell_minus_modepi.isna().sum())} vehicles undefined)",
            f"  vin_2 deviation spread across cells (row standard deviation, median per vehicle): {q('dev2_row_std_median', 0):.3g} to {q('dev2_row_std_median', 1):.3g}, fleet median {q('dev2_row_std_median', 0.5):.3g}",
            f"  per-cell part of the vin_2 voltage deviation vs per-cell part of the vin_3 SOC deviation, correlation: {group.dev2_vs_dsoc_corr.min():.3f} to {group.dev2_vs_dsoc_corr.max():.3f}, quartiles {q('dev2_vs_dsoc_corr', 0.25):.3f} / {q('dev2_vs_dsoc_corr', 0.5):.3f} / {q('dev2_vs_dsoc_corr', 0.75):.3f} ({int(group.dev2_vs_dsoc_corr.isna().sum())} vehicles undefined)",
        ]
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    workers = parser.parse_args().workers
    from fielddata.loaders import cao
    units = cao.systems()
    todo = [(r.brand, str(r.vehicle)) for r in units.itertuples() if r.brand in {"DTI", "QAS"} and r.vin_2 and r.vin_3]
    done = set()
    if PER_VEHICLE.exists():
        old = pd.read_csv(PER_VEHICLE, dtype={"vehicle": str})
        done = set(zip(old.brand, old.vehicle))
    todo = [item for item in todo if item not in done]
    PER_VEHICLE.parent.mkdir(parents=True, exist_ok=True)
    new_file = not PER_VEHICLE.exists()
    with open(PER_VEHICLE, "a", newline="", encoding="utf-8") as handle, Pool(workers) as pool:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        if new_file:
            writer.writeheader()
        for i, row in enumerate(pool.imap_unordered(check, todo), 1):
            writer.writerow(row)
            handle.flush()
            if i % 50 == 0:
                print(f"{i}/{len(todo)}", flush=True)
    frame = pd.read_csv(PER_VEHICLE, dtype={"vehicle": str})
    lines = summarize(frame)
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
