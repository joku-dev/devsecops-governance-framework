"""Explicit provider observation composition and whole technical record binding."""
from copy import deepcopy
from lib.provider_observation_context import execute as execute_kernel
from lib.provider_observation_backend import ReplayObservationBackend
from lib.providers.provider_observation_backend import NativeObservationBackend
from lib.provider_observation_reads import reader_type
from lib.providers.transports import Reader,BoundedAudit
from lib.providers.provider_observation_assurance import LegacyProviderAssurance
from lib.providers.provider_observation_legacy import PrivateSecurityModules
from lib.providers.self_security_capture import SecurityCollector
from lib.self_security import observed_values
from lib.providers.provider_observation_git import NativeObservationGit
from lib.provider_observation_git import ReplayObservationGit
from lib.providers.provider_observation_release import NativeObservationRelease
from lib.provider_observation_release import ReplayObservationRelease
from lib.providers.consumer_lifecycle_storage import Record,read_record,encode
from lib.providers.sbom_export_storage import owned_directory,AUTHORITY
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.synthetic_lifecycle_io import ReplayIO
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.providers.retained_argparse import capture_context as capture_parser_context
from lib.portable.contracts import ROOT
from lib.v2_source import selected_paths
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError

COMPONENTS=('provider_observation.py','provider_observation_application.py','provider_observation_ports.py',
 'provider_observation_context.py','provider_observation_backend.py','provider_observation_reads.py',
 'provider_observation_private.py','provider_observation_private_ports.py','provider_observation_credentials.py',
 'provider_observation_profile.py','provider_observation_git.py','provider_observation_release.py',
 'providers/provider_observation_assurance.py','providers/provider_observation_legacy.py',
 'providers/provider_observation_backend.py','providers/provider_observation_reads.py',
 'providers/provider_observation_private_ports.py','providers/provider_observation_credentials.py',
 'providers/provider_observation_profile.py','providers/provider_observation_git.py','providers/provider_observation_release.py')


def current_source(node,product_tree=None):
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):
        raise ValueError('provider_observation_closure_not_registered')
    return lifecycle_source(node,product_tree)


def released_resources(backend):
    simple={'required':False,'outside_original_cleanup':'no_extra_cleanup'}
    return {'credential':deepcopy(simple) if backend.roles_bound else None,
        'profile':deepcopy(simple) if backend.roles_bound else None,
        'private_metadata':{'required':False,'outside_original_cleanup':[]} if backend.roles_bound else None,
        'atomic':{'required':False,'unclosed_descriptors':[],'errors':[]} if backend.atomic is not None else None}


def execute(request,owner,node,*,clock=None):
    native=hasattr(owner,'record');source=request['source_label'];protected=(request['private_state_label'],source)
    backend=NativeObservationBackend(owner,protected_roots=protected,clock=clock) if native else ReplayObservationBackend(owner,protected_roots=protected,reader_url=Reader.url)
    child_node={k:node[k] for k in ('node_id','runtime_source_digest')}
    def factory(root,backend,emit_stderr):
        git=(NativeObservationGit if native else ReplayObservationGit)(owner,root,emit_stderr=emit_stderr)
        if native:child=NativeObservationRelease(owner,root,instance_root=owner.private_state/'state/provider-observation/release-children'/owner.record.root.name,node_context=child_node)
        else:child=ReplayObservationRelease(owner,root,node_context=child_node)
        def collector(get,at):return SecurityCollector(root,get,lambda:child.report(backend.revision,at),path_factory=lambda value:value)
        loader=PrivateSecurityModules(root,collector_factory=None,timed_collector_factory=collector,observed_values=observed_values)
        return LegacyProviderAssurance(root,process=git,loader=loader)
    try:
        kernel=execute_kernel(source,request['cwd_label'],request['argv'],owner,backend=backend,
            reader_type=reader_type(backend.reads,Reader),audit_type=BoundedAudit,assurance_factory=factory,parser_context=request['parser_context'])
    finally:
        # Revocation/descriptor cleanup remains mandatory after capture failure;
        # losing a journal intent never prevents in-memory credential teardown.
        if native:
            try:cleanup=backend.release_resources()
            except Exception:
                owner.record.capture_incomplete=True
                raise InputAdmissionError('provider_observation_resource_cleanup_incomplete') from None
    expected=released_resources(backend)
    if native:
        if cleanup!=expected or owner.record.capture_incomplete:
            owner.record.capture_incomplete=True;raise InputAdmissionError('provider_observation_extra_cleanup_or_capture_incomplete')
        owner.append({'kind':'provider-observation-resources-released','result':cleanup})
    else:
        if encode(owner.row())!=encode({'kind':'provider-observation-resources-released','result':expected}):
            raise IntegrityError('provider_observation_resource_release_changed')
    kernel['atomic_output_snapshot']=None if backend.atomic is None else deepcopy(backend.atomic.state.current)
    kernel['native_extra_cleanup_required']=False
    if not native:backend.finish()
    return kernel
