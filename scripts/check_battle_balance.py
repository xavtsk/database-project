"""Compare old/new pacing with deterministic, in-memory starter battles.

Run after database setup: python3 -m scripts.check_battle_balance
Reads the SQL catalogue but creates no trainers, battles or rewards.
"""
from collections import defaultdict
import json
import random
import statistics

from scripts.run_local import load_environment
from backend.catalog import catalog
from backend.teams.service import default_moves
from backend.battles.service import generate_opponent
from backend.battles.engine import MAX_HIT_FRACTION, choose_move, combatant, resolve


def compare():
    pokemon, _, chart = catalog()
    result = {}
    for version in ("prototype-1", "prototype-2"):
        cap = None if version == "prototype-1" else MAX_HIT_FRACTION
        rows = []
        for starter in (1, 4, 7):
            for difficulty in ("easy", "medium", "hard"):
                for seed in range(20):
                    rng = random.Random(seed)
                    opponent, _ = generate_opponent([pokemon[starter]], difficulty, rng)
                    state = dict(rules_version=version, status="active", turn_count=0, difficulty=difficulty, turns=[],
                                 player=dict(active=0, members=[combatant(pokemon[starter], default_moves(pokemon[starter]))]),
                                 opponent=dict(active=0, members=[combatant(p, default_moves(p)) for p in opponent]))
                    while state["status"] == "active":
                        player, enemy = state["player"]["members"][0], state["opponent"]["members"][0]
                        move = choose_move(player, enemy, "hard", rng, chart, damage_cap=cap)
                        state = resolve(state, dict(kind="move", move_id=move["id"]), rng, chart)
                    rows.append(dict(difficulty=difficulty, turns=state["turn_count"], result=state["status"]))
        result[version] = dict(battles=len(rows), one_turn_battles=sum(r["turns"] == 1 for r in rows),
                               median_turns=statistics.median(r["turns"] for r in rows),
                               minimum_turns=min(r["turns"] for r in rows), maximum_turns=max(r["turns"] for r in rows),
                               difficulties={d: dict(wins=sum(r["result"] == "win" for r in rows if r["difficulty"] == d),
                                                     battles=sum(r["difficulty"] == d for r in rows),
                                                     median_turns=statistics.median(r["turns"] for r in rows if r["difficulty"] == d))
                                             for d in ("easy", "medium", "hard")})
    assert result["prototype-2"]["one_turn_battles"] == 0
    assert result["prototype-2"]["minimum_turns"] >= 3
    return result


if __name__ == "__main__":
    load_environment()
    print(json.dumps(compare(), indent=2))
