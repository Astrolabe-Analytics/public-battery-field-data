"""Per-system profile of the pnnl_epri candidate release (raw data, through the loader).

What it does: for each of the 12 systems, reads its .feather through fielddata.loaders.pnnl_epri and records rows,
meters, span (HoursElapsed and DayNumber), row spacing on the system's timeline, the HoursElapsed dtype, the share of
rows with QualityFlag, coverage of each measured column, value ranges of Power, Current, Voltage, SOC and the
temperatures, the sign check (Power against the next change of SOC on the system-level meter) and, per meter, the
shares of positive Power and Current and how often they share a sign.
Reads: the 12 .feather files in the pnnl_epri data folder.
Writes: reports/candidates/pnnl_epri/pnnl_epri_units.csv (one row per system, appended as each finishes; systems
already recorded are skipped) and reports/candidates/pnnl_epri/pnnl_epri_meters.csv (one row per system and meter).
Rerun: python scripts/checks/pnnl_epri_units.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fielddata.loaders import pnnl_epri  # noqa: E402

OUT = ROOT / "reports" / "candidates" / "pnnl_epri"
UNITS = OUT / "pnnl_epri_units.csv"
METERS = OUT / "pnnl_epri_meters.csv"
MEASURED = ["Power", "RequestedPower", "ReactivePower", "RequestedReactivePower", "Voltage", "VoltageMax",
            "VoltageMin", "VoltageAvg", "Current", "SOC", "TempMax", "TempMin", "TempAvg", "TempAmbient"]
SYSTEM_METERS = ["PGCP", "PFDR", "PAC", "PDC"]  # system-level meter preference for the sign check


def _q(series, q):
    s = series.dropna()
    return float(s.quantile(q)) if len(s) else np.nan


def _sign_check(frame):
    """Share of steps where Power and the next SOC change have opposite signs (positive = discharge expected).
    ``frame`` holds HoursElapsed, Meter, Power and SOC."""
    has = frame[["Power", "SOC"]].notna().all(axis=1).groupby(frame["Meter"]).sum()
    has = has[has > 0]
    meters = [m for m in SYSTEM_METERS if m in has.index] or list(has.sort_values(ascending=False).index[:1])
    if not meters:
        return "", np.nan, 0
    m = meters[0]
    x = frame.loc[frame["Meter"] == m, ["HoursElapsed", "Power", "SOC"]].sort_values("HoursElapsed")
    dsoc = x["SOC"].shift(-1) - x["SOC"]
    ok = x["Power"].abs().gt(0.05) & dsoc.abs().gt(0) & dsoc.notna()
    if ok.sum() < 100:
        return m, np.nan, int(ok.sum())
    return m, float((np.sign(x.loc[ok, "Power"]) == -np.sign(dsoc[ok])).mean()), int(ok.sum())


def profile(unit: str) -> tuple[dict, list[dict]]:
    """Profile one system, reading a few columns at a time through the loader (the largest file has 65 million rows)."""
    base = pnnl_epri.load(unit=unit, columns=["DayNumber", "QualityFlag", "Use", "CycleIndex"])
    timeline = np.sort(base["HoursElapsed"].unique())
    step_s = np.diff(timeline) * 3600
    meters = list(pd.unique(base["Meter"]))
    by = base.groupby("Meter", sort=False)
    per = pd.DataFrame({"rows": by.size(), "quality_flag_share": by["QualityFlag"].mean()})
    row = {
        "unit": unit, "rows": len(base), "meters": len(meters), "meter_names": " ".join(meters),
        "timestamps": len(timeline), "hours_elapsed_dtype": str(base["HoursElapsed"].dtype),
        "first_hours": float(timeline[0]), "last_hours": float(timeline[-1]),
        "span_days": float(timeline[-1] - timeline[0]) / 24, "max_day_number": int(base["DayNumber"].max()),
        "median_step_s": float(np.median(step_s)), "share_steps_at_median": float(np.mean(np.isclose(step_s, np.median(step_s), atol=0.5))),
        "steps_over_1h": int((step_s > 3600).sum()), "longest_gap_h": float(step_s.max() / 3600),
        "covered_days": float(len(timeline) * np.median(step_s) / 86400),
        "quality_flag_share": float(base["QualityFlag"].mean()),
        "use_share": float(base["Use"].astype("boolean").fillna(False).mean()),
        "cycle_segments": int(base["CycleIndex"].nunique()),
    }
    del base, by
    frame = pnnl_epri.load(unit=unit, columns=["Power", "Current", "SOC"])
    row.update({"power_min": _q(frame["Power"], 0), "power_p001": _q(frame["Power"], 0.001),
                "power_p999": _q(frame["Power"], 0.999), "power_max": _q(frame["Power"], 1),
                "current_min": _q(frame["Current"], 0), "current_max": _q(frame["Current"], 1),
                "soc_min": _q(frame["SOC"], 0), "soc_max": _q(frame["SOC"], 1)})
    sign_meter, sign_share, sign_n = _sign_check(frame)
    by = frame.groupby("Meter", sort=False)
    per["power_positive_share"] = by["Power"].apply(lambda s: (s.dropna() > 0).mean() if s.notna().any() else np.nan)
    per["current_positive_share"] = by["Current"].apply(lambda s: (s.dropna() > 0).mean() if s.notna().any() else np.nan)
    both = frame[(frame["Power"].abs() > 0.01) & (frame["Current"].abs() > 0.01)]
    same = (np.sign(both["Power"]) == np.sign(both["Current"])).groupby(both["Meter"]).agg(["mean", "size"])
    per["power_current_same_sign_share"] = same["mean"].where(same["size"] >= 100)
    per["power_current_rows"] = same["size"]
    for c in ["Power", "Current", "SOC"]:
        per[f"cov_{c}"] = by[c].apply(lambda s: s.notna().mean())
    del frame, by, both
    frame = pnnl_epri.load(unit=unit, columns=["Voltage", "VoltageMax", "VoltageMin", "VoltageAvg"])
    row.update({"voltage_min": _q(frame["Voltage"], 0), "voltage_median": _q(frame["Voltage"], 0.5),
                "voltage_max": _q(frame["Voltage"], 1), "cellmax_max": _q(frame["VoltageMax"], 1),
                "cellmin_min": _q(frame["VoltageMin"], 0)})
    by = frame.groupby("Meter", sort=False)
    for c in ["Voltage", "VoltageMax", "VoltageMin", "VoltageAvg"]:
        per[f"cov_{c}"] = by[c].apply(lambda s: s.notna().mean())
    per["voltage_median"] = by["Voltage"].median()
    del frame, by
    frame = pnnl_epri.load(unit=unit, columns=["TempMax", "TempMin", "TempAvg", "TempAmbient", "RequestedPower",
                                               "ReactivePower", "RequestedReactivePower"])
    temps = frame[["TempMax", "TempMin", "TempAvg"]].stack()
    row.update({"temp_min": _q(temps, 0), "temp_max": _q(temps, 1),
                "ambient_min": _q(frame["TempAmbient"], 0), "ambient_max": _q(frame["TempAmbient"], 1),
                "sign_meter": sign_meter, "sign_discharge_positive_share": sign_share, "sign_steps": sign_n})
    by = frame.groupby("Meter", sort=False)
    for c in ["RequestedPower", "ReactivePower", "RequestedReactivePower", "TempMax", "TempMin", "TempAvg", "TempAmbient"]:
        per[f"cov_{c}"] = by[c].apply(lambda s: s.notna().mean())
    del frame, by, temps
    per = per.reindex(meters)
    meter_rows = [{"unit": unit, "meter": m, "rows": int(r["rows"]), "quality_flag_share": r["quality_flag_share"],
                   "power_positive_share": r["power_positive_share"], "current_positive_share": r["current_positive_share"],
                   "power_current_same_sign_share": r["power_current_same_sign_share"],
                   "power_current_rows": int(0 if pd.isna(r["power_current_rows"]) else r["power_current_rows"]),
                   "voltage_median": r["voltage_median"],
                   **{f"cov_{c}": round(float(r[f"cov_{c}"]), 4) for c in MEASURED}} for m, r in per.iterrows()]
    return row, meter_rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    done = set(pd.read_csv(UNITS)["unit"]) if UNITS.exists() else set()
    for unit in pnnl_epri.SYSTEMS:
        if unit in done:
            continue
        if not (pnnl_epri.directory("pnnl_epri") / f"{unit}.feather").exists():
            print(f"{unit}: not downloaded yet, skipped")
            continue
        row, meter_rows = profile(unit)
        for path, rows in ((UNITS, [row]), (METERS, meter_rows)):
            new = not path.exists()
            with path.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
                if new:
                    writer.writeheader()
                writer.writerows(rows)
        print(f"{unit}: {row['rows']:,} rows, {row['meters']} meters, {row['span_days']:.1f} days, "
              f"median step {row['median_step_s']:.0f} s")


if __name__ == "__main__":
    main()
