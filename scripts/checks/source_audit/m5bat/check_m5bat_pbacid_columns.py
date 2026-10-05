"""Per-year, per-column profile of the m5bat-pbacid release, read through the loader (raw, clean=False).

What it does: for every source (bms, bsc), year and column it records the row count, non-null count, exact
matches to the codebook sentinels 2345 and 2356, minimum, maximum, number of distinct values, the most common
value and its share, and (for the cumulative counters) the count equal to 65535 (0xFFFF). For every source
and year it also records the distribution of index steps (0 s, 1 s, 2-5 s, 6-60 s, over 60 s).
Reads: fielddata.loaders.m5bat_pbacid.load(source, years=[year], columns=[...]).
Writes: <out>/m5bat_pbacid_columns.csv and <out>/m5bat_pbacid_steps.csv, incrementally; items already
recorded are skipped on a rerun.
Usage: python check_m5bat_pbacid_columns.py <out_dir>
"""
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fielddata.loaders import m5bat_pbacid as m

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "reports")
OUT.mkdir(parents=True, exist_ok=True)
COLS_CSV = OUT / "m5bat_pbacid_columns.csv"
STEPS_CSV = OUT / "m5bat_pbacid_steps.csv"
COL_FIELDS = ["source", "year", "column", "n_rows", "n_nonnull", "n_eq_2345", "n_eq_2356", "n_eq_65535",
              "min", "max", "n_distinct", "top_value", "top_share"]
STEP_FIELDS = ["source", "year", "n_rows", "step_negative", "dup_0s", "step_1s", "step_2_5s", "step_6_60s", "step_gt_60s", "first", "last"]


def done(path, keys):
    if not path.exists():
        return set()
    with open(path, newline="") as f:
        return {tuple(row[k] for k in keys) for row in csv.DictReader(f)}


def append(path, fields, row):
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow(row)


def profile(series):
    s = series.dropna()
    row = {"n_rows": len(series), "n_nonnull": len(s), "n_eq_2345": int((s == 2345).sum()),
           "n_eq_2356": int((s == 2356).sum()), "n_eq_65535": int((s == 65535).sum())}
    if len(s):
        counts = s.value_counts()
        row.update({"min": float(s.min()), "max": float(s.max()), "n_distinct": len(counts),
                    "top_value": float(counts.index[0]), "top_share": round(counts.iloc[0] / len(s), 6)})
    return row


def main():
    cols_done = done(COLS_CSV, ["source", "year", "column"])
    steps_done = done(STEPS_CSV, ["source", "year"])
    for source in ("bms", "bsc"):
        all_columns = list(m.preview(source, 2025, rows=1).columns)
        group = 8 if source == "bms" else 6
        for year in range(2017, 2026):
            for i in range(0, len(all_columns), group):
                wanted = [c for c in all_columns[i:i + group] if (source, str(year), c) not in cols_done]
                if not wanted and (i > 0 or (source, str(year)) in steps_done):
                    continue
                frame = m.load(source, years=[year], columns=wanted or all_columns[:1])
                if i == 0 and (source, str(year)) not in steps_done:
                    step = np.diff(frame.index.asi8) / 1e9
                    append(STEPS_CSV, STEP_FIELDS, {
                        "source": source, "year": year, "n_rows": len(frame), "step_negative": int((step < 0).sum()), "dup_0s": int((step == 0).sum()),
                        "step_1s": int((step == 1).sum()), "step_2_5s": int(((step > 1) & (step <= 5)).sum()),
                        "step_6_60s": int(((step > 5) & (step <= 60)).sum()), "step_gt_60s": int((step > 60).sum()),
                        "first": frame.index.min(), "last": frame.index.max()})
                for column in wanted:
                    append(COLS_CSV, COL_FIELDS, {"source": source, "year": year, "column": column, **profile(frame[column])})
                    print(source, year, column, flush=True)
                del frame


if __name__ == "__main__":
    main()
