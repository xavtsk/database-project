"""Validation and opt-in MongoDB fixtures for observed simulator 1v1 outcomes."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import unittest
from unittest.mock import Mock, patch
import uuid

from backend.analytics.matchups import report
from backend.config import ROOT
from backend.db import mongo_client
from backend.errors import ValidationError

POKEMON = [dict(id=id, name=name) for id, name in ((1, 'bulbasaur'), (4, 'charmander'), (7, 'squirtle'))]


class MatchupValidationTests(unittest.TestCase):
    def test_invalid_ids_and_filters_fail_before_database_access(self):
        for first, second, rules, difficulty in (
                ('x', 7, 'prototype-2', ''), (True, 7, 'prototype-2', ''), (1.5, 7, 'prototype-2', ''),
                (0, 7, 'prototype-2', ''), (152, 7, 'prototype-2', ''), (4, 4, 'prototype-2', ''),
                ({'$gt': 0}, 7, 'prototype-2', ''), (4, 7, '', ''), (4, 7, {}, ''),
                (4, 7, 'prototype-2', 'impossible')):
            with self.subTest(first=first, rules=rules, difficulty=difficulty), \
                    patch('backend.analytics.matchups.query') as sql:
                logs = Mock()
                with self.assertRaises(ValidationError):
                    report(logs, 101, first, second, rules, difficulty)
                logs.aggregate.assert_not_called()
                sql.assert_not_called()


@unittest.skipUnless(os.getenv('RUN_QUERY_TESTS') == '1', 'Set RUN_QUERY_TESTS=1 for simulator matchup fixtures')
class MongoMatchupTests(unittest.TestCase):
    def setUp(self):
        from scripts.run_local import load_environment
        load_environment()
        self.client = mongo_client()
        self.database = 'pokedex_matchup_test_' + uuid.uuid4().hex
        self.addCleanup(self.client.close)
        self.addCleanup(lambda: self.client.drop_database(self.database))
        validator = json.loads((ROOT / 'database/nosql/battle_validator.json').read_text())
        self.logs = self.client[self.database].create_collection('battles', validator=validator)
        sql = patch('backend.analytics.matchups.query', return_value=POKEMON)
        sql.start(); self.addCleanup(sql.stop)

    def battle(self, status='win', first=4, second=7, **changes):
        player, opponent = dict(active=0, members=[dict(id=first)]), dict(active=0, members=[dict(id=second)])
        row = dict(_id=str(uuid.uuid4()), trainer_id=101, difficulty='medium', rules_version='prototype-2',
                   revision=1, status=status, started_at=datetime.now(timezone.utc), turn_count=4,
                   initial=dict(player=deepcopy(player), opponent=deepcopy(opponent)),
                   player=player, opponent=opponent, turns=[])
        row.update(changes)
        self.logs.insert_one(row)
        return row

    def result(self, first=4, second=7, rules='prototype-2', difficulty='medium'):
        return report(self.logs, 101, first, second, rules, difficulty)

    def test_both_orientations_counts_draws_and_reverses_selected_perspective(self):
        self.battle('win', turn_count=4)
        self.battle('win', turn_count=6)
        self.battle('loss', turn_count=8)
        self.battle('loss', first=7, second=4, turn_count=10)
        self.battle('draw', first=7, second=4, turn_count=12)
        result = self.result()
        self.assertEqual(result['summary'], dict(battles=5, wins=3, losses=1, draws=1, average_turns=8, win_rate=.6))
        roles = {r['selected_side']: r for r in result['rows']}
        self.assertEqual(roles['player']['battles'], 3)
        self.assertEqual(roles['opponent']['wins'], 1)
        self.assertEqual(roles['opponent']['draws'], 1)
        reverse = self.result(7, 4)['summary']
        self.assertEqual((reverse['wins'], reverse['losses'], reverse['draws']), (1, 3, 1))
        self.assertEqual(reverse['win_rate'], .2)

    def test_scope_rules_difficulty_and_genuine_starting_1v1(self):
        self.battle()
        self.battle('active')
        self.battle(trainer_id=102)
        self.battle(rules_version='prototype-1')
        self.battle(difficulty='hard')
        self.battle(first=1)
        self.battle('loss', turns=[dict(kind='forfeit', events=[])])
        self.battle('loss', turns=[dict(kind='turn', events=[dict(kind='forfeit')])])
        for player, opponent in (([dict(id=4)] * 2, [dict(id=7)]),
                                 ([dict(id=4)], [dict(id=7)] * 2), ([], [])):
            # Even if the final state has one survivor on each side, this isn't 1v1.
            self.battle(initial=dict(player=dict(members=player), opponent=dict(members=opponent)))
        self.battle(initial={})
        self.battle(initial=dict(player=dict(members='malformed'), opponent=dict(members=[dict(id=7)])))
        self.assertEqual(self.result()['summary']['battles'], 1)
        all_difficulties = self.result(difficulty='')
        self.assertEqual(all_difficulties['summary']['battles'], 2)
        self.assertEqual({r['difficulty'] for r in all_difficulties['rows']}, {'medium', 'hard'})
        self.assertEqual(self.result(rules='prototype-1')['summary']['battles'], 1)

    def test_empty_results_have_no_invented_win_rate(self):
        summary = self.result()['summary']
        self.assertEqual(summary['battles'], 0)
        self.assertIsNone(summary['win_rate'])
        self.assertEqual(self.result()['rows'], [])

    def test_all_matching_documents_count_once_and_shinies_share_species(self):
        for i in range(60):
            self.battle(initial=dict(player=dict(members=[dict(id=4, is_shiny=bool(i % 2))]),
                                     opponent=dict(members=[dict(id=7)])),
                        turns=[dict(kind='turn', events=[dict(kind='move', side='player')])] * 3)
        result = self.result()
        self.assertEqual(result['summary']['battles'], 60)  # Not limited to the history's latest 50.
        self.assertEqual(result['summary']['wins'], 60)

    def test_api_uses_session_trainer_and_returns_read_only_aggregate(self):
        from backend.app import create_app
        self.battle()
        self.battle('loss', trainer_id=102)
        with patch('backend.app.check_mysql'), patch('backend.app.mongo_client', return_value=self.client), \
                patch('backend.app.mongo_database', return_value=self.client[self.database]), \
                patch('backend.teams.service.trainer', side_effect=lambda id: dict(id=id)):
            app = create_app({'TESTING': True})
            client = app.test_client()
            self.assertEqual(client.get('/api/analytics/matchups').status_code, 400)
            with client.session_transaction() as session:
                session['trainer_id'] = 101
            response = client.get('/api/analytics/matchups?pokemon_id=4&opponent_id=7&difficulty=medium&trainer_id=102')
            self.assertEqual(response.status_code, 200, response.json)
            self.assertEqual(response.json['source'], 'mongodb')
            self.assertEqual(response.json['summary']['wins'], 1)
            self.assertEqual(response.json['summary']['losses'], 0)
            self.assertEqual(client.get('/api/analytics/matchups?pokemon_id=4&opponent_id=4').status_code, 400)
            self.assertEqual(self.logs.count_documents({}), 2)
