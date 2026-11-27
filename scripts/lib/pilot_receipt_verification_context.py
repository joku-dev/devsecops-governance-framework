"""Whole original verification API; provider/Git, clocks and temporaries are explicit."""
from contextlib import redirect_stdout,redirect_stderr
import io
from lib.lifecycle_preflight_context import PreflightPaths
from lib.personal_channel_context import OrderedStderr
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.pilot_receipt_verification import PilotReceiptVerification
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

def execute(source,cwd,base_ref,owner,*,validator_class,historical_provider_factory,
            fresh_provider_factory,transport_factory,exclusive_factory,temporary_factory):
    out,err=io.StringIO(),OrderedStderr();paths=PreflightPaths(source,cwd,owner,exclusive_factory)
    root=paths.path(source);context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path,provider_factory=historical_provider_factory)
    transport=transport_factory(owner,root,err.emit_raw);fresh=fresh_provider_factory(context,transport)
    program=PilotReceiptVerification(context,fresh,path_factory=paths.path,temporary=temporary_factory(owner),clock=transport.clock,git=transport)
    code=0;error=signal=returned=None
    try:
        with redirect_stdout(out),redirect_stderr(err):
            try:returned=program.verify_new_receipts(source,base_ref)
            except (InputAdmissionError,IntegrityError):raise
            except RetainedOutputError as caught:code,error=1,{'type':caught.original_type,'message':caught.original_message}
            except SystemExit as caught:
                code=0 if caught.code is None else caught.code if type(caught.code) is int else 1
                if caught.code is not None and type(caught.code) is not int:print(caught.code,file=err)
                signal={'type':'SystemExit','value':caught.code}
            except Exception as caught:code,error=1,{'type':type(caught).__name__,'message':str(caught)}
    finally:
        owner.adapter_cleanup=[]
        for session in getattr(owner,'personal_exclusive_sessions',[]):session.release()
        for session in getattr(owner,'pilot_temporary_sessions',[]):owner.adapter_cleanup.append(session.release())
    if len(out.getvalue())>131072 or len(err.getvalue())>131072 or error and len(error['message'])>65536:
        raise InputAdmissionError('pilot_receipt_verification_original_text_capture_budget')
    return {'exit_code':code,'kernel_exception':error,'original_exit_signal':signal,'return_value':returned,
        'stdout':out.getvalue(),'stderr':err.getvalue(),'stderr_parts':err.parts}
