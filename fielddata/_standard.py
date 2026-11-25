"""Layer 1 mappings. No cleaning, event inference, resampling or gap filling."""
from __future__ import annotations

import re
from collections.abc import Iterator

import numpy as np
import pandas as pd
from fielddata.registry import PACKAGES as REGISTRY_PACKAGES

PACKAGES = tuple(REGISTRY_PACKAGES)
TIERS = {"cao": "per-cell", "schaeffer": "per-cell", "ppl": "max-min",
         "xie": "per-cell", "zhang2023": "session", "evbattery": "session", "aitio": "pack-only",
         "beijing_ev": "session", "flashbattery-agv": "session", "changan": "per-cell",
         "rwth-android": "per-cell", "shenzhen_charging": "session", "tumftm": "session",
         "ved": "session", "stanford_ev": "session", "tongji_rest": "per-cell",
         "li2026": "per-cell", "zhou2026": "per-cell", "fei_bus": "pack-only",
         "cloverleaf": "max-min", "ku_leuven_bev": "max-min", "pnnl_epri": "max-min",
         "deng": "max-min", "li2026_evfault": "per-cell", "giu_ebike": "per-cell"}
NATIVE_SIGNS = {"cao": "discharge positive (DTI/QAS only)", "schaeffer": "charge positive",
                "ppl": "charge positive (DC current), discharge positive (AC power)",
                "xie": "charge positive (inferred)", "zhang2023": "charge negative (observed)",
                "evbattery": "charge negative (observed)", "aitio": "charge negative",
                "beijing_ev": "discharge positive (inferred)",
                "bilfinger2024": "charge positive (observed on charge records)",
                "bilfinger2026": "charge positive on charge records; discharge negative",
                "cloverleaf": "charge positive (inferred from SOC)",
                "changan": "discharge positive (SI Table 2)",
                "deng": "charge negative (paper)",
                "ku_leuven_bev": "discharge positive (observed)",
                "li2026": "discharge positive (paper)",
                "m5bat-2023-04": "discharge positive (current inferred; power stated)",
                "m5bat-pbacid": "discharge positive (codebook)",
                "pnnl_epri": "discharge positive (author code)",
                "bilfinger2025": "charge positive in observed charging records; mixed signs in one balancing file",
                "birds_cubesat": "not stated in the paper",
                "brazil_star": "not established; negative current may be unsigned-encoded",
                "shenzhen_charging": "not stated in the release documentation",
                "tongji_rest": "charge negative (inferred from source data)",
                "ved": "not established; retained as a source-named field",
                "rwth-android": "charge positive except OnePlus and Xiaomi devices",
                "rwth-home": "charge positive (paper and SI)",
                "tsukuba": "discharge positive (observed)",
                "zhou2026": "discharge positive (paper)",
                "li2026_evfault": "no current released",
                "giu_ebike": "discharge positive (README)"}

