"""Actual sparse Git admission, closed file inventory and isolated install failures."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.runtime_package import git
from lib.v2_distribution import restrict_source, verify_source, install
from lib.v2_source import active_fingerprints, selected_paths
from lib.v2_boundary import local_dependencies
from lib.v2_application import initialize
from test_portable_runtime import OPA


class Distribution(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name);self.root=self.base/'source';self.root.mkdir()
        files={'scripts/app.py':'print("neutral fixture")\n',
               'scripts/lib/providers/__init__.py':'', 'scripts/v1.py':'print("retired fixture")\n',
               'docs/fixture.md':'historical data\n'}
        boundary={'schema_version':2,'core_files':['scripts/app.py'],'composition':['scripts/ports.py'],
                  'adapters':'scripts/lib/providers','compatibility_facades':['scripts/facade.py'],
                  'browser_core':[],'verification':[]}
        files['scripts/ports.py']=''
        files['scripts/facade.py']='import sys\nfrom lib.providers import context as implementation\n'
        contract={'schema_version':2,'python_files':['scripts/app.py','scripts/ports.py','scripts/lib/providers/__init__.py'],
                  'data_roots':['config','docs'],'data_files':[],
                  'retired_entrypoints':['scripts/v1.py','scripts/facade.py']}
        files['config/axiom-v2-boundaries.json']=json.dumps(boundary)
        files['config/axiom-v2-distribution.json']=json.dumps(contract)
        for name,content in files.items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
        git(self.root,'init','--template=','-q');git(self.root,'add','.')
        git(self.root,'-c','user.name=AXIOM test','-c','user.email=test@localhost','commit','-qm','synthetic distribution fixture')

    def test_exact_commit_and_active_bytes_survive_while_v1_files_are_physically_absent(self):
        revision=git(self.root,'rev-parse','HEAD');before=active_fingerprints(self.root)
        self.assertEqual(restrict_source(self.root),before)
        self.assertEqual(git(self.root,'rev-parse','HEAD'),revision)
        self.assertEqual(git(self.root,'status','--porcelain'),b'')
        self.assertFalse((self.root/'scripts/v1.py').exists())
        self.assertFalse((self.root/'scripts/facade.py').exists())
        self.assertTrue((self.root/'docs/fixture.md').is_file())
        self.assertEqual(active_fingerprints(self.root),before)
        verify_source(self.root)

    def test_undeclared_executable_cannot_be_added_to_runtime(self):
        restrict_source(self.root);(self.root/'scripts/hidden.py').write_text('print("unexpected")')
        with self.assertRaisesRegex(ValueError,'undeclared_v2_runtime_file'):verify_source(self.root)

    def test_core_provider_import_is_rejected_after_sparse_selection(self):
        restrict_source(self.root);(self.root/'scripts/app.py').write_text('import requests\n')
        with self.assertRaisesRegex(ValueError,'architecture_boundary_failed'):verify_source(self.root)

    def test_existing_or_dirty_source_cannot_be_restricted(self):
        (self.root/'scripts/app.py').write_text('changed')
        with self.assertRaisesRegex(ValueError,'clean_admitted_source_required'):restrict_source(self.root)

    def test_symlink_and_missing_active_dependency_fail_closed(self):
        target=self.root/'scripts/app.py';target.unlink()
        with self.assertRaisesRegex(ValueError,'missing_v2_distribution_file'):selected_paths(self.root)
        target.symlink_to(self.root/'scripts/v1.py')
        with self.assertRaisesRegex(ValueError,'unsafe_v2_boundary_source'):selected_paths(self.root)

    def test_existing_prefix_preserves_v1_bytes_before_package_is_opened(self):
        prefix=self.base/'v1';prefix.mkdir();(prefix/'key').write_text('synthetic V1 fixture')
        with self.assertRaisesRegex(ValueError,'fresh_v2_installation_required'):
            install(self.base/'not-opened.zip','0'*64,prefix,sys.executable)
        self.assertEqual((prefix/'key').read_text(),'synthetic V1 fixture')

    def test_interrupted_initialization_has_no_admission_marker(self):
        target=self.base/'instance'
        from lib.consumer_intake_store import atomic_json
        def interrupted(path,value):
            if path.name=='workbench-key.json':raise OSError('injected filesystem failure')
            atomic_json(path,value)
        with patch('lib.v2_application.atomic_json',side_effect=interrupted):
            with self.assertRaises(OSError):initialize(target,opa=OPA,development=True)
        self.assertFalse((target/'instance.json').exists())
        with self.assertRaisesRegex(ValueError,'fresh_v2_instance_required'):
            initialize(target,opa=OPA,development=True)

    def test_duplicate_instance_json_keys_are_not_accepted(self):
        from lib.v2_application import instance
        target=self.base/'instance';initialize(target,opa=OPA,development=True)
        path=target/'instance.json';content=path.read_text();path.write_text('{"product":"axiom-v1",'+content[1:])
        with self.assertRaisesRegex(ValueError,'duplicate_json_key'):instance(target)


class RepositoryInventory(unittest.TestCase):
    def test_every_top_level_python_entrypoint_is_classified(self):
        policy=json.loads((ROOT/'config/axiom-v2-distribution.json').read_text())
        actual={str(p.relative_to(ROOT)) for p in (ROOT/'scripts').glob('*.py')}
        active={p for p in policy['python_files'] if p.count('/')==1}
        retired={p for p in policy['retired_entrypoints'] if p.count('/')==1}
        self.assertEqual(actual,active|retired);self.assertFalse(active&retired)

    def test_active_local_imports_are_in_the_reviewed_installation_closure(self):
        policy=json.loads((ROOT/'config/axiom-v2-distribution.json').read_text())
        active=set(policy['python_files'])
        for name in active:
            self.assertFalse(local_dependencies(ROOT,name)-active,name)
        selected=set(selected_paths(ROOT))
        self.assertFalse(selected&set(policy['retired_entrypoints']))
