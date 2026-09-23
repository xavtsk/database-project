"""Pure, testable turn resolution for the approved simplified battle rules."""
from copy import deepcopy
from math import floor

from backend.errors import ValidationError, integer

RULES_VERSION = "prototype-2"
MAX_HIT_FRACTION = 0.40

STRUGGLE = dict(id=0, name="fallback-strike", type="neutral", power=50, accuracy=None,
                damage_class="physical", priority=0, pp=1, remaining_pp=1)


def combatant(pokemon, selected_moves):
    moves = {m["id"]: m for m in pokemon["moves"]}
    if len(selected_moves) != 4 or len(set(selected_moves)) != 4 or not set(selected_moves) <= moves.keys():
        raise ValidationError("Battle members need four distinct eligible moves")
    return dict(id=pokemon["id"], name=pokemon["name"], types=list(pokemon["types"]),
                hp=2 * pokemon["hp"] + 60, max_hp=2 * pokemon["hp"] + 60,
                stats={s: pokemon[s] + 5 for s in ("attack", "defense", "special_attack", "special_defense", "speed")},
                moves=[dict(deepcopy(moves[m]), remaining_pp=moves[m]["pp"]) for m in selected_moves])


def type_factor(move, target, chart):
    factor = 1
    if move["id"] != 0:
        for name in target["types"]:
            factor *= chart[(move["type"], name)]
    return factor


def expected_damage(attacker, defender, move, chart, random_factor=1, damage_cap=MAX_HIT_FRACTION):
    special = move["damage_class"] == "special"
    attack = attacker["stats"]["special_attack" if special else "attack"]
    defense = defender["stats"]["special_defense" if special else "defense"]
    effectiveness = type_factor(move, defender, chart)
    if effectiveness == 0:
        return 0
    stab = 1.5 if move["id"] and move["type"] in attacker["types"] else 1
    damage = max(1, floor((22 * move["power"] * attack / defense / 50 + 2) * stab * effectiveness * random_factor))
    # Give both sides time to make decisions, even with 4× type advantages.
    # Use maximum HP, not remaining HP, so weakened Pokémon can still faint.
    if damage_cap is not None:
        damage = min(damage, max(1, floor(defender["max_hp"] * damage_cap)))
    return damage


def usable_moves(member):
    return [m for m in member["moves"] if m["remaining_pp"] > 0] or [dict(STRUGGLE)]


def choose_move(attacker, defender, difficulty, rng, chart, damage_cap=MAX_HIT_FRACTION):
    available = usable_moves(attacker)
    if difficulty == "easy" or (difficulty == "medium" and rng.random() < .5):
        return rng.choice(available)
    return max(available, key=lambda m: expected_damage(attacker, defender, m, chart, damage_cap=damage_cap) * (m["accuracy"] if m["accuracy"] is not None else 100) / 100)


def resolve(state, action, rng, chart):
    """Return a new state; an invalid or repeated action cannot mutate the input."""
    battle = deepcopy(state)
    # Preserve the rules of any older in-progress battle and its saved history.
    damage_cap = None if battle.get("rules_version") == "prototype-1" else MAX_HIT_FRACTION
    if battle["status"] != "active":
        raise ValidationError("This battle has finished")
    if not isinstance(action, dict):
        raise ValidationError("Choose a move or switch action")
    player, opponent = battle["player"], battle["opponent"]
    p = player["members"][player["active"]]
    o = opponent["members"][opponent["active"]]
    switching = action.get("kind") == "switch"
    if switching:
        slot = integer(action.get("slot"), "Switch slot")
        if not 0 <= slot < len(player["members"]) or slot == player["active"] or player["members"][slot]["hp"] <= 0:
            raise ValidationError("Choose a different healthy Pokémon")
        player["active"] = slot
        if p["hp"] <= 0:
            battle["turns"].append(dict(number=battle["turn_count"], kind="replacement", events=[dict(kind="switch", side="player", name=player["members"][slot]["name"])]))
            return battle
        player_move = None
    else:
        if p["hp"] <= 0:
            raise ValidationError("Choose a healthy replacement first")
        if action.get("kind") != "move":
            raise ValidationError("Choose a move or switch")
        move_id = integer(action.get("move_id"), "Move ID")
        player_move = next((m for m in usable_moves(p) if m["id"] == move_id), None)
        if player_move is None:
            raise ValidationError("That move is unavailable or has no PP")
    # Choose using the state before seeing a player's switch or selected move.
    opponent_move = choose_move(o, p, battle["difficulty"], rng, chart, damage_cap=damage_cap)
    events = []
    if switching:
        events.append(dict(kind="switch", side="player", name=player["members"][player["active"]]["name"]))
        actions = [("opponent", opponent_move)]
    else:
        actions = [("player", player_move), ("opponent", opponent_move)]
        tie = rng.random()
        actions.sort(key=lambda item: (item[1]["priority"], battle[item[0]]["members"][battle[item[0]]["active"]]["stats"]["speed"], tie if item[0] == "player" else 1-tie), reverse=True)
    for side, move in actions:
        enemy = "opponent" if side == "player" else "player"
        attacker = battle[side]["members"][battle[side]["active"]]
        target = battle[enemy]["members"][battle[enemy]["active"]]
        if attacker["hp"] <= 0 or target["hp"] <= 0:
            continue
        if move["id"]:
            move["remaining_pp"] -= 1
        hit = move["accuracy"] is None or rng.random() * 100 < move["accuracy"]
        damage = min(target["hp"], expected_damage(attacker, target, move, chart, rng.uniform(.85, 1), damage_cap=damage_cap)) if hit else 0
        target["hp"] -= damage
        event = dict(kind="move", side=side, pokemon_id=attacker["id"], name=attacker["name"], move_id=move["id"], move=move["name"], target=target["name"], damage=damage, hit=hit, effectiveness=type_factor(move, target, chart))
        if not move["id"]:
            recoil = min(attacker["hp"], max(1, floor(damage / 4)))
            attacker["hp"] -= recoil
            event["recoil"] = recoil
        events.append(event)
        for label, member in ((side, attacker), (enemy, target)):
            if member["hp"] == 0:
                events.append(dict(kind="faint", side=label, name=member["name"]))
    battle["turn_count"] += 1
    battle["turns"].append(dict(number=battle["turn_count"], kind="turn", action=action, events=events))
    alive_p = any(m["hp"] > 0 for m in player["members"])
    alive_o = any(m["hp"] > 0 for m in opponent["members"])
    if not alive_p and not alive_o:
        battle["status"] = "draw"
    elif not alive_o:
        battle["status"] = "win"
    elif not alive_p:
        battle["status"] = "loss"
    elif battle["turn_count"] >= 200:
        battle["status"] = "draw"
    elif o["hp"] <= 0:
        opponent["active"] = next(i for i, m in enumerate(opponent["members"]) if m["hp"] > 0)
        events.append(dict(kind="switch", side="opponent", name=opponent["members"][opponent["active"]]["name"]))
    return battle
