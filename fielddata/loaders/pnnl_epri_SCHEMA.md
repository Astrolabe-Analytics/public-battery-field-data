# pnnl_epri (candidate)

Crawford, A. (PNNL) and Thompson, J. (EPRI) (2026), "Grid-Scale BESS Operational Datasets for Battery Modeling Research", Zenodo, doi:10.5281/zenodo.22947521, published 2026-09-25. License: CC BY 4.0 (record). Candidate package: in `CANDIDATES`, not in the collection's totals.

The record's description is the abstract of a companion article ("This article releases a collection of datasets from 12 grid-scale BESS ..."). No article is linked from the record and none was found on 2026-10-09, so this note rests on the record's description and on the authors' processing scripts released with the data (`_common.R`, `_epri_channels.R` and one `<system>.R` per system). Those scripts are "published copies" with comments removed and source column names replaced by generic ones; the ratings and series cell counts they read come from a private `config/system_spec.json` that is not released.

## Files

26 files, kept as shipped: one `<system>.feather` per system (12, 3.43 GB in all), one `<system>.R` per system, `_common.R` and `_epri_channels.R`. The record publishes an MD5 for each file; `fielddata/reference_checksums.csv` holds them and `python -m fielddata.fetch pnnl_epri` checks them.

## Units

One unit is one system, one `.feather` file (`systems()`, 12 rows). Six systems come from the Washington Clean Energy Fund (WACEF) Grid Modernization projects studied by PNNL (`Avista`, `ENW`, `OPALCO`, `PSE`, `SnoPUDMESA1`, `SnoPUDMESA2`), and six from EPRI host sites that are anonymised (`EPRI_LFP1` to `EPRI_LFP3`, `EPRI_NMC1`, `EPRI_NMC2`, `EPRI_VRF1`). A system holds several meters (see Meters), which are measurement points of the one system, not separate units.

## Layout

Each file is long: one row per (`HoursElapsed`, `Meter`), sorted by `HoursElapsed` then `Meter`, with the 20 columns of `RELEASE_COLS` in `_common.R` in this order. Every meter of a system has a row at every timestamp of that system's timeline (`meter_block` writes all meters on the same `HoursElapsed` grid), with NaN where a meter has no value.

| column | type (feather) | unit as released | meaning (source) |
|---|---|---|---|
| HoursElapsed | double | h | hours since the system's first record (`add_elapsed`, `_common.R`) |
| DayNumber | int32 | day | calendar day since the first record's day, counted in the clock the script sets (`add_elapsed`; see Time) |
| Meter | string | | measurement point (see Meters) |
| Power | double | 1/h (C-rate) | real power divided by the system's rated energy in kWh (`write_release`); positive = discharge, auxiliary meters positive = consumption |
| RequestedPower | double | 1/h | power setpoint, same scaling |
| ReactivePower | double | 1/h | reactive power (kvar) divided by rated kWh |
| RequestedReactivePower | double | 1/h | reactive power setpoint, same scaling |
| Voltage | double | V per cell | meter voltage divided by the series cell count where one is configured (`write_release`); values above the chemistry's `cell_v_max` were set to NA by the authors |
| VoltageMax, VoltageMin, VoltageAvg | double | V | cell voltage statistics reported by the BMS, released as cell values (not divided) |
| Current | double | 1/h (C-rate) | current divided by the system's ampere-hour basis, rated kWh x 1000 / (cell nominal V x series cells) (`system_ah`); positive = discharge |
| SOC | double | fraction 0..1 | BMS state of charge divided by 100 in each script |
| TempMax, TempMin, TempAvg | double | degC | battery (module, cell or, for flow systems, electrolyte) temperatures |
| TempAmbient | double | degC | enclosure or outdoor air temperature, per script |
| QualityFlag | bool | | the authors' data-quality flag: per-system rules in `<system>.R` (for example averaged duplicate timestamps, an inverter replacement window, SOC at 0 while active, strings offline), plus SOC jumps above 0.2 at rest (`write_release`) |
| CycleIndex | string | | the authors' segment label: a new segment at each change of charge/discharge/rest state or gap; suffix `Out` when SOC is outside 0.05..0.95 (`add_cycles`) |
| Use | bool | | TRUE for segments the authors mark usable: SOC swing above 0.3, active, in range, at most 25 % flagged (`add_cycles`) |