# source: (standard name, multiplier). Unlisted author columns remain namespaced.
MAPPINGS = {
    "cao": {"current_A": ("pack_current", -1), "soc_pct": ("soc", 1),
            "temperature_degC": ("temperature", 1)},
    "schaeffer": {"U_Battery": ("pack_voltage", 1), "I_Battery": ("pack_current", 1),
                  "SOC_Battery": ("soc", 1)},
    "ppl": {"DCVoltage": ("pack_voltage", 1), "DCCurrent": ("pack_current", 1),
            "AvgSOC": ("soc", 1), "SOH": ("soh", 1), "PowerReal": ("ac_power", -1),
            "CellVoltAvg": ("cell_v_mean", 1), "CellVoltMax": ("cell_v_max", 1),
            "CellVoltMin": ("cell_v_min", 1), "ModuleTempMax": ("temp_max", 1),
            "ModuleTempMin": ("temp_min", 1)},
    "xie": {"totalCurrent": ("pack_current", 1)},
    "zhang2023": {"current": ("pack_current", -1), "soc": ("soc", 1),
                  "max_single_volt": ("cell_v_max", 1), "min_single_volt": ("cell_v_min", 1),
                  "max_temp": ("temp_max", 1), "min_temp": ("temp_min", 1)},
    "evbattery": {"volt": ("cell_v_mean", 1), "current": ("pack_current", -1), "soc": ("soc", 1),
                  "max_single_volt": ("cell_v_max", 1), "min_single_volt": ("cell_v_min", 1),
                  "max_temp": ("temp_max", 1), "min_temp": ("temp_min", 1)},
    "aitio": {"current_A": ("pack_current", -1), "voltage_V": ("pack_voltage", 1),
              "temperature_degC": ("temperature", 1)},
    "beijing_ev": {"voltage": ("pack_voltage", 1), "current": ("pack_current", -1),
                   "soc": ("soc", 1)},
    "bilfinger2024": {"I": ("pack_current", 1), "U": ("pack_voltage", 1), "SOC": ("soc", 1),
                      "time_ms": ("elapsed_time_s", 0.001), "time_s": ("elapsed_time_s", 1),
                      "time_min": ("elapsed_time_s", 60), "time_h": ("elapsed_time_s", 3600)},
    "bilfinger2025": {"I": ("pack_current", 1), "U": ("pack_voltage", 1), "SOC": ("soc", 1),
                      "time_ms": ("elapsed_time_s", 0.001), "time_s": ("elapsed_time_s", 1),
                      "time_min": ("elapsed_time_s", 60), "time_h": ("elapsed_time_s", 3600)},
    "bilfinger2026": {"I": ("pack_current", 1), "U": ("pack_voltage", 1), "SOC": ("soc", 1),
                      "time_ms": ("elapsed_time_s", 0.001), "time_s": ("elapsed_time_s", 1),
                      "time_min": ("elapsed_time_s", 60), "time_h": ("elapsed_time_s", 3600)},
    "brazil_star": {"Voltage": ("pack_voltage", 0.001), "Current": ("source__current_A", 0.001),
                    "SOC": ("soc", 0.1)},
    "birds_cubesat": {"Vbat_V": ("pack_voltage", 1), "Ibatt_mA": ("source__Ibatt_A", 0.001),
                      "Tbatt_C": ("temperature", 1), "time_s": ("elapsed_time_s", 1)},
    "cloverleaf": {"Vpack": ("pack_voltage", 1), "Ipack": ("pack_current", 1), "SOC": ("soc", 1),
                   "SOH": ("soh", 1), "Vcavg": ("cell_v_mean", 1), "Vcmax": ("cell_v_max", 1),
                   "Vcmin": ("cell_v_min", 1), "Vcdif": ("cell_v_spread", 1)},
    "deng": {"charge_current": ("pack_current", -1), "pack_voltage": ("pack_voltage", 1),
             "soc": ("soc", 1), "max_cell_voltage": ("cell_v_max", 1),
             "min_cell_voltage": ("cell_v_min", 1), "max_temperature": ("temp_max", 1),
             "min_temperature": ("temp_min", 1)},
    "changan": {"totalcurrent": ("pack_current", -1), "totalvoltage": ("pack_voltage", 1),
                "terminaltime": ("elapsed_time_s", 1), "soc": ("soc", 1),
                "maxvoltagebattery": ("cell_v_max", 1),
                "minvoltagebattery": ("cell_v_min", 1), "maxtemperaturevalue": ("temp_max", 1),
                "mintemperaturevalue": ("temp_min", 1)},
    "flashbattery-agv": {"mintemperature": ("temp_min", 1), "maxtemperature": ("temp_max", 1)},
    "ku_leuven_bev": {"RawBattCurrent132": ("pack_current", -1), "BattVoltage132": ("pack_voltage", 1),
                      "SOCave292": ("soc", 1), "BMSminPackTemperature": ("temp_min", 1),
                      "BMSmaxPackTemperature": ("temp_max", 1)},
    "li2026": {"cur": ("pack_current", -1)},
    "m5bat-2023-04": {"I_DC_Batt": ("pack_current", -0.1), "U_DC_Batt": ("pack_voltage", 0.1),
                      "SOC": ("soc", 0.1), "P_AC": ("pack_power", -1)},
    "m5bat-pbacid": {"current_A_bms": ("pack_current", -1), "voltage_bat_V_bms": ("pack_voltage", 1),
                     "soc_pct_bms": ("soc", 1), "power_dc_W_bms": ("pack_power", -0.001)},
    "pnnl_epri": {"Current": ("current_c_rate", -1), "Power": ("power_c_rate", -1),
                  "HoursElapsed": ("elapsed_time_s", 3600), "SOC": ("soc", 100),
                  "Voltage": ("cell_v_mean", 1), "VoltageMax": ("cell_v_max", 1),
                  "VoltageMin": ("cell_v_min", 1), "VoltageAvg": ("cell_v_mean", 1),
                  "TempMax": ("temp_max", 1), "TempMin": ("temp_min", 1), "TempAvg": ("temp_mean", 1)},
    "rwth-home": {"I_in_A": ("pack_current", 1), "V_in_V": ("pack_voltage", 1),
                  "P_in_W": ("pack_power", 0.001), "T_Bat_in_C": ("temperature", 1),
                  "T_Room_in_C": ("room_temperature", 1)},
    "rwth-android": {"current": ("pack_current", 1), "voltage_cell": ("pack_voltage", 1),
                     "state_of_charge": ("soc", 1), "temperature_cell": ("temperature", 1)},
    "tongji_rest": {"totalCurrent": ("pack_current", -1), "totalVoltage": ("pack_voltage", 1),
                    "soc": ("soc", 1), "temp_mean": ("temperature", 1)},
    "tsukuba": {"battery_dc_current": ("pack_current", -1), "battery_dc_voltage": ("pack_voltage", 1),
                "battery_active_power": ("pack_power", -1), "battery_soc": ("soc", 1)},
    "stanford_ev": {"V_pack_bms": ("pack_voltage", 1), "SOC_pack_bms": ("soc", 1),
                    "T_pack_bms": ("temperature", 1)},
    "fei_bus": {"SOH": ("soh", 1), "SOH(OCV)": ("source__SOH_OCV", 1),
                "mileage": ("source__mileage", 1)},
    "ved": {"HV Battery Voltage[V]": ("pack_voltage", 1), "HV Battery SOC[%]": ("soc", 1)},
    "zhou2026": {"TotalCurrent": ("pack_current", -1), "TotalVoltage": ("pack_voltage", 1),
                 "SOC": ("soc", 1), "MaxCellVoltage": ("cell_v_max", 0.001),
                 "MinCellVoltage": ("cell_v_min", 0.001), "MaxTemp": ("temp_max", 1),
                 "MinTemp": ("temp_min", 1)},
}


