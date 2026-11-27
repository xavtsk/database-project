"""MySQL service selection and compatibility guardrails, without live services."""
import os
import unittest
from unittest.mock import patch, MagicMock

from backend.config import sql_options
from backend.db import validate_mysql_server, require_mysql


class MySQLSetupTests(unittest.TestCase):
    def test_mysql_versions_support_checks_and_row_alias_import(self):
        for version in ("8.0.19", "8.0.44", "8.4.8", "9.0.1"):
            self.assertEqual(validate_mysql_server(version, "MySQL Community Server - GPL")["version"], version)
        for version, edition in (("5.7.44", "MySQL Community Server"), ("8.0.18", "MySQL Community Server"),
                                 ("12.3.0-MariaDB", "mariadb.org binary distribution"),
                                 ("5.5.5-10.11.0-MariaDB", "MariaDB Server"), ("unknown", "Unknown")):
            with self.subTest(version=version), self.assertRaises(RuntimeError):
                validate_mysql_server(version, edition)

    def test_default_port_avoids_existing_service_and_env_override_is_respected(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(sql_options()["port"], 3307)
            self.assertNotIn("database", sql_options(database=False))
        with patch.dict(os.environ, {"SQL_PORT": "3306", "SQL_DATABASE": "custom"}, clear=True):
            self.assertEqual(sql_options()["port"], 3306)
            self.assertEqual(sql_options()["database"], "custom")

    def test_server_probe_rejects_mariadb_without_writing(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = dict(version="12.3.0-MariaDB", edition="MariaDB Server")
        with self.assertRaisesRegex(RuntimeError, "points to MariaDB"):
            require_mysql(connection)
        self.assertEqual(cursor.execute.call_count, 1)
        self.assertTrue(cursor.execute.call_args.args[0].startswith("SELECT"))


if __name__ == "__main__":
    unittest.main()
