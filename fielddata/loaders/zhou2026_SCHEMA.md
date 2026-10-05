# zhou2026 schema

Source file: `Vehicle data.zip`, 60 parquet partitions (`Vehicle data/LFP_part_NNN.parquet` and `Vehicle data/part_NNN.parquet`). The release holds three vehicle identifiers, spread over 20 partitions each: `LFP01` (5,118,176 rows, 2019-05-05 to 2023-12-12), `vehicle45` (6,103,094 rows, 2019-05-09 to 2022-04-04) and `vehicle69` (5,015,309 rows, 2019-05-09 to 2022-04-04). The paper's fleet is 133 vehicles: 116 NMC passenger cars and 17 LFP buses (paper p. 2).

Vehicle types: `LFP01` (156 cells, LFP) matches the paper's bus pack (LFP, 1P156S, 210 Ah, 105 kWh nominal; SI Supplementary Table 1, p. 16). `vehicle45` and `vehicle69` (95 cells) match the NMC passenger-car pack (1P95S, 150 Ah, 52 kWh nominal); the authors' code calls the two 95-cell vehicles `NMC_passenger_01` and `NMC_passenger_02` (`code/config.py`). So the release holds two NMC passenger cars and one LFP bus. Cell voltage limits: 2.8 to 4.25 V for the cars and 2.5 to 3.65 V for the bus (SI Table 1).

`zhou2026_partitions.csv` (next to this file) records which vin is in which partition, with row counts and first and last timestamps. It is generated from the release by `build_index()` because that needs a pass over all 2.2 GB. `systems()` reads it.

`load(unit, columns=None, part=None)` returns one or more vins indexed by `Timestamp` (released as `YYYYMMDDhhmmss` integers, parsed, no zone). A whole vin with the per-cell strings needs well over 4 GB of memory, so pass `columns` or `part` (partition positions 0 to 19).

| column | unit | role |
|---|---|---|
| `vin` | | Vehicle identifier. |
| `VehicleStatus` | code | 1 is the driving state in the authors' code; values present: 1, 2, 3, 254. |
| `ChargingStatus` | code | 1 is charging in the authors' code; values present: 1, 3, 4. |
| `Speed`, `Mileage` | km/h, km (inferred) | Vehicle speed and odometer. |
| `TotalVoltage` | V | Pack voltage (cars about 330 to 400 V, bus about 500 to 535 V). |
| `TotalCurrent` | A | Pack current; negative = charging, positive = discharging (SI Figs. 23 and 24, pp. 39 to 40). |
| `SOC` | % | The BMS's SOC estimate, not a measurement (SI Note 1, p. 5). For the cars, 100 % is "the terminal voltage reaching the upper cutoff of 4.2 V under a C/10 current" (SI Note 1, p. 6). |
| `MaxVoltageCellID`, `MaxCellVoltage`, `MinVoltageCellID`, `MinCellVoltage` | mV | Highest and lowest cell voltage and its cell number. They equal the maximum and minimum of `CellVoltages` in every row checked. |
| `MaxTempProbeID`, `MaxTemp`, `MinTempProbeID`, `MinTemp` | C | Highest and lowest probe temperature and its probe number. |
| `TotalCells`, `TotalPacks` | count | 156 and 1 for LFP01; 95 and 1 for the cars. |
| `CellVoltages` | mV | String `<pack>:<v1>_<v2>_...`, one value per cell. |
| `CellTemperatures` | see below | String `<pack>:<t1>_<t2>_...`, one value per temperature probe, not per cell: 34 probes in each car, 26 or 28 entries in LFP01. The BMS measures "a few temperature points in each module" (SI Note 1, p. 5). |

The paper says the data items and formats follow the Chinese national remote-monitoring standard (paper p. 2, ref. 25); the paper and SI do not restate units or codes, and the standard's text is not held here. Units above are from value ranges unless a source is cited.

Temperature encoding, from the data (partition 0 of each vin): in the two cars, the largest `CellTemperatures` entry minus 40 equals `MaxTemp` and the smallest minus 40 equals `MinTemp` in every row, so the string carries probe temperatures offset by +40. In LFP01 the entries equal `MaxTemp` with no offset, and both carry the value 255: `MaxTemp` is 255 in 78.6 % of partition-0 rows and has a median of 255 over all LFP01 rows. No source defines 255; it is kept. `expand_cells()` does not rescale.

Processing before release: the paper calls its fleet data a "processed dataset" (p. 2) in which "anomalies, missing values, duplications and outliers" were handled "through deletion, interpolation and filtering" (Fig. 1 caption, p. 2), and SI Note 1 (p. 6) keeps only intact charging curves for the model. The released rows have not been through that step: LFP01 has 881 fully duplicated rows; vehicle45 and vehicle69 have rows with SOC <= 0 (11 and 107) and TotalVoltage <= 0 (123 and 33); vehicle45 has 10 NaN `MaxTemp`; LFP01 has zero cell voltages. The authors' `code/01_data_preprocessing.py` drops exactly these rows, so the release is the input to their preprocessing. Charging rows are 15.5 %, 29.0 % and 33.9 % of the three vins, so the release is not the charging-curve subset either.

Sampling and gaps: "a nominal frequency of 0.1 Hz" (paper p. 2). Steps of exactly 10 s are 77.5 % of LFP01's steps (20 s steps are another 21.8 %) and 99.8 % and 99.9 % of the cars'. There are no records while vehicles are idle (SI Note 2, p. 8), so gaps in `Timestamp` are expected. Time zone not stated; the vehicles operated in China (SI Note 1 and Supplementary Fig. 1, p. 17).

Cells can be replaced in service: in one car "six of the 95 cells" were replaced (SI Note 2, p. 7). A cell channel is a position in the pack, not a fixed cell.

`expand_cells(frame, column)` splits the per-cell strings into one numeric column per entry. `clean=True` changes nothing.
