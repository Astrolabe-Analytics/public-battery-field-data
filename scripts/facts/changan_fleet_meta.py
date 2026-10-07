"""Rebuild changan's per-vehicle summary (data/fleet_meta.csv) from the raw split archive.

fleet_meta.csv was made by this collection, not released, and the script that made it was not kept. This
script recomputes every column from data/raw/RAW_DATA.z01 + RAW_DATA.zip through fielddata.loaders.changan
and compares the result with the held fleet_meta.csv.

Column rules, fixed on vin2 and then confirmed on all 300 vehicles (every column below matches the held file):
- rows: rows with a BMS reading and a time (soc and terminaltime present; vin38 has one row with soc but no
  terminaltime). All other columns use these rows only.
- files: 1 (one CSV per vehicle RAR).
- span_days: (max - min terminaltime) / 86,400. terminaltime is a per-vehicle relative clock that can step
  backwards, so first-to-last in file order is not used.
- odo_start, odo_end: min and max totalodometer.
- dt_median: median step of terminaltime after a stable sort.
- i_res: smallest step between distinct totalcurrent values.
- soc_mean: mean soc. pct_charging: percent of rows with chargestatus 1.
- t_min_seen, t_max_seen: min of mintemperaturevalue and max of maxtemperaturevalue (raw, -40 sentinel kept).
- sessions: charging sessions. The original rule is unknown, so several candidates are recorded as
  sessions_g<gap>_m<rows> (a run of chargestatus 1 after sorting, split where the step exceeds <gap> s, kept
  if it has at least <rows> rows); `compare` picks the candidate that matches the most vehicles. None of them
  reproduces the held counts (at best 3 of 300 vehicles), so the held session counts cannot be rebuilt from
  the raw data. No fact or table uses them.

Reads: the raw split archive through fielddata.loaders.changan, and the held fleet_meta.csv through
changan.fleet() for the comparison.
Writes: reports/facts/_cache/changan_fleet_meta.csv (the rebuilt table, one row per vehicle, not committed:
it is derived from a CC BY-NC-SA release) and reports/checks/changan_fleet_meta_compare.txt (the comparison).

Run (resumable; finished vehicles are skipped):
    python scripts/facts/changan_fleet_meta.py build [--workers 6]
    python scripts/facts/changan_fleet_meta.py compare
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "reports" / "facts" / "_cache" / "changan_fleet_meta.csv"
REPORT = ROOT / "reports" / "checks" / "changan_fleet_meta_compare.txt"
KEEP = ["terminaltime", "soc", "totalodometer", "chargestatus", "totalcurrent",
        "mintemperaturevalue", "maxtemperaturevalue"]
CANDIDATES = [(g, m) for g in (300, 600, 1800) for m in (1, 6, 30)]
BASE = ["veh", "rows", "files", "span_days", "odo_start", "odo_end", "dt_median", "i_res", "soc_mean",
        "pct_charging", "t_min_seen", "t_max_seen"]
FIELDS = BASE + ["rows_all", "runs"] + [f"sessions_g{g}_m{m}" for g, m in CANDIDATES] + ["seconds"]


def summarize(unit: str) -> dict:
    from fielddata.loaders import changan
    start = time.time()
    parts, rows_all = [], 0
    for chunk in changan.load(unit, chunksize=500_000):
        rows_all += len(chunk)
        parts.append(chunk[KEEP].dropna(subset=["soc", "terminaltime"]))
    d = pd.concat(parts, ignore_index=True).sort_values("terminaltime", kind="stable")
    t = d["terminaltime"].to_numpy()
    current = np.unique(d["totalcurrent"].dropna().to_numpy())
    charging = (d["chargestatus"] == 1).to_numpy()
    step = np.r_[np.inf, np.diff(t)]
    previous = np.r_[False, charging[:-1]]
    row = {
        "veh": unit, "rows": len(d), "files": 1, "span_days": (t.max() - t.min()) / 86400,
        "odo_start": d["totalodometer"].min(), "odo_end": d["totalodometer"].max(),
        "dt_median": float(np.median(np.diff(t))), "i_res": float(np.diff(current).min()),
        "soc_mean": d["soc"].mean(), "pct_charging": 100 * charging.mean(),
        "t_min_seen": d["mintemperaturevalue"].min(), "t_max_seen": d["maxtemperaturevalue"].max(),
        "rows_all": rows_all, "runs": int((charging & ~previous).sum()),
    }
    for gap, minimum in CANDIDATES:
        new = charging & (~previous | (step > gap))
        sizes = np.bincount(np.cumsum(new)[charging])
        row[f"sessions_g{gap}_m{minimum}"] = int((sizes >= minimum).sum())
    row["seconds"] = round(time.time() - start)
    return row


def build(workers: int) -> None:
    from fielddata.loaders import changan
    units = list(changan.systems()["unit"])
    done = set(pd.read_csv(OUT)["veh"]) if OUT.exists() else set()
    todo = [u for u in units if u not in done]
    print(f"{len(done)} done, {len(todo)} to go", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    new_file = not OUT.exists()
    with open(OUT, "a", newline="", encoding="utf-8") as handle, Pool(workers) as pool:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        for i, row in enumerate(pool.imap_unordered(summarize, todo), 1):
            writer.writerow(row)
            handle.flush()
            print(f"{i}/{len(todo)} {row['veh']} rows={row['rows']} {row['seconds']}s", flush=True)


def compare() -> None:
    from fielddata.loaders import changan
    held = changan.fleet().set_index("veh")
    new = pd.read_csv(OUT).set_index("veh")
    lines = [f"rows: held {len(held)}, rebuilt {len(new)}, in both {len(held.index.intersection(new.index))}"]
    both = held.index.intersection(new.index)
    held, new = held.loc[both], new.loc[both]
    matches = {c: int((new[c] == held["sessions"]).sum()) for c in new.columns if c.startswith(("sessions_", "runs"))}
    best = max(matches, key=matches.get)
    lines.append(f"sessions candidates (vehicles matching exactly): {matches}")
    new["sessions"] = new[best]
    lines.append(f"{'column':14} {'max abs diff':>14} {'vehicles differing':>19}")
    for c in BASE[1:] + ["sessions"]:
        diff = (new[c] - held[c]).abs()
        differing = int(((diff > 1e-9) | (new[c].isna() != held[c].isna())).sum())
        lines.append(f"{c:14} {diff.max():14.6g} {differing:19d}")
    lines.append(f"unit-years: held {held['span_days'].sum() / 365.25:.4f}, rebuilt {new['span_days'].sum() / 365.25:.4f}")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["build", "compare"])
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    build(args.workers) if args.step == "build" else compare()
