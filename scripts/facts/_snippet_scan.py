"""Scan one snippet archive of zhang2023 or evbattery and cache per-archive aggregates.

Usage: python scripts/facts/_snippet_scan.py <package> <archive file name>
Writes reports/facts/_cache/<package>__<archive>.json with: snippet count, observation seconds
(union of snippet time ranges per vehicle and charge segment; valid only when snippet clocks are
segment-relative), most common cadence, and the 99th percentile of snippet maximum cell voltage.
Each archive is scanned separately so that no single run is long; rerunning replaces the cache.
"""
from __future__ import annotations

import collections
import json
import sys

import numpy as np

from _common import OUT, ROOT

sys.path.insert(0, str(ROOT))
from fielddata.loaders import _snippets  # noqa: E402  (snippets are read only through the loader)

CACHE = OUT / "_cache"


def union_seconds(spans):
    spans = sorted(spans)
    total, (start, end) = 0.0, spans[0]
    for s, e in spans[1:]:
        if s <= end:
            end = max(end, e)
        else:
            total += end - start
            start, end = s, e
    return total + end - start


def scan(package: str, archive_name: str) -> dict:
    intervals = collections.defaultdict(list)
    cadences = collections.Counter()
    vmax = []
    count = 0
    other = 0
    for _, array, meta in _snippets.iter_snippets(package, archive_name):
        t = array[:, 7]
        step = float(np.median(np.diff(t)))
        cadences[step] += 1
        intervals[(meta["car"], meta["charge_segment"])].append((float(t[0]), float(t[-1]) + step))
        vmax.append(float(np.max(array[:, 3])))
        count += 1
    result = {
        "package": package, "archive": archive_name, "snippets": count, "other_files": other,
        "vehicles": len({car for car, _ in intervals}),
        "observation_seconds_union": sum(union_seconds(v) for v in intervals.values()),
        "observation_seconds_sum": sum(e - s for v in intervals.values() for s, e in v),
        "cadence_s": cadences.most_common(1)[0][0],
        "vmax_p99": float(np.percentile(vmax, 99)),
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f"{package}__{archive_name}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result


if __name__ == "__main__":
    print(json.dumps(scan(sys.argv[1], sys.argv[2]), indent=2))
