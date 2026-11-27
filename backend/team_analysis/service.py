from backend.catalog import STATS
from backend.config import ROOT
from backend.db import query
from backend.teams.service import get_team

QUERY_DIR = ROOT / "database/relational/queries"
MATCHUPS_SQL = (QUERY_DIR / "team_matchups.sql").read_text(encoding="utf-8")
COVERAGE_SQL = (QUERY_DIR / "team_coverage.sql").read_text(encoding="utf-8")


def analyse(trainer_id, team_id):
    team = get_team(trainer_id, team_id)
    # These statistics are computed by MySQL, rather than by the browser.
    aggregates = ",".join(f"SUM(p.{s}) AS total_{s}, AVG(p.{s}) AS average_{s}" for s in STATS)
    stats = query(f"""SELECT COUNT(*) AS size,{aggregates} FROM team_members tm
        JOIN owned_pokemon o ON o.id=tm.owned_id JOIN pokemon p ON p.id=o.pokemon_id
        WHERE tm.team_id=%s""", (team_id,))[0]
    distribution = query("""SELECT t.name,COUNT(*) AS count FROM team_members tm
        JOIN owned_pokemon o ON o.id=tm.owned_id JOIN pokemon_types pt ON pt.pokemon_id=o.pokemon_id
        JOIN types t ON t.id=pt.type_id WHERE tm.team_id=%s GROUP BY t.id,t.name ORDER BY count DESC,t.name""", (team_id,))
    matchups = [dict(type=r["name"], **{k: int(r[k]) for k in ("weak", "double_weak", "resistant", "immune")})
                for r in query(MATCHUPS_SQL, (team_id,))]
    coverage = [dict(type=r["type"], best_multiplier=float(r["best_multiplier"]))
                for r in query(COVERAGE_SQL, (team_id,))]
    return dict(team=team["name"], stats={k: float(v) if v is not None else 0 for k, v in stats.items()},
                distribution=distribution, matchups=matchups, coverage=coverage, budget=team["budget"])
