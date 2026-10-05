# cloverleaf schema

Source file: `SNAM/export.xlsx` inside `Monitoring data 2nd life battery.zip`. The same archive holds PDF plots and inverter workbooks, which the loader does not read.

The workbook has four worksheets: three HV pack sheets (`SNAM HV - 2100173`, `-2100177`, `-2100179`, 20,000 s averages, 2021-09-01 to 2022-01-01, 520 or 521 rows each) and `typical day` (172 s averages over 2022-01-01, 489 rows). `systems()` lists only the three packs, which are run together as one second-life system and each count as a unit in the totals (three units), matching Table 2 and the dashboard. The typical-day sheet is not a unit and is not listed; load it with `typical_day()` (in `fielddata.loaders.cloverleaf`) or `fielddata.load("cloverleaf", unit="typical day")`.

## Columns and what the sources say (checked 2026-10-04)

The only author documentation is the Zenodo record (10.5281/zenodo.6373656, published 2022-03-21 by Futech for the EU CIRCUSOL project). Its description lists "Round Trip Efficiency", "State of Health evolution" and "Typical Day V I & Vcell" and defines no column, unit, sign convention, time zone or chemistry. The column names below are the workbook's own (row 1 of each sheet); the units are the workbook's row 2 (`%` for SOH and SOC, `Volt` for the voltages, `Ampere` for Ipack). Every meaning beyond the name and unit is our inference.

| column | unit (row 2) | role |
|---|---|---|
| epoch_ms | | Unix time in milliseconds (row 2 gives no unit; read from the magnitude, about 1.63e12 in September 2021). |
| date | | Date and time of the row (the index). Time zone not stated. In the data it equals epoch_ms read as UTC on all three pack sheets (offset 0 h in every month, September to December 2021), and UTC + 1 h on the typical-day sheet (all 489 rows, 1 January 2022), so the two kinds of sheet do not share a clock basis (raw data, checked 2026-10-04). |
| SOH, SOC | % | State of health and state of charge. The sources do not say how they are obtained; they are presumably BMS-reported estimates. |
| Vcdif, Vcavg, Vcmax, Vcmin | V | Cell-voltage spread, mean, maximum and minimum (names only; not defined by the publisher). |
| Vpack | V | Pack voltage. |
| Ipack | A | Pack current. The sign convention is not documented. In the data, positive Ipack goes with rising SOC: the correlation of Ipack with the next-row change of SOC is 0.72 to 0.73 on every sheet, and on the typical-day sheet SOC rises after 99 of 100 rows with Ipack > 0.5 A and falls after 109 of 112 rows with Ipack < -0.5 A (raw data, checked 2026-10-04). Positive Ipack is therefore charging, by inference from the data. |

Row 1 of each sheet says "All values are average values over 20000 seconds" (the three pack sheets) or "All values are average values over 172 seconds" (typical day). Every column is averaged, so Vcmax and Vcmin are window averages of the per-sample extremes, not the extremes over the window.

Chemistry is not stated in any held source; the facts table infers NMC-class from the released cell voltages.

## Unit count (checked 2026-10-02, decided 2026-10-03)

`systems()` returned four rows until 2026-10-05, when the typical-day sheet was taken out of the list (it stays loadable). Until 2026-10-03 the totals counted one unit (the rule was "one system; its sheets are three packs and a typical day"). What the deposit shows:

- The typical-day sheet is not a battery. It is one day of the same installation at 172 s averaging, so it is never a unit.
- The three pack sheets are three physical packs. Each has its own serial number in the sheet name, its own inverter workbook in the archive (`InverterSP1ES110LBL160 detailed.xlsx`, `InverterSP1ES110M72123 detailed.xlsx`, `InverterSP1ES110LC8076 detailed.xlsx`), and its own state of health (raw data: 90.0 to 93.0, 89.0 to 91.4 and 89.0 to 91.4 percent).
- They are run as one system. Pack current correlates at 1.000 between 2100173 and 2100177 and at 0.971 with 2100179, and pack voltage at 1.000 and 0.978 (raw data, 20,000 s averages). The Zenodo record describes "the second-life battery system", singular.

Decision (Robert, 2026-10-03): cloverleaf counts three units, one per pack, the same rule as for m5bat-2023-04. `fielddata/counting.py` counts the rows of `systems()` whose kind is `pack`. Service time is the first-to-last span of each pack sheet, summed over the three packs (1.00 unit-years). The energy (0.0797 MWh) was already computed for the whole system: one pack's capacity from the typical-day sheet, divided by its state of health, times the mean pack voltage, times three packs.
