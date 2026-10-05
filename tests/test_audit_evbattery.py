"""Source audit 2026-10-04: evbattery and zhang2023 snippets are returned as released (synthetic data only).

The schema notes state that the metadata label is the string "10" or "00", that unlabeled snippets carry
capacity 0, and that charging current is negative. The loader must pass these through unchanged, with or
without clean=True.
"""
import io
import pickle
import tarfile

import numpy as np
import pytest

import fielddata
from fielddata.loaders import _base, _snippets


@pytest.fixture
def root(monkeypatch, tmp_path):
    monkeypatch.setattr(_base, "data_root", lambda: tmp_path)
    monkeypatch.setattr(_snippets, "index_path", lambda package: tmp_path / f"{package}_index.csv")
    return tmp_path


def _write(path, members):
    with tarfile.open(path, "w:gz") as tar:
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


def _snippet(current, car, label, **meta):
    array = np.zeros((128, 8))
    array[:, 0] = 3.9
    array[:, 1] = current
    array[:, 2] = np.linspace(40, 45, 128)
    array[:, 7] = np.arange(128) * 10.0
    return pickle.dumps((array, {"car": car, "label": label, "charge_segment": "7", "mileage": 123.4, **meta}))


@pytest.mark.parametrize("clean", [False, True])
def test_evbattery_metadata_and_sign_as_released(root, package_directory, clean):
    d = package_directory("evbattery")
    _write(d / "battery_dataset3.tar.gz", [
        ("battery_dataset3/label/label.csv", b"car,label\n500,1\n545,0\n"),
        ("battery_dataset3/data/1.pkl", _snippet(-35.0, 500, "10", capacity=0)),
        ("battery_dataset3/data/2.pkl", _snippet(-20.0, 500, "10", capacity=39.03)),
    ])
    index = _snippets.build_index("evbattery", "battery_dataset3.tar.gz")
    assert index.set_index("car")["snippets"].to_dict() == {500: 2, 545: 0}
    frame = fielddata.load("evbattery", unit="battery_dataset3:500", clean=clean)
    assert len(frame) == 256
    assert set(frame["label"]) == {"10"}
    assert sorted(set(frame["capacity"])) == [0, 39.03]
    assert (frame["current"] < 0).all() and sorted(set(frame["current"])) == [-35.0, -20.0]
    assert frame["timestamp"].diff().dropna().isin([10.0, -1270.0]).all()
    assert frame.attrs["masked_value_count"] == 0


def test_zhang2023_label_code_as_released(root, package_directory):
    d = package_directory("zhang2023")
    _write(d / "battery_brand2.tar.gz", [
        ("battery_brand2/label/all_label.csv", b"car,label\n201,0\n"),
        ("battery_brand2/data/1.pkl", _snippet(0.0, 201, "00")),
    ])
    _snippets.build_index("zhang2023", "battery_brand2.tar.gz")
    frame = fielddata.load("zhang2023", unit="battery_brand2:201", clean=True)
    assert set(frame["label"]) == {"00"} and (frame["current"] == 0).all() and "capacity" not in frame
