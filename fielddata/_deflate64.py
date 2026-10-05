"""Deflate64 support for Python's zipfile, using the inflate64 package.

Why: two releases (tsukuba and m5bat-2023-04) are zip files whose members use the deflate64 method, which
Python's own zipfile cannot read. inflate64 has prebuilt wheels for current Python on macOS (Intel and Apple
Silicon), Windows and Linux, so nothing is compiled during install. It replaces zipfile-deflate64, which has
no wheels for Python 3.11 or newer and does not compile with the current Apple compiler.

Importing this module teaches zipfile to read deflate64 members. Every other compression method is read
exactly as before. Writing deflate64 is not supported. Loaders use ``from fielddata._deflate64 import zipfile``.
"""
from __future__ import annotations

import zipfile

import inflate64

ZIP_DEFLATED64 = 9


class _Inflater:
    """The decompressor interface that zipfile.ZipExtFile expects: decompress(data) and eof."""

    def __init__(self) -> None:
        self._inflater = inflate64.Inflater()

    def decompress(self, data: bytes) -> bytes:
        return self._inflater.inflate(data)

    @property
    def eof(self) -> bool:
        return self._inflater.eof


if not getattr(zipfile, "_fielddata_deflate64", False):
    _get_decompressor = zipfile._get_decompressor
    _check_compression = zipfile._check_compression

    def _get_decompressor_with_deflate64(compress_type):
        if compress_type == ZIP_DEFLATED64:
            return _Inflater()
        return _get_decompressor(compress_type)

    def _check_compression_with_deflate64(compression):
        if compression == ZIP_DEFLATED64:
            return None
        return _check_compression(compression)

    zipfile._get_decompressor = _get_decompressor_with_deflate64
    zipfile._check_compression = _check_compression_with_deflate64
    zipfile._fielddata_deflate64 = True

__all__ = ["zipfile", "ZIP_DEFLATED64"]
