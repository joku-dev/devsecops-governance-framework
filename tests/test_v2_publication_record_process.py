"""Closed process wires reject semantic tampering, even after ordinary JSON resealing."""
from copy import deepcopy
from pathlib import Path,PurePosixPath
import hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_publication_record_execution as reference
from lib.operational_publication_process import value
from lib.providers.operational_publication_protocol import LegacyPublisherProtocol
from lib.requirement_validation_replay import IntegrityError
class WholePublisherProcessWire(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        case=reference.WholePublisherRecordExecution();case.setUp()
        try:result,events,cls.cache=case.compare()
        finally:case.doCleanups()
        cls.wires=[]
        for i,event in enumerate(events):
            if event.get('kind')=='intent' and event.get('action')=='operational-publisher-process':
                row=events[i+1];cls.wires.append(json.loads(cls.cache[row['value']['sha256']]))
    def blob(self,ref):
        if type(ref) is not dict or set(ref)!={'sha256','bytes'} or type(ref['bytes']) is not int or ref['sha256'] not in self.cache:raise IntegrityError('test_retained_blob_changed')
        raw=self.cache[ref['sha256']]
        if len(raw)!=ref['bytes'] or hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise IntegrityError('test_retained_blob_binding_changed')
        return raw
    def chosen(self,post=False):
        wire=deepcopy(next(w for w in self.wires if (w['specification']['kind']=='post')==post));spec=deepcopy(wire['specification'])
        cwd=next(w['native_working_directory'] for w in self.wires if w['specification']['kind']=='post')
        profile=LegacyPublisherProtocol(spec['source_root'],scope='portfolio',repository='example/project',run_id='42',attempt='1',cwd=cwd,local_origin_root=str(PurePosixPath(spec['source_root']).parent))
        return wire,spec,profile
    def reject(self,edit,post=False):
        wire,spec,profile=self.chosen(post);edit(wire)
        with self.assertRaises(IntegrityError):value(wire,spec,profile,self.blob)
    def test_intact_raw_original_process_results_validate_after_source_and_tools_removed(self):
        for post in (False,True):
            wire,spec,profile=self.chosen(post);self.assertEqual(value(wire,spec,profile,self.blob).returncode,0)
    def test_changed_original_or_actual_arguments_rejected(self):
        self.reject(lambda w:w['specification']['original_arguments'].append('--force'))
        self.reject(lambda w:w['transport']['actual_arguments'].append('--force'))
    def test_replaced_source_program_or_source_Git_identity_rejected(self):
        self.reject(lambda w:w['transport']['program'].update(resolved=w['specification']['source_root']+'/unselected-tool'))
        self.reject(lambda w:w['Git_after']['identity'].__setitem__(1,w['Git_after']['identity'][1]+1))
    def test_forged_terminal_signal_or_original_error_rejected(self):
        self.reject(lambda w:w['transport']['observation'].update(started=False))
        self.reject(lambda w:w.update(original_error={'type':'CalledProcessError','message':'forged'}))
        self.reject(lambda w:w.update(signal_context={'unselected':'context'}))
    def test_false_OS_isolation_and_external_completion_proof_rejected(self):
        self.reject(lambda w:w['transport']['observation'].update(OS_network_or_process_tree_isolation_attested=True))
        self.reject(lambda w:w['effect_claim'].update(external_completion_independently_proven=True))
    def test_remote_and_working_directory_cannot_be_rebound(self):
        self.reject(lambda w:w['remote_binding'].update(push_url='/outside-selected-test-root/origin.git'),post=True)
        self.reject(lambda w:w.update(native_working_directory='/unselected-working-directory'),post=True)
        self.reject(lambda w:w.update(remote_binding=None),post=True)
    def test_POST_stdin_byte_reference_and_payload_bound_to_original_call(self):
        self.reject(lambda w:w['stdin'].update(bytes=True),post=True)
        self.reject(lambda w:w['specification'].update(input='{}'),post=True)
    def test_bool_as_stream_length_and_unchecked_text_codec_are_not_accepted(self):
        self.reject(lambda w:w['transport']['stdout'].update(bytes=True))
        self.reject(lambda w:w.update(effective_encoding='unknown-codec-publisher'))
