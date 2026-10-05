"""Summarise the per-snippet parquet files written by scan.py (evbattery and zhang2023 audit checks)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent
REPO = Path(Path(__file__).resolve().parents[3])
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)


def q(s, ps=(0.01, 0.5, 0.99)):
    s = pd.Series(s).dropna()
    return " / ".join(f"{s.quantile(p):.4g}" for p in ps) if len(s) else "n/a"


for f in sorted(OUT.glob("snip_*.parquet")):
    pkg, arch = f.stem.removeprefix("snip_").split("__")
    df = pd.read_parquet(f)
    a = json.loads((OUT / f"arch_{pkg}__{arch}.json").read_text())
    idx = pd.read_csv(REPO / f"fielddata/loaders/{pkg}_index.csv")
    idx = idx[idx["archive"] == arch]
    print(f"\n===== {pkg} {arch}: snippets {len(df):,}, vehicles {df.car.nunique()}, rows {a['rows']:,}")
    # index check
    counts = df.groupby("car").size()
    ix = idx.set_index("car")
    mism = [(c, counts.get(c, 0), n) for c, n in ix["snippets"].items() if counts.get(c, 0) != n]
    print("index: vehicles", len(ix), "snippets", int(ix["snippets"].sum()), "label1 vehicles (index)", int((ix["label"] == 1).sum()),
          "label1 with snippets", int(((ix["label"] == 1) & (ix["snippets"] > 0)).sum()), "count mismatches", mism[:5])
    lab = df.groupby("car")["label"].agg(["min", "max"])
    print("label from metadata: vehicles with label 1:", int((lab["max"] == 1).sum()), "mixed labels within vehicle:", int((lab["min"] != lab["max"]).sum()))
    mlab = ix["label"].reindex(lab.index)
    print("metadata label == index label for all vehicles:", bool((mlab == lab["max"]).all()))
    print("current rows <0 / >0 / ==0:", a["current_neg"], a["current_pos"], a["current_zero"], f"neg share {a['current_neg']/a['rows']:.6f}")
    print("snippets with all current<0:", int((df.i_neg == 128).sum()), "with any current>0:", int((df.i_pos > 0).sum()))
    print("dt top:", a["dt_top"][:8], "total", a["dt_total"])
    print("per-snippet median dt quantiles 1/50/99%:", q(df.dt_med), "| dt_min min", df.dt_min.min(), "dt_max max", df.dt_max.max())
    print("snippet duration (ts1-ts0) 1/50/99%:", q(df.ts1 - df.ts0), "| ts0 1/50/99%:", q(df.ts0))
    print("snippets with ts0 == 0:", int((df.ts0 == 0).sum()))
    print("soc col2 range 1/50/99%:", q(df.soc_min), q(df.soc_max), "| min", df.soc_min.min(), "max", df.soc_max.max(),
          "| soc1>=soc0 share", f"{(df.soc1 >= df.soc0).mean():.4f}", "soc1>soc0 share", f"{(df.soc1 > df.soc0).mean():.4f}")
    print("temp max col5 1/50/99%:", q(df.tmax_max), "temp min col6:", q(df.tmin_min), "| abs min/max", df.tmin_min.min(), df.tmax_max.max())
    print("volt col0 mean 1/50/99%:", q(df.v_mean), "| min", df.v_min.min(), "max", df.v_max.max())
    print("cell mean (max+min)/2 1/50/99%:", q(df.cell_mean), "| max_single max", df.vmax_max.max(), "min_single min", df.vmin_min.min())
    print("volt minus cell mean (snippet means) 1/50/99%:", q(df.v_mean - df.cell_mean), "| ratio volt/cell", q(df.v_mean / df.cell_mean))
    print("mileage 1/50/99%:", q(df.mileage), "| min", df.mileage.min(), "max", df.mileage.max())
    print("capacity values:", a["capacity_values"], "| meta keys", a["meta_keys"])
    if df.capacity.notna().any():
        c = df.capacity[df.capacity > 0]
        print("capacity>0 count", len(c), "range", c.min(), c.max(), "| distinct zero-count", int((df.capacity == 0).sum()), "nan", int(df.capacity.isna().sum()))
        print("vehicles with any capacity>0:", int(df[df.capacity > 0].car.nunique()))
    # coulomb counting
    dsoc = df.soc1 - df.soc0
    sel = dsoc >= 5
    impl = df.q_abs_ah[sel] / (dsoc[sel] / 100)
    print(f"implied capacity |I|dt/dSOC (dSOC>=5%, n={int(sel.sum())}) Ah 1/10/50/90/99%:", q(impl, (0.01, 0.1, 0.5, 0.9, 0.99)))
    if df.capacity.notna().any():
        s2 = sel & (df.capacity > 0)
        r = df.q_abs_ah[s2] / (dsoc[s2] / 100) / df.capacity[s2]
        print(f"ratio implied/label (n={int(s2.sum())}) 1/10/25/50/75/90/99%:", q(r, (0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99)))
        pv = (df[s2].assign(r=r)).groupby("car")["r"].median()
        print(f"per-vehicle median ratio over {len(pv)} vehicles 1/10/50/90/99%:", q(pv, (0.01, 0.1, 0.5, 0.9, 0.99)))
    pv_impl = df[sel].assign(impl=impl).groupby("car")["impl"].median()
    print(f"per-vehicle median implied capacity ({len(pv_impl)} vehicles) min/10/50/90/max:", q(pv_impl, (0, 0.1, 0.5, 0.9, 1)))
    # volt vs cell regression per vehicle, at snippet-mean level and within-snippet slope
    out = []
    for car, g in df.groupby("car"):
        if len(g) >= 5 and g.cell_mean.std() > 0:
            sl, ic = np.polyfit(g.cell_mean, g.v_mean, 1)
            r2 = np.corrcoef(g.cell_mean, g.v_mean)[0, 1] ** 2
            out.append(dict(car=car, slope=sl, intercept=ic, r2=r2, n=len(g), snip_slope_med=g.v_cell_slope.median(),
                            snip_slope_iqr=g.v_cell_slope.quantile(0.75) - g.v_cell_slope.quantile(0.25), snip_r_med=g.v_cell_r.median()))
    o = pd.DataFrame(out)
    print("per-vehicle fit volt ~ cell (snippet means): slope 1/50/99%", q(o.slope), "| intercept", q(o.intercept), "| r2", q(o.r2))
    print("within-snippet slope: per-vehicle median 1/50/99%", q(o.snip_slope_med), "| per-vehicle IQR 50%", q(o.snip_slope_iqr), "| within-snippet r median", q(o.snip_r_med))
    o.to_csv(OUT / f"voltfit_{pkg}__{arch}.csv", index=False)
