"""Loader for the in-service EV fault snapshots (Li, J., Che, Onori, Li, W. and Hu, Zenodo 10.5281/zenodo.23980122,
CC BY 4.0), data and code for "Cross-modal topology decodes battery faults from sparse voltage snapshots" (Energy
Storage Materials 2026, doi:10.1016/j.ensm.2026.105638; arXiv 2608.10825). Admitted in v1.3 (2026-11-24).
Kept separate from the ``li2026`` package (a different release and group).

One RAR5 archive, ``Data & Code.rar``, holding ``Data & Code/Data/<n>.csv`` (one voltage snapshot each: columns
``V 1`` to ``V 14``, cell voltages in mV, 50 rows), ``Data & Code/Label/<n>.csv`` (that snapshot's labels), the
readme, the authors' model code (``core_model.py``, model structure only) and the source data of the paper's figures.

Label files: the first line is ``0``, written without a decimal point, and the next 14 lines are ``0.0`` to ``4.0``.
The first line is the column header that pandas writes for a column named 0, not a value: ``labels()`` returns the 14
values as cells 1 to 14 (``V 1`` to ``V 14``) and keeps the header in ``header``. Codes: 0 fault-free, 1 to 4 the four
fault types in the order the readme and paper list them (excessive inconsistency, abnormal self-discharge, abnormal
capacity degradation, internal short circuit). Neither source numbers them; see ``li2026_evfault_SCHEMA.md``.

The archive is streamed with libarchive. On Windows set ``LIBARCHIVE`` to a libarchive DLL (as for ``xie``).
``clean`` masks nothing.
"""
from __future__ import annotations

import io
import re
from functools import lru_cache

import pandas as pd

from fielddata.loaders._base import directory, finish

_PACKAGE = "li2026_evfault"
_ARCHIVE = "Data & Code.rar"
_ROOT = "Data & Code/"
CELLS = [f"V {i}" for i in range(1, 15)]
# Order of the readme ("four fault type: excessive inconsistency (EI), abnormal self-discharge (ASD), abnormal capacity
# degradation (ACD), and internal short circuit (ISC)") and of the paper (p. 3; Fig. 3F lists FF, EI, ASD, ACD, ISC).
# The sources do not number them; scripts/checks/li2026_evfault_codes.py tests the order against the paper's source data.
CODES = {0: "FF", 1: "EI", 2: "ASD", 3: "ACD", 4: "ISC"}
NAMES = {"FF": "fault-free", "EI": "excessive inconsistency", "ASD": "abnormal self-discharge",
         "ACD": "abnormal capacity degradation", "ISC": "internal short circuit"}


def _archive():
    return directory(_PACKAGE) / _ARCHIVE


@lru_cache(maxsize=2)
def _members(path: str, prefix: str) -> dict[str, bytes]:
    import libarchive
    out = {}
    with libarchive.file_reader(path) as archive:
        for entry in archive:
            if entry.isfile and entry.pathname.startswith(prefix):
                out[entry.pathname] = b"".join(entry.get_blocks())
    return out


def members(prefix: str = "") -> dict[str, bytes]:
    """Archive members under ``Data & Code/<prefix>`` as {path: bytes} (for example ``readme.txt`` or ``Source data/``)."""
    return _members(str(_archive()), _ROOT + prefix)


def _window_ids() -> list[int]:
    names = members("Data/")
    return sorted(int(re.fullmatch(r".*/(\d+)\.csv", n).group(1)) for n in names)


def load(window=None, clean: bool = False) -> pd.DataFrame:
    """Voltage snapshots as released: one row per sample, ``window`` (the file number) and ``sample`` (0 to 49) added,
    ``V 1`` to ``V 14`` in mV unchanged. ``window`` may be one number, a list, or None for all."""
    data = members("Data/")
    wanted = _window_ids() if window is None else ([window] if isinstance(window, (int, str)) else list(window))
    frames = []
    for w in wanted:
        key = f"{_ROOT}Data/{int(w)}.csv"
        if key not in data:
            raise ValueError(f"{_PACKAGE}: unknown window {w!r}")
        frame = pd.read_csv(io.BytesIO(data[key]))
        frame.insert(0, "sample", range(len(frame)))
        frame.insert(0, "window", int(w))
        frames.append(frame)
    out = pd.concat(frames, ignore_index=True)
    return finish(out, _PACKAGE, clean, 0)


def labels(window=None) -> pd.DataFrame:
    """Per-cell labels as released: one row per window and cell (1 to 14), ``code`` (0 to 4 as in the file), ``label``
    (FF, EI, ASD, ACD or ISC, by the readme's order) and ``header``, the label file's first line."""
    files = members("Label/")
    ids = _window_ids() if window is None else ([window] if isinstance(window, (int, str)) else list(window))
    rows = []
    for w in ids:
        lines = files[f"{_ROOT}Label/{int(w)}.csv"].decode("utf-8").split()
        header, values = lines[0], [float(v) for v in lines[1:]]
        for cell, value in enumerate(values, start=1):
            rows.append({"window": int(w), "cell": cell, "code": value, "label": CODES.get(int(value)) if value == int(value) else None,
                         "header": header})
    return pd.DataFrame(rows)


def systems() -> pd.DataFrame:
    """One row per released snapshot window: samples, cells, labelled (non-zero) cells and their codes. The release has
    no vehicle identifiers, so windows cannot be grouped into the paper's 99 vehicles."""
    data = members("Data/")
    lab = labels()
    faulty = lab[lab["code"] != 0].groupby("window")
    rows = []
    for w in _window_ids():
        frame = pd.read_csv(io.BytesIO(data[f"{_ROOT}Data/{w}.csv"]))
        codes = faulty.get_group(w) if w in faulty.groups else None
        rows.append({"window": w, "samples": len(frame), "cells": frame.shape[1],
                     "faulty_cells": 0 if codes is None else len(codes),
                     "codes": "" if codes is None else ";".join(f"{c}:{int(k)}" for c, k in zip(codes["cell"], codes["code"]))})
    return pd.DataFrame(rows)
