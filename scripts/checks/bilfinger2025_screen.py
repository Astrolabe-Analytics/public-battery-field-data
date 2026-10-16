"""Screen Bilfinger et al. 2025 (npj Clean Energy, mediaTUM 1765567) against bilfinger2024 and bilfinger2026.

What it does: verifies the downloaded data.zip members against the release's own checksums.sha512, lists each 2025
vehicle file (rows, columns, date span, voltage range), and compares the vehicles the 2025 release shares by name with
the two releases already in the collection (five Cupra Born by number, the VW ID.3, the Tesla Model 3): identical
length and values on shared columns, or overlapping calendar dates. Raw values, no cleaning. Feather files only; the
2024 and 2026 releases are read through their loaders.

Reads: the bilfinger2025 package's data.zip on the SSD (the screening copy, moved there on admission), and bilfinger2024 and
bilfinger2026 through fielddata.
Writes: reports/checks/v12/bilfinger2025_screen.csv (one row per 2025 file) and prints the comparisons.

Run:
    python scripts/checks/bilfinger2025_screen.py
"""
from __future__ import annotations

import hashlib
import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import fielddata  # noqa: E402

ZIP = Path("D:/Public Battery Data/Why we need a standardized state of health measurement procedure for electric vehicle battery packs"
           " - A proposal for energy- and capacity-based metrics/data/data.zip")  # the screening copy, moved into the package on admission
OUT = ROOT / "reports" / "checks" / "v12" / "bilfinger2025_screen.csv"


def verify(z: zipfile.ZipFile) -> tuple[int, int]:
    manifest = z.read("m1765567/checksums.sha512").decode("utf-8")
    ok = total = 0
    for line in manifest.splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        name = name.strip().lstrip("*").replace("\\", "/").lstrip("./")  # the manifest uses Windows separators
        member = next((m for m in z.namelist() if m.endswith(name)), None)
        total += 1
        if member and hashlib.sha512(z.read(member)).hexdigest() == digest.lower():
            ok += 1
        elif member is None:
            print("not in zip:", name)
    return ok, total


def describe(name: str, df: pd.DataFrame) -> dict:
    vcol = next((c for c in ("U", "V", "voltage", "pack_voltage", "hv_battery_voltage") if c in df.columns), None)
    dcol = next((c for c in ("date", "datetime", "timestamp") if c in df.columns), None)
    row = {"file": name, "rows": len(df), "columns": len(df.columns), "voltage_column": vcol,
           "v_min": float(df[vcol].min()) if vcol else np.nan, "v_max": float(df[vcol].max()) if vcol else np.nan,
           "date_first": str(pd.to_datetime(df[dcol]).min()) if dcol else "", "date_last": str(pd.to_datetime(df[dcol]).max()) if dcol else "",
           "cell_voltage_columns": sum(c.startswith("cell_voltage") for c in df.columns)}
    return row


def compare(a: pd.DataFrame, b: pd.DataFrame) -> str:
    shared = [c for c in a.columns if c in b.columns and pd.api.types.is_numeric_dtype(a[c]) and pd.api.types.is_numeric_dtype(b[c])]
    if not shared:
        return "no shared numeric columns"
    if len(a) == len(b):
        same = [c for c in shared if np.allclose(a[c].to_numpy(float), b[c].to_numpy(float), equal_nan=True)]
        return f"same length {len(a)}, identical on {len(same)} of {len(shared)} shared numeric columns"
    v = next((c for c in ("U", "V") if c in shared), None)
    if v:  # different length: is one series contained in the other?
        sa, sb = a[v].to_numpy(float), b[v].to_numpy(float)
        short, long_ = (sa, sb) if len(sa) < len(sb) else (sb, sa)
        k = min(len(short), 200)
        window = np.lib.stride_tricks.sliding_window_view(long_, k)
        hits = np.where((np.abs(window - short[:k]) < 1e-9).all(axis=1))[0]
        return f"lengths {len(a)} vs {len(b)}; first {k} {v} values of the shorter found in the longer at {len(hits)} offsets"
    return f"lengths {len(a)} vs {len(b)}, no voltage column to align"


def main() -> int:
    z = zipfile.ZipFile(ZIP)
    ok, total = verify(z)
    print(f"checksums: {ok} of {total} members match the release's checksums.sha512")
    frames = {}
    for m in z.namelist():
        if m.endswith(".feather") and "/font/" not in m:
            frames[m.split("/data/", 1)[1]] = pd.read_feather(io.BytesIO(z.read(m)))
    table = pd.DataFrame([describe(k, v) for k, v in frames.items()])
    table.to_csv(OUT, index=False, lineterminator="\n")
    print(table.to_string(index=False))

    s24, s26 = fielddata.systems("bilfinger2024"), fielddata.systems("bilfinger2026")
    print("\nbilfinger2024 vehicle files:", s24.loc[s24["kind"] == "vehicle", "unit"].tolist() if "unit" in s24 else s24.iloc[:, 0].tolist())
    print("bilfinger2026 vehicle files:", s26.loc[s26["kind"] == "vehicle", "unit"].tolist() if "unit" in s26 else s26.iloc[:, 0].tolist())
    pairs = [(f"Cupra/Cupra_Born_{n}_JB_8A_CEE7_CS_2024.feather", "bilfinger2026", f"Cupra_{n}_JB_8A_CEE7_C45") for n in (204, 213, 288, 349, 397)]
    pairs += [("VW/VW_ID3_JB_8A_CEE7_FTM_2021.feather", "bilfinger2024", "VW_ID3_JB_8A_C40_2021"),
              ("VW/VW_ID3_JB_8A_CEE7_FTM_2023.feather", "bilfinger2024", "VW_ID3_JB_8A_C40_2023"),
              ("VW/VW_ID3_JB_8A_CEE7_FTM_2024.feather", "bilfinger2024", "VW_ID3_JB_8A_C40_2024"),
              ("VW/VW_ID3_FTM_JB_8A_CEE7_FTM_2024_balanced.feather", "bilfinger2026", "VW_ID3_FTM_JB_8A_CEE7_preRelax"),
              ("Tesla/Tesla_Model_3_JB_6A_CEE7_FTM_2021.feather", "bilfinger2024", "Tesla_JB_8A_CEE7_C57_2021"),
              ("Tesla/Tesla_Model_3_JB_6A_CEE7_FTM_2021.feather", "bilfinger2026", "Tesla_JB_6A_CEE7_C57_2022_w_cv")]
    print()
    for f25, pkg, unit in pairs:
        try:
            other = fielddata.load(pkg, unit=unit)
        except Exception as error:  # unit name differs: report it, do not guess
            print(f"{f25} vs {pkg} {unit}: could not load ({type(error).__name__}: {error})")
            continue
        span = (f"; dates {pd.to_datetime(other['date']).min()} to {pd.to_datetime(other['date']).max()}" if "date" in other else "; no dates")
        print(f"{f25} vs {pkg} {unit}: {compare(frames[f25], other)}{span}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
