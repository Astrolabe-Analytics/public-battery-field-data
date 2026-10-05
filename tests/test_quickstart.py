"""The quick start must cover every registered release (no data needed for this check)."""
from fielddata import quickstart
from fielddata.registry import PACKAGES


def test_every_release_has_a_sample_and_a_plot():
    assert set(quickstart.EXAMPLES) == set(PACKAGES)
    assert set(quickstart.PLOT) == set(PACKAGES)
