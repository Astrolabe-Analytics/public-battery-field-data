# beijing_ev schema (candidate)

Source: He, C., Mendeley Data, doi:10.17632/mm9rvfvmrb.3 (CC BY 4.0), for Wei, He, Li and Zhao, Journal of Energy Storage 49, 104091 (2022). The record's description is one sentence: driving-cycle data from a battery electric vehicle on actual roads in Beijing in 2018 and 2019. The paper could not be read here, so column meanings below are from the column names and the data, and say so.

## Files

Twelve workbooks in two folders, `2018/` and `2019/`, named `<year>.<month>.<day>.xlsx`, one per day: 2018-01-03, 01-17, 04-08, 04-19, 07-14, 07-28, 10-07, 10-28, 2019-01-13, 01-21, 08-07, 08-15. One sheet each.

## Units

One car. `systems()` has one row per day (`unit` is the day, `vehicle` is the car), with the first and last time and the odometer at the start and end of the day. The unit count rule (`fielddata.counting.CANDIDATE_RULES`) counts one vehicle.

## Columns (as released, `load()` changes no value)

| column | type | meaning |
|---|---|---|
| time | int | date and time as yyyymmddHHMMSS, about every 10 s. Time zone not stated (Beijing local time likely). |
| speed | float | vehicle speed, km/h from the range 0 to 106 (inferred, unit not stated) |
| mileage | int | odometer, km (inferred). 54,945 on 2018-01-03 to 157,688 on 2019-08-15, about 230 km per recorded day. |
| voltage | float | pack voltage, V (inferred). 310.1 to 372.8 raw. |
| current | float | pack current, A (inferred). -111.1 to 229.9 raw. Positive values go with driving, so positive is discharge (inferred). |
| soc | int | state of charge, percent. 18 to 100 raw. |

No temperature, cell data, vehicle model or battery rating is released.

## Cleaning

None known. `clean=True` masks nothing.

## Standard view

`fielddata.standard("beijing_ev", unit)` converts raw loader values without cleaning, resampling, or filling absent measurements. The unit tier is tagged as `session` by default; call `fielddata.standard_systems("beijing_ev")` for each unit's recorded tier and status.

Native current sign: discharge positive (inferred). Current is converted to charge-positive only where the sign mapping is established; otherwise the source-named value is retained or the unit is explicitly blocked.
Where GB/T 32960 has a semantic match, standard names follow its vocabulary. A column absent from the release remains absent; no measurement column is synthesized.

| Authors' column | Our column | Conversion | Meaning and check evidence |
|---|---|---|---|
| `voltage` | `pack_voltage` | unchanged | Meaning follows this schema note's source-column descriptions. The synthetic round-trip test verifies numerical conversion, not physical identity. |
| `current` | `pack_current` | multiply by -1 (reverse sign) | Meaning follows this schema note's source-column descriptions. The synthetic round-trip test verifies numerical conversion, not physical identity. |
| `soc` | `soc` | unchanged | Meaning follows this schema note's source-column descriptions. The synthetic round-trip test verifies numerical conversion, not physical identity. |

Other released fields retain their source names or a `source__` prefix with values unchanged; metadata identifiers retain their documented names. A round trip checks value preservation and does not establish an undocumented sensor meaning.
