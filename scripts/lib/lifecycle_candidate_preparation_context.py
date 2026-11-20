"""Explicit whole candidate execution; no acceptance or live lifecycle effects."""
from contextlib import redirect_stdout,redirect_stderr
import io
from lib.lifecycle_candidate_preparation import (CandidateNormalization,DevsecopsCandidateAdapter,
    ArchitectureCandidateAdapter,CandidateWriter,DevsecopsCandidateProgram,ArchitectureCandidateProgram)
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.synthetic_lifecycle_context import LifecyclePaths
from lib.retained_argparse import formatter_factory,parser_base
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

PROGRAMS={'devsecops':('prepare_lifecycle_devsecops_candidates.py',DevsecopsCandidateProgram),
    'architecture':('prepare_lifecycle_architecture_candidates.py',ArchitectureCandidateProgram)}


def compose(source,cwd,program,argv,io_port,*,validator_class,parser_context):
    if program not in PROGRAMS:raise InputAdmissionError('lifecycle_candidate_program_not_supported')
    paths=LifecyclePaths(source,cwd,io_port);root=paths.path(source)
    context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path)
    normalization=CandidateNormalization(context)
    devsecops=DevsecopsCandidateAdapter(context,normalization).adapt_devsecops
    architecture=ArchitectureCandidateAdapter(context,normalization).adapt_architecture
    writer=CandidateWriter(root,context,path_factory=paths.path,adapter=devsecops)
    filename,cls=PROGRAMS[program]
    def parser(**options):
        if options.get('fromfile_prefix_chars') is not None:raise InputAdmissionError('retained_argparse_argument_file_expansion_not_admitted')
        return parser_base(parser_context)(prog=filename,formatter_class=formatter_factory(parser_context),**options)
    kernel=cls(writer,devsecops if program=='devsecops' else architecture,
        path_factory=paths.path,argument_parser=parser,argv=list(argv))
    return context,writer,kernel


def execute(source,cwd,program,argv,io_port,*,validator_class,parser_context):
    context,writer,kernel=compose(source,cwd,program,argv,io_port,
        validator_class=validator_class,parser_context=parser_context)
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
