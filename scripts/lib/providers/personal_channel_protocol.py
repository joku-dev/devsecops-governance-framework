"""Finite original GitHub GET and local Git-tree argument contracts; no execution."""
import re
from lib.requirement_validation_budget import InputAdmissionError

CAPTURES='generated/reports/lifecycle-personal-channel'
GET=re.compile(r'repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/[1-9][0-9]*(?:/comments\?per_page=100&page=(?:[1-9]|10))?\Z')
GIT_SAFETY=['--no-optional-locks','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','protocol.allow=never']

class LegacyPersonalProtocol:
    def request(self,kind,arguments,root,cwd):
        if kind=='get':
            if type(arguments) is not dict or set(arguments)!={'endpoint'} or type(arguments['endpoint']) is not str or len(arguments['endpoint'])>8192 or GET.fullmatch(arguments['endpoint']) is None:
                raise InputAdmissionError('personal_fixed_get_endpoint_required')
            original=['gh','api','--hostname','github.com','--method','GET',arguments['endpoint']]
            return {'kind':kind,'original_arguments':original,'source_root':root,'cwd':cwd,'timeout':90,'text':False}
        if kind=='git-tree':
            if type(arguments) is not dict or set(arguments)!={'command','cwd','text'}:
                raise InputAdmissionError('personal_original_git_options_required')
            command=arguments['command']
            if (type(command) is not list or len(command)!=7 or command[:4]!=['git','ls-tree','-r','--name-only']
                    or command[5:]!=['--',CAPTURES] or type(command[4]) is not str or not command[4]
                    or command[4].startswith('-') or len(command[4])>8192 or any(ord(c)<32 for c in command[4])
                    or arguments['cwd']!=root or arguments['text'] is not True):
                raise InputAdmissionError('personal_original_git_tree_required')
            return {'kind':kind,'original_arguments':command,'source_root':root,'cwd':root,'timeout':90,'text':True}
        raise InputAdmissionError('personal_transport_operation_not_supported')

    def actual_arguments(self,spec,selected):
        original=spec['original_arguments'];label=original[0] if selected is None else selected
        return [label,*(GIT_SAFETY if spec['kind']=='git-tree' else []),*original[1:]]
