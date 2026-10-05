"""Synthetic-data tests for the tumftm loader changes from the 2026-10-04 source audit."""
import pandas as pd
import pytest

import fielddata
from fielddata.loaders import _base


@pytest.fixture
def root(monkeypatch, tmp_path):
    monkeypatch.setattr(_base, "data_root", lambda: tmp_path)
    return tmp_path


def test_time_bounds_keeps_valid_times_in_a_row_group_with_2087(root, package_directory):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from fielddata.loaders import tumftm
    d = package_directory("tumftm") / "electric-vehicle-uds-dataset" / "data"
    (d / "uds_data").mkdir(parents=True)
    pd.DataFrame({"value_id": [1200], "name_de": ["x"], "name_en": ["pack voltage"], "variable_name": ["hv_battery_voltage"],
                  "unit": ["V"], "min_val": [0], "max_val": [1000], "sampling_interval_ms": [200]}).to_csv(d / "value_overview.csv", index=False)
    times = pd.to_datetime(["2022-11-15 09:37:08", "2087-03-07 15:46:37", "2022-12-01 00:00:00", "2023-04-24 15:10:02"])
    table = pd.DataFrame({"vehicle_id": ["CUP1"] * 4, "time": times, "value_id": [1200] * 4, "value": [400.0] * 4})
    pq.write_table(pa.Table.from_pandas(table), d / "uds_data" / "CUP1.parquet", row_group_size=2)
    assert tumftm.time_bounds("CUP1", clean=True) == (pd.Timestamp("2022-11-15 09:37:08"), pd.Timestamp("2023-04-24 15:10:02"))
    assert tumftm.time_bounds("CUP1", clean=False)[1].year == 2087
    clean = fielddata.load("tumftm", unit="CUP1", clean=True)
    assert len(clean) == 4 and clean["time"].isna().sum() == 1
