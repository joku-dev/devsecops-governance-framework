"""Original action preparation over logical files and explicit sampled time."""
from contextlib import redirect_stdout,redirect_stderr
import io
from lib.personal_channel_context import PersonalPaths
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.pilot_action_preparation import PilotActionPreparation
from lib.retained_argparse import parser_base,formatter_factory
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

def execute(source,cwd,argv,io_port,*,validator_class,provider_factory,exclusive_factory,
            clock_factory,parser_context,prepare_arguments=None):
    if parser_context is None:raise InputAdmissionError('pilot_action_preparation_parser_context_required')
    paths=PersonalPaths(source,cwd,io_port,exclusive_factory);root=paths.path(source)
    context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path,provider_factory=provider_factory)
    def parser(**kw):return parser_base(parser_context)(prog='prepare_lifecycle_pilot_action.py',formatter_class=formatter_factory(parser_context),**kw)
    kernel=PilotActionPreparation(root,context,path_factory=paths.path,argument_parser=parser,argv=argv,clock=clock_factory(io_port))
    stdout,stderr=io.StringIO(),io.StringIO();error=signal=returned=None;code=0
    try:
        with redirect_stdout(stdout),redirect_stderr(stderr):
            try:
                if prepare_arguments is None:kernel.main()
                else:returned=kernel.prepare(**prepare_arguments)
            except (InputAdmissionError,IntegrityError):raise
            except RetainedOutputError as caught:code,error=1,{'type':caught.original_type,'message':caught.original_message}
            except SystemExit as caught:
                code=0 if caught.code is None else caught.code if type(caught.code) is int else 1
                if caught.code is not None and type(caught.code) is not int:print(caught.code,file=stderr)
                signal={'type':'SystemExit','value':caught.code}
            except Exception as caught:code,error=1,{'type':type(caught).__name__,'message':str(caught)}
    finally:
        for session in getattr(io_port,'personal_exclusive_sessions',[]):session.release()
    if len(stdout.getvalue())>131072 or len(stderr.getvalue())>131072 or error and len(error['message'])>65536:
        raise InputAdmissionError('pilot_action_preparation_original_stream_budget')
    return {'exit_code':code,'kernel_exception':error,'original_exit_signal':signal,'return_value':returned,
            'stdout':stdout.getvalue(),'stderr':stderr.getvalue()}
