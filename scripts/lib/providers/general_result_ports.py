"""Finite native general-result composition; no discovered plugins or tokens."""
import zipfile
from lib.providers import general_results

NATIVE_RESULT_PROVIDERS = ('github-actions',)


def require(provider):
    if provider not in NATIVE_RESULT_PROVIDERS:
        raise ValueError('unsupported_native_result_provider')


def general_result_capture(provider, repository, run_id, attempt, credential, destination, **options):
    require(provider)
    try:
        return general_results.capture(repository, run_id, attempt, credential, destination, **options)
    except zipfile.BadZipFile:
        raise ValueError('invalid_native_result_archive') from None


def general_result_verify(provider, source, sha256, *, budget):
    require(provider)
    try:
        return general_results.verify(source, sha256, budget=budget)
    except zipfile.BadZipFile:
        raise ValueError('invalid_native_result_archive') from None
