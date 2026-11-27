"""Closed prefix ports, raw process replay and builtin-only Git context plans.

The auxiliary directories here are test-owned probes. Native captured auxiliary
creation/stability/cleanup and complete prefix composition remain separate gates.
"""
from pathlib import Path
from unittest.mock import patch
import os,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from jsonschema import Draft202012Validator
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.providers.accepted_prefix_protocol import LegacyAcceptedPrefixProtocol,NativeAcceptedPrefixTransport,ReplayAcceptedPrefixTransport
from lib.accepted_prefix_git_context import (ATTRIBUTES,attribute_values,executable_driver_keys,frozen_files,FrozenHashArguments)
from lib.providers.personal_channel_protocol import GIT_SAFETY
from lib.requirement_validation_budget import InputAdmissionError
from lib.providers.synthetic_lifecycle_storage import read_record
from lib.synthetic_lifecycle_io import ReplayIO
import test_v2_personal_channel_transport as fixture

BASE='a'*40

def context(root):return RepositoryLifecycle(Path(root),validator_class=Draft202012Validator)
def environment():
    result={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','LD_','DYLD_'))}
    result.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_COUNT='0',GIT_OPTIONAL_LOCKS='0',GIT_NO_REPLACE_OBJECTS='1',GIT_NO_LAZY_FETCH='1',GIT_ALLOW_PROTOCOL='',GIT_TERMINAL_PROMPT='0')
    return result

def git(root,*args,aux=None):
    isolation=[] if aux is None else ['--git-dir='+str(aux),'--work-tree='+str(root)]
    return subprocess.run(['git',*GIT_SAFETY,*isolation,*args],cwd=root,env=environment(),capture_output=True)

class PrefixProtocol(unittest.TestCase):
    def setUp(self):self.root='/owned/source';self.context=context(self.root);self.profile=LegacyAcceptedPrefixProtocol(self.context)
    def spec(self,command,kind='git-tree',**options):return self.profile.request(kind,{'command':command,'cwd':self.root,'text' if kind=='git-tree' else 'capture_output':True,**options},self.root,self.root)
    def test_every_original_read_command_family_and_binary_optional_profile(self):
        p=self.profile
        commands=[['git','cat-file','-e',BASE+'^{commit}'],['git','ls-files','--',*p.ledgers],['git','ls-tree','-r',BASE,'--',*p.ledgers],['git','ls-tree','-r',BASE,'--',*p.preparation],*[['git','rev-parse',BASE+':'+name] for name in p.profiles]]
        for command in commands:
            spec=self.spec(command);self.assertTrue(spec['text']);self.assertEqual(p.actual_arguments(spec,None),['git',*GIT_SAFETY,*command[1:]])
        spec=self.spec(['git','cat-file','-e',BASE+':'+p.profiles[1]],'git-run');self.assertFalse(spec['text'])
    def test_mutating_options_provider_commands_dynamic_refs_and_broadened_paths_are_rejected(self):
        for command in (['git','fetch'],['gh','api'],['git','ls-files','--'],['git','cat-file','-e','HEAD^{commit}'],['git','rev-parse',BASE+':credentials'],['git','hash-object','-w','--',self.profile.profiles[0]],['git','hash-object','--','../outside'],['git','hash-object','--','status/unrelated.json']):
            with self.subTest(command=command),self.assertRaises(InputAdmissionError):self.spec(command)
        with self.assertRaises(InputAdmissionError):self.spec(['git','cat-file','-e',BASE+'^{commit}'],text=False)
        with self.assertRaises(InputAdmissionError):self.spec(['git','cat-file','-e',BASE+'^{commit}'],env={})
    def test_hash_requires_exact_owned_isolation_binding_without_native_fallback(self):
        path=self.profile.profiles[0];spec=self.spec(['git','hash-object','--',path])
        with self.assertRaisesRegex(InputAdmissionError,'isolated_hash_context_required'):self.profile.actual_arguments(spec,'/usr/bin/git')
        self.profile.hash_scope=FrozenHashArguments(self.root,'/private/state/hash/git',path)
        actual=self.profile.actual_arguments(spec,'/usr/bin/git');self.assertIn('--git-dir=/private/state/hash/git',actual);self.assertEqual(actual[-3:],['hash-object','--',path]);self.assertNotIn('--no-filters',actual)
        for changed in (self.profile.profiles[1],path+'/different'):
            with self.assertRaises(InputAdmissionError):self.profile.actual_arguments(self.spec(['git','hash-object','--',changed]),None)
        for private in (self.root,self.root+'/inside','/owned',self.root+'/../escape'):
            with self.assertRaises(InputAdmissionError):FrozenHashArguments(self.root,private,path)

