"""Whole original finite typed-publication command admission; shared native safety remains inherited."""
from pathlib import Path, PurePosixPath
import json
from lib.requirement_validation_budget import InputAdmissionError
from lib.typed_publication import SCOPES, LEDGERS
from lib.providers.operational_publication_protocol import LegacyPublisherProtocol

class LegacyTypedPublisherProtocol(LegacyPublisherProtocol):

    def request(self, command, options):
        if type(command) is not list or not command or len(command) > 20004 or any((type(v) is not str or not v or len(v) > 8192 or ('\x00' in v) for v in command)) or (sum((len(v.encode('utf-8')) for v in command)) > 1024 ** 2):
            raise InputAdmissionError('publisher_original_arguments_required')
        args = command[1:]
        if command[0] == 'git':
            values = {**options, 'cwd': str(options.get('cwd', ''))}
            checked = {'cwd': self.source, 'capture_output': True, 'text': True, 'check': True}
            unchecked = {'cwd': self.source, 'capture_output': True, 'check': False}
            exists = len(args) == 3 and args[:2] == ['cat-file', '-e'] and args[2].startswith('HEAD:') and args[2][5:].startswith(LEDGERS)
            fixed = [['diff', '--name-only', '--no-renames', '-z', 'HEAD'], ['ls-files', '--others', '--exclude-standard', '-z'], ['fetch', 'origin', 'main'], ['merge-base', '--is-ancestor', 'HEAD', 'refs/remotes/origin/main'], ['rev-parse', 'refs/remotes/origin/main'], ['switch', '-c', self.branch], ['reset', '--mixed', 'HEAD'], ['diff', '--cached', '--name-only', '-z'], ['rev-parse', 'HEAD'], ['push', 'origin', 'HEAD:refs/heads/' + self.branch], ['-c', 'user.name=' + self.profile.author_name, '-c', 'user.email=' + self.profile.author_email, '-c', 'commit.gpgsign=false', 'commit', '-m', 'Propose ' + self.scope + ' operational update']]

            def selected(value):
                p = PurePosixPath(value)
                return not p.is_absolute() and '..' not in p.parts and (str(p) == value) and any((value.startswith(v) if v.endswith('/') else value == v for v in SCOPES[self.scope]))
            add = args[:2] == ['add', '--'] and len(args) > 2 and all((selected(v) for v in args[2:]))
            if exists:
                if values != unchecked or not selected(args[2][5:]):
                    raise InputAdmissionError('publisher_original_exists_required')
                return {'kind': 'git', 'original_arguments': command, 'cwd': self.source, 'text': False, 'check': False, 'input': None, 'source_root': self.source}
            if values != checked or (args not in fixed and (not add)):
                raise InputAdmissionError('publisher_original_Git_operation_required')
            return {'kind': 'git', 'original_arguments': command, 'cwd': self.source, 'text': True, 'check': True, 'input': None, 'source_root': self.source}
        if command[0] != 'gh' or set(options) != {'input', 'text', 'capture_output', 'check'} or any((options[k] is not True for k in ('text', 'capture_output', 'check'))) or (type(options['input']) is not str) or (len(options['input'].encode('utf-8')) > 1024 ** 2) or (len(command) != 7) or (command[:4] != ['gh', 'api', '--method', 'POST']) or (command[5:] != ['--input', '-']):
            raise InputAdmissionError('publisher_original_POST_operation_required')
        payload = json.loads(options['input'])
        endpoint = command[4]
        if endpoint == self.profile.pulls_endpoint(self.repository):
            if type(payload) is not dict or set(payload) != {'title', 'head', 'base', 'body'} or payload['head'] != self.branch or (payload['base'] != 'main'):
                raise InputAdmissionError('publisher_original_review_target_required')
        elif endpoint in [self.profile.workflow_endpoint(self.repository, w) for w in self.profile.check_workflows]:
            if payload != {'ref': self.branch}:
                raise InputAdmissionError('publisher_original_dispatch_target_required')
        else:
            raise InputAdmissionError('publisher_original_POST_target_required')
        return {'kind': 'post', 'original_arguments': command, 'cwd': None, 'text': True, 'check': True, 'input': options['input'], 'source_root': self.source}
