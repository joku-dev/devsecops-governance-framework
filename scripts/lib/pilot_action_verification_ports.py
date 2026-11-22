"""Original action-check composition; no writer, publication or temporary port."""
from lib.providers.pilot_run_intake_io import NativeRunIO as NativeIO
from lib.pilot_run_intake_io import ReplayRunIO as ReplayIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture
from lib.providers.pilot_action_verification_protocol import NativeActionVerificationTransport,ReplayActionVerificationTransport
from lib.pilot_run_intake_ports import transaction_name,ledger
from lib.pilot_action_verification_context import execute as execute_kernel
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.portable.contracts import ROOT
from lib.v2_source import selected_paths

TRANSPORT_PROFILES=('legacy-personal-action-git-v1',)
DEFAULT_PROVIDER_EXECUTABLE='gh'
COMPONENTS=('pilot_action_verification.py','pilot_action_verification_context.py',
 'pilot_action_verification_ports.py','pilot_action_verification_application.py',
 'providers/pilot_action_verification_protocol.py')
def current_source(node,product_tree=None):
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):
        raise ValueError('pilot_action_verification_closure_not_registered')
    return lifecycle_source(node,product_tree)
def replay_owner(request,events,blob):
    return ReplayIO(events,blob,request['export_mode'],request['cwd_label'],ledger=ledger(request['source_label']),transaction_name=transaction_name)
def execute(request,owner,*,validator_class):
    if request['transport_profile'] not in TRANSPORT_PROFILES:raise ValueError('pilot_action_verification_transport_profile_not_supported')
    native=hasattr(owner,'record')
    def transport(io,root,emit):
        return NativeActionVerificationTransport(io,root,emit_stderr=emit,provider_executable=request['provider_executable']) if native else ReplayActionVerificationTransport(io,root,emit_stderr=emit)
    return execute_kernel(request['source_label'],request['cwd_label'],request['base_ref'],owner,validator_class=validator_class,
        provider_factory=lambda context,port:LegacyPersonalChannelCapture(context,fetch=port.fetch,clock=port.clock),
        transport_factory=transport,checked_at=request['checked_at'])
