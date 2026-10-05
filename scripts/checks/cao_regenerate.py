"""Settle the remaining unidentified Cao columns by testing them against the authors' own (unused) functions.

What it does: for every DTI and QAS vehicle, through fielddata.loaders.cao, on rows without placeholder values:
1. Leading columns of vin_2 and vin_3: the best single match among the authors' calculate_volt_modepi() (the
   paper's Eq. 2 pack voltage, Function_.py), the row mean, median, max and min of the cell voltages, pack SOC,
   current, temperature and the vin_3 cell-SOC mean (R^2 of a linear rescale), and a joint fit on volt_modepi,
   current and pack SOC, the inputs of the pack model's terminal voltage U = OCV(SOC) - U_P - R0*I (SI Note S1).
2. vin_1 (rows x 1 x 7, normalized): each column's best match among the same candidates, the leading columns,
   the cell-voltage sum and the same candidates one row later (linear rescale R^2), whether it is constant, the
   share of non-decreasing steps (a mileage counter never decreases), and for a column that varies but matches
   nothing, a speed test: its value during charging (current below -1 A, positive current is discharge).
3. vin_2 deviation block (dU_i): the per-row correlation of its per-cell part with the per-cell part of the vin_3
   SOC deviation (dSOC_i), and an approximate regeneration with Function_.py's deviation formula
   dU_i = OCV(SOC + dSOC_i) - OCV(SOC) - I*DRi, DRi = 3e-6, with an OCV polynomial (degree 5) fitted per vehicle
   from rest rows (|current| < 2 A), because the authors' coefficients b are not released.
4. DTI vin_3 extra column: non-decreasing share, distinct values, and its best correlation with every other
   column of vin_2, vin_3 and vin_1 and with the row index.

Reads: vin_1, vin_2 and vin_3 of every DTI and QAS vehicle through fielddata.loaders.cao.
Writes: reports/checks/cao_regenerate_per_vehicle.csv (one row per vehicle, resumable) and
reports/checks/cao_regenerate.txt (summary per brand).

Run (about five minutes on six processes; finished vehicles are skipped):
    python scripts/checks/cao_regenerate.py [--workers 6]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PER_VEHICLE = ROOT / "reports" / "checks" / "cao_regenerate_per_vehicle.csv"
SUMMARY = ROOT / "reports" / "checks" / "cao_regenerate.txt"
CODES = (-1004.8, -1000.0, -999.0, 65535.0)
FIELDS = ["brand", "vehicle", "rows", "rows_used", "vin1_rows_match", "leading", "vin1", "dU_rowcorr_median",
          "dU_regen_rowcorr_median", "dU_regen_abs_error_median", "dU_abs_median", "extra"]


def volt_modepi(cells: np.ndarray) -> np.ndarray:
    """The authors' calculate_volt_modepi (Function_.py), the inverse-Gaussian weighted mean of the paper's Eq. 2."""
    frame = pd.DataFrame(cells)
    mode, std = frame.mean(axis=1), frame.std(axis=1)
    lam = 1 / std
    pi1 = (1 / (2 * np.pi * frame.pow(3))).mul(lam, axis=0).pow(0.5)
    pi2 = ((-1) * frame.sub(mode, axis=0).pow(2).mul(lam, axis=0) / (2 * frame.mul(mode.pow(2), axis=0))).apply(np.exp)
    weights = pi1 * pi2
    return ((weights * frame).sum(axis=1) / weights.sum(axis=1)).to_numpy()


def r2(x: np.ndarray, y: np.ndarray) -> float:
    """R^2 of the best linear rescale y ~ p*x + q (x may have several columns)."""
    x = x.reshape(len(x), -1)
    keep = np.isfinite(x).all(axis=1) & np.isfinite(y)
    if keep.sum() < 10 or np.std(y[keep]) == 0 or (np.std(x[keep], axis=0) == 0).all():
        return float("nan")
    design = np.column_stack([x[keep], np.ones(keep.sum())])
    coef, *_ = np.linalg.lstsq(design, y[keep], rcond=None)
    residual = y[keep] - design @ coef
    return float(1 - residual.var() / y[keep].var())


def best(candidates: dict, y: np.ndarray, skip=()) -> tuple[str, float]:
    scores = [(r2(value, y), name) for name, value in candidates.items() if name not in skip]
    scores = [(s, n) for s, n in scores if np.isfinite(s)]
    if not scores:
        return "none", float("nan")
    score, name = max(scores)
    return name, round(score, 5)


def rowcorr(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a - a.mean(axis=1, keepdims=True)
    b = b - b.mean(axis=1, keepdims=True)
    # rows where either side is the same in every cell (to rounding) have no per-cell part: undefined
    varied = (np.abs(a).max(axis=1) > 1e-9) & (np.abs(b).max(axis=1) > 1e-9)
    den = np.sqrt((a ** 2).sum(axis=1) * (b ** 2).sum(axis=1))
    return np.where(varied & (den > 0), (a * b).sum(axis=1) / np.where(den > 0, den, 1), np.nan)


def check(item) -> dict:
    from fielddata.loaders import cao
    brand, vehicle = item
    v1 = np.asarray(cao.load_raw(brand, vehicle, "vin_1"), dtype=float)[:, 0, :]
    v2 = cao.load(brand, vehicle, which="vin_2", names="inferred")
    v3 = cao.load(brand, vehicle, which="vin_3", names="inferred")
    a2, a3 = v2.to_numpy(float), v3.to_numpy(float)
    n = (a2.shape[1] - 5) // 2
    current, soc, temp = v2.current_A.to_numpy(), v2.soc_pct.to_numpy(), v2.temperature_degC.to_numpy()
    cells = a2[:, 2:n + 2]
    good = ~np.isin(a2, CODES).any(axis=1) & (np.abs(current) <= 1000) & (cells > 0).all(axis=1)
    out = {"brand": brand, "vehicle": vehicle, "rows": len(a2), "rows_used": int(good.sum()), "vin1_rows_match": len(v1) == len(a2)}
    g = good
    mp = volt_modepi(cells)
    base = {"volt_modepi": mp, "cell mean": cells.mean(1), "cell median": np.median(cells, 1), "cell max": cells.max(1),
            "cell min": cells.min(1), "pack SOC": soc, "current": current, "temperature": temp, "cell SOC mean": a3[:, 2:n + 2].mean(1)}
    # 1. leading columns
    leading = {}
    for name, column in [("vin_2 col 0", a2[:, 0]), ("vin_2 col 1", a2[:, 1]), ("vin_3 col 0", a3[:, 0]), ("vin_3 col 1", a3[:, 1])]:
        match, score = best({k: v[g] for k, v in base.items()}, column[g])
        leading[name] = {"best": match, "r2": score, "joint_modepi_current_soc_r2": round(r2(np.column_stack([mp, current, soc])[g], column[g]), 5),
                         "median_abs_diff_to_modepi": float(f"{np.median(np.abs(column[g] - mp[g])):.4g}")}
    out["leading"] = json.dumps(leading)
    # 2. vin_1
    vin1 = {}
    if len(v1) == len(a2):
        cand = dict(base)
        cand.update({"cell sum": cells.sum(1), "vin_2 col 0": a2[:, 0], "vin_2 col 1": a2[:, 1], "vin_3 col 0": a3[:, 0], "vin_3 col 1": a3[:, 1]})
        nxt = {k + " (next row)": np.r_[v[1:], np.nan] for k, v in cand.items()}
        cand.update(nxt)
        gm = g & np.r_[g[1:], False]
        for j in range(7):
            column = v1[:, j]
            constant = bool(np.nanstd(column) == 0)
            match, score = ("constant", float("nan")) if constant else best({k: v[gm] for k, v in cand.items()}, column[gm])
            step = np.diff(column)
            entry = {"best": match, "r2": score, "constant_value": float(column[0]) if constant else None,
                     "nondecreasing_share": round(float(np.mean(step >= 0)), 3)}
            if not constant and (not np.isfinite(score) or score < 0.95):
                charging = g & (current < -1)
                low = np.nanmin(column)
                entry["share_at_minimum_while_charging"] = round(float(np.mean(column[charging] <= low + 1e-9)), 3) if charging.any() else None
                entry["share_at_minimum_overall"] = round(float(np.mean(column <= low + 1e-9)), 3)
                entry["r2_with_abs_current"] = round(r2(np.abs(current)[g], column[g]), 4)
            vin1[str(j)] = entry
    out["vin1"] = json.dumps(vin1)
    # 3. dU against dSOC, and an approximate regeneration of dU from Function_.py's formula
    du, ds = a2[g][:, n + 2:2 * n + 2], a3[g][:, n + 2:2 * n + 2]
    rc = rowcorr(du, ds)
    out["dU_rowcorr_median"] = float(np.nanmedian(rc)) if np.isfinite(rc).any() else float("nan")
    out["dU_abs_median"] = float(np.median(np.abs(du)))
    out["dU_regen_rowcorr_median"] = float("nan")
    out["dU_regen_abs_error_median"] = float("nan")
    scale = 100.0  # the loader returns SOC in percent for both brands
    rest = g & (np.abs(current) < 2)
    if rest.sum() > 50 and np.std(soc[rest]) > 0:
        poly = np.polyfit(soc[rest] / scale, mp[rest], 5)
        x = soc[g][:, None] / scale
        regen = np.polyval(poly, x + ds / scale) - np.polyval(poly, x) - current[g][:, None] * 3e-6
        rr = rowcorr(du, regen)
        out["dU_regen_rowcorr_median"] = float(np.nanmedian(rr)) if np.isfinite(rr).any() else float("nan")
        out["dU_regen_abs_error_median"] = float(np.median(np.abs(du - regen)))
    # 4. DTI extra column
    if brand == "DTI":
        extra = v3.extra.to_numpy()
        others = {f"vin_2 {c}": a2[:, i] for i, c in enumerate(v2.columns) if not c.startswith(("cell_v_", "cell_dU_"))}
        others.update({f"vin_3 {c}": a3[:, i] for i, c in enumerate(v3.columns) if not c.startswith(("cell_soc_", "cell_dsoc_")) and c != "extra"})
        others.update({"cell mean": cells.mean(1), "volt_modepi": mp, "row index": np.arange(len(a2), dtype=float)})
        if len(v1) == len(a2):
            others.update({f"vin_1 col {j}": v1[:, j] for j in range(7)})
        scores = []
        for name, value in others.items():
            keep = np.isfinite(value) & np.isfinite(extra)
            if keep.sum() > 10 and np.std(value[keep]) > 0 and np.std(extra[keep]) > 0:
                scores.append((abs(float(np.corrcoef(value[keep], extra[keep])[0, 1])), name))
        scores.sort(reverse=True)
        zero = extra == 0
        share = lambda mask: round(float(np.mean(zero[mask])), 3) if mask.any() else None
        out["extra"] = json.dumps({"nondecreasing_share": round(float(np.mean(np.diff(extra) >= 0)), 3), "distinct": int(len(np.unique(extra))),
                                   "integers": bool(np.allclose(extra, np.round(extra))), "max": float(extra.max()),
                                   "zero_share_rest": share(np.abs(current) < 1), "zero_share_discharging": share(current > 5), "zero_share_charging": share(current < -1),
                                   "best": [(name, round(score, 3)) for score, name in scores[:3]]})
    else:
        out["extra"] = ""
    return out


def summarize(frame: pd.DataFrame) -> list[str]:
    lines = []
    for brand, group in frame.groupby("brand"):
        lines.append(f"{brand}: {len(group)} vehicles, vin_1 has as many rows as vin_2 in {int(group.vin1_rows_match.sum())}")
        leading = [json.loads(x) for x in group.leading]
        for name in ["vin_2 col 0", "vin_2 col 1", "vin_3 col 0", "vin_3 col 1"]:
            entries = [x[name] for x in leading]
            counts = pd.Series([e["best"] for e in entries]).value_counts()
            r2s = pd.Series([e["r2"] for e in entries], dtype=float)
            joint = pd.Series([e["joint_modepi_current_soc_r2"] for e in entries], dtype=float)
            lines.append(f"  {name}: best single match {dict(counts.head(3))}, its R^2 median {r2s.median():.3f}; joint fit on volt_modepi, current and pack SOC R^2 median {joint.median():.3f} (10th percentile {joint.quantile(0.1):.3f})")
        vin1 = [json.loads(x) for x in group.vin1 if x and x != "{}"]
        for j in range(7):
            entries = [x[str(j)] for x in vin1]
            counts = pd.Series([e["best"] for e in entries]).value_counts()
            r2s = pd.Series([e["r2"] for e in entries], dtype=float)
            nondecr = pd.Series([e["nondecreasing_share"] for e in entries], dtype=float)
            line = f"  vin_1 col {j}: best match {dict(counts.head(3))}, R^2 median {r2s.median():.4f} (10th percentile {r2s.quantile(0.1):.4f}); non-decreasing share max {nondecr.max():.3f}"
            const = [e["constant_value"] for e in entries if e["best"] == "constant"]
            if const:
                line += f"; constant in {len(const)} vehicles (values {sorted(set(const))[:3]})"
            speed = pd.Series([e.get("share_at_minimum_while_charging") for e in entries], dtype=float).dropna()
            if len(speed):
                overall = pd.Series([e.get("share_at_minimum_overall") for e in entries], dtype=float).dropna()
                absr = pd.Series([e.get("r2_with_abs_current") for e in entries], dtype=float).dropna()
                line += (f"; where unmatched ({len(speed)} vehicles): at its minimum while charging median {speed.median():.3f} "
                         f"against {overall.median():.3f} overall, R^2 with |current| median {absr.median():.3f}")
            lines.append(line)
        q = group.dU_rowcorr_median
        lines.append(f"  dU vs dSOC, per-row correlation of the per-cell parts: median over vehicles {q.median():.3f}, 10th to 90th percentile {q.quantile(0.1):.3f} to {q.quantile(0.9):.3f} ({int(q.isna().sum())} vehicles undefined)")
        r = group.dU_regen_rowcorr_median
        lines.append(f"  dU regenerated with a fitted OCV curve: per-row correlation median {r.median():.3f} (10th to 90th percentile {r.quantile(0.1):.3f} to {r.quantile(0.9):.3f}); "
                     f"median absolute error {group.dU_regen_abs_error_median.median():.3g} against a median |dU| of {group.dU_abs_median.median():.3g}")
        if brand == "DTI":
            extra = [json.loads(x) for x in group.extra if x]
            tops = pd.Series([e["best"][0][0] for e in extra if e["best"]]).value_counts()
            topr = pd.Series([e["best"][0][1] for e in extra if e["best"]], dtype=float)
            nondecr = pd.Series([e["nondecreasing_share"] for e in extra], dtype=float)
            lines.append(f"  DTI extra column: best correlate {dict(tops.head(3))}, |r| median {topr.median():.3f}; non-decreasing share median {nondecr.median():.3f}, max {nondecr.max():.3f}")
            z = lambda key: pd.Series([e[key] for e in extra], dtype=float).dropna()
            lines.append(f"    integers in {sum(e['integers'] for e in extra)} of {len(extra)} vehicles, maximum {max(e['max'] for e in extra):g}; share of rows at zero, median over vehicles: "
                         f"at rest {z('zero_share_rest').median():.3f}, discharging {z('zero_share_discharging').median():.3f}, charging {z('zero_share_charging').median():.3f}")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    workers = parser.parse_args().workers
    from fielddata.loaders import cao
    units = cao.systems()
    todo = [(r.brand, str(r.vehicle)) for r in units.itertuples() if r.brand in {"DTI", "QAS"} and r.vin_1 and r.vin_2 and r.vin_3]
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
    frame = pd.read_csv(PER_VEHICLE, dtype={"vehicle": str}, keep_default_na=False, na_values=[""])
    for column in ["dU_rowcorr_median", "dU_regen_rowcorr_median", "dU_regen_abs_error_median", "dU_abs_median", "rows", "rows_used"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["vin1_rows_match"] = frame["vin1_rows_match"].astype(str) == "True"
    lines = summarize(frame)
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
