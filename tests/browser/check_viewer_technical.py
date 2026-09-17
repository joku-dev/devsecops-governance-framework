"""Browser acceptance for integrated technical views. Same setup as check_viewer_app.py."""
import sys
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright, expect

URL=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8771/generated/viewer/app/index.html'
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':1440,'height':1050})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda e:errors.append(e.text) if e.type=='error' else None)
    def go(route):
        page.goto(URL+'#'+route)
        page.wait_for_selector('h1')
        page.wait_for_timeout(100)
    data=page.request.get(urljoin(URL,'data.json')).json()
    for section in data['technical']['sections']:
        go(section['group']+'/'+section['tab'])
        expect(page.locator('h1')).to_have_text(section['title'])
        if section['available']:
            assert page.locator('.technical .viewer-section').count()==1
        else:
            assert 'Keine Daten erfasst' in page.locator('.technical').inner_text()
        assert page.locator('iframe').count()==0
        assert page.locator('.sidebar [aria-current=page]').count()==1
    go('repository/joku-dev%2Fha-CPsWMS/summary')
    assert page.locator('nav[aria-label="Repository-Ansichten"] a').count()==6
    for invalid in ('governance/summary','operations/summary','evidence/nonexistent'):
        go(invalid)
        assert page.locator('h1').inner_text()=='Ansicht nicht gefunden'
    go('evidence/trust')
    governance=page.locator('.panel').filter(has=page.get_by_role('heading',name='Latest Governance Evidence Trust',exact=True))
    ha=governance.locator('tbody tr').filter(has_text='joku-dev/ha-CPsWMS')
    assert ha.count()==2
    assert all('integrity_verified' in text for text in ha.all_text_contents())
    assert 'replay fail' in ha.filter(has_text='DevSecOps').inner_text()
    assert 'replay pass' in ha.filter(has_text='Architecture').inner_text()
    typed=page.locator('.panel').filter(has=page.get_by_role('heading',name='Latest Typed Evidence',exact=True))
    assert typed.locator('tbody tr').count()==2
    assert 'governance-framework-demo-consumer' in typed.inner_text()
    ha_typed=typed.locator('tbody tr').filter(has_text='joku-dev/ha-CPsWMS')
    assert ha_typed.count()==1
    ha_typed_text=ha_typed.inner_text()
    assert 'integrity_verified' in ha_typed_text
    assert '1993' in ha_typed_text and 'critical' in ha_typed_text
    assert ha_typed_text.count('archive verified')==5
    for image in ('ha-sync','query-api','semantic-enrichment','world-model-chat','neo4j'):
        assert image in ha_typed_text
    coverage=page.locator('.panel').filter(has=page.get_by_role('heading',name='Typed Evidence: Abdeckung',exact=True))
    coverage_text=coverage.inner_text()
    assert 'Kein Typed-Evidence-Eintrag für:' in coverage_text
    assert 'ai-native-engineering-factory' in coverage_text and 'ha-CPsWMS' not in coverage_text
    page.screenshot(path='/tmp/viewer-global-trust.png',full_page=True)
    go('evidence/replay')
    assert 'cross_commit_reuse' in page.locator('.technical').inner_text()
    assert 'FAIL' in page.locator('.notice').inner_text()
    page.screenshot(path='/tmp/integrated-replay-desktop.png',full_page=True)
    go('replay-triage') # compatibility alias within the app
    assert page.locator('h1').inner_text()=='Replay-Prüfung'
    go('governance/controls')
    page.locator('#control-status-filter').select_option('fail')
    assert all(s=='fail' for s in page.locator('[data-control-row]:visible').evaluate_all('(rows)=>rows.map(r=>r.dataset.status)'))
    page.locator('#control-search-filter').fill('not-a-control')
    assert page.locator('[data-control-row]:visible').count()==0
    page.locator('#control-search-filter').fill('')
    page.locator('#control-status-filter').select_option('all')
    assert page.locator('[data-control-row]:visible').count()==10
    panel=page.locator('.panel').filter(has=page.locator('#control-status-filter'))
    panel.get_by_role('button',name='Weiter').click()
    assert 'Seite 2' in panel.locator('.pager').inner_text()
    go('evidence/history')
    page.locator('#history-scope-filter').select_option('manual')
    assert page.locator('[data-history-row]:visible').count()>0
    assert all(s=='manual' for s in page.locator('[data-history-row]:visible').evaluate_all('(rows)=>rows.map(r=>r.dataset.scope)'))
    page.locator('#history-search-filter').fill('no-such-run')
    assert page.locator('[data-history-row]:visible').count()==0
    go('governance/graph')
    assert page.locator('.graph-node').count()>0
    page.locator('#graph-type-filter').select_option('Repository')
    page.locator('#graph-search-filter').fill('ha-CPsWMS')
    assert page.locator('.graph-node').count()>0
    assert all(label.startswith('Repository:') for label in page.locator('.graph-node').evaluate_all('(nodes)=>nodes.map(n=>n.getAttribute("aria-label"))'))
    page.locator('.graph-node').first.focus();page.keyboard.press('Enter')
    assert 'ha-CPsWMS' in page.locator('#graph-selection-details').inner_text()
    page.locator('#graph-reset').click()
    assert 'Keine Auswahl' in page.locator('#graph-selection-details').inner_text()
    page.screenshot(path='/tmp/integrated-graph-desktop.png',full_page=True)
    go('evidence/artifacts')
    links=page.locator('.technical a').evaluate_all('(a)=>a.map(e=>e.href)')
    assert any('/blob/main/status/' in link for link in links)
    assert any('/generated/reports/' in link for link in links)
    assert not any('/app/reports/' in link for link in links)
    # Source links and report paths are resolved without returning to the old viewer.
    for href in links:
        if '/generated/' in href and href.startswith(URL.split('/generated/')[0]) and not href.endswith('.jsonl'):
            assert page.request.get(href).ok,href
    for width in (390,720,1024):
        page.set_viewport_size({'width':width,'height':844})
        for section in data['technical']['sections']:
            go(section['group']+'/'+section['tab'])
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(width,section['id'])
        if width==390:
            go('evidence/replay');page.locator('#section-picker').select_option('#evidence/history')
            page.wait_for_selector('#history-scope-filter')
            page.go_back();page.wait_for_selector('#replay-triage')
            page.screenshot(path='/tmp/integrated-replay-mobile.png',full_page=True)
    assert not errors,errors
    # Defense in depth: even a malicious JSON fragment cannot add executable DOM.
    hostile={'version':1,'repositories':[],'technical':{'graph':None,'sections':[{'id':'controls','group':'governance','tab':'controls','title':'Test','available':True,'html':'<section class="viewer-section"><p onclick="window.injected=true">safe</p><img src=x onerror="window.injected=true"><script>window.injected=true</script><a href="javascript:window.injected=true">unsafe</a></section>'}]}}
    safe=browser.new_page();safe.route('**/data.json',lambda route:route.fulfill(json=hostile))
    safe.goto(URL+'#governance/controls');safe.wait_for_selector('.technical p')
    assert safe.locator('.technical script,.technical img,.technical [onclick],.technical a[href]').count()==0
    assert safe.evaluate('window.injected') is None
    # Domain filters must work even when fewer than eight result rows exist.
    tiny={'version':1,'repositories':[],'technical':{'graph':None,'sections':[{'id':'controls','group':'governance','tab':'controls','title':'Test','available':True,'html':'<section class="viewer-section"><select id="control-status-filter"><option value="all">All</option><option value="fail">Fail</option></select><input id="control-search-filter"><p id="control-filter-summary"></p><table><tbody><tr data-control-row="true" data-status="pass"><td>PASS row</td></tr><tr data-control-row="true" data-status="fail"><td>FAIL row</td></tr></tbody></table></section>'}]}}
    small=browser.new_page();small.route('**/data.json',lambda route:route.fulfill(json=tiny))
    small.goto(URL+'#governance/controls');small.wait_for_selector('[data-control-row]')
    small.locator('#control-status-filter').select_option('fail')
    assert small.locator('[data-control-row]:visible').count()==1
    assert small.locator('[data-control-row]:visible').inner_text()=='FAIL row'
    browser.close()
print('Technical acceptance passed: complete section coverage, native views, filters, pagination, graph, links, mobile, aliases, and escaping.')
