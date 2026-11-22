"""Explicit native writer or source-free replay, with complete lifecycle gates."""
import posixpath
from lib.consumer_publication_context import execute as execute_kernel
from lib.operational_publication_process import ReplayPublisherProcess
from lib.operational_publication_paths import ReplayPublisherPaths
from lib.providers.consumer_publication_gates import gates,release
from lib.providers.consumer_publication_profile import LegacyConsumerPublicationProfile
from lib.providers.operational_publication_api import LegacyOperationalPublicationAPI
from lib.providers.consumer_publication_process import NativeConsumerPublicationProcess
from lib.providers.consumer_publication_protocol import LegacyConsumerPublisherProtocol
from lib.providers.operational_publication_record import RecordingPublisherProcess
from lib.providers.operational_publication_paths import NativePublisherPaths

def execute(request,owner,*,validator_class,native_environment=None,local_origin_root=None):
    from lib.requirement_validation_budget import InputAdmissionError
    selected_origin=request.get('local_origin_root')
    if local_origin_root is not None and str(local_origin_root)!=selected_origin:raise InputAdmissionError('publisher_local_test_profile_binding_changed')
    local_origin_root=selected_origin
    source,cwd=request['source_label'],request['cwd_label'];native=hasattr(owner,'record');subject=request['subject'];profile=LegacyConsumerPublicationProfile()
    protocol=LegacyConsumerPublisherProtocol(source,**subject,cwd=cwd,local_origin_root=None if local_origin_root is None else str(local_origin_root),private_state_label=request.get('private_state_label'))
    # Only these declared output paths can be opened by the publisher core.
    outputs={posixpath.normpath(v if v.startswith('/') else cwd+'/'+v) for key in (profile.output_key,profile.summary_key) if (v:=request['environment'].get(key))}
    def process(io):
        if not native:return ReplayPublisherProcess(io,protocol)
        def writer():
            value=NativeConsumerPublicationProcess(source,**subject,profile=profile,environment=native_environment,provider_executable=request['provider_executable'],local_origin_root=local_origin_root)
            value.cwd=cwd;value.forbidden_program_roots=(str(io.private_state),)
            return value
        return RecordingPublisherProcess(io,protocol,writer)
    return execute_kernel(source,cwd,owner,invocation=request['invocation'],subject=subject,argv=request['argv'],
        environment=request['environment'],parser_context=request['parser_context'],
        process_factory=process,publication_paths_factory=lambda io:(NativePublisherPaths if native else ReplayPublisherPaths)(io,source=source,outputs=outputs),
        gates_factory=lambda io,emit:gates(source,cwd,io,validator_class=validator_class,provider_executable=request['provider_executable'],temporary_parent=request['temporary_parent'],emit_stderr=emit,environment=native_environment,opa_tool=request['opa_tool'],approved_opa_hashes=frozenset(request['approved_opa_hashes']),opa_workarea=request['opa_workarea']),
        api_factory=lambda process:LegacyOperationalPublicationAPI(process,profile),profile=profile,release=release)

# Environment values below are declared execution inputs, not proof that a
# workflow was protected or that the caller has operating authority.
def public_environment(options):
    p=LegacyConsumerPublicationProfile()
    value={p.repository_key:options['repository'],p.run_id_key:options['run_id'],p.attempt_key:options['attempt']}
    if options.get('workflow_ref') is not None:value[p.ref_key]=options['workflow_ref']
    for option,key in (('output_file',p.output_key),('summary_file',p.summary_key)):
        if options.get(option):value[key]=options[option]
    return value

def environment_valid(environment,subject):
    p=LegacyConsumerPublicationProfile();keys={p.repository_key,p.run_id_key,p.attempt_key,p.ref_key,p.output_key,p.summary_key}
    if type(environment) is not dict or not set(environment)<=keys or any(type(v) is not str or len(v)>8192 or '\0' in v for v in environment.values()):raise ValueError('publisher_public_environment_changed')
    for key,field in ((p.repository_key,'repository'),(p.run_id_key,'run_id'),(p.attempt_key,'attempt')):
        if key in environment and environment[key]!=subject[field]:raise ValueError('publisher_public_environment_subject_changed')
    return environment

from lib.consumer_lifecycle_ports import (NativeIO,Record,read_record,encode,AUTHORITY,owned_directory,current_source,ROOT,
    transaction_name,temporary_parent,capture_parser_context,DEFAULT_PROVIDER_EXECUTABLE)
from lib.consumer_lifecycle_io import ReplayConsumerIO
from lib.operational_publication_process import EFFECT

def outputs(environment,cwd):
    p=LegacyConsumerPublicationProfile()
    return [posixpath.normpath(value if value.startswith('/') else cwd+'/'+value) for key in (p.output_key,p.summary_key) if (value:=environment.get(key))]
