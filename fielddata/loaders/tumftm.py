"""Loader for the TUM FTM electric-vehicle UDS dataset (seven VW ID.3 and CUPRA Born vehicles)."""
from __future__ import annotations

import pandas as pd
import pyarrow.parquet as pq

from fielddata.loaders._base import as_list, check_unit, concat, directory, finish

_PACKAGE = "tumftm"
_ROOT = "electric-vehicle-uds-dataset/data"


def _files():
    return {p.stem: p for p in sorted((directory(_PACKAGE) / _ROOT / "uds_data").glob("*.parquet"))}


def signals():
    """The released value_overview.csv: value_id, names, variable_name, unit, range and sampling interval."""
    return pd.read_csv(directory(_PACKAGE) / _ROOT / "value_overview.csv")


def systems():
    """One row per vehicle parquet (CUP1 to CUP5, ID1, ID2) with its row count."""
    return pd.DataFrame([{"unit": k, "file": p.name, "bytes": p.stat().st_size, "rows": pq.ParquetFile(p).metadata.num_rows}
                         for k, p in _files().items()])


def load(unit, value_id=None, clean=False):
    """Load one or more vehicles in the released long format: vehicle_id, time, value_id, value.

    ``value_id`` selects signals (see ``signals()``); ``variable_name`` and ``unit`` are joined on. Only 15 of
    the 29 signals in ``value_overview.csv`` have rows; none is a pack current, C-rate or cell voltage. Times
    are naive; no source states the time zone. ``clean=True`` sets timestamps in or after 2030 to NaT and
    keeps the rows: CUP1 has 812 rows dated 2087-03-07, a value we observed in the data and that the authors
    do not describe.
    """
    files = _files()
    names = signals()[["value_id", "variable_name", "unit"]]
    frames = []
    for item in as_list(unit, files):
        name = check_unit(item, list(files), _PACKAGE)
        filters = None if value_id is None else [("value_id", "in", as_list(value_id, []))]
        frame = pq.read_table(files[name], filters=filters).to_pandas()
        masked = 0
        if clean:
            bad = frame["time"].dt.year >= 2030
            masked = int(bad.sum())
            frame.loc[bad, "time"] = pd.NaT
        frame = frame.merge(names, on="value_id", how="left")
        frames.append(finish(frame, _PACKAGE, clean, masked, unit=name))
    return concat(frames, _PACKAGE, clean)


def time_bounds(unit, clean=True):
    """First and last timestamp of one vehicle from the parquet row-group statistics.

    With ``clean=True`` timestamps in or after 2030 (the observed 2087 rows in CUP1) are left out: a row group
    whose statistics reach 2030 has its time column read so that its valid timestamps still count.
    """
    name = check_unit(unit, list(_files()), _PACKAGE)
    meta = pq.ParquetFile(_files()[name])
    column = meta.schema.names.index("time")
    cutoff = pd.Timestamp("2030-01-01")
    bounds = []
    for group in range(meta.metadata.num_row_groups):
        stats = meta.metadata.row_group(group).column(column).statistics
        if stats and stats.has_min_max:
            lo, hi = pd.Timestamp(stats.min), pd.Timestamp(stats.max)
            if clean and hi >= cutoff:
                times = meta.read_row_group(group, columns=["time"]).column("time").to_pandas()
                times = times[times < cutoff]
                if times.empty:
                    continue
                lo, hi = times.min(), times.max()
            bounds.append((lo, hi))
    return min(b[0] for b in bounds), max(b[1] for b in bounds)
