"""Read-only browser fixtures for rule/difficulty filters and strategy evidence.

Requires a running app and existing requirements-dev.txt. No API writes occur.
Set BROWSER_CHANNEL=msedge to use installed Edge; APP_URL selects the app address.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=os.getenv("BROWSER_CHANNEL") or None)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors, filters, failures = [], [], {}
        page.on("pageerror", lambda error: errors.append(str(error)))

        def api(route):
            assert route.request.method == "GET", "Evidence screen should not write data"
            url = urlparse(route.request.url)
            if url.path in failures:
                status, content_type, body = failures[url.path]
                route.fulfill(status=status, content_type=content_type, body=body)
                return
            if url.path == "/api/session":
                data = dict(csrf="fixture", trainer=dict(id=999999, name="Evidence preview", starter_chosen=True), profiles=[])
            elif url.path == "/api/analytics":
                data = dict(summary=dict(battles=12, wins=7, average_turns=8, average_seconds=60),
                            difficulty=[], moves=[], pokemon=[], predictions=[])
            elif url.path == "/api/analytics/strategy":
                query = parse_qs(url.query, keep_blank_values=True)
                rules = query.get("rules_version", ["prototype-2"])[0]
                difficulty = query.get("difficulty", [""])[0]
                filters.append((rules, difficulty))
                data = dict(rules_version=rules, difficulty=difficulty, rules_versions=["prototype-1", "prototype-2"],
                            battles=4 if rules == "prototype-2" else 0, min_attempts=5, dominant_share=.75,
                            note="Same rules only; misses included. Associations do not establish causal effects.",
                            moves=[], repetition=[], predictions=[])
                if rules == "prototype-2":
                    data.update(moves=[dict(_id=33, name="tackle", attempts=15, damage=94, hit_rate=11/15, damage_per_attempt=94/15)],
                                repetition=[dict(_id=dict(difficulty=difficulty or "medium", team_size=1, pattern="high repetition"),
                                                 battles=1, wins=1, losses=0, draws=0, average_top_share=.875)],
                                predictions=[dict(_id=dict(method="move-pressure-1", label="favoured", outcome="win"), battles=1)])
            elif url.path == "/api/analytics/historical":
                query = parse_qs(url.query)
                pokemon_id = int(query.get("pokemon_id", ["4"])[0])
                opponent_id = int(query.get("opponent_id", ["7"])[0])
                data = dict(pokemon_id=pokemon_id, opponent_id=opponent_id, installed=True,
                            source=dict(license="CC0: Public Domain", manifest_sha256="a" * 64),
                            pokemon=[dict(id=id, name=name) for id, name in ((1, "bulbasaur"), (4, "charmander"), (7, "squirtle"))],
                            note="External synthetic 1v1 results; separate from simulator predictions.",
                            rows=[], battles=0)
                if pokemon_id == 4:
                    data.update(battles=2, rows=[dict(attacker_role="first", battles=1, wins=1, losses=0, win_rate=1),
                                                dict(attacker_role="second", battles=1, wins=0, losses=1, win_rate=0)])
            else:
                data = dict(battles=[])
            route.fulfill(content_type="application/json", body=json.dumps(data))

        page.route("**/api/**", api)
        page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
        page.goto(os.getenv("APP_URL", "http://127.0.0.1:5050") + "/#analytics", wait_until="domcontentloaded")

        def ready():
            page.wait_for_function('!document.querySelector("#main").hasAttribute("aria-busy")')

        ready()
        evidence = page.locator("#strategy-evidence")
        expect(evidence).to_contain_text("4 completed battles")
        expect(evidence).to_contain_text("Small sample")
        expect(evidence).to_contain_text("73.3%")
        expect(evidence).to_contain_text("6.3")
        expect(evidence).to_contain_text("high repetition")
        expect(page.locator("#prediction-results")).to_contain_text("1 / 1 decisive battles")
        external = page.locator("#historical-evidence")
        expect(external).to_contain_text("2 distinct source results")
        expect(external).to_contain_text("CC0")
        expect(external).to_contain_text("first")
        expect(external).to_contain_text("second")
        external.screenshot(path=str(ROOT / ".local/historical-evidence-desktop.png"))
        page.locator('#historical-form [name="pokemon_id"]').select_option("1")
        page.get_by_role("button", name="Compare matchup", exact=True).click(); ready()
        expect(external).to_contain_text("No historical evidence")
        evidence.screenshot(path=str(ROOT / ".local/database-evidence-desktop.png"))
        page.locator('[name="difficulty"]').select_option("hard")
        page.get_by_role("button", name="Apply filters", exact=True).click(); ready()
        assert filters[-1] == ("prototype-2", "hard")
        expect(page.locator('#historical-form [name="pokemon_id"]')).to_have_value("1")
        page.locator('[name="rules_version"]').select_option("prototype-1")
        page.get_by_role("button", name="Apply filters", exact=True).click(); ready()
        expect(evidence).to_contain_text("0 completed battles")
        expect(evidence).to_contain_text("No player attacks")
        expect(page.locator("#prediction-results")).to_contain_text("No completed battles with predictions")
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator('[name="rules_version"]').select_option("prototype-2")
        page.get_by_role("button", name="Apply filters", exact=True).click(); ready()
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        evidence.screenshot(path=str(ROOT / ".local/database-evidence-mobile.png"))
        external.screenshot(path=str(ROOT / ".local/historical-evidence-mobile.png"))
        # A stale backend returns an HTML 404 for a new route. Show restart help.
        failures["/api/analytics/strategy"] = (404, "text/html", "<!doctype html><h1>Not Found</h1>")
        page.reload(wait_until="domcontentloaded"); ready()
        expect(page.locator("#notice")).to_contain_text("/api/analytics/strategy")
        expect(page.locator("#notice")).to_contain_text("HTTP 404")
        expect(page.locator("#notice")).to_contain_text("Restart the Python app")
        failures["/api/analytics/strategy"] = (500, "text/html", "<!doctype html><h1>Internal server error</h1>")
        page.reload(wait_until="domcontentloaded"); ready()
        expect(page.locator("#notice")).to_contain_text("HTTP 500")
        expect(page.locator("#notice")).to_contain_text("Check the app terminal")
        failures["/api/analytics/strategy"] = (503, "application/json", json.dumps(dict(error="Fixture database unavailable")))
        page.reload(wait_until="domcontentloaded"); ready()
        expect(page.locator("#notice")).to_have_text("Fixture database unavailable")
        assert not errors, errors
        print("PASS: strategy filters, damage/attempts including misses, repetition cohorts, small samples, "
              "prediction counts, external matchup roles, empty cohorts, mobile layout and HTML/JSON errors. No API writes.")
        browser.close()


if __name__ == "__main__":
    (ROOT / ".local").mkdir(exist_ok=True)
    check()
