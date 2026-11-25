"""Processed-copy integrity, partitioning, restart and explicit-block tests."""
import json

import pandas as pd
import pandas.testing as pdt
import pytest

from fielddata import processed
from fielddata._standard import from_raw


@pytest.fixture
def storage(monkeypatch, tmp_path):
    monkeypatch.setattr(processed, "cache_root", lambda: tmp_path / "_processed")
    monkeypatch.setattr(processed, "data_root", lambda: tmp_path)
    monkeypatch.setattr(processed, "code_version", lambda: {"revision": "test", "code_sha256": "abc",
                                                         "format_version": 1, "pandas": pd.__version__})
    monkeypatch.setattr(processed, "verify_sources", lambda package: [])
    return tmp_path


def test_partition_roundtrip_and_corruption(storage):
    raw = pd.DataFrame({"current_A": [-1.0, 2.0], "voltage_V": [12.0, 12.1]},
                       index=pd.to_datetime(["2020-01-31", "2020-02-01"], utc=True))
    view = from_raw("aitio", "1", raw)
    writer = processed._Writer("aitio", "1", [], processed.code_version())
    writer.append(view)
    manifest = writer.finish()
    assert [part["month"] for part in manifest["parts"]] == ["2020-01", "2020-02"]
    pdt.assert_frame_equal(processed.load("aitio", "1"), view)
    assert len(processed.load("aitio", "1", month="2020-02")) == 1
    path = processed.unit_directory("aitio", "1") / manifest["parts"][0]["file"]
    path.write_bytes(b"corrupt")
    with pytest.raises(processed.StaleProcessed, match="damaged"):
        processed.load("aitio", "1")


def test_undated_and_code_staleness(storage, monkeypatch):
    raw = pd.DataFrame({"current_A": [-1.0], "soc_pct": [50.0]})
    writer = processed._Writer("cao", "QAS:0", [], processed.code_version())
    writer.append(from_raw("cao", "QAS:0", raw))
    manifest = writer.finish()
    assert manifest["parts"][0]["month"] == "undated"
    monkeypatch.setattr(processed, "code_version", lambda: {"code_sha256": "different"})
    with pytest.raises(processed.StaleProcessed, match="code changed"):
        processed.load("cao", "QAS:0")


def test_ppl_mixed_epoch_copy_matches_combined_standard(storage, monkeypatch):
    import fielddata
    from fielddata.loaders import ppl

    frames = {
        2021: pd.DataFrame({"CellVoltMax": [3.4]}, index=pd.to_datetime(["2022-01-01"], utc=True)),
        2022: pd.DataFrame({"DCCurrent": [float("nan")]}, index=pd.to_datetime(["2022-01-01"], utc=True)),
    }
    monkeypatch.setattr(ppl, "load", lambda years: frames[years[0]])
    monkeypatch.setattr(ppl, "systems", lambda: pd.DataFrame({"years": [[2021, 2022]]}))
    unit = "E_W_Brown_BESS"
    writer = processed._Writer("ppl", unit, [], processed.code_version())
    for raw in frames.values():
        writer.append(from_raw("ppl", unit, raw))
    manifest = writer.finish()
    assert "pack_current" not in manifest["parts"][0]["columns"]
    assert "cell_v_max" not in manifest["parts"][1]["columns"]
    expected = fielddata.standard("ppl", unit)
    pdt.assert_frame_equal(processed.load("ppl", unit), expected)
    assert expected["data_tier"].tolist() == ["max-min", "pack-only"]


def test_changed_source_content(storage):
    writer = processed._Writer("aitio", "1", [], processed.code_version())
    writer.append(pd.DataFrame({"elapsed_time_s": [0], "unit": ["1"]}))
    writer.finish()
    with pytest.raises(processed.StaleProcessed, match="source content changed"):
        processed.validate("aitio", "1", sources=[{"file": "x", "bytes": 1, "sha256": "x"}])


def test_build_continues_after_known_block_and_resumes(storage, monkeypatch):
    import fielddata
    table = pd.DataFrame({"unit": ["GIS:0", "DTI:0"], "standard_status": ["blocked", "supported"],
                          "standard_reason": ["column meanings not established", ""]})
    monkeypatch.setattr(fielddata, "standard_systems", lambda package: table)
    monkeypatch.setattr(processed, "raw_frame", lambda *args: pd.DataFrame({"current_A": [-1.0]}))
    result = processed.build("cao")
    assert result["status"].tolist() == ["blocked", "built"]
    result = processed.build("cao")
    assert result["status"].tolist() == ["blocked", "reused"]
    path = processed.unit_directory("cao", "DTI:0") / "manifest.json"
    manifest = json.loads(path.read_text())
    assert manifest["rows"] == 1 and manifest["code_version"]["revision"] == "test"


