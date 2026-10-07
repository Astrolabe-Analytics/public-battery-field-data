"""Small helpers shared by the package loaders."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from fielddata.config import data_root
from fielddata.registry import metadata


def directory(package: str) -> Path:
    """Return the package's released data directory."""
    return data_root() / metadata(package)["data_directory"]


def as_list(unit, all_units):
    """Normalise a unit argument (None, one id, or a list) to a list of ids."""
    if unit is None:
        return list(all_units)
    if isinstance(unit, (str, int)):
        return [unit]
    return list(unit)


def check_unit(unit, all_units, package: str):
    units = [str(u) for u in all_units]
    if str(unit) not in units:
        raise ValueError(f"{package}: unknown unit {unit!r}; systems() lists {len(units)} units")
    return str(unit)


def mask_values(frame: pd.DataFrame, rules: dict) -> int:
    """Mask single values matching a rule {column: predicate}; never drops rows. Returns the count."""
    count = 0
    for column, predicate in rules.items():
        if column not in frame.columns:
            continue
        hit = predicate(frame[column])
        n = int(hit.sum())
        if n:
            frame[column] = frame[column].astype(float).mask(hit)
            count += n
    return count


def finish(frame: pd.DataFrame, package: str, clean: bool, masked: int, **extra) -> pd.DataFrame:
    frame.attrs = {"package": package, "n_rows": len(frame), "clean": clean, "masked_value_count": masked, **extra}
    return frame


def concat(frames, package: str, clean: bool, **extra) -> pd.DataFrame:
    out = pd.concat(frames, axis=0, sort=False) if len(frames) > 1 else frames[0]
    masked = sum(f.attrs.get("masked_value_count", 0) for f in frames)
    return finish(out, package, clean, masked, **extra)
