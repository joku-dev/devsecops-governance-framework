"""Explicit fresh collection, two-ledger effects and separately sampled record clock."""
from lib.providers.pilot_action_ledgers import NativeActionIO as NativeIO,native_effects
from lib.pilot_action_ledgers import ReplayActionIO,replay_effects
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.personal_channel_process import ReplayPersonalTransport
from lib.providers.personal_channel_protocol import LegacyPersonalProtocol
from lib.providers.pilot_action_intake_clock import NativeActionRecordedClock
from lib.pilot_action_intake_clock import ReplayActionRecordedClock
from lib.pilot_action_intake_context import execute as execute_kernel
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.portable.contracts import ROOT
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.v2_source import selected_paths
from lib.providers.retained_argparse import capture_context as capture_parser_context

TRANSPORT_PROFILES=('legacy-personal-github-get-v1',)
DEFAULT_PROVIDER_EXECUTABLE='gh'
COMPONENTS=('pilot_action_intake.py','pilot_action_intake_context.py','pilot_action_intake_clock.py',
    'pilot_action_ledgers.py','providers/pilot_action_ledgers.py','providers/pilot_action_intake_clock.py',
    'pilot_action_intake_application.py','pilot_action_intake_ports.py')

def current_source(node,product_tree=None):
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):
        raise ValueError('pilot_action_intake_closure_not_registered')
    return lifecycle_source(node,product_tree)

def transaction_name(raw):
    context=RepositoryLifecycle(ROOT,validator_class=None)
    return context.kernel.transaction_name(context.adapter.strict_json(raw))

def replay_owner(request,events,blob):
    return ReplayActionIO(events,blob,request['export_mode'],request['cwd_label'],source=request['source_label'],transaction_name=transaction_name)

def execute(request,owner,*,validator_class):
    if request['transport_profile'] not in TRANSPORT_PROFILES:raise ValueError('pilot_action_intake_transport_profile_not_supported')
    native=hasattr(owner,'record')
    def transport(io,root,emit):
        if native:return NativePersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit,provider_executable=request['provider_executable'])
        return ReplayPersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit)
    return execute_kernel(request['source_label'],request['cwd_label'],request['argv'],owner,
        validator_class=validator_class,provider_factory=lambda context,port:LegacyPersonalChannelCapture(context,fetch=port.fetch,clock=port.clock),
        transport_factory=transport,effects_factory=native_effects if native else replay_effects,
        clock_factory=NativeActionRecordedClock if native else ReplayActionRecordedClock,parser_context=request['parser_context'])
