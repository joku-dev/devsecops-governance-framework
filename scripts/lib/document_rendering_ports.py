"""Explicit native document composition and exact registered product bytes."""
import re
from lib.providers.document_rendering_io import Data,Output
from lib.providers.document_rendering_tools import Tools
from lib.providers.sbom_export_storage import Record,read_record,owned_directory,encode,AUTHORITY
from lib.v2_source import active_fingerprints,selected_paths
from lib.portable.contracts import ROOT,canonical_digest
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
from lib.retained_argparse import COMPONENTS as PARSER_COMPONENTS
from lib.providers.retained_argparse import capture_context as capture_parser_context


def current_source(node,product_tree=None):
    required={'scripts/lib/'+name for name in ('document_rendering.py','document_rendering_context.py',
        'document_rendering_io.py','document_rendering_ports.py','document_rendering_application.py',
        'providers/document_rendering_io.py','providers/document_rendering_tools.py')}
    required.update('scripts/lib/'+name for name in PARSER_COMPONENTS)
    if not required<=set(selected_paths(ROOT)):raise ValueError('document_rendering_closure_not_registered')
    if (type(node) is not dict or set(node)!={'node_id','source_revision','runtime_source_digest'}
            or type(node['node_id']) is not str or re.fullmatch('[a-f0-9]{32}',node['node_id']) is None
            or type(node['source_revision']) is not str or re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}',node['source_revision']) is None
            or node['runtime_source_digest']!=source_digest()):raise ValueError('document_rendering_node_binding_invalid')
    if product_tree is None:
        if node['source_revision']!=git_read(ROOT,'rev-parse','HEAD').decode().strip():raise ValueError('document_rendering_node_generation_changed')
        product_tree=git_read(ROOT,'rev-parse','HEAD^{tree}').decode().strip()
    elif type(product_tree) is not str or re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}',product_tree) is None:raise ValueError('document_rendering_product_tree_invalid')
    values=active_fingerprints(ROOT)
    return {'source_root':str(ROOT),'active_fingerprints':values,'source_digest':canonical_digest(values),
        'node_context':dict(node),'product_tree':product_tree,'independent_execution_authenticated':False}
