"""Portable service configuration, projection and deployment selection boundaries."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from jinja2 import Environment,StrictUndefined
except ImportError:
    Environment=StrictUndefined=None

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import portable_consumer_intake as cli
import deploy_vm
from lib.consumer_view import read_projection
from lib.consumer_intake_store import atomic_json
from lib.portable_intake.controller import Queue
from lib.portable_intake.store import Store


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.config={'schema_version':1,'mode':'paused','registry':str(ROOT/'config/portable-consumer-profiles.json'),
            'credentials_directory':'systemd','request_budget':300,'node_id':'a'*32}
        self.path=self.root/'operator.json';atomic_json(self.path,self.config)

    def test_private_configuration_and_service_credential_directory(self):
        with patch.dict(os.environ,{'CREDENTIALS_DIRECTORY':str(self.root/'service-credentials')}):
            value,profiles=cli.configuration(self.path)
            self.assertEqual(profiles,[]);self.assertEqual(value['credentials_directory'],str(self.root/'service-credentials'))
        self.path.chmod(0o644)
        with self.assertRaises(ValueError):cli.configuration(self.path)

    def test_operator_cannot_select_unreviewed_registry_or_unknown_mode(self):
        for field,value in [('registry','/private/tmp/alternative.json'),('mode','approved'),('node_id','generic-host'),('request_budget',100000)]:
            changed={**self.config,field:value};atomic_json(self.path,changed)
            with patch.dict(os.environ,{'CREDENTIALS_DIRECTORY':str(self.root)}),self.assertRaises(ValueError):cli.configuration(self.path)

    def test_paused_service_makes_no_provider_call_and_workbench_reads_allowlist(self):
        operations=self.root/'private';view=self.root/'public'
        with patch.dict(os.environ,{'CREDENTIALS_DIRECTORY':str(self.root)}),patch.object(cli,'central_operations') as central:
            self.assertEqual(cli.main(['work','--config',str(self.path),'--root',str(operations),'--projection',str(view)]),0)
            central.assert_not_called()
        data=read_projection(view)
        self.assertEqual(data['engine'],'portable-v1');self.assertEqual(data['mode'],'paused')
        self.assertEqual(data['jobs'],[]);self.assertIsNone(data['accepted'])
        self.assertEqual((view/'consumers.json').stat().st_mode&0o777,0o640)
        self.assertEqual(operations.stat().st_mode&0o777,0o700)

    def test_restored_host_binding_holds_work_but_allows_paused_status(self):
        operations=self.root/'private';operations.mkdir(mode=0o700)
        store=Store(operations);queue=Queue(store)
        queue.put('node_binding',{'node_id':'a'*32,'host_digest':'restored-other-machine'})
        store.close()
        atomic_json(self.path,{**self.config,'mode':'shadow'})
        with patch.dict(os.environ,{'CREDENTIALS_DIRECTORY':str(self.root)}):
            with self.assertRaisesRegex(ValueError,'restored_node'):cli.main(['poll','--config',str(self.path),'--root',str(operations)])
            self.assertEqual(cli.main(['status','--config',str(self.path),'--root',str(operations)]),0)

    def test_publisher_config_cannot_enable_source_unconfigured_operations(self):
        operations=self.root/'private';store=Store(operations);self.addCleanup(store.close)
        with self.assertRaisesRegex(cli.AccessFailure,'central_not_configured'):
            cli.central_operations(Queue(store),[],{**self.config,'mode':'publish'},None,at=1)

    def test_application_drift_is_reported_in_public_projection_even_when_work_fails(self):
        operations=self.root/'private';view=self.root/'public';atomic_json(self.path,{**self.config,'mode':'shadow'})
        with patch.dict(os.environ,{'CREDENTIALS_DIRECTORY':str(self.root)}),patch.object(cli,'work') as worker,patch.object(cli,'central_operations',side_effect=cli.AccessFailure('application_update_required')):
            with self.assertRaisesRegex(cli.AccessFailure,'application_update_required'):
                cli.main(['work','--config',str(self.path),'--root',str(operations),'--projection',str(view)])
            worker.assert_not_called()
        self.assertEqual(read_projection(view)['sync_error'],'application_update_required')

    @unittest.skipIf(Environment is None,'Template rendering runs in the pinned deployment environment')
    def test_portable_template_exposes_publish_credentials_only_to_worker(self):
        environment=Environment(undefined=StrictUndefined)
        template=environment.from_string((ROOT/'infra/ansible/templates/axiom-consumer.service.j2').read_text())
        for operation in ('poll','work'):
            rendered=template.render(consumer_operation=operation,vm_consumer_engine='portable-v1',vm_repo='/srv/axiom/repository',
                vm_venv='/srv/axiom/venvs/pin',vm_consumer_user='axiom-intake',vm_user='axiom',
                vm_consumer_root='/var/lib/axiom/consumers',vm_consumer_projection='/var/lib/axiom/consumer-view',
                vm_portable_credentials={'files':[{'path':'/etc/axiom/portable-credentials/reader-ci'},
                                                  {'path':'/etc/axiom/portable-credentials/publisher-central'}]})
            self.assertIn('/scripts/portable_consumer_intake.py '+operation,rendered)
            self.assertIn('LoadCredential=reader-ci:',rendered)
            self.assertEqual('LoadCredential=publisher-central:' in rendered,operation=='work')
            self.assertNotIn('consumer-reader.pem',rendered)
            self.assertIn('ProtectSystem=strict',rendered)

    def test_internal_git_mirror_is_explicit_and_never_contains_credentials(self):
        base={'host':'192.0.2.1','user':'operator','repository_url':'https://mirror.example/axiom.git','consumer_engine':'portable-v1'}
        atomic_json(self.path,base)
        self.assertEqual(deploy_vm.configuration(self.path)['repository_url'],base['repository_url'])
        for value in ('http://mirror.example/a.git','https://token@mirror.example/a.git','https://mirror.example/a.git?token=x'):
            atomic_json(self.path,{**base,'repository_url':value})
            with self.assertRaises(ValueError):deploy_vm.configuration(self.path)
