"""Prepare the approved prototype catalogue; preserve every raw response."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw"
OUTPUT = ROOT / "data/processed/game_data.json"
STAT_NAMES = ("hp", "attack", "defense", "special_attack", "special_defense", "speed")
FALLBACK_MOVES = (33, 1, 98, 129)  # Tackle, Pound, Quick Attack, Swift; project exceptions.


def prepare():
    types = sorted((json.loads(p.read_bytes()) for p in (RAW / "types").glob("*.json")), key=lambda t: t["id"])
    if {t["name"] for t in types} != set("normal fighting flying poison ground rock bug ghost steel fire water grass electric psychic ice dragon dark fairy".split()):
        raise ValueError("All 18 type resources are required; run setup with --fetch-dark once.")
    moves = []
    for path in (RAW / "moves").glob("*.json"):
        m = json.loads(path.read_bytes())
        if isinstance(m["power"], int) and m["power"] > 0 and m["damage_class"]["name"] in ("physical", "special"):
            moves.append(dict(id=m["id"], name=m["name"], type_id=int(m["type"]["url"].rstrip("/").split("/")[-1]),
                              damage_class=m["damage_class"]["name"], power=m["power"], accuracy=m["accuracy"],
                              pp=m["pp"], priority=m["priority"]))
    moves.sort(key=lambda m: m["id"])
    move_ids = {m["id"] for m in moves}
    pokemon, pokemon_types, pokemon_moves = [], [], []
    for number in range(1, 152):
        p = json.loads((RAW / "pokemon" / f"{number:03d}.json").read_bytes())
        s = json.loads((RAW / "species" / f"{number:03d}.json").read_bytes())
        rarity = "legendary" if s["is_legendary"] or s["is_mythical"] else "common" if s["capture_rate"] >= 150 else "uncommon" if s["capture_rate"] >= 75 else "rare"
        description = next((x["flavor_text"] for x in s["flavor_text_entries"] if x["language"]["name"] == "en"), "")
        stats = {x["stat"]["name"].replace("-", "_"): x["base_stat"] for x in p["stats"]}
        pokemon.append(dict(id=number, name=p["name"], **stats, rarity=rarity, description=" ".join(description.split())))
        for t in p["types"]:
            pokemon_types.append(dict(pokemon_id=number, type_id=int(t["type"]["url"].rstrip("/").split("/")[-1]), slot=t["slot"]))
        eligible = {int(x["move"]["url"].rstrip("/").split("/")[-1]) for x in p["moves"]} & move_ids
        original = eligible.copy()
        for fallback in FALLBACK_MOVES:
            if len(eligible) >= 4:
                break
            eligible.add(fallback)
        for move_id in sorted(eligible):
            pokemon_moves.append(dict(pokemon_id=number, move_id=move_id, source="raw" if move_id in original else "project_override"))
    effectiveness = []
    for attack in types:
        relations = attack["damage_relations"]
        for defense in types:
            factor = 1
            for field, value in (("no_damage_to", 0), ("half_damage_to", .5), ("double_damage_to", 2)):
                if defense["name"] in {t["name"] for t in relations[field]}:
                    factor = value
            effectiveness.append(dict(attacking_type=attack["id"], defending_type=defense["id"], multiplier=factor))
    return dict(pokemon=pokemon, types=[dict(id=t["id"], name=t["name"]) for t in types], moves=moves,
                pokemon_types=pokemon_types, pokemon_moves=pokemon_moves, type_effectiveness=effectiveness)


if __name__ == "__main__":
    data = prepare()
    OUTPUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print({table: len(rows) for table, rows in data.items()})
