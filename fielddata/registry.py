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
    "cloverleaf": _entry("cloverleaf", "Monitoring data second-life battery at Cloverleaf", "https://doi.org/10.5281/zenodo.6373656", None, "Voets and Ben-Al-Lal, pv magazine, 21 Jan 2022", "CC BY 4.0", "Monitoring data second-life battery at Cloverleaf/data", ["Monitoring data 2nd life battery.zip"]),
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

# Package 23, aitio (admitted 2026-10-06 for v1.1). Its files are listed one by one because the ORA record has no
# file API the downloader knows.
_AITIO_RECORD = "https://ora.ox.ac.uk/objects/uuid:e41d3d4c-f74e-4d76-81fd-0caa77ec6cec"
_AITIO_FILES = {  # name: (ORA file id, bytes as listed in the record)
    "GITT_OCV.mpt": ("dw0892b24g", 83771698), "meta_data.csv": ("dtd96k277p", 30337),
    "zip_to_npy.py": ("dxp68kg603", 717), "LICENSE": ("r3b591896q", 1153), "readme.md.txt": ("rkw52j8536", 3076),
    "set_0.zip": ("d3b591882v", 292802485), "set_1.zip": ("d7d278t433", 287351389), "set_2.zip": ("dqj72p736b", 284543563),
    "set_3.zip": ("d8049g533x", 288562736), "set_4.zip": ("df7623c86j", 291836884), "set_5.zip": ("dcz30ps94w", 280380830),
    "set_6.zip": ("dgt54kn28c", 300798725), "set_7.zip": ("drx913q19w", 264814532), "set_8.zip": ("dp8418n53w", 283778513),
    "set_9.zip": ("dfq977v07k", 300694522), "set_10.zip": ("d9g54xh85t", 81975272),
}
PACKAGES.update({
    "aitio": {
        "slug": "aitio",
        "title": "Predicting battery end of life from solar off-grid system field data using machine learning",
        "urls": {"data": "https://doi.org/10.5287/bodleian:aVR4oDV4N", "record": _AITIO_RECORD, "code": None,
                 "paper": "https://doi.org/10.1016/j.joule.2021.11.006",
                 "paper_accepted_manuscript": "https://ora.ox.ac.uk/objects/uuid:8ecbff88-f21a-40da-b36b-532966c81673"},
        "license": "CC BY-NC 4.0",
        # catalog fields, as recorded when aitio was a candidate
        "catalog": {"class": "stationary (off-grid solar home systems)", "chemistry": "lead-acid (VRLA)", "units": 1027,
                    "unit_rating": "12 V, 20 Ah (paper p. 3: nominal voltage 12 V, 6 cells in series, nominal capacity 20 Ah)",
                    "authors": "Aitio, A.; Howey, D. A.", "year": 2021, "venue": "Joule"},
        "data_directory": "Predicting battery end of life from solar off-grid system field data using machine learning/data",
        "data_files": list(_AITIO_FILES),
        # direct file URLs on the record: (name, url, bytes)
        "direct_files": [(name, f"{_AITIO_RECORD}/files/{fid}", size) for name, (fid, size) in _AITIO_FILES.items()],
        # our SHA-256 of each file as fetched on 2026-10-06; the record publishes none, so these are not publisher values
        "own_sha256": {'GITT_OCV.mpt': 'c6741d932e35414a5c30e34e03a03bf9f011ad6eb10c647e8312deff201151a5', 'meta_data.csv': '3561d90a99b3b07dc8b256bae873cae55ce1183fdcf9538cd46466ebd5025490', 'zip_to_npy.py': '7fe486cf8c4b21442ecee7708e6533578581e60f34a250722774b7e0eae4aa72', 'LICENSE': '8f93512c89ad9a4519834b315d7aa089bd3b567c805134043f382a27ada0a607', 'readme.md.txt': '2ebfbb40bd60073dffc6600d32e63b256547aae4ba4d59eb9e61896b28454237', 'set_0.zip': 'dc96006e960663f46a6b7dfe331eb8467d067cd3c57f1b041caaca37f60c3fa7', 'set_1.zip': 'a08ac13f23789ef9d262f5760ebd4021c878b164bda3317679a088f73fbc162b', 'set_2.zip': '2b479e45853358c0f9b1ede5a54b20f3780c8bed7cfc978577d185266e27a5eb', 'set_3.zip': 'e95beb1cd12d57d1655d3675410e452dbbd029f12795a38c3cb69c14a165fa4c', 'set_4.zip': 'b7d80036afef0df71ddbbaa63b7d09045013cd35e55c8a8cbeb3ccbc2018e905', 'set_5.zip': '2502d02227cb2268cb0b83764d3a1121c796a8bf9ce22f4d9996dc5e3d341615', 'set_6.zip': 'f480305949a13a86575b017e7446258b08650114b8b83b6144f5b4625692da38', 'set_7.zip': '541227e780cc47652bfa1292025b4e5fbf61cf52234cb6b61d58d83128cb80cd', 'set_8.zip': 'abc241c3b6b31dc4afb8580c1441916fb8c5f7bf50aff80f53634979c1914eef', 'set_9.zip': '39805140844500eb203d64c4166c4b583a3bfb7a0f6a1ba0cce6c3da05feaae2', 'set_10.zip': '3466d4ecfadab3754432afae518a9abb8384b5b1da780147fb318bd267f849e9'},
        "license_source": _AITIO_RECORD,
        "derived_outputs": "may publish non-commercially, under the release's license",
    },
})

