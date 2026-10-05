# bilfinger2026 schema

Source file: `data.zip` from mediaTUM, holding feather files: 26 files: 22 vehicle recordings and 4 laboratory files (one C/50 cell charge and three C/50 half-cell measurements). The vehicles are five CUPRA Born (file numbers 204, 213, 288, 349, 397), one VW ID.3 and one Tesla Model 3 SR+ (Bilfinger et al. 2026, doi:10.1016/j.etran.2026.100589, Sec. 2.1). The six VW Group vehicles share one pack: 108s2p NMC532 pouch cells, 58 kWh net; the Tesla pack is 106s1p LFP, 52.5 kWh net (paper Sec. 2.1 and Table 1). The VW ID.3 and the Tesla are the bilfinger2024 vehicles: `VW_ID3_FTM_JB_8A_CEE7_preRelax` is identical to bilfinger2024 `VW_ID3_JB_8A_C40_2024`, and `Tesla_JB_6A_CEE7_C57_2022_w_cv` is identical to bilfinger2024 `Tesla_JB_8A_CEE7_C57_2022` on all shared columns (measured through the loaders; the paper does not say the specimens are the same). The totals count them once.

`systems()` lists every file with its `kind` (vehicle, laboratory cell, laboratory half-cell; this release has no raw logs and no pickles), the `vehicle` it belongs to, format, archive member and size. `load(unit)` takes a file stem and returns that recording as released, with no index change.

## How the authors acquired and processed the vehicle files

- VW and Cupra: UDS queries through the OBD-II port; responses logged at 0.1 to 1 Hz; resolutions 0.01 A, 0.4 % SOC, 0.25 V and 1 C. Tesla: the whole CAN bus logged with Busmaster and decoded with a public .dbc file; pack current, SOC and voltage at 100 Hz, cell voltages and temperatures at 0.5 Hz; resolutions 0.01 A, 0.1 % SOC, 0.1 V and 0.1 C (paper Sec. 2.2).
- The paper says the data were synchronized onto one time vector with linear interpolation, and voltage and capacity were then filtered with a forward moving mean over 1 % of the points (paper Sec. 2.2). The released files do not fully match this (raw data, audit 2026-10-04). In every VW and Cupra file, `U`, `I`, `SOC` and the cell voltages all sit on the logged resolution grid (0.25 V, 0.01 A, 0.4 %, 1 mV) and repeat between updates. So they are logged values held on a shared time vector (steps of about 2 s, 0.2 s in `Cupra_288_JB_6A_CEE16_C17`, 10 s in three files), neither interpolated nor filtered. The Tesla files are on an exact 10 s grid with values off every resolution grid, so they were computed (interpolated or averaged), not sampled. The authors' code applies the 1 % moving mean when a file is read (`ReadFeather.read` in their repository), not in the files.

## Files and experiments

Most files are full AC charges at constant power from 0 % BMS SOC, in a workshop at 20 C, between the fixed evaluation bounds 370 to 450 V (VW) and 340 to 380 V (Tesla) (paper Sec. 2.3 and Table 1). The table below maps each vehicle file to the paper's experiments. Sources: the author notebooks, which name the file for each figure, and the charged energy between the bounds measured on raw data through this loader, compared with paper Tables 2 and 3. The paper calls the Cupras #1 to #5 without file numbers; the mapping comes from matching energy and charge.

| file | vehicle | experiment (paper section, table) | measured energy, kWh | paper, kWh |
|---|---|---|---|---|
| Cupra_288_JB_8A_CEE7_C45 | Cupra #1 | charging power 1.8 kW (Sec. 3.1, Table 2a); comparability (Table 3b) | 58.22 | 58.2 |
| Cupra_288_JB_6A_CEE16_C17 | Cupra #1 | charging power 4.2 kW; temperature, 20 C reference (Sec. 3.2, Table 2b) | 57.27 | 57.3 |
| Cupra_288_JB_10A_CEE16_C10 | Cupra #1 | charging power 6.9 kW; current direction, charge (Sec. 3.3, Table 2c) | 57.65 | 57.6 |
| Cupra_288_JB_32A_CEE32_C6 | Cupra #1 | charging power 11.1 kW | 57.14 | 57.1 |
| Cupra_288_JB_6A_CEE16_C17_outside | Cupra #1 | temperature, about 0 C outdoors in December (Sec. 3.2, Table 2b) | 56.96 | 57.0 |
| Cupra_288_C10_discharge | Cupra #1 | current direction, discharge through the thermal management at about 5 kW (Sec. 4.3, Table 2c) | 54.75 | 54.8 |
| Cupra_213_JB_8A_CEE7_C45 | Cupra #2 | repeatability 1 (Sec. 3.5, Table 3a); comparability | 58.43 | 58.4 |
| Cupra_213_JB_8A_CEE7_C45_repeatability | Cupra #2 | repeatability 2 | 58.40 | 58.4 |
| Cupra_213_JB_8A_CEE7_C45_repeatability_2 | Cupra #2 | repeatability 3 | 58.02 | 58.0 |
| Cupra_204_JB_8A_CEE7_C45 | Cupra #3 | comparability (Sec. 3.6, Table 3b) | 57.55 | 57.6 |
| Cupra_349_JB_8A_CEE7_C45 | Cupra #4 | comparability | 58.77 | 58.8 |
| Cupra_397_JB_8A_CEE7_C45 | Cupra #5 | comparability | 57.73 | 57.7 |
| Tesla_JB_6A_CEE7_C57_2022_w_cv | Tesla | charging power 1.8 kW (Table 2a) | 54.03 | 54.0 |
| Tesla_AC_5A_C17_w_cv | Tesla | charging power 4.2 kW; also the 20 C temperature reference (Table 2b; its footnote says 3.2 kW) | 53.29 | 53.3 |
| Tesla_AC_8A_C10_w_cv | Tesla | charging power 6.9 kW | 53.48 | 53.5 |
| Tesla_AC_16A_C5_w_cv | Tesla | charging power 11.1 kW | 53.86 | 53.9 |
| Tesla_AC_10A_C8_w_cv | Tesla | an extra charging-power test not in Tables 2 and 3 | 53.99 | none |
| Tesla_JB_6A_CEE16_C13_outside_w_cv | Tesla | temperature, about 0 C (Table 2b) | 52.60 | 52.6 |
| VW_ID3_FTM_JB_8A_CEE7_preRelax | VW ID.3 | resting SOC, reference with unknown relaxation (Sec. 3.4, Table 2d) | 55.91 | 55.9 |
| VW_ID3_FTM_8A_CEE7_RelaxHighSOC | VW ID.3 | charge after three weeks at 100 % SOC | 55.61 | 55.6 |
| VW_ID3_FTM_8A_CEE7_RelaxLowSOC | VW ID.3 | charge after three weeks at 10 % SOC | 56.31 | 56.3 |
| VW_ID3_FTM_8A_CEE7_Balancing | VW ID.3 | the rest phases themselves, 2024-04-30 to 2024-06-17: balancing after the full charge, rest at 100 % SOC, the drain on 2024-05-22, and the rest at 10 % SOC (Sec. 4.4, Fig. 6a) | n/a | n/a |

