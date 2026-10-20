"""Snapshot-based comparison, deliberately not a calibrated win probability."""
from backend.battles.engine import expected_damage, MAX_HIT_FRACTION
from backend.catalog import STATS

METHOD = "move-pressure-1"
LABELS = ("favoured", "evenly matched", "disadvantaged")


def classify(player_pressure, opponent_pressure):
    if opponent_pressure == 0:
        return "favoured" if player_pressure > 0 else "evenly matched"
    if player_pressure > opponent_pressure * 1.10:
        return "favoured"
    if player_pressure * 1.10 < opponent_pressure:
        return "disadvantaged"
    return "evenly matched"


def predict(sides, chart, rules_version, player_catalogue, opponent_catalogue):
    cap = None if rules_version == "prototype-1" else MAX_HIT_FRACTION

    def pressure(attackers, defenders):
        values = [max((expected_damage(a, d, m, chart, random_factor=.925, damage_cap=cap)
                       * (m["accuracy"] if m["accuracy"] is not None else 100) / 100 / d["max_hp"]
                       for m in a["moves"]), default=0) for a in attackers for d in defenders]
        return sum(values) / len(values) if values else 0

    player, opponent = sides["player"]["members"], sides["opponent"]["members"]
    p, o = pressure(player, opponent), pressure(opponent, player)
    stats = dict(player_base_stats=sum(m[s] for m in player_catalogue for s in STATS),
                 opponent_base_stats=sum(m[s] for m in opponent_catalogue for s in STATS),
                 player_average_speed=sum(m["stats"]["speed"] for m in player) / len(player),
                 opponent_average_speed=sum(m["stats"]["speed"] for m in opponent) / len(opponent))
    return dict(method=METHOD, label=classify(p, o), player_pressure=p, opponent_pressure=o,
                rules_version=rules_version, inputs=stats,
                reasons=[f"Best accuracy-adjusted attack averages {p:.1%} of opponent maximum HP per pairing; opponent {o:.1%}.",
                         f"Total base stats: yours {stats['player_base_stats']}, opponent {stats['opponent_base_stats']}.",
                         f"Average battle Speed: yours {stats['player_average_speed']:.1f}, opponent {stats['opponent_average_speed']:.1f}."],
                note="A starting-team heuristic, not a win probability. Assumes best available attacks; "
                     "does not simulate switching, move order, player decisions or the complete battle.")


def historical_context(battles, trainer_id, rules_version, difficulty, size):
    rows = list(battles.aggregate([
        {"$match": {"trainer_id": trainer_id, "rules_version": rules_version, "difficulty": difficulty,
                    "status": {"$in": ["win", "loss", "draw"]}, "turns.kind": {"$ne": "forfeit"},
                    "turns.events.kind": {"$ne": "forfeit"},
                    "$expr": {"$eq": [{"$size": {"$ifNull": ["$initial.player.members", []]}}, size]}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]))
    counts = {r["_id"]: r["count"] for r in rows}
    return dict(battles=sum(counts.values()), wins=counts.get("win", 0), losses=counts.get("loss", 0),
                draws=counts.get("draw", 0),
                note="Your prior battles with the same rules, difficulty and team size, excluding forfeits. "
                     "Different opponents and teams may be included; this is not the exact matchup's win rate.")
