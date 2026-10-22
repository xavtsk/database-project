"""Connection reuse must preserve transaction boundaries and exclusive checkout."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
import unittest
from unittest.mock import MagicMock, patch

from flask import Flask
import pymysql

from backend.db import SQLPool, query, transaction


class SQLPoolTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.pool = SQLPool({}, size=2)
        self.app.extensions['sql_pool'] = self.pool
        self.addCleanup(self.pool.close)
        self.factory = patch('backend.db.pymysql.connect').start()
        self.addCleanup(patch.stopall)
        self.connections = []

        def connect(**kwargs):
            connection = MagicMock(open=True)
            self.connections.append(connection)
            return connection

        self.factory.side_effect = connect

    def test_reads_reuse_connection_without_begin_or_commit(self):
        with self.app.app_context():
            query('SELECT %s', (1,))
            query('SELECT %s', (2,))
        self.assertEqual(self.factory.call_count, 1)
        connection = self.pool.acquire()
        connection.commit.assert_not_called()
        connection.begin.assert_not_called()
        connection.close.assert_not_called()
        self.assertTrue(self.factory.call_args.kwargs['autocommit'])
        self.pool.release(connection, True)

    def test_writes_begin_and_commit_before_a_later_read(self):
        with self.app.app_context():
            with transaction() as cursor:
                cursor.execute('UPDATE fixture SET value=1')
            query('SELECT value FROM fixture')
        self.assertEqual(self.factory.call_count, 1)
        connection = self.connections[0]
        connection.begin.assert_called_once()
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()

    def test_command_line_read_closes_its_autocommit_connection(self):
        query('SELECT 1')
        connection = self.connections[0]
        connection.begin.assert_not_called()
        connection.commit.assert_not_called()
        connection.close.assert_called_once()
        self.assertTrue(self.factory.call_args.kwargs['autocommit'])

    def test_dropped_read_retries_once_with_a_fresh_connection(self):
        failed, replacement = MagicMock(open=True), MagicMock(open=True)
        failed.cursor.return_value.__enter__.return_value.execute.side_effect = pymysql.OperationalError(2013, 'dropped')
        replacement.cursor.return_value.__enter__.return_value.fetchall.return_value = [{'value':1}]
        self.factory.side_effect = [failed, replacement]
        with self.app.app_context():
            self.assertEqual(query('SELECT value FROM fixture'), [{'value':1}])
        failed.close.assert_called_once()
        replacement.commit.assert_not_called()
        self.assertEqual(self.factory.call_count, 2)

    def test_persistent_read_disconnect_stops_after_one_retry(self):
        def broken(**kwargs):
            connection = MagicMock(open=True)
            connection.cursor.return_value.__enter__.return_value.execute.side_effect = pymysql.OperationalError(2013, 'dropped')
            return connection
        self.factory.side_effect = broken
        with self.app.app_context(), self.assertRaises(pymysql.OperationalError):
            query('SELECT 1')
        self.assertEqual(self.factory.call_count, 2)

    def test_read_query_errors_are_not_retried(self):
        connection = MagicMock(open=True)
        connection.cursor.return_value.__enter__.return_value.execute.side_effect = pymysql.OperationalError(1045, 'access denied')
        self.factory.side_effect = None
        self.factory.return_value = connection
        with self.app.app_context(), self.assertRaises(pymysql.OperationalError):
            query('SELECT 1')
        self.factory.assert_called_once()

    def test_failed_transaction_rolls_back_and_discards_connection(self):
        with self.app.app_context():
            with self.assertRaisesRegex(ValueError, 'cancel update'):
                with transaction():
                    raise ValueError('cancel update')
        self.connections[0].rollback.assert_called_once()
        self.connections[0].commit.assert_not_called()
        self.connections[0].close.assert_called_once()
        self.assertEqual(self.factory.call_count, 1)
        with self.app.app_context(), transaction():
            pass
        self.assertEqual(self.factory.call_count, 2)

    def test_commit_failure_does_not_retry_or_reuse_a_write(self):
        connection = MagicMock(open=True)
        connection.commit.side_effect = pymysql.OperationalError(2013, 'lost connection')
        self.factory.side_effect = None
        self.factory.return_value = connection
        with self.app.app_context(), self.assertRaises(pymysql.OperationalError):
            with transaction() as cursor:
                cursor.execute('UPDATE fixture SET value=1')
        connection.rollback.assert_called_once()
        connection.close.assert_called_once()
        self.assertEqual(cursor.execute.call_count, 1)
        self.assertTrue(self.pool.idle.empty())

    def test_idle_broken_connection_is_replaced_before_work(self):
        first = self.pool.acquire()
        self.pool.release(first, True)
        first.ping.side_effect = pymysql.OperationalError(2013, 'tunnel ended')
        with patch('backend.db.monotonic', return_value=10**12):
            replacement = self.pool.acquire()
        self.assertIsNot(first, replacement)
        first.ping.assert_called_once_with(reconnect=False)
        first.close.assert_called_once()
        self.pool.release(replacement, True)

    def test_failed_connect_returns_capacity(self):
        self.factory.side_effect = pymysql.OperationalError(2003, 'offline')
        for _ in range(3):
            with self.assertRaises(pymysql.OperationalError):
                self.pool.acquire()
        # Both slots remain available even after repeated connection failures.
        self.assertTrue(self.pool.slots.acquire(blocking=False))
        self.assertTrue(self.pool.slots.acquire(blocking=False))
        self.assertFalse(self.pool.slots.acquire(blocking=False))
        self.pool.slots.release()
        self.pool.slots.release()

    def test_overlapping_transactions_have_distinct_connections(self):
        ready = Barrier(3)
        finish = Event()

        def work():
            with self.app.app_context(), transaction() as cursor:
                ready.wait(timeout=3)
                if not finish.wait(timeout=3):
                    raise TimeoutError('Test did not release worker')
                return cursor

        with ThreadPoolExecutor(max_workers=2) as executor:
            first, second = executor.submit(work), executor.submit(work)
            try:
                ready.wait(timeout=3)
                self.assertEqual(self.factory.call_count, 2)
            finally:
                finish.set()
            self.assertIsNot(first.result(), second.result())


if __name__ == '__main__':
    unittest.main()
