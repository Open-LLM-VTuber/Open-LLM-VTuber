import json
import tempfile
import unittest
from pathlib import Path

from scripts.inspect_live2d_model import _format_text, inspect_model


class InspectLive2DModelTests(unittest.TestCase):
    def test_reports_missing_core_expression_and_motion_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_dir = Path(temp_dir) / "sample" / "runtime"
            model_dir.mkdir(parents=True)
            (model_dir / "sample.moc3").write_bytes(b"moc")
            (model_dir / "textures").mkdir()
            (model_dir / "textures" / "texture_00.png").write_bytes(b"png")

            model_path = model_dir / "sample.model3.json"
            model_path.write_text(
                json.dumps(
                    {
                        "Version": 3,
                        "FileReferences": {
                            "Moc": "sample.moc3",
                            "Textures": [
                                "textures\\texture_00.png",
                                "textures/texture_01.png",
                            ],
                            "Physics": "sample.physics3.json",
                            "Expressions": [
                                {"Name": "smile", "File": "smile.exp3.json"}
                            ],
                            "Motions": {"Idle": [{"File": "idle.motion3.json"}]},
                        },
                    }
                ),
                encoding="utf-8",
            )

            summary = inspect_model(
                model_path,
                Path(temp_dir),
                model_name=None,
                character_name=None,
            )

            self.assertEqual(summary["texture_count"], 2)
            self.assertEqual(len(summary["core_files"]), 4)
            core_status = {
                entry["file"]: entry["exists"] for entry in summary["core_files"]
            }
            self.assertTrue(core_status["sample.moc3"])
            self.assertTrue(core_status["textures\\texture_00.png"])
            self.assertEqual(
                {entry["kind"] for entry in summary["missing_files"]},
                {"texture", "physics", "expression", "motion"},
            )
            report = _format_text(summary)
            self.assertIn("## Missing referenced files", report)
            self.assertIn("sample.physics3.json", report)
            self.assertIn("idle.motion3.json", report)

    def test_ignores_invalid_texture_container_instead_of_counting_characters(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "sample.model3.json"
            model_path.write_text(
                json.dumps({"FileReferences": {"Textures": "not-a-list"}}),
                encoding="utf-8",
            )

            summary = inspect_model(
                model_path,
                Path(temp_dir),
                model_name=None,
                character_name=None,
            )

            self.assertEqual(summary["texture_count"], 0)
            self.assertEqual(
                summary["core_files"],
                [{"kind": "moc", "file": "", "exists": False}],
            )
            self.assertEqual(summary["missing_files"], summary["core_files"])

    def test_reports_absent_moc_with_other_valid_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_dir = Path(temp_dir)
            (model_dir / "texture.png").write_bytes(b"png")
            model_path = model_dir / "sample.model3.json"
            model_path.write_text(
                json.dumps({"FileReferences": {"Textures": ["texture.png"]}}),
                encoding="utf-8",
            )

            summary = inspect_model(
                model_path,
                model_dir,
                model_name=None,
                character_name=None,
            )

            self.assertEqual(summary["texture_count"], 1)
            self.assertEqual(
                summary["missing_files"],
                [{"kind": "moc", "file": "", "exists": False}],
            )
            self.assertIn("moc", _format_text(summary))
            self.assertIn("<invalid reference>", _format_text(summary))

    def test_outside_model_root_needs_a_served_url_for_config_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            model_path = root / "external" / "sample.model3.json"
            model_path.parent.mkdir()
            model_path.write_text(
                json.dumps({"FileReferences": {"Moc": "sample.moc3"}}),
                encoding="utf-8",
            )
            model_root = root / "live2d-models"

            summary = inspect_model(model_path, model_root, None, None)
            self.assertEqual(summary["model3_path"], str(model_path))
            self.assertIsNone(summary["suggested_model_dict_entry"])
            self.assertIn("Supply --public-url", _format_text(summary))
            self.assertNotIn('"url":', _format_text(summary))

            with_url = inspect_model(
                model_path,
                model_root,
                None,
                None,
                public_url="/live2d-models/custom/sample.model3.json",
            )
            self.assertEqual(
                with_url["suggested_model_dict_entry"]["url"],
                "/live2d-models/custom/sample.model3.json",
            )
            self.assertIn('"url":', _format_text(with_url))
            with self.assertRaisesRegex(ValueError, "--public-url"):
                inspect_model(
                    model_path, model_root, None, None, public_url="javascript:alert(1)"
                )


if __name__ == "__main__":
    unittest.main()
