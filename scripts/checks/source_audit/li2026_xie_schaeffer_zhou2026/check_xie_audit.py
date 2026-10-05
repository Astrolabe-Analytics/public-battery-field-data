"""Source-audit data checks for xie (swap-station device data, Zenodo 18328701, DataForPub.rar).

What it does: reads the label tables and all 271 device files through fielddata.loaders.xie (raw,
clean=False) and runs the checks listed in reports/source_audit_2026-10-04/xie.md:
  1  cell labels against device labels (which code means which fault class)
  4  row-to-row sampling intervals
  5  current sign (median cell voltage change against the sign of totalCurrent) and temperature range
  6  cell counts: per-device voltage columns against the cell table, and the authors' column rule
  7  repeated filenames in the device table and whether their labels differ
  8  the members of predefinedDataset/processedData/ in the archive.
What it reads: the released DataForPub.rar, only through the loader (needs the LIBARCHIVE environment
variable on Windows, pointing at the archive library DLL).
What it writes: <out_dir>/xie_audit_checks.txt (and prints the same text).
Run from the repository root:
  PYTHONPATH=. .venv/Scripts/python.exe <this file> <out_dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fielddata.loaders import xie as m

out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
out_dir.mkdir(parents=True, exist_ok=True)
lines: list[str] = []


def say(text=""):
    print(text)
    lines.append(str(text))


dev = m.device_labels()
cell = m.cell_labels()
units = m.systems()["unit"].tolist()
released = {u + ".csv" for u in units}
say(f"xie audit checks, raw data (clean=False). Device files: {len(units)}; device-table rows: {len(dev)}; "
    f"cell-table rows: {len(cell)}")

# 8. archive members
say("\n[8] Members under predefinedDataset/processedData/ and top level")
for name in m.members("predefinedDataset/processedData/"):
    say(f"  {name}")
say(f"  other members outside predefinedDataset/data/: "
    f"{[n for n in m.members('') if not n.startswith('predefinedDataset/')]}")

# 7. device table
say("\n[7] Device table")
vc = dev["filename"].value_counts()
say(f"  rows whose file is not released: {int((~dev['filename'].isin(released)).sum())}; "
    f"released files without a row: {len(released - set(dev['filename']))}")
say(f"  filenames with more than one row: {int((vc > 1).sum())} ({int(vc[vc > 1].sum() - (vc > 1).sum())} extra rows); "
    f"rows per repeated filename: {vc[vc > 1].value_counts().to_dict()}")
rep = dev[dev["filename"].isin(vc[vc > 1].index)]
same = rep.groupby("filename")["device_label"].nunique()
feat = rep.groupby("filename")[["corrMinMaxVoltages", "dtwDistance"]].nunique().max(axis=1)
say(f"  repeated filenames whose rows carry different labels: {int((same > 1).sum())}/{len(same)}; "
    f"whose feature values differ between rows: {int((feat > 1).sum())}")
say(f"  label sets of repeated filenames: "
    f"{rep.groupby('filename')['device_label'].apply(lambda s: ','.join(map(str, sorted(s)))).value_counts().to_dict()}")
say(f"  any repeated filename with label 5 among its rows: {bool((rep['device_label'] == 5).any())}")
devsets = dev.groupby("filename")["device_label"].apply(lambda s: frozenset(int(x) for x in s))
say(f"  distinct devices with label 5 only: {int((devsets == frozenset({5})).sum())}; devices with any fault code: "
    f"{int(devsets.apply(lambda s: bool(s - {5})).sum())}; devices per code (a device counts once per code): "
    f"{ {k: int(devsets.apply(lambda s, k=k: k in s).sum()) for k in (1, 2, 3, 4, 5)} }")

# 1. cell labels against device labels
say("\n[1] Cell labels against device labels")
cell["cell_label"] = cell["cell_label"].astype(int)
cell["cell_index"] = cell["cell_index"].astype(int)
cellsets = cell[cell["cell_label"] != 5].groupby("filename")["cell_label"].apply(lambda s: frozenset(s))
compare = pd.DataFrame({"device": devsets}).join(cellsets.rename("cells"))
compare["cells"] = compare["cells"].apply(lambda s: s if isinstance(s, frozenset) else frozenset({5}))
match = (compare["device"] == compare["cells"]).sum()
say(f"  devices whose set of device-table codes equals the set of non-5 cell codes (5 if none): {int(match)}/{len(compare)}")
for k in (1, 2, 3, 4):
    sub = compare[compare["device"].apply(lambda s, k=k: k in s)]
    say(f"  device code {k}: {len(sub)} devices; their fault-cell codes: "
        f"{pd.Series([c for s in sub['cells'] for c in s]).value_counts().sort_index().to_dict()}")
uniq = cell.drop_duplicates(["filename", "cell_index", "cell_label"])
say(f"  fault cells per code (unique filename, cell index, code): "
    f"{uniq[uniq['cell_label'] != 5]['cell_label'].value_counts().sort_index().to_dict()} (paper Table 1: MSC 26, "
    f"low capacity 31, high SOC 34, low SOC 18)")
dupcell = cell.duplicated(["filename", "cell_index"], keep=False)
say(f"  cell-table rows sharing a filename and cell index: {int(dupcell.sum())} rows; "
    f"distinct physical cells in the table: {cell[['filename', 'cell_index']].drop_duplicates().shape[0]}")
pairs = cell[dupcell].groupby(["filename", "cell_index"])["cell_label"].apply(lambda s: ','.join(map(str, sorted(s))))
say(f"  label pairs on those cells: {pairs.value_counts().to_dict()}")

# load all devices once
data = m.load(units)
vcols = [f"batCoreVoltage{i}" for i in range(1, 21)]
tcols = [c for c in data.columns if c.startswith("batCoreTemp") and c != "batCoreTempCount"]

# 6. cell counts
say("\n[6] Cell counts")
rows = []
ncell = cell[["filename", "cell_index"]].drop_duplicates().groupby("filename").size()
for u in units:
    f = data[data["unit"] == u]
    present = [c for c in vcols if c in f.columns and f[c].notna().any()]
    v = f[present]
    positive = int((v > 0).any().sum())
    # authors' rule (dataProcess.ipynb, get_device_voltages): consecutive columns from 1, then keep
    # columns whose sum is at least 1000 and whose standard deviation is above 0
    author = 0
    for c in vcols:
        if c not in present:
            break
        if v[c].sum() >= 1000 and v[c].std() > 0:
            author += 1
    rows.append({"unit": u, "positive": positive, "author": author, "table": int(ncell.get(u + ".csv", 0))})
cc = pd.DataFrame(rows)
say(f"  columns with any positive value: {int(cc['positive'].sum())}; authors' rule: {int(cc['author'].sum())}; "
    f"distinct cells in the cell table: {int(cc['table'].sum())} (paper Table 1: 5,234)")
diff = cc[cc["positive"] != cc["table"]]
say(f"  devices where positive-column count differs from the cell table: {len(diff)}")
for r in diff.itertuples():
    say(f"    {r.unit}: positive {r.positive}, authors' rule {r.author}, table {r.table}")
say(f"  devices where the authors' rule differs from the cell table: {int((cc['author'] != cc['table']).sum())}")
say(f"  cells per device (cell table): {cc['table'].value_counts().sort_index().to_dict()}")

# 4. sampling intervals
say("\n[4] Row-to-row intervals over all devices")
dts = []
for u in units:
    t = data[data["unit"] == u].index.to_series()
    dts.append(t.diff().dt.total_seconds().dropna())
dt = pd.concat(dts)
say(f"  intervals: {len(dt)}; median {dt.median() / 3600:.2f} h; share under 60 s {(dt < 60).mean():.1%}; "
    f"60 s to 2 h {((dt >= 60) & (dt <= 7200)).mean():.1%}; over 2 h {(dt > 7200).mean():.1%}")
say(f"  share 10 to 30 s {((dt >= 10) & (dt <= 30)).mean():.1%}; share 50 to 70 min "
    f"{((dt >= 3000) & (dt <= 4200)).mean():.1%}; zero intervals {(dt == 0).mean():.1%}")
bins = [0, 1, 10, 30, 60, 600, 3000, 4200, 7200, 6 * 3600, 12 * 3600, 24 * 3600, 7 * 86400, np.inf]
say("  histogram (s): " + pd.cut(dt, bins, right=False).value_counts().sort_index().to_string().replace("\n", "; "))
permed = pd.Series({u: d.median() for u, d in zip(units, dts)})
say(f"  median over devices of each device's median interval: {permed.median() / 3600:.2f} h")
span = data.reset_index().groupby("unit")["dateTime"].agg(["min", "max"])
say(f"  first and last timestamp over all devices (UTC as parsed): {span['min'].min()} to {span['max'].max()}")
say(f"  rows per device: min {data.groupby('unit').size().min()}, median {int(data.groupby('unit').size().median())}, "
    f"max {data.groupby('unit').size().max()}; total {len(data)}")

# 5. sign and temperature
say("\n[5] Current sign and temperature")
recs = []
for u in units:
    f = data[data["unit"] == u]
    med = f[[c for c in vcols if c in f.columns]].where(lambda x: x > 0).median(axis=1).to_numpy()
    t = f.index.asi8 / 1e9
    cur = f["totalCurrent"].to_numpy()
    for j in range(1, len(f)):
        # a step that starts at rest (|I| <= 0.1) and ends within 120 s: the voltage change is the response
        # to the current at the later row
        if t[j] - t[j - 1] <= 120 and abs(cur[j - 1]) <= 0.1:
            recs.append((cur[j], med[j] - med[j - 1], u))
st = pd.DataFrame(recs, columns=["i", "dv", "unit"])
say(f"  steps from a rest row (|totalCurrent| <= 0.1) to the next row within 120 s: {len(st)}")
for lo, hi in ((-np.inf, -50), (-50, -2), (-2, -0.1), (-0.1, 0.1), (0.1, 2), (2, 50), (50, np.inf)):
    g = st[(st["i"] > lo) & (st["i"] <= hi)]
    if len(g):
        say(f"  totalCurrent at the later row in ({lo}, {hi}]: {len(g)} steps on {g['unit'].nunique()} devices; "
            f"median cell voltage rose in {(g['dv'] > 0).mean():.1%}, fell in {(g['dv'] < 0).mean():.1%}; "
            f"median change {g['dv'].median():.1f} mV")
nz = data.loc[data["totalCurrent"] != 0, "totalCurrent"]
say(f"  nonzero totalCurrent: {len(nz)} values; quantiles 0.1 %, 1 %, 50 %, 99 %, 99.9 %: "
    f"{nz.quantile([.001, .01, .5, .99, .999]).round(2).tolist()}; |value| > 100: {int((nz.abs() > 100).sum())}")
say(f"  totalCurrent: min {data['totalCurrent'].min()}, max {data['totalCurrent'].max()}, share > 0 "
    f"{(data['totalCurrent'] > 0).mean():.1%}, share < 0 {(data['totalCurrent'] < 0).mean():.1%}, share 0 "
    f"{(data['totalCurrent'] == 0).mean():.1%}")
tv = data[tcols].stack()
say(f"  temperatures: min {tv.min()}, max {tv.max()}, outside -20 to 60: {int(((tv < -20) | (tv > 60)).sum())} of {len(tv)}")
say(f"  batCoreTempCount values: {data['batCoreTempCount'].value_counts().to_dict()}")
vv = data[[c for c in vcols if c in data.columns]].stack()
vp = vv[vv > 0]
say(f"  positive cell voltages: min {vp.min()}, max {vp.max()}; outside 2,500 to 3,630 mV: "
    f"{int(((vp < 2500) | (vp > 3630)).sum())} of {len(vp)}")

(out_dir / "xie_audit_checks.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
