"""Shared reader for the two Bilfinger (TUM) vehicle-level DVA/ICA releases on mediaTUM."""
from __future__ import annotations

import io
import zipfile
from pathlib import PurePosixPath

import pandas as pd

from fielddata.loaders._base import check_unit, directory, finish, mask_values


def _kind(member: str) -> str:
    parts = PurePosixPath(member).parts
    for kind in ("halfcell", "cell", "raw"):
        if kind in parts:
            return {"raw": "vehicle raw log", "cell": "laboratory cell", "halfcell": "laboratory half-cell"}[kind]
    return "vehicle"


def vehicle(member: str):
    if not _kind(member).startswith("vehicle"):
        return None
    base = PurePosixPath(member).name
    if base.startswith("Cupra_"):
        return "Cupra " + base.split("_")[1]
    if base.startswith("Tesla"):
        return "Tesla Model 3 SR+"
    if base.startswith("VW_ID3") or base.startswith("VW_FTM"):
        return "VW ID.3"
    return None


def members(package: str) -> dict[str, zipfile.ZipInfo]:
    with zipfile.ZipFile(directory(package) / "data.zip") as z:
        return {PurePosixPath(i.filename).stem: i for i in z.infolist() if i.filename.endswith((".pkl", ".feather"))}


def systems(package: str) -> pd.DataFrame:
    rows = []
    for stem, info in sorted(members(package).items()):
        rows.append({"unit": stem, "kind": _kind(info.filename), "vehicle": vehicle(info.filename),
                     "format": PurePosixPath(info.filename).suffix[1:], "member": info.filename, "bytes": info.file_size})
    return pd.DataFrame(rows)


def load(package: str, unit, clean=False, rules=None) -> pd.DataFrame:
    """Read one recording (pandas pickle or feather) as released.

    With clean=False the frame is returned unchanged. With clean=True, single values matching `rules`
    ({column: predicate}, given by the release module) are set to NaN; rows are never dropped and
    the count is in `frame.attrs["masked_value_count"]`. Only bilfinger2024 holds pickles; unpickling
    runs code, so load only archives whose checksum `fielddata.verify` has confirmed.
    """
    table = members(package)
    name = check_unit(unit, list(table), package)
    info = table[name]
    with zipfile.ZipFile(directory(package) / "data.zip") as z:
        data = z.read(info.filename)
    frame = pd.read_feather(io.BytesIO(data)) if info.filename.endswith(".feather") else pd.read_pickle(io.BytesIO(data))
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame(frame)
    masked = mask_values(frame, rules) if (clean and rules) else 0
    return finish(frame, package, clean, masked, unit=name, member=info.filename, kind=_kind(info.filename), vehicle=vehicle(info.filename))
