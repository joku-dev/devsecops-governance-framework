"""SCM proposals, CI dispatch and local Git are separate provider boundaries."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, build_opener

from lib.provider_errors import AccessFailure
from lib.providers.context import NoRedirect
from lib.portable.contracts import endpoint, repository_key, valid_id
from lib.secure_http import read_limited, require_https
from lib.providers.transports import Reader, encoded


def branch(value):
    if (not isinstance(value,str) or not value or value.startswith('/') or value.endswith(('/','.','.lock'))
            or '..' in value or '//' in value or '@{' in value or value=='@'
            or any(ord(c)<33 or c in '~^:?*[\\' for c in value)
            or any(part.startswith('.') for part in value.split('/'))):
        raise ValueError('invalid_git_branch')
    return value


class Writer(Reader):
    """A separate credential/client: failed mutations are reconciled, never blindly retried."""
    def post(self,path,payload):
        return self._post(path,json.dumps(payload).encode(),'application/json')

    def post_form(self,path,payload):
        return self._post(path,urlencode(payload).encode(),'application/x-www-form-urlencoded')

    def _post(self,path,data,content_type):
        try:
            request=Request(self.url(path),data=data,
                            headers={**self.headers,'Content-Type':content_type},method='POST')
            with build_opener(NoRedirect).open(request,timeout=30) as response:
                return json.loads(read_limited(response,max_bytes=4*1024**2) or b'{}')
        except HTTPError as error:
            raise AccessFailure('mutation_http_'+str(error.code)) from None
        except (URLError,TimeoutError,OSError,ValueError):
            raise AccessFailure('mutation_outcome_unknown') from None


class SCM:
    def __init__(self,profile,reader,writer=None):
        repository_key(profile)
        self.profile,self.reader,self.writer=profile,reader,writer
        self.provider=profile['provider']
        parts=profile['path'].split('/')
        if self.provider=='github' and len(parts)==2:
            self.route='/repos/'+'/'.join(encoded(p) for p in parts)
        elif self.provider=='gitlab':
            self.route='/projects/'+encoded(profile['native_id'])
        elif self.provider=='bitbucket-dc' and len(parts)==2:
            self.route='/rest/api/latest/projects/'+encoded(parts[0])+'/repos/'+encoded(parts[1])
        else:
            raise ValueError('unsupported_scm_proposal_profile')

    def check_identity(self):
        data=self.reader.get(self.route)
        path=data.get('full_name') if self.provider=='github' else data.get('path_with_namespace') if self.provider=='gitlab' else data.get('project',{}).get('key','')+'/'+data.get('slug','')
        if str(data['id'])!=self.profile['native_id'] or path!=self.profile['path']:
            raise ValueError('proposal_repository_mismatch')
        self.repository=data

    def require_clone_remote(self, remote):
        """A same-origin URL alone does not identify the authorized repository."""
        if not hasattr(self,'repository'):self.check_identity()
        data=self.repository
        if self.provider=='github':urls=[data.get('clone_url')]
        elif self.provider=='gitlab':urls=[data.get('http_url_to_repo')]
        else:urls=[row.get('href') for row in data.get('links',{}).get('clone',[])]
        require_https(remote)
        requested=urlsplit(remote)
        if requested.query or requested.fragment:raise ValueError('unsafe_native_clone_url')
        allowed=[]
        for url in urls:
            if not isinstance(url,str):continue
            parsed=urlsplit(url)
            if (parsed.scheme=='https' and not parsed.username and not parsed.password
                    and not parsed.query and not parsed.fragment
                    and endpoint('https://'+parsed.netloc)==endpoint(self.profile['instance'])):
                allowed.append(url.rstrip('/').removesuffix('.git'))
        if remote.rstrip('/').removesuffix('.git') not in allowed:
            raise ValueError('native_clone_repository_mismatch')

    def branch_sha(self,name):
        name=branch(name)
        if self.provider=='github':return self.reader.get(self.route+'/git/ref/heads/'+encoded(name))['object']['sha']
        if self.provider=='gitlab':return self.reader.get(self.route+'/repository/branches/'+encoded(name))['commit']['id']
        values=self.reader.get(self.route+'/branches?'+urlencode({'filterText':name,'limit':100}))['values']
        matches=[row for row in values if row['id']=='refs/heads/'+name]
        if len(matches)!=1:raise ValueError('branch_resolution_ambiguous')
        return matches[0]['latestCommit']

    def changes(self,source=None,target=None,*,prefixes=None):
        """Include closed changes so a consciously declined proposal is never reopened."""
        if source is not None:branch(source)
        if target is not None:branch(target)
        if self.provider=='github':
            query={'state':'all'}
            if source:query['head']=self.profile['path'].split('/')[0]+':'+source
            if target:query['base']=target
            rows=self.reader.pages(self.route+'/pulls?'+urlencode(query))
        elif self.provider=='gitlab':
            query={'scope':'all','state':'all'}
            if source:query['source_branch']=source
            if target:query['target_branch']=target
            rows=self.reader.pages(self.route+'/merge_requests?'+urlencode(query))
        else:
            rows=[];start=0
            while True:
                data=self.reader.get(self.route+'/pull-requests?'+urlencode({'state':'ALL','limit':100,'start':start}))
                rows.extend(data['values'])
                if data['isLastPage'] is True:break
                following=data['nextPageStart']
                if type(following) is not int or following<=start or following>10000:
                    raise ValueError('proposal_pagination_invalid')
                start=following
        selected=[]
        for row in rows:
            native_source=row['head']['ref'] if self.provider=='github' else row['source_branch'] if self.provider=='gitlab' else row['fromRef']['id'].removeprefix('refs/heads/')
            native_target=row['base']['ref'] if self.provider=='github' else row['target_branch'] if self.provider=='gitlab' else row['toRef']['id'].removeprefix('refs/heads/')
            if ((source is None or native_source==source) and (target is None or native_target==target)
                    and (prefixes is None or native_source.startswith(prefixes))):
                selected.append(row)
        normalized=[self.normalize(row) for row in selected]
        return [row for row in normalized if (source is None or row['source']==source) and (target is None or row['target']==target)]

    def normalize(self,data):
        result=self._normalize(data)
        if not valid_id(result['id']) or not re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}',result['sha']):
            raise ValueError('invalid_native_proposal_identity')
        branch(result['source']);branch(result['target'])
        return result

    def _normalize(self,data):
        if self.provider=='github':url=data['html_url']
        elif self.provider=='gitlab':url=data['web_url']
        else:
            links=data.get('links',{}).get('self',[])
            if len(links)!=1:raise ValueError('proposal_url_ambiguous')
            url=links[0]['href']
        parsed=urlsplit(url)
        require_https(url)
        if parsed.query or parsed.fragment or endpoint('https://'+parsed.netloc)!=endpoint(self.profile['instance']):
            raise ValueError('unsafe_native_proposal_url')
        if self.provider=='github':
            if any(str(data[side]['repo']['id'])!=self.profile['native_id'] for side in ('head','base')):
                raise ValueError('cross_repository_proposal_not_supported')
            return {'id':str(data['number']),'state':'merged' if data.get('merged_at') else 'open' if data['state']=='open' else 'closed',
                    'url':data['html_url'],'source':data['head']['ref'],'target':data['base']['ref'],'sha':data['head']['sha']}
        if self.provider=='gitlab':
            if any(str(data[name])!=self.profile['native_id'] for name in ('source_project_id','target_project_id')):
                raise ValueError('cross_repository_proposal_not_supported')
            return {'id':str(data['iid']),'state':{'opened':'open','locked':'open','merged':'merged','closed':'closed'}[data['state']],
                    'url':data['web_url'],'source':data['source_branch'],'target':data['target_branch'],'sha':data['sha']}
        links=data.get('links',{}).get('self',[])
        if any(str(data[side]['repository']['id'])!=self.profile['native_id'] for side in ('fromRef','toRef')):
            raise ValueError('cross_repository_proposal_not_supported')
        return {'id':str(data['id']),'state':{'OPEN':'open','MERGED':'merged','DECLINED':'closed'}[data['state']],
                'url':links[0]['href'] if len(links)==1 else None,
                'source':data['fromRef']['id'].removeprefix('refs/heads/'),
                'target':data['toRef']['id'].removeprefix('refs/heads/'),'sha':data['fromRef']['latestCommit']}

    def propose(self,source,target,sha,title,body,*,draft=False):
        if not self.writer:raise ValueError('separate_publisher_credential_required')
        if not isinstance(sha,str) or not re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}',sha):
            raise ValueError('immutable_proposal_sha_required')
        source,target=branch(source),branch(target)
        self.check_identity()
        matches=self.changes(source,target)
        if matches:
            if len(matches)!=1 or matches[0]['sha']!=sha:raise ValueError('proposal_identity_conflict')
            return matches[0]  # Closed/merged stays terminal; no reopen or recreate.
        if self.branch_sha(source)!=sha:raise ValueError('proposal_branch_changed')
        if self.provider=='github':
            payload={'head':source,'base':target,'title':title,'body':body}
            if draft:payload['draft']=True
            value=self.writer.post(self.route+'/pulls',payload)
        elif self.provider=='gitlab':
            value=self.writer.post(self.route+'/merge_requests',{'source_branch':source,'target_branch':target,
                'title':('Draft: '+title if draft else title),'description':body,'remove_source_branch':False})
        else:
            project,slug=self.profile['path'].split('/')
            repository={'slug':slug,'project':{'key':project}}
            payload={'title':title,'description':body,
                'fromRef':{'id':'refs/heads/'+source,'repository':repository},
                'toRef':{'id':'refs/heads/'+target,'repository':repository}}
            if draft:payload['draft']=True
            value=self.writer.post(self.route+'/pull-requests',payload)
        if draft:
            confirmed=(value.get('draft') is True or self.provider=='gitlab'
                       and (value.get('work_in_progress') is True or str(value.get('title','')).startswith('Draft: ')))
            if not confirmed:raise AccessFailure('native_draft_not_confirmed')
        result=self.normalize(value)
        if (result['source'],result['target'],result['sha'])!=(source,target,sha):
            raise ValueError('created_proposal_binding_mismatch')
        return result


def dispatch_ci(profile,writer,*,ref,inputs=None):
    """Explicit dispatch boundary; discovery and shadow collection never call this."""
    branch(ref)
    provider=profile['provider'];native=encoded(profile['native_id'])
    if provider=='github-actions':
        repository='/'.join(encoded(p) for p in profile['repository_path'].split('/'))
        return writer.post('/repos/'+repository+'/actions/workflows/'+native+'/dispatches',{'ref':ref,'inputs':inputs or {}})
    if provider=='gitlab-ci':
        return writer.post('/projects/'+native+'/pipeline',{'ref':ref,'variables':[
            {'key':key,'value':value,'variable_type':'env_var'} for key,value in (inputs or {}).items()]})
    if provider=='bamboo':
        if inputs:raise ValueError('bamboo_variable_dispatch_profile_not_supported')
        if profile.get('native_branch')!=ref:raise ValueError('bamboo_native_plan_branch_binding_required')
        return writer.post_form('/rest/api/latest/queue/'+native,{})
    raise ValueError('unsupported_ci_dispatch_profile')


def run_link(context):
    ci=context['ci'];origin=endpoint(ci['instance'])
    if ci['provider']=='github-actions':
        path='/'.join(quote(p,safe='') for p in context['scm']['path'].split('/'))
        return origin+'/'+path+'/actions/runs/'+encoded(ci['run_id'])+'/attempts/'+str(ci['attempt'])
    if ci['provider']=='gitlab-ci':
        path='/'.join(quote(p,safe='') for p in context['scm']['path'].split('/'))
        return origin+'/'+path+'/-/pipelines/'+encoded(ci['run_id'])
    if ci['provider']=='bamboo':return origin+'/browse/'+encoded(ci['run_id'])
    raise ValueError('unsupported_ci_link_profile')


def application_fingerprints(root):
    """New VM dependency closure includes config and IaC; legacy closure is unchanged."""
    from lib.application_source import fingerprints
    root=Path(root)
    if (root/'config/axiom-v2-distribution.json').is_file():
        from lib.v2_source import active_fingerprints
        return active_fingerprints(root)
    result=fingerprints(root)
    for directory in ('config','infra'):
        for path in sorted((root/directory).rglob('*')):
            if path.is_file():
                if path.is_symlink():raise ValueError('unsafe_application_dependency')
                result[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted((root/'.github').rglob('*')):
        if path.is_file():
            if path.is_symlink():raise ValueError('unsafe_application_dependency')
            result[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ('.gitattributes','.gitmodules','pyproject.toml','setup.cfg','.python-version'):
        path=root/name
        if path.exists():
            if path.is_symlink():raise ValueError('unsafe_application_dependency')
            result[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def require_compatible(installed,candidate):
    if (Path(installed)/'config/axiom-v2-distribution.json').is_file() and not (Path(candidate)/'config/axiom-v2-distribution.json').is_file():
        raise AccessFailure('application_update_required')
    if application_fingerprints(installed)!=application_fingerprints(candidate):
        raise AccessFailure('application_update_required')


class GitWorkspace:
    """Private disposable checkout, bounded explicit status paths and immutable commits."""
    def __init__(self,root,remote,token='',username='',*,publisher_token=None):
        require_https(remote)
        parsed=urlsplit(remote)
        if parsed.query or parsed.fragment or any(ord(c)<32 for c in username):raise ValueError('unsafe_git_remote')
        self.root,self.remote,self.token,self.username=Path(root).resolve(),remote,token,username
        self.publisher_token=publisher_token
        self.prepared=False

    def git(self,*arguments,stamp=None,trim=True,publishing=False,binary=False):
        env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GIT_CONFIG_COUNT':'4',
             'GIT_ASKPASS':'/bin/false','SSH_ASKPASS':'/bin/false',
             'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1',
             'GIT_CONFIG_KEY_0':'credential.helper','GIT_CONFIG_VALUE_0':'',
             'GIT_CONFIG_KEY_1':'credential.useHttpPath','GIT_CONFIG_VALUE_1':'true',
             'GIT_CONFIG_KEY_2':'http.followRedirects','GIT_CONFIG_VALUE_2':'false',
             'GIT_CONFIG_KEY_3':'core.hooksPath','GIT_CONFIG_VALUE_3':'/dev/null'}
        env.pop('GIT_CONFIG_PARAMETERS',None)
        env.pop('GIT_CONFIG',None)
        env.pop('GIT_TEMPLATE_DIR',None)
        env.pop('GIT_CURL_VERBOSE',None)
        for key in list(env):
            if key.startswith('GIT_TRACE'):env.pop(key)
        if stamp:
            env.update(GIT_AUTHOR_DATE=stamp,GIT_COMMITTER_DATE=stamp,
                GIT_AUTHOR_NAME='AXIOM evidence proposal',GIT_COMMITTER_NAME='AXIOM evidence proposal',
                GIT_AUTHOR_EMAIL='axiom-proposal@localhost',GIT_COMMITTER_EMAIL='axiom-proposal@localhost')
        token=self.publisher_token if publishing and self.publisher_token is not None else self.token
        if token:
            env.update(AXIOM_GIT_TOKEN=token,AXIOM_GIT_USERNAME=self.username,GIT_CONFIG_COUNT='5',
                GIT_CONFIG_KEY_4='credential.helper',GIT_CONFIG_VALUE_4='!f() { printf "username=%s\\npassword=%s\\n" "$AXIOM_GIT_USERNAME" "$AXIOM_GIT_TOKEN"; }; f')
        try:
            process=subprocess.run(['git',*arguments],cwd=self.root,env=env,capture_output=True,timeout=300,check=False)
        except subprocess.TimeoutExpired:raise AccessFailure('git_operation_timeout') from None
        if process.returncode:raise AccessFailure('git_operation_failed')
        if binary:return process.stdout
        output=process.stdout.decode()
        return output.strip() if trim else output

    def prepare(self,base):
        if not re.fullmatch('[a-f0-9]{40}',base):raise ValueError('immutable_git_base_required')
        self.root.mkdir(mode=0o700,parents=True,exist_ok=False)
        self.git('init','--template=','-q');self.git('remote','add','origin',self.remote)
        self.git('fetch','--depth=1','origin',base);self.git('checkout','--detach','-q',base)
        if self.git('rev-parse','HEAD')!=base:raise ValueError('git_checkout_mismatch')
        self.prepared=True

    def commit(self,files,message,*,at):
        from lib.portable_intake.bundle import timestamp
        stamp=timestamp(at).isoformat()
        if not self.prepared:raise ValueError('fresh_private_workspace_required')
        if (not isinstance(files,dict) or not 1<=len(files)<=25
                or any(not isinstance(text,str) or len(text.encode())>4*1024**2 for text in files.values())):
            raise ValueError('portable_batch_size_limit')
        for relative,content in files.items():
            if not re.fullmatch(r'status/portable/v2/candidates/[a-f0-9]{64}/[a-f0-9]{64}\.json',relative):
                raise ValueError('portable_publication_scope_violation')
            path=self.root/relative
            if path.exists() or path.is_symlink():raise ValueError('immutable_candidate_already_exists')
            if any(p.is_symlink() for p in path.parents):raise ValueError('unsafe_candidate_path')
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content)
        self.git('add','--',*files)
        for relative,content in files.items():
            if self.git('show',':'+relative,trim=False)!=content:raise ValueError('candidate_git_filter_changed_bytes')
        self.git('-c','user.name=AXIOM evidence proposal','-c','user.email=axiom-proposal@localhost',
                 '-c','commit.gpgsign=false','commit','-q','-m',message,stamp=stamp)
        return self.git('rev-parse','HEAD')

    def push(self,source,sha):
        if not self.prepared:raise ValueError('fresh_private_workspace_required')
        branch(source)
        if not re.fullmatch(r'automation/portable-consumer/[a-f0-9]{24}',source):
            raise ValueError('portable_publication_branch_required')
        if not re.fullmatch('[a-f0-9]{40}',sha):raise ValueError('immutable_proposal_commit_required')
        self.git('push','origin',sha+':refs/heads/'+source,publishing=True)  # No force or main update.
