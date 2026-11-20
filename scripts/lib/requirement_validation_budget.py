"""Keep additional source-admission limits separate from original decisions."""
from lib.operations_sources import yaml_value


class InputAdmissionError(Exception):
    """The selected data exceed a technical input bound; no validation verdict."""


YAML_ADMISSION_LIMITS = frozenset((
    'operations_source_file_budget',
    'operations_source_yaml_budget',
    'review_contract_expanded_node_budget',
    'review_contract_depth_budget',
    'review_contract_recursive_alias_not_supported',
    'review_contract_expanded_byte_budget',
))


def yaml_text(value):
    try:
        return yaml_value(value.encode('utf-8'))
    except ValueError as error:
        if str(error) in YAML_ADMISSION_LIMITS:
            raise InputAdmissionError(str(error)) from error
        raise
