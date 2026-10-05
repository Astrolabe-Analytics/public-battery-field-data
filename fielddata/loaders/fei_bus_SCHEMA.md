# fei_bus schema

Source files: `vin1.csv`, `vin5.csv`, `vin12.csv`, `vin19.csv`, one per commercial electric bus. Each is a short summary table, not telemetry.

The only author documentation is the Mendeley Data record (10.17632/j9ky68gnd3.3, version 3, 2025-09-03, contributor Zicheng Fei). Its whole description is "This dataset contains data obtained from batteries of commercial electric buses"; it lists no related article and defines no column, unit or method. Every meaning below beyond the column name is our inference.

`systems()` lists the four files. `load(unit=None)` reads one, several or all buses and adds a `unit` column; rows keep release order, because the release has no timestamps.

| column | unit | role |
|---|---|---|
| SOH | fraction | A state-of-health estimate of undocumented method (raw range 0.478 to 1.028). |
| SOH(OCV) | fraction | A second state-of-health estimate of undocumented method, named for open-circuit voltage (raw range 0.709 to 1.342). It reaches 1.34, which no capacity ratio can, so treat it as an index rather than a capacity ratio. |
| mileage | km (assumed; not documented) | Mileage at each estimate (raw range 51.7 to 262,626.6). |

Measured rows: vin1 101, vin5 161, vin12 329, vin19 71. Values above 1 in both SOH columns are kept as released; the record does not say how the estimates were made. `clean=True` changes nothing.

Release order is not a clean time series (raw data, checked 2026-10-04). Mileage rises between most consecutive rows (vin1 69 rises and 8 falls, vin5 100 and 5, vin12 270 and 20, vin19 49 and 5), but each file also has isolated rows with much lower mileage between rows near the maximum (vin1: 443 and 15,372 among rows above 100,000), and vin1 ends on a second rising run (23,344 to 39,434) after reaching 241,515. The largest fall between consecutive rows is 96,097 to 245,216 per file. Within each bus SOH and SOH(OCV) agree only loosely (Spearman 0.43 to 0.72) and their rank correlation with mileage is weak or of mixed sign (SOH: -0.74 to +0.29; SOH(OCV): -0.58 to -0.04). SOH(OCV) is above 1.05 in 2 to 47 percent of a bus's rows (vin12 47 percent).
