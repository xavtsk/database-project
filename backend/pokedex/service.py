from backend.catalog import catalog
from backend.db import query
from backend.errors import ValidationError


def browse(search="", type_name=""):
    # Parameterized filtering is performed in SQL; nested query demonstrates type membership.
    rows = query("""SELECT p.id FROM pokemon p WHERE
        (p.name LIKE %s OR CAST(p.id AS CHAR)=%s)
        AND (%s='' OR p.id IN (SELECT pt.pokemon_id FROM pokemon_types pt
            JOIN types t ON t.id=pt.type_id WHERE t.name=%s)) ORDER BY p.id""",
        (f"%{search}%", search, type_name, type_name))
    return [{k: v for k, v in catalog()[0][r["id"]].items() if k != "moves"} for r in rows]


def detail(pokemon_id):
    if pokemon_id not in catalog()[0]:
        raise ValidationError("Pokémon not found")
    return catalog()[0][pokemon_id]
