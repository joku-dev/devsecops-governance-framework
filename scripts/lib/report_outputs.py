"""Finite pure report selection; every returned path is an inert output file."""
import json
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib import control_reporting, report_graph, report_lineage, report_impact
from lib.report_data import ReportData
from lib.portable.contracts import ROOT
from lib.portable.runtime import read_json

KINDS = ('graph', 'control-coverage', 'traceability', 'architecture-traceability',
         'governance-traceability', 'source-lineage', 'change-impact')
CSV_PATHS = {'traceability': 'generated/xlsx/traceability_matrix.csv',
    'architecture-traceability': 'generated/csv/architecture_runtime_traceability.csv',
    'governance-traceability': 'generated/xlsx/governance_traceability_matrix.csv'}


def build(data, kind, *, membership=None, at=None):
    if kind == 'all':
        files = {}
        for selected in KINDS: files.update(build(data, selected, membership=membership, at=at))
        return files
    if kind not in KINDS: raise ValueError('unsupported_report_kind')
    if kind in ('source-lineage', 'change-impact'):
        if membership is None or at is None: raise ValueError('explicit_report_membership_and_time_required')
        context = ReportData(data, membership)
        module = report_lineage if kind == 'source-lineage' else report_impact
        name = 'source-lineage-report' if kind == 'source-lineage' else 'governance-change-impact'
        value = module.build_report(context, at)
        return {'generated/reports/' + name + '.json': (json.dumps(value, indent=2, allow_nan=False) + '\n').encode(),
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
