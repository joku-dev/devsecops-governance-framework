"""Read-only native acquisition. Provider responses never enter the common evaluator."""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import zipfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request

from lib.consumer_github import AccessFailure, retry_delay
from lib.portable.adapters import NoRedirect
from lib.portable.contracts import canonical_digest, endpoint, repository_key
from lib.secure_http import download_https, read_limited, require_https
from urllib.request import build_opener
from .bundle import timestamp


def encoded(value):
    return quote(str(value), safe='')


class Reader:
    """Configured endpoint, bounded requests, redacted failures, no credential redirects."""
    def __init__(self, base, token='', *, budget=100):
        require_https(base)
        parsed = urlsplit(base)
        if parsed.query or parsed.fragment:
            raise ValueError('invalid_reader_endpoint')
        self.base, self.token, self.budget, self.calls = base.rstrip('/'), token, budget, 0

    def url(self, path):
        if not path.startswith('/') or path.startswith('//') or '\\' in path or any(ord(c)<32 for c in path):
            raise ValueError('invalid_reader_path')
        if self.calls >= self.budget:
            raise AccessFailure('request_budget_exhausted', True)
        self.calls += 1
        return self.base + path

    @property
    def headers(self):
        return {'Accept':'application/json', 'User-Agent':'axiom-evidence-intake/2',
                **({'Authorization':'Bearer ' + self.token} if self.token else {})}

    def get(self, path):
        try:
            with build_opener(NoRedirect).open(Request(self.url(path), headers=self.headers), timeout=30) as response:
                return json.loads(read_limited(response, max_bytes=4*1024**2))
        except HTTPError as error:
            rate = error.code == 429 or (error.code == 403 and (error.headers.get('Retry-After') or error.headers.get('X-RateLimit-Remaining')=='0'))
            raise AccessFailure('rate_limited' if rate else 'http_' + str(error.code),
                                bool(rate or error.code >= 500), retry_delay(error.headers)) from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise AccessFailure('provider_read_failed', True) from None

    def download(self, path, destination):
        # Only API-selected relative paths on this configured origin receive credentials.
        try:
            download_https(self.url(path), Path(destination), headers=self.headers, max_bytes=512*1024**2)
        except HTTPError as error:
            raise AccessFailure('artifact_http_' + str(error.code), error.code==429 or error.code>=500,
                                retry_delay(error.headers)) from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise AccessFailure('artifact_download_failed', True) from None

    def pages(self, path, field=None, limit=25):
        for page in range(1, limit+1):
            data = self.get(path + ('&' if '?' in path else '?') + f'per_page=100&page={page}')
            rows = data[field] if field else data
            if not isinstance(rows, list):
                raise ValueError('invalid_provider_page')
            yield from rows
            if len(rows) < 100:
                return
        raise AccessFailure('provider_pagination_limit')


@dataclass(frozen=True)
class Observation:
    """Collector-owned native capture; deliberately no deserializer from bundle JSON."""
    kind: str
    identity: dict
    revision: str
    native_artifact_id: str
    archive_digest: str
    acquired_at: str
    producer_config_digest: str | None
    attempt_bound: bool
    raw_digest: str
    bundle_digest: str
    started_at: str | None
    completed_at: str | None
    scm_facts_digest: str | None

    def checks(self, context, manifest, policy, at, generated_at):
        identity = {'repository':repository_key(context['scm']), 'provider':context['ci']['provider'],
                    'instance':endpoint(context['ci']['instance']), 'run_id':context['ci']['run_id'],
                    'job_id':context['ci']['job_id'], 'attempt':context['ci']['attempt']}
        config = self.producer_config_digest is not None and self.producer_config_digest == policy.get('producer_config_sha256')
        facts_digest=canonical_digest({name:fact['value'] if fact['status']=='available' else None
                                      for name,fact in context['capabilities'].items()})
        bound = (self.identity == identity and self.attempt_bound and config
                 and self.scm_facts_digest==facts_digest
                 and self.bundle_digest == canonical_digest(manifest))
        native_fresh = False
        if self.started_at and self.completed_at:
            created, start, end = map(timestamp,(generated_at,self.started_at,self.completed_at))
            native_fresh = (start <= created <= end and 0 <= (at-end).total_seconds() <= policy['max_age_seconds'])
        custody = (0 <= (at-timestamp(self.acquired_at)).total_seconds() <= policy['max_age_seconds']
                   and bool(self.native_artifact_id) and len(self.archive_digest)==64 and len(self.raw_digest)==64)
        return {'producer_run_resolved':bound, 'commit_matches_run':bound and self.revision==context['revision']['tested'],
                'artifact_belongs_to_run':bound, 'custody_recorded':custody,
                'freshness_evaluated':native_fresh}


