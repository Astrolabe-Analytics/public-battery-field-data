# M5BAT Pb1 (m5bat-pbacid) codebook

Source: `codebook.csv`, packaged inside `Full_Dataset_M5BAT_Battery_Unit_Pb1.zip` (the sole archive
for this package). Header row: `table, column_name, original_register, description, unit, data_type,
availability, scale_applied, quality_notes`. 31 data rows: 8 for `BMS`, 23 for `BSC`. Read directly
from the archive; not extracted into the repo.

Both parquet families already carry the codebook's `column_name` values as their column names and a
UTC-aware `timestamp_utc` pandas index (confirmed via `pyarrow.parquet.read_schema` on
`Exide1_BMS_2025.parquet` and `Exide1_BSC_2025.parquet`), so no renaming or scaling is applied by the
loader; `scale_applied` in the codebook describes scaling the publisher already performed before
export, not a step the loader must repeat.

Sources for this note: the paper (Zurmühlen, Koltermann, Sauer, Energies 19 (2026) 4141, cited as "paper"),
the codebook PDF `Description_File.pdf` on the data record (cited as "Description_File.pdf"; it matches
`codebook.csv` except where noted), and the earlier M5BAT paper in Energies 15 (2022) 1342 (doi:10.3390/en15041342, cited as "the 2022 M5BAT paper").

## Processing before release

Per the paper (Sec. 3.2.1, p. 6, and Sec. 3.7, p. 8), the released files are the processed dataset, not the
raw manufacturer exports: "Raw exports were quality-filtered, UTC-unified, and deduplicated", "Gaps shorter
than 5 s were forward-filled; longer gaps were preserved as discontinuities", and BSC channels "are scaled to
physical units during preprocessing". No flag marks forward-filled rows, so a repeated value is not
necessarily a new measurement. The filtering criteria are not stated.

The released index shows the fill only from 2022 (data check, raw, `scripts/checks/check_m5bat_extra.py`):
in 2022-2025 both sources have no index steps of 2 or 3 s, one step of 4 s (2025) and one of 5 s (2022),
while in 2017-2021 the BMS files hold 150,156 to 709,979 steps of exactly 2 s per year and the BSC files
3,601 to 78,675. So in 2017-2021 gaps shorter than 5 s are still gaps. Repeated values are common
(data check, raw, `scripts/checks/check_m5bat_pbacid_repeats.py`): with |current| > 10 A, all four BMS
measurement channels equal the previous second in 66 % of 1 s steps in 2019 and 77 % in 2023, so the BMS
values change only every few seconds; for the BSC channels the share is 2.7 % (2019) and 8.2 % (2023). The
BMS values are therefore mostly carried over rather than new each second; the data cannot separate the
publisher's fill from the BMS's own update rate.

Time zone: the index `timestamp_utc` is UTC (Description_File.pdf header; paper Sec. 3.2.1 "UTC-unified").
The data start on 2017-05-15 17:11:51 UTC and end on 2025-06-17 06:30:05 UTC (data check), although the
paper describes the record as April 2017 to May 2025 (Sec. 4, Sec. 2.3).

Signs: power and current positive = discharging, negative = charging (Description_File.pdf for
`power_dc_W_bms`, `current_A_bms`, `power_ac_kW_bsc`, `current_A_bsc`; paper Sec. 3.2.1).

## Sentinels and `clean=True`

Description_File.pdf defines the BMS communication-error codes 2345 and 2356 for `power_dc_W_bms`,
`current_A_bms` and `voltage_bat_V_bms`, and 2345 only for `soc_pct_bms`; for power it says they "are treated
as NaN in this dataset". No other column has a sentinel. In the released files (data check, raw, all years)
none of these four columns contains 2345 or 2356 (they hold a few NaN instead), while the cumulative BMS
counters do pass through those values (2017: 13 and 14 rows in `energy_charge_Wh_bms`, 1,127 and 995 in
`energy_discharge_Wh_bms`). `clean=True` therefore masks the codes only in the four BMS columns, which
changes nothing in the released files, and additionally masks the uninitialised BSC energy counters (values at
or above 0xFFFF0000 in `energy_charge_kWh_bsc` and `energy_discharge_kWh_bsc`; see their rows). It never
drops rows.

