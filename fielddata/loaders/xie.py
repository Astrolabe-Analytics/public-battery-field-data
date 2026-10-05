"""Loader for the Xie et al. swap-station device data (Zenodo 18328701, DataForPub.rar)."""
from __future__ import annotations

import io
from pathlib import PurePosixPath

import pandas as pd

from fielddata.loaders._base import as_list, concat, directory, finish

_PACKAGE = "xie"
_ARCHIVE = "DataForPub.rar"
_DATA = "predefinedDataset/data/"
_PROCESSED = "predefinedDataset/processedData/"


def _read(members):
    """Read the named RAR members (streamed with libarchive) into {member: bytes}."""
    import libarchive
    wanted, found = set(members), {}
    with libarchive.file_reader(str(directory(_PACKAGE) / _ARCHIVE)) as archive:
        for entry in archive:
            if entry.pathname in wanted:
                found[entry.pathname] = b"".join(entry.get_blocks())
                if len(found) == len(wanted):
                    break
    return found


def members(prefix=""):
    """Sorted names of the archive members whose path starts with ``prefix`` (all members by default)."""
    import libarchive
    with libarchive.file_reader(str(directory(_PACKAGE) / _ARCHIVE)) as archive:
        return sorted(e.pathname for e in archive if e.pathname.startswith(prefix))


def _device_members():
    return [n for n in members(_DATA) if n.endswith(".csv")]


def device_labels():
    """The released device-level table (predefined_device_records.csv): label and screening features.

    Label codes, from the authors' code (dataProcess.ipynb, "Abnormal Conditions"): 1 micro-short circuit,
    2 low capacity, 3 high SOC, 4 low SOC, 5 normal. The authors' dataReorganization.ipynb writes one row per
    fault class of a device, so the 291 rows cover the 271 device files: 18 devices with two or three fault
    classes have one row per class, with the same features. Every row's file is released.
    """
    data = _read([_PROCESSED + "predefined_device_records.csv"])
    return pd.read_csv(io.BytesIO(next(iter(data.values()))))


def cell_labels():
    """The released cell-level table (predefined_device_cell_level.csv): one row per cell and label.

    ``cell_label`` uses the codes of :func:`device_labels`. A cell given two fault classes has two rows with the
    same features (authors' dataReorganization.ipynb). Labels are the authors' engineering judgment or
    laboratory tests of recalled packs on a fault-enriched pilot set (paper p. 3).
    """
    data = _read([_PROCESSED + "predefined_device_cell_level.csv"])
    return pd.read_csv(io.BytesIO(next(iter(data.values()))))


def systems():
    """One row per released device file (271).

    ``device_label`` is the code on the device's first row in the released device table; ``fault_codes`` lists
    every code the table gives the device (for example ``"1,3"``), since 18 devices carry more than one fault
    class. Codes: 1 micro-short circuit, 2 low capacity, 3 high SOC, 4 low SOC, 5 normal (authors' code).
    """
    units = pd.DataFrame({"unit": [PurePosixPath(m).stem for m in _device_members()]})
    labels = device_labels().assign(unit=lambda t: t["filename"].str.removesuffix(".csv"))[["unit", "device_label"]]
    codes = labels.groupby("unit")["device_label"].agg(lambda s: ",".join(str(c) for c in sorted(set(s)))).rename("fault_codes")
    return units.merge(labels.drop_duplicates("unit"), on="unit", how="left").merge(codes, on="unit", how="left")


def load(unit, clean=False):
    """Load one or more devices, indexed by ``dateTime`` (epoch milliseconds, parsed to UTC).

    Columns as released: totalCurrent, batCoreTempCount, batCoreVoltage1..20 (cell voltages, mV per paper
    Table 1), batCoreTemp1..5. No source names the current or temperature units or the current sign; A and
    degrees C are inferred from value ranges and the sign from the data (see the schema note). The time zone is
    not stated; epoch milliseconds are parsed as UTC. Rows are the cloud records of a selective-reporting
    protocol, so sampling is irregular (paper p. 3). Devices have 16 to 20 cells; unused voltage columns are
    empty. ``clean=True`` masks exact-zero cell voltages.
    """
    names = [str(u) for u in as_list(unit, [])]
    data = _read([f"{_DATA}{n}.csv" for n in names])
    missing = [n for n in names if f"{_DATA}{n}.csv" not in data]
    if missing:
        raise ValueError(f"{_PACKAGE}: unknown unit(s) {missing}")
    frames = []
    for n in names:
        frame = pd.read_csv(io.BytesIO(data[f"{_DATA}{n}.csv"]))
        frame["dateTime"] = pd.to_datetime(pd.to_numeric(frame["dateTime"], errors="coerce"), unit="ms", utc=True)
        masked = 0
        if clean:
            cells = [c for c in frame.columns if c.startswith("batCoreVoltage")]
            zero = frame[cells] == 0
            masked = int(zero.to_numpy().sum())
            frame[cells] = frame[cells].mask(zero)
        frame["unit"] = n
        frames.append(finish(frame.set_index("dateTime").sort_index(kind="stable"), _PACKAGE, clean, masked, unit=n))
    return concat(frames, _PACKAGE, clean)
