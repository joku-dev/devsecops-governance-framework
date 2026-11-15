"""Explicit SCM publication for Workbench packets; no implicit CLI identity."""
from pathlib import Path, PurePosixPath
import json
import re
import yaml
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib.private_credentials import check_private_file
from lib.provider_errors import AccessFailure
from lib.portable.contracts import endpoint, repository_key
from lib.portable_intake.bundle import timestamp
from lib.portable.runtime import read_json
from lib.providers.discovery import validate_api_endpoint
from lib.providers.operations import SCM, Writer, GitWorkspace, branch
from lib.providers.transports import Reader

REGISTER = 'model/documents/source-document-register.yaml'


def packet_path(name, kind):
    path=PurePosixPath(name)
    if (str(path)!=name or path.is_absolute() or '..' in path.parts or '\\' in name
            or ':' in name or any(ord(c)<32 for c in name)):
        return False
    return (name.startswith('docs/governance/change-requests/') and path.suffix=='.md'
            or kind=='source_candidate' and name==REGISTER
            or kind in ('source_candidate','source_review')
                and name.startswith('docs/governance/source-documents/'))


class PacketWorkspace(GitWorkspace):
    def commit_packet(self, files, kind, *, at, draft_id):
        if not self.prepared:raise ValueError('fresh_private_workspace_required')
        if (kind not in ('source_candidate','source_review','review_package')
                or not isinstance(files,dict) or not 1<=len(files)<=50
                or any(not packet_path(name,kind) or not isinstance(data,bytes)
                       or len(data)>8*1024**2 for name,data in files.items())):
            raise ValueError('workbench_publication_scope_violation')
        gcr='docs/governance/change-requests/GCR-WB-'+draft_id+'.md'
        if (not re.fullmatch('[a-f0-9]{32}',draft_id) or gcr not in files
                or any(name.startswith('docs/governance/change-requests/') and name!=gcr for name in files)
                or (self.root/gcr).exists()):
            raise ValueError('workbench_change_proposal_identity_mismatch')
        sources=[name for name in files if name.startswith('docs/governance/source-documents/')]
        if kind=='source_candidate':
            if len(sources)!=1 or REGISTER not in files or (self.root/sources[0]).exists():
                raise ValueError('workbench_candidate_source_mismatch')
            before=yaml.safe_load((self.root/REGISTER).read_bytes())
            after=yaml.safe_load(files[REGISTER])
            old=before.pop('documents');new=after.pop('documents')
            if (before!=after or not isinstance(new,list) or len(new)!=len(old)+1 or new[:-1]!=old
                    or new[-1].get('status')!='candidate' or new[-1].get('source_path')!=sources[0]
                    or new[-1].get('id') in {row['id'] for row in old}):
                raise ValueError('workbench_candidate_register_mismatch')
        elif kind=='source_review':
            if len(sources)!=1 or (self.root/sources[0]).read_bytes()!=files[sources[0]]:
                raise ValueError('workbench_review_cannot_rewrite_source')
        for name,data in files.items():
            path=self.root/name
            if path.is_symlink() or any(p.is_symlink() for p in path.parents):
                raise ValueError('unsafe_workbench_publication_path')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        self.git('add','--',*files)
        # Git filters must not rewrite candidate source bytes after review.
        for name,data in files.items():
            if self.git('show',':'+name,binary=True)!=data:
                raise ValueError('workbench_git_filter_changed_bytes')
        self.git('-c','user.name=AXIOM Workbench','-c','user.email=axiom-workbench@localhost',
                 '-c','commit.gpgsign=false','commit','-q','-m','Prepare Workbench candidate proposals',
                 stamp=timestamp(at).isoformat())
        return self.git('rev-parse','HEAD')

    def push_packet(self, source, sha):
        if (not self.prepared or not re.fullmatch(r'workbench/intake-[a-f0-9]{32}',source)
                or not re.fullmatch('[a-f0-9]{40}',sha)):
            raise ValueError('workbench_proposal_branch_required')
        self.git('push','origin',sha+':refs/heads/'+source,publishing=True)


class WorkbenchPublication:
    """Separate read/API/Git credentials; exact repository and target binding."""
    @classmethod
    def from_file(cls, path):
        check_private_file(path)
        value=read_json(path)
        return cls(value)

    def __init__(self, profile):
        schema=Path(__file__).resolve().parents[3]/'schemas/workbench-publication-v2.schema.json'
        try:Draft202012Validator(json.loads(schema.read_text()),format_checker=FormatChecker()).validate(profile)
        except ValidationError:raise ValueError('invalid_workbench_publication_profile') from None
        expected={'schema_version','scm','api_url','remote','target','git_username',
                  'reader_credential','publisher_credential','git_reader_credential','git_publisher_credential'}
        if set(profile)!=expected or profile['schema_version']!=2:
            raise ValueError('invalid_workbench_publication_profile')
        repository_key(profile['scm']);branch(profile['target'])
        SCM(profile['scm'],None)  # Validate supported native identity before admitting the profile.
        validate_api_endpoint(profile['api_url'],profile['scm']['instance'])
        # API exceptions do not permit a Git credential to cross the SCM origin.
        from urllib.parse import urlsplit
        remote=urlsplit(profile['remote'])
        if (remote.scheme!='https' or remote.username or remote.password or remote.query or remote.fragment
                or endpoint('https://'+remote.netloc)!=endpoint(profile['scm']['instance'])):
            raise ValueError('unsafe_workbench_git_remote')
        self.profile=profile

    def token(self, field):
        path=Path(self.profile[field]);check_private_file(path)
        value=path.read_text().strip()
        if not value or any(ord(c)<32 for c in value):raise ValueError('invalid_workbench_credential')
        return value

    def publish(self, *, root, destination, draft_id, context, files, kind, at, local_run):
        profile=self.profile
        if local_run(['git','status','--porcelain','--untracked-files=no'],root):
            raise ValueError('PR publication requires a clean tracked checkout')
        scm=SCM(profile['scm'],Reader(profile['api_url'],self.token('reader_credential')),
                Writer(profile['api_url'],self.token('publisher_credential')))
        scm.check_identity()
        if scm.branch_sha(profile['target'])!=context['commit']:
            raise ValueError('Remote default branch differs from this draft. Prepare a fresh package.')
        scm.require_clone_remote(profile['remote'])
        source='workbench/intake-'+draft_id
        # A prior attempt must be reconciled, including a lost API mutation reply.
        matches=scm.changes(source,profile['target'])
        if matches:
            if len(matches)!=1:raise ValueError('workbench_proposal_identity_conflict')
            raise ValueError('Prior Workbench proposal exists; reconcile before publishing again')
        workspace=PacketWorkspace(destination,profile['remote'],self.token('git_reader_credential'),
                                  profile['git_username'],publisher_token=self.token('git_publisher_credential'))
        workspace.prepare(context['commit'])
        selected={name:data for name,data in files.items() if name not in ('workbench-package.json','README.txt')}
        sha=workspace.commit_packet(selected,kind,at=at,draft_id=draft_id)
        workspace.push_packet(source,sha)
        # All providers receive a draft proposal, never a merge/approval request.
        result=scm.propose(source,profile['target'],sha,'Workbench: candidate intake and review preparation',
            'Human review required. Report-only proposals; no source promotion, semantic execution or baseline release.',draft=True)
        return {'url':result['url'],'branch':source,'commit':sha,
                'provider':profile['scm']['provider'],'instance':profile['scm']['instance'],'id':result['id']}
