"""Original fresh GET/recorded-clock phases and exact atomic store over explicit ports."""
from contextlib import redirect_stdout,redirect_stderr
import io
from copy import deepcopy
from lib.synthetic_lifecycle_context import LifecyclePaths
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.synthetic_ledger_store import SyntheticLedgerStore
from lib.personal_channel_context import OrderedStderr
from lib.pilot_action_intake import PilotActionIntake
from lib.retained_argparse import parser_base,formatter_factory
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

def execute(source,cwd,argv,owner,*,validator_class,provider_factory,transport_factory,
            effects_factory,clock_factory,parser_context,invocation=None):
    if parser_context is None:raise InputAdmissionError('pilot_action_intake_parser_context_required')
    paths=LifecyclePaths(source,cwd,owner);root=paths.path(source)
    context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path)
    effects=effects_factory(owner,source=source,transaction_name=lambda raw:context.kernel.transaction_name(context.adapter.strict_json(raw)))
    context.store=SyntheticLedgerStore(context,path_factory=paths.path,native=effects,locking=effects,temporary=effects)
    out,err=io.StringIO(),OrderedStderr();transport=transport_factory(owner,root,err.emit_raw);context.provider=provider_factory(context,transport)
    def parser(**kw):return parser_base(parser_context)(prog='intake_lifecycle_pilot_action.py',formatter_class=formatter_factory(parser_context),**kw)
    kernel=PilotActionIntake(root,context,path_factory=paths.path,argument_parser=parser,argv=list(argv),clock=clock_factory(owner))
    error=signal=None;returned=None;code=0
    try:
        with redirect_stdout(out),redirect_stderr(err):
            try:
                if invocation is None:kernel.main()
                elif invocation['method']=='collect_action':returned=kernel.collect_action(**invocation['arguments'])
                elif invocation['method']=='append_action_snapshot':returned=kernel.append_action_snapshot(**invocation['arguments'])
                else:raise InputAdmissionError('pilot_action_intake_API_not_supported')
            except (InputAdmissionError,IntegrityError):raise
            except RetainedOutputError as caught:code,error=1,{'type':caught.original_type,'message':caught.original_message}
            except SystemExit as caught:
                code=0 if caught.code is None else caught.code if type(caught.code) is int else 1
                if caught.code is not None and type(caught.code) is not int:print(caught.code,file=err)
                signal={'type':'SystemExit','value':caught.code}
            except Exception as caught:code,error=1,{'type':type(caught).__name__,'message':str(caught)}
    finally:
        native=owner.mode=='selected-files'
        observations=deepcopy({name:part.state.observed for name,part in effects.parts.items()}) if native else {}
        end_descriptors=deepcopy({name:part.state.descriptors for name,part in effects.parts.items()}) if native else {'private-projection':deepcopy(effects.descriptors)}
        owner.adapter_cleanup=[]
        if hasattr(effects,'release_resources'):
            for cleanup in effects.release_resources():
                owner.adapter_cleanup.append(cleanup)
                if cleanup['observed_descriptors'] or cleanup['remaining_descriptors'] or cleanup['errors']:
                    if hasattr(owner,'record'):owner.record.capture_incomplete=True
                    else:raise IntegrityError('pilot_action_intake_unclosed_resources')
    if len(out.getvalue())>131072 or len(err.getvalue())>131072 or error and len(error['message'])>65536:raise InputAdmissionError('pilot_action_intake_original_stream_budget')
    return {'exit_code':code,'kernel_exception':error,'original_exit_signal':signal,'return_value':returned,'stdout':out.getvalue(),'stderr':err.getvalue(),'stderr_parts':err.parts,
            'native_ledger_observations':observations,'kernel_end_ledger_descriptors':end_descriptors}
