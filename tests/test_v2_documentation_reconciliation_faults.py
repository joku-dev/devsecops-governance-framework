"""Whole native partial/close errors and separate host release on capture abort."""
import copy,hashlib,json,os,unittest
from unittest.mock import patch
import test_v2_documentation_reconciliation_capture as captured
from test_v2_documentation_reconciliation_capture import Q,NativeIO,NativeGit,Record,execute
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.synthetic_lifecycle_io import ReplayIO
from lib.documentation_reconciliation_git import ReplayGit
from lib.documentation_reconciliation_git import signal_diagnostic

class AppendFailures(unittest.TestCase):
    fixture=captured.CapturedOriginal.fixture
    capture=captured.CapturedOriginal.capture
    def setUp(self):
        captured.CapturedOriginal.setUp(self);previous=os.umask(0o077);self.addCleanup(os.umask,previous)

    def test_native_original_partial_close_keeps_opaque_prefix_and_no_false_full_write(self):
        root,args=self.fixture(functional=False);target=root/'caller-output';target.write_bytes(b'\xffold')
        kernel,inputs,events,blobs=self.capture(root,[*args,'--github-output',str(target)],mode='selected-files',expected=1,fault='partial-close',retain='selected-files-append-partial-close')
        self.assertEqual(target.read_bytes(),b'\xffoldreq');self.assertEqual(kernel['kernel_exception']['type'],'OSError')
        self.assertTrue(all(session.stream.closed for session in inputs.documentation_append_sessions))

    def test_native_original_full_bytes_close_failure_retains_error_and_no_success_claim(self):
        root,args=self.fixture(functional=False);target=root/'caller-output'
        kernel,inputs,events,blobs=self.capture(root,[*args,'--github-output',str(target)],mode='selected-files',expected=1,fault='full-close',retain='selected-files-append-full-close')
        self.assertEqual(target.read_bytes(),b'required=false\n');self.assertEqual(kernel['kernel_exception']['type'],'OSError')
        self.assertTrue(all(session.stream.closed for session in inputs.documentation_append_sessions))

    def test_journal_failure_after_buffered_write_releases_owned_stream_without_original_verdict(self):
        root,args=self.fixture(functional=False);target=root/'caller-output';private=self.parent/'abort-private';private.mkdir(mode=0o700)
        record=Record(private/'records',{'prototype':True},{'not_product_acceptance':True});record.append({'kind':'execution-intent'})
        inputs=NativeIO(record,mode='selected-files',cwd=str(root),private_state=private,product_root=Q)
        append=record.append;last={}
        def fail_return(value):
            if value.get('kind')=='intent':last.clear();last.update(value)
            if value.get('kind')=='returned' and last.get('action')=='documentation-native-append' and last.get('arguments',{}).get('stage')=='write':
                raise InputAdmissionError('injected append journal failure after buffered write')
            return append(value)
        with patch.object(record,'append',side_effect=fail_return):
            with self.assertRaises(InputAdmissionError):execute(str(root),str(root),[*args,'--github-output',str(target)],inputs,NativeGit)
        self.assertTrue(record.capture_incomplete);self.assertEqual(target.read_bytes(),b'required=false\n')
        self.assertTrue(all(session.stream.closed for session in inputs.documentation_append_sessions))

    def test_resealed_native_append_stage_descriptor_payload_and_close_mutations_rejected(self):
        root,args=self.fixture(functional=False);target=root/'caller-output';args=[*args,'--github-output',str(target)]
        kernel,inputs,events,blobs=self.capture(root,args,mode='selected-files')
        for attack in ('result-bool','descriptor-bool','payload','closed','changed-prefix'):
            altered=copy.deepcopy(events);data=dict(blobs)
            stage='open' if attack=='descriptor-bool' else 'close' if attack in ('closed','changed-prefix') else 'write'
            position=next(i for i,row in enumerate(altered) if row.get('action')=='documentation-native-append' and row['arguments']['stage']==stage)
            returned=altered[position+1];wire=json.loads(data[returned['value']['sha256']])
            def store(raw):
                sha=hashlib.sha256(raw).hexdigest();data[sha]=raw;return {'sha256':sha,'bytes':len(raw)}
            if attack=='result-bool':wire['result']=True
            elif attack=='descriptor-bool':wire['opened_file']['identity'][0]=True
            elif attack=='payload':altered[position]['arguments']['payload']=store(b'required=true\n')
            elif attack=='closed':wire['closed']=False
            else:wire['snapshot']['content']=store(b'forged original prefix\n')
            returned['value']=store((json.dumps(wire,separators=(',',':'))+'\n').encode())
            replay=ReplayIO(altered,lambda ref:data[ref['sha256']],'selected-files',str(root))
            with patch('os.open',side_effect=AssertionError('No native replay')):
                with self.assertRaises(IntegrityError,msg=attack):execute(str(root),str(root),args,replay,ReplayGit)

    def test_whole_original_real_git_signal_errors_and_source_deleted_replay_both_modes(self):
        for kind in ('SIGTERM','SIGUSR1','SIGKILL'):
            for mode in ('private-candidate','selected-files'):
                with self.subTest(signal=kind,mode=mode):
                    root,args=self.fixture()
                    kernel,inputs,events,blobs=self.capture(root,args,mode=mode,expected=1,fault='git-signal-'+kind)
                    self.assertEqual(kernel['kernel_exception']['type'],'CalledProcessError')
                    self.assertIn('Signals.'+kind,kernel['kernel_exception']['message'])
                    self.assertFalse(inputs.files)

    def test_signal_context_full_original_diagnostics_and_resealed_invalid_variants_rejected(self):
        import platform,signal
        from lib.documentation_reconciliation_git import value,SIGNALS
        self.assertEqual(SIGNALS[platform.system()],{item.value:item.name for item in signal.Signals})
        command=['git','diff','--name-only','--diff-filter=ACDMR','base..merge']
        for system,number,name in (('Darwin',30,'SIGUSR1'),('Linux',10,'SIGUSR1'),('Linux',33,None)):
            context={'implementation':'cpython','version':[3,12,3],'system':system}
            label='unknown signal 33' if name is None else f'<Signals.{name}: {number}>'
            self.assertEqual(signal_diagnostic(context,-number,command),f"Command '{command}' died with {label}.")
        root,args=self.fixture();kernel,inputs,events,blobs=self.capture(root,args,expected=1,fault='git-signal-SIGTERM')
        position=next(i for i,row in enumerate(events) if row.get('action')=='documentation-local-git');intent=events[position]['arguments'];wire=json.loads(blobs[events[position+1]['value']['sha256']])
        for attack in ('label','missing-context','system','boolean-version','signal-range','positive-context'):
            altered=copy.deepcopy(wire)
            if attack=='label':altered['return_error']['message']=f"Command '{intent['command']}' died with arbitrary injected signal label."
            elif attack=='missing-context':altered['signal_context']=None
            elif attack=='system':altered['signal_context']['system']='arbitrary'
            elif attack=='boolean-version':altered['signal_context']['version'][0]=True
            elif attack=='signal-range':altered['returncode']=altered['observation']['returncode']=-255
            else:altered['returncode']=altered['observation']['returncode']=1;altered['return_error']['message']=f"Command '{intent['command']}' returned non-zero exit status 1."
            with self.assertRaises(IntegrityError,msg=attack):value(altered,intent,lambda ref:blobs[ref['sha256']])

if __name__=='__main__':os.umask(0o077);unittest.main(verbosity=2)
