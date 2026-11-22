"""Whole immutable original publisher and recorded real synthetic gates, no gate doubles."""
from pathlib import Path
from unittest.mock import patch
import json,os,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_operational_publisher_integrated as original
from jsonschema import Draft202012Validator
from lib.operational_publication_ports import execute
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.pilot_run_intake_io import ReplayRunIO
from lib.pilot_run_intake_ports import ledger,transaction_name
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.retained_argparse import capture_context
class WholePublisherRecordedRealGates(unittest.TestCase):
    def setUp(self):
        self.case=original.WholeOperationalPublisherIntegrated();self.case.setUp();self.addCleanup(self.case.doCleanups)
    def compare(self,damage=False):
        c=self.case;p=c.root/'status/governance-lifecycle-overview.json';p.write_bytes(p.read_bytes()+b'\n')
        if damage:
            p=c.root/'generated/reports/governance-lifecycle-pilot.md';p.write_bytes(p.read_bytes()+b'wrong report\n')
        starting=original.snapshot(c.root)
        old=subprocess.run([sys.executable,'-B','-c',original.WRAPPER,str(c.root)],env=c.env,cwd=c.root,capture_output=True,timeout=300);self.assertEqual(old.returncode,0,old.stderr[-4000:]);parts=old.stdout.rsplit(b'\nAXIOM_ORIGINAL_RESULT=',1);self.assertEqual(len(parts),2);expected=json.loads(parts[1]);source=original.snapshot(c.root);branch=c.git('branch','--show-current');head=c.git('rev-parse','HEAD');calls=c.calls.read_bytes() if c.calls.exists() else b'';output=c.output.read_bytes()
        c.git('checkout','--force','main');c.git('reset','--hard',c.initial)
        if not damage:
            c.git('branch','-D','automation/lifecycle-synthetic/42-1');subprocess.run(['git','--git-dir',str(c.origin),'update-ref','-d','refs/heads/automation/lifecycle-synthetic/42-1'],check=True,env=c.env,capture_output=True)
        for name,(raw,mode) in starting.items():
            p=c.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(mode)
        c.calls.unlink(missing_ok=True);c.output.write_bytes(b'earlier=1\n')
        request={'source_label':str(c.root),'cwd_label':str(c.root),'subject':{'scope':'lifecycle-synthetic','repository':'example/project','run_id':'42','attempt':'1'},'argv':[],
            'invocation':'publish','environment':{'GITHUB_OUTPUT':str(c.output)},'parser_context':capture_context(),'provider_executable':str(c.tool),'temporary_parent':str(c.case.temporary),'local_origin_root':str(c.base)}
        record=Record(c.case.private/'real-complete-publisher-records',request,{'prototype':'whole recorded original and real synthetic gates'});record.append({'kind':'execution-intent','request':request});owner=NativeRunIO(record,mode='private-candidate',cwd=request['cwd_label'],private_state=c.case.private,ledger=ledger(str(c.root)),transaction_name=transaction_name)
        actual=execute(request,owner,validator_class=Draft202012Validator,native_environment=c.env)
        self.assertEqual({'return_value':actual['return_value'],'kernel_exception':actual['kernel_exception']},expected);self.assertEqual(actual['stdout'].encode(),parts[0]);self.assertEqual(actual['stderr'].encode(),old.stderr)
        self.assertEqual(original.snapshot(c.root),source);self.assertEqual(c.git('branch','--show-current'),branch);self.assertEqual(c.git('rev-parse','HEAD'),head);self.assertEqual(c.calls.read_bytes() if c.calls.exists() else b'',calls);self.assertEqual(c.output.read_bytes(),output)
        record.finish('complete',{'exit_code':actual['exit_code'],'kernel_result':actual},owner.touched);_,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};moved=c.base.with_name(c.base.name+'-source-free');c.base.rename(moved)
        try:
            replay=ReplayRunIO(events,lambda ref:cache[ref['sha256']],'private-candidate',request['cwd_label'],ledger=ledger(request['source_label']),transaction_name=transaction_name)
            with patch('subprocess.Popen',side_effect=AssertionError('No Git/POST/provider')),patch('os.open',side_effect=AssertionError('No source input/export')),patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No temporary')):
                pure=execute(request,replay,validator_class=Draft202012Validator);replay.finish()
            self.assertEqual(pure,actual)
        finally:moved.rename(c.base)
        for name,raw in cache.items():blob({'sha256':name,'bytes':len(raw)})
        self.assertTrue(closed());return actual
    def test_whole_publisher_with_real_prefix_pilot_overview_viewer_and_inert_replay(self):
        value=self.compare();self.assertEqual(value['exit_code'],0);self.assertTrue(any(v['kind']=='post' for v in value['native_process_observations']))
    def test_real_gate_failure_has_no_branch_commit_push_POST_or_pipeline_append(self):
        value=self.compare(True);self.assertEqual(value['kernel_exception'],{'type':'ContractError','message':'Lifecycle pilot report differs from projection'});self.assertFalse(any(v['kind']=='post' for v in value['native_process_observations']));self.assertEqual(value['pipeline_append_observations'],[])
