"""Opt-in real queries: MySQL fixtures roll back, MongoDB uses a unique test DB.

Run setup first, then RUN_QUERY_TESTS=1 with the regular project credentials.
No global MySQL CREATE/DROP grant is needed. Auto-increment gaps may remain.
"""
from contextlib import contextmanager
from copy import deepcopy
import os
import unittest
import uuid
from unittest.mock import patch

import pymysql

from backend.catalog import catalog
from backend.config import sql_options
from backend.db import mongo_client
from backend.teams.service import get_team, default_moves
from backend.team_analysis.recommendations import recommend, rank_candidates
from backend.team_analysis.service import analyse
from backend.analytics.strategy import report
from backend.errors import ValidationError


@unittest.skipUnless(os.getenv("RUN_QUERY_TESTS") == "1", "Set RUN_QUERY_TESTS=1 for real query fixtures")
class MySQLRecommendationTests(unittest.TestCase):
    def setUp(self):
        from scripts.run_local import load_environment
        load_environment()
        self.connection = pymysql.connect(**sql_options(), cursorclass=pymysql.cursors.DictCursor)
        self.connection.begin()
        self.cursor = self.connection.cursor()
        self.addCleanup(self.connection.close)
        self.addCleanup(self.connection.rollback)
        self.addCleanup(self.cursor.close)
        @contextmanager
        def tx():
            yield self.cursor
        for module in ("backend.db.transaction", "backend.teams.service.transaction"):
            mock = patch(module, tx);mock.start();self.addCleanup(mock.stop)
        catalog.cache_clear();self.addCleanup(catalog.cache_clear)
        self.cursor.execute("INSERT INTO trainers(name) VALUES ('SQL query fixture')")
        self.trainer = self.cursor.lastrowid
        self.cursor.execute("INSERT INTO teams(trainer_id,name) VALUES (%s,'Query fixture')", (self.trainer,))
        self.team = self.cursor.lastrowid

    def add_owned(self, pokemon_id):
        self.cursor.execute("INSERT INTO owned_pokemon(trainer_id,pokemon_id,source) VALUES (%s,%s,'reward')", (self.trainer, pokemon_id))
        return dict(owned_id=self.cursor.lastrowid, pokemon=catalog()[0][pokemon_id])

    def roster(self, ids):
        for slot, id in enumerate(ids, 1):
            member = self.add_owned(id)
            self.cursor.execute("INSERT INTO team_members VALUES (%s,%s,%s,%s)", (self.team, slot, member["owned_id"], self.trainer))
            for move_slot, move in enumerate(default_moves(member["pokemon"]), 1):
                self.cursor.execute("INSERT INTO team_member_moves VALUES (%s,%s,%s,%s)", (self.team, slot, move_slot, move))

    def compare(self, candidates):
        team = get_team(self.trainer, self.team)
        expected = rank_candidates(team["members"], candidates)
        actual = recommend(self.trainer, self.team)
        self.assertEqual([(s["owned_id"], s["replace_owned_id"]) for s in actual["suggestions"]],
                         [(s["owned_id"], s["replace_owned_id"]) for s in expected["suggestions"]])
        self.assertEqual(actual["before"]["coverage"], expected["before"]["coverage"])
        if expected["before"]["exposure"] is None:
            self.assertIsNone(actual["before"]["exposure"])
        else:
            self.assertAlmostEqual(actual["before"]["exposure"], expected["before"]["exposure"], places=8)
        for a, e in zip(actual["suggestions"], expected["suggestions"]):
            self.assertAlmostEqual(a["after"]["exposure"], e["after"]["exposure"], places=8)
            self.assertEqual(a["after"]["coverage"], e["after"]["coverage"])
            self.assertEqual(a["budget"]["total"], e["budget"]["total"])
        return actual

    def test_additions_dual_types_immunity_and_duplicate_species(self):
        self.roster([6, 76])
        candidates = [self.add_owned(id) for id in (7, 25, 94, 131, 150, 7)]
        self.compare(candidates)
        matchups = {r["type"]: r for r in analyse(self.trainer, self.team)["matchups"]}
        self.assertEqual(matchups["ground"]["immune"], 1)  # Charizard.
        self.assertEqual(matchups["water"]["double_weak"], 1)  # Golem.

    def test_full_team_replacements_and_budget(self):
        self.roster([1, 4, 7, 25, 74, 92])
        result = self.compare([self.add_owned(id) for id in (6, 76, 131, 150, 94)])
        self.assertTrue(all(s["replace_owned_id"] is not None and s["budget"]["total"] <= 30 for s in result["suggestions"]))

    def test_empty_team_and_no_candidates(self):
        self.compare([])
        self.compare([self.add_owned(id) for id in (1, 4, 7, 25)])

    def test_overbudget_legacy_team_and_ownership(self):
        self.roster([150] * 6)
        self.assertEqual(self.compare([self.add_owned(7)])["suggestions"], [])
        with self.assertRaises(ValidationError):
            recommend(self.trainer + 99999, self.team)

    def test_legendary_candidates_never_duplicate_retained_species(self):
        self.roster([150])
        duplicate = self.add_owned(150)
        self.cursor.execute('UPDATE owned_pokemon SET is_shiny=TRUE WHERE id=%s', (duplicate['owned_id'],))
        result = self.compare([duplicate, self.add_owned(144), self.add_owned(7)])
        self.assertNotIn(duplicate['owned_id'], [s['owned_id'] for s in result['suggestions']])

    def test_full_team_recommendations_can_repair_one_legacy_legend_duplicate(self):
        self.roster([144, 144, 10, 13, 19, 21])
        result = self.compare([self.add_owned(7), self.add_owned(150)])
        self.assertTrue(result['suggestions'])
        self.cursor.execute('SELECT owned_id FROM team_members WHERE team_id=%s AND slot IN (1,2)', (self.team,))
        duplicates = {r['owned_id'] for r in self.cursor.fetchall()}
        self.assertTrue(all(s['replace_owned_id'] in duplicates for s in result['suggestions']))


