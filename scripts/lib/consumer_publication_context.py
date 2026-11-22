"""Entire publisher over captured process, selection, append and real gate ports."""
from contextlib import redirect_stdout,redirect_stderr
import io,posixpath
from lib.consumer_publication import ConsumerPublisher
from lib.operational_publication_paths import PublisherPaths
from lib.personal_channel_context import OrderedStderr
from lib.retained_argparse import parser_base,formatter_factory
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

def execute(source,cwd,owner,*,invocation,subject,argv,environment,parser_context,process_factory,
            publication_paths_factory,gates_factory,api_factory,profile,release):
    if set(subject)!={'scope','repository','run_id','attempt'}:raise InputAdmissionError('publisher_execution_subject_required')
    out,err=io.StringIO(),OrderedStderr();publication_paths=publication_paths_factory(owner)
    paths=PublisherPaths(source,cwd,owner,publication_paths);root=paths.path(source)
    process=process_factory(owner);gates=gates_factory(owner,err.emit_raw)
    parent=parser_base(parser_context)
    class Parser(parent):
        def parse_args(self,*args,**kw):
            result=super().parse_args(*args,**kw)
            if result.scope!=subject['scope']:raise InputAdmissionError('publisher_operator_scope_binding_changed')
            return result
    def parser(**kw):return Parser(prog='publish_consumer_lifecycle.py',formatter_class=formatter_factory(parser_context),**kw)
    kernel=ConsumerPublisher(root,path_factory=paths.path,process=process,api=api_factory(process),gates=gates,
        profile=profile,environment=environment,argument_parser=parser,argv=list(argv))
    code=0;error=signal=returned=None
    try:
        with redirect_stdout(out),redirect_stderr(err):
            try:
                if invocation=='publish':returned=kernel.publish(root,**subject)
                elif invocation=='main':
                    expected={profile.repository_key:subject['repository'],profile.run_id_key:subject['run_id'],profile.attempt_key:subject['attempt']}
                    if any(k in environment and environment[k]!=v for k,v in expected.items()):raise InputAdmissionError('publisher_operator_environment_binding_changed')
                    returned=kernel.main()
                else:raise InputAdmissionError('publisher_invocation_not_supported')
            except (InputAdmissionError,IntegrityError):raise
            except RetainedOutputError as caught:code,error=1,{'type':caught.original_type,'message':caught.original_message}
            except SystemExit as caught:
                code=0 if caught.code is None else caught.code if type(caught.code) is int else 1
                if caught.code is not None and type(caught.code) is not int:print(caught.code,file=err)
                signal={'type':'SystemExit','value':caught.code}
            except Exception as caught:code,error=1,{'type':type(caught).__name__,'message':str(caught)}
    finally:release(owner)
    if len(out.getvalue())>131072 or len(err.getvalue())>131072 or error and len(error['message'])>65536:raise InputAdmissionError('publisher_original_text_budget')
    return {'exit_code':code,'kernel_exception':error,'original_exit_signal':signal,'return_value':returned,
        'stdout':out.getvalue(),'stderr':err.getvalue(),'stderr_parts':err.parts,'pipeline_append_observations':publication_paths.appends,
        'native_process_operation_count':process.calls,'native_process_observations':process.observations,'external_completion_independently_proven':False,'effects_repeated_during_replay':False}
