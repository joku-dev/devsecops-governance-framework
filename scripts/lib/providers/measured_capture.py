"""Explicit native measured-evidence acquisition and bounded selected ZIP reads.

This is the retained ha-CPsWMS GitHub wire profile, not a second control policy.
No gh command, ambient login or credential from an inspected repository is used.
"""
import base64
import hashlib
import io
from pathlib import Path
import re
import stat
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
import zipfile

from lib.measurement_logic import decode_json
from lib.private_credentials import check_private_file
from lib.provider_errors import AccessFailure
from lib.providers.context import NoRedirect
from lib.providers.transports import Reader
from lib.providers.measured_security import REPOSITORY, check_run
from lib.providers.measured_security import SERVICES, normalize as normalize_security
from lib.providers.measured_l1 import FILES, artifact_binding, normalize
from lib.consumer_intake_store import atomic_json

MAX_MEMBER = 32 * 1024**2
MAX_SELECTED = 128 * 1024**2


def storage_url(url):
    value = urlsplit(url)
    host = (value.hostname or '').lower()
    if (value.scheme != 'https' or value.username or value.password or value.fragment
            or value.port not in (None, 443)
            or not any(host.endswith('.' + suffix) for suffix in
                       ('blob.core.windows.net', 'actions.githubusercontent.com', 'githubusercontent.com'))):
        raise ValueError('invalid_measured_storage_endpoint')
    return url


class RemoteZip(io.RawIOBase):
    """No credentials on storage; exact ranges and one shared request/byte budget."""
    def __init__(self, reader, url, expected_size, accounting):
        self.reader, self.url, self.pos, self.accounting = reader, storage_url(url), 0, accounting
        self.charge()
        with build_opener(NoRedirect).open(Request(self.url, method='HEAD'), timeout=40) as response:
            self.size = int(response.headers['Content-Length'])
            if response.status != 200 or self.size != expected_size or not 0 < self.size <= 512 * 1024**3:
                raise ValueError('measured_archive_size_mismatch')

    def charge(self):
        if self.reader.calls >= self.reader.budget:
            raise AccessFailure('request_budget_exhausted', True)
        self.reader.calls += 1

    def seekable(self):
        return True

    def seek(self, offset, whence=0):
        if whence not in (0, 1, 2):
            raise ValueError('invalid_measured_archive_seek')
        position = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        if not 0 <= position <= self.size:
            raise ValueError('invalid_measured_archive_seek')
        self.pos = position
        return position

    def tell(self):
        return self.pos

    def read(self, size=-1):
        size = self.size - self.pos if size < 0 else min(size, self.size - self.pos)
        if not size:
            return b''
        if size < 0 or size > MAX_MEMBER or self.accounting['bytes'] + size > MAX_SELECTED:
            raise ValueError('measured_archive_range_budget_exhausted')
        self.charge()
        end = self.pos + size - 1
        request = Request(self.url, headers={'Range': f'bytes={self.pos}-{end}'})
        with build_opener(NoRedirect).open(request, timeout=40) as response:
            if (response.status != 206
                    or response.headers.get('Content-Range') != f'bytes {self.pos}-{end}/{self.size}'):
                raise ValueError('measured_archive_range_not_honored')
            raw = response.read(size + 1)
        if len(raw) != size:
            raise ValueError('measured_archive_range_incomplete')
        self.accounting['bytes'] += size
        self.pos += size
        return raw


