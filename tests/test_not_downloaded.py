"""A release that is not downloaded gives the fetch command, not a traceback from deep inside a loader."""
import pandas as pd
import pytest

import fielddata
from fielddata import doctor, quickstart, verify
from fielddata.registry import PACKAGES, metadata


@pytest.fixture
def empty_root(tmp_path, monkeypatch):
    monkeypatch.setenv("FIELDDATA_DATA_ROOT", str(tmp_path))
    return tmp_path


@pytest.mark.parametrize("package", list(PACKAGES))
def test_every_release_says_how_to_fetch(empty_root, package):
    message = f"Release {package} is not downloaded yet. Run: python -m fielddata.fetch {package}"
    try:  # some releases list their units from the registry, without the data
        fielddata.systems(package)
    except fielddata.NotDownloaded as err:
        assert str(err) == message
    with pytest.raises(fielddata.NotDownloaded) as err:
        quickstart.sample(package)
    assert str(err.value) == message


def test_it_is_a_file_not_found_error_shown_without_traceback(empty_root):
    with pytest.raises(FileNotFoundError) as err:
        fielddata.load("cloverleaf")
    assert err.value._render_traceback_() == [str(err.value)]


def test_a_missing_file_in_a_present_release_is_named(empty_root):
    folder = empty_root / metadata("cloverleaf")["data_directory"]
    folder.mkdir(parents=True)
    (folder / "unrelated.txt").write_text("x")
    with pytest.raises(fielddata.NotDownloaded) as err:
        fielddata.systems("cloverleaf")
    assert "Release cloverleaf is missing" in str(err.value)
    assert "python -m fielddata.fetch cloverleaf" in str(err.value)


def test_doctor_before_the_first_download(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FIELDDATA_DATA_ROOT", str(tmp_path / "not-yet"))
    assert doctor.main(["cloverleaf"]) == 1
    out = capsys.readouterr().out
    assert "No data downloaded yet. Run python -m fielddata.fetch <release>; it creates the folder." in out
    assert "Create it" not in out


def test_verify_summary_when_the_host_publishes_no_checksums():
    own = pd.Series(["no publisher checksum"] * 16)
    assert verify.summary(own, 0) == "16 files checked: host publishes no checksums; our SHA-256 recorded. 0 mismatches or errors."
    mixed = pd.Series(["match", "match", "no publisher checksum"])
    assert verify.summary(mixed, 0) == "3 files checked: 2 match a publisher checksum, 1 with no publisher checksum (our SHA-256 recorded), 0 mismatches or errors."
    assert verify.summary(pd.Series(["match"]), 0) == "1 files checked: 1 match a publisher checksum, 0 mismatches or errors."
