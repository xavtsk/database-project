"""Offline boundary and behavioural checks for budgets, advice and predictions."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import random
import unittest
from unittest.mock import Mock, patch

from backend.catalog import STATS
from backend.errors import ValidationError
from backend.teams.budget import pokemon_cost, team_budget, validate_budget
from backend.teams.service import save_team
from backend.team_analysis.recommendations import rank_candidates, team_scores, recommend
from backend.battles.engine import combatant
from backend.battles.prediction import classify, predict
from backend.battles.service import start_battle, act


TYPES = ("normal", "fire", "water", "grass", "ghost")


def pokemon(id=1, type_="normal", total=300):
    p = dict(id=id, name=f"pokemon-{id}", types=[type_], **dict.fromkeys(STATS, 50))
    p["hp"] += total - 300
    p["moves"] = [dict(id=i, name=f"move-{i}", type=type_, damage_class="physical",
                       power=40, accuracy=None, pp=20, priority=0) for i in range(1, 5)]
    return p


def member(id=1, type_="normal", total=300):
    return dict(owned_id=id, pokemon=pokemon(id, type_, total), moves=[1, 2, 3, 4])


class AdviceTests(unittest.TestCase):
    def setUp(self):
        self.chart = {(a, b): 1 for a in TYPES for b in TYPES}
        self.chart.update({("water", "fire"): 2, ("grass", "water"): 2, ("fire", "grass"): 2,
                           ("normal", "ghost"): 0})
        self.catalogue = ({}, [dict(name=t) for t in TYPES], self.chart)
        self.patch = patch("backend.catalog.catalog", return_value=self.catalogue)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.patch2 = patch("backend.team_analysis.recommendations.catalog", return_value=self.catalogue)
        self.patch2.start()
        self.addCleanup(self.patch2.stop)

    def test_budget_rounding_boundary_and_empty_team(self):
        self.assertEqual(pokemon_cost(pokemon(total=300)), 3)
        self.assertEqual(pokemon_cost(pokemon(total=301)), 4)
        self.assertEqual(team_budget([])["remaining"], 30)
        self.assertEqual(validate_budget([pokemon(total=500)] * 6)["total"], 30)
        with self.assertRaisesRegex(ValidationError, "31 points"):
            validate_budget([pokemon(total=500)] * 5 + [pokemon(total=501)])

    def test_exposure_combines_both_types_and_counts_double_weakness(self):
        m = member(1, "fire")
        m["pokemon"]["types"].append("normal")
        self.chart[("water", "normal")] = 2
        self.assertEqual(team_scores([m])["exposure"], 3)  # 4x weakness contributes 4-1.
        self.chart[("water", "normal")] = .5
        self.assertEqual(team_scores([m])["exposure"], 0)
        self.chart[("water", "normal")] = 0
        self.assertEqual(team_scores([m])["exposure"], 0)

    def test_addition_improves_coverage_without_mutating_team_and_deduplicates_species(self):
        members = [member(1, "fire")]
        water = member(2, "water")
        duplicate = deepcopy(water); duplicate["owned_id"] = 3
        before = deepcopy(members)
        result = rank_candidates(members, [water, duplicate, members[0]])
        self.assertEqual(members, before)
        self.assertEqual(len(result["suggestions"]), 1)
        suggestion = result["suggestions"][0]
        self.assertEqual(suggestion["owned_id"], 2)
        self.assertGreater(suggestion["coverage_gain"], 0)
        self.assertIsNone(suggestion["replace_owned_id"])
        self.assertEqual(len(suggestion["suggested_moves"]), 4)

    def test_full_team_replacement_and_no_improvement(self):
        members = [member(i, "fire") for i in range(1, 7)]
        result = rank_candidates(members, [member(7, "water")])
        self.assertEqual(result["suggestions"][0]["replace_owned_id"], 1)
        self.assertEqual(rank_candidates(members, [member(8, "fire")])["suggestions"], [])
        self.assertEqual(rank_candidates(members, [])["suggestions"], [])

    def test_budget_filter_and_empty_team_choices(self):
        members = [member(i, "fire", 600) for i in range(1, 6)]
        self.assertEqual(rank_candidates(members, [member(6, "water")])["suggestions"], [])
        empty = rank_candidates([], [member(8), member(7)])
        self.assertTrue(empty["empty_team"])
        self.assertIsNone(empty["before"]["exposure"])
        self.assertEqual([s["owned_id"] for s in empty["suggestions"]], [7, 8])

    def test_recommendation_checks_team_ownership_before_candidate_query(self):
        with patch("backend.team_analysis.recommendations.get_team", side_effect=ValidationError("Not owned")), \
             patch("backend.team_analysis.recommendations.query") as sql:
            with self.assertRaises(ValidationError):
                recommend(1, 99)
            sql.assert_not_called()

    def test_thresholds_and_zero_pressure(self):
        for p, o, label in ((1.1, 1, "evenly matched"), (1.11, 1, "favoured"),
                            (1, 1.1, "evenly matched"), (1, 1.11, "disadvantaged"),
                            (0, 0, "evenly matched"), (1, 0, "favoured"), (0, 1, "disadvantaged")):
            self.assertEqual(classify(p, o), label)

    def test_prediction_selected_moves_accuracy_legacy_cap_and_input_preservation(self):
        p, o = pokemon(1), pokemon(2)
        sides = dict(player=dict(members=[combatant(p, [1, 2, 3, 4])]),
                     opponent=dict(members=[combatant(o, [1, 2, 3, 4])]))
        before = deepcopy(sides)
        result = predict(sides, self.chart, "prototype-2", [p], [o])
        self.assertEqual(result["label"], "evenly matched")
        self.assertEqual(sides, before)
        for m in sides["player"]["members"][0]["moves"]:
            m["accuracy"] = 0
        self.assertEqual(predict(sides, self.chart, "prototype-2", [p], [o])["label"], "disadvantaged")
        for side in sides.values():
            for m in side["members"][0]["moves"]:
                m.update(power=10000, accuracy=None)
        current = predict(sides, self.chart, "prototype-2", [p], [o])
        legacy = predict(sides, self.chart, "prototype-1", [p], [o])
        self.assertLessEqual(current["player_pressure"], .4)
        self.assertGreater(legacy["player_pressure"], current["player_pressure"])
        sides["opponent"]["members"][0]["types"] = ["ghost"]
        self.assertEqual(predict(sides, self.chart, "prototype-2", [p], [o])["player_pressure"], 0)

    def test_battle_saves_prediction_once_and_preserves_it_after_forfeit(self):
        m = member()
        logs = Mock(); logs.aggregate.return_value = []; logs.insert_one.return_value = None
        with patch("backend.battles.service.get_team", return_value=dict(name="Team", members=[m])), \
             patch("backend.battles.service.catalog", return_value=self.catalogue), \
             patch("backend.battles.service.generate_opponent", return_value=([pokemon(2)], {})) as generate:
            b = start_battle(logs, 1, 1, "medium", random.Random(1))
        self.assertEqual(b["prediction"]["history"]["battles"], 0)
        self.assertEqual(b["turn_count"], 0)
        self.assertEqual(b["budget"]["total"], 3)
        self.assertEqual(logs.insert_one.call_args.args[0], b)
        generate.assert_called_once()
        logs.find_one.return_value = b
        logs.replace_one.return_value.matched_count = 1
        after = act(logs, 1, b["_id"], 0, {"kind": "forfeit"})
        self.assertEqual(after["prediction"], b["prediction"])

    def test_overbudget_existing_team_cannot_start_and_legacy_battle_can_continue(self):
        logs = Mock()
        members = [member(i, total=600) for i in range(1, 7)]
        with patch("backend.battles.service.get_team", return_value=dict(name="Old", members=members)):
            with self.assertRaisesRegex(ValidationError, "36 points"):
                start_battle(logs, 1, 1, "easy")
        logs.insert_one.assert_not_called()
        legacy = dict(_id="old", trainer_id=1, status="active", revision=0, turns=[], turn_count=0,
                      started_at=datetime.now(timezone.utc))
        logs.find_one.return_value = legacy
        logs.replace_one.return_value.matched_count = 1
        self.assertNotIn("prediction", act(logs, 1, "old", 0, {"kind": "forfeit"}))

    def test_overbudget_save_rejects_before_update_or_delete(self):
        cursor = Mock()
        cursor.fetchone.return_value = {"id": 1}
        cursor.fetchall.return_value = [dict(id=i, pokemon_id=i) for i in range(1, 7)]
        data = {i: pokemon(i, total=600) for i in range(1, 7)}
        @contextmanager
        def tx():
            yield cursor
        with patch("backend.teams.service.transaction", tx), \
             patch("backend.teams.service.catalog", return_value=(data, [], {})):
            with self.assertRaisesRegex(ValidationError, "36 points"):
                save_team(1, "Existing", [dict(owned_id=i, moves=[1, 2, 3, 4]) for i in data], 10)
        self.assertTrue(all(call.args[0].lstrip().startswith("SELECT") for call in cursor.execute.call_args_list))


if __name__ == "__main__":
    unittest.main()
