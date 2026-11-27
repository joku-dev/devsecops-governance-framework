"""Whole typed publisher native capture vs original and closed source-free replay."""
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr
import io,json,os,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from jsonschema import Draft202012Validator
from lib.typed_publication_ports import execute
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.pilot_run_intake_io import ReplayRunIO
from lib.pilot_run_intake_ports import ledger,transaction_name
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode
from lib.providers.retained_argparse import capture_context
import test_v2_typed_publication_native as reference


class WholeTypedPublicationExecution(unittest.TestCase):
    def setUp(self):
        self.typed=reference.WholeTypedPublisherNative();self.typed.setUp();self.addCleanup(self.typed.doCleanups);self.case=self.typed.case
    def compare(self,kind='normal',invocation='main',argv=None):
        c=self.case;values=[];record=actual=None
        for side in ('original','record'):
            root,origin,tools,output,summary,env=c.fixture(side)
            if kind!='no-change':self.typed.candidate(root)
            if kind in ('fail-pr','fail-dispatch'):(tools/'mode').write_text(kind)
            out,err=io.StringIO(),io.StringIO();returned=error=signal=None;args=['--scope','typed-evidence'] if argv is None else argv
            with patch.dict(os.environ,env,clear=True),redirect_stdout(out),redirect_stderr(err):
                if side=='original':
                    wrapper,publisher=reference.original(root)
                    try:
                        if invocation=='main':
                            with patch.object(sys,'argv',['publish_typed_evidence_assurance_update.py',*args]):returned=wrapper['main']()
                        elif invocation=='configure':returned=wrapper['configure']()
                        else:wrapper['configure']();returned=publisher.publish(root,scope='typed-evidence',repository='example/project',run_id='42',attempt='1')
                    except SystemExit as caught:signal={'type':'SystemExit','value':caught.code}
                    except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
                    rules={'ledgers':list(publisher.LEDGERS),'scopes':{k:list(v) for k,v in publisher.SCOPES.items()}}
                else:
                    request={'local_origin_root':str(c.base),'source_label':str(root),'cwd_label':str(ROOT),'subject':{'scope':'typed-evidence','repository':'example/project','run_id':'42','attempt':'1'},'argv':args,'invocation':invocation,'environment':{k:env[k] for k in ('GITHUB_REF','GITHUB_REPOSITORY','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_OUTPUT','GITHUB_STEP_SUMMARY')},'parser_context':capture_context(),'provider_executable':str(tools/'gh'),'temporary_parent':str(c.base/'temporary')}
                    private=c.base/('record-state-'+str(c.serial));private.mkdir(mode=0o700);record=Record(private/'records',request,{'prototype':'entire original typed-evidence publisher'});record.append({'kind':'execution-intent','request':request});owner=NativeRunIO(record,mode='private-candidate',cwd=request['cwd_label'],private_state=private,ledger=ledger(str(root)),transaction_name=transaction_name)
                    actual=execute(request,owner,validator_class=Draft202012Validator,native_environment=env);returned,error,signal=actual['return_value'],actual['kernel_exception'],actual['original_exit_signal'];rules=actual['publisher_scope_rules'];out.write(actual['stdout']);err.write(actual['stderr']);record.finish('complete',{'exit_code':actual['exit_code'],'kernel_result':actual},owner.touched)
            values.append({'returned':returned,'error':error,'signal':signal,'stdout':out.getvalue(),'stderr':err.getvalue(),'rules':rules,'files':c.snapshot(root),'head':c.git(root,'rev-parse','HEAD'),'branch':c.git(root,'branch','--show-current'),'refs':c.git(origin,'show-ref','--heads'),'staged':c.git(root,'diff','--cached','--name-only','-z'),'calls':(tools/'calls.jsonl').read_bytes() if (tools/'calls.jsonl').exists() else b'','output':output.read_bytes(),'summary':summary.read_bytes()})
        self.assertEqual(values[0],values[1]);request,_,retained,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};moved=c.base.with_name(c.base.name+'-absent-before-replay');c.base.rename(moved)
        try:
            replay=ReplayRunIO(events,lambda ref:cache[ref['sha256']],'private-candidate',request['cwd_label'],ledger=ledger(request['source_label']),transaction_name=transaction_name)
            with patch('subprocess.Popen',side_effect=AssertionError('No Git or provider')),patch('os.open',side_effect=AssertionError('No source or export')):again=execute(request,replay,validator_class=Draft202012Validator);replay.finish()
            self.assertEqual(again,actual)
        finally:moved.rename(c.base)
        for name,raw in cache.items():self.assertEqual(blob({'sha256':name,'bytes':len(raw)}),raw)
        self.assertTrue(closed());return actual
    def test_entire_original_typed_publisher_processes_and_scope_state_replay_without_source(self):self.assertEqual(self.compare()['exit_code'],0)
    def test_original_configuration_helper_is_observable_without_any_native_effect(self):
        result=self.compare(invocation='configure');self.assertEqual(result['exit_code'],0);self.assertEqual(result['native_process_operation_count'],0);self.assertEqual(result['publisher_scope_rules']['ledgers'][-3:],list(reference.ADDITIONAL_LEDGERS))
    def test_whole_main_help_keeps_configure_before_parser_exit_and_no_native_process(self):
        result=self.compare(argv=['--help']);self.assertEqual(result['original_exit_signal'],{'type':'SystemExit','value':0});self.assertEqual(result['native_process_operation_count'],0)
    def test_original_no_change_and_configured_publish_API_replay(self):
        self.assertEqual(self.compare('no-change')['exit_code'],0);self.case.serial+=1;self.assertEqual(self.compare(invocation='publish')['exit_code'],0)
    def test_original_partial_POST_failure_replays_without_another_push_or_POST(self):
        result=self.compare('fail-pr');self.assertEqual(result['kernel_exception']['type'],'CalledProcessError');self.assertTrue(any(v['original_arguments'][1]=='push' for v in result['native_process_observations']))
