"""Add per-instance shiny storage without resetting existing collections."""
import pymysql

from backend.config import sql_options
from backend.db import require_mysql


def apply(cursor):
    cursor.execute("SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() "
                   "AND TABLE_NAME='owned_pokemon' AND COLUMN_NAME='is_shiny'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE owned_pokemon ADD COLUMN is_shiny BOOLEAN NOT NULL DEFAULT FALSE "
                       "CHECK(is_shiny IN (0,1))")
        return True
    return False


def migrate():
    with pymysql.connect(**sql_options()) as connection:
        require_mysql(connection)
        with connection.cursor() as cursor:
            changed = apply(cursor)
    print("[MIGRATION] " + ("Added is_shiny; existing Pokemon remain non-shiny" if changed else "Shiny storage is already present"))


if __name__ == "__main__":
    from scripts.run_local import load_environment
    load_environment()
    migrate()
