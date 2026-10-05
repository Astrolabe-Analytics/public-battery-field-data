"""Synthetic-data tests for the bilfinger2026 clean rules added in the 2026-10-04 source audit."""
import io
import zipfile

import numpy as np
import pandas as pd
import pytest

import fielddata
from fielddata.loaders import _base

MEMBER = "DVA_robustness/data/VW/VW_ID3_FTM_8A_CEE7_Balancing.feather"


@pytest.fixture
def root(monkeypatch, tmp_path):
    monkeypatch.setattr(_base, "data_root", lambda: tmp_path)
    return tmp_path


def _write(package_directory, package, member, frame):
    d = package_directory(package)
    buf = io.BytesIO()
    frame.to_feather(buf)
    with zipfile.ZipFile(d / "data.zip", "w") as z:
        z.writestr(member, buf.getvalue())


def _frame():
    return pd.DataFrame({
        "U": [450.25, 1023.5, 450.25, 450.5],
        "I": [0.0, 0.0, 166272.14, -178.0],
        "SOC": [96.8, 101.6, 96.8, 94.4],
        "cell_voltage_1": [4.169, 5.094, 4.169, 4.17],
        "pack_temp_0": [26.0, 87.0, 26.0, 26.0],
    })


def test_raw_is_unchanged(root, package_directory):
    _write(package_directory, "bilfinger2026", MEMBER, _frame())
    raw = fielddata.load("bilfinger2026", unit="VW_ID3_FTM_8A_CEE7_Balancing")
    pd.testing.assert_frame_equal(raw, _frame())
    assert raw.attrs["masked_value_count"] == 0


def test_clean_masks_only_out_of_range_u_and_i(root, package_directory):
    _write(package_directory, "bilfinger2026", MEMBER, _frame())
    clean = fielddata.load("bilfinger2026", unit="VW_ID3_FTM_8A_CEE7_Balancing", clean=True)
    assert clean.attrs["masked_value_count"] == 2
    assert np.isnan(clean["U"].iloc[1]) and np.isnan(clean["I"].iloc[2])
    assert clean["U"].tolist()[::2] == [450.25, 450.25] and clean["I"].iloc[3] == -178.0
    # values left as released: the drain current, SOC, cell voltage and temperature spikes
    assert clean["SOC"].iloc[1] == 101.6 and clean["cell_voltage_1"].iloc[1] == 5.094 and clean["pack_temp_0"].iloc[1] == 87.0
    assert len(clean) == 4


def test_bilfinger2024_clean_changes_nothing(root, package_directory):
    _write(package_directory, "bilfinger2024", "m1737452/data/VW/vehicle/VW_ID3_JB_8A_C40_2024.feather", _frame())
    clean = fielddata.load("bilfinger2024", unit="VW_ID3_JB_8A_C40_2024", clean=True)
    pd.testing.assert_frame_equal(clean, _frame())
    assert clean.attrs["masked_value_count"] == 0
