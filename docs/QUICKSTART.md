# Five-minute quick start

For any release, open `notebooks/quickstart.ipynb`: set one line to the release name and run it from the top (it also runs in Google Colab). This page walks through the same steps by hand for one small release.

This example downloads a small public package from its original Zenodo record, checks it against the publisher checksum, loads the CSV, and draws one battery trace. Raw publisher files stay outside the repository.

## 1. Install from GitHub

```bash
python -m pip install "git+https://github.com/Astrolabe-Analytics/public-battery-field-data.git"
```

The GitHub repository must be public before this command works without authentication.

## 2. Fetch the example package

Choose a folder for downloaded data and run:

```bash
python -m fielddata.fetch flashbattery-agv --to ./data
```

The command asks Zenodo for every file in the data record, skips papers, resumes an interrupted `.part` file, and checks `dataset.csv` against the publisher MD5 recorded in `fielddata/reference_checksums.csv`. A successful run prints `matched`.

The CSV is saved below the package directory recorded in `fielddata/registry.py`:

```text
data/Automated Battery Power Fade Estimation for Fast Charge and Discharge Operations/data/dataset.csv
```

## 3. Load the released table

```python
from pathlib import Path
import pandas as pd

csv_path = Path("data/Automated Battery Power Fade Estimation for Fast Charge and Discharge Operations/data/dataset.csv")
data = pd.read_csv(csv_path, parse_dates=["date"])
print(data.shape)
print(data.columns.tolist())
```

The released columns include a battery identifier, date, cycle duration, cumulative discharge, and minimum and maximum temperature.

## 4. Plot one clear signal

```python
import matplotlib.pyplot as plt

battery = data["battery"].dropna().iloc[0]
daily = (
    data.loc[data["battery"] == battery]
    .groupby("date", as_index=False)["cycletime"]
    .median()
)
daily["cycle_hours"] = daily["cycletime"] / 3600

ax = daily.plot(x="date", y="cycle_hours", figsize=(10, 4), legend=False)
ax.set(title=f"{battery}: daily median cycle duration", xlabel="Date", ylabel="Cycle duration (hours)")
plt.tight_layout()
plt.show()
```

This is a descriptive operating trace, not a state-of-health diagnosis. Changes can reflect duty, controls, temperature, or battery condition.

## Fetch any package

List all packages and their download route:

```bash
python -m fielddata.fetch --list
```

Then replace the package name:

```bash
python -m fielddata.fetch <package> --to ./data
```

Zenodo and Figshare records are resolved through their public APIs. GitHub records are fetched from repository and Git LFS URLs. For Box, OneDrive, institutional portals, and other records without a stable public file API, the command prints numbered manual steps, expected file names, and recorded sizes instead of scraping the site.

When `--to` is omitted, the downloader uses `data_root` from ignored `config/local.toml`; if that setting is absent, it uses `./data`. Package loaders use the configured `data_root`, preserve released values by default, and are described in each loader's `fielddata/loaders/<package>_SCHEMA.md`.
