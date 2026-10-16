# rise_conbat schema (candidate)

Source: Fast, Scott, Casanova and MoradiKouchi, "Data-driven State-of-Health prediction for reused batteries in new applications", Zenodo, doi:10.5281/zenodo.17287096 (CC BY 4.0). RISE project "Data-Driven State-of-Health Prediction for Recycled Batteries in New Applications", funded by the Swedish Energy Agency. No paper. Conventions from the record's README.md, quoted where they matter.

## Files

One zip of database exports: 11 collection windows, `1. 230420-230516/` to `11. 240501-241104/` (yymmdd-yymmdd), and `BESS/9. 240207-240214/`. Each has db-export-cell.csv, db-export-module.csv, db-export-string.csv and db-export-module-info.csv. Some also have db-export-energy.csv, and window 1 has modules.csv. README: "Some exports evolve over time ... Always rely on headers present in each CSV." `hour` is UTC ("ISO-8601 strings with UTC offset").

Layouts (raw headers):
- Windows 1 to 4: long format, `hour, location, rack, string, module, [cell,] metric, value, is_filler`.
- Windows 5 to 7: wide, `hour, location, rack, shelf, module, [cell,] voltage, voltage_is_filler[, temperature, temperature_is_filler]`.
- Windows 8 on and BESS: as 5 to 7, with `module_uuid` after `hour`.
- String files: long format, with metrics such as ac-active-power, dc-current, dc-line-to-neutral-volts and relay states.

## Truncated exports

Three files end mid-row at about 1,020 MiB:
- `10. 240226- 240430/db-export-cell.csv` (1,069,023,232 bytes)
- `11. 240501-241104/db-export-cell.csv` (1,069,285,376)
- `11. 240501-241104/db-export-string.csv` (1,069,547,520, exactly 1,020 MiB)

Their last row is incomplete, and the rows after the cut were not exported. Window 10's cell data stop at 2024-04-13 22:35 and window 11's at 2024-06-18 09:08, though the windows run to 2024-04-30 and 2024-11-04. `load()` marks these files with `attrs["truncated"]`.

## Units

The module-info tables list installations: `id` (module id, car plus module number, for example `H406450-1`), car, car_model, disassembly_date, cells_in_series (12), nominal_energy_conversion, position (container, rack, string, module), and start_date and end_date. Modules from 11 cars rotate through the same positions over time, so positions do not identify modules.

The record's "106 modules" are installation rows. Window 11's table has 106 rows and 88 distinct module ids, because 19 modules were installed twice. With the BESS table that makes 107 installation rows, 88 modules and 11 cars ("VW Passat 15-" 91 rows, "VW Passat 20-" 16). At any one time, 24 module positions report module-level telemetry. `systems()` has one row per distinct module id (88). Maintainer's decisions of 2026-10-13 name no rule for this release, so counting distinct modules is a judgement call.

## Ratings

`nominal_energy_conversion` is 9.9 for "VW Passat 15-" and 13.0 for "VW Passat 20-". These are the pack energies of the Passat GTE (9.9 and 13 kWh), and `cells_in_series` is 12 per module. With 8 modules per pack, a module is 1.24 or 1.63 kWh nominal. This is derived, not stated per module.

## Cleaning

None. The `is_filler` flags (README: "synthetic or gap-filled values") are returned for the caller to use, and nothing is masked.
