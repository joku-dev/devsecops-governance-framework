"""Explicit lifecycle composition and exact registered product generation."""
import re
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.v2_source import active_fingerprints,selected_paths
from lib.portable.contracts import ROOT,canonical_digest
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
from lib.retained_argparse import COMPONENTS as PARSER_COMPONENTS
from lib.providers.retained_argparse import capture_context as capture_parser_context

COMPONENTS=('synthetic_lifecycle_reports.py','synthetic_lifecycle_context.py',
 'synthetic_lifecycle_io.py','synthetic_lifecycle_output.py','synthetic_lifecycle_projection.py',
 'synthetic_lifecycle_projection_io.py','synthetic_lifecycle_application.py','synthetic_lifecycle_ports.py',
 'providers/synthetic_lifecycle_io.py','providers/synthetic_lifecycle_output.py',
 'providers/synthetic_lifecycle_projection.py','providers/synthetic_lifecycle_storage.py')


def current_source(node,product_tree=None):
 required={'scripts/lib/'+name for name in COMPONENTS}
 required.add('scripts/templates/governance-lifecycle-viewer.html')
 required.update('scripts/lib/'+name for name in PARSER_COMPONENTS)
 if not required<=set(selected_paths(ROOT)):raise ValueError('synthetic_lifecycle_closure_not_registered')
 if (type(node) is not dict or set(node)!={'node_id','source_revision','runtime_source_digest'}
     or type(node['node_id']) is not str or re.fullmatch('[a-f0-9]{32}',node['node_id']) is None
     or type(node['source_revision']) is not str or re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}',node['source_revision']) is None
     or node['runtime_source_digest']!=source_digest()):raise ValueError('synthetic_lifecycle_node_binding_invalid')
 if product_tree is None:
  if node['source_revision']!=git_read(ROOT,'rev-parse','HEAD').decode().strip():raise ValueError('synthetic_lifecycle_node_generation_changed')
  product_tree=git_read(ROOT,'rev-parse','HEAD^{tree}').decode().strip()
 elif type(product_tree) is not str or re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}',product_tree) is None:raise ValueError('synthetic_lifecycle_product_tree_invalid')
 values=active_fingerprints(ROOT)
 return {'source_root':str(ROOT),'active_fingerprints':values,'source_digest':canonical_digest(values),
  'node_context':dict(node),'product_tree':product_tree,'independent_execution_authenticated':False}
