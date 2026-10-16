"""Facts for the eleven releases admitted in v1.2 (2026-10-13).

Values come from each package's loader through the measurements of scripts/checks/ondeck_deltas.py and
scripts/checks/v12_energy.py (outputs in reports/checks/v12/), under the v1.1 conventions (DESCRIPTOR.md 3.4 to 3.7)
and maintainer's decisions of 2026-10-13: energy is the stated rating where the paper or record gives one, otherwise
computed (from the stated configuration or from the data); service time is unit-years where the release has calendar
timestamps, otherwise observation-hours; overlaps are counted once, with observation time outside the earlier
release still counted; shenzhen_charging is a separate charging-sessions group, not systems, not MWh and not battery
faults, while its observation-hours count.
"""
from __future__ import annotations

import json

from _common import ROOT, fact

CHECKS = ROOT / "reports" / "checks" / "v12"
V12 = ["pnnl_epri", "beijing_ev", "brazil_star", "birds_cubesat", "ved", "shenzhen_charging", "tongji_rest", "rise_conbat",
       "tum_id3_2022", "cell_to_pack", "stanford_ev"]
DELTAS = "scripts/checks/ondeck_deltas.py -> reports/checks/v12/{}_deltas.json"
ENERGY = "scripts/checks/v12_energy.py -> reports/checks/v12/{}_energy.csv"

