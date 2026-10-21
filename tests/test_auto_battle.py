"""Policy choices, persistence and revision safety without external services."""
from copy import deepcopy
from datetime import datetime, timezone
import random
import unittest
from unittest.mock import Mock, patch

from backend.battles.automation import POLICY, choose_action
from backend.battles.engine import resolve
from backend.battles.service import act
from backend.errors import ValidationError
from tests.test_battle_engine import battle, fighter


class AutoBattleTests(unittest.TestCase):
    def setUp(self):
        self.chart = {(a, b): 1 for a in ("normal", "water", "ghost") for b in ("normal", "water", "ghost")}

    def test_accuracy_pp_and_immunity_are_considered_without_mutating_state(self):
        state = battle()
        state["player"]["members"][0]["moves"][1].update(power=1000, accuracy=30)
        before = deepcopy(state)
        action, reason = choose_action(state, self.chart)
        self.assertEqual(action, dict(kind="move", move_id=1))
        self.assertIn("accuracy-adjusted", reason)
        self.assertEqual(state, before)
        state["opponent"]["members"][0]["types"] = ["ghost"]
        self.chart[("normal", "ghost")] = 0
        state["player"]["members"][0]["moves"][2]["type"] = "water"
        self.assertEqual(choose_action(state, self.chart)[0]["move_id"], 3)
        state["player"]["members"][0]["moves"][2]["remaining_pp"] = 0
        self.assertNotEqual(choose_action(state, self.chart)[0]["move_id"], 3)

    def test_legacy_rules_use_uncapped_damage_and_fallback_is_available(self):
        state = battle()
        state["player"]["members"][0]["moves"][1].update(power=1000, accuracy=30)
        self.assertEqual(choose_action(state, self.chart)[0]["move_id"], 1)
        state["rules_version"] = "prototype-1"
        self.assertEqual(choose_action(state, self.chart)[0]["move_id"], 2)
        for move in state["player"]["members"][0]["moves"]:
            move["remaining_pp"] = 0
        action, reason = choose_action(state, self.chart)
        self.assertEqual(action, dict(kind="move", move_id=0))
        self.assertIn("Fallback Strike", reason)

    def test_fainted_replacement_is_healthy_and_does_not_cost_a_turn(self):
        state = battle(player=[fighter("fainted"), fighter("weak"), fighter("strong")])
        state["player"]["members"][0]["hp"] = 0
        for move in state["player"]["members"][2]["moves"]:
            move["power"] = 90
        action, reason = choose_action(state, self.chart)
        self.assertEqual(action, dict(kind="switch", slot=2))
        after = resolve(state, action, random.Random(1), self.chart)
        self.assertEqual(after["turn_count"], 0)
        self.assertEqual(after["turns"][-1]["events"][0]["slot"], 2)
        self.assertIn("strong", reason)
        state["status"] = "loss"
        with self.assertRaises(ValidationError):
            choose_action(state, self.chart)

    def test_complete_auto_battle_reaches_a_result_within_existing_turn_limit(self):
        state = battle(player=[fighter("first"), fighter("second")], opponent=[fighter("enemy", 1)])
        for _ in range(205):
            if state["status"] != "active":
                break
            action, _ = choose_action(state, self.chart)
            state = resolve(state, action, random.Random(10), self.chart)
        self.assertIn(state["status"], ("win", "loss", "draw"))
        self.assertLessEqual(state["turn_count"], 200)

    def saved(self):
        state = battle()
        state.update(_id="auto-fixture", trainer_id=1, revision=0, rules_version="prototype-2",
                     started_at=datetime.now(timezone.utc), reward=None, prediction={"label": "fixed"})
        return state

    def test_service_records_actual_server_choice_policy_and_preserves_prediction(self):
        previous = self.saved()
        logs = Mock()
        logs.find_one.return_value = previous
        logs.replace_one.return_value.matched_count = 1
        with patch("backend.battles.service.catalog", return_value=({}, [], self.chart)):
            result = act(logs, 1, previous["_id"], 0, dict(kind="auto", move_id=999, policy="client-forged"), random.Random(1))
        turn = result["turns"][-1]
        self.assertEqual(turn["controller"], "auto")
        self.assertEqual(turn["policy"], POLICY)
        self.assertEqual(turn["action"], dict(kind="move", move_id=1))
        self.assertIn("estimated", turn["decision"])
        self.assertEqual(result["prediction"], previous["prediction"])
        self.assertEqual(result["revision"], 1)
        self.assertEqual(previous["turns"], [])
        self.assertEqual(logs.replace_one.call_args.args[0]["revision"], 0)

    def test_manual_forfeit_is_labelled_and_stale_requests_never_choose_or_write(self):
        previous = self.saved()
        logs = Mock()
        logs.find_one.return_value = previous
        logs.replace_one.return_value.matched_count = 1
        result = act(logs, 1, previous["_id"], 0, dict(kind="forfeit"))
        self.assertEqual(result["turns"][-1]["controller"], "manual")
        self.assertNotIn("policy", result["turns"][-1])
        logs.reset_mock()
        with patch("backend.battles.service.choose_action") as choose:
            with self.assertRaisesRegex(ValidationError, "Battle changed"):
                act(logs, 1, previous["_id"], 99, dict(kind="auto"))
            choose.assert_not_called()
        logs.replace_one.assert_not_called()
        logs.find_one.return_value = None
        with self.assertRaisesRegex(ValidationError, "not found"):
            act(logs, 99, previous["_id"], 0, dict(kind="auto"))

    def test_lost_revision_race_does_not_deliver_a_reward(self):
        logs = Mock()
        logs.replace_one.return_value.matched_count = 0
        with patch("backend.battles.service.get_battle", return_value=self.saved()), \
                patch("backend.battles.service.catalog", return_value=({}, [], self.chart)), \
                patch("backend.battles.service.deliver_reward") as reward:
            with self.assertRaisesRegex(ValidationError, "Another action"):
                act(logs, 1, "auto-fixture", 0, dict(kind="auto"), random.Random(1))
            reward.assert_not_called()
