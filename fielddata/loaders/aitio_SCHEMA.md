# aitio

Aitio, A. and Howey, D. A. (2021), "Predicting battery end of life from solar off-grid system field data using machine learning", Joule. Data record: ORA, https://ora.ox.ac.uk/objects/uuid:e41d3d4c-f74e-4d76-81fd-0caa77ec6cec. License: CC BY-NC 4.0 (data/LICENSE). Package 23, admitted for v1.1.

## Files

Sixteen files, kept as shipped (zips not extracted): `set_0.zip` to `set_10.zip`, `meta_data.csv`, `GITT_OCV.mpt` (laboratory OCV test on a Biologic SP-150), `zip_to_npy.py` (the authors' unzip-and-convert tool), `LICENSE` and `readme.md.txt`. The record lists sizes but no checksums; `fielddata/reference_checksums.csv` holds our SHA-256 of each file.

The readme says the telemetry is "split into 10 zip files, containing ~100 .npz ... each". The release has 11: `set_0` to `set_9` hold 100 files each and `set_10` holds the remaining 27, so 1,027 files, one per battery, matching the readme's 1,027 batteries. Members are not in ID order across zips (battery 2 is in `set_1.zip`); `systems()` lists where each one is.

## Columns of each battery (`load`)

Each `<id>.npz` holds `arr_0`, an N x 4 float64 array (readme): a UNIX timestamp, then measured current, voltage and temperature.

| column | unit | meaning |
|---|---|---|
| time_s | s | UNIX time as released; the index `time` is the same instant as a UTC timestamp (UNIX time is UTC by definition) |
| current_A | A | battery current; the readme states "negative current is charging", and the loader keeps that sign |
| voltage_V | V | battery voltage (12 V lead-acid; median about 12.75 V) |
| temperature_degC | degC | battery temperature |

The readme says "the recording frequency is non-uniform in time"; the median interval is 60 s.

## Rows below 1 V and `clean=True`

168 rows in 91 batteries read below 1 V (median 0.015 V, raw data). All are brief blips inside normal readings: 121 are single rows, 120 of them with voltage above 10 V on both sides (median 13.2 V before and 13.1 V after), and the other 47 rows form 22 pairs and one run of three, each lasting under a minute. A 12 V lead-acid battery cannot read below 1 V and recover within a minute, so these are not measurements. `clean=True` masks these voltage values (one value each, the row stays) and records the count in `attrs["masked_value_count"]`. No placeholder code is documented, and nothing else is masked: other low voltage, high temperature or large current can be real fault data.

## meta_data.csv (`metadata()`)

Released columns: ID, ACTIVATED, IN_REPAIR_SYSTEM, STILL_ALIVE, Lifetime (days). The readme describes them as UID, activation date, repair date, lifetime and a flag for whether the battery entered repair; the released flag is STILL_ALIVE (491 FALSE, all with a repair date). Measured on the release: Lifetime is the repair date minus ACTIVATED for all 491 failed batteries, and 2020-09-15 minus ACTIVATED for all 536 live ones. The telemetry runs past both: a median 88.6 days after the repair date for failed batteries (6 end before it), and about 21 days past 2020-09-15 for live ones, to about 2020-10-05. Lifetime is therefore not the span of the data.

## Lifetime, the repair cut and `truncate_at_repair`

Lifetime and the repair cut are the authors' definitions. The paper (accepted manuscript p. 22, step 3) defines end of life as the date a battery entered repair for loss of capacity, and p. 23, step 8 says the failed batteries' "timeseries were truncated to only include data up to the repair date". The release does not apply that cut: it keeps telemetry after the repair date for 485 of the 491 failed batteries, for a median 88.6 days (`python scripts/checks/aitio_lifetime.py`). `load(..., truncate_at_repair=True)` drops each failed battery's rows from its IN_REPAIR_SYSTEM date on (rows before 00:00 UTC of that date are kept, the same boundary as Lifetime) and so reproduces the paper's input. Live batteries are unchanged. The default is False, also with `clean=True`, so the released data is returned unless the cut is asked for; `attrs["rows_dropped_after_repair"]` gives the count.
