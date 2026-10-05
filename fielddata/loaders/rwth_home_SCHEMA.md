# rwth-home schema

Source files: `Data_ID_01.zip` to `Data_ID_21.zip`, one per home-storage system, each holding monthly CSVs `<NN>/YYYY_MM_System_ID_NN.csv`, and `Metadata_and_Code.zip` with `Metadata_Systems.xlsx`, `Capacity_Tests.xlsx` and the authors' MATLAB code. The deposit holds 1,269 monthly CSVs (2015-07 to 2022-12), all matching the name pattern and their archive's ID (source-audit check 2026-10-04, `members()`); the paper (p. 1439, Data availability) and SI Note 2 (p. 3) say "1,270". No file is misnamed, so `months()` drops none; the deposit has one file fewer than stated, and which one cannot be told from the gaps (most systems lack 2020-10, 2020-11 and 2021-02 to 2021-08, transmission outages per SI Note 2).

`systems()` gives each system's archive, size, number of months and first and last month. `months(system)` lists its monthly files and `members(system)` every member name of its archive. `metadata()` returns `Metadata_Systems.xlsx` as released, including chemistry and cell number per system.

`load(unit, month=None)` reads one system, all months or the given `"YYYY-MM"` month(s), indexed by `Time` (1 s rows, parsed from `dd-MMM-yyyy HH:mm:ss`, SI Note 2). A whole system is tens of millions of rows, so pass `month` to read less.

## Measurement and processing before release

The values are measured by research loggers, not by the storage system's BMS: Gantner A127 with a Gantner Q.pac logger (hardware version 1, IDs 14, 18, 21) or Electrex Femto / Atto D4 with a Gantner Q.reader (version 2, the other IDs), with voltage accuracy 0.05 % (v1) or 0.25 % (v2), a current shunt of 0.5 %, and PT100 temperature sensors (SI Note 1, pp. 2-3; SI Table 2). "The measurement sensors were installed between the DC side of the converter and the system-level battery. Thus, the provision of power to the BMS inside the storage system is included in the measurements" (SI Note 1). The BMS self-supply and balancing show up as a small steady current offset, "around -30 mA for the shown system" (SI Methods, SOC estimation and current offset, p. 16).

Data cleaning by the authors (SI Note 2, p. 4): invalid values "outside the regular operation limits, such as a battery voltage of 0 V ... are filtered"; the filters follow datasheet limits and manual inspection and are not published; "The filtered outliers are changed to 'not a number' (NaN)". "A linear interpolation was used for gaps of up to 5 min" onto the 1 s grid; longer gaps remain gaps. NaN values in the released files can therefore be the authors' removed outliers.

Time zone: not stated (SI Note 2 gives only the format). The clock does not follow daylight saving time: on 2018-03-25 every system with data has all 3,600 rows from 02:00 to 02:59, and on 2018-10-28 no timestamp is repeated (16 systems checked, raw data, source-audit check). The timestamps are therefore UTC or a fixed offset, not German civil time; which one is not stated. `load()` assigns no zone.

## Columns

| column | unit | role |
|---|---|---|
| P_in_W | W | Battery DC power. Positive = charging (SI Fig. 1: "Positive HSS power represents charging"). |
| V_in_V | V | Battery (system-level) voltage. |
| I_in_A | A | Battery current. "Positive currents correspond to charging, negative currents represent the discharge" (SI Note 4, p. 7; paper Fig. 1e). This is the opposite of several other releases. Measured on raw data, March and October 2018, 16 systems: mean current at 10:00 to 13:00 is positive in 31 of 32 system-months and at 20:00 to 23:00 negative in 30 of 32 (exceptions: ID 18 in March, ID 01 evenings in October at +0.06 A). |
| T_Bat_in_C | C | Pack-housing temperature from a PT100 "attached to the outside of the battery pack or in the HSS housing"; "not the cell but the pack housing temperature" and "not comparable for different manufacturers" (SI Notes 2 and 3, SI Fig. 2). |
| T_Room_in_C | C | Room temperature of the installation room (SI Note 2). |
| Interpolated | flag | 1 = linearly interpolated (gap of up to 5 min), 0 = measured (SI Note 2). |

No cell voltages are released. `clean=True` changes nothing: the authors already replaced outliers with NaN.

## Metadata and events

`Metadata_Systems.xlsx` gives nominal capacity, voltage and energy, usable datasheet energy, cells in series and parallel, inverter power, manufacturer letter, chemistry and installation dates. Its `Chemistry` column says "LMO" for IDs 1 to 6, and its `Chemistry_detail` column says "LMO/NMC": the paper calls them "a blend of lithium manganese oxide (LMO) and NMC (simply referred to as 'LMO' in this paper)" (p. 1439). "Two of the NMC systems have a high nickel share" and "are sometimes classified as NCA" (paper p. 1439, SI Note 1). The metadata were gathered by the authors from labels, datasheets, interviews and teardowns, and "the obtained values are not guaranteed to be correct", and "the interconnection scheme is not accessible" (SI Note 1, p. 2).

`Capacity_Tests.xlsx` lists the start time and system ID of 60 field capacity tests (SI Note 2; SI Note 6). It is not read by the loader.

Measurements ended early for three systems: ID 18 (owner change, 2020) and IDs 14 and 21 (defective after the 2021 flood in western Germany) (SI Note 1, p. 3). Software updates changed control behaviour, power derating and EOD/EOC voltages over time (SI Note 5, p. 8), which affects capacity comparisons across years.