class UnsupportedStandard(ValueError):
    """A known unit whose physical mapping is not established."""


def canonical_unit(package: str, unit) -> str:
    if package not in PACKAGES:
        raise ValueError(f"standard view is not implemented for {package}")
    if unit is None:
        if package == "ppl":
            return "E_W_Brown_BESS"
        if package == "m5bat-pbacid":
            return "Pb1:bms"
        import fielddata
        table = standard_systems(package)
        supported = table[table["standard_status"] == "supported"]
        if len(supported) == 1:
            return str(supported["unit"].iloc[0])
        raise ValueError(f"{package}: specify one unit")
    name = str(unit)
    if package == "cao":
        parts = name.split(":")
        if len(parts) != 2 or parts[0] not in {"DTI", "QAS", "GIS"} or not parts[1].isdigit():
            raise ValueError("cao unit must be '<brand>:<vehicle>', for example 'QAS:0'")
        if parts[0] == "GIS":
            raise UnsupportedStandard(f"cao {name}: column meanings not established for GIS")
    if package == "ppl" and name != "E_W_Brown_BESS":
        raise ValueError(f"ppl: unknown unit {name}")
    if package == "m5bat-pbacid":
        parts = name.split(":")
        if len(parts) != 2 or parts[0] != "Pb1" or parts[1] not in {"bms", "bsc"}:
            raise ValueError("m5bat-pbacid unit must be 'Pb1:bms' or 'Pb1:bsc'")
    return name


