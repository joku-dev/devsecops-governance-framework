"""Original V1 model reports with explicit inert data and fixed output paths.

Automation repairs the stale ROOT/controls layout to the approved model/controls
location. Missing automation fields use the same control's explicit, unique
pipeline placement fields; no gate or classification is inferred. CSV headers
are explicit so legitimate empty reports remain readable.
Neither adjustment changes any control, policy, source status or enforcement.
"""
from collections import Counter, defaultdict
import csv
import io
import yaml

DOCUMENT_FIELDS = ('document_id', 'document_type', 'document_title', 'document_status', 'control_id', 'control_level', 'control_domain', 'control_title', 'rationale')
GAP_FIELDS = ('gap_id', 'category', 'severity', 'subject', 'location', 'summary', 'recommended_action')

def load_yaml(data, path):
    value = yaml.safe_load(data.raw(path))
    if not isinstance(value, dict): raise ValueError('model_report_mapping_required')
    return value


def automation_controls(context):
    controls = []
    for path in sorted(context.glob(context.root / 'model/controls', 'dscb-*.yaml')):
        document = load_yaml(context, path)
        controls.extend({**row, 'level': document.get('level')} for row in document.get('requirements', []))
    if not controls:
        raise ValueError('automation_controls_missing')
    ids = [row['id'] for row in controls]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate_automation_control')
    placements = None
    projected = []
    for control in controls:
        declared = control.get('automation', {})
        if not isinstance(declared, dict):
            raise ValueError('invalid_declared_automation_classification')
        missing = [name for name in ('type', 'maturity', 'check_type') if name not in declared]
        item = {**control, 'automation': dict(declared)}
        if missing:
            if placements is None:
                placements = load_yaml(context, context.root / 'pipeline-baseline/control-placement.yaml')['control_placements']
            matches = [row for row in placements if row['control'] == control['id']]
            if len(matches) != 1:
                raise ValueError('explicit_unique_automation_placement_required')
            placement = matches[0]
            if placement.get('level') != control['level']:
                raise ValueError('automation_placement_level_mismatch')
            fields = {'type': 'gate_type', 'maturity': 'maturity', 'check_type': 'check_type'}
            for name in missing:
                value = placement.get(fields[name])
                if not isinstance(value, str) or not value:
                    raise ValueError('explicit_automation_placement_field_required')
                item['automation'][name] = value
            if 'verification_requirement' not in item and 'verification_requirement' in placement:
                item['verification_requirement'] = placement['verification_requirement']
        projected.append(item)
    return projected

