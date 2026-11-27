"""Fixed legacy capture/rendering and existing read-only helper port composition."""
from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.providers.personal_channel_protocol import LegacyPersonalProtocol
from lib.personal_channel_process import ReplayPersonalTransport
from lib.providers.accepted_prefix_transport import AcceptedPrefixTransport
from lib.providers.accepted_prefix_paths import NativePrefixPaths
from lib.accepted_prefix_paths import ReplayPrefixPaths
from lib.providers.pilot_receipt_verification_protocol import NativeReceiptVerificationTransport,ReplayReceiptVerificationTransport
from lib.providers.pilot_action_verification_protocol import NativeActionVerificationTransport,ReplayActionVerificationTransport
from lib.providers.operating_verification_protocol import NativeOperatingVerificationTransport,ReplayOperatingVerificationTransport
from lib.providers.lifecycle_preflight import LegacyLifecyclePreflight
from lib.providers.lifecycle_ledger_validation_profile import DESCRIPTION,LegacyLifecycleValidatorMessages
from lib.providers.operating_publication_validation_protocol import NativePublicationValidationTransport,ReplayPublicationValidationTransport
from lib.providers.pilot_run_temporary import NativeTemporaryFactory
from lib.pilot_run_temporary import ReplayTemporaryFactory
from lib.pilot_run_private_temporary import PrivateTemporaryFactory
from lib.personal_channel_ports import exclusive_factory
from lib.lifecycle_ledger_validation_context import execute as execute_kernel

def execute(source,cwd,argv,owner,*,validator_class,parser_context,provider_executable,temporary_parent,publication_base_ref=None):
    native=hasattr(owner,'record')
    def ports(io,root,context,emit):
        personal=NativePersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit,provider_executable=provider_executable) if native else ReplayPersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit)
        result={'personal':personal,'prefix':AcceptedPrefixTransport(io,root,context,emit_stderr=emit)}
        for name,native_type,pure_type in (('receipts',NativeReceiptVerificationTransport,ReplayReceiptVerificationTransport),('actions',NativeActionVerificationTransport,ReplayActionVerificationTransport),('operating',NativeOperatingVerificationTransport,ReplayOperatingVerificationTransport)):
            result[name]=native_type(io,root,emit_stderr=emit,provider_executable=provider_executable) if native else pure_type(io,root,emit_stderr=emit)
        if publication_base_ref is not None:
            result['publication']=NativePublicationValidationTransport(io,root,emit_stderr=emit) if native else ReplayPublicationValidationTransport(io,root,emit_stderr=emit)
        return result
    def temporary(io):
        cls=PrivateTemporaryFactory if io.mode=='private-candidate' else NativeTemporaryFactory if native else ReplayTemporaryFactory
        return cls(io,temporary_parent)
    return execute_kernel(source,cwd,argv,owner,validator_class=validator_class,parser_context=parser_context,
        description=DESCRIPTION,messages=LegacyLifecycleValidatorMessages,ports_factory=ports,
        provider_factory=lambda context,port:LegacyPersonalChannelCapture(context,fetch=port.fetch,clock=port.clock),
        fresh_factory=lambda context,port:LegacyLifecyclePreflight(context,transport=port,clock=port.clock),
        prefix_paths_factory=NativePrefixPaths if native else ReplayPrefixPaths,temporary_factory=temporary,exclusive_factory=exclusive_factory,publication_base_ref=publication_base_ref)


from lib.providers.pilot_run_intake_io import NativeRunIO as NativeIO
from lib.pilot_run_intake_io import ReplayRunIO as ReplayIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.pilot_run_intake_ports import ledger,transaction_name,temporary_parent
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.providers.retained_argparse import capture_context as capture_parser_context
from lib.portable.contracts import ROOT
from lib.v2_source import selected_paths

TRANSPORT_PROFILES=('legacy-lifecycle-ledger-readonly-v1',)
DEFAULT_PROVIDER_EXECUTABLE='gh'
COMPONENTS=('lifecycle_ledger_validation.py','lifecycle_ledger_validation_context.py',
 'lifecycle_ledger_validation_ports.py','lifecycle_ledger_validation_application.py',
 'providers/lifecycle_ledger_validation_profile.py')

def current_source(node,product_tree=None):
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):raise ValueError('lifecycle_validator_closure_not_registered')
    return lifecycle_source(node,product_tree)
def replay_owner(request,events,blob):return ReplayIO(events,blob,request['export_mode'],request['cwd_label'],ledger=ledger(request['source_label']),transaction_name=transaction_name)
def execute_request(request,owner,*,validator_class):
    if request['transport_profile'] not in TRANSPORT_PROFILES:raise ValueError('lifecycle_validator_transport_profile_not_supported')
    return execute(request['source_label'],request['cwd_label'],request['argv'],owner,validator_class=validator_class,
        parser_context=request['parser_context'],provider_executable=request['provider_executable'],temporary_parent=request['temporary_parent'])
