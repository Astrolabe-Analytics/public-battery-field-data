"""Synthetic mapping and sign regressions for every layer-1 release."""
from pathlib import Path

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

import fielddata
from fielddata._standard import MAPPINGS, UnsupportedStandard, from_raw, mapping


CURRENT_SIGNS = {
    "cao": ("DTI:0", -1), "schaeffer": ("1", 1), "ppl": ("E_W_Brown_BESS", 1),
    "xie": ("1", 1), "zhang2023": ("1", -1), "evbattery": ("1", -1), "aitio": ("1", -1),
    "beijing_ev": ("1", -1), "bilfinger2024": ("1", 1), "bilfinger2026": ("1", 1),
    "cloverleaf": ("1", 1), "changan": ("1", -1), "deng": ("1", -1),
    "ku_leuven_bev": ("1", -1), "li2026": ("1", -1), "m5bat-2023-04": ("1", -1),
    "m5bat-pbacid": ("Pb1:bms", -1), "pnnl_epri": ("1", -1), "rwth-home": ("1", 1),
    "rwth-android": ("1", 1), "tsukuba": ("1", -1), "zhou2026": ("1", -1),
}


@pytest.mark.parametrize("package", CURRENT_SIGNS)
def test_roundtrip_and_charging_sign(package, monkeypatch):
    unit, native_charge_sign = CURRENT_SIGNS[package]
    values = {column: [2.0, 3.0, np.nan] for column in MAPPINGS[package]}
    current_target = "current_c_rate" if package == "pnnl_epri" else "pack_current"
    current, _ = next((source, factor) for source, (target, factor) in MAPPINGS[package].items()
                      if target == current_target)
    values[current] = [5.0 * native_charge_sign, -3.0 * native_charge_sign, 0]
    raw = pd.DataFrame(values)
    if package == "cao":
        raw["cell_v_001"] = [3300.0, 0.0, 65535.0]
    elif package == "schaeffer":
        raw["Timestamp"] = pd.date_range("2024-01-01", periods=3, freq="s")
        raw["U_Cell_1"] = [3.3, 0, np.inf]
        raw["Temperature_1"] = [25, 26, 27]
    elif package == "xie":
        raw["batCoreVoltage1"] = [3300.0, 0, 65535]
        raw["batCoreTemp1"] = [25, 26, 27]
    if package in {"zhang2023", "evbattery"}:
        raw["timestamp"] = [30.0, 40, 50]
        raw["snippet"] = "a"
    if package == "beijing_ev":
        raw["time"] = [20240101000000, 20240101000010, 20240101000020]
    if package == "tongji_rest":
        raw["reqDate"] = pd.date_range("2024-01-01", periods=3, freq="s")
    if package == "rwth-android":
        raw["manufacturer"] = "Google"
    if package in {"ppl", "xie", "aitio"}:
        raw.index = pd.date_range("2024-01-01", periods=3, freq="s", tz="UTC")
    before = raw.copy(deep=True)
    loader = fielddata._loader(package)
    monkeypatch.setattr(loader, "load", lambda **kwargs: raw)
    if package == "ppl":
        monkeypatch.setattr(loader, "systems", lambda: pd.DataFrame({"years": [[2024]]}))
    standard = fielddata.standard(package, unit)
    for source, (target, multiplier) in mapping(package, raw, unit).items():
        np.testing.assert_allclose(standard[target].to_numpy() / multiplier, raw[source].to_numpy(),
                                   equal_nan=True, rtol=1e-12, atol=1e-12)
    assert standard[current_target].iloc[0] > 0
    assert standard[current_target].iloc[1] < 0
    assert standard[current_target].iloc[2] == 0
    if package in {"cao", "schaeffer", "xie"}:
        assert standard["cell_v_001"].iloc[0] == pytest.approx(3.3)
        assert standard["cell_v_001"].iloc[1] == 0
    assert standard["data_tier"].nunique() == 1
    assert "state" not in standard
    pdt.assert_frame_equal(raw, before)


