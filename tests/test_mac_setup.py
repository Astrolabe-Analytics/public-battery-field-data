"""Fixes from the Mac clean-machine test (reports/MAC_DASHBOARD_TEST_2026-10-02.md).

deflate64 members are read through inflate64, "~" in data_root is expanded, verify fails when a release has no
files, verify writes its log outside the tracked files, and downloads use the certifi certificates.
"""
import os
import ssl

import inflate64

from fielddata import config, fetch, verify
from fielddata._deflate64 import ZIP_DEFLATED64, zipfile


def test_deflate64_members_decompress():
    text = b"time,voltage\n" + b"2016-06-01 00:00:00,350.1\n" * 2000
    deflater = inflate64.Deflater()
    packed = deflater.deflate(text) + deflater.flush()
    inflater = zipfile._get_decompressor(ZIP_DEFLATED64)
    assert inflater.decompress(packed) == text
    assert inflater.eof
    zipfile._check_compression(ZIP_DEFLATED64)  # no error: zipfile accepts the method


def test_home_folder_in_data_root_is_expanded(monkeypatch):
    monkeypatch.setenv("FIELDDATA_DATA_ROOT", "~/battery-data")
    assert config.data_root() == config.Path(os.path.expanduser("~/battery-data"))


def test_verify_fails_when_nothing_is_downloaded(monkeypatch, tmp_path):
    monkeypatch.setenv("FIELDDATA_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(verify, "_LOG", tmp_path / "local" / "verify_log.csv")
    assert verify.main(["cloverleaf"]) == 1


def test_verify_log_is_not_a_tracked_file():
    assert verify._LOG.parent.name == "local"
    ignored = (verify._ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "reports/local/" in ignored


def test_downloads_use_a_certificate_context():
    assert isinstance(fetch._SSL, ssl.SSLContext)
    assert fetch._SSL.verify_mode == ssl.CERT_REQUIRED
