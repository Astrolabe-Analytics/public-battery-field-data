"""Shared helpers for the v1.3 intake facts scripts (lin_agv, li2026_evfault, giu_ebike).

These releases are admitted with counts pending the maintainer's approval. Their facts scripts therefore write to
reports/candidates/<name>/ (facts.json, a short facts.txt and a per-unit profile CSV), not to reports/facts/, so the
facts table, totals, tables and dashboards are unchanged until the counts are approved. On approval, the release moves
into fielddata.registry.PACKAGES, its draft rule moves from fielddata.counting.PROPOSED_RULES into RULES, and its facts
are written to reports/facts/ like every other package.

Every fact uses _common.fact (value, basis, source, note). Units come from fielddata.counting.PROPOSED_RULES through the
loader. Sizes count the publisher-released files under data/.
"""
from __future__ import annotations

import json

from _common import FIELDS, ROOT, fact

from fielddata import counting
from fielddata.loaders._base import directory
from fielddata.registry import metadata

CANDIDATE_OUT = ROOT / "reports" / "candidates"

# Admitted in v1.3 (maintainer, 2026-11-20, admitted 2026-11-24). Their facts come through _common.measure like every
# other package: measure() calls apply() after the shared defaults and the unit count from fielddata/counting.py.
V13 = ["li2026_evfault", "giu_ebike"]
# Extra facts copied into reports/facts/<name>.json besides the 14 fields (scripts/totals.py reads snapshot_fault_labels).
EXTRA_KEYS = {"snapshots", "snapshot_fault_labels", "faults_stated", "fault_batteries_stated", "fault_label_cell_snapshots", "charge_end_sample", "faults_counted"}


def apply(package: str, facts: dict[str, dict], script: str) -> None:
    """Overwrite the shared defaults with the release's own facts from scripts/facts/<package>.py collect()."""
    import importlib
    own, extra = importlib.import_module(package).collect()
    facts.update(own)
    facts.update({key: value for key, value in extra.items() if key in EXTRA_KEYS})


def held(package: str) -> tuple[int, int]:
    """Count and bytes of the publisher-released files under the release's data/ folder."""
    folder = directory(package)  # file inventory: names and sizes only, as _common.inventory
    files = [p for p in folder.rglob("*") if p.is_file()]
    return len(files), sum(p.stat().st_size for p in files)


def base(package: str, script: str) -> dict[str, dict]:
    count, size = held(package)
    return {
        "units_released": fact(counting.proposed_units(package), "measured", f"fielddata/counting.py PROPOSED_RULES over fielddata.systems('{package}')",
                               f"Draft rule, pending approval: {counting.proposed_rule(package)}."),
        "cells_leadacid": fact(None, "not_in_release", note="Lithium-ion release; no lead-acid cells."),
        "size_gb": fact(size / 1e9, "measured", script),
        "files": fact(count, "measured", script),
        "fault_onset_timestamp": fact("no", "stated", f"{metadata(package)['urls']['data']}; the release has no fault-onset timestamp field"),
        "sentinels_documented": fact("no", "stated", f"{metadata(package)['urls']['data']}; the record and released documentation state no sentinel convention"),
    }


def write(package: str, facts: dict[str, dict], extra: dict | None = None) -> None:
    missing = [f for f in FIELDS if f not in facts]
    if missing:
        raise ValueError(f"{package}: facts missing {missing}")
    folder = CANDIDATE_OUT / package
    folder.mkdir(parents=True, exist_ok=True)
    out = {"package": package, "status": "counts pending approval", "facts": {f: facts[f] for f in FIELDS}, **(extra or {})}
    (folder / "facts.json").write_text(json.dumps(out, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8", newline="\n")
    lines = [f"{package}: proposed facts (counts pending approval), written by scripts/facts/{package}.py"]
    for field in FIELDS:
        f = facts[field]
        value = f["value"] if f["value"] is not None else "-"
        lines.append(f"{field}: {value} [{f['basis']}]")
    for key, value in (extra or {}).items():
        if isinstance(value, dict) and "value" in value:
            lines.append(f"{key}: {value['value']} [{value['basis']}]")
    (folder / "facts.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
