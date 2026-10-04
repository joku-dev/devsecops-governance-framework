"""Read-only integrity check for the confidential counsel ZIP; no extraction."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile


def verify(path, expected=None):
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected and digest != expected:
        raise ValueError('ZIP digest differs from the retained anchor')
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if len(names) != len(set(names)) or len(names) > 500:
            raise ValueError('Duplicate paths or excessive archive entries')
        if sum(item.file_size for item in infos) > 50_000_000:
            raise ValueError('Archive exceeds the supported size')
        for item in infos:
            name = item.filename
            if (PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts
                    or '\\' in name or stat.S_ISLNK(item.external_attr >> 16)):
                raise ValueError('Unsafe archive entry')
        manifest = json.loads(archive.read('MANIFEST.json'))
        files = manifest['files']
        if set(names) != set(files) | {'MANIFEST.json'}:
            raise ValueError('Manifest and file inventory differ')
        for name, expected_hash in files.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected_hash:
                raise ValueError('File digest differs: ' + name)
    return {'package_integrity_verified': True, 'file_count': len(names),
            'package_sha256': digest, 'external_anchor_checked': bool(expected),
            'technical_claims_or_patentability_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--expect-zip-sha256')
    args = parser.parse_args()
    print(json.dumps(verify(args.package, args.expect_zip_sha256), indent=2))