def mapping(package: str, raw: pd.DataFrame, unit: str) -> dict[str, tuple[str, float]]:
    """The reversible physical-column mapping, including released sensor channels."""
    result = {source: item for source, item in MAPPINGS.get(package, {}).items() if source in raw}
    for column in raw.columns:
        if package == "cao" and re.fullmatch(r"cell_v_\d+", column):
            result[column] = (column, 0.001 if unit.startswith("DTI:") else 1)
        elif package == "schaeffer" and (match := re.fullmatch(r"U_Cell_(\d+)", column)):
            result[column] = (f"cell_v_{int(match[1]):03d}", 1)
        elif package == "schaeffer" and (match := re.fullmatch(r"Temperature_(\d+)", column)):
            result[column] = (f"temp_{int(match[1]):03d}", 1)
        elif package == "schaeffer" and (match := re.fullmatch(r"I_CNV_Cell_(\d+)", column)):
            result[column] = (f"balance_current_{int(match[1]):03d}", 1)
        elif package == "xie" and (match := re.fullmatch(r"batCoreVoltage(\d+)", column)):
            result[column] = (f"cell_v_{int(match[1]):03d}", 0.001)
        elif package == "xie" and (match := re.fullmatch(r"batCoreTemp(\d+)", column)):
            result[column] = (f"temp_{int(match[1]):03d}", 1)
        elif package == "li2026" and (match := re.fullmatch(r"cell_(\d+)_V", column)):
            result[column] = (f"cell_v_{int(match[1]):03d}", 1)
        elif package == "li2026" and (match := re.fullmatch(r"cell_(\d+)_T", column)):
            result[column] = (f"temp_{int(match[1]):03d}", 1)
        elif package == "stanford_ev" and (match := re.fullmatch(r"V_cell_bms_(\d+)", column)):
            result[column] = (f"cell_v_{int(match[1]):03d}", 1)
        elif package == "stanford_ev" and (match := re.fullmatch(r"T_module_bms_(\d+)", column)):
            result[column] = (f"temp_{int(match[1]):03d}", 1)
        elif package == "zhou2026" and (match := re.fullmatch(r"CellVoltages_(\d+)", column)):
            result[column] = (f"cell_v_{int(match[1]):03d}", 0.001)
        elif package == "zhou2026" and (match := re.fullmatch(r"CellTemperatures_(\d+)", column)):
            result[column] = (f"temp_{int(match[1]):03d}", 1)
        elif package in {"bilfinger2024", "bilfinger2025", "bilfinger2026"} and (
                match := re.fullmatch(r"cell_voltage_(\d+)", column)):
            result[column] = (f"cell_v_{int(match[1]):03d}", 1)
        elif package == "tongji_rest" and (match := re.fullmatch(r"(?:cellVoltage_|cell_voltage_)(\d+)", column)):
            result[column] = (f"cell_v_{int(match[1]):03d}", 1)
    if package in {"bilfinger2024", "bilfinger2025", "bilfinger2026"}:
        elapsed_sources = [column for column in ("time_ms", "time_s", "time_min", "time_h")
                           if column in result]
        for source in elapsed_sources[1:]:
            result.pop(source)
    return result


def _infer_tier(package: str, converted_columns: list[str], raw: pd.DataFrame) -> str:
    if package in TIERS and package != "ppl":
        return TIERS[package]
    if package in {"bilfinger2024", "bilfinger2025", "bilfinger2026"}:
        return "per-cell" if any(column.startswith("cell_v_") for column in converted_columns) else "pack-only"
    if package == "ppl":
        return "max-min" if "CellVoltMax" in raw else "pack-only"
    if package == "flashbattery-agv":
        return "session"
    if package == "birds_cubesat":
        return "pack-only"
    if "snippet" in raw.columns:
        return "session"
    if any(column.startswith("cell_v_") for column in converted_columns):
        return "per-cell"
    if any(column.startswith("temp_") for column in converted_columns):
        return "per-cell"
    if any(column in converted_columns for column in {"cell_v_max", "cell_v_min", "cell_v_mean", "temp_max", "temp_min"}):
        return "max-min"
    return "pack-only"