# Candidate packages: loaders and downloads work, but they are not in PACKAGES, so they stay out of the
# collection's totals, tables and dashboard until they are admitted.
_PNNL_EPRI_SYSTEMS = ["Avista", "ENW", "EPRI_LFP1", "EPRI_LFP2", "EPRI_LFP3", "EPRI_NMC1", "EPRI_NMC2", "EPRI_VRF1",
                      "OPALCO", "PSE", "SnoPUDMESA1", "SnoPUDMESA2"]
CANDIDATES: dict = {
    "pnnl_epri": {
        "slug": "pnnl_epri",
        "title": "Grid-Scale BESS Operational Datasets for Battery Modeling Research",
        "urls": {"data": "https://doi.org/10.5281/zenodo.22947521", "code": "https://doi.org/10.5281/zenodo.22947521",
                 # data record only: the paper slot names the context source, as for cloverleaf
                 "paper": "DOE OE peer-review poster, Crawford 2026-05",
                 "context": "https://doepeerreview.sandia.gov/app/uploads/sites/82/2026/05/Crawford_Alasdair_Analytics.pdf"},
        "license": "CC BY 4.0",
        "license_source": "https://zenodo.org/records/22947521",
        "data_directory": "Grid-Scale BESS Operational Datasets for Battery Modeling Research/data",
        # one .feather per system (the unit) and one R script per system, plus _common.R and _epri_channels.R
        "data_files": [f"{s}.feather" for s in _PNNL_EPRI_SYSTEMS] + [f"{s}.R" for s in _PNNL_EPRI_SYSTEMS]
                      + ["_common.R", "_epri_channels.R"],
        "checksum_source": "https://zenodo.org/api/records/22947521 retrieved 2026-10-09",
        "derived_outputs": "may publish",
        "status": "approved for v1.2",
        "catalog": {"application": "grid storage", "chemistry": "LFP, NMC, LMO/NMC, vanadium flow",
                    "units": "12 (11 counted, EPRI_NMC2 is ppl)", "span": "60 days to 5.1 years per system, from 2015"},
    },
}


