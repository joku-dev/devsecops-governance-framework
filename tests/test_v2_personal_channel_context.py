"""Whole original CLI effects via logical ports; pure replay after source deletion."""
from pathlib import Path
from unittest.mock import patch
from datetime import datetime as NativeDatetime
import errno,hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from jsonschema import Draft202012Validator
from lib.personal_channel_context import execute,PersonalPaths
from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.providers.personal_channel_protocol import LegacyPersonalProtocol
from lib.personal_channel_process import ReplayPersonalTransport
from lib.providers.personal_channel_exclusive import NativeExclusive
from lib.personal_channel_exclusive import ReplayExclusive
from lib.personal_channel_private import PrivateExclusive
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.synthetic_lifecycle_io import ReplayIO
from lib.providers.retained_argparse import capture_context
from lib.requirement_validation_budget import InputAdmissionError
import test_v2_personal_channel_programs as reference

class FrozenDatetime:
    @staticmethod
    def now(zone):return NativeDatetime.fromisoformat('2026-11-15T12:00:00+00:00').astimezone(zone)

class WholePersonalContext(unittest.TestCase):
    def setUp(self):
        fixture=reference.WholePersonalChannelPrograms();fixture.setUp();self.addCleanup(fixture.doCleanups);self.fixture=fixture
    def compare(self,program,kind,native):
        data,config,tools=self.fixture.fixture(kind=kind if kind in ('race','invalid-json') else 'normal')
        args=['--ignored-original-argv'] if program!='check' else ['--output',str(data/'generated/reports/lifecycle-personal-channel/new.json')]
        if kind=='help':args=['--help']
        elif kind=='unknown':args=['--unknown']
        elif kind=='replay':args=['--replay',str(data/'generated/reports/lifecycle-personal-channel/00000001.json')]
        elif kind=='previous':args+=['--previous-capture',str(data/'generated/reports/lifecycle-personal-channel/00000001.json')]
        elif kind=='existing':args=['--output',str(data/'generated/reports/lifecycle-personal-channel/00000001.json')]
        if kind in ('raw-stderr','nonzero'):
            path=tools/'gh';raw=path.read_text();position=raw.index('import json,sys')
            injected="import sys\nsys.stderr.buffer.write(b'opaque\\xffstderr\\r\\n');sys.stderr.buffer.flush()\n"
            if kind=='nonzero':injected+='raise SystemExit(7)\n'
            path.write_text(raw[:position]+injected+raw[position:]);path.chmod(0o700)
        before=reference.snapshot(data)
        wrapper='''import runpy,sys
from datetime import datetime as NativeDatetime
import lib.governance_lifecycle.personal_probe as probe
class FrozenDatetime:
 @staticmethod
 def now(zone):return NativeDatetime.fromisoformat("2026-11-15T12:00:00+00:00").astimezone(zone)
probe.datetime=FrozenDatetime
path=sys.argv[1];sys.argv=sys.argv[1:]
runpy.run_path(path,run_name="__main__")
'''
        env={**os.environ,'PATH':str(tools)+os.pathsep+os.environ['PATH'],'PYTHONPATH':str(data/'scripts'),'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'}
        old=subprocess.run([sys.executable,'-B','-c',wrapper,str(data/'scripts'/reference.NAMES[program]),*args],cwd=data,env=env,capture_output=True,timeout=120)
        expected=reference.snapshot(data);reference.restore(data,before)
        call_file=tools/'calls.jsonl';old_calls=call_file.read_bytes() if call_file.exists() else b''
        if call_file.exists():call_file.unlink()
        private=data.parent/('context-'+str(self.fixture.serial));private.mkdir(mode=0o700)
        record=Record(private/'records',{'prototype':'whole personal context'},{'prototype':True});record.append({'kind':'execution-intent'})
        mode='selected-files' if native else 'private-candidate'
        owner=NativeIO(record,mode=mode,cwd=str(data),private_state=private,product_root=ROOT)
        with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}):frame=capture_context()
        common={'validator_class':Draft202012Validator,'provider_factory':lambda context,transport:LegacyPersonalChannelCapture(context,fetch=transport.fetch,clock=transport.clock),'parser_context':frame if program=='check' else None}
        with patch('lib.providers.personal_channel_transport.datetime',FrozenDatetime):
            actual=execute(str(data),str(data),program,args,owner,**common,
                transport_factory=lambda io,root,emit:NativePersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit,environment=env),
                exclusive_factory=NativeExclusive if native else PrivateExclusive)
        self.assertFalse(record.capture_incomplete);self.assertEqual(actual['exit_code'],old.returncode,(actual,old.stderr[-3000:]));self.assertEqual(actual['stdout'].encode(),old.stdout)
        raw_stderr=b''.join(part['text'].encode() if 'text' in part else (record.blobs/part['blob']['sha256']).read_bytes() for part in actual['stderr_parts'])
        if actual['kernel_exception'] is None:self.assertEqual(raw_stderr,old.stderr)
        else:
            error=actual['kernel_exception'];self.assertTrue(old.stderr.startswith(raw_stderr));self.assertTrue(old.stderr.endswith((error['type']+': '+error['message']+'\n').encode()),(actual,old.stderr[-3000:]))
        self.assertEqual(call_file.read_bytes() if call_file.exists() else b'',old_calls)
        if native:self.assertEqual(reference.snapshot(data),expected)
        else:
            self.assertEqual(reference.snapshot(data),before);files,dirs=map(dict,before)
            for name,value in owner.projected_changes.items():
                relative=Path(name).relative_to(data).as_posix()
                if value['kind']=='file':files[relative]=((record.blobs/value['content']['sha256']).read_bytes(),value['mode'])
                elif value['kind']=='directory':dirs[relative]=value['mode']
                elif value['kind']=='missing':files.pop(relative,None);dirs.pop(relative,None)
                else:self.fail(value)
            self.assertEqual((files,dirs),expected)
        record.finish('complete',{'exit_code':actual['exit_code'],'kernel_result':actual},owner.touched)
        _,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
        def inert(ref):
            raw=cache[ref['sha256']];self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);self.assertEqual(len(raw),ref['bytes']);seen.add(ref['sha256']);return raw
        shutil.rmtree(data);shutil.rmtree(tools)
        replay=ReplayIO(events,inert,mode,str(data))
        with patch('os.open',side_effect=AssertionError('No native input/output')),patch('subprocess.Popen',side_effect=AssertionError('No native process')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No native clock')):
            replayed=execute(str(data),str(data),program,args,replay,**common,
                transport_factory=lambda io,root,emit:ReplayPersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit),
                exclusive_factory=ReplayExclusive if native else PrivateExclusive)
            replay.finish()
        self.assertEqual(replayed,actual);self.assertEqual(replay.files,owner.files);self.assertEqual(replay.writes,owner.writes);self.assertEqual(replay.projected_changes,owner.projected_changes)
        self.assertEqual(seen,set(cache))
        for sha in seen:blob({'sha256':sha,'bytes':len(cache[sha])})
        self.assertTrue(closed())

    def test_whole_statement_and_evidence_original_effects_both_modes_and_no_source_replay(self):
        for program in ('statement','evidence'):
            for native in (False,True):
                with self.subTest(program=program,native=native):self.compare(program,'normal',native)
    def test_whole_new_capture_previous_capture_and_retained_replay_both_modes(self):
        for kind in ('normal','previous','replay'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare('check',kind,native)
    def test_original_help_unknown_and_existing_capture_guards_both_modes(self):
        for kind in ('help','unknown','existing'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare('check',kind,native)
    def test_original_raw_provider_stderr_nonzero_invalid_json_and_race_both_modes(self):
        for kind in ('raw-stderr','nonzero','invalid-json','race'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare('check',kind,native)
    def test_missing_parser_or_wrong_program_context_rejects_before_ports(self):
        def forbidden(*args):self.fail('No port before argument admission')
        for program,options in (('check',{}),('statement',{'parser_context':{}}),('unknown',{}),('evidence',{'verify_base_ref':'HEAD','argv':['--unknown']})):
            with self.subTest(program=program):
                argv=options.pop('argv',[])
                with self.assertRaises(InputAdmissionError):execute('/owned/source','/owned/source',program,argv,None,validator_class=None,provider_factory=forbidden,transport_factory=forbidden,exclusive_factory=forbidden,**options)

    def test_whole_original_verify_new_captures_function_real_git_and_provider_both_modes_then_pure_replay(self):
        for kind in ('accepted','new','provider-disagreement'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):
                    data,config,tools=self.fixture.fixture();capture=data/'generated/reports/lifecycle-personal-channel/00000001.json';raw=capture.read_bytes()
                    if kind!='accepted':capture.unlink()
                    def git(*args):return subprocess.run(['git','-C',str(data),*args],check=True,capture_output=True)
                    git('init','--initial-branch=fixture');git('add','--all');git('-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null','-c','user.name=AXIOM isolated original test','-c','user.email=fixture@invalid.example','commit','--quiet','-m','Private original verification fixture')
                    if kind!='accepted':capture.write_bytes(raw);capture.chmod(0o600)
                    if kind=='provider-disagreement':config={**config,'comments':'[]'};(tools/'config.json').write_text(json.dumps(config))
                    before=reference.snapshot(data)
                    wrapper='''from pathlib import Path
import json
from datetime import datetime as NativeDatetime
import lib.governance_lifecycle.personal_probe as probe
import generate_personal_channel_evidence as report
class FrozenDatetime:
 @staticmethod
 def now(zone):return NativeDatetime.fromisoformat("2026-11-15T12:00:00+00:00").astimezone(zone)
probe.datetime=FrozenDatetime
print(json.dumps(report.verify_new_captures(Path.cwd(),"HEAD")))
'''
                    env={**os.environ,'PATH':str(tools)+os.pathsep+os.environ['PATH'],'PYTHONPATH':str(data/'scripts'),'PYTHONDONTWRITEBYTECODE':'1'}
                    old=subprocess.run([sys.executable,'-B','-c',wrapper],cwd=data,env=env,capture_output=True,timeout=120)
                    self.assertEqual(old.returncode,1 if kind=='provider-disagreement' else 0);self.assertEqual(reference.snapshot(data),before)
                    calls=tools/'calls.jsonl';expected_calls=calls.read_bytes() if calls.exists() else b''
                    if calls.exists():calls.unlink()
                    private=data.parent/('verify-context-'+str(self.fixture.serial));private.mkdir(mode=0o700)
                    record=Record(private/'records',{'prototype':'whole verify function'},{'prototype':True});record.append({'kind':'execution-intent'})
                    mode='selected-files' if native else 'private-candidate';owner=NativeIO(record,mode=mode,cwd=str(data),private_state=private,product_root=ROOT)
                    common={'validator_class':Draft202012Validator,'provider_factory':lambda context,transport:LegacyPersonalChannelCapture(context,fetch=transport.fetch,clock=transport.clock),'verify_base_ref':'HEAD'}
                    with patch('lib.providers.personal_channel_transport.datetime',FrozenDatetime):
                        actual=execute(str(data),str(data),'evidence',[],owner,**common,transport_factory=lambda io,root,emit:NativePersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit,environment=env),exclusive_factory=NativeExclusive if native else PrivateExclusive)
                    self.assertFalse(record.capture_incomplete);self.assertEqual(actual['exit_code'],old.returncode)
                    self.assertEqual(actual['stdout'],'');self.assertEqual(actual['stderr'],'');self.assertEqual(actual['stderr_parts'],[])
                    if old.returncode:
                        error=actual['kernel_exception'];self.assertTrue(old.stderr.endswith((error['type']+': '+error['message']+'\n').encode()))
                    else:self.assertEqual(actual['return_value'],json.loads(old.stdout));self.assertEqual(actual['return_value'],0 if kind=='accepted' else 1)
                    self.assertEqual(calls.read_bytes() if calls.exists() else b'',expected_calls);self.assertEqual(reference.snapshot(data),before)
                    record.finish('complete',{'exit_code':actual['exit_code'],'kernel_result':actual},owner.touched)
                    _,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
                    def inert(ref):
                        value=cache[ref['sha256']];self.assertEqual(hashlib.sha256(value).hexdigest(),ref['sha256']);self.assertEqual(len(value),ref['bytes']);seen.add(ref['sha256']);return value
                    shutil.rmtree(data);shutil.rmtree(tools);replay=ReplayIO(events,inert,mode,str(data))
                    with patch('os.open',side_effect=AssertionError('No native input/output')),patch('subprocess.Popen',side_effect=AssertionError('No Git or provider program')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No native clock')):
                        replayed=execute(str(data),str(data),'evidence',[],replay,**common,transport_factory=lambda io,root,emit:ReplayPersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit),exclusive_factory=ReplayExclusive if native else PrivateExclusive);replay.finish()
                    self.assertEqual(replayed,actual);self.assertEqual(seen,set(cache));self.assertEqual(replay.files,owner.files);self.assertEqual(replay.writes,owner.writes)
                    for sha in seen:blob({'sha256':sha,'bytes':len(cache[sha])})
                    self.assertTrue(closed())

    def test_whole_context_journal_failure_releases_owned_output_without_returning_original_verdict(self):
        data,config,tools=self.fixture.fixture();private=data.parent/'context-journal-failure';private.mkdir(mode=0o700)
        record=Record(private/'records',{'prototype':'whole context journal failure'},{'prototype':True});record.append({'kind':'execution-intent'})
        owner=NativeIO(record,mode='selected-files',cwd=str(data),private_state=private,product_root=ROOT)
        with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}):frame=capture_context()
        environment={**os.environ,'PATH':str(tools)+os.pathsep+os.environ['PATH']};append=record.append;current={}
        def failing(row):
            if row.get('kind')=='intent':current.clear();current.update(row)
            if row.get('kind')=='returned' and current.get('action')=='personal-exclusive-output' and current['arguments']['stage']=='write':
                raise OSError(errno.ENOSPC,os.strerror(errno.ENOSPC))
            return append(row)
        output=data/'generated/reports/lifecycle-personal-channel/new.json'
        with patch.object(record,'append',failing),patch('lib.providers.personal_channel_transport.datetime',FrozenDatetime):
            with self.assertRaises(InputAdmissionError):
                execute(str(data),str(data),'check',['--output',str(output)],owner,
                    validator_class=Draft202012Validator,provider_factory=lambda context,transport:LegacyPersonalChannelCapture(context,fetch=transport.fetch,clock=transport.clock),
                    transport_factory=lambda io,root,emit:NativePersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit,environment=environment),exclusive_factory=NativeExclusive,parser_context=frame)
        self.assertTrue(record.capture_incomplete);self.assertTrue(output.exists())
        self.assertEqual(len(owner.personal_exclusive_sessions),1);session=owner.personal_exclusive_sessions[0]
        self.assertTrue(session.resource.closed);self.assertNotIn(str(output),owner.files)
        self.assertTrue(output.read_bytes());self.assertFalse((record.root/'result.json').exists())

if __name__=='__main__':unittest.main(verbosity=2)
