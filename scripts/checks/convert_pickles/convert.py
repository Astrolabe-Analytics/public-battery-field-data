"""Convert pickled pandas files inside a release zip to Parquet, once, in a throwaway environment.

Maintainer's decision (2026-10-13): pickled pandas files (tongji_rest, cell_to_pack) are converted once in an isolated
throwaway environment (a separate venv or container, no network, not the project's environment). The converted copies
stay local, out of git and the export, and the conversion is recorded with checksums of inputs and outputs.

Unpickling can run code, so this script is meant to run only in that throwaway environment, never in the project's
.venv. It does not import fielddata. Before it opens any pickle it disables network connections for its own process
(socket connect and getaddrinfo raise), so code inside a pickle cannot reach the network. It reads the zip read-only
and writes only into --out.

The pickle is unpickled straight from the zip stream, and its bytes are hashed as they are read, so a large pickle
is never held twice in memory. For each member ending in .pkl (optionally only those under --prefix) it unpickles with
pandas.read_pickle. A list of dicts of DataFrames (cell_to_pack: one dict per cycle) becomes one Parquet per dict key,
<member>.<key>.parquet, with an "item" column for the list position, written item by item. Otherwise it turns a
Series into a one-column frame and a dict of Series, DataFrames and scalars into one frame on their shared index (a
scalar is repeated on every row), keeps the index (written by to_parquet), and writes <out>/<member path>.parquet.
No value is changed. It
appends one row per member to --manifest: member, input bytes and SHA-256, output file, bytes and SHA-256, object type,
rows, columns, and any error.

Run (inside the throwaway environment; see run_tongji.sh and README.md beside this file):
    python convert.py --zip <release zip> --out <folder> --manifest <csv> [--prefix data/raw_test/]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import socket
import sys
import zipfile
from pathlib import Path


def block_network() -> None:
    def refuse(*args, **kwargs):
        raise OSError("network disabled for pickle conversion")
    socket.socket.connect = refuse
    socket.socket.connect_ex = refuse
    socket.create_connection = refuse
    socket.getaddrinfo = refuse


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class HashingReader:
    """A file-like wrapper that hashes every byte read, so a large pickle is never held as raw bytes in memory."""

    def __init__(self, handle):
        self.handle, self.digest, self.size = handle, hashlib.sha256(), 0

    def _take(self, data):
        self.digest.update(data)
        self.size += len(data)
        return data

    def read(self, n=-1):
        return self._take(self.handle.read(n))

    def readline(self, n=-1):
        return self._take(self.handle.readline(n))

    def readinto(self, buffer):
        count = self.handle.readinto(buffer)
        self._take(bytes(memoryview(buffer)[:count]))
        return count

    def finish(self):
        while self.read(1 << 20):  # hash any bytes after the pickle's STOP
            pass

    def hexdigest(self):
        return self.digest.hexdigest()


def file_sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_items(pd, items, key, target):
    """Write items[i][key] (DataFrames) for every i to one Parquet file, item by item, with an "item" column.
    Columns are the union over items in first-seen order. An item without a column gets it as missing. A column that
    holds text (object dtype) in any item is written as text in every item, each value as str(value). No value is
    otherwise changed."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    columns, mixed = [], set()
    for item in items:
        for column, dtype in item[key].dtypes.items():
            if str(column) not in columns:
                columns.append(str(column))
            if dtype == object:
                mixed.add(str(column))
    target.parent.mkdir(parents=True, exist_ok=True)
    writer, rows = None, 0
    for position, item in enumerate(items):
        frame = item[key].copy()
        frame.columns = [str(c) for c in frame.columns]
        frame = frame.reindex(columns=columns)
        for column in mixed:  # a column holding text in any item (for example Vpack in ESSL2 Pack#2) is written as
            frame[column] = frame[column].map(lambda v: None if v is None or v != v else str(v))  # text everywhere
        frame.insert(0, "item", position)
        table = pa.Table.from_pandas(frame, preserve_index=False)
        if writer is None:
            schema = table.schema
            writer = pq.ParquetWriter(target, schema)
        writer.write_table(table.cast(schema))
        rows += len(frame)
    if writer is not None:
        writer.close()
    return rows, len(columns) + 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--prefix", default="")
    args = parser.parse_args()

    block_network()
    import pandas as pd  # imported after the network is blocked

    fields = ["member", "input_bytes", "input_sha256", "output", "output_bytes", "output_sha256", "object", "rows", "columns", "error"]
    done = set()
    if args.manifest.exists():
        with args.manifest.open(newline="", encoding="utf-8") as handle:
            done = {row["member"] for row in csv.DictReader(handle) if not row["error"]}
    new_file = not args.manifest.exists()
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.zip) as archive, args.manifest.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        if new_file:
            writer.writeheader()
        members = [m for m in archive.infolist() if m.filename.endswith(".pkl") and m.filename.startswith(args.prefix)]
        for index, member in enumerate(members, 1):
            if member.filename in done:
                continue
            reader = HashingReader(archive.open(member))
            row = {"member": member.filename, "input_bytes": "", "input_sha256": "", "output": "",
                   "output_bytes": "", "output_sha256": "", "object": "", "rows": "", "columns": "", "error": ""}
            try:
                # streamed from the zip, the bytes hashed as they are read; pandas' compatibility unpickler maps
                # classes of older pandas versions (read_pickle itself needs a seekable file)
                from pandas.compat.pickle_compat import Unpickler
                obj = Unpickler(reader).load()
                reader.finish()
                row.update({"input_bytes": reader.size, "input_sha256": reader.hexdigest()})
                row["object"] = type(obj).__name__
                if isinstance(obj, list) and obj and all(isinstance(e, dict) for e in obj):
                    # cell_to_pack: a list of per-cycle dicts of DataFrames. One Parquet per key, rows of every item
                    # with an "item" column (the list position), written item by item.
                    outputs = []
                    for key in obj[0]:
                        target = args.out / f"{member.filename}.{key}.parquet"
                        rows, columns = write_items(pd, obj, key, target)
                        outputs.append((target, rows, columns))
                    row.update({"output": "|".join(o[0].relative_to(args.out).as_posix() for o in outputs),
                                "output_bytes": "|".join(str(o[0].stat().st_size) for o in outputs),
                                "output_sha256": "|".join(file_sha256(o[0]) for o in outputs),
                                "rows": "|".join(str(o[1]) for o in outputs), "columns": "|".join(str(o[2]) for o in outputs)})
                    writer.writerow(row)
                    handle.flush()
                    del obj
                    continue
                if isinstance(obj, dict):  # tongji NMC01_Car02: Series, DataFrames and scalars on one index
                    parts = {k: v for k, v in obj.items() if isinstance(v, (pd.Series, pd.DataFrame))}
                    frame = pd.concat([v.rename(k) if isinstance(v, pd.Series) else v for k, v in parts.items()], axis=1)
                    for k, v in obj.items():
                        if k not in parts:
                            frame[k] = v  # a scalar such as mileage, repeated on every row
                    obj = frame
                if isinstance(obj, pd.Series):
                    obj = obj.to_frame(name=obj.name if obj.name is not None else "value")
                if not isinstance(obj, pd.DataFrame):
                    raise TypeError(f"not a pandas object: {type(obj).__name__}")
                obj.columns = [str(c) for c in obj.columns]
                target = args.out / (member.filename + ".parquet")
                target.parent.mkdir(parents=True, exist_ok=True)
                obj.to_parquet(target)
                row.update({"output": target.relative_to(args.out).as_posix(), "output_bytes": target.stat().st_size,
                            "output_sha256": file_sha256(target), "rows": len(obj), "columns": len(obj.columns)})
            except Exception as error:  # noqa: BLE001 - record and carry on
                row["error"] = f"{type(error).__name__}: {error}"[:300]
            writer.writerow(row)
            handle.flush()
            if index % 200 == 0:
                print(f"{index} of {len(members)}", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
