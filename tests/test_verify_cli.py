"""The verify command line rejects unknown release names and skips files whose publisher posts no checksum."""
import pytest

from fielddata import verify


def test_unknown_release_is_rejected():
    with pytest.raises(SystemExit):
        verify.main(["no-such-release"])


def test_no_checksum_rows_are_recognised():
    refs = verify._references()
    assert any(r["algorithm"] == "none" for r in refs.values())
