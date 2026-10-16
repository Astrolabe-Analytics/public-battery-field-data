"""Energy from the data for the v1.2 releases (present usable energy, the v1.1 coulomb-counting method), with stated
ratings beside it as a cross-check.

What it does: for each package, through its loader, finds runs of samples with no gap over 300 s in which SOC moves
one way (charge or discharge) by at least 40 percentage points (a reversal of up to 2 points, such as regenerative
braking during a drive, does not end a run; a run ends at its extreme), and for each run computes ampere-hours per 100 percent
SOC (|integral of current dt| / (delta SOC / 100)) times the mean pack voltage over the run. The median over a unit's
runs is its energy, and the release's energy is the sum over its units. This is the method of scripts/facts/_extra.py
for zhou2026 and the other coulomb-counted releases (DESCRIPTOR.md 3.6). pnnl_epri releases current and power
normalised by unreleased ratings, so for it the same method gives usable energy as a fraction of the rated energy
(integral of normalised power / delta SOC), not kWh. Where a release lacks current, voltage or SOC it reports "not
computable" and why. Stated ratings (paper, record or registry) are only a cross-check column, with the ratio
measured / stated, and any ratio more than 20 percent from 1 is flagged. All values raw.

Reads: the packages through their loaders.
Writes: reports/checks/v12/<name>_energy.csv (one row per unit) and reports/candidates/V12_ENERGY.md.

Run:
    python scripts/checks/v12_energy.py [package ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import fielddata  # noqa: E402

OUT = ROOT / "reports" / "candidates"
CHECKS = ROOT / "reports" / "checks" / "v12"  # public outputs: deltas and measured energy per package
MIN_DSOC, MAX_GAP_S, REVERSAL = 40.0, 300.0, 2.0


def seconds(stamps) -> np.ndarray:
    """Seconds since 1970 for datetimes of any resolution (pandas may store parsed times in s, us or ns)."""
    return ((pd.to_datetime(stamps) - pd.Timestamp("1970-01-01")) / pd.Timedelta(seconds=1)).to_numpy(dtype=float)


def runs(t, i, v, soc):
    """kWh per run: t seconds, i amperes, v volts, soc percent, all aligned arrays sorted by time."""
    t, i, v, soc = (np.asarray(x, dtype=float) for x in (t, i, v, soc))
    ok = ~(np.isnan(t) | np.isnan(i) | np.isnan(v) | np.isnan(soc))
    t, i, v, soc = t[ok], i[ok], v[ok], soc[ok]
    if len(t) < 3:
        return []
    out, start = [], 0
    direction, extreme = 0, soc[0]
    for k in range(1, len(t) + 1):
        broken = k == len(t) or t[k] - t[k - 1] > MAX_GAP_S  # end of data or a gap: the next run starts after it
        end_run = broken
        if not end_run:
            if not direction and abs(soc[k] - soc[start]) > REVERSAL:
                direction = np.sign(soc[k] - soc[start])
            if direction:
                extreme = max(extreme, soc[k]) if direction > 0 else min(extreme, soc[k])
                # a reversal of more than REVERSAL points from the run's extreme ends it (small regen upticks do not)
                end_run = (extreme - soc[k]) * direction > REVERSAL
        if end_run:
            a, b = start, k
            if direction:  # end the run at its extreme, not at the reversal
                idx = np.arange(a, b)
                b = int(idx[np.argmax(soc[a:b] * direction)]) + 1
            dsoc = abs(soc[b - 1] - soc[a])
            if b - a >= 3 and dsoc >= MIN_DSOC:
                dt = np.diff(t[a:b])
                ah = abs(np.sum(i[a:b - 1] * dt)) / 3600
                out.append({"dsoc": dsoc, "ah_per_100": ah / (dsoc / 100), "kwh": ah / (dsoc / 100) * np.mean(v[a:b]) / 1000,
                            "hours": (t[b - 1] - t[a]) / 3600})
            start, direction = (k if broken else b - 1), 0  # after a reversal the next run starts at the extreme
            extreme = soc[start] if start < len(soc) else 0
    return out


def unit_row(package, unit, segments, stated_kwh=None, note=""):
    kwh = float(np.median([s["kwh"] for s in segments])) if segments else None
    return {"package": package, "unit": unit, "runs": len(segments), "kwh_measured": kwh,
            "kwh_stated": stated_kwh, "ratio": (kwh / stated_kwh) if kwh and stated_kwh else None, "note": note}


# ---- per package: returns (rows, method, not_computable_reason) ----

def beijing_ev():
    rows, segs = [], []
    for day in fielddata.systems("beijing_ev")["unit"]:
        d = fielddata.load("beijing_ev", unit=day)
        t = seconds(pd.to_datetime(d["time"].astype(str), format="%Y%m%d%H%M%S"))
        segs += runs(t, d["current"], d["voltage"], d["soc"])
    rows.append(unit_row("beijing_ev", "BEV", segs))
    return rows, "coulomb counting on pack current, voltage and SOC (10 s), runs over the 12 days", None


def brazil_star():
    rows = []
    for unit in fielddata.systems("brazil_star")["unit"]:
        d = fielddata.load("brazil_star", unit=unit, system="Battery", clean=True)
        d["t"] = pd.to_datetime(d["Time"], errors="coerce")
        d = d.dropna(subset=["t"]).sort_values("t")
        current = d["Current"].where(d["Current"] <= 32767)  # wrapped unsigned values left out of the integral
        segs = runs(seconds(d["t"]), current / 1000, d["Voltage"] / 1000, d["SOC"] / 10)
        rows.append(unit_row("brazil_star", unit, segs, note="current mA, voltage mV, SOC in tenths of a percent"))
    return rows, "coulomb counting on battery current, voltage and SOC (1 min)", None


def ved():
    rows = []
    systems = fielddata.systems("ved").set_index("unit")
    units = list(systems[systems["battery_signals"]].index) + ["439"]
    cols = ["Trip", "Timestamp(ms)", "HV Battery Current[A]", "HV Battery SOC[%]", "HV Battery Voltage[V]"]
    data = fielddata.load("ved", unit=[int(u) for u in units], columns=cols)
    for unit in units:
        d = data[data["VehId"] == int(unit)].copy()
        # DayNum repeats within a trip at its resolution; Timestamp(ms) is the time within the trip (README)
        d["t"] = d.groupby("Trip")["DayNum"].transform("min") * 86400 + d["Timestamp(ms)"] / 1000
        segs = []
        for _, trip in d.groupby("Trip"):
            trip = trip.sort_values("t")[["t", *cols[2:]]].ffill()
            segs += runs(trip["t"], trip[cols[2]], trip[cols[4]], trip[cols[3]])
        stated = 24.0 if systems.loc[unit, "Vehicle Type"] == "EV" else None
        rows.append(unit_row("ved", unit, segs, stated, "runs within trips; signals forward-filled between updates"))
    return rows, "coulomb counting on HV battery current, voltage and SOC within trips", None


def tongji_rest():
    rows = []
    for unit in ["LFP01", "NMC01_Car01", "NMC01_Car02", "NMC02"]:
        segs = []
        for kind in ("charge", "rest"):
            d = fielddata.load("tongji_rest", unit=unit, kind=kind)
            for _, seg in d.groupby("segment"):
                seg = seg.sort_values("reqDate")
                segs += runs(seconds(seg["reqDate"]), seg["totalCurrent"], seg["totalVoltage"], seg["soc"])
        rows.append(unit_row("tongji_rest", unit, segs))
    return rows, "coulomb counting on pack current, voltage and SOC within each released segment", None


def tum_id3_2022():
    segs = []
    from fielddata.loaders import tum_id3_2022 as tum
    for track in tum.tracks()["track"]:
        d = fielddata.load("tum_id3_2022", track=track, columns=["hv_battery_current", "hv_battery_voltage", "hv_soc"])
        if not {"hv_battery_current", "hv_battery_voltage", "hv_soc"} <= set(d.columns):
            continue
        d = d.sort_values("time").ffill()
        segs += runs(d["time"] / 1000, d["hv_battery_current"], d["hv_battery_voltage"], d["hv_soc"])
    return [unit_row("tum_id3_2022", "ID3", segs, 58.0, "same car as tumftm ID1; stated 58 kWh net (ID.3 Pro Performance)")], \
        "coulomb counting on pack current, voltage and SOC within drives", None


def cell_to_pack():
    rows = []
    from fielddata.loaders import cell_to_pack as c
    for unit in c.FIELD:
        d = c.load(unit, columns=["time(s)", "current(A)", "Vpack", "SOC"])
        segs = []
        for _, cyc in d.groupby("item"):
            segs += runs(cyc["time(s)"], cyc["current(A)"], cyc["Vpack"], cyc["SOC"])
        rows.append(unit_row("cell_to_pack", unit, segs, note="runs within each released cycle"))
    return rows, "coulomb counting on pack current, pack voltage and SOC within each cycle", None


def stanford_ev():
    from fielddata.loaders import stanford_ev as st
    segs = []
    sessions = st.sessions()
    for name in sessions[sessions["kind"] == "Charging"]["session"]:
        soc = st.load(name, "SOC_pack_bms")
        if soc.empty or soc["SOC_pack_bms"].max() - soc["SOC_pack_bms"].min() < MIN_DSOC:
            continue
        i = st.load(name, "I_pack_bms")
        v = st.load(name, "V_pack_bms")
        # the three signals have their own time bases: current and voltage are interpolated onto the SOC times
        current = np.interp(soc["t"], i["t"], i["I_pack_bms"])
        volts = np.interp(soc["t"], v["t"], v["V_pack_bms"])
        segs += runs(soc["t"], current, volts, soc["SOC_pack_bms"])
    return [unit_row("stanford_ev", "EV1", segs, None, "charging sessions with a 40 percent SOC swing")], \
        "coulomb counting on pack current, voltage and SOC in charging sessions (0.01 s)", None


def pnnl_epri():
    from fielddata.loaders import pnnl_epri as p
    ratings = pd.read_csv(OUT / "pnnl_epri" / "pnnl_epri_ratings.csv").set_index("unit")["rated_kwh"]
    # the system-level meter of scripts/checks/pnnl_epri_findings.py (EPRI_LFP2: the sum of its PACI meters)
    system_meter = {"Avista": "PGCP", "ENW": "PGCP", "OPALCO": "PGCP", "PSE": "PGCP", "SnoPUDMESA1": "PGCP",
                    "SnoPUDMESA2": "PGCP", "EPRI_VRF1": "PGCP", "EPRI_NMC1": "PDC", "EPRI_NMC2": "PDC",
                    "EPRI_LFP1": "PGCP", "EPRI_LFP2": "PACI", "EPRI_LFP3": "PGCP"}
    rows = []
    for unit in p.SYSTEMS:
        d = p.load(unit=unit, columns=["Power", "SOC"])
        meter = system_meter[unit]
        chosen = d["Meter"].astype(str).str.fullmatch(meter + (r"\d+" if unit == "EPRI_LFP2" else ""))
        power = d[chosen].groupby("HoursElapsed")["Power"].sum(min_count=1)
        soc = d.groupby("HoursElapsed")["SOC"].mean()  # SOC averaged over the meters that report it
        both = pd.concat([power, soc], axis=1).dropna().sort_index()
        # normalised power (C-rate, 1/h) integrated over hours gives energy in units of the rated energy
        best = runs(both.index.to_numpy() * 3600, both["Power"] * 1000, np.ones(len(both)), both["SOC"] * 100)
        fraction = float(np.median([s["kwh"] for s in best])) if best else None  # = usable / rated energy
        stated = ratings.get(unit)
        rows.append({"package": "pnnl_epri", "unit": unit, "runs": len(best), "usable_fraction_of_rated": fraction,
                     "kwh_stated": stated if pd.notna(stated) else None,
                     "kwh_measured": None, "ratio": fraction,
                     "note": "values released normalised by unreleased ratings: usable energy measured as a fraction of the rated energy only"})
    return rows, "coulomb counting on normalised power and SOC: usable energy as a fraction of the rated energy", \
        "the release divides power and current by ratings it does not release, so absolute energy cannot be computed from the data"


NOT_COMPUTABLE = {
    "birds_cubesat": "no SOC signal: the workbooks release battery voltage, current and temperature only",
    "rise_conbat": "no SOC signal: module and cell voltage and temperature, and string power, current and energy counters, but no state of charge",
    "shenzhen_charging": "not counted in MWh (maintainer's decision): charging sessions without vehicle identity",
}
MEASURE = {f.__name__: f for f in (beijing_ev, brazil_star, ved, tongji_rest, tum_id3_2022, cell_to_pack, stanford_ev, pnnl_epri)}


def main(argv: list[str]) -> int:
    names = argv or [*MEASURE, *NOT_COMPUTABLE]
    summary_path = CHECKS / "v12_energy_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    for name in names:
        if name in NOT_COMPUTABLE:
            summary[name] = {"method": None, "not_computable": NOT_COMPUTABLE[name], "kwh_measured": None}
            print(f"{name}: not computable ({NOT_COMPUTABLE[name]})")
            continue
        rows, method, reason = MEASURE[name]()
        table = pd.DataFrame(rows)
        table.to_csv(CHECKS / f"{name}_energy.csv", index=False, lineterminator="\n")
        measured = table["kwh_measured"].dropna()
        summary[name] = {"method": method, "not_computable": reason, "units_measured": int(measured.size), "units": len(table),
                         "kwh_measured": float(measured.sum()) if measured.size else None,
                         "kwh_stated": float(table["kwh_stated"].dropna().sum()) if table["kwh_stated"].notna().any() else None}
        print(f"{name}: {method}")
        print(table.to_string(index=False))
    summary_path.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