def selected_files(reader, repository, artifact, names, accounting):
    route = f"/repos/{repository}/actions/artifacts/{artifact['id']}/zip"
    request = Request(reader.url(route), headers=reader.headers)
    try:
        response = build_opener(NoRedirect).open(request, timeout=40)
    except HTTPError as error:
        if error.code != 302:
            raise AccessFailure('measured_artifact_unavailable', error.code >= 500) from None
        location = storage_url(error.headers['Location'])
    else:
        response.close()
        raise ValueError('measured_artifact_redirect_required')
    with zipfile.ZipFile(RemoteZip(reader, location, artifact['size_in_bytes'], accounting)) as archive:
        if len(archive.infolist()) > 10000:
            raise ValueError('measured_artifact_member_limit')
        result = {}
        for name in names:
            matches = [info for info in archive.infolist() if info.filename == name]
            if len(matches) != 1:
                raise ValueError('measured_artifact_member_missing_or_duplicate')
            member = matches[0]
            if (member.is_dir() or member.file_size > MAX_MEMBER or member.flag_bits & 1
                    or stat.S_ISLNK(member.external_attr >> 16)
                    or member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                raise ValueError('unsafe_measured_artifact_member')
            result[name] = archive.read(member)
        return result


def credential_reader(path, repository, budget):
    check_private_file(path)
    if Path(path).stat().st_size > 1024**2:
        raise ValueError('invalid_measured_reader_file')
    credential = decode_json(Path(path).read_bytes())
    if (set(credential) != {'schema_version', 'provider', 'instance', 'repository', 'token'}
            or credential['schema_version'] != 1 or credential['provider'] != 'github-actions'
            or credential['instance'] != 'https://api.github.com'
            or credential['repository'] != repository or repository != REPOSITORY
            or not isinstance(credential['token'], str) or not credential['token'].strip()
            or not 1 <= budget <= 2000):
        raise ValueError('measured_reader_binding_mismatch')
    return Reader(credential['instance'], credential['token'], budget=budget)


def capture(repository, run_id, credential_file, *, budget=500, kind='l1'):
    if repository != REPOSITORY or not re.fullmatch(r'[1-9][0-9]*', str(run_id)):
        raise ValueError('unsupported_measured_repository_or_run')
    reader = credential_reader(credential_file, repository, budget)
    try:
        run = reader.get(f'/repos/{repository}/actions/runs/{run_id}')
        try:
            check_run(run, repository, run_id)
        except ValueError:
            raise ValueError('measured_successful_main_run_required') from None
        listing = reader.get(f'/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100')
        if listing['total_count'] != len(listing['artifacts']):
            raise ValueError('measured_artifact_list_truncated')
        accounting = {'bytes': 0}
        def artifact(name):
            found = [item for item in listing['artifacts'] if item['name'] == name and not item['expired']]
            if len(found) != 1:
                raise ValueError('measured_artifact_identity_ambiguous')
            artifact_binding(found[0], run, name)
            return found[0]
        report_artifact = artifact('l1-control-coverage')
        report = selected_files(reader, repository, report_artifact, ['l1-coverage.json'], accounting)['l1-coverage.json']
        bundles = {}
        required_groups = groups(kind)
        for name, required in required_groups.items():
            item = artifact('l1-' + name)
            bundles[name] = (selected_files(reader, repository, item, ['manifest.json', *required], accounting), item)
        trace = None
        if kind == 'l1':
            content = reader.get(f"/repos/{repository}/contents/quality/traceability.json?ref={run['head_sha']}")
            if content['type'] != 'file' or content['encoding'] != 'base64':
                raise ValueError('measured_traceability_file_required')
            trace = base64.b64decode(''.join(content['content'].split()), validate=True)
            blob = b'blob ' + str(len(trace)).encode() + b'\0' + trace
            # Git object identity requires SHA-1 for this explicit GitHub profile.
            if hashlib.sha1(blob, usedforsecurity=False).hexdigest() != content['sha']:
                raise ValueError('measured_traceability_blob_mismatch')
        captured = (run, report, report_artifact, bundles, trace)
        result = normalize_capture(captured, kind)
        return result, {'requests': reader.calls, 'selected_transport_bytes': accounting['bytes'],
                        'native_metadata_rechecked': True, 'whole_archive_downloaded': False}, captured
    except (HTTPError, URLError, OSError, zipfile.BadZipFile):
        raise AccessFailure('measured_capture_failed', True) from None


def groups(kind):
    if kind == 'l1':
        return FILES
    if kind == 'containers':
        required = ('subject.json', 'vulnerabilities.json', 'vulnerabilities.execution.json')
        return {'image-' + service: required for service in SERVICES}
    raise ValueError('unsupported_measured_kind')


def normalize_capture(captured, kind):
    run, report, artifact, bundles, trace = captured
    if kind == 'l1':
        return normalize(run, report, artifact, bundles, trace)
    if kind == 'containers':
        artifact_binding(artifact, run, 'l1-control-coverage')
        return normalize_security(run, decode_json(report),
                                  {service: bundles['image-' + service] for service in SERVICES})
    raise ValueError('unsupported_measured_kind')


def export_bundle(captured, root, kind):
    """Save selected physical bytes. The manifest contains no reader credential."""
    root = Path(root)
    if root.is_symlink() or root.exists():
        raise ValueError('fresh_measured_bundle_required')
    root.mkdir(mode=0o700, parents=False)
    run, report, artifact, bundles, trace = captured
    files = {}
    def write(relative, raw):
        path = root / relative
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(0o600)
        files[relative] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    write('report/l1-coverage.json', report)
    artifacts = {}
    for name, required in groups(kind).items():
        raw, metadata = bundles[name]
        artifacts[name] = metadata
        for filename in ['manifest.json', *required]:
            write(name + '/' + filename, raw[filename])
    if kind == 'l1':
        write('repository/quality/traceability.json', trace)
    manifest = {'schema_version': 1, 'native_profile': 'ha-cpswms-github-measured-v1',
                'kind': kind, 'run': run, 'report_artifact': artifact,
                'artifacts': artifacts, 'files': files}
    atomic_json(root / 'capture.json', manifest)
    return hashlib.sha256((root / 'capture.json').read_bytes()).hexdigest()


def import_bundle(root, expected_sha256, kind):
    """Local metadata is operator-supplied; this does not recheck native provenance."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir() or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise ValueError('invalid_measured_bundle')
    root = root.resolve()
    def read(relative, limit):
        path = root / relative
        parents = list(path.relative_to(root).parts)
        if (path.is_symlink() or any(root.joinpath(*parents[:i]).is_symlink() for i in range(1, len(parents)))
                or not path.is_file() or path.stat().st_size > limit):
            raise ValueError('unsafe_measured_bundle_file')
        raw = path.read_bytes()
        if len(raw) > limit:
            raise ValueError('measured_bundle_file_limit')
        return raw
    raw = read('capture.json', 4 * 1024**2)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('measured_bundle_manifest_changed')
    manifest = decode_json(raw)
    if (set(manifest) != {'schema_version', 'native_profile', 'kind', 'run', 'report_artifact', 'artifacts', 'files'}
            or manifest['schema_version'] != 1 or manifest['native_profile'] != 'ha-cpswms-github-measured-v1'
            or manifest['kind'] != kind or set(manifest['artifacts']) != set(groups(kind))):
        raise ValueError('invalid_measured_bundle_contract')
    required = {'report/l1-coverage.json'}
    required.update(name + '/' + filename for name, names in groups(kind).items()
                    for filename in ['manifest.json', *names])
    if kind == 'l1':
        required.add('repository/quality/traceability.json')
    if set(manifest['files']) != required:
        raise ValueError('measured_bundle_scope_mismatch')
    physical = {}
    total = 0
    for name in sorted(required):
        record = manifest['files'][name]
        if set(record) != {'bytes', 'sha256'} or type(record['bytes']) is not int or not 0 <= record['bytes'] <= MAX_MEMBER:
            raise ValueError('invalid_measured_bundle_file_record')
        total += record['bytes']
        if total > MAX_SELECTED:
            raise ValueError('measured_bundle_total_limit')
        content = read(name, MAX_MEMBER)
        if len(content) != record['bytes'] or hashlib.sha256(content).hexdigest() != record['sha256']:
            raise ValueError('measured_bundle_bytes_changed')
        physical[name] = content
    bundles = {name: ({filename: physical[name + '/' + filename]
                      for filename in ['manifest.json', *names]}, manifest['artifacts'][name])
               for name, names in groups(kind).items()}
    captured = (manifest['run'], physical['report/l1-coverage.json'], manifest['report_artifact'],
                bundles, physical.get('repository/quality/traceability.json'))
    return normalize_capture(captured, kind)