@pytest.mark.parametrize("package", MAPPINGS)
def test_every_release_mapping_round_trips(package):
    unit = CURRENT_SIGNS.get(package, (None,))[0]
    if unit is None:
        unit = {"ppl": "E_W_Brown_BESS", "m5bat-pbacid": "Pb1:bms", "fei_bus": "vin1"}.get(package, "1")
    raw = pd.DataFrame({column: [2.0, 3.0, np.nan] for column in MAPPINGS[package]})
    if package == "schaeffer":
        raw["Timestamp"] = pd.date_range("2024-01-01", periods=3, freq="s")
    elif package == "beijing_ev":
        raw["time"] = [20240101000000, 20240101000010, 20240101000020]
    elif package == "tongji_rest":
        raw["reqDate"] = pd.date_range("2024-01-01", periods=3, freq="s")
    elif package == "shenzhen_charging":
        raw["end_time"] = pd.date_range("2024-01-01", periods=3, freq="s")
    elif package == "stanford_ev":
        raw["t"] = [0.0, 1.0, 2.0]
        raw["session"] = "20240101_000000"
    elif package in {"zhang2023", "evbattery"}:
        raw["timestamp"] = [30.0, 40.0, 50.0]
        raw["snippet"] = "synthetic"
    elif package == "rwth-android":
        raw["manufacturer"] = "Google"
    original = raw.copy(deep=True)
    result = from_raw(package, unit, raw)
    for source, (target, factor) in mapping(package, raw, unit).items():
        np.testing.assert_allclose(result[target].to_numpy() / factor, raw[source].to_numpy(),
                                   equal_nan=True, rtol=1e-12, atol=1e-12)
    pdt.assert_frame_equal(raw, original)


def test_tongji_invalid_calendar_value_is_preserved():
    raw = pd.DataFrame({
        "reqDate": ["not-a-time", None],
        "totalCurrent": [-2.0, -3.0],
        "segment": ["segment_1.pkl", "segment_2.pkl"],
    })
    standard = from_raw("tongji_rest", "NMC01_Car02", raw)
    assert standard["time"].isna().tolist() == [True, True]
    assert standard["source__reqDate"].tolist()[0] == "not-a-time"
    assert pd.isna(standard["source__reqDate"].iloc[1])
    assert standard["source__segment"].tolist() == ["segment_1.pkl", "segment_2.pkl"]


def test_changan_sensor_quote_artifacts_and_invalid_values_are_preserved():
    probes = ["\\24\\\"", "\\\"24\\\"", "not-a-number"] + ["25"] * 29
    raw = pd.DataFrame({
        "totalcurrent": [-2.0, -3.0],
        "probetemperatures": ["~".join(probes), None],
    })
    original = raw.copy(deep=True)
    standard = from_raw("changan", "vin1", raw)

    assert standard["temp_001"].iloc[0] == 24
    assert standard["temp_002"].iloc[0] == 24
    assert pd.isna(standard["temp_003"].iloc[0])
    assert standard["source__probetemperatures"].iloc[0] == original["probetemperatures"].iloc[0]
    assert standard.filter(regex=r"^temp_").iloc[1].isna().all()
    assert pd.isna(standard["source__probetemperatures"].iloc[1])
    pdt.assert_frame_equal(raw, original)


def test_stanford_stream_uses_session_start_and_selected_signal(monkeypatch):
    from fielddata.loaders import stanford_ev

    sessions = ["20240101_000000", "20240102_120000"]
    monkeypatch.setattr(stanford_ev, "sessions", lambda: pd.DataFrame({"session": sessions}))

    def load(session, signal, clean):
        return pd.DataFrame({"session": [session, session], "t": [0.0, 2.0],
                             "V_cell_bms_1": [3.4, 3.5]})

    monkeypatch.setattr(stanford_ev, "load", load)
    result = list(fielddata.iter_standard("stanford_ev", "EV1", signal="V_cell_bms"))
    assert [frame["cell_v_001"].tolist() for frame in result] == [[3.4, 3.5], [3.4, 3.5]]
    assert result[0]["time"].tolist() == list(pd.to_datetime(["2024-01-01 00:00:00", "2024-01-01 00:00:02"]))
    assert result[0]["data_tier"].tolist() == ["session", "session"]


def test_schaeffer_retains_all_temperature_and_balancing_channels():
    raw = pd.DataFrame({
        "Timestamp": pd.date_range("2024-01-01", periods=1),
        **{f"Temperature_{index}": [20.0 + index] for index in range(1, 5)},
        **{f"I_CNV_Cell_{index}": [0.1 * index] for index in range(1, 9)},
    })
    result = from_raw("schaeffer", "1", raw)
    assert [f"temp_{index:03d}" for index in range(1, 5)] == [
        column for column in result if column.startswith("temp_")
    ]
    assert [f"balance_current_{index:03d}" for index in range(1, 9)] == [
        column for column in result if column.startswith("balance_current_")
    ]
    assert result.loc[0, "temp_004"] == 24.0
    assert result.loc[0, "balance_current_008"] == 0.8


