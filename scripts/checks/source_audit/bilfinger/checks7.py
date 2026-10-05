"""Dates and spread of the out-of-range values (SOC 101.6, cell 5.094 V, pack_temp_0 >= 87, U 1023.5, I 166272.14) across all bilfinger vehicle files (loader, raw). Writes nothing."""
import numpy as np, pandas as pd
from fielddata.loaders import bilfinger2024 as A, bilfinger2026 as B
for mod, rel in [(A, "2024"), (B, "2026")]:
    for r in mod.systems().itertuples():
        if r.kind != "vehicle": continue
        d = mod.load(r.unit)
        cv = d[[c for c in d.columns if c.startswith("cell_voltage")]]
        pt = [c for c in d.columns if c.startswith("pack_temp_") and c[-1].isdigit()]
        hits = {"SOC>100": int((d.SOC > 100).sum()), "cell==5.094": int((cv == 5.094).sum().sum()), "temp>=60": int((d[pt] >= 60).sum().sum()) if pt else 0,
                "U==1023.5": int((d.U == 1023.5).sum()), "I==166272.14": int((d.I == 166272.14).sum())}
        if any(hits.values()):
            print(rel, r.unit, hits)
            if "date" in d:
                for k, m in [("SOC", d.SOC > 100), ("cell", (cv == 5.094).any(axis=1))]:
                    print("  ", k, d.date[m].min(), d.date[m].max())
d = B.load("VW_ID3_FTM_8A_CEE7_Balancing")
for name, m in [("U", d.U == 1023.5), ("I", d.I == 166272.14)]:
    runs = (m != m.shift()).cumsum()[m]
    print(name, "rows", int(m.sum()), "runs", runs.nunique(), "longest run", runs.value_counts().max())
c = clean = B.load("VW_ID3_FTM_8A_CEE7_Balancing", clean=True)
print("clean masked", clean.attrs["masked_value_count"], "U max after clean", clean.U.max(), "I max", clean.I.max())
