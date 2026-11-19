"""Complete original Workbench surface on a private instance, plus bounded backups."""
from contextlib import ExitStack
import base64
import copy
import hashlib
import io
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from lib.providers.workbench_data import WorkbenchData
from lib.providers.workbench_workspace import WorkbenchWorkspace
from lib import workbench_archive
import serve_governance_workbench as wb
from test_governance_workbench import WorkbenchTests
from acceptance.v1_workbench_oracle import load as original, Clock


class InstanceFixture:
    def private_instance(self, name='instance', node='a' * 32):
        if not hasattr(self, 'private_base'):
            temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
            self.private_base = Path(temporary.name).resolve()
        directory = self.private_base/name
        directory.mkdir(mode=0o700); (directory/'state').mkdir(mode=0o700)
        settings = {'source_root': str(self.root), 'node_id': node,
            'source_revision': self.app.head(), 'runtime_source_digest': 'b' * 64,
            'application_source_digest': 'c' * 64}
        workspace = WorkbenchWorkspace(directory, settings)
        return directory, settings, workspace

    def instance_app(self):
        # The V1 fixture root is itself a TemporaryDirectory. Keep state disjoint.
        self.instance, self.settings, self.workspace = self.private_instance()
        self.backend = WorkbenchData(self.root, self.workspace.root, instance=self.instance)
        self.app = wb.Workbench(self.root, self.workspace.root, backend=self.backend)


class PrivateInstanceWorkbenchTests(InstanceFixture, WorkbenchTests):
    """Inherit every existing upload/history/packet/HTTP/auth/client test."""
    def setUp(self):
        super().setUp(); self.instance_app()

    def other_workbench(self, name):
        instance, _, workspace = self.private_instance(name, node='e' * 32)
        return wb.Workbench(self.root, workspace.root,
            backend=WorkbenchData(self.root, workspace.root, instance=instance))

    def test_publication_uses_explicit_adapter_and_preserves_candidate_packet(self):
        draft = self.upload(); before = self.reg.read_bytes(); self.app.enable_pr = True
        publisher = Mock(); publisher.publish.return_value = {'url': 'https://scm.example/proposals/12'}
        self.app.publisher = publisher
        result = self.app.submit_pr(draft['draft_id'], {'confirm_publication': True})
        args = publisher.publish.call_args.kwargs
        self.assertEqual(args['destination'], self.instance/'state/workbench-publications'/('pr-' + draft['draft_id']))
        self.assertEqual(args['context'], draft['context'])
        self.assertEqual(args['files'][draft['source']['source_path']],
            (self.workspace.root/draft['draft_id']/draft['upload_name']).read_bytes())
        self.assertEqual(self.reg.read_bytes(), before)
        self.assertEqual(self.app.submit_pr(draft['draft_id'], {'confirm_publication': True}), result)
        self.assertEqual(publisher.publish.call_count, 1)


