"""Source audit 2026-10-04: ku_leuven_bev raw values pass through; clean=True masks only the odometer
"not available" value 4294967.295 (0xFFFFFFFF x 0.001 km). Synthetic data only."""
import io
import zipfile

import numpy as np
import pandas as pd
import pytest

import fielddata
from fielddata.loaders import _base


@pytest.fixture
def root(monkeypatch, tmp_path):
    monkeypatch.setattr(_base, "data_root", lambda: tmp_path)
    return tmp_path


def _release(package_directory):
    d = package_directory("ku_leuven_bev")
    body = ("Timestamp,SOCave292,RawBattCurrent132,Odometer3B6\n"
            "2024-08-10 06:39:51+00:00,51.3,-25.7,4294967.295\n"
            "2024-08-10 06:39:52+00:00,51.4,-47.3,39473.033\n")
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as z:
        z.writestr("BEV energy dynamic data_V2/fast charging sessions/BEV1_2024-08-10_fast_1.csv", body)
    with zipfile.ZipFile(d / "doi-10.48804-8kpdtw.zip", "w") as z:
        z.writestr("BEV energy dynamic data_V2.zip", inner.getvalue())


def test_raw_keeps_odometer_placeholder_and_sign(root, package_directory):
    _release(package_directory)
    raw = fielddata.load("ku_leuven_bev", unit="BEV1")
    assert raw.index.tz is not None and str(raw.index.tz) == "UTC"
    assert raw["Odometer3B6"].tolist() == [4294967.295, 39473.033]
    assert raw["RawBattCurrent132"].tolist() == [-25.7, -47.3]  # negative while charging, kept
    assert raw.attrs["masked_value_count"] == 0


def test_clean_masks_only_odometer_placeholder(root, package_directory):
    _release(package_directory)
    clean = fielddata.load("ku_leuven_bev", unit="BEV1", clean=True)
    assert np.isnan(clean["Odometer3B6"].iloc[0]) and clean["Odometer3B6"].iloc[1] == 39473.033
    assert clean.attrs["masked_value_count"] == 1 and len(clean) == 2
    assert clean["SOCave292"].tolist() == [51.3, 51.4]
    assert clean.index[0] == pd.Timestamp("2024-08-10 06:39:51", tz="UTC")
