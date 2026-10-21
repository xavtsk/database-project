"""Explainable suggestions; no saved team is modified by this module."""
import json

from backend.config import ROOT
from backend.catalog import catalog, effectiveness
from backend.db import query
from backend.teams.budget import team_budget, pokemon_cost, LIMIT
from backend.teams.service import default_moves, get_team
from backend.teams.limits import legendary_duplicates

RECOMMENDATION_SQL = (ROOT / "database/relational/queries/team_recommendations.sql").read_text(encoding="utf-8")


def team_scores(members):
    if not members:
        return dict(exposure=None, coverage=0, weaknesses={}, covered_types=[])
    types = [t["name"] for t in catalog()[1]]
    weaknesses = {t: sum(max(effectiveness(t, m["pokemon"]["types"]) - 1, 0)
                        for m in members) / len(members) for t in types}
    moves = [move for m in members for move in m["pokemon"]["moves"] if move["id"] in m["moves"]]
    covered = [t for t in types if any(effectiveness(move["type"], [t]) > 1 for move in moves)]
    return dict(exposure=sum(weaknesses.values()), coverage=len(covered), weaknesses=weaknesses, covered_types=covered)


def rank_candidates(members, candidates):
    """Reference scoring for offline/equivalence tests; production uses the SQL below."""
    before = team_scores(members)
    used = {m["owned_id"] for m in members}
    suggestions = []
    for candidate in candidates:
        if candidate["owned_id"] in used:
            continue
        pokemon = candidate["pokemon"]
        proposed_member = dict(owned_id=candidate["owned_id"], pokemon=pokemon, moves=default_moves(pokemon))
        for outgoing in (range(6) if len(members) == 6 else [None]):
            proposed = list(members)
            if outgoing is None:
                proposed.append(proposed_member)
            else:
                proposed[outgoing] = proposed_member
            if legendary_duplicates(m["pokemon"] for m in proposed):
                continue
            budget = team_budget(m["pokemon"] for m in proposed)
            if not budget["within_budget"]:
                continue
            after = team_scores(proposed)
            improvement = before["exposure"] - after["exposure"] if members else 0
            coverage_gain = after["coverage"] - before["coverage"]
            if members and not (improvement > 1e-9 or (abs(improvement) <= 1e-9 and coverage_gain > 0)):
                continue
            reason = ("Affordable choice for an empty team." if not members else
                      f"Defensive exposure {before['exposure']:.2f} → {after['exposure']:.2f}; "
                      f"super-effective coverage {before['coverage']} → {after['coverage']} of 18 types.")
            improved_types = [t for t in before["weaknesses"]
                              if after["weaknesses"][t] < before["weaknesses"][t] - 1e-9]
            new_coverage = sorted(set(after["covered_types"]) - set(before["covered_types"]))
            if improved_types:
                reason += " Less exposed to: " + ", ".join(improved_types) + "."
            if new_coverage:
                reason += " Adds coverage against: " + ", ".join(new_coverage) + "."
            suggestions.append(dict(owned_id=candidate["owned_id"], pokemon_id=pokemon["id"], name=pokemon["name"],
                                    cost=pokemon_cost(pokemon), budget=budget, before=before, after=after,
                                    exposure_reduction=improvement, coverage_gain=coverage_gain,
                                    replace_owned_id=members[outgoing]["owned_id"] if outgoing is not None else None,
                                    replace_name=members[outgoing]["pokemon"]["name"] if outgoing is not None else None,
                                    suggested_moves=[m for m in pokemon["moves"] if m["id"] in proposed_member["moves"]],
                                    reason=reason))
    suggestions.sort(key=lambda s: (-round(s["exposure_reduction"], 9), -s["coverage_gain"], s["cost"], s["owned_id"], s["replace_owned_id"] or 0))
    unique = []
    species = set()
    for suggestion in suggestions:
        if suggestion["pokemon_id"] not in species:
            unique.append(suggestion)
            species.add(suggestion["pokemon_id"])
        if len(unique) == 3:
            break
    return dict(before=before, suggestions=unique, budget=team_budget(m["pokemon"] for m in members),
                empty_team=not members,
                note="Suggestions use default eligible moves. Review and save changes in Team Builder. "
                     "Lower defensive exposure and coverage against single types do not guarantee victory.")


def recommend(trainer_id, team_id):
    team = get_team(trainer_id, team_id)
    # MySQL evaluates every affordable addition/replacement and ranks distinct species.
    # Python only formats the already-scored rows and hydrates suggested move names.
    rows = query(RECOMMENDATION_SQL, (trainer_id, team_id, LIMIT))
    first = rows[0]

    def scores(row, prefix):
        weaknesses = json.loads(row[prefix + "_weaknesses"])
        coverage = json.loads(row[prefix + "_coverage_types"])
        return dict(exposure=float(row[prefix + "_exposure"]) if row[prefix + "_exposure"] is not None else None,
                    coverage=int(row[prefix + "_coverage"]),
                    weaknesses={k: float(v) for k, v in weaknesses.items() if v is not None},
                    covered_types=sorted(k for k, v in coverage.items() if v > 1))

    before = scores(first, "before")
    suggestions = []
    for row in rows:
        if row["owned_id"] is None:
            continue
        pokemon = catalog()[0][row["pokemon_id"]]
        after = scores(row, "after")
        reason = ("Affordable choice for an empty team." if not team["members"] else
                  f"Defensive exposure {before['exposure']:.2f} → {after['exposure']:.2f}; "
                  f"super-effective coverage {before['coverage']} → {after['coverage']} of 18 types.")
        improved = sorted(t for t in before["weaknesses"] if after["weaknesses"][t] < before["weaknesses"][t] - 1e-9)
        added = sorted(set(after["covered_types"]) - set(before["covered_types"]))
        if improved:
            reason += " Less exposed to: " + ", ".join(improved) + "."
        if added:
            reason += " Adds coverage against: " + ", ".join(added) + "."
        budget = dict(version=team["budget"]["version"], limit=LIMIT, total=int(row["proposed_cost"]),
                      remaining=LIMIT-int(row["proposed_cost"]), within_budget=True)
        move_ids = default_moves(pokemon)
        suggestions.append(dict(owned_id=row["owned_id"], pokemon_id=row["pokemon_id"], name=row["name"],
                                cost=int(row["cost"]), budget=budget, before=before, after=after,
                                exposure_reduction=float(row["exposure_reduction"]), coverage_gain=int(row["coverage_gain"]),
                                replace_owned_id=row["replace_owned_id"], replace_name=row["replace_name"],
                                suggested_moves=[m for m in pokemon["moves"] if m["id"] in move_ids], reason=reason,
                                rank=int(row["recommendation_rank"])))
    return dict(before=before, suggestions=suggestions, budget=team["budget"], empty_team=not team["members"],
                note="MySQL ranks owned additions/replacements by defensive exposure, coverage gain and cost. "
                     "Suggestions use default eligible moves. Review and save changes in Team Builder. "
                     "These scores do not guarantee victory.")
