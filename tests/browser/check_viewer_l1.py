"""Optional Playwright acceptance for measured L1 controls and their data boundary."""
import copy
import sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8775/generated/viewer/app/index.html'
REPO = '#repository/joku-dev%2Fha-CPsWMS/'
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':1440,'height':1050})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    data=page.request.get(URL.rsplit('/',1)[0]+'/data.json').json()
    def go(tab):
        page.goto(URL+REPO+tab);page.wait_for_selector('h1')
    go('summary')
    page.get_by_role('link',name='Alle 16 Kontrollen').click()
    page.wait_for_selector('.l1-control')
    assert page.locator('.l1-control').count()==16
    assert page.locator('.l1-metrics .value').all_text_contents()==['5','6','2','3']
    assert 'denselben Commit' in page.locator('main').inner_text()
    assert '16 Kontrollen bestanden' in page.locator('main').inner_text()
    ha=next(r for r in data['repositories'] if r['id']=='joku-dev/ha-CPsWMS')
    if ha.get('control_assurance'):
        assert page.locator('.assurance-overview').count()==1
        assert page.locator('.assurance-integrity_verified,.assurance-unverified').count()==16
        first=page.locator('.l1-control').first
        first.locator('.l1-control-heading').click()
        assert first.locator('.assurance-grid').count()==1
        assert 'Freshness' in first.inner_text() and 'Subjektbindung' in first.inner_text()
    page.locator('#l1-status').select_option('gap');assert page.locator('.l1-control').count()==3
    page.locator('#l1-query').fill('013');assert page.locator('.l1-control').count()==1
    assert 'Deployment autorisieren' in page.locator('.l1-control').inner_text()
    page.locator('.l1-control-heading').click()
    page.get_by_text('Nachweise und Prüfsummen (1)',exact=True).click()
    assert page.locator('.l1-sources a').count()==1
    assert '/artifacts/' in page.locator('.l1-sources a').get_attribute('href')
    assert len(page.locator('.l1-sources code').inner_text())==64
    page.locator('#l1-status').select_option('all');page.locator('#l1-query').fill('Trivy')
    assert page.locator('.l1-control').count()==4
    page.locator('#l1-query').fill('not-a-real-control');assert page.locator('.l1-control').count()==0
    assert 'Keine passenden Kontrollen' in page.locator('main').inner_text()
    page.locator('#l1-query').fill('');page.screenshot(path='/tmp/viewer-l1-desktop.png',full_page=True)
    for width in (390,720,1024):
        page.set_viewport_size({'width':width,'height':844});go('l1');page.wait_for_selector('.l1-control')
        first=page.locator('.l1-control').first
        if first.get_attribute('open') is None:first.locator('.l1-control-heading').click()
        if first.locator('details').get_attribute('open') is None:first.locator('details summary').click()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
        if width==390:page.screenshot(path='/tmp/viewer-l1-mobile.png',full_page=True)
    # Matching commit is not assumed for evidence from another software revision.
    mismatch=copy.deepcopy(data);ha=next(r for r in mismatch['repositories'] if r['id']=='joku-dev/ha-CPsWMS')
    ha['l1_assessment']['run']['commit']='0'*40
    alternate=browser.new_page();alternate.route('**/data.json',lambda r:r.fulfill(json=mismatch))
    alternate.goto(URL+REPO+'l1');alternate.wait_for_selector('.l1-control')
    assert 'keinen bestätigten gemeinsamen Commit' in alternate.locator('main').inner_text()
    # No evidence is not a clean assessment.
    missing=copy.deepcopy(data);next(r for r in missing['repositories'] if r['id']=='joku-dev/ha-CPsWMS')['l1_assessment']=None
    empty=browser.new_page();empty.route('**/data.json',lambda r:r.fulfill(json=missing))
    empty.goto(URL+REPO+'l1');empty.wait_for_selector('h1')
    assert 'Keine gemessene L1-Bewertung erfasst' in empty.locator('main').inner_text()
    assert empty.locator('.l1-control').count()==0
    hostile=copy.deepcopy(data);ha=next(r for r in hostile['repositories'] if r['id']=='joku-dev/ha-CPsWMS')
    ha['l1_assessment']['controls'][0]['observation']='<img src=x onerror="window.injected=true">'
    safe=browser.new_page();safe.route('**/data.json',lambda r:r.fulfill(json=hostile))
    safe.goto(URL+REPO+'l1');safe.wait_for_selector('.l1-control')
    safe.locator('.l1-control-heading').first.click()
    assert '<img' in safe.locator('.l1-control').first.inner_text()
    assert safe.locator('main img').count()==0 and safe.evaluate('window.injected') is None
    go('summary');assert 'FAIL' in page.locator('main').inner_text() # historical replay is not cleared
    assert not errors,errors
    browser.close()
print('L1 browser acceptance passed: all controls, statuses, filters, evidence hashes, same-commit boundary, mobile, missing data and escaping.')
