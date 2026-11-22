"""Whole original finite typed-publication command admission; shared native safety remains inherited."""
from pathlib import Path, PurePosixPath
import json
from lib.requirement_validation_budget import InputAdmissionError
from lib.typed_publication import SCOPES, LEDGERS
from lib.providers.operational_publication_process import path_argument
from lib.providers.operational_publication_process import NativeOperationalPublicationProcess

class NativeTypedPublicationProcess(NativeOperationalPublicationProcess):

    def admit_git(self, command, options):
        from lib.typed_publication import SCOPES, LEDGERS
        if len(command) > 20004 or any((type(v) is not str or '\x00' in v or len(v) > 8192 for v in command)):
            raise InputAdmissionError('operational_publication_Git_arguments_required')
        args = command[1:]
        root = Path(options.get('cwd', '')).absolute()
        if root != self.root or options.get('capture_output') is not True:
            raise InputAdmissionError('operational_publication_Git_context_changed')
        exists = len(args) == 3 and args[:2] == ['cat-file', '-e'] and args[2].startswith('HEAD:') and path_argument(args[2][5:]) and args[2][5:].startswith(LEDGERS)
        if exists:
            if set(options) != {'cwd', 'capture_output', 'check'} or options['check'] is not False:
                raise InputAdmissionError('operational_publication_original_exists_options_required')
            return False
        if set(options) != {'cwd', 'text', 'capture_output', 'check'} or options['text'] is not True or options['check'] is not True:
            raise InputAdmissionError('operational_publication_original_Git_options_required')
        fixed = [['diff', '--name-only', '--no-renames', '-z', 'HEAD'], ['ls-files', '--others', '--exclude-standard', '-z'], ['fetch', 'origin', 'main'], ['merge-base', '--is-ancestor', 'HEAD', 'refs/remotes/origin/main'], ['rev-parse', 'refs/remotes/origin/main'], ['switch', '-c', self.branch], ['reset', '--mixed', 'HEAD'], ['diff', '--cached', '--name-only', '-z'], ['rev-parse', 'HEAD'], ['push', 'origin', 'HEAD:refs/heads/' + self.branch], ['-c', 'user.name=' + self.profile.author_name, '-c', 'user.email=' + self.profile.author_email, '-c', 'commit.gpgsign=false', 'commit', '-m', 'Propose ' + self.scope + ' operational update']]
        add = args[:2] == ['add', '--'] and len(args) > 2 and all((path_argument(v) and any((v.startswith(p) if p.endswith('/') else v == p for p in SCOPES[self.scope])) for v in args[2:]))
        if args not in fixed and (not add):
            raise InputAdmissionError('operational_publication_fixed_Git_operation_required')
        return args[:1] in (['fetch'], ['switch'], ['reset'], ['add'], ['push'], ['-c'])
