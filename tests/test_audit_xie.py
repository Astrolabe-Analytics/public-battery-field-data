"""Synthetic tests for the xie source-audit changes: archive member listing and multi-class device labels.

A RAR archive cannot be written here, so a stand-in ``libarchive`` module serves the members.
"""
import contextlib
import sys
import types

import pandas as pd
import pytest

from fielddata.loaders import _base, xie


class _Entry:
    def __init__(self, name, data):
        self.pathname = name
        self._data = data

    def get_blocks(self):
        yield self._data


@pytest.fixture
def fake_archive(monkeypatch, tmp_path, package_directory):
    monkeypatch.setattr(_base, "data_root", lambda: tmp_path)
    package_directory("xie")
    records = pd.DataFrame({"filename": ["a.csv", "b.csv", "b.csv", "c.csv"], "device_label": [5, 4, 1, 3],
                            "corrMinMaxVoltages": [0.9, 0.5, 0.5, 0.7], "permutationEntropy": [1, 1, 1, 1],
                            "dtwDistance": [10, 2000, 2000, 1500], "KLDivergence": [0, 0, 0, 0]})
    device = pd.DataFrame({"dateTime": [1727971205000, 1727971225000], "totalCurrent": [0.0, 5.0],
                           "batCoreTempCount": [5, 5], "batCoreVoltage1": [3300, 3350]}).to_csv(index=False).encode()
    members = {"fullDataset/fullDataset.json": b"{}",
               "predefinedDataset/processedData/predefined_device_records.csv": records.to_csv(index=False).encode(),
               "predefinedDataset/data/a.csv": device, "predefinedDataset/data/b.csv": device,
               "predefinedDataset/data/c.csv": device}

    @contextlib.contextmanager
    def file_reader(path):
        yield [_Entry(n, d) for n, d in members.items()]

    monkeypatch.setitem(sys.modules, "libarchive", types.SimpleNamespace(file_reader=file_reader))
    return members


def test_members_lists_by_prefix(fake_archive):
    assert xie.members("predefinedDataset/processedData/") == ["predefinedDataset/processedData/predefined_device_records.csv"]
    assert len(xie.members()) == len(fake_archive)


def test_systems_keeps_every_fault_code(fake_archive):
    table = xie.systems().set_index("unit")
    assert table.index.tolist() == ["a", "b", "c"]
    assert table.loc["b", "fault_codes"] == "1,4" and table.loc["b", "device_label"] == 4
    assert table.loc["a", "fault_codes"] == "5" and table.loc["c", "fault_codes"] == "3"


def test_load_reads_device(fake_archive):
    frame = xie.load("a")
    assert frame["batCoreVoltage1"].tolist() == [3300, 3350] and str(frame.index.tz) == "UTC"
