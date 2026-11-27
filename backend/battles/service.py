"""Persist battle snapshots in MongoDB and deliver victory rewards idempotently."""
from copy import deepcopy
from datetime import datetime, timezone
import random
import uuid

from pymongo.errors import DuplicateKeyError

from backend.catalog import STATS, catalog, effectiveness
from backend.config import ROOT
from backend.db import transaction
from backend.errors import ValidationError, integer
from backend.teams.service import default_moves, get_team
from backend.battles.engine import RULES_VERSION, combatant, resolve
from backend.battles.prediction import predict, historical_context
from backend.battles.automation import POLICY, choose_action
from backend.teams.budget import validate_budget
from backend.teams.limits import validate_team_species

RARITIES = (("common", .60), ("uncommon", .25), ("rare", .12), ("legendary", .03))
REWARD_ODDS = {
    "easy": dict(rarities=dict(RARITIES), shiny_chance=.01),
    "medium": dict(rarities=dict(common=.58, uncommon=.25, rare=.12, legendary=.05), shiny_chance=.02),
    "hard": dict(rarities=dict(common=.56, uncommon=.25, rare=.12, legendary=.07), shiny_chance=.03),
}
REWARD_POLICY = "difficulty-rewards-1"
REWARD_POOL_SQL = (ROOT / "database/relational/queries/reward_pool.sql").read_text(encoding="utf-8")


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


def select_reward(rng, difficulty="easy", odds=None):
    odds = deepcopy(odds if odds is not None else REWARD_ODDS[difficulty])
    roll = rng.random()
    cumulative = 0
    for rarity, probability in odds["rarities"].items():
        cumulative += probability
        if roll < cumulative:
            break
    pool = [p for p in catalog()[0].values() if p["rarity"] == rarity]
    selected = rng.choice(pool)
    shiny_roll = rng.random()
    return dict(pokemon_id=selected["id"], name=selected["name"], rarity=rarity, roll=roll,
                is_shiny=shiny_roll < odds["shiny_chance"], shiny_roll=shiny_roll,
                policy=REWARD_POLICY, difficulty=difficulty, odds=odds, delivered=False)


def eligible_reward(reward, pool, battle_id):
    """Keep the saved choice when eligible; otherwise reroll without changing shiny."""
    if not pool:
        raise ValidationError("No collection reward is available; the saved reward remains pending")
    selected = next((p for p in pool if p["id"] == reward["pokemon_id"]), None)
    if selected is None:
        # Retry-stable selection; the SQL reward record becomes authoritative at commit.
        rng = random.Random(f"{battle_id}:{reward.get('policy', 'collection-rewards-1')}")
        same_tier = [p for p in pool if p["rarity"] == reward["rarity"]]
        if same_tier:
            selected = rng.choice(same_tier)
        else:
            weights = reward.get("odds", {}).get("rarities", dict(RARITIES))
            available = [(tier, weight) for tier, weight in weights.items() if any(p["rarity"] == tier for p in pool)]
            threshold, cumulative = rng.random() * sum(weight for _, weight in available), 0
            tier = available[-1][0]
            for tier, weight in available:
                cumulative += weight
                if threshold < cumulative:
                    break
            selected = rng.choice([p for p in pool if p["rarity"] == tier])
    return dict(reward, pokemon_id=selected["id"], name=selected["name"], rarity=selected["rarity"],
                is_shiny=bool(reward.get("is_shiny", False)))


