"""Approved project costs, derived from catalogue stats rather than stored twice."""
from backend.catalog import STATS
from backend.errors import ValidationError

LIMIT = 30
VERSION = "base-stats-1"


def pokemon_cost(pokemon):
    return (sum(pokemon[s] for s in STATS) + 99) // 100


def team_budget(pokemon):
    costs = [pokemon_cost(p) for p in pokemon]
    total = sum(costs)
    return dict(version=VERSION, limit=LIMIT, costs=costs, total=total,
                remaining=LIMIT - total, within_budget=total <= LIMIT)


def validate_budget(pokemon):
    budget = team_budget(pokemon)
    if not budget["within_budget"]:
        raise ValidationError(f"Team costs {budget['total']} points; the budget is {LIMIT}. Remove or replace a member.")
    return budget
