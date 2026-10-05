"""deng's GitHub repository mixes the 20 released RARs with the authors' code: only the RARs land in data/ (no network)."""
from unittest.mock import patch

from fielddata.fetch import plan_package, resolve_files


def test_deng_rars_in_data_and_other_files_under_code(tmp_path):
    tree = {"tree": [{"type": "blob", "path": f"#{i}.rar", "size": 10} for i in range(1, 21)]
            + [{"type": "blob", "path": p, "size": 1} for p in ("README.md", "LICENSE", "capacity_extract.py", "Fig1.png", "Fig2.png", "docs/notes.txt")]
            + [{"type": "tree", "path": "docs"}]}

    def fake_json(url, **_):
        return {"default_branch": "main"} if url.endswith("battery-charging-data-of-on-road-electric-vehicles") else tree

    with patch("fielddata.fetch._json", side_effect=fake_json):
        files = resolve_files(plan_package("deng", tmp_path))
    data = [f.name for f in files if not f.name.startswith("code/")]
    code = [f.name for f in files if f.name.startswith("code/")]
    assert sorted(data) == sorted(f"#{i}.rar" for i in range(1, 21))
    assert len(code) == 6 and "code/docs/notes.txt" in code
