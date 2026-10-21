"""Reward probability boundaries and team species rules, without databases."""
from copy import deepcopy
import unittest
from unittest.mock import Mock, patch

from backend.battles.engine import combatant
from backend.battles.service import REWARD_ODDS, act, eligible_reward, select_reward, start_battle
from backend.errors import ValidationError
from backend.teams.limits import validate_team_species
from tests.test_team_advice import pokemon


class CollectionRewardTests(unittest.TestCase):
    def test_independent_shiny_boundary_for_every_rarity(self):
        pool = {i: dict(id=i, name=tier, rarity=tier) for i, tier in
                enumerate(('common', 'uncommon', 'rare', 'legendary'), 1)}
        for tier_roll, expected_tier in ((0, 'common'), (.60, 'uncommon'), (.85, 'rare'), (.98, 'legendary')):
            for shiny_roll, expected in ((0, True), (.009999, True), (.01, False), (.999, False)):
                with self.subTest(tier=expected_tier, shiny=shiny_roll), \
                        patch('backend.battles.service.catalog', return_value=(pool, [], {})):
                    rng = Mock()
                    rng.random.side_effect = [tier_roll, shiny_roll]
                    rng.choice.side_effect = lambda candidates: candidates[0]
                    reward = select_reward(rng)
                    self.assertEqual(reward['rarity'], expected_tier)
                    self.assertEqual(reward['is_shiny'], expected)
                    self.assertEqual(rng.random.call_count, 2)

    def test_reroll_preserves_shiny_prefers_same_tier_and_is_retry_stable(self):
        reward = dict(pokemon_id=1, name='full', rarity='common', roll=.2, shiny_roll=.005, is_shiny=True)
        before = deepcopy(reward)
        pool = [dict(id=2, name='available', rarity='common'), dict(id=150, name='mewtwo', rarity='legendary')]
        result = eligible_reward(reward, pool, 'battle')
        self.assertEqual(result['pokemon_id'], 2)
        self.assertTrue(result['is_shiny'])
        self.assertEqual(result['shiny_roll'], .005)
        self.assertEqual(eligible_reward(reward, pool, 'battle'), result)
        self.assertEqual(reward, before)

    def test_difficulty_shiny_and_legendary_boundaries(self):
        pool = {i: dict(id=i, name=tier, rarity=tier) for i, tier in
                enumerate(('common', 'uncommon', 'rare', 'legendary'), 1)}
        for difficulty, common_end, legendary_start, shiny_limit in (
                ('easy', .60, .97, .01), ('medium', .58, .95, .02), ('hard', .56, .93, .03)):
            for tier_roll, tier in ((common_end-1e-8, 'common'), (common_end, 'uncommon'),
                                    (legendary_start-1e-8, 'rare'), (legendary_start, 'legendary')):
                for shiny_roll, shiny in ((shiny_limit-1e-8, True), (shiny_limit, False)):
                    with self.subTest(difficulty=difficulty, tier=tier_roll, shiny=shiny_roll), \
                            patch('backend.battles.service.catalog', return_value=(pool, [], {})):
                        rng = Mock()
                        rng.random.side_effect = [tier_roll, shiny_roll]
                        rng.choice.side_effect = lambda candidates: candidates[0]
                        result = select_reward(rng, difficulty)
                        self.assertEqual(result['rarity'], tier)
                        self.assertEqual(result['is_shiny'], shiny)
                        self.assertEqual(result['odds'], REWARD_ODDS[difficulty])
                        self.assertAlmostEqual(sum(result['odds']['rarities'].values()), 1)

    def test_win_uses_saved_server_difficulty_and_odds_for_manual_and_auto(self):
        from datetime import datetime, timezone
        from tests.test_battle_engine import battle
        for action in (dict(kind='move', move_id=1, difficulty='easy'), dict(kind='auto', difficulty='easy')):
            row = battle()
            row.update(_id='fixture', trainer_id=1, revision=0, difficulty='hard',
                       reward_odds=deepcopy(REWARD_ODDS['hard']), started_at=datetime.now(timezone.utc), reward=None)
            won = deepcopy(row)
            won.update(status='win', turns=[dict(kind='turn', events=[])])
            logs = Mock()
            logs.replace_one.return_value.matched_count = 1
            with patch('backend.battles.service.get_battle', return_value=row), \
                    patch('backend.battles.service.resolve', return_value=won), \
                    patch('backend.battles.service.choose_action', return_value=(dict(kind='move', move_id=1), 'fixture')), \
                    patch('backend.battles.service.catalog', return_value=({}, [], {})), \
                    patch('backend.battles.service.select_reward', return_value={}) as choose, \
                    patch('backend.battles.service.deliver_reward', side_effect=lambda logs, saved: saved):
                act(logs, 1, 'fixture', 0, action)
            self.assertEqual(choose.call_args.args[1:], ('hard', REWARD_ODDS['hard']))

    def test_saved_odds_survive_later_configuration_changes(self):
        saved = deepcopy(REWARD_ODDS['hard'])
        rng = Mock()
        rng.random.side_effect = [.94, .025]
        rng.choice.side_effect = lambda candidates: candidates[0]
        with patch('backend.battles.service.catalog', return_value=({150: dict(id=150, name='mewtwo', rarity='legendary')}, [], {})), \
                patch.dict(REWARD_ODDS, hard=REWARD_ODDS['easy']):
            result = select_reward(rng, 'hard', saved)
        self.assertEqual(result['rarity'], 'legendary')
        self.assertTrue(result['is_shiny'])
        self.assertEqual(result['odds'], saved)

    def test_full_tier_fallback_uses_saved_difficulty_weights(self):
        # A .90 draw is above Hard's common/(common+legendary) split,
        # but below the old split. The Hard weights must award legendary.
        reward = dict(pokemon_id=1, name='full', rarity='rare', roll=.9, is_shiny=True,
                      odds=deepcopy(REWARD_ODDS['hard']), policy='difficulty-rewards-1')
        pool = [dict(id=2, name='common', rarity='common'), dict(id=150, name='mewtwo', rarity='legendary')]
        rng = Mock()
        rng.random.return_value = .90
        rng.choice.side_effect = lambda candidates: candidates[0]
        with patch('backend.battles.service.random.Random', return_value=rng):
            result = eligible_reward(reward, pool, 'fixture')
        self.assertEqual(result['rarity'], 'legendary')
        self.assertTrue(result['is_shiny'])

    def test_reroll_can_use_other_tier_and_legacy_rewards_stay_normal(self):
        reward = dict(pokemon_id=1, name='full', rarity='common', roll=.2)
        result = eligible_reward(reward, [dict(id=150, name='mewtwo', rarity='legendary')], 'battle')
        self.assertEqual(result['rarity'], 'legendary')
        self.assertFalse(result['is_shiny'])
        with self.assertRaisesRegex(ValidationError, 'pending'):
            eligible_reward(reward, [], 'battle')

    def test_eligible_choice_stays_the_same(self):
        reward = dict(pokemon_id=1, name='chosen', rarity='common', roll=.2, is_shiny=False)
        self.assertEqual(eligible_reward(reward, [dict(id=1, name='chosen', rarity='common')], 'id'), reward)

    def test_species_rules_combine_normal_shiny_and_allow_distinct_legends(self):
        legendary = dict(id=150, name='mewtwo', rarity='legendary')
        with self.assertRaisesRegex(ValidationError, 'Only one mewtwo'):
            validate_team_species([legendary, dict(legendary, is_shiny=True)])
        validate_team_species([legendary, dict(id=151, name='mew', rarity='legendary')])
        validate_team_species([dict(id=1, rarity='common')] * 6)

    def test_invalid_legacy_team_cannot_start_new_battle(self):
        p = dict(pokemon(), rarity='legendary')
        members = [dict(pokemon=p), dict(pokemon=dict(p, is_shiny=True))]
        logs = Mock()
        with patch('backend.battles.service.get_team', return_value=dict(members=members)):
            with self.assertRaisesRegex(ValidationError, 'Only one'):
                start_battle(logs, 1, 1, 'easy')
        logs.insert_one.assert_not_called()

    def test_shiny_combatants_have_same_stats_and_do_not_mutate_catalogue(self):
        normal = pokemon()
        shiny = dict(normal, is_shiny=True)
        a, b = combatant(normal, [1, 2, 3, 4]), combatant(shiny, [1, 2, 3, 4])
        self.assertFalse(a.pop('is_shiny'))
        self.assertTrue(b.pop('is_shiny'))
        self.assertEqual(a, b)
        self.assertNotIn('is_shiny', normal)
