# PPL E.W. Brown BESS schema

Source files: `BESS-Analysis/ESS_2017.csv` through `BESS-Analysis/ESS_2025.csv` inside the package data directory. The loader reads these annual CSV files directly from the held data directory and does not resample or convert units.

The system is one 1 MW / 2 MWh LG Chem lithium-ion battery at the PPL Renewable Integration Research Facility, E.W. Brown Generating Station: 20 racks in two climate-controlled containers, each rack holding 17 modules of 14 cells (51.8 V, 126 Ah per module), 4,760 cells in all, with a 1 MVA bidirectional inverter (paper Section II, Fig. 1, Section IV). The cathode chemistry is not stated.

Not read by `load()`: `BESS-Analysis/Weather_2017-2025.csv` and the cell-level share in `cell_level/` (see the last section).

## Files and measured coverage

| file | rows | first timestamp | last timestamp | median cadence |
|---|---:|---|---|---:|
| ESS_2017.csv | 87,780 | 2017-11-01 01:00:00 | 2017-12-31 23:59:00 | 60 s |
| ESS_2018.csv | 525,600 | 2018-01-01 00:00:00 | 2018-12-31 23:59:00 | 60 s |
| ESS_2019.csv | 525,600 | 2019-01-01 00:00:00 | 2019-12-31 23:59:00 | 60 s |
| ESS_2020.csv | 527,040 | 2020-01-01 00:00:00 | 2020-12-31 23:59:00 | 60 s |
| ESS_2021.csv | 525,301 | 2021-01-01 00:00:00 | 2021-12-31 19:00:00 | 60 s |
| ESS_2022.csv | 525,601 | 2022-01-01 00:00:00 | 2023-01-01 00:00:00 | 60 s |
| ESS_2023.csv | 525,601 | 2023-01-01 00:00:00 | 2024-01-01 00:00:00 | 60 s |
| ESS_2024.csv | 527,041 | 2024-01-01 00:00:00 | 2025-01-01 00:00:00 | 60 s |
| ESS_2025.csv | 570,241 | 2025-01-01 00:00:00 | 2026-02-01 00:00:00 | 60 s |
| total | 4,339,805 | 2017-11-01 01:00:00 | 2026-02-01 00:00:00 | 60 s |

## Annual ESS columns

The PPL release changes schema after 2021. `ESS_2017.csv` through `ESS_2021.csv` have 20 columns. `ESS_2022.csv` through `ESS_2025.csv` have 19 columns.

| column | unit | dtype as loaded | years present | notes |
|---|---|---|---|---|
| Timestamp | timestamp | datetime64[ns, UTC] index in `load()` | 2017-2025 | Released as a CSV column and set as the index by `load()`. Time zone not stated; the UTC tag is the loader's label, not a source fact (see Time stamps). |
| Year | year | integer | 2017-2025 | Calendar year field from the release. |
| Month | month number | integer | 2017-2025 | Calendar month field from the release. |
| Day | day number | integer | 2017-2025 | Calendar day field from the release. |
| Hour | hour number | integer | 2017-2025 | Calendar hour field from the release. |
| Minute | minute number | integer | 2017-2025 | Calendar minute field from the release. |
| AvgSOC | % | float | 2017-2025 | Average battery state of charge as estimated by the BMS (paper Fig. 3, "BMS-reported state-of-charge"). |
| SOH | % | float | 2017-2025 | State of health estimated by the BMS (paper Section III, Fig. 2). It falls from about 100 % to 84 % by 2023 (paper Section III), while the reference performance tests give a capacity loss approaching 13 % by the end of 2025 (Section VI); the test results are in paper Tables 4 and 5, not in the release. |
| PowerReal | kW | float | 2017-2025 | Real battery power. Positive means discharging (measured, see Sign convention). |
| Mode | category | string | 2017-2025 | Operating mode text, for example Idle, TargetSOC, PSmoothing, AutoFreqWatt, LGFollowing. The publisher gives no definitions. |
| Fault | flag or numeric status | float | 2017-2025 | Fault status column. Code meanings are not published. |
| Active | flag | float | 2017-2021 | Present only in the older CSV schema. Code meanings are not published; the paper lists "unit status (active and running)" among the logged values (Section III). |
| Running | flag | float | 2017-2025 | Battery system running flag. Code meanings are not published. |
| CellVoltAvg | V | float | 2017-2025 | Average cell voltage. |
| CellVoltMax | V | float | 2017-2021 | Present only in the older CSV schema. |
| CellVoltMin | V | float | 2017-2021 | Present only in the older CSV schema. |
| ModuleTempMax | C | float | 2017-2021 | Present only in the older CSV schema. |
| ModuleTempMin | C | float | 2017-2021 | Present only in the older CSV schema. |
| Container1.Temp | C | float | 2017-2025 | Container 1 temperature. |
| Container2.Temp | C | float | 2017-2025 | Container 2 temperature. |
| DCVoltage | V | float | 2022-2025 | Present only in the newer CSV schema. |
| DCCurrent | A | float | 2022-2025 | Present only in the newer CSV schema. Positive means charging (measured, see Sign convention). |
| ChargeEnergy | kWh | float | 2022-2025 | Present only in the newer CSV schema. |
| DischargeEnergy | kWh | float | 2022-2025 | Present only in the newer CSV schema. |

## Unit and reference-test capacity sources

`systems()` returns one row for `E_W_Brown_BESS`, the 1 MW / 2 MWh lithium-ion battery energy storage system at E.W. Brown Generating Station.

