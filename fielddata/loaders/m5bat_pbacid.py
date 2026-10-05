"""Raw loader for the M5BAT Pb1 flooded lead-acid archive (unit Pb1).

The released parquet files are the publisher's processed export, not raw manufacturer exports: per the paper
(Zurmuehlen et al., Energies 19 (2026) 4141, Sec. 3.2.1 and 3.7) they were quality-filtered, converted to UTC,
deduplicated, and gaps shorter than 5 s were forward-filled, with no flag on filled rows. See the schema note.
"""
import os
import tempfile
import zipfile

import pandas as pd
import pyarrow.parquet as pq

from fielddata.config import data_root
from fielddata.registry import PACKAGES

_SOURCES = {"bms": "BMS", "bsc": "BSC"}
_CHEMISTRY = "flooded lead-acid"
# Description_File.pdf defines the BMS communication-error codes for these four BMS columns only, and 2345
# alone for the SoC. Elsewhere 2345 or 2356 can be a real value (cumulative counters pass through them).
_SENTINELS = {
    "power_dc_W_bms": (2345, 2356),
    "current_A_bms": (2345, 2356),
    "voltage_bat_V_bms": (2345, 2356),
    "soc_pct_bms": (2345,),
}
# The on-board BSC AC energy counters were "uninitialised 0xFFFF before 2022" (Description_File.pdf,
# energy_charge_recon_kWh_bsc notes; paper Sec. 3.3.2). In 2017-2021 they hold 4,294,967,295 (0xFFFFFFFF) or
# 4,294,902,760 (high word 0xFFFF), about 4.3 billion kWh, which cannot be a measurement.
_UNINITIALISED_COUNTERS = ("energy_charge_kWh_bsc", "energy_discharge_kWh_bsc")
_HIGH_WORD_FFFF = 0xFFFF0000


def _clean_sentinels(frame):
    count = 0
    for column, codes in _SENTINELS.items():
        if column not in frame.columns:
            continue
        hit = frame[column].isin(codes)
        n = int(hit.sum())
        if n:
            frame[column] = frame[column].astype(float).mask(hit)
            count += n
    for column in _UNINITIALISED_COUNTERS:
        if column not in frame.columns:
            continue
        hit = frame[column] >= _HIGH_WORD_FFFF
        n = int(hit.sum())
        if n:
            frame[column] = frame[column].astype(float).mask(hit)
            count += n
    return count


def _archive_path():
    package = PACKAGES["m5bat-pbacid"]
    return data_root() / package["data_directory"] / package["data_files"][0]


def _members():
    with zipfile.ZipFile(_archive_path()) as archive:
        return archive.infolist()


def _member_year(name, prefix):
    # "Exide1_BMS_2019.parquet" -> 2019
    stem = name.removeprefix(f"Exide1_{prefix}_").removesuffix(".parquet")
    return int(stem)


def _read_member(archive, member, columns=None):
    """Extract one archive member to a system temp file, read it (optionally only some columns), then discard the temp file.

    The ``timestamp_utc`` index is always kept (``use_pandas_metadata``).
    """
    with tempfile.TemporaryDirectory() as scratch:
        archive.extract(member, scratch)
        path = os.path.join(scratch, member.filename)
        if columns is None:
            return pq.read_table(path).to_pandas()
        return pq.read_table(path, columns=list(columns), use_pandas_metadata=True).to_pandas()


def systems():
    """Return one released row for the Pb1 unit: chemistry, per-source years, files with bytes."""
    infos = _members()
    files = [{"file": info.filename, "bytes": info.file_size} for info in infos]
    rows = []
    for source_id, prefix in _SOURCES.items():
        years = sorted(_member_year(info.filename, prefix) for info in infos if info.filename.startswith(f"Exide1_{prefix}_"))
        rows.append({
            "unit": "Pb1",
            "chemistry": _CHEMISTRY,
            "source": source_id,
            "years": years,
            "files": files,
        })
    return pd.DataFrame(rows)


def load(source="bms", years=None, clean=False, columns=None):
    """Load one source's parquet years, indexed by the UTC timestamp, with codebook column names.

    ``columns`` reads only the named columns (a full BSC year is ~30 million rows by 23 columns).
    Signs follow the codebook: positive power and current = discharging, negative = charging. ``soc_pct_bms``
    is the BMS's own estimate. ``clean=True`` masks (sets to NaN) only the codebook's BMS communication-error
    codes (2345 and 2356 in power_dc_W_bms, current_A_bms, voltage_bat_V_bms; 2345 in soc_pct_bms) and the
    uninitialised BSC energy counters (values >= 0xFFFF0000 in energy_charge_kWh_bsc and
    energy_discharge_kWh_bsc, present in 2017-2021); no rows are dropped.
    """
    if source not in _SOURCES:
        raise ValueError("source must be 'bms' or 'bsc'")
    prefix = _SOURCES[source]
    with zipfile.ZipFile(_archive_path()) as archive:
        available_years = sorted(_member_year(info.filename, prefix) for info in archive.infolist() if info.filename.startswith(f"Exide1_{prefix}_"))
        requested_years = sorted(years) if years is not None else available_years
        missing = sorted(set(requested_years) - set(available_years))
        if missing:
            raise ValueError(f"years not present for {source}: {missing}")
        frames = []
        for year in requested_years:
            member = archive.getinfo(f"Exide1_{prefix}_{year}.parquet")
            frames.append(_read_member(archive, member, columns))
    frame = pd.concat(frames).sort_index() if len(frames) > 1 else frames[0]
    masked_value_count = _clean_sentinels(frame) if clean else 0
    frame.attrs = {
        "source": source,
        "years": requested_years,
        "n_rows": len(frame),
        "codebook_file": "codebook.csv",
        "clean": clean,
        "masked_value_count": masked_value_count,
        "columns": list(columns) if columns is not None else None,
    }
    return frame


def preview(source="bms", year=None, rows=1000):
    """The first ``rows`` rows of one source-year parquet, as released, without reading the whole year."""
    if source not in _SOURCES:
        raise ValueError("source must be 'bms' or 'bsc'")
    with zipfile.ZipFile(_archive_path()) as archive:
        with archive.open(f"Exide1_{_SOURCES[source]}_{int(year)}.parquet") as member:
            parquet = pq.ParquetFile(member)
            return next(parquet.iter_batches(batch_size=rows)).to_pandas().head(rows)
