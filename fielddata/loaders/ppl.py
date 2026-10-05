"""Loader for the PPL E.W. Brown BESS annual ESS telemetry CSVs."""
from __future__ import annotations

import io
import re
import zipfile

import pandas as pd

from fielddata.config import data_root
from fielddata.registry import PACKAGES

_PACKAGE = "ppl"
_UNIT = "E_W_Brown_BESS"
_ESS_PATTERN = re.compile(r"ESS_(\d{4})\.csv$")


# Outage placeholders: while the battery system is offline the files carry 0 in SOH and the cell voltages,
# and in the same rows 0 in AvgSOC and the module temperatures (runs of up to 61 days that line up with the
# outages in the paper, Section IV; the publisher's live feed shows the same zeros when the system is not
# running). A cell voltage or SOH of 0 cannot be a measurement of this battery, so those zeros are masked
# everywhere; AvgSOC and module-temperature zeros only in rows whose CellVoltAvg is 0.
_ZERO_ALWAYS = ("SOH", "CellVoltAvg", "CellVoltMax", "CellVoltMin")
_ZERO_WITH_CELLS = ("AvgSOC", "ModuleTempMax", "ModuleTempMin")


def _clean_impossible_values(frame):
    numeric = frame.select_dtypes(include="number")
    mask = numeric.abs() > 1_000_000
    for column in numeric.columns:
        if mask[column].any():
            frame[column] = numeric[column].astype(float).mask(mask[column])
    count = int(mask.to_numpy().sum())
    offline = frame["CellVoltAvg"] == 0 if "CellVoltAvg" in frame else pd.Series(False, index=frame.index)
    for column in _ZERO_ALWAYS + _ZERO_WITH_CELLS:
        if column not in frame:
            continue
        hit = frame[column] == 0
        if column in _ZERO_WITH_CELLS:
            hit &= offline
        if hit.any():
            frame[column] = frame[column].astype(float).mask(hit)
            count += int(hit.sum())
    return count


def _directory():
    return data_root() / PACKAGES[_PACKAGE]["data_directory"] / "BESS-Analysis"


def _ess_files():
    files = []
    for path in _directory().glob("ESS_*.csv"):
        match = _ESS_PATTERN.match(path.name)
        if match:
            files.append((int(match.group(1)), path))
    return sorted(files)


def systems():
    """Return one monitored system row for the E.W. Brown BESS."""
    files = [{"file": path.name, "bytes": path.stat().st_size} for _, path in _ess_files()]
    years = [year for year, _ in _ess_files()]
    return pd.DataFrame([{
        "unit": _UNIT,
        "site": "E.W. Brown Generating Station",
        "system_rating": "1 MW / 2 MWh",
        "chemistry": "lithium ion",
        "years": years,
        "files": files,
    }])


def load_raw(year, clean=False):
    """Load one released annual ESS CSV without cleaning, conversion, or resampling."""
    path = dict(_ess_files()).get(int(year))
    if path is None:
        raise ValueError(f"year not present for ppl: {year}")
    frame = pd.read_csv(path)
    masked_value_count = _clean_impossible_values(frame) if clean else 0
    frame.attrs = {"clean": clean, "masked_value_count": masked_value_count}
    return frame


def load(years=None, clean=False):
    """Load annual ESS CSVs indexed by Timestamp, preserving released columns.

    No source states the time zone of ``Timestamp``. The loader parses the released wall-clock values and
    tags them UTC; that label has no source, and the data suggest a local clock (see the schema note).
    Positive ``PowerReal`` means discharging and positive ``DCCurrent`` (2022 on) charging; this is measured
    from the data, not stated by the publisher. ``AvgSOC`` and ``SOH`` are BMS estimates (paper Fig. 2, 3).
    ``clean=True`` masks magnitudes above 1,000,000 and the outage zeros described at ``_ZERO_ALWAYS``;
    rows are kept.
    """
    available = dict(_ess_files())
    requested = sorted(available) if years is None else sorted(int(year) for year in years)
    missing = sorted(set(requested) - set(available))
    if missing:
        raise ValueError(f"years not present for ppl: {missing}")
    frames = []
    masked_value_count = 0
    for year in requested:
        frame = pd.read_csv(available[year])
        masked_value_count += _clean_impossible_values(frame) if clean else 0
        frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce", utc=True)
        frame = frame.set_index("Timestamp").sort_index()
        frames.append(frame)
    out = pd.concat(frames, axis=0, sort=False) if len(frames) > 1 else frames[0]
    out.attrs = {
        "package": _PACKAGE,
        "unit": _UNIT,
        "years": requested,
        "n_rows": len(out),
        "source_files": [available[year].name for year in requested],
        "clean": clean,
        "masked_value_count": masked_value_count,
    }
    return out


def time_bounds():
    """First timestamp of the first annual file and last timestamp of the last one, as released."""
    files = _ess_files()
    first = pd.read_csv(files[0][1], usecols=["Timestamp"], nrows=1)["Timestamp"].iloc[0]
    last = pd.read_csv(files[-1][1], usecols=["Timestamp"])["Timestamp"].iloc[-1]
    return pd.Timestamp(first), pd.Timestamp(last)


def preview(year, rows=1000):
    """The first ``rows`` rows of one annual ESS CSV, as released."""
    path = dict(_ess_files()).get(int(year))
    if path is None:
        raise ValueError(f"year not present for ppl: {year}")
    return pd.read_csv(path, nrows=rows)


def _cell_level_directory():
    return data_root() / PACKAGES[_PACKAGE]["data_directory"] / "cell_level"


def cell_level_files():
    """The monthly zips of the publisher's cell-level (BMS log) share, if held: name and bytes.

    These are the "sub-second cell level data" of the paper (Section III), linked from the repository's
    ``Cell_Level_Data`` file. ``load()`` does not read them.
    """
    paths = sorted(_cell_level_directory().glob("*.zip"))
    return pd.DataFrame([{"file": p.name, "bytes": p.stat().st_size} for p in paths], columns=["file", "bytes"])


def cell_level_members(file):
    """Members of one cell-level zip: name and uncompressed size."""
    with zipfile.ZipFile(_cell_level_directory() / file) as z:
        return pd.DataFrame([{"member": i.filename, "bytes": i.file_size} for i in z.infolist() if not i.is_dir()])


def cell_level_preview(file, member, rows=1000):
    """The first ``rows`` rows of one CSV log in a cell-level zip, as released (leading ``#`` lines skipped)."""
    with zipfile.ZipFile(_cell_level_directory() / file) as z:
        with z.open(member) as handle:
            comments = []
            for raw in io.TextIOWrapper(handle, encoding="latin-1"):
                if raw.strip() and not raw.startswith("#"):
                    break
                comments.append(raw.strip())
        with z.open(member) as handle:
            frame = pd.read_csv(io.TextIOWrapper(handle, encoding="latin-1"), skiprows=len(comments), nrows=rows)
    frame.attrs = {"file": file, "member": member, "comments": [c for c in comments if c]}
    return frame
