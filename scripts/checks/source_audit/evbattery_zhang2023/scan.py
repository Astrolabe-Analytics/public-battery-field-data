"""Audit data checks for evbattery and zhang2023 (source audit 2026-10-04).

Reads every snippet of one archive through the loader (fielddata.loaders.<package>.iter_snippets), raw values,
and writes one summary row per snippet to <scratch>/snip_<package>__<archive>.parquet plus archive-level
counters to <scratch>/arch_<package>__<archive>.json. Skips archives already done.
Usage: python scan.py <package> <archive>
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import importlib

OUT = Path(__file__).parent
package, archive = sys.argv[1], sys.argv[2]
snip_path = OUT / f"snip_{package}__{archive}.parquet"
arch_path = OUT / f"arch_{package}__{archive}.json"
if snip_path.exists() and arch_path.exists():
    print("done already", archive)
    sys.exit()
mod = importlib.import_module(f"fielddata.loaders.{package}")
cols = mod.COLUMNS
rows = []
dt_counter = collections.Counter()
meta_keys = collections.Counter()
capacity_values = collections.Counter()
n_rows = neg = pos = zero = 0
shapes = collections.Counter()
nan_cells = collections.Counter()
for member, a, meta in mod.iter_snippets(archive):
    a = a.astype(float)
    shapes[str(a.shape)] += 1
    for k in meta:
        meta_keys[k] += 1
    for j, c in enumerate(cols[: a.shape[1]]):
        nan_cells[c] += int(np.isnan(a[:, j]).sum())
    v, i, soc, vmax, vmin, tmax, tmin, ts = (a[:, j] for j in range(8))
    dt = np.diff(ts)
    for d in np.round(dt, 1):
        dt_counter[float(d)] += 1
    n_rows += len(i)
    neg += int((i < 0).sum()); pos += int((i > 0).sum()); zero += int((i == 0).sum())
    cell = (vmax + vmin) / 2
    q_ah = float(np.sum(np.abs(i[:-1]) * dt) / 3600.0)  # left Riemann sum of |I| dt, in A*h if dt is in s
    q_signed = float(np.sum(i[:-1] * dt) / 3600.0)
    if np.std(cell) > 0 and np.std(v) > 0:
        slope, intercept = np.polyfit(cell, v, 1)
        r = float(np.corrcoef(cell, v)[0, 1])
    else:
        slope = intercept = r = np.nan
    cap = meta.get("capacity", None)
    if cap is not None:
        capacity_values["nan" if (isinstance(cap, float) and np.isnan(cap)) else ("zero" if float(cap) == 0 else "positive")] += 1
    rows.append(dict(
        member=member.rsplit("/", 1)[-1], car=int(meta["car"]), label=meta.get("label"),
        charge_segment=meta.get("charge_segment"), mileage=float(meta["mileage"]) if meta.get("mileage") is not None else np.nan,
        capacity=float(cap) if cap is not None else np.nan,
        ts0=ts[0], ts1=ts[-1], dt_med=float(np.median(dt)), dt_min=float(dt.min()), dt_max=float(dt.max()),
        soc0=soc[0], soc1=soc[-1], soc_min=soc.min(), soc_max=soc.max(),
        i_mean=float(i.mean()), i_min=float(i.min()), i_max=float(i.max()), i_neg=int((i < 0).sum()), i_pos=int((i > 0).sum()),
        q_abs_ah=q_ah, q_signed_ah=q_signed,
        v_mean=float(v.mean()), v_min=float(v.min()), v_max=float(v.max()),
        cell_mean=float(cell.mean()), vmax_max=float(vmax.max()), vmin_min=float(vmin.min()),
        tmax_max=float(tmax.max()), tmin_min=float(tmin.min()),
        v_cell_slope=float(slope), v_cell_intercept=float(intercept), v_cell_r=r,
    ))
df = pd.DataFrame(rows)
df["charge_segment"] = df["charge_segment"].astype(str)
df["label"] = pd.to_numeric(df["label"], errors="coerce")
df.to_parquet(snip_path)
arch = dict(package=package, archive=archive, snippets=len(df), vehicles=int(df["car"].nunique()), rows=n_rows,
            current_neg=neg, current_pos=pos, current_zero=zero, shapes=dict(shapes), meta_keys=dict(meta_keys),
            capacity_values=dict(capacity_values), nan_cells=dict(nan_cells),
            dt_top=[[k, v] for k, v in dt_counter.most_common(25)], dt_total=sum(dt_counter.values()))
arch_path.write_text(json.dumps(arch, indent=1))
print(json.dumps(arch)[:2000])