def test_missing_columns_not_synthesized():
    raw = pd.DataFrame({"current_A": [-1]}, index=pd.to_datetime(["2020-01-01"], utc=True))
    result = from_raw("aitio", "1", raw)
    assert "soc" not in result and "pack_voltage" not in result and "cell_v_max" not in result


def test_encoded_and_average_voltage_not_pack_voltage():
    raw = pd.DataFrame({"volt": [123.0], "timestamp": [90.0], "snippet": ["a"]})
    zhang = from_raw("zhang2023", "battery_brand1:1", raw)
    ev = from_raw("evbattery", "battery_dataset1:1", raw)
    assert "pack_voltage" not in zhang and "pack_voltage" not in ev
    assert zhang["source__volt"].iloc[0] == 123
    assert ev["cell_v_mean"].iloc[0] == 123
    assert zhang["elapsed_time_s"].iloc[0] == 0
    assert zhang["source_time_s"].iloc[0] == 90
    assert "time" not in zhang


def test_ppl_timezone_and_schema_epochs():
    old = pd.DataFrame({"CellVoltMax": [3.4]}, index=pd.to_datetime(["2020-01-01"], utc=True))
    new = pd.DataFrame({"DCCurrent": [3.0]}, index=pd.to_datetime(["2024-01-01"], utc=True))
    a = from_raw("ppl", "E_W_Brown_BESS", old)
    b = from_raw("ppl", "E_W_Brown_BESS", new)
    assert a["time"].dt.tz is None
    assert "pack_current" not in a and "cell_v_max" not in b
    assert a["data_tier"].iloc[0] == "max-min" and b["data_tier"].iloc[0] == "pack-only"


@pytest.mark.parametrize("years", [None, [2022, 2021]])
def test_ppl_combined_view_preserves_each_input_schema_tier(monkeypatch, years):
    from fielddata.loaders import ppl

    frames = {
        2021: pd.DataFrame({"CellVoltMax": [3.4]}, index=pd.to_datetime(["2022-01-01"], utc=True)),
        2022: pd.DataFrame({"DCCurrent": [np.nan]}, index=pd.to_datetime(["2022-01-01"], utc=True)),
    }
    calls = []

    def load(years, **kwargs):
        calls.append(years)
        assert kwargs == {"clean": False}
        return frames[years[0]]

    monkeypatch.setattr(ppl, "load", load)
    monkeypatch.setattr(ppl, "systems", lambda: pd.DataFrame({"years": [[2021, 2022]]}))
    result = fielddata.standard("ppl", years=years, clean=False)
    assert calls == [[2021], [2022]]
    assert result["data_tier"].tolist() == ["max-min", "pack-only"]
    assert result["time"].nunique() == 1
    assert result["pack_current"].isna().all()
    assert result["cell_v_max"].tolist()[0] == 3.4
    assert pd.isna(result["cell_v_max"].iloc[1])
    assert result.attrs["data_tiers"] == ["max-min", "pack-only"]
    assert "data_tier" not in result.attrs


def test_ppl_empty_year_selection_is_explicit():
    with pytest.raises(ValueError, match="no annual ESS files selected"):
        fielddata.standard("ppl", years=[])


def test_cao_gis_error_names_unit_and_reason():
    with pytest.raises(UnsupportedStandard, match="cao GIS:4: column meanings not established"):
        fielddata.standard("cao", "GIS:4")


def test_cao_model_outputs_are_not_mapped_as_telemetry():
    with pytest.raises(ValueError, match="vin_2 telemetry only"):
        fielddata.standard("cao", "QAS:0", which="vin_3")


def test_cao_qas_cell_voltage_is_already_volts():
    frame = from_raw("cao", "QAS:0", pd.DataFrame({"cell_v_001": [3.2, 65535.0]}))
    assert frame["cell_v_001"].tolist() == [3.2, 65535.0]


