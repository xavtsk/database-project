"""Import only the approved Weedle's Cave source and reviewed identity mapping.

All validation runs before SQL writes. Source rows retain first-attacker order.
Reruns verify the stored rows instead of adding duplicate observations.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

import pymysql

from backend.config import sql_options
from backend.db import require_mysql
from scripts.data_import.audit_game_data import write_report
from scripts.data_import.fetch_historical import DESTINATION, ROOT
from scripts.data_import.inspect_historical import STATS, inspect

MAPPING = ROOT / "data/processed/historical_mapping.json"
REPORT = ROOT / ".local/historical-import.json"


def prepare(directory=DESTINATION, mapping_path=MAPPING):
    directory = Path(directory)
    approval = json.loads(Path(mapping_path).read_text(encoding="utf-8"))
    inspection = inspect(directory)
    expected = {r["file"]: r["sha256"] for r in approval["source_files"]}
    actual = {r["file"]: r["sha256"] for r in inspection["sources"]}
    if expected != actual or inspection["issues"]:
        raise ValueError("Historical source differs from the approved inspection")
    reviewed = {r["external_id"]: r["pokemon_id"] for r in approval["matches"]}
    proposed = {r["external_id"]: r["pokemon_id"] for r in inspection["proposed_mapping"] if r["pokemon_id"] is not None}
    if reviewed != proposed:
        raise ValueError("Current catalogue changes the reviewed mapping; inspect and approve a new mapping")
    # Re-read and re-hash the exact bytes that will be parsed for import.
    def rows(filename):
        body = (directory / filename).read_bytes()
        if hashlib.sha256(body).hexdigest() != expected[filename]:
            raise ValueError("Historical source changed during inspection")
        return list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))

    statuses = {r["external_id"]: r["status"] for r in inspection["proposed_mapping"]}
    pokemon = []
    for row in rows("pokemon.csv"):
        external_id = int(row["#"])
        status = "matched" if external_id in reviewed else statuses[external_id]
        if status not in ("matched", "outside_catalogue_or_form", "missing_name"):
            raise ValueError("Unreviewed historical mapping status")
        pokemon.append((external_id, row["Name"] or None, status, reviewed.get(external_id),
                        *(int(row[column]) for column in STATS), row["Type 1"].lower(), row["Type 2"].lower() or None))
    external_ids = {p[0] for p in pokemon}
    seen, combats = {}, []
    for source_row, row in enumerate(rows("combats.csv"), 1):
        first, second, winner = (int(row[c]) for c in ("First_pokemon", "Second_pokemon", "Winner"))
        if first == second or winner not in (first, second) or any(x not in external_ids for x in (first, second, winner)):
            raise ValueError(f"Invalid historical outcome at source row {source_row}")
        key = (first, second, winner)
        combats.append((source_row, first, second, winner, seen.get(key)))
        seen.setdefault(key, source_row)
    fingerprint = hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest()
    report = dict(status="validated", manifest_sha256=fingerprint, source_files=inspection["sources"],
                  pokemon_rows=len(pokemon), matched_pokemon=len(reviewed), combat_rows=len(combats),
                  duplicate_extra_rows=sum(row[-1] is not None for row in combats),
                  catalogue_eligible_unique_rows=inspection["combats"]["counts"]["catalogue_eligible_unique_rows"],
                  omitted_test_rows=inspection["tests"]["counts"]["rows"])
    source = ("weedles-cave:" + fingerprint, approval["source_url"], approval["license"], fingerprint)
    return source, pokemon, combats, report


def load(cursor, source, pokemon, combats):
    """Write through the caller's transaction; commit is the caller's responsibility."""
    # Validate duplicate lineage independently of the database's self-reference.
    originals, row_numbers = {}, set()
    for row, first, second, winner, duplicate_of in combats:
        if row <= 0 or row in row_numbers:
            raise ValueError("Invalid or repeated historical source-row key")
        row_numbers.add(row)
        if duplicate_of is not None:
            if duplicate_of >= row or originals.get(duplicate_of) != (first, second, winner):
                raise ValueError("Duplicate must reference an earlier original with the same ordered result")
        else:
            originals[row] = (first, second, winner)
    cursor.execute("SELECT id,source_url,license,manifest_sha256 FROM historical_sources WHERE dataset_key=%s FOR UPDATE", (source[0],))
    existing = cursor.fetchone()
    if existing:
        source_id = existing[0]
        if existing[1:] != source[1:]:
            raise ValueError("Stored historical provenance differs; refusing to overwrite")
        cursor.execute("SELECT external_id,original_name,mapping_status,pokemon_id,hp,attack,defense,special_attack,"
                       "special_defense,speed,type_1,type_2 FROM historical_pokemon WHERE source_id=%s ORDER BY external_id", (source_id,))
        if list(cursor.fetchall()) != sorted(pokemon):
            raise ValueError("Stored historical mappings differ; refusing to overwrite")
        cursor.execute("SELECT source_row,first_external_id,second_external_id,winner_external_id,duplicate_of_row "
                       "FROM historical_combats WHERE source_id=%s ORDER BY source_row", (source_id,))
        if list(cursor.fetchall()) != combats:
            raise ValueError("Stored historical results differ; refusing to overwrite")
        return source_id, "verified_existing"
    cursor.execute("INSERT INTO historical_sources(dataset_key,source_url,license,manifest_sha256) VALUES (%s,%s,%s,%s)", source)
    source_id = cursor.lastrowid
    cursor.executemany("INSERT INTO historical_pokemon(source_id,external_id,original_name,mapping_status,pokemon_id,"
                       "hp,attack,defense,special_attack,special_defense,speed,type_1,type_2) "
                       "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                       [(source_id, *row) for row in pokemon])
    cursor.executemany("INSERT INTO historical_combats(source_id,source_row,first_external_id,second_external_id,"
                       "winner_external_id,duplicate_of_row) VALUES (%s,%s,%s,%s,%s,%s)",
                       [(source_id, *row) for row in combats])
    return source_id, "inserted"


def initialize(cursor):
    """Create approved tables; never import data."""
    for statement in (ROOT / "database/relational/historical.sql").read_text(encoding="utf-8").split(";"):
        if statement.strip():
            cursor.execute(statement)


def run(directory=DESTINATION, report_path=REPORT):
    try:
        source, pokemon, combats, report = prepare(directory)
    except (ValueError, KeyError, OSError) as error:
        write_report(dict(status="rejected", reason=str(error)), report_path)
        raise
    write_report(report, report_path)
    with pymysql.connect(**sql_options()) as connection:
        require_mysql(connection)
        with connection.cursor() as cursor:
            initialize(cursor)
        # MySQL DDL commits implicitly; the data transaction starts after DDL.
        connection.begin()
        try:
            with connection.cursor() as cursor:
                source_id, action = load(cursor, source, pokemon, combats)
            connection.commit()
        except Exception:
            connection.rollback()
            report["status"] = "rolled_back"
            write_report(report, report_path)
            raise
    report.update(status="committed", source_id=source_id, action=action)
    write_report(report, report_path)
    print(f"[HISTORICAL] {action}: {len(pokemon)} identities, {len(combats)} result rows; "
          f"{report['catalogue_eligible_unique_rows']} distinct in-scope results. Audit: {report_path}")
    return report


if __name__ == "__main__":
    from scripts.run_local import load_environment
    load_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DESTINATION)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    run(args.directory, args.report)
