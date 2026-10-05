"""Co-occurrence of out-of-range codes in bilfinger2026 VW_ID3_FTM_8A_CEE7_Balancing (loader, raw).
Prints, for U == 1023.5, I == 166272.14, cell_voltage == 5.094, SOC > 100, temperatures >= 60 C: counts, rows, overlaps,
and the neighbouring values, to decide whether they are codes or measurements. Writes nothing."""
import numpy as np, pandas as pd
from fielddata.loaders import bilfinger2026 as B
d = B.load("VW_ID3_FTM_8A_CEE7_Balancing")
cv = [c for c in d.columns if c.startswith("cell_voltage")]
pt = [c for c in d.columns if c.startswith("pack_temp")] + ["ambient_air_temp"]
u = d.U == 1023.5; i = d.I == 166272.14
c = (d[cv] == 5.094); crow = c.any(axis=1)
print("U code rows", u.sum(), "I code rows", i.sum(), "cell code rows", crow.sum(), "cells per code row", c.sum(axis=1)[crow].value_counts().head().to_dict())
print("overlap U&cell", (u & crow).sum(), "I&cell", (i & crow).sum(), "U&I", (u & i).sum())
print("columns with 5.094:", c.sum()[c.sum() > 0].sort_values(ascending=False).head(10).to_dict())
print("SOC>100 values", d.SOC[d.SOC > 100].value_counts().to_dict())
print("temps >= 60:", {k: d[k][d[k] >= 60].value_counts().to_dict() for k in pt if (d[k] >= 60).any()})
print("temp max per column", d[pt].max().sort_values().tail(5).to_dict())
for name, m in [("U", u), ("I", i)]:
    idx = np.where(m)[0][:3]
    for k in idx:
        print(name, "row", k, d.iloc[max(0, k - 2):k + 3][["date", "U", "I", "SOC"]].to_string(header=False).replace("\n", " | "))
# neighbouring values of a 5.094 cell
col = c.sum().idxmax(); k = np.where(c[col])[0][0]
print(col, d[col].iloc[max(0, k - 3):k + 4].tolist())
# large negative currents
neg = d.I < -100
print("I<-100 rows", neg.sum(), "U on those rows", d.U[neg].describe()[["min", "50%", "max"]].to_dict(), "dates", d.date[neg].min(), d.date[neg].max())
k = np.where(neg)[0][0]; print(d.iloc[k - 3:k + 4][["date", "U", "I", "SOC"]].to_string())
# discharge file: is Q NaN beyond row 0 in the 2026 discharge only?
for r in B.systems().itertuples():
    if r.kind == "vehicle":
        x = B.load(r.unit); n = int(x.Q.isna().sum())
        if n: print("Q NaN:", r.unit, n, "of", len(x))
