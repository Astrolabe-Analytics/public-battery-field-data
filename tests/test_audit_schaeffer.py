"""Synthetic tests for the schaeffer source-audit change: clean=True also masks +-inf values."""
import zipfile

import numpy as np
import pandas as pd

from fielddata.loaders import schaeffer


def _write(directory, frame):
    with zipfile.ZipFile(directory / "field_data.zip", "w") as archive:
        archive.writestr("field_data/data_sys_1.csv", frame.to_csv(index=False))


def _frame():
    cells = {f"U_Cell_{i}": [3.3, 3.3, 0.0] for i in range(1, 9)}
    return pd.DataFrame({"Timestamp": ["2016-01-01 00:00:10", "2016-01-01 00:00:00", "2016-01-01 00:00:05"],
                         "U_Battery": [26.4, 26.4, 26.4], "I_Battery": [np.inf, -10.0, -np.inf],
                         "SOC_Battery": [90.0, 90.0, 90.0], **cells})


def test_clean_masks_infinite_values_only(monkeypatch, tmp_path, package_directory):
    _write(package_directory("schaeffer"), _frame())
    monkeypatch.setattr(schaeffer, "data_root", lambda: tmp_path)
    raw = schaeffer.load(1)
    clean = schaeffer.load(1, clean=True)
    assert np.isinf(raw["I_Battery"]).sum() == 2 and len(clean) == len(raw) == 3
    assert clean["I_Battery"].isna().sum() == 2 and clean["I_Battery"].dropna().tolist() == [-10.0]
    assert clean.attrs["infinite_value_counts"] == {"I_Battery": 2}
    assert clean.attrs["zero_cell_voltage_count"] == 8 and raw.attrs["infinite_value_counts"] == {}
    assert clean["U_Battery"].tolist() == raw["U_Battery"].tolist()


def test_clean_chunks_mask_infinite_values(monkeypatch, tmp_path, package_directory):
    _write(package_directory("schaeffer"), _frame())
    monkeypatch.setattr(schaeffer, "data_root", lambda: tmp_path)
    chunks = list(schaeffer.load(1, chunksize=2, clean=True))
    assert sum(c.attrs["infinite_value_counts"].get("I_Battery", 0) for c in chunks) == 2
    assert not any(np.isinf(c["I_Battery"]).any() for c in chunks)
