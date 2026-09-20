"""Extract cached Pokémon stats and types to CSV, without defining a database schema."""

import argparse
import csv
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "pokemon"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
STAT_COLUMNS = {
    "hp": "hp",
    "attack": "attack",
    "defense": "defense",
    "special-attack": "special_attack",
    "special-defense": "special_defense",
    "speed": "speed",
}
POKEMON_COLUMNS = ["pokemon_id", "name", *STAT_COLUMNS.values()]
TYPE_COLUMNS = ["pokemon_id", "type_name", "slot"]


def extract_rows(data, expected_id):
    """Validate one source record and extract only the agreed trial fields."""
    if type(data["id"]) is not int or data["id"] != expected_id:
        raise ValueError(f"expected Pokémon ID {expected_id}")
    if not isinstance(data["name"], str) or not data["name"].strip():
        raise ValueError("missing Pokémon name")

    stats = {}
    for entry in data["stats"]:
        name = entry["stat"]["name"]
        value = entry["base_stat"]
        if name not in STAT_COLUMNS or name in stats:
            raise ValueError(f"unexpected or duplicate stat: {name}")
        if type(value) is not int or value <= 0:
            raise ValueError(f"invalid base stat: {name}")
        stats[name] = value
    if set(stats) != set(STAT_COLUMNS):
        raise ValueError("all six base stats are required")

    pokemon_row = {"pokemon_id": expected_id, "name": data["name"]}
    pokemon_row.update({column: stats[name] for name, column in STAT_COLUMNS.items()})

    types = data["types"]
    if not 1 <= len(types) <= 2:
        raise ValueError("expected one or two Pokémon types")
    type_rows = []
    seen_names = set()
    seen_slots = set()
    for entry in types:
        name = entry["type"]["name"]
        slot = entry["slot"]
        if not isinstance(name, str) or not name.strip() or name in seen_names:
            raise ValueError("invalid or duplicate Pokémon type")
        if type(slot) is not int or slot not in (1, 2) or slot in seen_slots:
            raise ValueError("invalid or duplicate type slot")
        seen_names.add(name)
        seen_slots.add(slot)
        type_rows.append({"pokemon_id": expected_id, "type_name": name, "slot": slot})
    if seen_slots != set(range(1, len(types) + 1)):
        raise ValueError("type slots must start at 1")
    return pokemon_row, sorted(type_rows, key=lambda row: row["slot"])


def process_pokemon(raw_dir=RAW_DIR, output_dir=OUTPUT_DIR, *, sample=False):
    """Validate every input before writing either output; never append."""
    pokemon_rows = []
    type_rows = []
    for pokemon_id in range(1, 4 if sample else 152):
        path = Path(raw_dir) / f"{pokemon_id:03d}.json"
        try:
            data = json.loads(path.read_bytes())
            pokemon, types = extract_rows(data, pokemon_id)
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise ValueError(f"{path}: {error}") from error
        pokemon_rows.append(pokemon)
        type_rows.extend(types)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, columns, rows in (
        ("pokemon.csv", POKEMON_COLUMNS, pokemon_rows),
        ("pokemon_types.csv", TYPE_COLUMNS, type_rows),
    ):
        with (output_dir / filename).open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    return len(pokemon_rows), len(type_rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample", action="store_true",
        help="Process only IDs 1–3 into data/processed/sample/ instead of all 151",
    )
    args = parser.parse_args()
    output_dir = OUTPUT_DIR / "sample" if args.sample else OUTPUT_DIR
    try:
        pokemon_count, type_count = process_pokemon(output_dir=output_dir, sample=args.sample)
    except (OSError, ValueError) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1
    print(f"[PROCESSED] {output_dir / 'pokemon.csv'}: {pokemon_count} rows")
    print(f"[PROCESSED] {output_dir / 'pokemon_types.csv'}: {type_count} rows")
    print("Stats and types only; these CSVs do not define the final database schema.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
