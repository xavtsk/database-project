"""Exercise the real local browser UI. Creates a clearly labelled local test trainer.

Optional dependency: requirements-dev.txt and `python3 -m playwright install chromium`.
Run with an already-running application: python3 scripts/check_browser.py
Override APP_URL to test another local port. Screenshots stay in ignored .local/.
"""
from datetime import datetime
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def check():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("dialog", lambda dialog: dialog.accept())

        def ready():
            page.wait_for_function('!document.querySelector("#main").hasAttribute("aria-busy")')

        def nav(name):
            ready()
            page.locator(f'[data-nav="{name}"]').click()
            ready()

        page.goto(os.getenv("APP_URL", "http://127.0.0.1:5050"), wait_until="networkidle")
        ready()
        assert page.locator(".poke-card").count() == 151
        page.get_by_label("Search Pokémon").fill("bulbasaur")
        page.get_by_role("button", name="Search", exact=True).click(); ready()
        assert page.locator(".poke-card").count() == 1
        page.locator(".poke-card").click(); ready()
        assert page.locator("#dialog-title").inner_text().lower() == "bulbasaur"
        page.get_by_label("Close dialog").click(); ready()
        page.locator('[data-action="profiles"]').click(); ready()
        page.get_by_label("New trainer name").fill("Browser check " + datetime.now().strftime("%H:%M:%S"))
        page.get_by_role("button", name="Create trainer").click(); ready()
        page.locator('[data-action="starter"][data-value="7"]').click(); ready()
        assert page.locator(".member").count() == 1
        nav("analysis")
        assert page.locator(".metric").count() == 4

        wins = 0
        for difficulty in ("easy", "medium", "hard", "easy", "easy"):
            nav("battle")
            if page.locator('[data-action="new-battle"]').count():
                page.locator('[data-action="new-battle"]').click(); ready()
            page.locator('[name="team_id"]').select_option(index=1)
            page.locator(f'[name="difficulty"][value="{difficulty}"]').check()
            page.get_by_role("button", name="Start battle").click(); ready()
            assert page.locator(".arena").count() == 1
            page.reload(wait_until="networkidle"); ready()
            assert page.locator(".arena").count() == 1
            switches = page.locator('[data-action="switch"]:not([disabled])')
            if switches.count():
                switches.first.click(); ready()
            for _ in range(410):
                if page.locator(".result").count():
                    break
                moves = page.locator('[data-action="attack"]:not([disabled])')
                if moves.count():
                    moves.first.click()
                else:
                    page.locator('[data-action="switch"]:not([disabled])').first.click()
                ready()
            assert page.locator(".result").count() == 1
            victory = page.locator(".reward").count() == 1
            wins += victory
            print(difficulty, page.locator(".result h2").inner_text(), flush=True)
            if victory:
                assert "Added to your collection" in page.locator(".reward").inner_text()
                nav("teams")
                available = page.locator('[data-action="add-member"]:not([disabled])')
                if available.count():
                    available.first.click(); ready()
                    page.get_by_role("button", name="Save team", exact=True).click(); ready()
            nav("analytics")
            assert page.locator(".metric").first.locator("strong").inner_text() != "0"
        assert wins > 0, "No wins in this randomized browser run; rerun to exercise rewards."
        nav("teams")
        page.locator('[data-action="new-team"]').click(); ready()
        page.locator("#team-name").fill("Browser CRUD check")
        page.locator('[data-action="add-member"]').first.click(); ready()
        page.get_by_role("button", name="Save team", exact=True).click(); ready()
        page.locator('[data-action="remove-member"]').first.click(); ready()
        page.get_by_role("button", name="Save team", exact=True).click(); ready()
        assert page.locator(".member").count() == 0
        page.get_by_role("button", name="Delete team", exact=True).click(); ready()
        nav("analytics")
        page.screenshot(path=str(ROOT / ".local/analytics-browser-check.png"))
        nav("pokedex")
        page.screenshot(path=str(ROOT / ".local/pokedex-browser-check.png"))
        page.set_viewport_size({"width": 390, "height": 844})
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.screenshot(path=str(ROOT / ".local/mobile-browser-check.png"))
        assert not errors, errors
        print("PASS: all five screens, all difficulties, battle resume, rewards, team CRUD, mobile layout; no JavaScript errors.")
        browser.close()


if __name__ == "__main__":
    (ROOT / ".local").mkdir(exist_ok=True)
    check()
