"""Persist battle snapshots in MongoDB and deliver victory rewards idempotently."""
from copy import deepcopy
from datetime import datetime, timezone
import random
import uuid

from pymongo.errors import DuplicateKeyError

from backend.catalog import STATS, catalog, effectiveness
from backend.db import transaction
from backend.errors import ValidationError, integer
from backend.teams.service import default_moves, get_team
from backend.battles.engine import RULES_VERSION, combatant, resolve

RARITIES = (("common", .60), ("uncommon", .25), ("rare", .12), ("legendary", .03))


def strength(team):
    return sum(p[s] for p in team for s in STATS)


def generate_opponent(player, difficulty, rng):
    if difficulty not in ("easy", "medium", "hard"):
        raise ValidationError("Choose Easy, Medium or Hard")
    pool = list(catalog()[0].values())
    target = strength(player) * {"easy": .85, "medium": 1, "hard": 1.15}[difficulty]
    candidates = [rng.sample(pool, len(player)) for _ in range(100)]
    candidates.sort(key=lambda team: abs(strength(team) - target))
    closest = abs(strength(candidates[0]) - target)
    shortlist = [team for team in candidates if abs(strength(team) - target) <= closest + target * .05]

    def matchup(team):
        def pressure(a, b):
            return sum(max(effectiveness(t, target_["types"]) for t in attacker["types"]) for attacker in a for target_ in b) / (len(a) * len(b))
        return pressure(team, player) - pressure(player, team)

    selected = min(shortlist, key=matchup) if difficulty == "easy" else max(shortlist, key=matchup) if difficulty == "hard" else min(shortlist, key=lambda team: abs(matchup(team)))
    return selected, dict(player_strength=strength(player), target_strength=target,
                         actual_strength=strength(selected), matchup_score=matchup(selected), candidates=100)


def select_reward(rng):
    roll = rng.random()
    cumulative = 0
    for rarity, probability in RARITIES:
        cumulative += probability
        if roll < cumulative:
            break
    pool = [p for p in catalog()[0].values() if p["rarity"] == rarity]
    selected = rng.choice(pool)
    return dict(pokemon_id=selected["id"], name=selected["name"], rarity=rarity, roll=roll, delivered=False)


def deliver_reward(battles, battle):
    reward = battle.get("reward")
    if battle["status"] != "win" or not reward or reward["delivered"]:
        return battle
    with transaction() as cursor:
        # A trainer lock serializes starter/reward writes, including two retried requests.
        cursor.execute("SELECT id FROM trainers WHERE id=%s FOR UPDATE", (battle["trainer_id"],))
        if not cursor.fetchone():
            raise ValidationError("Reward trainer no longer exists")
        cursor.execute("SELECT owned_id FROM battle_rewards WHERE battle_id=%s", (battle["_id"],))
        existing = cursor.fetchone()
        if existing:
            owned_id = existing["owned_id"]
        else:
            cursor.execute("INSERT INTO owned_pokemon(trainer_id,pokemon_id,source) VALUES (%s,%s,'reward')", (battle["trainer_id"], reward["pokemon_id"]))
            owned_id = cursor.lastrowid
            cursor.execute("INSERT INTO battle_rewards(battle_id,trainer_id,owned_id,rarity,roll) VALUES (%s,%s,%s,%s,%s)",
                           (battle["_id"], battle["trainer_id"], owned_id, reward["rarity"], reward["roll"]))
    # If this fails after the SQL commit, the next read retries safely using battle_id.
    battles.update_one({"_id": battle["_id"]}, {"$set": {"reward.delivered": True, "reward.owned_id": owned_id}})
    reward.update(delivered=True, owned_id=owned_id)
    return battle


def get_battle(battles, trainer_id, battle_id):
    battle = battles.find_one({"_id": battle_id, "trainer_id": trainer_id})
    if not battle:
        raise ValidationError("Battle not found for this trainer")
    return deliver_reward(battles, battle)


def start_battle(battles, trainer_id, team_id, difficulty, rng=None):
    rng = rng or random.Random()
    team = get_team(trainer_id, integer(team_id, "Team ID"))
    if not 1 <= len(team["members"]) <= 6:
        raise ValidationError("Choose a team with 1–6 Pokémon")
    player = [m["pokemon"] for m in team["members"]]
    opponent, generation = generate_opponent(player, difficulty, rng)
    sides = dict(player=dict(active=0, members=[combatant(m["pokemon"], m["moves"]) for m in team["members"]]),
                 opponent=dict(active=0, members=[combatant(p, default_moves(p)) for p in opponent]))
    battle = dict(_id=str(uuid.uuid4()), trainer_id=trainer_id, team_id=team_id, team_name=team["name"],
                  difficulty=difficulty, rules_version=RULES_VERSION, revision=0, status="active",
                  started_at=datetime.now(timezone.utc), ended_at=None, turn_count=0,
                  initial=deepcopy(sides), generation=generation, **sides, turns=[], reward=None)
    try:
        battles.insert_one(battle)
    except DuplicateKeyError as error:
        raise ValidationError("Finish or forfeit your current battle before starting another") from error
    return battle


def act(battles, trainer_id, battle_id, revision, action, rng=None):
    integer(revision, "Battle revision")
    rng = rng or random.Random()
    previous = get_battle(battles, trainer_id, battle_id)
    if previous["revision"] != revision or previous["status"] != "active":
        raise ValidationError("Battle changed; refresh before choosing another action")
    if isinstance(action, dict) and action.get("kind") == "forfeit":
        updated = deepcopy(previous)
        updated["status"] = "loss"
        updated["turns"].append(dict(number=updated["turn_count"], kind="forfeit", events=[dict(kind="forfeit", side="player")]))
    else:
        updated = resolve(previous, action, rng, catalog()[2])
    updated["revision"] += 1
    if updated["status"] != "active":
        updated["ended_at"] = datetime.now(timezone.utc)
        updated["elapsed_seconds"] = max(0, (updated["ended_at"] - updated["started_at"]).total_seconds())
        if updated["status"] == "win":
            updated["reward"] = select_reward(rng)
    result = battles.replace_one({"_id": battle_id, "trainer_id": trainer_id, "revision": revision, "status": "active"}, updated)
    if result.matched_count != 1:
        raise ValidationError("Another action already resolved this turn; refresh the battle")
    return deliver_reward(battles, updated)
