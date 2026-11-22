"""Consumer composition, fixed journal profile and complete installed closure."""
from lib.providers.consumer_lifecycle_io import NativeConsumerIO as NativeIO
from lib.consumer_lifecycle_io import ReplayConsumerIO
from lib.providers.consumer_lifecycle_storage import Record, read_record, encode, AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.providers.consumer_lifecycle_execution import execute as execute_kernel
from lib.providers.retained_argparse import capture_context as capture_parser_context
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.pilot_action_intake_ports import transaction_name
from lib.pilot_run_intake_ports import temporary_parent
from lib.v2_source import selected_paths
from lib.portable.contracts import ROOT

TRANSPORT_PROFILES = ('legacy-consumer-readonly-v1',)
DEFAULT_PROVIDER_EXECUTABLE = 'gh'
COMPONENTS = ('consumer_lifecycle_application.py', 'consumer_lifecycle_ports.py',
    'consumer_lifecycle_contracts.py', 'consumer_lifecycle_admission.py', 'consumer_lifecycle_actions.py',
    'consumer_lifecycle_acceptance.py', 'consumer_lifecycle_program.py', 'consumer_lifecycle_context.py',
    'consumer_lifecycle_io.py', 'consumer_lifecycle_output.py', 'consumer_lifecycle_opa.py', 'consumer_lifecycle_execution.py',
    'providers/consumer_lifecycle_profile.py', 'providers/consumer_lifecycle_evidence.py',
    'providers/consumer_lifecycle_protocol.py', 'providers/consumer_lifecycle_transport.py',
    'providers/consumer_lifecycle_io.py', 'providers/consumer_lifecycle_output.py',
    'providers/consumer_lifecycle_storage.py', 'providers/consumer_lifecycle_opa.py',
    'providers/consumer_lifecycle_execution.py', 'providers/consumer_lifecycle_tools.py', 'personal_channel_process.py')


def current_source(node, product_tree=None):
    if not {'scripts/lib/' + name for name in COMPONENTS} <= set(selected_paths(ROOT)):
        raise ValueError('consumer_lifecycle_closure_not_registered')
    return lifecycle_source(node, product_tree)


def replay_owner(request, events, blob):
    return ReplayConsumerIO(events, blob, request['export_mode'], request['cwd_label'],
                            source=request['source_label'], transaction_name=transaction_name)


def execute_request(request, owner, *, validator_class):
    if request['transport_profile'] not in TRANSPORT_PROFILES:
        raise ValueError('consumer_lifecycle_transport_profile_not_supported')
    return execute_kernel(request['source_label'], request['cwd_label'], request['argv'], owner,
        validator_class=validator_class, parser_context=request['parser_context'],
        provider_executable=request['provider_executable'], temporary_parent=request['temporary_parent'],
        opa_tool=request['opa_tool'], approved_opa_hashes=frozenset(request['approved_opa_hashes']),
        opa_workarea=request['opa_workarea'], invocation=request['invocation'])
