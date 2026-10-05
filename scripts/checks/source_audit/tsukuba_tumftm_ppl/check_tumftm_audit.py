"""Source-audit data checks for the tumftm release (reports/source_audit_2026-10-04/tumftm.md).

What it does: through the tumftm loader only, for each of the seven vehicles and each signal listed in
value_overview.csv (signals()), loads the raw rows of that signal (load(unit, value_id=...)) and records the
row count, the first and last timestamp (raw, and with timestamps from 2030 on excluded), the value range, the
number of rows dated 2030 or later, the median spacing between consecutive timestamps, and the rows after
2023-04-01. It then prints: which value_ids are present per vehicle (including the ids >= 1288 that the
authors' histogram code computes), the per-vehicle first and last timestamps compared with the paper's UDS
test periods (Table 2), the summed span in unit-years, the hv_soc range, and the 2087 rows.
Reads: the tumftm release through fielddata (seven parquet files, about 98 million rows in all).
Writes: check_tumftm_audit_signals.csv next to this script (one row per vehicle and value_id; a rerun skips
pairs already recorded) and prints a summary.
Run from the repo root: .venv/Scripts/python.exe <path to this file>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))  # run from the repo root

import numpy as np
import pandas as pd

import fielddata
from fielddata.loaders import tumftm

OUT = Path(__file__).with_name("check_tumftm_audit_signals.csv")
CUTOFF = pd.Timestamp("2030-01-01")


def scan():
    sig = tumftm.signals()
    done = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame(columns=["unit", "value_id"])
    seen = set(zip(done["unit"].astype(str), done["value_id"].astype(int)))
    for unit in tumftm.systems()["unit"]:
        for vid in sig["value_id"]:
            if (unit, int(vid)) in seen:
                continue
            f = fielddata.load("tumftm", unit=unit, value_id=int(vid))
            t = f["time"]
            ok = t[t < CUTOFF].sort_values()
            v = f["value"]
            rec = {"unit": unit, "value_id": int(vid), "variable_name": sig.set_index("value_id").loc[vid, "variable_name"],
                   "rows": len(f), "rows_2030_on": int((t >= CUTOFF).sum()),
                   "time_min_raw": t.min(), "time_max_raw": t.max(), "time_min": ok.min(), "time_max": ok.max(),
                   "rows_after_2023_04_01": int(((t >= "2023-04-01") & (t < CUTOFF)).sum()),
                   "value_min": v.min(), "value_max": v.max(), "value_median": v.median(),
                   "median_spacing_s": ok.diff().dt.total_seconds().median() if len(ok) > 1 else np.nan,
                   "years_2087": ",".join(sorted({str(y) for y in t[t >= CUTOFF].dt.year.unique()}))}
            pd.DataFrame([rec]).to_csv(OUT, mode="a", header=not OUT.exists(), index=False)
            print(f"[scan] {unit} {vid} rows {len(f)}", flush=True)
    return pd.read_csv(OUT, parse_dates=["time_min_raw", "time_max_raw", "time_min", "time_max"])


def summary(per):
    pd.set_option("display.width", 250)
    present = per[per["rows"] > 0]
    print("\n[value_ids present per vehicle]")
    print(present.pivot_table(index=["value_id", "variable_name"], columns="unit", values="rows", aggfunc="sum").fillna(0).astype(int).to_string())
    absent = sorted(set(per["value_id"]) - set(present["value_id"]))
    print("[value_ids in value_overview.csv with no rows in any vehicle]", absent)
    print("[value_ids >= 1288 with rows]", sorted(set(present.loc[present["value_id"] >= 1288, "value_id"])))

    print("\n[per-vehicle bounds, timestamps from 2030 on excluded]")
    b = present.groupby("unit").agg(first=("time_min", "min"), last=("time_max", "max"), rows=("rows", "sum"),
                                    rows_2030_on=("rows_2030_on", "sum"), rows_after_2023_04_01=("rows_after_2023_04_01", "sum"))
    b["years"] = (b["last"] - b["first"]).dt.total_seconds() / (365.25 * 86400)
    print(b.to_string())
    print(f"  summed span {b['years'].sum():.3f} unit-years")
    for unit in b.index:
        after = present[(present["unit"] == unit) & (present["rows_after_2023_04_01"] > 0)]
        print(f"  {unit}: value_ids with rows after 2023-04-01: {sorted(after['value_id'])}; "
              f"last per id: {dict(zip(after['value_id'], after['time_max'].dt.date.astype(str)))}" if unit.startswith("CUP") else "", end="")
        print()

    print("\n[2087 rows]")
    print(present[present["rows_2030_on"] > 0][["unit", "value_id", "variable_name", "rows_2030_on", "years_2087", "time_max_raw"]].to_string(index=False))
    print(f"  total rows dated 2030 or later: {int(present['rows_2030_on'].sum())}")

    print("\n[value ranges, raw, and median spacing between rows of one signal]")
    print(present[["unit", "value_id", "variable_name", "value_min", "value_max", "median_spacing_s"]].to_string(index=False))


def soc_extremes():
    print("\n[hv_soc 900: share of rows below 4 % and above 96 %, raw]")
    for unit in tumftm.systems()["unit"]:
        v = fielddata.load("tumftm", unit=unit, value_id=900)["value"]
        print(f"  {unit}: rows {len(v)}, min {v.min()}, max {v.max()}, <4 %: {int((v < 4).sum())}, >96 %: {int((v > 96).sum())}")


def out_of_range():
    """Rows outside the min_val/max_val that value_overview.csv gives for each signal (raw values)."""
    sig = tumftm.signals().set_index("value_id")
    print("\n[rows outside value_overview.csv min_val..max_val, raw; most frequent offending values]")
    total = 0
    for unit in tumftm.systems()["unit"]:
        for vid in (4, 15, 56, 900, 961, 1200, 1208, 1209, 1265, 1269, 1272, 1273, 43, 1205, 1207):
            v = fielddata.load("tumftm", unit=unit, value_id=vid)["value"]
            if v.empty:
                continue
            lo, hi = sig.loc[vid, "min_val"], sig.loc[vid, "max_val"]
            bad = v[(v < lo) | (v > hi)]
            total += len(bad)
            if len(bad):
                top = bad.round(2).value_counts().head(3).to_dict()
                print(f"  {unit} {vid} {sig.loc[vid, 'variable_name']} [{lo}, {hi}]: {len(bad)} of {len(v)} rows; top {top}")
    print(f"  total rows outside the stated range: {total}")


if __name__ == "__main__":
    per = scan()
    summary(per)
    soc_extremes()
    out_of_range()
