"""Public metadata for supported data packages."""
PACKAGES = {
    "cao": {
        "slug": "cao",
        "title": "Model-Constrained Deep Learning for Online Fault Diagnosis in Li-ion Batteries over Stochastic Conditions",
        "urls": {
            "data": "https://doi.org/10.5281/zenodo.10656500",
            "code": "https://doi.org/10.5281/zenodo.14555916",
            "paper": "https://doi.org/10.1038/s41467-025-56832-8",
        },
        "license": "CC BY 4.0",
        "data_directory": "Model-Constrained Deep Learning for Online Fault Diagnosis in Li-ion Batteries over Stochastic Conditions/data",
        "archives": {
            "DTI.zip": "400135e26d8bac65cc171e63f71fd5dd",
            "GIS.zip": "2b4d5f9d0d045bbe5bb0318ea84f7e7e",
            "QAS_1.zip": "a3d3a182c7c82df26073a53f698148c8",
            "QAS_2.zip": "9183ff01f6cf3e187716ca3a2d7f6b53",
            "QAS_3.zip": "7cb6410cac2c44890eaccd9d594887bf",
            "QAS_4.zip": "d138ef98e2fb77c12afc88a6043e3be8",
            "QAS_5.zip": "f420b38bab7aca514ab834cbfa0010b8",
        },
        "checksum_source": "https://zenodo.org/records/10656500 retrieved 2026-09-10",
    }
}


def _entry(slug, title, data, code, paper, license, directory, files):
    return {
        "slug": slug, "title": title,
        "urls": {"data": data, "code": code, "paper": paper},
        "license": license, "data_directory": directory, "data_files": files,
        "source": f"battery-field-data/readmes/{slug}/README.txt",
    }


