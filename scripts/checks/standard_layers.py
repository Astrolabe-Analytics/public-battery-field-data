"""Check layer 1 mappings and build layer 2 from held files, without downloading.

Reads releases only through fielddata, checksum/code metadata and processed manifests.
The optional PPL power-source check also reads its held paper.
Writes reproducible check tables, pilot plots and notes under reports/checks/standard_layers.
The build also writes rebuildable data under the configured SSD _processed directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import pandas as pd
import pandas.testing as pdt

import fielddata
from fielddata import processed
from fielddata._standard import PACKAGES, from_raw, mapping, raw_frame

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "checks" / "standard_layers"
# Fixed held-data windows, selected from independently rising SOC or voltage.
# Keeping them fixed ensures a polarity regression cannot select a different period and pass.
KNOWN_CHARGES = {
    "cao": ("DTI:1", 634, 642),
    "schaeffer": ("3", 141690, 141698),
    "ppl": ("E_W_Brown_BESS", 534, 542),
    "xie": ("00dc55c44bcf46bd817a8cb6d77bceb5", 4, 5),
    "zhang2023": ("battery_brand1:1", 2432, 2440),
    "evbattery": ("battery_dataset1:0", 0, 8),
    "aitio": ("0", 12, 20),
}


def _save(frame, name):
    OUT.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT / name, index=False, lineterminator="\n")


def _note(text):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "README.md").write_text(text + "\n", encoding="utf-8", newline="\n")


def tests():
    OUT.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "pytest", "tests/test_standard.py", "tests/test_processed.py",
               "tests/test_loaders.py", "tests/test_loaders_all.py::test_snippets",
               "tests/test_aitio.py", "tests/test_one_way_in.py",
               "tests/test_binary_files.py", "--basetemp=reports/local/layer-tests", "-q"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (OUT / "tests.txt").write_text(result.stdout + result.stderr, encoding="utf-8", newline="\n")
    print(result.stdout, result.stderr)
    if result.returncode:
        raise SystemExit(result.returncode)
    decision = subprocess.run([sys.executable, "scripts/checks/test_decisions.py"], cwd=ROOT,
                              capture_output=True, text=True)
    (OUT / "decisions.txt").write_text(decision.stdout + decision.stderr, encoding="utf-8", newline="\n")
    print(decision.stdout, decision.stderr)
    if decision.returncode:
        raise SystemExit(decision.returncode)
    leak = subprocess.run([sys.executable, "scripts/leak_check.py"], cwd=ROOT,
                          capture_output=True, text=True)
    findings = [line.removeprefix("LEAK ").split(":", 3)[:3] for line in leak.stdout.splitlines()
                if line.startswith("LEAK ")]
    if leak.returncode not in (0, 1) or (leak.returncode and not findings):
        print(leak.stdout, leak.stderr)
        raise SystemExit(leak.returncode)
    owned = {".gitignore", "README.md", "STATUS.md", "docs/DECISIONS.md", "docs/STANDARD.md",
             "scripts/checks/standard_layers.py", "tests/test_standard.py", "tests/test_processed.py"}
    task_findings = [item for item in findings
                     if item[0] in owned or item[0].startswith(("fielddata/", "reports/checks/standard_layers/"))]
    public_log = (f"Repository-wide leak check: {'fail' if leak.returncode else 'pass'}.\n"
                  f"Task-path findings: {len(task_findings)}. Out-of-scope findings: {len(findings) - len(task_findings)}.\n"
                  "Only paths, lines and categories follow. Matched text and allowlisted content are omitted.\n"
                  + "\n".join(":".join(item) for item in findings) + "\n")
    (OUT / "leaks.txt").write_text(public_log, encoding="utf-8", newline="\n")
    print(public_log)
    if task_findings:
        raise SystemExit(1)


def verify(packages):
    rows = []
    for package in packages:
        for source in processed.verify_sources(package):
            rows.append({"package": package, **{k: v for k, v in source.items() if k != "mtime_ns"}})
        _save(pd.DataFrame(rows), "sources.csv")
    print("All requested loader input sizes and checksums match committed references.", flush=True)


def ppl_power_source():
    """Locate the PPL paper's inverter/real-power statements without copying them into the report."""
    from pypdf import PdfReader
    path = processed.source_paths("ppl")[0].parents[2] / "paper" / "Paper.pdf"
    findings = []
    ac_pages = []
    for number, page in enumerate(PdfReader(path).pages, 1):
        text = re.sub(r"\s+", " ", page.extract_text() or "")
        matches = list(re.finditer(r"reactive|real power|AC power|inverter", text, re.I))
        if "AC real and reactive power" in text:
            ac_pages.append(number)
        if matches:
            findings.append({"pdf_page": number, "terms": sorted({match.group().lower() for match in matches})})
            for match in matches[:5]:
                print(f"PDF page {number}: {text[max(0, match.start()-120):match.end()+180]}")
    OUT.mkdir(parents=True, exist_ok=True)
    if not ac_pages:
        raise AssertionError("PPL paper's AC real/reactive logging statement was not found")
    (OUT / "ppl_power_source.json").write_text(json.dumps({"ac_logging_pdf_pages": ac_pages, "findings": findings}, indent=2) + "\n",
                                            encoding="utf-8", newline="\n")
    (OUT / "ppl_power_source.md").write_text(
        "# PPL power source check\n\n"
        "Reproduce with `python scripts/checks/standard_layers.py ppl-power-source`.\n\n"
        f"The held paper, Section III, PDF page {ac_pages[0]}, describes logged AC real and reactive power "
        "separately from DC voltage and current. This targeted reread corroborates the AC-side designation "
        "in the standard view. It is source evidence, not an independent instrument-boundary data check. "
        "The schema's conservative audit-only flag identifies that lack of independent data corroboration. "
        "The held sign check is recorded separately in `charge_periods.csv` and the prior PPL audit.\n",
        encoding="utf-8", newline="\n")


