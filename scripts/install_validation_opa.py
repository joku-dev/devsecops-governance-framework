#!/usr/bin/env python3
"""Install only a checksum-pinned OPA, with a verified cache and bounded retries.

Transport data is not authority: version and hashes come from the preserved
validation-toolchain.env. Nothing is executed before its SHA-256 matches.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 128 * 1024 * 1024


class DownloadError(OSError):
    """A sanitized transport failure, without URLs, headers or response bodies."""


@dataclass(frozen=True)
class Tool:
    version: str
    asset: str
    sha256: str
    asset_id: int

    @property
    def cache_key(self):
        return f'axiom-opa-v1-{self.version}-{self.asset}-{self.sha256}'


def select_tool(toolchain=ROOT / 'scripts/validation-toolchain.env',
                sources=ROOT / 'scripts/opa-download-sources.json', *, system=None, machine=None):
    values = dict(line.split('=', 1) for line in toolchain.read_text().splitlines()
                  if line and not line.startswith('#'))
    platforms = {('Linux', 'x86_64'): ('opa_linux_amd64_static', 'OPA_LINUX_AMD64_STATIC_SHA256'),
                 ('Linux', 'aarch64'): ('opa_linux_arm64_static', 'OPA_LINUX_ARM64_STATIC_SHA256'),
                 ('Linux', 'arm64'): ('opa_linux_arm64_static', 'OPA_LINUX_ARM64_STATIC_SHA256'),
                 ('Darwin', 'x86_64'): ('opa_darwin_amd64', 'OPA_DARWIN_AMD64_SHA256'),
                 ('Darwin', 'arm64'): ('opa_darwin_arm64', 'OPA_DARWIN_ARM64_SHA256')}
    target = (system or platform.system(), machine or platform.machine())
    if target not in platforms:
        raise ValueError(f'Unsupported validation platform: {target}')
    asset, checksum_key = platforms[target]
    version, checksum = values['OPA_VERSION'], values[checksum_key]
    if not re.fullmatch(r'\d+\.\d+\.\d+', version) or not re.fullmatch(r'[a-f0-9]{64}', checksum):
        raise ValueError('Version and SHA-256 must be pinned')
    metadata = json.loads(sources.read_text())
    if metadata['version'] != version:
        raise ValueError('Download source metadata must match the pinned OPA version')
    asset_id = metadata['assets'][asset]
    if type(asset_id) is not int or asset_id <= 0:
        raise ValueError('Invalid release asset ID')
    return Tool(version, asset, checksum, asset_id)


def locations(tool, mirror=''):
    result = []
    if mirror:
        parsed = urlsplit(mirror)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or any(ord(c) < 33 for c in mirror)):
            raise ValueError('Mirror must be an HTTPS base URL without credentials, query or fragment')
        result.append((f'{mirror.rstrip("/")}/v{tool.version}/{tool.asset}', False, 'configured mirror'))
    result.extend([(f'https://github.com/open-policy-agent/opa/releases/download/v{tool.version}/{tool.asset}', False, 'official release'),
                   (f'https://api.github.com/repos/open-policy-agent/opa/releases/assets/{tool.asset_id}', True, 'official asset API')])
    return result


def matches(path, expected):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_BYTES:
        return False
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() == expected


def download(url, destination, *, api, timeout):
    # No token is needed for these public assets. In particular, no credentials
    # can be forwarded to redirected asset hosts or the optional mirror.
    args = ['curl', '--disable', '--fail', '--location', '--silent', '--show-error',
            '--proto', '=https', '--proto-redir', '=https', '--connect-timeout', '10',
            '--max-time', str(timeout), '--max-filesize', str(MAX_BYTES)]
    if api:
        args += ['--header', 'Accept: application/octet-stream', '--header', 'X-GitHub-Api-Version: 2022-11-28']
    # Hide URLs (including signed redirects) and proxy responses from CI output.
    result = subprocess.run([*args, '--write-out', '%{http_code}', '--output', str(destination), url], capture_output=True)
    if result.returncode:
        status = result.stdout.strip() if isinstance(result.stdout, bytes) else b''
        code = status.decode() if re.fullmatch(rb'[0-9]{3}', status) else 'unknown'
        raise DownloadError(f'HTTP {code}, curl exit {result.returncode}')


def install_copy(source, destination, tool):
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.opa-', dir=destination.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as output, source.open('rb') as original:
            shutil.copyfileobj(original, output)
            output.flush()
            os.fsync(output.fileno())
        if not matches(temporary, tool.sha256):
            raise ValueError('OPA SHA-256 mismatch; binary was not executed')
        temporary.chmod(0o755)
        result = subprocess.run([str(temporary.resolve()), 'version'], text=True, capture_output=True, timeout=10)
        if result.returncode or not re.search(r'^Version:\s*' + re.escape(tool.version) + r'\s*$', result.stdout, re.M):
            raise ValueError('OPA version mismatch')
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def install(tool, destination, cache, *, mirror='', offline=False, attempts=3, timeout=120,
            fetch=download, sleep=time.sleep):
    if not 1 <= attempts <= 5 or not 1 <= timeout <= 300:
        raise ValueError('Attempts must be 1..5 and timeout 1..300 seconds')
    routes = locations(tool, mirror)  # Reject invalid mirror configuration even on a cache hit.
    if matches(destination, tool.sha256):
        install_copy(destination, destination, tool)
        return 'installed'
    cached = cache / tool.cache_key / 'opa'
    if cache.is_symlink() or cached.parent.is_symlink():
        raise ValueError('OPA cache directories must not be symlinks')
    if matches(cached, tool.sha256):
        install_copy(cached, destination, tool)
        return 'cache'
    if offline:
        raise ValueError('No checksum-verified OPA available in offline mode')
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.opa-download-', dir=cache) as folder:
        temporary = Path(folder) / 'opa'
        for url, api, label in routes:
            for attempt in range(1, attempts + 1):
                temporary.unlink(missing_ok=True)
                try:
                    fetch(url, temporary, api=api, timeout=timeout)
                    if not matches(temporary, tool.sha256):
                        # A bad response is never executable or cacheable. Move to
                        # another transport instead of repeating corrupt content.
                        print(f'{label}: SHA-256 mismatch; trying another source', flush=True)
                        break
                    install_copy(temporary, destination, tool)
                    try:
                        cached.parent.mkdir(parents=True, exist_ok=True)
                        # Atomic cache population uses the same verification/version gate.
                        install_copy(temporary, cached, tool)
                    except OSError:
                        print('OPA installed and verified; local cache write unavailable', flush=True)
                    return label
                except OSError as exc:
                    reason = str(exc) if isinstance(exc, DownloadError) else type(exc).__name__
                    print(f'{label}: attempt {attempt}/{attempts} failed ({reason})', flush=True)
                    if attempt < attempts:
                        sleep(min(2 ** attempt, 8))
    raise ValueError('OPA unavailable from all configured sources; no unverified binary installed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=ROOT / '.venv-validation/bin/opa')
    parser.add_argument('--cache', type=Path, default=Path(os.environ.get('RUNNER_TOOL_CACHE', str(ROOT / '.local/tool-cache'))) / 'axiom-opa')
    parser.add_argument('--mirror', default=os.environ.get('AXIOM_OPA_MIRROR_URL', ''))
    parser.add_argument('--attempts', type=int, default=3)
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--describe', action='store_true', help='Emit non-sensitive GitHub step outputs without downloading')
    args = parser.parse_args()
    try:
        tool = select_tool()
        if args.describe:
            print(f'cache_key={tool.cache_key}\nversion={tool.version}\nasset={tool.asset}')
            return 0
        origin = install(tool, args.destination, args.cache, mirror=args.mirror, offline=args.offline,
                         attempts=args.attempts, timeout=args.timeout)
        print(f'OPA {tool.version}: verified SHA-256 and version ({origin})')
        return 0
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        print(f'OPA installation failed: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
