"""Explicit native self-security writer or inert whole-program replay."""
import posixpath
from lib.self_security_publication_context import execute as execute_kernel
from lib.self_security_publication_io import WorktreeEpochs,EpochPublisherProcess,ReplaySelfSecurityIO
from lib.providers.self_security_publication_io import NativeSelfSecurityIO,NativeWorktreeSnapshots
from lib.providers.self_security_publication_profile import LegacySelfSecurityPublicationProfile
from lib.providers.self_security_publication_protocol import LegacySelfSecurityPublicationProtocol
from lib.providers.self_security_publication_process import NativeSelfSecurityPublicationProcess
from lib.providers.self_security_publication_api import LegacySelfSecurityPublicationAPI
from lib.providers.operational_publication_record import RecordingPublisherProcess
from lib.operational_publication_process import ReplayPublisherProcess
from lib.providers.operational_publication_paths import NativePublisherPaths
from lib.operational_publication_paths import ReplayPublisherPaths


def execute(request,owner,*,native_environment=None):
    native=hasattr(owner,'record');source,cwd=request['source_label'],request['cwd_label'];subject=request['subject'];profile=LegacySelfSecurityPublicationProfile();origin=request['local_origin_root'];protocol=LegacySelfSecurityPublicationProtocol(source,**subject,cwd=cwd,local_origin_root=origin,private_state_label=request['private_state_label']);outputs=set(output_paths(request['environment'],cwd))
    def process(io):
        if native:
            snapshots=NativeWorktreeSnapshots(io,source);epochs=WorktreeEpochs(io,source,snapshots,snapshots.blob)
            def writer():
                value=NativeSelfSecurityPublicationProcess(source,**subject,profile=profile,environment=native_environment,provider_executable=request['provider_executable'],local_origin_root=origin);value.cwd=cwd;value.forbidden_program_roots=(str(io.private_state),);return value
            original=RecordingPublisherProcess(io,protocol,writer)
        else:epochs=WorktreeEpochs(io,source);original=ReplayPublisherProcess(io,protocol)
        return EpochPublisherProcess(original,epochs),epochs
    return execute_kernel(source,cwd,owner,invocation=request['invocation'],subject=subject,environment=request['environment'],process_factory=process,
        publication_paths_factory=lambda io:(NativePublisherPaths if native else ReplayPublisherPaths)(io,source=source,outputs=outputs),api_factory=lambda process:LegacySelfSecurityPublicationAPI(process,profile),profile=profile)


def public_environment(options):
    p=LegacySelfSecurityPublicationProfile();value={p.repository_key:options['repository'],p.run_id_key:options['run_id'],p.attempt_key:options['attempt']}
    if options.get('workflow_ref') is not None:value[p.ref_key]=options['workflow_ref']
    for option,key in (('output_file',p.output_key),('summary_file',p.summary_key)):
        if options.get(option):value[key]=options[option]
    return value


def environment_valid(value,subject):
    p=LegacySelfSecurityPublicationProfile();keys={p.repository_key,p.run_id_key,p.attempt_key,p.ref_key,p.output_key,p.summary_key}
    if type(value) is not dict or not set(value)<=keys or any(type(v) is not str or len(v)>8192 or '\0' in v for v in value.values()):raise ValueError('self_security_environment_changed')
    for key,field in ((p.repository_key,'repository'),(p.run_id_key,'run_id'),(p.attempt_key,'attempt')):
        if key in value and value[key]!=subject[field]:raise ValueError('self_security_environment_subject_changed')
    return value


def output_paths(environment,cwd):
    p=LegacySelfSecurityPublicationProfile()
    return [posixpath.normpath(value if value.startswith('/') else cwd+'/'+value) for key in (p.output_key,p.summary_key) if (value:=environment.get(key))]

from lib.lifecycle_ledger_validation_ports import (Record,read_record,encode,AUTHORITY,owned_directory,current_source,ROOT,ledger,transaction_name)
NativeIO=NativeSelfSecurityIO

DEFAULT_PROVIDER_EXECUTABLE='gh'
