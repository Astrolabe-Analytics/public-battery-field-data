"""Shared measurement helpers for package fact scripts."""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fielddata.config import data_root
from fielddata.registry import PACKAGES

OUT = ROOT / "reports" / "facts"
FIELDS = [
    "application", "chemistry", "units_released", "cells_liion", "cells_leadacid",
    "cell_channels_measured", "energy_mwh", "energy_basis", "span_unit_years",
    "obs_hours", "size_gb", "files", "fault_onset_timestamp", "sentinels_documented",
]
BASIS = {"measured", "stated", "derived", "not_in_release", "open"}
APPLICATION = {
    "schaeffer": "distributed storage", "rwth-home": "distributed storage", "cloverleaf": "distributed storage",
    "ppl": "grid-scale storage", "li2026": "grid-scale storage", "m5bat-pbacid": "grid-scale storage",
    "m5bat-2023-04": "grid-scale storage", "tsukuba": "distributed storage", "zhou2026": "passenger EV, bus",
    "flashbattery-agv": "industrial and robotics", "rwth-android": "consumer electronics",
    "xie": "light electric mobility", "fei_bus": "bus", "aitio": "distributed storage",
}
APPLICATIONS = {
    "passenger EV", "bus", "light electric mobility", "grid-scale storage",
    "distributed storage", "consumer electronics", "industrial and robotics",
}
CHEMISTRY = {
    "bilfinger2024": ("NMC and LFP", "stated", "https://doi.org/10.1016/j.etran.2024.100356, vehicle descriptions"),
    "bilfinger2026": ("NMC and LFP", "stated", "https://doi.org/10.1016/j.etran.2026.100589, vehicle descriptions"),
    "changan": ("NCM", "stated", "https://doi.org/10.1038/s41467-025-56485-7, p. 4, Results ('300 EVs equipped with NCM lithium-ion batteries')"),
    "deng": ("NMC", "stated", "https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles, README, section 'battery pack information update' (\"equipped with CATL NCM batteries\")"),
    "flashbattery-agv": ("lithium-ion", "stated", "https://doi.org/10.1109/CCNC51644.2023.10060391, p. 1 (Flash Battery lithium-ion packs in AGV applications)"),
    "li2026": ("LFP", "stated", "https://doi.org/10.1016/j.xcrp.2026.103210, experimental system"),
    "m5bat-2023-04": ("LMO/NMC; LFP; LTO; OCSM; OPzV", "stated", "https://doi.org/10.3390/en15041342 (Jacqué, K. et al., Energies 15, 1342, 2022), Sec. 2.1.2: the lithium units 5 to 8 are an LMO/NMC blend; other units from https://doi.org/10.18154/RWTH-2024-04895, p. 3 unit table"),
    "m5bat-pbacid": ("flooded OCSM lead-acid", "stated", "https://doi.org/10.3390/en19174141, Section 2"),
    "ppl": ("lithium-ion", "stated", "https://doi.org/10.1109/ACCESS.2026.3693606, Section II"),
    "schaeffer": ("LFP", "stated", "https://doi.org/10.1016/j.xcrp.2024.102258, Methods"),
    "tsukuba": ("lead-acid", "stated", "https://doi.org/10.1038/sdata.2019.20, system description"),
    "xie": ("LFP", "stated", "https://doi.org/10.1016/j.xcrp.2026.103154, Methods"),
    "zhou2026": ("NMC and LFP", "stated", "https://doi.org/10.1038/s41560-026-02131-5, Methods"),
    "aitio": ("lead-acid (VRLA)", "stated", "https://doi.org/10.1016/j.joule.2021.11.006, accepted manuscript p. 3 (valve-regulated lead-acid, 12 V, 6 cells in series)"),
}
ENERGY = {
    "bilfinger2024": (0.1105, "stated", "https://doi.org/10.1016/j.etran.2024.100356, vehicle descriptions"),
    "bilfinger2026": (0.4005, "stated", "https://doi.org/10.1016/j.etran.2026.100589, vehicle descriptions"),
    "cloverleaf": (0.084, "stated", "https://doi.org/10.5281/zenodo.6373656, record description"),
    "m5bat-pbacid": (1.066, "stated", "https://doi.org/10.3390/en19174141, Section 2"),
    "ppl": (2.0, "stated", "https://doi.org/10.1109/ACCESS.2026.3693606, Section II"),
    "rwth-home": (0.15263, "stated", "Metadata_and_Code.zip/00_Data/00_Metadata/Metadata_Systems.xlsx (released with the data; https://doi.org/10.1038/s41560-024-01620-9)"),
    "tsukuba": (0.326, "stated", "https://doi.org/10.1038/sdata.2019.20, system description"),
}


