"""Read-only browser fixtures for roster-height collection scrolling and miss chances."""
from copy import deepcopy
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def pokemon(id, name, stat=80):
    return dict(id=id, name=name, types=["grass", "poison"], rarity="common", description="Display fixture",
                **{s: stat for s in ("hp", "attack", "defense", "special_attack", "special_defense", "speed")},
                moves=[dict(id=i, name=name, type="normal", power=power, accuracy=accuracy, pp=10,
                            remaining_pp=10, damage_class="physical", priority=0)
                       for i, name, power, accuracy in ((1, "tackle", 40, 100), (2, "fire-blast", 110, 85),
                                                        (3, "swift", 60, None), (4, "fixture-zero-accuracy", 40, 0))])


def check():
    pool = [pokemon(id, name) for id, name in ((1, "bulbasaur"), (4, "charmander"), (7, "squirtle"),
                                             (25, "pikachu"), (74, "geodude"), (92, "gastly"))]
    owned = [dict(owned_id=1000+i, source="starter" if i == 0 else "reward", pokemon=deepcopy(pool[i % 6])) for i in range(42)]
    owned.append(dict(owned_id=2000, source="reward", pokemon=pokemon(150, "mewtwo", stat=110)))
    # Stress a schema-sized name without changing the actual catalogue.
    owned[-2]["pokemon"]["name"] = "long-pokemon-name-for-a-narrow-panel"
    team = dict(id=42, name="Collection fixture", members=[dict(owned_id=1000, pokemon=pool[0], moves=[1, 2, 3, 4])])
    actor = dict(id=1, name="bulbasaur", types=["grass"], hp=200, max_hp=200, moves=pool[0]["moves"])
    battle = dict(_id="display-fixture", trainer_id=999999, team_name="Display fixture", difficulty="easy",
                  revision=0, status="active", rules_version="prototype-2", turn_count=0, turns=[],
                  player=dict(active=0, members=[deepcopy(actor)]), opponent=dict(active=0, members=[deepcopy(actor)]),
                  generation=dict(player_strength=300, target_strength=300, actual_strength=300))
    errors = []
    empty = [False]

    def api(route):
        assert route.request.method == "GET", "Display checks must not submit API writes"
        path = urlparse(route.request.url).path
        if path == "/api/session":
            data = dict(csrf="fixture", trainer=dict(id=999999, name="Collection preview", starter_chosen=True), profiles=[])
        elif path == "/api/collection":
            data = dict(pokemon=[] if empty[0] else owned)
        elif path == "/api/teams":
            data = dict(teams=[dict(id=42, name=team["name"], size=1)])
        elif path == "/api/teams/42":
            data = team
        elif path == "/api/pokemon":
            data = dict(pokemon=[pool[0]], types=[])
        elif path == "/api/pokemon/1":
            data = pool[0]
        elif path == "/api/battles":
            data = dict(battles=[dict(_id=battle["_id"], status="active")])
        elif path == "/api/battles/display-fixture":
            data = battle
        else:
            raise AssertionError("Unexpected API request: " + path)
        route.fulfill(content_type="application/json", body=json.dumps(data))

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=os.getenv("BROWSER_CHANNEL") or None)
        page = browser.new_page(viewport=dict(width=1440, height=1100))
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/api/**", api)
        page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
        base = os.getenv("APP_URL", "http://127.0.0.1:5050")
        page.goto(base + "/#teams", wait_until="domcontentloaded")

        def ready():
            page.wait_for_function('!document.querySelector("#main").hasAttribute("aria-busy")')

        def card(id):
            return page.locator(f'[data-owned-id="{id}"]')

        def layout():
            result = page.locator(".collection-list").evaluate("e=>({overflow:getComputedStyle(e).overflowY,height:e.clientHeight,content:e.scrollHeight})")
            assert result["overflow"] == "auto" and result["height"] > 50, result
            assert result["content"] > result["height"], result
            panel = page.locator('.collection-panel').bounding_box()
            roster = page.locator('.collection-layout>section').bounding_box()
            if page.viewport_size['width'] > 1100:
                assert abs(panel['y'] + panel['height'] - roster['y'] - roster['height']) < 2, (panel, roster)
            else:
                assert panel['height'] <= page.viewport_size['height'] * .7 + 1, panel
            assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
            assert page.locator(".owned").evaluate_all("rows=>rows.every(e=>e.scrollWidth<=e.clientWidth+1)")
            return panel['height']

        ready();initial_height = layout()
        expect(page.locator(".owned")).to_have_count(43)
        expect(card(1000).get_by_role("button")).to_have_text("In team")
        expect(card(1006).get_by_role("button")).to_have_text("Add to team")  # Separate duplicate instance.
        page.screenshot(path=str(ROOT / ".local/collection-desktop.png"))
        card(2000).scroll_into_view_if_needed()
        assert page.locator(".collection-list").evaluate("e=>e.scrollTop") > 0

        page.locator("#team-name").fill("Unsaved name preserved")
        card(1001).get_by_role("button").click(); ready()
        expect(page.locator("#team-name")).to_have_value("Unsaved name preserved")
        expect(card(1001).get_by_role("button")).to_have_text("In team")
        assert layout() > initial_height
        picker = page.locator('[data-member="0"][data-slot="0"]')
        picker.select_option("2")
        expect(picker.locator("..").locator(".move-accuracy")).to_have_text("Hit 85% · Miss 15%")
        picker.select_option("3")
        expect(picker.locator("..").locator(".move-accuracy")).to_have_text("Hit 100% · Miss 0%")
        picker.select_option("4")
        expect(picker.locator("..").locator(".move-accuracy")).to_have_text("Hit 0% · Miss 100%")

        for id in (1002, 1003, 1004):
            card(id).get_by_role("button").click(); ready()
        expect(card(2000).get_by_role("button")).to_have_text("Over budget")
        card(1005).get_by_role("button").click(); ready()
        expect(card(1006).get_by_role("button")).to_have_text("Team full")
        full_height = layout()
        page.locator('[data-action="remove-member"][data-value="5"]').click(); ready()
        expect(card(1005).get_by_role("button")).to_have_text("Add to team")
        assert layout() < full_height

        page.set_viewport_size(dict(width=390, height=844));layout()
        page.locator(".collection-panel h3").scroll_into_view_if_needed()
        page.screenshot(path=str(ROOT / ".local/collection-mobile.png"))

        page.locator('[data-nav="battle"]').click(); ready()
        expect(page.locator('[data-action="attack"][data-value="2"]')).to_contain_text("Hit 85% · Miss 15%")
        expect(page.locator('[data-action="attack"][data-value="3"]')).to_contain_text("Hit 100% · Miss 0%")
        expect(page.locator('[data-action="attack"][data-value="4"]')).to_contain_text("Hit 0% · Miss 100%")
        for move in battle["player"]["members"][0]["moves"]:
            move["remaining_pp"] = 0
        page.reload(wait_until="domcontentloaded"); ready()
        expect(page.locator('[data-action="attack"][data-value="0"]')).to_contain_text("Hit 100% · Miss 0%")

        page.locator('[data-nav="pokedex"]').click(); ready()
        page.locator('[data-action="pokemon"][data-value="1"]').click(); ready()
        page.locator("#dialog-content details").evaluate("e=>e.open=true")
        expect(page.get_by_role("columnheader", name="Miss chance", exact=True)).to_be_visible()
        expect(page.locator("#dialog-content tr").filter(has_text="fire blast")).to_contain_text("15%")
        page.get_by_label("Close dialog").click(); ready()

        empty[0] = True
        page.locator('[data-nav="teams"]').click(); ready()
        expect(page.locator(".collection-empty")).to_contain_text("Your collection is empty")
        page.locator('[data-action="new-team"]').click(); ready()
        expect(page.locator('.member')).to_have_count(0)
        expect(page.locator('.collection-empty')).to_be_visible()
        assert not errors, errors
        browser.close()
        print("PASS: collection scrolls to last copy, matches growing/shrinking roster height, mobile height cap, duplicate IDs, add/remove/full/budget labels, "
              "unsaved edits, empty state and miss chances including 0%, 100%, null accuracy and fallback. No API writes.")


if __name__ == "__main__":
    (ROOT / ".local").mkdir(exist_ok=True)
    check()
