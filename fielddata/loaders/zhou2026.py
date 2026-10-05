"""Loader for the Zhou et al. vehicle data release (Vehicle data.zip, 60 parquet partitions)."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import pyarrow.compute as pc
import pyarrow.parquet as pq

from fielddata.loaders._base import as_list, check_unit, concat, directory, finish

_PACKAGE = "zhou2026"
_ARCHIVE = "Vehicle data.zip"
# Which vin appears in which partition, with row counts. Generated from the release by build_index()
# because reading it needs a pass over all 2.2 GB; committed so systems() is instant.
INDEX = Path(__file__).with_name("zhou2026_partitions.csv")


def build_index() -> pd.DataFrame:
    rows = []
    with zipfile.ZipFile(directory(_PACKAGE) / _ARCHIVE) as z:
        for name in sorted(n for n in z.namelist() if n.endswith(".parquet")):
            table = pq.read_table(io.BytesIO(z.read(name)), columns=["vin", "Timestamp"]).to_pandas()
            for vin, group in table.groupby("vin"):
                rows.append({"partition": name, "vin": vin, "rows": len(group),
                             "first": int(group["Timestamp"].min()), "last": int(group["Timestamp"].max())})
    frame = pd.DataFrame(rows)
    frame.to_csv(INDEX, index=False, lineterminator="\n")
    return frame


def _index():
    return pd.read_csv(INDEX)


def systems():
    """One row per released vehicle identifier (vin) with its partitions, rows and first and last timestamps."""
    idx = _index()
    g = idx.groupby("vin")
    out = pd.DataFrame({"unit": list(g.groups), "partitions": g.size().to_numpy(), "rows": g["rows"].sum().to_numpy(),
                        "first": g["first"].min().to_numpy(), "last": g["last"].max().to_numpy()})
    for c in ("first", "last"):
        out[c] = pd.to_datetime(out[c].astype(str), format="%Y%m%d%H%M%S")
    return out


def expand_cells(frame: pd.DataFrame, column: str = "CellVoltages") -> pd.DataFrame:
    """Split the released per-cell string into one numeric column per cell.

    Strings are released as ``<pack>:<v1>_<v2>_...``; a leading ``<pack>:`` prefix is dropped. Values are not
    rescaled. CellVoltages holds one value per cell in mV. CellTemperatures holds one value per temperature
    probe, not per cell; in the two cars the values are degrees C plus 40 (from the data: the largest minus 40
    equals MaxTemp), in LFP01 they carry no offset and include 255, which no source defines.
    """
    body = frame[column].astype(str).str.replace(r"^\d+:", "", regex=True)
    parts = body.str.split("_", expand=True)
    parts.columns = [f"{column}_{i + 1}" for i in range(parts.shape[1])]
    parts.index = frame.index
    return parts.apply(pd.to_numeric, errors="coerce")


def load(unit, columns=None, part=None, clean=False):
    """Load one or more vins, indexed by ``Timestamp`` (released as YYYYMMDDhhmmss integers, parsed; time zone not stated).

    LFP01 is an LFP bus (156 cells); vehicle45 and vehicle69 are NMC passenger cars (95 cells), per SI Table 1.
    TotalCurrent is negative while charging (SI Figs. 23-24); SOC is the BMS estimate. The released rows are
    the input to the authors' preprocessing, not its output: they still hold duplicates, SOC <= 0 and
    TotalVoltage <= 0 rows that the authors' code drops.

    ``columns`` limits the columns read (the per-cell strings CellVoltages and CellTemperatures are large).
    ``part`` picks some of the vin's partitions by position (0 to 19); a whole vin with the cell strings needs
    well over 4 GB of memory.
    Values are as released; ``clean`` has no effect.
    """
    idx = _index()
    frames = []
    with zipfile.ZipFile(directory(_PACKAGE) / _ARCHIVE) as z:
        for item in as_list(unit, []):
            vin = check_unit(item, idx["vin"].unique(), _PACKAGE)
            parts = []
            names = list(idx.loc[idx["vin"] == vin, "partition"])
            names = names if part is None else [names[i] for i in as_list(part, [])]
            for name in names:
                read = None if columns is None else sorted(set(columns) | {"vin", "Timestamp"})
                table = pq.read_table(io.BytesIO(z.read(name)), columns=read)
                parts.append(table.filter(pc.equal(table["vin"], vin)).to_pandas())
            frame = pd.concat(parts, ignore_index=True)
            frame["Timestamp"] = pd.to_datetime(frame["Timestamp"].astype("int64").astype(str), format="%Y%m%d%H%M%S", errors="coerce")
            frames.append(finish(frame.set_index("Timestamp").sort_index(kind="stable"), _PACKAGE, clean, 0, unit=vin))
    return concat(frames, _PACKAGE, clean)
