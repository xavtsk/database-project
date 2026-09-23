"""Environment configuration; credentials never belong in source control."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sql_options(database=True):
    options = dict(
        host=os.getenv("SQL_HOST", "127.0.0.1"),
        port=int(os.getenv("SQL_PORT", "3306")),
        user=os.getenv("SQL_USER", "pokedex"),
        password=os.getenv("SQL_PASSWORD", ""),
        charset="utf8mb4", connect_timeout=5,
    )
    if os.getenv("SQL_SOCKET"):
        options["unix_socket"] = os.environ["SQL_SOCKET"]
    if database:
        options["database"] = os.getenv("SQL_DATABASE", "pokedex_battle")
    return options
