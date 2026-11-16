"""Finite pure report selection; every returned path is an inert output file."""
import json
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib import control_reporting, report_graph, report_lineage, report_impact
from lib import report_source_replacement, report_source_intake, report_source_briefs
from lib import report_requirement_delta, report_source_process
from lib import report_model_followup
from lib import report_candidate_maturity, report_intake_health, report_replay_triage, report_portfolio
from lib.report_data import ReportData
from lib.portable.contracts import ROOT
from lib.portable.runtime import read_json

KINDS = ('graph', 'control-coverage', 'traceability', 'architecture-traceability',
         'governance-traceability', 'source-lineage', 'change-impact',
         'source-replacement', 'source-intake', 'source-review-briefs',
         'requirement-delta', 'source-process', 'automation', 'document-controls',
         'open-gaps', 'pipeline-baseline', 'candidate-maturity', 'intake-health', 'replay-triage', 'portfolio')
ADVISORY_REPORTS = {'portfolio': (report_portfolio, 'generated/reports/portfolio-onboarding-status'),
    'candidate-maturity': (report_candidate_maturity, 'generated/reports/harmonized-requirements-maturity'),
    'intake-health': (report_intake_health, 'status/intake-health'),
    'replay-triage': (report_replay_triage, 'generated/reports/replay-triage')}
MODEL_REPORTS = {'automation': report_model_followup.automation,
    'document-controls': report_model_followup.document_controls,
    'open-gaps': report_model_followup.open_gaps,
    'pipeline-baseline': report_model_followup.pipeline_baseline}
SOURCE_REPORTS = {
    'source-lineage': (report_lineage, 'source-lineage-report'),
    'change-impact': (report_impact, 'governance-change-impact'),
    'source-replacement': (report_source_replacement, 'architecture-source-replacement-assessment'),
    'source-intake': (report_source_intake, 'source-document-intake-status'),
    'source-review-briefs': (report_source_briefs, 'source-document-intake-review-briefs'),
    'requirement-delta': (report_requirement_delta, 'source-document-requirement-delta'),
    'source-process': (report_source_process, 'source-document-process-status'),
}
CSV_PATHS = {'traceability': 'generated/xlsx/traceability_matrix.csv',
    'architecture-traceability': 'generated/csv/architecture_runtime_traceability.csv',
    'governance-traceability': 'generated/xlsx/governance_traceability_matrix.csv'}


def build(data, kind, *, membership=None, at=None, window_days=30):
    if type(window_days) is not int or window_days < 1:
        raise ValueError('invalid_intake_health_window')
    if kind not in ('intake-health', 'all') and window_days != 30:
        raise ValueError('intake_health_window_not_applicable')
    if kind == 'all':
        files = {}
        for selected in KINDS:
            files.update(build(data, selected, membership=membership, at=at,
                               window_days=window_days if selected == 'intake-health' else 30))
        return files
    if kind not in KINDS: raise ValueError('unsupported_report_kind')
    if kind in ADVISORY_REPORTS:
        if membership is None or at is None: raise ValueError('explicit_report_membership_and_time_required')
        module, name = ADVISORY_REPORTS[kind]
        context = ReportData(data, membership)
        value = module.generate(context, at, window_days) if kind == 'intake-health' else module.generate(context, at)
        files = {name + '.json': (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()}
        if kind != 'intake-health': files[name + '.md'] = module.render_markdown(value).encode()
        return files
    if kind in MODEL_REPORTS:
        if membership is None: raise ValueError('explicit_report_membership_required')
        return MODEL_REPORTS[kind](ReportData(data, membership))
    if kind in SOURCE_REPORTS:
        if membership is None or at is None: raise ValueError('explicit_report_membership_and_time_required')
        context = ReportData(data, membership)
        module, name = SOURCE_REPORTS[kind]
        value = module.build_report(context, at)
        return {'generated/reports/' + name + '.json': (json.dumps(value, indent=2, allow_nan=False,
                    ensure_ascii=kind != 'source-process') + '\n').encode(),
                'generated/reports/' + name + '.md': module.render_markdown(value).encode()}
    if kind == 'graph':
        value = report_graph.build_graph(data)
        try:
            Draft202012Validator(read_json(ROOT / 'schemas/governance-graph.schema.json'),
                                 format_checker=FormatChecker()).validate(value)
        except ValidationError:
            raise ValueError('invalid_derived_graph_contract') from None
        return {'generated/graph/governance-graph.json': (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()}
    if kind == 'control-coverage':
        value, markdown = control_reporting.control_coverage(data)
        return {'generated/reports/control-coverage-report.json': (json.dumps(value, indent=2, allow_nan=False) + '\n').encode(),
                'generated/reports/control-coverage-report.md': markdown.encode()}
    return {CSV_PATHS[kind]: getattr(control_reporting, kind.replace('-', '_'))(data).encode()}
