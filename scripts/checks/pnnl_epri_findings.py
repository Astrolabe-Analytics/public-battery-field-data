"""Specific checks behind the pnnl_epri notes and schema (raw data, through the loader).

What it does, one line of output each:
  1. PSE: PSE.R computes a DC current zero offset (median DC current while the PCS is at rest) but subtracts 0 times it.
     Measures the released PDC Current and Power while PAC power is within 0.002 C of zero.
  2. EPRI_VRF1: share of positive Current on the inverter DC meters PDCI1 to PDCI3, against their Power.
  3. Avista: share of PDC1 and PDC2 rows with Voltage below 0.1 V per cell (strings at 0 V), and their SOC there.
  4. Stated power-to-energy ratio against the data: 99.9th percentile of |Power| at the system-level meter (or the sum
     over meters of one kind where there is no system meter) against rated_kw / rated_kwh from pnnl_epri_ratings.csv.
  5. SnoPUDMESA1: rows with |Power| above 2.5 C on any meter, and how many of them carry QualityFlag.
  6. Temperature exactly 0.0 degC: count per system (raw), a value the authors scrubbed as a sentinel in two systems.
  7. Avista: share of PDC rows inside the flagged replacement window, measured as QualityFlag share by DayNumber.
Reads: the pnnl_epri .feather files; reports/candidates/pnnl_epri/pnnl_epri_ratings.csv.
Writes: reports/candidates/pnnl_epri/pnnl_epri_findings.txt
Rerun: python scripts/checks/pnnl_epri_findings.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fielddata.loaders import pnnl_epri  # noqa: E402

OUT = ROOT / "reports" / "candidates" / "pnnl_epri"
SYSTEM_METER = {"Avista": "PGCP", "ENW": "PGCP", "OPALCO": "PGCP", "PSE": "PGCP", "SnoPUDMESA1": "PGCP",
                "SnoPUDMESA2": "PGCP", "EPRI_VRF1": "PGCP", "EPRI_NMC1": "PDC", "EPRI_NMC2": "PDC",
                "EPRI_LFP1": "PGCP", "EPRI_LFP2": "PACI", "EPRI_LFP3": "PGCP"}


def pse_offset(lines):
    d = pnnl_epri.load(unit="PSE", meter=["PAC", "PDC"], columns=["Power", "Current"])
    w = d.pivot_table(index="HoursElapsed", columns="Meter", values=["Power", "Current"])
    rest = w[("Power", "PAC")].abs() <= 0.002
    i, p = w.loc[rest, ("Current", "PDC")].dropna(), w.loc[rest, ("Power", "PDC")].dropna()
    lines.append(f"1. PSE at rest (|PAC Power| <= 0.002 C, {int(rest.sum()):,} timestamps): PDC Current median {i.median():.4f} C, "
                 f"positive in {100 * (i > 0).mean():.1f} %; PDC Power median {p.median():.4f} C, positive in {100 * (p > 0).mean():.1f} %")


def vrf_inverter_current(lines):
    d = pnnl_epri.load(unit="EPRI_VRF1", meter=["PDCI1", "PDCI2", "PDCI3"], columns=["Power", "Current"])
    for m, x in d.groupby("Meter"):
        i, p = x["Current"].dropna(), x["Power"].dropna()
        lines.append(f"2. EPRI_VRF1 {m}: Current positive in {100 * (i > 0).mean():.2f} % of {len(i):,} rows (min {i.min():.3f}, "
                     f"max {i.max():.3f} C); Power positive in {100 * (p > 0).mean():.2f} % of {len(p):,} rows")


def avista_zero_voltage(lines):
    d = pnnl_epri.load(unit="Avista", meter=["PDC1", "PDC2"], columns=["Voltage", "SOC", "Power", "DayNumber"])
    for m, x in d.groupby("Meter"):
        v = x["Voltage"].dropna()
        low = x["Voltage"] < 0.1
        lines.append(f"3. Avista {m}: Voltage below 0.1 V per cell in {100 * (v < 0.1).mean():.1f} % of {len(v):,} rows with a "
                     f"voltage; median |Power| there {x.loc[low, 'Power'].abs().median():.4f} C; DayNumber of those rows "
                     f"{int(x.loc[low, 'DayNumber'].min()) if low.any() else ''} to {int(x.loc[low, 'DayNumber'].max()) if low.any() else ''}")


def power_ratio(lines):
    ratings = pd.read_csv(OUT / "pnnl_epri_ratings.csv").set_index("unit")
    for unit, meter in SYSTEM_METER.items():
        d = pnnl_epri.load(unit=unit, columns=["Power"])
        if meter in set(d["Meter"]):
            p = d.loc[d["Meter"] == meter, "Power"]
            basis = meter
        else:  # no system meter: sum the meters of that kind at each timestamp
            sel = d["Meter"].str.match(rf"^{meter}\d")
            p = d[sel].groupby("HoursElapsed")["Power"].sum(min_count=1)
            basis = f"sum of {meter}n"
        q = float(p.abs().dropna().quantile(0.999))
        kw, kwh, ep = ratings.loc[unit, ["rated_kw", "rated_kwh", "poster_e_p"]]
        stated = kw / kwh if pd.notna(kw) and pd.notna(kwh) else np.nan
        lines.append(f"4. {unit}: p99.9 |Power| at {basis} {q:.3f} C; stated kW/kWh {stated:.3f}; 1 / poster E/P {1 / ep:.3f}")


def mesa1_spikes(lines):
    d = pnnl_epri.load(unit="SnoPUDMESA1", columns=["Power", "QualityFlag"])
    hit = d["Power"].abs() > 2.5
    lines.append(f"5. SnoPUDMESA1: {int(hit.sum()):,} rows with |Power| above 2.5 C ({', '.join(f'{m} {n}' for m, n in d.loc[hit, 'Meter'].value_counts().items())}); "
                 f"{int(d.loc[hit, 'QualityFlag'].sum()):,} of them flagged")


def zero_temps(lines):
    for unit in pnnl_epri.SYSTEMS:
        d = pnnl_epri.load(unit=unit, columns=["TempMax", "TempMin", "TempAvg"])
        counts = {c: int((d[c] == 0).sum()) for c in ["TempMax", "TempMin", "TempAvg"]}
        if any(counts.values()):
            lines.append(f"6. {unit}: temperature exactly 0.0 degC: " + ", ".join(f"{c} {n:,}" for c, n in counts.items() if n))


def avista_window(lines):
    d = pnnl_epri.load(unit="Avista", meter=["PGCP"], columns=["QualityFlag", "DayNumber"])
    flagged = d.groupby("DayNumber")["QualityFlag"].mean()
    days = flagged[flagged > 0.99].index
    lines.append(f"7. Avista: {len(days)} days with more than 99 % of PGCP rows flagged, DayNumber {days.min()} to {days.max()}; "
                 f"record DayNumber 0 to {int(d['DayNumber'].max())}")


def main() -> None:
    lines = []
    for check in (pse_offset, vrf_inverter_current, avista_zero_voltage, power_ratio, mesa1_spikes, zero_temps, avista_window):
        check(lines)
        print("\n".join(lines[-12:]) if check is power_ratio else lines[-1])
    (OUT / "pnnl_epri_findings.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
