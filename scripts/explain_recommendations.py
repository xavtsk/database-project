"""Export the actual parameterized MySQL recommendation query plan, without writes."""
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_local import load_environment
from backend.db import query, check_mysql
from backend.teams.service import get_team
from backend.teams.budget import LIMIT
from backend.team_analysis.recommendations import RECOMMENDATION_SQL


def explain(trainer_id, team_id, output):
    load_environment()
    get_team(trainer_id, team_id)  # Confirm the trainer owns this team.
    started = perf_counter()
    row = query("EXPLAIN FORMAT=JSON " + RECOMMENDATION_SQL, (trainer_id, team_id, LIMIT))[0]
    result = dict(query="database/relational/queries/team_recommendations.sql", server=check_mysql(),
                  explain_seconds=perf_counter()-started, plan=json.loads(next(iter(row.values()))))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"[EXPLAIN] Plan saved to {output}. This is a plan, not a measured query speedup.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trainer-id", type=int, required=True)
    parser.add_argument("--team-id", type=int, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / ".local/recommendation-explain.json")
    args = parser.parse_args()
    explain(args.trainer_id, args.team_id, args.output)
