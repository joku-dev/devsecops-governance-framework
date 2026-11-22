"""Whole fresh and saved-capture run intake over explicit ledger, GET, clock and temporary ports."""

from contextlib import redirect_stdout,redirect_stderr
from copy import deepcopy
import io
from lib.lifecycle_preflight_context import PreflightPaths
from lib.personal_channel_context import OrderedStderr
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.synthetic_ledger_store import SyntheticLedgerStore
from lib.pilot_run_intake import PilotRunIntake
from lib.retained_argparse import parser_base,formatter_factory
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

class MissingFreshPort:
    """Unbound execution is technical failure; original help needs no ports."""
    def __getattr__(self, name):
        raise InputAdmissionError("pilot_run_intake_fresh_ports_required")
    def __call__(self, *args, **kwargs):
        raise InputAdmissionError("pilot_run_intake_fresh_ports_required")

def explicit_port(value):
    return MissingFreshPort() if value is None else value


def execute(source,cwd,argv,owner,*,validator_class,historical_provider_factory,
            fresh_provider_factory,effects_factory,exclusive_factory,temporary_factory,
            parser_context,clock_factory,invocation=None):
    if parser_context is None:raise InputAdmissionError("pilot_run_intake_parser_context_required")
    out,err=io.StringIO(),OrderedStderr()
    paths=PreflightPaths(source,cwd,owner,exclusive_factory);root=paths.path(source)
    context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path,provider_factory=historical_provider_factory)
    effects=effects_factory(owner)
    context.store=SyntheticLedgerStore(context,path_factory=paths.path,native=effects,locking=effects,temporary=effects)
    def parser(**kw):return parser_base(parser_context)(prog='intake_lifecycle_pilot_run.py',formatter_class=formatter_factory(parser_context),**kw)
    kernel=PilotRunIntake(root,context,explicit_port(fresh_provider_factory(context,err.emit_raw)),path_factory=paths.path,
        temporary=explicit_port(temporary_factory(owner)),argument_parser=parser,argv=list(argv),clock=explicit_port(clock_factory(owner)))
    error=signal=None;returned=None;code=0
    try:
        with redirect_stdout(out),redirect_stderr(err):
            try:
                if invocation is None:kernel.main()
                elif invocation['method']=='append_capture':returned=kernel.append_capture(**invocation['arguments'])
                else:raise InputAdmissionError('pilot_run_intake_API_not_supported')
            except (InputAdmissionError,IntegrityError):raise
            except RetainedOutputError as caught:code,error=1,{'type':caught.original_type,'message':caught.original_message}
            except SystemExit as caught:
                code=0 if caught.code is None else caught.code if type(caught.code) is int else 1
                if caught.code is not None and type(caught.code) is not int:print(caught.code,file=err)
                signal={'type':'SystemExit','value':caught.code}
            except Exception as caught:code,error=1,{'type':type(caught).__name__,'message':str(caught)}
    finally:
        observed=deepcopy(effects.state.observed) if hasattr(effects,'state') else {}
        descriptors=deepcopy(effects.descriptors)
        owner.adapter_cleanup=[]
        if hasattr(effects,'release_resources'):
            cleanup=effects.release_resources();owner.adapter_cleanup.append(cleanup)
            if cleanup['observed_descriptors'] or cleanup['remaining_descriptors'] or cleanup['errors']:
                if hasattr(owner,'record'):owner.record.capture_incomplete=True
                else:raise IntegrityError('pilot_run_intake_unclosed_resources')
        for session in getattr(owner,'personal_exclusive_sessions',[]):session.release()
        for session in getattr(owner,'pilot_temporary_sessions',[]):owner.adapter_cleanup.append(session.release())
    if len(out.getvalue())>131072 or len(err.getvalue())>131072 or error and len(error['message'])>65536:
        raise InputAdmissionError('pilot_run_intake_original_text_capture_budget')
    return {'exit_code':code,'kernel_exception':error,'original_exit_signal':signal,'return_value':returned,'stdout':out.getvalue(),'stderr':err.getvalue(),'stderr_parts':err.parts,'native_receipt_observations':observed,'kernel_end_ledger_descriptors':descriptors}
