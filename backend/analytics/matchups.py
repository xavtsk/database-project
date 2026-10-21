"""Observed 1v1 species outcomes from the selected trainer's simulator logs."""
from backend.battles.engine import RULES_VERSION
from backend.db import query
from backend.errors import ValidationError


def report(battles, trainer_id, pokemon_id="4", opponent_id="7", rules_version=RULES_VERSION, difficulty=""):
    try:
        if any(type(value) not in (int, str) for value in (pokemon_id, opponent_id)):
            raise ValueError
        pokemon_id, opponent_id = int(pokemon_id), int(opponent_id)
    except (TypeError, ValueError):
        raise ValidationError("Choose two different Pokemon from IDs 1 to 151") from None
    if not 1 <= pokemon_id <= 151 or not 1 <= opponent_id <= 151 or pokemon_id == opponent_id:
        raise ValidationError("Choose two different Pokemon from IDs 1 to 151")
    if not isinstance(rules_version, str) or not 1 <= len(rules_version) <= 80:
        raise ValidationError("Choose one battle rules version")
    if difficulty not in ("", "easy", "medium", "hard"):
        raise ValidationError("Choose Easy, Medium, Hard or all difficulties")

    match = dict(trainer_id=trainer_id, rules_version=rules_version,
                 status={"$in": ["win", "loss", "draw"]})
    match.update({"turns.kind": {"$ne": "forfeit"}, "turns.events.kind": {"$ne": "forfeit"}})
    if difficulty:
        match["difficulty"] = difficulty
    # Initial snapshots define team size; final survivors do not establish a 1v1.
    sizes = [{"$eq": [{"$size": {"$cond": [{"$isArray": f"$initial.{side}.members"},
                                           f"$initial.{side}.members", []]}}, 1]}
             for side in ("player", "opponent")]
    totals = dict(battles={"$sum": 1}, wins={"$sum": {"$cond": ["$selected_won", 1, 0]}},
                  losses={"$sum": {"$cond": ["$selected_lost", 1, 0]}},
                  draws={"$sum": {"$cond": [{"$eq": ["$status", "draw"]}, 1, 0]}},
                  average_turns={"$avg": "$turn_count"})
    rate = {"$set": {"win_rate": {"$divide": ["$wins", "$battles"]}}}
    pipeline = [
        {"$match": match},
        {"$match": {"$expr": {"$and": sizes}}},
        {"$project": {"difficulty": 1, "status": 1, "turn_count": 1,
                      "player_id": {"$arrayElemAt": ["$initial.player.members.id", 0]},
                      "opponent_id": {"$arrayElemAt": ["$initial.opponent.members.id", 0]}}},
        {"$match": {"$or": [dict(player_id=pokemon_id, opponent_id=opponent_id),
                               dict(player_id=opponent_id, opponent_id=pokemon_id)]}},
        {"$set": {"selected_side": {"$cond": [{"$eq": ["$player_id", pokemon_id]}, "player", "opponent"]}}},
        {"$set": {
            "selected_won": {"$or": [{"$and": [{"$eq": ["$selected_side", "player"]}, {"$eq": ["$status", "win"]}]},
                                         {"$and": [{"$eq": ["$selected_side", "opponent"]}, {"$eq": ["$status", "loss"]}]}]},
            "selected_lost": {"$or": [{"$and": [{"$eq": ["$selected_side", "player"]}, {"$eq": ["$status", "loss"]}]},
                                          {"$and": [{"$eq": ["$selected_side", "opponent"]}, {"$eq": ["$status", "win"]}]}]}}},
        {"$facet": {
            "summary": [{"$group": dict(_id=None, **totals)}, rate, {"$unset": "_id"}],
            "rows": [{"$group": dict(_id=dict(difficulty="$difficulty", selected_side="$selected_side"), **totals)},
                     rate, {"$sort": {"_id.difficulty": 1, "_id.selected_side": 1}},
                     {"$set": {"difficulty": "$_id.difficulty", "selected_side": "$_id.selected_side"}},
                     {"$unset": "_id"}]
        }}]
    result = list(battles.aggregate(pipeline))[0]
    result["summary"] = result["summary"][0] if result["summary"] else dict(
        battles=0, wins=0, losses=0, draws=0, win_rate=None, average_turns=None)
    result.update(pokemon_id=pokemon_id, opponent_id=opponent_id, rules_version=rules_version, difficulty=difficulty,
                  source="mongodb", pokemon=query("SELECT id,name FROM pokemon ORDER BY id"),
                  note="Your completed battles with exactly one Pokemon on each starting side; team battles, active battles "
                       "and forfeits are excluded. Results count both species orientations, with wins/losses from the selected "
                       "Pokemon's perspective. Win rate = wins / all matching battles, including draws. "
                       "Moves and player/AI choices affect outcomes; this is observed evidence, not a predicted win probability.")
    return result
