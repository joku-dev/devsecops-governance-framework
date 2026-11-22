"""Registered whole consumer publisher with actual isolated Git and full gate.

Only the local bare fixture receives pushes; provider replies are saved test
bytes. No acceptance or provider-writing authority is granted to this node.
"""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_consumer_lifecycle_program as reference
from test_v2_consumer_lifecycle_execution import FixedClock
from lib.consumer_publication_application import generate,inspect,request_valid,PROFILE
from lib.consumer_publication_ports import Record,NativeIO,read_record
from lib.functional_parity import git_read
from lib.portable.runtime import source_digest
from lib.requirement_validation_budget import InputAdmissionError
from test_portable_runtime import OPA


class ConsumerPublisherApplication(unittest.TestCase):
    def setUp(self):
        self.fixture=reference.WholeConsumerProgram();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups);self.source=self.fixture.root;self.parent=self.fixture.parent;self.node=self.parent/'node';self.node.mkdir(mode=0o700);self.temporary=self.parent/'temporaries';self.temporary.mkdir(mode=0o700);self.output=self.parent/'output';self.summary=self.parent/'summary';self.output.write_text('prior=retained\n');self.summary.write_text('Earlier summary\n')
        self.environment={**os.environ,'PATH':str(self.fixture.tools)+os.pathsep+os.environ['PATH'],'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null','GIT_CONFIG_NOSYSTEM':'1','GIT_AUTHOR_DATE':'2026-11-15T12:00:00+00:00','GIT_COMMITTER_DATE':'2026-11-15T12:00:00+00:00','PYTHONDONTWRITEBYTECODE':'1'}
        def git(*args):return subprocess.check_output(['git','-c','core.hooksPath=/dev/null',*args],cwd=self.source,env=self.environment,stderr=subprocess.PIPE)
        self.git=git;git('init','--initial-branch=main');git('add','--','.',':!status/governance-consumer-lifecycle.json');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-qm','Accepted history and model; projection not yet published');self.base=git('rev-parse','HEAD').decode().strip();self.origin=self.parent/'local-origin.git';git('clone','--bare',str(self.source),str(self.origin));git('remote','add','origin',str(self.origin))
        gh=self.fixture.tools/'gh';text=gh.read_text();anchor="b=Path(__file__).resolve().parent;args=sys.argv[1:]\n";assert anchor in text;text=text.replace(anchor,anchor+"if args[:3]==['api','--method','POST']:\n assert len(args)==6 and args[4:]==['--input','-']\n payload=json.load(sys.stdin)\n with (b/'calls.jsonl').open('a') as h:h.write(json.dumps({'endpoint':args[3],'payload':payload})+'\\n')\n if args[3].endswith('/pulls'):print(json.dumps({'html_url':'https://github.com/owner/repo/pull/7'}))\n sys.exit(0)\n");gh.write_text(text);gh.chmod(0o700)
        self.identity={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()};self.settings={**self.identity,'opa':str(OPA),'opa_sha256':hashlib.sha256(OPA.read_bytes()).hexdigest()}
    def options(self,**extra):return {'source_worktree':str(self.source),'working_directory':str(self.source),'profile':PROFILE,'transport_profile':'legacy-consumer-publisher-local-test-v1','local_origin_root':str(self.parent),'scope':'consumer-lifecycle','repository':'owner/repo','run_id':'123','attempt':'2','workflow_ref':'refs/heads/main','provider_executable':str(self.fixture.tools/'gh'),'temporary_parent':str(self.temporary),'output_file':str(self.output),'summary_file':str(self.summary),**extra}
    def generate(self,**extra):
        with patch('lib.providers.personal_channel_transport.datetime',FixedClock):return generate(self.options(**extra),self.node,self.settings,native_environment=self.environment)
    def test_complete_full_consumer_gate_native_Git_POST_four_dispatches_and_source_free_replay(self):
        receipt,result=self.generate();self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0,result);self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred']);self.assertTrue(receipt['external_writes_may_have_occurred']);self.assertEqual(self.git('branch','--show-current').decode().strip(),'automation/consumer-lifecycle/123-2');self.assertEqual(self.git('diff','--cached','--name-only'),b'');self.assertNotEqual(self.git('rev-parse','HEAD').decode().strip(),self.base)
        calls=[json.loads(x) for x in (self.fixture.tools/'calls.jsonl').read_text().splitlines()];posts=[x for x in calls if type(x) is dict];self.assertEqual(len(posts),5);self.assertTrue(posts[-1]['endpoint'].endswith('/consumer-lifecycle-guard.yml/dispatches'));checked=inspect(receipt['record_root'],node=self.identity);self.assertTrue(checked['retained_declared_replay_consistent'])
        shutil.rmtree(self.source);shutil.rmtree(self.fixture.tools);shutil.rmtree(self.temporary);self.output.unlink();self.summary.unlink()
        real_open=os.open;record_root=Path(receipt['record_root'])
        def private_record_read_only(path,flags,*args,**kwargs):
            self.assertTrue(Path(path).is_absolute() and Path(path).is_relative_to(record_root),path)
            self.assertFalse(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            return real_open(path,flags,*args,**kwargs)
        with patch('subprocess.Popen',side_effect=AssertionError('No repeated Git/provider/OPA')),patch('os.open',side_effect=private_record_read_only),patch('lib.consumer_publication_ports.NativePublisherPaths',side_effect=AssertionError('No native output adapter')):self.assertEqual(inspect(receipt['record_root']),checked)
        with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.identity,'node_id':'b'*32})
    def test_strict_provider_origin_OPA_and_authority_request_binding(self):
        receipt,_=self.generate(original_arguments=['--help']);request,*_=read_record(receipt['record_root'])
        for change in ({'schema_version':True},{'approved_opa_hashes':['0'*64]},{'approved_opa_hashes':[['bad']]},{'opa_tool':'relative/opa'},{'opa_workarea':'/a/../b'},{'subject':{**request['subject'],'scope':'portfolio'}},{'local_origin_root':None},{'official_acceptance':True}):
            with self.subTest(change=change),self.assertRaises(ValueError):request_valid({**request,**change})
    def test_unobserved_Git_and_lost_completion_never_become_original_success_or_retry(self):
        with patch.object(NativeIO,'perform',side_effect=InputAdmissionError('unobserved process')):receipt,_=self.generate()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent']);self.assertEqual(self.git('branch','--show-current'),b'main\n')
        append=Record.append;lost=False;intents=[]
        def lose(record,row):
            nonlocal lost
            if row.get('kind')=='intent':intents.append(row)
            if row.get('kind')=='returned':lost=True
            if lost:raise OSError('Isolated publisher journal completion loss')
            return append(record,row)
        with patch.object(Record,'append',lose):receipt,_=self.generate()
        self.assertTrue(lost);self.assertEqual(len(intents),1);self.assertEqual(receipt['state'],'incomplete');self.assertFalse(receipt['journal_terminal_written']);self.assertIsNone(receipt['original_exit_code']);self.assertEqual(self.git('branch','--show-current'),b'main\n')
    def test_actual_registered_CLI_uses_default_scope_and_a_paused_node(self):
        node=self.parent/'cli-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')]
        def call(args):
            p=subprocess.run([*cli,*args],capture_output=True,timeout=300,env=self.environment);self.assertEqual(p.returncode,0,(p.stdout[-4000:],p.stderr[-4000:]));return p
        call(['--instance',str(node),'init','--development','--opa',str(OPA)])
        args=['--instance',str(node),'consumer-publisher','publish','--profile',PROFILE,'--transport-profile','legacy-consumer-publisher-local-test-v1','--local-origin-root',str(self.parent),'--source-worktree',str(self.source),'--working-directory',str(self.source),'--repository','owner/repo','--run-id','123','--attempt','2','--workflow-ref','refs/heads/main','--provider-executable',str(self.fixture.tools/'gh'),'--temporary-parent',str(self.temporary),'--original-arguments','--help']
        receipt=json.loads(call(args).stdout);self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],0);checked=json.loads(call(['--instance',str(node),'consumer-publisher','inspect','--record',receipt['record_root']]).stdout);shutil.rmtree(self.source);shutil.rmtree(self.fixture.tools);shutil.rmtree(self.temporary);pure=json.loads(call(['consumer-publisher','replay','--record',receipt['record_root']]).stdout);self.assertEqual(pure,checked);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')