## Meters

Meter names are built in the scripts (`meter_block` calls): `PDC` battery DC side (numbered per string, rack or module), `PDCI` inverter DC side, `PAC`/`PACI` inverter AC side, `PAUX` auxiliary load, `PFDR` feeder, `PGCP` grid connection point. A meter without a number is a system-level aggregate.

## Normalisation and what is not released

Ratings are not released. Power is a C-rate on rated energy and current a C-rate on the system's ampere-hour basis; voltage is per cell. The record gives the reason: "Power values are normalized to C-rates and timestamps are reported as elapsed time, which allows cross-system comparison and keeps confidential system specifications out of the released data." So energy throughput can be computed in units of rated capacity (equivalent full cycles), but not in kWh, unless a rating is taken from another source (see `reports/candidates/pnnl_epri/NOTES.md`).

## Time

`HoursElapsed` is a float of hours since each system's first record; no date is released. The scripts set the clock before computing it: `Etc/GMT+8` (fixed UTC-8, no daylight saving) for Avista, SnoPUDMESA1 and SnoPUDMESA2; `America/Los_Angeles` (the default of `add_elapsed`) for ENW, OPALCO and PSE; UTC for all EPRI systems. `HoursElapsed` itself is a difference of instants, so it is not affected by the zone; `DayNumber` is.

## Cleaning by the authors and by the loader

The authors already removed values before release: out-of-range SOC, temperatures outside -40..100 degC, power and current magnitudes above per-system limits, voltages above the chemistry's per-cell maximum, min/max/avg inconsistencies, and some temperature sentinel codes (0, 320 and 1127 deci-degF in SnoPUDMESA1 and SnoPUDMESA2). `load(clean=True)` therefore masks nothing further. Remaining near-zero values are kept as released (see the per-system profile).

## Systems

Measured through the loader on raw data (`python scripts/checks/pnnl_epri_units.py`, `reports/candidates/pnnl_epri/pnnl_epri_units.csv` and `pnnl_epri_meters.csv`). Span is first to last `HoursElapsed`. Chemistry is as stated in Crawford's 2026 DOE peer-review poster (alias table); the release itself states only the three families. Per-cell voltage agrees with each chemistry (median `Voltage` on DC meters: LFP 3.27 to 3.62 V, NMC 3.69 to 3.88 V, LMO/NMC 3.67 V, vanadium flow 1.34 to 1.52 V where the strings are live).

| unit | chemistry | rows | meters | span (days) | row spacing | clock set by the script |
|---|---|---:|---|---:|---:|---|
| Avista | vanadium flow | 65,031,470 | PAC1-2, PDC1-2, PFDR1-2, PGCP | 1,090.5 | 10 s | Etc/GMT+8 |
| ENW | LFP | 343,432 | PAC, PAUX, PDC, PGCP | 59.6 | 60 s | America/Los_Angeles |
| EPRI_LFP1 | LFP | 9,144,612 | 34 string meters PAC1420-1 ... , PAUX, PGCP | 882.0 | 300 s | UTC |
| EPRI_LFP2 | LFP | 3,935,832 | PACI1-8, PDC1-8, PDCI1-8 | 569.4 | 300 s | UTC |
| EPRI_LFP3 | LFP | 13,443,840 | PAC1-3, PGCP | 389.0 | 10 s | UTC |
| EPRI_NMC1 | NMC | 1,659,983 | PDC, PDC1.1-1.12 | 443.4 | 300 s | UTC |
| EPRI_NMC2 | NMC | 11,231,157 | PDC, PDC1.1-1.10, PDC2.1-2.10 | 1,857.0 | 300 s | UTC |
| EPRI_VRF1 | vanadium flow | 3,056,464 | PACI1-3, PDC1-9, PDCI1-3, PGCP | 663.3 | 300 s | UTC |
| OPALCO | LFP | 1,109,382 | PAC, PDC, PGCP | 262.0 | 60 s | America/Los_Angeles |
| PSE | LFP | 17,756,816 | PAC, PAUX, PDC, PGCP | 610.5 | 10 s | America/Los_Angeles |
| SnoPUDMESA1 | LMO/NMC | 41,377,980 | PAC1a-b, PAUX1a-b, PDC1a-b, PGCP | 709.4 | 10 s | Etc/GMT+8 |
| SnoPUDMESA2 | vanadium flow | 25,913,120 | PAC1-4, PDC1-4, PFDR, PGCP | 307.0 | 10 s | Etc/GMT+8 |