def automation(context):
    controls = automation_controls(context)
    governance = []
    for path in [context.root / 'governance' / 'policy-requirements.yaml', context.root / 'governance' / 'directive-requirements.yaml']:
        data = load_yaml(context, path)
        if 'requirements' not in data:
            continue
        for requirement in data.get('requirements', []):
            governance.append({**requirement, 'source_document': data.get('source_document')})
    if not controls:
        raise ValueError('automation_controls_missing')
    by_type = Counter((item['automation']['type'] for item in controls))
    by_maturity = Counter((item['automation']['maturity'] for item in controls))
    by_check_type = Counter((item['automation']['check_type'] for item in controls))
    by_level = defaultdict(Counter)
    for item in controls:
        by_level[item['level']][item['automation']['type']] += 1
    automation_supported = sum((1 for item in controls if item['automation']['type'] in {'blocking_gate', 'warning_gate', 'evidence_check'}))
    blocking = by_type['blocking_gate']
    lines = ['# Automation Coverage Report', '', '## Summary', '', f'- Total requirements: {len(controls)}', f'- Blocking gates: {blocking}', f'- Automation-supported requirements: {automation_supported}', f"- Review-led requirements: {by_type['review_check']}", f'- Automation-supported coverage: {automation_supported / len(controls):.1%}', f'- Blocking-gate coverage: {blocking / len(controls):.1%}', '', '## By Automation Type', '', '| Type | Count |', '|---|---:|']
    for key in ['blocking_gate', 'warning_gate', 'evidence_check', 'review_check']:
        lines.append(f'| `{key}` | {by_type[key]} |')
    lines.extend(['', '## By Maturity', '', '| Maturity | Count |', '|---|---:|'])
    for key in ['immediate', 'tool_integration_required', 'future']:
        lines.append(f'| `{key}` | {by_maturity[key]} |')
    lines.extend(['', '## By Check Type', '', '| Check Type | Count |', '|---|---:|'])
    for key in ['presence', 'linkage', 'threshold', 'configuration', 'approval', 'review', 'integrity', 'provenance']:
        lines.append(f'| `{key}` | {by_check_type[key]} |')
    lines.extend(['', '## By Level', '', '| Level | Blocking Gate | Warning Gate | Evidence Check | Review Check |', '|---|---:|---:|---:|---:|'])
    for level in ['L1', 'L2', 'L3', 'GOV']:
        counts = by_level[level]
        lines.append(f"| {level} | {counts['blocking_gate']} | {counts['warning_gate']} | {counts['evidence_check']} | {counts['review_check']} |")
    lines.extend(['', '## Governance Requirements', '', f"- Policy requirements: {sum((1 for item in governance if item['source_document'] == 'DevSecOps Policy'))}", f"- Directive requirements: {sum((1 for item in governance if item['source_document'] == 'DevSecOps Directive'))}", f'- Total Policy/Directive requirements: {len(governance)}', '', '| Source | Blocking Gate | Evidence Check | Review Check | Warning Gate |', '|---|---:|---:|---:|---:|'])
    for source in ['DevSecOps Policy', 'DevSecOps Directive']:
        counts = Counter((item['automation']['type'] for item in governance if item['source_document'] == source))
        lines.append(f"| {source} | {counts['blocking_gate']} | {counts['evidence_check']} | {counts['review_check']} | {counts['warning_gate']} |")
    lines.extend(['', '## Requirement Classification', '', '| ID | Level | Title | Type | Maturity |', '|---|---|---|---|---|'])
    for item in sorted(controls, key=lambda x: x['id']):
        lines.append(f"| `{item['id']}` | {item['level']} | {item['title']} | `{item['automation']['type']}` | `{item['automation']['maturity']}` |")
    lines.extend(['', '## Verification Requirements', '', '| ID | Check Type | Verification Requirement |', '|---|---|---|'])
    for item in sorted(controls, key=lambda x: x['id']):
        lines.append(f"| `{item['id']}` | `{item['automation']['check_type']}` | {item.get('verification_requirement', '')} |")
    markdown = '\n'.join(lines) + '\n'
    return {'generated/html/automation_report.md': markdown.encode()}

def pipeline_baseline(context):
    placements = load_yaml(context, context.root / 'pipeline-baseline' / 'control-placement.yaml')['control_placements']
    by_stage = Counter((item['stage'] for item in placements))
    by_gate = Counter((item['gate_type'] for item in placements))
    by_check = Counter((item['check_type'] for item in placements))
    lines = ['# CI/CD Pipeline Control Baseline Report', '', '## Summary', '', f'- Control placements: {len(placements)}', f'- Stages used: {len(by_stage)}', '', '## Controls by Stage', '', '| Stage | Controls |', '|---|---:|']
    for stage in ['plan', 'code', 'build', 'test', 'package', 'release', 'deploy', 'operate']:
        lines.append(f'| `{stage}` | {by_stage[stage]} |')
    lines.extend(['', '## Controls by Gate Type', '', '| Gate Type | Controls |', '|---|---:|'])
    for gate in ['blocking_gate', 'warning_gate', 'evidence_check', 'review_check']:
        lines.append(f'| `{gate}` | {by_gate[gate]} |')
    lines.extend(['', '## Controls by Check Type', '', '| Check Type | Controls |', '|---|---:|'])
    for check_type in ['presence', 'linkage', 'threshold', 'configuration', 'approval', 'review', 'integrity', 'provenance']:
        lines.append(f'| `{check_type}` | {by_check[check_type]} |')
    lines.extend(['', '## Control Placement Detail', '', '| Control | Stage | Gate Type | Check Type | Failure Result | Maturity |', '|---|---|---|---|---|---|'])
    for item in sorted(placements, key=lambda x: x['control']):
        lines.append(f"| `{item['control']}` | `{item['stage']}` | `{item['gate_type']}` | `{item['check_type']}` | `{item['default_gate_result_on_failure']}` | `{item['maturity']}` |")
    markdown = '\n'.join(lines) + '\n'
    return {'generated/html/pipeline_baseline_report.md': markdown.encode()}

