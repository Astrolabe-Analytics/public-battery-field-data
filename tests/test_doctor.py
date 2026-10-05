"""The setup check must work on an empty data folder and expand 'A through B' file ranges."""
from pathlib import Path

from fielddata import doctor
from fielddata.registry import PACKAGES


def test_ranges_expand():
    assert len(doctor.expected_files("deng")) == 20
    assert "Data_ID_07.zip" in doctor.expected_files("rwth-home")


def test_missing_and_misnamed_folders(tmp_path):
    problems = doctor.check_package(tmp_path, "flashbattery-agv")
    assert problems and "python -m fielddata.fetch flashbattery-agv" in problems[0]
    top = Path(PACKAGES["flashbattery-agv"]["data_directory"]).parts[0]
    (tmp_path / (top.lower() + " ")).mkdir()
    assert "rename it" in doctor.check_package(tmp_path, "flashbattery-agv")[0]


def test_every_release_is_checkable(tmp_path):
    for package in PACKAGES:
        assert doctor.check_package(tmp_path, package)


def _held(tmp_path, package, name, content):
    folder = tmp_path / PACKAGES[package]["data_directory"]
    folder.mkdir(parents=True)
    (folder / name).write_bytes(content)
    return folder


def test_partly_downloaded_file_is_incomplete_not_ready(tmp_path):
    _held(tmp_path, "cloverleaf", "Monitoring data 2nd life battery.zip", b"only the first bytes")
    problems = doctor.check_package(tmp_path, "cloverleaf")
    assert problems and problems[0].startswith("incomplete:") and "expected 7,593,131" in problems[0]


def test_wrong_checksum_at_the_right_size_is_incomplete(tmp_path, monkeypatch):
    content = b"same size, different bytes"
    _held(tmp_path, "cloverleaf", "Monitoring data 2nd life battery.zip", content)
    reference = {"Monitoring data 2nd life battery.zip": {"bytes": len(content), "algorithm": "md5", "expected": "0" * 32}}
    monkeypatch.setattr(doctor, "reference_files", lambda package: reference)
    problems = doctor.check_package(tmp_path, "cloverleaf")
    assert problems and problems[0].startswith("incomplete:") and "checksum" in problems[0]
    import hashlib
    reference["Monitoring data 2nd life battery.zip"]["expected"] = hashlib.md5(content).hexdigest()
    assert doctor.check_package(tmp_path, "cloverleaf") == []


def test_renamed_release_folder_is_found_by_its_files(tmp_path):
    (tmp_path / "my downloads" / "data").mkdir(parents=True)
    (tmp_path / "my downloads" / "data" / "Monitoring data 2nd life battery.zip").write_bytes(b"x")
    problems = doctor.check_package(tmp_path, "cloverleaf")
    assert len(problems) == 1 and "found under 'my downloads'" in problems[0] and "fielddata.fetch" not in problems[0]


def test_another_release_folder_is_not_taken_for_a_renamed_one(tmp_path):
    _held(tmp_path, "tsukuba", "294ecef46cba01f6392560efe6c78a28.zip", b"x")
    assert "python -m fielddata.fetch cloverleaf" in doctor.check_package(tmp_path, "cloverleaf")[0]