# On-deck candidates (v1.2 prep, intake phase 1, 2026-10-12): downloaded and checked against the record, no loader
# yet. Like pnnl_epri they stay out of the totals, tables and dashboard counts. "catalog" holds what the record or
# paper states, for the dashboard's On deck section.
def _ondeck(slug, title, data, paper, license, directory, files, catalog, *, code=None, license_source=None,
            checksum_source=None, derived="may publish", context=None):
    # A release without a paper is "data record only", as for cloverleaf and fei_bus. The paper slot then holds a
    # short note naming the context source (cloverleaf: "pv-magazine 2022-01-21"), and urls["context"] links to it.
    urls = {"data": data, "code": code, "paper": paper}
    if context:
        urls["paper"], urls["context"] = context
    return {"slug": slug, "title": title, "urls": urls, "license": license,
            "license_source": license_source or data, "data_directory": f"{directory}/data", "data_files": files,
            "checksum_source": checksum_source, "derived_outputs": derived, "status": "on deck", "catalog": catalog}


_CELL_TO_PACK_FILES = ["ESSL1.zip", "ESSL2.zip", "ESSH1.zip", "PBSL1.zip"] + [f"Pack_field#{i}.zip" for i in range(1, 17)]
CANDIDATES.update({
    "stanford_ev": _ondeck(
        "stanford_ev", "Feedback control bounds variability in large-scale electrochemical systems",
        "https://doi.org/10.25740/yx490wc6642", None, "CC BY-NC-ND 4.0",
        "Feedback control bounds variability in large-scale electrochemical systems",
        ["Field Dataset/**", "Laboratory Dataset/**"],
        {"application": "EV (passenger car)", "chemistry": None, "units": 1, "span": "2021-09 to 2025-04"},
        license_source="https://purl.stanford.edu/yx490wc6642", checksum_source="https://purl.stanford.edu/yx490wc6642.json",
        derived="loader only: no converted or derived data files may be published (CC BY-NC-ND)",
        context=("companion paper on the same vehicle, arXiv 2603.29107 (2026)", "https://arxiv.org/abs/2603.29107")),
    "cell_to_pack": _ondeck(
        "cell_to_pack", "Resolving inter-cell heterogeneity to mitigate degradation amplification in battery packs",
        "https://doi.org/10.5281/zenodo.20132842", None, "CC BY 4.0",
        "Resolving inter-cell heterogeneity to mitigate degradation amplification in battery packs", _CELL_TO_PACK_FILES,
        {"application": "grid storage (field packs) and lab cells and packs", "chemistry": "LFP (field packs), NMC (lab)", "units": "16 field packs of 416 cells", "span": "575 to 617 equivalent full cycles per pack"},
        checksum_source="https://zenodo.org/api/records/20132842",
        code="https://doi.org/10.5281/zenodo.21105057",
        context=("manuscript unpublished, authors' code record, Zenodo 21105057 (2026-07)", "https://github.com/BatICM/cell-to-pack-degradation")),
    "rise_conbat": _ondeck(
        "rise_conbat", "Data-driven State-of-Health prediction for reused batteries in new applications",
        "https://doi.org/10.5281/zenodo.17287096", None, "CC BY 4.0",
        "Data-driven State-of-Health prediction for reused batteries in new applications",
        ["Data-driven State-of-Health prediction for reused batteries in new applications.zip", "Conbat_clean.ipynb",
         "conbat_utils.py", "README.md", "CITATION.cff", "LICENSE"],
        {"application": "stationary storage (second-life)", "chemistry": None, "units": "106 modules from 11 cars", "span": "2023-04 to 2024-11"},
        checksum_source="https://zenodo.org/api/records/17287096",
        context=("project README (RISE, Swedish Energy Agency)", "https://zenodo.org/records/17287096")),
    "birds_cubesat": _ondeck(
        "birds_cubesat", "On-orbit Electrical Power System Dataset of 1U CubeSat constellation for Machine Learning Models",
        "https://doi.org/10.17632/8kp25ycf63.1", "https://doi.org/10.1016/j.dib.2022.108697", "CC BY 4.0",
        "On-orbit Electrical Power System Dataset of 1U CubeSat constellation for Machine Learning Models",
        ["NEPALISAT.xlsx", "RAAVANA.xlsx", "TSURU.xlsx", "UGUISU.xlsx"],
        {"application": "space (1U CubeSat)", "chemistry": None, "units": 4, "span": "2 to 42 ground-station downloads per satellite, 2020 to 2021"},
        checksum_source="https://data.mendeley.com/public-api/datasets/8kp25ycf63/files?folder_id=root&version=1"),
    "ved": _ondeck(
        "ved", "Vehicle Energy Dataset (VED), A Large-scale Dataset for Vehicle Energy Consumption Research",
        "https://github.com/gsoh/VED", "https://doi.org/10.1109/TITS.2020.3035596", "Apache 2.0",
        "Vehicle Energy Dataset (VED), A Large-scale Dataset for Vehicle Energy Consumption Research", ["VED/**"],
        {"application": "EV and PHEV (passenger cars), plus ICE and HEV", "chemistry": None, "units": "384 (static sheets; README says 383)",
         "span": "2017-11 to 2018-11"},
        code="https://github.com/gsoh/VED", license_source="https://github.com/gsoh/VED/blob/master/LICENSE"),
    "shenzhen_charging": _ondeck(
        "shenzhen_charging", "Privacy-preserving collaborative battery fault warning for massive electric vehicles by heterogeneous data from charging stations",
        "https://doi.org/10.17632/c7gg94tmvz.3", "https://doi.org/10.1038/s41467-025-67703-7", "CC BY 4.0",
        "Privacy-preserving collaborative battery fault warning for massive electric vehicles by heterogeneous data from charging stations",
        ["processed_data.xlsx", "processed_data_longer_than_30.xlsx", "Readme.txt"],
        {"application": "EV (public charging)", "chemistry": "LFP, NMC, LMO, LCO, LP", "units": "18,531 charging sessions (no vehicle ID)", "span": "2020-09 to 2024-03"},
        checksum_source="https://data.mendeley.com/public-api/datasets/c7gg94tmvz/files?folder_id=root&version=3"),
    "tum_id3_2022": _ondeck(
        "tum_id3_2022", "Quantifying the state of the art of electric powertrains in battery electric vehicles - Range, efficiency, and lifetime from component to system level of the Volkswagen ID.3",
        "https://doi.org/10.14459/2022mp1656313", "https://doi.org/10.1016/j.etran.2022.100167", "CC BY 4.0",
        "Quantifying the state of the art of electric powertrains in battery electric vehicles - Range, efficiency, and lifetime from component to system level of the Volkswagen ID.3",
        ["Data/Tracks/**", "Data/value_definitions.csv", "Data.sha512"],
        {"application": "EV (passenger car)", "chemistry": None, "units": "1 (same car as tumftm ID1)", "span": "2021-02 to 2021-12, 148 drives"},
        license_source="https://mediatum.ub.tum.de/1656313",
        checksum_source="https://dataserv.ub.tum.de/index.php/s/m1656313 (Data.sha512)"),
    "brazil_star": _ondeck(
        "brazil_star", "Brazil STAR Project Microgrid Monitoring Data",
        "https://doi.org/10.5281/zenodo.3959739", None, "CC BY 4.0",
        "Brazil STAR Project Microgrid Monitoring Data", ["Brazil_STAR_Microgrid_Monitoring.zip"],
        {"application": "off-grid solar (household microgrids)", "chemistry": None, "units": 4, "span": "2018-01 to 2019-02"},
        checksum_source="https://zenodo.org/api/records/3959739",
        context=("Coventry University STAR Energy project page", "https://www.coventry.ac.uk/research/research-directories/completed-projects/2019/star-energy/")),
    "tongji_rest": _ondeck(
        "tongji_rest", "Cross-Domain Feature-Based Battery State-of-Health Estimation from Rest Period for Real-World Electric Vehicles",
        "https://doi.org/10.5281/zenodo.16868546", "https://doi.org/10.1016/j.etran.2025.100471", "CC BY 4.0",
        "Cross-Domain Feature-Based Battery State-of-Health Estimation from Rest Period for Real-World Electric Vehicles",
        ["data.zip"], {"application": "EV", "chemistry": "NMC, LFP", "units": "4 field EVs (raw segments)", "span": "not read (pickled)"},
        checksum_source="https://zenodo.org/api/records/16868546"),
    "beijing_ev": _ondeck(
        "beijing_ev", "Online estimation of driving range for battery electric vehicles based on SOC-segmented actual driving cycle",
        "https://doi.org/10.17632/mm9rvfvmrb.3", "https://doi.org/10.1016/j.est.2022.104091", "CC BY 4.0",
        "Online estimation of driving range for battery electric vehicles based on SOC-segmented actual driving cycle",
        ["2018/**", "2019/**"], {"application": "EV (passenger car)", "chemistry": None, "units": 1, "span": "12 days, 2018-01 to 2019-08"},
        checksum_source="https://data.mendeley.com/public-api/datasets/mm9rvfvmrb (folders/3)"),
})

