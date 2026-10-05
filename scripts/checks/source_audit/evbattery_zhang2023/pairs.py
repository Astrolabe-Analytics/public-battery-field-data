"""Compare the shared fleet (zhang2023 battery_brand2 vs evbattery battery_dataset3) using the scan.py summaries
and the committed pair list reports/facts/_cache/zhang2023_evbattery_pairs.json. Also label codes and brand1 volt."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent
REPO = Path(Path(__file__).resolve().parents[3])
pairs = {int(k): v for k, v in json.loads((REPO / "reports/facts/_cache/zhang2023_evbattery_pairs.json").read_text())["pairs"].items()}
ov = json.loads((REPO / "reports/facts/_cache/zhang2023_evbattery_overlap.json").read_text())
print("pair list:", len(pairs), "unique evb partners", len(set(pairs.values())), "| overlap.json confirmed", ov["overlap_vehicles_confirmed"],
      "tolerance", len(ov["archive_pairs"]["battery_brand2.tar.gz = battery_dataset3.tar.gz"]["tolerance_matched"]))
z = pd.read_parquet(OUT / "snip_zhang2023__battery_brand2.tar.gz.parquet")
e = pd.read_parquet(OUT / "snip_evbattery__battery_dataset3.tar.gz.parquet")
zi = pd.read_csv(REPO / "fielddata/loaders/zhang2023_index.csv"); zi = zi[zi.archive == "battery_brand2.tar.gz"].set_index("car")
ei = pd.read_csv(REPO / "fielddata/loaders/evbattery_index.csv"); ei = ei[ei.archive == "battery_dataset3.tar.gz"].set_index("car")
print("zhang brand2 cars with data", int((zi.snippets > 0).sum()), "all in pair list:", set(zi[zi.snippets > 0].index) == set(pairs))
print("evb ds3 cars with data", int((ei.snippets > 0).sum()), "all partners:", set(ei[ei.snippets > 0].index) == set(pairs.values()))
rows = []
for zc, ec in pairs.items():
    zs, es = z[z.car == zc], e[e.car == ec]
    zseg, eseg = set(zs.charge_segment), set(es.charge_segment)
    rows.append(dict(z=zc, e=ec, z_snip=len(zs), e_snip=len(es), z_seg=len(zseg), e_seg=len(eseg), seg_both=len(zseg & eseg),
                     seg_only_z=len(zseg - eseg), seg_only_e=len(eseg - zseg), z_label=zi.label[zc], e_label=ei.label[ec],
                     z_mil_max=zs.mileage.max(), e_mil_max=es.mileage.max()))
p = pd.DataFrame(rows)
print("snippets: zhang", p.z_snip.sum(), "evb", p.e_snip.sum(), "| pairs with evb > zhang:", int((p.e_snip > p.z_snip).sum()),
      "| pairs with equal:", int((p.e_snip == p.z_snip).sum()))
print("charge segments: zhang", p.z_seg.sum(), "evb", p.e_seg.sum(), "shared", p.seg_both.sum(), "only zhang", p.seg_only_z.sum(), "only evb", p.seg_only_e.sum())
print("labels agree:", int((p.z_label == p.e_label).sum()), "of", len(p), "| label-1 pairs", int((p.z_label == 1).sum()))
print("ratio evb/zhang snippets per pair 0/10/50/90/100%:", p.eval("e_snip/z_snip").quantile([0, .1, .5, .9, 1]).round(3).tolist())
p.to_csv(OUT / "pairs_counts.csv", index=False)

# snippet-level join within a pair: same charge segment and same start/end SOC
z2 = z.assign(pe=z.car.map(pairs), k0=z.soc0.round(1), k1=z.soc1.round(1))
e2 = e.assign(k0=e.soc0.round(1), k1=e.soc1.round(1))
j = z2.merge(e2, left_on=["pe", "charge_segment", "k0", "k1"], right_on=["car", "charge_segment", "k0", "k1"], suffixes=("_z", "_e"))
j = j.drop_duplicates(subset=["member_z"]).drop_duplicates(subset=["member_e"])
print(f"snippets joined on (pair, charge_segment, start SOC, end SOC): {len(j):,} (zhang {len(z):,}, evb {len(e):,})")
r = (j.q_abs_ah_e / j.q_abs_ah_z).replace([np.inf, -np.inf], np.nan).dropna()
print("charge ratio evb/zhang per joined snippet 1/50/99%:", r.quantile([.01, .5, .99]).round(4).tolist())
print("mileage ratio evb/zhang 1/50/99%:", (j.mileage_e / j.mileage_z).replace([np.inf, -np.inf], np.nan).dropna().quantile([.01, .5, .99]).round(3).tolist())
print("tmax diff evb-zhang 1/50/99%:", (j.tmax_max_e - j.tmax_max_z).quantile([.01, .5, .99]).tolist(),
      "| cell mean diff:", (j.cell_mean_e - j.cell_mean_z).quantile([.01, .5, .99]).round(4).tolist())
print("evb volt minus evb cell mean 1/50/99%:", (j.v_mean_e - j.cell_mean_e).quantile([.01, .5, .99]).round(4).tolist())
fits = []
for (zc), g in j.groupby("car_z"):
    if len(g) > 20:
        sl, ic = np.polyfit(g.v_mean_e, g.v_mean_z, 1)
        res = g.v_mean_z - (sl * g.v_mean_e + ic)
        fits.append(dict(car=zc, n=len(g), slope=sl, intercept=ic, resid_sd=res.std()))
f = pd.DataFrame(fits)
print(f"per-vehicle fit zhang volt = a * evb volt + b over {len(f)} vehicles: slope 0/50/100%", f.slope.quantile([0, .5, 1]).round(4).tolist(),
      "intercept", f.intercept.quantile([0, .5, 1]).round(4).tolist(), "resid sd median", round(f.resid_sd.median(), 5))
sl, ic = np.polyfit(j.v_mean_e, j.v_mean_z, 1)
res = j.v_mean_z - (sl * j.v_mean_e + ic)
print(f"one fit over all joined snippets: slope {sl:.4f} intercept {ic:.4f} resid sd {res.std():.5f} | 99% abs resid {res.abs().quantile(.99):.4f}")
f.to_csv(OUT / "pairs_voltfit.csv", index=False)

# zero-current snippets in the shared fleet
for name, d in (("zhang brand2", z), ("evb ds3", e)):
    zero = d[(d.i_neg == 0) & (d.i_pos == 0)]
    print(f"{name}: snippets with current all zero {len(zero):,} of {len(d):,}; of those SOC rises in {int((zero.soc1 > zero.soc0).sum()):,};"
          f" vehicles affected {zero.car.nunique()}")

# label codes
for f_ in sorted(OUT.glob("snip_*.parquet")):
    d = pd.read_parquet(f_)
    pkg, arch = f_.stem.removeprefix("snip_").split("__")
    idx = pd.read_csv(REPO / f"fielddata/loaders/{pkg}_index.csv"); idx = idx[idx.archive == arch].set_index("car")
    codes = d.groupby("car")["label"].agg(lambda s: tuple(sorted(set(s))))
    tab = pd.crosstab(codes.astype(str), idx.label.reindex(codes.index))
    print(pkg, arch, "metadata label codes (numeric-coerced) vs label-table label:\n", tab.to_string())
