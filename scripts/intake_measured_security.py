#!/usr/bin/env python3
"""Capture verified report bytes from a successful measured L1 main run (report-only)."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import io
import json
import subprocess
import urllib.error
import urllib.request
from urllib.parse import urlparse
import zipfile

from lib.measured_security import ROOT, REPOSITORY, SERVICES, check_run, normalize, store_snapshot

MAX_FILE_BYTES = 32 * 1024 * 1024


def gh_json(endpoint):
    return json.loads(subprocess.check_output(['gh', 'api', endpoint], text=True))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


class RemoteZip(io.RawIOBase):
    """Read selected ZIP members; intentionally does not claim a whole-archive digest check."""
    def __init__(self, url):
        if urlparse(url).scheme != 'https':
            raise ValueError('Artifact download must use HTTPS')
        self.url, self.pos = url, 0
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=40) as response:
            self.size = int(response.headers['Content-Length'])

    def seekable(self):
        return True

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        return self.pos

    def tell(self):
        return self.pos

    def read(self, size=-1):
        size = self.size - self.pos if size < 0 else min(size, self.size - self.pos)
        if not size:
            return b''
        if size < 0 or size > MAX_FILE_BYTES:
            raise ValueError('Artifact range exceeds size limit')
        end = self.pos + size - 1
        request = urllib.request.Request(self.url, headers={'Range': f'bytes={self.pos}-{end}'})
        with urllib.request.urlopen(request, timeout=40) as response:
            if response.status != 206 or response.headers.get('Content-Range') != f'bytes {self.pos}-{end}/{self.size}':
                raise ValueError('Artifact server did not honor byte range')
            data = response.read(size + 1)
        if len(data) != size:
            raise ValueError('Incomplete artifact range')
        self.pos += size
        return data


def selected_files(repository, artifact, names, token):
    # Obtain a signed URL without forwarding the GitHub credential to blob storage.
    url = f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact['id']}/zip"
    request = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token})
    try:
        urllib.request.build_opener(NoRedirect).open(request, timeout=40)
    except urllib.error.HTTPError as error:
        if error.code != 302:
            raise ValueError(f'Artifact download unavailable: HTTP {error.code}') from None
        location = error.headers['Location']
    else:
        raise ValueError('Missing artifact redirect')
    with zipfile.ZipFile(RemoteZip(location)) as archive:
        results = {}
        for name in names:
            matches = [info for info in archive.infolist() if info.filename == name]
            if len(matches) != 1 or matches[0].file_size > MAX_FILE_BYTES:
                raise ValueError('Missing, duplicate or oversized artifact member: ' + name)
            results[name] = archive.read(matches[0])  # ZIP CRC + producer-manifest SHA-256 below.
        return results


def capture(repository, run_id):
    run = gh_json(f'repos/{repository}/actions/runs/{run_id}')
    check_run(run, repository, run_id)
    artifacts = gh_json(f'repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100')['artifacts']
    token = subprocess.check_output(['gh', 'auth', 'token'], text=True).strip()

    def artifact(name):
        matches = [a for a in artifacts if a['name'] == name and not a['expired']]
        if len(matches) != 1:
            raise ValueError('Expected one non-expired artifact: ' + name)
        a = matches[0]
        if (str(a['workflow_run']['id']) != str(run_id) or a['workflow_run']['head_sha'] != run['head_sha']
                or a['workflow_run']['repository_id'] != run['repository']['id']):
            raise ValueError('Artifact source binding mismatch')
        return a

    report_artifact = artifact('l1-control-coverage')
    report = json.loads(selected_files(repository, report_artifact, ['l1-coverage.json'], token)['l1-coverage.json'])

    def image(service):
        a = artifact('l1-image-' + service)
        return service, (selected_files(repository, a, ['manifest.json', 'subject.json',
            'vulnerabilities.json', 'vulnerabilities.execution.json'], token), a)

    with ThreadPoolExecutor(max_workers=5) as pool:
        bundles = dict(pool.map(image, SERVICES))
    return normalize(run, report, bundles)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default=REPOSITORY, choices=[REPOSITORY])
    parser.add_argument('--run-id', required=True, type=int)
    args = parser.parse_args()
    item = capture(args.repository, args.run_id)
    path = store_snapshot(ROOT / 'status/measured-security-results', item)
    print(f'Captured {path.relative_to(ROOT)}: {item["counts"]["CRITICAL"]} critical, {item["counts"]["HIGH"]} high (report-only)')


if __name__ == '__main__':
    main()
