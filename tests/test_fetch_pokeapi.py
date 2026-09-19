"""Offline checks for source preservation, caching and recoverable failures."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

from scripts.data_import.fetch_pokeapi import RawDownloader, download_range


def response_with(payload):
    response = Mock()
    response.content = payload
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    return response


class DownloaderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.raw_dir = Path(temporary.name)
        self.session = Mock()
        self.downloader = RawDownloader(self.session, self.raw_dir)
        delay = patch("scripts.data_import.fetch_pokeapi.time.sleep")
        delay.start()
        self.addCleanup(delay.stop)
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def test_preserves_response_bytes_and_cache_prevents_network(self):
        payload = b'{ "id": 1, "extra": {"untouched": [null, 3]}, "name": "bulbasaur" }\n'
        self.session.get.return_value = response_with(payload)
        self.downloader.fetch("pokemon", 1, "pokemon")
        path = self.raw_dir / "pokemon/001.json"
        self.assertEqual(path.read_bytes(), payload)
        self.assertFalse(path.with_suffix(".json.tmp").exists())
        self.session.get.assert_called_once_with(
            "https://pokeapi.co/api/v2/pokemon/1/", timeout=30
        )
        self.session.get.reset_mock()
        self.assertEqual(self.downloader.fetch("pokemon", 1, "pokemon"), json.loads(payload))
        self.session.get.assert_not_called()

    def test_invalid_cache_is_preserved_without_a_request(self):
        path = self.raw_dir / "pokemon/001.json"
        path.parent.mkdir()
        path.write_bytes(b'{"incomplete":')
        self.assertIsNone(self.downloader.fetch("pokemon", 1, "pokemon"))
        self.assertEqual(path.read_bytes(), b'{"incomplete":')
        self.session.get.assert_not_called()
        self.assertEqual(self.downloader.failed, 1)

    def test_http_timeout_and_invalid_json_do_not_create_cache(self):
        bad_status = response_with(b'{"error":"unavailable"}')
        bad_status.raise_for_status.side_effect = requests.HTTPError("503 unavailable")
        self.session.get.side_effect = [
            bad_status, requests.Timeout("timed out"), response_with(b"not JSON")
        ]
        for pokemon_id in range(1, 4):
            self.assertIsNone(self.downloader.fetch("pokemon", pokemon_id, "pokemon"))
        self.assertEqual(list(self.raw_dir.rglob("*.json")), [])
        self.assertEqual(self.downloader.failed, 3)

    def test_failed_write_does_not_leave_a_final_cache_file(self):
        self.session.get.return_value = response_with(b'{"id":1}')
        with patch.object(Path, "replace", side_effect=OSError("write failed")):
            self.assertIsNone(self.downloader.fetch("pokemon", 1, "pokemon"))
        self.assertEqual(list(self.raw_dir.rglob("*.json*")), [])
        self.assertEqual(self.downloader.failed, 1)

    def test_range_continues_after_failure_and_deduplicates_references(self):
        pokemon = json.dumps({
            "types": [{"type": {"name": "grass"}}],
            "moves": [{"move": {"name": "tackle"}}],
        }).encode()

        def get(url, **kwargs):
            if url.endswith("/pokemon/2/"):
                raise requests.Timeout("timed out")
            return response_with(pokemon if "/pokemon/" in url else b'{"id":1}')

        self.session.get.side_effect = get
        self.assertEqual(download_range(self.downloader, 1, 3), 1)
        urls = [call.args[0] for call in self.session.get.call_args_list]
        self.assertEqual(len(urls), 8)
        self.assertEqual(sum("/type/grass/" in url for url in urls), 1)
        self.assertEqual(sum("/move/tackle/" in url for url in urls), 1)
        self.assertTrue((self.raw_dir / "species/002.json").exists())
        self.assertTrue((self.raw_dir / "pokemon/003.json").exists())


if __name__ == "__main__":
    unittest.main()
