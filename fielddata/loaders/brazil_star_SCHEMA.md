# brazil_star schema (candidate)

Source: Gaura, Trindade, Brusey, Gyamfi and Verba, "Brazil STAR Project Microgrid Monitoring Data", Zenodo, doi:10.5281/zenodo.3959739 (CC BY 4.0). No paper describes the data. Column meanings and units are from `MonitoringDataReadMe.txt` in the zip, quoted below where they matter.

## Files

One zip, `Brazil_STAR_Microgrid_Monitoring.zip`: `MonitoringDataReadMe.txt` and 822 daily CSVs named `YYYY-MM-DD_STAR-X_SYS.csv`. The readme writes the name with a hyphen after the date. The files use an underscore. SYS is Battery, PV or IAM (individual appliance monitors). The loader reads the CSVs inside the zip without extracting it.

## Units

Four households, STAR-A to STAR-D, one battery each (`fielddata.counting.CANDIDATE_RULES`: one battery per household). Battery days: A 138, B 187, C 64, D 38. STAR-D has no PV files. Valid battery times run from 2018-01-02 (STAR-C) to 2019-02-28 (STAR-B). The record says collection ended in March 2019.

## Columns (as released)

Battery, one row per minute: Time (text, local time, zone not stated), Current (mA), AmpereHours (mAh), SOC, NumChargeCycles, NumFullDischarge, Voltage (mV, about 24 V), Power (W), DischargeEnergy and ChargeEnergy (0.01 kWh).

PV: Time, Panel_voltage (mV), Panel_power (W), Energy_generated (0.01 kWh), Battery_state (0 Off, 1 Low power, 2 Fault, 3 Bulk, 4 Absorption, 5 Float, 6 Inverting: the charge controller's state, not a battery fault label).

IAM: Time, Real_Power (W), Reactive_Power (W), Voltage (unit unknown, per the readme), Sensor_ID.

## Readme and data disagree

- SOC: the readme says percent. The values run to 1000, so they are tenths of a percent (inferred).

## Values that cannot be measurements (raw data, all four households)

- Time: 4,011 battery rows have a time before 2017 (mostly 1969-12-31 20:00:00, a clock reset to zero shown at UTC-4, some in 1987), or text that does not parse as a time. Appliance monitors also have rows dated 2036. `systems()` spans use only times from 2017 to 2029.
- SOC: 420 battery rows outside 0 to 1000, down to -1.3e10.
- Current: 2,576 battery rows above 32,767 mA, up to 64,356. 65,536 minus 64,356 is 1,180, close to the most negative value (-1,205 mA), so these look like negative currents stored as unsigned 16-bit numbers. Not masked: they are kept as released.

## Cleaning

`clean=True` masks single values, never rows: Time outside 2017 to 2029, and in Battery files SOC outside 0 to 1000. On all four households' battery files this masks 3,763 values.

## Standard view

`fielddata.standard("brazil_star", unit)` converts raw loader values without cleaning, resampling, or filling absent measurements. The unit tier is tagged as `assigned per unit by standard_systems()` by default; call `fielddata.standard_systems("brazil_star")` for each unit's recorded tier and status.

Native current sign: not established; negative current may be unsigned-encoded. Current is converted to charge-positive only where the sign mapping is established; otherwise the source-named value is retained or the unit is explicitly blocked.
Where GB/T 32960 has a semantic match, standard names follow its vocabulary. A column absent from the release remains absent; no measurement column is synthesized.

| Authors' column | Our column | Conversion | Meaning and check evidence |
|---|---|---|---|
| `Voltage` | `pack_voltage` | multiply by 0.001 | Meaning follows this schema note's source-column descriptions. The synthetic round-trip test verifies numerical conversion, not physical identity. |
| `Current` | `source__current_A` | multiply by 0.001 | Meaning follows this schema note's source-column descriptions. The synthetic round-trip test verifies numerical conversion, not physical identity. |
| `SOC` | `soc` | multiply by 0.1 | Meaning follows this schema note's source-column descriptions. The synthetic round-trip test verifies numerical conversion, not physical identity. |

Other released fields retain their source names or a `source__` prefix with values unchanged; metadata identifiers retain their documented names. A round trip checks value preservation and does not establish an undocumented sensor meaning.
