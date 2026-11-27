"""SQL-backed catalogue shared by the five features."""
from functools import lru_cache
from backend.db import query

STATS = ("hp", "attack", "defense", "special_attack", "special_defense", "speed")


@lru_cache(maxsize=1)
def catalog():
    pokemon = {p["id"]: dict(p, types=[], moves=[]) for p in query("SELECT * FROM pokemon ORDER BY id")}
    types = query("SELECT * FROM types ORDER BY id")
    moves = {m["id"]: m for m in query("SELECT m.*, t.name AS type FROM moves m JOIN types t ON t.id=m.type_id ORDER BY m.id")}
    for row in query("SELECT pt.*,t.name FROM pokemon_types pt JOIN types t ON t.id=pt.type_id ORDER BY pt.slot"):
        pokemon[row["pokemon_id"]]["types"].append(row["name"])
    for row in query("SELECT * FROM pokemon_moves ORDER BY pokemon_id,move_id"):
        pokemon[row["pokemon_id"]]["moves"].append(dict(moves[row["move_id"]], source=row["source"]))
    effectiveness = {}
    names = {t["id"]: t["name"] for t in types}
    for row in query("SELECT * FROM type_effectiveness"):
        effectiveness[(names[row["attacking_type"]], names[row["defending_type"]])] = float(row["multiplier"])
    return pokemon, types, effectiveness


def effectiveness(attack_type, defense_types):
    factor = 1
    chart = catalog()[2]
    for defense in defense_types:
        factor *= chart[(attack_type, defense)]
    return factor