PACKAGES.update({
    "bilfinger2024": _entry("bilfinger2024", "Battery pack diagnostics for EVs: Transfer of differential voltage and incremental capacity", "https://mediatum.ub.tum.de/1737452", "https://github.com/TUMFTM/Battery-Pack-Diagnostics", "https://doi.org/10.1016/j.etran.2024.100356", "CC BY 4.0", "Battery pack diagnostics for electric vehicles - Transfer of differential voltage and incremental capacity analysis from cell to vehicle level/data", ["data.zip"]),
    "bilfinger2026": _entry("bilfinger2026", "Battery pack diagnostics for EVs: Robustness of SOH and differential voltage", "https://mediatum.ub.tum.de/1840112", "https://github.com/TUMFTM/EV_DVA_robustness", "https://doi.org/10.1016/j.etran.2026.100589", "CC BY 4.0", "Battery pack diagnostics for electric vehicles - Robustness of the state of health measurement and differential voltage analysis at the vehicle level/data", ["data.zip"]),
    "changan": _entry("changan", "Multi-modal framework for battery SOH evaluation using open-source EV data", "http://ivstskl.changan.com.cn/?p=2697", "https://github.com/HoraceLiu1010/Multi-modal-SOH-estimation", "https://doi.org/10.1038/s41467-025-56485-7", "CC BY-NC-SA 4.0", "Multi-modal framework for battery state of health evaluation using open-source electric vehicle data/data", ["raw/RAW_DATA.z01", "raw/RAW_DATA.zip"]),
    "cloverleaf": _entry("cloverleaf", "Monitoring data second-life battery at Cloverleaf", "https://doi.org/10.5281/zenodo.6373656", None, "pv-magazine 2022-01-21", "CC BY 4.0", "Monitoring data second-life battery at Cloverleaf/data", ["Monitoring data 2nd life battery.zip"]),
    "deng": _entry("deng", "Prognostics of battery capacity based on charging data for on-road vehicles", "https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles", "https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles", "https://doi.org/10.1016/j.apenergy.2023.120954", "MIT (repository)", "Prognostics of battery capacity based on charging data and data-driven methods for on-road vehicles/data", ["#1.rar through #20.rar"]),
    "evbattery": _entry("evbattery", "EVBattery - Large-Scale EV Dataset for Battery Health & Capacity", "https://doi.org/10.6084/m9.figshare.23301881", "https://github.com/thinkenergy/dynamic_vae", "arXiv:2201.12358", "CC BY-NC-SA 4.0", "EVBattery - A Large-Scale Electric Vehicle Dataset for Battery Health and Capacity Estimation/data", ["battery_dataset1.tar.gz", "battery_dataset2.tar.gz", "battery_dataset3.tar.gz"]),
    "fei_bus": _entry("fei_bus", "Real EV dataset - Commercial Electric Buses", "https://doi.org/10.17632/j9ky68gnd3.3", None, "Mendeley", "CC BY 4.0", "Real EV dataset - Commercial Electric Buses/data", ["vin1.csv", "vin5.csv", "vin12.csv", "vin19.csv"]),
    "flashbattery-agv": _entry("flashbattery-agv", "Automated Battery Power Fade Estimation for Fast Charge/Discharge", "https://zenodo.org/records/7748947", None, "https://doi.org/10.1109/CCNC51644.2023.10060391", "CC BY 4.0", "Automated Battery Power Fade Estimation for Fast Charge and Discharge Operations/data", ["dataset.csv"]),
    "ku_leuven_bev": _entry("ku_leuven_bev", "Unveiling Energy Dynamics of Battery Electric Vehicle Using High-Resolution Data", "https://doi.org/10.48804/8KPDTW", "https://github.com/mayasko/BEV-data", "https://doi.org/10.1038/s41597-025-06148-5", "CC BY 4.0", "Unveiling Energy Dynamics of Battery Electric Vehicle Using High-Resolution Data/data", ["doi-10.48804-8kpdtw.zip"]),
    "li2026": _entry("li2026", "Large language model-based fault diagnosis for Li-ion batteries in cloud-edge systems", "https://zenodo.org/records/18471156", "https://github.com/Cuadger/DDP-based-dowm-sampling", "https://doi.org/10.1016/j.xcrp.2026.103210", "CC BY 4.0", "Large language model-based fault diagnosis for lithium-ion batteries in cloud-edge systems/data", ["BatteryData.zip"]),
    "m5bat-2023-04": _entry("m5bat-2023-04", "M5BAT Large-Scale Battery Storage System: Evaluation Operation Report 04/2023", "https://publications.rwth-aachen.de/record/985923", None, "https://doi.org/10.18154/RWTH-2024-04895", "CC BY 4.0", "M5BAT Large-Scale Battery Storage System Dataset - Evaluation Operation Report 04-2023/data", ["M5BAT_04-2023_RAW.zip"]),
    "m5bat-pbacid": _entry("m5bat-pbacid", "Operational Degradation of Flooded Lead-Acid Under FCR: Long-Term Evidence", "https://publications.rwth-aachen.de/record/1038622", None, "https://doi.org/10.3390/en19174141", "CC BY 4.0", "Operational Degradation of Flooded Lead-Acid Storage Under Frequency Containment Reserve/data", ["Full_Dataset_M5BAT_Battery_Unit_Pb1.zip"]),
})
PACKAGES["m5bat-pbacid"]["urls"]["dataset_doi"] = "https://doi.org/10.18154/RWTH-2026-06637"
PACKAGES["m5bat-pbacid"]["paper_citation"] = "Zurmühlen, Koltermann, Sauer, \"Operational Degradation of Flooded Lead-Acid Storage Under Frequency Containment Reserve\", Energies 19(17) 4141 (2026), doi:10.3390/en19174141"
PACKAGES["m5bat-pbacid"]["checksum_source"] = "RWTH record page https://publications.rwth-aachen.de/record/1038622, checked manually 2026-09-10"
PACKAGES.update({
    "ppl": _entry("ppl", "Utility-Scale Battery Energy Storage Systems - Field Pilot Unit Experience", "https://github.com/PPLResearch/BESS-Analysis", "https://github.com/PPLResearch/BESS-Analysis", "https://doi.org/10.1109/ACCESS.2026.3693606", "unstated", "Utility-Scale Battery Energy Storage Systems - Field Pilot Unit Experience, Analysis, and Review of Technological Advancements/data", ["BESS-Analysis/**"]),
    "rwth-android": _entry("rwth-android", "Battery Cell Field Data of Multiple Mobile Android Devices", "https://publications.rwth-aachen.de/record/1002905", None, "https://doi.org/10.18154/RWTH-2025-00754", "CC BY 4.0", "Battery Cell Field Data of Multiple Mobile Android Devices/data", ["Dataset_from_Mobile_Battery_Data_Explorer_2026-04.zip"]),
    "rwth-home": _entry("rwth-home", "Multi-year field measurements of home storage systems & capacity estimation", "https://doi.org/10.5281/zenodo.12091223", "https://doi.org/10.5281/zenodo.12091223", "https://doi.org/10.1038/s41560-024-01620-9", "CC BY 4.0", "Multi-year field measurements of home storage systems and their use in capacity estimation/data", ["Data_ID_01.zip through Data_ID_21.zip", "Metadata_and_Code.zip"]),
    "schaeffer": _entry("schaeffer", "Gaussian process-based online health monitoring and fault analysis from field data", "https://zenodo.org/records/13715694", "https://github.com/JoachimSchaeffer/BattGP", "https://doi.org/10.1016/j.xcrp.2024.102258", "CC BY-NC 4.0", "Gaussian process-based online health monitoring and fault analysis from field data/data", ["field_data.zip"]),
    "tsukuba": _entry("tsukuba", "Multiyear microgrid data from a research building in Tsukuba, Japan", "https://springernature.figshare.com/articles/dataset/7403954", None, "https://doi.org/10.1038/sdata.2019.20", "CC0 1.0", "Multiyear microgrid data from a research building in Tsukuba, Japan/data", ["294ecef46cba01f6392560efe6c78a28.zip"]),
    "tumftm": _entry("tumftm", "Lab-to-field gap in battery aging: Mismatch of operating conditions", "https://github.com/tumftm/electric-vehicle-uds-dataset", "https://github.com/tumftm/electric-vehicle-uds-dataset", "https://doi.org/10.1016/j.etran.2025.100518", "CC BY-NC 4.0", "Lab-to-field gap in battery aging studies - Mismatch of operating conditions between laboratory environments and real-world automotive applications/data", ["CUP3.parquet", "ID1.parquet", "electric-vehicle-uds-dataset/**"]),
    "xie": _entry("xie", "Realistic multi-fault diagnostics of millions-scale Li-ion batteries with rapid unsupervised learning", "https://zenodo.org/records/18328701", "https://zenodo.org/records/18327925", "https://doi.org/10.1016/j.xcrp.2026.103154", "CC BY 4.0 (data); MIT (code)", "Realistic multi-fault diagnostics of millions-scale Li-ion batteries with rapid unsupervised learning/data", ["DataForPub.rar"]),
    "zhang2023": _entry("zhang2023", "Realistic fault detection of Li-ion battery via dynamical deep learning approach", "https://doi.org/10.6084/m9.figshare.23659323", "https://github.com/962086838/Battery_fault_detection", "https://doi.org/10.1038/s41467-023-41226-5", "CC BY 4.0", "Realistic fault detection of Li-ion battery via dynamical deep learning/data", ["battery_brand1.tar.gz", "battery_brand2.tar.gz", "battery_brand3.tar.gz"]),
    "zhou2026": _entry("zhou2026", "Quantifying the impact of cell-to-cell inconsistency on EV battery degradation & utilization", "https://1drv.ms/u/c/909aeacce295a32a/IQCsGxZgHovYTqJEXhfqRIIZAWASy12k6Urytil7VPa0LJY?e=ISLuvO", "https://github.com/Rico-dicp/Ev-battery-cell-to-cell-inconsistency", "https://doi.org/10.1038/s41560-026-02131-5", "unstated (data); MIT (code)", "Quantifying the impact of cell-to-cell inconsistency on electric vehicle battery degradation and utilization/data", ["Vehicle data.zip"]),
})

