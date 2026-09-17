"""Optional browser acceptance: pip install playwright==1.63.0; playwright install chromium.

Serve the repository root, then run this file with the app index URL as argument.
No production data is changed. Synthetic responses exist only in the browser.
"""
import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8770/generated/viewer/app/index.html'
REPO = '#repository/joku-dev%2Fha-CPsWMS/'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width':1440,'height':1050})
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    def go(hash=''):
        page.goto(URL+hash)
        page.wait_for_selector('h1')
        page.wait_for_timeout(100)
    go()
    assert page.locator('.metric .value').all_text_contents()==['3','1','332','2']
    page.screenshot(path='/tmp/viewer-app-overview.png',full_page=True)
    page.get_by_role('link',name='ha-CPsWMS öffnen').click()
    page.wait_for_selector('.tabs')
    assert page.locator('.metric .value').all_text_contents()==['1','332','121','57']
    # The accepted governance intakes now bind to the measured scan commit.
    assert 'unterschiedliche Commits' not in page.locator('main').inner_text()
    assert page.locator('a[href*="35131186298"]').count() > 0
    assert page.locator('a[href*="35131185047"]').count() > 0
    assert 'FAIL' in page.locator('main').inner_text() # replay is not hidden by governance PASS
    page.screenshot(path='/tmp/viewer-app-repo.png',full_page=True)
    page.locator('nav[aria-label="Repository-Ansichten"]').get_by_role('link',name='Evidence Trust',exact=True).click()
    page.wait_for_selector('[data-trust-domain="devsecops"]')
    dev=page.locator('[data-trust-domain="devsecops"]');arch=page.locator('[data-trust-domain="architecture"]')
    assert 'integrity_verified' in dev.inner_text() and 'FAIL' in dev.inner_text()
    assert 'integrity_verified' in arch.inner_text() and 'PASS' in arch.inner_text()
    assert dev.locator('tbody td:nth-child(2)').all_text_contents()==['6','1','5']
    assert arch.locator('tbody td:nth-child(2)').all_text_contents()==['7','0','5']
    page.screenshot(path='/tmp/viewer-repository-trust.png',full_page=True)
    go(REPO+'security')
    assert page.locator('tbody tr').count()==5
    assert '13 → 1' in page.locator('main').inner_text()
    go(REPO+'findings')
    assert page.locator('[data-finding]').count()==20
    page.get_by_role('button',name='Weiter').click()
    assert 'Seite 2' in page.locator('.pager').inner_text()
    page.locator('#finding-severity').select_option('CRITICAL')
    assert page.locator('[data-finding]').count()==1
    assert 'CVE-2026-43185' in page.locator('[data-finding]').inner_text()
    page.locator('#finding-image').select_option('query-api')
    assert page.locator('[data-finding]').count()==0
    page.locator('#finding-image').select_option('all')
    page.locator('#finding-query').fill('nonexistent-value')
    assert page.locator('[data-finding]').count()==0
    page.locator('#finding-query').fill('43185')
    assert page.locator('[data-finding]').count()==1
    page.screenshot(path='/tmp/viewer-app-findings.png',full_page=True)
    go('#findings')
    page.locator('#finding-repo').select_option('joku-dev/governance-framework-demo-consumer')
    assert page.locator('[data-finding]').count()==0
    go('#repository-security')
    assert page.locator('.repository-security-metrics .value').all_text_contents()==['13','3','1','2']
    assert page.locator('[data-security-criterion]').count()==16
    assert page.locator('[data-security-criterion="GRS-002"] .badge.fail').count()==1
    assert page.locator('[data-security-criterion="GRS-005"] .badge.fail').count()==1
    assert page.locator('[data-security-criterion="GRS-014"] .badge.fail').count()==1
    assert 'report_only' in page.locator('main').inner_text()
    assert page.locator('a[href*="governance-repository-security.json"]').count()==1
    page.screenshot(path='/tmp/viewer-repository-security.png',full_page=True)
    go('#repositories')
    page.locator('#repo-search').fill('ha-CPsWMS')
    assert page.locator('tbody tr').count()==1
    go(REPO+'evidence')
    assert page.locator('.evidence-item').count()==4
    assert page.locator('a[href*="35131185085"]').count()==2
    go('#missing')
    assert page.locator('h1').inner_text()=='Ansicht nicht gefunden'
    go('#%broken')
    assert page.locator('h1').inner_text()=='Ansicht nicht gefunden'
    go(REPO+'summary');page.reload();page.wait_for_selector('.tabs')
    for width in (390, 720, 1024):
        page.set_viewport_size({'width':width,'height':844})
        for hash in ('#overview', REPO+'summary', REPO+'findings', REPO+'trust', '#repository-security', '#evidence'):
            go(hash)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(width,hash)
        go(REPO+'summary')
        if width==390:page.screenshot(path='/tmp/viewer-app-mobile.png',full_page=True)
    go('#overview')
    page.get_by_role('link',name='Befunde',exact=True).click();page.wait_for_selector('#finding-query')
    page.go_back();page.wait_for_selector('h1');assert 'Überblick' in page.locator('h1').inner_text()
    assert not errors,errors
    # A failed fetch must display an error, never reassuring zero counts.
    broken=browser.new_page()
    broken.route('**/data.json',lambda route:route.fulfill(status=503,body='Unavailable'))
    broken.goto(URL);broken.wait_for_selector('[role=alert]')
    assert broken.locator('.metric').count()==0
    # Hostile source text stays text; no event handlers or script-bearing URLs.
    original=page.request.get(URL.rsplit('/',1)[0]+'/data.json').json()
    hostile=json.loads(json.dumps(original));repo=hostile['repositories'][0]
    repo['findings'][0]['package']='<img src=x onerror="window.injected=true">'
    safe=browser.new_page();safe.route('**/data.json',lambda route:route.fulfill(json=hostile))
    safe.goto(URL+REPO+'findings');safe.wait_for_selector('[data-finding]')
    assert '<img' in safe.locator('main').inner_text()
    assert safe.locator('main img').count()==0
    assert safe.evaluate('window.injected') is None
    # Preserve coverage of the warning for genuinely mismatched contexts.
    mismatch=json.loads(json.dumps(original))
    ha=next(r for r in mismatch['repositories'] if r['id']=='joku-dev/ha-CPsWMS')
    ha['devsecops']['commit_id']='0'*40
    mixed=browser.new_page();mixed.route('**/data.json',lambda route:route.fulfill(json=mismatch))
    mixed.goto(URL+REPO+'summary');mixed.wait_for_selector('.tabs')
    assert 'unterschiedliche Commits' in mixed.locator('main').inner_text()
    missing_trust=json.loads(json.dumps(original))
    next(r for r in missing_trust['repositories'] if r['id']=='joku-dev/ha-CPsWMS')['devsecops'].pop('trust')
    absent=browser.new_page();absent.route('**/data.json',lambda route:route.fulfill(json=missing_trust))
    absent.goto(URL+REPO+'trust');absent.wait_for_selector('.trust-card')
    assert 'Kein Evidence-Trust-Status erfasst' in absent.locator('.trust-card').first.inner_text()
    assert absent.locator('.trust-card').first.locator('.badge.pass').count()==0
    empty=browser.new_page();empty.route('**/data.json',lambda route:route.fulfill(json={'version':1,'repositories':[]}))
    empty.goto(URL);empty.wait_for_selector('h1')
    assert empty.locator('.metric .value').all_text_contents()==['0','—','—','0']
    browser.close()
print('Browser acceptance passed: routes, filters, pagination, source links, mobile, errors, empty data and escaping.')