class FrozenConversionPlan(unittest.TestCase):
    def raw(self,path='data.json',**values):return b''.join((path+'\0'+key+'\0'+values.get(key,'unspecified')+'\0').encode() for key in ATTRIBUTES)
    def test_attribute_response_binds_every_key_path_order_and_raw_termination(self):
        raw=self.raw(text='set',eol='lf');self.assertEqual(attribute_values(raw,'data.json')['eol'],'lf')
        for changed in (raw[:-1],raw+b'\0',raw.replace(b'data.json',b'other.json',1),raw.replace(b'crlf',b'text',1),raw.replace(b'lf\0',b'lf\nfilter=bad\0',1)):
            with self.assertRaises(InputAdmissionError):attribute_values(changed,'data.json')
    def test_only_selected_driver_key_names_are_observed_and_executable_filters_fail_technically(self):
        self.assertEqual(executable_driver_keys(b'','lfs'),[])
        for raw in (b'filter.lfs.clean\0',b'filter.lfs.process\0'):
            with self.assertRaisesRegex(InputAdmissionError,'external_clean_or_process'):executable_driver_keys(raw,'lfs')
        for raw in (b'filter.other.clean\0',b'filter.lfs.clean=private-command\0',b'filter.lfs.required\0'):
            with self.assertRaisesRegex(InputAdmissionError,'driver_selection'):executable_driver_keys(raw,'lfs')
    def test_plan_cannot_smuggle_config_commands_includes_or_second_attribute_lines(self):
        attrs=attribute_values(self.raw(filter='unconfigured'),'data.json')
        files=frozen_files('data.json',attrs,{'core.autocrlf':'true'},filter_required=True)
        self.assertIn(b'required = true',files['config']);self.assertNotIn(b'clean =',files['config']);self.assertNotIn(b'process =',files['config'])
        for config in ({'filter.unconfigured.clean':'run'},{'include.path':'secret'},{'core.autocrlf':'true\n[filter "bad"]'}):
            with self.assertRaises(InputAdmissionError):frozen_files('data.json',attrs,config)
        with self.assertRaises(InputAdmissionError):frozen_files('data.json',{**attrs,'filter':'bad process=program'},{})
        with self.assertRaises(InputAdmissionError):frozen_files('data.json',attrs,{},filter_required=1)
    def test_actual_builtin_hashes_statuses_and_raw_stderr_match_in_private_Git_context(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old)
        with tempfile.TemporaryDirectory(prefix='axiom-prefix-context-tests-') as directory:
            parent=Path(directory).resolve()
            for n,(name,attrs,content,settings) in enumerate((('CRLF','text eol=lf',b'a\r\nb\r\n',{}),('indexCRLF','',b'a\r\nb\r\n',{'core.autocrlf':'true'}),('ident','ident',b'$Id: explicit expansion$\n',{}),('UTF16','text working-tree-encoding=UTF-16LE','a\nb\n'.encode('utf-16-le'),{}),('safecrlf','text eol=lf',b'a\r\nb\r\n',{'core.safecrlf':'true'}))):
                with self.subTest(name=name):
                    root=parent/name;root.mkdir();self.assertEqual(git(root,'init','--initial-branch=fixture').returncode,0)
                    path='data[one].json';target=root/path;target.write_bytes(content if name=='indexCRLF' else b'initial\n');self.assertEqual(git(root,'add','--',path).returncode,0)
                    # Git quoted patterns need escaped backslashes, generated by the same frozen pattern serializer below.
                    from lib.accepted_prefix_git_context import attribute_pattern
                    if attrs:(root/'.gitattributes').write_text(attribute_pattern(path)+' '+attrs+'\n')
                    target.write_bytes(content)
                    for key,value in settings.items():self.assertEqual(git(root,'config',key,value).returncode,0)
                    original=git(root,'hash-object','--',str(target));raw=git(root,'check-attr','-z',*ATTRIBUTES,'--',path);self.assertEqual(raw.returncode,0)
                    effective=attribute_values(raw.stdout,path);aux=parent/('frozen-'+str(n));aux.mkdir();(aux/'refs/heads').mkdir(parents=True);(aux/'info').mkdir();(aux/'objects').symlink_to(root/'.git/objects',target_is_directory=True);shutil.copyfile(root/'.git/index',aux/'index')
                    for file,value in frozen_files(path,effective,settings).items():(aux/file).write_bytes(value)
                    frozen=git(root,'hash-object','--',str(target),aux=aux)
                    self.assertEqual((frozen.returncode,frozen.stdout,frozen.stderr),(original.returncode,original.stdout,original.stderr))
                    plain=git(root,'hash-object','--no-filters','--',str(target));self.assertNotEqual((plain.returncode,plain.stdout,plain.stderr),(original.returncode,original.stdout,original.stderr))
                    # No native captured stability/cleanup claim: this proves only frozen builtin behavior.

