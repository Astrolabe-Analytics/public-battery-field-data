"""Looks for the unflagged forward-fill of gaps shorter than 5 s (paper Sec. 3.2.1) in m5bat-pbacid, raw data.

What it does: for one FCR-phase year (2019) and one reserve-phase year (2023) of each source, it takes the
measured channels (BMS: power_dc_W_bms, current_A_bms, voltage_bat_V_bms, soc_pct_bms; BSC: power_ac_kW_bsc,
current_A_bsc, voltage_bat_V_bsc, frequency_Hz_bsc), keeps rows 1 s after the previous row, and marks a row a
"repeat" when every one of these channels equals the previous row exactly. It counts runs of consecutive
repeats by length (1 to 10, and over 10), over all rows and over rows with |current| > 10 A at both rows
(active operation, where values normally change every second). A forward-filled gap of k missing seconds
shows as a run of k repeats; an excess of runs of length 1 to 4 against length 5 and over, during active
operation, is the signature of the fill.
Reads: fielddata.loaders.m5bat_pbacid.load(source, years=[year], columns=[...]).
Writes: <out>/m5bat_pbacid_repeats.csv.
Usage: python check_m5bat_pbacid_repeats.py <out_dir>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fielddata.loaders import m5bat_pbacid as m

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "reports")
CHANNELS = {"bms": (["power_dc_W_bms", "current_A_bms", "voltage_bat_V_bms", "soc_pct_bms"], "current_A_bms"),
            "bsc": (["power_ac_kW_bsc", "current_A_bsc", "voltage_bat_V_bsc", "frequency_Hz_bsc"], "current_A_bsc")}


def run_lengths(flag):
    edges = np.diff(np.concatenate([[0], flag.astype(np.int8), [0]]))
    return np.flatnonzero(edges == -1) - np.flatnonzero(edges == 1)


def main():
    rows = []
    for source, (columns, current) in CHANNELS.items():
        for year in (2019, 2023):
            f = m.load(source, years=[year], columns=columns).sort_index(kind="stable")
            values = f[columns].to_numpy()
            step1 = np.concatenate([[False], np.diff(f.index.asi8) == 1_000_000_000])
            same = np.concatenate([[False], np.all(values[1:] == values[:-1], axis=1)]) & step1
            active_now = np.abs(f[current].to_numpy()) > 10
            active = active_now & np.concatenate([[False], active_now[:-1]])
            for label, mask in (("all rows", np.ones(len(f), bool)), ("|I| > 10 A", active)):
                lengths = run_lengths(same & mask)
                pairs = int((step1 & mask).sum())
                row = {"source": source, "year": year, "subset": label, "rows": len(f),
                       "consecutive_1s_pairs": pairs, "repeat_rows": int((same & mask).sum()),
                       "repeat_share": (same & mask).sum() / pairs if pairs else np.nan}
                for k in range(1, 11):
                    row[f"runs_len_{k}"] = int((lengths == k).sum())
                row["runs_len_gt10"] = int((lengths > 10).sum())
                rows.append(row)
                print(row, flush=True)
            del f, values
    pd.DataFrame(rows).to_csv(OUT / "m5bat_pbacid_repeats.csv", index=False)


if __name__ == "__main__":
    main()
