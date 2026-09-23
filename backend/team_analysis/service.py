from backend.catalog import STATS, catalog, effectiveness
from backend.db import query
from backend.teams.service import get_team


def analyse(trainer_id, team_id):
    team = get_team(trainer_id, team_id)
    # These statistics are computed by MariaDB, rather than by the browser.
    aggregates = ",".join(f"SUM(p.{s}) AS total_{s}, AVG(p.{s}) AS average_{s}" for s in STATS)
    stats = query(f"""SELECT COUNT(*) AS size,{aggregates} FROM team_members tm
        JOIN owned_pokemon o ON o.id=tm.owned_id JOIN pokemon p ON p.id=o.pokemon_id
        WHERE tm.team_id=%s""", (team_id,))[0]
    distribution = query("""SELECT t.name,COUNT(*) AS count FROM team_members tm
        JOIN owned_pokemon o ON o.id=tm.owned_id JOIN pokemon_types pt ON pt.pokemon_id=o.pokemon_id
        JOIN types t ON t.id=pt.type_id WHERE tm.team_id=%s GROUP BY t.id,t.name ORDER BY count DESC,t.name""", (team_id,))
    matchups = []
    for type_ in catalog()[1]:
        factors = [effectiveness(type_["name"], m["pokemon"]["types"]) for m in team["members"]]
        matchups.append(dict(type=type_["name"], weak=sum(f > 1 for f in factors),
                             resistant=sum(0 < f < 1 for f in factors), immune=factors.count(0)))
    moves = [move for m in team["members"] for move in m["pokemon"]["moves"] if move["id"] in m["moves"]]
    coverage = [dict(type=t["name"], best_multiplier=max((effectiveness(m["type"], [t["name"]]) for m in moves), default=0)) for t in catalog()[1]]
    return dict(team=team["name"], stats={k: float(v) if v is not None else 0 for k, v in stats.items()},
                distribution=distribution, matchups=matchups, coverage=coverage)
