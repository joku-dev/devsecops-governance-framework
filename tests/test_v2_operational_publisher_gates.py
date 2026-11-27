"""Real whole lifecycle gates vs immutable V1, including native capture and inert replay.

The inherited eight scenarios use no gate doubles. They cover active/inactive
acceptance, withdrawal, fresh receipts/actions/captures and historical failure.
Publisher mutation/POST orchestration is a separate isolated native suite.
"""
from contextlib import redirect_stdout,redirect_stderr
import io,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'scripts')]
import test_v2_publication_validation_execution as original_gates
from lib.operational_publication_gate_ports import gates,release
from lib.personal_channel_context import OrderedStderr
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

def execute_gates(source,cwd,argv,owner,*,validator_class,parser_context,provider_executable,temporary_parent,publication_base_ref):
    assert argv==[] and publication_base_ref is not None
    out,err=io.StringIO(),OrderedStderr();code=0;error=signal=returned=None
    actual=gates(source,cwd,owner,validator_class=validator_class,provider_executable=provider_executable,
        temporary_parent=temporary_parent,emit_stderr=err.emit_raw)
    try:
        with redirect_stdout(out),redirect_stderr(err):
            try:returned=actual.validate_publication(source,publication_base_ref)
            except (InputAdmissionError,IntegrityError):raise
            except RetainedOutputError as caught:code,error=1,{'type':caught.original_type,'message':caught.original_message}
            except SystemExit as caught:
                code=0 if caught.code is None else caught.code if type(caught.code) is int else 1
                if caught.code is not None and type(caught.code) is not int:print(caught.code,file=err)
                signal={'type':'SystemExit','value':caught.code}
            except Exception as caught:code,error=1,{'type':type(caught).__name__,'message':str(caught)}
    finally:release(owner)
    return {'exit_code':code,'kernel_exception':error,'original_exit_signal':signal,'return_value':returned,
        'stdout':out.getvalue(),'stderr':err.getvalue(),'stderr_parts':err.parts}

class WholeOperationalPublisherRealGates(original_gates.WholePublicationValidationExecution):
    def compare(self,*args,**kwargs):
        with patch.object(original_gates,'execute',execute_gates):return super().compare(*args,**kwargs)
