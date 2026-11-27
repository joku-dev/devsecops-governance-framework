"""Closed original command/option binding shared by native capture and replay."""
from pathlib import PurePosixPath
import json,re
from urllib.parse import urlsplit
from lib.operational_publication import SCOPES,LEDGERS
from lib.providers.operational_publication_profile import LegacyOperationalPublicationProfile
from lib.providers.operational_publication_process import GIT_SAFETY
from lib.requirement_validation_budget import InputAdmissionError

class LegacyPublisherProtocol:
    def __init__(self,source,*,scope,repository,run_id,attempt,cwd=None,local_origin_root=None,private_state_label=None):
        if type(source) is not str or not PurePosixPath(source).is_absolute() or str(PurePosixPath(source))!=source or '..' in PurePosixPath(source).parts:raise InputAdmissionError('publisher_source_label_required')
        if scope not in SCOPES or type(repository) is not str or re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository) is None or any(type(v) is not str or re.fullmatch('[1-9][0-9]*',v) is None for v in (run_id,attempt)):raise InputAdmissionError('publisher_bound_subject_required')
        self.source,self.scope,self.repository,self.run_id,self.attempt=source,scope,repository,run_id,attempt
        self.cwd=source if cwd is None else cwd;self.local_origin_root=local_origin_root;self.private_state_label=private_state_label
        self.branch=f'automation/{scope}/{run_id}-{attempt}';self.profile=LegacyOperationalPublicationProfile()
    def request(self,command,options):
        if type(command) is not list or not command or len(command)>20004 or any(type(v) is not str or not v or len(v)>8192 or '\0' in v for v in command) or sum(len(v.encode('utf-8')) for v in command)>1024**2:raise InputAdmissionError('publisher_original_arguments_required')
        args=command[1:]
        if command[0]=='git':
            values={**options,'cwd':str(options.get('cwd',''))}
            checked={'cwd':self.source,'capture_output':True,'text':True,'check':True};unchecked={'cwd':self.source,'capture_output':True,'check':False}
            exists=len(args)==3 and args[:2]==['cat-file','-e'] and args[2].startswith('HEAD:') and args[2][5:].startswith(LEDGERS)
            fixed=[['diff','--name-only','--no-renames','-z','HEAD'],['ls-files','--others','--exclude-standard','-z'],['fetch','origin','main'],['merge-base','--is-ancestor','HEAD','refs/remotes/origin/main'],['rev-parse','refs/remotes/origin/main'],['switch','-c',self.branch],['reset','--mixed','HEAD'],['diff','--cached','--name-only','-z'],['rev-parse','HEAD'],['push','origin','HEAD:refs/heads/'+self.branch],['-c','user.name='+self.profile.author_name,'-c','user.email='+self.profile.author_email,'-c','commit.gpgsign=false','commit','-m','Propose '+self.scope+' operational update']]
            def selected(value):
                p=PurePosixPath(value)
                return not p.is_absolute() and '..' not in p.parts and str(p)==value and any(value.startswith(v) if v.endswith('/') else value==v for v in SCOPES[self.scope])
            add=args[:2]==['add','--'] and len(args)>2 and all(selected(v) for v in args[2:])
            if exists:
                if values!=unchecked or not selected(args[2][5:]):raise InputAdmissionError('publisher_original_exists_required')
                return {'kind':'git','original_arguments':command,'cwd':self.source,'text':False,'check':False,'input':None,'source_root':self.source}
            if values!=checked or args not in fixed and not add:raise InputAdmissionError('publisher_original_Git_operation_required')
            return {'kind':'git','original_arguments':command,'cwd':self.source,'text':True,'check':True,'input':None,'source_root':self.source}
        if command[0]!='gh' or set(options)!={'input','text','capture_output','check'} or any(options[k] is not True for k in ('text','capture_output','check')) or type(options['input']) is not str or len(options['input'].encode('utf-8'))>1024**2 or len(command)!=7 or command[:4]!=['gh','api','--method','POST'] or command[5:]!=['--input','-']:raise InputAdmissionError('publisher_original_POST_operation_required')
        payload=json.loads(options['input']);endpoint=command[4]
        if endpoint==self.profile.pulls_endpoint(self.repository):
            if type(payload) is not dict or set(payload)!={'title','head','base','body'} or payload['head']!=self.branch or payload['base']!='main':raise InputAdmissionError('publisher_original_review_target_required')
        elif endpoint in [self.profile.workflow_endpoint(self.repository,w) for w in self.profile.check_workflows]:
            if payload!={'ref':self.branch}:raise InputAdmissionError('publisher_original_dispatch_target_required')
        else:raise InputAdmissionError('publisher_original_POST_target_required')
        return {'kind':'post','original_arguments':command,'cwd':None,'text':True,'check':True,'input':options['input'],'source_root':self.source}
    def actual_arguments(self,spec,selected):
        return [selected or spec['original_arguments'][0],*(GIT_SAFETY if spec['kind']=='git' else []),*spec['original_arguments'][1:]]

    def validate_binding(self,spec,remote,native_cwd):
        from lib.requirement_validation_replay import IntegrityError
        if native_cwd!=(self.source if spec['kind']=='git' else self.cwd):raise IntegrityError('publisher_native_working_directory_changed')
        if remote is None:
            if spec['kind']=='post' or spec['original_arguments'][1] in ('fetch','switch','reset','add','push','-c'):raise IntegrityError('publisher_write_remote_binding_missing')
            return
        if type(remote) is not dict or set(remote)!={'pull_url','push_url','local_test_origin'} or type(remote['local_test_origin']) is not bool or remote['local_test_origin']!=(self.local_origin_root is not None):raise IntegrityError('publisher_remote_profile_changed')
        def valid(url):
            if type(url) is not str or not url or len(url)>8192:return False
            if self.local_origin_root is not None:
                p=PurePosixPath(url);base=PurePosixPath(self.local_origin_root)
                return p.is_absolute() and str(p)==url and '..' not in p.parts and p.is_relative_to(base)
            normalized=url.removesuffix('.git')
            if normalized.startswith('git@github.com:'):return normalized.removeprefix('git@github.com:').lower()==self.repository.lower()
            parts=urlsplit(normalized)
            return parts.hostname=='github.com' and parts.query==parts.fragment=='' and parts.path.removeprefix('/').lower()==self.repository.lower() and ((parts.scheme=='https' and parts.username is None and parts.password is None and parts.port in (None,443)) or (parts.scheme=='ssh' and parts.username=='git' and parts.password is None and parts.port in (None,22)))
        if not all(valid(remote[key]) for key in ('pull_url','push_url')):raise IntegrityError('publisher_remote_target_changed')

    def validate_program(self,program):
        from lib.requirement_validation_replay import IntegrityError
        if program is not None and self.private_state_label is not None and type(program) is dict and type(program.get('resolved')) is str and PurePosixPath(program['resolved']).is_relative_to(PurePosixPath(self.private_state_label)):raise IntegrityError('publisher_private_program_not_admitted')
