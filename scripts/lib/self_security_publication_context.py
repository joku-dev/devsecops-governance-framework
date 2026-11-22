"""Whole original self-security publisher over one IO/process/transition cursor."""
from contextlib import redirect_stdout,redirect_stderr
import io
from lib.self_security_publication import SelfSecurityPublisher
from lib.operational_publication_paths import PublisherPaths
from lib.personal_channel_context import OrderedStderr
from lib.requirement_review_output import RetainedOutputError
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError


def execute(source,cwd,owner,*,invocation,subject,environment,process_factory,publication_paths_factory,api_factory,profile):
    if set(subject)!={'repository','run_id','attempt'}:raise InputAdmissionError('self_security_execution_subject_required')
    out,err=io.StringIO(),OrderedStderr();publication=publication_paths_factory(owner);paths=PublisherPaths(source,cwd,owner,publication);root=paths.path(source);process,epochs=process_factory(owner)
    kernel=SelfSecurityPublisher(root,path_factory=paths.path,process=process,api=api_factory(process),profile=profile,environment=environment);code=0;error=signal=returned=None
    with redirect_stdout(out),redirect_stderr(err):
        try:
            if invocation=='publish':returned=kernel.publish(root,**subject)
            elif invocation=='main':
                expected={profile.repository_key:subject['repository'],profile.run_id_key:subject['run_id'],profile.attempt_key:subject['attempt']}
                if any(k in environment and environment[k]!=v for k,v in expected.items()):raise InputAdmissionError('self_security_environment_subject_changed')
                returned=kernel.main()
            else:raise InputAdmissionError('self_security_invocation_not_supported')
        except (InputAdmissionError,IntegrityError):raise
        except RetainedOutputError as caught:code,error=1,{'type':caught.original_type,'message':caught.original_message}
        except SystemExit as caught:
            code=0 if caught.code is None else caught.code if type(caught.code) is int else 1
            if caught.code is not None and type(caught.code) is not int:print(caught.code,file=err)
            signal={'type':'SystemExit','value':caught.code}
        except Exception as caught:code,error=1,{'type':type(caught).__name__,'message':str(caught)}
    if len(out.getvalue())>131072 or len(err.getvalue())>131072 or error and len(error['message'])>65536:raise InputAdmissionError('self_security_original_text_budget')
    return {'exit_code':code,'kernel_exception':error,'original_exit_signal':signal,'return_value':returned,'stdout':out.getvalue(),'stderr':err.getvalue(),'stderr_parts':err.parts,'pipeline_append_observations':publication.appends,'native_process_operation_count':process.calls,'native_process_observations':process.observations,'known_source_worktree_transitions':epochs.observations,'external_completion_independently_proven':False,'effects_repeated_during_replay':False}
