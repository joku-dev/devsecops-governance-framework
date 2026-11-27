"""Pure finite Git request contract for the complete original prefix helper."""
import re
from lib.accepted_prefix_git_context import relative_path,absolute_path,FrozenHashArguments
from lib.requirement_validation_budget import InputAdmissionError
GIT_SAFETY=['--no-optional-locks','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','protocol.allow=never']

SHA=re.compile('[a-f0-9]{40}\\Z')
# This validates Git's emitted C-quoted *label*. V1 joins that literal label
# without unquoting it; decoding it here would select a different source path.
C_QUOTED_LABEL=re.compile(r'"(?:[^"\\\x00-\x1f\x7f]|\\(?:[abtnvfr"\\]|[0-3][0-7]{2}))*"\Z')


def fail(reason):raise InputAdmissionError('accepted_prefix_git_'+reason)

class LegacyAcceptedPrefixProtocol:
    def __init__(self,context,*,hash_scope=None):
        self.ledgers=list(context.ledger.input_ledger_paths)
        self.profiles=(context.ledger.PROFILE_PATH,context.ledger.EXCEPTION_PROFILE_PATH)
        self.preparation=[context.preparation.PREPARATION_PATH,context.admission.OPERATING_PATH,
            'model/governance/lifecycle/personal-channel','generated/reports/lifecycle-personal-channel',
            'model/governance/lifecycle/operating-acceptance','model/governance/lifecycle/action-requests',
            'generated/reports/lifecycle-operating-acceptance']
        if len(self.ledgers)!=5 or any(not relative_path(p) for p in self.ledgers+list(self.profiles)+self.preparation):fail('original_context')
        self.hash_scope=hash_scope
    def hashed_path(self,value,root):
        if type(value) is not str:fail('hash_path')
        relative=value[len(root)+1:] if value.startswith(root+'/') else value
        if not relative_path(relative):fail('hash_path')
        ordinary=relative in self.profiles or any(relative.startswith(p+'/') for p in self.ledgers+self.preparation)
        literal_quoted=(C_QUOTED_LABEL.fullmatch(relative) is not None
            and any(relative.startswith('"'+p+'/') for p in self.ledgers+self.preparation))
        if not ordinary and not literal_quoted:fail('hash_selection')
        return relative
    def request(self,kind,arguments,root,cwd):
        if not absolute_path(root):fail('source_label')
        if kind not in ('git-tree','git-run') or type(arguments) is not dict:fail('operation')
        keys={'command','cwd','text' if kind=='git-tree' else 'capture_output'}
        if set(arguments)!=keys or arguments['cwd']!=root or arguments[next(iter(keys-{'command','cwd'}))] is not True:fail('original_options')
        command=arguments['command']
        if type(command) is not list or any(type(v) is not str for v in command) or len(command)<2 or command[0]!='git':fail('command')
        args=command[1:];admitted=False
        if kind=='git-run':
            admitted=len(args)==3 and args[:2]==['cat-file','-e'] and self.base_path(args[2],(self.profiles[1],))
        elif args[0]=='cat-file':
            admitted=len(args)==3 and args[1]=='-e' and args[2].endswith('^{commit}') and self.sha(args[2][:-9])
        elif args[0]=='ls-files':admitted=args==['ls-files','--',*self.ledgers]
        elif args[0]=='ls-tree':admitted=len(args)>=4 and args[:2]==['ls-tree','-r'] and self.sha(args[2]) and args[3:] in (['--',*self.ledgers],['--',*self.preparation])
        elif args[0]=='rev-parse':admitted=len(args)==2 and self.base_path(args[1],self.profiles)
        elif args[0]=='hash-object':
            admitted=len(args)==3 and args[1]=='--'
            if admitted:self.hashed_path(args[2],root)
        if not admitted:fail('original_readonly_command_required')
        return {'kind':kind,'original_arguments':command,'source_root':root,'cwd':root,'timeout':90,'text':kind=='git-tree'}
    @staticmethod
    def sha(value):return type(value) is str and SHA.fullmatch(value) is not None
    def base_path(self,value,paths):
        return len(value)>41 and self.sha(value[:40]) and value[40]==':' and value[41:] in paths
    def actual_arguments(self,spec,selected):
        command=spec['original_arguments']
        if command[1]=='hash-object':
            scope=self.hash_scope
            if type(scope) is not FrozenHashArguments or scope.root!=spec['source_root']:fail('isolated_hash_context_required')
            return scope.arguments(command,selected,GIT_SAFETY)
        return [selected or 'git',*GIT_SAFETY,*command[1:]]
