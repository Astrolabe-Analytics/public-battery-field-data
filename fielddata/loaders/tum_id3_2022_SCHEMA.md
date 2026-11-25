# tum_id3_2022 schema (candidate)

Source: Wassiliadis, N. et al. (17 authors), "Quantifying the state of the art of electric powertrains in battery electric vehicles: Range, efficiency, and lifetime from component to system level of the Volkswagen ID.3", eTransportation 12, 100167 (2022), doi:10.1016/j.etran.2022.100167. Data: mediaTUM "Electric powertrain data of a Volkswagen ID.3 during real-world driving situations", doi:10.14459/2022mp1656313 (CC BY 4.0). Signal meanings from `Data/value_definitions.csv`.

## Files

`Data/Tracks/track_0.csv` to `track_147.csv` and the same drives as `.mat`, `Data/value_definitions.csv` (two note lines, then Request_ID, Value_ID, Name_en, Variable_name, Unit, Source (UDS request), Description, 223 rows), and `Data.sha512` (SHA-512 of the other 297 files). The loader reads the CSVs.

## Unit

One ID.3 Pro Performance. `scripts/checks/tum_id3_vs_tumftm.py` shows it is tumftm's ID1: at matching timestamps all 28,185 ID1 SOC readings and 330,778 pack voltage readings are identical (median difference 0), and the clocks agree. Maintainer's decision (2026-10-13): its extra signals belong to that unit, counted once, under tumftm. `fielddata.counting.CANDIDATE_RULES` counts 0 new units.

## Drives

148 drives, 2021-02-11 08:00:50 to 2021-12-08 14:14:20 (time column, ms since 1970, UTC, inferred), 2,168,330 rows at 0.1 s, about 60 hours of driving in all. Columns differ between drives: 8 to 178 per drive, 215 distinct across all.

## Columns (as released)

time (ms since 1970), hv_battery_current (A, "pack current"), hv_battery_voltage (V, "pack voltage", defined twice in value_definitions.csv), hv_soc (%), hv_temp_min and hv_temp_max (degC), hv_battery_temp_inlet and outlet, cell_voltage_1 to cell_voltage_108 (V), pack_temp_0, mileage (km), charger, climate, DC/DC and powertrain signals, and GPS and IMU channels. See definitions() for the full table.

What this release adds to tumftm's ID1 over 2021-02 to 2021-12: pack current and the 108 cell voltages. The tumftm schema notes that tumftm has neither.

## Cleaning

None known. `clean=True` masks nothing.

## Standard view

`fielddata.standard("tum_id3_2022", unit)` converts raw loader values without cleaning, resampling, or filling absent measurements. The unit tier is tagged as `assigned per unit by standard_systems()` by default; call `fielddata.standard_systems("tum_id3_2022")` for each unit's recorded tier and status.

Native current sign: not established in the available sources. Current is converted to charge-positive only where the sign mapping is established; otherwise the source-named value is retained or the unit is explicitly blocked.
Where GB/T 32960 has a semantic match, standard names follow its vocabulary. A column absent from the release remains absent; no measurement column is synthesized.

| Authors' column | Our column | Conversion | Meaning and check evidence |
|---|---|---|---|
| ? | ? | No physical mapping is enabled | The release-specific loader/schema limitations above are not resolved by inference; standard units are explicitly blocked or not telemetry. |

Other released fields retain their source names or a `source__` prefix with values unchanged; metadata identifiers retain their documented names. A round trip checks value preservation and does not establish an undocumented sensor meaning.
