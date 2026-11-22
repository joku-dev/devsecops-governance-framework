"""Whole original vs durable capture, exact Git/File epochs and inert replay."""
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr
import copy,io,json,os,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.self_security_publication_ports import execute,NativeIO,Record,read_record,ledger,transaction_name
from lib.self_security_publication_io import ReplaySelfSecurityIO
from lib.requirement_validation_replay import IntegrityError
from test_v2_self_security_publication import ORIGINAL
import test_v2_self_security_publication_native as reference


class WholeSelfSecurityPublicationExecution(unittest.TestCase):
    def setUp(self):self.case=reference.SelfSecurityNativeFixture();self.case.setUp();self.addCleanup(self.case.doCleanups)
    def compare(self,kind='normal',invocation='main'):
        c=self.case;values=[];actual=record=None
        for side in ('original','record'):
            root,origin,tools,output,summary,env=c.fixture(side,kind);out,err=io.StringIO(),io.StringIO();returned=error=signal=None
            with patch.dict(os.environ,env,clear=True),redirect_stdout(out),redirect_stderr(err):
                if side=='original':
                    ns={'__name__':'immutable_self_security_publisher','__file__':str(root/'scripts/publish_self_security_refresh.py')};exec(compile(ORIGINAL.read_bytes(),'immutable_self_security_publisher','exec'),ns);ns['ROOT']=root
                    try:returned=ns['main']() if invocation=='main' else ns['publish'](root,repository='owner/repo',run_id='123',attempt='2')
                    except SystemExit as caught:signal={'type':'SystemExit','value':caught.code}
                    except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
                else:
                    private=c.base/('record-state-'+str(c.serial));private.mkdir(mode=0o700);request={'source_label':str(root),'cwd_label':str(ROOT),'subject':{'repository':'owner/repo','run_id':'123','attempt':'2'},'environment':{k:env[k] for k in ('GITHUB_REF','GITHUB_REPOSITORY','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_OUTPUT','GITHUB_STEP_SUMMARY')},'provider_executable':str(tools/'gh'),'local_origin_root':str(c.base),'private_state_label':str(private),'invocation':invocation};record=Record(private/'records',request,{'prototype':'whole original self security program'});record.append({'kind':'execution-intent','request':request});owner=NativeIO(record,source=str(root),mode='selected-files',cwd=str(ROOT),private_state=private,product_root=ROOT,ledger=ledger(str(root)),transaction_name=transaction_name);actual=execute(request,owner,native_environment=env);returned,error,signal=actual['return_value'],actual['kernel_exception'],actual['original_exit_signal'];out.write(actual['stdout']);err.write(actual['stderr']);record.finish('complete',{'exit_code':actual['exit_code'],'kernel_result':actual},owner.touched)
            values.append({'returned':returned,'error':error,'signal':signal,'stdout':out.getvalue(),'stderr':err.getvalue(),'files':c.snapshot(root),'head':c.git(root,'rev-parse','HEAD'),'branch':c.git(root,'branch','--show-current'),'refs':c.git(origin,'show-ref','--heads'),'staged':c.git(root,'diff','--cached','--name-only','-z'),'calls':(tools/'calls.jsonl').read_bytes() if (tools/'calls.jsonl').exists() else b'','output':output.read_bytes(),'summary':summary.read_bytes()})
        self.assertEqual(values[0],values[1],(kind,values[0]['error'],values[1]['error']));request,_,retained,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};moved=c.base.with_name(c.base.name+'-absent-before-replay');c.base.rename(moved)
        try:
            replay=ReplaySelfSecurityIO(events,lambda ref:cache[ref['sha256']],'selected-files',request['cwd_label'],source=request['source_label'],ledger=ledger(request['source_label']),transaction_name=transaction_name)
            with patch('subprocess.Popen',side_effect=AssertionError('No Git or provider')),patch('os.open',side_effect=AssertionError('No Source/export')):again=execute(request,replay);replay.finish()
            self.assertEqual(again,actual);self.assertEqual(replay.touched,retained['touched_files'])
        finally:moved.rename(c.base)
        for name,raw in cache.items():self.assertEqual(blob({'sha256':name,'bytes':len(raw)}),raw)
        self.assertTrue(closed());return actual,events,cache,request
    def test_full_original_capture_and_replay_include_reset_clean_switch_and_two_native_report_writes(self):
        value,_,_,_=self.compare();self.assertEqual(value['exit_code'],0);self.assertEqual(len(value['known_source_worktree_transitions']),6);self.assertEqual(len(value['pipeline_append_observations']),6)
    def test_existing_PR_restore_and_merge_have_their_own_observed_source_epochs(self):
        value,_,_,_=self.compare('existing');self.assertEqual(value['exit_code'],0);self.assertEqual(len(value['known_source_worktree_transitions']),8)
    def test_advanced_main_is_actually_merged_then_source_reports_restored_and_inertly_replayed(self):
        value,_,_,_=self.compare('existing-advanced');self.assertEqual(value['exit_code'],0);self.assertEqual(len(value['known_source_worktree_transitions']),8);self.assertTrue(any('merge' in v['original_arguments'] for v in value['native_process_observations']))
    def test_timestamp_only_main_and_direct_publish_require_no_source_mutation_or_POST(self):
        value,_,_,_=self.compare('timestamp-only');self.assertEqual(value['exit_code'],0);self.assertEqual(value['known_source_worktree_transitions'],[])
    def test_partial_POST_and_later_dispatch_failure_replay_preserves_pushed_worktree(self):
        value,_,_,_=self.compare('fail-dispatch');self.assertEqual(value['kernel_exception']['type'],'CalledProcessError');self.assertEqual(value['pipeline_append_observations'],[])
    def test_changed_epoch_binding_is_rejected_without_repeating_a_write(self):
        value,events,cache,request=self.compare();changed=copy.deepcopy(events);row=next(x for x in changed if x.get('kind')=='intent' and x.get('action')=='self-security-worktree-after');row['arguments']['epoch']=9
        replay=ReplaySelfSecurityIO(changed,lambda ref:cache[ref['sha256']],'selected-files',request['cwd_label'],source=request['source_label'],ledger=ledger(request['source_label']),transaction_name=transaction_name)
        with patch('subprocess.Popen',side_effect=AssertionError('No repeated process')),patch('os.open',side_effect=AssertionError('No source or output')):
            with self.assertRaisesRegex(IntegrityError,'intent_changed'):execute(request,replay)