def fact(value, basis: str, source: str = "", note: str = "") -> dict:
    if basis not in BASIS:
        raise ValueError(basis)
    if basis in {"measured", "stated", "derived"} and (value is None or not source):
        raise ValueError(f"{basis} facts require value and source")
    if basis in {"not_in_release", "open"} and not note:
        raise ValueError(f"{basis} facts require a note")
    return {"value": value, "basis": basis, "source": source, "note": note}


def released_directory(package: str) -> Path:
    return data_root() / PACKAGES[package]["data_directory"]


# Folders inside data/ that this collection added (author-code snapshots, extracted copies); not publisher-released files.
NOT_RELEASED = {"code", "extracted"}


def inventory(package: str) -> tuple[int, int]:
    """Count and size of the publisher-released files only: everything under data/ except data/code/ and data/extracted/."""
    directory = released_directory(package)
    files = [p for p in directory.rglob("*") if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts
             and p.relative_to(directory).parts[0] not in NOT_RELEASED]
    return len(files), sum(p.stat().st_size for p in files)


def base_facts(package: str, script: str) -> dict[str, dict]:
    count, byte_count = inventory(package)
    application = APPLICATION.get(package, "passenger EV")
    facts = {
        "application": fact(application, "derived", "classification mapping required by the facts audit brief"),
        "chemistry": fact(None, "open", note="Chemistry was not established from release metadata by this run."),
        "units_released": fact(None, "open", note="Released unit identifiers require package-specific inspection."),
        "cells_liion": fact(None, "open", note="Physical lithium-ion cell count requires topology or unit metadata."),
        "cells_leadacid": fact(None, "not_in_release", note="No lead-acid cell count applies or is exposed in this release."),
        "cell_channels_measured": fact(None, "open", note="Cell-channel count requires package-specific schema inspection."),
        "energy_mwh": fact(None, "open", note="No release-visible energy rating was established by this run."),
        "energy_basis": fact("none", "derived", "energy_mwh is not available"),
        "span_unit_years": fact(None, "open", note="Per-unit timestamp spans require package-specific inspection."),
        "obs_hours": fact(None, "not_in_release", note="Observation-hours are not used when calendar spans are measurable or no cadence is available."),
        "size_gb": fact(byte_count / 1_000_000_000, "measured", script),
        "files": fact(count, "measured", script),
        "fault_onset_timestamp": fact(
            "no",
            "stated",
            "docs/descriptor/TABLE3_faults.md; released labels and metadata contain no explicit fault-onset timestamp field",
        ),
        "sentinels_documented": fact(
            "no",
            "stated",
            f"{PACKAGES[package]['urls']['data']}; public data record and released documentation state no sentinel convention",
        ),
    }
    if package in CHEMISTRY:
        value, basis, source = CHEMISTRY[package]
        facts["chemistry"] = fact(value, basis, source)
    if package == "cao":
        facts["chemistry"] = fact(
            "DTI: NMC-class; QAS: LFP; GIS: unknown",
            "derived",
            "fielddata/specs.py cao groups (cell-voltage range rule over released vin_2 cell voltages)",
            "Inferred from measured cell-voltage ranges; the Zenodo record, released archives, and paper do not name the chemistry.",
        )
    if package == "m5bat-pbacid":
        facts["sentinels_documented"] = fact(
            "yes",
            "stated",
            "fielddata/loaders/m5bat_pbacid_SCHEMA.md; released codebook defines 2345/2356 as BMS communication-error placeholders",
            "The released files contain no 2345/2356 values in the four codebook columns; the publisher replaced them with NaN (measured, source audit 2026-10-04).",
        )
    if package == "tsukuba":
        facts["sentinels_documented"] = fact(
            "yes",
            "stated",
            "https://doi.org/10.1038/sdata.2019.20, p. 6-7, Known issues",
            "Error code -999,999 on and before the maintenance days (14 Nov 2015, 19 Nov 2016, 18 Nov 2017) and on other days; battery DC voltage 0 on maintenance days; "
            "DC current between -680 and -450 A out of range; all blanked in the cleaned files (paper p. 6-7). Raw files hold 1,243,210 values of -999,999 and no +999,999 "
            "(scripts/checks/source_audit/tsukuba_tumftm_ppl/check_tsukuba_audit.py).",
        )
    if package == "ppl":
        facts["sentinels_documented"]["note"] = ("Zeros in SOH, cell voltages, AvgSOC and module temperatures during outages are observed placeholders, "
                                                 "not documented by the publisher; clean=True masks them (source audit 2026-10-04).")
    if package == "flashbattery-agv":
        facts["sentinels_documented"] = fact(
            "yes",
            "stated",
            "https://doi.org/10.1109/CCNC51644.2023.10060391, Sec. IV, p. 3 (reset date 1st January 2000, temperatures -40 \u00b0C and 215 \u00b0C)",
            "Documented for the fleet data the release is drawn from; the release contains none of them (dates 2019-12-16 to 2022-02-07, temperatures 10 to 48 \u00b0C, "
            "no missing values; scripts/checks/source_audit/changan_cloverleaf_fei_agv/flashbattery_agv_audit_checks.py). The paper says its data were filtered and "
            "missing values imputed; whether the release was is not stated.",
        )
    if package in ENERGY:
        value, basis, source = ENERGY[package]
        facts["energy_mwh"] = fact(value, basis, source)
        facts["energy_basis"] = fact(basis, "derived", f"energy_mwh uses the {basis} basis")
    return facts


