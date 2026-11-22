"""Whole typed publisher vs actual isolated Git and explicit fake provider POST."""
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr
import argparse,io,json,os,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.typed_publication import TypedEvidencePublisher,ADDITIONAL_LEDGERS
from lib.providers.typed_publication_process import NativeTypedPublicationProcess
from lib.providers.operational_publication_profile import LegacyOperationalPublicationProfile
from lib.providers.operational_publication_api import LegacyOperationalPublicationAPI
from test_v2_typed_publication import TYPED,GENERIC
import test_v2_operational_publisher_native as reference


def original(root):
    module=ModuleType('publish_operational_update');module.__file__=str(root/'scripts/publish_operational_update.py');exec(compile(GENERIC.read_bytes(),'immutable_operational_publisher','exec'),module.__dict__);module.ROOT=root
    wrapper={'__name__':'immutable_typed_publisher','__file__':str(root/'scripts/publish_typed_evidence_assurance_update.py')}
    with patch.dict(sys.modules,{'publish_operational_update':module}):exec(compile(TYPED.read_bytes(),'immutable_typed_publisher','exec'),wrapper)
    return wrapper,module


class WholeTypedPublisherNative(unittest.TestCase):
    def setUp(self):
        self.case=reference.WholeOperationalPublisherNative();self.case.setUp();self.addCleanup(self.case.doCleanups);c=self.case
        for name in ADDITIONAL_LEDGERS:
            p=c.seed/name/'old.json';p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);p.write_text('{"explicitly_synthetic_historical_fixture":true}\n')
        c.git(c.seed,'add','--','status');c.git(c.seed,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-qm','Three historical typed ledger fixtures');c.initial=c.git(c.seed,'rev-parse','HEAD').strip()
    def candidate(self,root):
        for name in ADDITIONAL_LEDGERS:
            p=root/name/'new.json';p.write_text('{"explicitly_synthetic_new_fixture":true}\n')
    def compare(self,kind='normal',main=True):
        c=self.case;values=[]
        for side in ('original','ported'):
            root,origin,tools,output,summary,env=c.fixture(side)
            if kind!='no-change':self.candidate(root)
            if kind in ('fail-pr','fail-dispatch','malformed','empty'):(tools/'mode').write_text(kind)
            if kind=='historical':(root/ADDITIONAL_LEDGERS[0]/'old.json').write_text('{"forbidden_overwrite":true}\n')
            if kind=='out-of-scope':(root/'README.md').write_text('Unselected normative change\n')
            if kind=='missing-output-parent':output=c.base/'missing-output-parent'/'output';env['GITHUB_OUTPUT']=str(output)
            if kind=='bad-ref':env['GITHUB_REF']='refs/heads/feature'
            out,err=io.StringIO(),io.StringIO();returned=error=signal=None
            with patch.dict(os.environ,env,clear=True),redirect_stdout(out),redirect_stderr(err):
                try:
                    if side=='original':
                        wrapper,publisher=original(root)
                        if main:
                            with patch.object(sys,'argv',['publish_typed_evidence_assurance_update.py','--scope','typed-evidence']):returned=wrapper['main']()
                        else:wrapper['configure']();returned=publisher.publish(root,scope='typed-evidence',repository=reference.REPOSITORY,run_id=reference.RUN,attempt=reference.ATTEMPT)
                    else:
                        profile=LegacyOperationalPublicationProfile();process=NativeTypedPublicationProcess(root,scope='typed-evidence',repository=reference.REPOSITORY,run_id=reference.RUN,attempt=reference.ATTEMPT,profile=profile,environment=env,provider_executable=str(tools/'gh'),local_origin_root=c.base);publisher=TypedEvidencePublisher(root,path_factory=Path,process=process,api=LegacyOperationalPublicationAPI(process,profile),gates=None,profile=profile,environment=env,argument_parser=lambda **kw:argparse.ArgumentParser(prog='publish_typed_evidence_assurance_update.py',**kw),argv=['--scope','typed-evidence'])
                        if main:returned=publisher.main()
                        else:publisher.configure();returned=publisher.publish(root,scope='typed-evidence',repository=reference.REPOSITORY,run_id=reference.RUN,attempt=reference.ATTEMPT)
                except SystemExit as caught:signal={'type':'SystemExit','value':caught.code}
                except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
            values.append({'returned':returned,'error':error,'signal':signal,'stdout':out.getvalue(),'stderr':err.getvalue(),'files':c.snapshot(root),'head':c.git(root,'rev-parse','HEAD'),'branch':c.git(root,'branch','--show-current'),'refs':c.git(origin,'show-ref','--heads'),'staged':c.git(root,'diff','--cached','--name-only','-z'),'calls':(tools/'calls.jsonl').read_bytes() if (tools/'calls.jsonl').exists() else b'','output':output.read_bytes() if output.is_file() else None,'summary':summary.read_bytes(),'ledgers':publisher.LEDGERS,'scopes':publisher.SCOPES})
        self.assertEqual(values[0],values[1],(kind,values[0]['error'],values[1]['error']));return values[1]
    def test_three_additional_native_ledgers_commit_push_PR_and_three_dispatches(self):
        value=self.compare();self.assertIsNone(value['error']);self.assertEqual(value['branch'].strip(),'automation/typed-evidence/42-1');self.assertEqual(len(value['calls'].splitlines()),4);self.assertNotEqual(value['head'].strip(),self.case.initial);self.assertEqual(value['staged'],'')
    def test_whole_original_configured_publish_helper_and_main_ref_guard(self):
        self.assertIsNone(self.compare(main=False)['error']);self.case.serial+=1;self.assertEqual(self.compare('bad-ref')['signal'],{'type':'SystemExit','value':2})
    def test_no_change_has_no_new_branch_or_POST(self):
        value=self.compare('no-change');self.assertEqual(value['head'].strip(),self.case.initial);self.assertEqual(value['calls'],b'')
    def test_historical_additional_ledgers_and_unselected_source_are_rejected(self):
        for i,kind in enumerate(('historical','out-of-scope')):
            self.case.serial+=i+1
            with self.subTest(kind=kind):
                value=self.compare(kind);self.assertEqual(value['error']['type'],'ValueError');self.assertEqual(value['head'].strip(),self.case.initial);self.assertEqual(value['calls'],b'')
    def test_POST_dispatch_and_output_failures_keep_original_partial_native_effects(self):
        for i,kind in enumerate(('fail-pr','fail-dispatch','malformed','empty','missing-output-parent')):
            self.case.serial+=i+1
            with self.subTest(kind=kind):
                value=self.compare(kind);self.assertIsNotNone(value['error']);self.assertNotEqual(value['head'].strip(),self.case.initial);self.assertTrue(any(value['head'].strip() in line and 'automation/typed-evidence/' in line for line in value['refs'].splitlines()))
