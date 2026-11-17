"""Finite measured profile composition; no native data can select executable code."""
from jsonschema import ValidationError
import xml.etree.ElementTree as ET

from lib.providers import measured_capture, measured_l1, measured_security

MEASURED_PROVIDERS = ('github-actions',)


def require_provider(provider):
    if provider not in MEASURED_PROVIDERS:
        raise ValueError('unsupported_measured_provider')


def measured_import(provider, root, expected_sha256, kind):
    require_provider(provider)
    try:
        return measured_capture.import_bundle(root, expected_sha256, kind)
    except (ValidationError, ET.ParseError):
        raise ValueError('invalid_measured_evidence') from None


def measured_capture_live(provider, repository, run_id, credential_file, *, budget, kind):
    require_provider(provider)
    try:
        return measured_capture.capture(repository, run_id, credential_file, budget=budget, kind=kind)
    except (ValidationError, ET.ParseError):
        raise ValueError('invalid_measured_evidence') from None


def measured_export(provider, captured, root, kind):
    require_provider(provider)
    return measured_capture.export_bundle(captured, root, kind)


def measured_validate(provider, kind, result):
    require_provider(provider)
    try:
        if kind == 'l1':
            measured_l1.validate_snapshot(result)
        elif kind == 'containers':
            measured_security.validate_snapshot(result)
        else:
            raise ValueError('unsupported_measured_kind')
    except (ValidationError, ET.ParseError):
        raise ValueError('invalid_measured_assessment') from None


def measured_supplement_profile(provider, measured):
    """The existing native profile admits only its exact original mainline scope."""
    require_provider(provider)
    measured_validate(provider, 'l1', measured)
    if (measured['repository_id'] != measured_security.REPOSITORY
            or measured['run']['event'] != 'push' or measured['run']['branch'] != 'main'):
        raise ValueError('staging_mainline_measured_subject_required')
    return {'repository': measured_security.REPOSITORY, 'baseline': measured_l1.BASELINE,
            'consolidated_profile': 'ha-cpswms-l1-consolidated-v1'}
