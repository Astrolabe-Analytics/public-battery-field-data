# Dataset screening

This is the list of public battery datasets we have looked at, and where each one stands. It is a living list. We update it as we screen new suggestions and as datasets change.

A dataset qualifies for the collection when it meets all of these:

- The batteries ran in real-world field operation, such as vehicles, grid storage or off-grid systems.
- The release has battery-level signals, such as voltage, current, temperature or state of charge, recorded over time.
- Anyone can download it without a login or subscription.
- Its license allows redistribution, or allows us to publish a loader that reads the original files.

We also follow three placement rules:

- If a release contains some real field battery data, meaning battery-level time series from real operation, it goes on deck. We then take the whole release, not only the field part.
- Packs or modules cycled in a lab go under "Adjacent, maybe later".
- Cells cycled in a lab are out of scope, whatever the test protocol. We tag each one with what it was cycled for, such as EV, eVTOL, grid or second-life, for future reference.

To suggest a dataset, see [CONTRIBUTING.md](CONTRIBUTING.md).

Of the Battery Data Commons field datasets, these are already in our collection: BBOXX off-grid solar (aitio), EV pack AC-charging diagnostics (bilfinger2026), Beihang EV fault diagnosis (cao), Changan new energy vehicles (changan), BAIC EU500 on-road charging (deng), EVBattery (evbattery), M5BAT grid storage (m5bat-2023-04), Android smartphone batteries (rwth-android), residential home storage (rwth-home), 28 LFP battery systems (schaeffer), VW ID.3 and CUPRA Born UDS data (tumftm), EV charging and fault data (zhang2023).

## On deck (help welcome)

These qualify. We plan to add them in a future release. If you know one of them well, we would like to hear from you.

