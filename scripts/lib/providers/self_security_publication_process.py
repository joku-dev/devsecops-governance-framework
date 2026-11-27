"""Owned original self-security Git/API writer; shared process limits and identity guards."""
from pathlib import Path
import hashlib, os, subprocess
from lib.providers.operational_publication_process import NativeOperationalPublicationProcess, NativePublisherPipes, GIT_SAFETY, lookup, program_identity, failure_value
from lib.providers.self_security_publication_protocol import LegacySelfSecurityPublicationProtocol
from lib.requirement_validation_budget import InputAdmissionError

class NativeSelfSecurityPublicationProcess(NativeOperationalPublicationProcess):

    def __init__(self, root, *, repository, run_id, attempt, profile, environment=None, provider_executable='gh', local_origin_root=None, timeout=90):
        self.root = Path(root).absolute()
        self.profile = profile
        self.environment = dict(os.environ if environment is None else environment)
        self.cwd = str(Path.cwd())
        self.scope = 'self-security'
        self.repository = repository
        self.protocol = LegacySelfSecurityPublicationProtocol(str(self.root), repository=repository, run_id=run_id, attempt=attempt, local_origin_root=None if local_origin_root is None else str(local_origin_root), cwd=self.cwd)
        self.branch = profile.branch
        self.provider_executable = provider_executable
        self.local_origin_root = None if local_origin_root is None else Path(local_origin_root).resolve()
        self.timeout = timeout
        if type(timeout) not in (int, float) or not 0 < timeout <= 600:
            raise InputAdmissionError('self_security_publisher_deadline_required')
        self.observations = []
        self.remote_pins = None
        self.root_identity = self.context()
        self.git_identity = self.git_context()

    def admit_git(self, command, options):
        self.protocol.request(list(command), options)
        return command[1:2] in (['fetch'], ['reset'], ['clean'], ['switch'], ['-c'], ['add'], ['push'])

    def run(self, command, **options):
        self.last_native = None
        command = list(command)
        if not command or command[0] not in ('git', 'gh'):
            raise InputAdmissionError('operational_publication_fixed_program_required')
        mutation = False
        data = None
        if command[0] == 'git':
            mutation = self.admit_git(command, options)
            env = self.git_environment()
            cwd = str(self.root)
            name = 'git'
        else:
            spec = self.protocol.request(command, options)
            if spec['kind'] not in ('get', 'post'):
                raise InputAdmissionError('self_security_publisher_api_kind_required')
            env = dict(self.environment)
            if env.get('GH_HOST', 'github.com') != 'github.com':
                raise InputAdmissionError('operational_publication_explicit_host_profile_required')
            cwd = self.cwd
            name = self.provider_executable
            mutation = True
        selected = lookup(name, cwd, env)
        identity = None if selected is None else program_identity(selected, cwd)
        if identity is not None and any((Path(identity['resolved']).is_relative_to(root) for root in (self.root, *getattr(self, 'forbidden_program_roots', ())))):
            raise InputAdmissionError('operational_publication_source_or_private_program_forbidden')
        if self.context() != self.root_identity or self.git_context() != self.git_identity:
            raise InputAdmissionError('operational_publication_source_replaced')
        if command[0] == 'git' and selected is not None:
            self.preflight_filter_profile(selected)
        if command[0] == 'git' and mutation and (selected is not None):
            self.git_write_tree()
            self.preflight(selected)
        actual = [selected or command[0], *(GIT_SAFETY if command[0] == 'git' else []), *command[1:]]
        encoding = subprocess._text_encoding() if options.get('text', False) else None
        if options.get('input') is not None:
            data = options['input'].encode(encoding)
        process = NativePublisherPipes()
        code = None
        out = err = b''
        start_error = None
        row = {'original_arguments': command, 'actual_arguments': actual, 'cwd': cwd, 'write_operation': mutation, 'remote': self.remote_pins, 'program': identity, 'input_sha256': None if data is None else hashlib.sha256(data).hexdigest(), 'input_bytes': None if data is None else len(data)}
        self.observations.append(row)
        try:
            try:
                code, out, err = process.run(actual, cwd, env, self.timeout, data)
            except OSError as error:
                if isinstance(error, FileNotFoundError):
                    error = FileNotFoundError(error.errno, error.strerror, command[0])
                    start_error = failure_value(error)
                    raise error from None
                start_error = failure_value(error)
                raise
            if self.context() != self.root_identity or self.git_context() != self.git_identity or (identity is not None and program_identity(selected, cwd) != identity):
                raise InputAdmissionError('operational_publication_source_or_program_changed')
            stdout = out.decode(encoding).replace('\r\n', '\n').replace('\r', '\n') if encoding else out
            stderr = err.decode(encoding).replace('\r\n', '\n').replace('\r', '\n') if encoding else err
            row.update(returncode=code, stdout_sha256=hashlib.sha256(out).hexdigest(), stderr_sha256=hashlib.sha256(err).hexdigest())
            if code and options['check']:
                raise subprocess.CalledProcessError(code, command, output=stdout, stderr=stderr)
            return subprocess.CompletedProcess(command, code, stdout, stderr)
        finally:
            row['observation'] = dict(process.observation)
            self.last_native = {'row': row, 'raw_stdout': out, 'raw_stderr': err, 'raw_stdin': data, 'effective_encoding': encoding, 'returncode': code, 'start_error': start_error, 'source_identity': list(self.root_identity), 'Git_identity': list(self.git_identity)}
