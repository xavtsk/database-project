"""Small explicit SQL transaction helpers and a shared MongoDB client."""
from contextlib import contextmanager
import os

import pymysql
from pymongo import MongoClient

from backend.config import sql_options


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
