"""Offline tests of the agreed rules, using deliberately small combat fixtures."""
from copy import deepcopy
import random
import unittest

from backend.battles.engine import combatant, expected_damage, resolve, choose_move
from backend.errors import ValidationError
from scripts.data_import.prepare_game_data import prepare


def fighter(name="test", speed=50, types=None):
    return dict(id=1, name=name, types=types or ["normal"], hp=100, max_hp=100,
                stats=dict(attack=50, defense=50, special_attack=100, special_defense=50, speed=speed),
                moves=[dict(id=i, name=f"move-{i}", type="normal", damage_class="physical", power=40,
                            pp=10, remaining_pp=10, accuracy=None, priority=0) for i in range(1,5)])


def battle(player=None, opponent=None):
    return dict(status="active", turn_count=0, difficulty="easy", turns=[],
                player=dict(active=0,members=player or [fighter("player",100)]),
                opponent=dict(active=0,members=opponent or [fighter("opponent",20)]))


class BattleRulesTests(unittest.TestCase):
    def setUp(self):
        self.chart={(a,b):1 for a in ("normal","water","grass","ghost") for b in ("normal","water","grass","ghost")}

    def test_damage_formula_special_stat_stab_and_immunity(self):
        a,b=fighter(),fighter()
        move=a['moves'][0]
        self.assertEqual(expected_damage(a,b,move,self.chart),29)
        move['damage_class']='special'
        self.assertEqual(expected_damage(a,b,move,self.chart),40)
        self.assertEqual(expected_damage(a,b,move,self.chart,damage_cap=None),55)
        b['types']=['ghost'];self.chart[('normal','ghost')]=0
        self.assertEqual(expected_damage(a,b,move,self.chart),0)

    def test_attack_pp_miss_and_input_preservation(self):
        state=battle();state['player']['members'][0]['moves'][0]['accuracy']=0
        before=deepcopy(state)
        after=resolve(state,{'kind':'move','move_id':1},random.Random(1),self.chart)
        self.assertEqual(state,before)
        self.assertEqual(after['player']['members'][0]['moves'][0]['remaining_pp'],9)
        self.assertEqual(after['opponent']['members'][0]['hp'],100)
        self.assertFalse(after['turns'][0]['events'][0]['hit'])

    def test_faster_knockout_prevents_retaliation(self):
        state=battle();state['opponent']['members'][0]['hp']=1
        after=resolve(state,{'kind':'move','move_id':1},random.Random(1),self.chart)
        self.assertEqual(after['status'],'win')
        self.assertEqual(after['player']['members'][0]['hp'],100)

    def test_priority_beats_speed_and_ties_are_reproducible(self):
        state=battle();state['player']['members'][0]['hp']=1
        for move in state['opponent']['members'][0]['moves']:move['priority']=1
        after=resolve(state,{'kind':'move','move_id':1},random.Random(2),self.chart)
        self.assertEqual(after['status'],'loss')
        self.assertEqual(after['opponent']['members'][0]['hp'],100)
        tied=battle();tied['opponent']['members'][0]['stats']['speed']=100
        self.assertEqual(resolve(tied,{'kind':'move','move_id':1},random.Random(5),self.chart),resolve(tied,{'kind':'move','move_id':1},random.Random(5),self.chart))

    def test_voluntary_and_forced_switch(self):
        state=battle(player=[fighter('first'),fighter('second')])
        after=resolve(state,{'kind':'switch','slot':1},random.Random(1),self.chart)
        self.assertEqual(after['turn_count'],1)
        self.assertEqual(after['player']['members'][0]['hp'],100)
        self.assertLess(after['player']['members'][1]['hp'],100)
        state['player']['members'][0]['hp']=0
        with self.assertRaises(ValidationError):resolve(state,{'kind':'move','move_id':1},random.Random(1),self.chart)
        after=resolve(state,{'kind':'switch','slot':1},random.Random(1),self.chart)
        self.assertEqual(after['turn_count'],0)
        self.assertEqual(after['player']['members'][1]['hp'],100)
        with self.assertRaises(ValidationError):resolve(after,{'kind':'switch','slot':0},random.Random(1),self.chart)

    def test_opponent_replacement_is_free(self):
        state=battle(opponent=[fighter('first',1),fighter('second',1)])
        state['opponent']['members'][0]['hp']=1
        after=resolve(state,{'kind':'move','move_id':1},random.Random(1),self.chart)
        self.assertEqual(after['opponent']['active'],1)
        self.assertEqual(after['turn_count'],1)
        self.assertEqual(after['opponent']['members'][1]['hp'],100)

    def test_exhaustion_recoil_and_simultaneous_defeat(self):
        state=battle();state['player']['members'][0]['hp']=1;state['opponent']['members'][0]['hp']=1
        for move in state['player']['members'][0]['moves']:move['remaining_pp']=0
        after=resolve(state,{'kind':'move','move_id':0},random.Random(1),self.chart)
        self.assertEqual(after['status'],'draw')
        self.assertEqual(after['turns'][0]['events'][0]['recoil'],1)
        with self.assertRaises(ValidationError):resolve(battle(),{'kind':'move','move_id':0},random.Random(1),self.chart)

    def test_turn_cap_and_invalid_actions(self):
        state=battle();state['turn_count']=199
        after=resolve(state,{'kind':'move','move_id':1},random.Random(1),self.chart)
        self.assertEqual(after['status'],'draw')
        for action in ({'kind':'move','move_id':999},{'kind':'switch','slot':7},{'kind':'move','move_id':True},{}):
            with self.subTest(action=action),self.assertRaises(ValidationError):resolve(state,action,random.Random(1),self.chart)

    def test_hard_ai_uses_expected_damage(self):
        a,b=fighter(),fighter();a['moves'][3]['power']=120
        self.assertEqual(choose_move(a,b,'hard',random.Random(1),self.chart)['id'],4)

    def test_full_health_targets_survive_overpowered_super_effective_hits(self):
        state=battle();target=state['opponent']['members'][0]
        target['types']=['water','grass']
        self.chart[('normal','water')]=2;self.chart[('normal','grass')]=2
        state['player']['members'][0]['moves'][0]['power']=1000
        for _ in range(2):
            state=resolve(state,{'kind':'move','move_id':1},random.Random(1),self.chart)
            self.assertGreater(state['opponent']['members'][0]['hp'],0)
            self.assertEqual(state['status'],'active')
        self.assertEqual(state['opponent']['members'][0]['hp'],20)
        state=resolve(state,{'kind':'move','move_id':1},random.Random(1),self.chart)
        self.assertEqual(state['status'],'win')

    def test_cap_applies_to_both_sides_and_legacy_battles_keep_their_rules(self):
        state=battle()
        for side in ('player','opponent'):
            for move in state[side]['members'][0]['moves']:move['power']=1000
        after=resolve(state,{'kind':'move','move_id':1},random.Random(1),self.chart)
        self.assertEqual(after['player']['members'][0]['hp'],60)
        self.assertEqual(after['opponent']['members'][0]['hp'],60)
        state['rules_version']='prototype-1'
        legacy=resolve(state,{'kind':'move','move_id':1},random.Random(1),self.chart)
        self.assertEqual(legacy['status'],'win')

    def test_cap_is_based_on_maximum_not_remaining_hp(self):
        state=battle();state['opponent']['members'][0]['hp']=30
        state['player']['members'][0]['moves'][0]['power']=1000
        after=resolve(state,{'kind':'move','move_id':1},random.Random(1),self.chart)
        self.assertEqual(after['opponent']['members'][0]['hp'],0)
        self.assertEqual(after['status'],'win')


class PreparedGameDataTests(unittest.TestCase):
    def test_complete_valid_catalogue_and_explicit_overrides(self):
        data=prepare()
        self.assertEqual(len(data['pokemon']),151)
        self.assertEqual(len(data['types']),18)
        self.assertEqual(len(data['type_effectiveness']),324)
        moves={m['id'] for m in data['moves']}
        overrides={r['pokemon_id'] for r in data['pokemon_moves'] if r['source']=='project_override'}
        self.assertEqual(overrides,{11,13,14,129,132})
        for pokemon in data['pokemon']:
            eligible={r['move_id'] for r in data['pokemon_moves'] if r['pokemon_id']==pokemon['id']}
            self.assertGreaterEqual(len(eligible),4)
            self.assertLessEqual(eligible,moves)
        self.assertEqual({p['rarity'] for p in data['pokemon']},{'common','uncommon','rare','legendary'})
