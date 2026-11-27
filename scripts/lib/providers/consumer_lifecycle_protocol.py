"""Finite consumer evidence GETs and original read-only local Git operations.

These are transport admission rules, not governance findings or credentials.
The complete consumer model schema remains a separate required validation.
"""
from copy import deepcopy
from pathlib import PurePosixPath
import re

from lib.providers.personal_channel_protocol import GIT_SAFETY
from lib.providers.operating_verification_protocol import base
from lib.requirement_validation_budget import InputAdmissionError

MODEL = 'model/governance/lifecycle/consumer-operation'
HISTORY = 'governance/consumer-lifecycle'
OBSERVATIONS = HISTORY + '/observations'
ACTIONS = HISTORY + '/actions'
ACCEPTANCE = HISTORY + '/acceptance'
INDEX = 'status/governance-consumer-lifecycle.json'
CENTRAL = 'joku-dev/devsecops-governance-framework'
REPOSITORY = re.compile(r'[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*\Z')
INTEGER = r'[1-9][0-9]*'
COMMIT = r'[a-f0-9]{40}'


def path_label(value):
    return (type(value) is str and bool(value) and len(value) <= 8192
            and str(PurePosixPath(value)) == value and not PurePosixPath(value).is_absolute()
            and '..' not in PurePosixPath(value).parts
            and not any(ord(c) < 32 or 0xd800 <= ord(c) <= 0xdfff for c in value))


class LegacyConsumerProtocol:
    def __init__(self, profile):
        try:
            consumer = profile['scope']['repository_id']
            source = deepcopy(profile['source'])
            baseline = source['baseline_repository']
            files = source['reference_files']
            valid = (REPOSITORY.fullmatch(consumer) is not None
                     and REPOSITORY.fullmatch(baseline) is not None
                     and path_label(source['workflow_path'])
                     and path_label(source['baseline_ref'])
                     and re.fullmatch(COMMIT, source['baseline_tag_object']) is not None
                     and re.fullmatch(COMMIT, source['reference_commit']) is not None
                     and type(files) is dict and 0 < len(files) <= 64
                     and all(path_label(name) and type(digest) is str
                             and re.fullmatch('[a-f0-9]{64}', digest) is not None
                             for name, digest in files.items()))
        except (KeyError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise InputAdmissionError('consumer_explicit_evidence_profile_required')
        self.consumer, self.source = consumer, source

    def get_allowed(self, endpoint, raw):
        consumer = 'repos/' + self.consumer
        baseline = 'repos/' + self.source['baseline_repository']
        if raw:
            if re.fullmatch(re.escape(consumer + '/contents/' + self.source['workflow_path'] + '?ref=') + COMMIT, endpoint):
                return True
            return endpoint in {baseline + '/contents/' + path + '?ref=' + self.source['reference_commit']
                                for path in self.source['reference_files']}
        if endpoint in (consumer,
                        baseline + '/git/ref/tags/' + self.source['baseline_ref'],
                        baseline + '/git/tags/' + self.source['baseline_tag_object']):
            return True
        suffix = (r'/actions/runs/' + INTEGER + r'(?:/artifacts\?per_page=100&page=(?:[1-9]|10))?'
                  r'|/actions/workflows/' + INTEGER + r'|/actions/artifacts/' + INTEGER + r'(?:/zip)?')
        if re.fullmatch(re.escape(consumer) + '(?:' + suffix + ')', endpoint):
            return True
        return False

    def request(self, kind, arguments, root, cwd):
        if kind == 'get':
            if (type(arguments) is not dict or set(arguments) != {'endpoint', 'raw'}
                    or type(arguments['endpoint']) is not str or len(arguments['endpoint']) > 8192
                    or type(arguments['raw']) is not bool
                    or not self.get_allowed(arguments['endpoint'], arguments['raw'])):
                raise InputAdmissionError('consumer_fixed_read_endpoint_required')
            command = ['gh', 'api', '--hostname', 'github.com', '--method', 'GET', arguments['endpoint']]
            if arguments['raw']:
                command += ['-H', 'Accept: application/vnd.github.raw+json']
            return self.spec(kind, command, root, cwd, False)
        if type(arguments) is not dict or arguments.get('cwd') != root:
            raise InputAdmissionError('consumer_original_git_options_required')
        command = arguments.get('command')
        if type(command) is not list or any(type(x) is not str for x in command):
            raise InputAdmissionError('consumer_original_read_git_required')
        if kind == 'git-tree' and set(arguments) == {'command', 'cwd', 'text'}:
            tree_paths = ([OBSERVATIONS], [ACTIONS], [ACCEPTANCE], [OBSERVATIONS, ACTIONS], [HISTORY, MODEL])
            if (len(command) >= 7 and command[:4] == ['git', 'ls-tree', '-r', '--name-only']
                    and base(command[4]) and command[5] == '--' and command[6:] in tree_paths
                    and arguments['text'] is True):
                return self.spec(kind, command, root, root, True)
            if (len(command) == 3 and command[:2] == ['git', 'show'] and arguments['text'] is False
                    and self.history_show(command[2])):
                return self.spec(kind, command, root, root, False)
        if kind == 'git-run' and set(arguments) == {'command', 'cwd', 'capture_output'}:
            suffix = ':' + INDEX
            if (len(command) == 3 and command[:2] == ['git', 'show'] and command[2].endswith(suffix)
                    and base(command[2][:-len(suffix)]) and arguments['capture_output'] is True):
                return self.spec(kind, command, root, root, False)
        if kind == 'git-checked-run' and set(arguments) == {'command', 'cwd', 'capture_output', 'check'}:
            if (len(command) == 5 and command[:4] == ['git', 'ls-files', '--error-unmatch', '--']
                    and path_label(command[4]) and command[4].startswith(MODEL + '/action-requests/')
                    and arguments['check'] is True and arguments['capture_output'] is True):
                return self.spec(kind, command, root, root, False)
        raise InputAdmissionError('consumer_original_read_git_required')

    def history_show(self, selector):
        if ':' not in selector:
            return False
        revision, path = selector.split(':', 1)
        return base(revision) and path_label(path) and (path.startswith(HISTORY + '/') or path.startswith(MODEL + '/'))

    @staticmethod
    def spec(kind, command, root, cwd, text):
        return {'kind': kind, 'original_arguments': command, 'source_root': root,
                'cwd': cwd, 'timeout': 90, 'text': text}

    def actual_arguments(self, spec, selected):
        original = spec['original_arguments']
        return [original[0] if selected is None else selected,
                *(GIT_SAFETY if spec['kind'] != 'get' else []), *original[1:]]


class LegacyConsumerCentralProtocol(LegacyConsumerProtocol):
    """Personal statements/required guard use the original central credential."""
    def __init__(self):
        pass
    def get_allowed(self, endpoint, raw):
        return not raw and (endpoint == 'repos/' + CENTRAL + '/rules/branches/main'
            or re.fullmatch(re.escape('repos/' + CENTRAL) + r'/issues/' + INTEGER
                            + r'(?:/comments\?per_page=100&page=(?:[1-9]|10))?', endpoint) is not None)