def from_raw(package: str, unit, raw: pd.DataFrame) -> pd.DataFrame:
    """Convert one raw-loader frame, without dropping rows or changing raw input."""
    name = canonical_unit(package, unit)
    if not isinstance(raw, pd.DataFrame):
        raise TypeError("from_raw requires one DataFrame, not a chunk iterator")
    if "unit" in raw and package != "tumftm" and not raw["unit"].astype(str).eq(name).all():
        raise ValueError(f"{package} {name}: raw frame contains another unit")
    result = {}
    conversions = mapping(package, raw, name)
    time_columns = set()
    if package == "cao":
        result["frame_index"] = np.arange(len(raw), dtype=np.int64)
        result["elapsed_time_s"] = result["frame_index"] * 30
        time_basis = "relative frames, assumed 30 s spacing from paper, not measured time"
    elif package in {"zhang2023", "evbattery"}:
        result["source_time_s"] = raw["timestamp"]
        result["elapsed_time_s"] = raw["timestamp"] - raw.groupby("snippet", sort=False)["timestamp"].transform("first")
        time_columns = {"timestamp"}
        time_basis = "relative to snippet start, publisher clock, no calendar dates"
    elif package == "schaeffer":
        result["time"] = raw["Timestamp"]
        time_columns = {"Timestamp"}
        time_basis = "wall clock, time zone not stated"
    elif package == "beijing_ev":
        if pd.api.types.is_datetime64_any_dtype(raw["time"]):
            result["time"] = raw["time"]
        else:
            result["time"] = pd.to_datetime(raw["time"].astype(str), format="%Y%m%d%H%M%S")
        time_columns = {"time"}
        time_basis = "released local date-time, timezone not stated"
    elif package == "tongji_rest":
        result["time"] = pd.to_datetime(raw["reqDate"], errors="coerce")
        result["source__reqDate"] = raw["reqDate"]
        time_columns = {"reqDate"}
        time_basis = "released segment time, timezone not stated"
    elif package == "shenzhen_charging":
        result["time"] = pd.to_datetime(raw["end_time"])
        time_columns = {"end_time"}
        time_basis = "released charging-station sampling time, timezone not stated"
    elif package == "stanford_ev":
        if "session" not in raw:
            raise ValueError("stanford_ev: standard time needs the released session identifier")
        start = pd.to_datetime(raw["session"].astype(str), format="%Y%m%d_%H%M%S")
        result["time"] = start + pd.to_timedelta(raw["t"], unit="s")
        result["elapsed_time_s"] = raw["t"]
        time_columns = {"t"}
        time_basis = "session filename start plus released seconds from session start; timezone not stated"
    elif isinstance(raw.index, pd.DatetimeIndex):
        time = raw.index
        if package == "ppl":
            time = time.tz_localize(None) if time.tz is not None else time
            time_basis = "wall clock, time zone not stated, unsupported raw UTC label removed"
        else:
            time_basis = "raw loader DatetimeIndex"
        result["time"] = time
        if package == "aitio":
            time_columns = {"time_s"}
    elif "time" in raw.columns and pd.api.types.is_datetime64_any_dtype(raw["time"]):
        result["time"] = raw["time"]
        time_columns = {"time"}
        time_basis = "raw loader time column"
    elif "date" in raw.columns and pd.api.types.is_datetime64_any_dtype(raw["date"]):
        result["time"] = raw["date"]
        time_columns = {"date"}
        time_basis = "released calendar time, timezone not stated"
    elif raw.index.name == "sample":
        result["source_sample_index"] = raw.index
        time_basis = "publisher file sample index; sample interval not stated"
    else:
        time_basis = "no standard time column from raw loader"
    for source, (target, factor) in conversions.items():
        if package == "rwth-android" and source == "current":
            if "manufacturer" not in raw:
                raise ValueError("rwth-android: cannot normalize current without the released manufacturer field")
            reverse = raw["manufacturer"].astype(str).str.lower().isin({"oneplus", "xiaomi"})
            result[target] = raw[source].where(~reverse, -raw[source])
        else:
            result[target] = raw[source] if factor == 1 else raw[source] * factor
    expanded_columns = set()
    if package == "changan":
        for source, prefix, count in (("batteryvoltage", "cell_v", 96),
                                      ("probetemperatures", "temp", 32)):
            if source not in raw:
                continue
            values = raw[source].astype("string")
            present = values.dropna()
            if not present.empty and not present.str.count("~").eq(count - 1).all():
                raise ValueError(f"changan {name}: unexpected sensor count in {source}")
            parts = values.str.split("~", expand=True).reindex(columns=range(count)).astype("string")
            normalized = parts.apply(lambda column: column.str.replace(r'^[\\"]+|[\\"]+$', "", regex=True))
            changed_rows = (parts.notna() & parts.ne(normalized)).any(axis=1)
            for index in range(count):
                converted = pd.to_numeric(normalized[index], errors="coerce")
                changed_rows |= parts[index].notna() & converted.isna()
                result[f"{prefix}_{index + 1:03d}"] = converted
            result[f"source__{source}"] = values.where(changed_rows)
            expanded_columns.add(source)
    elif package == "zhou2026":
        from fielddata.loaders.zhou2026 import expand_cells
        for source, prefix in (("CellVoltages", "cell_v"), ("CellTemperatures", "temp")):
            if source not in raw:
                continue
            for column, values in expand_cells(raw, source).items():
                index = int(column.rsplit("_", 1)[1])
                converted = values * 0.001 if source == "CellVoltages" else values
                if source == "CellTemperatures" and name != "LFP01":
                    converted = converted - 40
                result[f"{prefix}_{index:03d}"] = converted
            expanded_columns.add(source)
    for column in raw.columns:
        if (column not in conversions and column not in time_columns and column != "unit"
                and column not in expanded_columns):
            target = column if column in {"snippet", "charge_segment", "label", "mileage", "capacity", "session"} else f"source__{column}"
            result[target] = raw[column]
    result["unit"] = name
    tier = _infer_tier(package, list(result), raw)
    result["data_tier"] = tier
    result = pd.DataFrame(result, index=raw.index).reset_index(drop=True)
    result.attrs = {"package": package, "unit": name, "data_tier": tier, "time_basis": time_basis,
                    "current_sign": "charge positive", "native_current_sign": NATIVE_SIGNS.get(package, "not yet established"),
                    "clean": bool(raw.attrs.get("clean", False)), "standard_version": 1,
                    "units": {"pack_current": "A", "pack_voltage": "V", "cell_v_*": "V",
                              "soc": "%", "temp_*": "degC", "temperature": "degC", "pack_power": "kW",
                              "ac_power": "kW", "current_c_rate": "1/h", "power_c_rate": "1/h",
                              "balance_current_*": "A (release units may be undocumented)"}}
    return result


