"""Write and execute the short package notebooks for packages that have a loader but no hand-built notebook.

Usage: python scripts/make_notebooks.py <package> [<package> ...]
Each notebook has the same four sections: released units, one unit as released, raw signal ranges and
a first look at one signal. The text is per package and describes the executed output.
Execution needs the data (fielddata.config.data_root). Run scripts/check_notebook.py on the result.
"""
from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent
SETUP = """from pathlib import Path
import sys
import matplotlib.pyplot as plt
import pandas as pd

ROOT = next(path for path in [Path.cwd(), *Path.cwd().parents] if (path / 'fielddata').exists())
sys.path.insert(0, str(ROOT))
from fielddata import load, systems
"""

SPECS = {
    "cao": dict(
        title="Cao 2025 EV fleet telemetry from three manufacturers",
        intro="This notebook lists the vehicles in the Zenodo release, opens one QAS vehicle's main table (vin_2) as released, and plots one cell voltage. It makes no diagnosis. The files carry no column names, units or timestamps, so the column names here are the loader's inferred names. `notebooks/cao_in_depth.ipynb` explains every column and the checks behind each name.",
        systems_note="The release has 514 vehicles, one row each, with the archive it sits in, which of the three files it has, and its label (0 healthy, 1 faulty, empty where the authors gave none). The rows shown run from DTI vehicle 0 to QAS vehicle 392.",
        load="frame = load('cao', brand='QAS', vehicle='189', names='inferred')",
        load_note="QAS vehicle 189 has 32,649 rows and 225 columns: two pack-model values, 110 cell voltages, 110 voltage deviations, then temperature, state of charge and current. State of charge is in percent, because the loader converts QAS from the released fraction. There is no time column.",
        ranges_note="These ranges are raw values before any cleaning, as released except that state of charge is converted to percent. Current values near -1,000 A are placeholders, not measurements. The in-depth notebook explains them.",
        cols="['cell_v_001', 'cell_v_110', 'temperature_degC', 'soc_pct', 'current_A']",
        plot="ax = frame['cell_v_001'].plot(figsize=(7, 3.5), lw=0.6, legend=False)\nax.set_xlabel('row (no timestamps, rows about 30 s apart)')\nax.set_ylabel('cell 1 voltage (V)')\nplt.show()",
        plot_note="Cell 1 of QAS vehicle 189 cycles between about 3.1 and 3.4 V over the record, with long charges rising to about 3.4 V. Row number stands in for time.",
    ),
    "bilfinger2024": dict(
        title="Bilfinger 2024 vehicle-level charging recordings",
        intro="This notebook lists the files in the mediaTUM release, opens one VW ID.3 charging recording as released, and plots its pack voltage. It makes no diagnosis.",
        systems_note="Each row is one released file. The vehicle recordings and raw logs come from a 2021 VW ID.3 and a 2020 Tesla Model 3. The laboratory cell and half-cell files are reference measurements, not field units.",
        load="frame = load('bilfinger2024', unit='VW_ID3_JB_8A_C40_2021')",
        load_note="The recording is one slow charge. It has one column per series position (108 for the ID.3, each a pair of cells in parallel) next to pack voltage, current, BMS SOC, the charge integrated from current, and elapsed time.",
        cols="['U', 'I', 'SOC', 'Q', 'cell_voltage_1']",
        plot="ax = frame.plot(x='time_h', y='U', legend=False, figsize=(7, 3.5))\nax.set_xlabel('elapsed time (h)')\nax.set_ylabel('pack voltage (V)')\nplt.show()",
        plot_note="Pack voltage rises steadily through the slow 8 A charge.",
    ),
    "bilfinger2026": dict(
        title="Bilfinger 2026 vehicle-level charging recordings",
        intro="This notebook lists the files in the mediaTUM release, opens one CUPRA Born charging recording as released, and plots its pack voltage. It makes no diagnosis.",
        systems_note="Each row is one released file, with the vehicle it belongs to. Five CUPRA Born, one VW ID.3 and one Tesla Model 3 appear. The ID.3 and the Tesla are the two vehicles of bilfinger2024 and count once in the collection totals.",
        load="frame = load('bilfinger2026', unit='Cupra_204_JB_8A_CEE7_C45')",
        load_note="The recording is one charge of CUPRA 204. Column order differs between files in this release, so columns are selected by name.",
        cols="['U', 'I', 'SOC', 'Q', 'cell_voltage_1']",
        plot="ax = frame.plot(x='time_h', y='U', legend=False, figsize=(7, 3.5))\nax.set_xlabel('elapsed time (h)')\nax.set_ylabel('pack voltage (V)')\nplt.show()",
        plot_note="Pack voltage rises through the charge, the shape the paper's differential voltage analysis starts from.",
    ),
    "changan": dict(
        title="Changan 300-vehicle raw telemetry",
        intro="This notebook lists the 300 vehicle files inside the split archive, streams the first 20,000 rows of one vehicle without unpacking the archive, and plots pack voltage. It makes no diagnosis.",
        systems_note="Each row is one vehicle RAR inside the two-volume split zip, with the volume and byte offset where it starts.",
        load="frame = load('changan', unit='vin3', nrows=20000)",
        load_note="The rows are 10 s telemetry as released. `terminaltime` is a relative clock with no calendar date, and the per-cell voltages arrive as one `~`-separated string of 96 values.",
        cols="['terminaltime', 'soc', 'totalvoltage', 'totalcurrent', 'minvoltagebattery', 'maxvoltagebattery']",
        plot="ax = frame['totalvoltage'].plot(figsize=(7, 3.5))\nax.set_xlabel('row in file order')\nax.set_ylabel('pack voltage (V)')\nplt.show()",
        plot_note="In the first 5,000 rows pack voltage often reads 0 V. In these rows the BMS block is zero or, with chargestatus 255, the current is a fill value of -1000 A (see the schema file). `clean=True` masks the 0 V values and the -1000 A current. After that the file shows charges to about 400 V and falling voltage while driving. File order is used because `terminaltime` is not sorted in the release.",
    ),
    "cloverleaf": dict(
        title="Cloverleaf second-life battery monitoring workbook",
        intro="This notebook lists the worksheets in the released workbook, loads one HV pack sheet, and plots its SOH. It makes no diagnosis.",
        systems_note="The three units are the three HV packs of one second-life system, as 20,000 s averages. The workbook also holds a typical day of the whole system at 172 s averages, which is not a unit and is loaded with `load('cloverleaf', unit='typical day')`.",
        load="frame = load('cloverleaf', unit='SNAM HV - 2100173')",
        load_note="The sheet runs from 2021-09-01 to 2022-01-01 with one averaged row about every 5.6 hours.",
        cols="['SOH', 'SOC', 'Vcavg', 'Vcdif', 'Vpack', 'Ipack']",
        plot="ax = frame['SOH'].plot(figsize=(7, 3.5), drawstyle='steps-post')\nax.set_xlabel('')\nax.set_ylabel('SOH (%)')\nplt.show()",
        plot_note="SOH steps down from 92 to 90 percent over the four months. Values between the steps are averages over a 20,000 s window.",
    ),
    "evbattery": dict(
        title="EVBattery charging snippets",
        intro="This notebook lists the released vehicles from the committed snippet index, loads every snippet of one vehicle, and plots one snippet. It makes no diagnosis.",
        systems_note="Each row is one labeled vehicle with its archive and snippet count. One labeled car, car 545 in battery_dataset3, has no snippets, which is why the release carries data for 464 vehicles as the paper states.",
        load="frame = load('evbattery', unit='battery_dataset3:500')",
        load_note="Each snippet is 128 rows with its own relative clock in seconds, so snippets are stacked rather than joined on time. The table also carries each snippet's charge segment, label, mileage and capacity field.",
        cols="['volt', 'current', 'soc', 'max_single_volt', 'min_single_volt', 'max_temp', 'mileage']",
        plot="first = frame[frame['snippet'] == frame['snippet'].iloc[0]]\nax = first.plot(x='timestamp', y=['max_single_volt', 'min_single_volt'], figsize=(7, 3.5), color=['0.2', '0.6'], legend=False)\nax.set_xlabel('snippet clock (s)')\nax.set_ylabel('cell voltage (V)')\nplt.show()",
        plot_note="Within one snippet the two cell-voltage extremes rise together through the charge, about 35 mV apart.",
    ),
    "fei_bus": dict(
        title="Commercial electric bus SOH tables",
        intro="This notebook lists the four released bus files, loads them, and plots SOH against mileage. It makes no diagnosis.",
        systems_note="Each row is one bus. The files are short summary tables, not telemetry.",
        load="frame = load('fei_bus')",
        load_note="All four buses together give 662 SOH estimates with mileage. The release has no timestamps.",
        cols="['SOH', 'SOH(OCV)', 'mileage']",
        plot="fig, ax = plt.subplots(figsize=(7, 3.5))\nfor unit, group in frame.groupby('unit'):\n    ax.plot(group['mileage'], group['SOH'], '.', color='0.4', markersize=4)\nax.set_xlabel('mileage (km)')\nax.set_ylabel('SOH (fraction)')\nplt.show()",
        plot_note="Across the four buses SOH stays mostly between 0.7 and 0.95 over 260,000 km, with wide scatter between neighbouring estimates and no clear trend in this view. The record does not say how the estimates were made.",
    ),
    "flashbattery-agv": dict(
        title="Flash Battery AGV per-cycle table",
        intro="This notebook lists the ten released AGV packs, loads their per-cycle rows, and plots one pack's temperature per cycle. It makes no diagnosis.",
        systems_note="Each row is one pack with its number of cycles and first and last calendar day.",
        load="frame = load('flashbattery-agv')",
        load_note="The release has one aggregate row per cycle: a cycle counter, the cycle duration, a cumulative discharge counter and pack temperature extremes. There are no voltage or current series.",
        cols="['counter', 'cycletime', 'totaldischarge', 'mintemperature', 'maxtemperature']",
        plot="one = frame[frame['unit'] == 'FB-0']\nax = one['maxtemperature'].plot(style='.', color='0.4', markersize=2, figsize=(7, 3.5))\nax.set_xlabel('')\nax.set_ylabel('pack temperature per cycle (C)')\nplt.show()",
        plot_note="Pack FB-0's per-cycle temperature follows a seasonal pattern, warmer from November to April than in summer.",
    ),
    "ku_leuven_bev": dict(
        title="KU Leuven battery-electric vehicle sessions",
        intro="This notebook lists the two vehicles and their sessions, loads one vehicle's slow-charging sessions, and plots SOC through one session. It makes no diagnosis.",
        systems_note="Each row is one vehicle with its number of sessions of each type and its first and last session date.",
        load="frame = load('ku_leuven_bev', unit='BEV1', session_type='slow charging')",
        load_note="The table stacks BEV1's 42 slow-charging sessions, indexed by UTC time. Columns are the decoded CAN signals, named with their CAN message id.",
        cols="['SOCave292', 'BattVoltage132', 'RawBattCurrent132', 'BMSmaxPackTemperature', 'TotalChargeKWh3D2']",
        plot="one = frame[frame['session'] == frame['session'].iloc[0]]\nax = one['SOCave292'].plot(figsize=(7, 3.5))\nax.set_xlabel('')\nax.set_ylabel('SOC (%)')\nplt.show()",
        plot_note="SOC rises steadily through one slow charge and then holds near 100 percent.",
    ),
    "li2026": dict(
        title="li2026 energy-storage-station cells",
        intro="This notebook lists the 90 released battery groups, loads one eight-cell group, and plots one cell voltage. It makes no diagnosis.",
        systems_note="Each row is one eight-cell group in one of three recording periods. There are 240 numbered cells, while the paper describes 200.",
        load="frame = load('li2026', unit='real_world_02-03/battery_01')",
        load_note="The group's files are joined in sample order. The release has no calendar timestamps, so the index is the sample number from the file names.",
        cols="['cell_001_V', 'cell_008_V', 'cell_001_T', 'cur']",
        plot="ax = frame['cell_001_V'].iloc[:4000].plot(figsize=(7, 3.5))\nax.set_xlabel('sample')\nax.set_ylabel('cell 001 voltage (V)')\nplt.show()",
        plot_note="Over the first 4,000 samples cell 001 charges, discharges and charges again, with the flat plateaus of an LFP cell.",
    ),
    "m5bat-2023-04": dict(
        title="M5BAT evaluation month 04/2023",
        intro="This notebook lists the released unit files, loads one battery unit at 1 s resolution for the month, and plots its SOC over one day. It makes no diagnosis.",
        systems_note="Each row is one CSV: ten battery units and BESS, the plant connection point. Batt1 is the lead-acid string also released as m5bat-pbacid. The report's p. 3 table gives each unit's technology: Batt1-2 OCSM lead-acid, Batt3-4 OPzV lead-acid gel, Batt5-8 LMO, Batt9 LFP, Batt10 LTO.",
        load="frame = load('m5bat-2023-04', unit='Batt2')",
        load_note="The unit has one row per second for all of April 2023. Values are integers as released. The evaluation report (pp. 6-7) gives their units: SOC in 0.1 %, I_DC_Batt in 0.1 A, U_DC_Batt in 0.1 V, power in kW and kVAr (negative = charging). The index is UTC (report pp. 6-7).",
        cols="['P_AC', 'SOC', 'I_DC_Batt', 'U_DC_Batt', 'interpolated']",
        plot="ax = frame.loc['2023-04-10', 'SOC'].plot(figsize=(7, 3.5))\nax.set_xlabel('')\nax.set_ylabel('SOC (released integer)')\nplt.show()",
        plot_note="Over one day the released SOC integer stays within a few units of 689, so the unit held a near-constant state of charge that day.",
    ),
    "rwth-android": dict(
        title="RWTH Android device battery telemetry",
        intro="This notebook lists the 33 released devices, loads one, and plots its state of charge. It makes no diagnosis.",
        systems_note="Each row is one device, with its manufacturer, model, battery technology and the span of its records.",
        load="unit = systems('rwth-android')['unit'].iloc[0]\nframe = load('rwth-android', unit=unit)",
        load_note="The device table carries the Android battery fields as exported by the Mobile Battery Data Explorer, indexed by timestamp.",
        cols="['state_of_charge', 'current', 'voltage_cell', 'temperature_cell', 'charge_counter']",
        plot="ax = frame['state_of_charge'].plot(figsize=(7, 3.5))\nax.set_xlabel('')\nax.set_ylabel('state of charge (%)')\nplt.show()",
        plot_note="State of charge falls over days and jumps back up at each charge, often to 100 percent.",
    ),
    "rwth-home": dict(
        title="RWTH home-storage field measurements",
        intro="This notebook lists the 21 released systems, loads one month of one system at 1 s resolution, and plots battery voltage. It makes no diagnosis.",
        systems_note="Each row is one home-storage system with its number of monthly files and first and last month.",
        load="frame = load('rwth-home', unit=1, month='2015-08')",
        load_note="The August 2015 file of system 01 at 1 s resolution. The release carries battery power, voltage, current and temperature, room temperature, and a flag for values the publisher filled.",
        cols="['P_in_W', 'V_in_V', 'I_in_A', 'T_Bat_in_C', 'T_Room_in_C']",
        plot="ax = frame['V_in_V'].resample('10min').mean().plot(figsize=(7, 3.5))\nax.set_xlabel('')\nax.set_ylabel('battery voltage (V, 10 min mean)')\nplt.show()",
        plot_note="Battery voltage follows a daily cycle, rising while the system charges during the day and falling as it discharges in the evening and night.",
    ),
    "aitio": dict(
        title="BBOXX solar-home-system batteries",
        intro="This notebook lists the released batteries with their repair labels, loads one battery as released, and plots its voltage over one week. It makes no diagnosis.",
        systems_note="Each row is one battery, one .npz file inside one of the shipped zips, joined with meta_data.csv. STILL_ALIVE is FALSE for the 491 batteries that entered repair for capacity loss. The authors chose this roughly balanced split, so it is not a failure rate.",
        load="frame = load('aitio', unit='0')",
        load_note="One battery at a median 60 s interval, indexed by UTC time. Current is negative while charging, as the readme states.",
        cols="['current_A', 'voltage_V', 'temperature_degC']",
        plot="week = frame.loc['2019-06-01':'2019-06-07']\nax = week['voltage_V'].plot(figsize=(7, 3.5))\nax.set_xlabel('')\nax.set_ylabel('battery voltage (V)')\nplt.show()",
        plot_note="Over the week of 1 to 7 June 2019 the raw voltage of battery 0 stays between 12.0 and 14.4 V, with a median of 12.9 V.",
    ),
    "tsukuba": dict(
        title="Tsukuba research-building microgrid",
        intro="This notebook shows the one released system and its per-second files, loads two days, and plots battery SOC. It makes no diagnosis.",
        systems_note="The release is one building microgrid with one lead-acid battery. Raw and publisher-cleaned per-second files are both released.",
        load="frame = load('tsukuba', start='2016-03-01', end='2016-03-02')",
        load_note="Two days at one row per second. Column names are English translations of the Japanese headers, and units are kept in the frame's attributes.",
        cols="['battery_active_power', 'battery_dc_voltage', 'battery_dc_current', 'battery_soc', 'pv_active_power']",
        plot="ax = frame['battery_soc'].plot(figsize=(7, 3.5))\nax.set_xlabel('')\nax.set_ylabel('battery SOC (%)')\nplt.show()",
        plot_note="Over two days battery SOC stays between 91 and 95 percent, discharging during the working day and recharging in the evening.",
    ),
    "tumftm": dict(
        title="TUM FTM electric-vehicle UDS data",
        intro="This notebook lists the seven released vehicles, loads one signal for one vehicle, and plots it with the observed 2087 timestamps masked. It makes no diagnosis.",
        systems_note="Each row is one vehicle file in long format: one row per timestamp and signal.",
        load="frame = load('tumftm', unit='CUP1', value_id=1200, clean=True)",
        load_note="Pack voltage (value id 1200) for CUP1, with `variable_name` and `unit` joined from the release's signal table. `clean=True` sets the 2087 timestamps, which we observed in the data and the authors do not describe, to NaT and keeps their rows.",
        cols="['value']",
        plot="series = frame.dropna(subset=['time']).set_index('time')['value'].sort_index()\nax = series.resample('1D').median().plot(figsize=(7, 3.5), style='.', color='0.4')\nax.set_xlabel('')\nax.set_ylabel('pack voltage (V, daily median)')\nplt.show()",
        plot_note="Daily median pack voltage of CUP1 from November 2022 to April 2023, from cleaned timestamps, with a gap in early March.",
    ),
    "xie": dict(
        title="Xie swap-station device data",
        intro="This notebook lists the 271 released devices with their labels, loads all devices, and plots the cell voltages of one device. It makes no diagnosis.",
        systems_note="Each row is one device file with its device label from the released records table.",
        load="released = systems('xie')\nframe = load('xie', unit=list(released['unit']))",
        load_note="All 271 devices together are 20,780 rows. Rows are hours apart, and each device has 16 to 20 cell-voltage columns in mV.",
        cols="['totalCurrent', 'batCoreVoltage1', 'batCoreVoltage16', 'batCoreTemp1']",
        plot="one = frame[frame['unit'] == frame['unit'].iloc[0]]\ncells = [c for c in one.columns if c.startswith('batCoreVoltage') and one[c].gt(0).any()]\nax = one[cells].plot(figsize=(7, 3.5), color='0.6', legend=False)\nax.set_xlabel('')\nax.set_ylabel('cell voltage (mV)')\nplt.show()",
        plot_note="Most cells of this device move together, and one cell departs from the group several times. That kind of departure is what the paper's fault screening looks for.",
    ),
    "zhang2023": dict(
        title="Zhang 2023 charging snippets",
        intro="This notebook lists the released vehicles from the committed snippet index, loads every snippet of one vehicle, and plots one snippet. It makes no diagnosis.",
        systems_note="Each row is one labeled vehicle with its archive and snippet count. One labeled car, car 230 in battery_brand2, has no snippets, so the release carries data for 347 vehicles as the paper states.",
        load="frame = load('zhang2023', unit='battery_brand3:401')",
        load_note="Each snippet is 128 rows with its own relative clock in seconds, stacked with its charge segment, label and mileage.",
        cols="['volt', 'current', 'soc', 'max_single_volt', 'min_single_volt', 'max_temp', 'mileage']",
        plot="first = frame[frame['snippet'] == frame['snippet'].iloc[0]]\nax = first.plot(x='timestamp', y=['max_single_volt', 'min_single_volt'], figsize=(7, 3.5), color=['0.2', '0.6'], legend=False)\nax.set_xlabel('snippet clock (s)')\nax.set_ylabel('cell voltage (V)')\nplt.show()",
        plot_note="Within one snippet the two cell-voltage extremes rise together through the charge, about 10 mV apart.",
    ),
    "zhou2026": dict(
        title="Zhou 2026 vehicle data",
        intro="This notebook lists the three released vehicles from the committed partition index, loads a few columns for one vehicle, and plots its daily median SOC. It makes no diagnosis.",
        systems_note="Each row is one vehicle identifier in the release with its partitions, rows and first and last timestamp. The paper's fleet is 133 vehicles.",
        load="frame = load('zhou2026', unit='vehicle45', columns=['SOC', 'TotalVoltage', 'TotalCurrent', 'ChargingStatus'])",
        load_note="Four columns of vehicle45 over all 20 of its partitions. The per-cell strings are left out here because they need a lot of memory.",
        cols="['SOC', 'TotalVoltage', 'TotalCurrent', 'ChargingStatus']",
        plot="ax = frame['SOC'].resample('1D').median().plot(figsize=(7, 3.5), style='.', color='0.4')\nax.set_xlabel('')\nax.set_ylabel('SOC (%, daily median)')\nplt.show()",
        plot_note="Daily median SOC of vehicle45 over nearly three years of operation, with gaps where the vehicle did not report.",
    ),
}


