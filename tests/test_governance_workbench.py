from __future__ import annotations

import base64
import http.client
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
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
        self.root = Path(self.tmp.name)
        (self.root / 'docs/governance/source-documents').mkdir(parents=True)
        (self.root / 'model/documents').mkdir(parents=True)
        (self.root / 'schemas').mkdir()
        for name in ('source-document-register.schema.json', 'governance-workbench-draft.schema.json'):
            shutil.copy(ROOT / 'schemas' / name, self.root / 'schemas' / name)
        self.path = self.root / 'docs/governance/source-documents/TEST-SRC-001.md'
        self.path.write_text('# Test\nThe system shall retain evidence for twelve months.\n')
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
        payload={'filename':'proposal.md','content_base64':base64.b64encode(b'# Candidate\nThe system shall retain evidence for eighteen months.\n').decode(),
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
        self.assertTrue(draft['deltas'])
        with zipfile.ZipFile(io.BytesIO(self.app.packet(draft['draft_id']))) as archive:
            jsonschema.validate(json.loads(archive.read('workbench-package.json')), wb.read_json(self.root / 'schemas/governance-workbench-draft.schema.json'))
            reg=yaml.safe_load(archive.read(wb.REGISTER))
            self.assertEqual(reg['documents'][-1]['status'],'candidate')
            self.assertIsNone(reg['documents'][-1]['supersedes'])
            self.assertEqual(wb.digest(archive.read(draft['source']['source_path'])),draft['sha256'])
        self.assertEqual(self.reg.read_bytes(),before)

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
        finally:
            conn.close();server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':
    unittest.main()
