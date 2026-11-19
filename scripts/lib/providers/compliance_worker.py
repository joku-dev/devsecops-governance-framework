"""Fixed own complete-compliance child, launched only by the admitted parent."""
from pathlib import Path
import hashlib
import json
import os
import sys

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib import compliance_operation as contract
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT
from lib.providers.compliance_decisions import record as record_decisions
from lib.providers.compliance_native import NativeComplianceEnvironment
from lib.providers.repository_journal import RepositoryJournal
from lib.result_bytes import safe_bytes, strict_json

OWN_MODULE = 'scripts/lib/providers/compliance_worker.py'
MAX_REQUEST = 64*1024
MAX_RESULT = 8*1024**2


def native_status(decision, environment, selected):
    integration = next((r for r in environment.suboperations if r['kind'] == 'integration'), {})
    repository = next((r for r in environment.suboperations if r['kind'] == 'repository'), {})
    repo = ('pass' if repository.get('original_finding_exit') == 0 else 'fail') \
        if repository.get('execution') == 'complete' else 'incomplete'
    unit = 'not_run' if selected['skip_unit_tests'] else (
        'not_run' if environment.unit_outcome is None else
        'pass' if environment.unit_outcome['returncode'] == 0 else 'fail')
    opa = 'pass' if (environment.opa is not None
        and len(environment.opa.observations) == 22
        and all(r.get('native_outcome', {}).get('exit_code') == 0 for r in environment.opa.observations)) else 'incomplete'
    result = {**contract.result_status(decision, integration=integration.get('execution'),
        repository=repo, unit=unit, opa=opa, skip_unit_tests=selected['skip_unit_tests']),
        'error_type': decision.get('exception', {}).get('type') if decision.get('kind') == 'raised' else None}
    if selected['fail_on_findings'] and result['original_finding_exit'] == 1 and result['modern_exit'] == 0:
        result['modern_exit'] = 1
    return result


def child(request_path):
    from lib.v2_application import instance
    revision = git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()
    if git_read(ROOT, 'show', revision+':'+OWN_MODULE) != Path(__file__).read_bytes():
        raise ValueError('committed_complete_compliance_worker_required')
    path = Path(request_path)
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise ValueError('private_complete_compliance_request_required')
    packet = contract.request(strict_json(safe_bytes(path, limit=MAX_REQUEST)))
    header, selected = packet['binding'], packet['options']
    root = Path(packet['record_root'])
    if path != root/'request.json':
        raise ValueError('complete_compliance_owned_request_required')
    actual_root, settings = instance(header['instance_root'])
    if (str(ROOT) != header['product_source_root'] or revision != header['source_revision']
            or git_read(ROOT, 'rev-parse', 'HEAD^{tree}').decode().strip() != header['source_tree']
            or any(settings[key] != header[key] for key in ('node_id', 'runtime_source_digest', 'source_revision'))):
        raise ValueError('complete_compliance_worker_instance_changed')
    acquisition = root/'acquisition'; acquisition.mkdir(mode=0o700)
    environment = None
    result = {'schema_version': 1, 'binding': header, 'execution': 'incomplete',
        'original_finding_exit': None, 'modern_exit': 2, 'legacy_stdout': '',
        'error_type': None, 'decision_recorded': False,
        'full_default_unit_scope': not selected['skip_unit_tests'], **contract.AUTHORITY}
    with RepositoryJournal(acquisition, header) as journal:
        try:
            environment = NativeComplianceEnvironment(instance_root=actual_root,
                package=packet['package'], package_pin=header['package_sha256'],
                workarea=root/'work', at=header['assessed_at'], cwd=selected['cwd'],
                output_file=selected['output_file'], target_repo=selected['target_repo'],
                input_file=selected['input_file'], on_event=journal.append)
            decision_root = root/'decisions'; decision_root.mkdir(mode=0o700)
            recorded = record_decisions(decision_root, contract.decision_binding(header), environment,
                output_file=selected['output_file'], target_repo=selected['target_repo'],
                input_file=selected['input_file'], skip_unit_tests=selected['skip_unit_tests'],
                on_event=journal.append)
            decision = recorded['decision']['outcome']
            result.update(native_status(decision, environment, selected), decision_recorded=True)
            if result['execution'] == 'complete':
                environment.checkpoint()
        except Exception as error:
            result.update(execution='incomplete', modern_exit=2, error_type=type(error).__name__)
            journal.append({'kind': 'compliance-child-error', 'error_type': type(error).__name__})
        if environment is not None:
            result.update(legacy_stdout=environment.stdout.getvalue(),
                suboperations=environment.suboperations,
                unit_outcome=environment.unit_outcome, unit_statistics=environment.unit_statistics,
                preflight=environment.preflight, tools=environment.tools,
                opa_observations=[] if environment.opa is None else environment.opa.observations,
                export_effects=environment.write_effects, final_source_files=environment.expected,
                execution_source_root=str(environment.root), input_label=str(environment.input_label),
                input_observed=environment.input_observed,
                input_sha256=None if environment.input_bytes is None else hashlib.sha256(environment.input_bytes).hexdigest(),
                viewer_projection=environment.projection)
        raw = (json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(',', ':'))+'\n').encode()
        if len(raw) > MAX_RESULT:
            raise ValueError('complete_compliance_child_result_budget')
        target = root/'result.json'
        with target.open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        target.chmod(0o600)
        journal.append({'kind': 'complete-compliance-child-finished', 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(), 'execution': result['execution']})
    print(json.dumps({'operation_id': header['operation_id'], 'execution': result['execution'],
        'original_finding_exit': result['original_finding_exit'], 'modern_exit': result['modern_exit'],
        'result_sha256': hashlib.sha256(raw).hexdigest(), **contract.AUTHORITY}, separators=(',', ':')))
    return result['modern_exit']


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(2)
    try:
        raise SystemExit(child(sys.argv[1]))
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'execution': 'incomplete', 'error_type': type(error).__name__,
            **contract.AUTHORITY}), file=sys.stderr)
        raise SystemExit(2)