def build(packages, force):
    for package in packages:
        summary = processed.build(package, force=force)
        _save(summary, f"build_{package}.csv")
    summarize()


def summarize():
    rows, inventory = [], []
    for package in PACKAGES:
        table = fielddata.standard_systems(package)
        path = OUT / f"build_{package}.csv"
        if path.exists():
            result = pd.read_csv(path).set_index("unit")
            result.index = result.index.astype(str)
        else:
            result = pd.DataFrame()
        for row in table.itertuples():
            unit = str(row.unit)
            status = result.loc[unit, "status"] if unit in result.index else "not built"
            count = int(result.loc[unit, "rows"]) if unit in result.index else 0
            inventory.append({"package": package, "unit": unit, "data_tier": row.data_tier,
                              "status": status, "rows": count, "reason": row.standard_reason})
        selected = [row for row in inventory if row["package"] == package]
        rows.append({"package": package, "built_or_reused": sum(row["status"] in {"built", "reused"} for row in selected),
                     "blocked": sum(row["status"] == "blocked" for row in selected),
                     "empty": sum(row["status"] == "empty" for row in selected),
                     "not_built": sum(row["status"] == "not built" for row in selected),
                     "rows_raw": sum(row["rows"] for row in selected)})
    _save(pd.DataFrame(inventory), "units.csv")
    _save(pd.DataFrame(rows), "summary.csv")
    print(pd.DataFrame(rows).to_string(index=False), flush=True)


def audit(packages):
    """Verify every completed manifest and physical Parquet shape, not just the build log."""
    rows = []
    for package in packages:
        sources = processed.verify_sources(package)
        version = processed.code_version()
        table = fielddata.standard_systems(package)
        for row in table.itertuples():
            if row.standard_status != "supported":
                continue
            manifest = processed.validate(package, str(row.unit), sources=sources, version=version)
            expected = int(row.snippets) * 128 if hasattr(row, "snippets") else manifest["rows"]
            if manifest["rows"] != expected:
                raise AssertionError(f"{package} {row.unit}: output rows differ from snippet inventory")
            rows.append({"package": package, "unit": str(row.unit), "rows_raw": manifest["rows"],
                         "parts": len(manifest["parts"]), "checksums_and_shape": "pass"})
            _save(pd.DataFrame(rows), "processed_audit.csv")
    print("Every supported unit has a content-verified processed manifest and matching Parquet shape.", flush=True)
    cachecheck(packages)
    write_note()


