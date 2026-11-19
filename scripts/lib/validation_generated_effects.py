"""Audit closed generated metadata effects and the exact own Viewer output."""
from datetime import datetime
import hashlib
from pathlib import PurePosixPath
import re

from lib.result_bytes import strict_json
from lib.result_bytes import safe_bytes

GENERATED_ADDITIONS = frozenset({'generated/viewer/app/data.json'})
MAX_VIEWER_DATA = 8 * 1024**2

GENERATED = frozenset({
    'generated/graph/governance-graph.json',
    'generated/reports/architecture-source-replacement-assessment.json',
    'generated/reports/architecture-source-replacement-assessment.md',
    'generated/reports/blocking-mode-alignment.json',
    'generated/reports/evidence-attestation-pilot.json',
    'generated/reports/governance-change-impact.json',
    'generated/reports/governance-change-impact.md',
    'generated/reports/multi-consumer-readiness.json',
    'generated/reports/multi-consumer-readiness.md',
    'generated/reports/source-document-intake-review-briefs.json',
    'generated/reports/source-document-intake-review-briefs.md',
    'generated/reports/source-document-intake-status.json',
    'generated/reports/source-document-intake-status.md',
    'generated/reports/source-document-process-status.json',
    'generated/reports/source-document-requirement-delta.json',
    'generated/reports/source-document-requirement-delta.md',
    'generated/reports/source-lineage-report.json',
    'generated/reports/source-lineage-report.md',
    'generated/viewer/status-viewer.html',
})


def differences(left, right, prefix=''):
    if type(left) is not type(right):
        return [prefix]
    if type(left) is dict:
        if left.keys() != right.keys():
            return [prefix + '/$keys']
        return [p for key in left for p in differences(left[key], right[key], prefix + '/' + key)]
    if type(left) is list:
        if len(left) != len(right):
            return [prefix + '/$length']
        return [p for i in range(len(left)) for p in differences(left[i], right[i], prefix + '/' + str(i))]
    return [prefix] if left != right else []


def timestamp(value):
    if not isinstance(value, str) or datetime.fromisoformat(value.replace('Z', '+00:00')).utcoffset() is None:
        raise ValueError('explicit_generated_metadata_timezone_required')


def checked_change(name, before, after, source, example_sha256):
    if name not in GENERATED or before == after:
        raise ValueError('closed_product_generated_effect_required')
    if name.endswith('.json'):
        old, new = strict_json(before), strict_json(after)
        diff = differences(old, new)
        if name == 'generated/reports/evidence-attestation-pilot.json':
            relative = 'docs/examples/evidence-attestation.example.json'
            if (diff != ['/attestation_ref'] or new['attestation_ref'] != str(source / relative)
                    or not isinstance(old['attestation_ref'], str)
                    or not PurePosixPath(old['attestation_ref']).is_absolute()
                    or PurePosixPath(old['attestation_ref']).as_posix() != old['attestation_ref']
                    or '..' in PurePosixPath(old['attestation_ref']).parts
                    or not old['attestation_ref'].endswith('/' + relative)
                    or hashlib.sha256((source / relative).read_bytes()).hexdigest() != example_sha256):
                raise ValueError('unexpected_product_attestation_generation_effect')
            return 'owned_example_display_path_only'
        if diff != ['/generated_at']:
            raise ValueError('unexpected_product_generated_semantics')
        timestamp(old['generated_at']); timestamp(new['generated_at'])
        return 'generation_timestamp_only'
    if name.endswith('.md'):
        old, new = before.decode().splitlines(), after.decode().splitlines()
        changed = [(a, b) for a, b in zip(old, new) if a != b]
        if len(old) != len(new) or len(changed) != 1:
            raise ValueError('unexpected_product_generated_markdown')
        for line in changed[0]:
            match = re.fullmatch(r'Generated: `([^`]+)`', line)
            if not match:
                raise ValueError('unexpected_product_generated_markdown')
            timestamp(match[1])
        if after != before.replace(changed[0][0].encode(), changed[0][1].encode(), 1):
            raise ValueError('unexpected_product_generated_markdown')
        return 'generation_timestamp_only'
    # Only the intelligence graph's embedded timestamp may change in the Viewer.
    position = next((i for i, (a, b) in enumerate(zip(before, after)) if a != b), None)
    if position is None:
        raise ValueError('unexpected_product_generated_viewer')
    pattern = rb'"generated_at":\s*"([^"]+)"'
    old = next((m for m in re.finditer(pattern, before) if m.start(1) <= position < m.end(1)), None)
    new = None if old is None else next((m for m in re.finditer(pattern, after) if m.start(1) == old.start(1)), None)
    if (old is None or new is None or b'governance-intelligence-graph' not in before[max(0, old.start()-100):old.start()]
            or after != before[:old.start(1)] + new[1] + before[old.end(1):]):
        raise ValueError('unexpected_product_generated_viewer')
    timestamp(old[1].decode()); timestamp(new[1].decode())
    return 'embedded_graph_generation_timestamp_only'


def retain_effects(source, before, destination, example_sha256):
    destination.mkdir(mode=0o700)
    rows = []
    for name, old in sorted(before.items()):
        new = (source / name).read_bytes()
        if old == new:
            continue
        kind = checked_change(name, old, new, source, example_sha256)
        for label, raw in (('before', old), ('after', new)):
            path = destination / label / name
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            path.write_bytes(raw)
            path.chmod(0o600)
        rows.append({'path': name, 'classification': kind,
            'before_sha256': hashlib.sha256(old).hexdigest(), 'after_sha256': hashlib.sha256(new).hexdigest(),
            'before_bytes': len(old), 'after_bytes': len(new)})
    return rows


def retain_additions(source, names, expected_projection, destination):
    """Only the exact own projection may become the known ignored Viewer output."""
    if set(names) - GENERATED_ADDITIONS:
        raise ValueError('unknown_product_test_generated_output')
    if not names:
        return []
    if type(expected_projection) is not bytes or not 0 < len(expected_projection) <= MAX_VIEWER_DATA:
        raise ValueError('complete_product_viewer_projection_required')
    if type(strict_json(expected_projection)) is not dict:
        raise ValueError('complete_product_viewer_projection_required')
    name = 'generated/viewer/app/data.json'
    raw = safe_bytes(source / name, limit=MAX_VIEWER_DATA)
    if raw != expected_projection:
        raise ValueError('product_test_generated_viewer_projection_mismatch')
    destination.mkdir(mode=0o700)
    target = destination / name
    target.parent.mkdir(mode=0o700, parents=True)
    target.write_bytes(raw); target.chmod(0o600)
    return [{'path': name, 'classification': 'complete_known_own_viewer_projection',
        'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
        'raw_bytes_retained': True, 'official_acceptance': False,
        'authority_transferred': False}]