Measured energy is the integral of `U * I` between the voltage bounds, using the authors' selection (`extract_between_voltages`), on raw data; the discharge row uses the absolute value. Cupra files are dated 2022-11-11 to 2022-12-15 and VW ID.3 files 2024-04-22 to 2024-06-17; the Tesla files carry no dates. Paper mileages: Cupra #1 17 to 30 km, Cupras #3 and #5 about 300 km, VW ID.3 40,700 km, Tesla 23,200 km (38,450 km for the 0 C test) (paper Tables 2 and 3).

## Columns of the vehicle files

| column | unit | role |
|---|---|---|
| U | V | Pack voltage. |
| I | A | Pack current. Positive while charging: `I` is never negative in the 20 charging files and negative on every row with a value in `Cupra_288_C10_discharge`; `VW_ID3_FTM_8A_CEE7_Balancing` has both signs (raw data, audit 2026-10-04). The paper states no sign convention. |
| SOC | % | BMS-estimated SOC, not the dashboard value (paper Sec. 2.3); for that VW, 96 % BMS SOC equals 100 % dashboard SOC (paper Fig. 5 caption). Resolution 0.4 % VW, 0.1 % Tesla. Tesla files add `pack_soc_min`, `pack_soc_max` and, in two files, `pack_soc_ui`. |
| Q | Ah | Charge computed by the authors by integrating current (paper Sec. 2.4.1; author code: "the Q is already calculated from the current signal"), not a sensor value. It equals the trapezoid integral of the released `I` over `time_h` in 21 of 22 vehicle files (from 0, except `Tesla_AC_8A_C10_w_cv`, which starts at 0.14 Ah). In `Cupra_288_C10_discharge` `Q` is empty after the first row. |
| P, E | kW, kWh | Power and energy computed by the authors, in the four VW ID.3 files. |
| cell_voltage_N | V | One column per series position. VW and Cupra: 108 positions, numbered from 1, each a pair of cells in parallel (108s2p), so a column is the voltage of a parallel pair. Tesla: 106 single cells (106s1p), numbered from 0. |
| pack_temp_N, ambient_air_temp | C | Module temperatures and ambient air temperature (paper Sec. 2.2), 1 C resolution, in the VW ID.3 files and five of the Cupra 288 files. Tesla files have `pack_temp_min` and `pack_temp_max` only. `Cupra_288_JB_6A_CEE16_C17` adds `T` and `T_pack`, which the paper does not describe. |
| time_ms, time_s, time_min, time_h | ms, s, min, h | Elapsed time within the recording. |
| date | timestamp | Calendar time of each row, in VW ID.3 and Cupra files only. Time zone not stated by the authors; in the overlapping bilfinger2024 files it equals logged Unix time rendered as UTC. |

## Out-of-range values in VW_ID3_FTM_8A_CEE7_Balancing

This 784,507-row file holds short runs of one to four rows with fixed values that sit between normal readings (raw data, audit 2026-10-04): `U` = 1023.5 V in 157 rows, `I` = 166,272.14 A in 65 rows, a cell voltage of 5.094 V in 1,579 values (1,186 rows), `SOC` = 101.6 % in 276 rows and `pack_temp_0` = 87.0 or 87.5 C in 4,984 rows. All of them fall between 2024-05-02 and 2024-05-22, during the rest at 100 % SOC. The paper does not mention them. `clean=True` masks the `U` and `I` values only, because a 108s pack near 450 V cannot read 1023.5 V and no pack current reaches 166 kA; the other values are left as released. `Q` and `E` in this file integrate the 166,272.14 A rows and are not usable after the first one. The rows with `I` between -100 and -323 A on 2024-05-22 are the drain through the thermal management (paper Sec. 4.4) and are real. No other vehicle file in bilfinger2024 or bilfinger2026 has any of these values.

## Laboratory files

`VW_LG_78Ah_NMC_20deg_CC_C50` and the three `..._C50_Anode`, `..._Cathode_ch`, `..._Cathode_dch` half-cell files are the VW cell and electrode references behind paper Fig. 2 (author notebook 01-FIG_DVA_C_NMC532_halfcells). They have `U`, `I`, `Q`, `SOC`, `T1[C]` (20.0) and elapsed time.

Column order differs between files; select columns by name.