def raw_frame(package: str, unit, **kwargs) -> pd.DataFrame:
    import fielddata

    name = canonical_unit(package, unit)
    if package == "cao":
        if kwargs.get("which", "vin_2") != "vin_2":
            raise ValueError("cao standard view maps vin_2 telemetry only, not vin_1 or vin_3 model outputs")
        brand, vehicle = name.split(":")
        return fielddata.load(package, brand=brand, vehicle=vehicle, names="inferred", **kwargs)
    if package == "schaeffer":
        if kwargs.get("chunksize") is not None:
            raise ValueError("use fielddata.iter_standard for streaming Schaeffer conversion")
        return fielddata.load(package, system=int(name), **kwargs)
    if package == "ppl":
        return fielddata.load(package, **kwargs)
    if package == "deng":
        return fielddata.load(package, pack=name, **kwargs)
    if package == "m5bat-pbacid":
        _, source = name.split(":")
        return fielddata.load(package, source=source, **kwargs)
    if package == "tongji_rest":
        kind = kwargs.pop("kind", None)
        if kind is not None:
            return fielddata.load(package, unit=name, kind=kind, **kwargs)
        frames = []
        for segment_kind in ("charge", "rest"):
            frame = fielddata.load(package, unit=name, kind=segment_kind, **kwargs)
            frame["record_type"] = segment_kind
            frames.append(frame)
        return pd.concat(frames, ignore_index=True)
    if package == "stanford_ev":
        signal = kwargs.pop("signal", "V_pack_bms")
        sessions = fielddata._loader(package).sessions()["session"].tolist()
        return fielddata.load(package, session=sessions, signal=signal, **kwargs)
    return fielddata.load(package, unit=name, **kwargs)


def standardize(package: str, unit, raw: pd.DataFrame) -> pd.DataFrame:
    """Convert an existing single-unit loader frame without I/O or changing its values."""
    return from_raw(package, unit, raw)


