"""Loader for the Tongji EV rest-period release (Tao, Zhu, Li, Jiang, Chang, Dai and Wei, Zenodo
10.5281/zenodo.16868546, CC BY 4.0), the data of eTransportation 26, 100471 (2025). Candidate package: not in the totals.

``data.zip`` holds raw charge and rest segments of four field EVs (``data/raw_test/``: LFP01, NMC01_Car01,
NMC01_Car02, NMC02) as pickled pandas files, and derived feature workbooks for more vehicles and for laboratory cells
(``data/data_train/``, ``data/data_test/``). Unpickling can run code, so this loader never unpickles. It reads the
Parquet copies made once by ``scripts/checks/convert_pickles/run_tongji.sh`` in a throwaway environment (maintainer's
decision, 2026-10-13), kept in ``converted/`` beside the release's ``data/`` folder, outside git and the export. The
conversion changes no value. Its manifest (input and output SHA-256) is
reports/candidates/tongji_rest/pickle_conversion.csv. The feature workbooks are read from the zip.

``systems()`` lists field vehicles, feature-only vehicles and laboratory cells, ``segments(unit)`` a field vehicle's
segment files, ``load(unit, kind="charge"|"rest")`` its segments as released, and ``features(name)`` one feature
workbook. See ``tongji_rest_SCHEMA.md``.
"""
from __future__ import annotations

import io
import re
import zipfile

import pandas as pd

from fielddata.loaders._base import as_list, check_unit, concat, directory, finish

_PACKAGE = "tongji_rest"
FIELD = ["LFP01", "NMC01_Car01", "NMC01_Car02", "NMC02"]
KINDS = {"charge": "charge_segment", "rest": "rest_segment"}


def _zip() -> zipfile.ZipFile:
    return zipfile.ZipFile(directory(_PACKAGE) / "data.zip")


def _converted():
    folder = directory(_PACKAGE).parent / "converted" / "data" / "raw_test"
    if not folder.exists():
        raise FileNotFoundError(f"{_PACKAGE}: the converted segments are missing ({folder}). Run "
                                "scripts/checks/convert_pickles/run_tongji.sh once (it unpickles in a throwaway venv).")
    return folder


def _feature_files() -> list[str]:
    with _zip() as archive:
        return sorted(m.filename for m in archive.infolist() if m.filename.endswith("_feature.xlsx"))


def _feature_unit(path: str) -> str:
    return re.sub(r"_(fast|slow)_feature\.xlsx$", "", path.rsplit("/", 1)[-1])


def segments(unit: str, kind: str = "charge") -> list:
    """The converted segment files of one field vehicle, in name order."""
    unit = check_unit(unit, FIELD, _PACKAGE)
    folder = _converted() / f"{KINDS[kind]}_{unit}"
    return sorted(folder.glob("*.parquet"), key=lambda p: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", p.name)])


def systems() -> pd.DataFrame:
    """Field vehicles (raw segments), feature-only vehicles and laboratory cells, with what the release holds for each."""
    rows = []
    for unit in FIELD:
        charge, rest = segments(unit, "charge"), segments(unit, "rest")
        times = pd.concat([pd.read_parquet(p, columns=["reqDate"])["reqDate"] for p in charge + rest])
        rows.append({"unit": unit, "kind": "field vehicle", "chemistry": unit[:3], "charge_segments": len(charge),
                     "rest_segments": len(rest), "first": times.min(), "last": times.max(), "feature_files": 0})
    features = {}
    for path in _feature_files():
        features.setdefault(_feature_unit(path), []).append(path)
    for unit, paths in sorted(features.items()):
        if unit in FIELD:
            rows[FIELD.index(unit)]["feature_files"] += len(paths)
            continue
        kind = "laboratory cell" if unit.startswith("Lab") else "feature only"
        rows.append({"unit": unit, "kind": kind, "chemistry": None if kind == "laboratory cell" else unit[:3],
                     "charge_segments": 0, "rest_segments": 0, "first": pd.NaT, "last": pd.NaT, "feature_files": len(paths)})
    return pd.DataFrame(rows)


def load(unit=None, kind: str = "charge", clean=False):
    """Segments of one field vehicle (or several) as released, one row per sample, with a ``segment`` column.

    The kept pandas index of each segment is the ``index`` column. ``clean`` masks nothing.
    """
    if kind not in KINDS:
        raise ValueError(f"{_PACKAGE}: kind must be one of {list(KINDS)}")
    units = as_list(unit, FIELD)
    frames = []
    for u in units:
        parts = []
        for path in segments(u, kind):
            part = pd.read_parquet(path).reset_index()
            part.insert(0, "segment", path.name.removesuffix(".pkl.parquet"))
            parts.append(part)
        frame = pd.concat(parts, ignore_index=True)
        if len(units) > 1:
            frame.insert(0, "unit", u)
        frames.append(finish(frame, _PACKAGE, clean, 0, unit=u, kind=kind))
    return concat(frames, _PACKAGE, clean)


def features(name: str) -> pd.DataFrame:
    """One feature workbook as released, by its file name without folder (for example ``LFP01_01_fast_feature.xlsx``)."""
    with _zip() as archive:
        match = [m for m in archive.namelist() if m.endswith("/" + name)]
        if not match:
            raise ValueError(f"{_PACKAGE}: no feature workbook named {name!r}")
        return pd.read_excel(io.BytesIO(archive.read(match[0])), engine="openpyxl")
