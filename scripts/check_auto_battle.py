"""Browser fixtures for animation, single-step automation and safe interruption.

Requires a running app and requirements-dev.txt. Every API call is intercepted;
POSTs only resolve an in-memory battle with the actual engine. No database writes.
"""
import json
import os
from pathlib import Path
import random
import sys
from time import monotonic
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright, expect
from backend.battles.automation import POLICY, choose_action
from backend.battles.engine import resolve
from tests.test_battle_engine import battle, fighter


def fixture():
    first, second, enemy = fighter("bulbasaur", 100), fighter("charmander", 90), fighter("squirtle", 10)
    for p, id in ((first, 1), (second, 4), (enemy, 7)):
        p.update(id=id, hp=200, max_hp=200)
        p["moves"][0].update(name="water-pulse", type="water")
        p["moves"][1].update(name="risky-attack", accuracy=0)
    row = battle(player=[first, second], opponent=[enemy])
    row.update(_id="animation-fixture", trainer_id=999999, team_name="Animation fixture", revision=0,
               rules_version="prototype-2", reward=None,
               generation=dict(player_strength=600, target_strength=600, actual_strength=600))
    return row


def check():
    chart = {(a, b): 1 for a in ("normal", "water") for b in ("normal", "water")}
    saved, posts, pending, errors = [fixture()], [], [], []
    options = dict(hold=False, fail=False)

    def reply(route, data, status=200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(data))

    def finish(route, request):
        before = saved[0]
        assert request["revision"] == before["revision"], "Only one action may be in flight"
        requested = request["action"]
        automatic = requested["kind"] == "auto"
        action, reason = choose_action(before, chart) if automatic else (requested, "")
        after = resolve(before, action, random.Random(20), chart)
        after["revision"] += 1
        after["turns"][-1].update(controller="auto" if automatic else "manual", action=action)
        if automatic:
            after["turns"][-1].update(policy=POLICY, decision=reason)
        if after["status"] == "win":
            after["reward"] = dict(pokemon_id=1, name="bulbasaur", rarity="common", delivered=True)
        saved[0] = after
        reply(route, after)

    def api(route):
        path = urlparse(route.request.url).path
        if route.request.method == "POST":
            assert path == "/api/battles/animation-fixture/actions", "Unexpected API write"
            request = route.request.post_data_json
            posts.append(request)
            if options["fail"]:
                options["fail"] = False
                reply(route, dict(error="Fixture turn failed; automation stopped."), 500)
            elif options["hold"]:
                options["hold"] = False
                pending.append((route, request))
            else:
                finish(route, request)
        elif path == "/api/session":
            reply(route, dict(csrf="fixture", trainer=dict(id=999999, name="Auto preview", starter_chosen=True), profiles=[]))
        elif path == "/api/battles":
            reply(route, dict(battles=[dict(_id=saved[0]["_id"], status=saved[0]["status"])]))
        elif path == "/api/battles/animation-fixture":
            reply(route, saved[0])
        elif path == "/api/pokemon":
            reply(route, dict(pokemon=[], types=[]))
        else:
            raise AssertionError("Unexpected API request: " + path)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=os.getenv("BROWSER_CHANNEL") or None)
        page = browser.new_page(viewport=dict(width=1440, height=1100))
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/api/**", api)
        page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
        url = os.getenv("APP_URL", "http://127.0.0.1:5050") + "/#battle"
        page.goto(url, wait_until="domcontentloaded")

        def ready():
            page.wait_for_function('!document.querySelector("#main").hasAttribute("aria-busy")')

        def layout():
            expect(page.locator('.arena-message')).to_have_count(0)
            expect(page.locator('.battle-message')).to_have_count(1)
            arena = page.locator('.arena').bounding_box()
            controls = page.locator('.battle-controls').bounding_box()
            analysis = page.locator('.battle-analysis').bounding_box()
            battle_box = page.locator('.battle-layout').bounding_box()
            message = page.locator('.battle-message').bounding_box()
            assert message['y'] >= arena['y'] + arena['height'], (arena, message)
            assert analysis['y'] >= battle_box['y'] + battle_box['height'], (analysis, battle_box)
            if page.viewport_size['width'] > 1200:
                assert controls['x'] >= arena['x'] + arena['width'], (arena, controls)
                assert abs(controls['y'] - arena['y']) < 2, (arena, controls)
            else:
                assert controls['y'] >= arena['y'] + arena['height'], (arena, controls)
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
            assert page.locator('.move-button').evaluate_all('items=>items.every(e=>e.scrollWidth<=e.clientWidth+1)')
            player = page.locator('[data-side="player"] .sprite-stage').bounding_box()
            opponent = page.locator('[data-side="opponent"] .sprite-stage').bounding_box()
            assert player['x'] < opponent['x'] and player['y'] > opponent['y'], (player, opponent)
            for actor in (player, opponent):
                assert actor['x'] >= arena['x'] and actor['y'] >= arena['y'], (actor, arena)
                assert actor['x'] + actor['width'] <= arena['x'] + arena['width'], (actor, arena)
                assert actor['y'] + actor['height'] <= arena['y'] + arena['height'], (actor, arena)
                for panel in page.locator('.fighter-info').all():
                    box = panel.bounding_box()
                    overlap = (actor['x'] < box['x'] + box['width'] and box['x'] < actor['x'] + actor['width']
                               and actor['y'] < box['y'] + box['height'] and box['y'] < actor['y'] + actor['height'])
                    assert not overlap, (actor, box)
            assert 'battlefield.svg' in page.locator('.arena').evaluate('e=>getComputedStyle(e).backgroundImage')

        def capture_messages():
            page.evaluate('''() => {
                window.messageObserver?.disconnect();window.battleMessages=[];
                window.messageObserver=new MutationObserver(()=>{
                    const text=document.querySelector('.battle-message')?.textContent;
                    if(text&&window.battleMessages.at(-1)!==text)window.battleMessages.push(text);
                });
                window.messageObserver.observe(document.querySelector('#main'),{subtree:true,childList:true,characterData:true});
            }''')

        def check_messages():
            expected = page.evaluate('state.battle.turns.at(-1).events.map(eventText)')
            actual = page.evaluate('window.battleMessages')
            position = 0
            for text in expected:
                assert text in actual[position:], (expected, actual)
                position = actual.index(text, position) + 1
            expect(page.locator('.battle-message')).to_have_text(expected[-1])

        def held_request():
            deadline = monotonic() + 5
            while not pending and monotonic() < deadline:
                page.wait_for_timeout(20)
            assert len(pending) == 1, "The fixture should hold exactly one request"

        def reset():
            assert not pending
            saved[0] = fixture()
            page.goto(url, wait_until="domcontentloaded")
            page.reload(wait_until="domcontentloaded")
            ready()

        ready()
        layout()
        try:
            page.wait_for_function('Array.from(document.querySelectorAll(".battle-sprite")).every(e=>e.complete)', timeout=8000)
        except Exception:
            pass  # External sprite availability must not prevent layout verification.
        page.screenshot(path=str(ROOT / '.local/battle-sidebar-desktop.png'), full_page=True)
        page.locator('.arena').screenshot(path=str(ROOT / '.local/pixel-battle-desktop.png'))
        for width in (1280, 1024, 390, 320):
            page.set_viewport_size(dict(width=width, height=900)); layout()
        page.set_viewport_size(dict(width=390, height=844))
        page.locator('.arena').screenshot(path=str(ROOT / '.local/pixel-battle-mobile.png'))
        page.set_viewport_size(dict(width=1440, height=1100))
        capture_messages()
        page.locator('[data-action="attack"][data-value="1"]').click()
        expect(page.locator('.battle-message')).to_contain_text('Your bulbasaur used water pulse.')
        expect(page.locator(".battle-projectile")).to_be_visible(timeout=5000)
        page.locator(".arena").screenshot(path=str(ROOT / ".local/battle-attack-desktop.png"))
        ready()
        check_messages()
        expect(page.locator(".battle-log")).to_contain_text("MANUAL")
        expect(page.locator('[data-side="opponent"] .hp')).to_have_attribute("aria-valuenow", str(saved[0]["opponent"]["members"][0]["hp"]))

        # Pause must work during a pending response, without sending a second turn.
        options["hold"] = True
        count = len(posts)
        with page.expect_request("**/actions"):
            page.get_by_role("button", name="Auto Battle", exact=True).click()
        held_request()
        expect(page.get_by_role("button", name="Pause Auto Battle", exact=True)).to_be_visible()
        expect(page.locator('[data-action="attack"]').first).to_be_disabled()
        assert len(pending) == 1
        page.get_by_role("button", name="Pause Auto Battle", exact=True).click()
        finish(*pending.pop())
        expect(page.locator("#auto-status")).to_have_text("Manual control", timeout=10000)
        page.wait_for_timeout(900)
        assert len(posts) == count + 1
        expect(page.locator(".battle-log")).to_contain_text("highest estimated")

        # A manual switch and a miss also use saved events for their visuals.
        page.locator('[data-action="switch"][data-value="1"]').click(); ready()
        expect(page.locator('[data-side="player"] h3')).to_have_text("charmander")
        page.locator('[data-action="attack"][data-value="2"]').click()
        expect(page.locator(".battle-miss")).to_contain_text("Miss", timeout=5000)
        ready()

        # Type messages use recorded multipliers, including dual-type results.
        for multiplier, text in ((2, 'Super effective!'), (4, 'Super effective!'),
                                 (.5, 'Not very effective.'), (.25, 'Not very effective.'), (0, 'No effect')):
            reset()
            chart[('water', 'normal')] = multiplier
            capture_messages()
            page.locator('[data-action="attack"][data-value="1"]').click()
            expect(page.locator('.battle-type-message')).to_contain_text(text, timeout=5000)
            expect(page.locator('.battle-message')).to_contain_text(text)
            ready()
            check_messages()
            expect(page.locator('.battle-log')).to_contain_text(text)
            expect(page.locator('.arena-message')).to_have_count(0)
            if multiplier == 0:
                assert saved[0]['opponent']['members'][0]['hp'] == 200
                assert saved[0]['player']['members'][0]['hp'] == 200
            page.reload(wait_until='domcontentloaded'); ready()
            expect(page.locator('.battle-log')).to_contain_text(text)

        # A miss must not claim that an attack was super effective or immune.
        reset()
        chart[('water', 'normal')] = 2
        saved[0]['player']['members'][0]['moves'][0]['accuracy'] = 0
        page.reload(wait_until='domcontentloaded'); ready()
        page.locator('[data-action="attack"][data-value="1"]').click()
        expect(page.locator('.battle-miss')).to_have_text('Miss', timeout=5000)
        ready()
        player_event = page.evaluate('eventText(state.battle.turns.at(-1).events.find(e=>e.side==="player"))')
        assert 'It missed.' in player_event and 'effective' not in player_event
        assert page.evaluate('effectivenessText({hit:true,effectiveness:1})') == ''
        assert page.evaluate('effectivenessText({hit:true})') == ''  # Legacy missing multiplier.

        page.emulate_media(reduced_motion='reduce')
        reset()
        capture_messages()
        page.locator('[data-action="attack"][data-value="1"]').click(); ready()
        check_messages()
        expect(page.locator('.arena-message')).to_have_count(0)
        expect(page.locator('.battle-log')).to_contain_text('Super effective!')
        page.emulate_media(reduced_motion='no-preference')
        chart[('water', 'normal')] = 1

        # A player's knockout is announced and kept visible for replacement.
        reset()
        saved[0]['player']['members'][0]['hp'] = 1
        saved[0]['opponent']['members'][0]['stats']['speed'] = 200
        for move in saved[0]['opponent']['members'][0]['moves']:
            move.update(accuracy=None, power=80)
        page.reload(wait_until='domcontentloaded'); ready(); capture_messages()
        page.locator('[data-action="attack"][data-value="1"]').click()
        expect(page.locator('.battle-message')).to_have_text('Your bulbasaur fainted.', timeout=6000)
        ready(); check_messages()

        # The automatic free replacement must not consume a combat turn.
        reset()
        saved[0]["player"]["members"][0]["hp"] = 0
        page.reload(wait_until="domcontentloaded"); ready()
        options["hold"] = True
        with page.expect_request("**/actions"):
            page.get_by_role("button", name="Auto Battle", exact=True).click()
        held_request()
        page.get_by_role("button", name="Pause Auto Battle", exact=True).click()
        finish(*pending.pop())
        expect(page.locator("#auto-status")).to_have_text("Manual control", timeout=10000)
        assert saved[0]["turn_count"] == 0 and saved[0]["player"]["active"] == 1
        expect(page.locator(".battle-log")).to_contain_text("REPLACEMENT · AUTO")

        # An in-flight response cannot reopen battle or queue turns after navigation.
        reset(); options["hold"] = True
        with page.expect_request("**/actions"):
            page.get_by_role("button", name="Auto Battle", exact=True).click()
        held_request()
        count = len(posts)
        page.locator('[data-nav="pokedex"]').click(); ready()
        finish(*pending.pop())
        page.wait_for_timeout(1000)
        assert len(posts) == count, (count, len(posts), page.url, posts[-2:])
        expect(page.locator(".arena")).to_have_count(0)
        expect(page.locator('[data-nav="pokedex"]')).to_have_attribute("aria-current", "page")

        # Failed actions stop the loop and recover state with a read, without retries.
        reset(); options["fail"] = True
        count = len(posts)
        page.get_by_role("button", name="Auto Battle", exact=True).click()
        expect(page.locator("#notice")).to_contain_text("Fixture turn failed", timeout=5000)
        expect(page.locator("#auto-status")).to_have_text("Manual control")
        page.wait_for_timeout(1000)
        assert len(posts) == count + 1 and saved[0]["revision"] == 0

        # Hidden tabs pause before the next scheduled action.
        page.get_by_role("button", name="Auto Battle", exact=True).click()
        page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))")
        expect(page.locator("#auto-status")).to_have_text("Manual control")
        page.wait_for_timeout(900)
        assert len(posts) == count + 1
        page.evaluate("delete document.hidden")

        # Reduced motion keeps readable messages without starting movement effects.
        reset()
        page.emulate_media(reduced_motion="reduce")
        page.evaluate("() => {window.battleMotionCalls=0;const original=Element.prototype.animate;Element.prototype.animate=function(...args){if(this.matches('.battle-sprite,.battle-projectile,.battle-damage'))window.battleMotionCalls++;return original.apply(this,args)}}")
        page.locator('[data-action="attack"][data-value="1"]').click(); ready()
        assert page.evaluate("window.battleMotionCalls") == 0
        expect(page.locator('[data-side="opponent"] .hp')).to_have_attribute("aria-valuenow", str(saved[0]["opponent"]["members"][0]["hp"]))
        page.set_viewport_size(dict(width=390, height=844))
        layout()
        page.screenshot(path=str(ROOT / '.local/battle-sidebar-mobile.png'), full_page=True)
        assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
        page.locator(".arena").screenshot(path=str(ROOT / ".local/battle-arena-mobile.png"))

        # Automation stops at a result; the existing reward case remains available.
        saved[0] = fixture(); saved[0]["opponent"]["members"][0]["hp"] = 1
        page.reload(wait_until="domcontentloaded"); ready()
        count = len(posts)
        page.get_by_role("button", name="Auto Battle", exact=True).click()
        expect(page.locator(".reward-case")).to_be_visible(timeout=5000)
        page.wait_for_timeout(1000)
        assert len(posts) == count + 1
        expect(page.get_by_role("button", name="Open reward case", exact=True)).to_be_visible()
        expect(page.locator('[data-action="auto-battle"]')).to_have_count(0)
        expect(page.locator('.battle-message')).to_have_text('Opponent’s squirtle fainted.')
        assert not errors, errors
        browser.close()
        print("PASS: manual attacks/switches/misses, auto choice explanations, pause in flight, replacement, "
              "navigation, hidden tabs, failed requests, reduced motion, mobile layout and victory stop. No database writes.")


if __name__ == "__main__":
    (ROOT / ".local").mkdir(exist_ok=True)
    check()
