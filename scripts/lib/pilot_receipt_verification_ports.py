"""Composition for original fresh receipt verification; no ledger writer is supplied."""
from lib.providers.pilot_run_intake_io import NativeRunIO as NativeIO
from lib.pilot_run_intake_io import ReplayRunIO as ReplayIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
from lib.providers.lifecycle_preflight import LegacyLifecyclePreflight
from lib.providers.pilot_receipt_verification_protocol import NativeReceiptVerificationTransport,ReplayReceiptVerificationTransport
from lib.providers.pilot_run_temporary import NativeTemporaryFactory
from lib.pilot_run_temporary import ReplayTemporaryFactory
from lib.pilot_run_private_temporary import PrivateTemporaryFactory
from lib.personal_channel_ports import exclusive_factory
from lib.pilot_run_intake_ports import temporary_parent,transaction_name,ledger
from lib.pilot_receipt_verification_context import execute as execute_kernel
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.portable.contracts import ROOT
from lib.v2_source import selected_paths

TRANSPORT_PROFILES=('legacy-preflight-receipt-git-v1',)
DEFAULT_PROVIDER_EXECUTABLE='gh'
COMPONENTS=('pilot_receipt_verification.py','pilot_receipt_verification_context.py',
 'pilot_receipt_verification_ports.py','pilot_receipt_verification_application.py',
 'providers/pilot_receipt_verification_protocol.py')
def current_source(node,product_tree=None):
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):
        raise ValueError('pilot_receipt_verification_closure_not_registered')
    return lifecycle_source(node,product_tree)
def replay_owner(request,events,blob):
    return ReplayIO(events,blob,request['export_mode'],request['cwd_label'],ledger=ledger(request['source_label']),transaction_name=transaction_name)
def execute(request,owner,*,validator_class):
    if request['transport_profile'] not in TRANSPORT_PROFILES:raise ValueError('pilot_receipt_verification_transport_profile_not_supported')
    native=hasattr(owner,'record');selected=request['export_mode']=='selected-files'
    def transport(io,root,emit):
        return NativeReceiptVerificationTransport(io,root,emit_stderr=emit,provider_executable=request['provider_executable']) if native else ReplayReceiptVerificationTransport(io,root,emit_stderr=emit)
    def temporary(io):
        kind=PrivateTemporaryFactory if not selected else NativeTemporaryFactory if native else ReplayTemporaryFactory
        return kind(io,request['temporary_parent'])
    return execute_kernel(request['source_label'],request['cwd_label'],request['base_ref'],owner,validator_class=validator_class,
        historical_provider_factory=lambda context:LegacyRepositoryLifecycleCapture(context),
        fresh_provider_factory=lambda context,port:LegacyLifecyclePreflight(context,transport=port,clock=port.clock),
        transport_factory=transport,exclusive_factory=exclusive_factory,temporary_factory=temporary)
