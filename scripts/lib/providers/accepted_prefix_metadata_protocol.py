"""Finite read-only Git conversion metadata queries; no filter command bodies.

All responses are binary captured CompletedProcess observations, separate from
original business Git diagnostics. An unsupported or failed metadata capture
must remain technically incomplete, never become an original prefix finding.
"""
import re
from lib.accepted_prefix_git_context import ATTRIBUTES,BUILTINS,relative_path,absolute_path,setting
from lib.providers.personal_channel_protocol import GIT_SAFETY
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.personal_channel_process import ReplayPersonalTransport
from lib.requirement_validation_budget import InputAdmissionError

class PrefixMetadataProtocol:
    def __init__(self,path,driver=None):
        if not relative_path(path) or driver is not None and (not setting(driver) or any(c.isspace() for c in driver)):raise InputAdmissionError('accepted_prefix_metadata_selection_required')
        self.path,self.driver=path,driver
    def commands(self):
        commands=[['git','rev-parse',flag] for flag in ('--absolute-git-dir','--git-common-dir','--shared-index-path','--show-object-format')]
        commands.extend([['git','rev-parse','--git-path',name] for name in ('index','objects')])
        commands.append(['git','check-attr','-z',*ATTRIBUTES,'--',self.path])
        commands.extend([['git','config','--null','--get',key] for key in BUILTINS])
        if self.driver is not None:
            commands.extend([['git','config','--null','--type=bool','--get','filter.'+self.driver+'.required'],
                ['git','config','--null','--name-only','--get-regexp','^filter\\.'+re.escape(self.driver)+'\\.(clean|process)$']])
        return commands
    def request(self,kind,arguments,root,cwd):
        if (kind!='git-run' or not absolute_path(root) or type(arguments) is not dict or set(arguments)!={'command','cwd','capture_output'}
                or arguments['cwd']!=root or arguments['capture_output'] is not True or arguments['command'] not in self.commands()):
            raise InputAdmissionError('accepted_prefix_fixed_metadata_query_required')
        return {'kind':kind,'original_arguments':arguments['command'],'source_root':root,'cwd':root,'timeout':90,'text':False}
    def actual_arguments(self,spec,selected):return [selected or 'git',*GIT_SAFETY,*spec['original_arguments'][1:]]

class NativePrefixMetadataTransport(NativePersonalTransport):
    def __init__(self,owner,root,path,*,driver=None,environment=None):
        super().__init__(owner,root,PrefixMetadataProtocol(path,driver),emit_stderr=lambda ref:None,environment=environment)
    def run(self,command):return self.request('git-run',{'command':command,'cwd':self.root,'capture_output':True})

class ReplayPrefixMetadataTransport(ReplayPersonalTransport):
    def __init__(self,owner,root,path,*,driver=None):
        super().__init__(owner,root,PrefixMetadataProtocol(path,driver),emit_stderr=lambda ref:None)
    def run(self,command):return self.request('git-run',{'command':command,'cwd':self.root,'capture_output':True})
