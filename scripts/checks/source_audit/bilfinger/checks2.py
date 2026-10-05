"""Follow-up audit checks for bilfinger2024/2026 through the loaders (raw data, clean=False).

1. Duplicates across releases: VW_ID3_JB_8A_C40_2024 (2024) vs VW_ID3_FTM_JB_8A_CEE7_preRelax (2026);
   Tesla_JB_8A_CEE7_C57_2022 (2024) vs Tesla_JB_6A_CEE7_C57_2022_w_cv (2026).
2. Full-range charged energy of each 2024 vehicle file (paper 2024 Sec. 4.4/4.5: 60.6, 55.0, 59.40 kWh VW; 57.0, 55.1 kWh Tesla).
3. date column against the Unix `time` column (time zone).
4. Discharge file: NaN rows, sign, energy between 370 and 450 V.
5. Balancing file: values of U and I outside physical range.
6. Tesla cell voltage: spacing of the points where the slope changes (knots).
7. VW 2021 vehicle file vs its raw log.
"""
import numpy as np
import pandas as pd

from fielddata.loaders import bilfinger2024 as A, bilfinger2026 as B


def ctz(y, x):
    y = np.asarray(y, float); x = np.asarray(x, float)
    return np.concatenate([[0.0], np.cumsum((y[1:] + y[:-1]) / 2 * np.diff(x))])


print("## 1 duplicates")
for ua, ub in [("VW_ID3_JB_8A_C40_2024", "VW_ID3_FTM_JB_8A_CEE7_preRelax"), ("Tesla_JB_8A_CEE7_C57_2022", "Tesla_JB_6A_CEE7_C57_2022_w_cv")]:
    a, b = A.load(ua), B.load(ub)
    common = [c for c in a.columns if c in b.columns]
    only_a = [c for c in a.columns if c not in b.columns]; only_b = [c for c in b.columns if c not in a.columns]
    same = all(np.array_equal(a[c].values, b[c].values, equal_nan=True) for c in common) and len(a) == len(b)
    print(ua, "vs", ub, "rows", len(a), len(b), "common cols", len(common), "identical on common cols:", same, "only in 2024:", only_a, "only in 2026:", only_b)

print("\n## 2 full-range energy (kWh) and charge (Ah), integral of U*I and I over the whole file")
for u in ["VW_ID3_JB_8A_C40_2021", "VW_ID3_JB_8A_C40_2023", "VW_ID3_JB_8A_C40_2024", "Tesla_JB_8A_CEE7_C57_2021", "Tesla_JB_8A_CEE7_C57_2022"]:
    d = A.load(u)
    E = ctz(d["U"] * d["I"] / 1000, d["time_h"])[-1]
    print(u, "E_full=%.2f kWh" % E, "Q_end=%.2f Ah" % d["Q"].iloc[-1], "U %.2f-%.2f V" % (d["U"].min(), d["U"].max()), "SOC %.1f-%.1f" % (d["SOC"].min(), d["SOC"].max()), "hours %.1f" % d["time_h"].iloc[-1])
for u in ["VW_ID3_FTM_8A_CEE7_RelaxHighSOC", "VW_ID3_FTM_8A_CEE7_RelaxLowSOC"]:
    d = B.load(u)
    E = ctz(d["U"] * d["I"] / 1000, d["time_h"])[-1]
    print(u, "E_full=%.2f kWh" % E, "date", d["date"].min(), d["date"].max())

print("\n## 3 date vs unix time")
for mod, u in [(A, "VW_ID3_JB_8A_C40_2023")]:
    d = mod.load(u)
    diff = (d["date"] - pd.to_datetime(d["time"], unit="s")).dt.total_seconds()
    print(u, "date - to_datetime(time, unit=s) [s]: min %.6f max %.6f" % (diff.min(), diff.max()))
for u in ["VW_FTM_JB_8A_2024"]:
    raw = A.load(u); veh = A.load("VW_ID3_JB_8A_C40_2024")
    t0 = pd.to_datetime(raw["time"], unit="s")
    print(u, "raw unix range as UTC", t0.min(), t0.max(), "| vehicle date range", veh["date"].min(), veh["date"].max())
d = A.load("VW_ID3_JB_8A_C40_2021")
print("VW_ID3_JB_8A_C40_2021 columns time (int) first/last", d["time"].iloc[0], d["time"].iloc[-1], "date first", d["date"].iloc[0])

