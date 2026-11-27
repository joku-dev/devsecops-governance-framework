"""Same consumer read-only transports, independent OPA and full acceptance gate.

This composition is not an acceptance grant. Actual publication remains a
separately selected native operation with potentially partial external effects.
"""
from lib.consumer_publication_gate_context import build
from lib.providers.consumer_lifecycle_execution import DeferredEvidence,ConsumerProcesses
from lib.providers.consumer_lifecycle_profile import LegacyConsumerProfile
from lib.providers.consumer_lifecycle_evidence import LegacyConsumerEvidence
from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture
from lib.providers.consumer_lifecycle_transport import (NativeConsumerTransport,ReplayConsumerTransport,
    NativeConsumerCentralTransport,ReplayConsumerCentralTransport)
from lib.providers.consumer_lifecycle_opa import NativeConsumerOPA,LegacyConsumerOPAProfile
from lib.consumer_lifecycle_opa import ReplayConsumerOPA
from lib.providers.consumer_lifecycle_io import native_effects
from lib.consumer_lifecycle_io import replay_effects
from lib.providers.pilot_run_temporary import NativeTemporaryFactory
from lib.pilot_run_temporary import ReplayTemporaryFactory
from lib.pilot_run_private_temporary import PrivateTemporaryFactory
from lib.personal_channel_ports import exclusive_factory
from lib.requirement_validation_replay import IntegrityError


def gates(source,cwd,owner,*,validator_class,provider_executable,temporary_parent,emit_stderr,
          opa_tool,approved_opa_hashes,opa_workarea,environment=None):
    native=hasattr(owner,'record')
    def ports(io,root,context):
        central=(NativeConsumerCentralTransport(io,root,emit_stderr=emit_stderr,environment=environment,provider_executable=provider_executable)
                 if native else ReplayConsumerCentralTransport(io,root,emit_stderr=emit_stderr))
        def reader():
            profile=context.consumer_contracts.load_operating(root)
            return (NativeConsumerTransport(io,root,profile,emit_stderr=emit_stderr,environment=environment,provider_executable=provider_executable)
                    if native else ReplayConsumerTransport(io,root,profile,emit_stderr=emit_stderr))
        def policy():
            if native:return NativeConsumerOPA(io,root,tool=opa_tool,approved_hashes=approved_opa_hashes,workarea=opa_workarea)
            return ReplayConsumerOPA(io,root,profile=LegacyConsumerOPAProfile(),tool=str(opa_tool),approved_hashes=approved_opa_hashes,workarea=opa_workarea)
        return {'central':central,'evidence':DeferredEvidence(reader),'process':ConsumerProcesses(central,policy)}
    def temporary(io):
        cls=PrivateTemporaryFactory if io.mode=='private-candidate' else NativeTemporaryFactory if native else ReplayTemporaryFactory
        return cls(io,temporary_parent)
    def evidence(root,context,profile,architecture,reader,process,temporary,clock,validator,path):
        return LegacyConsumerEvidence(root,context,path_factory=path,profile=profile,process=process,
            temporary=temporary,clock=clock,validator_class=validator,default_fetch=reader.fetch,architecture=architecture)
    return build(source,cwd,owner,validator_class=validator_class,ports_factory=ports,
        profile_factory=lambda context,port:LegacyConsumerProfile(context,default_fetch=port.fetch),
        provider_factory=lambda context,port:LegacyPersonalChannelCapture(context,fetch=port.fetch,clock=port.clock),
        evidence_factory=evidence,effects_factory=native_effects if native else replay_effects,
        exclusive_factory=exclusive_factory,temporary_factory=temporary)


def release(owner):
    owner.adapter_cleanup=[]
    try:
        process=getattr(owner,'consumer_publication_process',None)
        if process is not None:process.finish()
        effects=getattr(owner,'consumer_publication_effects',None)
        if effects is not None and hasattr(effects,'release_resources'):
            for cleanup in effects.release_resources():
                owner.adapter_cleanup.append(cleanup)
                if cleanup['observed_descriptors'] or cleanup['remaining_descriptors'] or cleanup['errors']:
                    raise IntegrityError('consumer_publication_unclosed_ledger_resources')
    finally:
        try:
            for session in getattr(owner,'personal_exclusive_sessions',[]):session.release()
        finally:
            for session in getattr(owner,'pilot_temporary_sessions',[]):owner.adapter_cleanup.append(session.release())
