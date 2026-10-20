"""Browser checks with API fixtures; never creates trainers, battles or rewards.

Requires the running app plus existing requirements-dev.txt browser dependencies.
Run: python scripts/check_reward_case.py
Set BROWSER_CHANNEL=msedge to use installed Edge instead of Playwright Chromium.
Screenshots are written to ignored .local/.
"""
from copy import deepcopy
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
URL = os.getenv("APP_URL", "http://127.0.0.1:5050")
POOL = [dict(id=id, name=name, rarity=rarity, types=[type_]) for id, name, rarity, type_ in (
    (1, "bulbasaur", "common", "grass"), (4, "charmander", "common", "fire"),
    (7, "squirtle", "common", "water"), (25, "pikachu", "uncommon", "electric"),
    (94, "gengar", "rare", "ghost"), (150, "mewtwo", "legendary", "psychic"))]


def fixture(id="case-browser-fixture", status="win", delivered=True):
    member = dict(id=7, name="squirtle", types=["water"], hp=90, max_hp=100,
                  moves=[dict(id=33, name="tackle", type="normal", power=40, remaining_pp=10)])
    side = dict(active=0, members=[member])
    return dict(_id=id, trainer_id=999999, difficulty="easy", team_name="Reward preview", status=status,
                rules_version="prototype-2", turn_count=4, turns=[], player=side, opponent=deepcopy(side),
                generation=dict(player_strength=314, target_strength=300, actual_strength=310),
                reward=dict(pokemon_id=150, name="mewtwo", rarity="legendary", delivered=delivered)
                if status == "win" else None)


def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=os.getenv("BROWSER_CHANNEL") or None)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        errors, requests = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        fail_catalogue = False

        def api(route):
            request = route.request
            assert request.method == "GET", "Reward presentation must not write to the backend"
            requests.append(request.url)
            path = request.url.split("/api/", 1)[1].split("?", 1)[0]
            if path == "session":
                data = dict(csrf="fixture", trainer=dict(id=999999, name="Preview", starter_chosen=True), profiles=[])
            elif path == "pokemon":
                if fail_catalogue:
                    route.fulfill(status=503, content_type="application/json", body='{"error":"Offline fixture"}')
                    return
                data = dict(pokemon=POOL, types=[])
            elif path == "teams":
                data = dict(teams=[])
            elif path == "collection":
                data = dict(pokemon=[])
            else:
                data = dict(battles=[])
            route.fulfill(content_type="application/json", body=json.dumps(data))

        page.route("**/api/**", api)
        page.route("https://fonts.googleapis.com/**", lambda route: route.abort())

        def ready():
            page.wait_for_function('!document.querySelector("#main").hasAttribute("aria-busy")')

        def show(battle):
            page.evaluate("battle => {state.battle=battle; state.view='battle'; drawBattle();}", battle)

        page.goto(URL + "/#battle", wait_until="domcontentloaded")
        ready()
        battle = fixture()
        show(battle)
        expect(page.get_by_role("button", name="Open reward case", exact=True)).to_be_visible()
        expect(page.locator(".case-revealed")).to_be_hidden()
        page.locator(".reward-case").screenshot(path=str(ROOT / ".local/reward-case-sealed.png"))
        page.get_by_role("button", name="Open reward case", exact=True).click()
        ready()
        expect(page.locator(".case-card")).to_have_count(34)
        expect(page.locator('[data-winner="true"] strong')).to_have_text("mewtwo")
        page.locator(".reward-case").screenshot(path=str(ROOT / ".local/reward-case-opening.png"))
        expect(page.locator(".case-revealed")).to_be_visible(timeout=7000)
        expect(page.locator(".reward-name")).to_have_text("mewtwo")
        expect(page.locator(".case-delivery")).to_have_text("Added to your collection.")
        page.locator(".reward-case").screenshot(path=str(ROOT / ".local/reward-case-revealed.png"))

        # Reload/history renders the same award without another opening or backend mutation.
        page.reload(wait_until="domcontentloaded"); ready(); show(battle)
        expect(page.locator(".case-revealed")).to_be_visible()
        expect(page.get_by_role("button", name="Open reward case", exact=True)).to_be_hidden()

        show(fixture("skip-fixture"))
        page.get_by_role("button", name="Open reward case", exact=True).click(); ready()
        page.get_by_role("button", name="Skip animation", exact=True).click(); ready()
        expect(page.locator(".case-revealed")).to_be_visible()
        expect(page.locator(".reward-name")).to_have_text("mewtwo")

        show(fixture("double-click-fixture"))
        count = len(requests)
        page.get_by_role("button", name="Open reward case", exact=True).evaluate("button => {button.click(); button.click();}")
        ready()
        assert len(requests) == count + 1
        page.get_by_role("button", name="Skip animation", exact=True).click(); ready()
        expect(page.locator(".case-revealed")).to_be_visible()

        show(fixture("cancel-fixture"))
        page.get_by_role("button", name="Open reward case", exact=True).click(); ready()
        page.locator('[data-nav="pokedex"]').click(); ready()
        page.wait_for_timeout(100)
        assert page.locator(".reward-case").count() == 0

        page.emulate_media(reduced_motion="reduce")
        show(fixture("reduced-motion-fixture", delivered=False))
        count = len(requests)
        page.get_by_role("button", name="Open reward case", exact=True).click(); ready()
        expect(page.locator(".case-revealed")).to_be_visible()
        expect(page.locator(".case-delivery")).to_contain_text("delivery pending")
        assert len(requests) == count  # Reduced motion requires no decorative catalogue request.

        page.emulate_media(reduced_motion="no-preference")
        fail_catalogue = True
        show(fixture("offline-fixture"))
        page.get_by_role("button", name="Open reward case", exact=True).click(); ready()
        expect(page.locator(".case-card .ball")).to_have_count(33)
        page.get_by_role("button", name="Skip animation", exact=True).click(); ready()
        expect(page.locator(".reward-name")).to_have_text("mewtwo")

        page.set_viewport_size({"width": 390, "height": 844})
        show(fixture())
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.locator(".reward-case").screenshot(path=str(ROOT / ".local/reward-case-mobile.png"), animations="disabled")
        for status in ("loss", "draw"):
            show(fixture(status=status))
            expect(page.locator(".reward-case")).to_have_count(0)
        assert not errors, errors
        print("PASS: full reel, saved winner, skip, reload, double clicks, navigation cancellation, reduced motion, "
              "pending delivery, failed catalogue, mobile layout and no case for loss/draw. No backend writes.")
        browser.close()


if __name__ == "__main__":
    (ROOT / ".local").mkdir(exist_ok=True)
    check()