| Dataset | Link | Why |
|---|---|---|
| PNNL/EPRI grid battery energy storage | [https://zenodo.org/records/22947521](https://zenodo.org/records/22947521) | 12 grid storage systems with voltage, current, temperature and SOC over time. CC BY 4.0. One of the 12 is the same system as our ppl package, so we count it once. Accepted for the next release, v1.2. |
| Stanford passenger EV BMS | [https://doi.org/10.25740/yx490wc6642](https://doi.org/10.25740/yx490wc6642) | One passenger EV from Sep 2021 to Apr 2025, with cell and pack voltage, current, SOC, and module and pack temperature. 18 GB. The license is CC BY-NC-ND, so we will publish a loader that reads the original files and no converted or derived data files. |
| LFP and NMC cell-to-pack lab and field aging | [https://zenodo.org/records/20132842](https://zenodo.org/records/20132842) | 16 grid storage packs in the field, plus lab cells and packs from the same batches. CC BY 4.0. We will take the lab parts too. |
| RISE second-life BESS (Conbat) | [https://zenodo.org/records/17287096](https://zenodo.org/records/17287096) | 106 second-life VW Passat modules from 11 cars, in containers at 3 sites, Apr 2023 to Nov 2024. Cell voltage, module voltage and temperature, string current and AC power at 1-minute rows. CC BY 4.0. The record does not describe the use case in words. |
| BIRDS CubeSat | [https://doi.org/10.17632/8kp25ycf63.1](https://doi.org/10.17632/8kp25ycf63.1) | Battery voltage, current and temperature from 4 small satellites in orbit, from deployment to end of life, recorded during ground station passes. CC BY 4.0. A new application for us: space. |
| VED (Vehicle Energy Dataset) | [https://github.com/gsoh/VED](https://github.com/gsoh/VED) | 27 plug-in hybrid and electric vehicles in Ann Arbor, 2017 to 2018, with pack current, voltage and SOC on trips. Apache 2.0. We will take the whole release, including the 356 combustion and hybrid vehicles. |
| Shenzhen public EV charging (Yang/Autosun) | [https://doi.org/10.17632/c7gg94tmvz.3](https://doi.org/10.17632/c7gg94tmvz.3) | Real charging voltage, current and SOC at 1 minute for 10,154 EVs, 2020 to 2023, each session labeled normal or fault by the charger. CC BY 4.0. There is no vehicle ID, so each charging session is a separate snapshot and one battery cannot be followed over time. |
| VW ID.3 (TUM 2022) | [https://doi.org/10.14459/2022mp1656313](https://doi.org/10.14459/2022mp1656313) | One ID.3, 148 drives up to Dec 2021, with pack current, voltage, temperature and SOC. CC BY 4.0. 2.8 GB. |
| Brazil STAR microgrid | [https://zenodo.org/records/3959739](https://zenodo.org/records/3959739) | 4 off-grid homes in Amazonas, Jan 2018 to Mar 2019, with battery voltage, current, SOC, Ah and cycle counts. CC BY 4.0. |
| Tongji EV rest periods | [https://zenodo.org/records/16868546](https://zenodo.org/records/16868546) | Raw cell voltage, pack current and mean temperature for 4 field EVs, and derived features for about 80 more. CC BY 4.0. |
| Beijing EV | [https://doi.org/10.17632/mm9rvfvmrb.3](https://doi.org/10.17632/mm9rvfvmrb.3) | One battery EV over 12 days in 2018 and 2019, with pack voltage, current and SOC at about 10 seconds. CC BY 4.0. |

## Adjacent, maybe later

These are close to the scope but not a clean fit today. Most are packs or modules tested in a lab, or field data released only as summaries.

| Dataset | Link | Why |
|---|---|---|
| Kyungpook 1,114-EV health | [https://zenodo.org/records/18896326](https://zenodo.org/records/18896326) | Real fleet, but one summary row per vehicle. Raw time series only on request. |
| BMW 225xe PHEV charging records | [https://zenodo.org/records/22941976](https://zenodo.org/records/22941976) | One plug-in hybrid, 892 charging sessions from 2021 to 2026, as summary tables per session with no time series. |
| eVED (extended VED) | [https://github.com/zhangsl2013/eVED](https://github.com/zhangsl2013/eVED) | Adds road and map features to VED, with no new battery data. Data license not stated. |
| Second-life EV microgrid (UC Davis winery) | [https://doi.org/10.17632/mmrz3njn6b.2](https://doi.org/10.17632/mmrz3njn6b.2) | Real deployment in 2019 and 2020, but only string power in kW, with no voltage, current, temperature or SOC. |
| Dalhousie second-life packs | [https://doi.org/10.17632/sbh8pnpnmn.1](https://doi.org/10.17632/sbh8pnpnmn.1) | Lab packs. Six second-life EV packs on a cycler with a frequency regulation profile. |
| Loughborough second-life sweat testing | [https://repository.lboro.ac.uk/articles/online_resource/Long-Term_Sweat_Testing_Data_for_Second-Life_Batteries/28732490](https://repository.lboro.ac.uk/articles/online_resource/Long-Term_Sweat_Testing_Data_for_Second-Life_Batteries/28732490) | Lab modules. Second-life modules on grid-like profiles. |
| eVTOL battery modules | [https://doi.org/10.25447/sit.21301188.v1](https://doi.org/10.25447/sit.21301188.v1) | Lab modules. New modules on eVTOL mission cycles. |
| EPA 48 V mild hybrid pack (A123 pack) | [https://doi.org/10.23719/1435437](https://doi.org/10.23719/1435437) | Lab pack. One new pack on drive cycles, with a pack model. |
| Air-cooled PHEV pack | [https://doi.org/10.5683/SP3/THZTJC](https://doi.org/10.5683/SP3/THZTJC) | Lab pack. Short test of a plug-in hybrid pack. |
| KIT FOBSS modular system | [https://publikationen.bibliothek.kit.edu/1000094469](https://publikationen.bibliothek.kit.edu/1000094469) | Lab pack. Modular battery system on a test bench. |
| OPzS lead-acid bank | [https://zenodo.org/records/17252822](https://zenodo.org/records/17252822) | Lab pack. New six-battery stationary bank. |

## Not openly accessible

These need a login or a paid subscription to download, so others could not reproduce our work from them.

| Dataset | Link | Why |
|---|---|---|
| BMW i3 driving data | [https://doi.org/10.21227/6jr9-5235](https://doi.org/10.21227/6jr9-5235) | IEEE DataPort, login required. |
| EVECS Renault operating data | [https://ieee-dataport.org/documents/ev-energy-consumption-and-speed-profiles-dataset-evecs](https://ieee-dataport.org/documents/ev-energy-consumption-and-speed-profiles-dataset-evecs) | IEEE DataPort, subscription required. |
| NCUE megawatt-scale BESS | [https://doi.org/10.21227/jv22-8x07](https://doi.org/10.21227/jv22-8x07) | IEEE DataPort, login required. Field voltage, current and kWh from a pilot system in Taiwan. |

## Out of scope for now

| Dataset | Link | Tag | Why |
|---|---|---|---|
| LG M50LT drive cycles | [https://doi.org/10.14279/depositonce-21133](https://doi.org/10.14279/depositonce-21133) | EV | Lab cells. |
| McMaster state-of-power | [https://doi.org/10.5683/SP3/RPCWBY](https://doi.org/10.5683/SP3/RPCWBY) | EV, power limits | Lab cells. |
| Empa coin cells | [https://zenodo.org/records/19107066](https://zenodo.org/records/19107066) | Materials research | Lab cells. |
| Oxford grid-trading cells | [https://ora.ox.ac.uk/objects/uuid:9aae61af-2949-49f1-8ad5-6aea448979e5](https://ora.ox.ac.uk/objects/uuid:9aae61af-2949-49f1-8ad5-6aea448979e5) | Grid trading | Lab cells, not a real grid. |
| Stanford-Relyion second-life | [https://osf.io/fns57/](https://osf.io/fns57/) | Second-life | Lab cells. |
| Stanford Energy Control Lab second-life | [https://osf.io/8jnr5/](https://osf.io/8jnr5/) | Second-life | Lab cells. |
| HEV harvested LFP cells | [https://doi.org/10.17632/c7jhyd9c5t.1](https://doi.org/10.17632/c7jhyd9c5t.1) | Second-life, from hybrids | Lab cells. |
| PulseBat | [https://zenodo.org/records/13360631](https://zenodo.org/records/13360631) | Retired cells, pulse tests | Lab cells. |
| Retired Li-ion (USTC LINKE 1.0) | [https://zenodo.org/records/14958140](https://zenodo.org/records/14958140) | Retired cells, capacity sorting | Lab cells. This full release replaces the earlier partial release 14562266. |
| ReLiB-100k | [https://www.kaggle.com/datasets/liuyunlong0621/relib-100k](https://www.kaggle.com/datasets/liuyunlong0621/relib-100k) | Retired cells, capacity sorting | Lab cells, 106,693 of them. Kaggle login required. Same group as LINKE. |
| UK grid supply and demand | [https://doi.org/10.17862/cranfield.rd.12662681](https://doi.org/10.17862/cranfield.rd.12662681) | | No battery data. |
| Residential power and battery | [https://zenodo.org/records/8219786](https://zenodo.org/records/8219786) | | Nameplate ratings only. |
| EV charging sessions, Norway | [https://zenodo.org/records/12730566](https://zenodo.org/records/12730566) | | Session records with no battery signals. |
| Truck electrification | [https://figshare.com/articles/dataset/24421210](https://figshare.com/articles/dataset/24421210) | | CO2 and cost factors only. |
| Kaggle EV thermal runaway | [https://www.kaggle.com/datasets/zara2099/ev-battery-charging-and-thermal-runaway-dataset](https://www.kaggle.com/datasets/zara2099/ev-battery-charging-and-thermal-runaway-dataset) | | Origin unknown, likely synthetic. |
| CH-BatteryGen | [https://github.com/CH-BatteryGen/dataset-warehouse](https://github.com/CH-BatteryGen/dataset-warehouse) | | AI-generated data, and redistribution is not allowed. |
| EV Li-ion fault diagnosis | [https://doi.org/10.17632/t42ynjk936.1](https://doi.org/10.17632/t42ynjk936.1) | | Battery model output, not measurements. |
| APROS IES | [https://zenodo.org/records/14058544](https://zenodo.org/records/14058544) | | Simulation output. |
| 255 W panel and 72 Ah Li-ion | [https://doi.org/10.21227/b1vj-rr95](https://doi.org/10.21227/b1vj-rr95) | | Simulation, according to the author. |
| Energy storage power station | [https://zenodo.org/records/18471156](https://zenodo.org/records/18471156) | | Duplicate of a dataset already in the collection (li2026). |
| Anomaly detection in battery field data | [https://zenodo.org/records/8428302](https://zenodo.org/records/8428302) | | Code only, no data. |

## Thanks

Thanks to msudars (#1) and Battery Data Commons for suggestions.
