"""Read-only external 1v1 context; never alters simulator predictions or rankings."""
from backend.config import ROOT
from backend.db import query
from backend.errors import ValidationError

MATCHUPS_SQL = (ROOT / "database/relational/queries/historical_matchups.sql").read_text(encoding="utf-8")
SOURCE_URL = "https://www.kaggle.com/terminus7/pokemon-challenge"


def matchup(pokemon_id="4", opponent_id="7"):
    try:
        pokemon_id, opponent_id = int(pokemon_id), int(opponent_id)
    except (TypeError, ValueError):
        raise ValidationError("Choose two Pokemon IDs from 1 to 151") from None
    if not 1 <= pokemon_id <= 151 or not 1 <= opponent_id <= 151 or pokemon_id == opponent_id:
        raise ValidationError("Choose two different Pokemon from IDs 1 to 151")
    sources = query("SELECT id,source_url,license,manifest_sha256,imported_at FROM historical_sources "
                    "WHERE source_url=%s ORDER BY id DESC LIMIT 1", (SOURCE_URL,))
    result = dict(pokemon_id=pokemon_id, opponent_id=opponent_id, installed=bool(sources), source=None,
                  pokemon=query("SELECT id,name FROM pokemon ORDER BY id"), rows=[], battles=0,
                  note="External synthetic 1v1 results from Weedle's Cave, using a different algorithm and some different "
                       "base stats. First-attacker order is preserved; repeated exact rows and unmapped forms are excluded. "
                       "This is separate from your simulator history and is not a team win probability.")
    if sources:
        result["source"] = sources[0]
        result["rows"] = [dict(row, wins=int(row["wins"]), losses=int(row["losses"]), win_rate=float(row["win_rate"]))
                          for row in query(MATCHUPS_SQL, (sources[0]["id"], pokemon_id, opponent_id))]
        result["battles"] = sum(row["battles"] for row in result["rows"])
    return result
