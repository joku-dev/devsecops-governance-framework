"""Whole operational decisions/rendering over an explicit presentation profile.

Collection, URLs, workflow names, schema/config files, Git and clocks belong to
the application/adapters. Findings grant no operating authority.
"""
from __future__ import annotations
from datetime import datetime,timezone
import html

def timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError('Timestamp must be a string')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    return parsed.astimezone(timezone.utc)

def age_hours(value: str, now: datetime) -> float:
    age = (now - timestamp(value)).total_seconds() / 3600
    if age < 0:
        raise ValueError('Observation timestamp is in the future')
    return age

def build_report(observation: dict, config: dict, now: datetime, checkout_sha: str, *, profile) -> dict:
    checks = []
    repo_url = profile.repository_url(config['repository'])

    def add(category, subject, status, detail, action, owner='Governance Platform Lead', url=''):
        checks.append({'category': category, 'subject': subject, 'status': status, 'detail': detail, 'action': action, 'owner': owner, 'source_url': url})
    for error in observation.get('errors', []):
        add('observation', error['source'], 'unknown', error['error'], 'Inspect collection logs, API access and input validity; rerun the report.')

    def run_check(name, runs, max_age=None, head=None):
        url = profile.workflow_url(config['repository'], name)
        if runs is None or (name == profile.MAIN_WORKFLOW and (not head)):
            add('workflow', name, 'unknown', 'Run metadata or main SHA unavailable.', profile.CI_ACCESS_ACTION, url=url)
            return
        candidates = [run for run in runs if not head or run.get('head_sha') == head]
        if not candidates:
            add('workflow', name, 'attention', 'No matching main push / scheduled run was observed.', 'Check trigger delivery and workflow enablement; investigate the missing run.', url=url)
            return
        run = candidates[0]
        try:
            age = age_hours(run['created_at'], now)
        except (KeyError, ValueError, TypeError):
            add('workflow', name, 'unknown', 'Invalid run timestamp.', 'Inspect run metadata.', url=url)
            return
        completed = run.get('status') == 'completed'
        ok = completed and run.get('conclusion') == 'success' and (max_age is None or age <= max_age)
        detail = f"Run {run.get('id')}: {run.get('status')}/{run.get('conclusion')}; age {age:.1f}h."
        if not completed and age > config['run_warning_hours']:
            detail += ' Execution/queue time exceeds the warning threshold.'
        if max_age is not None and age > max_age:
            detail += ' Scheduled heartbeat overdue.'
        add('workflow', name, 'ok' if ok else 'attention', detail, 'None.' if ok else 'Inspect run logs/queue; fix the cause and rerun. Manual reruns do not replace the scheduled heartbeat.', url=run.get('html_url', url))
    runs = observation.get('workflow_runs', {})
    run_check(profile.MAIN_WORKFLOW, runs.get(profile.MAIN_WORKFLOW), head=observation.get('main_head'))
    run_check(profile.DOCS_WORKFLOW, runs.get(profile.DOCS_WORKFLOW))
    for name, threshold in config['scheduled_workflows'].items():
        run_check(name, runs.get(name), max_age=threshold)
    for name in profile.INTAKES:
        items = runs.get(name)
        if items is None:
            add('intake', name, 'unknown', 'Intake runs unavailable.', profile.CI_ACCESS_ACTION)
            continue
        failed = []
        invalid = False
        for run in items:
            try:
                age = age_hours(run['created_at'], now)
            except (KeyError, ValueError, TypeError):
                invalid = True
                continue
            if age <= config['intake_failure_window_hours'] and (run.get('status') == 'completed' and run.get('conclusion') != 'success' or (run.get('status') != 'completed' and age > config['run_warning_hours'])):
                failed.append(run)
        add('intake', name, 'unknown' if invalid else 'attention' if failed else 'ok', f'{len(failed)} failed, cancelled, skipped or overdue runs in the observation window.', 'Inspect failed runs and any unmerged evidence PRs; retry after correcting the cause.' if failed or invalid else 'None.', url=profile.workflow_url(config['repository'], name))
    registry = observation.get('registry')
    if not registry or not registry.get('integrations'):
        add('evidence', 'Consumer inventory', 'unknown', 'No consumer inventory available.', 'Restore/complete the integration registry.')
    for entry in (registry or {}).get('integrations', []):
        repository = entry['repository']
        owner = entry.get('action_owner') or entry.get('owner') or 'Repository Owner (assignment required)'
        for domain in profile.INDEXES:
            index = observation.get('indexes', {}).get(domain)
            if index is None:
                add('evidence', f'{repository}: {domain}', 'unknown', 'Result index unavailable.', 'Restore and validate the result index.', owner)
                continue
            row = next((row for row in index.get('repositories', []) if row['repository_id'] == repository), None)
            if row is None and domain != 'devsecops':
                continue
            latest = dict((row or {}).get('latest_result') or {})
            matching = next((item for item in (row or {}).get('history', []) if latest.get('source_file') and item.get('source_file') == latest['source_file'] and (item.get('pipeline_run_id') == latest.get('pipeline_run_id')) and (item.get('commit_id') == latest.get('commit_id'))), {})
            for key in ('pipeline_event', 'branch', 'pipeline_url'):
                if key not in latest and key in matching:
                    latest[key] = matching[key]
            problems = []
            try:
                age_days = age_hours(latest['generated_at'], now) / 24
                if age_days > config['evidence_max_age_days']:
                    problems.append(f'Evidence is {age_days:.1f} days old')
            except (KeyError, ValueError, TypeError):
                age_days = None
                problems.append('Missing/invalid source result timestamp')
            if latest.get('pipeline_event') != 'push' or latest.get('branch') != 'main':
                problems.append('No official mainline push result; fallback remains diagnostic')
            if domain == 'typed_evidence':
                if latest.get('collector_status') != 'collected' or latest.get('finding_count', 0) > 0 or any((latest.get(key) != 'pass' for key in ('freshness', 'content_integrity', 'replay'))):
                    problems.append('Typed evidence contains findings or incomplete verification')
            elif str(latest.get('status', 'missing')).lower() not in ('pass', 'success'):
                problems.append(f"Recorded evaluation: {latest.get('status', 'missing')}")
            add('evidence', f'{repository}: {domain}', 'attention' if problems else 'ok', '; '.join(problems) if problems else f'Current passing mainline evidence ({age_days:.1f} days old).', 'Produce a new consumer mainline result, investigate findings, and review its intake PR.' if problems else 'None.', owner, latest.get('pipeline_url', profile.repository_actions_url(repository)))
    health = observation.get('intake_health')
    if health is None:
        add('intake', 'Collection recovery', 'unknown', 'Telemetry could not be recomputed.', 'Validate intake records and regenerate the health projection.')
    else:
        attempts = health['summary']['collection_attempts']
        unresolved = attempts.get('open', 0) + attempts.get('permanent', 0)
        add('intake', 'Collection recovery', 'attention' if unresolved else 'ok', f"{attempts.get('open', 0)} open, {attempts.get('permanent', 0)} permanent, {attempts.get('resolved', 0)} resolved attempts.", 'Triage open/permanent attempts using the retry runbook; preserve historical records.' if unresolved else 'None.')
        events = health['summary']['events']
        add('intake', 'Intake observation sample', 'ok' if events['total'] else 'attention', f"{events['total']} events in the rolling 30-day window; this is not a blocking-readiness approval.", 'None.' if events['total'] else 'Verify expected consumer activity and dispatch delivery; obtain current evidence.')
    prs = observation.get('pull_requests')
    if prs is None:
        add('review', 'PR queue', 'unknown', 'PR metadata unavailable.', 'Restore pull-request read access.', 'Repository Owner')
    elif not prs:
        add('review', 'PR queue', 'ok', 'No open PRs targeting main.', 'None.', 'Repository Owner')
    for pr in prs or []:
        try:
            age = age_hours(pr['createdAt'], now)
            overdue = age > config['review_warning_hours']
            detail = f"Age {age:.1f}h; review {pr.get('reviewDecision') or 'none'}; merge {pr.get('mergeStateStatus')}; draft {pr.get('isDraft')}."
        except (KeyError, ValueError, TypeError):
            overdue, detail = (True, 'Invalid PR creation timestamp.')
        needs_work = overdue or pr.get('mergeStateStatus') in ('DIRTY', 'BEHIND', 'UNSTABLE') or pr.get('reviewDecision') == 'CHANGES_REQUESTED'
        add('review', f"PR #{pr['number']}", 'attention' if needs_work else 'ok', detail, 'Assign an independent reviewer; inspect checks/conflicts and regenerate operational projections after reconciliation. Do not bypass review.' if needs_work else 'Review within the warning window; approval and merge remain explicit maintainer decisions.', 'Repository Owner', pr['url'])
    security = observation.get('security')
    if not security or not security.get('criteria'):
        add('security', 'Self-security assessment', 'unknown', 'Live assessment unavailable.', 'Restore assessment inputs and read access.', 'Repository Owner / Security')
    else:
        security_observation = security.get('observation', {})
        errors = security_observation.get('api_errors', [])
        missing_settings = [f'{section}.{key}' for section, keys in {'repository': ('visibility', 'default_branch'), 'security_features': ('secret_scanning', 'secret_scanning_push_protection', 'dependabot_security_updates', 'private_vulnerability_reporting'), 'actions': ('allowed_actions', 'sha_pinning_required', 'default_workflow_permissions')}.items() for key in keys if security_observation.get(section, {}).get(key) is None]
        unexpected_errors = [error for error in errors if not profile.expected_optional_protection_error(error)]
        if missing_settings or unexpected_errors:
            add('observation', 'Security API observations', 'unknown', f"Unavailable settings: {', '.join(missing_settings) or 'none'}; {len(unexpected_errors)} other API errors. Full errors retained in the observation artifact.", 'Use the self-security report to distinguish confirmed gaps from inaccessible settings; arrange a scoped authenticated verification.', 'Repository Owner / Security')
        for criterion in security['criteria']:
            action = next((step['action'] for step in security.get('next_steps', []) if criterion['id'] in step['addresses']), 'Inspect the self-security evidence and resolve the finding or missing observation.')
            add('security', f"{criterion['id']}: {criterion['title']}", 'ok' if criterion['status'] == 'pass' else 'attention', criterion['detail'], 'None.' if criterion['status'] == 'pass' else action, 'Repository Owner / Security', profile.workflow_url(config['repository'], profile.SECURITY_WORKFLOW))
    summary = {status: sum((check['status'] == status for check in checks)) for status in ('ok', 'attention', 'unknown')}
    return {'schema_version': '1.0.0', 'generated_at': now.isoformat().replace('+00:00', 'Z'), 'repository': config['repository'], 'checkout_sha': checkout_sha, 'main_head': observation.get('main_head'), 'enforcement': 'report_only', 'overall_status': 'attention' if summary['attention'] else 'unknown' if summary['unknown'] else 'ok', 'summary': summary, 'thresholds': config, 'checks': checks, 'decision_boundary': {'changes_official_results': False, 'approves_prs': False, 'changes_enforcement': False}}