APPLICATION = {
    "pnnl_epri": "grid-scale storage", "rise_conbat": "grid-scale storage", "cell_to_pack": "grid-scale storage",
    "brazil_star": "distributed storage", "birds_cubesat": "satellite",
    "beijing_ev": "passenger EV", "ved": "passenger EV", "tongji_rest": "passenger EV", "tum_id3_2022": "passenger EV",
    "stanford_ev": "passenger EV", "shenzhen_charging": "passenger EV",
}
APPLICATION_NOTE = {
    "brazil_star": "Off-grid household solar and battery systems, classed with aitio's off-grid systems (maintainer, 2026-10-13).",
    "birds_cubesat": "Satellite (maintainer, 2026-10-13 and 2026-10-16): batteries of 1U CubeSats in orbit, a class of its own, kept separate from eVTOL and aerospace.",
    "rise_conbat": "Second-life modules from VW Passat cars in grid-tied containers (maintainer, 2026-10-13: grid-scale storage, noted as second-life).",
    "shenzhen_charging": "Charging sessions at 30 public stations in Shenzhen; vehicle types are not stated. The release is a separate charging-sessions group: no systems are counted (maintainer, 2026-10-13).",
}
CHEMISTRY = {
    "pnnl_epri": ("LFP; NMC; LMO/NMC; vanadium flow", "stated", "Crawford 2026 DOE OE peer-review poster, alias table (https://doepeerreview.sandia.gov/app/uploads/sites/82/2026/05/Crawford_Alasdair_Analytics.pdf); per system in fielddata/loaders/pnnl_epri.py"),
    "birds_cubesat": ("NiMH", "stated", "https://doi.org/10.1016/j.dib.2022.108697, Section 2 and Table 2 (Eneloop BK-3MCCE)"),
    "tongji_rest": ("LFP; NMC", "stated", "https://doi.org/10.5281/zenodo.16868546, vehicle names LFP01, NMC01 and NMC02 in the release"),
    "cell_to_pack": ("LFP; NMC", "stated", "https://doi.org/10.5281/zenodo.20132842, record description (LiFePO4 and NMC)"),
    "shenzhen_charging": ("LFP; NMC; LMO; LCO; LP", "stated", "https://doi.org/10.17632/c7gg94tmvz.3, Readme.txt (types 03 LFP, 06 NMC, 04 LMO, 05 LCO, 07 LP); https://doi.org/10.1038/s41467-025-67703-7 (Yang et al. 2025, the five types including Li polymer, LiPo)"),
}
CHEMISTRY_NOTE = {
    "shenzhen_charging": "LP is lithium polymer (maintainer, 2026-10-13): the source paper names the five types LFP, NMC, LMO, LCO and Li polymer (LiPo), 0.07 percent of the data. Lithium polymer is a cell format, not a chemistry, so the chemistry of code 07 is not stated. "
                         "Its charging-voltage shape is steep like LCO and NMC, not flat like LFP (34 sessions, no vehicle identifier, so the number of batteries is unknown; scripts/checks/shenzhen_lp_chemistry.py). "
                         "The type codes match the Chinese charging protocol GB/T 27930, which the paper does not cite. Maintainer's view (2026-10-16): codes 05 and 07 are swapped relative to the Readme. The paper's battery-type shares (LCO 0.19 percent, LiPo 0.07 percent; Yang et al. 2025, Fig. 1a) match the data's code 07 and code 05 shares by rows (0.20 and 0.05 percent, over-30-minutes workbook), so code 05 is taken to be lithium polymer and code 07 LCO. The release's Readme says 05 LCO, 07 LP. The set of chemistry labels does not change.",
}
# cells and released cell-voltage channels: (cells_liion, channels, basis, source)
CELLS = {
    "tongji_rest": (432, "measured", "cell-voltage columns of the four field vehicles' converted segments (LFP01 123, NMC01_Car01 107, NMC01_Car02 108, NMC02 94), through fielddata.loaders.tongji_rest"),
    "cell_to_pack": (6656, "measured", "V1 to V416 in each of the 16 field packs' converted time series, through fielddata.loaders.cell_to_pack"),
    "stanford_ev": (108, "measured", "the 108 columns of V_cell_bms, through fielddata.loaders.stanford_ev"),
    "tum_id3_2022": (108, "measured", "cell_voltage_1 to cell_voltage_108 in the drives, through fielddata.loaders.tum_id3_2022 (tumftm ID1, whose release has no cell channels)"),
}
STATED_ENERGY = {
    "pnnl_epri": (63.870, "derived", "PNNL reports for the six WACEF systems (ENW at its 4 MWh nameplate) and the Crawford 2026 poster for the EPRI systems; per system in reports/candidates/pnnl_epri/pnnl_epri_ratings.csv",
                  "Nine systems: Avista 3.2, ENW 4.0, OPALCO 2.0, PSE 4.4, SnoPUDMESA1 1.0, SnoPUDMESA2 8.0, EPRI_LFP3 40.0, EPRI_NMC1 1.0, EPRI_VRF1 0.27 MWh. EPRI_LFP1 and EPRI_LFP2 are unrated, and EPRI_NMC2 is ppl's system, counted there. "
                  "ENW: PNNL's 5.5 MWh designed usable is noted, the nameplate is used (maintainer, 2026-10-13). Split basis: 23.87 MWh stated (the eight other rated systems) and 40.0 MWh computed (EPRI_LFP3). EPRI_LFP3: 40 MWh computed from the data's peak power of 0.25 C, a 4-hour ratio, at the poster's 10 MW, which matches the poster's printed E/P of 4.0 (maintainer, 2026-10-16: trust the data; computed, not stated). The poster also states 30,000 kWh (3 hours); the poster's 30 MWh is noted as a discrepancy. The data are normalised, so they fix the ratio, not the absolute size: 30 MWh run at no more than 7.5 MW would also fit. "
                  "EPRI_NMC1 and EPRI_VRF1 rest on the poster alone. The data are normalised by unreleased ratings, so energy is not computable from them (usable fractions in reports/checks/v12/pnnl_epri_energy.csv)."),
    "ved": (0.072, "stated", "https://github.com/gsoh/VED, README ('2013 Nissan Leaf with an advertised battery capacity of 24 kWh')",
            "The 3 EVs only. The 24 PHEVs and vehicle 439 have no stated rating; 13 PHEVs are computable from the data (reports/checks/v12/ved_energy.csv) but are not added, one basis per release."),
}


def _deltas(package: str) -> dict:
    return json.loads((CHECKS / f"{package}_deltas.json").read_text(encoding="utf-8"))


