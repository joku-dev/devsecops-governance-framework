"""Durable whole reports and exact ordered read profile; no production publisher."""
from contextlib import redirect_stdout
from copy import deepcopy
import io,json,os
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tests'))
from lib.self_security_application import SecurityContext,render,run,FILES
from lib.providers.self_security_capture import PROFILE,request_paths,SecurityCollector
from lib.providers.self_security_native import SecurityAPI,ReplaySecurityAPI,capture_source
from lib.provider_errors import AccessFailure
from lib.consumer_intake_store import atomic_json
import test_v2_self_security as original_tests


class ProvidedReports(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.instance=self.base/'instance';self.instance.mkdir(mode=0o700)
        self.context=SecurityContext(self.instance,{'node_id':'a'*32})
        self.observation=(ROOT/'docs/examples/governance-repository-security-observation.example.json').read_bytes()
        self.model=(ROOT/'model/controls/governance-repository-security.yaml').read_bytes()
    def create(self,**kw):
        return self.context.create(profile=PROFILE,repository='owner/repo',observation_raw=self.observation,**kw)
    def test_whole_original_wire_and_ignored_provided_time_and_visible_authority(self):
        original_tests.OriginalSecurityDecisions.setUpClass();old=original_tests.OriginalSecurityDecisions.original
        import yaml
        for fail in (False,True):
            operation,value=self.create(observed_at='ignored-for-provided-observation',fail_on_findings=fail)
            target=self.context.operations/operation
            expected=old.assess(yaml.safe_load(self.model),json.loads(self.observation))
            self.assertEqual((target/'outputs/report.json').read_text(),json.dumps(expected,indent=2)+'\n')
            self.assertEqual((target/'outputs/report.md').read_text(),old.render_markdown(expected))
            self.assertEqual((target/'outputs/stdout.txt').read_text(),'Governance repository self-security: pass (16 pass, 0 fail)\n')
            self.assertEqual(value['execution'],'complete');self.assertEqual(value['exit_code'],0)
            self.assertIsNone(value['resolved_observed_at']);self.assertFalse(value['official_acceptance']);self.assertFalse(value['authority_transferred'])
            with patch('lib.self_security_application.SecurityAPI',side_effect=AssertionError('HTTP forbidden')),patch.object(self.context,'releases',side_effect=AssertionError('signature forbidden')):
                self.assertEqual(self.context.inspect(operation),value)
    def test_report_only_and_opt_in_finding_exit_preserve_same_reports(self):
        observation=json.loads(self.observation);observation['repository']['branch_protected']=False;self.observation=json.dumps(observation).encode()
        first,a=self.create();second,b=self.create(fail_on_findings=True)
        self.assertEqual(a['exit_code'],0);self.assertEqual(b['exit_code'],1);self.assertEqual(a['output_files'],b['output_files'])
        self.assertEqual(self.context.inspect(first),a);self.assertEqual(self.context.inspect(second),b)
    def test_invalid_original_inputs_are_durable_incomplete_not_empty_passes(self):
        for raw in (b'not JSON',b'null',b'[]',b'{"repository":null}',b'{"actions":{"third_party_unpinned_refs":null}}'):
            with self.subTest(raw=raw):
                self.observation=raw;operation,value=self.create();self.assertEqual(value['execution'],'incomplete');self.assertEqual(value['exit_code'],2)
                self.assertTrue((self.context.operations/operation/'pending.json').is_file())
                with self.assertRaises(ValueError):self.context.inspect(operation)
    def test_report_model_source_journal_and_authority_tampering_are_rejected(self):
        operation,value=self.create();target=self.context.operations/operation
        for name in ('outputs/report.json','outputs/report.md','outputs/stdout.txt','inputs/observation.json','inputs/model.yaml','pending.json','native-results.json'):
            path=target/name;before=path.read_bytes();path.write_bytes(before+b'changed')
            with self.subTest(name=name),self.assertRaises((ValueError,json.JSONDecodeError)):self.context.inspect(operation)
            path.write_bytes(before)
        for name in ('assessment.json','native-results.json','pending.json'):
            path=target/name;before=path.read_bytes();row=json.loads(before);row['authority_transferred']=True;atomic_json(path,row)
            with self.subTest(name=name),self.assertRaises(ValueError):self.context.inspect(operation)
            path.write_bytes(before)
        self.assertEqual(self.context.inspect(operation),value)
    def test_provided_inputs_cannot_silently_invoke_native_capture(self):
        for kw in ({'source_worktree':ROOT},{'token_file':Path(self.temp.name)/'token'}):
            with self.assertRaises(ValueError):self.create(**kw)
    def test_cli_exports_keep_exact_legacy_stdout_and_whole_files(self):
        observation=self.base/'observation.json';observation.write_bytes(self.observation)
        output=self.base/'exports/report.json';md=output.with_suffix('.md');stream=io.StringIO()
        with redirect_stdout(stream):
            code=run(['assess','--profile',PROFILE,'--observation',str(observation),'--output-json',str(output),'--output-md',str(md),'--format','legacy'],self.instance,{'node_id':'a'*32})
        self.assertEqual(code,0);self.assertEqual(stream.getvalue(),'Governance repository self-security: pass (16 pass, 0 fail)\n')
        self.assertTrue(output.is_file());self.assertTrue(md.is_file());self.assertEqual(output.stat().st_mode&0o077,0)


class NativeReadContract(unittest.TestCase):
    def test_all_seven_bounded_reads_error_order_intent_before_result_and_replay(self):
        paths=request_paths('owner/repo');events=[]
        def get(path):
            events.append(('get',path))
            if path.endswith('/workflow'):raise AccessFailure('http_403')
            return {'opaque':'response'}
        api=SecurityAPI('owner/repo',on_intent=lambda row:events.append(('intent',row['path'])),on_result=lambda row:events.append(('result',row['path'])))
        with patch.object(api.reader,'get',side_effect=get):actual=[api(path) for path in paths]
        self.assertEqual([event[0] for event in events],['intent','get','result']*7)
        self.assertEqual(actual[4],(None,paths[4]+': http_403'));self.assertNotIn('token',json.dumps(api.rows).lower())
        replay=ReplaySecurityAPI('owner/repo',api.rows);self.assertEqual([replay(path) for path in paths],actual);replay.finish()
        with self.assertRaises(ValueError):api(paths[0])
        for changed in ('method','path','sequence','error','extra'):
            rows=deepcopy(api.rows)
            if changed=='extra':rows[0]['unexpected']=True
            else:rows[0][changed]={'method':'POST','path':'other','sequence':False,'error':'unbound error'}[changed]
            replay=ReplaySecurityAPI('owner/repo',rows)
            with self.subTest(changed=changed),self.assertRaises(ValueError):replay(paths[0])
    def test_explicit_credential_mode_and_unsafe_source_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);token=root/'token';token.write_text('dummy-not-a-real-secret');token.chmod(0o644)
            with self.assertRaises(ValueError):SecurityAPI('owner/repo',token_file=token)
            target=root/'source';target.mkdir();(target/'.github').symlink_to(root)
            with self.assertRaises(ValueError):capture_source(target)


