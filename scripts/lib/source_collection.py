"""Source-only release input collection from one frozen local Git revision.

The product never executes inspected application code or consumes its working
tree. Declared approvals stay unverified; native source layouts belong to ports.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile

from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import canonical_digest
from lib.portable.runtime import read_json, source_digest
from lib.provider_ports import SOURCE_CI_PROFILES, local_source_signals


def snapshot(repository, revision, destination):
    repository = Path(repository).resolve()
    destination = Path(destination)
    if destination.is_symlink() or not destination.is_dir() or any(destination.iterdir()):
        raise ValueError('fresh_collection_snapshot_required')
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('exact_collection_revision_required')
    resolved = git_read(repository, 'rev-parse', '--verify', revision + '^{commit}').decode().strip()
    if resolved != revision:
        raise ValueError('collection_revision_mismatch')
    rows = git_read(repository, 'ls-tree', '-r', '-l', '-z', revision)
    files = {}
    total = 0
    # Parse and bound the whole inventory before retrieving any source blob.
    entries = []
    for row in rows.split(b'\0'):
        if not row:
            continue
        metadata, raw_name = row.split(b'\t', 1)
        mode, kind, blob, size = metadata.decode().split()
        name = raw_name.decode()
        path = Path(name)
        if (mode not in ('100644', '100755') or kind != 'blob' or path.is_absolute()
                or '..' in path.parts or '.git' in path.parts or '\\' in name
                or any(ord(c) < 32 for c in name)):
            raise ValueError('unsafe_collection_source')
        size = int(size)
        total += size
        if size > 16 * 1024**2 or total > 128 * 1024**2 or len(entries) >= 10000:
            raise ValueError('collection_source_limit_exceeded')
        entries.append((name, blob, size))
    for name, blob, size in entries:
        raw = git_read(repository, 'cat-file', 'blob', blob)
        if len(raw) != size:
            raise ValueError('collection_source_changed')
        path = destination / name
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(0o600)
        files[name] = hashlib.sha256(raw).hexdigest()
    return {'commit': revision,
            'short_commit': git_read(repository, 'rev-parse', '--short', revision).decode().strip(),
            'tree': git_read(repository, 'rev-parse', revision + '^{tree}').decode().strip(),
            'files': files}


def collect(domain, repository, revision, *, ci_profile, release_id, baseline):
    repository = Path(repository).resolve()
    with tempfile.TemporaryDirectory(prefix='axiom-source-collection-') as temporary:
        root = Path(temporary)
        binding = snapshot(repository, revision, root)
        signals = local_source_signals(ci_profile, root)
        if domain == 'controls':
            from lib.controls_collection import collect as collect_controls
            payload = collect_controls(root, release_id, source_commit=binding['short_commit'], ci_signals=signals)
        elif domain == 'architecture':
            from lib.architecture_collection import collect as collect_architecture
            payload = collect_architecture(root, release_id, baseline,
                source_commit=binding['short_commit'], ci_signals=signals)
        else:
            raise ValueError('unsupported_collection_domain')
        # Preserve the V1 descriptive source label while reading frozen blobs.
        payload['target_repository']['path'] = str(repository)
    return {'schema_version': 1, 'kind': 'source-declaration-collection', 'domain': domain,
            'repository': str(repository), 'revision': revision, 'tree': binding['tree'],
            'source_files': binding['files'], 'ci_profile': ci_profile,
            'runtime_source_digest': source_digest(), 'working_tree_used': False,
            'provider_invoked': False, 'evidence_trust': 'unverified', 'official_acceptance': False,
            'input': payload, 'input_digest': canonical_digest(payload)}


def persist(value, instance_root):
    state = Path(instance_root) / 'state'
    base = state / 'collections'
    if state.is_symlink() or base.is_symlink():
        raise ValueError('unsafe_collection_state')
    base.mkdir(mode=0o700, exist_ok=True)
    if base.stat().st_mode & 0o077:
        raise ValueError('private_collection_state_required')
    identity = canonical_digest(value)
    target = base / identity
    if target.is_symlink():
        raise ValueError('unsafe_collection_state')
    target.mkdir(mode=0o700, exist_ok=True)
    if target.stat().st_mode & 0o077:
        raise ValueError('private_collection_state_required')
    for name, data in [('collection.json', value), ('input.json', value['input'])]:
        path = target / name
        if path.is_symlink():
            raise ValueError('unsafe_collection_state')
        if path.exists():
            if read_json(path) != data:
                raise ValueError('immutable_collection_conflict')
        else:
            atomic_json(path, data)
    return {'collection_id': identity, 'domain': value['domain'], 'revision': value['revision'],
            'input_path': str(target / 'input.json'), 'input_digest': value['input_digest'],
            'input_sha256': hashlib.sha256((target / 'input.json').read_bytes()).hexdigest(),
            'evidence_trust': 'unverified', 'working_tree_used': False, 'official_acceptance': False}


def run(arguments, instance_root):
    parser = argparse.ArgumentParser(prog='axiom-v2 collect-source', allow_abbrev=False)
    parser.add_argument('--domain', choices=('controls', 'architecture'), required=True)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--ci-profile', choices=SOURCE_CI_PROFILES, required=True)
    parser.add_argument('--release-id', default='demo-release-candidate')
    parser.add_argument('--baseline', default='demo-solution-baseline')
    args = parser.parse_args(arguments)
    value = collect(args.domain, args.repo, args.revision, ci_profile=args.ci_profile,
                    release_id=args.release_id, baseline=args.baseline)
    print(json.dumps(persist(value, instance_root), sort_keys=True))
    return 0