def test_invalid_time_is_flagged_and_not_dropped(storage):
    writer = processed._Writer("aitio", "1", [], processed.code_version())
    writer.append(pd.DataFrame({"time": pd.to_datetime([None], utc=True), "source__Timestamp_raw": [""]}))
    manifest = writer.finish()
    assert manifest["rows"] == 1
    assert manifest["invalid_time_rows"] == 1
    assert manifest["parts"][0]["month"] == "undated"
    frame = processed.load("aitio", "1")
    assert pd.isna(frame["time"].iloc[0])
    assert frame["source__Timestamp_raw"].iloc[0] == ""


def test_mixed_integer_and_string_source_values_are_losslessly_encoded(storage):
    frame = pd.DataFrame({"source__raw_code": [362, "0365", None]})
    writer = processed._Writer("birds_cubesat", "TSURU", [], processed.code_version())
    writer.append(frame)
    manifest = writer.finish()
    loaded = processed.load("birds_cubesat", "TSURU")
    assert loaded["source__raw_code"].tolist()[:2] == [
        '{"type": "int", "value": 362}',
        '{"type": "str", "value": "0365"}',
    ]
    assert loaded["source__raw_code"].isna().tolist() == [False, False, True]
    assert manifest["parts"][0]["attrs"]["source_value_encodings"]["source__raw_code"].startswith("JSON tagged")


def test_m5bat_iter_load_yields_bounded_parquet_batches(monkeypatch, tmp_path):
    import zipfile
    import pyarrow as pa
    import pyarrow.parquet as pq
    from fielddata.loaders import m5bat_pbacid

    monkeypatch.setattr(m5bat_pbacid, "data_root", lambda: tmp_path)
    archive_path = tmp_path / "source.zip"
    table = pa.Table.from_pandas(pd.DataFrame(
        {"current_A_bms": [1.0, 2.0, 3.0]},
        index=pd.DatetimeIndex(["2020-01-01", "2020-01-02", "2020-01-03"],
                               tz="UTC", name="timestamp_utc")))
    parquet_path = tmp_path / "Exide1_BMS_2020.parquet"
    pq.write_table(table, parquet_path)
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write(parquet_path, "Exide1_BMS_2020.parquet")
    monkeypatch.setattr(m5bat_pbacid, "_archive_path", lambda: archive_path)

    batches = list(m5bat_pbacid.iter_load(source="bms", chunksize=2))
    assert [len(batch) for batch in batches] == [2, 1]
    assert all(batch.index.name == "timestamp_utc" for batch in batches)
    assert pd.concat(batches)["current_A_bms"].tolist() == [1.0, 2.0, 3.0]


def test_unexpected_failure_is_recorded_and_raised(storage, monkeypatch):
    import fielddata
    table = pd.DataFrame({"unit": ["DTI:0"], "standard_status": ["supported"], "standard_reason": [""]})
    monkeypatch.setattr(fielddata, "standard_systems", lambda package: table)
    def fail(*args):
        raise RuntimeError("unreadable source")
    monkeypatch.setattr(processed, "raw_frame", fail)
    with pytest.raises(RuntimeError, match="unreadable"):
        processed.build("cao")
    summary = pd.read_csv(processed.cache_root() / "build_summary.csv")
    assert summary.iloc[-1]["status"] == "failed"


def test_streaming_snippets_keep_unit_identity_and_sign(storage, monkeypatch):
    import numpy as np
    import fielddata
    table = pd.DataFrame({"unit": ["battery_brand1:1", "battery_brand1:2", "battery_brand1:3"],
                          "archive": ["battery_brand1.tar.gz"] * 3,
                          "standard_status": ["supported", "supported", "empty"],
                          "standard_reason": ["", "", "label only"]})
    monkeypatch.setattr(fielddata, "standard_systems", lambda package: table)
    array = np.zeros((2, 8))
    array[:, 1] = -5
    array[:, 7] = [100, 110]
    records = [(f"{i}.pkl", array, {"car": i, "charge_segment": 1, "label": "00"}) for i in (1, 2)]
    monkeypatch.setattr(processed._snippets, "iter_snippets", lambda *args: iter(records))
    summary = processed.build("zhang2023", chunksize=2)
    assert set(summary["status"]) == {"built", "empty"}
    for unit in ("battery_brand1:1", "battery_brand1:2"):
        frame = processed.load("zhang2023", unit)
        assert frame["unit"].unique().tolist() == [unit]
        assert frame["pack_current"].tolist() == [5, 5]
        assert frame["elapsed_time_s"].tolist() == [0, 10]


def test_failed_rebuild_preserves_completed_manifest(storage):
    writer = processed._Writer("aitio", "1", [], processed.code_version())
    writer.append(pd.DataFrame({"elapsed_time_s": [0], "unit": ["1"]}))
    original = writer.finish()
    incomplete = processed._Writer("aitio", "1", [], processed.code_version())
    incomplete.append(pd.DataFrame({"elapsed_time_s": [1], "unit": ["1"]}))
    assert processed.validate("aitio", "1")["parts"] == original["parts"]


def test_empty_source_inventory_is_not_success(monkeypatch):
    monkeypatch.setattr(processed, "source_paths", lambda package: [])
    with pytest.raises(FileNotFoundError, match="no loader input files held"):
        processed.verify_sources("ppl")
