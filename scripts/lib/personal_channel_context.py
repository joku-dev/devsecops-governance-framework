"""Whole original programs over explicit file, exclusive-output and read ports.

Provider stderr is retained as ordered raw-byte references among Python text
writes. No decoding of provider stderr and no original-program argv rewriting.
"""
from contextlib import redirect_stdout,redirect_stderr
from pathlib import PurePosixPath
import io
from lib.synthetic_lifecycle_context import LifecyclePaths,LifecyclePath
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.personal_channel_programs import PersonalStatementProgram,PersonalChannelCheckProgram,PersonalChannelEvidenceProgram
from lib.personal_channel_collection import PersonalProbeCollection
from lib.retained_argparse import parser_base,formatter_factory
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

PROGRAMS={'statement':('generate_personal_channel_probe.py',PersonalStatementProgram),
          'check':('check_lifecycle_personal_channel.py',PersonalChannelCheckProgram),
          'evidence':('generate_personal_channel_evidence.py',PersonalChannelEvidenceProgram)}
MAX_TEXT=131072
MAX_STDERR=8*1024**2

class PersonalPaths(LifecyclePaths):
    def __init__(self,source,cwd,io_port,exclusive_factory):
        super().__init__(source,cwd,io_port);self.exclusive_factory=exclusive_factory
    def path(self,value):
        if isinstance(value,LifecyclePath):value=super().path(value).value
        return PersonalPath(self,PurePosixPath(value))

class PersonalPath(LifecyclePath):
    def __truediv__(self,value):return self.namespace.path(super().__truediv__(value))
    @property
    def parent(self):return self.namespace.path(super().parent)
    @property
    def parents(self):return tuple(self.namespace.path(value) for value in super().parents)
    def resolve(self,strict=False):return self.namespace.path(super().resolve(strict))
    def open(self,mode='r',encoding=None,errors=None):
        if mode=='xb':
            if encoding is not None or errors is not None:raise InputAdmissionError('personal_original_binary_open_options_required')
            return self.namespace.exclusive_factory(self.namespace.io,self.namespace.absolute(self.value),str(self))
        return super().open(mode,encoding,errors)

class OrderedStderr(io.StringIO):
    def __init__(self):super().__init__();self.parts=[];self.bytes=0
    def reserve(self,count):
        self.bytes+=count
        if self.bytes>MAX_STDERR or len(self.parts)>=8192:raise InputAdmissionError('personal_original_stderr_capture_budget')
    def write(self,text):
        if type(text) is not str:return super().write(text)
        if text:
            self.reserve(len(text.encode('utf-8')));self.parts.append({'text':text})
        return super().write(text)
    def emit_raw(self,ref):
        if (type(ref) is not dict or set(ref)!={'sha256','bytes'} or type(ref['sha256']) is not str
                or len(ref['sha256'])!=64 or any(c not in '0123456789abcdef' for c in ref['sha256'])
                or type(ref['bytes']) is not int or not 0<=ref['bytes']<=256*1024):
            raise IntegrityError('personal_provider_stderr_reference_changed')
        if ref['bytes']:self.reserve(ref['bytes']);self.parts.append({'blob':dict(ref)})

def execute(source,cwd,program,argv,io_port,*,validator_class,provider_factory,
            transport_factory,exclusive_factory,parser_context=None,verify_base_ref=None):
    if program not in PROGRAMS:raise InputAdmissionError('personal_original_program_not_supported')
    if program=='check' and parser_context is None:raise InputAdmissionError('personal_original_parser_context_required')
    if program!='check' and parser_context is not None:raise InputAdmissionError('personal_original_program_has_no_parser')
    if verify_base_ref is not None and (program!='evidence' or argv or type(verify_base_ref) is not str or not verify_base_ref):
        raise InputAdmissionError('personal_original_verify_function_arguments_required')
    paths=PersonalPaths(source,cwd,io_port,exclusive_factory);root=paths.path(source)
    out,err=io.StringIO(),OrderedStderr()
    transport=transport_factory(io_port,root,err.emit_raw)
    context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path,
        provider_factory=lambda value:provider_factory(value,transport))
    collector=PersonalProbeCollection(context)
    filename,kind=PROGRAMS[program]
    options={'path_factory':paths.path}
    if program=='check':
        def parser(**kw):return parser_base(parser_context)(prog=filename,formatter_class=formatter_factory(parser_context),**kw)
        options.update(argument_parser=parser,argv=argv,collector=collector)
    elif program=='evidence':options.update(process=transport,collector=collector)
    kernel=kind(root,context,**options)
    error=signal=None;returned=None;code=0
    try:
        with redirect_stdout(out),redirect_stderr(err):
            try:
                if verify_base_ref is None:kernel.main()
                else:returned=kernel.verify_new_captures(root,verify_base_ref)
            except (InputAdmissionError,IntegrityError):raise
            except RetainedOutputError as caught:code,error=1,{'type':caught.original_type,'message':caught.original_message}
            except SystemExit as caught:
                code=0 if caught.code is None else caught.code if type(caught.code) is int else 1
                if caught.code is not None and type(caught.code) is not int:print(caught.code,file=err)
                signal={'type':'SystemExit','value':caught.code}
            except Exception as caught:code,error=1,{'type':type(caught).__name__,'message':str(caught)}
    finally:
        for session in getattr(io_port,'personal_exclusive_sessions',[]):session.release()
    if len(out.getvalue())>MAX_TEXT or len(err.getvalue())>MAX_TEXT or error and len(error['message'])>65536:
        raise InputAdmissionError('personal_original_text_capture_budget')
    return {'exit_code':code,'kernel_exception':error,'original_exit_signal':signal,'return_value':returned,
            'stdout':out.getvalue(),'stderr':err.getvalue(),'stderr_parts':err.parts}