def build(package: str) -> Path:
    s = SPECS[package]
    md, code = nbformat.v4.new_markdown_cell, nbformat.v4.new_code_cell
    cells = [
        md(f"# {s['title']}\n\n{s['intro']}"),
        md("## 1. Released units"),
        md(f"This step lists what `systems('{package}')` reports for the release."),
        code(SETUP + f"\nreleased = systems('{package}')\ndisplay(released)"),
        md(s["systems_note"]),
        md("## 2. One unit as released"),
        md("This step loads one unit with the default `clean=False`, so every value is as released."),
        code(s["load"] + "\nprint(frame.shape)\ndisplay(frame.head())"),
        md(s["load_note"]),
        md("## 3. Signal ranges"),
        md("This step summarises a few signals of the loaded unit."),
        code(f"display(frame[{s['cols']}].describe().T)"),
        md(s.get("ranges_note", "These ranges are raw values as released, before any cleaning. The schema file next to the loader lists units and any sentinel codes.")),
        md("## 4. A first look"),
        md("This step plots one signal to show the shape of the data."),
        code(s["plot"]),
        md(s["plot_note"]),
    ]
    nb = nbformat.v4.new_notebook(cells=cells)
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(ROOT / "notebooks")}}).execute()
    nb.metadata.pop("kernelspec", None)
    path = ROOT / "notebooks" / f"{package.replace('-', '_')}.ipynb"
    nbformat.write(nb, path)
    return path


if __name__ == "__main__":
    for name in sys.argv[1:]:
        print(build(name))
