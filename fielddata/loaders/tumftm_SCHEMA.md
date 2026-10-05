# tumftm schema

Source files: `electric-vehicle-uds-dataset/data/uds_data/<vehicle>.parquet` for CUP1 to CUP5 (CUPRA Born) and ID1, ID2 (VW ID.3), with 986,864 to 40,401,700 rows each. `data/value_overview.csv` defines the signals. The per-session histogram JSONs in `data/json/` are not read.

`systems()` lists the seven vehicles with row counts. `signals()` returns `value_overview.csv`: 29 signals with `value_id`, German and English names, `variable_name`, unit, range (`min_val`, `max_val`) and sampling interval.

`load(unit, value_id=None)` returns the released long format (`vehicle_id`, `time`, `value_id`, `value`) for one or more vehicles, optionally for chosen signals, with `variable_name` and `unit` joined on. Each signal has its own polling interval, from 0.1 to 10 s (paper Section 2.3 and Table 3), so rows of different signals are not aligned in time.

## What the parquets hold

The authors' export query (`preprocessing/03_export/sql/can_export.sql`) selects the raw UDS rows (`sensor.can`) for the 29 value_ids of `value_overview.csv`; the README calls `uds_data` "Raw UDS data". Only 15 of the 29 value_ids have rows in any vehicle (raw data, all seven parquets read through `load()`): 4 `vehicle_speed`, 15 `ambient_air_temp`, 56 `hv_aux_power`, 900 `hv_soc`, 961, 1265 and 1269 (motor and inverter temperatures), 1200 `hv_battery_voltage`, 1208 `hv_temp_min`, 1209 `hv_temp_max`, 1272 and 1273 (pack inlet and outlet temperatures), and, for ID1 only, 43 `interior_temp`, 1205 `ptc1_current` and 1207 `ptc_voltage`. Value_ids 1206 and 1288 to 1303 have no rows. Ids 1288 to 1303 (cell C-rate, temperature spread, DOD, durations, `cell_voltage_max`, `cell_voltage_min`, cell voltage spread, distance, PTC power, C-rate peaks) are quantities that the authors' histogram code computes per recording (`preprocessing/01_histogram_creation/classes/track.py` and `charging.py`, for example the maximum and minimum over the interpolated `cell_voltage_*` channels); they appear only in the JSON histograms. The release therefore has no pack current, no C-rate and no cell-voltage channel.

Sign convention: the release has no current or C-rate rows. For the C-rates in its histograms the paper uses negative for discharging and positive for charging (paper Section 4.2, "discharging occurs at -0.2 C and charging at 0.1 C"); the cell C-rate is pack current divided by 2 x 78 Ah (paper Eq. 1).

`hv_soc` (900) is the SOC reported by the battery management system, which keeps margins against the SOC shown to the driver (paper Section 4.2). The paper says no SOC below 4 % or above 96 % was recorded except in ID1. In the raw parquets every vehicle has values above 96 % (maximum 96.4 to 98.4 % for CUP1 to CUP5 and ID2, 101.6 % for ID1), and ID1 reaches 0 %.

## Coverage

Rows exist only while a vehicle was driven or charged. No data were recorded while parked, which is 96.5 to 99.5 % of the measurement periods, and some recordings are missing because of unplugged loggers or logger faults (paper Section 2.3 and Section 4.1). First and last timestamps per vehicle (raw, 2087 rows left out) match the UDS test periods of paper Table 2: ID1 2021-02-01 to 2023-06-13, ID2 2021-07-26 to 2023-10-10, CUP1 to CUP5 2022-11-10 to 2023-05-04 (the paper gives 11/22 to 03/23; the files run into April and early May 2023 with the full UDS signal set). The CUPRA API data (SOC and odometer only, 07/23 to 04/24, paper Section 2.3) are not in the parquets. ID2 had 35,000 km when logging began; the other vehicles were new (paper Section 2.2). The UDS campaign covered 40,665 km; the "more than 72,000 km" in the README and paper includes 31,627 km taken from the CUPRA API (paper Section 2.3).

Timestamps are naive. No source states the time zone; the authors' database column is `timestamp` without zone (`preprocessing/02_database_schemas/sensor.can.sql`).

## Values outside the stated ranges

The raw parquets hold values outside the `min_val`/`max_val` ranges of `value_overview.csv`, 20,863 rows in all (raw data, checked for every vehicle): pack inlet and outlet temperature (1272, 1273) up to 1023.98 C, mostly exactly 1023 or 1022; `hv_aux_power` (56) of exactly 25,400 W; `hv_battery_voltage` (1200) of several thousand volts in 0 to 25 rows per vehicle; `vehicle_speed` (4) above 254 km/h, including 803 rows of exactly 255 in ID1. The authors do not describe these values, and the loader does not mask them.

## Clean option

CUP1 carries 812 rows dated 2087-03-07 across ten signals (467 of them `hv_battery_voltage`). We observed these in the data; the authors do not describe them. `clean=True` sets every timestamp in or after 2030 to NaT and keeps the rows. `time_bounds(unit, clean=True)` leaves those timestamps out.