def capture(context, policy, reader, archive, *, at, audit_sink=None, scm_reader=None):
    """Acquire one exact completed native run/job, including failed governance runs.

    All identifiers come from the requested context but are checked against API responses.
    The trusted profile fixes workflow/job/artifact/configuration. No latest-success lookup.
    """
    from .bundle import validate_policy
    from lib.portable.contracts import context_errors
    validate_policy(policy)
    if (context_errors(context) or repository_key(context['scm'])!=repository_key(policy['scm'])
            or context['scm']['path']!=policy['scm']['path'] or context['ci']['provider']!=policy['ci']['provider']
            or endpoint(context['ci']['instance'])!=endpoint(policy['ci']['instance'])):
        raise ValueError('requested_context_outside_intake_policy')
    ci, scm = context['ci'], context['scm']
    transport = policy['transport']
    if endpoint(ci['instance']) != endpoint(transport['instance']):
        raise ValueError('transport_instance_mismatch')
    provider = ci['provider']
    audit = [] if audit_sink is None else audit_sink

    def get(path):
        data = reader.get(path)
        audit.append({'path':path, 'response':data})
        return data

    config_digest = None
    attempt_bound = False
    started_at = completed_at = None
    if provider == 'github-actions':
        if scm['provider'] != 'github' or endpoint(scm['instance']) != endpoint(ci['instance']):
            raise ValueError('unsupported_github_scm_composition')
        route = '/repos/' + '/'.join(encoded(p) for p in scm['path'].split('/'))
        repo = get(route)
        run = get(route + '/actions/runs/' + encoded(ci['run_id']) + '/attempts/' + str(ci['attempt']))
        if (str(repo['id']) != scm['native_id'] or repo['full_name'] != scm['path'] or str(run['id']) != ci['run_id']
                or run['run_attempt'] != ci['attempt'] or run['status'] != 'completed'
                or str(run['repository']['id']) != scm['native_id']
                or run['path'].split('@')[0] != transport['workflow_path']):
            raise ValueError('native_run_binding_mismatch')
        jobs = list(reader.pages(route + '/actions/runs/' + encoded(ci['run_id']) + '/attempts/' + str(ci['attempt']) + '/jobs', 'jobs'))
        audit.append({'jobs':jobs})
        matches = [job for job in jobs if job['name'] == transport['job_name']]
        if len(matches) != 1 or matches[0]['status'] != 'completed' or ci['job_id'] != transport['logical_job_id']:
            raise ValueError('native_job_binding_mismatch')
        job = matches[0]
        started_at,completed_at = job['started_at'],job['completed_at']
        uploads = [step for step in job.get('steps',[]) if step['name']==transport['upload_step_name']]
        if len(uploads)!=1 or uploads[0].get('conclusion')!='success':
            raise ValueError('native_artifact_upload_not_successful')
        artifacts = list(reader.pages(route + '/actions/runs/' + encoded(ci['run_id']) + '/artifacts', 'artifacts'))
        audit.append({'artifacts':artifacts})
        found = [a for a in artifacts if a['name']==transport['artifact_name'] and not a['expired']
                 and timestamp(job['started_at']) <= timestamp(a['created_at']) <= timestamp(job['completed_at'])]
        if len(found) != 1:
            raise ValueError('ambiguous_native_artifact')
        artifact = found[0]
        if (str(artifact['workflow_run']['id']) != ci['run_id']
                or str(artifact['workflow_run']['repository_id']) != scm['native_id']
                or artifact['workflow_run']['head_sha'] != run['head_sha']):
            raise ValueError('native_artifact_binding_mismatch')
        reader.download(route + '/actions/artifacts/' + encoded(artifact['id']) + '/zip', archive)
        digest = hashlib.sha256(Path(archive).read_bytes()).hexdigest()
        if artifact.get('digest') != 'sha256:' + digest:
            raise ValueError('native_archive_digest_mismatch')
        config = get(route + '/contents/' + '/'.join(encoded(p) for p in transport['workflow_path'].split('/')) + '?ref=' + encoded(run['head_sha']))
        config_digest = hashlib.sha256(base64.b64decode(config['content'])).hexdigest()
        revision, artifact_id, attempt_bound = run['head_sha'], str(artifact['id']), True
        # A workflow-run head SHA does not independently prove a PR merge checkout.
        # Branch provenance is supported here; merge/head event closure remains explicit.
        event={'push':'push','workflow_dispatch':'manual','schedule':'schedule','pull_request':'pull_request'}.get(run['event'],'unknown')
        attempt_bound = (context['revision']['mode']=='branch' and event==context['ci']['event']
                         and run['head_branch']==context['revision']['branch'])
    elif provider == 'gitlab-ci':
        if scm['provider'] != 'gitlab' or endpoint(scm['instance']) != endpoint(ci['instance']):
            raise ValueError('unsupported_gitlab_scm_composition')
        route = '/projects/' + encoded(scm['native_id'])
        repo = get(route)
        run = get(route + '/pipelines/' + encoded(ci['run_id']))
        job = get(route + '/jobs/' + encoded(ci['job_id']))
        if (str(repo['id']) != scm['native_id'] or repo['path_with_namespace'] != scm['path']
                or str(run['id']) != ci['run_id'] or str(run['project_id']) != scm['native_id']
                or str(job['id']) != ci['job_id'] or str(job['pipeline']['id']) != ci['run_id']
                or str(job['pipeline']['project_id']) != scm['native_id'] or job['commit']['id'] != run['sha']
                or job['name'] != transport['job_name'] or job['status'] not in ('success','failed')
                or run['status'] not in ('success','failed','canceled') or ci['attempt'] != 1):
            raise ValueError('native_run_job_binding_mismatch')
        # A retried GitLab job gets a new native job ID; attempt remains 1.
        reader.download(route + '/jobs/' + encoded(ci['job_id']) + '/artifacts', archive)
        config = get(route + '/repository/files/' + encoded(transport['configuration_path']) + '?ref=' + encoded(run['sha']))
        config_digest = hashlib.sha256(base64.b64decode(config['content'])).hexdigest()
        revision, artifact_id, attempt_bound = run['sha'], ci['job_id'], True
        event={'push':'push','merge_request_event':'pull_request','web':'manual','schedule':'schedule'}.get(run['source'],'unknown')
        attempt_bound = event==ci['event'] and job['pipeline']['sha']==run['sha']
        if context['revision']['mode']=='branch':
            attempt_bound=attempt_bound and run['ref']==context['revision']['branch']
        started_at,completed_at = job['started_at'],job['finished_at']
    elif provider == 'bamboo':
        result = get('/rest/api/latest/result/' + encoded(ci['run_id']) + '.json?expand=artifacts')
        if result['buildResultKey'] != ci['run_id'] or result['lifeCycleState'] != 'Finished':
            raise ValueError('native_bamboo_result_mismatch')
        artifacts = result.get('artifacts',{}).get('artifact',[])
        found = [a for a in artifacts if a['name']==transport['artifact_name']]
        if len(found)!=1:
            raise ValueError('ambiguous_native_artifact')
        url = found[0]['link']['href']
        parsed, base = urlsplit(url), urlsplit(reader.base)
        if (parsed.scheme,parsed.netloc) != (base.scheme,base.netloc) or parsed.query or parsed.fragment:
            raise ValueError('unsafe_native_artifact_url')
        if not parsed.path.startswith(base.path.rstrip('/') + '/'):
            raise ValueError('native_artifact_outside_instance')
        reader.download(parsed.path[len(base.path.rstrip('/')):], archive)
        revision, artifact_id = result['vcsRevisionKey'], ci['run_id'] + ':' + transport['artifact_name']
        # Bamboo SCM/job/spec closure is deliberately unresolved for unmeasured installations.
        # Bytes and native build are collected, but this profile cannot earn provenance_verified.
    else:
        raise ValueError('unsupported_native_transport')
    identity = {'repository':repository_key(scm), 'provider':provider, 'instance':endpoint(ci['instance']),
                'run_id':ci['run_id'], 'job_id':ci['job_id'], 'attempt':ci['attempt']}
    # Reacquire SCM facts independently of consumer-supplied context/input.
    # Drift or unknown effective protection prevents native candidate promotion.
    if scm_reader is None and provider in ('github-actions','gitlab-ci'):
        scm_reader=reader
    facts_digest=None
    if scm_reader is not None:
        from lib.portable.adapters import scm_facts, ProviderError
        class SCMAPI:
            def get(self,path):
                try:
                    data=scm_reader.get(path)
                    audit.append({'scm_path':path,'response':data})
                    return data
                except AccessFailure:
                    raise ProviderError('independent_scm_lookup_failed') from None
        branch=context['change_request']['target_branch'] if context['change_request'] else context['revision']['branch']
        facts=scm_facts(policy['scm'],branch,SCMAPI())
        closure=(facts.get('protected_branch',{}).get('status')=='available'
                 and facts.get('direct_push_allowed',{}).get('status')=='available'
                 and (facts['protected_branch']['value'] is False or facts.get('review_required',{}).get('status')=='available'))
        if closure:
            facts_digest=canonical_digest({name:fact['value'] if fact['status']=='available' else None for name,fact in facts.items()})
    with zipfile.ZipFile(archive) as zipped:
        prefix=transport.get('bundle_prefix','')
        if prefix and (prefix.startswith('/') or '..' in prefix.split('/') or '\\' in prefix or ':' in prefix):
            raise ValueError('unsafe_configured_bundle_prefix')
        manifest_name=prefix.rstrip('/')+'/bundle.json' if prefix else 'bundle.json'
        names=[info for info in zipped.infolist() if info.filename==manifest_name]
        if len(names)!=1 or names[0].file_size>65536:
            raise ValueError('native_bundle_manifest_missing_or_ambiguous')
        bundle_digest=canonical_digest(json.loads(zipped.read(names[0])))
    observation = Observation(provider, identity, revision, artifact_id,
                              hashlib.sha256(Path(archive).read_bytes()).hexdigest(), at,
                              config_digest, attempt_bound, canonical_digest(audit),bundle_digest,
                              started_at,completed_at,facts_digest)
    return observation, audit
