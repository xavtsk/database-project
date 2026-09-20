"""Check stats/type extraction against the raw data, without network requests."""

import csv
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.data_import.process_pokemon import RAW_DIR, process_pokemon


def process_sample(raw_dir, output_dir):
    return process_pokemon(raw_dir, output_dir, sample=True)


class PokemonProcessingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.raw = Path(temporary.name) / "raw"
        self.output = Path(temporary.name) / "processed"
        self.raw.mkdir()
        for pokemon_id in (1, 2, 3):
            name = f"{pokemon_id:03d}.json"
            shutil.copyfile(RAW_DIR / name, self.raw / name)

    def read_csv(self, name):
        with (self.output / name).open(encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))

    def test_values_unique_ids_and_all_type_relationships_match_raw_data(self):
        self.assertEqual(process_sample(self.raw, self.output), (3, 6))
        pokemon = self.read_csv("pokemon.csv")
        types = self.read_csv("pokemon_types.csv")
        self.assertEqual([row["pokemon_id"] for row in pokemon], ["1", "2", "3"])
        self.assertEqual(len({(row["pokemon_id"], row["slot"]) for row in types}), 6)
        self.assertLessEqual({row["pokemon_id"] for row in types}, {row["pokemon_id"] for row in pokemon})
        for row in pokemon:
            pokemon_id = int(row["pokemon_id"])
            raw = json.loads((self.raw / f"{pokemon_id:03d}.json").read_bytes())
            self.assertEqual(row["name"], raw["name"])
            for stat in raw["stats"]:
                column = stat["stat"]["name"].replace("-", "_")
                self.assertEqual(int(row[column]), stat["base_stat"])
            actual = {(item["type_name"], int(item["slot"])) for item in types if item["pokemon_id"] == row["pokemon_id"]}
            expected = {(item["type"]["name"], item["slot"]) for item in raw["types"]}
            self.assertEqual(actual, expected)

    def test_rerun_is_identical_and_raw_files_are_unchanged(self):
        def raw_snapshot():
            return {p.name: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in self.raw.glob("*.json")}

        before = raw_snapshot()
        process_sample(self.raw, self.output)
        first = {p.name: p.read_bytes() for p in self.output.glob("*.csv")}
        process_sample(self.raw, self.output)
        self.assertEqual(first, {p.name: p.read_bytes() for p in self.output.glob("*.csv")})
        self.assertEqual(before, raw_snapshot())

    def test_stat_and_type_order_does_not_change_output(self):
        process_sample(self.raw, self.output)
        first = {p.name: p.read_bytes() for p in self.output.glob("*.csv")}
        path = self.raw / "001.json"
        data = json.loads(path.read_bytes())
        data["stats"].reverse()
        data["types"].reverse()
        path.write_text(json.dumps(data), encoding="utf-8")
        process_sample(self.raw, self.output)
        self.assertEqual(first, {p.name: p.read_bytes() for p in self.output.glob("*.csv")})

    def test_missing_file_does_not_create_outputs(self):
        (self.raw / "003.json").unlink()
        with self.assertRaisesRegex(ValueError, "003.json"):
            process_sample(self.raw, self.output)
        self.assertFalse(self.output.exists())

    def test_invalid_input_does_not_overwrite_previous_outputs(self):
        process_sample(self.raw, self.output)
        before = {p.name: p.read_bytes() for p in self.output.glob("*.csv")}
        path = self.raw / "003.json"
        original = path.read_bytes()
        mutations = {
            "wrong ID": lambda data: data.update(id=1),
            "missing stat": lambda data: data["stats"].pop(),
            "duplicate stat": lambda data: data["stats"].append(data["stats"][0]),
            "duplicate type": lambda data: data["types"].append(data["types"][0]),
            "duplicate slot": lambda data: data["types"][1].update(slot=1),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                data = json.loads(original)
                mutate(data)
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError):
                    process_sample(self.raw, self.output)
                self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.glob("*.csv")})
        path.write_text("{incomplete", encoding="utf-8")
        with self.assertRaises(ValueError):
            process_sample(self.raw, self.output)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.glob("*.csv")})

    def test_full_dataset_preserves_all_stats_and_type_relationships(self):
        expected_types = set()
        source = {}
        for pokemon_id in range(1, 152):
            data = json.loads((RAW_DIR / f"{pokemon_id:03d}.json").read_bytes())
            source[str(pokemon_id)] = data
            expected_types.update(
                (str(pokemon_id), item["type"]["name"], str(item["slot"]))
                for item in data["types"]
            )

        self.assertEqual(process_pokemon(RAW_DIR, self.output), (151, len(expected_types)))
        pokemon = self.read_csv("pokemon.csv")
        types = self.read_csv("pokemon_types.csv")
        self.assertEqual([row["pokemon_id"] for row in pokemon], [str(i) for i in range(1, 152)])
        self.assertEqual(len(types), len(expected_types))
        self.assertEqual(
            {(row["pokemon_id"], row["type_name"], row["slot"]) for row in types},
            expected_types,
        )
        for row in pokemon:
            raw = source[row["pokemon_id"]]
            self.assertEqual(row["name"], raw["name"])
            for stat in raw["stats"]:
                self.assertEqual(int(row[stat["stat"]["name"].replace("-", "_")]), stat["base_stat"])

        first = {p.name: p.read_bytes() for p in self.output.glob("*.csv")}
        process_pokemon(RAW_DIR, self.output)
        self.assertEqual(first, {p.name: p.read_bytes() for p in self.output.glob("*.csv")})

    def test_full_run_requires_files_beyond_the_sample(self):
        with self.assertRaisesRegex(ValueError, "004.json"):
            process_pokemon(self.raw, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
