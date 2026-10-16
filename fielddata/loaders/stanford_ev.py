"""Loader for the Stanford passenger EV BMS release (Lanubile, Marini, Bosoni, Colombo, Paxton and Onori, Stanford Digital
Repository 10.25740/yx490wc6642, CC BY-NC-ND 4.0). Candidate package: not in the totals. No paper yet.

License: CC BY-NC-ND 4.0. Maintainer's decision (2026-10-13): this loader reads the original files only. No converted or
derived data files from this release go into the repository or the export, and it gets no preview image.

One passenger EV (the record does not name it; it is not taken to be the Audi e-tron of the group's companion paper,
arXiv 2603.29107, see stanford_ev_SCHEMA.md). Field data are one MATLAB v5 file per charging or driving session,
``Field Dataset/<Charging|Driving>/<yyyymmdd_hhmmss>.mat``, from 2021-09-21 to 2025-04-09. Each signal is a struct with
``data`` and ``t`` (``time`` for T_pack_bms), t in seconds from the session start, each signal at its own rate.
Laboratory data are one file per module (``Module_NN.mat``) in two campaigns. Reading needs scipy. No value is changed.

``systems()`` has the vehicle, ``sessions()`` the field sessions, ``lab_files()`` the laboratory files,
``load(session, signal)`` one signal of one session or several, ``mileage(session)`` the session's odometer value, and
``load_lab(path)`` one laboratory file. See ``stanford_ev_SCHEMA.md``.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from fielddata.loaders._base import concat, directory, finish

_PACKAGE = "stanford_ev"
VEHICLE = "EV1"
SIGNALS = ["I_pack_bms", "V_pack_bms", "SOC_pack_bms", "V_cell_bms", "T_module_bms", "T_pack_bms"]
LICENSE_NOTE = "CC BY-NC-ND 4.0: read the original files only; do not publish converted or derived data files"


def _loadmat(path, names=None):
    try:
        from scipy.io import loadmat
    except ImportError as error:
        raise ImportError("stanford_ev: reading MATLAB files needs scipy (python -m pip install scipy)") from error
    return loadmat(str(path), squeeze_me=True, struct_as_record=False, variable_names=names)


def _field_files() -> dict[str, object]:
    root = directory(_PACKAGE) / "Field Dataset"
    return {p.stem: p for kind in ("Charging", "Driving") for p in sorted((root / kind).glob("*.mat"))}


def sessions() -> pd.DataFrame:
    """One row per field session: name (yyyymmdd_hhmmss), kind (Charging or Driving), start time from the name, bytes."""
    rows = []
    for name, path in _field_files().items():
        rows.append({"session": name, "kind": path.parent.name, "start": pd.to_datetime(name, format="%Y%m%d_%H%M%S"),
                     "file": f"Field Dataset/{path.parent.name}/{path.name}", "bytes": path.stat().st_size})
    return pd.DataFrame(rows).sort_values("start").reset_index(drop=True)


def lab_files() -> pd.DataFrame:
    """One row per laboratory file: campaign, test folder, module and bytes (five files are empty, as released)."""
    root = directory(_PACKAGE) / "Laboratory Dataset"
    rows = []
    for path in sorted(root.rglob("*.mat")):
        parts = path.relative_to(root).parts
        rows.append({"path": path.relative_to(root).as_posix(), "campaign": parts[0], "test": "/".join(parts[1:-1]),
                     "module": int(re.search(r"\d+", path.stem).group()), "bytes": path.stat().st_size})
    return pd.DataFrame(rows)


def systems() -> pd.DataFrame:
    """The one vehicle: sessions by kind and first and last session start."""
    s = sessions()
    return pd.DataFrame([{"unit": VEHICLE, "vehicle": "passenger EV (not named in the record)", "license": LICENSE_NOTE,
                          "charging_sessions": int((s["kind"] == "Charging").sum()), "driving_sessions": int((s["kind"] == "Driving").sum()),
                          "first": s["start"].min(), "last": s["start"].max()}])


def _signal_frame(struct, signal: str) -> pd.DataFrame:
    time = np.atleast_1d(getattr(struct, "t" if "t" in struct._fieldnames else "time"))
    data = np.asarray(getattr(struct, "data"))
    if data.ndim == 1 and time.size and data.size != time.size and data.size % time.size == 0:
        data = data.reshape(time.size, -1)  # a one-row multi-column signal, flattened by squeeze_me
    if data.ndim == 1:
        frame = pd.DataFrame({signal: data})
    else:
        frame = pd.DataFrame(data, columns=[f"{signal}_{i + 1}" for i in range(data.shape[1])])
    frame.insert(0, "t", time)
    return frame


def load(session=None, signal: str = "V_pack_bms", clean=False):
    """One signal (see SIGNALS) of one session or several, as released: ``t`` (s from the session start) and the data
    (one column, or one per cell or sensor), with a ``session`` column. ``clean`` masks nothing."""
    if signal not in SIGNALS:
        raise ValueError(f"{_PACKAGE}: signal must be one of {SIGNALS}")
    files = _field_files()
    names = list(files) if session is None else ([session] if isinstance(session, str) else list(session))
    frames = []
    for name in names:
        if name not in files:
            raise ValueError(f"{_PACKAGE}: unknown session {name!r}; sessions() lists {len(files)}")
        struct = _loadmat(files[name], [signal]).get(signal)
        frame = _signal_frame(struct, signal) if struct is not None else pd.DataFrame(columns=["t", signal])
        frame.insert(0, "session", name)
        frames.append(finish(frame, _PACKAGE, clean, 0, session=name, signal=signal))
    return concat(frames, _PACKAGE, clean, signal=signal)


def mileage(session: str) -> int:
    """The session's Mileage_bms value as released (units not stated, likely km)."""
    value = float(_loadmat(_field_files()[session], ["Mileage_bms"])["Mileage_bms"])
    return None if np.isnan(value) else int(value)  # some sessions release NaN (see stanford_ev_SCHEMA.md)


def load_lab(path: str) -> pd.DataFrame:
    """One laboratory file (a path from lab_files()) as released: time_lab, I_module_lab, V_module_lab, V_Cell_lab
    (3 cells) and T_module_lab (3 sensors). Empty files give an empty frame."""
    full = directory(_PACKAGE) / "Laboratory Dataset" / path
    if full.stat().st_size == 0:
        return finish(pd.DataFrame(), _PACKAGE, False, 0, path=path)
    content = {k: np.asarray(v) for k, v in _loadmat(full).items() if not k.startswith("__")}
    columns = {}
    for key, value in content.items():
        if value.ndim == 2 and value.shape[1] > 1:
            for i in range(value.shape[1]):
                columns[f"{key}_{i + 1}"] = value[:, i]
        else:
            columns[key] = value.ravel()
    return finish(pd.DataFrame(columns), _PACKAGE, False, 0, path=path)
