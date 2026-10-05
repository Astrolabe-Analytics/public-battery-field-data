# Deng on-road EV charging-data schema

Source files: `#1.rar` through `#20.rar` in the package data directory. Each archive contains one CSV for one vehicle pack. The loader extracts each requested archive into a temporary system directory, reads the CSV, and removes the temporary copy.

## What the release is

The packs come from 20 BAIC EU500 vehicles "equipped with CATL NCM batteries", nominal capacity 145 Ah, "90 battery cells connected in series and 32 temperature sensors inside the pack" (data-record README, section "battery pack information update"). Only the maximum and minimum of the 32 temperature sensors are released. The vehicles "are used as commercial taxis in the same city" (paper p. 9); the city is not named. The cell nominal voltage is not stated in any source.

Rows exist only during charging sessions. "The data are collected though charging devices, which receive the battery charging data via control area network (CAN) communication during the charging process" and "the recoding frequency of the charging data is 8 s" (paper p. 3). Driving and rest are not recorded, so first-to-last spans are calendar spans, not observed time. The authors give the duration as "around 29 months" (paper abstract and README); the released timestamps span 27.7 months (table below).

Processing before release: the data set is released "with sensitive information removing" (paper p. 11, Data availability). Which fields were changed is not stated.

Time zone: not stated. Paper Table 1 (p. 2) gives the time format `yyyy-mm-dd hh:mm:ss` with no zone. `load()` returns naive timestamps as released. The hour-of-day pattern of session starts (fewest at 07:00 to 10:00 on the released clock, a rise at 23:00) fits local clock time in China better than UTC (source-audit data check, 2026-10-04); this is an inference, not a stated fact.

## Files and measured coverage

The measurement below was made directly from all 20 held RAR archives. The combined data contain 16,100,728 rows. The earliest timestamp is 2019-07-22 16:35:17 and the latest timestamp is 2021-11-16 01:05:42.

| pack | archive | rows | first timestamp | last timestamp | span days | median cadence |
|---|---|---:|---|---|---:|---:|
| #1 | #1.rar | 854,591 | 2019-07-26 20:02:35 | 2021-11-15 16:46:40 | 842 | 8 s |
| #2 | #2.rar | 841,810 | 2019-07-25 15:14:26 | 2021-11-15 14:12:56 | 843 | 8 s |
| #3 | #3.rar | 802,918 | 2019-07-26 19:08:05 | 2021-11-15 22:20:40 | 843 | 8 s |
| #4 | #4.rar | 844,537 | 2019-07-25 15:58:38 | 2021-11-15 17:57:51 | 844 | 8 s |
| #5 | #5.rar | 832,189 | 2019-07-26 00:22:51 | 2021-11-15 17:44:04 | 843 | 8 s |
| #6 | #6.rar | 815,202 | 2019-07-25 18:35:34 | 2021-11-15 15:59:52 | 843 | 8 s |
| #7 | #7.rar | 808,770 | 2019-07-26 09:00:02 | 2021-11-15 15:54:48 | 843 | 10 s |
| #8 | #8.rar | 798,496 | 2019-07-26 10:26:45 | 2021-11-15 21:01:06 | 843 | 8 s |
| #9 | #9.rar | 792,060 | 2019-07-23 21:27:55 | 2021-11-15 19:19:13 | 845 | 10 s |
| #10 | #10.rar | 728,849 | 2019-07-24 23:00:08 | 2021-11-15 14:07:37 | 844 | 8 s |
| #11 | #11.rar | 809,470 | 2019-07-26 06:21:45 | 2021-11-15 22:53:06 | 843 | 10 s |
| #12 | #12.rar | 825,533 | 2019-07-22 16:35:17 | 2021-11-16 01:05:42 | 847 | 8 s |
| #13 | #13.rar | 818,352 | 2019-07-26 11:17:42 | 2021-11-15 17:47:13 | 843 | 8 s |
| #14 | #14.rar | 793,132 | 2019-07-26 01:07:17 | 2021-11-15 18:58:44 | 843 | 8 s |
| #15 | #15.rar | 704,958 | 2019-07-25 12:11:45 | 2021-11-15 21:21:31 | 844 | 8 s |
| #16 | #16.rar | 819,567 | 2019-07-23 08:46:14 | 2021-11-15 21:24:27 | 846 | 8 s |
| #17 | #17.rar | 767,868 | 2019-07-25 21:53:04 | 2021-11-15 20:03:29 | 843 | 8 s |
| #18 | #18.rar | 856,192 | 2019-07-26 02:53:18 | 2021-11-15 18:01:41 | 843 | 10 s |
| #19 | #19.rar | 778,745 | 2019-07-24 13:10:55 | 2021-11-15 22:26:25 | 845 | 10 s |
| #20 | #20.rar | 807,489 | 2019-07-26 11:03:04 | 2021-11-15 10:20:28 | 842 | 8 s |