# v1.2 (2026-10-13): the eleven candidates admitted to the collection. They keep their registry entries, without the
# candidate status; CANDIDATES is left empty for the next intake.
V12_ADMITTED = ["pnnl_epri", "beijing_ev", "brazil_star", "birds_cubesat", "ved", "shenzhen_charging", "tongji_rest",
                "rise_conbat", "tum_id3_2022", "cell_to_pack", "stanford_ev"]
for _name in V12_ADMITTED:
    _entry_v12 = CANDIDATES.pop(_name)
    _entry_v12.pop("status", None)
    PACKAGES[_name] = _entry_v12

# Related sources for releases without a paper (maintainer, 2026-10-16): shown as "related" next to the author citation.
PACKAGES["cloverleaf"]["urls"]["context"] = ("https://www.pv-magazine.com/2022/01/21/economic-and-technical-feasibility-of-a-storage-as-a-"
                                             "service-model-using-second-life-batteries-for-a-commercial-end-user/")
PACKAGES["brazil_star"]["urls"]["paper"] = "Trindade et al. 2022, Environ. Sci. Proc. 15, 16"
PACKAGES["brazil_star"]["urls"]["context"] = "https://doi.org/10.3390/environsciproc2022015016"
PACKAGES["brazil_star"]["urls"]["project_page"] = "https://www.coventry.ac.uk/research/research-directories/completed-projects/2019/star-energy/"
PACKAGES["pnnl_epri"]["urls"]["paper"] = "Crawford 2026, DOE OE peer-review poster"
PACKAGES["fei_bus"]["urls"]["paper"] = None