def profile_measurements(package: str, facts: dict[str, dict], script: str) -> None:
    if package == "cao":
        from fielddata.loaders import cao
        systems = cao.systems()
        counts = systems.groupby("brand").size().to_dict()
        channels = counts.get("DTI", 0) * 85 + counts.get("QAS", 0) * 110
        facts["units_released"] = fact(len(systems), "measured", script)
        facts["cells_liion"] = fact(channels, "derived", "DTI vehicles x 85 plus QAS vehicles x 110; GIS excluded because its channel meaning is unresolved")
        facts["cell_channels_measured"] = fact(channels, "derived", "DTI vehicles x 85 plus QAS vehicles x 110; GIS excluded because its channel meaning is unresolved")
        facts["span_unit_years"] = fact(None, "not_in_release", note="Released tensors contain no timestamps.")
        facts["obs_hours"] = fact(None, "not_in_release", note="No released timestamps or established cadence support observation-hours.")
    elif package == "deng":
        profile = pd.read_csv(ROOT / "reports" / "deng_system_profile.csv")
        facts["units_released"] = fact(len(profile), "measured", script)
        facts["cells_liion"] = fact(len(profile) * 90, "derived", "20 release packs x 90 series cells stated in the release metadata")
        facts["cell_channels_measured"] = fact(None, "not_in_release", note="The charging CSVs expose pack extrema, not individual cell channels.")
        facts["energy_mwh"] = fact(0.95265, "derived", "20 packs x 90 cells x 145 Ah x 3.65 V / 1,000,000",
            "The 3.65 V cell voltage is assumed, not stated; measured mid-SOC voltage is 3.71 V at low current and 3.76 V under charge (source audit 2026-10-04), which would give 0.966 MWh at 3.7 V.")
        facts["energy_basis"] = fact("computed", "derived", "energy_mwh is computed from stated configuration")
        facts["span_unit_years"] = fact(profile["span_days"].sum() / 365.25, "measured", script)
        facts["obs_hours"] = fact(None, "not_in_release", note="Calendar spans are measurable; sampled rows are charging-only and not continuous watched time.")
    elif package == "m5bat-pbacid":
        profile = pd.read_csv(ROOT / "reports" / "m5bat_pbacid_system_profile.csv")
        start = pd.to_datetime(profile["bms_first"]).min(); end = pd.to_datetime(profile["bms_last"]).max()
        facts["units_released"] = fact(1, "derived", "the release holds one system")
        facts["cells_leadacid"] = fact(300, "stated", "https://doi.org/10.3390/en19174141, Section 2")
        facts["cell_channels_measured"] = fact(None, "not_in_release", note="Release contains string-level measurements, not individual cell-voltage channels.")
        facts["span_unit_years"] = fact((end-start).total_seconds()/31557600, "measured", script)
    elif package == "ppl":
        from fielddata.loaders import ppl
        first, last = ppl.time_bounds()
        facts["units_released"] = fact(1, "derived", "the release holds one system")
        facts["cells_liion"] = fact(4760, "stated", "https://doi.org/10.1109/ACCESS.2026.3693606, system description")
        facts["cell_channels_measured"] = fact(None, "not_in_release", note="Released plant telemetry provides cell extrema and rack aggregates, not 4,760 individual channels.")
        facts["span_unit_years"] = fact((pd.Timestamp(last)-pd.Timestamp(first)).total_seconds()/31557600, "measured", script)
    elif package == "schaeffer":
        profile = pd.read_csv(ROOT / "reports" / "schaeffer_system_profile.csv")
        facts["units_released"] = fact(len(profile), "measured", script)
        facts["cells_liion"] = fact(len(profile)*8, "derived", "28 released systems x 8 series cells per system")
        facts["cell_channels_measured"] = fact(len(profile)*8, "derived", "28 released systems x 8 released cell-voltage channels")
        facts["energy_mwh"] = fact(0.10752, "derived", "28 systems x 24 V x 160 Ah / 1,000,000")
        facts["energy_basis"] = fact("computed", "derived", "energy_mwh is computed from stated configuration")
        facts["span_unit_years"] = fact(profile["duration_days"].sum()/365.25, "measured", script)


