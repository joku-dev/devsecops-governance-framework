"""Explicit legacy native protocol, identity aliases and compatibility messages."""
import re

PROFILE='legacy-commit-bound-spdx-v1'
API_ROOT='https://api.github.com'
API_VERSION='2026-03-10'
SOURCE='GitHub dependency graph SBOM API'
ERRORS={'repository':'GITHUB_REPOSITORY must be in owner/name form',
        'commit':'GITHUB_SHA must be a full commit SHA','token':'GH_TOKEN is required'}


def identity(repository):
    return {'root_names':[f'github/{repository}', f'com.github.{repository}'],
            'root_purl_prefix':f'pkg:github/{repository}@',
            'invalid_json_message':'GitHub returned invalid JSON for the SBOM'}


def report_locator(payload):return payload.get('sbom_url')


def report_identifier(repository,locator):
    prefix=f'{API_ROOT}/repos/{repository}/dependency-graph/sbom/fetch-report/'
    if not isinstance(locator,str) or not locator.startswith(prefix):
        raise RuntimeError('GitHub did not return the expected SBOM report URL')
    identifier=locator[len(prefix):]
    if not re.fullmatch(r'[0-9a-f-]{36}',identifier):
        raise RuntimeError('GitHub returned an invalid SBOM report identifier')
    return identifier


def generation_timeout_error():return 'GitHub SBOM generation did not finish before timeout'
