"""rwth-home source-audit data checks (2026-10-04).

What it does, through the loader only (raw data, clean=False):
  1. counts every .csv member of the 21 Data_ID_XX.zip archives (`rwth_home.members`) and lists any whose
     name does not match YYYY_MM_System_ID_NN.csv or whose ID differs from the archive's; lists months
     missing between each system's first and last monthly file;
  2. daylight-saving test: for every system with the months 2018-03 and 2018-10 (`rwth_home.load(unit,
     month=...)`), counts rows stamped 02:00-02:59 on 2018-03-25 (absent if local time with DST) and
     duplicated timestamps on 2018-10-28 (an hour repeated if local time with DST), with the rows on the
     neighbouring hours for comparison;
  3. current sign, as a cross-check of SI Note 4: in those months, mean I_in_A at 10:00-13:00 vs 20:00-23:00.
Reads: the released rwth-home archives through fielddata.loaders.rwth_home.
Writes into <out_dir>: rh_members.csv, rh_dst.csv (incremental), rh_summary.txt.
Run from the repo root: PYTHONPATH=. .venv/Scripts/python.exe <this file> <out_dir>
"""
import sys
from pathlib import Path

import pandas as pd

from fielddata.loaders import rwth_home as r

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
lines = []

rows = []
for u in r._units():
    names = [n for n in r.members(u) if n.lower().endswith(".csv")]
    good = [n for n in names if (m := r._MONTH.search(n)) and m.group(3) == u]
    have = pd.PeriodIndex([pd.Period(m, "M") for m, _ in r.months(u)])
    full = pd.period_range(have.min(), have.max(), freq="M")
    missing = [str(p) for p in full if p not in set(have)]
    rows.append({"unit": u, "csv_members": len(names), "matching": len(good),
                 "not_matching": ";".join(sorted(set(names) - set(good))), "first": str(have.min()), "last": str(have.max()),
                 "months_missing_inside_range": ";".join(missing)})
mem = pd.DataFrame(rows)
mem.to_csv(out / "rh_members.csv", index=False)
lines.append(f"csv members in all archives: {mem['csv_members'].sum()}, matching the monthly pattern and archive ID: {mem['matching'].sum()}")
lines.append("non-matching: " + (", ".join(x for x in mem["not_matching"] if x) or "none"))
lines.append("months missing inside a system's first-to-last range: " + "; ".join(f"{a}: {b}" for a, b in zip(mem["unit"], mem["months_missing_inside_range"]) if b))

dst_csv = out / "rh_dst.csv"
done = set(pd.read_csv(dst_csv, dtype={"unit": str})["unit"]) if dst_csv.exists() else set()
for u in r._units():
    if u in done:
        continue
    have = dict(r.months(u))
    if "2018-03" not in have or "2018-10" not in have:
        continue
    row = {"unit": u}
    mar = r.load(u, month="2018-03")
    day = mar.loc["2018-03-25"]
    for h in (1, 2, 3):
        row[f"mar25_rows_h{h:02d}"] = int((day.index.hour == h).sum())
    row["mar25_interp_h01_03"] = int(day.loc[(day.index.hour >= 1) & (day.index.hour <= 3), "Interpolated"].sum())
    noon = mar.between_time("10:00", "13:00")["I_in_A"].mean()
    eve = mar.between_time("20:00", "23:00")["I_in_A"].mean()
    del mar
    octo = r.load(u, month="2018-10")
    day = octo.loc["2018-10-28"]
    for h in (1, 2, 3):
        row[f"oct28_rows_h{h:02d}"] = int((day.index.hour == h).sum())
    row["oct28_duplicated_ts"] = int(day.index.duplicated().sum())
    row["oct_month_duplicated_ts"] = int(octo.index.duplicated().sum())
    row["mar_I_mean_10_13"] = float(noon)
    row["mar_I_mean_20_23"] = float(eve)
    row["oct_I_mean_10_13"] = float(octo.between_time("10:00", "13:00")["I_in_A"].mean())
    row["oct_I_mean_20_23"] = float(octo.between_time("20:00", "23:00")["I_in_A"].mean())
    del octo
    pd.DataFrame([row]).to_csv(dst_csv, mode="a", header=not dst_csv.exists(), index=False)
    print(u, row, flush=True)

dst = pd.read_csv(dst_csv, dtype={"unit": str})
lines.append(f"DST test on {len(dst)} systems with both 2018-03 and 2018-10:")
lines.append(dst.to_string(index=False))
(out / "rh_summary.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