class CompleteOriginalWorkbenchTests(InstanceFixture, WorkbenchTests):
    # Avoid duplicating the inherited regression suite; this class's suite is
    # explicitly restricted below to its own independent original comparisons.
    def setUp(self):
        super().setUp(); self.old, _, self.old_process = original(ROOT/'tests/fixtures/v2-workbench-original', self.root)
        self.legacy = self.old.Workbench(self.root)
        self.instance_app()
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(wb, 'datetime', Clock))
        self.stack.enter_context(patch.object(self.old, 'datetime', Clock))
        self.stack.enter_context(patch.object(self.old_process, 'datetime', Clock))
        self.stack.enter_context(patch('lib.providers.workbench_data.datetime', Clock))
        self.stack.enter_context(patch('secrets.token_hex', return_value='d' * 32))

    def equivalent(self, value):
        value = copy.deepcopy(value)
        prefix = self.legacy.state_dir.relative_to(self.root).as_posix() + '/'
        def labels(item):
            if isinstance(item, dict):
                for name, row in item.items():
                    if name == 'source_path' and isinstance(row, str) and row.startswith(prefix):
                        item[name] = 'state/workbench/' + row[len(prefix):]
                    else: labels(row)
            elif isinstance(item, list):
                for row in item: labels(row)
        labels(value); return value

    def pair(self, method, *args):
        old = getattr(self.legacy, method)(*copy.deepcopy(args))
        new = getattr(self.app, method)(*copy.deepcopy(args))
        self.assertEqual(new, self.equivalent(old)); return old, new

    def payload(self):
        return {'filename': 'candidate.md', 'content_base64': base64.b64encode(
            b'# Candidate\n[DSCB-L1-REQ-001] The system shall retain evidence for eighteen months.\n').decode(),
            'metadata': {'id': 'TEST-CAND-002', 'title': 'New source', 'owner': 'Owner', 'version': '2',
            'governance_domains': ['devsecops'], 'replacement_for': 'TEST-SRC-001'}}

    def packets_equal(self, identifier):
        old = self.legacy.packet_files(identifier); new = self.app.packet_files(identifier)
        self.assertEqual(old.keys(), new.keys())
        for name in old:
            if name == 'workbench-package.json':
                self.assertEqual(json.loads(new[name]), self.equivalent(json.loads(old[name])))
            else: self.assertEqual(new[name], old[name], name)
        with zipfile.ZipFile(io.BytesIO(self.legacy.packet(identifier))) as a, zipfile.ZipFile(io.BytesIO(self.app.packet(identifier))) as b:
            self.assertEqual(a.namelist(), b.namelist())
            for name in a.namelist():
                if name == 'workbench-package.json':
                    self.assertEqual(json.loads(b.read(name)), self.equivalent(json.loads(a.read(name))))
                else: self.assertEqual(b.read(name), a.read(name), name)

    def test_original_complete_registered_state_context_extraction_history_and_process(self):
        for method, args in [('register', ()), ('context', ()), ('document', ('TEST-SRC-001',)),
                ('inspect', (self.app.document('TEST-SRC-001'),)), ('requirement_history', ('TEST-SRC-001',)),
                ('formal_status', (self.app.document('TEST-SRC-001'), wb.digest(self.path.read_bytes()))), ('state', ())]:
            with self.subTest(method=method): self.pair(method, *args)

    def test_original_candidate_notes_saved_draft_full_packet_and_zip_members(self):
        _, new = self.pair('create_draft', self.payload()); identifier = new['draft_id']
        self.pair('note', identifier, {'subject': new['requirements'][0]['id'], 'reviewer': 'Human',
            'outcome': 'needs_clarification', 'rationale': 'Proposal only'})
        self.pair('draft', identifier); self.packets_equal(identifier)
        self.assertEqual(json.loads((self.app.draft_dir(identifier)/'draft.json').read_bytes()),
            self.equivalent(json.loads((self.legacy.draft_dir(identifier)/'draft.json').read_bytes())))

    def test_original_source_review_full_draft_notes_packet_and_formal_history(self):
        before = self.reg.read_bytes()
        _, new = self.pair('source_review', {'source_id': 'TEST-SRC-001'}); identifier = new['draft_id']
        self.pair('note', identifier, {'subject': 'source', 'reviewer': 'Human',
            'outcome': 'confirm_candidate', 'rationale': 'Not an approval'})
        self.pair('draft', identifier); self.packets_equal(identifier)
        self.assertEqual(self.reg.read_bytes(), before)

    def test_original_review_package_complete_scope_and_not_run_semantics(self):
        _, new = self.pair('review_package', {'source_ids': ['TEST-SRC-001']})
        self.assertEqual(new['execution'], 'not_run')
        self.pair('note', new['draft_id'], {'subject': 'TEST-SRC-001', 'reviewer': 'Human',
            'outcome': 'propose_resolution', 'rationale': 'Separate review required'})
        self.packets_equal(new['draft_id'])

    def test_original_stale_source_upload_and_register_observations(self):
        _, new = self.pair('create_draft', self.payload()); identifier = new['draft_id']
        for app in (self.legacy, self.app): (app.draft_dir(identifier)/new['upload_name']).write_bytes(b'changed')
        self.pair('draft', identifier)
        for app in (self.legacy, self.app):
            with self.assertRaisesRegex(ValueError, 'upload'): app.packet(identifier)
        self.path.write_text('Changed current registered source')
        self.pair('draft', identifier)
        for app in (self.legacy, self.app):
            with self.assertRaisesRegex(ValueError, 'Repository changed'):
                app.note(identifier, {'subject': 'source', 'reviewer': 'x', 'outcome': 'reject_candidate', 'rationale': 'x'})

    def test_original_live_unregistered_and_newly_registered_source_observations(self):
        unregistered = self.root/'docs/governance/source-documents/NEW-SRC-002.md'
        unregistered.write_text('# New source\n[DSCB-L1-REQ-002] The system shall retain complete records.\n')
        self.pair('state')
        import yaml
        register = yaml.safe_load(self.reg.read_bytes())
        new = {**register['documents'][0], 'id': 'NEW-SRC-002',
            'source_path': 'docs/governance/source-documents/NEW-SRC-002.md'}
        register['documents'].append(new); self.reg.write_text(yaml.safe_dump(register))
        self.pair('inspect', new); self.pair('state')
        unregistered.unlink(); self.pair('state')

    def test_original_complete_docx_upload_identifiers_warnings_and_packet_members(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>[DSCB-L1-REQ-003] The system shall protect records.</w:t></w:r></w:p></w:body></w:document>')
            archive.writestr('word/comments.xml', '<comments/>')
        payload = self.payload(); payload.update(filename='candidate.docx', content_base64=base64.b64encode(output.getvalue()).decode())
        _, new = self.pair('create_draft', payload)
        self.assertIn('docx_comments_present_not_included', new['warnings'])
        self.assertEqual(new['requirements'][0]['source_requirement_id'], 'DSCB-L1-REQ-003')
        self.packets_equal(new['draft_id'])

    @unittest.skipUnless(importlib.util.find_spec('pypdf'), 'Optional PDF parser required; installed Workbench packages include it')
    def test_original_complete_pdf_upload_page_locators_and_empty_page_warnings(self):
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
        writer = PdfWriter(); page = writer.add_blank_page(width=300, height=300)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject(); stream.set_data(b'BT /F1 12 Tf 10 100 Td ([DSCB-L1-REQ-003] The system shall protect records.) Tj ET')
        page[NameObject('/Contents')] = stream
        writer.add_blank_page(width=300, height=300)
        output = io.BytesIO(); writer.write(output)
        payload = self.payload(); payload.update(filename='candidate.pdf', content_base64=base64.b64encode(output.getvalue()).decode())
        _, new = self.pair('create_draft', payload)
        self.assertEqual(new['requirements'][0]['source_requirement_id'], 'DSCB-L1-REQ-003')
        self.assertTrue(new['requirements'][0]['source_locator'].startswith('page:1'))
        self.assertIn('pdf_text_not_extractable_ocr_required_pages:2', new['warnings'])
        self.packets_equal(new['draft_id'])

    def test_original_invalid_uploads_ids_scope_and_note_outcomes(self):
        for update in ({'filename': '../evil.md'}, {'content_base64': '!'}, {'content_base64': ''},
                       {'metadata': {'id': 'TEST-SRC-001'}}, {'filename': 'unsupported.exe'}):
            payload = self.payload(); payload.update(update); results = []
            for app in (self.legacy, self.app):
                try: app.create_draft(payload)
                except Exception as error: results.append((type(error), str(error)))
                else: self.fail('Invalid original input unexpectedly accepted')
            self.assertEqual(*results)


def load_tests(loader, tests, pattern):
    # Imported base classes are helpers, not a second implicit suite.
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(PrivateInstanceWorkbenchTests))
    suite.addTests(CompleteOriginalWorkbenchTests(name) for name in CompleteOriginalWorkbenchTests.__dict__ if name.startswith('test_'))
    suite.addTests(WorkspaceBackupTests(name) for name in WorkspaceBackupTests.__dict__ if name.startswith('test_'))
    suite.addTests(loader.loadTestsFromTestCase(WorkbenchEntrypointTests))
    return suite


