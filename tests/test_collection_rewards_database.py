"""Opt-in real MySQL/MongoDB checks, with SQL rollback and disposable logs."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import unittest
from unittest.mock import Mock, patch
import uuid

import pymysql

from backend.battles.service import deliver_reward, get_battle, select_reward
from backend.catalog import catalog
from backend.config import ROOT, sql_options
from backend.db import mongo_client
from backend.errors import ValidationError
from backend.teams.service import collection, default_moves, get_team, save_team
from tests.test_battle_engine import battle


@unittest.skipUnless(os.getenv('RUN_QUERY_TESTS') == '1', 'Set RUN_QUERY_TESTS=1 for collection reward fixtures')
class SavedCollectionRewardTests(unittest.TestCase):
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
        for module in ('backend.db.transaction', 'backend.teams.service.transaction', 'backend.battles.service.transaction'):
            mock = patch(module, tx)
            mock.start(); self.addCleanup(mock.stop)
        catalog.cache_clear(); self.addCleanup(catalog.cache_clear)
        self.cursor.execute("INSERT INTO trainers(name) VALUES ('Collection reward fixture')")
        self.trainer = self.cursor.lastrowid
        self.client = mongo_client()
        self.database = 'pokedex_collection_test_' + uuid.uuid4().hex
        self.addCleanup(self.client.close)
        self.addCleanup(lambda: self.client.drop_database(self.database))
        validator = json.loads((ROOT / 'database/nosql/battle_validator.json').read_text())
        self.logs = self.client[self.database].create_collection('battles', validator=validator)

    def owned(self, pokemon_id=1, shiny=False, count=1):
        for _ in range(count):
            self.cursor.execute("INSERT INTO owned_pokemon(trainer_id,pokemon_id,source,is_shiny) VALUES (%s,%s,'reward',%s)",
                                (self.trainer, pokemon_id, shiny))
        return self.cursor.lastrowid

    def winning(self, pokemon_id=1, shiny=False):
        p = catalog()[0][pokemon_id]
        row = battle()
        row.update(_id=str(uuid.uuid4()), trainer_id=self.trainer, status='win', rules_version='prototype-2', revision=1,
                   started_at=datetime.now(timezone.utc), initial=deepcopy({k: row[k] for k in ('player', 'opponent')}),
                   reward=dict(pokemon_id=pokemon_id, name=p['name'], rarity=p['rarity'], roll=.2,
                               is_shiny=shiny, shiny_roll=.005 if shiny else .5, delivered=False))
        self.logs.insert_one(row)
        return row

    def count(self, pokemon_id, shiny):
        self.cursor.execute('SELECT COUNT(*) AS n FROM owned_pokemon WHERE trainer_id=%s AND pokemon_id=%s AND is_shiny=%s',
                            (self.trainer, pokemon_id, shiny))
        return self.cursor.fetchone()['n']

    def member(self, owned_id, pokemon_id):
        return dict(owned_id=owned_id, moves=default_moves(catalog()[0][pokemon_id]))

    def test_six_normals_and_six_shinies_then_reroll_each_variant(self):
        self.owned(shiny=False, count=6)
        self.owned(shiny=True, count=6)
        for shiny in (False, True):
            row = self.winning(shiny=shiny)
            reward = deliver_reward(self.logs, row)['reward']
            self.assertNotEqual(reward['pokemon_id'], 1)
            self.assertEqual(reward['is_shiny'], shiny)
            self.assertEqual(reward['rerolled_from']['pokemon_id'], 1)
            self.assertEqual(self.count(1, shiny), 6)
            self.assertEqual(self.count(reward['pokemon_id'], shiny), 1)
        self.assertEqual(len(collection(self.trainer)), 14)

    def test_full_normal_does_not_block_shiny_and_reverse(self):
        self.owned(1, False, 6)
        self.owned(4, True, 6)
        for pokemon_id, shiny in ((1, True), (4, False)):
            result = deliver_reward(self.logs, self.winning(pokemon_id, shiny))['reward']
            self.assertEqual(result['pokemon_id'], pokemon_id)
            self.assertEqual(result['is_shiny'], shiny)
            self.assertEqual(self.count(pokemon_id, shiny), 1)

    def test_legendary_collection_can_exceed_six(self):
        self.owned(150, False, 6)
        result = deliver_reward(self.logs, self.winning(150))['reward']
        self.assertEqual(result['pokemon_id'], 150)
        self.assertEqual(self.count(150, False), 7)

    def test_difficulty_reward_odds_and_shiny_status_persist_through_retry(self):
        for difficulty, expected_tier, expected_shiny in (
                ('easy', 'rare', False), ('medium', 'legendary', False), ('hard', 'legendary', True)):
            rng = Mock()
            rng.random.side_effect = [.96, .025]
            rng.choice.side_effect = lambda candidates: candidates[0]
            reward = select_reward(rng, difficulty)
            self.assertEqual(reward['rarity'], expected_tier)
            self.assertEqual(reward['is_shiny'], expected_shiny)
            row = self.winning()
            self.logs.update_one({'_id': row['_id']}, {'$set': {'difficulty': difficulty, 'reward': reward}})
            delivered = get_battle(self.logs, self.trainer, row['_id'])['reward']
            self.logs.update_one({'_id': row['_id']}, {'$set': {'reward.delivered': False}})
            repaired = get_battle(self.logs, self.trainer, row['_id'])['reward']
            self.assertEqual(delivered, repaired)
            self.assertEqual(repaired['odds'], reward['odds'])
            self.assertEqual(repaired['is_shiny'], expected_shiny)

    def test_sql_award_repairs_failed_mongo_marker_without_reroll_or_second_grant(self):
        self.owned(1, True, 6)
        row = self.winning(1, True)
        failing_logs = Mock()
        failing_logs.update_one.side_effect = RuntimeError('simulated Mongo marker failure')
        with self.assertRaisesRegex(RuntimeError, 'marker failure'):
            deliver_reward(failing_logs, row)
        self.assertFalse(self.logs.find_one({'_id': row['_id']})['reward']['delivered'])
        self.cursor.execute('SELECT o.id,o.pokemon_id,o.is_shiny FROM battle_rewards r JOIN owned_pokemon o ON o.id=r.owned_id WHERE battle_id=%s', (row['_id'],))
        award = self.cursor.fetchone()
        repaired = get_battle(self.logs, self.trainer, row['_id'])['reward']
        self.assertEqual(repaired['owned_id'], award['id'])
        self.assertEqual(repaired['pokemon_id'], award['pokemon_id'])
        self.assertTrue(repaired['is_shiny'])
        self.assertEqual(get_battle(self.logs, self.trainer, row['_id'])['reward'], repaired)
        self.cursor.execute('SELECT COUNT(*) AS n FROM owned_pokemon WHERE trainer_id=%s', (self.trainer,))
        self.assertEqual(self.cursor.fetchone()['n'], 7)

    def test_team_rejects_normal_shiny_legend_duplicates_before_edits(self):
        normal = self.owned(150)
        shiny = self.owned(150, True)
        other = self.owned(151)
        team_id = save_team(self.trainer, 'Original', [self.member(normal, 150)])
        with self.assertRaisesRegex(ValidationError, 'Only one mewtwo'):
            save_team(self.trainer, 'Rejected edit', [self.member(normal, 150), self.member(shiny, 150)], team_id)
        self.assertEqual(get_team(self.trainer, team_id)['name'], 'Original')
        self.assertEqual(len(get_team(self.trainer, team_id)['members']), 1)
        save_team(self.trainer, 'Distinct species', [self.member(shiny, 150), self.member(other, 151)], team_id)
        members = get_team(self.trainer, team_id)['members']
        self.assertTrue(members[0]['pokemon']['is_shiny'])
        self.assertFalse(members[1]['pokemon']['is_shiny'])
        self.assertNotIn('is_shiny', catalog()[0][150])

    def test_normal_duplicates_and_shiny_metadata_survive_save(self):
        a, b = self.owned(), self.owned(shiny=True)
        team_id = save_team(self.trainer, 'Normal species duplicates', [self.member(a, 1), self.member(b, 1)])
        roster = get_team(self.trainer, team_id)['members']
        self.assertEqual([m['pokemon']['is_shiny'] for m in roster], [False, True])
        self.assertEqual([m['is_shiny'] for m in collection(self.trainer)], [False, True])

    def test_legacy_excess_copies_are_kept_and_do_not_gain_another(self):
        self.owned(count=7)
        reward = deliver_reward(self.logs, self.winning())['reward']
        self.assertNotEqual(reward['pokemon_id'], 1)
        self.assertEqual(self.count(1, False), 7)
