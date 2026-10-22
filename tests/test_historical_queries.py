"""Approved historical parsing and opt-in transactional MySQL query fixtures."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

import pymysql

from backend.analytics.historical import MATCHUPS_SQL, matchup
from backend.config import sql_options
from backend.errors import ValidationError
from scripts.data_import.import_historical import MAPPING, load, prepare


class HistoricalPreparationTests(unittest.TestCase):
    def test_reviewed_mapping_and_duplicate_lineage(self):
        source, pokemon, combats, audit = prepare()
        self.assertEqual(len(pokemon), 800)
        self.assertEqual(len(combats), 50000)
        self.assertEqual(audit["matched_pokemon"], 150)
        self.assertEqual(audit["duplicate_extra_rows"], 1952)
        self.assertEqual(audit["catalogue_eligible_unique_rows"], 1589)
        for row_number, first, second, winner, duplicate_of in combats:
            if duplicate_of:
                self.assertLess(duplicate_of, row_number)
                self.assertEqual(combats[duplicate_of - 1][1:4], (first, second, winner))
        self.assertEqual(source[3], audit["manifest_sha256"])

    def test_unapproved_mapping_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            approval = json.loads(MAPPING.read_text(encoding="utf-8"))
            approval["matches"][0]["pokemon_id"] = 151
            path = Path(temporary) / "mapping.json"
            path.write_text(json.dumps(approval), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "reviewed mapping"):
                prepare(mapping_path=path)

    def test_invalid_matchups_fail_before_database_access(self):
        for first, second in (("1 OR 1=1", "4"), (0, 4), (1, 152), (4, 4)):
            with self.assertRaises(ValidationError):
                matchup(first, second)


@unittest.skipUnless(os.getenv("RUN_QUERY_TESTS") == "1", "Set RUN_QUERY_TESTS=1 for real query fixtures")
class HistoricalSQLTests(unittest.TestCase):
    def setUp(self):
        from scripts.run_local import load_environment
        load_environment()
        self.connection = pymysql.connect(**sql_options())
        self.connection.begin()
        self.addCleanup(self.connection.close)
        self.addCleanup(self.connection.rollback)
        self.cursor = self.connection.cursor()
        self.addCleanup(self.cursor.close)
        self.source = ("fixture:" + uuid.uuid4().hex, "fixture", "test fixture", "f" * 64)
        self.pokemon = [
            (101, "Bulbasaur", "matched", 1, 45, 49, 49, 65, 65, 45, "grass", "poison"),
            (202, "Charmander", "matched", 4, 39, 52, 43, 60, 50, 65, "fire", None),
            (303, "Mega Venusaur", "outside_catalogue_or_form", None, 80, 100, 123, 122, 120, 80, "grass", "poison")]
        self.combats = [(1, 101, 202, 101, None), (2, 101, 202, 101, 1),
                        (3, 202, 101, 202, None), (4, 101, 303, 101, None)]
        self.source_id, _ = load(self.cursor, self.source, self.pokemon, self.combats)

    def test_rerun_verifies_same_rows_and_role_query_excludes_duplicates_and_forms(self):
        source_id, action = load(self.cursor, self.source, self.pokemon, self.combats)
        self.assertEqual((source_id, action), (self.source_id, "verified_existing"))
        with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(MATCHUPS_SQL, (source_id, 1, 4))
            rows = cursor.fetchall()
            self.assertEqual([(r["attacker_role"], r["battles"], int(r["wins"]), int(r["losses"])) for r in rows],
                             [("first", 1, 1, 0), ("second", 1, 0, 1)])
            cursor.execute(MATCHUPS_SQL, (source_id, 1, 7))
            self.assertEqual(cursor.fetchall(), ())
        changed = self.combats[:]
        changed[0] = (1, 101, 202, 202, None)
        changed[1] = (2, 101, 202, 202, 1)
        with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
            load(self.cursor, self.source, self.pokemon, changed)

    def test_checks_foreign_keys_and_mapping_constraints(self):
        for first, second, winner, duplicate_of, expected in (
            (101, 303, 202, None, 3819),  # Existing winner is not a participant.
            (101, 101, 101, None, 3819),  # Self matchup.
            (101, 202, 101, 999, 3819),  # Duplicate must refer to an earlier row.
            (101, 999, 101, None, 1452),  # Unresolved participant.
            (101, 202, 101, 0, 3819),  # Duplicate source rows are positive.
        ):
            with self.subTest(first=first, second=second, winner=winner, duplicate_of=duplicate_of):
                with self.assertRaises(pymysql.MySQLError) as caught:
                    self.cursor.execute("INSERT INTO historical_combats VALUES (%s,10,%s,%s,%s,%s)",
                                        (self.source_id, first, second, winner, duplicate_of))
                self.assertEqual(caught.exception.args[0], expected)
        with self.assertRaises(pymysql.MySQLError) as caught:
            self.cursor.execute("UPDATE historical_pokemon SET mapping_status='matched' WHERE source_id=%s AND external_id=303", (self.source_id,))
        self.assertEqual(caught.exception.args[0], 3819)

    def test_importer_rejects_missing_different_or_indirect_duplicate_lineage(self):
        for first, second, winner, duplicate_of in ((101, 202, 101, 5), (101, 202, 202, 1), (101, 202, 101, 2)):
            with self.subTest(duplicate_of=duplicate_of):
                with self.assertRaisesRegex(ValueError, "earlier original"):
                    load(self.cursor, self.source, self.pokemon, self.combats + [(10, first, second, winner, duplicate_of)])

    def test_historical_api_uses_selected_profile_and_returns_live_query_results(self):
        from backend.app import create_app
        @contextmanager
        def fixture_transaction(read_only=False):
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                yield cursor
        self.cursor.execute("INSERT INTO trainers(name) VALUES ('Historical API fixture')")
        trainer_id = self.cursor.lastrowid
        with patch("backend.db.transaction", fixture_transaction), patch("backend.analytics.historical.SOURCE_URL", "fixture"):
            app = create_app({"TESTING": True})
            self.addCleanup(app.extensions["mongo"].close)
            client = app.test_client()
            self.assertEqual(client.get("/api/analytics/historical").status_code, 400)
            with client.session_transaction() as session:
                session["trainer_id"] = trainer_id
            response = client.get("/api/analytics/historical?pokemon_id=1&opponent_id=4")
            self.assertEqual(response.status_code, 200, response.json)
            self.assertEqual(response.json["battles"], 2)
            self.assertEqual(response.json["source"]["id"], self.source_id)
            self.assertEqual(len(response.json["rows"]), 2)
            self.assertEqual(client.get("/api/analytics/historical?pokemon_id=4&opponent_id=4").status_code, 400)
