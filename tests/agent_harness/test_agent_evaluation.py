from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import evaluate_agent_reviews as cli
from scripts.lib.agent_evaluation import grade_evaluation, load_dataset, packet_set_digest, prepare_evaluation
from scripts.lib.agent_review import digest

ROOT=Path(__file__).resolve().parents[2]


class AgentEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.dataset=load_dataset()

    def gold_fixture(self):
        # Synthetic unit-test answers, never evidence of actual model performance.
        records=[]
        for case in self.dataset['cases']:
            response={**case['expected_classification'],'findings':[{
                'code':code,'severity':severity,'reason':'Synthetic fixture answer only',
                'evidence_refs':[next(iter(case['inputs']))]}
                for code,severity in case['expected_findings'].items()]}
            records.append({'case_id':case['id'],'response':response})
        return {'evaluation_digest':digest(self.dataset),'packet_set_digest':packet_set_digest(self.dataset),'records':records}

    def test_dataset_contains_defects_and_benign_counterexamples(self):
        self.assertEqual(len(self.dataset['cases']),10)
        self.assertEqual(sum(not c['expected_findings'] for c in self.dataset['cases']),2)
        covered={code for c in self.dataset['cases'] for code in c['expected_findings']}
        self.assertEqual(covered,set(self.dataset['taxonomy']))

    def test_prepare_is_private_has_no_gold_answers_and_calls_no_provider(self):
        with tempfile.TemporaryDirectory() as directory, patch('subprocess.Popen') as provider:
            output=Path(directory)/'packets'
            manifest=prepare_evaluation(ROOT,self.dataset,output)
            provider.assert_not_called()
            self.assertFalse(manifest['provider_invoked'])
            self.assertEqual(output.stat().st_mode & 0o777,0o700)
            for case in self.dataset['cases']:
                path=output/(case['id']+'.prompt.json')
                prompt=json.loads(path.read_text())
                self.assertNotIn('expected_findings',prompt)
                self.assertNotIn('expected_classification',prompt)
                self.assertEqual(path.stat().st_mode & 0o777,0o600)

    def test_perfect_synthetic_fixture_scores_without_inventing_measurements(self):
        report=grade_evaluation(self.dataset,self.gold_fixture())
        self.assertTrue(report['complete_coverage'])
        self.assertEqual(report['totals']['true_positive'],8)
        self.assertEqual(report['totals']['false_positive'],0)
        self.assertEqual(report['recall'],1)
        self.assertEqual(report['classification_accuracy'],1)
        self.assertIsNone(report['sum_case_elapsed_seconds'])
        self.assertIsNone(report['usage'])
        self.assertEqual(report['observed_models'],[])
        self.assertFalse(report['provider_invoked'])

    def test_misses_false_alarms_and_wrong_classifications_are_measured(self):
        bundle=self.gold_fixture()
        bundle['records'][0]['response']['findings']=[]
        bundle['records'][-2]['response']['findings']=[{'code':'candidate_derivation','severity':'high',
            'reason':'Synthetic false alarm','evidence_refs':['register_change']}]
        bundle['records'][-1]['response']['evidence_context']='mainline'
        report=grade_evaluation(self.dataset,bundle)
        self.assertEqual(report['totals']['false_positive'],1)
        self.assertEqual(report['totals']['false_negative'],1)
        self.assertEqual(report['precision'],7/8)
        self.assertEqual(report['recall'],7/8)
        self.assertEqual(report['classification_accuracy'],29/30)

    def test_missing_invalid_duplicate_and_other_revision_responses(self):
        bundle=self.gold_fixture()
        bundle['records'][0]['response']={'private_text':'PRIVATE_RESPONSE'}
        bundle['records'].pop()
        report=grade_evaluation(self.dataset,bundle)
        self.assertFalse(report['complete_coverage'])
        self.assertEqual(report['totals']['valid_cases'],8)
        self.assertNotIn('PRIVATE_RESPONSE',json.dumps(report))
        empty=grade_evaluation(self.dataset,{'evaluation_digest':digest(self.dataset),'packet_set_digest':packet_set_digest(self.dataset),'records':[]})
        self.assertIsNone(empty['precision'])
        self.assertEqual(empty['recall'],0)
        bundle=self.gold_fixture()
        bundle['records'].append(deepcopy(bundle['records'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate'):
            grade_evaluation(self.dataset,bundle)
        with self.assertRaisesRegex(ValueError,'revision'):
            grade_evaluation(self.dataset,{'evaluation_digest':'0'*64,'records':[]})
        bundle=self.gold_fixture()
        bundle['packet_set_digest']='0'*64
        with self.assertRaisesRegex(ValueError,'prompt/role/skill revision'):
            grade_evaluation(self.dataset,bundle)

    def test_measurements_require_case_bound_digest_checked_distinct_runs(self):
        bundle=self.gold_fixture()
        with tempfile.TemporaryDirectory() as directory:
            for index,record in enumerate(bundle['records']):
                trace={'case_id':record['case_id'],'evaluation_digest':digest(self.dataset),
                       'packet_set_digest':packet_set_digest(self.dataset),
                       'run_id':f'{index:032x}','elapsed_seconds':1.25,'requested_model':'synthetic-model',
                       'observed_model':None,'usage':{'input_tokens':10,'cached_input_tokens':4,
                                                    'output_tokens':3,'private_extra':'PRIVATE_TRACE'}}
                path=Path(directory)/(str(index)+'.json')
                path.write_text(json.dumps(trace))
                record.update(trace_file=str(path),trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            report=grade_evaluation(self.dataset,bundle)
            self.assertEqual(report['sum_case_elapsed_seconds'],12.5)
            self.assertEqual(report['usage'],{'input_tokens':100,'cached_input_tokens':40,'output_tokens':30})
            self.assertNotIn('PRIVATE_TRACE',json.dumps(report))
            self.assertEqual(report['observed_models'],[])
            first=bundle['records'][0]
            original=dict(first)
            first.pop('trace_file'); first.pop('trace_sha256')
            self.assertIsNone(grade_evaluation(self.dataset,bundle)['usage'])
            first.update(original)
            path=Path(first['trace_file'])
            trace=json.loads(path.read_text())
            trace['case_id']='different-case'
            path.write_text(json.dumps(trace))
            first['trace_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'case/revision'):
                grade_evaluation(self.dataset,bundle)
            trace['case_id']=first['case_id']; trace['run_id']=f'{1:032x}'
            path.write_text(json.dumps(trace))
            first['trace_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'multiple evaluation cases'):
                grade_evaluation(self.dataset,bundle)
            first['trace_sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'digest mismatch'):
                grade_evaluation(self.dataset,bundle)
            first.pop('trace_sha256')
            with self.assertRaisesRegex(ValueError,'file and its digest'):
                grade_evaluation(self.dataset,bundle)

    def test_unsafe_case_paths_and_in_repository_outputs_are_rejected(self):
        dataset=deepcopy(self.dataset)
        dataset['cases'][0]['id']='../escape'
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'identity'):
                prepare_evaluation(ROOT,dataset,Path(directory)/'out')
        with self.assertRaisesRegex(ValueError,'outside'):
            prepare_evaluation(ROOT,self.dataset,ROOT/'private-eval-output')

    def test_cli_prepares_and_grades_without_calls_or_overwrites(self):
        with tempfile.TemporaryDirectory() as directory, patch('subprocess.Popen') as provider:
            root=Path(directory)
            self.assertEqual(cli.main(['--prepare',str(root/'packets')]),0)
            (root/'answers.json').write_text(json.dumps(self.gold_fixture()))
            self.assertEqual(cli.main(['--responses',str(root/'answers.json'),'--output',str(root/'report.json')]),0)
            self.assertEqual(cli.main(['--responses',str(root/'answers.json'),'--output',str(root/'report.json')]),2)
            provider.assert_not_called()
