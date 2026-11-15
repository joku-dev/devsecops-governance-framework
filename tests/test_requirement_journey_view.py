"""Pilot regressions against exact revision bindings and deliberately broken inputs."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import subprocess
import tempfile
import unittest

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from lib.requirement_journey_view import project, REGISTER, CATALOG, ARTIFACTS, CASES, PRA, PILOTS

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'a' * 40


class RequirementJourneyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for path in (REGISTER, CATALOG, ARTIFACTS):
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
        shutil.copytree(ROOT / CASES, self.root / CASES)
        shutil.copytree(ROOT / 'docs/governance/source-documents', self.root / 'docs/governance/source-documents')
        for m in yaml.safe_load((ROOT / ARTIFACTS).read_text())['entries']:
            p = m['artifact']['path']
            (self.root / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / p, self.root / p)

    def load(self):
        return project(self.root, REVISION)

    def modify(self, path, fn):
        target = self.root / path
        value = yaml.safe_load(target.read_text())
        fn(value)
        target.write_text(json.dumps(value))

    def test_six_cases_exact_bindings_and_no_runtime_claims(self):
        data = self.load()
        self.assertEqual([c['id'] for c in data['cases']], [i for i, _ in PILOTS])
        for case in data['cases']:
            self.assertEqual(case['issues'], [])
            self.assertEqual(len(case['phases']), 5)
            self.assertEqual([p['evidence'] for p in case['phases'][3:]], ['Nicht verknüpft'] * 2)
        a, b, c, opened, rejected, duplicate = data['cases']
        self.assertIn('DSCB-L1-REQ-003', a['statement'])
        mapping = a['phases'][2]['branches'][0]
        self.assertEqual(mapping['label'], 'RTA-000001')
        self.assertEqual(mapping['fields']['Enforcement'], 'none')
        self.assertEqual(b['phases'][2]['branches'], [])
        branches = c['phases'][2]['branches']
        self.assertEqual([r['label'] for r in branches], ['RTA-000010', 'RTA-000011'])
        self.assertEqual(len({r['fields']['Artefakt'] for r in branches}), 1)
        self.assertEqual(len({r['fields']['Artefaktkennung'] for r in branches}), 2)
        self.assertIn('offen', opened['phases'][1]['decision'])
        self.assertIn('Abgelehnt', rejected['phases'][1]['decision'])
        self.assertEqual(duplicate['phases'][1]['branches'][0]['fields']['Duplikatziel'], 'GRQ-000019')
        for case in data['cases'][3:]:
            self.assertEqual(case['kind'], 'history')
            self.assertIsNone(case['statement'])
            self.assertEqual(case['phases'][2]['branches'], [])

    def test_allowlist_excludes_proposal_text_analysis_and_notes(self):
        path = f'{CASES}/{PRA}.json'
        def edit(c):
            for p in c['proposals']:
                p.update(statement='PRIVATE-STATEMENT', analysis={'notes':'PRIVATE-NOTE'})
                if p.get('decision'):
                    p['decision']['rationale'] = 'PRIVATE-RATIONALE'
        self.modify(path, edit)
        serialized = json.dumps(self.load())
        self.assertNotIn('PRIVATE-', serialized)

    def test_missing_revision_never_uses_newer_text_or_mapping(self):
        def edit(c):
            r = next(r for r in c['requirements'] if r['id'] == 'GRQ-000003')
            r['revisions'][0]['revision'] = 2
            r['active_revision'] = 2
            r['revisions'][0]['statement'] = 'NEWER-TEXT'
        self.modify(CATALOG, edit)
        case = self.load()['cases'][0]
        self.assertIsNone(case['statement'])
        self.assertNotIn('NEWER-TEXT', json.dumps(case))
        self.assertTrue(case['issues'])
        self.assertEqual(case['phases'][2]['branches'], [])

    def test_non_active_revision_hides_statement_and_keeps_exact_revision(self):
        def edit(c):
            r = c['requirements'][0]
            r['active_revision'] = 2
            newer = deepcopy(r['revisions'][0]); newer.update(revision=2, statement='NEW-TEXT')
            r['revisions'].append(newer)
        self.modify(CATALOG, edit)
        case = self.load()['cases'][1]
        self.assertIsNone(case['statement'])
        self.assertTrue(case['issues'])
        self.assertNotIn('NEW-TEXT', json.dumps(case))

    def test_stale_missing_hashes_and_source_path_mismatch(self):
        p = self.root / 'policies/opa/branch_protection.rego'
        p.write_text(p.read_text() + '\n# changed\n')
        c = self.load()['cases'][0]
        self.assertEqual(c['phases'][2]['branches'][0]['fields']['Hashprüfung'], 'Hash weicht ab')
        source = yaml.safe_load((self.root / REGISTER).read_text())['documents'][2]['source_path']
        (self.root / source).unlink()
        c = self.load()['cases'][0]
        self.assertEqual(c['phases'][0]['branches'][0]['fields']['Hashprüfung gegen Lifecycle-Quelle'], 'Datei fehlt')
        p.unlink()
        self.assertEqual(self.load()['cases'][0]['phases'][2]['branches'][0]['fields']['Hashprüfung'], 'Datei fehlt')
        self.modify(REGISTER, lambda r: r['documents'].append(deepcopy(r['documents'][2])))
        self.assertIn('mehrdeutig', json.dumps(self.load()['cases'][0], ensure_ascii=False))

    def test_ambiguous_sources_and_rta_are_visible(self):
        self.modify(ARTIFACTS, lambda r: r['entries'].append(deepcopy(r['entries'][0])))
        self.assertTrue(self.load()['cases'][0]['issues'])
        case_path = f'{CASES}/RLC-DSCB-STD-REQ-001-MIGRATION.json'
        self.modify(case_path, lambda c: c['proposals'].append(deepcopy(c['proposals'][11])))
        c = self.load()['cases'][0]
        self.assertIn('mehrdeutig', json.dumps(c, ensure_ascii=False))
        self.assertEqual(c['phases'][0]['branches'], [])

    def test_exact_activation_and_source_refs_not_text_similarity(self):
        path = f'{CASES}/RLC-DSCB-STD-REQ-001-MIGRATION.json'
        self.modify(path, lambda c: c['proposals'][11]['activation'].update(revision=2))
        self.assertTrue(self.load()['cases'][0]['issues'])
        self.modify(ARTIFACTS, lambda r: r['entries'][0].update(requirement_ref='GRQ-000003@rev2'))
        self.assertEqual(self.load()['cases'][0]['phases'][2]['branches'], [])
        self.modify(CATALOG, lambda c: c['requirements'][2]['revisions'][0].update(source_refs=['SIMILAR-012']))
        self.assertTrue(self.load()['cases'][0]['issues'])

    def test_changed_source_and_mismatched_register_path_remain_visible(self):
        case_path = f'{CASES}/RLC-DSCB-STD-REQ-001-MIGRATION.json'
        source_path = json.loads((self.root / case_path).read_text())['source']['source_path']
        path = self.root / source_path
        path.write_text(path.read_text() + '\nchanged source bytes\n')
        case = self.load()['cases'][0]
        self.assertEqual(case['phases'][0]['branches'][0]['fields']['Hashprüfung gegen Lifecycle-Quelle'], 'Hash weicht ab')
        self.modify(REGISTER, lambda r: r['documents'][2].update(source_path='different.md'))
        self.assertIn('Registerbindung fehlt', json.dumps(self.load()['cases'][0], ensure_ascii=False))

    def test_missing_proposal_duplicate_catalog_and_wrong_mapping_refs(self):
        path = f'{CASES}/{PRA}.json'
        self.modify(path, lambda c: c.update(proposals=[p for p in c['proposals'] if p['proposal_id'] != PRA + '-P0001']))
        self.assertTrue(self.load()['cases'][3]['issues'])
        self.modify(CATALOG, lambda c: c['requirements'].append(deepcopy(c['requirements'][2])))
        self.assertIsNone(self.load()['cases'][0]['statement'])
        self.modify(ARTIFACTS, lambda r: r['entries'][0].update(source_requirement_refs=['UNRELATED-012']))
        self.assertEqual(self.load()['cases'][0]['phases'][2]['branches'], [])
        (self.root / CATALOG).write_text((ROOT / CATALOG).read_text())
        case = self.load()['cases'][0]
        self.assertEqual(case['phases'][2]['branches'][0]['fields']['Exakte Zuordnungsbindung'], 'Nicht belegt')

    def test_empty_inputs_and_unpinned_revision_stay_visible(self):
        shutil.rmtree(self.root / 'model')
        data = project(self.root)
        self.assertEqual(len(data['cases']), 6)
        for c in data['cases']:
            self.assertTrue(c['issues'])
            self.assertIsNone(c['statement'])
            self.assertEqual(c['phases'][0]['branches'], [])
        self.assertIsNone(data['repository_revision'])

    def test_build_revision_refuses_dirty_and_untracked_authority_inputs(self):
        from lib.viewer_app import requirement_journey_revision
        self.assertIsNone(requirement_journey_revision(self.root))
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.DEVNULL, text=True).strip()
        git('init', '-q')
        git('add', '.')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture')
        revision = git('rev-parse', 'HEAD')
        self.assertEqual(requirement_journey_revision(self.root), revision)
        path = self.root / 'model/untracked.yaml'
        path.write_text('untracked: true')
        self.assertIsNone(requirement_journey_revision(self.root))
        path.unlink()
        path = self.root / CATALOG
        path.write_text(path.read_text() + '\n# changed\n')
        self.assertIsNone(requirement_journey_revision(self.root))

    def test_all_evidence_links_are_pinned_and_traversal_is_rejected(self):
        self.modify(ARTIFACTS, lambda r: r['entries'][0]['artifact'].update(path='../../private.txt'))
        data = self.load()
        self.assertTrue(data['cases'][0]['issues'])
        def walk(v):
            if isinstance(v, dict):
                if 'url' in v:
                    self.assertIn('/blob/' + REVISION + '/', v['url'])
                    self.assertNotIn('..', v['url'])
                for x in v.values(): walk(x)
            elif isinstance(v, list):
                for x in v: walk(x)
        walk(data)


if __name__ == '__main__':
    unittest.main()
