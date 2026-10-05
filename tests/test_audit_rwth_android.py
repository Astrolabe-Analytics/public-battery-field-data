"""Source audit 2026-10-04: rwth-android raw values pass through; clean=True masks only -2147.483648
(Integer.MIN_VALUE x 1e-6, "not provided") in the current and charge columns. Synthetic data only."""
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
    d = package_directory("rwth-android")
    frame = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-01-15 19:28:06.173", "2026-01-15 19:28:30.175"]),
        "battery_technology": ["Li-ion"] * 2, "manufacturer": ["OnePlus"] * 2, "model": ["OPD2415"] * 2,
        "charge_counter": [7.923, 7.919], "nominal_capacity": [0.0, 0.0], "state_of_charge": [69, 69],
        "current": [0.211, 0.363], "current_avg": [-2147.483648, -2147.483648], "status": [3, 3],
        "voltage_cell": [4.083, 4.083], "cell_id": ["abc"] * 2,
    })
    buf = io.BytesIO()
    frame.to_parquet(buf)
    with zipfile.ZipFile(d / "Dataset_from_Mobile_Battery_Data_Explorer_2026-04.zip", "w") as z:
        z.writestr("abc.parquet", buf.getvalue())


def test_raw_unchanged(root, package_directory):
    _release(package_directory)
    raw = fielddata.load("rwth-android", unit="abc")
    assert raw.index.tz is None
    assert raw["current_avg"].tolist() == [-2147.483648, -2147.483648]
    assert raw["current"].tolist() == [0.211, 0.363]  # positive while discharging on this make, kept
    assert raw["nominal_capacity"].tolist() == [0.0, 0.0]
    assert raw.attrs["masked_value_count"] == 0


def test_clean_masks_only_not_provided(root, package_directory):
    _release(package_directory)
    clean = fielddata.load("rwth-android", unit="abc", clean=True)
    assert clean["current_avg"].isna().all() and clean.attrs["masked_value_count"] == 2
    assert clean["current"].tolist() == [0.211, 0.363]
    assert clean["nominal_capacity"].tolist() == [0.0, 0.0] and len(clean) == 2
    assert np.isclose(clean["charge_counter"].iloc[0], 7.923)
