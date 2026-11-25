# shenzhen_charging schema (candidate)

Source: Yang, H., Tian, J., Mai, W. and Chung, C.-Y., Mendeley Data, doi:10.17632/c7gg94tmvz.3 (CC BY 4.0), the data of Yang et al., "Privacy-preserving collaborative battery fault warning for massive electric vehicles by heterogeneous data from charging stations", Nature Communications 17, 974 (2026), doi:10.1038/s41467-025-67703-7. Column meanings from `Readme.txt`.

## Files

`processed_data.xlsx` (all sessions) and `processed_data_longer_than_30.xlsx` (sessions longer than 30 minutes, all of which are also in the first file), 8 sheets each. Readme: "dividing charging stations into 8 data owners". The owner code `class_judge` runs from 1 to 30, not 1 to 8.

## Units

Maintainer's decision (2026-10-13): one unit per charging session. There is no vehicle identifier, so one battery cannot be followed across sessions.

`systems()` (from `processed_data.xlsx`) has 31,449 distinct sessions (`transaction_id`, a 32-digit number kept as text). Each has one begin time, one battery type and one label.

**Duplicated sessions.** 4,538 sessions appear in both Sheet1 and Sheet7, with the same rows, begin time, battery type and owner code. Sheet7's owner codes 1, 2 and 3 repeat Sheet1's. `load()` returns those rows twice, once per sheet, as released, with a `sheet` column. Drop duplicates on (`transaction_id`, `id`) to count each minute once. `systems()` counts each session once.

## Columns (as released)

id, transaction_id, begin_time, end_time ("current sampling time"), total_charging_kwh, total_charging_min, current_soc, current_energy_meter_value, chargingv (V), charginga (A), out_power, charging_gun_temperature1 and 2 (the charging gun, not the battery), types (battery type code: 03 LFP, 06 NMC, 04 LMO, 05 LCO, 07 LP), class_judge (data owner), label (1 faulty, 0 normal).

Signals are measured by the charger: voltage, current, power, SOC and energy. There are no cell voltages and no battery temperature.

Sessions by battery type: LFP 19,733, NMC 11,321, LMO 298, LP 69, LCO 28. LP is lithium polymer, a cell format (source paper: Li polymer, LiPo). Maintainer's view (2026-10-16): codes 05 and 07 are swapped relative to the Readme. The paper's battery-type shares (LCO 0.19 percent, LiPo 0.07 percent; Yang et al. 2026, Fig. 1a) match the data's code 07 and code 05 shares by rows (0.20 and 0.05 percent, over-30-minutes workbook), so code 05 is taken to be lithium polymer and code 07 LCO. The release's Readme says 05 LCO, 07 LP. The set of chemistry labels does not change. The loader returns the codes as released. Rows: 1,288,719 distinct session-minutes. end_time runs from 2020-07-01 to 2024-03-13.

## Faults

5,680 of the 31,449 sessions are labelled faulty (label 1 on all their rows). The readme: faults reported by engineering personnel (thermal runaway, unbalanced cell voltages, short circuit and others), or temperatures high enough for the station to disconnect. Maintainer's decision (2026-10-13): all 5,680 count as battery faults, per session, since the release has no vehicle identifier (docs/descriptor/TABLE3_faults.md).

## Record and data disagree

The record says the longer file has 21,175 charging sequences, 1,547,432 sampling points and 10,154 EVs, from October 2020 to October 2023. The longer file has 18,531 distinct sessions and 1,382,319 rows, from September 2020 to March 2024. The vehicle count cannot be checked.

## Cleaning

None. `clean=True` masks nothing.

## Standard view

`fielddata.standard("shenzhen_charging", unit)` converts raw loader values without cleaning, resampling, or filling absent measurements. The unit tier is tagged as `session` by default; call `fielddata.standard_systems("shenzhen_charging")` for each unit's recorded tier and status.

Native current sign: not stated in the release documentation. Current is converted to charge-positive only where the sign mapping is established; otherwise the source-named value is retained or the unit is explicitly blocked.
Where GB/T 32960 has a semantic match, standard names follow its vocabulary. A column absent from the release remains absent; no measurement column is synthesized.

| Authors' column | Our column | Conversion | Meaning and check evidence |
|---|---|---|---|
| ? | ? | No physical mapping is enabled | The release-specific loader/schema limitations above are not resolved by inference; standard units are explicitly blocked or not telemetry. |

Other released fields retain their source names or a `source__` prefix with values unchanged; metadata identifiers retain their documented names. A round trip checks value preservation and does not establish an undocumented sensor meaning.
