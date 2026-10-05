"""Synthetic check of the tolerance match used to pair the last Zhang 2023 / EVBattery vehicles (no data needed)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "facts"))
import _overlap_scan  # noqa: E402


def _snippet(seed):
    rng = np.random.default_rng(seed)
    rows = 128
    return np.column_stack([
        rng.normal(-20, 5, rows),          # current (A)
        np.linspace(40, 60, rows),         # SOC (%)
        np.linspace(3.80, 3.95, rows),     # max cell voltage (V)
        np.linspace(3.78, 3.93, rows),     # min cell voltage (V)
        np.full(rows, 25.0),               # max temperature (C)
        np.full(rows, 23.0),               # min temperature (C)
    ])


def test_same_recording_matches_and_shifted_voltage_does_not():
    e = _snippet(1)
    same = e + np.array([0.0, 0.0, 0.0005, -0.0005, 0.0, 0.0])   # within storage resolution
    shifted = e + np.array([0.0, 0.0, 0.01, 0.0, 0.0, 0.0])     # median max-cell voltage off by 0.01 V
    result = _overlap_scan._tolerance_match(np.stack([same, shifted]), e)
    assert result.tolist() == [True, False]
