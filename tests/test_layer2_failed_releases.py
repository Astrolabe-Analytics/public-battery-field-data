"""Regression checks for finishing repairs without restarting paused Changan."""
import json
import sys

import pandas as pd
import pytest

from scripts.checks import layer2_failed_releases as repair
from scripts.checks import layer2_code_fingerprint_check as fingerprint


def test_default_run_excludes_changan(monkeypatch):
    selected = []
    monkeypatch.setattr(sys, "argv", ["layer2_failed_releases.py"])
    monkeypatch.setattr(repair, "run", lambda packages: selected.extend(packages))
    repair.main()
    assert selected == repair.RELEASES[:-1]


def test_explicit_changan_rejected_before_io(monkeypatch):
    def unexpected_io():
        pytest.fail("Paused Changan must not access processed storage")

    monkeypatch.setattr(repair.processed, "cache_root", unexpected_io)
    with pytest.raises(ValueError, match="resume only when a task needs Changan"):
        repair.run(["changan"])


def test_verified_checkpoint_still_uses_fresh_build_verification(monkeypatch, tmp_path):
    monkeypatch.setattr(repair, "OUT", tmp_path)
    monkeypatch.setattr(repair.processed, "cache_root", lambda: tmp_path / "_processed")
    pd.DataFrame([{
        "release": "birds_cubesat", "result": "verified", "rows": 2, "processed_bytes": 10
    }]).to_csv(tmp_path / "progress.csv", index=False)
    calls = []
    checkpoints = []
    monkeypatch.setattr(repair, "_ensure_held_checksums", lambda package: [])
    monkeypatch.setattr(repair, "_write_progress",
                        lambda rows, before: checkpoints.append(rows))

    def build(package, checksums):
        calls.append(package)
        return "fresh verification", 2, 10

    monkeypatch.setattr(repair, "_build", build)
    repair.run(["birds_cubesat"])
    assert calls == ["birds_cubesat"]
    assert checkpoints[0][-1]["result"] == "paused"
    assert checkpoints[0][-1]["progress"] == ""


def test_repair_failure_is_checkpointed_and_raised(monkeypatch, tmp_path):
    monkeypatch.setattr(repair, "OUT", tmp_path)
    monkeypatch.setattr(repair.processed, "cache_root", lambda: tmp_path / "_processed")
    monkeypatch.setattr(repair, "_ensure_held_checksums", lambda package: [])
    checkpoints = []
    monkeypatch.setattr(repair, "_write_progress",
                        lambda rows, before: checkpoints.append(rows))

    def fail(package, checksums):
        raise ValueError("checksum mismatch")

    monkeypatch.setattr(repair, "_build", fail)
    with pytest.raises(RuntimeError, match="repair failures remain"):
        repair.run(["birds_cubesat"])
    assert checkpoints[0][0]["result"] == "incomplete"
    assert "checksum mismatch" in checkpoints[0][0]["detail"]


def test_spot_check_decodes_mixed_values_across_parts(monkeypatch, tmp_path):
    expected = pd.DataFrame({"source__raw_code": [362, "0365", None], "pack_voltage": [1., 2., 3.]})
    monkeypatch.setattr(repair.fielddata, "standard", lambda package, unit: expected)
    monkeypatch.setattr(repair.processed, "cache_root", lambda: tmp_path / "_processed")
    writer = repair.processed._Writer("birds_cubesat", "TSURU", [], {})
    writer.append(expected)
    writer.finish()
    result = repair._spot_check("birds_cubesat", "TSURU")
    assert result["result"] == "matched"
    assert result["spot_rows"] == 3
    assert result["loader_rows"] == result["processed_rows"] == 3


def test_spot_check_rejects_changed_values(monkeypatch, tmp_path):
    expected = pd.DataFrame({"pack_voltage": [1., 2., 3.]})
    monkeypatch.setattr(repair.fielddata, "standard", lambda package, unit: expected)
    monkeypatch.setattr(repair.processed, "cache_root", lambda: tmp_path / "_processed")
    writer = repair.processed._Writer("birds_cubesat", "TSURU", [], {})
    writer.append(expected.assign(pack_voltage=4.))
    writer.finish()
    with pytest.raises(AssertionError):
        repair._spot_check("birds_cubesat", "TSURU")