print("\n## 4 discharge file")
d = B.load("Cupra_288_C10_discharge")
print("rows", len(d), "NaN per column:", {c: int(d[c].isna().sum()) for c in ["I", "U", "SOC", "Q", "time_h"]})
dd = d.dropna(subset=["I", "U"])
print("I range", dd["I"].min(), dd["I"].max(), "U first/last", dd["U"].iloc[0], dd["U"].iloc[-1], "SOC first/last", dd["SOC"].iloc[0], dd["SOC"].iloc[-1])
print("Q first/last/min", d["Q"].iloc[0], d["Q"].iloc[-1], d["Q"].min())
E = ctz(dd["U"] * dd["I"] / 1000, dd["time_h"])
sel = ((dd["U"] >= 370) & (dd["U"] <= 450)).values
e = E[sel]; q = dd["Q"].values[sel]
print("discharged energy between 370 and 450 V: %.2f kWh, charge %.2f Ah (paper Table 2(c) dch: 54.8 kWh, 135.5 Ah; Q column is NaN after row 0)" % (np.max(np.abs(e - e[0])), np.nanmax(np.abs(q - q[0]))))
print("mean |power| above 5 pct SOC (kW): %.2f" % (np.abs(dd["U"] * dd["I"])[dd["SOC"] > 5].mean() / 1000))

print("\n## 5 Balancing file out-of-range values")
d = B.load("VW_ID3_FTM_8A_CEE7_Balancing")
U, I = d["U"], d["I"]
print("rows", len(d), "U>500:", int((U > 500).sum()), "U<300:", int((U < 300).sum()), "U value counts above 500:", U[U > 500].value_counts().head(5).to_dict())
print("|I|>500:", int((I.abs() > 500).sum()), "I>500 values:", I[I > 500].value_counts().head(5).to_dict(), "I<-100:", int((I < -100).sum()), I[I < -100].describe().to_dict())
bad = (U > 500) | (I.abs() > 500)
print("rows with U>500 or |I|>500:", int(bad.sum()), "dates of first/last:", d.loc[bad, "date"].min(), d.loc[bad, "date"].max())
print("same rows? U>500 & |I|>500:", int(((U > 500) & (I.abs() > 500)).sum()))
print("I percentiles", I.quantile([0.001, 0.01, 0.5, 0.99, 0.999]).to_dict())
print("SOC range", d["SOC"].min(), d["SOC"].max(), "SOC>100:", int((d["SOC"] > 100).sum()))
cv = [c for c in d.columns if c.startswith("cell_voltage")]
cvv = d[cv]
print("cell voltage range", np.nanmin(cvv.values), np.nanmax(cvv.values), "cells >5 V:", int((cvv > 5).sum().sum()), "values >5 V:", pd.Series(cvv.values.ravel()).loc[lambda s: s > 5].value_counts().head(5).to_dict())
pt = [c for c in d.columns if c.startswith("pack_temp") or c == "ambient_air_temp"]
print("temperature range", np.nanmin(d[pt].values), np.nanmax(d[pt].values))
# other vehicle files: any U>500, |I|>500, cell voltage > 5 V
for mod, rel in [(A, "2024"), (B, "2026")]:
    for r in mod.systems().itertuples():
        if r.kind != "vehicle":
            continue
        x = mod.load(r.unit)
        cv = x[[c for c in x.columns if c.startswith("cell_voltage")]]
        print(rel, r.unit, "U>500:", int((x["U"] > 500).sum()), "|I|>500:", int((x["I"].abs() > 500).sum()), "cellV>5:", int((cv > 5).sum().sum()), "cellV<2:", int((cv < 2).sum().sum()), "cellV range %.3f-%.3f" % (np.nanmin(cv.values), np.nanmax(cv.values)))

print("\n## 6 Tesla cell voltage knots")
d = B.load("Tesla_JB_6A_CEE7_C57_2022_w_cv")
t = d["time_s"].values; y = d["cell_voltage_0"].values
s = np.diff(y) / np.diff(t)
knot = np.where(~np.isclose(np.diff(s), 0, atol=1e-9))[0] + 1
gaps = np.diff(t[knot])
print("rows", len(d), "slope changes", len(knot), "knot spacing s: median", np.median(gaps), "p10", np.percentile(gaps, 10), "p90", np.percentile(gaps, 90))
print("distinct cell_voltage_0 decimals sample", y[:8])
for c in ["U", "I", "SOC"]:
    yy = d[c].values; ss = np.diff(yy) / np.diff(t); k = np.where(~np.isclose(np.diff(ss), 0, atol=1e-9))[0]
    print(c, "share of rows with slope change", len(k) / len(d))

print("\n## 7 VW 2021 vehicle vs raw log")
v = A.load("VW_ID3_JB_8A_C40_2021"); r = A.load("VW_FTM_JB_8A_2021")
m = v.merge(r, left_on="time", right_on="TIMESTAMP", how="left")
print("rows", len(v), len(r), "matched", int(m["hv_battery_voltage"].notna().sum()),
      "max |U - hv_battery_voltage|", float((m["U"] - m["hv_battery_voltage"]).abs().max()),
      "max |I - hv_battery_current|", float((m["I"] - m["hv_battery_current"]).abs().max()),
      "max |SOC - hv_soc|", float((m["SOC"] - m["hv_soc"]).abs().max()))
print("raw 2021 columns", [c for c in r.columns if not c.startswith("cell_voltage")])
print("raw 2021 I min (before start of vehicle file)", r["hv_battery_current"].min(), "vehicle I min", v["I"].min())
