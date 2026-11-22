"""Explicit readonly legacy transports, exact store effects, clocks and temporary scope."""
from lib.providers.pilot_update_io import NativeUpdateIO
from lib.pilot_update_io import ReplayUpdateIO
from lib.providers.pilot_update_protocol import NativePilotUpdateTransport,ReplayPilotUpdateTransport,DESCRIPTION
from lib.providers.lifecycle_preflight_protocol import NativePreflightTransport,ReplayPreflightTransport
from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture
from lib.providers.lifecycle_preflight import LegacyLifecyclePreflight
from lib.providers.pilot_action_ledgers import native_effects
from lib.pilot_action_ledgers import replay_effects
from lib.providers.pilot_run_temporary import NativeTemporaryFactory
from lib.pilot_run_temporary import ReplayTemporaryFactory
from lib.pilot_run_private_temporary import PrivateTemporaryFactory
from lib.providers.pilot_action_intake_clock import NativeActionRecordedClock
from lib.pilot_action_intake_clock import ReplayActionRecordedClock
from lib.personal_channel_ports import exclusive_factory
from lib.pilot_update_context import execute as execute_kernel

def execute(source,cwd,argv,owner,*,validator_class,parser_context,provider_executable,temporary_parent,invocation=None):
    native=hasattr(owner,'record')
    def ports(io,root,emit):
        return {'personal':NativePilotUpdateTransport(io,root,emit_stderr=emit,provider_executable=provider_executable) if native else ReplayPilotUpdateTransport(io,root,emit_stderr=emit),
                'preflight':NativePreflightTransport(io,root,emit_stderr=emit,provider_executable=provider_executable) if native else ReplayPreflightTransport(io,root,emit_stderr=emit)}
    def temporary(io):
        cls=PrivateTemporaryFactory if io.mode=='private-candidate' else NativeTemporaryFactory if native else ReplayTemporaryFactory
        return cls(io,temporary_parent)
    return execute_kernel(source,cwd,argv,owner,validator_class=validator_class,parser_context=parser_context,description=DESCRIPTION,ports_factory=ports,
        provider_factory=lambda ctx,port:LegacyPersonalChannelCapture(ctx,fetch=port.fetch,clock=port.clock),fresh_factory=lambda ctx,port:LegacyLifecyclePreflight(ctx,transport=port,clock=port.clock),
        effects_factory=native_effects if native else replay_effects,exclusive_factory=exclusive_factory,temporary_factory=temporary,
        clock_factory=NativeActionRecordedClock if native else ReplayActionRecordedClock,invocation=invocation)


from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.pilot_action_intake_ports import transaction_name
from lib.pilot_run_intake_ports import temporary_parent
from lib.providers.retained_argparse import capture_context as capture_parser_context
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.v2_source import selected_paths
from lib.portable.contracts import ROOT
NativeIO=NativeUpdateIO
TRANSPORT_PROFILES=('legacy-pilot-update-readonly-v1',)
DEFAULT_PROVIDER_EXECUTABLE='gh'
COMPONENTS=('operating_capture.py','pilot_update_program.py','pilot_update_context.py','pilot_update_io.py','pilot_update_ports.py','pilot_update_application.py','providers/pilot_update_protocol.py','providers/pilot_update_io.py','personal_channel_process.py','providers/personal_channel_transport.py')
def current_source(node,product_tree=None):
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):raise ValueError('pilot_update_closure_not_registered')
    return lifecycle_source(node,product_tree)
def replay_owner(request,events,blob):return ReplayUpdateIO(events,blob,request['export_mode'],request['cwd_label'],source=request['source_label'],transaction_name=transaction_name)
def execute_request(request,owner,*,validator_class):
    if request['transport_profile'] not in TRANSPORT_PROFILES:raise ValueError('pilot_update_transport_profile_not_supported')
    return execute(request['source_label'],request['cwd_label'],request['argv'],owner,validator_class=validator_class,parser_context=request['parser_context'],provider_executable=request['provider_executable'],temporary_parent=request['temporary_parent'],invocation=request['invocation'])
