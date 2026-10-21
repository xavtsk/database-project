"""Read-only browser fixtures for shiny collection, team and case presentation."""
from copy import deepcopy
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, expect
from check_collection_display import pokemon

ROOT = Path(__file__).resolve().parents[1]


def check():
    normal = pokemon(1, 'bulbasaur', stat=50)
    shiny = dict(deepcopy(normal), is_shiny=True)
    legend = dict(pokemon(150, 'mewtwo', stat=100), rarity='legendary')
    shiny_legend = dict(deepcopy(legend), is_shiny=True)
    other_legend = dict(pokemon(151, 'mew', stat=100), rarity='legendary')
    owned = [dict(owned_id=id, source='reward', pokemon=p) for id, p in
             ((4, shiny_legend), (1, normal), (5, other_legend), (2, shiny), (3, legend))]
    team = dict(id=42, name='Shiny preview', members=[dict(owned_id=3, pokemon=legend, moves=[1, 2, 3, 4])])
    actor = dict(shiny, hp=200, max_hp=200)
    enemy = dict(normal, hp=200, max_hp=200)
    row = dict(_id='shiny-display-fixture', trainer_id=999999, team_name='Shiny preview', difficulty='easy',
               status='active', rules_version='prototype-2', revision=0, turn_count=0, turns=[],
               player=dict(active=0, members=[actor]), opponent=dict(active=0, members=[enemy]),
               generation=dict(player_strength=300, target_strength=300, actual_strength=300))
    errors = []

    def api(route):
        assert route.request.method == 'GET', 'Shiny display checks must not write to APIs'
        path = urlparse(route.request.url).path
        if path == '/api/session':
            data = dict(csrf='fixture', trainer=dict(id=999999, name='Shiny preview', starter_chosen=True), profiles=[])
        elif path == '/api/collection':
            data = dict(pokemon=owned)
        elif path == '/api/teams':
            data = dict(teams=[dict(id=42, name=team['name'], size=1)])
        elif path == '/api/teams/42':
            data = team
        elif path == '/api/battles':
            # Offer the same resumable ID, then return its latest saved result.
            data = dict(battles=[dict(_id=row['_id'], status='active')])
        elif path == '/api/battles/' + row['_id']:
            data = row
        elif path == '/api/pokemon':
            data = dict(pokemon=[normal, legend, other_legend], types=[])
        else:
            raise AssertionError('Unexpected API: ' + path)
        route.fulfill(content_type='application/json', body=json.dumps(data))

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=os.getenv('BROWSER_CHANNEL') or None)
        page = browser.new_page(viewport=dict(width=1440, height=1100))
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('**/api/**', api)
        page.route('https://fonts.googleapis.com/**', lambda route: route.abort())
        base = os.getenv('APP_URL', 'http://127.0.0.1:5050')

        def ready():
            page.wait_for_function('!document.querySelector("#main").hasAttribute("aria-busy")')

        def card(id):
            return page.locator(f'[data-owned-id="{id}"]')

        page.goto(base + '/#teams', wait_until='domcontentloaded'); ready()
        assert page.locator('.collection-group').evaluate_all('rows=>rows.map(e=>Number(e.dataset.speciesId))') == [1, 150, 151]
        assert page.locator('[data-species-id="1"] .owned').evaluate_all('rows=>rows.map(e=>Number(e.dataset.ownedId))') == [1, 2]
        expect(page.locator('[data-species-id="1"] .collection-group-heading')).to_contain_text('Normal 1 / 6')
        expect(page.locator('[data-species-id="1"] .collection-group-heading')).to_contain_text('Shiny 1 / 6')
        expect(card(2).locator('img')).to_have_attribute('src', normal_sprite := 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/shiny/1.png')
        expect(card(4).get_by_role('button')).to_have_text('Legendary limit')
        expect(card(4).get_by_role('button')).to_be_disabled()
        expect(card(5).get_by_role('button')).to_be_enabled()
        card(2).get_by_role('button').click(); ready()
        expect(page.locator('.member .shiny-badge')).to_have_count(1)
        expect(card(1).get_by_role('button')).to_be_enabled()  # Normal/shiny non-legend may coexist.
        assert card(2).evaluate("e=>getComputedStyle(e,'::after').animationName") == 'shiny-twinkle'
        page.screenshot(path=str(ROOT / '.local/shiny-collection-desktop.png'), full_page=True)

        page.set_viewport_size(dict(width=390, height=844))
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
        assert page.locator('.owned').evaluate_all('rows=>rows.every(e=>e.scrollWidth<=e.clientWidth+1)')
        page.locator('.collection-panel').scroll_into_view_if_needed()
        page.screenshot(path=str(ROOT / '.local/shiny-collection-mobile.png'), full_page=True)
        page.locator('[data-nav="battle"]').click(); ready()
        expect(page.locator('[data-side="player"] .battle-sprite')).to_have_attribute('src', normal_sprite.replace('/shiny/', '/back/shiny/'))
        expect(page.locator('[data-side="player"] .shiny-badge')).to_be_visible()
        expect(page.locator('[data-action="switch"]')).to_contain_text('Shiny bulbasaur')
        assert page.locator('[data-side="player"] .sprite-stage').evaluate("e=>getComputedStyle(e,'::after').animationName") == 'shiny-twinkle'
        page.emulate_media(reduced_motion='reduce')
        assert page.locator('[data-side="player"] .sprite-stage').evaluate("e=>getComputedStyle(e,'::after').animationName") == 'none'
        page.emulate_media(reduced_motion='no-preference')

        row.update(status='win', reward=dict(pokemon_id=1, name='bulbasaur', rarity='common', is_shiny=True,
                                            delivered=True, owned_id=2, selection_note='Full variant rerolled.'))
        page.reload(wait_until='domcontentloaded'); ready()
        expect(page.locator('.case-sealed')).to_be_visible()
        expect(page.locator('.case-revealed')).to_be_hidden()
        page.locator('[data-action="open-reward"]').click()
        expect(page.locator('.case-opening')).to_be_visible()
        expect(page.locator('.case-card[data-winner="true"] img')).to_have_attribute('src', normal_sprite)
        page.locator('[data-action="skip-reward"]').click(); ready()
        expect(page.locator('.case-revealed .shiny-badge')).to_be_visible()
        expect(page.locator('.reward-name')).to_have_text('Shiny bulbasaur')
        expect(page.locator('.case-revealed')).to_contain_text('Full variant rerolled.')
        page.locator('.case-revealed').evaluate('async e=>{await Promise.all(e.getAnimations().map(a=>a.finished))}')
        page.screenshot(path=str(ROOT / '.local/shiny-case-mobile.png'))
        page.reload(wait_until='domcontentloaded'); ready()
        expect(page.locator('.case-revealed')).to_be_visible()
        page.emulate_media(reduced_motion='reduce')
        assert page.locator('.case-burst').evaluate('e=>getComputedStyle(e).animationName') == 'none'
        assert not errors, errors
        browser.close()
        print('PASS: species order, separate variant counts, shiny sprites/badges, team legendary guard, '
              'desktop/mobile layout, battle sparkles, reduced motion and persisted shiny case reveal. No API writes.')


if __name__ == '__main__':
    (ROOT / '.local').mkdir(exist_ok=True)
    check()