class NativeSecurityReports(unittest.TestCase):
    def setUp(self):
        import test_v2_release_verification as releases
        self.releases_module=releases
        self.fixture=releases.fixture.ReleaseIntegrityTests()
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.source=self.fixture.root.resolve();self.base=self.source.parent
        workflows=self.source/'.github/workflows';workflows.mkdir(parents=True)
        (workflows/'codeql.yml').write_text('permissions:\n  contents: read\nuses: third/action@main\n')
        (self.source/'.github/CODEOWNERS').write_text('/scripts/ @test\n')
        self.instance=self.base/'instance';self.instance.mkdir(mode=0o700)
        self.context=SecurityContext(self.instance,{'node_id':'b'*32},product_root=self.source)
        self.model=(ROOT/'model/controls/governance-repository-security.yaml').read_bytes()
        self.paths=request_paths('owner/repo')
    def create(self,**kw):
        return self.context.create(profile=PROFILE,repository='owner/repo',source_worktree=self.source,model_raw=self.model,observed_at='opaque-original-time',**kw)
    def transport(self,path):
        if path.endswith('/actions/permissions/workflow'):raise AccessFailure('http_403')
        return {'visibility':'private','default_branch':'main'} if path=='/'+self.paths[0] else [] if path=='/'+self.paths[-1] else {}
    def test_seven_actual_adapter_reads_real_signature_verification_and_whole_original_report(self):
        import yaml
        original_tests.OriginalSecurityDecisions.setUpClass();old=original_tests.OriginalSecurityDecisions.original
        calls=[]
        def read(path):calls.append(path);return self.transport(path)
        with patch('lib.providers.self_security_native.Reader.get',side_effect=read):operation,value=self.create()
        self.assertEqual(value['execution'],'complete',value);self.assertEqual(calls,['/'+p for p in self.paths])
        target=self.context.operations/operation
        release=self.context.releases().inspect(value['release_assessment'])
        release_target=self.context.releases().operations/value['release_assessment']
        with patch.dict(os.environ,{'GIT_DIR':str(self.source/'.git')}):
            expected_release=self.releases_module.ORIGINAL.verify_release_integrity(release_target/'inputs',release_target/'inputs/model/governance/release-signing-policy.yaml')
        self.assertEqual(release['report'],expected_release)
        self.assertTrue(release['native_observations']);self.assertEqual(release['report']['unverified_release_tags'],[])
        replay=ReplaySecurityAPI('owner/repo',value['native_responses'])
        with patch.object(old,'ROOT',target/'inputs/source'),patch.object(old,'gh_api',side_effect=replay),patch.object(old,'tag_verification',return_value=expected_release):
            observation=old.collect_live('owner/repo','opaque-original-time')
        replay.finish();expected=old.assess(yaml.safe_load(self.model),observation)
        self.assertEqual((target/'outputs/report.json').read_text(),json.dumps(expected,indent=2)+'\n')
        self.assertEqual((target/'outputs/report.md').read_text(),old.render_markdown(expected))
        self.assertEqual(self.context.inspect(operation),value)
        for index in range(1,8):
            self.assertTrue((target/'requests'/f'{index:02}.json').is_file());self.assertTrue((target/'responses'/f'{index:02}.json').is_file())
        # Retained replay has no caller/source/HTTP/signature-tool dependency.
        (self.source/'.github/CODEOWNERS').write_text('changed after completed observation')
        with patch('lib.self_security_application.capture_security_source',side_effect=AssertionError('fresh source forbidden')),patch('lib.providers.self_security_native.Reader.get',side_effect=AssertionError('fresh API forbidden')),patch('lib.release_validation_application.ReleaseVerificationEnvironment',side_effect=AssertionError('native signature forbidden')):
            self.assertEqual(self.context.inspect(operation),value)
    def test_denied_admin_facts_remain_visible_and_real_release_failure_is_a_finding(self):
        (self.source/'releases/test/payload.txt').write_text('tampered private test payload')
        with patch('lib.providers.self_security_native.Reader.get',side_effect=AccessFailure('http_403')):
            operation,value=self.create(fail_on_findings=True)
        self.assertEqual(value['execution'],'complete',value);self.assertEqual(value['exit_code'],1)
        report=json.loads((self.context.operations/operation/'outputs/report.json').read_bytes())
        self.assertEqual(len(report['observation']['api_errors']),7)
        self.assertIn('GRS-014',[row['id'] for row in report['criteria'] if row['status']=='fail'])
        self.assertTrue(report['observation']['release_integrity']['verification_errors'])
        self.assertEqual(self.context.inspect(operation),value)
    def test_changed_source_leaves_durable_pending_no_automatic_retry(self):
        def read(path):
            if path=='/'+self.paths[0]:(self.source/'.github/CODEOWNERS').write_text('changed during acquisition')
            return self.transport(path)
        with patch('lib.providers.self_security_native.Reader.get',side_effect=read):
            with self.assertRaisesRegex(ValueError,'changed_during_acquisition'):self.create()
        target=next(self.context.operations.iterdir());self.assertTrue((target/'native-results.json').is_file());self.assertFalse((target/'assessment.json').exists())
        self.assertEqual(len(list((target/'requests').iterdir())),7)
    def test_native_journal_and_nested_signature_evidence_tampering_are_rejected(self):
        with patch('lib.providers.self_security_native.Reader.get',side_effect=self.transport):operation,value=self.create()
        target=self.context.operations/operation
        release=self.context.releases().operations/value['release_assessment']
        for path in (target/'requests/01.json',target/'responses/01.json',release/'references.json',release/'assessment.json',target/'inputs/source/.github/CODEOWNERS'):
            before=path.read_bytes();path.write_text('{}')
            with self.subTest(path=path.name),self.assertRaises(ValueError):self.context.inspect(operation)
            path.write_bytes(before)
        self.assertEqual(self.context.inspect(operation),value)


if __name__=='__main__':unittest.main()
