"""Instance-owned full V1-compatible control/architecture reports, not acceptance."""
from datetime import datetime
from collections import Counter
import hashlib
import tempfile
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib.portable.contracts import canonical_digest
from lib.portable.contracts import ROOT
from lib.portable.runtime import read_json, source_digest, file_digest
from lib.consumer_intake_store import atomic_json
from lib.tool_integrity import require_opa


def evaluate(domain,input_path,*,opa,at,source_revision):
    input_path=Path(input_path)
    if input_path.is_symlink() or not input_path.is_file() or input_path.stat().st_size>16*1024**2:
        raise ValueError('invalid_full_assessment_input')
    raw=input_path.read_bytes()
    if len(raw)>16*1024**2:raise ValueError('invalid_full_assessment_input')
    timestamp=datetime.fromisoformat(at.replace('Z','+00:00'))
    if timestamp.tzinfo is None:raise ValueError('explicit_assessment_timezone_required')
    opa=require_opa(opa)
    from lib.functional_parity import git_read
    actual_revision=git_read(ROOT,'rev-parse','HEAD').decode().strip()
    if source_revision!=actual_revision:raise ValueError('full_assessment_source_revision_mismatch')
    source_worktree_clean=not bool(git_read(ROOT,'status','--porcelain','--untracked-files=all').strip())
    # Freeze operator input once, so every query and the returned digest use
    # the same physical bytes even if the original path changes mid-assessment.
    with tempfile.TemporaryDirectory(prefix='axiom-full-assessment-') as temporary:
        snapshot=Path(temporary)/'input.json';snapshot.write_bytes(raw);snapshot.chmod(0o600)
        payload=read_json(snapshot)
        if not isinstance(payload,dict):raise ValueError('full_assessment_object_required')
        if domain=='controls':
            from control_evaluation import generate_control_evaluation_report, ROOT as CONTROL_ROOT
            report=generate_control_evaluation_report(snapshot,opa=opa)
            original=input_path.resolve()
            report['input_file']=str(original.relative_to(CONTROL_ROOT)) if original.is_relative_to(CONTROL_ROOT) else str(original)
            execution='incomplete' if any(r['status']=='error' for r in report['policy_results'].values()) else 'complete'
        elif domain=='architecture':
            from lib.architecture_assessment import evaluate as assess
            report=assess(snapshot,opa=opa);execution='complete'
        else:raise ValueError('unsupported_full_assessment_domain')
    assessment={'schema_version':1,'kind':'v1-compatible-full-assessment','domain':domain,
        'source_revision':source_revision,'runtime_source_digest':source_digest(),
        'source_worktree_clean':source_worktree_clean,
        'input_sha256':hashlib.sha256(raw).hexdigest(),'opa_sha256':file_digest(opa),'assessed_at':at,
        'execution':execution,'mode':'report-only','official_compliance_result':False,
        'input_origin':'operator_supplied','evidence_trust':'unverified','authority_transferred':False,
        'report':report}
    validate(assessment)
    return assessment


def validate(assessment):
    try:
        Draft202012Validator(read_json(ROOT/'schemas/axiom-v2-full-assessment.schema.json'),
                             format_checker=FormatChecker()).validate(assessment)
    except ValidationError:raise ValueError('invalid_full_assessment') from None
    if assessment['runtime_source_digest']!=source_digest():raise ValueError('full_assessment_runtime_changed')
    report=assessment['report']
    if assessment['domain']=='controls':
        rows=report['controls'];counts=Counter(row['status'] for row in rows)
        if len({r['control_id'] for r in rows})!=len(rows):raise ValueError('duplicate_full_assessment_control')
        expected={'total_controls':len(rows),**{k:counts[k] for k in ('pass','fail','not_tested','not_applicable')},
                  'applicable_controls':len(rows)-counts['not_applicable'],'tested_controls':counts['pass']+counts['fail']}
    else:
        rows=report['gates']
        if len({r['id'] for r in rows})!=4:raise ValueError('duplicate_full_assessment_gate')
        expected={'gate_count':len(rows),'passed':sum(not r['findings'] for r in rows),
                  'with_findings':sum(bool(r['findings']) for r in rows),'finding_count':sum(len(r['findings']) for r in rows)}
    if expected!=report['summary']:raise ValueError('full_assessment_summary_mismatch')


def persist(assessment,instance_root):
    root=Path(instance_root).resolve();state=root/'state/assessments'
    if (state.is_symlink() or any(p.is_symlink() for p in (root/'state',))):
        raise ValueError('unsafe_assessment_state')
    state.mkdir(mode=0o700,parents=True,exist_ok=True)
    if state.stat().st_mode&0o077:raise ValueError('private_assessment_state_required')
    validate(assessment)
    identity=canonical_digest(assessment);path=state/(identity+'.json')
    if path.is_symlink():raise ValueError('unsafe_assessment_state')
    if path.exists():
        if read_json(path)!=assessment:raise ValueError('immutable_assessment_conflict')
    else:atomic_json(path,assessment)
    return {'assessment_id':identity,'domain':assessment['domain'],'execution':assessment['execution'],
            'mode':assessment['mode'],'official_compliance_result':False,
            'summary':assessment['report']['summary']}
