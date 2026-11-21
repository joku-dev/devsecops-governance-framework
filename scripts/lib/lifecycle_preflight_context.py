"""Entire preflight capture/replay over explicit observed paths, GETs and clock."""
from contextlib import redirect_stdout,redirect_stderr
from copy import deepcopy
from pathlib import PurePosixPath
import io
from lib.personal_channel_context import PersonalPaths,PersonalPath,OrderedStderr
from lib.synthetic_lifecycle_context import LifecyclePath
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.lifecycle_preflight_program import LifecyclePreflightProgram
from lib.retained_argparse import parser_base,formatter_factory
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

class PreflightPaths(PersonalPaths):
    def path(self,value):
        if isinstance(value,LifecyclePath):value=super().path(value).value
        return PreflightPath(self,PurePosixPath(value))
class PreflightPath(PersonalPath):
    def rglob(self,pattern):
        if pattern!='*':raise InputAdmissionError('preflight_original_rglob_required')
        count=0
        def walk(directory,depth):
            nonlocal count
            if depth>100:raise InputAdmissionError('preflight_directory_depth_budget')
            if not directory.is_dir():return
            children=list(directory.iterdir());count+=len(children)
            if count>10000:raise InputAdmissionError('preflight_directory_entry_budget')
            yield from children
            for path in children:
                if path.is_dir():yield from walk(path,depth+1)
        yield from walk(self,0)

def execute(source,cwd,argv,owner,*,validator_class,transport_factory,provider_factory,
            exclusive_factory,parser_context,invocation=None):
    if parser_context is None:raise InputAdmissionError('preflight_parser_context_required')
    paths=PreflightPaths(source,cwd,owner,exclusive_factory);root=paths.path(source)
    out,err=io.StringIO(),OrderedStderr();transport=transport_factory(owner,root,err.emit_raw)
    context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path,
        provider_factory=lambda context:provider_factory(context,transport))
    def parser(**kw):return parser_base(parser_context)(prog='preflight_lifecycle_live_evidence.py',formatter_class=formatter_factory(parser_context),**kw)
    kernel=LifecyclePreflightProgram(context.provider,argument_parser=parser,argv=list(argv))
    error=signal=None;returned=None;code=0
    try:
        with redirect_stdout(out),redirect_stderr(err):
            try:
                if invocation is None:kernel.main()
                elif invocation['method']=='collect_preflight':returned=context.provider.collect_preflight(**invocation['arguments'])
                elif invocation['method']=='replay_capture':returned=context.provider.replay_capture(**invocation['arguments'])
                else:raise InputAdmissionError('preflight_API_not_supported')
            except (InputAdmissionError,IntegrityError):raise
            except RetainedOutputError as caught:code,error=1,{'type':caught.original_type,'message':caught.original_message}
            except SystemExit as caught:
                code=0 if caught.code is None else caught.code if type(caught.code) is int else 1
                if caught.code is not None and type(caught.code) is not int:print(caught.code,file=err)
                signal={'type':'SystemExit','value':caught.code}
            except Exception as caught:code,error=1,{'type':type(caught).__name__,'message':str(caught)}
    finally:
        for session in getattr(owner,'personal_exclusive_sessions',[]):session.release()
    if len(out.getvalue())>131072 or len(err.getvalue())>131072 or error and len(error['message'])>65536:
        raise InputAdmissionError('preflight_original_text_capture_budget')
    return {'exit_code':code,'kernel_exception':error,'original_exit_signal':signal,'return_value':returned,
            'stdout':out.getvalue(),'stderr':err.getvalue(),'stderr_parts':err.parts,'external_native_path_observations':deepcopy(getattr(owner,'preflight_external_changes',{}))}