def apply(package: str, facts: dict, script: str) -> None:
    facts["application"] = fact(APPLICATION[package], "derived", "classification mapping required by the facts audit brief", APPLICATION_NOTE.get(package, ""))
    if package in CHEMISTRY:
        value, basis, source = CHEMISTRY[package]
        facts["chemistry"] = fact(value, basis, source, CHEMISTRY_NOTE.get(package, ""))
    else:
        facts["chemistry"] = fact(None, "not_in_release", note="Neither the release nor its paper or record states the cell chemistry.")
    if package in CELLS:
        cells, basis, source = CELLS[package]
        facts["cells_liion"] = fact(cells, basis, source, "Counted from the released channels (DESCRIPTOR.md 3.4).")
        facts["cell_channels_measured"] = fact(cells, basis, source)
    elif package == "rise_conbat":
        facts["cells_liion"] = fact(88 * 12, "derived", "88 distinct modules x 12 cells in series (cells_in_series in the release's module-info tables)")
        facts["cell_channels_measured"] = fact(None, "open", note="Cell files hold per-cell voltages for the modules reporting in each window; counting distinct cell channels needs a pass over the 12 windows.")
    else:
        facts["cells_liion"] = fact(None, "not_in_release", note="The release gives pack- or system-level signals and no cell topology.")
        facts["cell_channels_measured"] = fact(None, "not_in_release", note="No individual cell-voltage channels are released.")
    if package == "birds_cubesat":
        facts["cells_liion"] = fact(None, "not_in_release", note="The batteries are NiMH; a lithium-ion cell count does not apply.")
    # Cells are physical cells, not series elements (maintainer, 2026-10-16): tum_id3_2022's 108 cell-voltage channels are
    # series pairs. stanford_ev keeps its 108 channels as cells, because its vehicle is not matched to a stated topology.
    if package == "tum_id3_2022":
        facts["cells_liion"] = fact(216, "derived",
            "https://doi.org/10.1016/j.etran.2022.100167 (paper/Wassiliadis_2022_eTransportation.pdf): nine modules (p. 9), each 12s2p with cells \"joined in parallel pairs\" (p. 4), 216 cells in the battery system (p. 5); 108s2p",
            "The release's 108 cell-voltage channels are the 108 series pairs. The vehicle is tumftm's ID1, whose 216 cells tumftm already counts, so totals subtract them once (overlap_cells_liion).")
        facts["overlap_cells_liion"] = fact(216, "derived", "tumftm counts 7 vehicles x 216 cells, ID1 among them (https://doi.org/10.1016/j.etran.2025.100518, p. 3)",
            "Dedup rule (fielddata/counting.py): ID1's cells count once, under tumftm.")
    if package == "stanford_ev":
        facts["cells_liion"] = fact(108, "measured", "the 108 columns of V_cell_bms, through fielddata.loaders.stanford_ev",
            "The release's 108 cell-voltage channels, counted as released. The record does not name the vehicle, and it is not taken to be the Audi e-tron of the group's companion paper (doi:10.1109/OJPEL.2026.3691252, 4P108S, 432 cells): the paper says that car's pack was taken apart after January 2024, but this release shows one pack in use, with the same cell-voltage pattern and a rising odometer, from September 2021 to April 2025 (scripts/checks/stanford_ev_timeline.py). Maintainer, 2026-10-16: the match cannot be shown, so the data's count is used.")


    if package == "pnnl_epri":
        table = json.loads((CHECKS / "v12_energy_summary.json").read_text(encoding="utf-8"))  # noqa: F841  (energy evidence)
        import pandas as pd
        units = pd.read_csv(ROOT / "reports" / "candidates" / "pnnl_epri" / "pnnl_epri_deltas.csv").set_index("unit")
        span = float(units.drop(index="EPRI_NMC2")["unit_years"].sum()) + 304 / 365.25
        facts["span_unit_years"] = fact(span, "measured", "fielddata.loaders.pnnl_epri (first to last HoursElapsed per system, scripts/checks/pnnl_epri_units.py)",
            "Eleven systems, plus EPRI_NMC2's 304 days before ppl's first file (0.832 unit-years): EPRI_NMC2 is ppl's E.W. Brown system, counted once, and its time outside ppl still counts.")
    else:
        d = _deltas(package)
        if d.get("service_basis", "unit_years") == "unit_years":
            facts["span_unit_years"] = fact(d["unit_years"], "measured", DELTAS.format(package), "; ".join(d.get("notes", [])))
            facts["obs_hours"] = fact(None, "not_in_release", note="Calendar spans are measurable, so observation-hours are not used.")
        else:
            facts["span_unit_years"] = fact(None, "not_in_release", note="The release has no calendar timestamps.")
            facts["obs_hours"] = fact(d["obs_hours"], "measured", DELTAS.format(package), "; ".join(d.get("notes", [])))
        if package == "tum_id3_2022":
            facts["span_unit_years"] = fact(0.0, "measured", DELTAS.format(package),
                "Same vehicle as tumftm ID1 (scripts/checks/tum_id3_vs_tumftm.py), counted once: no time falls outside ID1's span (2021-02-11 to 2021-12-08 lies inside 2021-02-01 to 2023-06-13).")

    if package == "pnnl_epri":  # split basis (maintainer, 2026-10-16): eight systems stated, EPRI_LFP3 computed
        value, basis, source, note = STATED_ENERGY[package]
        facts["energy_mwh"] = fact(value, basis, source, note)
        facts["energy_basis"] = fact("stated and computed", "derived",
            "energy_mwh is 23.87 MWh stated (eight rated systems) and 40.0 MWh computed (EPRI_LFP3); totals count each part under its basis")
        facts["energy_split_stated_mwh"] = fact(23.870, "stated", "reports/candidates/pnnl_epri/pnnl_epri_ratings.csv",
            "Avista 3.2, ENW 4.0, OPALCO 2.0, PSE 4.4, SnoPUDMESA1 1.0, SnoPUDMESA2 8.0, EPRI_NMC1 1.0, EPRI_VRF1 0.27 MWh")
        facts["energy_split_computed_mwh"] = fact(40.0, "derived", "reports/candidates/pnnl_epri/NOTES.md (EPRI_LFP3 at 40 MWh)",
            "EPRI_LFP3: the data's 0.25 C peak power (a 4-hour ratio) at the poster's 10 MW")
    elif package in STATED_ENERGY:
        value, basis, source, note = STATED_ENERGY[package]
        facts["energy_mwh"] = fact(value, basis, source, note)
        facts["energy_basis"] = fact("stated", "derived", "energy_mwh uses the stated basis")
    elif package == "birds_cubesat":
        facts["energy_mwh"] = fact(4 * 14.4 / 1e6, "derived", "4 satellites x 6 NiMH cells (3S2P) x 2.0 Ah x 1.2 V, paper Table 2 / 1,000,000",
            "Computed from the stated configuration; not computable from the data (no SOC).")
        facts["energy_basis"] = fact("computed", "derived", "energy_mwh is computed from stated configuration")
    elif package in {"beijing_ev", "brazil_star", "tongji_rest", "cell_to_pack", "stanford_ev"}:
        d = _deltas(package)
        facts["energy_mwh"] = fact(d["energy_mwh"], "measured", ENERGY.format(package),
            "Present usable energy computed from the data: coulomb counting over runs of at least 40 points of SOC with no gap over 300 s, ampere-hours per 100 percent SOC times mean pack voltage, median per unit, summed. "
            + ("STAR-A only: the other three households never swing 40 percent SOC." if package == "brazil_star" else "")
            + ("The record does not name the vehicle." if package == "stanford_ev" else ""))
        facts["energy_basis"] = fact("computed", "derived", "energy_mwh is computed from the released data")
    elif package == "rise_conbat":
        facts["energy_mwh"] = fact(0.1151, "stated", "https://doi.org/10.5281/zenodo.17287096, module-info tables (nominal_energy_conversion, the VW Passat GTE pack rating, 9.9 or 13.0 kWh) / 8 modules per pack",
            "88 distinct modules: 72 from 9.9 kWh packs and 16 from 13.0 kWh packs, each pack rating divided by 8 modules per pack (maintainer, 2026-10-13). Not computable from the data (no SOC signal).")
        facts["energy_basis"] = fact("stated", "derived", "energy_mwh uses the stated basis")
    elif package == "tum_id3_2022":
        facts["energy_mwh"] = fact(None, "not_in_release", note="The vehicle is tumftm ID1, counted once there. 58.8 kWh computed from the data (ratio 1.01 to the stated 58 kWh net) is a cross-check, not added (reports/checks/v12/tum_id3_2022_energy.csv).")
    elif package == "shenzhen_charging":
        facts["energy_mwh"] = fact(None, "not_in_release", note="Not counted in MWh (maintainer, 2026-10-13): charging sessions without vehicle identity.")

    if package == "brazil_star":
        facts["sentinels_documented"]["note"] = ("Observed, not documented: battery times reset to 1969-12-31 20:00 and 1987, SOC outside 0 to 1000 and currents above 32,767 mA "
                                                 "(unsigned 16-bit); clean=True masks the times and SOC values (fielddata/loaders/brazil_star_SCHEMA.md).")
    if package == "shenzhen_charging":
        d = _deltas(package)
        facts["charging_sessions"] = fact(d["charging_sessions"], "measured", DELTAS.format(package),
            "Distinct transaction_id in processed_data.xlsx; 4,538 sessions repeated in Sheet1 and Sheet7 are counted once.")
        facts["charging_fault_labels"] = fact(d["charging_fault_labels"], "measured", DELTAS.format(package),
            "Sessions labelled faulty (label 1). The Readme describes two kinds of battery fault: faults reported by engineering personnel (thermal runaway, unbalanced cell voltages, short circuit) and over-temperature disconnections by the stations. "
            "Counted as battery faults, per session, batteries not identified (maintainer, 2026-10-13; docs/descriptor/TABLE3_faults.md).")
