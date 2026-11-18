"""Real filesystem and declared technical receipt boundaries; no authority or providers."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(os.environ.get('AXIOM_TEST_PRODUCT_ROOT',Path(__file__).resolve().parents[1]));sys.path.insert(0,str(ROOT/'scripts'))
from lib import functional_parity as parity


class ParityEvidence(unittest.TestCase):
    def setUp(self):
        previous=os.umask(0o077);self.addCleanup(os.umask,previous)
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name).resolve();self.root=self.base/'source';self.root.mkdir()
        for name in ('config','schemas','scripts'): (self.root/name).mkdir()
        shutil.copyfile(ROOT/'schemas/axiom-v2-functional-parity.schema.json',self.root/'schemas/axiom-v2-functional-parity.schema.json')
        self.matrix=json.loads((ROOT/'config/axiom-v2-functional-parity.json').read_text())
        for group in ('areas','entrypoints','ci_workflows','operating_workflows'):
            for row in self.matrix[group]:
                row['state']='pending'
                if 'evidence' in row:row['evidence']=[]
        self.subject=self.matrix['entrypoints'][0];self.subject.update(state='verified',v2_implementation='scripts/subject.py:Implemented',evidence=[])
        self.implementation=self.root/'scripts/subject.py';self.implementation.write_text('class Implemented:\n    pass\n')
        (self.root/'config/axiom-v2-distribution.json').write_text(json.dumps({'python_files':['scripts/subject.py']}))
        self.pack=self.root/parity.PACKAGED_EVIDENCE;self.pack.mkdir();self.runtime=parity.source_digest();self.values={}
        for kind in ('positive','negative','installed'):
            value={'schema_version':1,'subject':self.subject['v1_path'],'kind':kind,'passed':True,'runtime_source_digest':self.runtime,
                'evidence_kind':'declared_technical_parity_evidence','v1_reference':parity.V1_REFERENCE,
                'original_source_sha256':self.subject['v1_sha256'],'implementation_source_sha256':hashlib.sha256(self.implementation.read_bytes()).hexdigest(),
                'authority_transferred':False,'independent_human_approval':False,'official_acceptance':False,'production_approval':False,
                'evidence_sources':{'coverage_audit':{'sha256':'a'*64,'bytes':12}},'case_counts':{kind if kind!='installed' else 'installed_mac':1}}
            self.subject['evidence'].append({'id':kind,'kind':kind,'sha256':'0'*64});self.values[kind]=value;self.rewrite(kind,value)
        self.save()

    def save(self):(self.root/'config/axiom-v2-functional-parity.json').write_text(json.dumps(self.matrix))

    def rewrite(self,kind,value):
        raw=value if isinstance(value,bytes) else (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
        (self.pack/(kind+'.json')).write_bytes(raw)
        next(row for row in self.subject['evidence'] if row['kind']==kind)['sha256']=hashlib.sha256(raw).hexdigest()
        self.save();return raw

    def test_packaged_receipts_are_read_by_default_and_keep_incomplete_goal_false(self):
        before={p.name:p.read_bytes() for p in self.pack.iterdir()};value=parity.audit(self.root)
        self.assertEqual(value['states']['entrypoints']['verified'],1);self.assertEqual(value['evidence_receipts_checked'],3)
        self.assertEqual(value['evidence_directory_source'],'packaged');self.assertFalse(value['functional_parity_complete'])
        self.assertFalse(value['source_scope_verified']);self.assertFalse(value['authority_transferred']);self.assertFalse(value['evidence_assertions_independently_authenticated'])
        self.assertEqual(value['matrix_sha256'],hashlib.sha256((self.root/'config/axiom-v2-functional-parity.json').read_bytes()).hexdigest())
        self.assertEqual({p.name:p.read_bytes() for p in self.pack.iterdir()},before)

    def test_operator_directory_is_explicit_and_never_falls_back_to_packaged_copy(self):
        external=self.base/'operator';shutil.copytree(self.pack,external)
        value=parity.audit(self.root,evidence_root=external);self.assertEqual(value['evidence_directory_source'],'operator')
        (external/'positive.json').unlink()
        with self.assertRaisesRegex(ValueError,'evidence_missing'):parity.audit(self.root,evidence_root=external)
        self.assertTrue((self.pack/'positive.json').exists())

    def test_ordinary_minimal_private_v1_metadata_still_requires_explicit_directory(self):
        value={k:self.values['positive'][k] for k in ('schema_version','subject','kind','passed','runtime_source_digest')};self.rewrite('positive',value)
        with self.assertRaisesRegex(ValueError,'public_metadata_required'):parity.audit(self.root)
        checked=parity.audit(self.root,evidence_root=self.pack);self.assertEqual(checked['evidence_receipts_checked'],3)

    def test_missing_receipt_is_a_failure_not_a_pending_or_successful_claim(self):
        (self.pack/'installed.json').unlink()
        with self.assertRaisesRegex(ValueError,'evidence_missing'):parity.audit(self.root)

    def test_receipt_changed_without_matrix_digest_update_is_rejected(self):
        (self.pack/'negative.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'evidence_digest_changed'):parity.audit(self.root)

    def test_rehashed_wrong_subject_kind_passed_or_stale_runtime_is_rejected(self):
        for key,changed in (('subject','scripts/another.py'),('kind','negative'),('passed',False),('runtime_source_digest','0'*64)):
            with self.subTest(key=key):
                value=deepcopy(self.values['positive']);value[key]=changed;self.rewrite('positive',value)
                with self.assertRaises(ValueError):parity.audit(self.root)
                self.rewrite('positive',self.values['positive'])

    def test_original_source_and_current_implementation_bindings_are_checked(self):
        for key in ('original_source_sha256','implementation_source_sha256'):
            value=deepcopy(self.values['positive']);value[key]='0'*64;self.rewrite('positive',value)
            with self.assertRaisesRegex(ValueError,'evidence_source_changed'):parity.audit(self.root)
            self.rewrite('positive',self.values['positive'])
        self.implementation.write_text('class Implemented:\n    changed=True\n')
        with self.assertRaisesRegex(ValueError,'evidence_source_changed'):parity.audit(self.root)

    def test_changed_original_matrix_hash_does_not_relabel_old_evidence(self):
        self.subject['v1_sha256']='0'*64;self.save()
        with self.assertRaisesRegex(ValueError,'evidence_source_changed'):parity.audit(self.root)

    def test_rehashed_private_bodies_and_authority_claims_fail_closed_contract(self):
        for key,data in (('private_review_text','synthetic private review text'),('raw_input',{}),('authority_transferred',True),('independent_human_approval',True),('official_acceptance',True),('production_approval',True)):
            with self.subTest(key=key):
                value=deepcopy(self.values['positive']);value[key]=data;self.rewrite('positive',value)
                with self.assertRaisesRegex(ValueError,'invalid_functional_parity_evidence_metadata'):parity.audit(self.root)
                self.rewrite('positive',self.values['positive'])

    def test_evidence_source_descriptors_are_hashes_not_private_paths_or_body_text(self):
        for change in ({'raw_log':'private contents'},{'coverage_audit':{'path':'/private/secret','sha256':'a'*64,'bytes':12}},{'coverage_audit':{'sha256':'bad','bytes':12}},{'coverage_audit':{'sha256':'a'*64,'bytes':True}}):
            value=deepcopy(self.values['positive']);value['evidence_sources']=change;self.rewrite('positive',value)
            with self.assertRaisesRegex(ValueError,'invalid_functional_parity_evidence_metadata'):parity.audit(self.root)

    def test_duplicate_keys_nonfinite_numbers_and_nonobject_receipts_are_rejected(self):
        raw=json.dumps(self.values['positive']).encode()
        for malformed in (b'{"kind":"negative",'+raw[1:],raw[:-1]+b',"case_counts":{"positive":NaN}}',b'[]'):
            self.rewrite('positive',malformed)
            with self.assertRaises(ValueError):parity.audit(self.root)

    def test_public_receipt_requires_expected_source_and_non_authority_metadata(self):
        for key in ('evidence_kind','v1_reference','evidence_sources','original_source_sha256','implementation_source_sha256','authority_transferred','independent_human_approval','official_acceptance','production_approval'):
            value=deepcopy(self.values['positive']);del value[key];self.rewrite('positive',value)
            with self.assertRaisesRegex(ValueError,'public_metadata_required'):parity.audit(self.root)

    def test_file_symlink_hardlink_fifo_and_symlink_pack_are_rejected(self):
        path=self.pack/'positive.json';raw=path.read_bytes();unrelated=self.base/'unrelated.json';unrelated.write_bytes(raw)
        for kind in ('symlink','hardlink','fifo'):
            path.unlink()
            if kind=='symlink':path.symlink_to(unrelated)
            elif kind=='hardlink':os.link(unrelated,path)
            else:os.mkfifo(path,0o600)
            with self.assertRaises(ValueError):parity.audit(self.root)
            path.unlink();path.write_bytes(raw)
        alternate=self.base/'alternate';self.pack.rename(alternate);self.pack.symlink_to(alternate,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'unsafe_functional_parity_evidence'):parity.audit(self.root)

    def test_file_size_and_direct_id_traversal_are_bounded(self):
        path=self.pack/'positive.json'
        with path.open('wb') as stream:stream.truncate(parity.MAX_RECEIPT+1)
        with self.assertRaisesRegex(ValueError,'regular_bounded_file_required'):parity.audit(self.root)
        with self.assertRaisesRegex(ValueError,'unsafe_functional_parity_evidence_id'):
            parity.evidence_checked({'id':'../outside','kind':'positive','sha256':'0'*64},self.subject['v1_path'],self.pack)

    def test_reader_detects_a_concurrent_edit_without_changing_other_actor_bytes(self):
        native=parity.os.read;changed=[False];target=self.pack/'positive.json';other=b'other actor bytes'
        def read(fd,size):
            raw=native(fd,size)
            if raw and not changed[0]:changed[0]=True;target.write_bytes(other)
            return raw
        with patch.object(parity.os,'read',side_effect=read):
            with self.assertRaisesRegex(ValueError,'changed_during_read'):parity.receipt_bytes(self.pack,'positive.json')
        self.assertEqual(target.read_bytes(),other)

    def test_runtime_change_during_audit_is_not_a_successful_verification(self):
        native=parity.receipt_bytes;changed=[False]
        def read(*args):raw=native(*args);changed[0]=True;return raw
        with patch.object(parity,'source_digest',side_effect=lambda:'0'*64 if changed[0] else self.runtime),patch.object(parity,'receipt_bytes',side_effect=read):
            with self.assertRaisesRegex(ValueError,'functional_parity_program_changed'):parity.audit(self.root)

    def test_ambiguous_or_oversize_matrix_cannot_supply_verification_claims(self):
        path=self.root/'config/axiom-v2-functional-parity.json';original=path.read_bytes()
        path.write_bytes(b'{"schema_version":1,'+original[1:])
        with self.assertRaisesRegex(ValueError,'duplicate_result_input_key'):parity.audit(self.root)
        with path.open('wb') as stream:stream.truncate(parity.MAX_MATRIX+1)
        with self.assertRaisesRegex(ValueError,'regular_bounded_file_required'):parity.audit(self.root)

    def test_matrix_symlink_and_direct_metadata_name_traversal_are_rejected(self):
        path=self.root/'config/axiom-v2-functional-parity.json';other=self.base/'other-matrix.json';other.write_bytes(path.read_bytes())
        path.unlink();path.symlink_to(other)
        with self.assertRaisesRegex(ValueError,'missing_or_unsafe'):parity.audit(self.root)
        with self.assertRaisesRegex(ValueError,'unsafe_functional_parity_metadata_name'):
            parity.metadata_bytes(self.pack,'../other-matrix.json',parity.MAX_MATRIX)
