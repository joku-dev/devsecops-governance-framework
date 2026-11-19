"""Freeze two exact parentless comparison snapshots; never install or run them."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.runtime_package import git, tracked, text_json

REFERENCES = {
    'v1': '6b557fefe295b58272d2271326576ca3a3687197',
    'lifecycle-pilot': 'c2250325f34d938ea4f607036e003a36a3f2f9da',
}
AUTHORITY = {'production_approval': False, 'operating_acceptance_inherited': False,
             'authority_transferred': False, 'independent_execution_attested': False}


def freeze(repository, destination):
    repository = Path(repository).resolve(strict=True)
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError('fresh_reference_input_destination_required')
    destination.mkdir(mode=0o700, parents=True)
    snapshots = []
    for name, revision in REFERENCES.items():
        rows = tracked(repository, revision)
        manifest = {'schema_version': 1, 'source_commit': revision,
            'source_tree': git(repository, 'rev-parse', revision + '^{tree}').decode().strip(),
            'target': {'system': 'reference-data', 'machine': 'immutable-source'},
            'files': [], 'locks': [], 'opa': None, 'prepared_dependencies': False}
        contents = {}
        for row in rows:
            raw = git(repository, 'cat-file', 'blob', row['git_blob'])
            if len(raw) != row['size']:
                raise ValueError('reference_blob_size_changed')
            path = 'source/' + row['path']
            contents[path] = raw
            manifest['files'].append({**row, 'path': path,
                'sha256': hashlib.sha256(raw).hexdigest()})
        raw = git(repository, 'cat-file', 'commit', revision)
        contents['commit.raw'] = raw
        manifest['files'].append({'path': 'commit.raw', 'mode': '100644', 'size': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()})
        package = destination / (name + '.zip')
        with zipfile.ZipFile(package, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in ['manifest.json', *sorted(contents)]:
                info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, text_json(manifest).encode() if path == 'manifest.json' else contents[path])
        if package.stat().st_size > 16 * 1024**2:
            raise ValueError('reference_archive_byte_budget')
        package.chmod(0o600)
        snapshots.append({'id': name, 'path': package.name, 'source_revision': revision,
            'source_tree': manifest['source_tree'], 'source_files': len(rows),
            'sha256': hashlib.sha256(package.read_bytes()).hexdigest(), 'bytes': package.stat().st_size})
    result = {'schema_version': 1, 'purpose': 'immutable-original-test-reference-data',
              'snapshots': snapshots, **AUTHORITY}
    path = destination / 'manifest.json'
    path.write_text(text_json(result))
    path.chmod(0o600)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    print(text_json(freeze(args.repository, args.destination)), end='')