def test_tier_inventory_retains_blocked_and_empty(monkeypatch):
    from fielddata.loaders import cao, zhang2023
    monkeypatch.setattr(cao, "systems", lambda: pd.DataFrame({"brand": ["DTI", "GIS"], "vehicle": ["0", "1"]}))
    table = fielddata.standard_systems("cao")
    assert table["standard_status"].tolist() == ["supported", "blocked"]
    assert pd.isna(table["data_tier"].iloc[1])
    monkeypatch.setattr(zhang2023, "systems", lambda: pd.DataFrame({"unit": ["a", "b"], "snippets": [1, 0]}))
    assert fielddata.standard_systems("zhang2023")["standard_status"].tolist() == ["supported", "empty"]


def test_snippet_batch_matches_raw_reader():
    from fielddata.loaders import _snippets
    records = [(f"data/{i}.pkl", np.ones((3, 8)), {"car": 1, "label": "00", "charge_segment": i}) for i in range(2)]
    expected = pd.concat([_snippets.snippet_frame(*record) for record in records], ignore_index=True)
    pdt.assert_frame_equal(_snippets.snippet_batch(records), expected)


def test_schaeffer_balancing_currents_are_exposed():
    raw = pd.DataFrame({"Timestamp": pd.to_datetime(["2024-01-01"]), "I_Battery": [1.0],
                        "I_CNV_Cell_1": [0.2], "I_CNV_Cell_8": [0.8], "Temperature_4": [25.0]})
    view = from_raw("schaeffer", "3", raw)
    assert view["balance_current_001"].tolist() == [0.2]
    assert view["balance_current_008"].tolist() == [0.8]
    assert view["temp_004"].tolist() == [25.0]


def test_standard_falls_back_to_central_mapping_for_loaders_without_wrapper(monkeypatch):
    from fielddata.loaders import beijing_ev

    raw = pd.DataFrame({"time": pd.to_datetime(["2024-01-01"]), "voltage": [350.0], "current": [-20.0], "soc": [90]})
    monkeypatch.setattr(beijing_ev, "load", lambda **kwargs: raw)
    result = fielddata.standard("beijing_ev", "2018-01-03")
    assert result["pack_voltage"].tolist() == [350.0]
    assert result["pack_current"].tolist() == [20.0]
    assert result["soc"].tolist() == [90]


def test_m5bat_pbacid_units_include_source(monkeypatch):
    released = pd.DataFrame({"unit": ["Pb1", "Pb1"], "source": ["bms", "bsc"]})
    monkeypatch.setattr(fielddata, "systems", lambda package: released)
    table = fielddata.standard_systems("m5bat-pbacid")
    assert set(table["unit"]) == {"Pb1:bms", "Pb1:bsc"}


def test_public_batch_conversion_is_pure_and_rejects_mixed_units(monkeypatch):
    def unexpected_io(*args, **kwargs):
        raise AssertionError("conversion must not read released data")

    monkeypatch.setattr(fielddata, "load", unexpected_io)
    raw = pd.DataFrame({"totalCurrent": [4.0], "batCoreVoltage1": [3300.0], "unit": ["a"]},
                       index=pd.to_datetime(["2024-01-01"], utc=True))
    before = raw.copy(deep=True)
    result = fielddata.standardize("xie", "a", raw)
    assert result["cell_v_001"].iloc[0] == pytest.approx(3.3)
    pdt.assert_frame_equal(raw, before)
    with pytest.raises(ValueError, match="another unit"):
        fielddata.standardize("xie", "b", raw)


@pytest.mark.parametrize("entry", ["iter_standard", "standard"])
def test_schaeffer_standard_stream_reads_once_and_preserves_order(monkeypatch, entry):
    from fielddata.loaders import schaeffer

    raw = pd.DataFrame({"Timestamp": pd.to_datetime(["2024-02-01", "2024-01-01", "2024-01-01"]),
                        "I_Battery": [3.0, -2.0, 0.0], "U_Cell_1": [3.3, 0.0, np.inf]})
    calls = []

    def load(**kwargs):
        calls.append(kwargs)
        return iter([raw.iloc[:2], raw.iloc[2:]])

    monkeypatch.setattr(schaeffer, "load", load)
    stream = getattr(fielddata, entry)("schaeffer", "3", chunksize=2, clean=True)
    assert calls == []
    actual = pd.concat(list(stream), ignore_index=True)
    pdt.assert_frame_equal(actual, fielddata.standardize("schaeffer", "3", raw))
    assert calls == [{"system": 3, "chunksize": 2, "clean": True}]


