"""rise_conbat candidate loader on a synthetic zip: installations, distinct modules and one window's file."""
import zipfile

from fielddata.registry import CANDIDATES, PACKAGES

INFO = ("id,car,disassembly_date,cells_in_series,nominal_energy_conversion,model_number,container,rack,string,module,start_date,car_model,end_date\n"
        "S370751-1,S370751,2017-07-08,12,9.9,X,1,1,1,1,2022-12-31 23:00:00+00,VW Passat 20-,2023-04-25 22:00:00+00\n"
        "H406450-1,H406450,2020-01-04,12,9.9,X,1,1,1,1,2023-11-27 00:00:00+00,VW Passat 15-,\n"
        "S370751-1,S370751,2017-07-08,12,9.9,X,1,1,2,1,2023-12-01 00:00:00+00,VW Passat 20-,\n")
FIRST = "cells_in_series,battery_chemistry,nominal_energy_conversion,milage,car_model,container,rack,string,module,module_uuid,start_date\n"
BESS = "id,car,disassembly_date,cells_in_series,nominal_energy_conversion,model_number,container,rack,string,module,start_date,car_model\n"
MODULE = ("hour,module_uuid,location,rack,shelf,module,voltage,voltage_is_filler,temperature,temperature_is_filler\n"
          "2024-05-01 00:00:00+00,H406450-1,3,1,2,1,50.006,f,23.68,f\n"
          "2024-05-01 00:00:00+00,S370751-1,3,1,2,2,49.99,t,23.4,f\n")


def test_rise_reads_modules_and_windows(monkeypatch, tmp_path, package_directory):
    from fielddata.loaders import rise_conbat

    folder = package_directory("rise_conbat")
    with zipfile.ZipFile(folder / rise_conbat.ARCHIVE, "w") as archive:
        archive.writestr("11. 240501-241104/db-export-module-info.csv", INFO)
        archive.writestr("11. 240501-241104/db-export-module.csv", MODULE)
        archive.writestr("1. 230420-230516/db-export-module-info.csv", FIRST)
        archive.writestr("BESS/9. 240207-240214/db-export-module-info.csv", BESS)
    monkeypatch.setattr("fielddata.loaders._base.data_root", lambda: tmp_path)

    modules = rise_conbat.systems().set_index("unit")
    assert len(modules) == 2 and modules.loc["S370751-1", "installations"] == 2
    assert modules["last_end"].isna().all()  # both still installed at the last export
    rows = rise_conbat.load("11. 240501-241104", "module", unit="H406450-1")
    assert rows["voltage"].tolist() == [50.006] and rows["voltage_is_filler"].tolist() == ["f"]
    assert list(rise_conbat.windows()["window"]) == ["1. 230420-230516", "BESS/9. 240207-240214", "11. 240501-241104"]


def test_rise_is_a_package():
    assert "rise_conbat" in PACKAGES and "rise_conbat" not in CANDIDATES  # admitted in v1.2
