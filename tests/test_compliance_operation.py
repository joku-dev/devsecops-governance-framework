"""Complete scope/mode/node contract, including original vacuous-pass limits."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib import compliance_operation as operation
from lib.providers.compliance_worker import native_status
from types import SimpleNamespace


class ComplianceOperationContract(unittest.TestCase):
    def setUp(self):
        self.header={'schema_version':1,'kind':'product-complete-compliance','operation_id':'1'*64,
            'node_id':'2'*32,'runtime_source_digest':'3'*64,'source_revision':'4'*40,'source_tree':'5'*40,
            'package_sha256':'6'*64,'product_source_root':'/private/product/source',
            'instance_root':'/private/product/instance','assessed_at':'2026-11-15T12:00:00Z',
            'engine_profile':operation.PROFILE,**operation.AUTHORITY}
        self.selected={'cwd':'/private/operator','output_file':'reports/result.json',
            'target_repo':'consumer','input_file':None,'skip_unit_tests':False,'fail_on_findings':False}

    def test_closed_current_source_node_and_owned_package_request(self):
        root=self.header['instance_root']+'/state/compliance/operations/'+self.header['operation_id']
        packet={'binding':self.header,'options':self.selected,'record_root':root,'package':root+'/input.zip'}
        self.assertEqual(operation.request(packet),packet)
        decision=operation.decision_binding(self.header)
        self.assertEqual(decision['kind'],'product-compliance-decision-record')
        self.assertEqual(decision['node_id'],self.header['node_id'])
        for key in ('official_acceptance','authority_transferred','independent_execution_attested'):
            self.assertIs(decision[key],False)

    def test_foreign_operation_path_cannot_select_another_private_file(self):
        root=self.header['instance_root']+'/state/compliance/operations/'+self.header['operation_id']
        for change in ({'record_root':'/private/unrelated'}, {'package':root+'/../another/input.zip'}):
            packet={'binding':self.header,'options':self.selected,'record_root':root,'package':root+'/input.zip',**change}
            with self.subTest(change=change),self.assertRaises(ValueError):operation.request(packet)

    def test_authority_boolean_version_and_unknown_fields_are_rejected(self):
        for change in ({'official_acceptance':True},{'schema_version':True},{'extra':'field'},
                       {'node_id':'missing'},{'source_tree':'5'*39}):
            with self.subTest(change=change),self.assertRaises(ValueError):operation.binding({**self.header,**change})

    def test_original_relative_labels_are_retained_and_explicit_modes_are_strict(self):
        self.assertEqual(operation.options(self.selected)['target_repo'],'consumer')
        for change in ({'skip_unit_tests':1},{'fail_on_findings':'false'},{'cwd':'relative'},
                       {'output_file':'\x00'},{'another_option':False}):
            with self.subTest(change=change),self.assertRaises(ValueError):operation.options({**self.selected,**change})

    def test_consumer_findings_are_report_only_with_original_exit_preserved(self):
        result=operation.result_status({'kind':'returned','original_exit_code':1},
            integration='complete',repository='pass',unit='pass',opa='findings',skip_unit_tests=False)
        self.assertEqual(result,{'execution':'complete','original_finding_exit':1,'modern_exit':0})

    def test_self_engine_failure_is_visible_even_in_report_only_mode(self):
        for changed in ({'repository':'fail'},{'unit':'fail'}):
            values={'integration':'complete','repository':'pass','unit':'pass','opa':'pass',**changed}
            result=operation.result_status({'kind':'returned','original_exit_code':1},skip_unit_tests=False,**values)
            self.assertEqual(result['modern_exit'],1)

    def test_native_incomplete_acquisition_never_inherits_legacy_vacuous_pass(self):
        result=operation.result_status({'kind':'returned','original_exit_code':0},
            integration='incomplete',repository='pass',unit='pass',opa='pass',skip_unit_tests=False)
        self.assertEqual(result,{'execution':'incomplete','original_finding_exit':0,'modern_exit':2})

    def test_default_cannot_accept_an_unexecuted_or_skipped_unit_suite(self):
        for unit in ('not_run',None,'skipped'):
            result=operation.result_status({'kind':'returned','original_exit_code':0},
                integration='complete',repository='pass',unit=unit,opa='pass',skip_unit_tests=False)
            self.assertEqual(result['execution'],'incomplete')
        result=operation.result_status({'kind':'returned','original_exit_code':0},
            integration='complete',repository='pass',unit='not_run',opa='pass',skip_unit_tests=True)
        self.assertEqual(result['execution'],'complete')

    def test_original_raised_error_or_incomplete_opa_stays_incomplete(self):
        for decision,opa in (({'kind':'raised','exception':{}},'pass'),
                            ({'kind':'returned','original_exit_code':1},'incomplete')):
            result=operation.result_status(decision,integration='complete',repository='pass',
                unit='pass',opa=opa,skip_unit_tests=False)
            self.assertEqual(result['modern_exit'],2)

    def test_missing_or_boolean_original_exit_cannot_be_a_complete_operation(self):
        for value in (None,False,True,2):
            with self.subTest(exit=value),self.assertRaises(ValueError):
                operation.result_status({'kind':'returned','original_exit_code':value},
                    integration='complete',repository='pass',unit='pass',opa='pass',skip_unit_tests=False)

    def test_empty_or_partial_native_opa_observations_cannot_claim_full_acquisition(self):
        environment=SimpleNamespace(suboperations=[{'kind':'integration','execution':'complete'},
            {'kind':'repository','execution':'complete','original_finding_exit':0}],
            unit_outcome={'returncode':0})
        for count in (0,1,12,21,23):
            environment.opa=SimpleNamespace(observations=[{'native_outcome':{'exit_code':0}}]*count)
            with self.subTest(count=count):
                result=native_status({'kind':'returned','original_exit_code':0},environment,self.selected)
                self.assertEqual((result['execution'],result['modern_exit']),('incomplete',2))

    def test_original_raised_type_is_visible_in_the_native_summary_without_a_fabricated_traceback(self):
        environment=SimpleNamespace(suboperations=[],unit_outcome=None,opa=None)
        result=native_status({'kind':'raised','exception':{'type':'PermissionError'}},environment,self.selected)
        self.assertEqual((result['execution'],result['modern_exit'],result['error_type']),
                         ('incomplete',2,'PermissionError'))
        self.assertIsNone(result['original_finding_exit'])
        self.assertNotIn('traceback',result)

    def test_explicit_fail_on_findings_is_recorded_in_the_actual_native_and_modern_exit(self):
        environment=SimpleNamespace(suboperations=[{'kind':'integration','execution':'complete'},
            {'kind':'repository','execution':'complete','original_finding_exit':0}],
            unit_outcome={'returncode':0},opa=SimpleNamespace(
                observations=[{'native_outcome':{'exit_code':0}}]*22))
        decision={'kind':'returned','original_exit_code':1}
        self.assertEqual(native_status(decision,environment,self.selected)['modern_exit'],0)
        selected={**self.selected,'fail_on_findings':True}
        result=native_status(decision,environment,selected)
        self.assertEqual((result['execution'],result['modern_exit'],result['original_finding_exit']),
                         ('complete',1,1))
