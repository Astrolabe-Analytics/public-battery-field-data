"""Loader for the commercial electric bus SOH summary tables (Mendeley Data j9ky68gnd3)."""
from __future__ import annotations

import pandas as pd

from fielddata.loaders._base import as_list, check_unit, concat, directory, finish

_PACKAGE = "fei_bus"


def _files():
    return sorted(directory(_PACKAGE).glob("vin*.csv"), key=lambda p: int(p.stem[3:]))


def systems():
    """One row per released bus summary file."""
    return pd.DataFrame([{"unit": p.stem, "file": p.name, "bytes": p.stat().st_size} for p in _files()])


def load(unit=None, clean=False):
    """Load one or more buses. Columns as released: SOH, SOH(OCV), mileage (km assumed). No timestamps.

    The Mendeley record defines no column: both SOH columns are estimates of undocumented method (SOH(OCV)
    reaches 1.34), and the mileage unit is not stated. Release order is mostly, not strictly, rising mileage.

    Rows keep release order; ``clean`` has no effect because no impossible values were found.
    """
    frames = []
    for item in as_list(unit, [p.stem for p in _files()]):
        name = check_unit(item, [p.stem for p in _files()], _PACKAGE)
        frame = pd.read_csv(directory(_PACKAGE) / f"{name}.csv")
        frame["unit"] = name
        frames.append(finish(frame, _PACKAGE, clean, 0, unit=name))
    return concat(frames, _PACKAGE, clean)