def cachecheck(packages):
    """Compare saved processed values with the original standard view, one unit per release."""
    checks = []
    for package in packages:
        unit = KNOWN_CHARGES[package][0]
        if package == "schaeffer":
            raw = next(iter(fielddata.load(package, system=int(unit), chunksize=250_000)))
            expected = from_raw(package, unit, raw)
            month = "2013-05"
            expected = expected[expected["time"].dt.strftime("%Y-%m") == month].reset_index(drop=True)
            actual = processed.load(package, unit, month=month).iloc[:len(expected)].reset_index(drop=True)
        else:
            expected = fielddata.standard(package, unit)
            actual = processed.load(package, unit)
        if expected.empty:
            raise AssertionError(f"{package}: processed comparison selected no rows")
        pdt.assert_frame_equal(actual, expected, check_dtype=False)
        checks.append({"package": package, "unit": unit, "rows_raw_compared": len(expected),
                       "processed_values_vs_standard": "pass"})
        _save(pd.DataFrame(checks), "processed_roundtrip.csv")
    print("Processed values match the standard view in every release's held comparison unit.", flush=True)


def check(packages):
    checks, periods = [], []
    for package in packages:
        unit, a, b = KNOWN_CHARGES[package]
        if package == "schaeffer":
            raw = next(iter(fielddata.load(package, system=int(unit), chunksize=250_000)))
        elif package == "ppl":
            raw = fielddata.load(package, years=[2022])
        else:
            raw = raw_frame(package, unit)
        view = from_raw(package, unit, raw)
        for source, (target, factor) in mapping(package, raw, unit).items():
            np.testing.assert_allclose(view[target].to_numpy() / factor, raw[source].to_numpy(),
                                       rtol=1e-12, atol=1e-10, equal_nan=True)
        if package != "schaeffer":
            kwargs = {"years": [2022]} if package == "ppl" else {}
            public = fielddata.standard(package, unit, **kwargs)
            pdt.assert_frame_equal(public, view)
        if "soc" in view:
            level = view["soc"]
        else:
            cells = [c for c in view if c.startswith("cell_v_") and c[-3:].isdigit()]
            level = view[cells].median(axis=1) if cells else view["pack_voltage"]
        delta = float(level.iloc[b] - level.iloc[a])
        if not np.isfinite(delta) or delta <= 0:
            raise AssertionError(f"{package} {unit}: fixed charge-period SOC/voltage no longer rises")
        current = view["pack_current"].iloc[a:b + 1]
        if not (current > 0).all():
            raise AssertionError(f"{package} {unit}: known charge-period current is not positive")
        clock = "time" if "time" in view else "elapsed_time_s"
        periods.append({"package": package, "unit": unit, "start_row": a, "stop_row": b,
                        "start": str(view[clock].iloc[a]), "stop": str(view[clock].iloc[b]),
                        "independent_increase": delta, "min_charging_current_A": float(current.min()),
                        "basis": "raw after documented unit/sign conversion",
                        "evidence": "SOC rises" if "soc" in view else "terminal/cell voltage rises"})
        checks.append({"package": package, "unit": unit, "rows_raw_checked": len(raw),
                       "mapped_columns": len(mapping(package, raw, unit)), "roundtrip": "pass",
                       "charging_sign": "pass"})
        _save(pd.DataFrame(checks), "roundtrip.csv")
        _save(pd.DataFrame(periods), "charge_periods.csv")
        if package in {"cao", "schaeffer", "ppl"}:
            plot(package, unit, view, a, b)
    write_note()