The annual ESS CSV files contain the BMS state-of-health column as `SOH`, in percent. No separate annual reference-test capacity table, workbook, or sheet was found in the held PPL data directory. The earlier read-only reproduction notes identify the annual reference-test capacity/SOH comparison as paper Figure 2 and Figure 3 caption evidence, not a machine-readable table in the released telemetry files.

## Operating history

Rows from November and December 2017 cover commissioning and acceptance testing; systematic data collection started in 2018 (paper Section III). The operators limited the maximum SOC after the April 2019 Surprise, Arizona fire (Section IV). From 2024 the usable SOC window was reduced from 10-90 % to 35-65 % and dispatch was capped at 200 kW (Section V, Section VII).

## Time stamps

No source states the time zone: not the paper, not the repository README and not the publisher's live-feed snapshot (`ESS_snapshot_20260825.json`). `load()` parses the released wall-clock values and tags them UTC; that tag has no source. The data, read through the loader (raw), point to a local clock but do not settle it. PV smoothing mode (`Mode` PSmoothing) in June and July runs from about 07:00 to 16:59 with its centre at 12.6 h, close to solar noon at the site in local standard time (12.65 h) and far from it in UTC (17.65 h); this rests on 366 minutes only. `ESS_2021.csv` ends at 2021-12-31 19:00, which is 2022-01-01 00:00 UTC if the clock is US Eastern Standard Time. Every file is a complete one-minute grid with no missing or repeated hour at the daylight-saving changes, so either the clock does not observe daylight saving or the files were resampled onto a regular grid. Long stretches change linearly from minute to minute (for example 100 % of changing `CellVoltAvg` minutes in 2017 and 85 % in 2023 lie on the straight line between their neighbours), which points to interpolation onto the grid. The paper says reference tests discharge after sunset (Section VII), but of the 30 full-power discharges from at least 85 % to at most 15 % SOC found in 2018-2025, one starts after sunset if the clock is local and none if it is UTC, so that test does not decide it.

## Sign convention

Not stated by the publisher. Measured through the loader (raw): in 2018-2020, when |PowerReal| > 50 kW and SOC changes, the sign of `PowerReal` is opposite to the next-minute change of `AvgSOC` in 94.7 % of minutes (correlation -0.62), so positive `PowerReal` is discharging. In 2022-2025 `DCCurrent` correlates with the SOC change at +0.69 and with `PowerReal` at -1.00, so positive `DCCurrent` is charging.

## Outages and zero placeholders

The files keep a row every minute through outages. While the system is offline, `SOH` and `CellVoltAvg` (and up to 2021 `CellVoltMax`, `CellVoltMin`, `ModuleTempMax`, `ModuleTempMin`) read exactly 0, mostly together with `AvgSOC` 0 and `Running` 0. Measured through the loader (raw), `SOH` is 0 in 13,114 to 313,533 rows a year (313,533 in 2019, 177,260 in 2021, 150,244 in 2024). The longest runs line up with the outages in paper Section IV: 2019-05-14 to 2019-07-02 and 2019-07-05 to 2019-09-04 (safety outage after the April 2019 Arizona incident; `Running` is 0 from 2019-04-22), 2019-12-12 to 2020-01-29 (the December firmware upgrade, which the paper puts at about 29 days), 2021-07-20 to 2021-09-07 (within the 100-day power-conversion outage), 2022-03-19 to 2022-04-19 (the 30-day converter outage), 2024-01-12 to 2024-03-11 (the 60-day January shutdown) and 2024-09-24 to 2024-11-08 (45 days; the paper places the 45-day tracker installation in August), plus 2017-11-04 to 2017-12-18 during commissioning. The publisher's live feed also reports 0 for SOH, SOC and cell voltages while the system is not running. A cell voltage or SOH of 0 cannot be a measurement of this battery, so `clean=True` masks 0 in `SOH`, `CellVoltAvg`, `CellVoltMax` and `CellVoltMin`, and 0 in `AvgSOC`, `ModuleTempMax` and `ModuleTempMin` in rows whose `CellVoltAvg` is 0. Zeros in `PowerReal`, `DCVoltage`, `DCCurrent` and the container temperatures are kept, since they can be real while the system is idle. `ESS_2025.csv` also has 36,381 blank `AvgSOC` cells. `AvgSOC` stays at one non-zero value for up to 18.9 days (37.5 % from 2018-10-05 to 2018-10-24).

## Cell-level share (not read by `load()`)

The repository's `Cell_Level_Data` file links a Box share of monthly zips, which the paper calls "sub-second cell level data" (Section III). We hold a snapshot of 110 zips (66.6 GB, December 2016 to February 2026). `cell_level_files()`, `cell_level_members(file)` and `cell_level_preview(file, member, rows)` list and read them. Each day folder holds BMS logs (`Bank1`, `Bank2`, `Bank1_Racks`, `Bank2_Racks`, `Section`, `PLC1`, `PLC2`, `RARD`; written `Bank1Racks`, `Rard` and so on in 2025) and event-log text files. The bank logs step at 1 s. The RARD log holds individual cell voltages: on 15 July 2018 and on 15 January 2025 each row is one rack, with 17 modules of 14 cell voltages (238 cell-voltage columns) and two temperatures per module, and the rows step through all 20 racks at 5 s per row, so each cell is logged every 100 s. In 2018 the RARD file has a two-row header (module labels, then field names), and `cell_level_preview` returns the second header row as its first data row; in 2025 it has one header row with names such as `[Module#1]Cell Voltage1`.
