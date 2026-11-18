"""Whole frozen-V1 release decisions; actual native tools are test fixtures only."""
from pathlib import Path
import ast
import copy
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.release_verification import ReleaseVerification
from lib.v2_boundary import violations
from lib.providers.release_references import ReleaseReferences
from lib.providers.release_verification import ReleaseVerificationEnvironment
from lib.release_replay import ReplayReleaseEnvironment

FIXTURE=ROOT/'tests/fixtures/v2-release-verification'
CONTRACT=json.loads((FIXTURE/'contract.json').read_bytes())
RAW=(FIXTURE/'release_integrity.py.txt').read_bytes()
assert CONTRACT['v1_reference']=='6b557fefe295b58272d2271326576ca3a3687197'
assert hashlib.sha256(RAW).hexdigest()==CONTRACT['source_sha256']=='518e60080d5e596c831d0d00b835ff0d2286c33af5c5ee0dbf8fdf9dd9b0ae98'
ORIGINAL=types.ModuleType('frozen_v1_release_integrity_reference')
ORIGINAL.__file__=str(FIXTURE/'release_integrity.py.txt')
exec(compile(RAW,ORIGINAL.__file__,'exec'),ORIGINAL.__dict__)

spec=importlib.util.spec_from_file_location('original_release_native_test_fixture',ROOT/'tests/test_release_integrity.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


class TestNativeEnvironment:
    """Explicit TEST-only native oracle harness, not the unfinished product port."""
    __test__=False
    def __init__(self,root):self.root=root;self.observations=[]
    def temporary_file(self,*args,**kwargs):return tempfile.NamedTemporaryFile(*args,**kwargs)
    def run(self,command,**kwargs):
        result=subprocess.run(command,timeout=15,**kwargs)
        self.observations.append((command,result.returncode,result.stdout,result.stderr))
        return result


class OriginalDecisionParityTests(fixture.ReleaseIntegrityTests):
    def verify(self):
        expected=ORIGINAL.verify_release_integrity(self.root,self.policy_path)
        self.environment=TestNativeEnvironment(self.root)
        actual=ReleaseVerification(self.environment).verify_release_integrity(self.root,self.policy_path)
        self.assertEqual(actual,expected)
        # Compare the complete original JSON wire as well as the whole object.
        self.assertEqual(json.dumps(actual,indent=2)+'\n',json.dumps(expected,indent=2)+'\n')
        return actual

    def test_default_root_and_policy_are_environment_data_not_global_product(self):
        expected=ORIGINAL.verify_release_integrity(self.root,self.policy_path)
        self.assertEqual(ReleaseVerification(TestNativeEnvironment(self.root)).verify_release_integrity(),expected)
        self.assertTrue((self.root/'.git').is_dir())

    def test_native_work_is_explicitly_injected(self):
        self.verify()
        commands=[row[0] for row in self.environment.observations]
        self.assertTrue(any(c[:2]==['git','verify-tag'] or 'verify-tag' in c for c in commands))
        self.assertTrue(any(c[:2]==['ssh-keygen','-lf'] for c in commands))
        self.assertTrue(any(c[:3]==['ssh-keygen','-Y','verify'] for c in commands))

    def test_policy_repository_mismatch_preserves_complete_original_report(self):
        policy=yaml.safe_load(self.policy_path.read_bytes());policy['repository_id']='other/repository'
        self.policy_path.write_text(yaml.safe_dump(policy))
        self.assertIn('Release integrity manifest repository differs from policy',self.verify()['verification_errors'])

    def test_untrusted_manifest_principal_preserves_whole_report(self):
        value=json.loads(self.manifest_path.read_bytes());value['signer_principal']='untrusted@example.invalid'
        self.manifest_path.write_text(json.dumps(value))
        self.assertIn('Release integrity manifest signer is not trusted',self.verify()['verification_errors'])

    def test_duplicate_legacy_record_preserves_original_error_and_decisions(self):
        value=json.loads(self.manifest_path.read_bytes());value['legacy_tags'].append(copy.deepcopy(value['legacy_tags'][0]))
        self.manifest_path.write_text(json.dumps(value))
        self.assertTrue(any('Duplicate or missing legacy tag record' in row for row in self.verify()['verification_errors']))

    def test_invalid_manifest_json_preserves_original_report(self):
        self.manifest_path.write_text('{"broken"')
        self.assertTrue(any('manifest is invalid' in row for row in self.verify()['verification_errors']))

    def test_missing_manifest_and_signature_preserve_original_safe_file_failures(self):
        original=self.manifest_path.read_bytes();self.manifest_path.unlink()
        self.assertTrue(any('missing or is a symlink' in row for row in self.verify()['verification_errors']))
        self.manifest_path.write_bytes(original)
        self.manifest_path.with_suffix('.json.sig').unlink()
        self.assertTrue(any('missing or is a symlink' in row for row in self.verify()['verification_errors']))

    def test_missing_checksum_artifact_preserves_original_error(self):
        (self.root/'releases/test/checksums.sha256').unlink()
        self.assertTrue(any('missing or is a symlink' in row for row in self.verify()['verification_errors']))

    def test_invalid_checksum_line_preserves_complete_report(self):
        (self.root/'releases/test/checksums.sha256').write_text('not-a-digest\n')
        self.assertTrue(any('Invalid checksum entry' in row for row in self.verify()['verification_errors']))

    def test_checksum_path_escape_preserves_original_rejection(self):
        (self.root/'releases/test/checksums.sha256').write_text('0'*64+'  ../outside\n')
        self.assertTrue(any('escapes the repository' in row for row in self.verify()['verification_errors']))

    def test_symlink_artifact_preserves_original_rejection(self):
        p=self.root/'releases/test/payload.txt';raw=p.read_bytes();p.unlink()
        outside=Path(self.temp.name)/'outside';outside.write_bytes(raw);p.symlink_to(outside)
        self.assertTrue(any('escapes the repository' in row for row in self.verify()['verification_errors']))

    def test_missing_native_tags_remain_reportable_not_a_new_blocking_exception(self):
        self.git('tag','-d',self.direct_tag,self.legacy_tag)
        result=self.verify();self.assertEqual(result['release_tags'],[])
        self.assertEqual(result['unverified_release_tags'],[self.legacy_tag])
        self.assertIsInstance(result['unverified_release_tags'],list)

    def test_lightweight_and_nested_names_retain_original_scope(self):
        self.git('-c','tag.gpgSign=false','tag','lightweight-baseline-v1')
        self.git('-c','tag.gpgSign=false','tag','-a','nested/release-baseline-v1','-m','nested')
        result=self.verify()
        self.assertIn('lightweight-baseline-v1',result['unverified_release_tags'])
        self.assertIn('nested/release-baseline-v1',result['unverified_release_tags'])

    def test_tag_pointing_to_another_tag_retains_original_peel_behavior(self):
        self.git('-c','tag.gpgSign=false','tag','-a','chained-baseline-v1',self.legacy_tag,'-m','tag chain')
        result=self.verify();row=next(r for r in result['tag_assessments'] if r['tag']=='chained-baseline-v1')
        self.assertEqual(row['target_commit_sha'],self.git('rev-parse',self.legacy_tag+'^{commit}').strip())

    def test_inactive_or_bad_fingerprint_preserve_original_exception(self):
        original=self.policy_path.read_bytes()
        for change in ('inactive','fingerprint'):
            with self.subTest(change=change):
                policy=yaml.safe_load(original)
                if change=='inactive':policy['direct_signature']['trusted_signers'][0]['status']='inactive'
                else:policy['direct_signature']['trusted_signers'][0]['fingerprint']='SHA256:incorrect'
                self.policy_path.write_text(yaml.safe_dump(policy))
                with self.assertRaises(ValueError) as expected:ORIGINAL.verify_release_integrity(self.root,self.policy_path)
                with self.assertRaises(ValueError) as actual:ReleaseVerification(TestNativeEnvironment(self.root)).verify_release_integrity()
                self.assertEqual(str(actual.exception),str(expected.exception))


class Sha256DecisionParityTests(OriginalDecisionParityTests):
    def git(self,*args):
        if args and args[0]=='init':args=('init','--object-format=sha256',*args[1:])
        return super().git(*args)


class NativeCapsuleParityTests(OriginalDecisionParityTests):
    def files(self):
        return {p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*')
            if p.is_file() and not p.is_symlink() and '.git' not in p.relative_to(self.root).parts}

    def verify(self):
        expected=ORIGINAL.verify_release_integrity(self.root,self.policy_path)
        references=ReleaseReferences(self.root).capture();files=self.files()
        area=Path(self.temp.name)/'native-work';area.mkdir(mode=0o700,exist_ok=True)
        with ReleaseVerificationEnvironment(self.root,files,references,area) as native:
            actual=ReleaseVerification(native).verify_release_integrity()
            self.assertEqual(actual,expected)
            self.assertEqual(json.dumps(actual,indent=2)+'\n',json.dumps(expected,indent=2)+'\n')
            metadata=copy.deepcopy(native.metadata);observations=copy.deepcopy(native.observations)
            capsule=native.capsule
        self.assertFalse(capsule.exists());self.assertTrue(observations)
        with patch('subprocess.Popen',side_effect=AssertionError('native replay forbidden')):
            replay=ReplayReleaseEnvironment(self.root,files,references,metadata,observations)
            self.assertEqual(ReleaseVerification(replay).verify_release_integrity(),actual);replay.finish()
        self.last_native=(references,files,metadata,observations,actual)
        return actual

    def test_native_work_is_explicitly_injected(self):
        self.verify();rows=self.last_native[3]
        self.assertTrue(all(row['process_started'] and row['error_type'] is None for row in rows))
        self.assertTrue(any(row['request']['stage']=='capsule-object' for row in rows))
        self.assertTrue(any(row['request'].get('request',{}).get('operation')=='verify-tag' for row in rows))

    def test_replay_survives_missing_caller_git_without_any_native_tool(self):
        self.verify();references,files,metadata,observations,expected=self.last_native
        (self.root/'.git').rename(Path(self.temp.name)/'removed-git')
        with patch('subprocess.Popen',side_effect=AssertionError('native replay forbidden')):
            replay=ReplayReleaseEnvironment(self.root,files,references,metadata,observations)
            self.assertEqual(ReleaseVerification(replay).verify_release_integrity(),expected);replay.finish()

    def test_replay_rejects_changed_tool_request_order_status_and_extra_rows(self):
        self.verify();references,files,metadata,original,expected=self.last_native
        changes=[lambda v:v[0].update(undeclared=True),lambda v:v[0].update(tool_sha256='0'*64),
            lambda v:v[0].update(returncode=True),lambda v:v[0].update(process_started=False),
            lambda v:v[0].update(error_type='TimeoutError'),lambda v:v[0].update(stdout_base64='!'),
            lambda v:v.reverse(),lambda v:v.append(copy.deepcopy(v[-1]))]
        for change in changes:
            with self.subTest(change=change):
                observations=copy.deepcopy(original);change(observations)
                with self.assertRaises(ValueError):
                    replay=ReplayReleaseEnvironment(self.root,files,references,metadata,observations)
                    ReleaseVerification(replay).verify_release_integrity();replay.finish()

    def test_source_config_and_ambient_values_do_not_supply_native_helpers(self):
        marker=Path(self.temp.name)/'never-executed';script=Path(self.temp.name)/'untrusted-helper'
        script.write_text('#!/bin/sh\n/usr/bin/touch '+str(marker)+'\nexit 1\n');script.chmod(0o700)
        self.git('config','gpg.ssh.program',str(script))
        references=ReleaseReferences(self.root).capture();area=Path(self.temp.name)/'isolated-native';area.mkdir(mode=0o700)
        with patch.dict(os.environ,{'AXIOM_RELEASE_SYNTHETIC_SECRET':'must-not-inherit'}):
            with ReleaseVerificationEnvironment(self.root,self.files(),references,area) as native:
                self.assertNotIn('AXIOM_RELEASE_SYNTHETIC_SECRET',native.environment)
                result=ReleaseVerification(native).verify_release_integrity()
        self.assertEqual(result['unverified_release_tags'],[]);self.assertFalse(marker.exists())


class Sha256NativeCapsuleParityTests(NativeCapsuleParityTests):
    def git(self,*args):
        if args and args[0]=='init':args=('init','--object-format=sha256',*args[1:])
        return super().git(*args)


class StructureTests(unittest.TestCase):
    def test_runtime_fingerprint_covers_each_release_core_and_native_module(self):
        import lib.portable.runtime as runtime
        paths=['scripts/lib/'+name for name in ('release_verification.py','release_reference_facts.py',
            'release_requests.py','release_replay.py','release_inputs.py','release_validation_application.py',
            'providers/release_references.py','providers/release_verification.py')]
        with tempfile.TemporaryDirectory() as temporary:
            copied=Path(temporary)/'product'
            shutil.copytree(ROOT,copied,ignore=shutil.ignore_patterns('.git','__pycache__','.DS_Store','.venv*'))
            with patch.object(runtime,'ROOT',copied):
                baseline=runtime.source_digest()
                for name in paths:
                    with self.subTest(module=name):
                        path=copied/name;original=path.read_bytes();path.write_bytes(original+b'\n# isolated fingerprint mutation\n')
                        self.assertNotEqual(runtime.source_digest(),baseline);path.write_bytes(original)
                        self.assertEqual(runtime.source_digest(),baseline)

    def test_all_ten_functions_are_exact_after_declared_environment_substitutions(self):
        original=ast.parse(RAW);names=set(CONTRACT['function_names'])
        class Ports(ast.NodeTransformer):
            def visit_Name(self,node):
                if isinstance(node.ctx,ast.Load):
                    if node.id in names:return ast.Attribute(ast.Name('self',ast.Load()),node.id,ast.Load())
                    if node.id in ('ROOT','DEFAULT_POLICY'):return ast.Attribute(ast.Name('self',ast.Load()),'root' if node.id=='ROOT' else 'policy_path',ast.Load())
                return node
            def visit_Attribute(self,node):
                node=self.generic_visit(node)
                if isinstance(node.value,ast.Name):
                    pair=(node.value.id,node.attr)
                    if pair in (('subprocess','run'),('tempfile','NamedTemporaryFile')):
                        return ast.Attribute(ast.Attribute(ast.Name('self',ast.Load()),'environment',ast.Load()),'run' if pair[1]=='run' else 'temporary_file',ast.Load())
                    if pair==('subprocess','CompletedProcess'):return ast.Name('object',ast.Load())
                return node
        tree=ast.parse((ROOT/'scripts/lib/release_verification.py').read_bytes());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
        methods={n.name:n for n in cls.body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(set(methods),names|{'__init__'});self.assertEqual(len(names),10)
        for node in original.body:
            if not isinstance(node,ast.FunctionDef):continue
            node.args.args.insert(0,ast.arg(arg='self'))
            if node.name=='verify_release_integrity':
                node.args.defaults[0]=ast.Constant(None)
                node.body.insert(1,ast.parse('if root is None: root = self.root').body[0])
            with self.subTest(function=node.name):self.assertEqual(ast.dump(Ports().visit(node)),ast.dump(methods[node.name]))

    def test_core_has_no_native_import_or_execution_capability(self):
        source=(ROOT/'scripts/lib/release_verification.py').read_text();self.assertEqual(violations('scripts/lib/release_verification.py',source),[])
        modules={n.name for node in ast.walk(ast.parse(source)) if isinstance(node,ast.Import) for n in node.names}
        self.assertFalse(modules&{'subprocess','tempfile','os','shutil'})


if __name__=='__main__':unittest.main()