Unit and chemistry: M5BAT Pb1 is the flooded lead-acid unit of the M5BAT hybrid storage system
(paper title: "Operational Degradation of Flooded Lead-Acid Storage Under Frequency Containment
Reserve", Zurmühlen, Koltermann, Sauer, *Energies* 19(17) 4141 (2026), doi:10.3390/en19174141).
Nominal system voltage ~600 V, 300 series cells (299 after a 2023 bypass), per `voltage_bat_V_bms`
quality notes.

Row counts measured from the archive's own parquet footers (`pyarrow.parquet.ParquetFile(...).metadata.num_rows`,
2026-09-10): BMS totals 249,423,269 rows across 2017-2025; BSC totals 251,662,700 rows across
2017-2025.

## BMS columns (8), from codebook rows with `table == "BMS"`

| column_name | original_register | unit | dtype | availability | scale_applied | quality_notes |
|---|---|---|---|---|---|---|
| power_dc_W_bms | Exide1_LT_i_P_DC | W | float32 | 2017-2025 | none | Signed: positive = discharging, negative = charging. Stored in physical units by BMS (no scaling factor applied). Sentinel values 2345/2356 are BMS communication-error placeholders treated as NaN in this dataset. |
| current_A_bms | Exide1_LT_i_I_DC | A | float32 | 2017-2025 | none | Signed: positive = discharging, negative = charging. Used for DCIR calculation. Sentinel 2345/2356 indicates BMS communication error. |
| voltage_bat_V_bms | Exide1_LT_w_U_DC | V | float32 | 2017-2025 | none | Nominal system voltage ~600 V (300 series cells, 299 after the 2023 bypass); typical operating range ~610-630 V. Used for DCIR calculation. Sentinel 2345/2356 indicates BMS communication error. |
| soc_pct_bms | Exide1_LT_w_SoC | % | float32 | 2017-2025 | none | A BMS estimate, not a measurement. Proprietary BMS algorithm (manufacturer-internal SoC model), not independently calibrated. Sentinel 2345 indicates BMS communication error. |
| energy_charge_Wh_bms | Exide1_LT_dw_Eges_lad | Wh | int64 | 2017-2025 | 32bit_reconstruct | Reconstructed from two 16-bit register words (`dw_Eges_lad_high << 16 \| dw_Eges_lad_low`). Counter resets to zero after BMS power cycle or overflow (~4.3 GWh). Use incremental differences for energy throughput. |
| energy_discharge_Wh_bms | Exide1_LT_dw_Eges_entlad | Wh | int64 | 2017-2025 | 32bit_reconstruct | Same construction and caveats as `energy_charge_Wh_bms`. Absolute value (unsigned); does not include charging. |
| flag_imbalance_voltage_bms | Exide1_LT_x_Warn_Spannung_unausgeglichen_Bat | (none) | int64 | 2017-2025 | none | Boolean: 1 = warning active. Triggered when voltage spread across battery strings exceeds BMS threshold; corresponds to the sulphation-related warning discussed in the paper. The sources describe it differently: paper Table 1 "Cell voltage imbalance/sulfation warning flag", Sec. 2.3 "inter-string voltage imbalance warning flag". Pb1 is a single 300S/1P string (Table A1) and the BMS monitors groups of three cells (Sec. 4.1), so the spread is presumably among cell groups within the string (inference). Source and data disagree: the paper (Sec. 2.3) says this flag "was active during 72% of all sampled seconds in January 2022", but in the released files it is 1 in at most 7 rows per million in 2017-2021 and 0 in every non-null row in 2022-2025 (data check, raw). `flag_alarm_voltage_imbalance_bms` is likewise 0 in every non-null row in 2022-2025. |
| flag_alarm_voltage_imbalance_bms | Exide1_LT_x_Alarm_Spannung_unausgeglichen_Bat | (none) | int64 | 2017-2025 | none | Boolean: 1 = alarm active. Higher severity than `flag_imbalance_voltage_bms`; triggers protective shutdown if sustained. |

