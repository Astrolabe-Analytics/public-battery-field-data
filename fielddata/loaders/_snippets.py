"""Shared reader for the charging-snippet releases zhang2023 and evbattery (tar.gz of torch pickles).

Each snippet is one pickle holding a (128, 8) array and a metadata dict (car, charge_segment, label,
mileage, and for evbattery capacity). Pickles are read with the torch-free reader in fielddata._io.
A tar.gz can only be read front to back, so loading one vehicle streams its whole archive.
"""
from __future__ import annotations

import collections
import io
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd

from fielddata._io import torchfree
from fielddata.loaders._base import check_unit, concat, directory, finish

# Column order of the snippet arrays: the column.pkl shipped in the zhang2023 archives; evbattery ships none,
# and its released code (DyAD/train.py, args.columns) uses the same order.
COLUMNS = ["volt", "current", "soc", "max_single_volt", "min_single_volt", "max_temp", "min_temp", "timestamp"]


def index_path(package: str) -> Path:
    return Path(__file__).with_name(f"{package.replace('-', '_')}_index.csv")


def archives(package: str):
    return sorted(p.name for p in directory(package).glob("*.tar.gz"))


def build_index(package: str, archive: str) -> pd.DataFrame:
    """Scan one archive: per car, its label (from the label CSV) and snippet count. Updates the committed index."""
    counts, labels = collections.Counter(), {}
    with tarfile.open(directory(package) / archive, "r:gz") as tar:
        for member in tar:
            if not member.isfile():
                continue
            raw = tar.extractfile(member).read()
            if member.name.endswith(".csv") and "/label/" in member.name:
                table = pd.read_csv(io.BytesIO(raw))
                labels.update(dict(zip(table["car"].astype(int), table["label"])))
            elif member.name.endswith(".pkl") and not member.name.endswith("column.pkl"):
                loaded = torchfree.load(raw)
                if isinstance(loaded, tuple) and len(loaded) == 2 and isinstance(loaded[1], dict):
                    counts[int(loaded[1]["car"])] += 1
    stem = archive.removesuffix(".tar.gz")
    rows = [{"unit": f"{stem}:{car}", "archive": archive, "car": car, "label": labels.get(car), "snippets": counts.get(car, 0)}
            for car in sorted(set(labels) | set(counts))]
    new = pd.DataFrame(rows)
    path = index_path(package)
    if path.is_file():
        old = pd.read_csv(path)
        new = pd.concat([old[old["archive"] != archive], new]).sort_values(["archive", "car"])
    new.to_csv(path, index=False, lineterminator="\n")
    return new


def systems(package: str) -> pd.DataFrame:
    return pd.read_csv(index_path(package))


def iter_snippets(package: str, archive: str):
    """Yield (member name, array, metadata) for every snippet in one archive, in archive order."""
    with tarfile.open(directory(package) / archive, "r:gz") as tar:
        for member in tar:
            if member.isfile() and member.name.endswith(".pkl") and not member.name.endswith("column.pkl"):
                loaded = torchfree.load(tar.extractfile(member).read())
                if isinstance(loaded, tuple) and len(loaded) == 2 and isinstance(loaded[1], dict):
                    yield member.name, np.asarray(loaded[0]), dict(loaded[1])


def load(package: str, unit, clean=False) -> pd.DataFrame:
    """Load every snippet of one vehicle ("<archive stem>:<car>") as one long table, 128 rows per snippet.

    Columns: the eight array columns (see COLUMNS; ``timestamp`` is the snippet's own relative clock in
    seconds, not a calendar time), plus snippet, charge_segment, label, mileage (and capacity where present).
    """
    table = systems(package)
    name = check_unit(unit, table["unit"], package)
    row = table[table["unit"] == name].iloc[0]
    frames = []
    for member, array, meta in iter_snippets(package, row["archive"]):
        if int(meta["car"]) != int(row["car"]):
            continue
        frame = pd.DataFrame(array.astype(float), columns=COLUMNS[: array.shape[1]])
        frame["snippet"] = member.rsplit("/", 1)[-1].removesuffix(".pkl")
        for key, value in meta.items():
            if key != "car":
                frame[key] = value
        frames.append(finish(frame, package, clean, 0))
    if not frames:
        raise ValueError(f"{package}: no snippets found for {name}")
    out = concat(frames, package, clean, unit=name, snippets=len(frames))
    out["unit"] = name
    return out.reset_index(drop=True)
