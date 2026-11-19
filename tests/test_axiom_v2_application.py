"""Fresh V2 state and shared real CLI execution; no native credentials/authority."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.v2_application import initialize, instance, run, set_option
from test_portable_runtime import OPA
import axiom_v2


class Instances(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.path=self.base/'instance-a'

    def create(self):return initialize(self.path,opa=OPA,development=True)

    def test_fresh_instances_have_distinct_nodes_keys_and_private_state(self):
        first=self.create();other=self.base/'instance-b'
        second=initialize(other,opa=OPA,port=8876,development=True)
        self.assertNotEqual(first['node_id'],second['node_id'])
        self.assertNotEqual((self.path/'workbench-key.json').read_bytes(),(other/'workbench-key.json').read_bytes())
        self.assertEqual(instance(self.path)[1],first)
        for relative in ('instance.json','consumer.json','workbench-key.json'):
            self.assertEqual((self.path/relative).stat().st_mode&0o077,0)
        self.assertEqual(json.loads((self.path/'consumer.json').read_text())['mode'],'paused')

    def test_existing_root_and_v1_data_are_not_imported_or_overwritten(self):
        self.path.mkdir();old=self.path/'queue.sqlite3';old.write_bytes(b'untouched V1 fixture')
        with self.assertRaisesRegex(ValueError,'fresh_v2_instance_required'):self.create()
        self.assertEqual(old.read_bytes(),b'untouched V1 fixture')

    def test_old_generation_or_changed_runtime_cannot_be_resumed(self):
        self.create();p=self.path/'instance.json';original=json.loads(p.read_text())
        for key,value in (('product','axiom-v1'),('runtime_source_digest','0'*64)):
            changed={**original,key:value};p.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'source_or_generation_mismatch'):instance(self.path)

    def test_changed_or_unapproved_opa_is_rejected(self):
        binary=self.base/'fake-opa';binary.write_bytes(b'not a real OPA binary')
        with self.assertRaisesRegex(ValueError,'pinned_opa_required'):
            initialize(self.path,opa=binary,development=True)

    def test_real_paused_collector_status_uses_only_its_fresh_sqlite(self):
        self.create();out=io.StringIO()
        with redirect_stdout(out),patch('lib.providers.transports.Reader.get',side_effect=AssertionError('no native reads')):
            self.assertEqual(run('collector',['status'],instance_path=self.path),0)
        result=json.loads(out.getvalue())
        self.assertTrue(result['paused']);self.assertFalse(result['publisher_active'])
        self.assertEqual(result['counts'],{})
        self.assertTrue((self.path/'state/consumers/queue.sqlite3').is_file())

    def test_path_override_and_duplicate_options_cannot_target_v1_state(self):
        self.create();target=self.path/'state/consumers';foreign=self.base/'v1'
        for arguments in (['--root',str(foreign)],['--root',str(target),'--root',str(foreign)],
                          ['--root='+str(target),'--root='+str(foreign)]):
            with self.assertRaisesRegex(ValueError,'path_override_rejected'):
                run('collector',['status',*arguments],instance_path=self.path)
        self.assertFalse(foreign.exists())
        self.assertFalse((target/'queue.sqlite3').exists())

    def test_legacy_migration_entrypoints_are_not_exposed(self):
        self.create()
        for action in ('migrate-legacy','restore-legacy'):
            with self.assertRaisesRegex(ValueError,'retired_in_v2'):
                run('evidence',[action],instance_path=self.path)
        with self.assertRaisesRegex(ValueError,'not_supported'):
            run('consumer_intake.py',[],instance_path=self.path)

    def test_development_instance_cannot_enable_collection_or_publication(self):
        self.create();p=self.path/'consumer.json';config=json.loads(p.read_text())
        config['mode']='publish';p.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError,'must_remain_paused'):
            run('collector',['work'],instance_path=self.path)
        with self.assertRaisesRegex(ValueError,'cannot_publish'):
            run('workbench',['--enable-pr'],instance_path=self.path)

    def test_workbench_uses_node_state_port_and_key_without_printing_it(self):
        settings=self.create();out=io.StringIO()
        def server(argv, *, application, access_key):
            self.assertEqual(argv[argv.index('--port')+1],'8875')
            self.assertEqual(application.state_dir, self.path.resolve()/'state/workbench')
            self.assertEqual(application.consumer_projection, self.path.resolve()/'projection')
            self.assertEqual(access_key, json.loads((self.path/'workbench-key.json').read_bytes())['key'])
            self.assertEqual(os.environ['AXIOM_WORKBENCH_KEY'], 'prior synthetic test key')
            self.assertFalse((ROOT/'.local/governance-workbench'/settings['node_id']).exists())
            return 0
        with patch.dict(os.environ,{'AXIOM_WORKBENCH_KEY':'prior synthetic test key'}),redirect_stdout(out),patch(
                'serve_governance_workbench.main',side_effect=server):
            self.assertEqual(run('workbench',[],instance_path=self.path),0)
            self.assertEqual(os.environ['AXIOM_WORKBENCH_KEY'],'prior synthetic test key')
        self.assertEqual(out.getvalue(),'')

    def test_cli_rejection_contains_only_redacted_diagnostic_code(self):
        out=io.StringIO()
        with redirect_stderr(out):self.assertEqual(axiom_v2.main(['collector','status']),2)
        self.assertEqual(json.loads(out.getvalue())['diagnostics'],['explicit_v2_instance_required'])

    def test_option_binding_is_idempotent_for_exact_repeated_paths(self):
        values=['--root','/private/a','--root=/private/a']
        self.assertEqual(set_option(values,'--root','/private/a'),values)
