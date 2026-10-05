# ku_leuven_bev schema

Source file: `doi-10.48804-8kpdtw.zip`, which holds `BEV energy dynamic data_V2.zip` and the record's `readme_V2.txt`. Inside the inner zip, one CSV per session sits in four folders: slow charging (109 files), fast charging (25), driving (1,396) and parking (780), for two vehicles, BEV1 and BEV2. The paper gives the same counts ("around 2310 files", Data Records, p. 9). `Additional files/` (a raw MF4 example, its decoded CSV, the CAN DBC and two-year energy totals) is not read by the loader.

## Vehicles

Both are privately owned Tesla Model Y cars, "primarily used for commuting by a single driver", driven in Belgium (paper pp. 2, 6 and 9).

| unit | model | battery | stated energy | in service since | paper collection period (Table 3, p. 4) |
|---|---|---|---|---|---|
| BEV1 | Tesla Model Y SR | LFP | 60.5 kWh | Feb 2023 | 2024-07-23 to 2025-02-18 |
| BEV2 | Tesla Model Y LR | NCA | 78.8 kWh | Oct 2022 | 2024-05-08 to 2025-04-30 |

Paper Table 3 (p. 4) and p. 9: "BEV1 is LFP battery, while BEV2 employs a NCA battery." The energies are the paper's "initial battery energy capacities" (p. 3).

## How the files were made

The authors logged the vehicle CAN bus with a CSS Electronics CAN edge logger to MF4 files (paper p. 2). CAN messages arrive "around 10 or 20 ms intervals depending on the type of message" (p. 10). They decoded the logs with the DBC file, classified the operation modes, and in a cleaning step applied "filtering and combining tasks ... to ensure consistency at a fixed time resolution (1s resolution)" (p. 3). The released code averages each decoded signal into 1 s bins (`resample('1S').mean()`) and outer-joins the signals on the 1 s grid (`data_processing_V1.py`, section 1). The CSVs are "in their final, processed form with a time resolution of one second" (Usage Notes, p. 13). Values are therefore 1 s means, not single CAN readings, and a signal is empty in seconds where none of its messages arrived. "The vehicle entered sleep mode during some sessions, which collected few data points" (p. 3).

The session folders are the authors' classification (p. 3; `data_processing_V1.py` sections 2 to 5). Slow-charging sessions run from a rise to a fall of `ChargeLinePower264` through 0.5 kW outside driving, and these files keep the authors' helper column `segment_id`. Fast-charging files hold the rows with `FC_dcCurrent` > 0. Driving sessions are split at gaps over 60 s. "Parking is defined as any time during which no charging or driving data was collected" (p. 7).

## Coverage

`sessions()` lists every session file with vehicle, type and date. `systems()` gives per vehicle the session counts by type and the first and last session date (BEV1 2024-07-23 to 2025-05-27, BEV2 2024-05-08 to 2025-04-30). Three parking-session file names write the date as `YYYY-MM_DD`; the loader reads them as dates.

BEV1 runs past the paper's stated end date (2025-02-18): 36 BEV1 files (16 driving, 19 parking, 1 slow charging) are dated 2025-05-23 to 2025-05-27, and their `Timestamp` values fall on those dates, so they are not mislabeled (raw data, source-audit check 2026-10-04). BEV1 has no files between those two periods.

## Columns

`load(unit, session_type=None)` returns all sessions of one vehicle, or one type, as one table indexed by `Timestamp`, with `session` (file name), `session_type` and `unit` columns. Paper Table 5 (p. 12) describes every column. The main ones:

| column | unit | role |
|---|---|---|
| Timestamp | | "ISO 8601-formatted datetime values with UTC time zone" (Table 5). Index, UTC. Median step 1 s in every vehicle and session type. |
| SOCave292 | % | BMS-reported average pack SOC ("Battery average SoC values", Table 5). An estimate, not a measurement. |
| BattVoltage132, RawBattCurrent132 | V, A | Pack voltage and current from the vehicle's sensors. The paper states no sign. Measured on raw data: negative while charging (in charging rows of sessions where SOC rises, 624,620 rows below 0 and 12,098 above 0 in all slow and fast sessions of both cars) and mostly positive while driving above 80 km/h (501,812 rows above 0, 68,353 below 0). Positive = discharge. |
| BMSminPackTemperature, BMSmaxPackTemperature | C | Pack temperature extremes. Table 5 gives the minimum's unit as "V", a typo; the maximum is in °C. |
| TotalChargeKWh3D2, TotalDischargeKWh3D2 | kWh | The vehicle's cumulative charge and discharge energy counters. |
| ChargeLineVoltage264, ChargeLineCurrent264, ChargeLinePower264 | V, A, kW | AC grid-side charging signals ("Grid AC ... recorded during slow charging sessions", Table 5). |
| FC_dcCurrent, FC_dcVoltage, FC*Limit*, FCMax*, FCMin* | A, V, kW | DC fast-charger current, voltage and limits (Table 5). |
| BMS_maxDischargePower, BMS_maxRegenPower, BMSdissipation312, BMS_preconditionAllowed | kW, bit | BMS power limits, dissipation and preconditioning flag (Table 5). |
| BMS_kwhDriveDischargeTotal, BMS_kwhRegenChargeTotal | kWh | Drive and regeneration energy counters (Table 5). |
| DI_uiSpeed, Odometer3B6, UI_Range | km/h, km, km | Speed, odometer, displayed range (Table 5). |
| VCFRONT_tempAmbient, VCRIGHT_tempAmbientRaw | C | Ambient temperature from the front and right vehicle controllers (Table 5). |
| GPSLatitude04F, GPSLongitude04F | degrees | Position. |
| segment_id | | Helper column of the authors' slow-charging extraction code; present in slow-charging files only. |

`Odometer3B6` holds 4294967.295 (0xFFFFFFFF scaled by 0.001 km) where no odometer frame was received: in all non-null odometer rows of charging and parking files of both cars except one row each in BEV2 slow-charging and parking files, and in 592 of 590,909 BEV1 and 1,005 of 1,425,728 BEV2 driving rows (6,196 and 7,302 rows per car in all, raw data, source-audit check). The publisher does not document it; it cannot be a reading. `clean=True` masks that value only; nothing else is changed.

No cell-level signals are released.
