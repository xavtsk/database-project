"""Rule-aware descriptive evidence from nested simulator events, computed by MongoDB."""
from backend.battles.engine import RULES_VERSION
from backend.battles.prediction import LABELS
from backend.errors import ValidationError

MIN_ATTEMPTS = 5
DOMINANT_SHARE = .75


def report(battles, trainer_id, rules_version=RULES_VERSION, difficulty=""):
    if not isinstance(rules_version, str) or not 1 <= len(rules_version) <= 80:
        raise ValidationError("Choose one battle rules version")
    if difficulty not in ("", "easy", "medium", "hard"):
        raise ValidationError("Choose Easy, Medium, Hard or all difficulties")
    match = {"trainer_id": trainer_id, "rules_version": rules_version,
             "status": {"$in": ["win", "loss", "draw"]},
             "turns.kind": {"$ne": "forfeit"}, "turns.events.kind": {"$ne": "forfeit"}}
    if difficulty:
        match["difficulty"] = difficulty
    player_moves = [{"$unwind": "$turns"}, {"$unwind": "$turns.events"},
                    {"$match": {"turns.events.kind": "move", "turns.events.side": "player"}}]
    pipeline = [{"$match": match}, {"$facet": {
        "sample": [{"$count": "battles"}],
        "moves": player_moves + [
            {"$group": {"_id": "$turns.events.move_id", "name": {"$first": "$turns.events.move"},
                        "attempts": {"$sum": 1}, "damage": {"$sum": {"$ifNull": ["$turns.events.damage", 0]}},
                        "hits": {"$sum": {"$cond": [{"$eq": ["$turns.events.hit", True]}, 1, 0]}}}},
            {"$set": {"damage_per_attempt": {"$divide": ["$damage", "$attempts"]},
                      "hit_rate": {"$divide": ["$hits", "$attempts"]}}},
            {"$sort": {"damage_per_attempt": -1, "attempts": -1, "_id": 1}}, {"$limit": 20}],
        "repetition": player_moves + [
            {"$group": {"_id": {"battle": "$_id", "move": "$turns.events.move_id"},
                        "uses": {"$sum": 1}, "status": {"$first": "$status"},
                        "difficulty": {"$first": "$difficulty"},
                        "team_size": {"$first": {"$size": {"$ifNull": ["$initial.player.members", []]}}}}},
            {"$group": {"_id": "$_id.battle", "attempts": {"$sum": "$uses"}, "top_uses": {"$max": "$uses"},
                        "distinct_moves": {"$sum": 1}, "status": {"$first": "$status"},
                        "difficulty": {"$first": "$difficulty"}, "team_size": {"$first": "$team_size"}}},
            {"$match": {"attempts": {"$gte": MIN_ATTEMPTS}}},
            {"$set": {"top_share": {"$divide": ["$top_uses", "$attempts"]}}},
            {"$group": {"_id": {"difficulty": "$difficulty", "team_size": "$team_size",
                                  "pattern": {"$cond": [{"$gte": ["$top_share", DOMINANT_SHARE]},
                                                          "high repetition", "mixed moves"]}},
                        "battles": {"$sum": 1},
                        "wins": {"$sum": {"$cond": [{"$eq": ["$status", "win"]}, 1, 0]}},
                        "losses": {"$sum": {"$cond": [{"$eq": ["$status", "loss"]}, 1, 0]}},
                        "draws": {"$sum": {"$cond": [{"$eq": ["$status", "draw"]}, 1, 0]}},
                        "average_top_share": {"$avg": "$top_share"}, "average_attempts": {"$avg": "$attempts"}}},
            {"$sort": {"_id.difficulty": 1, "_id.team_size": 1, "_id.pattern": 1}}],
        "predictions": [
            {"$match": {"prediction.method": {"$type": "string"}, "prediction.label": {"$in": list(LABELS)}}},
            {"$group": {"_id": {"method": "$prediction.method", "label": "$prediction.label", "outcome": "$status"},
                        "battles": {"$sum": 1}}},
            {"$sort": {"_id.method": 1, "_id.label": 1, "_id.outcome": 1}}]
    }}]
    result = list(battles.aggregate(pipeline))[0]
    versions = sorted(v for v in battles.distinct("rules_version", {"trainer_id": trainer_id})
                      if isinstance(v, str) and v)
    if RULES_VERSION not in versions:
        versions.append(RULES_VERSION)
    result.update(rules_version=rules_version, difficulty=difficulty, rules_versions=sorted(versions),
                  battles=result["sample"][0]["battles"] if result["sample"] else 0,
                  min_attempts=MIN_ATTEMPTS, dominant_share=DOMINANT_SHARE,
                  note="Completed battles under the selected rules; forfeits excluded. Damage per attempt includes misses "
                       "and actual damage limited by remaining HP. Repetition groups use the same difficulty and team size, "
                       "but team composition, strength and player decisions can still differ. These are associations, not causal effects.")
    del result["sample"]
    return result
