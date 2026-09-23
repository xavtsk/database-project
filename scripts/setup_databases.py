"""Create the approved schema and import the catalogue without resetting player data.

Run from the root with: python3 -m scripts.setup_databases --fetch-dark
The SQL user must have permission to create/use SQL_DATABASE.
"""
import argparse
import json
import os
import re

import pymysql
import requests

from backend.config import ROOT, sql_options
from backend.db import mongo_client, mongo_database
from scripts.data_import.fetch_pokeapi import RawDownloader
from scripts.data_import.prepare_game_data import prepare, OUTPUT


def setup(fetch_dark=False):
    if fetch_dark:
        with requests.Session() as session:
            if RawDownloader(session).fetch("type", "dark", "types") is None:
                raise RuntimeError("Could not cache the required Dark type")
    data = prepare()
    OUTPUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    name = os.getenv("SQL_DATABASE", "pokedex_battle")
    if not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise ValueError("Invalid SQL_DATABASE")
    with pymysql.connect(**sql_options(database=False)) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4")
            cursor.execute(f"USE `{name}`")
            for statement in (ROOT / "database/relational/schema.sql").read_text().split(";"):
                if statement.strip():
                    cursor.execute(statement)
            # Dependencies require types before Pokémon-type and move references.
            for table in ("pokemon", "types", "moves", "pokemon_types", "pokemon_moves", "type_effectiveness"):
                rows = data[table]
                columns = list(rows[0])
                column_sql = ",".join(f"`{c}`" for c in columns)
                updates = ",".join(f"`{c}`=VALUES(`{c}`)" for c in columns)
                sql = f"INSERT INTO {table} ({column_sql}) VALUES ({','.join(['%s'] * len(columns))}) ON DUPLICATE KEY UPDATE {updates}"
                cursor.executemany(sql, [tuple(row[c] for c in columns) for row in rows])
                print(f"[SQL] {table}: {len(rows)} rows")
        connection.commit()
    with mongo_client() as client:
        database = mongo_database(client)
        if "battles" not in database.list_collection_names():
            validator = json.loads((ROOT / "database/nosql/battle_validator.json").read_text())
            database.create_collection("battles", validator=validator)
        database.battles.create_index([("trainer_id", 1), ("started_at", -1)])
        database.battles.create_index([("trainer_id", 1)], unique=True,
                                      partialFilterExpression={"status": "active"}, name="one_active_battle_per_trainer")
        print("[MongoDB] battle collection and indexes ready")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-dark", action="store_true")
    setup(parser.parse_args().fetch_dark)
