# cell_to_pack schema (candidate)

Source: He, Y., Deng, Z., Huang, H.-Z., Liu, Y., Busch, P. A., Tang, X., Hu, X. and Li, W., "Data for: Resolving inter-cell heterogeneity to mitigate degradation amplification in battery packs", Zenodo, doi:10.5281/zenodo.20132842 (CC BY 4.0). The manuscript is unpublished. Code: doi:10.5281/zenodo.21105057. The record: 34 cells and 22 packs, LFP and NMC, 13 operating protocols, field measurements from grid-storage packs. Column meanings are from the column names.

## Files

Twenty zips:
- `Pack_field#1.zip` to `#16`: `Pack_field#N.pkl`, `capacity_matrix_#N.csv`, `SOC_matrix_#N.csv` and `pack_capacity_#N.csv`.
- `ESSH1.zip`, `ESSL1.zip`, `ESSL2.zip` and `PBSL1.zip`: `<group>/cells/*.pkl` and `<group>/pack/*.pkl`.

## Pickles and their conversion

Maintainer's decision (2026-10-13): convert once in an isolated throwaway environment, keep the converted copies local and out of git and the export, and record the conversion with checksums. `scripts/checks/convert_pickles/run_cell_to_pack.sh` runs `convert.py` in the throwaway venv used for tongji_rest (network blocked in-process before unpickling). Each pickle is unpickled straight from its zip, hashing the bytes as they are read.

Every pickle here is a list with one entry per cycle, each a dict of `constant_metadata` (one row) and `timeseries_data` (one row per sample). `convert.py` writes one Parquet per key, `<member>.constant_metadata.parquet` and `<member>.timeseries_data.parquet`, with an `item` column for the list position. In `ESSL2/pack/Pack#2.pkl` the `Vpack` column holds text in some cycles and numbers in others, so it is written as text there, each value as its own characters. Manifest with each input's and output's SHA-256: `reports/candidates/cell_to_pack/pickle_conversion.csv`.

## Units

Maintainer's decision: hold everything, count only the 16 field packs as units. `systems()` lists field packs (`kind = "field pack"`), laboratory packs and laboratory cells (including `ESSH1/Pack_field#1#cell#N`, cells taken from field pack 1).

## Field packs

- `constant_metadata` (one row per cycle): cycle, rate_capacity (Ah), SOH. The rate capacity is 302 Ah in every pack.
- `timeseries_data`: time(s), current(A), charge_capacity(Ah), SOC, Vpack, V1 to V416 (416 cells in series) and further per-cell channels, 839 columns with `item`. About 691,000 rows per pack.
- `capacity_matrix_#N.csv` and `SOC_matrix_#N.csv`: EFC (equivalent full cycles) and Col0 to Col415, one per cell. `pack_capacity_#N.csv`: EFC and Pack_Capacity. EFC runs to between 574 and 617 per pack. No calendar dates are released.
- Rated energy is not stated. At an assumed 3.2 V LFP nominal, 302 Ah x 416 cells is about 402 kWh per pack (derived, `rated_kwh` in `systems()`).

## Laboratory cells and packs

Cells: `constant_metadata` with rate_capacity (Ah), cycle, initial_capacity (Ah), DR and SOH, and `timeseries_data` with time(s), voltage(V), current(A), temperature(degC), charge_capacity(Ah) and SOC. Packs: like the field packs, with fewer cells.

## Cleaning

None. `clean=True` masks nothing.
