# Schaeffer field-data schema

The released `field_data.zip` archive contains 28 CSV files named `field_data/data_sys_1.csv` through `field_data/data_sys_28.csv`. Each file is one portable 24 V LFP battery system of about 160 Ah with eight prismatic cells in series. Each file has a `Timestamp` column, which the loader parses without assigning a time zone; the time zone is not stated in any source.

Sources: the final article (Cell Reports Physical Science 5, 102258, 2024; held as `supplementary/Document S2 - Article plus supplemental information (mmc2).pdf`), its SI, the record README and the authors' BattGP code. The held `paper/Paper.pdf` is the arXiv v3 preprint, which the authors mark as outdated; it says 29 systems, 232 cells and 131 million rows. The final article says 28 systems, 224 cells and 133 million rows (Summary p. 1; Table 1, p. 4). The record README says 28 systems but 232 cells.

All systems "showed some form of unsatisfactory behavior and were returned to the manufacturer"; they are "a very small fraction of batteries sold", so the set "is biased and not representative" (record README; final article p. 3). The manufacturer is anonymous and each system's use case is unknown, typically "recreational vehicles, solar energy storage, and more" (final article p. 3). No country is stated; the article notes only higher temperatures in "the Northern hemisphere's summer months" (p. 4).

| Released columns | Unit | Meaning (record README sensor list; final article; BattGP code) |
|---|---|---|
| `U_Battery` | V | Pack voltage. |
| `I_Battery` | A | Load current; negative = discharge. The article selects discharge data as current between -80 and -5 A (Table 3, p. 14, "Discharge only"); BattGP `src/config.py` uses the same limits. |
| `SOC_Battery` | % | The BMS's estimated state of charge, not a measurement (final article p. 4, "estimated SOC"; preprint p. 7, "the SOC estimation of the BMS"). |
| `Temperature_1` through `Temperature_4` | C | Four sensors, each between two adjacent cells (final article p. 4, Figure 1). BattGP `src/batt_data/data_columns.py` maps them to cells 1-2, 3-4, 5-6 and 7-8 in order. |
| `U_Cell_1` through `U_Cell_8` | V | Eight series-cell voltages. |
| `I_CNV_Cell_1` through `I_CNV_Cell_8` | not stated | Active cell-balancing converter currents (final article Figure 3E, p. 6). |
| `U_CR`, `I_CR` | not stated | Named in no source; BattGP does not import them. Nonzero in 6,118,458 rows. |

Units come from the final article's Table 3 ("Current (A)", "Temperature (C)", "SOC (%)", p. 14) and cell voltages quoted in V (p. 4); the preprint's Figure 2 axes agree.

`load(system)` reads one CSV from the archive, parses and stably sorts `Timestamp`, and preserves the remaining release column names and values without unit conversion. `load(system, chunksize=...)` instead returns a chunk reader over that one CSV in source order, with `Timestamp` parsed in every chunk. `systems()` lists the 28 released system IDs and their archive members.

## Measured on the raw release (all 28 systems)

- Rows: 132,777,059 in total (the article's 133 million), from 266,067 (system 28) to 24,153,489 (system 8).
- Sampling: the article gives a median interval of 5 s (Table 1, p. 4) and says the systems are "mostly sampled with 5 s" (p. 18). Of all timestamp steps, 81.3 % are exactly 5 s and 13.0 % are 60 or 61 s; the median step is 5 s in 25 systems, 7 s in system 27 and 60 s in systems 24, 25 and 28. 844,596 steps repeat a timestamp, 5 go backwards (one each in systems 4, 8, 9, 10 and 21) and 92 exceed 1 h.
- Gaps and dates: some series have gaps "because the system was fully switched off, the user tampered with it and its data storage unit, or for other unknown reasons", and "the exact manufacturing and shipping dates are unavailable" (final article p. 3), so the first record is not the commissioning date. Logging can continue after use ends: system 8 runs from November 2016 to March 2022, with heavy use only from late 2017 to November 2021 (p. 4 and the data).
- Sign: in 10-minute windows with at least 60 rows and a mean current above 5 A in magnitude, the sign of the mean current equals the sign of the SOC_Battery change in 98.4 % of 181,605 windows, so positive current is charge.
- Current outliers: the article reports discharge currents beyond 1,000 A in systems 3, 4 and 16 (p. 4). In the release, values below -1,000 A occur in systems 3 (17 values, minimum -1,047.5), 4 (10, minimum -6,696.4) and 23 (9, minimum -1,008.1), not in system 16 (minimum -352.6). Values above +1,000 A occur in systems 3 (one, 21,854.1) and 4 (two, maximum 15,879.9). They are kept in both raw and cleaned output.
- Non-finite values: `I_Battery` holds one +-inf value (system 3). There are no NaN values.

## Cleaning

The record README and the article define no sentinel or invalid value. `load(system, clean=True)` masks, one value at a time and never a whole row:

- exact zero readings in `U_Cell_1` through `U_Cell_8` (not documented by the authors; treated as invalid by this loader). Counts on the raw release are in the table below.
- +-inf in any numeric column, since infinity cannot be a measurement. The authors' BattGP reader drops NaN and inf values (`src/batt_data/data_utils.py`, `read_battery_fielddata`). Counts are in `attrs["infinite_value_counts"]`.

Real but unusual readings, such as cell voltages above 3.6 V or below 2.0 V (final article p. 4) and the large currents above, are not masked.

| system | U_Cell_1 | U_Cell_2 | U_Cell_3 | U_Cell_4 | U_Cell_5 | U_Cell_6 | U_Cell_7 | U_Cell_8 | total |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 7 |
| 16 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 4 |
| all other systems | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| all systems | 0 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 11 |
