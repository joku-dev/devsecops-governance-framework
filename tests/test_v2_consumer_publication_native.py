"""Whole original consumer publisher against actual isolated Git and fake POST.

The full consumer gate is covered separately. This file compares all native
orchestration effects with explicit gate stand-ins and never contacts GitHub.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr
import argparse,io,json,os,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.consumer_publication import ConsumerPublisher
from lib.providers.consumer_publication_profile import LegacyConsumerPublicationProfile
from lib.providers.consumer_publication_process import NativeConsumerPublicationProcess
from lib.providers.operational_publication_api import LegacyOperationalPublicationAPI
from test_v2_consumer_publication import ORIGINAL
import test_v2_operational_publisher_native as reference


class WholeConsumerPublisherNative(unittest.TestCase):
    def setUp(self):
        self.case=reference.WholeOperationalPublisherNative();self.case.setUp();self.addCleanup(self.case.doCleanups);c=self.case;p=c.seed/'status/governance-consumer-lifecycle.json';p.write_text('{}\n');c.git(c.seed,'add','--',str(p));c.git(c.seed,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-qm','Consumer projection fixture');c.initial=c.git(c.seed,'rev-parse','HEAD').strip()
    def compare(self,kind='normal',main=False):
        c=self.case;results=[]
        for side in ('original','ported'):
            root,origin,tools,output,summary,env=c.fixture(side);selected=root/'status/governance-consumer-lifecycle.json'
            if kind!='no-change':selected.write_text('{"explicit":"consumer candidate"}\n')
            if kind in ('fail-pr','fail-dispatch','malformed','empty'):(tools/'mode').write_text(kind)
            if kind=='out-of-scope':(root/'README.md').write_text('Unselected source change\n')
            if kind=='symlink':selected.unlink();selected.symlink_to(root/'README.md')
            if kind=='missing-output-parent':output=c.base/'missing-output-parent'/'output';env['GITHUB_OUTPUT']=str(output)
            if kind=='unprotected-main':env['GITHUB_REF']='refs/heads/feature'
            trace=[]
            def gate(gate_root,base):
                trace.append({'source_is_selected':gate_root==root,'base':base})
                if kind=='gate-failure':raise ValueError('Explicit consumer gate failure')
            gates=SimpleNamespace(validate_publication=gate);out,err=io.StringIO(),io.StringIO();returned=error=signal=None
            with patch.dict(os.environ,env,clear=True),redirect_stdout(out),redirect_stderr(err):
                try:
                    if side=='original':
                        namespace={'__name__':'immutable_consumer_publisher','__file__':str(root/'scripts/publish_consumer_lifecycle.py')};exec(compile(ORIGINAL.read_bytes(),'immutable_consumer_publisher','exec'),namespace);namespace['ROOT']=root
                        with patch.dict(sys.modules,{'lib.governance_lifecycle.consumer_acceptance':gates}),patch.object(sys,'argv',['publish_consumer_lifecycle.py']):returned=namespace['main']() if main else namespace['publish'](root,scope='consumer-lifecycle',repository=reference.REPOSITORY,run_id=reference.RUN,attempt=reference.ATTEMPT)
                    else:
                        profile=LegacyConsumerPublicationProfile();process=NativeConsumerPublicationProcess(root,scope='consumer-lifecycle',repository=reference.REPOSITORY,run_id=reference.RUN,attempt=reference.ATTEMPT,profile=profile,environment=env,provider_executable=str(tools/'gh'),local_origin_root=c.base);kernel=ConsumerPublisher(root,path_factory=Path,process=process,api=LegacyOperationalPublicationAPI(process,profile),gates=gates,profile=profile,environment=env,argument_parser=lambda **kw:argparse.ArgumentParser(prog='publish_consumer_lifecycle.py',**kw),argv=[]);returned=kernel.main() if main else kernel.publish(root,scope='consumer-lifecycle',repository=reference.REPOSITORY,run_id=reference.RUN,attempt=reference.ATTEMPT)
                except SystemExit as caught:signal={'type':'SystemExit','value':caught.code}
                except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
            results.append({'returned':returned,'exception':error,'signal':signal,'stdout':out.getvalue(),'stderr':err.getvalue(),'source':c.snapshot(root),'branch':c.git(root,'branch','--show-current'),'head':c.git(root,'rev-parse','HEAD'),'refs':c.git(origin,'show-ref','--heads'),'staged':c.git(root,'diff','--cached','--name-only','-z'),'calls':(tools/'calls.jsonl').read_bytes() if (tools/'calls.jsonl').exists() else b'','output':output.read_bytes() if output.is_file() else None,'summary':summary.read_bytes(),'gate':trace})
        self.assertEqual(results[0],results[1],(kind,results[0]['exception'],results[1]['exception']));return results[1]
    def test_entire_consumer_branch_commit_local_push_PR_four_dispatches_and_both_appends(self):
        value=self.compare();self.assertIsNone(value['exception']);self.assertEqual(len(value['calls'].splitlines()),5);self.assertEqual(len(value['gate']),1);self.assertEqual(value['branch'].strip(),'automation/consumer-lifecycle/42-1')
    def test_default_scope_main_and_protected_ref_error_are_original(self):
        self.assertEqual(self.compare(main=True)['returned'],0);self.case.serial+=1;self.assertEqual(self.compare('unprotected-main',main=True)['signal'],{'type':'SystemExit','value':2})
    def test_original_no_change_has_no_gate_branch_commit_push_or_api(self):
        value=self.compare('no-change');self.assertEqual(value['gate'],[]);self.assertEqual(value['calls'],b'');self.assertEqual(value['head'].strip(),self.case.initial)
    def test_original_native_gate_selection_and_symlink_failures_precede_push(self):
        for n,kind in enumerate(('out-of-scope','symlink','gate-failure')):
            self.case.serial+=n+1
            with self.subTest(kind=kind):
                value=self.compare(kind);self.assertIsNotNone(value['exception']);self.assertEqual(value['head'].strip(),self.case.initial);self.assertEqual(value['calls'],b'')
    def test_original_partial_effects_after_push_and_failure_are_retained(self):
        for n,kind in enumerate(('fail-pr','fail-dispatch','malformed','empty','missing-output-parent')):
            self.case.serial+=n+1
            with self.subTest(kind=kind):
                value=self.compare(kind);self.assertIsNotNone(value['exception']);self.assertNotEqual(value['head'].strip(),self.case.initial);self.assertTrue(any(value['head'].strip() in row and 'automation/consumer-lifecycle/' in row for row in value['refs'].splitlines()))
