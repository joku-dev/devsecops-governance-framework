"""Diagnostic history projection over explicit IO and captured-evidence adapter."""
from contextlib import redirect_stdout,redirect_stderr
import io
from lib.pilot_projection_programs import PilotActionProgram,PilotValidationProgram
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.synthetic_lifecycle_context import LifecyclePaths
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

PROGRAMS={'actions':('generate_lifecycle_pilot_actions.py',PilotActionProgram),
          'validation':('generate_lifecycle_pilot_validation.py',PilotValidationProgram)}

def execute(source,cwd,program,argv,io_port,*,validator_class,provider_factory):
    if program not in PROGRAMS:raise InputAdmissionError('pilot_projection_program_not_supported')
    paths=LifecyclePaths(source,cwd,io_port);root=paths.path(source)
    context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path,provider_factory=provider_factory)
    kernel=PROGRAMS[program][1](root,context,path_factory=paths.path)
    # Both originals ignore sys.argv; preserving it as request data must not
    # invent new original help/parser behavior or parse it in this kernel.
    out,err=io.StringIO(),io.StringIO();error=signal=None
    with redirect_stdout(out),redirect_stderr(err):
        try:code=kernel.main()
        except (InputAdmissionError,IntegrityError):raise
        except RetainedOutputError as caught:code,error=1,{'type':caught.original_type,'message':caught.original_message}
        except SystemExit as caught:
            code=0 if caught.code is None else caught.code if type(caught.code) is int else 1
            if caught.code is not None and type(caught.code) is not int:print(caught.code,file=err)
            signal={'type':'SystemExit','value':caught.code}
        except Exception as caught:code,error=1,{'type':type(caught).__name__,'message':str(caught)}
    return {'exit_code':0 if code is None else code,'kernel_exception':error,'original_exit_signal':signal,
            'stdout':out.getvalue(),'stderr':err.getvalue()}
