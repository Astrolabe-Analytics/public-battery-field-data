"""A small first look at any release: one unit, a modest slice of rows.

Every loader answers ``fielddata.systems(package)`` and ``fielddata.load(package, ...)``, but the arguments
that keep a first load small differ by release (one month, one year, one partition, a few rows). ``EXAMPLES``
records those arguments so that ``sample(package)`` works the same way for every release and fits in a
few GB of memory.
"""
import itertools

import fielddata

# package -> keyword arguments for fielddata.load() that return a small, representative slice
EXAMPLES = {
    "aitio": {"unit": "0", "clean": True},
    "bilfinger2024": {"unit": None},  # filled from systems(): first vehicle-kind unit
    "bilfinger2026": {"unit": "Cupra_204_JB_8A_CEE7_C45"},
    "cao": {"brand": "QAS", "vehicle": "0", "names": "inferred", "clean": True},
    "changan": {"unit": "vin1", "nrows": 200_000, "clean": True},
    "cloverleaf": {"unit": "SNAM HV - 2100173"},
    "deng": {"pack": "#1"},
    "evbattery": {"unit": "battery_dataset1:0"},
    "fei_bus": {"unit": "vin1"},
    "flashbattery-agv": {"unit": "FB-0"},
    "ku_leuven_bev": {"unit": "BEV1", "session_type": "driving"},
    "li2026": {"unit": "real_world_02-03/battery_01"},
    "m5bat-2023-04": {"unit": "Batt2"},
    "m5bat-pbacid": {"source": "bms", "year": 2023, "rows": 200_000},  # via preview(): a full year is ~30 million rows
    "ppl": {"years": [2019]},
    "rwth-android": {"unit": "03b3c5a4a5d9a7a3d9829afa52b734c1"},
    "rwth-home": {"unit": "01", "month": "2019-06"},
    "schaeffer": {"system": 1, "chunksize": 500_000},  # first chunk only
    "tsukuba": {"start": "2016-06-01", "end": "2016-06-08"},
    "tumftm": {"unit": "CUP1", "value_id": 1200, "clean": True},  # pack voltage; the release is in long format
    "xie": {"unit": "0022234cc5964eae8c383cc9032cd51f"},
    "zhang2023": {"unit": "battery_brand1:1"},
    "zhou2026": {"unit": "LFP01", "part": 0,
                 "columns": ["Timestamp", "TotalVoltage", "TotalCurrent", "SOC", "MaxCellVoltage", "MinCellVoltage"]},
}


def example_args(package):
    """The load() arguments used by sample() for this release."""
    args = dict(EXAMPLES[package])
    if package == "bilfinger2024":
        units = fielddata.systems(package)
        args["unit"] = units.loc[units["kind"] == "vehicle", "unit"].iloc[0]
    return args


# releases whose loader has a preview() that reads only the first rows of a file
PREVIEW = {"m5bat-pbacid"}


def sample(package, **overrides):
    """Return a small DataFrame from one unit of ``package``. Keyword arguments replace the defaults,
    for example ``sample("rwth-home", unit="05")``."""
    args = {**example_args(package), **overrides}
    if package in PREVIEW:
        return fielddata._call(package, "preview", **args)
    frame = fielddata.load(package, **args)
    if not hasattr(frame, "columns"):  # a chunk reader: take the first chunk
        try:
            frame = next(iter(frame))
        except Exception as err:
            replacement = fielddata._not_downloaded(package, err)
            if replacement is None:
                raise
            raise replacement from err
    return frame


# package -> (column to plot, column for the x axis or None to use the frame's index)
PLOT = {
    "bilfinger2024": ("U", None), "bilfinger2026": ("U", None), "cao": ("cell_v_001", None),
    "changan": ("totalvoltage", "terminaltime"), "cloverleaf": ("Vpack", "epoch_ms"), "deng": ("pack_voltage", "number"),
    "evbattery": ("volt", "timestamp"), "fei_bus": ("SOH", "mileage"), "flashbattery-agv": ("cycletime", "counter"),
    "ku_leuven_bev": ("BattVoltage132", None), "li2026": ("cell_001_V", None), "m5bat-2023-04": ("U_DC_Batt", None),
    "m5bat-pbacid": ("voltage_bat_V_bms", None), "ppl": ("CellVoltAvg", None), "rwth-android": ("voltage_cell", None),
    "rwth-home": ("V_in_V", None), "schaeffer": ("U_Battery", "Timestamp"), "tsukuba": ("battery_dc_voltage", None),
    "tumftm": ("value", "time"), "xie": ("batCoreVoltage1", None), "zhang2023": ("max_single_volt", "timestamp"),
    "zhou2026": ("TotalVoltage", None), "aitio": ("voltage_V", None),
}


def plot(package, frame, ax=None):
    """Draw one signal from ``sample(package)`` and label it; returns the matplotlib axes."""
    import matplotlib.pyplot as plt
    y, x = PLOT[package]
    ax = ax or plt.subplots(figsize=(9, 3.5))[1]
    title = f"{package}: {y}"
    if "snippet" in frame.columns:  # snippet releases: draw one charging snippet, not hundreds on top of each other
        frame = frame[frame["snippet"] == frame["snippet"].iloc[0]]
        title += " (one snippet)"
    if x and package == "fei_bus":  # summary rows, not a time series
        frame = frame.sort_values(x)
        ax.plot(frame[x], frame[y], "o", ms=3, color="#2a6f97")
    else:
        xs = frame[x] if x else frame.index
        ax.plot(xs, frame[y], lw=0.6, color="#2a6f97")
    ax.set(title=title, xlabel=x or (frame.index.name or "row"), ylabel=y)
    return ax
