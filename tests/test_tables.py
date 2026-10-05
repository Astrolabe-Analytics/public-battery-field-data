import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import tables  # noqa: E402


def test_generated_tables_are_current():
    facts = tables.load_facts()
    assert tables.TABLE2.read_text(encoding="utf-8") == tables.table2(facts)
    assert tables.TABLE4.read_text(encoding="utf-8") == tables.table4(facts)


def test_every_claim_has_a_source_and_page():
    with tables.CLAIMS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            assert row["source"].startswith("https://"), row
            assert "p." in row["locator"], row
