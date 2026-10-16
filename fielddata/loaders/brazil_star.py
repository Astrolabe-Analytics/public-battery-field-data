"""Loader for the Brazil STAR microgrid monitoring release (Gaura, Trindade, Brusey, Gyamfi and Verba, Zenodo
10.5281/zenodo.3959739, CC BY 4.0). Candidate package: not in the totals. No paper describes the data.

Four households (STAR-A to STAR-D) in a rural community in Amazonas, Brazil, with a solar and battery system each.
The release is one zip, ``Brazil_STAR_Microgrid_Monitoring.zip``, of daily CSVs named ``YYYY-MM-DD-STAR-X_SYS.csv``
(SYS is Battery, PV or IAM, individual appliance monitors) and ``MonitoringDataReadMe.txt``. The loader reads the
CSVs inside the zip and changes no value: units are as the readme gives them (current mA, ampere-hours mAh, voltage
mV, energy in 0.01 kWh), and ``Time`` stays the released text.

``systems()`` lists the four households, and ``load(unit, system="Battery")`` returns one household's files of one
kind, one row per minute, with the day file's name added. See ``brazil_star_SCHEMA.md``.
"""
from __future__ import annotations

import io
import re
import zipfile

import pandas as pd

from fielddata.loaders._base import as_list, check_unit, concat, directory, finish

_PACKAGE = "brazil_star"
ARCHIVE = "Brazil_STAR_Microgrid_Monitoring.zip"
UNITS = ["STAR-A", "STAR-B", "STAR-C", "STAR-D"]
KINDS = ["Battery", "PV", "IAM"]
COLUMNS = {
    "Battery": ["Time", "Current", "AmpereHours", "SOC", "NumChargeCycles", "NumFullDischarge", "Voltage", "Power",
                "DischargeEnergy", "ChargeEnergy"],
    "PV": ["Time", "Panel_voltage", "Panel_power", "Energy_generated", "Battery_state"],
    "IAM": ["Time", "Real_Power", "Reactive_Power", "Voltage", "Sensor_ID"],
}
VALID_FROM, VALID_TO = pd.Timestamp("2017-01-01"), pd.Timestamp("2030-01-01")  # outside: clock resets (schema)
_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})[-_](STAR-[A-D])_(Battery|PV|IAM)\.csv$")  # the readme shows "-", the files "_"


def _archive() -> zipfile.ZipFile:
    return zipfile.ZipFile(directory(_PACKAGE) / ARCHIVE)


def _members(archive: zipfile.ZipFile) -> list[tuple[str, str, str, str]]:
    """(member name, day, household, kind) for every daily CSV, in name order."""
    out = []
    for name in sorted(archive.namelist()):
        match = _NAME.search(name)
        if match:
            out.append((name, *match.groups()))
    return out


def systems() -> pd.DataFrame:
    """One row per household: days of Battery, PV and IAM files, battery rows, and first and last battery Time."""
    rows = []
    with _archive() as archive:
        members = _members(archive)
        for unit in UNITS:
            row = {"unit": unit, "household": unit}
            for kind in KINDS:
                row[f"{kind.lower()}_days"] = sum(1 for _, _, u, k in members if u == unit and k == kind)
            times, count = [], 0
            for name, _, u, k in members:
                if u == unit and k == "Battery":
                    frame = pd.read_csv(io.BytesIO(archive.read(name)), usecols=["Time"])
                    count += len(frame)
                    times.append(pd.to_datetime(frame["Time"], errors="coerce"))
            stamps = pd.concat(times) if times else pd.Series(dtype="datetime64[ns]")
            valid = stamps[(stamps >= VALID_FROM) & (stamps < VALID_TO)]
            row.update({"battery_rows": count, "first": valid.min(), "last": valid.max(),
                        "battery_time_invalid": int(len(stamps) - len(valid))})
            rows.append(row)
    return pd.DataFrame(rows)


def load(unit=None, system="Battery", clean=False):
    """Load one household's daily files of one kind (Battery, PV or IAM) as released, with a ``file`` column.

    ``clean=True`` masks single values that cannot be measurements (see the schema): Time outside 2017 to 2029
    (clock resets such as 1969-12-31 20:00, and appliance monitors dated 2036), and in Battery files SOC outside
    0 to 1000 (tenths of a percent). Rows are kept. Every other value is as released.
    """
    if system not in KINDS:
        raise ValueError(f"{_PACKAGE}: system must be one of {KINDS}")
    units = as_list(unit, UNITS)
    frames = []
    with _archive() as archive:
        members = _members(archive)
        for u in units:
            u = check_unit(u, UNITS, _PACKAGE)
            parts = []
            for name, _, household, kind in members:
                if household == u and kind == system:
                    part = pd.read_csv(io.BytesIO(archive.read(name)))
                    part.insert(0, "file", name)
                    parts.append(part)
            frame = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["file", *COLUMNS[system]])
            masked = 0
            if clean and len(frame):
                stamps = pd.to_datetime(frame["Time"], errors="coerce")
                bad = stamps.notna() & ((stamps < VALID_FROM) | (stamps >= VALID_TO))
                frame["Time"] = frame["Time"].mask(bad)
                masked += int(bad.sum())
                if system == "Battery":
                    soc = pd.to_numeric(frame["SOC"], errors="coerce")
                    bad = (soc < 0) | (soc > 1000)
                    frame["SOC"] = soc.mask(bad)
                    masked += int(bad.sum())
            if len(units) > 1:
                frame.insert(0, "unit", u)
            frames.append(finish(frame, _PACKAGE, clean, masked, unit=u, system=system))
    return concat(frames, _PACKAGE, clean, system=system)
