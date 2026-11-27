"""Inspect the approved CSV cache without changing raw files or any database.

Name matching is an inspection proposal, not an approved identity mapping.
Missing names and alternate forms are never inferred from row numbers or stats.
"""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import re

from scripts.data_import.audit_game_data import write_report
from scripts.data_import.fetch_historical import DESTINATION, FILES, ROOT

REPORT = ROOT / ".local/historical-inspection.json"
STATS = {"HP": "hp", "Attack": "attack", "Defense": "defense",
         "Sp. Atk": "special_attack", "Sp. Def": "special_defense", "Speed": "speed"}


def name_key(name):
    # These spelling changes preserve gender and do not remove form identifiers.
    name = name.lower().replace("\u2640", "f").replace("\u2642", "m")
    return re.sub(r"[^a-z0-9]", "", name)


def inspect(directory=DESTINATION, catalogue_path=ROOT / "data/processed/game_data.json"):
    directory = Path(directory)
    manifest = json.loads((directory / "source.json").read_text(encoding="utf-8"))
    expected = {r["file"]: r["sha256"] for r in manifest["files"]}
    sources, tables = [], {}
    for filename in FILES:
        body = (directory / filename).read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        if digest != expected.get(filename):
            raise ValueError("Source hash differs from download manifest: " + filename)
        reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
        tables[filename] = list(reader)
        if any(None in row or any(value is None for value in row.values()) for row in tables[filename]):
            raise ValueError("Malformed CSV row: " + filename)
        sources.append(dict(file=filename, sha256=digest, rows=len(tables[filename]), columns=reader.fieldnames))

    catalogue_body = Path(catalogue_path).read_bytes()
    game = json.loads(catalogue_body)
    by_name = {}
    for pokemon in game["pokemon"]:
        by_name.setdefault(name_key(pokemon["name"]), []).append(pokemon)
    types = {r["id"]: r["name"] for r in game["types"]}
    pokemon_types = {}
    for link in game["pokemon_types"]:
        pokemon_types.setdefault(link["pokemon_id"], set()).add(types[link["type_id"]])

    issues, mapping, mapped, external_ids, stat_differences = [], [], {}, set(), []
    for row_number, row in enumerate(tables["pokemon.csv"], 1):
        try:
            external_id = int(row["#"])
            if external_id <= 0 or external_id in external_ids:
                raise ValueError("Duplicate or nonpositive external ID")
            external_ids.add(external_id)
            stats = {target: int(row[source]) for source, target in STATS.items()}
            if any(value <= 0 for value in stats.values()) or row["Legendary"] not in ("True", "False"):
                raise ValueError("Invalid stat or legendary flag")
            generation = int(row["Generation"])
            if not 1 <= generation <= 6 or not row["Type 1"] or any(
                row[column].lower() not in types.values() for column in ("Type 1", "Type 2") if row[column]
            ):
                raise ValueError("Invalid generation or type")
        except (KeyError, ValueError) as error:
            issues.append(dict(file="pokemon.csv", source_row=row_number, reason=str(error)))
            continue
        matches = by_name.get(name_key(row["Name"]), []) if row["Name"].strip() else []
        status = ("missing_name" if not row["Name"].strip() else
                  "ambiguous_name" if len(matches) > 1 else
                  "outside_catalogue_or_form" if not matches else "proposed_match")
        candidate = matches[0] if len(matches) == 1 else None
        if candidate and {row[c].lower() for c in ("Type 1", "Type 2") if row[c]} != pokemon_types[candidate["id"]]:
            status = "type_mismatch_review"
        if status == "proposed_match":
            mapped[external_id] = candidate["id"]
            differences = {key: dict(external=value, current=candidate[key]) for key, value in stats.items()
                           if value != candidate[key]}
            if differences:
                stat_differences.append(dict(external_id=external_id, pokemon_id=candidate["id"], differences=differences))
        mapping.append(dict(source_row=row_number, external_id=external_id, original_name=row["Name"],
                            pokemon_id=candidate["id"] if status == "proposed_match" else None, status=status))
    duplicate_mappings = [key for key, count in Counter(mapped.values()).items() if count > 1]
    if duplicate_mappings:
        issues.append(dict(file="pokemon.csv", reason="Multiple external entries map to one catalogue ID",
                           pokemon_ids=duplicate_mappings))

    def inspect_battles(filename, has_winner):
        columns = ("First_pokemon", "Second_pokemon", "Winner") if has_winner else ("First_pokemon", "Second_pokemon")
        records, seen, eligible_seen = [], {}, set()
        counts = Counter()
        for row_number, row in enumerate(tables[filename], 1):
            try:
                values = tuple(int(row[column]) for column in columns)
            except (KeyError, ValueError):
                counts["malformed_rows"] += 1
                records.append(dict(source_row=row_number, issues=["malformed_identifiers"]))
                continue
            first, second = values[:2]
            flags = []
            if any(value not in external_ids for value in values):
                flags.append("unresolved_external_id")
            if first == second:
                flags.append("self_matchup")
            if has_winner and values[2] not in (first, second):
                flags.append("winner_not_participant")
            eligible = not flags and first in mapped and second in mapped
            counts["rows"] += 1
            counts["invalid_rows"] += bool(flags)
            counts["catalogue_eligible_rows"] += eligible
            counts["outside_catalogue_rows"] += not flags and not eligible
            duplicate_of = seen.get(values)
            if duplicate_of:
                counts["exact_duplicate_extra_rows"] += 1
            else:
                seen[values] = row_number
            if eligible:
                eligible_seen.add(values)
            for flag in flags:
                counts[flag] += 1
            if flags or duplicate_of:
                records.append(dict(source_row=row_number, issues=flags, duplicate_of=duplicate_of))
        counts["catalogue_eligible_unique_rows"] = len(eligible_seen)
        return dict(counts=dict(counts), flagged_rows=records)

    return dict(inspection_version=1, source_url=manifest["source_url"], license=manifest["license"],
                source_description=manifest["battle_data"], sources=sources,
                catalogue_sha256=hashlib.sha256(catalogue_body).hexdigest(), issues=issues,
                mapping_status_counts=dict(Counter(row["status"] for row in mapping)), proposed_mapping=mapping,
                catalogue_without_proposed_match=[r["name"] for r in game["pokemon"] if r["id"] not in mapped.values()],
                mapped_stat_differences=stat_differences,
                combats=inspect_battles("combats.csv", True), tests=inspect_battles("tests.csv", False),
                note="Inspection only. Proposed name matches need approval. No raw files, SQL rows or simulator predictions changed. "
                     "Repeated identical outcomes might be repeated observations or duplicate exports; the source cannot establish independence.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DESTINATION)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    result = inspect(args.directory)
    write_report(result, args.report)
    print(json.dumps({key: result[key] for key in ("mapping_status_counts", "catalogue_without_proposed_match", "issues")}, indent=2))
    for key in ("combats", "tests"):
        print(key + ": " + json.dumps(result[key]["counts"], sort_keys=True))
    print(f"Stat differences in {len(result['mapped_stat_differences'])} proposed matches. Report: {args.report}")
