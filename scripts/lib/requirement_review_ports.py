"""Explicit native composition for original advisory report execution."""
import re
from lib.providers.requirement_validation_source import Source
from lib.providers.requirement_review_output import Output
from lib.providers.requirement_review_profile import LEGACY_MIGRATION_INVENTORY,empty_min_error
from lib.providers.sbom_export_storage import Record,read_record,owned_directory,encode,AUTHORITY
from lib.v2_source import active_fingerprints,selected_paths
from lib.portable.contracts import ROOT,canonical_digest
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read


def current_source(node,product_tree=None):
    required={
        'scripts/lib/requirement_migration_generation.py','scripts/lib/requirement_platform_generation.py',
        'scripts/lib/requirement_review_context.py','scripts/lib/requirement_review_output.py',
        'scripts/lib/requirement_review_application.py','scripts/lib/requirement_review_ports.py',
        'scripts/lib/requirement_validation_budget.py','scripts/lib/requirement_validation_replay.py',
        'scripts/lib/providers/requirement_validation_source.py',
        'scripts/lib/providers/requirement_review_output.py','scripts/lib/providers/requirement_review_profile.py',
    }
    if not required<=set(selected_paths(ROOT)):
        raise ValueError('requirement_review_closure_not_registered')
    if (type(node) is not dict or set(node)!={'node_id','source_revision','runtime_source_digest'}
            or type(node['node_id']) is not str or not re.fullmatch('[a-f0-9]{32}',node['node_id'])
            or type(node['source_revision']) is not str or not re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}',node['source_revision'])
            or node['runtime_source_digest']!=source_digest()):
        raise ValueError('requirement_review_node_binding_invalid')
    if product_tree is None:
        if node['source_revision']!=git_read(ROOT,'rev-parse','HEAD').decode().strip():
            raise ValueError('requirement_review_node_generation_changed')
        product_tree=git_read(ROOT,'rev-parse','HEAD^{tree}').decode().strip()
    elif type(product_tree) is not str or not re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}',product_tree):
        raise ValueError('requirement_review_product_tree_invalid')
    values=active_fingerprints(ROOT)
    return {'source_root':str(ROOT),'active_fingerprints':values,'source_digest':canonical_digest(values),
            'node_context':dict(node),'product_tree':product_tree,'independent_execution_authenticated':False}
