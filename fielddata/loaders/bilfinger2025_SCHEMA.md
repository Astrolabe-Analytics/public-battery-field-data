# bilfinger2025 schema

Source file: `data.zip` from the mediaTUM data server (record 1765567, doi:10.14459/2024mp1765567), the share's "Download all" zip, 305,568,300 bytes. It holds `m1765567/checksums.sha512` (SHA-512 of the other 29 members) and, under `m1765567/data/`, 21 feather files and 8 font files used by the authors' figures. All 29 members match the release's own checksums (fielddata.verify, 2026-10-15).

The feather files are 17 vehicle recordings and 4 laboratory files, in folders Cupra, Taycan, Tesla and VW (with VW/cell). Paper: Bilfinger et al. (2025), npj Clean Energy 1, 10, doi:10.1038/s44406-025-00010-8, read in arXiv 2508.15517v1.

`systems()` lists every file with its `kind` (vehicle or laboratory cell), the `vehicle` it belongs to, format, archive member and size. `load(unit)` takes a file stem and returns that recording as released, with no index change. `clean=True` changes nothing: no placeholder or out-of-range code is documented for this release.

## Vehicles

The paper (p. 13, Methods, "Vehicles under test") lists two VW ID.3, five Cupra Born, one Tesla Model 3 SR+, two Porsche Taycan "from different sources" and two Tesla Model Y Long Range. File names carry a site code that separates them.

| vehicle (systems()["vehicle"]) | files | in the collection |
|---|---|---|
| VW ID.3 | `VW_ID3_JB_8A_CEE7_FTM_2021`, `_2023`, `_2024`, `VW_ID3_FTM_JB_8A_CEE7_FTM_2024_balanced`, `_imbalanced` | bilfinger2024 vehicle: the 2021, 2023 and 2024 files are identical to bilfinger2024's three ID.3 charges (every shared column) |
| VW ID.3 (GB, defective cell) | `VW_ID3_JB_8A_CEE7_GB_2024_cell_defect` | new: the paper's second ID.3, which "has a defective cell limiting the overall battery pack performance" (p. 13) |
| Cupra 204, 213, 288, 349, 397 | `Cupra_Born_<n>_JB_8A_CEE7_CS_2024` | bilfinger2026 vehicles (same licence-plate numbers), new charges in April 2024 |
| Tesla Model 3 SR+ | `Tesla_Model_3_JB_6A_CEE7_FTM_2021`, `_2025` | bilfinger2024 vehicle: the 2021 file is identical to bilfinger2024's 2021 charge |
| Porsche Taycan (FTM), (AMS) | `Porsche_Taycan_JB_10A_CEE7_FTM_2023`, `_AMS_2024` | new, two cars (10,000 and 70,500 km) |
| Tesla Model Y (TW), (MI) | `Tesla_Model_Y_JB_8A_CEE7_TW_2024`, `_MI_2025` | new, two cars (77,600 km, built 2022, and 24,800 km, built 2024) |

The units are counted in `fielddata/counting.py` (5 new; the others count once under bilfinger2024 and bilfinger2026). Evidence per file is in `reports/checks/v12/bilfinger2025_vehicles.csv` and `bilfinger2025_screen.csv`.

## Columns of the vehicle files

| column | unit | role |
|---|---|---|
| U | V | Pack voltage. |
| I | A | Pack current, positive while charging: no negative value in 16 of the 17 vehicle files. `VW_ID3_FTM_JB_8A_CEE7_FTM_2024_imbalanced` has 11,409 negative rows. |
| SOC | % | BMS-estimated SOC. Present in every vehicle file. |
| Q, E, P | Ah, kWh, kW | Charge, energy and power computed by the authors, not sensor values. `Q` is in every vehicle file. `E` is missing in the Taycan FTM, the 2021 Tesla Model 3 and the 2021 and 2023 ID.3 files. |
| cell_voltage_N | V | Cell-voltage columns: 108 in each VW ID.3 and Cupra file (108s2p, a column per parallel pair), 192 in the Taycan FTM file (numbered 1 to 198; the paper gives 198s2p), 106 in the 2021 Tesla Model 3 file, and 111 in the 2025 Tesla Model 3 and both Model Y files (more columns than the 106 and 96 series cells the paper gives). The Taycan AMS file has none. |
| temperatures | C | 20 to 22 temperature columns in the VW Group files; `hv_temp_avg` and `outside_temp` in the Taycan files; none in the 2025 Tesla files. |
| time_ms, time_s, time_min, time_h | ms, s, min, h | Elapsed time within the recording. |
| date | timestamp | Calendar time in the VW ID.3, Cupra and Taycan files. The Tesla files carry elapsed time only. Time zone not stated. |

The Tesla files also hold decoded CAN signals (`UnixTimeSeconds528`, `RawBattCurrent132`, `SOCmin292`, `UI_SOC` and others), as named by the authors' .dbc decoding.

## Laboratory files

`VW_LG_78Ah_NMC_20deg_CC_C50` and `..._C50_Anode`, `..._Cathode_ch`, `..._Cathode_dch` are C/50 reference curves of the VW cell (LG 78 Ah NMC532) and its electrodes. They are held but are not field units.

## Out of scope here

The paper's Supplementary Table 1 and its Author Correction (doi:10.1038/s44406-025-00018-0) could not be read from scripts (nature.com refuses them). The code repository is https://github.com/TUMFTM/nature_soh. Its LICENSE file is GPL-3.0, while its README says LGPL-3.0.
