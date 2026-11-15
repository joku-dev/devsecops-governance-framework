"""CI/SCM adapters. Native facts stop at the portable context boundary."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .contracts import VERSION, endpoint, validate
from .runtime import source_digest


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ProviderError(ValueError):
    pass


class API:
    def __init__(self, base, token, provider):
        parsed = urlsplit(base)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment):
            raise ProviderError('Invalid provider API endpoint')
        self.base, self.token, self.provider = base.rstrip('/'), token, provider

    def get(self, path):
        if not path.startswith('/') or path.startswith('//') or '\\' in path:
            raise ProviderError('Invalid API path')
        headers = {'Accept': 'application/json', 'User-Agent': 'axiom-portable/' + VERSION}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        if self.provider == 'github':
            headers['X-GitHub-Api-Version'] = '2022-11-28'
        try:
            with build_opener(NoRedirect).open(Request(self.base + path, headers=headers), timeout=30) as response:
                raw = response.read(4 * 1024 * 1024 + 1)
                if len(raw) > 4 * 1024 * 1024:
                    raise ProviderError('provider_response_too_large')
                return json.loads(raw)
        except HTTPError as error:
            raise ProviderError(f'provider_http_{error.code}') from None
        except (URLError, OSError, ValueError):
            raise ProviderError('provider_request_failed') from None


def checked_out_revision(checkout):
    result = subprocess.run(['git', '-C', str(Path(checkout).resolve()), 'rev-parse', '--verify', 'HEAD'],
                            capture_output=True, text=True, timeout=15, check=False)
    if result.returncode:
        raise ValueError('checkout_revision_unavailable')
    return result.stdout.strip()


def capability(value=None, status='missing', source='not_collected'):
    return {'value': value, 'status': status, 'source': source}



def github_protection(api, route, branch):
    direct = capability(status='unsupported',source='effective_bypass_resolution_required')
    review_fact = capability()
    try:
        protection = api.get(route + '/branches/' + quote(branch,safe='') + '/protection')
        review = protection.get('required_pull_request_reviews')
        bypass = review.get('bypass_pull_request_allowances') if isinstance(review,dict) else None
        if isinstance(review,dict) and type(review.get('required_approving_review_count')) is int:
            review_fact = capability(review['required_approving_review_count']>0,'available','protection_api')
        if (isinstance(review,dict) and protection.get('enforce_admins',{}).get('enabled') is True
                and isinstance(bypass,dict) and all(bypass.get(key)==[] for key in ('users','teams','apps'))):
            return capability(False,'available','protection_no_bypass'),review_fact
    except ProviderError:
        pass
    rules = api.get(route + '/rules/branches/' + quote(branch,safe=''))
    if not isinstance(rules,list):
        raise ProviderError('invalid_branch_rules_response')
    ids = {str(row['ruleset_id']) for row in rules if row.get('type')=='pull_request'
           and row.get('ruleset_source_type')=='Repository'}
    for identity in sorted(ids):
        detail = api.get(route + '/rulesets/' + quote(identity,safe=''))
        if str(detail.get('id')) != identity or detail.get('enforcement')!='active' or detail.get('bypass_actors')!=[]:
            continue
        for rule in detail.get('rules',[]):
            count = rule.get('parameters',{}).get('required_approving_review_count')
            if rule.get('type')=='pull_request' and type(count) is int:
                direct = capability(False,'available','active_ruleset_without_bypass')
                review_fact = capability(count>0,'available','active_ruleset_without_bypass')
                if count>0:
                    return direct,review_fact
    return direct,review_fact


def scm_facts(profile, branch, api):
    """Unavailable data stays unknown. Access errors never prove protection."""
    provider, native, path = profile['provider'], profile['native_id'], profile['path']
    facts = {name: capability() for name in ('protected_branch', 'direct_push_allowed', 'review_required')}
    try:
        if provider == 'github':
            if len(path.split('/')) != 2:
                raise ProviderError('invalid_repository_path')
            route = '/repos/' + '/'.join(quote(part, safe='') for part in path.split('/'))
            repository = api.get(route)
            if str(repository['id']) != native:
                raise ProviderError('repository_identity_mismatch')
            data = api.get(route + '/branches/' + quote(branch, safe=''))
            if data.get('name') != branch or type(data.get('protected')) is not bool:
                raise ProviderError('invalid_branch_response')
            facts['protected_branch'] = capability(data['protected'], 'available', 'branch_api')
            if not data['protected']:
                facts['direct_push_allowed'] = capability(True, 'available', 'branch_api')
            else:
                facts['direct_push_allowed'],facts['review_required'] = github_protection(api,route,branch)
        elif provider == 'gitlab':
            route = '/projects/' + quote(native, safe='')
            repository = api.get(route)
            if str(repository['id']) != native or repository['path_with_namespace'] != path:
                raise ProviderError('repository_identity_mismatch')
            data = api.get(route + '/repository/branches/' + quote(branch, safe=''))
            if data.get('name') != branch or type(data.get('protected')) is not bool:
                raise ProviderError('invalid_branch_response')
            facts['protected_branch'] = capability(data['protected'], 'available', 'branch_api')
            if not data['protected']:
                facts['direct_push_allowed'] = capability(True, 'available', 'branch_api')
            else:
                # All matching protected-branch rules may grant push access. Paginate all.
                rules, page = [], 1
                while True:
                    rows = api.get(route + f'/protected_branches?per_page=100&page={page}')
                    if not isinstance(rows, list) or page > 100:
                        raise ProviderError('invalid_or_excessive_branch_rules')
                    rules.extend(rows)
                    if len(rows) < 100:
                        break
                    page += 1
                from fnmatch import fnmatchcase
                matching = [row for row in rules if fnmatchcase(branch, row['name'])]
                levels = [level for row in matching for level in row.get('push_access_levels', [])]
                if levels and all(type(level.get('access_level')) is int for level in levels):
                    allowed = any(level['access_level'] != 0 or any(level.get(key) is not None for key in ('user_id','group_id','deploy_key_id','member_role_id')) for level in levels)
                    facts['direct_push_allowed'] = capability(allowed, 'available', 'all_matching_protected_branch_rules')
            approvals, page = [], 1
            while True:
                rows = api.get(route + f'/approval_rules?per_page=100&page={page}')
                if not isinstance(rows,list) or page > 100:
                    raise ProviderError('invalid_or_excessive_approval_rules')
                approvals.extend(rows)
                if len(rows)<100:
                    break
                page+=1
            branch_ids = {row['id'] for row in matching} if data['protected'] else set()
            applicable = [rule for rule in approvals if rule.get('rule_type') in ('regular','any_approver')
                          and (not rule.get('protected_branches') or rule.get('applies_to_all_protected_branches') is True
                               or any(branch.get('id') in branch_ids for branch in rule['protected_branches']))]
            if all(type(rule.get('approvals_required')) is int for rule in applicable):
                facts['review_required'] = capability(any(rule['approvals_required']>0 for rule in applicable), 'available','applicable_project_approval_rules')
        elif provider == 'bitbucket-dc':
            parts = path.split('/')
            if len(parts) != 2:
                raise ProviderError('invalid_repository_path')
            route = '/rest/api/1.0/projects/' + quote(parts[0], safe='') + '/repos/' + quote(parts[1], safe='')
            repository = api.get(route)
            if str(repository['id']) != native:
                raise ProviderError('repository_identity_mismatch')
            # API facts are acquired without guessing effective project inheritance or exemptions.
            # Scope/matcher support must be reviewed for each installed DC version.
            restrictions, start = [], 0
            while True:
                data = api.get('/rest/branch-permissions/2.0/projects/' + quote(parts[0], safe='') + '/repos/' + quote(parts[1], safe='') + f'/restrictions?limit=100&start={start}')
                restrictions.extend(data['values'])
                if data['isLastPage'] is True:
                    break
                following = data['nextPageStart']
                if type(following) is not int or following <= start or following > 10000:
                    raise ProviderError('invalid_restriction_pagination')
                start = following
            matches = [row for row in restrictions if row.get('type') == 'pull-request-only'
                       and row.get('matcher', {}).get('id') == 'refs/heads/' + branch
                       and row.get('matcher', {}).get('type', {}).get('id') == 'BRANCH']
            if matches:
                facts['protected_branch'] = capability(True, 'available', 'exact_branch_pull_request_restriction')
                if any(all(row.get(key) == [] for key in ('users','groups','accessKeys')) for row in matches):
                    facts['direct_push_allowed'] = capability(False, 'available', 'exact_branch_restriction_without_exemptions')
                else:
                    facts['direct_push_allowed'] = capability(status='unsupported', source='restriction_exemptions_present')
            settings = api.get(route + '/settings/pull-requests')
            approvals = settings.get('com.atlassian.bitbucket.server.bundled-hooks.requiredApproversMergeHook')
            if isinstance(approvals,dict) and type(approvals.get('enabled')) is bool and type(approvals.get('count')) is int:
                facts['review_required'] = capability(approvals['enabled'] and approvals['count']>0, 'available','effective_required_approvers_merge_hook')
        else:
            raise ProviderError('unsupported_scm_provider')
    except (ProviderError, KeyError, TypeError, ValueError, AttributeError) as error:
        code = str(error) if isinstance(error, ProviderError) else 'invalid_provider_response'
        facts = {name: capability(status='error', source=code) for name in facts}
    return facts


def collect_context(ci_provider, profile, env, checkout, *, api=None):
    validate('profile',profile)
    if profile['ci']['provider'] != ci_provider:
        raise ValueError('configured_ci_provider_mismatch')
    scm = profile['scm']
    instance = endpoint(scm['instance'])
    url = urlsplit(scm['url'])
    if url.scheme != 'https' or url.username or url.password or url.query or url.fragment or endpoint('https://' + url.netloc) != instance:
        raise ValueError('unsafe_repository_url')
    tested = checked_out_revision(checkout)
    branch, source, target, mode, change = None, None, None, 'branch', None
    run, job, attempt, event, reference = None, None, 1, 'unknown', None
    ci_instance = profile['ci']['instance']
    if ci_provider == 'github-actions':
        native = json.loads(Path(env['GITHUB_EVENT_PATH']).read_text()) if env.get('GITHUB_EVENT_PATH') else {}
        run, job = env.get('GITHUB_RUN_ID'), env.get('GITHUB_JOB')
        attempt = int(env['GITHUB_RUN_ATTEMPT']) if env.get('GITHUB_RUN_ATTEMPT') else None
        name = env.get('GITHUB_EVENT_NAME')
        event = {'push':'push','pull_request':'pull_request','workflow_dispatch':'manual','schedule':'schedule'}.get(name,'unknown')
        source = env.get('GITHUB_SHA')
        branch = env.get('GITHUB_REF_NAME')
        reference = str(native.get('number')) if native.get('number') else run
        if name == 'pull_request':
            pr = native['pull_request']
            source, target = pr['head']['sha'], pr['base']['sha']
            mode = 'source-head' if tested == source else 'merge-result'
            if mode == 'merge-result' and tested != pr.get('merge_commit_sha'):
                raise ValueError('checkout_does_not_match_pull_request')
            branch = pr['head']['ref']
            change = {'kind':'pull_request','id':str(native['number']), 'source_repository':str(pr['head']['repo']['id']),
                      'target_repository':str(pr['base']['repo']['id']), 'source_branch':branch,'target_branch':pr['base']['ref']}
            if str(pr['base']['repo']['id']) != scm['native_id']:
                raise ValueError('change_target_identity_mismatch')
        elif source != tested:
            raise ValueError('checkout_does_not_match_run')
    elif ci_provider == 'gitlab-ci':
        run, job = env.get('CI_PIPELINE_ID'), env.get('CI_JOB_ID')
        reference = env.get('CI_PIPELINE_URL')
        source, branch = env.get('CI_COMMIT_SHA'), env.get('CI_COMMIT_BRANCH')
        kind = env.get('CI_PIPELINE_SOURCE')
        event = {'push':'push','merge_request_event':'pull_request','web':'manual','schedule':'schedule'}.get(kind,'unknown')
        if source != tested:
            raise ValueError('checkout_does_not_match_run')
        if kind == 'merge_request_event':
            branch = env.get('CI_MERGE_REQUEST_SOURCE_BRANCH_NAME')
            mode = 'merge-result' if env.get('CI_MERGE_REQUEST_EVENT_TYPE') in ('merged_result','merge_train') else 'source-head'
            target = env.get('CI_MERGE_REQUEST_TARGET_BRANCH_SHA')
            source = env.get('CI_MERGE_REQUEST_SOURCE_BRANCH_SHA') if mode == 'merge-result' else tested
            change = {'kind':'merge_request','id':env.get('CI_MERGE_REQUEST_IID',''),
                      'source_repository':env.get('CI_MERGE_REQUEST_SOURCE_PROJECT_ID'), 'target_repository':env.get('CI_MERGE_REQUEST_TARGET_PROJECT_ID'),
                      'source_branch':branch,'target_branch':env.get('CI_MERGE_REQUEST_TARGET_BRANCH_NAME')}
            if change['target_repository'] != scm['native_id']:
                raise ValueError('change_target_identity_mismatch')
        elif env.get('CI_PROJECT_ID') != scm['native_id']:
            raise ValueError('repository_identity_mismatch')
    elif ci_provider == 'bamboo':
        run, job = env.get('bamboo_buildResultKey'), env.get('bamboo_buildKey')
        reference = env.get('bamboo_resultsUrl')
        source, branch = env.get('bamboo_planRepository_revision'), env.get('bamboo_planRepository_branchName')
        if source != tested:
            raise ValueError('checkout_does_not_match_run')
        # Trigger reason is a human string, not a reliable PR/push discriminator.
        event = profile['ci'].get('event', 'unknown')
    else:
        raise ValueError('unsupported_ci_provider')
    if env.get('GITHUB_REPOSITORY_ID') and ci_provider == 'github-actions' and not change and env['GITHUB_REPOSITORY_ID'] != scm['native_id']:
        raise ValueError('repository_identity_mismatch')
    token = env.get(scm.get('token_env', ''), '')
    api = api or API(scm['api_url'], token, scm['provider'])
    if reference and '://' in reference:
        native_url=urlsplit(reference)
        if native_url.username or native_url.password or native_url.query or native_url.fragment:
            raise ValueError('unsafe_native_reference')
    protected = change['target_branch'] if change else branch
    facts = scm_facts(scm, protected, api) if protected else {}
    context = {'schema_version':VERSION, 'scm':{key:scm[key] for key in ('provider','instance','native_id','path','url')},
               'ci':{'provider':ci_provider,'instance':endpoint(ci_instance),'run_id':run,'job_id':job,'attempt':attempt,
                     'event':event,'native_reference':reference},
               'revision':{'tested':tested,'source':source,'target':target,'branch':branch,'mode':mode},
               'change_request':change,'capabilities':facts,'synthetic':False,
               'governance':{**profile['governance'],'runtime_version':VERSION,'adapter_version':VERSION,'runtime_source_digest':source_digest()}}
    context['scm']['instance'] = instance
    validate('context', context)
    return context
