"""Offline inspection checks: identity, source integrity and suspect result rows."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.data_import.inspect_historical import inspect, name_key, ROOT


class HistoricalInspectionTests(unittest.TestCase):
    def test_downloaded_source_scope_and_identity_are_explicit(self):
        result = inspect()
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["mapping_status_counts"], {
            "proposed_match": 150, "outside_catalogue_or_form": 649, "missing_name": 1})
        mapping = {r["external_id"]: r for r in result["proposed_mapping"]}
        self.assertIsNone(mapping[4]["pokemon_id"])  # Mega Venusaur, not Charmander.
        self.assertEqual(mapping[5]["pokemon_id"], 4)
        self.assertIsNone(mapping[63]["pokemon_id"])  # Do not invent the missing name.
        self.assertEqual(result["catalogue_without_proposed_match"], ["primeape"])
        self.assertEqual(result["combats"]["counts"]["catalogue_eligible_unique_rows"], 1589)
        self.assertEqual(len(result["mapped_stat_differences"]), 6)
        self.assertNotEqual(name_key("Nidoran\u2640"), name_key("Nidoran\u2642"))
        self.assertNotEqual(name_key("Mega Charizard X"), name_key("Charizard"))

    def fixture(self, directory):
        rows = {
            "pokemon.csv": (["#", "Name", "Type 1", "Type 2", "HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed", "Generation", "Legendary"],
                            [[101, "Bulbasaur", "Grass", "Poison", 45, 49, 49, 65, 65, 45, 1, "False"],
                             [202, "Charmander", "Fire", "", 39, 52, 43, 60, 50, 65, 1, "False"]]),
            "combats.csv": (["First_pokemon", "Second_pokemon", "Winner"],
                            [[101, 202, 101], [101, 202, 101], [202, 101, 101], [101, 202, 999],
                             [101, 101, 101], [101, "bad", 101]]),
            "tests.csv": (["First_pokemon", "Second_pokemon"], [[101, 202]])}
        files = []
        for filename, (columns, values) in rows.items():
            path = directory / filename
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(columns)
                writer.writerows(values)
            files.append(dict(file=filename, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        manifest = dict(files=files, source_url="fixture", license="test fixture", battle_data="fixture")
        (directory / "source.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_order_duplicates_bad_outcomes_and_hash_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.fixture(directory)
            result = inspect(directory)
            counts = result["combats"]["counts"]
            self.assertEqual(counts["catalogue_eligible_rows"], 3)
            self.assertEqual(counts["catalogue_eligible_unique_rows"], 2)  # Reverse role is distinct.
            self.assertEqual(counts["exact_duplicate_extra_rows"], 1)
            self.assertEqual(counts["winner_not_participant"], 1)
            self.assertEqual(counts["self_matchup"], 1)
            self.assertEqual(counts["malformed_rows"], 1)
            (directory / "combats.csv").write_text("modified", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Source hash differs"):
                inspect(directory)
