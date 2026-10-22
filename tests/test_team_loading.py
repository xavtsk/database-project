"""Joined team reads preserve member identity, shiny variants and move order."""
from copy import deepcopy
from contextlib import contextmanager
import unittest
from unittest.mock import Mock, patch

from backend.errors import ValidationError
from backend.teams.service import get_team, save_team


class TeamLoadingTests(unittest.TestCase):
    def test_duplicates_remain_separate_owned_members_and_moves_keep_slot_order(self):
        pokemon = dict(id=25, name='pikachu', hp=35, attack=55, defense=40,
                       special_attack=50, special_defense=50, speed=90, types=['electric'], moves=[])
        original = deepcopy(pokemon)
        rows = [dict(id=3, name='Partners', slot=slot, owned_id=owned, pokemon_id=25,
                     is_shiny=shiny, move_id=move)
                for slot, owned, shiny, moves in [(1, 90, 0, [8, 3, 7, 2]), (2, 91, 1, [2, 7, 3, 8])]
                for move in moves]
        with patch('backend.teams.service.query', return_value=rows) as query, \
                patch('backend.teams.service.catalog', return_value=({25:pokemon}, [], {})):
            team = get_team(5, 3)
        self.assertEqual(query.call_args.args[1], (3, 5))
        self.assertEqual([m['owned_id'] for m in team['members']], [90, 91])
        self.assertEqual([m['moves'] for m in team['members']], [[8,3,7,2], [2,7,3,8]])
        self.assertEqual([m['pokemon']['is_shiny'] for m in team['members']], [False, True])
        self.assertEqual(team['budget']['total'], 8)
        self.assertEqual(pokemon, original)

    def test_empty_team_is_returned_without_a_placeholder_member(self):
        row = dict(id=3, name='Empty', slot=None, owned_id=None, pokemon_id=None, is_shiny=None, move_id=None)
        with patch('backend.teams.service.query', return_value=[row]), \
                patch('backend.teams.service.catalog') as catalog:
            team = get_team(5, 3)
        self.assertEqual(team['members'], [])
        self.assertEqual(team['budget']['total'], 0)
        catalog.assert_not_called()

    def test_missing_or_unowned_team_is_rejected(self):
        with patch('backend.teams.service.query', return_value=[]), self.assertRaises(ValidationError):
            get_team(5, 999)

    def test_batched_save_keeps_owned_id_and_move_slot_associations(self):
        cursor = Mock()
        cursor.fetchone.return_value = {'id':5}
        cursor.fetchall.return_value = [{'id':90, 'pokemon_id':25}, {'id':91, 'pokemon_id':25}]
        pokemon = dict(id=25, name='pikachu', rarity='common', hp=35, attack=55, defense=40,
                       special_attack=50, special_defense=50, speed=90, types=['electric'],
                       moves=[{'id':n} for n in (8,3,7,2)])
        members = [dict(owned_id=90, moves=[8,3,7,2]), dict(owned_id=91, moves=[2,7,3,8])]

        @contextmanager
        def tx():
            yield cursor

        with patch('backend.teams.service.transaction', tx), \
                patch('backend.teams.service.catalog', return_value=({25:pokemon}, [], {})):
            self.assertEqual(save_team(5, 'Partners', members, 3), 3)
        batches = cursor.executemany.call_args_list
        self.assertEqual(len(batches), 2)
        self.assertEqual(batches[0].args[1], [(3,1,90,5), (3,2,91,5)])
        self.assertEqual(batches[1].args[1],
                         [(3,1,1,8),(3,1,2,3),(3,1,3,7),(3,1,4,2),
                          (3,2,1,2),(3,2,2,7),(3,2,3,3),(3,2,4,8)])


if __name__ == '__main__':
    unittest.main()
