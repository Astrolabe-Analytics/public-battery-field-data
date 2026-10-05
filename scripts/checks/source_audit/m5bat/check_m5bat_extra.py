"""Follow-up checks for the m5bat-2023-04 and m5bat-pbacid source audits, raw data.

What it does:
1. m5bat-2023-04 BESS: runs of rows with Grid_frequency == 0 (start, end, length), to compare with the report's
   p. 5 event "06:33:48 till 07:11:00 no frequency measurement" on 2023-04-03.
2. m5bat-pbacid: for every source and year, the number of index steps of exactly 2, 3, 4, 5, 6 and 7-10 s
   (a forward-fill of gaps shorter than 5 s would leave no steps of 2 to 4 s).
3. m5bat-pbacid counters: for every year, the five most common values of energy_charge_kWh_bsc and
   energy_discharge_kWh_bsc with their shares, the count of values >= 0xFFFF0000 (4,294,901,760; high register
   word 0xFFFF), and the same count for the BMS counters energy_charge_Wh_bms and energy_discharge_Wh_bms.
Reads: fielddata.load("m5bat-2023-04", unit="BESS"); fielddata.loaders.m5bat_pbacid.load(..., columns=[...]).
Writes: <out>/m5bat_2023_04_freq_zero.csv, <out>/m5bat_pbacid_step_hist.csv, <out>/m5bat_pbacid_counters.csv.
Usage: python check_m5bat_extra.py <out_dir>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import fielddata
from fielddata.loaders import m5bat_pbacid as m

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "reports")
HIGH = 0xFFFF0000


def freq_zero():
    f = fielddata.load("m5bat-2023-04", unit="BESS")["Grid_frequency"]
    zero = (f == 0).to_numpy()
    edges = np.diff(np.concatenate([[0], zero.astype(int), [0]]))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    rows = [{"start": f.index[s], "end": f.index[e - 1], "rows": e - s} for s, e in zip(starts, ends)]
    pd.DataFrame(rows).to_csv(OUT / "m5bat_2023_04_freq_zero.csv", index=False)
    print(rows, flush=True)


def steps():
    rows = []
    for source, column in (("bms", "soc_pct_bms"), ("bsc", "power_ac_kW_bsc")):
        for year in range(2017, 2026):
            idx = m.load(source, years=[year], columns=[column]).index.sort_values()
            step = np.diff(idx.tz_localize(None).values).astype("timedelta64[s]").astype(np.int64)
            row = {"source": source, "year": year, "rows": len(idx)}
            for k in (1, 2, 3, 4, 5, 6):
                row[f"step_{k}s"] = int((step == k).sum())
            row["step_7_10s"] = int(((step >= 7) & (step <= 10)).sum())
            row["step_gt_10s"] = int((step > 10).sum())
            rows.append(row)
            print(row, flush=True)
    pd.DataFrame(rows).to_csv(OUT / "m5bat_pbacid_step_hist.csv", index=False)


def counters():
    rows = []
    for source, columns in (("bsc", ["energy_charge_kWh_bsc", "energy_discharge_kWh_bsc"]),
                            ("bms", ["energy_charge_Wh_bms", "energy_discharge_Wh_bms"])):
        for year in range(2017, 2026):
            f = m.load(source, years=[year], columns=columns)
            for column in columns:
                s = f[column].dropna()
                counts = s.value_counts(normalize=True).head(5)
                rows.append({"source": source, "year": year, "column": column, "rows": len(s),
                             "n_ge_0xFFFF0000": int((s >= HIGH).sum()),
                             "share_ge_0xFFFF0000": float((s >= HIGH).mean()) if len(s) else np.nan,
                             "n_zero": int((s == 0).sum()),
                             "top5": "; ".join(f"{v:.0f} ({p:.4f})" for v, p in counts.items())})
                print(rows[-1], flush=True)
            del f
    pd.DataFrame(rows).to_csv(OUT / "m5bat_pbacid_counters.csv", index=False)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    freq_zero()
    steps()
    counters()