def test_whole_unit_spot_check_rejects_missing_rows(monkeypatch, tmp_path):
    expected = pd.DataFrame({"pack_voltage": [1., 2., 3.]})
    monkeypatch.setattr(repair.fielddata, "standard", lambda package, unit: expected)
    monkeypatch.setattr(repair.processed, "cache_root", lambda: tmp_path / "_processed")
    writer = repair.processed._Writer("birds_cubesat", "TSURU", [], {})
    writer.append(expected.iloc[:2])
    writer.finish()
    with pytest.raises(AssertionError, match="row counts differ"):
        repair._spot_check("birds_cubesat", "TSURU")


def test_streaming_spot_check_closes_loader_and_handles_months(monkeypatch, tmp_path):
    from fielddata.loaders import m5bat_pbacid

    frame = pd.DataFrame({
        "time": pd.to_datetime(["2020-01-31", "2020-02-01"], utc=True),
        "pack_current": [-1., 2.],
    })
    closed = []

    def batches(**kwargs):
        assert kwargs == {"source": "bms", "chunksize": 4096}
        try:
            yield frame
            pytest.fail("Spot check must consume only the bounded first loader batch")
        finally:
            closed.append(True)

    monkeypatch.setattr(m5bat_pbacid, "iter_load", batches)
    monkeypatch.setattr(repair.fielddata, "standardize", lambda package, unit, raw: raw)
    monkeypatch.setattr(repair.processed, "cache_root", lambda: tmp_path / "_processed")
    writer = repair.processed._Writer("m5bat-pbacid", "Pb1:bms", [], {})
    writer.append(frame)
    writer.finish()
    result = repair._spot_check("m5bat-pbacid", "Pb1:bms")
    assert result["result"] == "matched"
    assert result["scope"] == "first loader batch"
    assert closed == [True]


def test_progress_preserves_changan_pause_and_updates_status(monkeypatch, tmp_path):
    monkeypatch.setattr(repair, "ROOT", tmp_path)
    monkeypatch.setattr(repair, "OUT", tmp_path / "reports")
    monkeypatch.setattr(repair, "COORD", tmp_path / "A.md")
    monkeypatch.setattr(repair.processed, "cache_root", lambda: tmp_path / "_processed")
    (tmp_path / "STATUS.md").write_text(
        "| birds_cubesat | yes | no | 0 | 0 | no |\n\n"
        "## Layer 2 failed-release repairs, 2026-10-20\nold progress\n",
        encoding="utf-8",
    )
    (tmp_path / "A.md").write_text("# A\n", encoding="utf-8")
    repair._write_progress([
        {"progress": "3 of 10", "release": "birds_cubesat", "result": "verified",
         "rows": 2, "processed_bytes": 10, "detail": "checked"},
        {"progress": "", "release": "changan", "result": "paused",
         "rows": 0, "processed_bytes": 0, "detail": repair.CHANGAN_PAUSE},
    ], {"free_bytes": 100})
    status = (tmp_path / "STATUS.md").read_text(encoding="utf-8")
    coord = (tmp_path / "A.md").read_text(encoding="utf-8")
    assert "| birds_cubesat | yes | yes | 2 | 10 | yes |" in status
    assert "old progress" not in status
    assert "done 3 of 10 releases" in coord
    assert "done  releases" not in coord
    assert repair.CHANGAN_PAUSE in coord