def document_controls(context):
    controls = {}
    for path in sorted(context.glob(context.root / 'model' / 'controls', 'dscb-*.yaml')):
        data = load_yaml(context, path)
        level = data.get('level')
        for requirement in data.get('requirements', []):
            controls[requirement['id']] = {**requirement, 'level': level}
    documents = load_yaml(context, context.root / 'model' / 'documents' / 'governance-documents.yaml').get('documents', [])
    mappings = load_yaml(context, context.root / 'model' / 'traceability' / 'document-to-control.yaml').get('mappings', [])
    document_by_id = {item['id']: item for item in documents}
    rows = []
    for mapping in mappings:
        document = document_by_id[mapping['document_id']]
        control_ids = set(mapping.get('control_ids', []))
        control_levels = set(mapping.get('control_levels', []))
        matched_controls = []
        for control_id, control in controls.items():
            if control_id in control_ids or control['level'] in control_levels:
                matched_controls.append((control_id, control))
        matched_controls.sort(key=lambda item: item[0])
        for control_id, control in matched_controls:
            rows.append({'document_id': document['id'], 'document_type': document['type'], 'document_title': document['title'], 'document_status': document['status'], 'control_id': control_id, 'control_level': control['level'], 'control_domain': control['domain'], 'control_title': control['title'], 'rationale': mapping['rationale']})
    handle = io.StringIO(newline='')
    writer = csv.DictWriter(handle, fieldnames=DOCUMENT_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    csv_text = handle.getvalue()
    lines = ['# Document To Control Authority Matrix', '', f'Document Count: `{len(documents)}`', f'Mapped Rows: `{len(rows)}`', '', '| Document | Type | Control | Level | Domain | Rationale |', '| --- | --- | --- | --- | --- | --- |']
    for row in rows:
        lines.append(f"| `{row['document_id']}` {row['document_title']} | `{row['document_type']}` | `{row['control_id']}` {row['control_title']} | `{row['control_level']}` | `{row['control_domain']}` | {row['rationale']} |")
    markdown = '\n'.join(lines) + '\n'
    return {'generated/xlsx/document_control_matrix.csv': csv_text.encode(), 'generated/reports/document-control-matrix.md': markdown.encode()}

def collect_controls(context):
    controls = {}
    for path in sorted(context.glob(context.root / 'model' / 'controls', 'dscb-*.yaml')):
        data = load_yaml(context, path)
        level = data.get('level')
        for requirement in data.get('requirements', []):
            controls[requirement['id']] = {**requirement, 'level': level, 'source_file': str(path.relative_to(context.root))}
    return controls

def open_gaps(context):
    controls = collect_controls(context)
    documents = load_yaml(context, context.root / 'model' / 'documents' / 'governance-documents.yaml').get('documents', [])
    capabilities = load_yaml(context, context.root / 'model' / 'platform' / 'platform-capabilities.yaml').get('capabilities', [])
    waiver_authorities = load_yaml(context, context.root / 'model' / 'waivers' / 'waiver-authorities.yaml').get('authorities', {})
    waiver_schema = load_yaml(context, context.root / 'schemas' / 'waiver.schema.json')
    rows = []
    for document in documents:
        if document['status'] == 'draft':
            rows.append({'gap_id': f"GAP-DOC-{document['id']}", 'category': 'governance_document_status', 'severity': 'medium', 'subject': document['id'], 'location': document['repository_path'], 'summary': f"{document['title']} is still in draft status.", 'recommended_action': 'Review, approve, and update the catalog status once the document is formally adopted.'})
    for capability in capabilities:
        if capability.get('area') == 'TBD':
            rows.append({'gap_id': f"GAP-CAP-{capability['id']}", 'category': 'platform_capability_model', 'severity': 'medium', 'subject': capability['id'], 'location': 'model/platform/platform-capabilities.yaml', 'summary': f"Platform capability {capability['id']} still uses placeholder area 'TBD'.", 'recommended_action': 'Assign the capability to a concrete architectural area for governance and ownership reporting.'})
    for control_id, control in controls.items():
        verification_method = control.get('verification', {}).get('method')
        policy = control.get('policy_as_code', {})
        if verification_method == 'automated' and (not policy.get('candidate')):
            rows.append({'gap_id': f'GAP-POL-{control_id}', 'category': 'policy_automation_candidate', 'severity': 'low', 'subject': control_id, 'location': control['source_file'], 'summary': f'{control_id} uses automated verification but is not yet modeled as a policy-as-code candidate.', 'recommended_action': 'Review whether this control should remain evidence-only or be promoted into an executable policy candidate.'})
    schema_risk_levels = set(waiver_schema['properties']['risk_classification']['enum'])
    authority_risk_levels = set(waiver_authorities.keys())
    for risk_level in sorted(schema_risk_levels - authority_risk_levels):
        rows.append({'gap_id': f'GAP-WAIVER-AUTH-{risk_level}', 'category': 'waiver_governance', 'severity': 'high', 'subject': risk_level, 'location': 'model/waivers/waiver-authorities.yaml', 'summary': f'Waiver schema allows risk classification {risk_level} but no approval authority is defined.', 'recommended_action': 'Add an explicit approval authority for the missing risk classification.'})
    for risk_level in sorted(authority_risk_levels - schema_risk_levels):
        rows.append({'gap_id': f'GAP-WAIVER-SCHEMA-{risk_level}', 'category': 'waiver_governance', 'severity': 'high', 'subject': risk_level, 'location': 'schemas/waiver.schema.json', 'summary': f'Waiver authorities define risk classification {risk_level} but the waiver schema does not allow it.', 'recommended_action': 'Align the waiver schema with the defined approval authority model.'})
    rows.sort(key=lambda item: (item['severity'], item['category'], item['subject']))
    handle = io.StringIO(newline='')
    writer = csv.DictWriter(handle, fieldnames=GAP_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    csv_text = handle.getvalue()
    severity_counts = {'high': sum((1 for row in rows if row['severity'] == 'high')), 'medium': sum((1 for row in rows if row['severity'] == 'medium')), 'low': sum((1 for row in rows if row['severity'] == 'low'))}
    lines = ['# Open Gap Report', '', f'Gap Count: `{len(rows)}`', f"High: `{severity_counts['high']}`", f"Medium: `{severity_counts['medium']}`", f"Low: `{severity_counts['low']}`", '', '| Gap | Category | Severity | Subject | Location | Summary | Recommended Action |', '| --- | --- | --- | --- | --- | --- | --- |']
    for row in rows:
        lines.append(f"| `{row['gap_id']}` | `{row['category']}` | `{row['severity']}` | `{row['subject']}` | `{row['location']}` | {row['summary']} | {row['recommended_action']} |")
    markdown = '\n'.join(lines) + '\n'
    return {'generated/xlsx/open_gap_report.csv': csv_text.encode(), 'generated/reports/open-gap-report.md': markdown.encode()}
