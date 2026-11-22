"""Whole observation program over explicit paths, private roles and read/effect ports."""
from contextlib import redirect_stdout,redirect_stderr
from datetime import datetime,timezone
from pathlib import PurePosixPath
from types import SimpleNamespace
import io,posixpath

from lib.provider_observation import ProviderObservation
from lib.synthetic_lifecycle_context import LifecyclePaths,LifecyclePath
from lib.personal_channel_context import OrderedStderr
from lib.retained_argparse import parser_base,formatter_factory
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError


class SecretText:
    """Opaque native credential capability; never a retained token value."""
    def __init__(self,identifier,*,stripped=False):self.identifier,self.stripped=identifier,stripped
    def strip(self):return SecretText(self.identifier,stripped=True)


class ObservationPaths(LifecyclePaths):
    def __init__(self,source,cwd,io_port,backend):super().__init__(source,cwd,io_port);self.backend=backend
    def path(self,value):
        if isinstance(value,LifecyclePath):value=super().path(value).value
        return ObservationPath(self,PurePosixPath(value))


class ObservationPath(LifecyclePath):
    def __truediv__(self,value):return self.namespace.path(super().__truediv__(value))
    @property
    def parent(self):return self.namespace.path(super().parent)
    @property
    def parents(self):return tuple(self.namespace.path(p) for p in super().parents)
    def read_text(self,encoding=None,errors=None):
        if self.namespace.backend.is_credential(self):
            if encoding is not None or errors is not None:raise InputAdmissionError('provider_observation_original_secret_read_required')
            return self.namespace.backend.secret_read(self)
        if self.namespace.backend.is_profile(self):return self.namespace.backend.profile_read(self,encoding,errors)
        return super().read_text(encoding=encoding,errors=errors)


def execute(source,cwd,argv,owner,*,backend,reader_type,audit_type,assurance_factory,parser_context):
    paths=ObservationPaths(source,cwd,owner,backend);root=paths.path(source);backend.bind_paths(paths)
    def argument_parser(**options):
        cls=parser_base(parser_context)
        parser=cls(prog='observe_provider_assurance.py',formatter_class=formatter_factory(parser_context),**options)
        parse=parser.parse_args
        def parsed(values=None,namespace=None):
            args=parse(argv if values is None else values,namespace)
            backend.roles(args.profile,args.credential_file,args.output_root)
            backend.action,backend.revision=args.action,args.revision
            return args
        parser.parse_args=parsed;return parser
    out,err=io.StringIO(),OrderedStderr()
    assurance=assurance_factory(root,backend,err.emit_raw)
    class ObservedDateTime:
        @staticmethod
        def now(tz):
            if tz is not timezone.utc:raise InputAdmissionError('provider_observation_UTC_clock_required')
            return datetime.fromisoformat(backend.clock())
    kernel=ProviderObservation(path_factory=paths.path,native=SimpleNamespace(umask=backend.umask),
        argparse_port=SimpleNamespace(ArgumentParser=argument_parser),reader_type=reader_type,
        audit_type=audit_type,private_check=backend.private_check,capture_reviews=assurance.capture_reviews,
        capture_security=assurance.capture_security,atomic_json=backend.atomic_json,datetime_port=ObservedDateTime)
    returned=error=signal=None;code=0
    with redirect_stdout(out),redirect_stderr(err):
        try:returned=kernel.main()
        except (InputAdmissionError,IntegrityError):raise
        except RetainedOutputError as caught:code,error=1,{'type':caught.original_type,'message':caught.original_message}
        except SystemExit as caught:
            code=0 if caught.code is None else caught.code if type(caught.code) is int else 1
            if caught.code is not None and type(caught.code) is not int:print(caught.code,file=err)
            signal={'type':'SystemExit','value':caught.code}
        except Exception as caught:code,error=1,{'type':type(caught).__name__,'message':str(caught)}
    if len(out.getvalue())>131072 or len(err.getvalue())>131072 or error and len(error['message'])>65536:
        raise InputAdmissionError('provider_observation_original_text_budget')
    return {'exit_code':code,'return_value':returned,'kernel_exception':error,
        'original_exit_signal':signal,'stdout':out.getvalue(),'stderr':err.getvalue(),'stderr_parts':err.parts}
