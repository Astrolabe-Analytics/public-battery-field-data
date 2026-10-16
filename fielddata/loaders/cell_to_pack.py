"""Loader for the LFP and NMC cell-to-pack aging release (He, Deng, Huang, Liu, Busch, Tang, Hu and Li, Zenodo
10.5281/zenodo.20132842, CC BY 4.0), data for the manuscript "Resolving inter-cell heterogeneity to mitigate degradation
amplification in battery packs" (unpublished). Candidate package: not in the totals.

Twenty zips. ``Pack_field#1`` to ``#16`` each hold one field grid-storage pack: a pickle of per-cycle data and three
derived CSVs (per-cell capacity and SOC matrices against equivalent full cycles, and pack capacity). ``ESSH1``,
``ESSL1``, ``ESSL2`` and ``PBSL1`` hold laboratory cells and packs, as pickles. Unpickling can run code, so this loader
never unpickles. It reads the Parquet copies made once by ``scripts/checks/convert_pickles/run_cell_to_pack.sh`` in a
throwaway environment (maintainer's decision, 2026-10-13), kept in ``converted/`` beside the release's ``data/`` folder,
outside git and the export. Manifest with input and output SHA-256: reports/candidates/cell_to_pack/pickle_conversion.csv.
Each pickle was a list with one entry per cycle, holding ``constant_metadata`` (one row) and ``timeseries_data``.
The Parquet copies keep both, with an ``item`` column for the list position. No value is changed.

Maintainer's decision: hold everything, count only the 16 field packs as units.

``systems()`` lists field packs, laboratory packs and laboratory cells, ``load(unit, part="timeseries"|"metadata")``
reads one unit's converted data, and ``matrix(unit, which)`` reads a field pack's CSV from its zip.
See ``cell_to_pack_SCHEMA.md``.
"""
from __future__ import annotations

import re
import zipfile

import pandas as pd

from fielddata.loaders._base import directory, finish

_PACKAGE = "cell_to_pack"
FIELD = [f"Pack_field#{i}" for i in range(1, 17)]
LAB = ["ESSH1", "ESSL1", "ESSL2", "PBSL1"]
MATRICES = {"capacity": "capacity_matrix", "SOC": "SOC_matrix", "pack_capacity": "pack_capacity"}
CELL_NOMINAL_V = 3.2  # LFP nominal cell voltage, assumed: the release states no nominal voltage


def _converted():
    folder = directory(_PACKAGE).parent / "converted"
    if not folder.exists():
        raise FileNotFoundError(f"{_PACKAGE}: the converted data are missing ({folder}). Run "
                                "scripts/checks/convert_pickles/run_cell_to_pack.sh once (it unpickles in a throwaway venv).")
    return folder


def _paths() -> dict[str, tuple[str, object]]:
    """unit -> (kind, path prefix of its two Parquet files)."""
    root = _converted()
    out = {unit: ("field pack", root / unit / f"{unit}.pkl") for unit in FIELD}
    for group in LAB:
        for parquet in sorted((root / group).rglob("*.pkl.constant_metadata.parquet")):
            stem = parquet.name.removesuffix(".pkl.constant_metadata.parquet")
            kind = "laboratory pack" if parquet.parent.name == "pack" else "laboratory cell"
            out[f"{group}/{stem}"] = (kind, parquet.with_name(f"{stem}.pkl"))
    return out


def matrix(unit: str, which: str = "pack_capacity") -> pd.DataFrame:
    """A field pack's CSV from its zip, as released: ``capacity`` and ``SOC`` (EFC and Col0 to Col415, one column per
    cell in series) or ``pack_capacity`` (EFC and Pack_Capacity)."""
    if unit not in FIELD:
        raise ValueError(f"{_PACKAGE}: matrices exist for the field packs only: {FIELD[0]} to {FIELD[-1]}")
    number = unit.split("#")[1]
    with zipfile.ZipFile(directory(_PACKAGE) / f"{unit}.zip") as archive, archive.open(f"{MATRICES[which]}_#{number}.csv") as handle:
        return pd.read_csv(handle)


def systems() -> pd.DataFrame:
    """One row per unit: kind (field pack, laboratory pack or laboratory cell), group, cycles, rated capacity (Ah),
    first and last SOH. Field packs also get cells in series, last EFC and a derived rated energy."""
    rows = []
    for unit, (kind, prefix) in _paths().items():
        meta = pd.read_parquet(f"{prefix}.constant_metadata.parquet")
        row = {"unit": unit, "kind": kind, "group": unit.split("/")[0] if "/" in unit else unit, "cycles": len(meta),
               "rated_ah": meta["rate_capacity (Ah)"].iloc[0], "soh_first": meta["SOH"].iloc[0], "soh_last": meta["SOH"].iloc[-1]}
        if kind == "field pack":
            capacity = matrix(unit, "pack_capacity")
            import pyarrow.parquet as pq
            names = pq.read_schema(f"{prefix}.timeseries_data.parquet").names
            cells = sum(bool(re.fullmatch(r"V\d+", n)) for n in names)
            row.update({"cells_in_series": cells, "efc_last": float(capacity["EFC"].max()),
                        "rated_kwh": float(row["rated_ah"]) * cells * CELL_NOMINAL_V / 1000})
        rows.append(row)
    return pd.DataFrame(rows)


def load(unit: str, part: str = "timeseries", columns=None, clean=False):
    """One unit's converted data as released: ``timeseries`` (one row per sample, ``item`` is the cycle's list
    position) or ``metadata`` (one row per cycle). ``columns`` reads only those columns. ``clean`` masks nothing."""
    paths = _paths()
    if unit not in paths:
        raise ValueError(f"{_PACKAGE}: unknown unit {unit!r}; systems() lists {len(paths)} units")
    key = {"timeseries": "timeseries_data", "metadata": "constant_metadata"}[part]
    frame = pd.read_parquet(f"{paths[unit][1]}.{key}.parquet", columns=None if columns is None else ["item", *columns])
    return finish(frame, _PACKAGE, clean, 0, unit=unit, part=part)


def cell_columns(frame: pd.DataFrame) -> list[str]:
    """The per-cell voltage columns (V1, V2, ...) of a pack's time series."""
    return [c for c in frame.columns if re.fullmatch(r"V\d+", c)]
