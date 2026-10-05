"""Human-readable descriptions of each package, shared by the explorer app and the notebooks.

Every entry is plain language a battery engineer can read. Facts here must already be established in
the package's notebook or schema file. Nothing internal to the project goes here: this is public text.

Keys per package:
  description   one paragraph on what the package is
  systems_word  the concrete word for one monitored system ("vehicle", "storage unit")
  groups        optional: selector name and a note per group value (cao manufacturers)
  files         optional: selector name and a note per file (cao vin_1/2/3, m5bat bms/bsc)
"""

SPECS = {
    "cao": {
        "systems_word": "vehicle",
        "description": (
            "Cao et al. published telemetry from electric vehicles belonging to three anonymised "
            "manufacturers, coded DTI, QAS and GIS. The paper states 515 vehicles, whereas the release "
            "contains 514. Each vehicle has a folder holding three data files, saved with PyTorch. The files "
            "carry no column names, no units and no timestamps. Faulty-or-healthy labels are given for all "
            "80 DTI vehicles and for 82 of the 393 QAS vehicles. GIS has no labels. The data are seven zip "
            "archives, 38 GB, on Zenodo under CC BY 4.0. The public release carries only a binary label, not "
            "the fault type the paper discusses."
        ),
        "groups": {
            "label": "Manufacturer",
            "notes": {
                "DTI": "80 vehicles, 85 cell channels each, cell voltages in millivolts (NMC range). "
                       "Labels for all 80: 77 healthy, 3 faulty. Deviation block is a constant 0.1 in most "
                       "vehicles and carries no information.",
                "QAS": "393 vehicles, 110 cell channels each, cell voltages in volts (LFP range). Labels "
                       "for 82 vehicles: 24 healthy, 58 faulty. The other 311 are unlabeled, not healthy. "
                       "Deviation columns equal cell voltage minus the row mean.",
                "GIS": "41 vehicles, 90 columns, no labels. A pack-level voltage, temperature, state of "
                       "charge, an odometer-like counter, and 85 small columns (0 to 0.07) whose meaning is "
                       "not established.",
            },
        },
        "files": {
            "label": "File",
            "notes": {
                "vin_2": "The measurements table, in physical units. Two pack-level values, N cell "
                         "voltages, N per-cell deviations, then temperature, state of charge and current. "
                         "N is 85 for DTI and 110 for QAS. This is the file to look at.",
                "vin_3": "The same table rescaled to roughly 0 to 1, with one extra placeholder column "
                         "(a constant 65535). The input to the authors' second model.",
                "vin_1": "Seven normalized features per row, all between 0 and 1, one always zero. The "
                         "input to the authors' sequence model, most likely voltage, temperature, current, "
                         "state of charge, speed and mileage plus one unused slot. Not raw telemetry.",
            },
        },
    },
    "m5bat-pbacid": {
        "systems_word": "storage unit",
        "description": (
            "One flooded lead-acid battery string (Exide OCSM, unit Pb1) in the M5BAT hybrid storage plant "
            "at RWTH Aachen, recorded at one second resolution from 2017 to 2025. About 250 million rows "
            "from each of two sources, saved as one Parquet file per year, with a codebook giving every "
            "column's unit and meaning. The unit provided frequency containment reserve until 2021 and ran "
            "in a low-utilisation reserve mode from 2022. A companion paper analyses its degradation."
        ),
        "files": {
            "label": "Source",
            "notes": {
                "bms": "Battery management system: DC power, current, terminal voltage, state of charge, "
                       "energy counters and two voltage-imbalance flags. 8 columns.",
                "bsc": "Power conversion system controller: AC power, grid frequency, cabinet temperature, "
                       "energy counters, operating-mode flags, setpoints and inverter measurements. 23 columns.",
            },
        },
    },
    "ppl": {
        "systems_word": "battery energy storage system",
        "description": (
            "PPL released one-minute telemetry for the 1 MW / 2 MWh lithium-ion BESS at E.W. Brown "
            "Generating Station. The annual ESS CSV files span 2017-11-01 through 2026-02-01 and contain "
            "4,339,805 rows. The shared columns include average SOC, BMS-reported SOH, real power, mode, "
            "fault status, running status, average cell voltage, and container temperatures. The 2017-2021 "
            "files also carry max/min cell voltage and max/min module temperature, while 2022-2025 add DC "
            "voltage, DC current, charge energy, and discharge energy."
        ),
    },
    "deng": {
        "systems_word": "vehicle pack",
        "description": (
            "Deng et al. released charging telemetry for 20 BAIC EU500 vehicle packs with CATL NCM cells. "
            "The held archives contain 16,100,728 rows spanning 2019-07-22 through 2021-11-16. Each pack "
            "CSV includes record time, SOC, pack voltage, charge current, max and min cell voltage, max and "
            "min temperature, available energy, and available capacity. The median row cadence is 8 seconds "
            "for 15 packs and 10 seconds for 5 packs."
        ),
    },
    "schaeffer": {
        "systems_word": "battery system",
        "description": (
            "Schaeffer et al. released timestamped field telemetry from 28 portable 24 V LFP battery "
            "systems that were returned to the manufacturer. Each system has eight series-cell voltages, "
            "one pack-current sensor, pack SOC, four temperature sensors, and eight balancing-current "
            "channels. The CSV records range from one month to five years."
        ),
    },
}