class PrefixRecordedReadTransport(unittest.TestCase):
    def setUp(self):
        fixture_case=fixture.WholeReadTransport();fixture_case.setUp();self.addCleanup(fixture_case.doCleanups);self.fixture=fixture_case;self.root=fixture_case.data;self.context=context(self.root)
    def test_real_local_Git_text_and_binary_nonzero_results_replay_after_source_removal(self):
        self.assertEqual(git(self.root,'init','--initial-branch=fixture').returncode,0)
        profile=LegacyAcceptedPrefixProtocol(self.context);commands=[('git-tree',['git','ls-files','--',*profile.ledgers]),('git-run',['git','cat-file','-e',BASE+':'+profile.profiles[1]])]
        record,owner=self.fixture.owner();port=NativeAcceptedPrefixTransport(owner,self.root,self.context,emit_stderr=lambda ref:self.fail('Binary run stderr is captured'),environment=environment());results=[]
        for kind,command in commands:
            original=subprocess.run(command,cwd=self.root,env=environment(),capture_output=True)
            actual=port.check_output(command,cwd=self.root,text=True) if kind=='git-tree' else port.run(command,cwd=self.root,capture_output=True)
            if kind=='git-tree':self.assertEqual(actual,original.stdout.decode())
            else:self.assertEqual((actual.args,actual.returncode,actual.stdout,actual.stderr),(original.args,original.returncode,original.stdout,original.stderr));self.assertNotEqual(actual.returncode,0)
            results.append(actual)
        record.finish('complete',{'exit_code':0},owner.touched);_,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()}
        shutil.rmtree(self.root);replay=ReplayIO(events,lambda ref:cache[ref['sha256']],'private-candidate',str(self.root));pure=ReplayAcceptedPrefixTransport(replay,self.root,self.context,emit_stderr=lambda ref:self.fail('No inherited stderr'))
        with patch('subprocess.Popen',side_effect=AssertionError('No native Git')),patch('os.open',side_effect=AssertionError('No input')):
            self.assertEqual(pure.check_output(commands[0][1],cwd=self.root,text=True),results[0]);self.assertEqual(vars(pure.run(commands[1][1],cwd=self.root,capture_output=True)),vars(results[1]));replay.finish()
        for name,raw in cache.items():blob({'sha256':name,'bytes':len(raw)})
        self.assertTrue(closed())
    def test_missing_hash_context_marks_incomplete_before_any_process_can_execute(self):
        record,owner=self.fixture.owner();port=NativeAcceptedPrefixTransport(owner,self.root,self.context,emit_stderr=lambda ref:None,environment=environment());command=['git','hash-object','--',self.context.ledger.PROFILE_PATH]
        with patch('subprocess.Popen',side_effect=AssertionError('No Git execution')):
            with self.assertRaisesRegex(InputAdmissionError,'isolated_hash_context_required'):port.check_output(command,cwd=self.root,text=True)
        self.assertTrue(record.capture_incomplete)
