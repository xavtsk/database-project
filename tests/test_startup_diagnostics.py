"""Startup diagnostics distinguish cloud failures and never expose credentials."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pymysql
from pymongo.errors import ConfigurationError, OperationFailure, ServerSelectionTimeoutError

from scripts.run_local import load_environment, startup_failure


class StartupDiagnosticsTests(unittest.TestCase):
    def test_reports_stale_terminal_keys_without_changing_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.env').write_text('SQL_PORT=3308\nSQL_PASSWORD="new-private-password"\nMONGO_URI="mongodb+srv://user:new-secret@cluster.example/"\nPORT=5050\n')
            with patch('scripts.run_local.ROOT', root), patch.dict(os.environ, {
                    'SQL_PORT': '3307', 'SQL_PASSWORD': 'old-private-password',
                    'MONGO_URI': 'mongodb://127.0.0.1:27017', 'PORT': '5051'}, clear=True):
                overrides = load_environment()
                self.assertEqual(overrides, ['SQL_PORT', 'SQL_PASSWORD', 'MONGO_URI'])
                self.assertEqual(os.environ['SQL_PORT'], '3307')
                self.assertEqual(os.environ['SQL_PASSWORD'], 'old-private-password')
                self.assertEqual(os.environ['PORT'], '5051')
                self.assertNotIn('private-password', repr(overrides))
                self.assertNotIn('new-secret', repr(overrides))

    def test_fresh_environment_loads_quoted_atlas_uri_and_cloud_port(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            uri = 'mongodb+srv://user:encoded%40password@cluster.example/?retryWrites=true&w=majority'
            (root / '.env').write_text('SQL_PORT=3308\nMONGO_URI="' + uri + '"\n')
            with patch('scripts.run_local.ROOT', root), patch.dict(os.environ, {}, clear=True):
                self.assertEqual(load_environment(), [])
                self.assertEqual(os.environ['SQL_PORT'], '3308')
                self.assertEqual(os.environ['MONGO_URI'], uri)

    def test_mysql_errors_distinguish_tunnel_authentication_and_missing_data(self):
        with patch.dict(os.environ, {'SQL_HOST': '127.0.0.1', 'SQL_PORT': '3308'}, clear=True):
            for code, expected in ((2003, 'SSH tunnel'), (1045, 'project account'), (1146, 'catalogue')):
                with self.subTest(code=code):
                    message = startup_failure(pymysql.OperationalError(code, 'sensitive-driver-details'), 'Application')
                    self.assertIn(expected, message)
                    self.assertNotIn('sensitive-driver-details', message)

    def test_mongo_errors_distinguish_atlas_network_authentication_and_uri(self):
        secret = 'mongodb+srv://user:do-not-print-this@cluster.example/'
        with patch.dict(os.environ, {'MONGO_URI': secret}, clear=True):
            for error, expected in ((ServerSelectionTimeoutError(secret), 'Atlas connection failed'),
                                    (OperationFailure(secret, code=18), 'database user'),
                                    (ConfigurationError(secret), 'settings are invalid')):
                with self.subTest(kind=type(error).__name__):
                    message = startup_failure(error, 'MongoDB')
                    self.assertIn(expected, message)
                    self.assertNotIn(secret, message)
                    self.assertNotIn('do-not-print-this', message)

    def test_local_mongo_network_error_mentions_local_server(self):
        with patch.dict(os.environ, {'MONGO_URI': 'mongodb://127.0.0.1:27017'}, clear=True):
            message = startup_failure(ServerSelectionTimeoutError('internal network details'), 'MongoDB')
            self.assertIn('configured MongoDB server', message)
            self.assertNotIn('Atlas', message)


if __name__ == '__main__':
    unittest.main()