# v1.2 (maintainer, 2026-10-15): the 35th release, screened 2026-10-15 (reports/checks/v12/bilfinger2025_screen.md). Same
# group and layout as bilfinger2024 and 2026: one "Download all" data.zip from the mediaTUM data server, so its
# download is manual like theirs (the data-server route fetches single files, not data.zip).
PACKAGES["bilfinger2025"] = {
    **_entry("bilfinger2025", "Why we need a standardized SOH measurement procedure for EV battery packs",
             "https://mediatum.ub.tum.de/1765567", "https://github.com/TUMFTM/nature_soh",
             "https://doi.org/10.1038/s44406-025-00010-8", "CC BY 4.0",
             "Why we need a standardized state of health measurement procedure for electric vehicle battery packs - "
             "A proposal for energy- and capacity-based metrics/data", ["data.zip"]),
    "license_source": "https://mediatum.ub.tum.de/1765567",
    "derived_outputs": "may publish",
    "checksum_source": "checksums.sha512 inside data.zip (publisher, zip-internal); mediaTUM 1765567",
}
PACKAGES["bilfinger2025"]["urls"]["dataset_doi"] = "https://doi.org/10.14459/2024mp1765567"
PACKAGES["bilfinger2025"]["urls"]["preprint"] = "https://arxiv.org/abs/2508.15517"

def metadata(package: str) -> dict:
    """Registry entry for an admitted package or a candidate."""
    if package in PACKAGES:
        return PACKAGES[package]
    if package in CANDIDATES:
        return CANDIDATES[package]
    raise KeyError(f"unknown package {package!r}")
