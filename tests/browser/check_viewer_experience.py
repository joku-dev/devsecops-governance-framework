"""Current-data UX acceptance, including missing evidence and mobile reading."""
from copy import deepcopy
import json
import sys
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8772/generated/viewer/app/index.html'
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width':1440, 'height':1000})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    data = page.request.get(urljoin(URL, 'data.json')).json()
    def go(route='overview'):
        page.goto(URL+'#'+route)
        page.wait_for_selector('h1')
    go()
    assert page.locator('.priority-card').count()==3
    page.get_by_role('link', name='Handlungsbedarf', exact=False).click()
    page.wait_for_selector('#repo-filter')
    assert page.locator('#repo-filter').input_value()=='attention'
    page.locator('#repo-search').fill('no-such-repository')
    assert page.locator('#repo-results tbody tr').count()==0
    assert 'Keine passenden' in page.locator('#repo-results').inner_text()
    go('repositories/quality')
    assert page.locator('#repo-filter').input_value()=='quality'
    go('cases')
    assert page.locator('.case-timeline li').count()==len(data['consumer_case']['timeline'])
    assert 'Abgeschlossen' in page.locator('main').inner_text()
    assert page.locator('.case-timeline a').count()==len(data['consumer_case']['timeline'])
    repo=data['repositories'][0]
    from urllib.parse import quote
    base='repository/'+quote(repo['id'],safe='')+'/'
    go(base+'summary')
    assert page.locator('.decision-summary').count()==1
    assert 'Alter allein ist kein Freshness-Urteil' in page.locator('.decision-summary').inner_text()
    go(base+'trust')
    assert 'Integrität verifiziert' in page.locator('main').inner_text()
    assert page.locator('details summary').count()>=2
    for width in (390,720,1440):
        page.set_viewport_size({'width':width,'height':900})
        for route in ('overview','repositories/quality','cases',base+'summary',base+'trust'):
            go(route)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(width,route)
        go('overview')
        page.screenshot(path=f'/tmp/governance-viewer-experience-{width}.png',full_page=True)
    # Unknown/missing data cannot imply zero cases or successful governance.
    fixture=deepcopy(data)
    fixture['consumer_case']={'available':False}
    fixture['repositories'][0]['devsecops']=None
    fixture['repositories'][0]['architecture']=None
    fixture['repositories'][0]['id']='<img src=x onerror=alert(1)>'
    page.route('**/data.json', lambda route: route.fulfill(content_type='application/json',body=json.dumps(fixture)))
    page.reload()
    page.wait_for_selector('h1')
    go()
    assert page.locator('.priority-card strong').nth(2).inner_text()=='—'
    go('cases')
    assert 'nicht verifiziert verfügbar' in page.locator('main').inner_text()
    assert page.locator('.case-timeline').count()==0
    go('repositories')
    assert page.locator('main img').count()==0
    assert not errors, errors
    browser.close()
print('Viewer experience acceptance passed')
