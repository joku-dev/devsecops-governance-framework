"""Technical-view coverage and the script-free projection boundary."""
from html.parser import HTMLParser
import json
import re
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.viewer_technical import project_technical, link, SECTIONS
from generate_status_viewer import build_evidence_trust_section


class Cells(HTMLParser):
    def __init__(self):
        super().__init__(); self.values=[]; self.current=None
    def handle_starttag(self,tag,attrs):
        if tag in ('th','td'): self.current=[]
    def handle_endtag(self,tag):
        if tag in ('th','td') and self.current is not None:
            self.values.append(''.join(self.current));self.current=None
    def handle_data(self,data):
        if self.current is not None:self.current.append(data)


class TechnicalViewerTests(unittest.TestCase):
    def test_governance_trust_visible_without_typed_intake(self):
        dev = {'repositories': [{'repository_id': 'org/application', 'latest_result': {
            'pipeline_run_id': '42', 'commit_id': 'official',
            'trust': {'effective_level': 'integrity_verified', 'replay': 'fail'},
        }, 'history': [{'commit_id': 'newer-pr-commit'}]}]}
        source = build_evidence_trust_section({}, dev, {})
        self.assertIn('org/application', source)
        self.assertIn('Evidence: integrity_verified', source)
        self.assertIn('replay fail', source)
        self.assertIn('official', source)
        self.assertNotIn('newer-pr-commit', source)
        self.assertIn('Keine Typed Evidence erfasst.', source)
        self.assertIn('Kein Typed-Evidence-Eintrag für:', source)
        section = next(s for s in project_technical(source)['sections'] if s['id']=='evidence-trust')
        self.assertTrue(section['available'])

    def test_global_trust_missing_is_not_success_and_text_is_escaped(self):
        index = {'repositories': [{'repository_id': 'org/<script>', 'latest_result': {}}]}
        source = build_evidence_trust_section({}, index, {})
        self.assertIn('Evidence: not tracked', source)
        self.assertIn('not_evaluated', source)
        self.assertNotIn('integrity_verified', source)
        self.assertNotIn('<script>', source)
        self.assertIn('org/&lt;script&gt;', source)

    def test_typed_coverage_is_not_inferred_from_governance(self):
        typed = {'repositories': [{'repository_id': 'org/demo', 'latest_result': {
            'evidence_type': 'vulnerability_scan', 'trust': {'effective_level': 'integrity_verified'},
        }}]}
        dev = {'repositories': [{'repository_id': name, 'latest_result': {}} for name in ['org/demo', 'org/application']]}
        source = build_evidence_trust_section(typed, dev, {})
        coverage = source.split('Kein Typed-Evidence-Eintrag für:', 1)[1].split('</p>', 1)[0]
        self.assertIn('org/application', coverage)
        self.assertNotIn('org/demo', coverage)
        typed_table = source.split('<h2>Latest Typed Evidence</h2>', 1)[1]
        self.assertIn('org/demo', typed_table)
        self.assertNotIn('org/application', typed_table)

    def test_all_existing_sections_have_destinations(self):
        data=project_technical((ROOT/'generated/viewer/status-viewer.html').read_text())
        present={s['id'] for s in data['sections'] if s['available']}
        source=(ROOT/'generated/viewer/status-viewer.html').read_text()
        expected=set(re.findall(r'<section id="([^"]+)" class="viewer-section"',source))-{'measured-security'}
        self.assertEqual(expected,present)
        self.assertEqual(len(SECTIONS),len({(s['group'],s['tab']) for s in data['sections']}))
        self.assertTrue(data['graph']['nodes'])
        self.assertTrue(data['graph']['edges'])
        for section in data['sections']:
            if section['html']:
                self.assertNotIn('<script',section['html'])
                self.assertNotIn('style=',section['html'])

    def test_table_values_preserved_with_escaped_source_text(self):
        source='<section class="viewer-section" id="controls"><section><table><tr><th>ID</th><td>&lt;img src=x onerror=alert(1)&gt;</td><td>FAIL &amp; PASS</td></tr></table></section></section>'
        result=next(s for s in project_technical(source)['sections'] if s['id']=='controls')['html']
        before=Cells();before.feed(source);after=Cells();after.feed(result)
        self.assertEqual(before.values,after.values)
        self.assertNotIn('<img',result)

    def test_inline_code_and_event_handlers_are_not_projected(self):
        source='<section class="viewer-section" id="controls"><p onclick="bad()" style="color:red">safe</p><script>bad()</script></section>'
        result=next(s for s in project_technical(source)['sections'] if s['id']=='controls')['html']
        self.assertNotIn('bad()',result)
        self.assertNotIn('onclick',result)
        self.assertNotIn('style=',result)
        self.assertIn('safe',result)

    def test_graph_data_is_separate_from_html(self):
        source='<section class="viewer-section" id="governance-graph"><script id="governance-graph-data" type="application/json">{"nodes":[],"edges":[]}</script></section>'
        data=project_technical(source)
        self.assertEqual({'nodes':[],'edges':[]},data['graph'])
        self.assertNotIn('<script',next(s for s in data['sections'] if s['id']=='governance-graph')['html'])

    def test_relative_artifact_and_source_links_resolve_from_app(self):
        self.assertEqual('../../reports/replay-triage.md',link('../reports/replay-triage.md'))
        self.assertEqual('../../../operations/status/current-governance-platform-state',link('../../operations/status/current-governance-platform-state/'))
        self.assertEqual('https://github.com/joku-dev/devsecops-governance-framework/blob/main/status/intake-health.json',link('../../status/intake-health.json'))
        self.assertEqual('#evidence/history',link('#runs'))
        self.assertEqual('#evidence/replay',link('#replay-triage'))
        self.assertEqual('#findings',link('#measured-security'))
        self.assertEqual('https://github.com/org/repo',link('https://github.com/org/repo'))

    def test_unsafe_and_unmapped_content_fails_build(self):
        for value in ('javascript:alert(1)','data:text/html,attack','//evil.test/a','../../../../outside','https:\\evil.test','java\nscript:alert(1)','#unknown'):
            with self.subTest(value=value),self.assertRaises(ValueError):link(value)
        for html in ('<section class="viewer-section" id="unknown"></section>',
                     '<section class="viewer-section" id="controls"><iframe src="https://evil.test"></iframe></section>',
                     '<section class="viewer-section" id="controls">'):
            with self.subTest(html=html),self.assertRaises(ValueError):project_technical(html)

    def test_absent_optional_section_is_explicit(self):
        data=project_technical('')
        self.assertIsNone(data['graph'])
        self.assertTrue(all(not s['available'] and s['html'] is None for s in data['sections']))
