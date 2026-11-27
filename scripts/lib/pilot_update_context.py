"""Original pilot runner, captured operating writes and shared two-ledger store."""
from contextlib import redirect_stdout,redirect_stderr
from copy import deepcopy
import io
from lib.lifecycle_preflight_context import PreflightPaths
from lib.personal_channel_context import OrderedStderr
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.synthetic_ledger_store import SyntheticLedgerStore
from lib.operating_verification import OperatingVerification
from lib.operating_capture import OperatingCapture
from lib.pilot_run_intake import PilotRunIntake
from lib.pilot_action_intake import PilotActionIntake
from lib.pilot_projection_programs import PilotValidationProgram,PilotActionProgram
from lib.pilot_update_program import PilotUpdateProgram
from lib.retained_argparse import parser_base,formatter_factory
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

def execute(source,cwd,argv,owner,*,validator_class,parser_context,description,ports_factory,
            provider_factory,fresh_factory,effects_factory,exclusive_factory,temporary_factory,
            clock_factory,invocation=None):
    if parser_context is None:raise InputAdmissionError('pilot_update_parser_context_required')
    out,err=io.StringIO(),OrderedStderr();paths=PreflightPaths(source,cwd,owner,exclusive_factory);root=paths.path(source)
    context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path);ports=ports_factory(owner,root,err.emit_raw)
    context.provider=provider_factory(context,ports['personal']);fresh=fresh_factory(context,ports['preflight'])
    effects=effects_factory(owner,source=source,transaction_name=lambda raw:context.kernel.transaction_name(context.adapter.strict_json(raw)))
    context.store=SyntheticLedgerStore(context,path_factory=paths.path,native=effects,locking=effects,temporary=effects)
    temporary=temporary_factory(owner);clock=clock_factory(owner)
    def parser(**kw):return parser_base(parser_context)(prog='run_lifecycle_pilot_update.py',formatter_class=formatter_factory(parser_context),**kw)
    collector=OperatingVerification(root,context,path_factory=paths.path,git=ports['personal'])
    operating=OperatingCapture(root,context,path_factory=paths.path,collector=collector)
    receipts=PilotRunIntake(root,context,fresh,path_factory=paths.path,temporary=temporary,argument_parser=parser,argv=[],clock=clock)
    actions=PilotActionIntake(root,context,path_factory=paths.path,argument_parser=parser,argv=[],clock=clock)
    reports={'receipt_reports':PilotValidationProgram(root,context,path_factory=paths.path),'action_reports':PilotActionProgram(root,context,path_factory=paths.path)}
    program=PilotUpdateProgram(root,context,path_factory=paths.path,operating=operating,receipts=receipts,actions=actions,fresh=fresh,temporary=temporary,git=ports['personal'],clock=clock,capture_method=context.provider.capture_method,argument_parser=parser,argv=list(argv),description=description,**reports)
    code=0;error=signal=returned=None
    try:
        with redirect_stdout(out),redirect_stderr(err):
            try:
                if invocation is None:program.main()
                elif invocation['method']=='run':returned=program.run(**invocation['arguments'])
                elif invocation['method'] in ('capture','generate'):returned=getattr(operating,invocation['method'])()
                else:raise InputAdmissionError('pilot_update_original_API_required')
            except (InputAdmissionError,IntegrityError):raise
            except RetainedOutputError as caught:code,error=1,{'type':caught.original_type,'message':caught.original_message}
            except SystemExit as caught:
                code=0 if caught.code is None else caught.code if type(caught.code) is int else 1
                if caught.code is not None and type(caught.code) is not int:print(caught.code,file=err)
                signal={'type':'SystemExit','value':caught.code}
            except Exception as caught:code,error=1,{'type':type(caught).__name__,'message':str(caught)}
    finally:
        observations=deepcopy({name:part.state.observed for name,part in effects.parts.items()}) if owner.mode=='selected-files' else {}
        descriptors=deepcopy(effects.descriptors)
        owner.adapter_cleanup=[]
        if hasattr(effects,'release_resources'):
            for cleanup in effects.release_resources():
                owner.adapter_cleanup.append(cleanup)
                if cleanup['observed_descriptors'] or cleanup['remaining_descriptors'] or cleanup['errors']:
                    if hasattr(owner,'record'):owner.record.capture_incomplete=True
                    else:raise IntegrityError('pilot_update_unclosed_ledger_resources')
        for session in getattr(owner,'personal_exclusive_sessions',[]):session.release()
        for session in getattr(owner,'pilot_temporary_sessions',[]):owner.adapter_cleanup.append(session.release())
    if len(out.getvalue())>131072 or len(err.getvalue())>131072 or error and len(error['message'])>65536:raise InputAdmissionError('pilot_update_original_text_budget')
    return {'exit_code':code,'kernel_exception':error,'original_exit_signal':signal,'return_value':returned,'stdout':out.getvalue(),'stderr':err.getvalue(),'stderr_parts':err.parts,
        'native_ledger_observations':observations,'kernel_end_ledger_descriptors':descriptors}