## BSC columns (23), from codebook rows with `table == "BSC"`

| column_name | original_register | unit | dtype | availability | scale_applied | quality_notes |
|---|---|---|---|---|---|---|
| power_ac_kW_bsc | i_P_AC | kW | float64 | 2017-2025 | none | Signed: positive = discharging to grid, negative = charging from grid. Primary FCR control signal. Unit confirmed as kW (no scaling factor in BSC firmware; validated against nameplate rating +/-630 kW). |
| frequency_Hz_bsc | w_freq | Hz | float64 | 2017-2025 | auto (see notes) | Primary FCR activation signal, assembled from different sources across periods. 2017-2021: raw integers auto-scaled to Hz by BESSDataLoader (x0.01 if median ~5000; /1000 if median ~50000). 2022-2025: sourced from `Data_Messung.parquet` column `ui_netzfrequenz_1s_mHz` / 1000. Unavailable Jan-Sep 2022 (column absent that period); those rows are NaN. |
| temperature_degC_bsc | i_T_Batt | °C | float64 | 2017-2025 | x0.1 | Battery cabinet air temperature measured by the BMS temperature sensor and relayed via the BSC (not an independent BSC sensor). Ambient sensor `i_T_Ambient` was defective throughout (constant 0 °C) and is not published. |
| energy_charge_kWh_bsc | dw_E_AC_Wirk_Lad | kWh | float64 | 2017-2025 | 32bit_reconstruct (2017-2021 only) | 2017-2021: reconstructed from 16-bit high/low register pair by BESSDataLoader. 2022-2025: stored as combined float64. Counter may reset after BSC power cycle; use incremental differences for throughput. **Not usable before 2022**: the on-board counter was "uninitialised 0xFFFF before 2022" (Description_File.pdf, `energy_charge_recon_kWh_bsc` notes; paper Sec. 3.3.2), which contradicts the "2017-2021: reconstructed" line of this row. In the data (raw) every 2017-2021 value is 4,294,967,295 (0xFFFFFFFF, in the rows where the BSC recorded, 84.5 % to 91.3 % per year) or 0 (rows where all BSC channels are NaN); `clean=True` masks the former. Use `energy_charge_recon_kWh_bsc` for the full record. In 2022-2025 the counter rises from 7,382 to 9,497 while the reconstructed column rises by 211,267 kWh, a ratio of about 1:100, so the released counter appears to count in units of 100 kWh, not kWh (data check, inference; not stated in the sources). |
| energy_discharge_kWh_bsc | dw_E_AC_Wirk_Entlad | kWh | float64 | 2017-2025 | 32bit_reconstruct (2017-2021 only) | Same construction and caveats as `energy_charge_kWh_bsc`. **Not usable before 2022** (same sources): 2017-2021 values are 4,294,902,760 (high word 0xFFFF) or 0, with a third value in 2021; `clean=True` masks values at or above 0xFFFF0000. Use `energy_discharge_recon_kWh_bsc`. In 2022-2025 it rises from 5,927 to 7,529 while the reconstructed column rises by 160,415 kWh, again about 1:100 (data check). |
| energy_charge_recon_kWh_bsc | (derived from i_P_AC / power_ac_kW_bsc) | kWh | float64 | 2017-2025 (full record) | time-integral of power_ac_kW_bsc (charge = integral of negative power) | PROVENANCE: reconstructed at export time by rectangular time-integration of `power_ac_kW_bsc`, because the on-board counter `energy_charge_kWh_bsc` is populated only from 2022 onward (uninitialised 0xFFFF before 2022). Validated against that counter to <1% over the 2022-2025 overlap. Cumulative across exported years ascending, starts at 0 in the first exported year; gaps capped at 5 s contribute no energy. Use period-to-period differences for throughput/round-trip efficiency. |
| energy_discharge_recon_kWh_bsc | (derived from i_P_AC / power_ac_kW_bsc) | kWh | float64 | 2017-2025 (full record) | time-integral of power_ac_kW_bsc (discharge = integral of positive power) | Same reconstruction, provenance and caveats as `energy_charge_recon_kWh_bsc`. |
| flag_fcr_active_bsc | x_BSC_Opmode_PQ | (none) | int64 | 2017-2025 | none | Boolean: 1 = PQ-regulation mode active. Predominantly FCR (BSC adjusts AC power proportionally to grid-frequency deviation from 50 Hz per ENTSO-E FCR spec) but may include other set-point-driven PQ operation; not an exclusive FCR indicator. |
| flag_standby_bsc | x_BSC_Opmode_Silent | (none) | int64 | 2017-2025 | none | Boolean: 1 = standby (connected but not providing FCR). |
| flag_stop_bsc | x_BSC_Opmode_Stop | (none) | int64 | 2017-2025 | none | Boolean: 1 = system stopped (no grid connection). |
| flag_failure_bsc | x_BSC_Opmode_Failure | (none) | int64 | 2017-2025 (data); codebook.csv says 2022-2025 | none | Boolean: 1 = failure state. `codebook.csv` says "Not present in 2017-2021 BSC firmware schema; column absent those years", but Description_File.pdf gives 2017-2025 and the data agree: the column is present and populated in every year, with value 1 in 0.04 % to 7.0 % of non-null rows per year (2017 highest). |
| flag_const_bsc | x_BSC_Opmode_Const | (none) | int64 | 2017-2025 (data); codebook.csv says 2022-2025 | none | Boolean: 1 = constant-power mode, used for maintenance/equalization charging (capacity tests run under PQ control, not this mode). Present in every year (Description_File.pdf: 2017-2025), but 0 in every non-null row 2017-2025 (data check, raw), so it never marks equalization charging in this release. |
| flag_qod_bsc | x_BSC_Opmode_QoD | (none) | int64 | 2017-2025 (data); codebook.csv says 2022-2025 | none | Boolean: 1 = Quality-of-Delivery mode (reactive power / voltage support). Present in every year (Description_File.pdf: 2017-2025), 0 in every non-null row 2017-2025 (data check, raw). |
| flag_wait_bsc | x_BSC_Opmode_Wait | (none) | int64 | 2017-2025 (data); codebook.csv says 2022-2025 | none | Boolean: 1 = system initializing or waiting for grid synchronization. Present and populated in every year (Description_File.pdf: 2017-2025), value 1 in 0.03 % to 1.0 % of non-null rows per year. |
| power_ac_setpoint_kW_bsc | i_P_Set_AC | kW | float64 | 2017-2025 | none | In FCR mode, the frequency-derived power command computed by the supervisory controller (FSC); otherwise the manually dispatched setpoint. |
| power_reactive_kvar_bsc | i_Q_AC | kvar | float64 | 2017-2025 | none | Signed convention follows IEEE standard (positive = inductive). Not analyzed in the paper; included for future power-quality studies. |
| power_reactive_setpoint_kvar_bsc | i_Q_Set_AC | kvar | float64 | 2017-2025 | none | Companion to `power_ac_setpoint_kW_bsc`. |
| power_apparent_kVA_bsc | i_S_AC | kVA | float64 | 2017-2025 | none | 2017-2021 values restored from the completed inverter-side source export (`Data_2017_2021_InvLT`); an earlier intermediate export had omitted this register for that period. Relationship: S² = P² + Q². |
| current_ac_A_bsc | i_I_AC_RMS | A | float64 | 2017-2025 | x0.1 | 2017-2021 values restored from the completed inverter-side source export (`Data_2017_2021_InvLT`); an earlier intermediate export had omitted this register for that period. |
| voltage_bat_V_bsc | w_U_DC_Batt | V | float64 | 2017-2025 | x0.1 | BSC measurement point (inverter DC terminals). Differs from `voltage_bat_V_bms` (battery pole terminals) by cable resistance. Included for cross-validation; BMS value is authoritative. The paper describes it differently: Table 1 "DC voltage at battery terminal", and Sec. 3.3.1 uses it as the battery terminal voltage for DCIR. |
| voltage_inv_V_bsc | w_U_DC_Inv | V | float64 | 2017-2025 | x0.1 | The paper says this signal "was unavailable after 2021" (Sec. 3.3.5; also Sec. 4.3 and 5); the codebook says it was restored later. The data agree with the codebook: 2022-2025 rows are all non-null, 0 to 762 V, with 0 in 1.1 % to 20.6 % of rows per year (data check, raw). Available across the full record. 2022-2025 values restored from the corrected source export (`Data_2022_2025_neu`); an earlier intermediate export had omitted this register for 2022+. Used for cable-resistance estimation: R_cable = (voltage_bat_V_bsc - voltage_inv_V_bsc) / current_A_bsc. |
| current_A_bsc | i_I_DC_Batt | A | float64 | 2017-2025 | x0.1 | BSC measurement point (inverter DC terminals). Signed: positive = discharging, negative = charging. Included for cross-validation with `current_A_bms`. |
| flag_cmd_fullcharge_bsc | x_cmd_FullCharge | (none) | int64 | 2017-2025 | none | Boolean: 1 = full-charge command active, issued periodically to counteract sulphation buildup. Available across the full record; 2022-2025 values restored from the corrected source export (`Data_2022_2025_neu`) after an earlier intermediate export omitted this register for 2022+, which had made the equalization fraction read ~0 for those years (a data artifact, not a real cessation of equalization charging). |

