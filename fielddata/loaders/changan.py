"""Loader for the Changan 300-vehicle raw telemetry (split archive RAW_DATA.z01 + RAW_DATA.zip).

The archive is served as a two-volume split zip whose members are one RAR per vehicle, each holding one CSV.
This loader streams a vehicle straight out of the split archive (inflate, then un-RAR, then CSV) without
unpacking 72 GB to disk. Needs libarchive (``libarchive-c``) for the RAR layer.
"""
from __future__ import annotations

import io
import os
import re
import struct
import zlib

import pandas as pd

from fielddata.loaders._base import check_unit, directory, finish, mask_values

_PACKAGE = "changan"
_PARTS = ("raw/RAW_DATA.z01", "raw/RAW_DATA.zip")
# A pack or cell voltage of exactly 0 V cannot be a measurement of a live pack. Two kinds of row carry it
# (raw data, vin1 to vin3 in full, source audit 2026-10-04): chargestatus 0 with the whole BMS block at zero
# (169 rows in vin2, 421 in vin3) and chargestatus 255 with totalcurrent exactly -1000 A, soc 4 and maximum
# temperature -40 C (51, 55 and 22 rows). A current of exactly -1000 A occurs only in those 0 V rows, so it is a
# fill value, not a measurement, and is masked too. Neither code is documented by the publisher.
_ZERO_RULES = {c: (lambda s: s == 0) for c in ("totalvoltage", "minvoltagebattery", "maxvoltagebattery")}
_ZERO_RULES["totalcurrent"] = lambda s: s == -1000


def _parts():
    return [directory(_PACKAGE) / p for p in _PARTS]


def _members():
    """Central directory of the split zip: {vehicle: (member, method, disk, offset)}."""
    zmain = _parts()[1]
    size = os.path.getsize(zmain)
    with open(zmain, "rb") as handle:
        handle.seek(max(0, size - 70000))
        tail = handle.read()
        k = tail.rfind(b"PK\x06\x06")
        cd_size, cd_off = struct.unpack("<IQHHIIQQQQ", tail[k:k + 56])[-2:]
        handle.seek(cd_off)
        cd = handle.read(cd_size)
    out, p = {}, 0
    while cd[p:p + 4] == b"PK\x01\x02":
        (_, _, _, _, meth, _, _, _, csz, usz, nl, el, cl, disk, _, _, off) = struct.unpack("<IHHHHHHIIIHHHHHII", cd[p:p + 46])
        name = cd[p + 46:p + 46 + nl].decode()
        extra, q = cd[p + 46 + nl:p + 46 + nl + el], 0
        while q < len(extra):
            hid, hs = struct.unpack("<HH", extra[q:q + 4])
            data, r = extra[q + 4:q + 4 + hs], 0
            if hid == 1:  # zip64 extended information
                r += 8 if usz == 0xFFFFFFFF else 0
                r += 8 if csz == 0xFFFFFFFF else 0
                if off == 0xFFFFFFFF:
                    off = struct.unpack("<Q", data[r:r + 8])[0]
                    r += 8
                if disk == 0xFFFF:
                    disk = struct.unpack("<I", data[r:r + 4])[0]
            q += 4 + hs
        if name.lower().endswith(".rar"):
            match = re.search(r"(vin\d+)", name)
            out[match.group(1) if match else os.path.basename(name)] = (name, meth, disk, off)
        p += 46 + nl + el + cl
    return out


