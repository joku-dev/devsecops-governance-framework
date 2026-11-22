"""Explicit existing read-only/native or inert replay helper compositions.

The caller owns its journal, streams, schema resources and temporary scope.
This factory performs no publisher writes and never changes operating authority.
"""
from lib.operational_publication_gate_context import build
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
from lib.providers.operating_publication_validation_protocol import NativePublicationValidationTransport,ReplayPublicationValidationTransport
from lib.providers.lifecycle_preflight import LegacyLifecyclePreflight
from lib.providers.pilot_run_temporary import NativeTemporaryFactory
from lib.pilot_run_temporary import ReplayTemporaryFactory
from lib.pilot_run_private_temporary import PrivateTemporaryFactory
from lib.personal_channel_ports import exclusive_factory

def gates(source,cwd,owner,*,validator_class,provider_executable,temporary_parent,emit_stderr,environment=None):
    native=hasattr(owner,'record')
    def ports(io,root,context):
        personal=NativePersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit_stderr,
            provider_executable=provider_executable,environment=environment) if native else ReplayPersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit_stderr)
        result={'personal':personal,'prefix':AcceptedPrefixTransport(io,root,context,emit_stderr=emit_stderr)}
        for name,native_type,pure_type in (('receipts',NativeReceiptVerificationTransport,ReplayReceiptVerificationTransport),
                ('actions',NativeActionVerificationTransport,ReplayActionVerificationTransport),
                ('operating',NativeOperatingVerificationTransport,ReplayOperatingVerificationTransport)):
            result[name]=native_type(io,root,emit_stderr=emit_stderr,provider_executable=provider_executable,environment=environment) if native else pure_type(io,root,emit_stderr=emit_stderr)
        result['publication']=NativePublicationValidationTransport(io,root,emit_stderr=emit_stderr) if native else ReplayPublicationValidationTransport(io,root,emit_stderr=emit_stderr)
        return result
    def temporary(io):
        cls=PrivateTemporaryFactory if io.mode=='private-candidate' else NativeTemporaryFactory if native else ReplayTemporaryFactory
        return cls(io,temporary_parent)
    return build(source,cwd,owner,validator_class=validator_class,ports_factory=ports,
        provider_factory=lambda context,port:LegacyPersonalChannelCapture(context,fetch=port.fetch,clock=port.clock),
        fresh_factory=lambda context,port:LegacyLifecyclePreflight(context,transport=port,clock=port.clock),
        prefix_paths_factory=NativePrefixPaths if native else ReplayPrefixPaths,
        temporary_factory=temporary,exclusive_factory=exclusive_factory)

def release(owner):
    owner.adapter_cleanup=[]
    try:
        for session in getattr(owner,'personal_exclusive_sessions',[]):session.release()
    finally:
        for session in getattr(owner,'pilot_temporary_sessions',[]):owner.adapter_cleanup.append(session.release())
