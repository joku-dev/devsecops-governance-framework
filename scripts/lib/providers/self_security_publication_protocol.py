"""Finite exact original self-security Git and GET/PATCH/POST request admission."""
from pathlib import PurePosixPath
import json,re
from lib.providers.operational_publication_protocol import LegacyPublisherProtocol
from lib.providers.self_security_publication_profile import LegacySelfSecurityPublicationProfile
from lib.self_security_publication import ALLOWED_PATHS,REPORT_JSON
from lib.requirement_validation_budget import InputAdmissionError


class LegacySelfSecurityPublicationProtocol(LegacyPublisherProtocol):
    def __init__(self,source,*,repository,run_id,attempt,cwd=None,local_origin_root=None,private_state_label=None):
        if type(source) is not str or not PurePosixPath(source).is_absolute() or str(PurePosixPath(source))!=source or '..' in PurePosixPath(source).parts:raise InputAdmissionError('self_security_publisher_source_required')
        if type(repository) is not str or re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository) is None or any(type(v) is not str or re.fullmatch('[1-9][0-9]*',v) is None for v in (run_id,attempt)):raise InputAdmissionError('self_security_publisher_subject_required')
        self.source,self.repository,self.run_id,self.attempt=source,repository,run_id,attempt;self.cwd=source if cwd is None else cwd;self.local_origin_root=local_origin_root;self.private_state_label=private_state_label;self.profile=LegacySelfSecurityPublicationProfile();self.branch=self.profile.branch
    def request(self,command,options):
        if type(command) is not list or not command or len(command)>100 or any(type(v) is not str or not v or len(v)>8192 or '\0' in v for v in command):raise InputAdmissionError('self_security_publisher_arguments_required')
        args=command[1:]
        if command[0]=='git':
            if set(options)!={'cwd','capture_output','text','check'} or str(options['cwd'])!=self.source or options['capture_output'] is not True or options['text'] is not True or type(options['check']) is not bool:raise InputAdmissionError('self_security_publisher_git_options_required')
            actor=['-c','user.name='+self.profile.author_name,'-c','user.email='+self.profile.author_email,'-c','commit.gpgsign=false']
            remote='refs/remotes/origin/'+self.branch
            checked=[['diff','--name-only','--no-renames','-z','HEAD'],['ls-files','--others','--exclude-standard','-z'],['fetch','origin','main'],['merge-base','--is-ancestor','HEAD','refs/remotes/origin/main'],['fetch','origin',self.branch],['reset','--hard','HEAD'],['clean','-fd','--','generated'],['switch','-C',self.branch,remote],['switch','-c',self.branch,'refs/remotes/origin/main'],[*actor,'merge','--no-edit','refs/remotes/origin/main'],['diff','--cached','--name-only','-z'],[*actor,'commit','-m','Propose self-security status refresh'],['rev-parse','HEAD'],['push','origin','HEAD:refs/heads/'+self.branch]]
            unchecked=[['ls-remote','--exit-code','--heads','origin','refs/heads/'+self.branch],['show','HEAD:'+REPORT_JSON],['show',remote+':'+REPORT_JSON]]
            add=args[:2]==['add','--'] and len(args)>2 and all(x in ALLOWED_PATHS for x in args[2:])
            if not ((options['check'] and (args in checked or add)) or (not options['check'] and args in unchecked)):raise InputAdmissionError('self_security_publisher_fixed_git_operation_required')
            return {'kind':'git','original_arguments':command,'cwd':self.source,'text':True,'check':options['check'],'input':None,'source_root':self.source}
        if command[0]!='gh' or set(options)!={'input','text','capture_output','check'} or any(options[k] is not True for k in ('text','capture_output','check')) or len(command) not in (5,7) or command[:3]!=['gh','api','--method']:raise InputAdmissionError('self_security_publisher_api_options_required')
        method,endpoint=command[3:5];raw=options['input'];payload=None
        if len(command)==7:
            if command[5:]!=['--input','-'] or type(raw) is not str or len(raw.encode())>1024**2:raise InputAdmissionError('self_security_publisher_api_payload_required')
            payload=json.loads(raw)
        elif raw is not None:raise InputAdmissionError('self_security_publisher_original_empty_input_required')
        if method=='GET' and endpoint==self.profile.open_pr_endpoint(self.repository):
            if payload is not None:raise InputAdmissionError('self_security_publisher_query_payload_forbidden')
            kind='get'
        elif method=='POST' and endpoint==self.profile.pull_endpoint(self.repository):
            if type(payload) is not dict or set(payload)!={'title','head','base','body'} or payload['head']!=self.branch or payload['base']!='main':raise InputAdmissionError('self_security_publisher_review_target_required')
            kind='post'
        elif method=='PATCH' and re.fullmatch(re.escape(self.profile.pull_endpoint(self.repository))+'/[1-9][0-9]*',endpoint):
            if type(payload) is not dict or set(payload)!={'title','body'}:raise InputAdmissionError('self_security_publisher_review_patch_required')
            kind='post'
        elif method=='POST' and endpoint in [self.profile.workflow_endpoint(self.repository,w) for w in self.profile.check_workflows]:
            expected={'ref':self.branch}
            if endpoint==self.profile.workflow_endpoint(self.repository,'dependency-review.yml'):expected['inputs']={'base_ref':'main','head_ref':self.branch}
            if payload!=expected:raise InputAdmissionError('self_security_publisher_dispatch_target_required')
            kind='post'
        else:raise InputAdmissionError('self_security_publisher_fixed_api_target_required')
        return {'kind':kind,'original_arguments':command,'cwd':None,'text':True,'check':True,'input':raw,'source_root':self.source}
