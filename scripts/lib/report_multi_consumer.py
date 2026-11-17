"""Original compatibility readiness from normalized source-signature observations."""
from collections import Counter
from lib.identifiers import slugify_repository

def index_repositories(index: dict) -> dict[str, dict]:
    return {item.get('repository_id', ''): item for item in index.get('repositories', []) if item.get('repository_id')}

def expected_results_path(domain: str, repository_id: str) -> str:
    roots = {'devsecops': 'status/results', 'architecture': 'status/architecture-results', 'typed_evidence': 'status/typed-evidence-results'}
    return f'{roots[domain]}/{slugify_repository(repository_id)}/'

def add_check(checks: list[dict], check_id: str, passed: bool, reason: str, refs: list[str]) -> None:
    checks.append({'id': check_id, 'result': 'pass' if passed else 'fail', 'reason': reason, 'evidence_refs': refs})

def build_report(*, registry: dict, indexes: dict[str, dict], portfolio: dict, intake_health: dict, events: list[dict], workflow_observations: dict[str, str]) -> dict:
    integrations = registry.get('integrations', [])
    registered_ids = [item.get('repository', '') for item in integrations]
    registered = set(registered_ids)
    indexed = {domain: index_repositories(index) for domain, index in indexes.items()}
    checks = []
    add_check(checks, 'multiple_consumers_registered', len(registered) >= 2, f'Registry contains {len(registered)} distinct consumer repositories.', ['status/application-repository-integrations.yaml'])
    add_check(checks, 'registry_ids_unique', len(registered_ids) == len(registered) and '' not in registered, 'Every registry entry has a unique owner/repository identifier.', ['status/application-repository-integrations.yaml'])
    declared_count = registry.get('summary', {}).get('integrated_repositories')
    add_check(checks, 'registry_summary_consistent', declared_count == len(registered), f'Registry summary declares {declared_count}; observed {len(registered)}.', ['status/application-repository-integrations.yaml'])
    devsecops_ids = set(indexed.get('devsecops', {}))
    add_check(checks, 'devsecops_registry_coverage', devsecops_ids == registered, 'The DevSecOps latest-state index covers exactly the registered consumers.', ['status/repository-results-index.json'])
    isolation_ok = True
    for domain, repositories in indexed.items():
        if not set(repositories).issubset(registered):
            isolation_ok = False
        for repository_id, item in repositories.items():
            expected = expected_results_path(domain, repository_id)
            latest_source = item.get('latest_result', {}).get('source_file', '')
            if item.get('results_path') != expected or not latest_source.startswith(expected):
                isolation_ok = False
    add_check(checks, 'result_storage_isolated', isolation_ok, 'Every indexed result and latest source remains inside its consumer-specific status path.', ['status/repository-results-index.json', 'status/architecture-results-index.json', 'status/typed-evidence-results-index.json'])
    portfolio_ids = {item.get('repository_id') for item in portfolio.get('repositories', []) if item.get('repository_id')}
    add_check(checks, 'portfolio_registry_coverage', portfolio_ids == registered, 'The portfolio projection contains exactly the registered consumer repositories.', ['generated/reports/portfolio-onboarding-status.json', 'status/application-repository-integrations.yaml'])
    concurrency_ok = bool(workflow_observations) and all((row['repository_scope_expression_present'] and row['run_scope_expression_present'] and row['cancellation_disabled_signature_present'] for row in workflow_observations.values()))
    add_check(checks, 'intake_concurrency_isolated', concurrency_ok, 'All central intake concurrency groups bind consumer repository and downstream run without cancellation.', sorted(workflow_observations))
    event_ids = [event.get('event_id') for event in events]
    event_isolation_ok = len(event_ids) == len(set(event_ids))
    for event in events:
        repository_id = event.get('repository_id', '')
        source_file = event.get('_source_file', '')
        expected_prefix = f'status/intake-events/{slugify_repository(repository_id)}/'
        if repository_id not in registered or not source_file.startswith(expected_prefix):
            event_isolation_ok = False
    add_check(checks, 'telemetry_identity_isolated', event_isolation_ok, 'Intake event IDs are unique and stored below the matching consumer path.', ['status/intake-events/', 'status/intake-health.json'])
    health_repositories = {row.get('value') for row in intake_health.get('dimensions', []) if row.get('dimension') == 'repository_id'}
    add_check(checks, 'health_dimensions_registered', health_repositories.issubset(registered), 'Every consumer represented in Intake Health is present in the integration registry.', ['status/intake-health.json', 'status/application-repository-integrations.yaml'])
    event_counts = Counter((event.get('repository_id') for event in events))
    repository_rows = []
    integration_by_id = {item.get('repository'): item for item in integrations}
    for repository_id in sorted(registered):
        repository_rows.append({'repository_id': repository_id, 'governance_mode': integration_by_id[repository_id].get('governance_mode', 'unknown'), 'devsecops_result': repository_id in indexed.get('devsecops', {}), 'architecture_result': repository_id in indexed.get('architecture', {}), 'typed_evidence_result': repository_id in indexed.get('typed_evidence', {}), 'telemetry_events': event_counts.get(repository_id, 0)})
    candidates = [intake_health.get('generated_at', ''), portfolio.get('generated_at', ''), *[event.get('completed_at', '') for event in events]]
    generated_at = max((value for value in candidates if value), default='1970-01-01T00:00:00Z')
    passed = sum((check['result'] == 'pass' for check in checks))
    failed = len(checks) - passed
    return {'schema_version': '1.0.0', 'report_id': 'multi-consumer-readiness', 'generated_at': generated_at, 'enforcement': 'report_only', 'ready': failed == 0, 'summary': {'registered_consumers': len(registered), 'devsecops_consumers': len(indexed.get('devsecops', {})), 'architecture_consumers': len(indexed.get('architecture', {})), 'typed_evidence_consumers': len(indexed.get('typed_evidence', {})), 'telemetry_consumers': len({event.get('repository_id') for event in events}), 'passed_checks': passed, 'failed_checks': failed}, 'checks': checks, 'repositories': repository_rows}

