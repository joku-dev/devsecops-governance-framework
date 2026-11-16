"""One evaluation and gate implementation for CI and service callers."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

import yaml

from control_evaluation import CONTROL_POLICY_MAP, POLICY_QUERIES, evaluate_single_control
from .contracts import ROOT, VERSION, canonical_digest, context_errors, validate

MODES = ('report-only', 'block-on-error')
SEVERITIES = ('none', 'info', 'low', 'medium', 'high', 'critical')
GATE_CONTROLS = {'DSCB-L1-REQ-003', 'DSCB-L1-REQ-006', 'DSCB-L1-REQ-009', 'DSCB-L1-REQ-010', 'DSCB-L1-REQ-011'}


def read_json(path):
    def unique(pairs):
        result = {}
        for key,value in pairs:
            if key in result:
                raise ValueError('duplicate_json_key')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)


def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def baseline(root=ROOT, baseline_id=None):
    registry = read_json(root/'config/portable-runtime-compatibility.json')
    if registry['schema_version'] != VERSION or registry['runtime_version'] != VERSION:
        raise ValueError('unsupported_runtime_compatibility_manifest')
    baseline_id = baseline_id or registry['default_baseline']
    selected = [row for row in registry['baselines'] if row['id']==baseline_id]
    if len(selected)!=1 or selected[0]['scope']!='pipeline-l1' or selected[0]['domain']!='devsecops':
        raise ValueError('unsupported_baseline_scope')
    selected = selected[0]
    package = root/selected['package']
    if not package.resolve().is_relative_to((root/'releases').resolve()):
        raise ValueError('invalid_baseline_package_path')
    manifest = package/'checksums.sha256'
    if file_digest(manifest) != selected['manifest_sha256']:
        raise ValueError('baseline_manifest_checksum_mismatch')
    seen = set()
    for line in manifest.read_text().splitlines():
        expected, relative = line.split('  ', 1)
        path = root / relative
        if (relative in seen or not re.fullmatch('[a-f0-9]{64}', expected) or path.is_symlink()
                or not path.resolve().is_relative_to(package.resolve()) or file_digest(path) != expected):
            raise ValueError('baseline_checksum_mismatch')
        seen.add(relative)
    metadata = read_json(package / 'release-metadata.json')
    if not seen or metadata['release_id'] != baseline_id:
        raise ValueError('invalid_baseline_manifest')
    return package, {'id':metadata['release_id'], 'digest':file_digest(manifest),
                     'source_revision':metadata['source_snapshot']['governance_repo_ref']}


def source_digest():
    paths = [*(p for p in sorted((ROOT/'scripts/lib/portable').glob('*.py')) if p.name!='adapters.py'),
             *sorted((ROOT/'scripts/lib/providers').glob('*.py')), ROOT/'scripts/lib/provider_errors.py', ROOT/'scripts/lib/provider_ports.py', ROOT/'scripts/lib/application_source.py', ROOT/'scripts/lib/v2_boundary.py', ROOT/'scripts/lib/v2_application.py', ROOT/'scripts/axiom_v2.py', ROOT/'config/axiom-v2-boundaries.json', ROOT/'schemas/workbench-publication-v2.schema.json', ROOT/'scripts/control_evaluation.py',
             ROOT/'scripts/governance_runtime.py', ROOT/'scripts/install_validation_opa.py',
             ROOT/'scripts/validation-toolchain.env', ROOT/'config/portable-runtime-compatibility.json', ROOT/'requirements-validation.lock', *sorted((ROOT/'schemas').glob('portable-*-v1.schema.json'))]
    paths.extend([ROOT/'scripts/lib/v2_distribution.py', ROOT/'scripts/lib/v2_source.py', ROOT/'scripts/lib/functional_parity.py', ROOT/'config/axiom-v2-distribution.json'])
    paths.extend([ROOT/'scripts/lib/full_evaluation.py',ROOT/'scripts/lib/architecture_assessment.py',ROOT/'scripts/lib/tool_integrity.py'])
    paths.extend(ROOT/'scripts/lib'/name for name in ('candidate_workspace.py','requirement_application.py','requirement_workspace.py','requirement_lifecycle.py'))
    paths.extend(ROOT/'scripts/lib'/name for name in ('dcr_application.py', 'dcr_manifest.py', 'dcr_structure.py', 'dcr_semantics.py', 'dcr_response.py', 'dcr_evaluation.py'))
    paths.extend(ROOT/'scripts/lib'/name for name in ('dcr_source_context.py','dcr_operations.py','dcr_catalog.py','dcr_projection.py','document_consistency_view.py'))
    for name in ('document-consistency-review-semantic', 'document-consistency-review-semantic-v2', 'document-consistency-review-operations'):
        paths.extend(p for p in sorted((ROOT/'tests/fixtures'/name).rglob('*')) if p.is_file() and p.suffix not in ('.py', '.pyc'))
    paths.extend([ROOT/'scripts/generate_document_consistency_review_model.py',ROOT/'scripts/lib/explicit_requirements.py',ROOT/'scripts/lib/source_document_text.py'])
    paths.extend(sorted((ROOT/'schemas').glob('document-consistency-*.schema.json')))
    paths.extend(sorted((ROOT/'model/governance/document-consistency').glob('*')))
    paths.extend(ROOT/'scripts/lib'/name for name in ('report_graph.py','control_reporting.py','report_sources.py','report_outputs.py','report_application.py','report_data.py','report_lineage.py','report_impact.py','report_source_replacement.py','report_source_intake.py','report_source_briefs.py','report_requirement_delta.py','report_source_process.py','report_model_followup.py','release_assessment.py','combined_reporting.py','domain_reporting.py'))
    paths.extend(ROOT/'schemas'/name for name in ('axiom-v2-report-assessment.schema.json','axiom-v2-domain-report.schema.json','axiom-v2-full-assessment.schema.json','governance-graph.schema.json'))
    paths.extend(ROOT/'scripts/lib'/name for name in ('native_result_logic.py','native_result_assessments.py','result_bytes.py'))
    paths.append(ROOT/'schemas/axiom-v2-native-result-assessment.schema.json')
    paths.extend(ROOT/'scripts/lib'/name for name in ('ci_bundle_results.py','ci_bundle_storage.py','result_assessments.py','result_snapshot_store.py','results_projection.py','result_index_application.py','result_application.py'))
    paths.extend(ROOT/'schemas'/name for name in ('axiom-v2-result-metadata.schema.json','axiom-v2-result-snapshot.schema.json','axiom-v2-result-assessment.schema.json','axiom-v2-result-projection.schema.json','governance-results-index.schema.json','architecture-results-index.schema.json','typed-evidence-results-index.schema.json'))
    paths.extend(ROOT/'scripts/lib'/name for name in ('controls_collection.py','architecture_collection.py','source_collection.py'))
    paths.extend(ROOT/'scripts/lib'/name for name in ('measurement_logic.py','measured_application.py'))
    paths.extend([ROOT/'schemas/measured-l1-assessment.schema.json', ROOT/'schemas/measured-container-security.schema.json'])
    paths.append(ROOT/'schemas/axiom-v2-measured-assessment.schema.json')
    paths.extend(ROOT/name for name in ('scripts/lib/artifact_integrity.py', 'scripts/lib/evidence_verification.py', 'scripts/lib/typed_result_ledger.py', 'scripts/lib/typed_evidence_application.py', 'scripts/lib/providers/typed_capture.py', 'scripts/lib/providers/typed_containers.py', 'scripts/lib/providers/typed_ports.py', 'scripts/lib/result_ledger.py'))
    paths.extend(ROOT/name for name in ('schemas/axiom-v2-typed-assessment.schema.json','schemas/evidence-trust-record.schema.json','schemas/evidence-collector-contract.schema.json','model/evidence/evidence-trust-model.yaml'))
    paths.extend(ROOT/'scripts/lib'/name for name in ('evidence_freshness.py', 'assurance_projection.py', 'staging_projection.py', 'consolidated_projection.py', 'supplement_application.py'))
    paths.extend(ROOT/name for name in ('schemas/axiom-v2-supplement.schema.json','schemas/control-evidence-assurance.schema.json','schemas/staging-deployment-result.schema.json','schemas/consolidated-l1-assessment.schema.json','schemas/typed-evidence-result.schema.json','model/evidence/control-evidence-assurance-profile.yaml','model/evidence/evidence-freshness-policies.yaml','model/evidence/evidence-types.yaml'))
    paths.extend([ROOT/'schemas/axiom-v2-full-assessment.schema.json',ROOT/'schemas/axiom-v2-functional-parity.schema.json'])
    return canonical_digest({str(path.relative_to(ROOT)):file_digest(path) for path in paths})



def approved_opa_hashes(expected):
    hashes = set(re.findall(r'^OPA_\w+_SHA256=([a-f0-9]{64})$', (ROOT/'scripts/validation-toolchain.env').read_text(), re.M))
    for build in read_json(ROOT/'config/portable-runtime-compatibility.json').get('additional_opa_builds',[]):
        if build['version'] != expected or not re.fullmatch('[a-f0-9]{64}',build['sha256']):
            raise ValueError('invalid_opa_build_registry')
        hashes.add(build['sha256'])
    return hashes


def opa_evaluate(payload, directory, opa):
    expected = re.search(r'^OPA_VERSION=(.+)$', (ROOT/'scripts/validation-toolchain.env').read_text(), re.M).group(1)
    if file_digest(opa) not in approved_opa_hashes(expected):
        raise ValueError('opa_checksum_mismatch')
    version = subprocess.run([str(opa), 'version'], capture_output=True, text=True, timeout=15, check=True)
    if not re.search(r'^Version:\s*' + re.escape(expected) + r'\s*$', version.stdout, re.M):
        raise ValueError('opa_version_mismatch')
    results = {}
    with tempfile.TemporaryDirectory(prefix='axiom-evaluate-') as folder:
        path = Path(folder)/'input.json'
        path.write_text(json.dumps(payload))
        for policy, query in POLICY_QUERIES.items():
            result = subprocess.run([str(opa), 'eval', '-f', 'json', '-d', str(directory), '-i', str(path), query],
                                    capture_output=True, text=True, timeout=60, check=False)
            if result.returncode:
                raise ValueError('opa_evaluation_failed')
            try:
                messages = json.loads(result.stdout)['result'][0]['expressions'][0]['value']
                if not isinstance(messages, list) or any(not isinstance(item, str) for item in messages):
                    raise ValueError('invalid_opa_result')
            except (IndexError, KeyError, TypeError, json.JSONDecodeError):
                raise ValueError('invalid_opa_result') from None
            results[policy] = {'status':'fail' if messages else 'pass','deny_count':len(messages),'deny_messages':messages}
    return expected, results


def prepare_evidence(context, checkout, artifact, sbom, scan, governance_input=None):
    """Hash real files. Never invent scanner output or infer provenance from presence."""
    root = Path(checkout).resolve()
    subjects = []
    paths = []
    for role,relative in zip(('artifact','sbom','vulnerability_scan'),(artifact,sbom,scan)):
        path = root / relative
        if (Path(relative).is_absolute() or path.is_symlink() or not path.resolve().is_relative_to(root)
                or not path.is_file() or path.stat().st_size > 256 * 1024 * 1024):
            raise ValueError('missing_or_unsafe_evidence_file')
        paths.append(path)
        subjects.append({'role':role,'path':str(path.relative_to(root)), 'sha256':file_digest(path), 'size':path.stat().st_size})
    inventory, vulnerabilities = read_json(paths[1]), read_json(paths[2])
    if (inventory.get('bomFormat') != 'CycloneDX' or not isinstance(inventory.get('components'), list)
            or not isinstance(inventory.get('metadata', {}).get('component'), dict)):
        raise ValueError('invalid_sbom')
    if (vulnerabilities.get('max_severity') not in SEVERITIES or not isinstance(vulnerabilities.get('findings'), list)
            or not isinstance(vulnerabilities.get('scanner'), str)
            or vulnerabilities['scanner'].lower() in ('', 'placeholder', 'example-scanner', 'synthetic')):
        raise ValueError('invalid_or_synthetic_scan')
    if any(not isinstance(item,dict) or item.get('severity') not in SEVERITIES or not isinstance(item.get('id'),str) or not item['id'].strip() for item in vulnerabilities['findings']):
        raise ValueError('invalid_finding_severity')
    computed = max((SEVERITIES.index(item['severity']) for item in vulnerabilities['findings']), default=0)
    if computed != SEVERITIES.index(vulnerabilities['max_severity']):
        raise ValueError('scan_summary_mismatch')
    digest = subjects[0]['sha256']
    hashes = inventory['metadata']['component'].get('hashes', [])
    linked = any(item.get('alg') == 'SHA-256' and item.get('content') == digest for item in hashes)
    if vulnerabilities.get('artifact_sha256') != digest:
        raise ValueError('scan_artifact_binding_missing')
    payload = deepcopy(governance_input or {})
    payload.update({
        'contract_version':'1.0', 'required_platform_level':'PRA-Level 1', 'release_candidate':False,
        'run_context':{'event':context['ci']['event'], 'purpose':'pull_request_validation' if context['change_request'] else 'branch_validation','release_context':False},
        'pipeline':{'pipeline_id':context['ci']['provider'],'pipeline_run_id':context['ci']['run_id'],
                    'commit_id':context['revision']['tested'],'status':'in_progress','security_gates':{'enforced':None},
                    'security_thresholds_exceeded':None},
        'repository':{'repository_id':context['scm']['path'],'branch':context['revision']['branch']},
        'artifact':{'artifact_id':paths[0].name,'digest':{'exists':True,'linked_to_artifact':True,'value':digest},'signature':{'exists':False}},
        'evidence':{'sbom':{'exists':True,'linked_to_artifact':linked},'vulnerability_scan':{'exists':True,'max_severity':vulnerabilities['max_severity']},'pipeline_execution':{'status':'evaluation_started'}},
        'release':{'approved_waiver':{'exists':False}}, 'waivers':[], 'vulnerabilities':deepcopy(vulnerabilities['findings'])})
    for name, fact in context['capabilities'].items():
        if fact['status'] == 'available' and type(fact['value']) is bool:
            payload['repository'][name] = fact['value']
    return payload, subjects


def evaluate(context, payload, subjects, *, opa, mode='report-only', max_severity='high', at=None):
    if mode not in MODES:
        raise ValueError('unsupported_enforcement_mode')
    if max_severity not in SEVERITIES:
        raise ValueError('unsupported_severity_threshold')
    at = at or datetime.now(timezone.utc).isoformat()
    if datetime.fromisoformat(at.replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('evaluation_time_must_have_timezone')
    package, binding = baseline(baseline_id=context['governance']['baseline_id'])
    result = {'schema_version':VERSION,'scope':'pipeline-l1','generated_at':at,'context':deepcopy(context),
              'context_digest':canonical_digest(context),'baseline':binding,
              'runtime':{'version':VERSION,'source_digest':source_digest(),'opa_version':'not_executed','adapter_version':VERSION},
              'execution':'incomplete','decision':'not_evaluated','evidence_trust':'unverified','full_baseline_assessment':False,
              'checks':[],'controls':[],'diagnostics':context_errors(context),
              'requested_enforcement':mode,'enforcement_observation':{'state':'not_verified','blocks_merge':None},'subjects':subjects}
    if context['governance']['baseline_digest'] != binding['digest']:
        result['diagnostics'].append('context_baseline_digest_mismatch')
    if context['governance']['runtime_source_digest'] != result['runtime']['source_digest']:
        result['diagnostics'].append('context_runtime_digest_mismatch')
    def check(identity, value, message):
        result['checks'].append({'id':identity,'status': 'not_evaluated' if value is None else 'pass' if value else 'fail','message':message})
    check('context_complete', not result['diagnostics'], 'Native identity and tested revision must be complete')
    if len(subjects) != 3 or [row.get('role') for row in subjects] != ['artifact','sbom','vulnerability_scan'] or len({row['path'] for row in subjects}) != 3 or payload.get('artifact',{}).get('digest',{}).get('value') != subjects[0]['sha256']:
        result['diagnostics'].append('subject_manifest_mismatch')
    if payload.get('pipeline', {}).get('commit_id') != context['revision']['tested']:
        result['diagnostics'].append('evidence_revision_mismatch')
    repo = payload.get('repository', {})
    if payload.get('waivers') or payload.get('release',{}).get('approved_waiver',{}).get('exists'):
        result['diagnostics'].append('waiver_authority_not_resolved')
    for name in ('protected_branch','review_required'):
        observed = context['capabilities'].get(name,{})
        expected = observed.get('value') if observed.get('status')=='available' else None
        if repo.get(name) != expected:
            result['diagnostics'].append('context_evidence_fact_mismatch:' + name)
    direct = repo.get('direct_push_allowed')
    fact = context['capabilities'].get('direct_push_allowed', {})
    if fact.get('status') != 'available' or type(direct) is not bool or direct != fact.get('value'):
        result['diagnostics'].append('required_fact_unavailable:direct_push_allowed')
        check('direct_push_prohibited', None, 'No authoritative direct-push fact available')
    else:
        check('direct_push_prohibited', not direct, 'Direct modification must be prohibited')
    if repo.get('protected_branch') is True and type(repo.get('review_required')) is not bool:
        result['diagnostics'].append('required_fact_unavailable:review_required')
    for identity, value in [('artifact_digest',payload.get('artifact',{}).get('digest',{}).get('exists')),
                            ('sbom_artifact_binding',payload.get('evidence',{}).get('sbom',{}).get('linked_to_artifact')),
                            ('vulnerability_scan',payload.get('evidence',{}).get('vulnerability_scan',{}).get('exists'))]:
        check(identity, value if type(value) is bool else None, identity)
        if type(value) is not bool:
            result['diagnostics'].append('required_fact_unavailable:' + identity)
    seen = payload.get('evidence',{}).get('vulnerability_scan',{}).get('max_severity')
    check('severity_threshold', SEVERITIES.index(seen) <= SEVERITIES.index(max_severity) if seen in SEVERITIES else None, 'Maximum allowed severity: ' + max_severity)
    if seen not in SEVERITIES:
        result['diagnostics'].append('required_fact_unavailable:scan_severity')
    if result['diagnostics']:
        return validate('result', result)
    payload = deepcopy(payload)
    payload['pipeline']['security_thresholds_exceeded'] = SEVERITIES.index(seen) > SEVERITIES.index(max_severity)
    version, policies = opa_evaluate(payload, package/'source/policies/opa', opa)
    result['runtime']['opa_version'] = version
    controls = yaml.safe_load((package/'source/model/controls/dscb-l1.yaml').read_text())['requirements']
    for control in controls:
        control = {**control, '_level_file':'L1', '_source_file':str((package/'source/model/controls/dscb-l1.yaml').relative_to(ROOT))}
        if control['id'] in GATE_CONTROLS:
            decision = evaluate_single_control(control, payload, policies)
            binding_check = {'DSCB-L1-REQ-003':'direct_push_prohibited', 'DSCB-L1-REQ-006':'sbom_artifact_binding',
                             'DSCB-L1-REQ-009':'vulnerability_scan', 'DSCB-L1-REQ-010':'severity_threshold',
                             'DSCB-L1-REQ-011':'artifact_digest'}[control['id']]
            checked = next(row for row in result['checks'] if row['id']==binding_check)
            decision['status'] = 'fail' if policies[CONTROL_POLICY_MAP[control['id']]]['status']=='fail' or checked['status']=='fail' else 'pass'
            decision['message'] = 'Portable pipeline-l1 scope: ' + binding_check + '; unchanged Rego policy: ' + CONTROL_POLICY_MAP[control['id']]
            decision['policy_findings'] = policies[CONTROL_POLICY_MAP[control['id']]]['deny_messages']
            # Mapped Rego rules are unchanged; pipeline scope also checks actual supplied files.
        else:
            decision = {'control_id':control['id'],'status':'not_evaluated',
                        'message':'Outside the portable pipeline-l1 gate scope; requires separate governed evidence/review'}
        result['controls'].append(decision)
    result['execution'] = 'complete'
    failed = any(check['status']=='fail' for check in result['checks']) or any(control['status']=='fail' for control in result['controls'])
    result['decision'] = 'fail' if failed else 'pass'
    return validate('result', result)


def gate(result, mode=None):
    validate('result', result)
    mode = mode or result['requested_enforcement']
    if mode not in MODES:
        raise ValueError('unsupported_enforcement_mode')
    if result['context']['synthetic'] and mode == 'block-on-error':
        return 2
    if canonical_digest(result['context']) != result['context_digest']:
        raise ValueError('result_context_digest_mismatch')
    required_checks = {'context_complete','direct_push_prohibited','artifact_digest','sbom_artifact_binding','vulnerability_scan','severity_threshold'}
    if {row['id'] for row in result['checks']} != required_checks or len(result['checks']) != len(required_checks):
        raise ValueError('missing_or_duplicate_gate_checks')
    if result['execution'] != 'complete' or result['decision']=='not_evaluated':
        return 2
    controls = {row['control_id']:row for row in result['controls']}
    if len(controls) != len(result['controls']) or set(controls) != {f'DSCB-L1-REQ-{i:03}' for i in range(1,17)}:
        raise ValueError('missing_or_duplicate_controls')
    if any(controls[identity]['status'] not in ('pass','fail') for identity in GATE_CONTROLS):
        return 2
    if context_errors(result['context']):
        return 2
    if result['diagnostics'] or any(row['status']=='not_evaluated' for row in result['checks']):
        return 2
    failed = any(row['status']=='fail' for row in result['checks']) or any(row['status']=='fail' for row in result['controls'])
    if failed != (result['decision']=='fail'):
        raise ValueError('inconsistent_decision')
    return 1 if failed and mode == 'block-on-error' else 0
