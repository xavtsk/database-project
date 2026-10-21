"""Species rules shared by team saves, battle entry and recommendations."""
from collections import Counter

from backend.errors import ValidationError

NON_LEGENDARY_COLLECTION_LIMIT = 6


def legendary_duplicates(pokemon):
    counts = Counter(p["id"] for p in pokemon if p.get("rarity") == "legendary")
    return {id for id, count in counts.items() if count > 1}


def validate_team_species(pokemon):
    pokemon = list(pokemon)
    duplicates = legendary_duplicates(pokemon)
    if duplicates:
        name = next(p["name"] for p in pokemon if p["id"] in duplicates)
        raise ValidationError(f"Only one {name} is allowed per team: legendary species cannot be duplicated")
