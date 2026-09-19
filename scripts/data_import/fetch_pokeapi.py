"""Cache complete PokéAPI responses without transforming the source data."""

import argparse
import json
from pathlib import Path
import re
import time

import requests


API_BASE = "https://pokeapi.co/api/v2"
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 0.2


class RawDownloader:
    def __init__(self, session, raw_dir=RAW_DIR):
        self.session = session
        self.raw_dir = Path(raw_dir)
        self.downloaded = 0
        self.cached = 0
        self.failed = 0

    def error(self, resource, error):
        self.failed += 1
        print(f"[ERROR] {resource}: {error}", flush=True)

    def fetch(self, endpoint, identifier, folder):
        filename = (
            f"{identifier:03d}.json"
            if isinstance(identifier, int)
            else f"{identifier}.json"
        )
        relative_path = Path(folder) / filename
        path = self.raw_dir / relative_path
        temporary_path = path.with_suffix(".json.tmp")

        try:
            if path.exists():
                # Never silently replace an existing source file, even if damaged.
                try:
                    data = json.loads(path.read_bytes())
                    if not isinstance(data, dict):
                        raise ValueError("expected a JSON object")
                except (OSError, ValueError) as error:
                    self.error(
                        relative_path,
                        f"cannot read cache ({error}); inspect or move this file "
                        "before rerunning; no request made",
                    )
                    return None
                self.cached += 1
                print(f"[CACHED] {relative_path}", flush=True)
                return data

            # A single session, sequential requests, no automatic retries.
            time.sleep(REQUEST_DELAY)
            with self.session.get(
                f"{API_BASE}/{endpoint}/{identifier}/", timeout=REQUEST_TIMEOUT
            ) as response:
                response.raise_for_status()
                payload = response.content
                data = json.loads(payload)
                if not isinstance(data, dict):
                    raise ValueError("expected a JSON object")

            path.parent.mkdir(parents=True, exist_ok=True)
            # Validate JSON, then save the original bytes, not re-serialized data.
            # Rename only after writing so an interrupted write is not a cache hit.
            temporary_path.write_bytes(payload)
            temporary_path.replace(path)
            self.downloaded += 1
            print(f"[DOWNLOADED] {relative_path}", flush=True)
            return data
        except (requests.RequestException, OSError, ValueError) as error:
            self.error(relative_path, error)
            return None
        finally:
            if temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError as error:
                    self.error(relative_path, f"could not remove temporary file: {error}")


def referenced_names(pokemon, field, reference_key):
    """Read references only; do not change the cached Pokémon response."""
    names = set()
    for entry in pokemon[field]:
        name = entry[reference_key]["name"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9-]+", name):
            raise ValueError(f"invalid {reference_key} name: {name!r}")
        names.add(name)
    return names


def download_range(downloader, start_id, end_id):
    type_names = set()
    move_names = set()

    for pokemon_id in range(start_id, end_id + 1):
        pokemon = downloader.fetch("pokemon", pokemon_id, "pokemon")
        downloader.fetch("pokemon-species", pokemon_id, "species")
        if pokemon is None:
            continue
        for field, key, names in (
            ("types", "type", type_names),
            ("moves", "move", move_names),
        ):
            try:
                names.update(referenced_names(pokemon, field, key))
            except (KeyError, TypeError, ValueError) as error:
                downloader.error(f"pokemon/{pokemon_id:03d}.json {field}", error)

    print(f"[REFERENCES] {len(type_names)} unique types, {len(move_names)} unique moves")
    for name in sorted(type_names):
        downloader.fetch("type", name, "types")
    for name in sorted(move_names):
        downloader.fetch("move", name, "moves")

    print(
        f"[SUMMARY] downloaded={downloader.downloaded} "
        f"cached={downloader.cached} errors={downloader.failed}",
        flush=True,
    )
    return 1 if downloader.failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-id", type=int, default=1, help="First Pokémon ID (default: 1)")
    parser.add_argument(
        "--end-id", type=int, required=True,
        help="Last Pokémon ID, inclusive; use 3 for the test, 151 after approval",
    )
    args = parser.parse_args()
    if not 1 <= args.start_id <= args.end_id <= 151:
        parser.error("IDs must satisfy 1 <= start-id <= end-id <= 151")

    with requests.Session() as session:
        session.headers.update({"User-Agent": "INF2003-Pokedex-RawData/0.1"})
        return download_range(RawDownloader(session), args.start_id, args.end_id)


if __name__ == "__main__":
    raise SystemExit(main())
