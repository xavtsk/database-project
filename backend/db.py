"""Small explicit SQL transaction helpers and a shared MongoDB client."""
from contextlib import contextmanager
import os
import re
from queue import Empty, LifoQueue
from threading import BoundedSemaphore
from time import monotonic

import pymysql
from pymongo import MongoClient
from flask import current_app, has_app_context

from backend.config import sql_options


class SQLPool:
    """At most four exclusive connections per app; completed transactions are reused."""

    def __init__(self, options, size=4):
        self.options = dict(options)
        # Single SELECT statements finish without a separate COMMIT round trip.
        # Multi-statement writes explicitly BEGIN in transaction() below.
        self.options['autocommit'] = True
        self.idle = LifoQueue()
        self.slots = BoundedSemaphore(size)

    def acquire(self):
        if not self.slots.acquire(timeout=5):
            raise pymysql.OperationalError(2003, "MySQL connections are busy; retry shortly")
        try:
            try:
                connection, returned_at = self.idle.get_nowait()
            except Empty:
                connection = None
            if connection is not None:
                try:
                    if not connection.open:
                        raise pymysql.InterfaceError(0, "Closed connection")
                    # Avoid an extra network round trip on every short request.
                    if monotonic() - returned_at > 30:
                        connection.ping(reconnect=False)
                except pymysql.MySQLError:
                    connection.close()
                    connection = None
            if connection is None:
                connection = pymysql.connect(**self.options, cursorclass=pymysql.cursors.DictCursor)
            return connection
        except BaseException:
            self.slots.release()
            raise

    def release(self, connection, reusable):
        try:
            if reusable and connection.open:
                self.idle.put((connection, monotonic()))
            else:
                connection.close()
        finally:
            self.slots.release()

    def close(self):
        """Release idle sockets when the app process exits or a test finishes."""
        while True:
            try:
                connection, _ = self.idle.get_nowait()
            except Empty:
                break
            connection.close()


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
def transaction(read_only=False):
    pool = current_app.extensions.get("sql_pool") if has_app_context() else None
    connection = pool.acquire() if pool else pymysql.connect(**sql_options(), autocommit=True, cursorclass=pymysql.cursors.DictCursor)
    reusable = False
    try:
        if not read_only:
            connection.begin()
        with connection.cursor() as cursor:
            yield cursor
        if not read_only:
            connection.commit()
        reusable = True
    except BaseException:
        try:
            connection.rollback()
        except pymysql.MySQLError:
            pass
        raise
    finally:
        if pool:
            pool.release(connection, reusable)
        else:
            connection.close()


def query(sql, params=()):
    """Execute one read statement; grouped writes must use transaction()."""
    for attempt in range(2):
        try:
            with transaction(read_only=True) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except pymysql.OperationalError as error:
            # A dropped idle socket is safe to replace for a standalone read.
            # Never retry grouped writes or authentication/query errors.
            code = error.args[0] if error.args else None
            if attempt or code not in (2006, 2013):
                raise


def mongo_client():
    return MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"),
                       serverSelectionTimeoutMS=3000, tz_aware=True)


def mongo_database(client):
    return client[os.getenv("MONGO_DATABASE", "pokedex_battle")]