def iter_standard(package: str, unit=None, *, archive=None, chunksize=250_000,
                  clean=False, signal="V_pack_bms") -> Iterator[pd.DataFrame]:
    """Stream Schaeffer source-order chunks or complete snippets in one archive."""
    import fielddata

    if not isinstance(chunksize, int) or isinstance(chunksize, bool) or chunksize < 1:
        raise ValueError("chunksize must be a positive integer")
    if package == "schaeffer":
        if archive is not None:
            raise ValueError("schaeffer: specify unit, not archive")
        name = canonical_unit(package, unit)
        for raw in fielddata.load(package, system=int(name), chunksize=chunksize, clean=clean):
            yield standardize(package, name, raw)
    elif package in {"zhang2023", "evbattery"}:
        if unit is not None or archive is None:
            raise ValueError(f"{package}: specify archive, not unit, to scan once")
        loader = fielddata._loader(package)
        if archive not in set(loader.systems()["archive"]):
            raise ValueError(f"{package}: unknown archive {archive}")
        from fielddata.loaders._snippets import snippet_frame

        for member, array, meta in loader.iter_snippets(archive):
            name = f"{archive.removesuffix('.tar.gz')}:{int(meta['car'])}"
            raw = snippet_frame(member, array, meta)
            raw.attrs["clean"] = clean
            yield standardize(package, name, raw)
    elif package == "stanford_ev":
        if archive is not None:
            raise ValueError("stanford_ev: specify unit, not archive")
        name = canonical_unit(package, unit)
        loader = fielddata._loader(package)
        for session in loader.sessions()["session"]:
            raw = fielddata.load(package, session=session, signal=signal, clean=clean)
            yield standardize(package, name, raw)
    else:
        raise ValueError(f"{package}: streaming standard view supports schaeffer, zhang2023, evbattery and stanford_ev")


def standard(package: str, unit=None, **kwargs) -> pd.DataFrame | Iterator[pd.DataFrame]:
    """Load one unit in the common view. Source-specific columns are retained with source__ names."""
    if package == "schaeffer" and kwargs.get("chunksize") is not None:
        return iter_standard(package, unit, **kwargs)
    if package == "xie" and isinstance(unit, (list, tuple)):
        names = [canonical_unit(package, name) for name in unit]
        if not names or len(set(names)) != len(names):
            raise ValueError("xie: specify a nonempty list of distinct units")
        import fielddata

        raw = fielddata.load(package, unit=names, **kwargs)
        frames = [standardize(package, name, raw[raw["unit"].astype(str) == name]) for name in names]
        if any(frame.empty for frame in frames):
            raise ValueError("xie: bulk raw loader omitted a requested unit")
        result = pd.concat(frames, ignore_index=True, sort=False)
        result.attrs = frames[0].attrs.copy()
        result.attrs.pop("unit")
        result.attrs["units_selected"] = names
        return result
    if package == "deng" and isinstance(unit, (list, tuple)):
        names = [canonical_unit(package, name) for name in unit]
        import fielddata

        raw = fielddata.load(package, pack=names, **kwargs)
        frames = []
        for name in names:
            subset = raw[raw["pack"].astype(str).isin({str(name), f"#{str(name).removeprefix('#')}"})]
            frames.append(standardize(package, name, subset))
        if any(frame.empty for frame in frames):
            raise ValueError("deng: bulk raw loader omitted a requested pack")
        result = pd.concat(frames, ignore_index=True, sort=False)
        result.attrs = frames[0].attrs.copy()
        result.attrs.pop("unit")
        result.attrs["units_selected"] = names
        return result
    name = canonical_unit(package, unit)
    if package == "ppl":
        from fielddata.loaders import ppl

        years = kwargs.pop("years", None)
        years = ppl.systems()["years"].iloc[0] if years is None else sorted(int(year) for year in years)
        if not years:
            raise ValueError("ppl: no annual ESS files selected or held")
        frames = [from_raw(package, name, raw_frame(package, name, years=[year], **kwargs))
                  for year in years]
        result = pd.concat(frames, ignore_index=True, sort=False) if len(frames) > 1 else frames[0]
        result.attrs = frames[0].attrs.copy()
        tiers = list(dict.fromkeys(result["data_tier"]))
        if len(tiers) > 1:
            result.attrs.pop("data_tier")
            result.attrs["data_tiers"] = tiers
        return result
    return from_raw(package, name, raw_frame(package, name, **kwargs))


