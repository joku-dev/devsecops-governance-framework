"""Whole original publisher vs durable capture and inert replay, using actual isolated Git.

No real provider write is made. Portfolio/other domain cases do not invoke any
lifecycle gate; real synthetic/live gate integration is tested separately.
"""
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr
import io,json,hashlib,os,shutil,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_operational_publisher_native as reference
from jsonschema import Draft202012Validator
from lib.operational_publication_ports import execute
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.pilot_run_intake_io import ReplayRunIO
from lib.pilot_run_intake_ports import ledger,transaction_name
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.retained_argparse import capture_context

class WholePublisherRecordExecution(unittest.TestCase):
    def setUp(self):
        self.case=reference.WholeOperationalPublisherNative();self.case.setUp();self.addCleanup(self.case.doCleanups)
    def compare(self,kind='normal',scope='portfolio',invocation='publish',argv=None):
        c=self.case;results=[];actual=None;record=None
        for side in ('original','record'):
            root,origin,tools,output,summary,env=c.fixture(side)
            selected={'portfolio':'generated/reports/portfolio-onboarding-status.json','devsecops':'status/repository-results-index.json','architecture':'status/architecture-results-index.json','typed-evidence':'status/typed-evidence-results-index.json'}[scope]
            if kind!='no-change':(root/selected).write_text('{"explicit":"recorded change"}\n')
            if kind in ('fail-pr','fail-dispatch','malformed','empty'):(tools/'mode').write_text(kind)
            if kind=='out-of-scope':(root/'README.md').write_text('unselected source change\n')
            if kind=='symlink':(root/selected).unlink();(root/selected).symlink_to(root/'README.md')
            if kind=='append-only':(root/'status/results/historical.json').write_text('{"changed":true}\n')
            if kind=='new-ledger':(root/'status/results/new.json').write_text('{"new":true}\n')
            if kind=='new-output-file':output.unlink()
            if kind=='missing-output-parent':output=c.base/'explicit-missing-output-parent'/'output';env['GITHUB_OUTPUT']=str(output)
            if kind=='output-directory':output=c.base/'explicit-original-and-record-output-directory';output.mkdir(mode=0o700,exist_ok=True);env['GITHUB_OUTPUT']=str(output)
            if kind=='same-output':summary=output;env['GITHUB_STEP_SUMMARY']=str(summary)
            if kind in ('opaque-stdout','opaque-stderr','unicode-output','surrogate-output'):
                p=tools/'gh';text=p.read_text();condition="if command[3].endswith('/pulls'):\n"
                if kind=='opaque-stdout':text=text.replace(condition,"if command[3].endswith('/pulls'):\n sys.stdout.buffer.write(bytes([255]));sys.exit(0)\n",1)
                elif kind=='opaque-stderr':text=text.replace(condition,"if command[3].endswith('/pulls'):\n sys.stderr.buffer.write(bytes([255]))\n",1)
                elif kind=='unicode-output':text=text.replace("/pull/123'","/pull/123?label=\\u00e4'")
                else:text=text.replace("/pull/123'","/pull/123?label=\\ud800'")
                p.write_text(text)
            out,err=io.StringIO(),io.StringIO();returned=error=signal=None
            args=['--scope',scope] if argv is None else argv
            with patch.dict(os.environ,env,clear=True),redirect_stdout(out),redirect_stderr(err):
                if side=='original':
                    old=c.old(root)
                    try:
                        if invocation=='main':
                            with patch.object(sys,'argv',['publish_operational_update.py',*args]):returned=old['main']()
                        else:returned=old['publish'](root,scope=scope,repository=reference.REPOSITORY,run_id=reference.RUN,attempt=reference.ATTEMPT)
                    except SystemExit as caught:signal={'type':'SystemExit','value':caught.code}
                    except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
                else:
                    selected_env={key:env[key] for key in ('GITHUB_REF','GITHUB_REPOSITORY','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_OUTPUT','GITHUB_STEP_SUMMARY') if key in env}
                    request={'local_origin_root':str(c.base),'source_label':str(root),'cwd_label':str(ROOT),'subject':{'scope':scope,'repository':reference.REPOSITORY,'run_id':reference.RUN,'attempt':reference.ATTEMPT},'argv':args,'invocation':invocation,'environment':selected_env,'parser_context':capture_context(),'provider_executable':str(tools/'gh'),'temporary_parent':str(c.base/'temporary')}
                    private=c.base/('record-state-'+str(c.serial));private.mkdir(mode=0o700);record=Record(private/'records',request,{'prototype':'whole original publisher development comparison'});record.append({'kind':'execution-intent','request':request});owner=NativeRunIO(record,mode='private-candidate',cwd=request['cwd_label'],private_state=private,ledger=ledger(str(root)),transaction_name=transaction_name)
                    actual=execute(request,owner,validator_class=Draft202012Validator,native_environment=env,local_origin_root=c.base)
                    returned,error,signal=actual['return_value'],actual['kernel_exception'],actual['original_exit_signal'];out.write(actual['stdout']);err.write(actual['stderr'])
                    record.finish('complete',{'exit_code':actual['exit_code'],'kernel_result':actual},owner.touched)
            results.append({'returned':returned,'exception':error,'signal':signal,'stdout':out.getvalue(),'stderr':err.getvalue(),'source':c.snapshot(root),'branch':c.git(root,'branch','--show-current'),'head':c.git(root,'rev-parse','HEAD'),'remote':c.git(origin,'show-ref','--heads'),'staged':c.git(root,'diff','--cached','--name-only','-z'),'calls':(tools/'calls.jsonl').read_bytes() if (tools/'calls.jsonl').exists() else b'','output':output.read_bytes() if output.is_file() else 'directory' if output.is_dir() else None,'summary':summary.read_bytes() if summary.is_file() else 'directory' if summary.is_dir() else None,'output_mode':output.stat().st_mode&0o777 if output.exists() else None,'summary_mode':summary.stat().st_mode&0o777 if summary.exists() else None})
        self.assertEqual(results[0],results[1],(kind,scope,results[0].get('exception'),results[1].get('exception')))
        request,_,retained,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
        def inert(ref):
            raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return raw
        # Remove source Git, tools, outputs and the on-disk record together.
        moved=c.base.with_name(c.base.name+'-unavailable-for-pure-replay');c.base.rename(moved)
        try:
            replay=ReplayRunIO(events,inert,'private-candidate',request['cwd_label'],ledger=ledger(request['source_label']),transaction_name=transaction_name)
            with patch('subprocess.Popen',side_effect=AssertionError('No Git/POST')),patch('os.open',side_effect=AssertionError('No filesystem open')),patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No temporary writer')):
                pure=execute(request,replay,validator_class=Draft202012Validator);replay.finish()
            self.assertEqual(pure,actual);self.assertEqual(seen,set(cache))
        finally:moved.rename(c.base)
        for name,raw in cache.items():blob({'sha256':name,'bytes':len(raw)})
        self.assertTrue(closed());return actual,events,cache
    def test_entire_original_branch_commit_push_POST_dispatch_append_and_source_free_replay(self):
        result,_,_=self.compare();self.assertEqual(result['exit_code'],0);self.assertEqual(len(result['pipeline_append_observations']),6)
    def test_original_failure_after_successful_push_is_replayed_without_another_push(self):
        result,_,_=self.compare('fail-pr');self.assertEqual(result['kernel_exception']['type'],'CalledProcessError');self.assertEqual(result['pipeline_append_observations'],[])
    def test_original_later_dispatch_failure_retains_both_completed_CI_output_appends(self):
        result,_,_=self.compare('fail-dispatch');self.assertEqual(result['exit_code'],1);self.assertEqual(len(result['pipeline_append_observations']),6)
    def test_no_change_preserves_no_mutation_and_original_message(self):
        result,_,_=self.compare('no-change');self.assertEqual(result['native_process_operation_count'],2);self.assertEqual(result['stdout'],'No operational changes to propose.\n')
    def test_original_symlink_rejection_is_a_retained_verdict_not_a_native_writer(self):
        result,_,_=self.compare('symlink');self.assertEqual(result['kernel_exception']['type'],'ValueError')
    def test_original_out_of_scope_rejection_preserves_both_streams(self):
        result,_,_=self.compare('out-of-scope');self.assertEqual(result['kernel_exception']['type'],'ValueError')
    def test_original_append_only_rejection_and_binary_cat_file_result(self):
        result,_,_=self.compare('append-only',scope='devsecops');self.assertEqual(result['kernel_exception']['type'],'ValueError')
    def test_original_new_ledger_file_is_committed_then_inertly_replayed(self):
        result,_,_=self.compare('new-ledger',scope='devsecops');self.assertEqual(result['exit_code'],0)
    def test_whole_main_uses_the_original_parser_and_environment(self):
        result,_,_=self.compare(invocation='main');self.assertEqual(result['return_value'],0)
    def test_whole_main_help_without_native_operations(self):
        result,_,_=self.compare(invocation='main',argv=['--help']);self.assertEqual(result['original_exit_signal'],{'type':'SystemExit','value':0});self.assertEqual(result['native_process_operation_count'],0)
    def test_original_missing_output_parent_fails_after_PR_and_never_dispatches(self):
        value,_,_=self.compare('missing-output-parent');self.assertEqual(value['kernel_exception']['type'],'FileNotFoundError');self.assertEqual(len([v for v in value['native_process_observations'] if v['kind']=='post']),1)
    def test_original_directory_output_failure_is_a_retained_error(self):
        value,_,_=self.compare('output-directory');self.assertEqual(value['kernel_exception']['type'],'IsADirectoryError')
    def test_original_both_CI_outputs_may_select_the_same_owned_file(self):
        value,_,_=self.compare('same-output');self.assertEqual(value['exit_code'],0);self.assertEqual(len(value['pipeline_append_observations']),6)
    def test_original_unicode_pipeline_output_preserves_UTF8_bytes(self):
        value,_,_=self.compare('unicode-output');self.assertEqual(value['exit_code'],0)
    def test_original_surrogate_pipeline_write_error_is_not_an_unobserved_native_effect(self):
        value,_,_=self.compare('surrogate-output');self.assertEqual(value['kernel_exception']['type'],'UnicodeEncodeError')
    def test_original_opaque_stdout_and_stderr_decode_failures_keep_raw_blobs(self):
        for kind in ('opaque-stdout','opaque-stderr'):
            # Each comparison creates fresh source/origin/state names.
            if kind=='opaque-stderr':self.case.serial+=1
            value,_,_=self.compare(kind);self.assertEqual(value['kernel_exception']['type'],'UnicodeDecodeError')
    def test_other_non_lifecycle_scopes_keep_their_whole_native_flow(self):
        for i,scope in enumerate(('architecture','typed-evidence')):
            self.case.serial+=i
            value,_,_=self.compare(scope=scope);self.assertEqual(value['exit_code'],0)
    def test_original_new_pipeline_output_file_creation_preserves_bytes_and_native_mode(self):
        value,_,_=self.compare('new-output-file');self.assertEqual(value['exit_code'],0)
