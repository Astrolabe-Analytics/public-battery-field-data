"""Loader for the PNNL/EPRI grid-scale BESS release (Crawford and Thompson, Zenodo 10.5281/zenodo.22947521,
CC BY 4.0). Candidate package: not in the collection's totals.

The release holds 12 grid-scale battery systems, one ``<system>.feather`` per system, each written by the authors'
``write_release`` (``_common.R``) from that system's script (``<system>.R``). A file is long: one row per
(``HoursElapsed``, ``Meter``), with the 20 columns of ``RELEASE_COLS``. Values are normalised by the authors before
release (``_common.R``, ``write_release``): power and reactive power are divided by the system's rated energy
(so they are C-rates, 1/h), current is divided by the system's ampere-hour basis (a C-rate), voltage is per cell
where a series count is configured, SOC is a fraction, and time is elapsed hours from the first record. The ratings
used are not released. The loader reads each file with pyarrow and changes no value.

``systems()`` lists the 12 units, ``load(unit, meter=None)`` returns one system (or a list) as released, and
``meters(unit)`` lists a system's meters. See ``pnnl_epri_SCHEMA.md``.
"""
from __future__ import annotations

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as feather

from fielddata.loaders._base import as_list, check_unit, concat, directory, finish

_PACKAGE = "pnnl_epri"
COLUMNS = ["HoursElapsed", "DayNumber", "Meter", "Power", "RequestedPower", "ReactivePower", "RequestedReactivePower",
           "Voltage", "VoltageMax", "VoltageMin", "VoltageAvg", "Current", "SOC",
           "TempMax", "TempMin", "TempAvg", "TempAmbient", "QualityFlag", "CycleIndex", "Use"]

# system: (programme, chemistry, source). The release holds no chemistry per system; the record names three families
# (LFP, NMC, vanadium redox flow). Chemistry here is as stated in the alias table of Crawford's DOE peer-review poster
# (2026-05, https://doepeerreview.sandia.gov/app/uploads/sites/82/2026/05/Crawford_Alasdair_Analytics.pdf); which alias is
# which system is matched in reports/candidates/pnnl_epri/pnnl_epri_ratings.csv and pnnl_epri_SCHEMA.md.
_POSTER = "Crawford 2026 DOE peer-review poster, alias table"
SYSTEMS = {
    "Avista": ("WACEF", "vanadium flow", f"{_POSTER} (WADOC Flow 1)"),
    "ENW": ("WACEF", "LFP", f"{_POSTER} (WADOC Li-Ion 4)"),
    "EPRI_LFP1": ("EPRI", "LFP", "system name; poster (EPRI Li-Ion 3)"),
    "EPRI_LFP2": ("EPRI", "LFP", "system name; poster (EPRI Li-Ion 5)"),
    "EPRI_LFP3": ("EPRI", "LFP", "system name; poster (EPRI Li-Ion 4)"),
    "EPRI_NMC1": ("EPRI", "NMC", "system name; poster (EPRI Li-Ion 2)"),
    "EPRI_NMC2": ("EPRI", "NMC", "system name; poster (EPRI Li-Ion 1)"),
    "EPRI_VRF1": ("EPRI", "vanadium flow", "system name; poster (EPRI Flow 1)"),
    "OPALCO": ("WACEF", "LFP", f"{_POSTER} (WADOC Li-Ion 3)"),
    "PSE": ("WACEF", "LFP", f"{_POSTER} (WADOC Li-Ion 2)"),
    "SnoPUDMESA1": ("WACEF", "LMO/NMC", f"{_POSTER} (WADOC Li-Ion 1); bank 1a LMO, bank 1b NMC (PNNL-27237)"),
    "SnoPUDMESA2": ("WACEF", "vanadium flow", f"{_POSTER} (WADOC Flow 2)"),
}


def _path(unit: str):
    return directory(_PACKAGE) / f"{unit}.feather"


def systems() -> pd.DataFrame:
    """One row per system (one per .feather file): programme, chemistry, file and size."""
    rows = []
    for unit, (programme, chemistry, source) in SYSTEMS.items():
        path = _path(unit)
        rows.append({"unit": unit, "programme": programme, "chemistry": chemistry, "chemistry_source": source,
                     "cell_count": "not applicable" if chemistry == "vanadium flow" else "not released",
                     "file": path.name, "bytes": path.stat().st_size})
    return pd.DataFrame(rows)


def meters(unit: str) -> list[str]:
    """The meters (``Meter`` values) of one system, in released order of first appearance."""
    unit = check_unit(unit, SYSTEMS, _PACKAGE)
    column = feather.read_table(_path(unit), columns=["Meter"]).column("Meter").to_pandas()
    return list(pd.unique(column))


def load(unit=None, meter=None, columns=None, clean=False):
    """Load one system (or a list of systems) as released: one row per (HoursElapsed, Meter), no value changed.

    ``meter`` keeps only the named meter(s) (for example ``"PGCP"`` or ``["PDC1", "PDC2"]``). ``columns`` reads only
    those columns (``HoursElapsed`` and ``Meter`` are always read). ``clean`` is accepted for the common interface
    and masks nothing: the authors already removed out-of-range values before release (``<system>.R``), and no
    sentinel code remains (see ``pnnl_epri_SCHEMA.md``).
    """
    units = as_list(unit, SYSTEMS)
    wanted = None if columns is None else list(dict.fromkeys(["HoursElapsed", "Meter", *columns]))
    meter_list = None if meter is None else as_list(meter, [])
    frames = []
    for u in units:
        u = check_unit(u, SYSTEMS, _PACKAGE)
        table = feather.read_table(_path(u), columns=wanted)
        if meter_list is not None:
            meter_type = table.schema.field("Meter").type
            table = table.filter(pc.is_in(table.column("Meter"), value_set=pa.array(meter_list, type=meter_type)))
        frame = table.to_pandas()
        if len(units) > 1:
            frame.insert(0, "unit", u)
        frames.append(finish(frame, _PACKAGE, clean, 0, unit=u))
    return concat(frames, _PACKAGE, clean)
