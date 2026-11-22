"""Consumer read-token selection and captured read-only provider/Git effects.

Independent OPA evaluation is a separate mandatory process port. These classes
never accept arbitrary commands, source programs, provider writes or credentials
in a persisted observation. Replay performs no credential or environment lookup.
"""
import os

from lib.providers.consumer_lifecycle_profile import LegacyConsumerReader
from lib.providers.consumer_lifecycle_protocol import LegacyConsumerProtocol, LegacyConsumerCentralProtocol
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.personal_channel_process import ReplayPersonalTransport, MAX_STDERR
from lib.requirement_validation_budget import InputAdmissionError

STREAM_LIMITS = (16 * 1024 ** 2, MAX_STDERR)


class ConsumerReadMethods:
    def check_output(self, command, *, cwd, text=False):
        return self.request('git-tree', {'command': command, 'cwd': str(cwd), 'text': text})

    def run(self, command, *, cwd, capture_output, check=False):
        if check is True:
            return self.request('git-checked-run', {'command': command, 'cwd': str(cwd),
                                                  'capture_output': capture_output, 'check': check})
        if check is not False:
            raise InputAdmissionError('consumer_original_check_option_required')
        return self.request('git-run', {'command': command, 'cwd': str(cwd), 'capture_output': capture_output})


class NativeConsumerTransport(ConsumerReadMethods, NativePersonalTransport):
    def __init__(self, owner, root, profile, *, emit_stderr, environment=None, provider_executable='gh'):
        self.reader_environment = dict(os.environ if environment is None else environment)
        selected = dict(self.reader_environment)
        if selected.get('CONSUMER_EVIDENCE_TOKEN'):
            selected['GH_TOKEN'] = selected['CONSUMER_EVIDENCE_TOKEN']
        super().__init__(owner, root, LegacyConsumerProtocol(profile), emit_stderr=emit_stderr,
                         environment=selected, provider_executable=provider_executable, stream_limits=STREAM_LIMITS)
        self.reader = LegacyConsumerReader(self, lambda: dict(self.reader_environment))

    def fetch(self, endpoint, *, raw=False):
        # Execute the complete original read-token helper over this finite port.
        return self.reader.github_get(endpoint, raw=raw)

    def check_output(self, command, *, cwd=None, text=False, env=None, timeout=None):
        if type(command) is list and command[:1] == ['gh']:
            if (cwd is not None or text is not False or env != self.environment or type(timeout) is not int or timeout != 90
                    or command[:6] != ['gh', 'api', '--hostname', 'github.com', '--method', 'GET']
                    or len(command) not in (7, 9)
                    or len(command) == 9 and command[7:] != ['-H', 'Accept: application/vnd.github.raw+json']):
                raise InputAdmissionError('consumer_original_provider_read_options_required')
            return self.request('get', {'endpoint': command[6], 'raw': len(command) == 9})
        if env is not None or timeout is not None or cwd is None:
            raise InputAdmissionError('consumer_original_git_output_options_required')
        return super().check_output(command, cwd=cwd, text=text)


class ReplayConsumerTransport(ConsumerReadMethods, ReplayPersonalTransport):
    def __init__(self, owner, root, profile, *, emit_stderr):
        super().__init__(owner, root, LegacyConsumerProtocol(profile), emit_stderr=emit_stderr, stream_limits=STREAM_LIMITS)

    def fetch(self, endpoint, *, raw=False):
        return self.request('get', {'endpoint': endpoint, 'raw': raw})


class NativeConsumerCentralTransport(ConsumerReadMethods, NativePersonalTransport):
    def __init__(self, owner, root, *, emit_stderr, environment=None, provider_executable='gh'):
        super().__init__(owner, root, LegacyConsumerCentralProtocol(), emit_stderr=emit_stderr,
                         environment=environment, provider_executable=provider_executable, stream_limits=STREAM_LIMITS)
    def fetch(self, endpoint):
        return self.request('get', {'endpoint': endpoint, 'raw': False})


class ReplayConsumerCentralTransport(ConsumerReadMethods, ReplayPersonalTransport):
    def __init__(self, owner, root, *, emit_stderr):
        super().__init__(owner, root, LegacyConsumerCentralProtocol(), emit_stderr=emit_stderr, stream_limits=STREAM_LIMITS)
    def fetch(self, endpoint):
        return self.request('get', {'endpoint': endpoint, 'raw': False})
