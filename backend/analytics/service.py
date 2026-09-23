"""History and server-side aggregation pipelines over persisted battle logs."""


def history(battles, trainer_id):
    return list(battles.find({"trainer_id": trainer_id}, {
        "_id": 1, "difficulty": 1, "status": 1, "turn_count": 1,
        "started_at": 1, "ended_at": 1, "team_name": 1, "reward": 1,
    }).sort("started_at", -1).limit(50))


def analytics(battles, trainer_id):
    completed = {"$match": {"trainer_id": trainer_id, "status": {"$in": ["win", "loss", "draw"]}}}
    totals = dict(battles={"$sum": 1}, wins={"$sum": {"$cond": [{"$eq": ["$status", "win"]}, 1, 0]}},
                  losses={"$sum": {"$cond": [{"$eq": ["$status", "loss"]}, 1, 0]}},
                  draws={"$sum": {"$cond": [{"$eq": ["$status", "draw"]}, 1, 0]}},
                  average_turns={"$avg": "$turn_count"}, average_seconds={"$avg": "$elapsed_seconds"})
    pipeline = [completed, {"$facet": {
        "summary": [{"$group": dict(_id=None, **totals)}],
        "difficulty": [{"$group": dict(_id="$difficulty", **totals)}, {"$sort": {"_id": 1}}],
        "pokemon": [
            {"$unwind": "$initial.player.members"},
            # Deduplicate species appearing twice in the same team for appearance win rates.
            {"$group": {"_id": {"battle": "$_id", "pokemon": "$initial.player.members.id"},
                         "name": {"$first": "$initial.player.members.name"}, "status": {"$first": "$status"}}},
            {"$group": {"_id": "$_id.pokemon", "name": {"$first": "$name"}, "appearances": {"$sum": 1},
                         "wins": {"$sum": {"$cond": [{"$eq": ["$status", "win"]}, 1, 0]}}}},
            {"$sort": {"appearances": -1, "_id": 1}}],
        "moves": [{"$unwind": "$turns"}, {"$unwind": "$turns.events"},
                  {"$match": {"turns.events.kind": "move", "turns.events.side": "player"}},
                  {"$group": {"_id": "$turns.events.move_id", "name": {"$first": "$turns.events.move"}, "uses": {"$sum": 1}}},
                  {"$sort": {"uses": -1, "_id": 1}}, {"$limit": 20}]
    }}]
    result = list(battles.aggregate(pipeline))[0]
    result["summary"] = result["summary"][0] if result["summary"] else dict(battles=0, wins=0, losses=0, draws=0, average_turns=0, average_seconds=0)
    return result
