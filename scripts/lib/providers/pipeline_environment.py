"""Explicit original CI environment views; declarations, without native calls."""

PROFILES = ('github-actions', 'bamboo', 'bitbucket-pipelines', 'jenkins')
KEYS = frozenset(('APPROVED_WAIVER_EXISTS', 'BITBUCKET_BRANCH', 'BITBUCKET_BUILD_NUMBER', 'BITBUCKET_COMMIT', 'BITBUCKET_PIPELINE_URL', 'BITBUCKET_PIPELINE_UUID', 'BITBUCKET_PR_DESTINATION_BRANCH', 'BITBUCKET_PR_ID', 'BITBUCKET_REPO_FULL_NAME', 'BITBUCKET_REPO_SLUG', 'BITBUCKET_WORKSPACE', 'BRANCH_NAME', 'BUILD_NUMBER', 'BUILD_TAG', 'BUILD_URL', 'CHANGE_ID', 'CHANGE_TARGET', 'EXTERNAL_DIRECT_DOWNLOADS_DETECTED', 'GITHUB_BASE_REF', 'GITHUB_EVENT_NAME', 'GITHUB_REF_NAME', 'GITHUB_REPOSITORY', 'GITHUB_RUN_ID', 'GITHUB_SERVER_URL', 'GITHUB_SHA', 'GITHUB_WORKFLOW', 'GIT_COMMIT', 'GIT_URL', 'GOVERNANCE_REPOSITORY_ID', 'JOB_NAME', 'VULNERABILITY_MAX_SEVERITY', 'bamboo_buildNumber', 'bamboo_buildResultKey', 'bamboo_buildTriggerReason', 'bamboo_planName', 'bamboo_planRepository_branchName', 'bamboo_planRepository_repositoryUrl', 'bamboo_planRepository_revision', 'bamboo_repository_id', 'bamboo_resultsUrl'))

def github_actions_context(environment) -> dict:
    repository_id = environment.get("GITHUB_REPOSITORY", "unknown")
    branch = environment.get("GITHUB_BASE_REF") or environment.get("GITHUB_REF_NAME") or "unknown"
    run_id = environment.get("GITHUB_RUN_ID", "unknown")
    server_url = environment.get("GITHUB_SERVER_URL", "https://github.com")
    context = {
        "source": "github-actions",
        "repository_id": repository_id,
        "branch": branch,
        "commit_id": environment.get("GITHUB_SHA", "unknown"),
        "pipeline_id": environment.get("GITHUB_WORKFLOW", "GitHub Actions"),
        "pipeline_run_id": run_id,
        "pipeline_url": f"{server_url}/{repository_id}/actions/runs/{run_id}" if repository_id != "unknown" else "",
        "event": environment.get("GITHUB_EVENT_NAME", "unknown"),
    }
    if environment.get("GITHUB_BASE_REF"):
        context["pull_request_target"] = environment["GITHUB_BASE_REF"]
    return context

def bamboo_context(environment) -> dict:
    repository_id = (
        environment.get("bamboo_planRepository_repositoryUrl")
        or environment.get("bamboo_repository_id")
        or "unknown"
    )
    run_id = environment.get("bamboo_buildResultKey") or environment.get("bamboo_buildNumber") or "unknown"
    return {
        "source": "bamboo",
        "repository_id": repository_id,
        "branch": environment.get("bamboo_planRepository_branchName", "unknown"),
        "commit_id": environment.get("bamboo_planRepository_revision", "unknown"),
        "pipeline_id": environment.get("bamboo_planName", "Bamboo"),
        "pipeline_run_id": str(run_id),
        "pipeline_url": environment.get("bamboo_resultsUrl", ""),
        "event": environment.get("bamboo_buildTriggerReason", "bamboo"),
    }

def bitbucket_pipelines_context(environment) -> dict:
    repository_full_name = environment.get("BITBUCKET_REPO_FULL_NAME", "")
    repository_slug = environment.get("BITBUCKET_REPO_SLUG", "unknown")
    workspace = environment.get("BITBUCKET_WORKSPACE", "")
    repository_id = repository_full_name or f"{workspace}/{repository_slug}".strip("/") or "unknown"
    event = "pull_request" if environment.get("BITBUCKET_PR_ID") else "branch_build"
    context = {
        "source": "bitbucket-pipelines",
        "repository_id": repository_id,
        "branch": environment.get("BITBUCKET_BRANCH") or environment.get("BITBUCKET_PR_DESTINATION_BRANCH") or "unknown",
        "commit_id": environment.get("BITBUCKET_COMMIT", "unknown"),
        "pipeline_id": environment.get("BITBUCKET_PIPELINE_UUID", "Bitbucket Pipelines"),
        "pipeline_run_id": environment.get("BITBUCKET_BUILD_NUMBER", "unknown"),
        "pipeline_url": environment.get("BITBUCKET_PIPELINE_URL", ""),
        "event": event,
    }
    if environment.get("BITBUCKET_PR_ID"):
        context["pull_request_id"] = environment["BITBUCKET_PR_ID"]
    if environment.get("BITBUCKET_PR_DESTINATION_BRANCH"):
        context["pull_request_target"] = environment["BITBUCKET_PR_DESTINATION_BRANCH"]
    return context

def jenkins_context(environment) -> dict:
    run_id = environment.get("BUILD_TAG") or environment.get("BUILD_NUMBER") or "unknown"
    event = "pull_request" if environment.get("CHANGE_ID") else "branch_build"
    context = {
        "source": "jenkins",
        "repository_id": environment.get("GOVERNANCE_REPOSITORY_ID") or environment.get("GIT_URL", "unknown"),
        "branch": environment.get("CHANGE_TARGET") or environment.get("BRANCH_NAME", "unknown"),
        "commit_id": environment.get("GIT_COMMIT", "unknown"),
        "pipeline_id": environment.get("JOB_NAME", "Jenkins"),
        "pipeline_run_id": str(run_id),
        "pipeline_url": environment.get("BUILD_URL", ""),
        "event": event,
    }
    if environment.get("CHANGE_ID"):
        context["pull_request_id"] = environment["CHANGE_ID"]
    if environment.get("CHANGE_TARGET"):
        context["pull_request_target"] = environment["CHANGE_TARGET"]
    return context

def context_for(platform: str, environment) -> dict:
    if platform == "github-actions":
        return github_actions_context(environment)
    if platform == "bamboo":
        return bamboo_context(environment)
    if platform == "bitbucket-pipelines":
        return bitbucket_pipelines_context(environment)
    if platform == "jenkins":
        return jenkins_context(environment)
    raise ValueError(f"Unsupported platform: {platform}")

def declared_environment(profile, environment):
    if profile not in PROFILES: raise ValueError('unsupported_declared_pipeline_profile')
    if (not isinstance(environment, dict) or set(environment) - KEYS
            or len(environment) > len(KEYS)
            or any(not isinstance(v, str) or len(v) > 4096 or any(ord(c) < 32 for c in v) for v in environment.values())):
        raise ValueError('invalid_declared_pipeline_environment')
    boolean = lambda v: str(v).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
    return {'kind': 'legacy-environment-view-v1', 'profile': profile,
            'context': context_for(profile, environment),
            'scan_fallback': environment.get('VULNERABILITY_MAX_SEVERITY', 'none'),
            'external_direct_downloads_detected': boolean(environment.get('EXTERNAL_DIRECT_DOWNLOADS_DETECTED', 'false')),
            'approved_waiver_exists': boolean(environment.get('APPROVED_WAIVER_EXISTS', 'false'))}
