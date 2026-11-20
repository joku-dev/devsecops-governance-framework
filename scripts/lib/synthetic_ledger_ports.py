"""Explicit ledger composition and exact current product generation binding."""
from lib.providers.synthetic_ledger_io import NativeIO
from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
from lib.providers.synthetic_lifecycle_storage import Record, read_record, encode, AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source, ROOT
from lib.v2_source import selected_paths
from lib.providers.retained_argparse import capture_context as capture_parser_context

COMPONENTS = ('synthetic_ledger_context.py', 'synthetic_ledger_packets.py', 'synthetic_ledger_programs.py',
    'synthetic_ledger_store.py', 'synthetic_ledger_projection.py', 'synthetic_ledger_io.py',
    'synthetic_ledger_effect_state.py', 'synthetic_ledger_replay_effects.py', 'synthetic_ledger_execution.py',
    'synthetic_ledger_private.py', 'synthetic_ledger_application.py', 'synthetic_ledger_ports.py',
    'providers/synthetic_ledger_files.py', 'providers/synthetic_ledger_io.py',
    'providers/synthetic_ledger_effects.py', 'providers/synthetic_ledger_private.py',
    'retained_argparse.py','argparse_profiles/__init__.py','argparse_profiles/cpython312.py',
    'argparse_profiles/cpython311.py','argparse_profiles/cpython313.py','providers/retained_argparse.py',
    'argparse_profiles/LICENSE-3.11.txt','argparse_profiles/NOTICE-3.11.md','argparse_profiles/LICENSE-3.12.txt','argparse_profiles/LICENSE-3.13.txt',
    'argparse_profiles/NOTICE-3.12.md','argparse_profiles/NOTICE-3.13.md')


def current_source(node, product_tree=None):
    if not {'scripts/lib/' + name for name in COMPONENTS} <= set(selected_paths(ROOT)):
        raise ValueError('synthetic_ledger_closure_not_registered')
    return lifecycle_source(node, product_tree)
