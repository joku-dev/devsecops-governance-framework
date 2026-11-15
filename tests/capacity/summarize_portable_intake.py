#!/usr/bin/env python3
"""Audit each expected physical execution against its durable receipt, then export metrics."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.consumer_intake_store import atomic_json
from lib.portable.contracts import repository_key
from lib.portable_intake.controller import task_key


def audit(directory):
    directory=Path(directory)
    report=json.loads((directory/'report.json').read_text())
    profiles=json.loads((directory/'fixtures/profiles.json').read_text())
    tasks=json.loads((directory/'fixtures/tasks.json').read_text())
    db=sqlite3.connect((directory/'private/queue.sqlite3').as_uri()+'?mode=ro',uri=True)
    try:
        expected_keys=set();receipt_keys=set();negative=0
        for task in tasks:
            policy=profiles[task['profile_index']]['policy'];locator=task['locator'];key=task_key(policy,locator)
            if key in expected_keys:raise ValueError('duplicate_expected_execution')
            expected_keys.add(key)
            saved=db.execute('SELECT state,receipt_key FROM native_tasks WHERE key=?',(key,)).fetchone()
            if saved is None or saved[0]!='held':raise ValueError('expected_synthetic_held_execution_missing')
            if saved[1] in receipt_keys:raise ValueError('physical_execution_receipt_collision')
            receipt_keys.add(saved[1])
            row=db.execute('SELECT receipt FROM receipts WHERE key=?',(saved[1],)).fetchone()
            if row is None:raise ValueError('missing_receipt')
            receipt=json.loads(row[0]);producer=receipt['producer']
            if (receipt['decision']!=task['expected_decision'] or receipt['execution']!='complete'
                    or producer['scm']!=policy['scm'] or receipt['repository_key']!=repository_key(policy['scm'])
                    or producer['ci']['provider']!=policy['ci']['provider'] or producer['ci']['instance']!=policy['ci']['instance']
                    or producer['ci']['run_id']!=locator['run_id'] or producer['ci']['attempt']!=locator['attempt']
                    or producer['synthetic'] is not True or receipt['candidate_eligible'] is not False
                    or receipt['official_acceptance'] is not False or receipt['blocks_merge'] is not None):
                raise ValueError('execution_decision_or_identity_mismatch')
            if not all(receipt['checks'][name] for name in ('content_digest_verified','subject_identity_complete','baseline_ref_resolved')):
                raise ValueError('actual_file_or_baseline_verification_missing')
            logical_job=(policy['transport']['logical_job_id'] if policy['ci']['provider']=='github-actions'
                         else 'job-'+policy['scm']['native_id'] if policy['ci']['provider']=='bamboo' else locator['job_id'])
            if logical_job!=producer['ci']['job_id']:
                raise ValueError('native_job_identity_mismatch')
            negative+=receipt['decision']=='fail'
        if len(tasks)!=report['execution_count'] or len(profiles)!=report['repository_count']:
            raise ValueError('measurement_count_mismatch')
        if db.execute('SELECT count(*) FROM native_tasks').fetchone()[0]!=len(tasks) or db.execute('SELECT count(*) FROM receipts').fetchone()[0]!=len(tasks):
            raise ValueError('unexpected_extra_or_missing_execution')
        if db.execute('SELECT count(*) FROM portable_batches').fetchone()[0]:raise ValueError('unexpected_publication')
        report['execution_audit']={'expected_executions':len(tasks),'matched_receipts':len(receipt_keys),
            'negative_decisions_verified':negative,'positive_decisions_verified':len(tasks)-negative,
            'distinct_repository_keys':len({repository_key(p['policy']['scm']) for p in profiles}),
            'identity_collisions':0,'missing_receipts':0,'real_remote_publications':0}
        return report
    finally:db.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--measurement-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();atomic_json(a.output,audit(a.measurement_root),mode=0o644)