_LICENSE_SOURCES = {
    "cao": "https://zenodo.org/records/10656500",
    "bilfinger2024": "https://mediatum.ub.tum.de/1737452",
    "bilfinger2026": "https://mediatum.ub.tum.de/1840112",
    "changan": "http://ivstskl.changan.com.cn/?p=2697",
    "cloverleaf": "https://doi.org/10.5281/zenodo.6373656",
    "deng": "https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles",
    "evbattery": "https://doi.org/10.6084/m9.figshare.23301881",
    "fei_bus": "https://doi.org/10.17632/j9ky68gnd3.3",
    "flashbattery-agv": "https://zenodo.org/records/7748947",
    "ku_leuven_bev": "https://doi.org/10.48804/8KPDTW",
    "li2026": "https://zenodo.org/records/18471156",
    "m5bat-2023-04": "https://publications.rwth-aachen.de/record/985923",
    "m5bat-pbacid": "https://publications.rwth-aachen.de/record/1038622",
    "ppl": "https://github.com/PPLResearch/BESS-Analysis",
    "rwth-android": "https://publications.rwth-aachen.de/record/1002905",
    "rwth-home": "https://doi.org/10.5281/zenodo.12091223",
    "schaeffer": "https://zenodo.org/records/13715694",
    "tsukuba": "https://springernature.figshare.com/articles/dataset/7403954",
    "tumftm": "https://github.com/tumftm/electric-vehicle-uds-dataset",
    "xie": "https://zenodo.org/records/18328701",
    "zhang2023": "https://doi.org/10.6084/m9.figshare.23659323",
    "zhou2026": "https://1drv.ms/u/c/909aeacce295a32a/IQCsGxZgHovYTqJEXhfqRIIZAWASy12k6Urytil7VPa0LJY?e=ISLuvO",
}

for _slug, _source in _LICENSE_SOURCES.items():
    PACKAGES[_slug]["license_source"] = _source
    _license = PACKAGES[_slug]["license"].upper()
    if "UNSTATED" in _license:
        PACKAGES[_slug]["derived_outputs"] = "published by maintainer decision; no license stated"
    elif "-NC" in _license:
        PACKAGES[_slug]["derived_outputs"] = "may publish non-commercially, under the release's license"
    else:
        PACKAGES[_slug]["derived_outputs"] = "may publish"