@pytest.mark.parametrize("package", ["zhang2023", "evbattery"])
def test_archive_standard_stream_scans_once_and_keeps_snippets(monkeypatch, package):
    from fielddata.loaders._snippets import snippet_frame

    loader = fielddata._loader(package)
    archive = "battery_brand1.tar.gz" if package == "zhang2023" else "battery_dataset1.tar.gz"
    array = np.zeros((2, 8))
    array[:, 1] = [-5, -3]
    array[:, 7] = [90, 100]
    records = [(f"data/{i}.pkl", array, {"car": car, "charge_segment": i, "label": "00"})
               for i, car in enumerate([2, 1, 2])]
    calls = []

    def snippets(name):
        calls.append(name)
        yield from records

    monkeypatch.setattr(loader, "systems", lambda: pd.DataFrame({"archive": [archive]}))
    monkeypatch.setattr(loader, "iter_snippets", snippets)
    stream = fielddata.iter_standard(package, archive=archive)
    assert calls == []
    chunks = list(stream)
    assert calls == [archive]
    assert [chunk["unit"].iloc[0] for chunk in chunks] == [
        f"{archive.removesuffix('.tar.gz')}:{car}" for car in [2, 1, 2]]
    for chunk, record in zip(chunks, records):
        expected = fielddata.standardize(package, chunk["unit"].iloc[0], snippet_frame(*record))
        pdt.assert_frame_equal(chunk, expected)
        assert chunk["pack_current"].tolist() == [5, 3]
        assert chunk["elapsed_time_s"].tolist() == [0, 10]


def test_xie_bulk_standard_uses_one_loader_call(monkeypatch):
    from fielddata.loaders import xie

    raw = pd.DataFrame({"unit": ["a", "b", "a"], "totalCurrent": [1, 2, 3],
                        "batCoreVoltage1": [3300, 3400, 3500]},
                       index=pd.to_datetime(["2024-01-01"] * 3, utc=True))
    calls = []

    def load(**kwargs):
        calls.append(kwargs)
        return raw

    monkeypatch.setattr(xie, "load", load)
    result = fielddata.standard("xie", ["b", "a"], clean=True)
    assert calls == [{"unit": ["b", "a"], "clean": True}]
    assert result["unit"].tolist() == ["b", "a", "a"]
    assert result["pack_current"].tolist() == [2, 1, 3]
    assert result.attrs["units_selected"] == ["b", "a"]
    assert "unit" not in result.attrs


@pytest.mark.parametrize("kwargs", [{"chunksize": 0}, {"chunksize": True}, {"archive": "bad"}])
def test_invalid_stream_arguments_are_explicit(kwargs):
    with pytest.raises(ValueError):
        list(fielddata.iter_standard("schaeffer", "3", **kwargs))


def test_stream_propagates_loader_read_error(monkeypatch):
    from fielddata.loaders import schaeffer

    def load(**kwargs):
        yield pd.DataFrame({"Timestamp": pd.to_datetime(["2024-01-01"]), "I_Battery": [1]})
        raise OSError("synthetic interrupted read")

    monkeypatch.setattr(schaeffer, "load", load)
    stream = fielddata.iter_standard("schaeffer", "3")
    assert next(stream)["pack_current"].tolist() == [1]
    with pytest.raises(OSError, match="interrupted read"):
        next(stream)


@pytest.mark.parametrize("units", [[], ["a", "a"]])
def test_xie_bulk_invalid_selection_is_error(units):
    with pytest.raises(ValueError, match="nonempty list of distinct units"):
        fielddata.standard("xie", units)


@pytest.mark.parametrize("package", MAPPINGS)
def test_schema_baseline_and_every_mapping_row_has_evidence(package):
    root = Path(__file__).resolve().parents[1]
    schema_name = package.replace("-", "_")
    text = (root / "fielddata" / "loaders" / f"{schema_name}_SCHEMA.md").read_text(encoding="utf-8")
    section = text.split("## Standard view", 1)[1].split("\n## ", 1)[0]
    table = section[section.index("| Authors'"):].split("\n\n", 1)[0]
    lines = table.splitlines()
    assert "Meaning and check evidence" in lines[0]
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert len(cells) == 4 and cells[3], line
    assert "native current sign" in section.lower()
    assert "GB/T 32960" in section
