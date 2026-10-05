"""Source audit 2026-10-04: deng timestamps are naive (no zone stated) and raw values pass through (synthetic data only).

The paper (Table 1, p. 2) gives the time format without a zone, so load() must not label it UTC.
Negative charging current, BMS available_* fields and the row counter come back as released.
"""
import shutil

import pandas as pd


def _install(monkeypatch, tmp_path, package_directory, fixture_dir):
    from fielddata.loaders import deng

    directory = package_directory("deng")
    (directory / "#1.rar").write_bytes(b"synthetic-rar-placeholder")
    monkeypatch.setattr(deng, "data_root", lambda: tmp_path)
    monkeypatch.setattr(deng, "_unrar", lambda: "synthetic-unrar")

    def extract(command, check):
        target = str(command[-1]).rstrip("\\/")
        shutil.copyfile(fixture_dir / "deng_pack.csv", f"{target}/pack.csv")

    monkeypatch.setattr(deng.subprocess, "run", extract)
    return deng


def test_deng_timestamps_naive(monkeypatch, tmp_path, package_directory, fixture_dir):
    deng = _install(monkeypatch, tmp_path, package_directory, fixture_dir)
    frame = deng.load("#1")
    assert frame.index.tz is None
    assert frame.index[0] == pd.Timestamp("2020-01-01 00:00:00")
    assert frame.index[1] == pd.Timestamp("2020-01-01 00:00:10")


def test_deng_raw_values_unchanged(monkeypatch, tmp_path, package_directory, fixture_dir):
    deng = _install(monkeypatch, tmp_path, package_directory, fixture_dir)
    frame = deng.load("#1")
    assert frame["charge_current"].tolist() == [-20, -19]  # negative while charging, kept
    assert frame["number"].tolist() == [1, 2]
    assert frame["available_capacity"].tolist() == [80, 79]
    assert frame.attrs["masked_value_count"] == 0
