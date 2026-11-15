"""Finite pure report selection; every returned path is an inert output file."""
import json
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib import control_reporting, report_graph
from lib.portable.contracts import ROOT
from lib.portable.runtime import read_json

KINDS = ('graph', 'control-coverage', 'traceability', 'architecture-traceability', 'governance-traceability')
CSV_PATHS = {'traceability': 'generated/xlsx/traceability_matrix.csv',
    'architecture-traceability': 'generated/csv/architecture_runtime_traceability.csv',
    'governance-traceability': 'generated/xlsx/governance_traceability_matrix.csv'}


def build(data, kind):
    if kind == 'all':
        files = {}
        for selected in KINDS: files.update(build(data, selected))
        return files
    if kind not in KINDS: raise ValueError('unsupported_report_kind')
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
