"""Finite legacy interoperability selection; no live GitHub operations."""
import shutil

from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
from lib.providers.source_inspection import configuration_source_profile

REPOSITORY_ENGINE_PROFILES = ('legacy-repository-validator-v1',)


def repository_engine_profile(name):
    if name not in REPOSITORY_ENGINE_PROFILES:
        raise ValueError('unsupported_repository_engine_profile')
    return {'capture_adapter_factory': LegacyRepositoryLifecycleCapture,
        'schema_identifier_bases': ('https://joku-dev.github.io/devsecops-governance-framework/schemas/',),
        'source_configuration_profile': configuration_source_profile('github-actions')}


def repository_git_tool():
    value = shutil.which('git')
    if value is None:raise ValueError('repository_git_tool_missing')
    return value
