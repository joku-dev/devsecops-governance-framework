"""Explicit consumer-only wiring; personal and evidence credentials stay separate."""
from lib.consumer_lifecycle_execution import execute as execute_kernel
from lib.providers.consumer_lifecycle_profile import LegacyConsumerProfile
from lib.providers.consumer_lifecycle_evidence import LegacyConsumerEvidence
from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture
from lib.providers.consumer_lifecycle_transport import (NativeConsumerTransport, ReplayConsumerTransport,
    NativeConsumerCentralTransport, ReplayConsumerCentralTransport)
from lib.providers.consumer_lifecycle_opa import NativeConsumerOPA, LegacyConsumerOPAProfile
from lib.consumer_lifecycle_opa import ReplayConsumerOPA
from lib.providers.consumer_lifecycle_io import native_effects
from lib.consumer_lifecycle_io import replay_effects
from lib.providers.pilot_run_temporary import NativeTemporaryFactory
from lib.pilot_run_temporary import ReplayTemporaryFactory
from lib.pilot_run_private_temporary import PrivateTemporaryFactory
from lib.personal_channel_ports import exclusive_factory
from lib.requirement_validation_budget import InputAdmissionError

DESCRIPTION = 'Prepare, verify or operate the bounded consumer lifecycle through reviewed PRs.'


class DeferredEvidence:
    def __init__(self, factory):
        self.factory, self.port = factory, None
    def fetch(self, endpoint, *, raw=False):
        if self.port is None:
            self.port = self.factory()
        return self.port.fetch(endpoint, raw=raw)


class ConsumerProcesses:
    def __init__(self, central, policy_factory):
        self.central, self.policy_factory, self.policy = central, policy_factory, None
    def check_output(self, command, **options):
        return self.central.check_output(command, **options)
    def run(self, command, **options):
        if type(command) is list and command[:1] == ['opa']:
            if self.policy is None:
                self.policy = self.policy_factory()
            return self.policy.run(command, **options)
        return self.central.run(command, **options)
    def finish(self):
        if self.policy is not None and getattr(self.policy, 'resources', {}):
            raise InputAdmissionError('consumer_opa_materialization_resources_unclosed')


def execute(source, cwd, argv, owner, *, validator_class, parser_context, provider_executable,
            temporary_parent, opa_tool, approved_opa_hashes, opa_workarea, environment=None, invocation=None):
    native = hasattr(owner, 'record')
    def ports(io, root, context, emit):
        central = (NativeConsumerCentralTransport(io, root, emit_stderr=emit, environment=environment, provider_executable=provider_executable)
                   if native else ReplayConsumerCentralTransport(io, root, emit_stderr=emit))
        def reader():
            profile = context.consumer_contracts.load_operating(root)
            return (NativeConsumerTransport(io, root, profile, emit_stderr=emit, environment=environment, provider_executable=provider_executable)
                    if native else ReplayConsumerTransport(io, root, profile, emit_stderr=emit))
        def policy():
            if native:
                return NativeConsumerOPA(io, root, tool=opa_tool, approved_hashes=approved_opa_hashes, workarea=opa_workarea)
            return ReplayConsumerOPA(io, root, profile=LegacyConsumerOPAProfile(), tool=str(opa_tool), approved_hashes=approved_opa_hashes, workarea=opa_workarea)
        return {'central': central, 'evidence': DeferredEvidence(reader), 'process': ConsumerProcesses(central, policy)}
    def temporary(io):
        cls = PrivateTemporaryFactory if io.mode == 'private-candidate' else NativeTemporaryFactory if native else ReplayTemporaryFactory
        return cls(io, temporary_parent)
    def evidence(root, context, profile, architecture, reader, process, temporary, clock, validator, path):
        return LegacyConsumerEvidence(root, context, path_factory=path, profile=profile, process=process,
            temporary=temporary, clock=clock, validator_class=validator, default_fetch=reader.fetch, architecture=architecture)
    return execute_kernel(source, cwd, argv, owner, validator_class=validator_class, parser_context=parser_context,
        description=DESCRIPTION, ports_factory=ports, profile_factory=lambda c, port: LegacyConsumerProfile(c, default_fetch=port.fetch),
        provider_factory=lambda c, port: LegacyPersonalChannelCapture(c, fetch=port.fetch, clock=port.clock),
        evidence_factory=evidence, effects_factory=native_effects if native else replay_effects,
        exclusive_factory=exclusive_factory, temporary_factory=temporary, invocation=invocation)
