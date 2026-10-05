# Public battery field data

[![CI](https://github.com/Astrolabe-Analytics/public-battery-field-data/actions/workflows/ci.yml/badge.svg)](https://github.com/Astrolabe-Analytics/public-battery-field-data/actions/workflows/ci.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23150592.svg)](https://doi.org/10.5281/zenodo.23150592)

This repository provides a consistent Python interface, verification notebooks, and reproducible summary tables for 22 public battery field-data packages. Raw publisher files are not redistributed.

Python 3.12 or newer is required (the pinned environment is tested on 3.12, 3.13 and 3.14, so it also runs in Google Colab); the Python that comes with macOS is too old.

First get the code, either with git:

```
git clone https://github.com/Astrolabe-Analytics/public-battery-field-data.git
cd public-battery-field-data
```

or, without git, with Code > Download ZIP on the GitHub page, then unzip it and open a terminal in that folder. From the repository folder, make a virtual environment, then install the pinned environment and this package:

```
python3 -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pip install -e .
```

Every dependency installs from a prebuilt wheel on macOS (Intel and Apple Silicon), Windows and Linux. Downloads use the `certifi` certificates, so Python from the python.org macOS installer works without running its "Install Certificates" command.

## What's in this repo

- `fielddata/`: the Python package: one loader per release, the registry, download (`fetch`), checks (`verify`, `doctor`) and the package facts.
- `notebooks/`: the quick start and one notebook per release.
- `docs/`: the dashboard (`docs/dashboard/`), the paper's tables and figures (`docs/descriptor/`) and the quick-start guide.
- `reports/`: generated outputs: headline totals, Table 1, facts and checks behind each number, the verification log and the license audit.
- `scripts/`: rebuild the published numbers and tables (`rebuild.py`), regenerate facts, notebooks and the dashboard, and the data checks.
- `tests/`: the test suite (`python -m pytest`), on synthetic data, so it needs no downloads.
- `config/`: the example settings file for your data folder.

## Get the data

Start with [`reports/TABLE1_access.md`](reports/TABLE1_access.md). It links each paper, public data record, and code release, and records the package license, held size, file count, and checksum status.

Choose where the data goes. Copy the example settings file to the ignored `config/local.toml`:

```
cp config/local.example.toml config/local.toml      # on Windows: copy config\local.example.toml config\local.toml
```

Then open `config/local.toml` and replace the whole placeholder path `PATH_TO_PUBLIC_BATTERY_DATA_HOLDINGS` with a folder outside the repository, keeping the quotes, for example `data_root = "~/battery-data"`. Without this file, downloads go to `./data` inside the repository. Then `python -m fielddata.fetch <release>` downloads a release, or prints the steps for one that needs a browser. Run `python -m fielddata.verify <release>` to compare the files with publisher checksums, or record our own hash where no publisher checksum exists. It writes its log to `reports/local/`, which git ignores, and it fails if the release has no files yet.

How each release downloads, as of October 2026 (`python -m fielddata.fetch --list` shows the same):

- One command (`python -m fielddata.fetch <release>`): cao, cloverleaf, deng, evbattery, flashbattery-agv, li2026, rwth-home, schaeffer, tsukuba, tumftm, xie, zhang2023.
- Manual, in a web browser (the fetch command prints the steps): bilfinger2024, bilfinger2026, changan, fei_bus, ku_leuven_bev, m5bat-2023-04, m5bat-pbacid, rwth-android, zhou2026.
- Partly manual: ppl. The command downloads the 0.95 GB on GitHub. The 66.6 GB of cell-level data is on a Box share linked from the repository's `Cell_Level_Data` file; the command prints the link as a manual step. The ppl loader does not read the cell-level data.

## Rebuild the published numbers

Run `python scripts/rebuild.py` from the repository root. It regenerates `reports/TOTALS.md` and `reports/TABLE1_access.md` from committed package facts, registry metadata, and the saved verification log. Repeated runs are deterministic. Stated and computed quantities remain separate, and provisional values are identified.

## Check your setup

Run `python -m fielddata.doctor` (or name releases: `python -m fielddata.doctor rwth-home tumftm`). It checks that the data folder is set, that each release's files are where the loaders expect them and complete, and that a RAR reader is installed for the three RAR releases. A file whose size, or for files up to 1 GB checksum, differs from the publisher's is reported as incomplete, not ready. A release folder saved under another name is found and named, so you can rename it instead of downloading again. Every problem comes with what to do. It only reads; it never downloads or moves anything.

## Quick start

Open [`notebooks/quickstart.ipynb`](notebooks/quickstart.ipynb) with `jupyter lab notebooks/quickstart.ipynb` and run it from the top (Run > Restart Kernel and Run All Cells). It also runs in Google Colab, where it installs the package and downloads the chosen release itself. Set one line to any release name and it lists the units, loads a small slice of one unit and plots a signal. It works for all 22 releases; the preset slices are in `fielddata/quickstart.py`. [`docs/QUICKSTART.md`](docs/QUICKSTART.md) covers installing and downloading a first release. Every release has a basic notebook in `notebooks/`. For a worked example of a release published without column names, units or timestamps, read [`notebooks/cao_in_depth.ipynb`](notebooks/cao_in_depth.ipynb), next to the basic [`notebooks/cao.ipynb`](notebooks/cao.ipynb).

For a one-page overview of all 22 releases (the paper's Tables 1 and 2 in one sortable table, plus how to download and load each release), open [`docs/dashboard/index.html`](docs/dashboard/index.html). It is generated by `python scripts/make_dashboard.py`.

## Rebuilding the facts on a clean machine

The EVBattery facts need the Zhang 2023 / EVBattery overlap result, so on a fresh checkout run, from `scripts/facts/`:

1. `python _overlap_scan.py sig <package> <archive>` for each of the six archives (zhang2023: battery_brand1/2/3.tar.gz; evbattery: battery_dataset1/2/3.tar.gz)
2. `python _overlap_scan.py compare`
3. `python _overlap_scan.py refine`
4. `python _overlap_scan.py tolerance`
5. `python _overlap_scan.py pairs`
6. then the package scripts (`python evbattery.py --force` and the others), `python build.py`, and `python scripts/rebuild.py` from the repository root.

## Loaders and notebooks

Use `fielddata.load("<package>", ...)` to load a supported package and `fielddata.systems("<package>")` to list its systems. Loaders preserve released values by default. Package notebooks document file structure, signals, checks and paper comparisons. Each loader's `fielddata/loaders/<package>_SCHEMA.md` explains its columns, units and sentinel codes.

## Licenses

Repository code is MIT licensed in [`LICENSE`](LICENSE). Repository-authored text, tables, and figures are CC BY 4.0 under [`LICENSE-docs`](LICENSE-docs). Third-party datasets and papers retain their own terms; package-specific licenses and source URLs are recorded in `fielddata/registry.py` and Table 1.

Derived outputs (previews, facts, profiles and notebooks made from a release) follow that release's terms. This repository is non-commercial: free, public and academic, with no revenue. Outputs derived from the four non-commercial releases (changan and evbattery, CC BY-NC-SA 4.0; schaeffer and tumftm, CC BY-NC 4.0) are published for non-commercial use only, under the release's license. Two releases (ppl and zhou2026) state no license for their data; their previews and facts are published by the maintainer's decision, and the dashboard says so under each preview. [`reports/DERIVED_LICENCE_AUDIT.md`](reports/DERIVED_LICENCE_AUDIT.md), written by `python scripts/license_audit.py`, lists every tracked derived file with its release's terms.

## Citation

Cite this repository as: Masse, R. (2026). Public Battery Field Data. Zenodo. https://doi.org/10.5281/zenodo.23150592 (this DOI covers all versions; v1.0.0 is https://doi.org/10.5281/zenodo.23150593). Citation metadata is provided in [`CITATION.cff`](CITATION.cff). Cite the original dataset and paper alongside this repository when using a package.