def simple_measurements(package: str, facts: dict[str, dict], script: str) -> None:
    if package in {"bilfinger2024", "bilfinger2026"}:
        for field in ("cells_liion", "cell_channels_measured", "span_unit_years"):
            facts[field] = fact(None, "open", note="Measured in scripts/facts/_extra.py.")
    elif package == "cloverleaf":
        facts["units_released"] = fact(3, "derived", "three HV pack sheets, one per battery pack")
        facts["chemistry"] = fact(None, "not_in_release", note="The Zenodo record and released workbooks do not state cell chemistry.")
        facts["cells_liion"] = fact(None, "not_in_release", note="The released workbooks provide pack and cell-summary signals but do not state physical cell count.")
        facts["cell_channels_measured"] = fact(None, "not_in_release", note="The release provides Vcell average, minimum, maximum, and difference summaries, not individual cell channels.")
        facts["span_unit_years"] = fact(None, "open", note="Measured in scripts/facts/_extra.py.")
    elif package == "fei_bus":
        facts["chemistry"] = fact(None, "not_in_release", note="Released summary CSVs do not state chemistry.")
        facts["cells_liion"] = fact(None, "not_in_release", note="Released summary CSVs do not state cell topology.")
        facts["cell_channels_measured"] = fact(None, "not_in_release", note="Released files contain bus-level summary values, not cell channels.")
        facts["energy_mwh"] = fact(None, "not_in_release", note="No pack rating is present in the summary CSVs.")
        facts["span_unit_years"] = fact(None, "not_in_release", note="Released summary CSVs contain no calendar timestamps.")
    elif package == "flashbattery-agv":
        import fielddata
        dates = fielddata.load("flashbattery-agv").index
        facts["cells_liion"] = fact(None, "not_in_release", note="Per-cycle aggregate release does not expose pack topology.")
        facts["cell_channels_measured"] = fact(None, "not_in_release", note="Per-cycle aggregate release has no cell channels.")
        facts["energy_mwh"] = fact(None, "not_in_release", note="No pack energy rating is present in the aggregate CSV.")
        facts["span_unit_years"] = fact((dates.max()-dates.min()).total_seconds()/31557600, "measured", script)
    elif package == "rwth-home":
        facts["span_unit_years"] = fact(None, "open", note="Measured in scripts/facts/_extra.py.")
        facts["cells_liion"] = fact(None, "open", note="System topology requires Metadata_Systems.xlsx inspection.")
        facts["cell_channels_measured"] = fact(None, "open", note="Monthly CSV schemas require inspection.")
    elif package == "evbattery" or package == "zhang2023":
        facts["chemistry"] = fact(None, "not_in_release", note="Label tables and archive metadata do not state chemistry.")
        facts["cells_liion"] = fact(None, "not_in_release", note="Released snippets do not provide a physical pack-topology field.")
        facts["cell_channels_measured"] = fact(None, "open", note="Snippet tensor schemas require a bounded pickle schema scan.")
        facts["span_unit_years"] = fact(None, "not_in_release", note="Released snippets have relative sample positions but no calendar timestamps.")
        facts["obs_hours"] = fact(None, "open", note="Observation-hours require reading snippet lengths and establishing cadence.")
    elif package == "rwth-android":
        import fielddata
        devices = fielddata.systems("rwth-android")
        spans = float(((devices["last"] - devices["first"]).dt.total_seconds() / 31557600).sum())
        technologies = set()
        for unit in devices["unit"]:
            technologies.update(fielddata.load("rwth-android", unit=unit)["battery_technology"].dropna().unique())
        facts["cells_liion"] = fact(len(devices), "derived", "one released cell_id telemetry table per device parquet",
            "Assumes one cell per device (the data paper says most devices have a single cell); one cell_id per file measured.")
        facts["cell_channels_measured"] = fact(len(devices), "derived", "one voltage_cell channel per released device parquet")
        technology_text = "; ".join(sorted(str(value) for value in technologies))
        facts["chemistry"] = fact(technology_text, "stated", "device-reported battery_technology field in the released tables") if technology_text else fact(None, "not_in_release", note="battery_technology is empty in all released device tables.")
        facts["span_unit_years"] = fact(spans, "measured", script,
            "The held archive is the portal export Dataset_from_Mobile_Battery_Data_Explorer_2026-04.zip, not the section under 10.18154/RWTH-2025-00754: "
            "it includes 214,351 rows from 5 devices before the paper's 2026-01-14 start and ends 2026-03-31 (3.09 device-years without those rows).")
        facts["sentinels_documented"]["note"] = ("current_avg = -2147.483648 (Integer.MIN_VALUE x 1e-6) on every row of 10 devices, observed, masked by clean=True; "
                                                 "nominal_capacity 0 on 7 devices, left as released (source audit 2026-10-04).")
    elif package == "tumftm":
        from fielddata.loaders import tumftm
        spans = 0.0
        for unit in tumftm.systems()["unit"]:
            start, end = tumftm.time_bounds(unit, clean=True)
            spans += (end - start).total_seconds() / 31557600
        facts["chemistry"] = fact(None, "not_in_release", note="Vehicle files do not provide cell chemistry metadata.")
        facts["cells_liion"] = fact(None, "not_in_release", note="UDS telemetry does not expose physical pack topology.")
        facts["cell_channels_measured"] = fact(None, "not_in_release", note="The parquets hold 15 named UDS signals with rows; no individual cell-voltage channel, and the computed cell_voltage_max/min (value_id 1293/1294) have no rows.")
        facts["span_unit_years"] = fact(spans, "measured", script, "The 812 rows dated 2087-03-07 in CUP1, observed in the data and not described by the authors, are excluded.")
    elif package == "m5bat-2023-04":
        facts["cells_liion"] = fact(None, "not_in_release", note="Unit CSVs provide pack-level signals but not lithium cell topology.")
        facts["cells_leadacid"] = fact(None, "not_in_release", note="Unit CSVs provide pack-level signals but not lead-acid cell topology.")
        facts["cell_channels_measured"] = fact(None, "not_in_release", note="No individual cell-voltage channels are released.")
        facts["span_unit_years"] = fact(None, "open", note="Measured in scripts/facts/_extra.py.")
    elif package == "li2026":
        import fielddata
        numbered = set()
        for row in fielddata.systems("li2026").itertuples():
            numbered.update(range(row.first_cell, row.last_cell + 1))
        facts["cells_liion"] = fact(200, "stated", "https://doi.org/10.1016/j.xcrp.2026.103210, dataset description")
        facts["cell_channels_measured"] = fact(len(numbered), "measured", script)
        facts["span_unit_years"] = fact(None, "not_in_release", note="Filenames use sample indices and the release has no calendar timestamps.")
        facts["obs_hours"] = fact(1203, "stated", "https://doi.org/10.1016/j.xcrp.2026.103210, dataset description")
    elif package == "tsukuba":
        facts["units_released"] = fact(1, "derived", "one building microgrid battery system in the release")
        facts["cells_leadacid"] = fact(300, "stated", "https://doi.org/10.1038/sdata.2019.20, system description")
        facts["cell_channels_measured"] = fact(None, "not_in_release", note="Released tables contain system-level battery measurements, not individual cell channels.")
        facts["span_unit_years"] = fact((pd.Timestamp('2018-04-24')-pd.Timestamp('2015-01-01')).total_seconds()/31557600, "stated", "https://doi.org/10.1038/sdata.2019.20, data coverage")
    elif package == "xie":
        facts["units_released"] = fact(271, "stated", "https://doi.org/10.1016/j.xcrp.2026.103154, dataset description")
        facts["cells_liion"] = fact(5248, "stated", "https://doi.org/10.1016/j.xcrp.2026.103154, dataset description")
        facts["cell_channels_measured"] = fact(None, "open", note="RAR table inspection is needed to distinguish populated from listed channels.")
        facts["span_unit_years"] = fact(None, "open", note="RAR timestamp scan is needed per device.")
    elif package == "zhou2026":
        # units, cells, channels and span are measured in scripts/facts/_extra.py
        for field in ("units_released", "cells_liion", "cell_channels_measured", "span_unit_years"):
            facts[field] = fact(None, "open", note="Measured in scripts/facts/_extra.py.")
    elif package == "ku_leuven_bev":
        facts["units_released"] = fact(2, "stated", "https://doi.org/10.1038/s41597-025-06148-5, Data Records")
        facts["chemistry"] = fact(None, "open", note="Chemistry must be read from nested metadata or established from a cited source.")
        facts["cells_liion"] = fact(None, "open", note="Pack topology must be read from nested metadata.")
        facts["cell_channels_measured"] = fact(None, "open", note="Nested telemetry schema inspection is required.")
        facts["span_unit_years"] = fact(None, "open", note="Nested timestamp scan is required.")

    if package == "changan":
        facts["cells_liion"] = fact(28800, "derived", "300 released vehicles x 96 series cells stated in the paper",
            "96 series positions per pack as stated (paper p. 4); any parallel cells within a position are not stated.")
        facts["cell_channels_measured"] = fact(None, "open", note="Three raw sample headers expose batteryvoltage strings; all 300 raw files require split-archive streaming to confirm 96 channels each.")
        facts["energy_mwh"] = fact(16.2936, "derived", "300 vehicles x 96 cells x 155 Ah x 3.65 V / 1,000,000",
            "155 Ah and 96S are stated (paper p. 4, Results); the 3.65 V nominal cell voltage is our assumption for NCM, not stated in the paper, SI or peer review file.")
        facts["energy_basis"] = fact("computed", "derived", "energy_mwh is computed from stated configuration")
        facts["obs_hours"] = fact(None, "not_in_release", note="Spans of the relative timestamps are measurable (no calendar dates); observation-hours are not substituted for unit-years.")

    if package in {"cao", "deng", "evbattery", "ku_leuven_bev", "li2026", "rwth-android", "schaeffer", "tumftm", "xie", "zhang2023", "zhou2026"} and facts["energy_mwh"]["basis"] == "open":
        facts["energy_mwh"] = fact(None, "not_in_release", note="The release does not provide a complete nominal pack-energy rating or configuration from which to compute one.")
    if package in {"m5bat-pbacid", "tsukuba", "aitio"}:
        facts["cells_liion"] = fact(None, "not_in_release", note="This package is lead-acid; a lithium-ion cell count does not apply.")


