# tongji_rest schema (candidate)

Source: Tao, Zhu, Li, Jiang, Chang, Dai and Wei, "Cross-domain feature-based battery state-of-health estimation from rest period for real-world electric vehicles", eTransportation 26, 100471 (2025), doi:10.1016/j.etran.2025.100471. Data: Zenodo, doi:10.5281/zenodo.16868546 (CC BY 4.0). The paper could not be read here (ScienceDirect blocks automated access), so meanings below come from the column names and the data, and say so.

## Files

`data.zip` (129,606,252 bytes, MD5 matches the record): 5,210 files under `data/`.
- `data/raw_test/<charge|rest>_segment_<vehicle>/`: 5,056 pickled pandas files, one per charge or rest segment, for four field vehicles.
- `data/data_train/` and `data/data_test/`: 154 feature workbooks (`<name>_<fast|slow>_feature.xlsx`), one row per segment with derived features (for example seg_num, t_start, soc_start, soc_end).

## Pickles and their conversion

Maintainer's decision (2026-10-13): convert once in an isolated throwaway environment, keep the converted copies local and out of git and the export, and record the conversion with checksums. `scripts/checks/convert_pickles/run_tongji.sh` creates a separate venv (not the project's `.venv`; pandas 3.0.6, pyarrow), and `convert.py` blocks network connections in its own process before unpickling. It writes one Parquet per pickle into `converted/` beside the release's `data/` folder. All 5,056 converted without error: 3,632 were DataFrames and 1,424 (all of NMC01_Car02) were dicts of Series, DataFrames and a scalar mileage on one index, merged into one table with no value changed (the scalar repeated on every row). Manifest with each input's and output's SHA-256: `reports/candidates/tongji_rest/pickle_conversion.csv`.

## Units

Field vehicles with raw segments are the units (`fielddata.counting.CANDIDATE_RULES`): 4.

| vehicle | charge segments | rest segments | first | last | cell-voltage columns |
|---|---:|---:|---|---|---:|
| LFP01 | 805 | 797 | 2021-07-12 | 2024-05-30 | 123 |
| NMC01_Car01 | 553 | 533 | 2021-09-18 | 2023-04-01 | 107 |
| NMC01_Car02 | 712 | 712 | 2021-09-18 | 2023-12-20 | 108 |
| NMC02 | 504 | 440 | 2020-09-29 | 2023-12-27 | 94 |

`systems()` also lists 83 vehicles that appear only in feature workbooks (`kind = "feature only"`, for example LFP01_01 to LFP01_21) and 28 laboratory cells (`Lab...`, `kind = "laboratory cell"`). These are not units.

## Columns of the raw segments (as converted)

`load()` adds `segment` (file name) and `index` (the segment's kept pandas index). Then reqDate (time, about every 10 s), totalVoltage (V), totalCurrent (A, negative while charging, inferred), soc (percent), temp_mean (mean probe temperature, degC, inferred), cellVoltage_1 and up, or cell_voltage_1 and up for NMC01_Car02 (V), and an odometer: accumulatedMileage (km), or `mileage` (one value per segment) for NMC01_Car02. NMC01_Car02 also has probe_temp_1 to probe_temp_54.

## Cleaning

None known. `clean=True` masks nothing.
