"""Raw loader for the Cao et al. released archives."""
from io import BytesIO
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

from fielddata._io import torchfree
from fielddata.config import data_root
from fielddata.registry import PACKAGES


_SENTINEL_VALUES = (-1004.8, -1000.0, -999.0, 65535.0)
# QAS writes stretches of current near -1,000 A (for example -995.0) where no current was recorded. No QAS
# vehicle charges anywhere near that rate, so clean=True masks QAS current at or below this value.
_QAS_BAD_CURRENT_A = -900.0


def _inferred_columns(width, which="vin_2"):
    """Return inferred names for the authors' pack + deviation layout (see cao_SCHEMA.md).

    vin_2 (2/N/N/3): pack-model state, measured cell voltages, model voltage deviations (dU_i), and measured
    temperature, state of charge and current. vin_3 (2/N/N/4): pack-model state, model cell state of charge,
    model state-of-charge deviations (dSOC_i), and the same three measured columns with an extra third column.
    State of charge is named ``soc_pct`` and returned in percent (see ``load``).
    """
    trailing = 3 if which == "vin_2" else 4
    if width < 2 + trailing or (width - 2 - trailing) % 2:
        raise ValueError(f"cannot infer names for {which} width {width}")
    cell_count = (width - 2 - trailing) // 2
    cells, deviations = ("cell_v", "cell_dU") if which == "vin_2" else ("cell_soc", "cell_dsoc")
    tail = ["temperature_degC", "soc_pct", "current_A"] if which == "vin_2" else ["temperature_degC", "soc_pct", "extra", "current_A"]
    return [
        "pack_state_a",
        "pack_state_b",
        *[f"{cells}_{index:03d}" for index in range(1, cell_count + 1)],
        *[f"{deviations}_{index:03d}" for index in range(1, cell_count + 1)],
        *tail,
    ]


def _clean_mask(frame, which, brand=None):
    """Return the value-wise impossible-measurement mask for a loaded frame."""
    values = frame.to_numpy(dtype=float, copy=False)
    masked = np.isin(values, _SENTINEL_VALUES) | (np.abs(values) > 1e6)
    if "current_A" in frame.columns:
        current_index = frame.columns.get_loc("current_A")
        masked[:, current_index] |= np.abs(values[:, current_index]) > 1000
        if brand == "QAS":
            masked[:, current_index] |= values[:, current_index] <= _QAS_BAD_CURRENT_A
    if which == "vin_2" and {"temperature_degC", "current_A"}.issubset(frame.columns):
        cell_columns = [column for column in frame.columns if column.startswith("cell_v_")]
        if cell_columns:
            cell_indices = frame.columns.get_indexer(cell_columns)
            masked[:, cell_indices] |= values[:, cell_indices] <= 0
        temperature_index = frame.columns.get_loc("temperature_degC")
        masked[:, temperature_index] |= (~np.isfinite(values[:, temperature_index]) | (values[:, temperature_index] < -40) | (values[:, temperature_index] > 150))
    return masked


def _archive_paths():
    package = PACKAGES["cao"]
    directory = data_root() / package["data_directory"]
    return [(filename, directory / filename) for filename in package["archives"]]


def _brand(filename):
    return filename.split("_", 1)[0].split(".", 1)[0]


def _labels(archive):
    label_members = [member for member in archive.namelist() if member.lower().endswith("labels.xls")]
    if not label_members:
        return {}
    labels = pd.read_excel(BytesIO(archive.read(label_members[0])), header=None)
    return {str(row.iloc[0]): row.iloc[1] for _, row in labels.iterrows() if len(row) > 1 and pd.notna(row.iloc[1])}


def systems():
    """Return one released row for each vehicle represented in the Cao archives.

    Each brand has at most one Labels.xls, and it covers every vehicle of that brand whichever archive the
    vehicle is in: the QAS sheet sits in QAS_5.zip but labels all 393 QAS vehicles across QAS_1 to QAS_5.
    """
    rows = []
    labels_by_brand = {}
    for filename, path in _archive_paths():
        with zipfile.ZipFile(path) as archive:
            labels_by_brand.setdefault(_brand(filename), {}).update(_labels(archive))
            members = archive.namelist()
            vehicles = {}
            for member in members:
                parts = Path(member).parts
                if len(parts) >= 2 and parts[-1] in {"vin_1.pkl", "vin_2.pkl", "vin_3.pkl"}:
                    vehicle = parts[-2]
                    vehicles.setdefault(vehicle, set()).add(parts[-1])
            for vehicle, files in vehicles.items():
                rows.append({
                    "brand": _brand(filename),
                    "vehicle": vehicle,
                    "source_zip": filename,
                    "vin_1": "vin_1.pkl" in files,
                    "vin_2": "vin_2.pkl" in files,
                    "vin_3": "vin_3.pkl" in files,
                })
    for row in rows:
        row["label"] = labels_by_brand.get(row["brand"], {}).get(row["vehicle"])
    return pd.DataFrame(rows).sort_values(["brand", "source_zip", "vehicle"], key=lambda series: series.map(lambda value: int(value) if str(value).isdigit() else str(value))).reset_index(drop=True)


