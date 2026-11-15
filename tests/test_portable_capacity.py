"""The capacity evidence auditor must detect missing, changed or shared executions."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.portable.contracts import repository_key
from lib.portable_intake.controller import task_key
from test_portable_runtime import context

spec=importlib.util.spec_from_file_location('capacity_audit',ROOT/'tests/capacity/summarize_portable_intake.py')
audit_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit_module)


class CapacityAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        (self.root/'fixtures').mkdir();(self.root/'private').mkdir()
        ctx=context('gitlab-ci');ci=ctx['ci'];policy={'scm':ctx['scm'],'ci':ci}
        locator={k:ci[k] for k in ('run_id','job_id','attempt')};key=task_key(policy,locator)
        self.write('fixtures/profiles.json',[{'policy':policy}]);self.write('fixtures/tasks.json',[{'profile_index':0,'locator':locator,'expected_decision':'fail'}])
        self.write('report.json',{'execution_count':1,'repository_count':1})
        self.receipt={'producer':ctx,'decision':'fail','execution':'complete','repository_key':repository_key(ctx['scm']),
            'candidate_eligible':False,'official_acceptance':False,'blocks_merge':None,
            'checks':{name:True for name in ('content_digest_verified','subject_identity_complete','baseline_ref_resolved')}}
        self.receipt['producer']['synthetic']=True
        self.db=sqlite3.connect(self.root/'private/queue.sqlite3');self.addCleanup(self.db.close)
        self.db.executescript('CREATE TABLE native_tasks(key TEXT,state TEXT,receipt_key TEXT); CREATE TABLE receipts(key TEXT,receipt TEXT); CREATE TABLE portable_batches(id TEXT);')
        self.db.execute('INSERT INTO native_tasks VALUES (?,?,?)',(key,'held','receipt'))
        self.db.execute('INSERT INTO receipts VALUES (?,?)',('receipt',json.dumps(self.receipt)));self.db.commit()

    def write(self,name,value):(self.root/name).write_text(json.dumps(value))

    def test_exact_negative_decision_is_audited(self):
        result=audit_module.audit(self.root)['execution_audit']
        self.assertEqual(result['negative_decisions_verified'],1)
        self.assertEqual(result['matched_receipts'],1)

    def test_changed_decision_is_rejected(self):
        self.receipt['decision']='pass'
        self.db.execute('UPDATE receipts SET receipt=?',(json.dumps(self.receipt),));self.db.commit()
        with self.assertRaisesRegex(ValueError,'decision_or_identity'):audit_module.audit(self.root)

    def test_missing_receipt_is_rejected(self):
        self.db.execute('DELETE FROM receipts');self.db.commit()
        with self.assertRaisesRegex(ValueError,'missing_receipt'):audit_module.audit(self.root)

    def test_duplicate_expected_identity_is_rejected(self):
        tasks=json.loads((self.root/'fixtures/tasks.json').read_text());self.write('fixtures/tasks.json',tasks*2)
        with self.assertRaisesRegex(ValueError,'duplicate_expected'):audit_module.audit(self.root)
