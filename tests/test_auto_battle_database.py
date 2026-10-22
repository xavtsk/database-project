"""Opt-in saved auto turns and idempotent SQL reward, with rollback fixtures."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import random
import unittest
from unittest.mock import patch
import uuid

import pymysql

from backend.config import ROOT, sql_options
from backend.db import mongo_client
from backend.battles.automation import POLICY
from backend.battles.service import act, get_battle
from backend.errors import ValidationError
from tests.test_battle_engine import battle, fighter


@unittest.skipUnless(os.getenv("RUN_QUERY_TESTS") == "1", "Set RUN_QUERY_TESTS=1 for saved auto-battle checks")
class SavedAutoBattleTests(unittest.TestCase):
    def setUp(self):
        from scripts.run_local import load_environment
        load_environment()
        self.client = mongo_client()
        self.database = "pokedex_auto_test_" + uuid.uuid4().hex
        self.addCleanup(self.client.close)
        self.addCleanup(lambda: self.client.drop_database(self.database))
        validator = json.loads((ROOT / "database/nosql/battle_validator.json").read_text())
        self.logs = self.client[self.database].create_collection("battles", validator=validator)
        self.connection = pymysql.connect(**sql_options(), cursorclass=pymysql.cursors.DictCursor)
        self.connection.begin()
        self.addCleanup(self.connection.close)
        self.addCleanup(self.connection.rollback)
        self.cursor = self.connection.cursor()
        self.addCleanup(self.cursor.close)
        self.cursor.execute("INSERT INTO trainers(name) VALUES ('Auto battle fixture')")
        self.trainer_id = self.cursor.lastrowid

        @contextmanager
        def transaction():
            yield self.cursor
        mock = patch("backend.battles.service.transaction", transaction)
        mock.start();self.addCleanup(mock.stop)
        self.chart = {("normal", "normal"): 1}
        mock = patch("backend.battles.service.catalog", return_value=({}, [], self.chart))
        mock.start();self.addCleanup(mock.stop)

    def saved(self, player=None):
        row = battle(player=player)
        row.update(_id=str(uuid.uuid4()), trainer_id=self.trainer_id, rules_version="prototype-2", revision=0,
                   started_at=datetime.now(timezone.utc), initial=deepcopy({k: row[k] for k in ("player", "opponent")}), reward=None)
        self.logs.insert_one(row)
        return row

    def test_auto_and_manual_turns_persist_with_existing_validator(self):
        from backend.app import create_app
        row = self.saved(player=[fighter("fainted"), fighter("replacement")])
        self.logs.update_one({"_id": row["_id"]}, {"$set": {"player.members.0.hp": 0}})
        @contextmanager
        def fixture_transaction(read_only=False):
            yield self.cursor
        with patch("backend.app.mongo_client", return_value=self.client), \
                patch("backend.app.mongo_database", return_value=self.client[self.database]), \
                patch("backend.db.transaction", fixture_transaction):
            app = create_app({"TESTING": True})
            client = app.test_client()
            with client.session_transaction() as session:
                session.update(trainer_id=self.trainer_id, csrf="fixture")
            response = client.post(f"/api/battles/{row['_id']}/actions", headers={"X-CSRF-Token": "fixture"},
                                   json=dict(revision=0, action=dict(kind="auto")))
            self.assertEqual(response.status_code, 200, response.json)
            replaced = response.json
        self.assertEqual(replaced["turn_count"], 0)
        self.assertEqual(replaced["turns"][-1]["policy"], POLICY)
        attacked = act(self.logs, self.trainer_id, row["_id"], 1, dict(kind="auto"), random.Random(1))
        manual = act(self.logs, self.trainer_id, row["_id"], 2, dict(kind="move", move_id=2), random.Random(1))
        saved = self.logs.find_one({"_id": row["_id"]})
        self.assertEqual([t["controller"] for t in saved["turns"]], ["auto", "auto", "manual"])
        self.assertEqual(saved["revision"], 3)
        self.assertIn("move_type", saved["turns"][1]["events"][0])
        with self.assertRaisesRegex(ValidationError, "Battle changed"):
            act(self.logs, self.trainer_id, row["_id"], 1, dict(kind="auto"))
        self.assertEqual(self.logs.find_one({"_id": row["_id"]})["revision"], 3)

    def test_auto_victory_and_repeated_reads_grant_one_reward(self):
        row = self.saved()
        self.logs.update_one({"_id": row["_id"]}, {"$set": {"opponent.members.0.hp": 1}})
        reward = dict(pokemon_id=1, name="bulbasaur", rarity="common", roll=.1, delivered=False)
        with patch("backend.battles.service.select_reward", return_value=reward):
            result = act(self.logs, self.trainer_id, row["_id"], 0, dict(kind="auto"), random.Random(1))
        self.assertEqual(result["status"], "win")
        self.assertTrue(result["reward"]["delivered"])
        for _ in range(2):
            self.assertEqual(get_battle(self.logs, self.trainer_id, row["_id"])["reward"]["owned_id"], result["reward"]["owned_id"])
        self.cursor.execute("SELECT COUNT(*) AS total FROM battle_rewards WHERE battle_id=%s", (row["_id"],))
        self.assertEqual(self.cursor.fetchone()["total"], 1)
        self.cursor.execute("SELECT COUNT(*) AS total FROM owned_pokemon WHERE trainer_id=%s", (self.trainer_id,))
        self.assertEqual(self.cursor.fetchone()["total"], 1)
