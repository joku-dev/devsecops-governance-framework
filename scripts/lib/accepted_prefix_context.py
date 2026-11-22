"""Entire original accepted-prefix helper with captured Git and path ports."""
from contextlib import redirect_stdout,redirect_stderr
import io
from lib.synthetic_lifecycle_context import LifecyclePaths
from lib.personal_channel_context import OrderedStderr
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.accepted_prefix import AcceptedPrefix
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

def execute(source,cwd,base_ref,owner,*,validator_class,transport_factory,paths_factory):
    out,err=io.StringIO(),OrderedStderr()
    # Context constants are pure; all actual probes use the explicit prefix port.
    paths=LifecyclePaths(source,cwd,owner);root=paths.path(source)
    context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path)
    paths=LifecyclePaths(source,cwd,paths_factory(owner,root,context));root=paths.path(source)
    context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path)
    port=transport_factory(owner,root,context,err.emit_raw);program=AcceptedPrefix(context,path_factory=paths.path,transport=port)
    code=0;error=signal=returned=None
    with redirect_stdout(out),redirect_stderr(err):
        try:returned=program.check_accepted_prefix(source,base_ref)
        except (InputAdmissionError,IntegrityError):raise
        except RetainedOutputError as caught:code,error=1,{'type':caught.original_type,'message':caught.original_message}
        except SystemExit as caught:
            code=0 if caught.code is None else caught.code if type(caught.code) is int else 1
            if caught.code is not None and type(caught.code) is not int:print(caught.code,file=err)
            signal={'type':'SystemExit','value':caught.code}
        except Exception as caught:code,error=1,{'type':type(caught).__name__,'message':str(caught)}
    if len(out.getvalue())>131072 or len(err.getvalue())>131072 or error and len(error['message'])>65536:raise InputAdmissionError('accepted_prefix_text_capture_budget')
    return {'exit_code':code,'kernel_exception':error,'original_exit_signal':signal,'return_value':returned,
        'stdout':out.getvalue(),'stderr':err.getvalue(),'stderr_parts':err.parts}