def write_note():
    _note(
        "# Standard-view verification\n\n"
        "Run `python scripts/checks/standard_layers.py test`, then `verify`, `check` and `build` "
        "with the same script. No download is performed.\n\n"
        "The test log records synthetic mapping, missing-column, raw-loader and cache-integrity checks. "
        "`leaks.txt` records the existing public-text leak check. The repository-wide check reports "
        "out-of-scope findings in existing files, which this task leaves unchanged. The task-path check "
        "passes. Only paths, lines and categories are saved, not matched text or allowlisted content. "
        "The decisions log checks the existing counting ledger without changing it. "
        "`sources.csv` records freshly measured sizes and SHA-256 values, compared with committed publisher "
        "checksums or the committed holding snapshot where no publisher checksum exists. "
        "`roundtrip.csv` checks one supported unit per release against its raw loader after inversion of "
        "every physical-column conversion. `charge_periods.csv` records a raw period with independently "
        "rising SOC or voltage and positive mapped charging current. The windows are fixed in the script, "
        "not selected afresh based on current polarity. This is a sign sanity check, not a "
        "layer-3 event definition or a claim that every rising voltage interval is charging.\n\n"
        "Pilot plots show raw values after documented conversion, using DejaVu Sans. "
        "The check action regenerates them from the fixed windows without committing measurement-series copies. "
        "Schaeffer derivatives are CC BY-NC 4.0. "
        "PPL states no data license and its preview follows the maintainer's recorded permission decision. "
        "Cao derivatives follow CC BY 4.0.\n\n"
        "`summary.csv` and `units.csv` are produced from held unit inventories and completed builds. "
        "GIS units are explicit blocks, not dropped units. Label-only snippet units are explicit empty entries. "
        "Processed values are raw after conversion, not cleaned, filtered or deduplicated. "
        "The PPL build covers the annual ESS telemetry, not the separate cell-level share. "
        "Cao uses assumed 30-second frame spacing, not measured timestamps. "
        "Cao, Zhang and EVBattery have undated partitions. PPL and Schaeffer retain wall-clock times "
        "without claiming a time zone.\n\n"
        "Run `python scripts/checks/standard_layers.py audit` to check every supported unit's saved manifest, "
        "source content, output checksums and physical Parquet shape. Results are in `processed_audit.csv`. "
        "It also compares held processed values with their standard view in one unit per release, recorded "
        "in `processed_roundtrip.csv`. Schaeffer uses the source-order portion of its first chunk in May 2013, "
        "and PPL compares the complete annual ESS stream, including changing schema tiers and duplicated "
        "year-boundary records. Both representations convert annual inputs before concatenating them.\n\n"
        "Source baseline: committed audits and schema notes at "
        "`d447b9eed0206f139d0a9bca6ece5fb0c8c6bc36`, not a fresh full reread of paper, supplement and author code. "
        "The maintainer approved this baseline with targeted rereads and held-data checks. Each mapping row cites "
        "its evidence, and audit-only meanings are flagged in each schema note. A new data-versus-audit "
        "disagreement requires a full reread and an entry in `docs/DECISIONS.md`. None was found by these "
        "mapping checks. Source-internal wording inconsistencies are documented there and in the notes."
    )


def plot(package, unit, view, a, b):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.family"] = "DejaVu Sans"
    start, stop = max(0, a - 10), min(len(view), b + 30)
    portion = view.iloc[start:stop]
    voltage = next((c for c in ("cell_v_001", "cell_v_mean", "cell_v_max", "pack_voltage") if c in portion), None)
    columns = [c for c in ("time", "elapsed_time_s", "pack_current", "soc", voltage) if c and c in portion]
    points = portion[columns].copy()
    points.insert(0, "row", np.arange(start, stop))
    fig, axes = plt.subplots(2, 1, figsize=(6, 3.5), sharex=True, constrained_layout=True)
    axes[0].plot(points["row"], points["pack_current"], color="#245b78")
    axes[0].axhline(0, color="0.5", linewidth=0.6)
    axes[0].set_ylabel("Current (A)\ncharge positive")
    signal = voltage or "soc"
    axes[1].plot(points["row"], portion[signal], color="#245b78")
    axes[1].set_ylabel(f"{signal}\n{'V' if signal != 'soc' else '%'}")
    axes[1].set_xlabel("Released row (no resampling)")
    fig.suptitle(f"{package} {unit}: charging maps to positive current", fontsize=10)
    fig.savefig(OUT / f"{package}.png", dpi=140)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("test", "verify", "build", "check", "summary", "audit", "ppl-power-source"))
    parser.add_argument("packages", nargs="*", choices=PACKAGES)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    packages = args.packages or PACKAGES
    if args.action == "test":
        tests()
    elif args.action == "verify":
        verify(packages)
    elif args.action == "build":
        build(packages, args.force)
    elif args.action == "check":
        check(packages)
    elif args.action == "audit":
        audit(packages)
    elif args.action == "ppl-power-source":
        ppl_power_source()
    else:
        summarize()


if __name__ == "__main__":
    main()
