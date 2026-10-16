"""stanford_ev candidate loader on synthetic MATLAB files: one session, signals read unchanged."""
import numpy as np
import pytest

from fielddata.registry import CANDIDATES, PACKAGES


def test_stanford_reads_signals_unchanged(monkeypatch, tmp_path, package_directory):
    savemat = pytest.importorskip("scipy.io").savemat
    from fielddata.loaders import stanford_ev

    root = package_directory("stanford_ev")
    driving = root / "Field Dataset" / "Driving"
    (root / "Field Dataset" / "Charging").mkdir(parents=True)
    driving.mkdir(parents=True)
    savemat(driving / "20210921_234539.mat", {
        "I_pack_bms": {"data": np.array([1.5, -2.0]), "t": np.array([0.0, 0.01])},
        "V_cell_bms": {"data": np.array([[3.8, 3.81, 3.79]]), "t": np.array([0.0])},
        "T_pack_bms": {"data": np.array([20, 21], dtype=np.uint8), "time": np.array([0.0, 0.5])},
        "Mileage_bms": 4748})
    lab = root / "Laboratory Dataset" / "First Laboratory Campaign" / "GITT"
    lab.mkdir(parents=True)
    savemat(lab / "Module_01.mat", {"time_lab": np.array([[0.0], [1.0]]), "V_Cell_lab": np.array([[3.7, 3.7, 3.6], [3.7, 3.6, 3.6]])})
    (lab / "Module_02.mat").write_bytes(b"")
    monkeypatch.setattr("fielddata.loaders._base.data_root", lambda: tmp_path)

    vehicle = stanford_ev.systems()
    assert vehicle.loc[0, "driving_sessions"] == 1 and "CC BY-NC-ND" in vehicle.loc[0, "license"]
    current = stanford_ev.load("20210921_234539", "I_pack_bms")
    assert current["I_pack_bms"].tolist() == [1.5, -2.0] and current["t"].tolist() == [0.0, 0.01]
    cells = stanford_ev.load("20210921_234539", "V_cell_bms")
    assert list(cells.columns) == ["session", "t", "V_cell_bms_1", "V_cell_bms_2", "V_cell_bms_3"]
    assert stanford_ev.load("20210921_234539", "T_pack_bms")["T_pack_bms"].tolist() == [20, 21]
    assert stanford_ev.mileage("20210921_234539") == 4748
    files = stanford_ev.lab_files()
    assert files["bytes"].tolist() == [mat.stat().st_size for mat in sorted(lab.glob("*.mat"))]
    assert stanford_ev.load_lab("First Laboratory Campaign/GITT/Module_01.mat")["V_Cell_lab_3"].tolist() == [3.6, 3.6]
    assert stanford_ev.load_lab("First Laboratory Campaign/GITT/Module_02.mat").empty


def test_stanford_is_a_package_and_loader_only():
    assert "stanford_ev" in PACKAGES and "stanford_ev" not in CANDIDATES  # admitted in v1.2
    assert "no converted or derived data files" in PACKAGES["stanford_ev"]["derived_outputs"]
