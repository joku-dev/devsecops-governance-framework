"""Explicit native composition for the whole read-only requirement validator."""
import re
from lib.providers.requirement_validation_source import Source, History, history_commands
from lib.providers.sbom_export_storage import Record, read_record, owned_directory, encode, AUTHORITY
from lib.v2_source import active_fingerprints, selected_paths
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read


def current_source(node, product_tree=None):
    required = {'scripts/lib/requirement_validation.py','scripts/lib/requirement_validation_context.py',
                'scripts/lib/requirement_validation_replay.py','scripts/lib/requirement_validation_application.py',
                'scripts/lib/requirement_validation_ports.py','scripts/lib/providers/requirement_validation_source.py'}
    if not required <= set(selected_paths(ROOT)):
        raise ValueError('requirement_validation_closure_not_registered')
    if (not isinstance(node,dict) or set(node) != {'node_id','source_revision','runtime_source_digest'}
            or not isinstance(node['node_id'],str) or re.fullmatch('[a-f0-9]{32}',node['node_id']) is None
            or not isinstance(node['source_revision'],str) or re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}',node['source_revision']) is None):
        raise ValueError('requirement_validation_node_binding_invalid')
    if node['runtime_source_digest'] != source_digest():
        raise ValueError('requirement_validation_node_generation_changed')
    if product_tree is None:
        if node['source_revision'] != git_read(ROOT,'rev-parse','HEAD').decode().strip():
            raise ValueError('requirement_validation_node_generation_changed')
        product_tree=git_read(ROOT,'rev-parse','HEAD^{tree}').decode().strip()
    elif not isinstance(product_tree,str) or re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}',product_tree) is None:
        raise ValueError('requirement_validation_product_tree_invalid')
    fingerprints = active_fingerprints(ROOT)
    return {'source_root':str(ROOT),'active_fingerprints':fingerprints,
            'source_digest':canonical_digest(fingerprints),'node_context':dict(node),
            'product_tree':product_tree,
            'independent_execution_authenticated':False}
