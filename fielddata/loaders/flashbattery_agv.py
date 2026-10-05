"""Loader for the Flash Battery AGV partial-discharge observation table (Zenodo 7748947)."""
from __future__ import annotations

import pandas as pd

from fielddata.loaders._base import as_list, check_unit, directory, finish

_PACKAGE = "flashbattery-agv"


def _table():
    return pd.read_csv(directory(_PACKAGE) / "dataset.csv")


def systems():
    """One row per released battery pack (the ``battery`` column)."""
    t = _table()
    g = t.groupby("battery")
    return pd.DataFrame({"unit": list(g.groups), "cycles": g.size().to_numpy(),
                         "first_date": g["date"].min().to_numpy(), "last_date": g["date"].max().to_numpy()})


def load(unit=None, clean=False):
    """Load partial-discharge observations for one, several or all packs, indexed by ``date`` (the day the
    observation started; no time of day, time zone not stated).

    Columns as released (README.adoc; paper Table I): counter (observation counter over all operating modes),
    cycletime (s; the paper's Table I says minutes, the released values are seconds), totaldischarge (cumulative
    discharge, Ah), mintemperature and maxtemperature (lowest and highest cell temperature, integer C), battery.
    ``clean`` has no effect: the release holds none of the invalid values the paper names (date 2000-01-01,
    -40 C, 215 C) and no other impossible values were found.
    """
    t = _table()
    units = sorted(t["battery"].unique())
    wanted = [check_unit(u, units, _PACKAGE) for u in as_list(unit, units)]
    t = t[t["battery"].isin(wanted)].copy()
    t["date"] = pd.to_datetime(t["date"])
    t = t.rename(columns={"battery": "unit"}).set_index("date").sort_index(kind="stable")
    return finish(t, _PACKAGE, clean, 0, units=wanted)
