# li2026 schema

Source file: `BatteryData.zip`, 600 CSVs named `BatteryData/<period>/battery_NN_cells_AAA-BBB_t_SSSSS-EEEEE.csv`. There are three recording periods (`real_world_02-03`, `real_world_03_04`, `real_world_05_06`). Each holds battery groups 1 to 30 of eight cells (cells 001 to 240), split into files of 4,000 samples.

`systems()` gives one row per period and battery group (90 rows) with its cell range and sample count (31,960, 32,561 and 9,780 samples per group in the three periods). `load(unit)` takes `"<period>/battery_NN"` and joins that group's files in sample order, indexed by `sample` (the index in the file names).

| column | unit | role |
|---|---|---|
| cell_AAA_V ... | V | Cell voltages, renamed from `vol_1..vol_8` to global cell numbers. |
| cell_AAA_T ... | C | Cell temperatures, renamed from `temp_1..temp_8`. |
| cur | A | Pack current, positive = discharge. |

Units are not stated in any source (paper p. 4, SI Methods S7 and the author code README name the signals without units); they are inferred from value ranges. Raw voltages run 3.073 to 3.604 V and temperatures 21 to 45 C over all 240 cells and three periods.

Sign: the paper states "power consumption (i.e., battery discharge) is defined as positive current" for the station record (p. 4, Figure 4 description). The data agree: the mean cell voltage falls during runs of positive current and rises during runs of negative current.

One series string: `cur` is identical at every sample in all 30 groups of a period, so the 240 cells of each period carry one current. SI Methods S7 describes the current as "identical for all cells connected in series", and the author code README calls `cur` the "Pack current". Per-cell voltage offsets and temperature ranks correlate at 0.98 and 0.997 between the first two periods (same cells) and at 0.6 and 0.27 between those and `real_world_05_06`, so whether the third period holds the same cells is not settled by the data. The paper refers to "operational energy-storage stations" (plural) and does not give a string or station count.

Cells: LFP (paper p. 3, "another type of LFP battery"), 200 Ah, 3.25 V nominal, 2.2 to 3.8 V limits, below 0.9 mOhm DC resistance (SI Table S1, "Energy storage station" column). The paper describes 200 cells monitored for 1,203 h (p. 3); the files hold 240 numbered cells, and all 240 voltage channels vary in every period, so the difference is not explained by dead channels.

Processing before release: the paper does not say whether the released station files are raw, cleaned or down-sampled. Its statement that raw measurements were "cleaned and labeled" and expanded by "trajectory slicing and data augmentation" belongs to the laboratory data (p. 3). The files are not the output of the authors' down-sampling code, which writes `orig_idx`, `sel_*`, `vdd` and `cdd` columns (author code README, Output Format). Voltage and current steps at the boundaries between the 4,000-sample files look like steps inside files, so the files are consecutive slices of one stream per period. 74,301 samples per group over the paper's 1,203 h would be about 58 s per sample, but the release has no time column and no source states the sampling interval.

Faults and labels: the paper reports ESC, SDF and ICF events in the station data (p. 3 to 4) and an inconsistency fault in "cell 2" of its Figure 4 example (p. 4), but the release carries no fault labels, event times or cell identities for them. No file has a column other than `vol_*`, `temp_*` and `cur`.

Time: no calendar timestamps; time zone not stated. Location: the paper does not locate the stations (p. 3); the authors' institutions are in China (p. 1). `clean=True` changes nothing.
