#!/usr/bin/env python3
"""Centrally verify five complete image archives from the fixed ha-CPsWMS profile."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.error
import urllib.request
from urllib.parse import urlparse
import zipfile

from intake_measured_security import gh_json, NoRedirect
from intake_evidence_trust_github_actions_run import write_snapshot, TRUST_RESULT_ROOTS
from lib.container_typed_evidence import PROFILE, NAMES, VULNERABILITY_NAMES, MAX_IMAGE, verify_bundle
from lib.measured_security import (
    REPOSITORY,
    ROOT,
    SERVICES,
    check_run,
    normalize as normalize_measured_security,
    store_snapshot as store_measured_security_snapshot,
)
from lib.result_ledger import apply_replay_assessment, load_snapshot_payloads

MAX_ZIP = 1024**3
MAX_SMALL = 32 * 1024**2


def prior_for_evidence_type(snapshots, evidence_type):
    """Prevent distinct evidence types from becoming replay conflicts for one run."""
    return [snapshot for snapshot in snapshots
            if snapshot.get('trust', snapshot).get('capture', {}).get('evidence_type') == evidence_type]


def bind_artifact(artifacts, name, run):
    matches = [a for a in artifacts if a['name'] == name]
    if len(matches) != 1:
        raise ValueError('Expected exactly one artifact: ' + name)
    artifact = matches[0]
    binding = artifact['workflow_run']
    if (artifact['expired'] or str(binding['id']) != str(run['id'])
            or binding['head_sha'] != run['head_sha'] or binding['head_branch'] != 'main'
            or binding['repository_id'] != run['repository']['id']
            or artifact['size_in_bytes'] > MAX_ZIP):
        raise ValueError('Artifact source binding or size mismatch')
    return dict(artifact)


def extract_selected(archive_path, output, names):
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        for name in names:
            entries = [i for i in archive.infolist() if i.filename == name]
            limit = MAX_IMAGE if name == 'image.tar' else MAX_SMALL
            if len(entries) != 1 or entries[0].file_size > limit or (entries[0].external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Missing, duplicate, symlink or oversized artifact member: ' + name)
            with archive.open(entries[0]) as source, (output / name).open('wb') as target:
                total = 0
                while data := source.read(1024**2):
                    total += len(data)
                    if total > limit:
                        raise ValueError('Artifact member exceeds size limit')
                    target.write(data)


def download(artifact, output, names, token):
    url = f'https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{artifact["id"]}/zip'
    request = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token})
    try:
        urllib.request.build_opener(NoRedirect).open(request, timeout=60)
    except urllib.error.HTTPError as error:
        if error.code != 302:
            raise ValueError(f'Artifact download unavailable: HTTP {error.code}') from None
        location = error.headers['Location']
    else:
        raise ValueError('Missing artifact redirect')
    if urlparse(location).scheme != 'https':
        raise ValueError('Artifact download must use HTTPS')
    output.mkdir(parents=True, exist_ok=True)
    archive = output / 'download.zip'
    digest, total = hashlib.sha256(), 0
    # Never forward the GitHub credential to artifact blob storage.
    with urllib.request.urlopen(location, timeout=120) as source, archive.open('wb') as target:  # nosec B310: signed URL is HTTPS and receives no credential.
        while data := source.read(1024**2):
            total += len(data)
            if total > MAX_ZIP:
                raise ValueError('Artifact ZIP exceeds size limit')
            digest.update(data)
            target.write(data)
    if total != artifact['size_in_bytes']:
        raise ValueError('Artifact ZIP size differs from GitHub metadata')
    actual = digest.hexdigest()
    if artifact.get('digest') and artifact['digest'] != 'sha256:' + actual:
        raise ValueError('Artifact ZIP digest differs from GitHub metadata')
    artifact['verified_zip_sha256'] = actual
    extract_selected(archive, output, names)
    archive.unlink()


def capture(run_id):
    run = gh_json(f'repos/{REPOSITORY}/actions/runs/{run_id}')
    check_run(run, REPOSITORY, run_id)
    listing = gh_json(f'repos/{REPOSITORY}/actions/runs/{run_id}/artifacts?per_page=100')
    artifacts = listing['artifacts']
    if listing['total_count'] != len(artifacts):
        raise ValueError('Truncated artifact listing')
    token = os.environ.get('GH_RESULT_INTAKE_TOKEN') or os.environ.get('GH_TOKEN') or subprocess.check_output(['gh','auth','token'], text=True).strip()
    with tempfile.TemporaryDirectory(prefix='ha-typed-trust-') as temp:
        root = Path(temp)
        coverage = bind_artifact(artifacts, 'l1-control-coverage', run)
        download(coverage, root/'coverage', ['l1-coverage.json', 'typed-evidence-manifest.json'], token)
        report = json.loads((root/'coverage/l1-coverage.json').read_text())
        declaration = json.loads((root/'coverage/typed-evidence-manifest.json').read_text())
        names = NAMES if declaration.get('profile') == PROFILE else VULNERABILITY_NAMES
        bundles, paths = {}, {}
        for service in SERVICES:
            artifact = bind_artifact(artifacts, 'l1-image-' + service, run)
            path = root/service
            download(artifact, path, ['manifest.json', *names], token)
            raw_names = ('manifest.json', 'subject.json', 'vulnerabilities.json', 'vulnerabilities.execution.json')
            raw = {name: (path/name).read_bytes() for name in raw_names}
            bundles[service], paths[service] = (raw, artifact), path
            print('Downloaded full image evidence: ' + service, flush=True)
        verified_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        trusts = verify_bundle(run, report, declaration, bundles, paths, verified_at)
        measured_security = normalize_measured_security(run, report, bundles)
        measured_security_path = store_measured_security_snapshot(
            ROOT / 'status/measured-security-results',
            measured_security,
        )
        prior = load_snapshot_payloads(TRUST_RESULT_ROOTS)
        outputs = [measured_security_path]
        for trust in trusts.values():
            trust['capture']['source']['artifact_digest'] = coverage['verified_zip_sha256']
            evidence_type = trust['capture']['evidence_type']
            same_type_prior = prior_for_evidence_type(prior, evidence_type)
            trust = apply_replay_assessment(trust, same_type_prior)
            outputs.append(write_snapshot(repository_id=REPOSITORY, run=run, artifact=coverage, trust=trust,
                archive_sha256=coverage['verified_zip_sha256']))
        return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True, type=int)
    args = parser.parse_args()
    for output in capture(args.run_id):
        print(output)


if __name__ == '__main__':
    main()