@pytest.mark.parametrize("damage", ["none", "size", "checksum", "missing"])
def test_tongji_converted_inputs_checked_against_manifest(monkeypatch, tmp_path, damage):
    import hashlib
    from fielddata.loaders import tongji_rest

    root = tmp_path / "release" / "converted"
    root.mkdir(parents=True)
    path = root / "segment.parquet"
    path.write_bytes(b"held")
    sha256 = hashlib.sha256(b"held").hexdigest()
    manifest = tmp_path / "reports" / "candidates" / "tongji_rest" / "pickle_conversion.csv"
    manifest.parent.mkdir(parents=True)
    pd.DataFrame([{"output": "segment.parquet", "output_bytes": 4,
                   "output_sha256": sha256, "error": ""}]).to_csv(manifest, index=False)
    monkeypatch.setattr(repair, "ROOT", tmp_path)
    monkeypatch.setattr(repair, "OUT", tmp_path / "reports")
    monkeypatch.setattr(repair, "data_root", lambda: tmp_path)
    monkeypatch.setattr(repair, "metadata", lambda package: {"data_directory": "release/data"})
    monkeypatch.setattr(tongji_rest, "FIELD", ["unit"])
    monkeypatch.setattr(tongji_rest, "segments",
                        lambda unit, kind: [path] if kind == "charge" and damage != "missing" else [])
    if damage == "size":
        path.write_bytes(b"larger")
    elif damage == "checksum":
        path.write_bytes(b"edit")
    if damage == "none":
        repair._verify_tongji_converted_inputs()
        result = pd.read_csv(tmp_path / "reports" / "converted_source_verification.csv")
        assert result["sha256"].tolist() == [sha256]
    else:
        with pytest.raises(ValueError, match="size mismatch|checksum mismatch|differ from"):
            repair._verify_tongji_converted_inputs()


@pytest.mark.parametrize("state", ["current", "stale", "missing", "partial"])
def test_fingerprint_check_fails_for_stale_or_missing_manifests(monkeypatch, tmp_path, state):
    version = {"code_sha256": "current", "format_version": 1, "pandas": "test", "pyarrow": "test"}
    monkeypatch.setattr(fingerprint, "ROOT", tmp_path)
    monkeypatch.setattr(fingerprint, "cache_root", lambda: tmp_path / "_processed")
    monkeypatch.setattr(fingerprint, "code_version", lambda: version)
    monkeypatch.setattr(fingerprint.fielddata, "standard_systems", lambda package: pd.DataFrame({
        "unit": ["TSURU", "UGUISU"] if state == "partial" else ["TSURU"],
        "standard_status": ["supported", "supported"] if state == "partial" else ["supported"],
    }))
    monkeypatch.setattr(sys, "argv", ["layer2_code_fingerprint_check.py", "--packages", "birds_cubesat"])
    if state != "missing":
        path = tmp_path / "_processed" / "birds_cubesat" / "unit=TSURU" / "manifest.json"
        path.parent.mkdir(parents=True)
        stored = {**version, "code_sha256": "current" if state == "partial" else state}
        path.write_text(json.dumps({"unit": "TSURU", "code_version": stored}), encoding="utf-8")
    if state == "current":
        fingerprint.main()
    else:
        with pytest.raises(SystemExit, match="Missing or stale"):
            fingerprint.main()
    assert (tmp_path / "reports" / "checks" / "layer2_failed_releases" /
            "code_fingerprint_check.csv").is_file()


@pytest.mark.parametrize("package", ["tumftm", "m5bat-pbacid", "zhou2026"])
@pytest.mark.parametrize("processed_rows", [3, 2])
def test_full_loader_row_counts(monkeypatch, tmp_path, package, processed_rows):
    from fielddata.loaders import m5bat_pbacid

    monkeypatch.setattr(repair, "OUT", tmp_path)
    monkeypatch.setattr(repair.fielddata, "standard_systems", lambda package: pd.DataFrame({
        "unit": ["Pb1:bms"], "standard_status": ["supported"], "rows": [3],
    }))
    monkeypatch.setattr(repair.processed, "_read_manifest",
                        lambda package, unit: {"rows": processed_rows})

    def batches(**kwargs):
        assert kwargs == {"source": "bms", "columns": [], "chunksize": 1_000_000}
        yield pd.DataFrame(index=range(2))
        yield pd.DataFrame(index=range(1))

    monkeypatch.setattr(m5bat_pbacid, "iter_load", batches)
    if processed_rows == 3:
        repair._verify_loader_row_counts(package)
        result = pd.read_csv(tmp_path / "loader_row_counts.csv")
        assert result["loader_rows"].tolist() == [3]
        assert result["processed_rows"].tolist() == [3]
    else:
        with pytest.raises(AssertionError, match="row counts differ"):
            repair._verify_loader_row_counts(package)
