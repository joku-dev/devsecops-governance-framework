from __future__ import annotations

import base64
import http.client
import io
import json
from pathlib import Path
import shutil
import subprocess
import socket
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch
import zipfile

import yaml
import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import serve_governance_workbench as wb
import generate_source_document_requirement_delta as delta


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / 'docs/governance/source-documents').mkdir(parents=True)
        (self.root / 'model/documents').mkdir(parents=True)
        (self.root / 'schemas').mkdir()
        for name in ('source-document-register.schema.json', 'governance-workbench-draft.schema.json'):
            shutil.copy(ROOT / 'schemas' / name, self.root / 'schemas' / name)
        self.path = self.root / 'docs/governance/source-documents/TEST-SRC-001.md'
        self.path.write_text('# Test\n[DSCB-L1-REQ-001] The system shall retain evidence for twelve months.\n')
        self.reg = self.root / wb.REGISTER
        self.reg.write_text(yaml.safe_dump({'schema_version':'1.0.0','documents':[{'id':'TEST-SRC-001','title':'Test source','status':'approved','source_path':str(self.path.relative_to(self.root)),'owner':'test-owner','version':'1','intake_date':'2026-10-11','governance_domains':['devsecops'],'derived_artifact_areas':[]}]}))
        for args in (['git','init','-q'],['git','add','.'],['git','-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture']):
            subprocess.run(args,cwd=self.root,check=True,capture_output=True)
        self.patcher = patch.object(delta, 'ROOT', self.root)
        self.patcher.start()
        self.app = wb.Workbench(self.root)

    def tearDown(self):
        self.patcher.stop()
        self.tmp.cleanup()

    def upload(self, **changes):
        payload={'filename':'proposal.md','content_base64':base64.b64encode(b'# Candidate\n[DSCB-L1-REQ-001] The system shall retain evidence for eighteen months.\n').decode(),
                 'metadata':{'id':'TEST-CAND-002','title':'Replacement','owner':'test-owner','version':'2','governance_domains':['devsecops'],'replacement_for':'TEST-SRC-001'}}
        payload.update(changes)
        return self.app.create_draft(payload)

    def test_upload_and_packet_preserve_bytes_and_candidate_boundary(self):
        before = self.reg.read_bytes()
        draft = self.upload()
        self.assertEqual(self.reg.read_bytes(), before)
        self.assertFalse((self.root/draft['source']['source_path']).exists())
        self.assertEqual(draft['source']['status'],'candidate')
        self.assertEqual(draft['source']['derived_artifact_areas'],[])
        self.assertEqual(len(draft['deltas']), 1)
        self.assertEqual(draft['deltas'][0]['matched_identifier'], 'DSCB-L1-REQ-001')
        self.assertEqual(draft['requirements'][0]['source_requirement_id'], 'DSCB-L1-REQ-001')
        self.assertEqual(draft['requirements'][0]['identification_class'], 'explicit_identifier')
        with zipfile.ZipFile(io.BytesIO(self.app.packet(draft['draft_id']))) as archive:
            jsonschema.validate(json.loads(archive.read('workbench-package.json')), wb.read_json(self.root / 'schemas/governance-workbench-draft.schema.json'))
            reg=yaml.safe_load(archive.read(wb.REGISTER))
            self.assertEqual(reg['documents'][-1]['status'],'candidate')
            self.assertIsNone(reg['documents'][-1]['supersedes'])
            self.assertEqual(wb.digest(archive.read(draft['source']['source_path'])),draft['sha256'])
        self.assertEqual(self.reg.read_bytes(),before)


    def test_draft_diagnostics_are_response_only_and_saved_history_is_unchanged(self):
        draft = self.app.source_review({'source_id': 'TEST-SRC-001'})
        stored = self.app.draft_dir(draft['draft_id']) / 'draft.json'
        before = stored.read_bytes()
        self.assertFalse(draft['stale'])
        self.assertEqual(draft['stale_details']['reasons'], [])
        self.assertEqual(draft['formal_status']['authority'], 'recorded_history_only')
        self.path.write_text(self.path.read_text() + '\nA changed source.\n')
        current = self.app.draft(draft['draft_id'])
        self.assertTrue(current['stale'])
        self.assertIn('source_changed', {r['code'] for r in current['stale_details']['reasons']})
        self.assertEqual(stored.read_bytes(), before)
        with self.assertRaises(ValueError):
            self.app.note(draft['draft_id'], {'subject':'source', 'reviewer':'Test', 'outcome':'needs_clarification', 'rationale':'Blocked'})
        with self.assertRaises(ValueError):
            self.app.packet(draft['draft_id'])

    def test_missing_registered_source_keeps_draft_and_state_readable_but_locked(self):
        draft = self.app.source_review({'source_id': 'TEST-SRC-001'})
        self.path.unlink()
        current = self.app.draft(draft['draft_id'])
        self.assertTrue(current['stale'])
        reason = next(r for r in current['stale_details']['reasons'] if r['code'] == 'source_missing')
        self.assertEqual(reason['source_id'], 'TEST-SRC-001')
        self.assertIsNone(reason['current'])
        self.assertEqual(self.app.state()['drafts'][0]['draft_id'], draft['draft_id'])
        self.assertEqual(self.app.requirement_history('TEST-SRC-001')['cases'], [])
        with self.assertRaises(ValueError):
            self.app.packet(draft['draft_id'])

    def test_removed_registration_does_not_hide_existing_preparation(self):
        draft = self.app.source_review({'source_id': 'TEST-SRC-001'})
        register = yaml.safe_load(self.reg.read_text()); register['documents'] = []
        self.reg.write_text(yaml.safe_dump(register))
        current = self.app.draft(draft['draft_id'])
        self.assertTrue(current['stale'])
        self.assertIn('source_metadata_changed', {r['code'] for r in current['stale_details']['reasons']})
        self.assertEqual(current['source']['id'], 'TEST-SRC-001')

    def test_commit_and_register_changes_explain_independent_stale_causes(self):
        draft = self.app.source_review({'source_id': 'TEST-SRC-001'})
        with patch.object(self.app, 'head', return_value='f' * 40):
            current = self.app.draft(draft['draft_id'])
            self.assertTrue(current['stale'])
            self.assertEqual([r['code'] for r in current['stale_details']['reasons']], ['repository_changed'])
        register = yaml.safe_load(self.reg.read_text()); register['documents'][0]['owner'] = 'Another owner'
        self.reg.write_text(yaml.safe_dump(register))
        codes = {r['code'] for r in self.app.draft(draft['draft_id'])['stale_details']['reasons']}
        self.assertTrue({'register_changed', 'source_metadata_changed'}.issubset(codes))

    def test_formal_status_uses_exact_source_hash_and_never_local_notes(self):
        directory = self.root / 'model/requirements/lifecycle-cases'; directory.mkdir(parents=True)
        binding = {'source_id':'TEST-SRC-001', 'source_path':str(self.path.relative_to(self.root)), 'source_sha256':wb.digest(self.path.read_bytes())}
        (directory / 'matching.json').write_text(json.dumps({'source':binding, 'proposals':[{'decision':{'disposition':'approve'}, 'activation':{'requirement_id':'GRQ-1'}}, {'decision':None}]}))
        (directory / 'other.json').write_text(json.dumps({'source':{**binding, 'source_sha256':'a' * 64}, 'proposals':[{'decision':{'disposition':'approve'}}]}))
        draft = self.app.source_review({'source_id':'TEST-SRC-001'})
        formal = draft['formal_status']
        self.assertEqual(formal['recorded_proposals'], 2)
        self.assertEqual(formal['recorded_decisions'], 1)
        self.assertEqual(formal['recorded_activations'], 1)
        self.assertEqual(formal['open_historical_proposals'], 1)
        self.assertEqual(formal['other_source_cases'], 1)
        updated = self.app.note(draft['draft_id'], {'subject':'source', 'reviewer':'Test', 'outcome':'confirm_candidate', 'rationale':'Proposal only'})
        self.assertEqual(updated['formal_status'], formal)
        self.assertEqual(self.app.inspect(self.app.document('TEST-SRC-001'))['formal_status'], formal)
        saved = json.loads((self.app.draft_dir(draft['draft_id']) / 'draft.json').read_text())
        self.assertNotIn('formal_status', saved); self.assertNotIn('stale_details', saved)
        with zipfile.ZipFile(io.BytesIO(self.app.packet(draft['draft_id']))) as archive:
            packet = json.loads(archive.read('workbench-package.json'))
            self.assertNotIn('formal_status', packet); self.assertNotIn('stale_details', packet)
            jsonschema.validate(packet, wb.read_json(self.root / 'schemas/governance-workbench-draft.schema.json'))

    def test_new_source_review_preserves_old_notes_without_inheriting_them(self):
        old = self.app.source_review({'source_id':'TEST-SRC-001'})
        old = self.app.note(old['draft_id'], {'subject':'source', 'reviewer':'Test', 'outcome':'needs_clarification', 'rationale':'An earlier question'})
        old_file = self.app.draft_dir(old['draft_id']) / 'draft.json'; before = old_file.read_bytes()
        fresh = self.app.source_review({'source_id':'TEST-SRC-001'})
        self.assertNotEqual(old['draft_id'], fresh['draft_id'])
        self.assertEqual(fresh['notes'], [])
        self.assertEqual(old_file.read_bytes(), before)

    def test_changed_or_missing_uploaded_original_is_diagnosed_and_locked(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                draft = self.upload()
                original = self.app.draft_dir(draft['draft_id']) / draft['upload_name']
                if missing:
                    original.unlink()
                else:
                    original.write_bytes(b'Changed original')
                result = self.app.draft(draft['draft_id'])
                self.assertTrue(result['stale'])
                self.assertIn('uploaded_source_missing' if missing else 'uploaded_source_changed',
                              {r['code'] for r in result['stale_details']['reasons']})
                with self.assertRaises(ValueError):
                    self.app.packet(draft['draft_id'])

    def test_unlabelled_upload_produces_no_requirement_candidates(self):
        draft = self.upload(content_base64=base64.b64encode(
            b"# Requirements\nThe system SHALL retain evidence.\nSee DSCB-L1-REQ-001 for details.\n"
        ).decode())
        self.assertEqual(draft['requirements'], [])
        self.assertTrue(draft['lines'])

    def test_registered_source_review_notes_reopen_and_packet_preserve_authority(self):
        original, register = self.path.read_bytes(), self.reg.read_bytes()
        draft = self.app.source_review({'source_id': 'TEST-SRC-001'})
        self.assertEqual(draft['kind'], 'source_review')
        self.assertEqual(draft['source']['status'], 'approved')
        subject = draft['requirements'][0]['id']
        note = {'subject': subject, 'reviewer': 'Review test', 'outcome': 'needs_clarification',
                'rationale': 'Check the recorded identifier origin.'}
        self.app.note(draft['draft_id'], note)
        result = self.app.note(draft['draft_id'], {**note, 'outcome': 'confirm_candidate',
                                                'rationale': 'Proposal only; owner decision remains separate.'})
        self.assertEqual(len(result['notes']), 2)
        self.assertEqual(self.app.draft(draft['draft_id'])['notes'], result['notes'])
        with zipfile.ZipFile(io.BytesIO(self.app.packet(draft['draft_id']))) as archive:
            self.assertEqual(archive.read(draft['source']['source_path']), original)
            self.assertNotIn(wb.REGISTER, archive.namelist())
            packet = json.loads(archive.read('workbench-package.json'))
            jsonschema.validate(packet, wb.read_json(self.root / 'schemas/governance-workbench-draft.schema.json'))
            self.assertEqual(packet['source']['status'], 'approved')
            self.assertTrue(all(n['authority'] == 'proposal_only' for n in packet['notes']))
            change = archive.read(f'docs/governance/change-requests/GCR-WB-{draft["draft_id"]}.md').decode()
            self.assertIn('Explicit requirements: 1; with item notes: 1.', change)
            self.assertIn('Clarification required: none.', change)
        self.assertEqual(self.reg.read_bytes(), register)
        self.assertEqual(self.path.read_bytes(), original)

    def test_registered_review_blocks_stale_sources_and_published_notes(self):
        tampered = self.app.source_review({'source_id': 'TEST-SRC-001'})
        tampered['source']['status'] = 'candidate'
        self.app.save(self.app.draft_dir(tampered['draft_id']), tampered)
        self.assertTrue(self.app.draft(tampered['draft_id'])['stale'])
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.app.packet(tampered['draft_id'])
        draft = self.app.source_review({'source_id': 'TEST-SRC-001'})
        draft['pr'] = {'url': 'https://github.com/owner/repo/pull/1'}
        self.app.save(self.app.draft_dir(draft['draft_id']), draft)
        with self.assertRaisesRegex(ValueError, 'already been submitted'):
            self.app.note(draft['draft_id'], {})
        self.path.write_text('Changed registered source')
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.app.packet(draft['draft_id'])
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.app.note(draft['draft_id'], {})

    def test_history_is_read_only_and_retains_unlabelled_proposals_and_decisions(self):
        directory = self.root / 'model/requirements/lifecycle-cases'
        directory.mkdir(parents=True)
        case = {'case_id': 'RLC-TEST', 'status': 'partially_activated',
                'source': {'source_id': 'TEST-SRC-001', 'source_path': str(self.path.relative_to(self.root)),
                           'source_sha256': wb.digest(self.path.read_bytes())},
                'proposals': [{'proposal_id': 'OLD-1', 'source_requirement_id': 'TEST-SRC-001-REQ-001',
                               'statement': 'A historical version table row.', 'decision': {'disposition': 'reject'},
                               'activation': None}]}
        path = directory / 'RLC-TEST.json'
        path.write_text(json.dumps(case))
        before = path.read_bytes()
        history = self.app.requirement_history('TEST-SRC-001')
        self.assertTrue(history['cases'][0]['source_matches'])
        self.assertEqual(history['cases'][0]['proposals'], case['proposals'])
        self.assertEqual(path.read_bytes(), before)
        self.path.write_text('Changed source version')
        self.assertFalse(self.app.requirement_history('TEST-SRC-001')['cases'][0]['source_matches'])
        with self.assertRaisesRegex(ValueError, 'Unknown registered source'):
            self.app.requirement_history('OTHER-SRC-001')

    def test_older_draft_rows_remain_read_only_and_do_not_count_as_current(self):
        draft = self.upload()
        draft['requirements'].append({'id': 'old-row', 'source_requirement_id': 'TEST-SRC-001-REQ-002',
                                      'identification_class': 'inferred_candidate', 'statement': 'Historical narrative.'})
        old_note = {'subject': 'old-row', 'reviewer': 'Previous reviewer', 'outcome': 'confirm_candidate',
                    'rationale': 'Retained earlier proposal.', 'recorded_at': '2026-10-01', 'authority': 'proposal_only'}
        draft['notes'].append(old_note)
        self.app.save(self.app.draft_dir(draft['draft_id']), draft)
        with self.assertRaisesRegex(ValueError, 'historical entries are read-only'):
            self.app.note(draft['draft_id'], {**old_note, 'rationale': 'Do not treat this as current.'})
        summary = wb.preparation_summary(self.app.draft(draft['draft_id']))
        self.assertIn('Explicit requirements: 1; with item notes: 0.', summary)
        self.assertEqual(self.app.draft(draft['draft_id'])['notes'], [old_note])

    def test_review_rejects_source_changes_during_preparation_and_candidate_schema_stays_strict(self):
        inspect = self.app.inspect
        def changed(source):
            result = inspect(source)
            self.path.write_text('Concurrent source change')
            return result
        with patch.object(self.app, 'inspect', side_effect=changed), self.assertRaisesRegex(ValueError, 'Source changed'):
            self.app.source_review({'source_id': 'TEST-SRC-001'})
        self.assertEqual(list(self.app.state_dir.iterdir()), [])
        draft = self.upload()
        draft['source']['status'] = 'approved'
        with self.assertRaises(jsonschema.ValidationError):
            self.app.save(self.app.draft_dir(draft['draft_id']), draft)

    def test_changed_source_blocks_note_and_export(self):
        draft=self.upload()
        self.path.write_text('Changed source bytes')
        self.assertTrue(self.app.draft(draft['draft_id'])['stale'])
        with self.assertRaisesRegex(ValueError,'stale'):
            self.app.packet(draft['draft_id'])
        with self.assertRaisesRegex(ValueError,'changed'):
            self.app.note(draft['draft_id'],{})

    def test_tampered_upload_blocks_export(self):
        draft=self.upload()
        (self.app.draft_dir(draft['draft_id'])/draft['upload_name']).write_text('tampered')
        with self.assertRaisesRegex(ValueError,'upload bytes changed'):
            self.app.packet(draft['draft_id'])

    def test_notes_are_append_only_unconfirmed_and_scoped(self):
        draft=self.upload()
        note={'subject':'source','reviewer':'Owner','outcome':'needs_clarification','rationale':'Confirm authority first.'}
        result=self.app.note(draft['draft_id'],note)
        self.assertEqual(result['notes'][0]['authority'],'proposal_only')
        self.assertEqual(result['source']['status'],'candidate')
        with self.assertRaises(ValueError):
            self.app.note(draft['draft_id'],{**note,'subject':'unrelated-requirement'})
        with self.assertRaises(ValueError):
            self.app.note(draft['draft_id'],{**note,'outcome':'approved'})

    def test_path_traversal_duplicate_id_and_oversized_upload_fail(self):
        for name in ('../evil.md','sub/file.md','sub\\file.md','file.exe'):
            with self.subTest(name=name),self.assertRaises(ValueError):
                self.upload(filename=name)
        with self.assertRaises(ValueError):
            self.app.draft('../../etc/passwd')
        with self.assertRaises(ValueError):
            self.upload(content_base64=base64.b64encode(b'x'*(wb.MAX_UPLOAD+1)).decode())
        payload={'id':'TEST-SRC-001','title':'Overwrite','owner':'test','version':'2','governance_domains':['devsecops']}
        with self.assertRaises(ValueError):
            self.upload(metadata=payload)

    def test_docx_comments_warning_and_bomb_limit(self):
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>The system shall retain evidence safely.</w:t></w:r></w:p></w:body></w:document>')
            archive.writestr('word/comments.xml','<comments/>')
        result=self.upload(filename='source.docx',content_base64=base64.b64encode(buf.getvalue()).decode())
        self.assertIn('docx_comments_present_not_included',result['warnings'])
        bomb=io.BytesIO()
        with zipfile.ZipFile(bomb,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('word/document.xml',b'x'*(21*1024*1024))
        with self.assertRaisesRegex(ValueError,'decompressed'):
            self.upload(filename='bomb.docx',content_base64=base64.b64encode(bomb.getvalue()).decode())

    def test_review_scope_is_preparation_not_execution(self):
        draft=self.app.review_package({'source_ids':['TEST-SRC-001']})
        self.assertEqual(draft['execution'],'not_run')
        self.assertEqual(draft['manifest'][0]['sha256'],wb.digest(self.path.read_bytes()))
        with self.assertRaises(ValueError):
            self.app.review_package({'source_ids':['TEST-SRC-001','TEST-SRC-001']})
        with self.assertRaisesRegex(ValueError,'disabled'):
            self.app.submit_pr(draft['draft_id'],{'confirm_publication':True})

    def test_pr_requires_explicit_publication_confirmation(self):
        draft=self.upload()
        self.app.enable_pr=True
        with patch.object(wb.shutil,'which',return_value='/usr/bin/gh'), self.assertRaisesRegex(ValueError,'confirmation'):
            self.app.submit_pr(draft['draft_id'],{})

    def test_pr_adapter_uses_isolated_worktree_and_candidate_only_paths(self):
        draft=self.upload()
        self.app.enable_pr=True
        commands=[]
        head=draft['context']['commit']
        def fake_run(args,cwd,timeout=30):
            commands.append(args)
            if args[:3]==['git','rev-parse','HEAD']: return head
            if args[:3]==['git','status','--porcelain']: return ''
            if args[:3]==['gh','repo','view']: return json.dumps({'nameWithOwner':'owner/repo','defaultBranchRef':{'name':'main'}})
            if args[:2]==['git','ls-remote']: return head+'\trefs/heads/main'
            if args[:3]==['git','worktree','add']:
                Path(args[-2]).mkdir()
            if args[:3]==['gh','pr','create']: return 'https://github.com/owner/repo/pull/12'
            return ''
        with patch.object(wb.shutil,'which',return_value='/usr/bin/gh'),patch.object(wb,'run',side_effect=fake_run):
            result=self.app.submit_pr(draft['draft_id'],{'confirm_publication':True})
        self.assertEqual(result['url'],'https://github.com/owner/repo/pull/12')
        tree=self.app.state_dir/('pr-'+draft['draft_id'])
        reg=yaml.safe_load((tree/wb.REGISTER).read_text())
        self.assertEqual(reg['documents'][-1]['status'],'candidate')
        self.assertFalse((tree/'workbench-package.json').exists())
        self.assertFalse(any('merge' in command for command in commands))
        self.assertTrue(any(command[:3]==['gh','pr','create'] and '--draft' in command for command in commands))
        self.assertEqual(self.app.draft(draft['draft_id'])['pr'],result)

    def test_pr_rejects_dirty_checkout_and_moved_remote(self):
        draft=self.upload()
        self.app.enable_pr=True
        head=draft['context']['commit']
        def responses(args,cwd,timeout=30):
            if args[:3]==['git','rev-parse','HEAD']: return head
            if args[:3]==['git','status','--porcelain']: return ' M unrelated.py'
            return ''
        with patch.object(wb.shutil,'which',return_value='/usr/bin/gh'),patch.object(wb,'run',side_effect=responses),self.assertRaisesRegex(ValueError,'clean tracked'):
            self.app.submit_pr(draft['draft_id'],{'confirm_publication':True})
        def moved(args,cwd,timeout=30):
            if args[:3]==['git','rev-parse','HEAD']: return head
            if args[:3]==['git','status','--porcelain']: return ''
            if args[:3]==['gh','repo','view']: return json.dumps({'nameWithOwner':'owner/repo','defaultBranchRef':{'name':'main'}})
            if args[:2]==['git','ls-remote']: return 'f'*40+'\trefs/heads/main'
            return ''
        with patch.object(wb.shutil,'which',return_value='/usr/bin/gh'),patch.object(wb,'run',side_effect=moved),self.assertRaisesRegex(ValueError,'Remote default branch differs'):
            self.app.submit_pr(draft['draft_id'],{'confirm_publication':True})

    def test_js_escapes_untrusted_source_text(self):
        if not shutil.which('node'):
            self.skipTest('Node unavailable')
        result=subprocess.run(['node','-e',"const {escapeHTML}=require('./scripts/workbench/app.js'); process.stdout.write(escapeHTML('<img src=x onerror=alert(1)>'));"],cwd=ROOT,text=True,capture_output=True,check=True)
        self.assertEqual(result.stdout,'&lt;img src=x onerror=alert(1)&gt;')

    def test_workspace_navigation_client(self):
        if not shutil.which('node'):
            self.skipTest('Node is required for the focused client regression')
        result = subprocess.run(['node', 'tests/workbench-navigation.test.cjs'], cwd=ROOT,
                                capture_output=True, text=True, check=True)
        self.assertIn('state-based next actions passed', result.stdout)

    def test_guided_intake_client_validation_and_metadata_suggestions(self):
        if not shutil.which('node'):
            self.skipTest('Node unavailable; JS checks can run with the external Node runtime')
        result = subprocess.run(['node', 'tests/workbench-guided-intake.test.cjs'], cwd=ROOT,
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_guided_requirement_review_progress_and_history_separation(self):
        if not shutil.which('node'):
            self.skipTest('Node unavailable')
        result = subprocess.run(['node', 'tests/workbench-requirement-review.test.cjs'], cwd=ROOT,
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_http_login_csrf_host_and_private_data(self):
        server=wb.make_server(self.app,'test-key-long-enough-for-session',port=0)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        port=server.server_address[1]
        conn=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
        origin=f'http://127.0.0.1:{port}'
        def request(method,path,payload=None,extra=None):
            headers={'Host':f'127.0.0.1:{port}'}
            if payload is not None:headers.update({'Content-Type':'application/json','Origin':origin})
            headers.update(extra or {})
            conn.request(method,path,None if payload is None else json.dumps(payload),headers)
            response=conn.getresponse();body=response.read();return response,body
        try:
            r,b=request('GET','/api/state');self.assertEqual(r.status,401)
            r,b=request('GET','/api/sources/TEST-SRC-001/history');self.assertEqual(r.status,401)
            r,b=request('GET','/',extra={'Host':'evil.example'});self.assertEqual(r.status,403)
            r,b=request('POST','/api/login',{'key':'test-key-long-enough-for-session'},{'Origin':'https://evil.example'});self.assertEqual(r.status,403)
            r,b=request('POST','/api/login',{'key':'test-key-long-enough-for-session'});self.assertEqual(r.status,200)
            cookie=r.getheader('Set-Cookie');self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie)
            r,b=request('GET','/api/state',extra={'Cookie':cookie});self.assertEqual(r.status,200)
            state=json.loads(b)
            r,b=request('POST','/api/review-packages',{'source_ids':['TEST-SRC-001']},{'Cookie':cookie});self.assertEqual(r.status,403)
            r,b=request('POST','/api/review-packages',{'source_ids':['TEST-SRC-001']},{'Cookie':cookie,'X-CSRF-Token':state['csrf']});self.assertEqual(r.status,201)
            self.assertEqual(json.loads(b)['execution'],'not_run')
            r,b=request('GET','/api/sources/TEST-SRC-001',extra={'Cookie':cookie});self.assertEqual(r.status,200)
            self.assertIn('Content-Security-Policy',dict(r.getheaders()))
            self.assertEqual(r.getheader('Cache-Control'),'no-store')
            r,b=request('POST','/api/source-reviews',{'source_id':'TEST-SRC-001'},{'Cookie':cookie});self.assertEqual(r.status,403)
            r,b=request('POST','/api/source-reviews',{'source_id':'TEST-SRC-001'},{'Cookie':cookie,'X-CSRF-Token':state['csrf']});self.assertEqual(r.status,201)
            draft=json.loads(b)
            r,b=request('POST',f'/api/drafts/{draft["draft_id"]}/notes',{'subject':draft['requirements'][0]['id'],'reviewer':'HTTP test','outcome':'needs_clarification','rationale':'Verify origin.'},{'Cookie':cookie,'X-CSRF-Token':state['csrf']});self.assertEqual(r.status,200)
            r,b=request('GET',f'/api/drafts/{draft["draft_id"]}',extra={'Cookie':cookie});self.assertEqual(r.status,200)
            self.assertEqual(json.loads(b)['notes'][0]['authority'],'proposal_only')
            r,b=request('GET',f'/api/drafts/{draft["draft_id"]}/packet',extra={'Cookie':cookie});self.assertEqual(r.status,200)
            with zipfile.ZipFile(io.BytesIO(b)) as archive:
                self.assertEqual(archive.read(str(self.path.relative_to(self.root))),self.path.read_bytes())
                self.assertNotIn(wb.REGISTER,archive.namelist())
            r,b=request('GET','/api/sources/TEST-SRC-001/history',extra={'Cookie':cookie});self.assertEqual(r.status,200)
            self.assertEqual(json.loads(b)['cases'],[])
            r,b=request('GET','/workspace-navigation.js');self.assertEqual(r.status,200)
            self.assertIn(b'WorkspaceNavigation',b)
            stored = self.app.draft_dir(draft['draft_id']) / 'draft.json'; before = stored.read_bytes()
            self.path.unlink()
            r,b=request('GET',f'/api/drafts/{draft["draft_id"]}',extra={'Cookie':cookie});self.assertEqual(r.status,200)
            current=json.loads(b);self.assertTrue(current['stale'])
            self.assertIn('source_missing',{x['code'] for x in current['stale_details']['reasons']})
            self.assertEqual(current['formal_status']['authority'],'recorded_history_only')
            self.assertEqual(stored.read_bytes(),before)
            r,b=request('GET','/api/state',extra={'Cookie':cookie});self.assertEqual(r.status,200)
            self.assertTrue(next(d for d in json.loads(b)['drafts'] if d['draft_id']==draft['draft_id'])['stale'])
            r,b=request('GET',f'/api/drafts/{draft["draft_id"]}/packet',extra={'Cookie':cookie});self.assertEqual(r.status,409)
        finally:
            conn.close();server.shutdown();server.server_close();thread.join(timeout=5)

    def test_idle_browser_connection_and_parallel_notes_do_not_block_or_lose_data(self):
        draft = self.app.source_review({'source_id': 'TEST-SRC-001'})
        key = 'parallel-browser-test-access-key'
        server = wb.make_server(self.app, key, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        idle = socket.create_connection(('127.0.0.1', port), timeout=2)
        def request(method, path, payload=None, headers=None):
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
            try:
                data = json.dumps(payload) if payload is not None else None
                fields = {'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{port}', **(headers or {})}
                conn.request(method, path, data, fields)
                response = conn.getresponse()
                body = response.read()
                return response.status, dict(response.getheaders()), body
            finally:
                conn.close()
        try:
            # The first TCP connection deliberately sends no HTTP request.
            # An ordinary HTTPServer waits on it instead of serving this page.
            self.assertEqual(request('GET', '/')[0], 200)
            status, headers, _ = request('POST', '/api/login', {'key': key})
            self.assertEqual(status, 200)
            cookie = headers['Set-Cookie']
            _, _, body = request('GET', '/api/state', headers={'Cookie': cookie})
            token = json.loads(body)['csrf']
            def note(index):
                return request('POST', f'/api/drafts/{draft["draft_id"]}/notes',
                               {'subject': draft['requirements'][0]['id'], 'reviewer': 'Concurrent test',
                                'outcome': 'needs_clarification', 'rationale': f'Question {index}'},
                               {'Cookie': cookie, 'X-CSRF-Token': token})[0]
            with ThreadPoolExecutor(max_workers=4) as executor:
                self.assertEqual(list(executor.map(note, range(8))), [200] * 8)
            notes = self.app.draft(draft['draft_id'])['notes']
            self.assertEqual(len(notes), 8)
            self.assertEqual({n['rationale'] for n in notes}, {f'Question {i}' for i in range(8)})
        finally:
            idle.close();server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':
    unittest.main()
