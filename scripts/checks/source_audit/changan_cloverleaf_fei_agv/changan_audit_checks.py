"""Changan source-audit data checks (reports/source_audit_2026-10-04/changan.md, findings 1, 4 and 8).

What it does: streams vehicles vin1, vin2 and vin3 in full through fielddata.loaders.changan.load (raw, clean=False)
and computes
  1. a cross-tabulation of chargestatus against the sign of totalcurrent (neg < 0, zero, pos > 0, missing), and a
     profile of each chargestatus code (rows, rows with totalvoltage == 0, rows with speed > 0, median totalcurrent,
     speed and soc), per vehicle;
  4. per vehicle, rows whose batteryvoltage or probetemperatures string is missing altogether; on vin1 also the
     number of ~-separated entries per present string and the number of strings with an empty entry (single-sensor
     gaps);
  5. per vehicle, the rows with totalcurrent == -1000 (seen in chargestatus 255 rows), cross-tabulated with
     chargestatus and with totalvoltage == 0, and the soc and temperature values in those rows (sentinel check);
  8. on vin1, the median of maxvoltagebattery and of all expanded batteryvoltage entries (1 mV histogram), raw data
     excluding exact zeros, and the count of values above 10 (which would mean mV).
Reads: the split archive raw/RAW_DATA.z01 + RAW_DATA.zip through the loader (on Windows the LIBARCHIVE environment
variable must point at the archive library DLL, for example the one installed with Anaconda).
Writes: prints results; writes per-vehicle CSVs to changan_audit_out/ next to this script and skips a vehicle whose
profile CSV already exists (delete the folder to rerun).
Run from the repo root: PYTHONPATH=. .venv/Scripts/python.exe <this file>   (about 15 minutes for vin1 to vin3)
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from fielddata.loaders import changan

OUT = pathlib.Path(__file__).with_name("changan_audit_out")
CHUNK = 500_000
EMPTY_ENTRY = r"^~|~~|~$|^$"


def sign(s: pd.Series) -> pd.Series:
    out = pd.Series("missing", index=s.index)
    out[s < 0] = "neg"
    out[s == 0] = "zero"
    out[s > 0] = "pos"
    return out


def median_of(hist: np.ndarray) -> float:
    c = np.cumsum(hist)
    return float(np.searchsorted(c, c[-1] / 2)) / 1000 if c[-1] else float("nan")


def run_vehicle(unit: str, detail: bool) -> None:
    prof_path = OUT / f"{unit}_chargestatus_profile.csv"
    if prof_path.exists():
        print(f"== {unit}: cached")
        for name in ("chargestatus_x_currentsign", "chargestatus_profile", "summary"):
            print(pd.read_csv(OUT / f"{unit}_{name}.csv", index_col=0).to_string())
        return
    ct = None
    parts = []
    summary = {"rows": 0, "batteryvoltage_missing": 0, "probetemperatures_missing": 0}
    cell_counts = pd.Series(dtype="float64")
    probe_counts = pd.Series(dtype="float64")
    maxv_hist = np.zeros(10001, dtype="int64")  # 0 to 10.000 V in 1 mV bins
    cell_hist = np.zeros(10001, dtype="int64")
    for chunk in changan.load(unit, chunksize=CHUNK):
        summary["rows"] += len(chunk)
        tab = pd.crosstab(chunk["chargestatus"].fillna(-1), sign(chunk["totalcurrent"]))
        ct = tab if ct is None else ct.add(tab, fill_value=0)
        parts.append(chunk[["chargestatus", "totalvoltage", "totalcurrent", "speed", "soc"]].assign(
            chargestatus=chunk["chargestatus"].fillna(-1)))
        bv, pt = chunk["batteryvoltage"], chunk["probetemperatures"]
        summary["batteryvoltage_missing"] += int(bv.isna().sum())
        summary["probetemperatures_missing"] += int(pt.isna().sum())
        if detail:
            bv, pt = bv.dropna().astype(str), pt.dropna().astype(str)
            cell_counts = cell_counts.add(bv.str.count("~").add(1).value_counts(), fill_value=0)
            probe_counts = probe_counts.add(pt.str.count("~").add(1).value_counts(), fill_value=0)
            summary["batteryvoltage_with_empty_entry"] = summary.get("batteryvoltage_with_empty_entry", 0) + int(bv.str.contains(EMPTY_ENTRY).sum())
            summary["probetemperatures_with_empty_entry"] = summary.get("probetemperatures_with_empty_entry", 0) + int(pt.str.contains(EMPTY_ENTRY).sum())
            mv = chunk["maxvoltagebattery"].dropna().to_numpy()
            mv = mv[mv != 0]
            summary["maxvoltagebattery_gt10"] = summary.get("maxvoltagebattery_gt10", 0) + int((mv > 10).sum())
            maxv_hist += np.bincount(np.rint(mv[(mv >= 0) & (mv <= 10)] * 1000).astype(int), minlength=10001)[:10001]
            cells = changan.expand(chunk.dropna(subset=["batteryvoltage"]), "batteryvoltage").to_numpy().ravel()
            cells = cells[~np.isnan(cells) & (cells != 0)]
            summary["cell_values_gt10"] = summary.get("cell_values_gt10", 0) + int((cells > 10).sum())
            cell_hist += np.bincount(np.rint(cells[(cells >= 0) & (cells <= 10)] * 1000).astype(int), minlength=10001)[:10001]
        print(f"{unit}: {summary['rows']:,} rows read", flush=True)
    ct = ct.fillna(0).astype("int64")
    allrows = pd.concat(parts)
    prof = allrows.groupby("chargestatus").agg(
        rows=("totalcurrent", "size"),
        totalvoltage_zero=("totalvoltage", lambda s: int((s == 0).sum())),
        speed_gt0=("speed", lambda s: int((s > 0).sum())),
        median_current=("totalcurrent", "median"),
        median_speed=("speed", "median"),
        median_soc=("soc", "median"),
    )
    if detail:
        summary["median_maxvoltagebattery_V"] = median_of(maxv_hist)
        summary["maxvoltagebattery_values"] = int(maxv_hist.sum())
        summary["median_cell_V"] = median_of(cell_hist)
        summary["cell_values"] = int(cell_hist.sum())
        summary["batteryvoltage_entries_per_row"] = str({int(k): int(v) for k, v in cell_counts.sort_index().items()})
        summary["probetemperatures_entries_per_row"] = str({int(k): int(v) for k, v in probe_counts.sort_index().items()})
    summ = pd.Series(summary, name="value").to_frame()
    print(f"== {unit}")
    for frame in (ct, prof, summ):
        print(frame.to_string())
    ct.to_csv(OUT / f"{unit}_chargestatus_x_currentsign.csv")
    summ.to_csv(OUT / f"{unit}_summary.csv")
    prof.to_csv(prof_path)


def sentinel_vehicle(unit: str) -> None:
    path = OUT / f"{unit}_current_minus1000.csv"
    if path.exists():
        print(f"== {unit} totalcurrent == -1000: cached")
        print(pd.read_csv(path).to_string())
        return
    parts = []
    total = 0
    for chunk in changan.load(unit, chunksize=CHUNK):
        total += len(chunk)
        hit = chunk[(chunk["totalcurrent"] == -1000) | (chunk["chargestatus"] == 255) | (chunk["totalvoltage"] == 0)]
        parts.append(hit.drop(columns=["batteryvoltage", "probetemperatures"]))
    hits = pd.concat(parts)
    hits = hits.assign(current_is_minus1000=hits["totalcurrent"] == -1000, voltage_is_zero=hits["totalvoltage"] == 0,
                       chargestatus=hits["chargestatus"].fillna(-1))
    tab = (hits.groupby(["chargestatus", "current_is_minus1000", "voltage_is_zero"])
           .agg(rows=("soc", "size"), soc_values=("soc", lambda s: str(sorted(s.dropna().unique().tolist())[:10])),
                speed_gt0=("speed", lambda s: int((s > 0).sum())),
                maxtemp_values=("maxtemperaturevalue", lambda s: str(sorted(s.dropna().unique().tolist())[:10])),
                minvoltagebattery_zero=("minvoltagebattery", lambda s: int((s == 0).sum())))
           .reset_index())
    tab.insert(0, "vehicle_rows", total)
    print(f"== {unit} rows with totalcurrent == -1000, chargestatus 255 or totalvoltage 0")
    print(tab.to_string())
    tab.to_csv(path, index=False)


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    OUT.mkdir(exist_ok=True)
    for unit, detail in (("vin1", True), ("vin2", False), ("vin3", False)):
        run_vehicle(unit, detail)
    for unit in ("vin1", "vin2", "vin3"):
        sentinel_vehicle(unit)