## Columns

The CSV files are read with the following column names, matching the held code's capacity-extraction convention.

| column | unit | dtype as loaded | role |
|---|---|---|---|
| number | row number | integer | Row counter: equals 0 to n-1 in file order in all 20 files (measured, raw, source-audit check 2026-10-04). The authors' capacity_extract.py stores column 0 of a session as `veh_name` but never uses it. |
| record_time | timestamp | datetime64 index in `load()`, naive | Time `yyyy-mm-dd hh:mm:ss` (paper Table 1, p. 2); released as `yyyymmddhhmmss` integers. Time zone not stated. Sessions are split at gaps over 10 s in the authors' code. |
| soc | % | float | BMS-estimated SOC, resolution 0.1 (paper Table 1). Not measured. The authors note that "the inevitable estimation error of SOC could cause a large error in battery capacity" (p. 2) and that Eq. (1) "depends on high-precision estimation of battery SOC" (p. 3). |
| pack_voltage | V | float | Pack voltage, resolution 0.1 V (paper Table 1). |
| charge_current | A | float | Pack current. Negative while charging: Eq. (1) uses "I is the battery current with negative value for charging process" (paper p. 3). Raw data: 15,897,589 rows below 0, 203,105 at 0 and 34 above 0 over all packs (source-audit check). Charge ampere-hours use the negative current integral. |
| max_cell_voltage | V | float | Maximum cell voltage, resolution 0.001 V (paper Table 1). |
| min_cell_voltage | V | float | Minimum cell voltage, resolution 0.001 V (paper Table 1). |
| max_temperature | C | integer | Maximum cell temperature of the 32 pack sensors, resolution 1 (paper Table 1, README). |
| min_temperature | C | integer | Minimum cell temperature, resolution 1 (paper Table 1). |
| available_energy | kWh (name-based) | float | Undocumented BMS field: not in paper Table 1, and the authors' code only names it. Inside every charging session it rises with `soc` (Pearson r = 1.000 per pack median), so it is remaining energy, not a full-energy or health estimate (source-audit check). |
| available_capacity | Ah (name-based) | float | Undocumented BMS field, as above. It rises with `soc` inside every charging session (r = 1.000; 51,853 sessions), so it is remaining charge, not a capacity or SOH estimate. `available_capacity / (soc/100)` gives a BMS full-capacity figure of about 136 Ah in each pack's first month and 131 to 135 Ah in its last (source-audit check). |
| pack | pack id | string | Added by `load()` to identify the source pack after concatenation. |

## BMS health and capacity fields

The release has no state-of-health column, and no source defines `available_capacity` or `available_energy`. In the raw data both rise with `soc` inside each charging session, so they hold remaining charge and remaining energy. Do not use `available_capacity` itself as a capacity or SOH estimate. The ratio `available_capacity / (soc/100)` behaves like a BMS full-capacity value (about 136 Ah at the start, 131 to 135 Ah at the end of each pack's record), but that reading is an inference from the data, not a documented field.

Charge capacity can be coulomb-counted as the authors do (paper Eq. (1), capacity_extract.py): split sessions at gaps over 10 s, keep sessions of at least 100 rows without SOC steps above 2 or below -0.1, and divide the charge (negative current integral) by the SOC change. Because SOC is a BMS estimate, single-session values scatter, and the authors use monthly mean or median values (paper Sec. 2.1). With a SOC swing of at least 20 points, the per-pack median of this capacity is 120.5 to 125.0 Ah, and the monthly median falls from about 133 to 135 Ah in the first month to 107 to 118 Ah in the last (raw data, source-audit check).
