"""Actual Git metadata capture/replay, driver nonexecution and changing-input guards."""
from pathlib import Path
from unittest.mock import patch
import copy,hashlib,json,shutil,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from jsonschema import Draft202012Validator
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.accepted_prefix_metadata import capture_context,file_selection,file_value,ReplayGitInputs
from lib.providers.accepted_prefix_metadata import NativeGitInputs
from lib.providers.accepted_prefix_metadata_protocol import NativePrefixMetadataTransport,ReplayPrefixMetadataTransport,PrefixMetadataProtocol
from lib.providers.accepted_prefix_transport import AcceptedPrefixTransport
from lib.providers.synthetic_lifecycle_storage import read_record
from lib.synthetic_lifecycle_io import ReplayIO
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
import test_v2_personal_channel_transport as fixture
from test_v2_accepted_prefix_transport import git,environment

PROFILE='model/governance/lifecycle/synthetic-grs002-profile.json'
class PrefixContextCapture(unittest.TestCase):
    def setUp(self):
        case=fixture.WholeReadTransport();case.setUp();self.addCleanup(case.doCleanups);self.fixture=case;self.root=case.data
        self.assertEqual(git(self.root,'init','--initial-branch=fixture').returncode,0)
        p=self.root/PROFILE;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'{"explicit_fixture":true}\r\n');self.assertEqual(git(self.root,'add','--',PROFILE).returncode,0)
        self.assertEqual(git(self.root,'-c','user.name=Prefix fixture','-c','user.email=prefix@example.invalid','commit','-m','Explicit test data').returncode,0)
        self.record,self.owner=case.owner()
    def port(self):return AcceptedPrefixTransport(self.owner,self.root,RepositoryLifecycle(self.root,validator_class=Draft202012Validator),emit_stderr=lambda ref:None,environment=environment())
    def metadata(self,root,owner,native):
        return lambda path,driver:NativePrefixMetadataTransport(owner,root,path,driver=driver,environment=environment()) if native else ReplayPrefixMetadataTransport(owner,root,path,driver=driver)
    def replay_metadata(self,root):
        context=capture_context(str(root),PROFILE,self.metadata(root,self.owner,True));selected=file_selection(str(root),PROFILE,context);inputs=NativeGitInputs(self.owner,selected);values={role:inputs.read(role) for role in selected}
        self.record.finish('complete',{'exit_code':0},self.owner.touched);_,_,_,events,blob,closed=read_record(self.record.root);cache={p.name:p.read_bytes() for p in self.record.blobs.iterdir()};seen=set()
        def inert(ref):
            raw=cache[ref['sha256']];assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'];seen.add(ref['sha256']);return raw
        shutil.rmtree(root);pure=ReplayIO(events,inert,'private-candidate',str(root))
        with patch('subprocess.Popen',side_effect=AssertionError('No metadata Git')),patch('os.open',side_effect=AssertionError('No Git or source files')):
            self.assertEqual(capture_context(str(root),PROFILE,self.metadata(root,pure,False)),context);replay=ReplayGitInputs(pure,selected);self.assertEqual({role:replay.read(role) for role in selected},values);pure.finish()
        self.assertEqual(seen,set(cache))
        for name,raw in cache.items():blob({'sha256':name,'bytes':len(raw)})
        self.assertTrue(closed());return context
    def test_standard_Git_context_and_bounded_source_index_replay_without_inputs(self):self.replay_metadata(self.root)
    def test_split_index_and_real_linked_worktree_common_directory_bindings(self):
        self.assertEqual(git(self.root,'update-index','--split-index').returncode,0);result=self.replay_metadata(self.root);self.assertTrue(result['shared'])
        self.setUp();worktree=self.root.parent/'linked-prefix-source';self.assertEqual(git(self.root,'worktree','add','--detach',str(worktree),'HEAD').returncode,0)
        # owner.cwd is the original test fixture; the closed metadata protocol
        # always binds the actual Git query cwd to the selected linked source.
        result=self.replay_metadata(worktree);self.assertNotEqual(result['gitdir'],result['common']);self.assertEqual(result['common'],str(self.root/'.git'))
    def test_selected_clean_and_process_driver_configuration_never_executes_or_retains_command_bodies(self):
        for suffix in ('clean','process'):
            with self.subTest(suffix=suffix):
                if suffix!='clean':self.setUp()
                marker=self.root/'MUST-NOT-EXIST';body='echo DO-NOT-EXECUTE > '+str(marker)
                self.assertEqual(git(self.root,'config','filter.selected.'+suffix,body).returncode,0);(self.root/'.gitattributes').write_text(PROFILE+' filter=selected\n')
                with self.assertRaisesRegex(InputAdmissionError,'external_clean_or_process'):self.port().check_output(['git','hash-object','--',PROFILE],cwd=self.root,text=True)
                self.assertFalse(marker.exists());self.assertTrue(self.record.capture_incomplete)
                self.assertTrue(all(body.encode() not in p.read_bytes() for p in self.record.blobs.iterdir()))
    def test_unselected_configured_filter_does_not_change_original_hash_or_trigger_program(self):
        marker=self.root/'MUST-NOT-EXIST';body='echo DO-NOT-EXECUTE > '+str(marker);self.assertEqual(git(self.root,'config','filter.unselected.clean',body).returncode,0)
        original=git(self.root,'hash-object','--',PROFILE);self.assertEqual(original.returncode,0)
        self.assertEqual(self.port().check_output(['git','hash-object','--',PROFILE],cwd=self.root,text=True),original.stdout.decode());self.assertFalse(marker.exists());self.assertFalse(self.record.capture_incomplete)
        self.assertTrue(all(body.encode() not in p.read_bytes() for p in self.record.blobs.iterdir()))
    def test_changed_attributes_config_index_and_source_after_hash_are_incomplete_and_auxiliary_is_quarantined(self):
        for kind in ('attributes','configuration','index','source'):
            with self.subTest(kind=kind):
                if kind!='attributes':self.setUp()
                port=self.port();factory=port.new_port
                def new_port(scope=None):
                    current=factory(scope)
                    if scope is not None:
                        old=current.check_output
                        def race(*args,**kwargs):
                            value=old(*args,**kwargs)
                            if kind=='attributes':(self.root/'.gitattributes').write_text(PROFILE+' -text\n')
                            elif kind=='configuration':self.assertEqual(git(self.root,'config','core.autocrlf','true').returncode,0)
                            elif kind=='index':
                                (self.root/'explicit-new.json').write_bytes(b'{}\n');self.assertEqual(git(self.root,'add','explicit-new.json').returncode,0)
                            else:(self.root/PROFILE).write_bytes(b'Explicit changed source\n')
                            return value
                        current.check_output=race
                    return current
                port.new_port=new_port
                with self.assertRaisesRegex(InputAdmissionError,'context_changed|inputs_changed'):port.check_output(['git','hash-object','--',PROFILE],cwd=self.root,text=True)
                self.assertTrue(self.record.capture_incomplete);scopes=list((self.owner.private_state/'state/accepted-prefix-hash').iterdir());self.assertEqual(len(scopes),1);self.assertTrue((scopes[0]/'HEAD').exists())
    def test_closed_metadata_contract_never_allows_config_bodies_credentials_writes_or_unbound_paths(self):
        profile=PrefixMetadataProtocol(PROFILE,'selected')
        for command in (['git','config','--list'],['git','config','--get','credential.helper'],['git','config','--get','filter.selected.clean'],['git','config','filter.selected.clean','write'],['git','check-attr','filter','--','outside']):
            with self.assertRaises(InputAdmissionError):profile.request('git-run',{'command':command,'cwd':str(self.root),'capture_output':True},str(self.root),str(self.root))
    def test_resealed_file_metadata_content_identity_and_capture_flags_fail_closed(self):
        selected={'source':str(self.root/PROFILE)};NativeGitInputs(self.owner,selected).read('source')
        self.record.finish('complete',{'exit_code':0},self.owner.touched);_,_,_,events,blob,_=read_record(self.record.root);wire=json.loads(blob(events[3]['value']));spec=wire['selection']
        for change in (lambda w:w.update(schema_version=True),lambda w:w['before'].update(nlink=2),lambda w:w['content'].update(bytes=True),lambda w:w['before'].update(identity=[True,1]),lambda w:w['after'].update(bytes=0),lambda w:w['selection'].update(role='index')):
            bad=copy.deepcopy(wire);change(bad)
            with self.assertRaises(IntegrityError):file_value(bad,spec,blob)

    def test_empty_builtin_setting_and_empty_filter_attribute_preserve_original_Git_semantics(self):
        self.assertEqual(git(self.root,'config','core.eol','').returncode,0)
        (self.root/'.gitattributes').write_text(PROFILE+' text eol=lf filter=\n')
        old=git(self.root,'hash-object','--',PROFILE);self.assertEqual(old.returncode,0,old.stderr)
        actual=self.port().check_output(['git','hash-object','--',PROFILE],cwd=self.root,text=True)
        self.assertEqual(actual,old.stdout.decode());self.assertFalse(self.record.capture_incomplete)
