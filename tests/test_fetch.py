import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fielddata.fetch import _checksum_for, plan_package, print_manual, resolve_files
from fielddata.registry import PACKAGES


MANUAL_PACKAGES = {
    "bilfinger2024",
    "bilfinger2026",
    "changan",
    "fei_bus",
    "ku_leuven_bev",
    "m5bat-2023-04",
    "m5bat-pbacid",
    "rwth-android",
    "zhou2026",
}


class FetchPlanTests(unittest.TestCase):
    def test_every_package_has_a_registry_backed_plan_without_downloading(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch("fielddata.fetch._download", side_effect=AssertionError("planning must not download")):
                plans = {package: plan_package(package, root) for package in PACKAGES}

            self.assertEqual(len(plans), 22)
            for package, plan in plans.items():
                metadata = PACKAGES[package]
                self.assertEqual(plan.record_url, metadata["urls"]["data"])
                self.assertEqual(plan.expected_files, tuple(metadata.get("data_files") or metadata.get("archives", {}).keys()))
                self.assertEqual(plan.destination, root / metadata["data_directory"])
                self.assertEqual(plan.automatic, package not in MANUAL_PACKAGES)

    def test_automatic_source_routes(self) -> None:
        self.assertEqual(plan_package("flashbattery-agv").source_kind, "zenodo")
        self.assertEqual(plan_package("cloverleaf").source_kind, "zenodo")
        self.assertEqual(plan_package("zhang2023").source_kind, "figshare")
        self.assertEqual(plan_package("deng").source_kind, "github")
        self.assertFalse(plan_package("zhou2026").automatic)

    def test_zenodo_plan_uses_api_files_and_skips_papers(self) -> None:
        response = {
            "files": [
                {"key": "dataset.csv", "size": 12, "checksum": "md5:abc", "links": {"content": "https://files/dataset"}},
                {"key": "Paper.pdf", "size": 99, "links": {"content": "https://files/paper"}},
            ]
        }
        with patch("fielddata.fetch._json", return_value=response):
            files = resolve_files(plan_package("flashbattery-agv"))
        self.assertEqual([(item.name, item.url, item.size) for item in files], [("dataset.csv", "https://files/dataset", 12)])

    def test_figshare_plan_uses_api_files_and_skips_papers(self) -> None:
        response = {
            "files": [
                {"name": "battery_brand1.tar.gz", "size": 42, "supplied_md5": "abc", "download_url": "https://files/data"},
                {"name": "paper.pdf", "size": 10, "download_url": "https://files/paper"},
            ]
        }
        with patch("fielddata.fetch._json", return_value=response):
            files = resolve_files(plan_package("zhang2023"))
        self.assertEqual([item.name for item in files], ["battery_brand1.tar.gz"])
        self.assertEqual(files[0].api_checksum, "md5:abc")

    def test_github_plan_preserves_registered_repository_folder(self) -> None:
        responses = [
            {"default_branch": "main"},
            {"tree": [{"type": "blob", "path": "ESS_2025.csv", "size": 123}, {"type": "blob", "path": "paper/Paper.pdf", "size": 9}]},
        ]
        with patch("fielddata.fetch._json", side_effect=responses):
            files = resolve_files(plan_package("ppl"))
        self.assertEqual([item.name for item in files], ["BESS-Analysis/ESS_2025.csv"])
        self.assertTrue(files[0].url.endswith("/main/ESS_2025.csv"))

    def test_reference_checksum_lookup_uses_recorded_data_path(self) -> None:
        self.assertEqual(_checksum_for("flashbattery-agv", "dataset.csv"), ("md5", "2faa82bd0c27763d4b12d4c58510a1f5"))
        self.assertIsNone(_checksum_for("flashbattery-agv", "README.adoc"))

    def test_manual_plan_prints_numbered_steps_filename_and_size(self) -> None:
        output = io.StringIO()
        with patch("sys.stdout", output):
            print_manual(plan_package("m5bat-pbacid", "downloads"))
        text = output.getvalue()
        self.assertIn("1. Open https://publications.rwth-aachen.de/record/1038622", text)
        self.assertIn("Full_Dataset_M5BAT_Battery_Unit_Pb1.zip (4.33 GB (page display))", text)
        self.assertIn("4. Run python -m fielddata.verify", text)


if __name__ == "__main__":
    unittest.main()
