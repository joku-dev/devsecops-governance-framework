"""Explicit selected-file/Git composition and registered product generation."""
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.providers.documentation_reconciliation_git import NativeGit
from lib.providers.documentation_reconciliation_append import NativeAppend
from lib.documentation_reconciliation_git import ReplayGit
from lib.documentation_reconciliation_append import ReplayAppend
from lib.documentation_reconciliation_private import PrivateAppend
from lib.documentation_reconciliation_context import execute as execute_kernel
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.portable.contracts import ROOT
from lib.v2_source import selected_paths
from lib.providers.retained_argparse import capture_context as capture_parser_context

COMPONENTS=('documentation_reconciliation.py','documentation_reconciliation_context.py',
    'documentation_reconciliation_git.py','documentation_reconciliation_append.py',
    'documentation_reconciliation_private.py','documentation_reconciliation_ports.py',
    'documentation_reconciliation_application.py','providers/documentation_reconciliation_git.py',
    'providers/documentation_reconciliation_append.py',
    'retained_argparse.py','providers/retained_argparse.py','argparse_profiles/__init__.py',
    'argparse_profiles/cpython311.py','argparse_profiles/cpython312.py','argparse_profiles/cpython313.py',
    'argparse_profiles/LICENSE-3.11.txt','argparse_profiles/LICENSE-3.12.txt','argparse_profiles/LICENSE-3.13.txt',
    'argparse_profiles/NOTICE-3.11.md','argparse_profiles/NOTICE-3.12.md','argparse_profiles/NOTICE-3.13.md')

def current_source(node,product_tree=None):
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):
        raise ValueError('documentation_reconciliation_closure_not_registered')
    return lifecycle_source(node,product_tree)

def append_factory(owner,path,label):
    cls=PrivateAppend if owner.mode=='private-candidate' else NativeAppend if hasattr(owner,'record') else ReplayAppend
    return cls(owner,path,label)

def execute(source,cwd,argv,owner,process_factory,*,parser_context=None):
    return execute_kernel(source,cwd,argv,owner,process_factory,append_factory=append_factory,parser_context=parser_context)