def load_raw(brand, vehicle, which="vin_2"):
    """Load one released vehicle tensor without reshaping or conversion."""
    if which not in {"vin_1", "vin_2", "vin_3"}:
        raise ValueError("which must be vin_1, vin_2, or vin_3")
    matching_archives = [(filename, path) for filename, path in _archive_paths() if _brand(filename) == brand]
    if not matching_archives:
        raise ValueError(f"unknown Cao brand: {brand}")
    for filename, path in matching_archives:
        with zipfile.ZipFile(path) as archive:
            member = next((
                name for name in archive.namelist()
                if Path(name).parts[-2:] == (str(vehicle), f"{which}.pkl")
            ), None)
            if member:
                return torchfree.load(archive.read(member))
    raise FileNotFoundError(f"{which}.pkl not found for {brand} vehicle {vehicle}")


def load(brand, vehicle, which="vin_2", names="generic", clean=False):
    """Load one released two-dimensional vehicle tensor as a raw DataFrame.

    ``clean=True`` masks only individual values that cannot be measurements.
    The measured release sentinels are -1004.8, -1000, -999, and 65535.
    It also masks values with magnitude above 1e6, nonpositive inferred cell
    voltages, inferred temperatures outside -40 to 150 degC, inferred
    current whose magnitude exceeds 1000 A and, for QAS, inferred current at
    or below -900 A (the stretches near -1,000 A where no current was
    recorded). With inferred names it adds a boolean column ``current_invalid``,
    True in rows whose current was masked; the model outputs in those rows were
    computed from the bad current and are suspect. ``frame.attrs['masked_value_count']``
    records the number of values masked. Raw loading is the default.

    With ``names="inferred"``, state of charge is returned in percent for every brand: ``soc_pct`` (the
    onboard SOC reported by the vehicle's BMS) and, in vin_3, the per-cell ``cell_soc_###`` and
    ``cell_dsoc_###``. DTI releases these in percent (0 to 100) and QAS as a fraction (0 to 1), so QAS values
    are multiplied by 100. Placeholder codes are never rescaled. ``names="generic"`` returns every value as
    released.
    """
    values = load_raw(brand, vehicle, which)
    if values.ndim != 2:
        raise ValueError(f"{which}.pkl has released shape {values.shape}; use load_raw() for the unreshaped tensor")
    if names == "generic":
        columns = [f"col_{index:02d}" for index in range(values.shape[1])]
    elif names == "inferred" and which in {"vin_2", "vin_3"}:
        columns = _inferred_columns(values.shape[1], which)
    elif names == "inferred":
        raise ValueError("inferred names are defined only for vin_2 and vin_3")
    else:
        raise ValueError("names must be generic or inferred")
    frame = pd.DataFrame(values, columns=columns)
    masked_values = np.zeros(frame.shape, dtype=bool)
    if clean:
        masked_values = _clean_mask(frame, which, brand)
    frame = frame.mask(masked_values)
    if clean and "current_A" in frame.columns:
        frame["current_invalid"] = masked_values[:, frame.columns.get_loc("current_A")]
    if names == "inferred" and brand == "QAS":
        soc_columns = [c for c in frame.columns if c == "soc_pct" or c.startswith(("cell_soc_", "cell_dsoc_"))]
        released = frame[soc_columns].to_numpy(dtype=float)
        # a plain multiplication, not rounded, so results match those computed from the released fraction
        frame[soc_columns] = np.where(np.isin(released, _SENTINEL_VALUES), released, released * 100)
    frame.attrs = {
        "brand": brand,
        "vehicle": str(vehicle),
        "width": values.shape[1],
        "n_rows": values.shape[0],
        "masked_value_count": int(masked_values.sum()),
        "clean": clean,
        "schema_status": "GIS layout unknown; generic columns retained" if brand == "GIS" else "author code settles structural groups only; generic columns retained",
    }
    return frame