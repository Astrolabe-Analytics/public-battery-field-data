"""pack_temp_0 values of 87.0/87.5 C and SOC 101.6 in bilfinger2026 VW_ID3_FTM_8A_CEE7_Balancing (loader, raw): runs, dates, other module temps. Writes nothing."""
import numpy as np, pandas as pd
from fielddata.loaders import bilfinger2026 as B
d = B.load("VW_ID3_FTM_8A_CEE7_Balancing")
m = d.pack_temp_0 >= 87
runs = (m != m.shift()).cumsum()[m]
print("rows", m.sum(), "runs", runs.nunique(), "first", d.date[m].min(), "last", d.date[m].max())
others = [c for c in d.columns if c.startswith("pack_temp") and c != "pack_temp_0"]
print("other module temps on those rows: max", d.loc[m, others].max().max(), "median", np.nanmedian(d.loc[m, others].values))
print("pack_temp_0 on other rows: range", d.pack_temp_0[~m].min(), d.pack_temp_0[~m].max())
k = np.where(m)[0][0]; print(d.pack_temp_0.iloc[k-3:k+4].tolist(), d.pack_temp_1.iloc[k-3:k+4].tolist())
s = d.SOC == 101.6
print("SOC 101.6 rows", s.sum(), "with U code", (s & (d.U == 1023.5)).sum(), "SOC around:", d.SOC.iloc[np.where(s)[0][0]-2:np.where(s)[0][0]+3].tolist())
