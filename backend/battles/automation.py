"""Small deterministic player policy using only the current saved battle state."""
from backend.battles.engine import MAX_HIT_FRACTION, expected_damage, type_factor, usable_moves
from backend.errors import ValidationError

POLICY = "expected-damage-1"


def choose_action(battle, chart):
    if battle["status"] != "active":
        raise ValidationError("This battle has finished")
    player = battle["player"]
    attacker = player["members"][player["active"]]
    target = battle["opponent"]["members"][battle["opponent"]["active"]]
    cap = None if battle.get("rules_version") == "prototype-1" else MAX_HIT_FRACTION

    def score(member, move):
        damage = min(target["hp"], expected_damage(member, target, move, chart,
                                                  random_factor=.925, damage_cap=cap))
        accuracy = move["accuracy"] if move["accuracy"] is not None else 100
        return damage * accuracy / 100

    if attacker["hp"] <= 0:
        healthy = [(slot, member) for slot, member in enumerate(player["members"]) if member["hp"] > 0]
        if not healthy:
            raise ValidationError("No healthy replacement is available")
        slot, replacement = max(healthy, key=lambda item: (
            max(score(item[1], move) for move in usable_moves(item[1])),
            item[1]["hp"] / item[1]["max_hp"], -item[0]))
        return dict(kind="switch", slot=slot), f"Replaced the fainted Pokemon with {replacement['name']}, the healthy partner with the best estimated attack."

    move = max(usable_moves(attacker), key=lambda m: (
        score(attacker, m), m["accuracy"] if m["accuracy"] is not None else 100,
        m["remaining_pp"], -m["id"]))
    if move["id"] == 0:
        reason = "All selected moves have no PP left, so used Fallback Strike."
    else:
        effectiveness = type_factor(move, target, chart)
        matchup = (" It is super effective." if effectiveness > 1 else
                   " The target is immune; no available move can deal estimated damage." if effectiveness == 0 else
                   " The target resists it, but it is the best available attack." if effectiveness < 1 else "")
        reason = (f"Chose {move['name']}: highest estimated accuracy-adjusted damage "
                  f"({score(attacker, move):.1f} HP), considering remaining PP, target HP and saved battle rules." + matchup)
    return dict(kind="move", move_id=move["id"]), reason
