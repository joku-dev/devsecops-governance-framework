"""Finite typed profile composition; no executable plugin discovery."""
import tarfile
import zipfile
from jsonschema import ValidationError

from lib.providers import typed_capture

TYPED_PROVIDERS = ('github-actions',)


def require_provider(provider):
    if provider not in TYPED_PROVIDERS:
        raise ValueError('unsupported_typed_provider')


def typed_import(provider, source, sha256, destination, at, *, budget):
    require_provider(provider)
    try:
        typed_capture.copy_bundle(source, sha256, destination, budget=budget)
        return typed_capture.verify(destination, sha256, at, budget=budget)
    except (ValidationError, tarfile.TarError, zipfile.BadZipFile):
        raise ValueError('invalid_typed_evidence') from None


def typed_verify(provider, source, sha256, at, *, budget):
    require_provider(provider)
    try:
        return typed_capture.verify(source, sha256, at, budget=budget)
    except (ValidationError, tarfile.TarError, zipfile.BadZipFile):
        raise ValueError('invalid_typed_evidence') from None


def typed_capture_live(provider, repository, run_id, credential, destination, *, requests, budget):
    require_provider(provider)
    try:
        return typed_capture.capture(repository, run_id, credential, destination,
            request_budget=requests, storage_budget=budget)
    except (ValidationError, tarfile.TarError, zipfile.BadZipFile):
        raise ValueError('invalid_typed_evidence') from None
