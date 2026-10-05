"""Raw loader for the Schaeffer et al. battery-system field-data archive."""
from io import TextIOWrapper
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

from fielddata.config import data_root
from fielddata.registry import PACKAGES


def _archive_path():
    """Return the released field-data archive path."""
    package = PACKAGES["schaeffer"]
    return data_root() / package["data_directory"] / package["data_files"][0]


def _member_name(system):
    """Return the archive member for a released system number."""
    try:
        system = int(system)
    except (TypeError, ValueError) as exc:
        raise ValueError("system must be an integer from 1 through 28") from exc
    if not 1 <= system <= 28:
        raise ValueError("system must be an integer from 1 through 28")
    return f"field_data/data_sys_{system}.csv"


def systems():
    """Return one released row for each Schaeffer battery system."""
    with zipfile.ZipFile(_archive_path()) as archive:
        rows = []
        for system in range(1, 29):
            info = archive.getinfo(_member_name(system))
            rows.append({"system": system, "file": info.filename, "bytes": info.file_size})
    return pd.DataFrame(rows)


def _clean_cell_zeros(frame):
    """Mask exact-zero cell voltages (not documented by the authors), preserving every other value."""
    columns = [f"U_Cell_{index}" for index in range(1, 9)]
    counts = {column: int((frame[column] == 0).sum()) for column in columns}
    frame.loc[:, columns] = frame[columns].mask(frame[columns] == 0)
    return counts


def _clean_infinite(frame):
    """Mask +-inf values in numeric columns, one value at a time.

    Infinity cannot be a measurement; the authors' BattGP reader drops NaN and inf values
    (``src/batt_data/data_utils.py``, ``read_battery_fielddata``). Returns counts per column with any.
    """
    numeric = frame.select_dtypes("number").columns
    infinite = np.isinf(frame[numeric])
    counts = {column: int(n) for column, n in infinite.sum().items() if n}
    if counts:
        frame.loc[:, numeric] = frame[numeric].mask(infinite)
    return counts


def load(system, chunksize=None, clean=False):
    """Load one system as a timestamp-sorted DataFrame or CSV chunk reader.

    Set ``chunksize`` to a positive row count to stream the system once in
    source order. Each returned chunk has a parsed ``Timestamp`` column.
    Set ``clean=True`` to mask exact-zero cell voltages and +-inf values, one value at a time.

    Units (final article Table 3 and p. 4): voltages V, I_Battery A with negative = discharge (Table 3,
    "Discharge only", current -80 < x < -5 A), SOC_Battery % (a BMS estimate, not a measurement),
    temperatures degrees C. Temperature_k neighbours cells 2k-1 and 2k (BattGP ``data_columns.py``).
    Timestamps are naive; the time zone is not stated.
    """
    member = _member_name(system)
    if chunksize is not None:
        if not isinstance(chunksize, int) or chunksize < 1:
            raise ValueError("chunksize must be a positive integer")

        def chunks():
            with zipfile.ZipFile(_archive_path()) as archive:
                with archive.open(member) as raw:
                    yield from pd.read_csv(
                        TextIOWrapper(raw, encoding="utf-8"),
                        parse_dates=["Timestamp"],
                        chunksize=chunksize,
                    )

        def cleaned_chunks():
            for chunk in chunks():
                zero_counts = _clean_cell_zeros(chunk) if clean else {f"U_Cell_{index}": 0 for index in range(1, 9)}
                inf_counts = _clean_infinite(chunk) if clean else {}
                chunk.attrs = {"system": int(system), "clean": clean, "zero_cell_voltage_counts": zero_counts,
                               "infinite_value_counts": inf_counts}
                yield chunk

        return cleaned_chunks()
    with zipfile.ZipFile(_archive_path()) as archive:
        with archive.open(member) as raw:
            frame = pd.read_csv(TextIOWrapper(raw, encoding="utf-8"), parse_dates=["Timestamp"])
    frame = frame.sort_values("Timestamp", kind="stable").reset_index(drop=True)
    zero_counts = _clean_cell_zeros(frame) if clean else {f"U_Cell_{index}": 0 for index in range(1, 9)}
    inf_counts = _clean_infinite(frame) if clean else {}
    frame.attrs = {
        "system": int(system),
        "n_rows": len(frame),
        "timestamp_column": "Timestamp",
        "cell_voltage_columns": [f"U_Cell_{index}" for index in range(1, 9)],
        "current_column": "I_Battery",
        "soc_column": "SOC_Battery",
        "temperature_columns": [f"Temperature_{index}" for index in range(1, 5)],
        "clean": clean,
        "zero_cell_voltage_counts": zero_counts,
        "zero_cell_voltage_count": sum(zero_counts.values()),
        "infinite_value_counts": inf_counts,
    }
    return frame