def render_markdown(report: dict) -> str:

    def cell(value):
        return html.escape(str(value)).replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ')
    lines = ['# Daily Governance Operations', '', f"Observed: `{report['generated_at']}`", f"Status: **{report['overall_status']}** — {report['summary']['ok']} OK, {report['summary']['attention']} attention, {report['summary']['unknown']} unknown.", f"Checkout: `{report['checkout_sha']}`; observed main: `{report['main_head']}`.", '', 'A successful workflow means this report was produced; it does not mean governance criteria passed.', 'Thresholds are operational warnings, not approved SLAs. Owners are accountable roles; name the assignee during triage.', '', '| Status | Area | Subject | Observation | Owner | Next action | Source |', '|---|---|---|---|---|---|---|']
    order = {'attention': 0, 'unknown': 1, 'ok': 2}
    for check in sorted(report['checks'], key=lambda check: (order[check['status']], check['category'], check['subject'])):
        lines.append('| ' + ' | '.join((cell(check[key]) for key in ('status', 'category', 'subject', 'detail', 'owner', 'action', 'source_url'))) + ' |')
    lines += ['', 'Read-only observation. Pending PRs do not update official results. No PR approval, merge, waiver or enforcement activation is performed.', 'API failures and capped result sets are visible as unknown; raw observations accompany this report.']
    return '\n'.join(lines) + '\n'
