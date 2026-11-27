"""Read-only comparison of the same delivered-award facts in SQL and MongoDB.

Uses existing awards only. It creates no trainers, battles, tables or indexes.
Connections and one warm-up per store are outside the measured samples.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean, median
from time import perf_counter

import pymysql

from backend.config import sql_options
from backend.db import mongo_client, mongo_database
from scripts.run_local import load_environment


FIELDS = "r.battle_id,r.trainer_id,r.owned_id,o.pokemon_id,o.is_shiny"
AWARDS = " FROM battle_rewards r JOIN owned_pokemon o ON o.id=r.owned_id "
PROJECTION = {"_id": 1, "trainer_id": 1, "reward.owned_id": 1,
              "reward.pokemon_id": 1, "reward.is_shiny": 1}


def sql_rows(rows):
    return sorted((r["battle_id"], int(r["trainer_id"]), int(r["owned_id"]),
                   int(r["pokemon_id"]), bool(r["is_shiny"])) for r in rows)


def mongo_rows(rows):
    return sorted((r["_id"], int(r["trainer_id"]), int(r["reward"]["owned_id"]),
                   int(r["reward"]["pokemon_id"]), bool(r["reward"].get("is_shiny", False))) for r in rows)


def fingerprint(rows):
    return sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def compare(read_sql, read_mongo, expected, samples=7):
    """Alternate store order and reject any sample returning different facts."""
    if not expected:
        raise ValueError("No matching delivered awards; complete a winning battle first")
    times = {"mysql": [], "mongodb": []}
    readers = {"mysql": (read_sql, sql_rows), "mongodb": (read_mongo, mongo_rows)}
    for name, (read, normalize) in readers.items():
        if normalize(read()) != expected:
            raise ValueError(f"{name} warm-up did not return the same award facts")
    for index in range(samples):
        for name in (("mysql", "mongodb") if index % 2 == 0 else ("mongodb", "mysql")):
            read, normalize = readers[name]
            start = perf_counter()
            rows = read()
            elapsed = perf_counter() - start
            if normalize(rows) != expected:
                raise ValueError(f"{name} results changed during measurement; investigate before comparing")
            times[name].append(elapsed)
    return {
        name: dict(samples_seconds=[round(t, 6) for t in values],
                   median_seconds=round(median(values), 6),
                   mean_seconds=round(mean(values), 6),
                   min_seconds=round(min(values), 6), max_seconds=round(max(values), 6))
        for name, values in times.items()
    }


def run(samples=7, limit=100, trainer_id=None):
    if not 3 <= samples <= 30 or not 1 <= limit <= 500:
        raise ValueError("Use 3–30 samples and a cohort limit of 1–500")
    if trainer_id is not None and trainer_id < 1:
        raise ValueError("Trainer ID must be positive")
    with pymysql.connect(**sql_options(), autocommit=True, cursorclass=pymysql.cursors.DictCursor) as connection, \
            mongo_client() as client:
        logs = mongo_database(client).battles
        with connection.cursor() as cursor:
            where = "WHERE r.trainer_id=%s " if trainer_id is not None else ""
            params = (trainer_id, limit) if trainer_id is not None else (limit,)
            cursor.execute("SELECT " + FIELDS + AWARDS + where + "ORDER BY r.battle_id LIMIT %s", params)
            candidates = cursor.fetchall()
        candidate_ids = [r["battle_id"] for r in candidates]
        delivered = list(logs.find({"_id": {"$in": candidate_ids}, "status": "win", "reward.delivered": True}, PROJECTION))
        matched_ids = sorted(r["_id"] for r in delivered)
        included = set(matched_ids)
        expected = sql_rows([r for r in candidates if r["battle_id"] in included])
        if mongo_rows(delivered) != expected:
            raise ValueError("Stored SQL/MongoDB award facts disagree; investigate before benchmarking")
        if not expected:
            raise ValueError("No shared delivered awards; no evidence was fabricated")
        statement = "SELECT " + FIELDS + AWARDS + "WHERE r.battle_id IN (" + ",".join(["%s"] * len(matched_ids)) + ")"

        def read_sql():
            with connection.cursor() as cursor:
                cursor.execute(statement, tuple(matched_ids))
                return cursor.fetchall()

        def read_mongo():
            return list(logs.find({"_id": {"$in": matched_ids}, "status": "win", "reward.delivered": True}, PROJECTION))

        timings = compare(read_sql, read_mongo, expected, samples)
        return dict(measured_at_utc=datetime.now(timezone.utc).isoformat(),
                    workload="Retrieve the same delivered award identity, trainer, owned copy, species and shiny flag",
                    candidate_awards=len(candidates), matched_awards=len(expected),
                    excluded_without_delivered_mongo_award=len(candidates)-len(expected),
                    samples_per_store=samples, equivalent_results=True, result_sha256=fingerprint(expected),
                    timings=timings,
                    method="Persistent connections; one excluded warm-up per store; alternating store order; driver fetch fully consumed; no requested result ordering; canonicalisation outside timing",
                    scope="Existing matching delivered awards only; no production writes; not a full data-consistency audit",
                    limitations=["Different deployments/network paths; cannot isolate database-engine speed",
                                 "Small fixed cohort, warm connections, sequential reads; no throughput, scaling or cold-start claim",
                                 "MySQL joins current ownership; MongoDB reads embedded delivered-award snapshots",
                                 "No end-to-end browser, battle-write or concurrency performance measured"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--trainer-id", type=int)
    parser.add_argument("--output", type=Path, default=Path(".local/evaluation/database-comparison.json"))
    args = parser.parse_args()
    try:
        load_environment()
        result = run(args.samples, args.limit, args.trainer_id)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    except Exception as error:
        # Driver errors can embed private URIs; only print the exception class.
        raise SystemExit(f"Read-only comparison failed ({type(error).__name__}). Check the tunnel and database access.") from None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Equivalent facts verified for {result['matched_awards']} delivered awards.")
    for name, values in result["timings"].items():
        print(f"{name}: median {values['median_seconds']:.4f}s across {args.samples} samples")
    print(f"Report saved to {args.output}. Different deployments: do not infer engine superiority.")


if __name__ == "__main__":
    main()
