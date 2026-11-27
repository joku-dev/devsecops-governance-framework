"""Actual own-source Git and inert replay; configuration cannot launch helpers."""
from pathlib import Path
from unittest.mock import patch
import copy,hashlib,os,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.providers.consumer_lifecycle_storage import Record,read_record
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.synthetic_lifecycle_io import ReplayIO
from lib.provider_observation_git import HEAD,STATUS,ReplayObservationGit
from lib.providers.provider_observation_git import NativeObservationGit
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError


class ObservationGit(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name).resolve();self.source=self.base/'own-product';self.source.mkdir(mode=0o700);self.records=self.base/'records';self.records.mkdir(mode=0o700)
        self.command('init','--quiet');(self.source/'scripts').mkdir();(self.source/'scripts/data.txt').write_text('before\n');self.command('add','.');self.command('-c','user.name=Fixture','-c','user.email=fixture@example.test','-c','commit.gpgsign=false','commit','--quiet','-m','Fixture')
    def command(self,*args):return subprocess.check_output(['git',*args],cwd=self.source)
    def native(self):
        record=Record(self.records,{'development_Git_only':True},{'installed_acceptance':False});record.append({'kind':'execution-intent'});owner=NativeIO(record,mode='selected-files',cwd=str(self.base),private_state=self.records,product_root=ROOT);return record,NativeObservationGit(owner,self.source,emit_stderr=lambda ref:None)
    def test_actual_original_two_reads_and_status_bytes_replay_without_source_or_programs(self):
        (self.source/'scripts/data.txt').write_text('after\n');(self.source/'scripts/untracked.txt').write_text('untracked\n');record,port=self.native();actual=[port.check_output(HEAD,cwd=self.source,text=True),port.check_output(STATUS,cwd=self.source)]
        self.assertEqual(actual,[subprocess.check_output(HEAD,cwd=self.source,text=True),subprocess.check_output(STATUS,cwd=self.source)]);record.finish('complete',{'exit_code':0},{})
        _,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};used=set();self.source.rename(self.base/'source-removed')
        def retained(ref):
            raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);used.add(ref['sha256']);return raw
        owner=ReplayIO(events,retained,'selected-files',str(self.base));pure=ReplayObservationGit(owner,self.source,emit_stderr=lambda ref:None)
        with patch('subprocess.Popen',side_effect=AssertionError('No replay tool')),patch('os.open',side_effect=AssertionError('No source replay')):
            self.assertEqual([pure.check_output(HEAD,cwd=self.source,text=True),pure.check_output(STATUS,cwd=self.source)],actual);owner.finish()
        self.assertEqual(used,set(cache))
        for name in used:blob({'sha256':name,'bytes':len(cache[name])})
        self.assertTrue(closed())
    def test_source_clean_filter_and_config_include_are_rejected_before_status(self):
        for key in ('filter.fixture.clean','filter.fixture.process','include.path','includeIf.gitdir:*/.path'):
            with self.subTest(key=key):
                self.command('config',key,'/not/an/approved/helper');record,port=self.native()
                with self.assertRaisesRegex(InputAdmissionError,'program_or_include_forbidden'):port.check_output(STATUS,cwd=self.source)
                self.assertTrue(record.capture_incomplete);self.command('config','--unset-all',key)
                self.assertEqual(port.calls,1,'Only builtin configuration names may have run')
                with self.assertRaises(InputAdmissionError):port.check_output(STATUS,cwd=self.source)
                self.assertEqual(port.calls,1)
    def test_config_values_including_credentials_are_never_retained(self):
        secret='synthetic-url-private-294a6';self.command('config','remote.origin.url','https://'+secret+'@example.test/repo.git');record,port=self.native();port.check_output(HEAD,cwd=self.source,text=True)
        for path in record.root.rglob('*'):
            if path.is_file():self.assertNotIn(secret.encode(),path.read_bytes())
    def test_closed_command_cwd_and_text_profiles_fail_before_process(self):
        for command,cwd,text in ((['git','fetch'],self.source,False),(HEAD,self.base,True),(HEAD,self.source,False),(STATUS,self.source,True)):
            record,port=self.native()
            with patch('subprocess.Popen',side_effect=AssertionError('No unadmitted process')),self.assertRaises(InputAdmissionError):port.check_output(command,cwd=cwd,text=text)
            self.assertEqual(port.calls,0)
    def test_original_unborn_HEAD_error_stderr_and_terminal_are_preserved(self):
        unborn=self.base/'unborn';unborn.mkdir(mode=0o700);subprocess.check_call(['git','init','--quiet'],cwd=unborn);self.source=unborn;record,port=self.native();parts=[];port.emit_stderr=parts.append
        with self.assertRaises(RetainedOutputError) as caught:port.check_output(HEAD,cwd=self.source,text=True)
        expected=subprocess.run(HEAD,cwd=self.source,capture_output=True)
        self.assertEqual(caught.exception.original_type,'CalledProcessError');self.assertEqual(caught.exception.original_message,str(subprocess.CalledProcessError(expected.returncode,HEAD,output=expected.stdout)))
        self.assertFalse(record.capture_incomplete);self.assertEqual(len(parts),1);self.assertEqual((record.blobs/parts[0]['sha256']).read_bytes(),expected.stderr)
    def test_resealed_intent_or_process_streams_do_not_replay_and_stick(self):
        record,port=self.native();port.check_output(HEAD,cwd=self.source,text=True);record.finish('complete',{'exit_code':0},{})
        _,_,_,events,blob,_=read_record(record.root)
        for kind in ('cwd','text','actual-argv','missing-stream'):
            changed=copy.deepcopy(events)
            intent=next(i for i,row in enumerate(changed) if row.get('action')=='personal-read-process')
            if kind in ('cwd','text'):changed[intent]['arguments']['cwd' if kind=='cwd' else 'text']='/wrong' if kind=='cwd' else True
            else:
                # NativeIO stores the whole returned process wire as a blob.
                import json
                value=json.loads(blob(changed[intent+1]['value']))
                if kind=='actual-argv':value['actual_arguments'].append('--unsafe')
                else:value['stdout']={'sha256':'0'*64,'bytes':1}
                raw=json.dumps(value).encode();reference={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};changed[intent+1]['value']=reference
            def retained(ref):return raw if kind in ('actual-argv','missing-stream') and ref==reference else blob(ref)
            owner=ReplayIO(changed,retained,'selected-files',str(self.base));pure=ReplayObservationGit(owner,self.source,emit_stderr=lambda ref:None)
            with self.assertRaises((InputAdmissionError,IntegrityError,ValueError)):pure.check_output(HEAD,cwd=self.source,text=True)
            position=owner.position
            with self.assertRaises((InputAdmissionError,IntegrityError)):pure.check_output(HEAD,cwd=self.source,text=True)
            self.assertEqual(position,owner.position)
