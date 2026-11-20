"""Whole legacy mains with original argument parsing and lazy selected ports.

Binding follows successful original argparse processing. No ledger hints are
guessed from argv, and help/parser failures need no selected filesystem.
"""
import argparse
from contextlib import redirect_stdout, redirect_stderr
import io

from lib.synthetic_lifecycle_context import LifecyclePaths
from lib.synthetic_ledger_context import compose, PROGRAMS
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError
from lib.retained_argparse import formatter_factory,parser_base


class SelectedPorts:
    def __init__(self, factory):
        self.factory, self.io, self.effects, self.binding = factory, None, None, None

    def bind(self, paths, ledger):
        if self.binding is not None: raise InputAdmissionError('synthetic_ledger_original_parser_repeated')
        value = paths.path(ledger)
        binding = {'path': paths.absolute(value.value), 'label': str(value)}
        self.io, self.effects = self.factory(binding)
        self.binding = binding

    def require(self):
        if self.binding is None: raise InputAdmissionError('synthetic_ledger_IO_before_original_parse')


class LazyIO:
    def __init__(self, ports): self.ports = ports
    def __getattr__(self, name):
        self.ports.require()
        return getattr(self.ports.io, name)
    @property
    def files(self): return {} if self.ports.io is None else self.ports.io.files
    @property
    def writes(self): return [] if self.ports.io is None else self.ports.io.writes
    @property
    def touched(self): return {} if self.ports.io is None else self.ports.io.touched
    @property
    def projected_changes(self): return {} if self.ports.io is None else self.ports.io.projected_changes


class LazyEffects:
    def __init__(self, ports): self.ports = ports
    def __getattr__(self, name):
        self.ports.require()
        return getattr(self.ports.effects, name)


def execute(source, cwd, program, argv, *, port_factory, validator_factory, parser_context=None):
    if program not in PROGRAMS: raise InputAdmissionError('synthetic_ledger_program_not_supported')
    ports = SelectedPorts(port_factory)
    selected = LazyIO(ports)
    paths = LifecyclePaths(source, cwd, selected)
    class OriginalParser(parser_base(parser_context) if parser_context is not None else argparse.ArgumentParser):
        def __init__(self,*args,**kwargs):
            if parser_context is not None:
                if kwargs.get('fromfile_prefix_chars') is not None:raise InputAdmissionError('retained_argparse_argument_file_expansion_not_admitted')
                kwargs['formatter_class']=formatter_factory(parser_context)
            super().__init__(*args,**kwargs)
        def parse_args(self, *args, **kwargs):
            values = super().parse_args(*args, **kwargs)
            ports.bind(paths, values.ledger)
            return values
    effects = LazyEffects(ports)
    validator = validator_factory(selected)
    context, programs = compose(paths.path(source), validator_class=validator, path_factory=paths.path,
        argument_parser=OriginalParser, argv=list(argv), native=effects, locking=effects, temporary=effects)
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try: code, error, signal = programs[program].main(), None, None
        except (InputAdmissionError, IntegrityError): raise
        except RetainedOutputError as failure:
            code, error, signal = 1, {'type': failure.original_type, 'message': failure.original_message}, None
        except SystemExit as failure:
            value = failure.code
            if len(str(value)) > 65536: raise InputAdmissionError('synthetic_ledger_exit_message_budget') from failure
            code = 0 if value is None else value if isinstance(value, int) else 1
            if value is not None and not isinstance(value, int): print(value, file=err)
            error, signal = None, {'type': 'SystemExit', 'value': value}
        except Exception as failure:
            if len(str(failure)) > 65536: raise InputAdmissionError('synthetic_ledger_error_message_budget') from failure
            code, error, signal = 1, {'type': type(failure).__name__, 'message': str(failure)}, None
        stdout, stderr = out.getvalue(), err.getvalue()
        if len(stdout) > 131072 or len(stderr) > 131072:
            raise InputAdmissionError('synthetic_ledger_stream_budget')
    return {'kernel_result': {'exit_code': 0 if code is None else code, 'kernel_exception': error,
            'original_exit_signal': signal, 'stdout': stdout, 'stderr': stderr},
            'binding': ports.binding, 'io': selected, 'effects': ports.effects}
