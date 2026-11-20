"""Explicit candidate source/output composition and complete product generation."""
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.portable.contracts import ROOT
from lib.v2_source import selected_paths
from lib.providers.retained_argparse import capture_context as capture_parser_context

COMPONENTS=('lifecycle_candidate_preparation.py','lifecycle_candidate_preparation_context.py',
    'lifecycle_candidate_preparation_application.py','lifecycle_candidate_preparation_ports.py',
    'retained_argparse.py','providers/retained_argparse.py','argparse_profiles/__init__.py',
    'argparse_profiles/cpython311.py','argparse_profiles/cpython312.py','argparse_profiles/cpython313.py',
    'argparse_profiles/LICENSE-3.11.txt','argparse_profiles/LICENSE-3.12.txt','argparse_profiles/LICENSE-3.13.txt',
    'argparse_profiles/NOTICE-3.11.md','argparse_profiles/NOTICE-3.12.md','argparse_profiles/NOTICE-3.13.md')

def current_source(node,product_tree=None):
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):
        raise ValueError('lifecycle_candidates_closure_not_registered')
    return lifecycle_source(node,product_tree)
