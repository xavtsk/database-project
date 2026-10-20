"""Small explicit SQL transaction helpers and a shared MongoDB client."""
from contextlib import contextmanager
import os
import re

import pymysql
from pymongo import MongoClient

from backend.config import sql_options


def validate_mysql_server(version, edition):
    """Reject the wrong service before setup writes any schema or catalogue data."""
    if "mariadb" in (version + " " + edition).lower():
        raise RuntimeError("This project now uses MySQL Server. The configured SQL_HOST/SQL_PORT points to MariaDB. "
                           "Connect to your MySQL service instead (the local setup uses port 3307).")
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match or tuple(map(int, match.groups())) < (8, 0, 19) or "mysql" not in edition.lower():
        raise RuntimeError("MySQL Server 8.0.19 or newer is required; MySQL 8.4 LTS is recommended.")
    return dict(version=version, edition=edition)


def require_mysql(connection):
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT VERSION() AS version, @@version_comment AS edition")
        info = cursor.fetchone()
    return validate_mysql_server(info["version"], info["edition"])


def check_mysql():
    # No database selection: this also works before the schema has been created.
    with pymysql.connect(**sql_options(database=False)) as connection:
        return require_mysql(connection)


@contextmanager
def transaction():
    connection = pymysql.connect(**sql_options(), cursorclass=pymysql.cursors.DictCursor)
    try:
        with connection.cursor() as cursor:
            yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def query(sql, params=()):
    with transaction() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def mongo_client():
    return MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"),
                       serverSelectionTimeoutMS=3000, tz_aware=True)


def mongo_database(client):
    return client[os.getenv("MONGO_DATABASE", "pokedex_battle")]
