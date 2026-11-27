"""Audit cached PokéAPI records and stage normalized rows before any SQL import.

Raw bytes are hashed and never changed. Invalid required records reject the whole
batch, leaving the previous staged catalogue and database untouched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from scripts.data_import.prepare_game_data import RAW, ROOT, OUTPUT, STAT_NAMES, prepare

REPORT = ROOT / ".local/import-audit.json"
TYPE_NAMES = set("normal fighting flying poison ground rock bug ghost steel fire water grass electric psychic dragon dark fairy ice".split())
KEYS = {"pokemon": ("id",), "types": ("id",), "moves": ("id",), "pokemon_types": ("pokemon_id", "slot"),
        "pokemon_moves": ("pokemon_id", "move_id"), "type_effectiveness": ("attacking_type", "defending_type")}


def integer(value, minimum=0, maximum=None):
    return type(value) is int and value >= minimum and (maximum is None or value <= maximum)


def reference(value, kind):
    match = re.search(r"/" + re.escape(kind) + r"/(\d+)/?$", value.get("url", "")) if isinstance(value, dict) else None
    if not match:
        raise ValueError(f"Invalid {kind} reference")
    return int(match[1])


def write_report(report, path=REPORT):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def validate_tables(data):
    """Independently verify primary keys and foreign references of normalized rows."""
    issues = []
    for table, fields in KEYS.items():
        keys = [tuple(r[f] for f in fields) for r in data[table]]
        if len(set(keys)) != len(keys):
            issues.append(dict(file=table, reason="Duplicate normalized primary key"))
    for table in ("pokemon", "types", "moves"):
        if len({r["name"] for r in data[table]}) != len(data[table]):
            issues.append(dict(file=table, reason="Duplicate normalized unique name"))
    pokemon = {r["id"] for r in data["pokemon"]}
    types = {r["id"] for r in data["types"]}
    moves = {r["id"] for r in data["moves"]}
    checks = (("pokemon_types", "pokemon_id", pokemon), ("pokemon_types", "type_id", types),
              ("moves", "type_id", types), ("pokemon_moves", "pokemon_id", pokemon),
              ("pokemon_moves", "move_id", moves), ("type_effectiveness", "attacking_type", types),
              ("type_effectiveness", "defending_type", types))
    for table, column, parent in checks:
        if any(r[column] not in parent for r in data[table]):
            issues.append(dict(file=table, reason=f"Unresolved foreign key: {column}"))
    if pokemon != set(range(1, 152)):
        issues.append(dict(file="pokemon", reason="Expected IDs 1–151 exactly"))
    if len(data["type_effectiveness"]) != 18 * 18:
        issues.append(dict(file="type_effectiveness", reason="Expected a complete 18×18 chart"))
    return issues


def audit(raw_dir=RAW):
    raw_dir = Path(raw_dir)
    resources, sources, issues, excluded, filtered = {}, [], [], [], []

    def reject(path, reason):
        issues.append(dict(file=path, reason=reason))

    def load(relative):
        try:
            body = (raw_dir / relative).read_bytes()
            sources.append(dict(file=relative, bytes=len(body), sha256=hashlib.sha256(body).hexdigest()))
            record = json.loads(body)
            if not isinstance(record, dict):
                raise ValueError("Expected a JSON object")
            resources[relative] = record
            return record
        except (OSError, ValueError) as error:
            reject(relative, "Missing/unreadable source" if isinstance(error, OSError) else "Invalid JSON object")
            return None

    def validate(path, function):
        try:
            function()
        except (KeyError, TypeError, ValueError, AttributeError, IndexError):
            reject(path, "Invalid required fields or unresolved source reference")

    def require(condition):
        if not condition:
            raise ValueError("Invalid field")

    for name in sorted(TYPE_NAMES):
        load(f"types/{name}.json")
    type_ids = {Path(path).stem: r.get("id") if integer(r.get("id"), 1) else None
                for path, r in resources.items() if path.startswith("types/")}
    for name in sorted(TYPE_NAMES):
        path = f"types/{name}.json"
        if path not in resources:
            continue
        def check_type(name=name, path=path):
            t = resources[path]
            require(t["name"] == name and integer(t["id"], 1))
            for relation in ("no_damage_to", "half_damage_to", "double_damage_to"):
                require(isinstance(t["damage_relations"][relation], list))
                for linked in t["damage_relations"][relation]:
                    require(linked["name"] in TYPE_NAMES and reference(linked, "type") == type_ids[linked["name"]])
        validate(path, check_type)
    if len(set(type_ids.values())) != 18:
        reject("types", "Missing or duplicate type identifiers")

    required_moves = {}
    for id in range(1, 152):
        ppath, spath = f"pokemon/{id:03d}.json", f"species/{id:03d}.json"
        p, s = load(ppath), load(spath)
        if p is not None:
            def check_pokemon(p=p, id=id):
                require(integer(p["id"], 1) and p["id"] == id and isinstance(p["name"], str) and bool(p["name"]))
                require(reference(p["species"], "pokemon-species") == id)
                require(len(p["stats"]) == 6)
                stats = {r["stat"]["name"].replace("-", "_"): r["base_stat"] for r in p["stats"]}
                require(set(stats) == set(STAT_NAMES) and all(integer(v, 1, 255) for v in stats.values()))
                require(1 <= len(p["types"]) <= 2 and sorted(t["slot"] for t in p["types"]) == list(range(1, len(p["types"])+1)))
                require(len({t["type"]["name"] for t in p["types"]}) == len(p["types"]))
                for t in p["types"]:
                    require(t["type"]["name"] in TYPE_NAMES and reference(t["type"], "type") == type_ids[t["type"]["name"]])
                for item in p["moves"]:
                    move = item["move"]
                    require(isinstance(move["name"], str) and re.fullmatch(r"[a-z0-9-]+", move["name"]) is not None)
                    move_id = reference(move, "move")
                    require(move["name"] not in required_moves or required_moves[move["name"]] == move_id)
                    required_moves[move["name"]] = move_id
            validate(ppath, check_pokemon)
        if s is not None:
            def check_species(s=s, id=id):
                require(integer(s["id"], 1) and s["id"] == id and type(s["is_legendary"]) is bool and type(s["is_mythical"]) is bool)
                require(p is None or s["name"] == p["name"])
                require(integer(s["capture_rate"], 0, 255) and isinstance(s["flavor_text_entries"], list))
                for entry in s["flavor_text_entries"]:
                    require(isinstance(entry["flavor_text"], str) and isinstance(entry["language"]["name"], str))
            validate(spath, check_species)

    for name, id in sorted(required_moves.items()):
        path = f"moves/{name}.json"
        m = load(path)
        if m is None:
            continue
        def check_move(m=m, id=id, name=name):
            require(integer(m["id"], 1) and m["id"] == id and m["name"] == name)
            require(m["type"]["name"] in TYPE_NAMES and reference(m["type"], "type") == type_ids[m["type"]["name"]])
            require(m["damage_class"]["name"] in ("physical", "special", "status"))
            require(m["power"] is None or integer(m["power"], 0))
            require(m["accuracy"] is None or integer(m["accuracy"], 0, 100))
            require(integer(m["pp"], 1) and type(m["priority"]) is int)
        validate(path, check_move)
        damage_class = m.get("damage_class")
        if m.get("power") is None or m.get("power") == 0 or isinstance(damage_class, dict) and damage_class.get("name") == "status":
            filtered.append(dict(file=path, reason="Outside the approved positive-power physical/special move pool"))

    for kind in ("pokemon", "species", "types", "moves"):
        for path in sorted((raw_dir / kind).glob("*.json")):
            relative = path.relative_to(raw_dir).as_posix()
            if relative not in resources and not any(i["file"] == relative for i in issues):
                excluded.append(dict(file=relative, reason="Outside the selected ID/type/reference scope"))
    data = None
    identities = set()
    for path, record in resources.items():
        identity = (path.split("/", 1)[0], record.get("id"))
        if not integer(identity[1], 1):
            continue
        if identity in identities:
            reject(path, "Duplicate raw resource identifier")
        identities.add(identity)
    if not issues:
        try:
            data = prepare(raw_dir, resources=resources)
            issues.extend(validate_tables(data))
        except (KeyError, TypeError, ValueError, AttributeError):
            reject("normalized catalogue", "Normalization failed validation")
    sources.sort(key=lambda s: s["file"])
    digest = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()
    report = dict(audit_version=1, source="PokéAPI v2 local cache", status="rejected" if issues else "validated",
                  dataset_sha256=digest, source_files=len(sources), sources=sources, issues=issues,
                  excluded_sources=excluded, filtered_moves=filtered,
                  table_counts={k: len(v) for k, v in data.items()} if data is not None else {},
                  project_move_overrides=sum(r["source"] == "project_override" for r in data["pokemon_moves"]) if data else 0)
    return (None if issues else data), report


def stage(raw_dir=RAW, output=OUTPUT, report_path=REPORT):
    data, report = audit(raw_dir)
    write_report(report, report_path)
    if data is None:
        raise ValueError(f"Catalogue import rejected: {len(report['issues'])} issues. See {report_path}")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    return data, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=RAW)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--stage", action="store_true", help="Replace game_data.json only after successful validation")
    args = parser.parse_args()
    if args.stage:
        _, result = stage(args.raw_dir, report_path=args.report)
    else:
        _, result = audit(args.raw_dir)
        write_report(result, args.report)
    print(f"[AUDIT] {result['status']}: {result['source_files']} files, {len(result['issues'])} issues; {args.report}")
    raise SystemExit(1 if result["issues"] else 0)
