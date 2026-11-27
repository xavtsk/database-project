"""API failures stay readable when routes are missing or the server raises."""
import os
import unittest
from unittest.mock import MagicMock, patch

from backend.app import create_app


class APIErrorTests(unittest.TestCase):
    def setUp(self):
        with patch("backend.app.check_mysql"), patch("backend.app.mongo_client", return_value=MagicMock()), \
                patch.dict(os.environ, {"FLASK_SECRET_KEY": "offline-test-secret"}):
            self.app = create_app({"TESTING": True, "PROPAGATE_EXCEPTIONS": False})

        @self.app.get("/api/test-failure")
        def failure():
            raise RuntimeError("internal fixture details")

        self.client = self.app.test_client()

    def test_missing_api_is_json_while_missing_page_stays_html(self):
        response = self.client.get("/api/not-an-existing-route")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.is_json)
        self.assertIn("error", response.json)
        page = self.client.get("/not-an-existing-page")
        self.assertEqual(page.status_code, 404)
        self.assertEqual(page.mimetype, "text/html")

    def test_method_error_preserves_allow_header(self):
        response = self.client.get("/api/profiles/select")
        self.assertEqual(response.status_code, 405)
        self.assertTrue(response.is_json)
        self.assertIn("POST", response.headers["Allow"])

    def test_unexpected_api_error_is_generic_json_and_logs_details(self):
        with self.assertLogs(self.app.logger, level="ERROR") as logs:
            response = self.client.get("/api/test-failure")
        self.assertEqual(response.status_code, 500)
        self.assertIn("Check the app terminal", response.json["error"])
        self.assertNotIn("internal fixture details", response.get_data(as_text=True))
        self.assertIn("internal fixture details", "\n".join(logs.output))

    def test_new_analytics_routes_exist_before_profile_selection(self):
        for path in ("/api/analytics/strategy", "/api/analytics/historical", "/api/analytics/matchups"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 400)
                self.assertIn("Choose or create a trainer", response.json["error"])
