# tsukuba schema

Source file: `294ecef46cba01f6392560efe6c78a28.zip`. It holds `1 Raw_data_per_second.zip` (118 CSVs of up to 12 days each, 2015-01-01 to 2018-04-24), `2 Cleaned_data_per_second.zip` (the publisher's cleaned version, 119 CSVs), a per-second summary, hourly solar irradiation, electricity prices, holidays and the authors' extraction code. The per-second CSVs are deflate64-compressed.

The release is one research-building microgrid with one lead-acid battery: 326 kWh rated capacity and a 90 kW control maximum (paper p. 3). `systems()` returns that one unit with its file counts and date range, and `files(version)` lists the per-second files.

## Files

The paper says both per-second sets hold 119 files (p. 4 and Table 3). The cleaned set has 119; the raw set has 118 because raw 2017-11-13 to 2017-11-24 is not in the deposit, so `version="raw"` returns no rows for those 12 days, which include the 18 Nov 2017 maintenance day. One raw member is misnamed `20150701-20160712SecCsv.csv`; its rows run from 2015-07-01 00:00:00 to 2015-07-12 23:59:59, and `files()` gives it that last day. Raw files hold 103,507,200 rows and cleaned files 104,544,000, one per second of the 1,210 days (paper p. 5-6); both counts are measured with the loader.

## Signals

Each per-second CSV has three header rows: Japanese signal names (cp932), signal codes and units. `load(start=None, end=None, version="raw")` reads the files covering the date range. Columns are renamed from codes to English names. The names are our translations of the Japanese headers, checked against the paper's Table 4 (p. 6); codes, Japanese names and units are kept in `attrs["signals"]`.

| code | column | unit | paper Table 4 |
|---|---|---|---|
| 10101 | battery_active_power | kW | Active power of the battery |
| 10105 | battery_dc_voltage | V | Direct voltage of the battery |
| 10106 | battery_dc_current | A | Direct current of the battery |
| 10201 | grid_point_voltage | V | Voltage of purchased electricity at the receiving end |
| 10203 | grid_point_active_power | kW | Active power of purchased electricity at the receiving end |
| 10307 | pv_active_power | kW | Total active power generation by all four solar arrays |
| 12144 | battery_active_power_setpoint | kW | Active battery power command value |
| 12152 | battery_soc | % | State of charge of the battery |
| 20106, 20109, 20112, 20115 | pv1 to pv4_active_power | kW | Active power generation by solar arrays 1 to 4 |

Code 20104 (solar irradiance, W/m2, Table 4) is not in the per-second files; the paper's Table 3 gives the per-second files 12 parameters, and irradiance is only in the hourly file, which the loader does not read. The pyranometer sits at the foot of an array, is partly obstructed and has never been cleaned or recalibrated (paper p. 3-4).

Sign convention: positive `battery_active_power` and `battery_dc_current` mean discharging. The paper does not state it; we determined it from the data (raw, 10 to 16 July 2017): both correlate with the per-minute change of `battery_soc` at -0.95, and their means are positive during the 13:00-16:00 weekday peak, when SOC falls, and negative at night, when SOC rises.

`battery_soc` is the energy management system's estimate, not a measurement. It is reset to 100 % when the charging voltage reaches the specified value, typically once a week at night, with the same voltage as the battery degrades, and it can exceed 100 % during this calibration; such values are kept even in the cleaned files (paper p. 3, 7). Raw and cleaned files reach 322.29 % (November 2016), and 2,337,042 values exceed 100 %. The paper also reports a 0 % reading on 19 Nov 2016 and a frozen segment from 24 Feb 2017 15:03:47 to 17 Mar 2017 15:40:21, both blanked in the cleaned files (p. 7).

Operating context (paper p. 3): regular operation between 30 and 95 % SOC, with 30 % held as emergency backup, at most 90 kW; charging at night and discharging in the 13:00-16:00 peak; the peak cut runs only from July to September.

Timestamps are indexed as released, with no zone assigned. The paper does not state a time zone; its operating times (night charging, 13:00-16:00 peak) read as Japan local time.

## Error values and cleaning

The paper (p. 6-7, Known issues) describes these errors in the raw files, all removed and left blank in the cleaned files, which keep every timestamp:

- error value -999,999 on the maintenance Saturdays 14 Nov 2015, 19 Nov 2016 and 18 Nov 2017 and the day before each, and on some other days. In the raw files the loader finds 1,243,210 such values in 105,026 rows, in five files: those covering 13-14 Nov 2015 and 18-19 Nov 2016, and three in January to March 2017. No +999,999 occurs.
- battery DC voltage of 0 on the maintenance days and the days before (21,997 raw values; 2,552 zeros remain in the cleaned files).
- battery DC current between -680 and -450 A, judged out of range (1,811,739 raw values; none in the cleaned files).
- grid-point voltage and power of 0 around 20:14 on 25 Sep 2017, and grid-point power of 0 or 2400 from 11:24:45 to 11:26:06 on 13 Nov 2015.
- the SOC values named above.

The cleaned files also set negative total PV power at night (code 10307) to 0; the paper counts 882,281 such values (p. 6). The raw files hold 960,266 negative `pv_active_power` values and the cleaned files 89,526. Values the paper calls suspect but keeps in the cleaned files: grid-point active power after 20:15:09 on 25 Sep 2017, grid-point values below 200 on 18 Nov 2016 and 17 Nov 2017, and SOC above 100 %.

`clean=True` blanks only the error value -999,999 (exact match, single values; rows are kept). For the publisher's other removals use `version="cleaned"`. All counts above are from the loader on the full span (raw unless stated).

## Malformed rows in the cleaned files

Two cleaned rows lost their seconds: "2015/11/14 20:13" (between 20:13:36 and 20:13:38) and "2017/3/13 0:00" (the first row of its file, before 00:00:01). The loader gives each the second implied by its neighbours. The cleaned file 20180401-20180412 ends every line with two empty fields, which the loader drops.

The full span is about 100 million rows, so pass a date range.