def deliver_reward(battles, battle):
    reward = battle.get("reward")
    if battle["status"] != "win" or not reward or reward["delivered"]:
        return battle
    with transaction() as cursor:
        # A trainer lock serializes starter/reward writes, including two retried requests.
        cursor.execute("SELECT id FROM trainers WHERE id=%s FOR UPDATE", (battle["trainer_id"],))
        if not cursor.fetchone():
            raise ValidationError("Reward trainer no longer exists")
        cursor.execute("""SELECT r.owned_id,o.pokemon_id,o.is_shiny,p.name,p.rarity
            FROM battle_rewards r JOIN owned_pokemon o ON o.id=r.owned_id
            JOIN pokemon p ON p.id=o.pokemon_id WHERE r.battle_id=%s""", (battle["_id"],))
        existing = cursor.fetchone()
        if existing:
            owned_id = existing["owned_id"]
            final_reward = dict(reward, pokemon_id=existing["pokemon_id"], name=existing["name"],
                                rarity=existing["rarity"], is_shiny=bool(existing["is_shiny"]))
        else:
            cursor.execute(REWARD_POOL_SQL, (battle["trainer_id"], bool(reward.get("is_shiny", False))))
            final_reward = eligible_reward(reward, cursor.fetchall(), battle["_id"])
            cursor.execute("INSERT INTO owned_pokemon(trainer_id,pokemon_id,source,is_shiny) VALUES (%s,%s,'reward',%s)",
                           (battle["trainer_id"], final_reward["pokemon_id"], final_reward["is_shiny"]))
            owned_id = cursor.lastrowid
            cursor.execute("INSERT INTO battle_rewards(battle_id,trainer_id,owned_id,rarity,roll) VALUES (%s,%s,%s,%s,%s)",
                           (battle["_id"], battle["trainer_id"], owned_id, final_reward["rarity"], reward["roll"]))
    if final_reward["pokemon_id"] != reward["pokemon_id"]:
        final_reward["rerolled_from"] = reward.get("rerolled_from", dict(pokemon_id=reward["pokemon_id"], name=reward["name"], rarity=reward["rarity"]))
        final_reward["selection_note"] = "The original normal/shiny variant reached its collection limit; a different eligible Pokemon was awarded."
    final_reward.update(delivered=True, owned_id=owned_id)
    # If this fails after the SQL commit, the next read retries safely using battle_id.
    battles.update_one({"_id": battle["_id"], "trainer_id": battle["trainer_id"]}, {"$set": {"reward": final_reward}})
    battle["reward"] = final_reward
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
    validate_team_species(player)
    budget = validate_budget(player)
    opponent, generation = generate_opponent(player, difficulty, rng)
    sides = dict(player=dict(active=0, members=[combatant(m["pokemon"], m["moves"]) for m in team["members"]]),
                 opponent=dict(active=0, members=[combatant(p, default_moves(p)) for p in opponent]))
    prediction = predict(sides, catalog()[2], RULES_VERSION, player, opponent)
    prediction["history"] = historical_context(battles, trainer_id, RULES_VERSION, difficulty, len(player))
    battle = dict(_id=str(uuid.uuid4()), trainer_id=trainer_id, team_id=team_id, team_name=team["name"],
                  difficulty=difficulty, reward_odds=deepcopy(REWARD_ODDS[difficulty]),
                  rules_version=RULES_VERSION, revision=0, status="active",
                  started_at=datetime.now(timezone.utc), ended_at=None, turn_count=0,
                  initial=deepcopy(sides), generation=generation, budget=budget, prediction=prediction,
                  **sides, turns=[], reward=None)
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
    automatic = isinstance(action, dict) and action.get("kind") == "auto"
    if automatic:
        action, reason = choose_action(previous, catalog()[2])
    if isinstance(action, dict) and action.get("kind") == "forfeit":
        updated = deepcopy(previous)
        updated["status"] = "loss"
        updated["turns"].append(dict(number=updated["turn_count"], kind="forfeit", events=[dict(kind="forfeit", side="player")]))
    else:
        updated = resolve(previous, action, rng, catalog()[2])
    # Save the actual selected action, not just the client's 'auto' request.
    turn = updated["turns"][-1]
    turn.update(controller="auto" if automatic else "manual", action=deepcopy(action))
    if automatic:
        turn.update(policy=POLICY, decision=reason)
    updated["revision"] += 1
    if updated["status"] != "active":
        updated["ended_at"] = datetime.now(timezone.utc)
        updated["elapsed_seconds"] = max(0, (updated["ended_at"] - updated["started_at"]).total_seconds())
        if updated["status"] == "win":
            updated["reward"] = select_reward(rng, updated["difficulty"], updated.get("reward_odds"))
    result = battles.replace_one({"_id": battle_id, "trainer_id": trainer_id, "revision": revision, "status": "active"}, updated)
    if result.matched_count != 1:
        raise ValidationError("Another action already resolved this turn; refresh the battle")
    return deliver_reward(battles, updated)