def standard_systems(package: str) -> pd.DataFrame:
    """Tag every released unit, including explicitly blocked and empty units."""
    import fielddata

    if package not in PACKAGES:
        raise ValueError(f"standard view is not implemented for {package}")
    table = fielddata.systems(package).copy()
    if package == "cao":
        table["unit"] = table["brand"] + ":" + table["vehicle"].astype(str)
    elif package == "schaeffer":
        table["unit"] = table["system"].astype(str)
    elif package == "m5bat-pbacid":
        table["unit"] = table["unit"].astype(str) + ":" + table["source"].astype(str)
    elif "unit" not in table.columns and "session" in table.columns:
        table["unit"] = table["session"].astype(str)
    elif "unit" not in table.columns and "system" in table.columns:
        table["unit"] = table["system"].astype(str)
    elif "unit" not in table.columns and "pack" in table.columns:
        table["unit"] = table["pack"].astype(str)
    elif "unit" not in table.columns and "window" in table.columns:  # li2026_evfault: one voltage snapshot per row
        table["unit"] = table["window"].astype(str)
    if "unit" not in table.columns:
        raise ValueError(f"{package}: systems() does not expose a unit column")
    table["unit"] = table["unit"].astype(str)
    table["data_tier"] = TIERS.get(package, "pack-only")
    table["standard_status"] = "supported"
    table["standard_reason"] = ""
    if package == "cao":
        blocked = table["brand"] == "GIS"
        table.loc[blocked, "standard_status"] = "blocked"
        table.loc[blocked, "data_tier"] = pd.NA
        table.loc[blocked, "standard_reason"] = "column meanings not established for GIS, tier unverified"
    if "snippets" in table:
        empty = table["snippets"] == 0
        table.loc[empty, "standard_status"] = "empty"
        table.loc[empty, "standard_reason"] = "label only, no released snippets"
    if package == "ppl":
        table["data_tier"] = "max-min (2017-2021), pack-only (2022 onward)"
    if package in {"bilfinger2024", "bilfinger2025", "bilfinger2026"}:
        table["data_tier"] = "per-cell"
        if package == "bilfinger2025" and "unit" in table:
            no_cells = table["unit"].str.contains("Taycan.*AMS", case=False, regex=True)
            table.loc[no_cells, "data_tier"] = "pack-only"
        if "kind" in table:
            non_vehicle = table["kind"] != "vehicle"
            table.loc[non_vehicle, "standard_status"] = "blocked"
            table.loc[non_vehicle, "standard_reason"] = "laboratory reference recordings are not field units"
    if package == "m5bat-2023-04" and "kind" in table:
        plant = table["kind"] == "plant connection point"
        table.loc[plant, "standard_status"] = "blocked"
        table.loc[plant, "standard_reason"] = "plant connection point is not a battery unit"
    if package == "tongji_rest" and "kind" in table:
        non_field = table["kind"] != "field vehicle"
        table.loc[non_field, "standard_status"] = "blocked"
        table.loc[non_field, "standard_reason"] = "feature-only records and laboratory cells are not field units"
    if package == "ved" and "battery_signals" in table:
        no_battery = ~table["battery_signals"].astype(bool)
        table.loc[no_battery, "standard_status"] = "blocked"
        table.loc[no_battery, "standard_reason"] = "no released battery signals for this vehicle"
    if package == "rise_conbat":
        table["standard_status"] = "blocked"
        table["standard_reason"] = "load requires window selection before unit filtering"
    if package == "cell_to_pack":
        table["standard_status"] = "blocked"
        table["standard_reason"] = "converted parquet dependency and unit-part choices are release-specific"
    if package == "li2026_evfault":  # v1.3
        table["standard_status"] = "blocked"
        table["standard_reason"] = "voltage snapshots without time, current or vehicle identifiers; units are not systems"
    if package == "giu_ebike":  # v1.3
        table["standard_status"] = "blocked"
        table["standard_reason"] = "cleaned and raw recordings have different columns and time bases; mapping not yet established"
    return table
