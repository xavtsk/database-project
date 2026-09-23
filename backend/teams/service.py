"""Trainer collections and saved teams, with transactional ownership checks."""
from backend.catalog import catalog
from backend.db import query, transaction
from backend.errors import ValidationError, integer, text_name


def profiles():
    return query("SELECT id,name,starter_chosen FROM trainers ORDER BY id")


def create_profile(name):
    with transaction() as cursor:
        cursor.execute("INSERT INTO trainers(name) VALUES (%s)", (text_name(name, 40),))
        return cursor.lastrowid


def trainer(trainer_id):
    rows = query("SELECT id,name,starter_chosen FROM trainers WHERE id=%s", (trainer_id,))
    if not rows:
        raise ValidationError("Choose a trainer profile first")
    return rows[0]


def default_moves(pokemon):
    eligible = sorted(pokemon["moves"], key=lambda m: (m["type"] not in pokemon["types"], abs(m["power"] - 70), m["id"]))
    return [m["id"] for m in eligible[:4]]


def choose_starter(trainer_id, pokemon_id):
    integer(pokemon_id, "Pokémon ID")
    if pokemon_id not in (1, 4, 7):
        raise ValidationError("Choose Bulbasaur, Charmander or Squirtle")
    with transaction() as cursor:
        cursor.execute("SELECT * FROM trainers WHERE id=%s FOR UPDATE", (trainer_id,))
        owner = cursor.fetchone()
        if not owner or owner["starter_chosen"]:
            raise ValidationError("This trainer has already chosen a starter")
        cursor.execute("INSERT INTO owned_pokemon(trainer_id,pokemon_id,source) VALUES (%s,%s,'starter')", (trainer_id, pokemon_id))
        owned_id = cursor.lastrowid
        cursor.execute("INSERT INTO teams(trainer_id,name) VALUES (%s,'My first team')", (trainer_id,))
        team_id = cursor.lastrowid
        cursor.execute("INSERT INTO team_members VALUES (%s,1,%s,%s)", (team_id, owned_id, trainer_id))
        for slot, move in enumerate(default_moves(catalog()[0][pokemon_id]), 1):
            cursor.execute("INSERT INTO team_member_moves VALUES (%s,1,%s,%s)", (team_id, slot, move))
        cursor.execute("UPDATE trainers SET starter_chosen=TRUE WHERE id=%s", (trainer_id,))
    return team_id


def collection(trainer_id):
    rows = query("SELECT id AS owned_id,pokemon_id,source,acquired_at FROM owned_pokemon WHERE trainer_id=%s ORDER BY id", (trainer_id,))
    return [dict(row, pokemon=catalog()[0][row["pokemon_id"]]) for row in rows]


def list_teams(trainer_id):
    return query("""SELECT t.id,t.name,COUNT(tm.slot) AS size FROM teams t
        LEFT JOIN team_members tm ON tm.team_id=t.id WHERE t.trainer_id=%s GROUP BY t.id,t.name ORDER BY t.id""", (trainer_id,))


def get_team(trainer_id, team_id):
    with transaction() as cursor:
        cursor.execute("SELECT id,name FROM teams WHERE id=%s AND trainer_id=%s", (team_id, trainer_id))
        team = cursor.fetchone()
        if not team:
            raise ValidationError("Team not found for this trainer")
        cursor.execute("""SELECT tm.slot,tm.owned_id,o.pokemon_id FROM team_members tm
            JOIN owned_pokemon o ON o.id=tm.owned_id WHERE tm.team_id=%s ORDER BY tm.slot""", (team_id,))
        members = cursor.fetchall()
        cursor.execute("SELECT member_slot,move_id FROM team_member_moves WHERE team_id=%s ORDER BY member_slot,move_slot", (team_id,))
        selections = cursor.fetchall()
    team["members"] = [dict(m, pokemon=catalog()[0][m["pokemon_id"]],
                            moves=[s["move_id"] for s in selections if s["member_slot"] == m["slot"]]) for m in members]
    return team


def save_team(trainer_id, name, members, team_id=None):
    name = text_name(name, 60)
    if not isinstance(members, list) or len(members) > 6:
        raise ValidationError("A team can contain at most six Pokémon")
    owned_ids = []
    for member in members:
        if not isinstance(member, dict):
            raise ValidationError("Invalid team member")
        owned_ids.append(integer(member.get("owned_id"), "Owned Pokémon ID"))
    if len(set(owned_ids)) != len(owned_ids):
        raise ValidationError("An owned Pokémon may only appear once in a team")
    with transaction() as cursor:
        cursor.execute("SELECT id FROM trainers WHERE id=%s FOR UPDATE", (trainer_id,))
        if not cursor.fetchone():
            raise ValidationError("Trainer not found")
        cursor.execute("SELECT id,pokemon_id FROM owned_pokemon WHERE trainer_id=%s", (trainer_id,))
        owned = {r["id"]: r["pokemon_id"] for r in cursor.fetchall()}
        for member in members:
            if member["owned_id"] not in owned:
                raise ValidationError("You can only use Pokémon in your collection")
            move_ids = member.get("moves")
            if not isinstance(move_ids, list) or len(move_ids) != 4 or any(type(m) is not int for m in move_ids) or len(set(move_ids)) != 4:
                raise ValidationError("Choose four distinct moves for every member")
            allowed = {m["id"] for m in catalog()[0][owned[member["owned_id"]]]["moves"]}
            if not set(move_ids) <= allowed:
                raise ValidationError("A selected move is not in this Pokémon's fixed move pool")
        if team_id is None:
            cursor.execute("INSERT INTO teams(trainer_id,name) VALUES (%s,%s)", (trainer_id, name))
            team_id = cursor.lastrowid
        else:
            cursor.execute("SELECT id FROM teams WHERE id=%s AND trainer_id=%s FOR UPDATE", (team_id, trainer_id))
            if not cursor.fetchone():
                raise ValidationError("Team not found for this trainer")
            cursor.execute("UPDATE teams SET name=%s WHERE id=%s", (name, team_id))
            cursor.execute("DELETE FROM team_members WHERE team_id=%s", (team_id,))
        for slot, member in enumerate(members, 1):
            cursor.execute("INSERT INTO team_members VALUES (%s,%s,%s,%s)", (team_id, slot, member["owned_id"], trainer_id))
            for move_slot, move_id in enumerate(member["moves"], 1):
                cursor.execute("INSERT INTO team_member_moves VALUES (%s,%s,%s,%s)", (team_id, slot, move_slot, move_id))
    return team_id


def delete_team(trainer_id, team_id):
    with transaction() as cursor:
        cursor.execute("DELETE FROM teams WHERE id=%s AND trainer_id=%s", (team_id, trainer_id))
        if not cursor.rowcount:
            raise ValidationError("Team not found for this trainer")
