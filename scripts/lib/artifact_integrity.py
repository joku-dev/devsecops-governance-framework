"""Explicit-context verification extracted from frozen V1 6b557fefe295b58272d2271326576ca3a3687197.

No source CLI dispatch or native acquisition is included here.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import tarfile
MAX_IMAGE=2*1024**3

def digest_file(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def verify_docker_archive(path, image_id, commit=None):
    """Match config digest and every uncompressed layer to Docker's immutable image ID."""
    with tarfile.open(path, 'r:') as archive:
        files = {}
        for number, member in enumerate(archive):
            if number >= 20000:
                raise ValueError('Too many image archive members')
            name = PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts or member.issym() or member.islnk():
                raise ValueError('Unsafe image archive member')
            if member.isdir():
                continue
            if not member.isfile() or member.name in files or member.size > MAX_IMAGE:
                raise ValueError('Duplicate, oversized or unsupported image member')
            files[member.name] = member

        def read(name, limit=8 * 1024 ** 2):
            member = files.get(name)
            if member is None or member.size > limit:
                raise ValueError('Missing or oversized image metadata')
            with archive.extractfile(member) as stream:
                return stream.read(limit + 1)
        manifest = json.loads(read('manifest.json'))
        if not isinstance(manifest, list) or len(manifest) != 1:
            raise ValueError('Expected exactly one Docker image')
        config_bytes = read(manifest[0]['Config'])
        if 'sha256:' + hashlib.sha256(config_bytes).hexdigest() != image_id:
            raise ValueError('Archive config does not match scanned image ID')
        config = json.loads(config_bytes)
        if commit is not None and config.get('config', {}).get('Labels', {}).get('org.opencontainers.image.revision') != commit:
            raise ValueError('Archive revision label differs from source commit')
        layers, diff_ids = (manifest[0]['Layers'], config['rootfs']['diff_ids'])
        if not layers or len(layers) != len(diff_ids) or len(set(layers)) != len(layers):
            raise ValueError('Invalid image layer binding')
        for name, expected in zip(layers, diff_ids):
            if name not in files:
                raise ValueError('Missing image layer')
            with archive.extractfile(files[name]) as stream:
                actual = 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != expected:
                raise ValueError('Archive layer does not match image config')
        return len(layers)