def render_markdown(report: dict) -> str:
    summary = report['summary']
    lines = ['# Multi-Consumer Readiness', '', f"Generated: `{report['generated_at']}`", '', f"Readiness: `{('PASS' if report['ready'] else 'FAIL')}` (report-only)", '', '| Registered | DevSecOps | Architecture | Typed Evidence | Telemetry | Checks |', '|---:|---:|---:|---:|---:|---:|', f"| {summary['registered_consumers']} | {summary['devsecops_consumers']} | {summary['architecture_consumers']} | {summary['typed_evidence_consumers']} | {summary['telemetry_consumers']} | {summary['passed_checks']} pass / {summary['failed_checks']} fail |", '', '## Checks', '', '| Check | Result | Reason |', '|---|---|---|']
    for check in report['checks']:
        lines.append(f"| `{check['id']}` | `{check['result']}` | {check['reason']} |")
    lines += ['', '## Consumers', '', '| Repository | Mode | DevSecOps | Architecture | Typed Evidence | Telemetry Events |', '|---|---|---:|---:|---:|---:|']
    for row in report['repositories']:
        lines.append(f"| `{row['repository_id']}` | `{row['governance_mode']}` | {row['devsecops_result']} | {row['architecture_result']} | {row['typed_evidence_result']} | {row['telemetry_events']} |")
    lines += ['', 'Readiness proves isolated central storage, indexing, concurrency, portfolio projection, and telemetry identity. It does not require every consumer to produce every optional evidence domain and does not change enforcement.']
    return '\n'.join(lines) + '\n'


def generate(context, at, observations):
    from lib.report_intake_health import records
    return build_report(
        registry=context.yaml(context.root / 'status/application-repository-integrations.yaml'),
        indexes={domain: context.json(context.root / 'status' / name) for domain, name in
            [('devsecops', 'repository-results-index.json'), ('architecture', 'architecture-results-index.json'),
             ('typed_evidence', 'typed-evidence-results-index.json')]},
        portfolio=context.json(context.root / 'generated/reports/portfolio-onboarding-status.json'),
        intake_health=context.json(context.root / 'status/intake-health.json'),
        events=records(context, 'status/intake-events'), workflow_observations=observations)
