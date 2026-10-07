from pathlib import Path

import pytest

from fielddata.registry import metadata


@pytest.fixture
def fixture_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def package_directory(tmp_path):
    def create(package_id):
        path = tmp_path / metadata(package_id)["data_directory"]
        path.mkdir(parents=True, exist_ok=True)
        return path

    return create
