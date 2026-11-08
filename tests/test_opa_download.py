"""Transport failures, poisoned caches and byte verification use synthetic binaries."""
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import install_validation_opa as opa

PAYLOAD = b'#!/bin/sh\nprintf "Version: 1.18.2\\n"\n'


class OpaDownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.destination = self.root / 'bin/opa'
        self.cache = self.root / 'cache'
        self.tool = opa.Tool('1.18.2', 'opa_linux_amd64_static', hashlib.sha256(PAYLOAD).hexdigest(), 464348303)
        self.calls = []

    def fetch(self, url, path, **options):
        self.calls.append((url, options)); path.write_bytes(PAYLOAD)

    def run_install(self, **kwargs):
        return opa.install(self.tool, self.destination, self.cache, sleep=lambda _: None, **kwargs)

    def test_platform_selection_matches_preserved_pins_and_official_asset_ids(self):
        for system, machine, asset in [('Linux','x86_64','opa_linux_amd64_static'),('Linux','aarch64','opa_linux_arm64_static'),('Darwin','arm64','opa_darwin_arm64'),('Darwin','x86_64','opa_darwin_amd64')]:
            with self.subTest(asset=asset):
                tool = opa.select_tool(system=system, machine=machine)
                self.assertEqual(tool.asset, asset); self.assertEqual(tool.version,'1.18.2')
                self.assertRegex(tool.sha256,r'^[a-f0-9]{64}$'); self.assertGreater(tool.asset_id,0)
        with self.assertRaisesRegex(ValueError,'Unsupported'):
            opa.select_tool(system='Linux',machine='unknown')

    def test_success_is_verified_atomic_executable_and_reused_offline(self):
        self.assertEqual(self.run_install(fetch=self.fetch),'official release')
        self.assertEqual(self.destination.read_bytes(),PAYLOAD); self.assertTrue(os.access(self.destination,os.X_OK))
        self.assertEqual(len(self.calls),1)
        self.destination.unlink()
        self.assertEqual(self.run_install(offline=True,fetch=lambda *_: self.fail('network on cache hit')),'cache')
        self.assertEqual(self.run_install(offline=True,fetch=lambda *_: self.fail('network on installed hit')),'installed')
        self.assertEqual(list(self.destination.parent.glob('.opa-*')),[])

    def test_bounded_retries_then_api_fallback(self):
        def fetch(url,path,**options):
            self.calls.append((url, options))
            if not options['api']:raise OSError('HTTP 504')
            path.write_bytes(PAYLOAD)
        self.assertEqual(self.run_install(fetch=fetch,attempts=2,timeout=17),'official asset API')
        self.assertEqual(len(self.calls),3)
        self.assertTrue(self.calls[-1][1]['api']); self.assertEqual(self.calls[-1][1]['timeout'],17)
        self.assertIn('/releases/assets/464348303',self.calls[-1][0])

    def test_corrupt_primary_never_executes_and_falls_back(self):
        marker=self.root/'executed'
        def fetch(url,path,**options):
            path.write_bytes(PAYLOAD if options['api'] else f'#!/bin/sh\ntouch {marker}\n'.encode())
        self.run_install(fetch=fetch)
        self.assertFalse(marker.exists());self.assertEqual(self.destination.read_bytes(),PAYLOAD)

    def test_partial_failed_download_is_removed_before_retry(self):
        def fetch(url,path,**options):
            self.assertFalse(path.exists())
            if not self.calls:
                self.calls.append(url);path.write_bytes(b'partial');raise OSError('connection interrupted')
            path.write_bytes(PAYLOAD)
        self.run_install(fetch=fetch)
        self.assertEqual(self.destination.read_bytes(),PAYLOAD)
        self.assertEqual(list(self.cache.glob('.opa-download-*')),[])

    def test_corrupt_cache_is_never_trusted_offline_and_is_repaired_online(self):
        cached=self.cache/self.tool.cache_key/'opa';cached.parent.mkdir(parents=True);cached.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'offline'):
            self.run_install(offline=True,fetch=self.fetch)
        self.assertFalse(self.destination.exists());self.assertEqual(self.calls,[])
        self.run_install(fetch=self.fetch);self.assertEqual(cached.read_bytes(),PAYLOAD)

    def test_all_sources_fail_closed_without_replacing_previous_file(self):
        self.destination.parent.mkdir();self.destination.write_bytes(b'existing file')
        def fail(url,path,**options):raise OSError('unavailable')
        with self.assertRaisesRegex(ValueError,'unavailable'):
            self.run_install(fetch=fail,attempts=1)
        self.assertEqual(self.destination.read_bytes(),b'existing file')
        self.assertFalse((self.cache/self.tool.cache_key/'opa').exists())

    def test_matching_hash_with_wrong_version_is_not_installed_or_cached(self):
        wrong=b'#!/bin/sh\nprintf "Version: 9.0.0\\n"\n'
        self.tool=replace(self.tool,sha256=hashlib.sha256(wrong).hexdigest())
        def fetch(url,path,**options):path.write_bytes(wrong)
        with self.assertRaisesRegex(ValueError,'version mismatch'):
            self.run_install(fetch=fetch)
        self.assertFalse(self.destination.exists());self.assertFalse((self.cache/self.tool.cache_key/'opa').exists())

    def test_optional_mirror_keeps_the_same_hash_and_falls_back_on_corruption(self):
        def fetch(url,path,**options):
            self.calls.append(url);path.write_bytes(b'bad mirror bytes' if url.startswith('https://mirror.example') else PAYLOAD)
        self.assertEqual(self.run_install(fetch=fetch,mirror='https://mirror.example/opa'),'official release')
        self.assertEqual(self.calls[0],'https://mirror.example/opa/v1.18.2/opa_linux_amd64_static')
        for url in ['http://mirror.example','https://name:secret@mirror.example','https://mirror.example/?token=secret','https://mirror.example/#fragment']:
            with self.subTest(url=url),self.assertRaises(ValueError):opa.locations(self.tool,url)

    def test_cached_symlink_is_not_used(self):
        cached=self.cache/self.tool.cache_key/'opa';cached.parent.mkdir(parents=True)
        source=self.root/'original';source.write_bytes(PAYLOAD);cached.symlink_to(source)
        with self.assertRaisesRegex(ValueError,'offline'):self.run_install(offline=True,fetch=self.fetch)

    def test_cache_parent_symlink_cannot_redirect_a_write(self):
        self.cache.mkdir();outside=self.root/'outside';outside.mkdir()
        (self.cache/self.tool.cache_key).symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlinks'):self.run_install(fetch=self.fetch)
        self.assertEqual(self.calls,[]);self.assertEqual(list(outside.iterdir()),[])

    def test_network_transport_is_https_bounded_unauthenticated_and_does_not_execute(self):
        with patch.object(opa.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as run:
            opa.download('https://api.github.com/repos/open-policy-agent/opa/releases/assets/1',self.root/'download',api=True,timeout=19)
        args=run.call_args.args[0]
        self.assertEqual(args[1],'--disable');self.assertIn('=https',args);self.assertIn('19',args);self.assertIn('Accept: application/octet-stream',args)
        self.assertFalse(any('Authorization' in arg for arg in args));self.assertTrue(run.call_args.kwargs['capture_output'])

    def test_transport_error_reports_status_without_echoing_proxy_secrets(self):
        failure=subprocess.CompletedProcess([],22,stdout=b'504',stderr=b'proxy secret https://example.invalid/?token=secret')
        with patch.object(opa.subprocess,'run',return_value=failure):
            with self.assertRaisesRegex(opa.DownloadError,'HTTP 504, curl exit 22') as caught:
                opa.download('https://example.invalid/file',self.root/'download',api=False,timeout=2)
        self.assertNotIn('secret',str(caught.exception));self.assertNotIn('example.invalid',str(caught.exception))

    def test_cache_write_failure_does_not_discard_a_verified_installation(self):
        original=opa.install_copy
        def copy(source,destination,tool):
            if destination.name=='opa' and self.cache in destination.parents:raise OSError('cache read-only')
            return original(source,destination,tool)
        with patch.object(opa,'install_copy',side_effect=copy):
            self.assertEqual(self.run_install(fetch=self.fetch),'official release')
        self.assertEqual(self.destination.read_bytes(),PAYLOAD)

    def test_source_metadata_cannot_silently_select_a_different_version(self):
        toolchain=self.root/'toolchain.env'
        toolchain.write_text((ROOT/'scripts/validation-toolchain.env').read_text().replace('1.18.2','9.0.0'))
        with self.assertRaisesRegex(ValueError,'metadata must match'):
            opa.select_tool(toolchain=toolchain,system='Linux',machine='x86_64')

    def test_action_checks_cache_bytes_and_propagates_installer_failure(self):
        action=yaml.safe_load((ROOT/'.github/actions/setup-opa-verified/action.yml').read_text())
        verify=next(s for s in action['runs']['steps'] if s['name']=='Verify or download OPA')
        self.assertNotIn('if',verify);self.assertNotIn('continue-on-error',verify)
        self.assertIn('install_validation_opa.py',verify['run']);self.assertNotIn('|| true',verify['run'])
        workflow=(ROOT/'.github/workflows/governance-ci-v2.yml').read_text()
        self.assertIn('name: Governance CI v2',workflow);self.assertIn('./scripts/bootstrap_validation_env.sh',workflow)
        self.assertNotIn('open-policy-agent/setup-opa@',workflow)
        self.assertNotIn('open-policy-agent/setup-opa@',(ROOT/'.github/workflows/publish-docs.yml').read_text())

    def test_accepted_implementations_remain_byte_identical(self):
        import json
        for name in ['model/governance/lifecycle/operating-acceptance/00000001.json','model/governance/lifecycle/consumer-operation/acceptance.json']:
            for file,sha in json.loads((ROOT/name).read_text())['implementation_manifest'].items():
                self.assertEqual(hashlib.sha256((ROOT/file).read_bytes()).hexdigest(),sha,file)


if __name__=='__main__':unittest.main()
