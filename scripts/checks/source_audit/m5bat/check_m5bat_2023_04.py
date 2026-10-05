"""Data checks for the m5bat-2023-04 source audit (reports/source_audit_2026-10-04/m5bat-2023-04.md), raw data.

What it does:
1. Time zone: compares the April 2023 files with the m5bat-pbacid release, whose index is UTC per its codebook.
   (a) BESS Grid_frequency / 1000 against pbacid BSC frequency_Hz_bsc over all of April 2023;
   (b) Batt1 U_DC_Batt / 10 against pbacid BMS voltage_bat_V_bms on 2023-04-10.
   Each is the Pearson r between the 2023-04 value at file time t and the pbacid value at UTC t - lag, for lags
   of -2, -1, 0, +1, +2 h, and for lags of -10 to +10 s. A peak at lag 0 means the file time is UTC; a peak at
   +2 h would mean CEST (MESZ, UTC+2).
2. Per battery unit: median U_DC_Batt / 10 over rows with U_DC_Batt > 0 (to compare with the report p. 3
   wiring), SOC and U_DC_Batt ranges, sign agreement of I_DC_Batt and P_AC over rows with |P_AC| > 10 kW,
   share of rows with interpolated == 1, number and longest run of consecutive interpolated rows, and the
   share of rows with each Mode flag set. The same interpolation figures for BESS.
Reads: fielddata.load("m5bat-2023-04", unit=...) and fielddata.loaders.m5bat_pbacid.load(...).
Writes: <out>/m5bat_2023_04_timezone.csv and <out>/m5bat_2023_04_units.csv.
Usage: python check_m5bat_2023_04.py <out_dir>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import fielddata
from fielddata.loaders import m5bat_pbacid

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "reports")
OUT.mkdir(parents=True, exist_ok=True)


def utc_naive(index):
    index = pd.DatetimeIndex(index)
    return index.tz_convert("UTC").tz_localize(None) if index.tz is not None else index


def lag_r(a, b, lag):
    """Pearson r of a(t) and b(t - lag), both 1 s series indexed by naive UTC-or-file time."""
    shifted = b.copy()
    shifted.index = shifted.index + lag
    joined = pd.concat([a.rename("a"), shifted.rename("b")], axis=1, join="inner").dropna()
    return (joined["a"].corr(joined["b"]) if len(joined) > 2 else np.nan), len(joined)


def runs(flag):
    values = flag.to_numpy().astype(bool)
    if not values.any():
        return 0, 0
    edges = np.diff(np.concatenate([[0], values.astype(int), [0]]))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    return len(starts), int((ends - starts).max())


def timezone():
    rows = []
    bess = fielddata.load("m5bat-2023-04", unit="BESS")
    f_file = (bess["Grid_frequency"] / 1000.0)
    f_file.index = utc_naive(f_file.index)
    bsc = m5bat_pbacid.load("bsc", years=[2023], columns=["frequency_Hz_bsc"])["frequency_Hz_bsc"]
    bsc.index = utc_naive(bsc.index)
    bsc = bsc.loc["2023-03-31 21:00":"2023-05-01 03:00"]
    bsc = bsc[~bsc.index.duplicated()]
    batt1 = fielddata.load("m5bat-2023-04", unit="Batt1")
    u_file = batt1["U_DC_Batt"].loc["2023-04-10"] / 10.0
    u_file.index = utc_naive(u_file.index)
    bms = m5bat_pbacid.load("bms", years=[2023], columns=["voltage_bat_V_bms"])["voltage_bat_V_bms"]
    bms.index = utc_naive(bms.index)
    bms = bms.loc["2023-04-09 21:00":"2023-04-11 03:00"]
    bms = bms[~bms.index.duplicated()]
    lags = [pd.Timedelta(hours=h) for h in (-2, -1, 0, 1, 2)] + [pd.Timedelta(seconds=s) for s in range(-10, 11) if s]
    for name, a, b in (("frequency: BESS Grid_frequency/1000 vs pbacid frequency_Hz_bsc, April 2023", f_file, bsc),
                       ("voltage: Batt1 U_DC_Batt/10 vs pbacid voltage_bat_V_bms, 2023-04-10", u_file, bms)):
        for lag in lags:
            r, n = lag_r(a, b, lag)
            rows.append({"pair": name, "lag_s": int(lag.total_seconds()), "r": r, "n_rows": n})
            print(name, lag, r, n, flush=True)
    # level agreement at lag 0
    joined = pd.concat([u_file.rename("a"), bms.rename("b")], axis=1, join="inner").dropna()
    rows.append({"pair": "voltage: median(Batt1 U/10 - pbacid voltage_bat_V_bms), V, 2023-04-10, lag 0",
                 "lag_s": 0, "r": float((joined["a"] - joined["b"]).median()), "n_rows": len(joined)})
    pd.DataFrame(rows).to_csv(OUT / "m5bat_2023_04_timezone.csv", index=False)


def units():
    rows = []
    for unit in [f"Batt{i}" for i in range(1, 11)] + ["BESS"]:
        f = fielddata.load("m5bat-2023-04", unit=unit)
        n_runs, longest = runs(f["interpolated"])
        row = {"unit": unit, "n_rows": len(f), "interpolated_share": f["interpolated"].mean(),
               "interpolated_runs": n_runs, "interpolated_longest_run_s": longest,
               "index_unique": f.index.is_unique,
               "index_steps_not_1s": int((np.diff(utc_naive(f.index).values).astype("timedelta64[s]").astype(np.int64) != 1).sum()),
               "index_tz": str(f.index.tz), "first": f.index.min(), "last": f.index.max()}
        if unit != "BESS":
            u = f["U_DC_Batt"]
            p, i = f["P_AC"], f["I_DC_Batt"]
            active = p.abs() > 10
            agree = (np.sign(p[active]) == np.sign(i[active]))
            row.update({"U_median_V_when_gt0": (u[u > 0] / 10).median(), "U_min": u.min(), "U_max": u.max(),
                        "SOC_min": f["SOC"].min(), "SOC_max": f["SOC"].max(),
                        "P_AC_min_kW": p.min(), "P_AC_max_kW": p.max(),
                        "rows_absP_gt10": int(active.sum()), "sign_I_equals_sign_P_share": agree.mean() if active.any() else np.nan,
                        "corr_I_P_active": i[active].corr(p[active]) if active.any() else np.nan,
                        **{f"{m}_share": f[m].mean() for m in ("Mode_PQ", "Mode_Stop", "Mode_Silent", "Mode_Wait")}})
        else:
            row.update({"Grid_frequency_min": f["Grid_frequency"].min(), "Grid_frequency_max": f["Grid_frequency"].max(),
                        "Temperature_min": f["Temperature"].min(), "Temperature_max": f["Temperature"].max(),
                        "SOC_min": f["SOC"].min(), "SOC_max": f["SOC"].max()})
        rows.append(row)
        print(row, flush=True)
        del f
    pd.DataFrame(rows).to_csv(OUT / "m5bat_2023_04_units.csv", index=False)


if __name__ == "__main__":
    units()
    timezone()
