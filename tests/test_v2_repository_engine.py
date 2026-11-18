"""Complete engine on a captured view with real native tools and deleted sources."""
import copy
import io
import json
from pathlib import Path
import shutil
import sys
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.repository_engine import RepositoryEngine
from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
from lib.providers.repository_opa import RepositoryOPA
from lib.providers.release_references import ReleaseReferences
from lib.providers.release_verification import ReleaseVerificationEnvironment
from lib.providers.attestation_verification import verify,outcome
from lib.provider_ports import configuration_source_profile
from lib.portable.runtime import approved_opa_hashes
from lib import repository_capture as capture_contract
from lib.v2_boundary import violations


@unittest.skipUnless(all(shutil.which(name) for name in ('git','ssh-keygen','openssl','opa')),'native validation tools absent')
class RepositoryEngineTests(unittest.TestCase):
    def setUp(self):
        import test_v2_repository_capture as fixture
        for name in ('command','commit','journal','port','capture'):
            setattr(self,name,MethodType(getattr(fixture.RepositoryCaptureTests,name),self))
        fixture.RepositoryCaptureTests.setUp(self)
        self.events=[]
        self.area=self.base/'native';self.area.mkdir(mode=0o700)

    def minimal(self,**overrides):
        manifest,files,commit=self.capture()
        def unavailable(*args,**kwargs):raise AssertionError('unexpected native execution in this minimal fixture')
        options={'capture_adapter_factory':LegacyRepositoryLifecycleCapture,
            'schema_identifier_bases':('https://joku-dev.github.io/devsecops-governance-framework/schemas/',),
            'source_configuration_profile':configuration_source_profile('github-actions'),
            'clock':lambda:'2026-11-15T12:00:00Z','verify_attestation':unavailable,
            'release_port':SimpleNamespace(root=self.source,run=unavailable,temporary_file=unavailable),
            'opa_port':None,'append_event':lambda row:self.events.append(copy.deepcopy(row))}
        options.update(overrides)
        return RepositoryEngine(manifest,files,commit,**options)

    def test_missing_required_profiles_and_native_ports_cannot_turn_into_fake_success(self):
        for options in ({'capture_adapter_factory':None},{'verify_attestation':None},
                        {'append_event':None},{'release_port':SimpleNamespace(root='/different')},
                        {'opa_port':object()}):
            with self.assertRaises((ValueError,AttributeError)):self.minimal(**options)

    def test_original_uncaught_missing_input_stays_incomplete_and_cannot_be_resumed(self):
        engine=self.minimal();shutil.rmtree(self.source)
        with patch('subprocess.Popen',side_effect=AssertionError('no native worker needed')):
            result=engine.execute()
        self.assertEqual(result['execution'],'incomplete')
        self.assertEqual(result['exit_code'],2)
        self.assertEqual(result['exception_type'],'FileNotFoundError')
        self.assertEqual(self.events[-1]['phase'],'incomplete')
        with self.assertRaisesRegex(ValueError,'already_executed'):engine.execute()

    def real(self,negative):
        shutil.copytree(ROOT,self.source,dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('.git','__pycache__','.venv*','.DS_Store','*.pyc'))
        self.commit()
        if negative:
            import yaml
            path=self.source/'model/controls/dscb-l1.yaml'
            value=yaml.safe_load(path.read_bytes());value['requirements'][0]['id']=value['requirements'][1]['id']
            path.write_text(yaml.safe_dump(value,sort_keys=False))
        manifest,files,commit=self.capture(capture_contract.WORKING)
        references=ReleaseReferences(self.source).capture()
        opa=RepositoryOPA(shutil.which('opa'),approved_hashes=frozenset(approved_opa_hashes('1.18.2')),
            workarea=self.area,on_intent=lambda row:None,on_start=lambda row:None,on_finish=lambda row:None)
        def crypto(key,statement,signature):
            observation,stdout,stderr=verify(key,statement,signature,self.area,'legacy-attestation-pilot-v1',lambda row:None)
            return outcome(observation)
        with ReleaseVerificationEnvironment(self.source,files,references,self.area) as release:
            engine=RepositoryEngine(manifest,files,commit,capture_adapter_factory=LegacyRepositoryLifecycleCapture,
                schema_identifier_bases=('https://joku-dev.github.io/devsecops-governance-framework/schemas/',),
                source_configuration_profile=configuration_source_profile('github-actions'),clock=lambda:'2026-11-15T12:00:00Z',
                verify_attestation=crypto,release_port=release,opa_port=opa,
                append_event=lambda row:self.events.append(copy.deepcopy(row)))
            shutil.rmtree(self.source)
            result=engine.execute()
        self.assertFalse(self.source.exists())
        self.assertEqual(result['execution'],'complete')
        self.assertIsNone(result['exception_type'])
        self.assertEqual(result['stderr'],'')
        self.assertEqual(result['exit_code'],1 if negative else 0)
        if negative:
            self.assertEqual(result['stdout'],"Validation failed:\n- Duplicate control IDs: ['DSCB-L1-REQ-002']\n- Traceability references unknown controls: ['DSCB-L1-REQ-001']\n- Coverage status references unknown controls: ['DSCB-L1-REQ-001']\n")
        else:
            self.assertEqual(result['stdout'],'Validation passed\n- controls: 46\n- L1: 16\n- L2: 14\n- L3: 11\n- GOV: 5\n- traceability mappings: 46\n- registered source documents: 15\n- policy candidates: 31\n')
        self.assertEqual(engine.dataset.files['model/controls/dscb-l1.yaml'],files['model/controls/dscb-l1.yaml'])
        self.assertTrue(all(name.startswith('generated/') for name in engine.dataset.files.keys()-files.keys()))
        self.assertTrue(any(row.get('kind')=='dataset-effect' and row.get('phase')=='content' for row in self.events))
        self.assertFalse(any(row.get('phase')=='incomplete' for row in self.events))

    def test_complete_original_positive_sequence_runs_after_the_source_is_deleted(self):self.real(False)

    def test_complete_original_negative_sequence_runs_after_the_source_is_deleted(self):self.real(True)

    def test_engine_core_has_no_native_or_legacy_provider_import(self):
        name='scripts/lib/repository_engine.py';self.assertEqual(violations(name,(ROOT/name).read_text()),[])


if __name__=='__main__':unittest.main()