def measure(package: str) -> Path:
    script = f"scripts/facts/{package}.py"
    facts = base_facts(package, script)
    if package in {"cao", "deng", "m5bat-pbacid", "ppl", "schaeffer"}:
        profile_measurements(package, facts, script)
    else:
        simple_measurements(package, facts, script)
    import _extra
    _extra.apply(package, facts, script)
    # Units always come from the package loader, through the one shared definition in fielddata/counting.py.
    from fielddata import counting
    earlier = facts["units_released"].get("note", "")
    facts["units_released"] = fact(counting.units(package), "measured",
        f"fielddata/counting.py over fielddata.systems('{package}')",
        (f"Rule: {counting.rule(package)}. " + earlier).strip())
    if package in {"m5bat-pbacid", "tsukuba", "aitio"}:
        facts["cells_liion"] = fact(None, "not_in_release", note="This package is lead-acid; a lithium-ion cell count does not apply.")
    if package == "zhou2026":
        facts["application"]["note"] = ("The release holds two NMC passenger cars (vehicle45, vehicle69) and one LFP bus (LFP01): "
                                        "https://doi.org/10.1038/s41560-026-02131-5, SI Supplementary Table 1 p. 16, and TotalCells 95 / 156 (measured).")
        facts["obs_hours"]["note"] = "Observation-hours are not used because calendar spans are measurable; the cadence is stated (nominal 0.1 Hz, paper p. 2)."
    if package == "li2026":
        facts["fault_onset_timestamp"] = fact("no", "stated",
            "the release contains no labels; the paper reports ESC, SDF and ICF events in the station data (https://doi.org/10.1016/j.xcrp.2026.103210, p. 3-4)")
    output = {"package": package, "facts": {}}
    for field in FIELDS:
        current = facts[field]
        output["facts"][field] = {**current, "note": current.get("note", "")}
    for key in sorted(k for k in facts if k.startswith("overlap_")):
        output[key] = facts[key]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{package}.json"
    path.write_text(json.dumps(output, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"{package}: wrote {path.relative_to(ROOT)}")
    return path


def run(package: str) -> None:
    path = OUT / f"{package}.json"
    if path.is_file() and "--force" not in sys.argv:
        print(f"{package}: skipped existing {path.relative_to(ROOT)}")
        return
    measure(package)