class _Inflated(io.RawIOBase):
    """Read-only stream of one member's decompressed bytes, continuing across the volume boundary."""

    def __init__(self, parts, disk, offset, method):
        self._files = [open(p, "rb") for p in parts[disk:]]
        self._i = 0
        f = self._files[0]
        f.seek(offset)
        nl, el = struct.unpack("<HH", f.read(30)[26:30])
        f.seek(offset + 30 + nl + el)
        self._z = zlib.decompressobj(-15) if method == 8 else None
        self._buf = b""

    def readable(self):
        return True

    def _raw(self, n):
        while self._i < len(self._files):
            data = self._files[self._i].read(n)
            if data:
                return data
            self._i += 1
        return b""

    def readinto(self, b):
        while not self._buf:
            raw = self._raw(1 << 20)
            if not raw:
                if self._z is not None:
                    self._buf = self._z.flush()
                    self._z = None
                    if self._buf:
                        break
                return 0
            self._buf = self._z.decompress(raw) if self._z is not None else raw
            if self._z is not None and self._z.eof:
                self._i = len(self._files)
        n = min(len(b), len(self._buf))
        b[:n] = self._buf[:n]
        self._buf = self._buf[n:]
        return n

    def close(self):
        for f in self._files:
            f.close()
        super().close()


class _Blocks(io.RawIOBase):
    def __init__(self, blocks):
        self._it, self._buf = iter(blocks), b""

    def readable(self):
        return True

    def readinto(self, b):
        while not self._buf:
            try:
                self._buf = bytes(next(self._it))
            except StopIteration:
                return 0
        n = min(len(b), len(self._buf))
        b[:n] = self._buf[:n]
        self._buf = self._buf[n:]
        return n


def fleet():
    """The committed per-vehicle summary fleet_meta.csv (derived by the collection from the raw files)."""
    return pd.read_csv(directory(_PACKAGE) / "fleet_meta.csv")


def systems():
    """One row per vehicle RAR in the split archive (300), keyed vin1 to vin300."""
    rows = [{"unit": k, "member": v[0], "volume": _PARTS[v[2]], "offset": v[3]} for k, v in _members().items()]
    return pd.DataFrame(rows).sort_values("unit", key=lambda s: s.str[3:].astype(int)).reset_index(drop=True)


def load(unit, nrows=None, chunksize=None, clean=False):
    """Stream one vehicle's raw 0.1 Hz CSV out of the split archive.

    Columns as released (SI Table 2 of the paper): terminaltime (relative seconds, adjusted by the publisher for
    privacy, no calendar date; rows are randomly ordered, so sort by terminaltime), soc (BMS estimate), speed,
    totalodometer, chargestatus (1 = charging, 3 = discharging; other codes undocumented), totalvoltage,
    totalcurrent (positive = discharging, negative = charging), min/maxvoltagebattery, min/maxtemperaturevalue,
    and the ``~``-separated per-cell strings batteryvoltage and probetemperatures (see ``expand``). A whole vehicle is
    up to about 3 GB of text: pass ``nrows`` or ``chunksize`` (returns an iterator). ``clean=True`` masks
    exact-zero pack and cell-extreme voltages and a totalcurrent of exactly -1000 A (the fill value that appears
    only in 0 V rows with chargestatus 255), one value at a time.
    """
    import libarchive
    members = _members()
    name = check_unit(unit, list(members), _PACKAGE)
    member, method, disk, offset = members[name]
    raw = io.BufferedReader(_Inflated(_parts(), disk, offset, method), buffer_size=1 << 20)

    def frames():
        with libarchive.stream_reader(raw) as archive:
            for entry in archive:
                if entry.pathname.lower().endswith(".csv"):
                    text = io.BufferedReader(_Blocks(entry.get_blocks()), buffer_size=1 << 20)
                    reader = pd.read_csv(text, nrows=nrows, chunksize=chunksize)
                    for chunk in ([reader] if chunksize is None else reader):
                        masked = mask_values(chunk, _ZERO_RULES) if clean else 0
                        yield finish(chunk, _PACKAGE, clean, masked, unit=name, member=member)
                    return

    if chunksize is not None:
        return frames()
    return next(frames())


def expand(frame: pd.DataFrame, column: str = "batteryvoltage") -> pd.DataFrame:
    """Split a ``~``-separated per-cell string column into one numeric column per cell."""
    parts = frame[column].astype(str).str.split("~", expand=True)
    parts.columns = [f"{column}_{i + 1}" for i in range(parts.shape[1])]
    return parts.apply(pd.to_numeric, errors="coerce")