Each system's timeline is regular at its row spacing (at least 99.6 % of steps equal the median). Gaps over one hour: Avista 78 (longest 192 h), PSE 29 (longest 758 h), SnoPUDMESA1 54 (426 h), SnoPUDMESA2 16 (115 h), OPALCO 5 (44 h); none in the others. EPRI_LFP1 and EPRI_LFP3 release no current, and EPRI_LFP3 no voltage (AC meters only). The three vanadium flow systems have a stack-cell series count in the authors' config (per-cell voltage about 1.4 to 1.5 V), but no cell count in the collection's sense.

## Sign convention

The authors release positive = discharge for Power, RequestedPower and Current (`write_release`; EPRI_NMC1 and EPRI_NMC2 are flipped from a charge-positive source). Measured: on each system's system-level meter, Power and the next change of SOC have opposite signs in 92.8 % (SnoPUDMESA2) to 100 % of steps with |Power| above 0.05 C (not testable on EPRI_LFP2, which has no system meter and only one qualifying step on PDC1); on every meter that has both, Power and Current share their sign in 100 % of rows with both above 0.01 C. Auxiliary meters (`PAUX`) are positive = consumption by construction (`abs`).

## Findings (raw data; `python scripts/checks/pnnl_epri_findings.py`, `reports/candidates/pnnl_epri/pnnl_epri_findings.txt`)

- EPRI_VRF1 inverter DC meters `PDCI1` to `PDCI3`: Current is never positive (0.00 % of about 144,500 rows each, minimum -0.80 C), while their Power is positive in about 6 % of rows. The discharge sign of the inverter DC current is lost. The module meters `PDC1` to `PDC9` are consistent.
- PSE `PDC` at rest (PAC within 0.002 C of zero, 2,439,231 timestamps): Current median +0.0060 C and positive in 99.6 % of them, Power positive in 100 %. `PSE.R` computes the DC current zero offset (`I_OFFSET`) but subtracts `0*I_OFFSET`, so the offset is in the release.
- Avista `PDC1` and `PDC2`: Voltage below 0.1 V per cell in 78.2 % and 50.7 % of rows with a voltage (PDC2 Power is 0 C at the median in those rows; PDC1 has no Power there): strings at 0 V while out of service, released as 0 rather than missing (inference). 545 days (DayNumber 384 to 928) are flagged on more than 99 % of rows: the inverter, tank and stack replacement window `Avista.R` sets from 2016-11-01 to 2018-04-30.
- SnoPUDMESA1 `PGCP`: 71 rows with |Power| above 2.5 C (up to 6.75 C), all with QualityFlag; the authors flag them as power spikes and keep the values.
- Temperature exactly 0.0 degC, kept as released: Avista (TempMax 7.6 M, TempMin 8.9 M rows), EPRI_VRF1 (about 202,000 each), EPRI_NMC1 (50,868 each), EPRI_LFP2 (28,316 to 36,000), EPRI_NMC2 (1,983 max/min, 42,595 avg), PSE (399, 893), ENW (7 TempMin). The authors scrubbed 0 as a sentinel only in SnoPUDMESA1 and SnoPUDMESA2; in the others 0 coincides with offline periods but is not documented as a code, so `clean=True` leaves it.
- EPRI_NMC2 is the ppl E.W. Brown system (see `reports/candidates/pnnl_epri/NOTES.md`): its hour 0 is 2017-01-01 00:00 UTC.
