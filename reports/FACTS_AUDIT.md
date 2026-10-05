# Facts audit

Each cell gives the status of the corresponding value in `fielddata/package_facts.csv`: measured from the release, stated by a public source, derived by a stated rule, unavailable from the release, or still open.

| Package | application | chemistry | units_released | cells_liion | cells_leadacid | cell_channels_measured | energy_mwh | energy_basis | span_unit_years | obs_hours | size_gb | files | fault_onset_timestamp | sentinels_documented |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bilfinger2024 | derived | stated | measured | derived | not_in_release | measured | stated | derived | measured | not_in_release | measured | measured | stated | stated |
| bilfinger2026 | derived | stated | measured | derived | not_in_release | measured | stated | derived | measured | not_in_release | measured | measured | stated | stated |
| cao | derived | derived | measured | derived | not_in_release | derived | derived | derived | not_in_release | derived | measured | measured | stated | stated |
| changan | derived | stated | measured | derived | not_in_release | measured | derived | derived | derived | not_in_release | measured | measured | stated | stated |
| cloverleaf | derived | derived | measured | not_in_release | not_in_release | not_in_release | derived | derived | measured | not_in_release | measured | measured | stated | stated |
| deng | derived | stated | measured | derived | not_in_release | not_in_release | derived | derived | measured | not_in_release | measured | measured | stated | stated |
| evbattery | derived | derived | measured | not_in_release | not_in_release | not_in_release | not_in_release | derived | not_in_release | measured | measured | measured | stated | stated |
| fei_bus | derived | not_in_release | measured | not_in_release | not_in_release | not_in_release | not_in_release | derived | not_in_release | not_in_release | measured | measured | stated | stated |
| flashbattery-agv | derived | stated | measured | not_in_release | not_in_release | not_in_release | not_in_release | derived | measured | not_in_release | measured | measured | stated | stated |
| ku_leuven_bev | derived | stated | measured | not_in_release | not_in_release | not_in_release | stated | derived | measured | not_in_release | measured | measured | stated | stated |
| li2026 | derived | stated | measured | derived | not_in_release | measured | derived | derived | not_in_release | stated | measured | measured | stated | stated |
| m5bat-2023-04 | derived | stated | measured | derived | derived | not_in_release | derived | derived | measured | not_in_release | measured | measured | stated | stated |
| m5bat-pbacid | derived | stated | measured | not_in_release | stated | not_in_release | stated | derived | measured | not_in_release | measured | measured | stated | stated |
| ppl | derived | stated | measured | stated | not_in_release | measured | stated | derived | measured | not_in_release | measured | measured | stated | stated |
| rwth-android | derived | stated | measured | derived | not_in_release | derived | derived | derived | measured | not_in_release | measured | measured | stated | stated |
| rwth-home | derived | stated | measured | stated | not_in_release | not_in_release | stated | derived | measured | not_in_release | measured | measured | stated | stated |
| schaeffer | derived | stated | measured | derived | not_in_release | derived | derived | derived | measured | not_in_release | measured | measured | stated | stated |
| tsukuba | derived | stated | measured | not_in_release | not_in_release | not_in_release | stated | derived | stated | not_in_release | measured | measured | stated | stated |
| tumftm | derived | stated | measured | derived | not_in_release | not_in_release | stated | derived | measured | not_in_release | measured | measured | stated | stated |
| xie | derived | stated | measured | derived | not_in_release | measured | not_in_release | derived | measured | not_in_release | measured | measured | stated | stated |
| zhang2023 | derived | derived | measured | not_in_release | not_in_release | not_in_release | not_in_release | derived | not_in_release | measured | measured | measured | stated | stated |
| zhou2026 | derived | stated | measured | derived | not_in_release | measured | stated | derived | measured | not_in_release | measured | measured | stated | stated |

## Open values


## Cross-package overlap

EVBattery and Zhang2023 share **49 vehicles**: zhang2023 brand 2 and evbattery dataset 3 are one fleet under different vehicle numbers. The overlap is tested by content (identical snippets) by `scripts/facts/_overlap_scan.py`; see `reports/facts/_cache/zhang2023_evbattery_overlap.json`.
