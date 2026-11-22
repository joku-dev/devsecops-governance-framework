"""Whole GitHub original including actual Git, logical scans and signed release child."""
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
import hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_provider_observation_context as whole
import test_v2_provider_observation as reference
import test_v2_release_verification as releases
from lib.providers.provider_observation_assurance import LegacyProviderAssurance
from lib.providers.provider_observation_legacy import PrivateSecurityModules
from lib.providers.self_security_capture import SecurityCollector
from lib.self_security import observed_values
from lib.providers.provider_observation_backend import NativeObservationBackend
from lib.providers.provider_observation_git import NativeObservationGit
from lib.provider_observation_git import ReplayObservationGit
from lib.providers.provider_observation_release import NativeObservationRelease
from lib.provider_observation_release import ReplayObservationRelease
from lib.portable.runtime import source_digest


class WholeGitHubObservation(unittest.TestCase):
    def test_three_whole_original_native_security_paths_and_source_free_complete_release_replays(self):
        test=whole.WholeRecordedObservation();test.setUp();self.addCleanup(test.doCleanups)
        signed=releases.fixture.ReleaseIntegrityTests();signed.setUp();self.addCleanup(signed.doCleanups)
        # Data/tags from the real signed fixture; never an expected report stub.
        source=test.world.source;ordinary_source=Path(signed.root).resolve()
        for child in ordinary_source.iterdir():
            target=source/child.name
            if child.is_dir():shutil.copytree(child,target,dirs_exist_ok=True)
            else:shutil.copyfile(child,target)
        def commit():
            subprocess.check_call(['git','add','.'],cwd=source)
            subprocess.check_call(['git','-c','commit.gpgsign=false','commit','--quiet','-m','Admitted own-source fixture data'],cwd=source)
            return subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
        revision=commit();node={'node_id':'b'*32,'runtime_source_digest':source_digest()}
        raw=(ROOT/'tests/fixtures/v2-self-security-original/assess_governance_repository_security.py.txt').read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),'c825703be300f4f4f9e5407645b210d56348987dd5dc437375ecc047f48a7c60')
        oracle=ModuleType('complete_frozen_self_security_oracle');oracle.__file__=str(ROOT/'tests/fixtures/v2-self-security-original/assess_governance_repository_security.py.txt');exec(compile(raw,oracle.__file__,'exec'),oracle.__dict__);oracle.ROOT=source;oracle.verify_release_integrity=releases.ORIGINAL.verify_release_integrity
        def original_collector(get):oracle.gh_api=get;return oracle
        test.original_loader=PrivateSecurityModules(source,collector_factory=original_collector,observed_values=oracle.observed_values)
        def factory(root,backend,emit_stderr):
            native=isinstance(backend,NativeObservationBackend);process=(NativeObservationGit if native else ReplayObservationGit)(backend.owner,root,emit_stderr=emit_stderr)
            if native:child=NativeObservationRelease(backend.owner,root,instance_root=backend.owner.private_state/'release-children'/backend.owner.record.root.name,node_context=node)
            else:child=ReplayObservationRelease(backend.owner,root,node_context=node)
            def collector(get,observed_at):
                return SecurityCollector(root,get,lambda:child.report(reference.REV,observed_at),path_factory=lambda path:path)
            loader=PrivateSecurityModules(root,collector_factory=None,timed_collector_factory=collector,observed_values=observed_values)
            return LegacyProviderAssurance(root,process=process,loader=loader)
        test.factory=factory
        for case in ('normal','security-api-error','workflow-unpinned'):
            if case=='workflow-unpinned':
                path=source/'.github/workflows/codeql.yml';path.write_text(path.read_text().replace('@'+'a'*40,'@v4'));revision=commit()
            with self.subTest(case=case),patch.object(reference,'REV',revision):
                captured=test.capture('github','security',case);record=captured[0];result=json.loads((test.work/'output/candidate.json').read_bytes());self.assertEqual(len(result['criteria']),16)
                self.assertFalse(result['official_acceptance']);self.assertFalse(result['live_authority'])
                if case=='security-api-error':self.assertEqual(result['observation_errors'],['http_403']);self.assertTrue(all(row['status']=='not_proven' for row in result['criteria']))
                else:
                    self.assertEqual(result['observation_errors'],[]);self.assertTrue(any(row['status']=='pass' for row in result['criteria']))
                self.assertTrue(list((test.records/'release-children'/record.root.name/'state/release-validation/operations').iterdir()))
                test.replay(captured)
