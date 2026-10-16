"""Where are the reference performance tests (RPTs) in the pnnl_epri release? (raw data, through the loader)

The release has no dates and no test labels. An RPT is a set of full charges and discharges at constant power, so this
script lists every deep half-cycle: a run of one sign of Power at the system meter (|Power| above 0.02 C, gaps of at
most 15 min, runs shorter than 15 min of rest joined) whose SOC changes by at least 0.7. It then groups deep
half-cycles that start within 3 days of each other into clusters; clusters of four or more half-cycles are the
candidates for RPTs (a baseline RPT is typically three full cycles). For Avista, whose script anchors DayNumber 384 to
2016-11-01 (Avista.R flags 2016-11-01 to 2018-04-30, which the data show as DayNumber 384 to 928, pnnl_epri_findings.txt),
the clusters are also given as dates.
Reads: the pnnl_epri .feather files.
Writes: reports/candidates/pnnl_epri/pnnl_epri_deep_cycles.csv (one row per deep half-cycle),
reports/candidates/pnnl_epri/pnnl_epri_rpt_clusters.csv (one row per cluster of four or more) and
reports/candidates/pnnl_epri/pnnl_epri_rpt_stated.csv (each publicly stated RPT date placed on DayNumber with the anchors
below, and the nearest deep half-cycle).
Rerun: python scripts/checks/pnnl_epri_rpt.py
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
METER_ORDER = ["PGCP", "PDC", "PDC1", "PDC1a", "PDC1.1"]
# DayNumber -> date. Avista: from its script's flag window (see the docstring). EPRI_NMC2: hour 0 is 2017-01-01 00:00 UTC
# (pnnl_epri_overlap_confirm.csv). OPALCO and PSE: chosen so that the first stated RPT falls on a deep-cycle cluster
# (OPALCO DayNumber 4 = 2021-08-14, PSE DayNumber 84 = 2017-01-07); every other stated date is then a test of the anchor.
ANCHORS = {"Avista": (384, "2016-11-01"), "EPRI_NMC2": (0, "2017-01-01"), "OPALCO": (4, "2021-08-14"), "PSE": (84, "2017-01-07")}
# RPT dates stated in public reports (source in the third field).
STATED_RPT = {
    "Avista": (["2015-09-08", "2015-10-11", "2016-01-13", "2016-11-08", "2016-11-13"],
               "PNNL-28480 / PNNL-29378: baseline 2015-09-08 to 2015-10-11 and 2016-01-13; post-cycle 2016-11-08 to 13"),
    "PSE": (["2017-01-07", "2017-02-14", "2017-03-17", "2017-09-25", "2017-09-28", "2017-10-02", "2018-03-23", "2018-06-07", "2018-06-11"],
            "PNNL-28379: baseline, post-cycle 1 and post-cycle 2 RPT dates"),
    "OPALCO": (["2021-08-14", "2021-08-15", "2021-08-17", "2022-04-13", "2022-04-14", "2022-04-17"],
               "PNNL-ACT-10121: baseline and post-cycle 1 RPT dates"),
    "EPRI_NMC2": (["2017-07-13", "2018-01-05", "2018-07-27", "2018-08-28", "2018-11-05", "2018-11-07", "2018-12-16", "2020-04-16",
                   "2020-10-19", "2020-12-25", "2020-12-26", "2021-01-22", "2021-06-01", "2021-11-23", "2022-02-28", "2022-07-09",
                   "2022-10-06", "2022-11-14", "2023-06-27"],
                  "EPRI 3002027885 (E.W. Brown RPT list; 2018-11-07 listed three times)"),
}
P_MIN, DSOC_MIN, CLUSTER_DAYS = 0.02, 0.7, 3


def system_series(unit):
    for m in METER_ORDER:
        x = pnnl_epri.load(unit=unit, meter=m, columns=["Power", "SOC", "DayNumber"])
        if x[["Power", "SOC"]].notna().all(axis=1).sum() > 1000:
            return m, x.sort_values("HoursElapsed").reset_index(drop=True)
    return None, None


def deep_half_cycles(unit):
    meter, x = system_series(unit)
    if x is None:
        return []
    x = x.dropna(subset=["Power", "SOC"])
    state = np.where(x["Power"] > P_MIN, 1, np.where(x["Power"] < -P_MIN, -1, 0))
    active = x[state != 0].copy()
    active["state"] = state[state != 0]
    gap = active["HoursElapsed"].diff().gt(0.25) | active["state"].ne(active["state"].shift())
    active["run"] = gap.cumsum()
    rows = []
    for _, r in active.groupby("run"):
        dsoc = r["SOC"].iloc[-1] - r["SOC"].iloc[0]
        if abs(dsoc) >= DSOC_MIN:
            rows.append({"unit": unit, "meter": meter, "direction": "discharge" if r["state"].iloc[0] > 0 else "charge",
                         "start_hours": r["HoursElapsed"].iloc[0], "day_number": int(r["DayNumber"].iloc[0]),
                         "duration_h": r["HoursElapsed"].iloc[-1] - r["HoursElapsed"].iloc[0],
                         "soc_from": r["SOC"].iloc[0], "soc_to": r["SOC"].iloc[-1],
                         "mean_abs_power_c": r["Power"].abs().mean(), "power_cv": r["Power"].abs().std() / r["Power"].abs().mean()})
    return rows


def main() -> None:
    cycles = pd.DataFrame([row for unit in pnnl_epri.SYSTEMS for row in deep_half_cycles(unit)])
    cycles.to_csv(OUT / "pnnl_epri_deep_cycles.csv", index=False, lineterminator="\n", float_format="%.4f")
    clusters = []
    for unit, c in cycles.groupby("unit", sort=False):
        c = c.sort_values("start_hours")
        cid = (c["day_number"].diff() > CLUSTER_DAYS).cumsum()
        for _, g in c.groupby(cid):
            if len(g) < 4:
                continue
            row = {"unit": unit, "first_day": int(g["day_number"].min()), "last_day": int(g["day_number"].max()),
                   "half_cycles": len(g), "discharges": int((g["direction"] == "discharge").sum()),
                   "median_abs_power_c": g["mean_abs_power_c"].median(), "median_power_cv": g["power_cv"].median()}
            if unit in ANCHORS:
                day0, date0 = ANCHORS[unit]
                base = pd.Timestamp(date0) - pd.Timedelta(days=day0)
                row["dates_if_anchored"] = f"{(base + pd.Timedelta(days=row['first_day'])).date()} to {(base + pd.Timedelta(days=row['last_day'])).date()}"
            clusters.append(row)
    clusters = pd.DataFrame(clusters)
    clusters.to_csv(OUT / "pnnl_epri_rpt_clusters.csv", index=False, lineterminator="\n", float_format="%.4f")
    stated = []
    for unit, (dates, source) in STATED_RPT.items():
        day0, date0 = ANCHORS[unit]
        base = pd.Timestamp(date0) - pd.Timedelta(days=day0)
        c = cycles[cycles["unit"] == unit]
        last_day = int(c["day_number"].max()) if len(c) else -1
        for d in dates:
            day = (pd.Timestamp(d) - base).days
            near = (c["day_number"] - day).abs()
            stated.append({"unit": unit, "stated_date": d, "day_number": day, "in_record": 0 <= day <= last_day,
                           "nearest_deep_half_cycle_days": int(near.min()) if len(near) else None,
                           "deep_half_cycles_within_1_day": int((near <= 1).sum()), "source": source})
    stated = pd.DataFrame(stated)
    stated.to_csv(OUT / "pnnl_epri_rpt_stated.csv", index=False, lineterminator="\n")
    print(stated.drop(columns="source").to_string())
    print(cycles.groupby("unit")["direction"].value_counts().unstack(fill_value=0).to_string())
    print(clusters.to_string())


if __name__ == "__main__":
    main()