@unittest.skipUnless(os.getenv("RUN_QUERY_TESTS") == "1", "Set RUN_QUERY_TESTS=1 for real query fixtures")
class MongoStrategyTests(unittest.TestCase):
    def setUp(self):
        from scripts.run_local import load_environment
        load_environment()
        self.client = mongo_client()
        self.name = "pokedex_query_test_" + uuid.uuid4().hex
        self.battles = self.client[self.name].battles
        self.addCleanup(self.client.close)
        self.addCleanup(lambda: self.client.drop_database(self.name))

    def battle(self, status, moves, **changes):
        row = dict(_id=str(uuid.uuid4()), trainer_id=123, rules_version="prototype-2", difficulty="medium", status=status,
                   initial=dict(player=dict(members=[dict(id=1)])),
                   prediction=dict(method="move-pressure-1", label="favoured"),
                   turns=[dict(kind="turn", events=[dict(kind="move", side="player", move_id=id, move=f"move-{id}", damage=damage, hit=hit),
                                                    dict(kind="move", side="opponent", move_id=999, move="ignored", damage=999, hit=True)])
                          for id, damage, hit in moves])
        row.update(changes)
        self.battles.insert_one(row)
        return row

    def test_filters_misses_repetition_samples_and_prediction_outcomes(self):
        repeated = [(33, 10, True)] * 7 + [(44, 20, True)]
        mixed = [(33, 6, True)] * 4 + [(44, 0, False)] * 4
        self.battle("win", repeated)
        self.battle("loss", mixed)
        self.battle("draw", [(33, 0, False)] * 4)
        self.battle("win", repeated, rules_version="prototype-1")
        self.battle("win", repeated, difficulty="hard")
        self.battle("active", repeated)
        self.battle("win", repeated, trainer_id=999)
        forfeited = self.battle("loss", repeated)
        self.battles.update_one({"_id": forfeited["_id"]}, {"$push": {"turns": dict(kind="forfeit", events=[dict(kind="forfeit")])}})
        legacy = self.battle("draw", [])
        self.battles.update_one({"_id": legacy["_id"]}, {"$unset": {"prediction": ""}})
        result = report(self.battles, 123, "prototype-2", "medium")
        self.assertEqual(result["battles"], 4)
        moves = {r["_id"]: r for r in result["moves"]}
        self.assertEqual(moves[33]["attempts"], 15)
        self.assertEqual(moves[33]["damage"], 94)
        self.assertAlmostEqual(moves[33]["hit_rate"], 11 / 15)
        self.assertEqual(moves[44]["attempts"], 5)
        self.assertEqual(moves[44]["damage_per_attempt"], 4)
        self.assertNotIn(999, moves)
        patterns = {r["_id"]["pattern"]: r for r in result["repetition"]}
        self.assertEqual(patterns["high repetition"]["wins"], 1)
        self.assertEqual(patterns["mixed moves"]["losses"], 1)
        self.assertEqual(sum(r["battles"] for r in result["predictions"]), 3)
        self.assertEqual(report(self.battles, 123, "prototype-1", "medium")["battles"], 1)
        self.assertEqual(report(self.battles, 123, "unknown", "medium")["moves"], [])

    def test_repetition_boundary_and_invalid_filters(self):
        self.battle("win", [(33, 10, True)] * 6 + [(44, 10, True)] * 2)
        result = report(self.battles, 123, "prototype-2", "medium")
        self.assertEqual(result["repetition"][0]["_id"]["pattern"], "high repetition")
        for rules, difficulty in (({}, ""), ("", ""), ("prototype-2", "impossible")):
            with self.assertRaises(ValidationError):
                report(self.battles, 123, rules, difficulty)


if __name__ == "__main__":
    unittest.main()
