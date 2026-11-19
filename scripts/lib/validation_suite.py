"""Complete original local validation ordering over explicit native ports.

Stdlib-only: tool checking works before application dependencies are available.
The default includes every validator and full unit discovery. Native adapters own
commands/source/leases; an observation is not an execution or approval attestation.
"""
from dataclasses import dataclass
import base64

PROFILE='legacy-local-validation-v1'
MAX_STREAM=8*1024**2
USAGE=('Usage: scripts/validate_all.sh [--check-tools]\n\n'
       'Run the complete local governance validation with the pinned toolchain.\n\n'
       'Options:\n'
       '  --check-tools  Verify the prepared toolchain without running validators.\n\n'
       'Environment variables:\n'
       '  VALIDATION_VENV  Validation environment directory. Default: .venv-validation\n')
TOOL_PHASES=('require_tools','opa_version','dependency_versions','dependency_consistency')
VALIDATOR_PHASES=('opa_check','runtime_validation','repository_validation','provenance_validation','unit_tests')


def mode(arguments):
    if type(arguments) is not list or any(type(s) is not str for s in arguments):
        raise ValueError('validation_suite_argument_list_required')
    first=arguments[0] if arguments else ''
    # The original help branch exits before its later extra-argument check.
    if first in ('--help','-h'):return 'help'
    if len(arguments)>1 or first not in ('','--check-tools'):return 'usage-error'
    return 'check-tools' if first=='--check-tools' else 'validate'


@dataclass(frozen=True)
class Observation:
    returncode:int
    stdout:bytes=b''
    stderr:bytes=b''

    def checked(self):
        if (type(self.returncode) is not int or not 0<=self.returncode<=255
                or type(self.stdout) is not bytes or type(self.stderr) is not bytes
                or max(len(self.stdout),len(self.stderr))>MAX_STREAM):
            raise ValueError('validation_suite_native_observation_required')
        return self
    def wire(self):
        self.checked()
        return {'returncode':self.returncode,'stdout_base64':base64.b64encode(self.stdout).decode(),
                'stderr_base64':base64.b64encode(self.stderr).decode()}
    @classmethod
    def from_wire(cls,row):
        if type(row) is not dict or set(row)!={'returncode','stdout_base64','stderr_base64'}:
            raise ValueError('validation_suite_observation_shape_changed')
        decoded=[]
        for key in ('stdout_base64','stderr_base64'):
            value=row[key]
            if type(value) is not str or len(value)>4*((MAX_STREAM+2)//3):
                raise ValueError('validation_suite_stream_budget')
            raw=base64.b64decode(value,validate=True)
            if base64.b64encode(raw).decode()!=value:raise ValueError('validation_suite_stream_encoding_changed')
            decoded.append(raw)
        return cls(row['returncode'],*decoded).checked()


def run(arguments,ports,journal,sink,*,environment_label,expected_opa_version):
    """Fail fast on every actual shell-status result; never default to a skip.

    OPA-version stdout is command-substitution data, not emitted output. The port
    returns the original awk pipeline's captured bytes, including interior LFs or
    CRs. The core strips only trailing LFs, like shell command substitution.
    Unknown exceptions leave the durable phase intent without a fabricated end.
    """
    selected=mode(arguments)
    if selected in ('help','usage-error'):
        sink.write('stdout' if selected=='help' else 'stderr',USAGE.encode())
        return 0 if selected=='help' else 2
    if (type(environment_label) is not str or not environment_label or '\0' in environment_label
            or type(expected_opa_version) is not str or not expected_opa_version):
        raise ValueError('validation_suite_explicit_labels_required')
    def step(action,*,stdout=True):
        token=journal.before(action)
        value=ports.perform(action)
        if type(value) is not Observation:raise ValueError('validation_suite_typed_observation_required')
        value.checked();journal.after(token,value.wire())
        if stdout:sink.write('stdout',value.stdout)
        sink.write('stderr',value.stderr)
        return value
    value=step('require_tools')
    if value.returncode:return value.returncode
    version=step('opa_version',stdout=False)
    if version.returncode:return version.returncode
    actual=version.stdout.rstrip(b'\n')
    if actual!=expected_opa_version.encode():
        sink.write('stderr',b'OPA version mismatch: expected '+expected_opa_version.encode()+b', got '+actual+
                   b'\nRun: ./scripts/bootstrap_validation_env.sh\n')
        return 1
    for action in ('dependency_versions','dependency_consistency'):
        value=step(action)
        if value.returncode:return value.returncode
    sink.write('stdout',b'Validation toolchain ready (OPA '+actual+b').\n')
    if selected=='check-tools':return 0
    for action in VALIDATOR_PHASES:
        value=step(action)
        if value.returncode:return value.returncode
    return 0


class RecordedPorts:
    def __init__(self,rows):
        if type(rows) is not list or len(rows)>len(TOOL_PHASES)+len(VALIDATOR_PHASES):
            raise ValueError('validation_suite_recorded_sequence_required')
        self.rows=rows;self.position=0
    def perform(self,action):
        if self.position==len(self.rows):raise ValueError('validation_suite_recording_incomplete')
        row=self.rows[self.position];self.position+=1
        if type(row) is not dict or set(row)!={'action','observation'} or row['action']!=action:
            raise ValueError('validation_suite_recorded_order_changed')
        return Observation.from_wire(row['observation'])
    def complete(self):
        if self.position!=len(self.rows):raise ValueError('validation_suite_unused_recordings')


def replay(arguments,rows,sink,*,environment_label,expected_opa_version):
    ports=RecordedPorts(rows)
    class Observer:
        def before(self,action):return action
        def after(self,*ignored):pass
    result=run(arguments,ports,Observer(),sink,environment_label=environment_label,
               expected_opa_version=expected_opa_version)
    ports.complete();return result
