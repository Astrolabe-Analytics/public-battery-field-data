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
    """The vehicle a recording belongs to, named the same across bilfinger2024, 2025 and 2026.

    bilfinger2025 adds vehicles of other models and a second VW ID.3. Its paper (arXiv 2508.15517, p. 13) has two
    VW ID.3s, the second "has a defective cell" (the release's GB file), two Porsche Taycans "from different sources"
    and two Tesla Model Y. Their file names carry a site code (FTM, AMS, MI, TW, GB), which tells the vehicles apart.
    """
    if not _kind(member).startswith("vehicle"):
        return None
    base = PurePosixPath(member).name
    if base.startswith("Cupra_Born_"):  # bilfinger2025 names: Cupra_Born_<plate>_...
        return "Cupra " + base.split("_")[2]
    if base.startswith("Cupra_"):
        return "Cupra " + base.split("_")[1]
    if base.startswith("Porsche_Taycan"):
        return "Porsche Taycan (" + ("AMS" if "_AMS_" in base else "FTM") + ")"
    if base.startswith("Tesla_Model_Y"):
        return "Tesla Model Y (" + ("MI" if "_MI_" in base else "TW") + ")"
    if base.startswith("Tesla"):
        return "Tesla Model 3 SR+"
    if base.startswith("VW_ID3") and "_GB_" in base:
        return "VW ID.3 (GB, defective cell)"
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