class WorkspaceBackupTests(InstanceFixture, WorkbenchTests):
    # Restrict to own methods below; fixture is inherited for real schemas/Git.
    def setUp(self):
        super().setUp(); self.instance_app()

    def backup_path(self): return self.private_base/'draft-backup.zip'

    def pin(self): return hashlib.sha256(self.backup_path().read_bytes()).hexdigest()

    def test_complete_draft_bytes_restore_on_new_node_without_keys_or_publication(self):
        draft = self.upload(); self.app.note(draft['draft_id'], {'subject': 'source', 'reviewer': 'Human',
            'outcome': 'needs_clarification', 'rationale': 'Proposal'})
        before = self.workspace.capture(); receipt = self.workspace.backup(self.backup_path())
        other, settings, workspace = self.private_instance('other-instance', node='e' * 32)
        self.assertEqual(workspace.restore(self.backup_path(), self.pin())['original_node_id'], self.settings['node_id'])
        self.assertEqual(workspace.capture(), before)
        self.assertFalse((other/'workbench-key.json').exists())
        self.assertFalse(receipt['publication_enabled']); self.assertFalse(receipt['authority_transferred'])
        self.assertFalse((other/'state/workbench-publications').exists())

    def test_backup_is_reproducible_and_never_overwrites_or_targets_product_or_instance(self):
        self.upload(); first = self.workspace.backup(self.backup_path())
        second_path = self.private_base/'second.zip'; second = self.workspace.backup(second_path)
        self.assertEqual(first['sha256'], second['sha256']); self.assertEqual(self.backup_path().read_bytes(), second_path.read_bytes())
        with self.assertRaises(FileExistsError): self.workspace.backup(self.backup_path())
        for path in (self.root/'forbidden.zip', self.instance/'forbidden.zip'):
            with self.assertRaisesRegex(ValueError, 'outside_product_and_instance'): self.workspace.backup(path)
            self.assertFalse(path.exists())

    def test_server_and_offline_effects_have_one_owner_and_restore_needs_empty_workspace(self):
        self.upload(); self.workspace.backup(self.backup_path())
        _, _, another = self.private_instance('other-instance', node='e' * 32)
        with self.workspace.lease():
            with self.assertRaisesRegex(ValueError, 'busy'): self.workspace.backup(self.private_base/'busy.zip')
        with self.assertRaisesRegex(ValueError, 'fresh_workbench_restore_required'): self.workspace.restore(self.backup_path(), self.pin())

    def test_changed_upload_invalid_draft_and_private_files_are_never_backed_up(self):
        draft = self.upload(); folder = self.workspace.root/draft['draft_id']; source = folder/draft['upload_name']
        raw = source.read_bytes(); source.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'upload_binding'): self.workspace.backup(self.backup_path())
        source.write_bytes(raw); source.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'private_workbench_file'): self.workspace.backup(self.backup_path())
        source.chmod(0o600); source.unlink(); source.symlink_to(self.path)
        with self.assertRaisesRegex(ValueError, 'private_workbench_file'): self.workspace.backup(self.backup_path())
        self.assertFalse(self.backup_path().exists())

    def test_archive_tamper_wrong_product_extra_member_and_path_escape_are_rejected(self):
        self.upload(); self.workspace.backup(self.backup_path()); raw = self.backup_path().read_bytes()
        manifest, files = workbench_archive.inspect(raw, self.workspace.schema, self.workspace.binding)
        changed = dict(self.workspace.binding); changed['runtime_source_digest'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'product_mismatch'):
            workbench_archive.inspect(raw, self.workspace.schema, changed)
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as old, zipfile.ZipFile(output, 'w') as new:
            for info in old.infolist(): new.writestr(info, old.read(info))
            new.writestr('../escape', b'forbidden')
        with self.assertRaisesRegex(ValueError, 'member'):
            workbench_archive.inspect(output.getvalue(), self.workspace.schema, self.workspace.binding)
        self.assertEqual(self.workspace.capture()[0], files)

    def test_stale_proposals_and_interrupted_empty_folders_are_preserved_without_authority(self):
        draft = self.upload(); self.path.write_text('Changed registered source')
        empty = self.workspace.root/('f' * 32); empty.mkdir(mode=0o700)
        before = self.workspace.capture(); self.workspace.backup(self.backup_path())
        _, _, target = self.private_instance('target', node='e' * 32); target.restore(self.backup_path(), self.pin())
        self.assertEqual(target.capture(), before)
        app = wb.Workbench(self.root, target.root, backend=WorkbenchData(self.root, target.root, instance=target.instance))
        self.assertTrue(app.draft(draft['draft_id'])['stale'])
        with self.assertRaisesRegex(ValueError, 'stale'): app.packet(draft['draft_id'])

    def test_explicit_whole_archive_checksum_and_private_input_are_required(self):
        self.upload(); self.workspace.backup(self.backup_path())
        _, _, target = self.private_instance('target', node='e' * 32)
        before = target.capture()
        with self.assertRaisesRegex(ValueError, 'checksum_mismatch'):
            target.restore(self.backup_path(), '0' * 64)
        with self.assertRaisesRegex(ValueError, 'digest_required'):
            target.restore(self.backup_path(), 'invalid')
        self.backup_path().chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'private_workbench_file'):
            target.restore(self.backup_path(), self.pin())
        self.assertEqual(target.capture(), before)

    def test_keys_and_native_publication_worktrees_never_enter_draft_backups(self):
        self.upload(); key = b'synthetic-private-key-never-backup'
        (self.instance/'workbench-key.json').write_bytes(key)
        native = self.instance/'state/workbench-publications'; native.mkdir(mode=0o700)
        (native/'attempt').write_text('synthetic private native recovery data')
        self.workspace.backup(self.backup_path()); raw = self.backup_path().read_bytes()
        self.assertNotIn(key, raw)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertTrue(all(name == 'manifest.json' or name.split('/')[0] in
                {p.name for p in self.workspace.root.iterdir()} for name in archive.namelist()))
        self.assertTrue((native/'attempt').exists())

    def test_hardlinked_and_nonregular_uploads_and_linked_draft_directories_are_rejected(self):
        draft = self.upload(); folder = self.workspace.root/draft['draft_id']; upload = folder/draft['upload_name']
        alias = self.private_base/'alias'; os.link(upload, alias)
        with self.assertRaisesRegex(ValueError, 'private_workbench_file'): self.workspace.capture()
        with self.assertRaisesRegex(ValueError, 'private_workbench_file'): self.backend.extract(upload)
        alias.unlink(); raw = upload.read_bytes(); upload.unlink(); os.mkfifo(upload, 0o600)
        with self.assertRaisesRegex(ValueError, 'private_workbench_file'): self.workspace.capture()
        upload.unlink(); upload.write_bytes(raw); upload.chmod(0o600)
        moved = self.private_base/'moved'; folder.rename(moved); folder.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'private_workbench_draft_directory'): self.app.draft(draft['draft_id'])

    def test_unknown_workspace_files_and_malformed_private_drafts_remain_unmodified(self):
        draft = self.upload(); folder = self.workspace.root/draft['draft_id']; saved = folder/'draft.json'; raw = saved.read_bytes()
        saved.write_text('{"schema_version": "bad"}')
        with self.assertRaisesRegex(ValueError, 'invalid_private_workbench_draft'): self.app.draft(draft['draft_id'])
        with self.assertRaisesRegex(ValueError, 'invalid_workbench_backup_draft'): self.workspace.backup(self.backup_path())
        self.assertEqual(saved.read_text(), '{"schema_version": "bad"}')
        saved.write_bytes(raw); (folder/'unexpected').write_text('retain for manual inspection')
        with self.assertRaisesRegex(ValueError, 'invalid_workbench_backup_member'): self.workspace.backup(self.backup_path())
        self.assertTrue((folder/'unexpected').exists()); self.assertFalse(self.backup_path().exists())

    def test_verification_constructor_is_read_only_and_source_roots_stay_disjoint(self):
        instance, settings, workspace = self.private_instance('verify', node='e' * 32)
        workspace.root.rmdir()
        readonly = WorkbenchWorkspace(instance, settings, create=False)
        self.assertFalse(readonly.root.exists())
        invalid = self.root/'bad-instance'; invalid.mkdir(mode=0o700); (invalid/'state').mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError, 'outside_product'):
            WorkbenchWorkspace(invalid, {**settings, 'source_root': str(self.root)})
        self.assertFalse((invalid/'state/workbench').exists())

    def test_manifest_cannot_grant_authority_inject_keys_or_hide_bytes(self):
        self.upload(); files, directories = self.workspace.capture()
        raw, manifest = workbench_archive.create(files, directories, self.workspace.binding, self.workspace.schema)
        variants = []
        for name, value in [('authority_transferred', True), ('keys_included', True),
                            ('directories', [['invalid']]), ('files', {})]:
            changed = copy.deepcopy(manifest); changed[name] = value; variants.append(changed)
        for changed in variants:
            output = io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(raw)) as old, zipfile.ZipFile(output, 'w') as new:
                for info in old.infolist():
                    new.writestr(info, json.dumps(changed).encode() if info.filename == 'manifest.json' else old.read(info))
            with self.assertRaises(ValueError):
                workbench_archive.inspect(output.getvalue(), self.workspace.schema, self.workspace.binding)
        self.assertEqual(self.workspace.capture(), (files, directories))

    def test_server_unknown_draft_and_changed_upload_keep_original_stale_behavior(self):
        with self.assertRaisesRegex(ValueError, 'Unknown draft'): self.app.draft('f' * 32)
        draft = self.upload(); upload = self.workspace.root/draft['draft_id']/draft['upload_name']
        upload.write_bytes(b'changed source')
        current = self.app.draft(draft['draft_id'])
        self.assertTrue(current['stale'])
        self.assertIn('uploaded_source_changed', {r['code'] for r in current['stale_details']['reasons']})
        with self.assertRaisesRegex(ValueError, 'upload'): self.app.packet(draft['draft_id'])


    def test_explicit_historical_import_preserves_original_bytes_and_stale_history_after_update(self):
        draft = self.upload(); before = self.workspace.capture(); self.workspace.backup(self.backup_path())
        import subprocess
        marker = self.root/'updated-source.txt'; marker.write_text('controlled product update')
        subprocess.run(['git','add','.'],cwd=self.root,check=True,capture_output=True)
        subprocess.run(['git','-c','user.name=Test','-c','user.email=test@example.invalid',
            'commit','--no-gpg-sign','-qm','controlled source update'],cwd=self.root,check=True,capture_output=True)
        instance, _, target = self.private_instance('updated', node='e' * 32)
        with self.assertRaisesRegex(ValueError, 'product_mismatch'):
            target.restore(self.backup_path(), self.pin())
        result = target.restore(self.backup_path(), self.pin(), allow_source_change=True)
        self.assertTrue(result['historical_source_import']); self.assertFalse(result['authority_transferred'])
        self.assertEqual(target.capture(), before)
        app = wb.Workbench(self.root, target.root, backend=WorkbenchData(self.root, target.root, instance=instance))
        current = app.draft(draft['draft_id'])
        self.assertTrue(current['stale'])
        self.assertIn('repository_changed', {r['code'] for r in current['stale_details']['reasons']})
        with self.assertRaisesRegex(ValueError, 'stale'): app.packet(draft['draft_id'])


    def test_unsafe_candidate_and_scope_destinations_cannot_be_saved_loaded_or_exported(self):
        draft = self.upload(); folder = self.workspace.root/draft['draft_id']; saved = folder/'draft.json'
        raw = saved.read_bytes()
        unsafe = ['../../synthetic-escape-test.md', '/absolute.md',
            'docs/governance/source-documents/../escape.md',
            'docs/governance/source-documents/OTHER-ID-001.md',
            'docs/governance/source-documents/TEST-CAND-002.sh',
            'docs/governance/source-documents/TEST-CAND-002.md\n',
            'docs/governance/source-documents//TEST-CAND-002.md']
        for name in unsafe:
            with self.subTest(destination=name):
                changed = json.loads(raw); changed['source']['source_path'] = name
                with self.assertRaisesRegex(ValueError, 'source_destination'):
                    self.app.save(folder, changed)
                self.assertEqual(saved.read_bytes(), raw)
                # Model a coherent private-file edit that bypasses save().
                saved.write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError, 'source_destination'):
                    self.app.packet(draft['draft_id'])
                self.app.enable_pr = True; self.app.publisher = Mock()
                with self.assertRaisesRegex(ValueError, 'source_destination'):
                    self.app.submit_pr(draft['draft_id'], {'confirm_publication':True})
                self.app.publisher.publish.assert_not_called()
                with self.assertRaisesRegex(ValueError, 'source_destination'):
                    self.workspace.backup(self.backup_path())
                saved.write_bytes(raw)
        scope = self.app.review_package({'source_ids':['TEST-SRC-001']})
        scope['manifest'][0]['source_path'] = '../../escape.md'
        with self.assertRaisesRegex(ValueError, 'source_destination'):
            self.app.save(self.workspace.root/scope['draft_id'], scope)
        review = self.app.source_review({'source_id':'TEST-SRC-001'})
        review['source']['source_path'] = '../../escape.md'
        with self.assertRaisesRegex(ValueError, 'source_destination'):
            self.app.save(self.workspace.root/review['draft_id'], review)
        self.assertFalse(self.backup_path().exists())

    def test_coherent_schema_valid_backup_with_explicit_digest_still_cannot_inject_packet_path(self):
        draft = self.upload(); self.workspace.backup(self.backup_path())
        with zipfile.ZipFile(self.backup_path()) as archive:
            members = [(copy.copy(info), archive.read(info)) for info in archive.infolist()]
        name = draft['draft_id']+'/draft.json'
        files = {info.filename:raw for info,raw in members}
        changed = json.loads(files[name]); changed['source']['source_path'] = '../../synthetic-escape-test.md'
        files[name] = json.dumps(changed).encode()
        manifest = json.loads(files['manifest.json'])
        manifest['files'][name] = {'sha256':hashlib.sha256(files[name]).hexdigest(), 'bytes':len(files[name])}
        files['manifest.json'] = json.dumps(manifest).encode()
        malformed = self.private_base/'coherent-malicious.zip'
        with zipfile.ZipFile(malformed,'w',compression=zipfile.ZIP_STORED) as archive:
            for info, _ in members: archive.writestr(info, files[info.filename])
        malformed.chmod(0o600); pin = hashlib.sha256(malformed.read_bytes()).hexdigest()
        _, _, target = self.private_instance('guarded', node='e'*32)
        before = target.capture()
        for explicit_historical in (False,True):
            with self.assertRaisesRegex(ValueError, 'source_destination'):
                target.restore(malformed, pin, allow_source_change=explicit_historical)
            self.assertEqual(target.capture(), before)



class WorkbenchEntrypointTests(unittest.TestCase):
    def test_standalone_v2_facade_requires_explicit_instance_before_server_or_key_creation(self):
        from contextlib import redirect_stderr
        with patch.object(wb, 'make_server') as server, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as result: wb.main([])
        self.assertEqual(result.exception.code, 2); server.assert_not_called()

    def test_standalone_facade_preserves_full_explicit_option_forwarding(self):
        with patch('lib.v2_application.run', return_value=0) as run:
            self.assertEqual(wb.main(['--instance','/private/instance','--port','19090',
                '--consumer-projection','/private/projection','--state-dir','/private/state',
                '--enable-pr','--publication-profile','/private/profile']),0)
        self.assertEqual(run.call_args.args, ('workbench', ['--port','19090','--state-dir','/private/state',
            '--consumer-projection','/private/projection','--publication-profile','/private/profile','--enable-pr']))
        self.assertEqual(run.call_args.kwargs, {'instance_path':Path('/private/instance')})
