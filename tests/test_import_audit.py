"""Source validation, provenance and rejection before replacing staged data."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.data_import.audit_game_data import audit, stage, validate_tables
from scripts.data_import.prepare_game_data import RAW, prepare


class ImportAuditTests(unittest.TestCase):
    def test_existing_cache_normalizes_identically_and_manifest_is_repeatable(self):
        data, report = audit()
        again, second = audit()
        self.assertEqual(data, prepare())
        self.assertEqual(data, again)
        self.assertEqual(report, second)
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["source_files"], 912)
        self.assertEqual(report["table_counts"]["moves"], 353)
        self.assertEqual(len(report["filtered_moves"]), 239)
        self.assertGreater(report["project_move_overrides"], 0)
        source = next(s for s in report["sources"] if s["file"] == "pokemon/001.json")
        self.assertEqual(source["sha256"], hashlib.sha256((RAW / "pokemon/001.json").read_bytes()).hexdigest())

    def test_bad_stats_reject_batch_and_preserve_previous_stage(self):
        target = RAW / "pokemon/001.json"
        original = Path.read_bytes
        damaged = json.loads(target.read_bytes())
        damaged["stats"][0]["base_stat"] = True

        def read(path):
            return json.dumps(damaged).encode() if path == target else original(path)

        with tempfile.TemporaryDirectory() as folder, patch.object(Path, "read_bytes", read):
            output, report_path = Path(folder) / "stage.json", Path(folder) / "audit.json"
            output.write_text("previous stage", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "import rejected"):
                stage(output=output, report_path=report_path)
            self.assertEqual(output.read_text(), "previous stage")
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "rejected")
            self.assertTrue(any(i["file"] == "pokemon/001.json" for i in report["issues"]))

    def test_missing_referenced_move_is_reported(self):
        target = RAW / "moves/tackle.json"
        original = Path.read_bytes
        def read(path):
            if path == target:
                raise FileNotFoundError("fixture")
            return original(path)
        with patch.object(Path, "read_bytes", read):
            data, report = audit()
        self.assertIsNone(data)
        self.assertIn(dict(file="moves/tackle.json", reason="Missing/unreadable source"), report["issues"])

    def test_normalized_duplicate_keys_and_foreign_keys_are_detected(self):
        data = prepare()
        damaged = deepcopy(data)
        damaged["pokemon_types"].append(deepcopy(damaged["pokemon_types"][0]))
        damaged["pokemon_moves"][0]["move_id"] = 999999
        reasons = [i["reason"] for i in validate_tables(damaged)]
        self.assertIn("Duplicate normalized primary key", reasons)
        self.assertIn("Unresolved foreign key: move_id", reasons)


if __name__ == "__main__":
    unittest.main()
