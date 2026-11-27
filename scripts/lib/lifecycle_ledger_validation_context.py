"""Whole original validator, shared model/IO cursor and explicit helper factories."""
from contextlib import redirect_stdout,redirect_stderr
import io
from lib.lifecycle_preflight_context import PreflightPaths
from lib.synthetic_lifecycle_context import LifecyclePaths
from lib.personal_channel_context import OrderedStderr
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.lifecycle_ledger_validation import LifecycleLedgerValidator
from lib.operating_publication_validation import OperatingPublicationValidation
from lib.accepted_prefix import AcceptedPrefix
from lib.pilot_receipt_verification import PilotReceiptVerification
from lib.pilot_action_verification import PilotActionVerification
from lib.operating_verification import OperatingVerification
from lib.personal_channel_programs import PersonalChannelEvidenceProgram
from lib.personal_channel_collection import PersonalProbeCollection
from lib.retained_argparse import parser_base,formatter_factory
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

class PrefixRootBinding:
    def __init__(self,source,program):self.source,self.program=source,program
    def check_accepted_prefix(self,repo,base_ref):
        if str(repo)!=self.source:raise InputAdmissionError('lifecycle_validator_prefix_root_changed')
        # Preserve the same absolute label across the dedicated probe namespace.
        return self.program.check_accepted_prefix(str(repo),base_ref)

def execute(source,cwd,argv,owner,*,validator_class,parser_context,description,messages,
            ports_factory,provider_factory,fresh_factory,prefix_paths_factory,
            temporary_factory,exclusive_factory,publication_base_ref=None):
    out,err=io.StringIO(),OrderedStderr();paths=PreflightPaths(source,cwd,owner,exclusive_factory);root=paths.path(source)
    context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path)
    ports=ports_factory(owner,root,context,err.emit_raw)
    context.provider=provider_factory(context,ports['personal'])
    prefix_paths=LifecyclePaths(source,cwd,prefix_paths_factory(owner,root,context))
    prefix=PrefixRootBinding(source,AcceptedPrefix(context,path_factory=prefix_paths.path,transport=ports['prefix']))
    receipts=PilotReceiptVerification(context,fresh_factory(context,ports['receipts']),path_factory=paths.path,
        temporary=temporary_factory(owner),clock=ports['receipts'].clock,git=ports['receipts'])
    personal=PersonalChannelEvidenceProgram(root,context,path_factory=paths.path,process=ports['personal'],collector=PersonalProbeCollection(context))
    actions=PilotActionVerification(context,path_factory=paths.path,git=ports['actions'])
    operating=OperatingVerification(root,context,path_factory=paths.path,git=ports['operating'])
    def parser(**kw):return parser_base(parser_context)(prog='validate_governance_lifecycle_ledger.py',formatter_class=formatter_factory(parser_context),**kw)
    program=LifecycleLedgerValidator(context,argument_parser=parser,argv=argv,description=description,messages=messages,
        prefix=prefix,receipts=receipts,personal=personal,actions=actions,operating=operating)
    code=0;error=signal=returned=None
    try:
        with redirect_stdout(out),redirect_stderr(err):
            try:
                if publication_base_ref is None:returned=program.main()
                else:
                    publication=OperatingPublicationValidation(context,path_factory=paths.path,prefix=prefix,receipts=receipts,actions=actions,operating=operating,git=ports['publication'])
                    returned=publication.validate_publication(source,publication_base_ref)
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
    if len(out.getvalue())>131072 or len(err.getvalue())>131072 or error and len(error['message'])>65536:raise InputAdmissionError('lifecycle_validator_original_text_budget')
    return {'exit_code':code,'kernel_exception':error,'original_exit_signal':signal,'return_value':returned,
        'stdout':out.getvalue(),'stderr':err.getvalue(),'stderr_parts':err.parts}
