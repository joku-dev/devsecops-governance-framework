"""Exact Git identity and offline admission boundaries; no network or source deployment."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.runtime_package import build,admit,digest,git,prepare_environment


class RuntimePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.repo=self.root/'repo';self.repo.mkdir()
        (self.repo/'scripts').mkdir()
        for path in ('scripts/validation-toolchain.env','scripts/opa-download-sources.json','requirements-validation.lock'):
            shutil.copyfile(ROOT/path,self.repo/path)
        (self.repo/'readme.txt').write_text('Exact committed source\n')
        (self.repo/'runner.sh').write_text('#!/bin/sh\nexit 0\n');(self.repo/'runner.sh').chmod(0o755)
        git(self.repo,'init','--template=','-q');git(self.repo,'add','.')
        git(self.repo,'-c','user.name=Synthetic fixture','-c','user.email=fixture@localhost','-c','commit.gpgsign=false',
            'commit','-qm','Exact synthetic package source')
        self.revision=git(self.repo,'rev-parse','HEAD').decode().strip()
        self.package=self.root/'runtime.zip'

    def create(self,**kwargs):return build(self.repo,self.revision,self.package,**kwargs)

    def test_deterministic_package_excludes_worktree_changes_and_untracked_private_state(self):
        first=self.create();before=self.package.read_bytes()
        (self.repo/'readme.txt').write_text('Uncommitted local draft\n')
        (self.repo/'secret.pem').write_text('untracked-secret')
        (self.repo/'.local').mkdir();(self.repo/'.local/private.json').write_text('{"secret":"untracked"}')
        other=self.root/'second.zip';second=build(self.repo,self.revision,other)
        self.assertEqual(before,other.read_bytes());self.assertEqual(first,second)
        with zipfile.ZipFile(other) as z:
            self.assertEqual(z.read('source/readme.txt'),b'Exact committed source\n')
            self.assertFalse(any('secret' in name or '.local' in name for name in z.namelist()))

    def test_admission_reconstructs_original_commit_tree_modes_and_clean_worktree(self):
        created=self.create();target=self.root/'admitted';manifest=admit(self.package,created['sha256'],target)
        source=target/'source'
        self.assertEqual(git(source,'rev-parse','HEAD').decode().strip(),self.revision)
        self.assertEqual(git(source,'rev-parse','HEAD^{tree}').decode().strip(),created['source_tree'])
        self.assertEqual(git(source,'cat-file','commit','HEAD'),git(self.repo,'cat-file','commit','HEAD'))
        self.assertEqual(git(source,'status','--porcelain'),b'')
        self.assertEqual((source/'runner.sh').stat().st_mode&0o777,0o755)
        self.assertEqual(manifest['source_commit'],self.revision)
        self.assertEqual((source/'.git/shallow').read_text(),self.revision+'\n')

    def test_independent_hash_is_checked_before_extraction_or_git_execution(self):
        self.create();target=self.root/'untrusted'
        with patch('lib.runtime_package.git',side_effect=AssertionError('must not execute git')):
            with self.assertRaisesRegex(ValueError,'checksum'):admit(self.package,'0'*64,target)
        self.assertFalse(target.exists())

    def rewrite_package(self,mutate):
        with zipfile.ZipFile(self.package) as z:members={name:z.read(name) for name in z.namelist()}
        mutate(members)
        replacement=self.root/'rewritten.zip'
        with zipfile.ZipFile(replacement,'w',compression=zipfile.ZIP_STORED) as z:
            for name,content in members.items():z.writestr(name,content)
        return replacement

    def test_resigned_archive_with_changed_source_cannot_keep_original_git_identity(self):
        self.create()
        def alter(members):
            members['source/readme.txt']=b'Altered source\n';manifest=json.loads(members['manifest.json'])
            row=next(row for row in manifest['files'] if row['path']=='source/readme.txt')
            row.update(size=len(members[row['path']]),sha256=hashlib.sha256(members[row['path']]).hexdigest())
            members['manifest.json']=json.dumps(manifest).encode()
        replacement=self.rewrite_package(alter)
        with self.assertRaisesRegex(ValueError,'git_blob_mismatch'):admit(replacement,digest(replacement),self.root/'bad-source')

    def test_unsafe_archive_and_unlisted_members_are_rejected(self):
        self.create()
        for name in ('../escape','unlisted-private.txt'):
            replacement=self.rewrite_package(lambda members:members.update({name:b'unsafe'}))
            with self.assertRaises(ValueError):admit(replacement,digest(replacement),self.root/('out-'+str(len(name))))
            replacement.unlink()
        self.assertFalse((self.root/'escape').exists())

    def test_missing_prepared_dependencies_fail_without_network_or_environment(self):
        created=self.create();target=self.root/'admitted';admit(self.package,created['sha256'],target)
        with patch('lib.runtime_package.subprocess.run',side_effect=AssertionError('no subprocess needed')):
            with self.assertRaisesRegex(ValueError,'not_prepared'):
                prepare_environment(target,self.root/'venv',sys.executable,package=self.package,expected_sha256=created['sha256'])
        self.assertFalse((self.root/'venv').exists())

    def test_mutated_admission_manifest_cannot_become_dependency_authority(self):
        created=self.create();target=self.root/'admitted';admit(self.package,created['sha256'],target)
        manifest=json.loads((target/'manifest.json').read_text());manifest['prepared_dependencies']=True
        (target/'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'binding_changed'):
            prepare_environment(target,self.root/'venv',sys.executable,package=self.package,expected_sha256=created['sha256'])

    def test_untracked_import_shadow_cannot_enter_admitted_source_before_environment_preparation(self):
        created=self.create();target=self.root/'admitted';admit(self.package,created['sha256'],target)
        (target/'source/jsonschema.py').write_text('raise RuntimeError("untracked import shadow")')
        with self.assertRaisesRegex(ValueError,'file_set_changed'):
            prepare_environment(target,self.root/'venv',sys.executable,package=self.package,expected_sha256=created['sha256'])
        self.assertFalse((self.root/'venv').exists())

    def test_unsigned_unknown_opa_and_unlocked_wheels_are_never_executed_or_bundled(self):
        fake=self.root/'opa';fake.write_text('#!/bin/sh\ntouch SHOULD_NOT_RUN\n');fake.chmod(0o755)
        with self.assertRaisesRegex(ValueError,'opa_checksum'):self.create(opa=fake)
        wheels=self.root/'wheels';wheels.mkdir();(wheels/'unapproved-1.0-py3-none-any.whl').write_bytes(b'not hash-locked')
        with self.assertRaisesRegex(ValueError,'wheel_not'):self.create(wheelhouse=wheels)
        self.assertFalse((self.repo/'SHOULD_NOT_RUN').exists())

    def test_tracked_private_material_or_symlink_cannot_silently_change_exact_source_scope(self):
        for kind in ('secret.pem','symlink'):
            path=self.repo/kind
            if kind=='symlink':path.symlink_to('readme.txt')
            else:path.write_text('tracked synthetic private key')
            git(self.repo,'add',kind)
            git(self.repo,'-c','user.name=Fixture','-c','user.email=fixture@localhost','-c','commit.gpgsign=false','commit','-qm','Invalid package fixture')
            revision=git(self.repo,'rev-parse','HEAD').decode().strip()
            with self.assertRaises(ValueError):build(self.repo,revision,self.root/(kind+'.zip'))
            git(self.repo,'rm',kind);git(self.repo,'-c','user.name=Fixture','-c','user.email=fixture@localhost','-c','commit.gpgsign=false','commit','-qm','Remove invalid fixture')

    def test_partial_admission_cannot_overwrite_existing_root(self):
        created=self.create();target=self.root/'existing';target.mkdir();(target/'keep').write_text('unchanged')
        with self.assertRaisesRegex(ValueError,'fresh_package_root'):admit(self.package,created['sha256'],target)
        self.assertEqual((target/'keep').read_text(),'unchanged')