## Periods and events

- 2017 and parts of 2018 are commissioning. The paper (Sec. 4.1, p. 10) classifies 56.6 % of 2017 as
  stop/failure, while "the BMS and BSC channels were still being calibrated (sensor offset and gain settings,
  energy-counter initialization)"; the 2022 M5BAT paper (Sec. 3.1, p. 7) states that "the lead-acid batteries
  could not be fully commissioned until the end of 2018". Treat 2017 values with caution.
- 2017-2021 FCR-primary operation; from 2022 low-utilization reserve operation (paper Sec. 3.1, 4.1).
- 2023-08-10: a defective cell was bypassed (string 300S to 299S); before that, the faulty cell triggered
  "recurring protection shutdowns" (paper Sec. 2.2 and 4.1).
- Periodic reference capacity tests are in the record but not flagged; the last one, on 2025-04-14, indicated
  about 21 % residual capacity (paper Sec. 5.12 item 2, Table A1). Description_File.pdf says capacity tests
  run under PQ control, so `flag_const_bsc` does not mark them.
- The unit was decommissioned in mid-2025 (paper Table A1, "planned technology change").

## Recorded but not released

- 53 of the 55 BMS warning and alarm flags (paper Sec. 1 and 2.3 count 55; two flags are released). Whether
  the two released flags are among the 55 is not stated.
- The cell-voltage data of the 100 three-cell groups at about one-minute resolution, 2017-2022 (paper
  Sec. 5.12 item 7 and Sec. 3.3.1).
- The BMS field `eta_rt_BMS` named in paper Sec. 3.3.3, and the defective BSC ambient sensor `i_T_Ambient`
  (Description_File.pdf).

## Archive layout

Single archive `Full_Dataset_M5BAT_Battery_Unit_Pb1.zip`, one directory level, 19 members:

- `Exide1_BMS_<year>.parquet` for year in 2017-2025 (9 files)
- `Exide1_BSC_<year>.parquet` for year in 2017-2025 (9 files)
- `codebook.csv`

Both families already carry a `timestamp_utc` UTC-aware pandas index and codebook `column_name`
values as column names (verified with `pyarrow.parquet.read_schema` on the 2025 file of each
family, 2026-09-10).
