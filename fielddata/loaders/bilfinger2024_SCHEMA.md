# bilfinger2024 schema

Source file: `data.zip` from mediaTUM, holding pandas pickles and feather files: 17 files: 5 vehicle recordings, 3 vehicle raw logs, 6 laboratory cell and 3 half-cell reference measurements. The vehicles are a 2021 VW ID.3 Pro (108s2p, 216 NMC pouch cells) and a 2020 Tesla Model 3 Standard Range Plus (106s1p, 106 LFP prismatic cells) (Bilfinger et al. 2024, doi:10.1016/j.etran.2024.100356, Sec. 3.1 and Appendix A Table 1). Each vehicle recording is one full low-power AC charge from 0 % BMS SOC (paper Sec. 3.2): three VW charges (files dated 2021, 2023, 2024) and two Tesla charges (2021, 2022 by file name). The release holds discrete charging tests, not continuous telemetry. Both vehicles reappear in bilfinger2026: `VW_ID3_JB_8A_C40_2024` is identical to bilfinger2026 `VW_ID3_FTM_JB_8A_CEE7_preRelax`, and `Tesla_JB_8A_CEE7_C57_2022` is identical to bilfinger2026 `Tesla_JB_6A_CEE7_C57_2022_w_cv` on all shared columns (measured through the loaders); the totals count both vehicles once.

`systems()` lists every file with its `kind` (vehicle, vehicle raw log, laboratory cell, laboratory half-cell), the `vehicle` it belongs to, format, archive member and size. `load(unit)` takes a file stem and returns that recording as released, with no index change. `clean=True` changes nothing: no out-of-range or code values were found in this release.

## How the authors acquired and processed the vehicle files

- VW: unified diagnostic services (UDS) requests through the OBD-II port every 1000 ms; responses arrived about every 10 s (about 0.1 Hz). Estimated resolution 0.25 V (pack voltage) and 0.01 A (pack current). Tesla: the whole CAN bus was logged and decoded with a public .dbc file. "After completion of the measurement, the signals are synchronized onto a single time vector by interpolation" (paper Sec. 3.3). The paper fixes the vehicle sample rate at 10 s (Sec. 4.2).
- What the released rows show (raw data, audit 2026-10-04): `VW_ID3_JB_8A_C40_2021` is on an exact 2 s grid with values off the resolution grid, so it is interpolated, and it equals its raw log `VW_FTM_JB_8A_2021` on every matched row (that raw log is itself already on the 2 s grid). `VW_ID3_JB_8A_C40_2023` (steps about 5 s) and `VW_ID3_JB_8A_C40_2024` (steps mostly 2.3 to 4.5 s) hold logged values: every `U`, `I`, `SOC` and cell voltage sits on the logged grid (0.25 V, 0.01 A, 0.4 %, 1 mV) and is repeated between updates. The Tesla files are on an exact 10 s grid with values off every resolution grid, so they were computed (interpolated or averaged), not sampled.
- The authors' 1 % moving-mean filter (paper Sec. 4.2) is applied in their analysis code when a file is read, not in the released files.
- The three VW charges ran under different BMS software: ID.Software 2.0, 2.4 and 3.2 (paper Appendix B Table 2). In the 2023 charge the BMS capped the upper voltage, which lowers the charged capacity; the cap was gone after the 3.2 update (paper Sec. 4.4 and 4.5). Raw maxima of `U`: 452.0 V (2021), 446.75 V (2023), 454.5 V (2024).
- Paper Table 2 dates the measurements 2021-02-08, 2023-06-16 and 2024-05-22. The `date` columns run 2021-02-05 to 2021-02-07, 2023-06-16 to 2023-06-18 and 2024-04-22 to 2024-04-24. The 2024 file is the paper's ID.Software 3.2 charge (charged energy over the whole file 59.44 kWh, paper Sec. 4.5: 59.40 kWh), so the file dates and the paper table disagree for 2021 and 2024.

## Columns of the vehicle files

| column | unit | role |
|---|---|---|
| U | V | Pack voltage. |
| I | A | Pack current. Positive while charging: `I` is positive on every row of all five vehicle files, which are all charges (raw data, audit 2026-10-04). The paper states no sign convention. |
| SOC | % | BMS-estimated SOC, not the dashboard value: VW dashboard 0 % is about 4 % BMS SOC, Tesla offset 0.2 % (paper Sec. 3.2). Tesla files add `pack_soc_min`, `pack_soc_max` and `pack_soc_ui` (the dashboard SOC by its name; not described in the paper). |
| Q | Ah | Charge computed by the authors by integrating current (paper Eq. 3), not a sensor value. It equals the trapezoid integral of the released `I` over `time_h`, starting at 0 with no offset, in every vehicle file. |
| P, E | kW, kWh | Power and energy computed by the authors, in `VW_ID3_JB_8A_C40_2024` only. |
| cell_voltage_N | V | One column per series position. VW ID.3: 108 positions, numbered from 1, each a pair of cells in parallel (108s2p, 216 cells), so a column is the voltage of a parallel pair. Tesla: 106 single cells (106s1p), numbered from 0. |
| pack_temp_N, ambient_air_temp | C | Temperature channels in `VW_ID3_JB_8A_C40_2024` and the 2023 and 2024 raw logs only. The 2024 paper does not describe them. |
| time, time_ms, time_s, time_min, time_h | s, ms, s, min, h | `time_*` is elapsed time within the test. `time` is seconds from the start of the raw log in the 2021 VW file and Unix time in seconds in the 2023 VW file. |
| date | timestamp | Calendar time of each row, VW files only; Tesla files carry elapsed time only. Time zone not stated by the authors. In the 2023 file `date` equals the Unix `time` column rendered as UTC exactly, and in 2024 it matches the raw log's Unix time rendered as UTC. |

Vehicle raw logs (`kind` vehicle raw log, VW only) use `hv_battery_voltage`, `hv_battery_current`, `hv_soc` and, in 2023 and 2024, temperatures and other gateway signals with a Unix `time` column (2021: `TIMESTAMP`, seconds from the start). The 2023 and 2024 raw logs run longer than their vehicle files (2024: to 08:07 UTC on 2024-04-24, against 04:07 in the vehicle file).

## Laboratory files

Cells were taken from used modules of unknown history (paper Sec. 3.4) and charged in a thermal chamber at constant temperature on a BaSyTec cycler, CC or CP, matching the vehicle C-rates: VW cell C/45 and C/6 (CC and CP), Tesla cell C/57 (paper Sec. 3.4, 4.1 and Fig. 6). The file names say 20 degC and the `T1[C]` column reads 20.0; the paper gives no chamber temperature. Rows were recorded every 1 s or every 4 mV (paper Sec. 3.4). The release also holds a C/50 CC cell file and C/50 half-cell files (anode, cathode charge, cathode discharge) that the paper text does not describe in detail.

Column order differs between files; select columns by name. The pickles are the publisher's pandas pickles. Unpickling runs code, so load only an archive whose checksum `fielddata.verify` has confirmed.
