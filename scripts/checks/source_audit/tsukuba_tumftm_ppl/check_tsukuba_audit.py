"""Source-audit data checks for the tsukuba release (reports/source_audit_2026-10-04/tsukuba.md).

What it does: through the tsukuba loader only, (1) compares the raw and cleaned per-second file lists,
(2) lists the signal codes in the per-second files, (3) scans every raw and every cleaned per-second file
(raw values, clean=False) and counts the error code -999,999 and +999,999, values of battery DC current in
[-680, -450] A, battery DC voltage of 0, SOC above 100 % and equal to 0, negative total PV power, and blanks,
(4) for one July 2017 week, relates the sign of battery current and power to the change in SOC and to the
time of day.
Reads: the tsukuba release through fielddata (about 2 x 119 files, roughly 3 s each).
Writes: check_tsukuba_audit_perfile.csv next to this script (one row per file and version; rerun skips
files already recorded) and prints a summary.
Run from the repo root: .venv/Scripts/python.exe <path to this file>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))  # run from the repo root

import numpy as np
import pandas as pd

import fielddata
from fielddata.loaders import tsukuba

OUT = Path(__file__).with_name("check_tsukuba_audit_perfile.csv")
SIGNALS = list(tsukuba.NAMES.values())


def file_lists():
    raw, cleaned = tsukuba.files("raw"), tsukuba.files("cleaned")
    both = cleaned.merge(raw, on=["first_day", "last_day"], how="outer", indicator=True, suffixes=("_cleaned", "_raw"))
    print(f"[files] raw {len(raw)}, cleaned {len(cleaned)}")
    print(both[both["_merge"] != "both"].to_string(index=False))
    return raw, cleaned


def scan(raw, cleaned):
    done = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame(columns=["version", "first_day"])
    seen = set(zip(done["version"], done["first_day"].astype(str)))
    for version, table in (("raw", raw), ("cleaned", cleaned)):
        for _, row in table.iterrows():
            key = (version, str(row["first_day"].date()))
            if key in seen:
                continue
            f = fielddata.load("tsukuba", start=row["first_day"], end=row["last_day"], version=version)
            values = f[SIGNALS]
            real = values.mask(values.abs() == 999999)
            rec = {"version": version, "first_day": key[1], "last_day": str(row["last_day"].date()), "rows": len(f),
                   "time_min": f.index.min(), "time_max": f.index.max(),
                   "n_m999999": int((values == -999999).to_numpy().sum()), "n_p999999": int((values == 999999).to_numpy().sum()),
                   "n_blank": int(values.isna().to_numpy().sum()),
                   "rows_with_m999999": int((values == -999999).any(axis=1).sum()),
                   "dc_current_m680_m450": int(real["battery_dc_current"].between(-680, -450).sum()),
                   "dc_voltage_zero": int((real["battery_dc_voltage"] == 0).sum()),
                   "soc_gt100": int((real["battery_soc"] > 100).sum()), "soc_zero": int((real["battery_soc"] == 0).sum()),
                   "pv_total_negative": int((real["pv_active_power"] < 0).sum())}
            for c in SIGNALS:
                rec[f"min_{c}"], rec[f"max_{c}"] = real[c].min(), real[c].max()
                rec[f"m999_{c}"] = int((values[c] == -999999).sum())
            pd.DataFrame([rec]).to_csv(OUT, mode="a", header=not OUT.exists(), index=False)
            print(f"[scan] {version} {key[1]} rows {len(f)} -999999 {rec['n_m999999']}", flush=True)
    return pd.read_csv(OUT)


def summary(per):
    for version, g in per.groupby("version"):
        print(f"\n[{version}] files {len(g)}, rows {g['rows'].sum():,}, first {g['time_min'].min()}, last {g['time_max'].max()}")
        for col in ["n_m999999", "n_p999999", "rows_with_m999999", "n_blank", "dc_current_m680_m450", "dc_voltage_zero",
                    "soc_gt100", "soc_zero", "pv_total_negative"]:
            print(f"  {col}: {int(g[col].sum()):,}")
        hit = g[g["n_m999999"] > 0][["first_day", "n_m999999", "rows_with_m999999"]]
        print(f"  files with -999999: {len(hit)}")
        print(hit.to_string(index=False))
        print("  per-signal -999999 counts:", {c: int(g[f'm999_{c}'].sum()) for c in SIGNALS})
        print("  ranges excluding +-999999:")
        for c in SIGNALS:
            print(f"    {c}: {g[f'min_{c}'].min()} to {g[f'max_{c}'].max()}")


def maintenance_days():
    print("\n[maintenance days, raw] -999999 counts per day and column")
    for day in ["2015-11-13", "2015-11-14", "2016-11-18", "2016-11-19", "2017-11-17", "2017-11-18"]:
        f = fielddata.load("tsukuba", start=day, end=day, version="raw")
        if f.empty:
            print(f"  {day}: no raw rows")
            continue
        n = (f == -999999).sum()
        print(f"  {day}: rows {len(f)}, rows with any -999999 {int((f == -999999).any(axis=1).sum())}, "
              f"per column min {int(n.min())} max {int(n.max())}, dc_voltage==0 {int((f['battery_dc_voltage'] == 0).sum())}, "
              f"soc==0 {int((f['battery_soc'] == 0).sum())}")


def sign_week():
    print("\n[sign] raw 2017-07-10 to 2017-07-16, rows with an error code dropped")
    f = fielddata.load("tsukuba", start="2017-07-10", end="2017-07-16", version="raw", clean=True)
    f = f.dropna(subset=["battery_dc_current", "battery_active_power", "battery_soc"])
    m = f[["battery_dc_current", "battery_active_power", "battery_soc"]].resample("60s").mean()
    m["dsoc"] = m["battery_soc"].diff()
    ok = m.dropna()
    print(f"  minutes {len(ok)}; corr(current, dSOC/min) {ok['battery_dc_current'].corr(ok['dsoc']):.3f}; "
          f"corr(power, dSOC/min) {ok['battery_active_power'].corr(ok['dsoc']):.3f}; "
          f"corr(current, power) {ok['battery_dc_current'].corr(ok['battery_active_power']):.3f}")
    hour = f.index.hour
    weekday = f.index.dayofweek < 5
    for label, sel in (("weekday 13:00-16:00", weekday & (hour >= 13) & (hour < 16)), ("00:00-06:00", hour < 6)):
        g = f[sel]
        print(f"  {label}: mean current {g['battery_dc_current'].mean():.1f} A, mean power {g['battery_active_power'].mean():.1f} kW, "
              f"SOC change {g['battery_soc'].groupby(g.index.date).agg(lambda s: s.iloc[-1] - s.iloc[0]).mean():.2f} %/day-window")


if __name__ == "__main__":
    raw, cleaned = file_lists()
    sample = fielddata.load("tsukuba", start="2016-06-01", end="2016-06-01")
    codes = {k: v["unit"] for k, v in sample.attrs["signals"].items()}
    print(f"[codes] {len(codes)} per-second signals (renamed from codes via NAMES):", codes)
    print("[codes] 20104 (irradiance) present:", "20104" in codes or "solar_irradiance" in codes)
    per = scan(raw, cleaned)
    summary(per)
    maintenance_days()
    sign_week()
