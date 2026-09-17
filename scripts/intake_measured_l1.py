#!/usr/bin/env python3
"""Verify and retain a report-only L1 assessment from existing ha-CPsWMS raw artifacts."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import subprocess

from intake_measured_security import gh_json, selected_files
from lib.measured_security import ROOT, REPOSITORY, check_run
from lib.measured_l1 import FILES, artifact_binding, normalize, store_snapshot


def capture(repository, run_id):
    run = gh_json(f'repos/{repository}/actions/runs/{run_id}')
    check_run(run, repository, run_id)
    listing = gh_json(f'repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100')
    if listing['total_count'] != len(listing['artifacts']):
        raise ValueError('Artifact list truncated; cannot uniquely bind evidence')
    artifacts = listing['artifacts']
    token = subprocess.check_output(['gh', 'auth', 'token'], text=True).strip()
    def artifact(name):
        found = [a for a in artifacts if a['name'] == name and not a['expired']]
        if len(found) != 1:
            raise ValueError('Expected one available artifact: ' + name)
        artifact_binding(found[0], run, name)
        return found[0]
    report_artifact = artifact('l1-control-coverage')
    report_raw = selected_files(repository, report_artifact, ['l1-coverage.json'], token)['l1-coverage.json']
    def fetch(name):
        a = artifact('l1-' + name)
        return name, (selected_files(repository, a, ['manifest.json', *FILES[name]], token), a)
    with ThreadPoolExecutor(max_workers=5) as pool:
        bundles = dict(pool.map(fetch, FILES))
    content = gh_json(f"repos/{repository}/contents/quality/traceability.json?ref={run['head_sha']}")
    if content['type'] != 'file' or content['encoding'] != 'base64':
        raise ValueError('Traceability is not a committed file')
    raw = base64.b64decode(content['content'])
    # Git blob identity verifies the source file returned at the exact commit.
    blob = b'blob ' + str(len(raw)).encode() + b'\0' + raw
    if hashlib.sha1(blob, usedforsecurity=False).hexdigest() != content['sha']:
        raise ValueError('Traceability Git blob identity mismatch')
    return normalize(run, report_raw, report_artifact, bundles, raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default=REPOSITORY, choices=[REPOSITORY])
    parser.add_argument('--run-id', type=int, required=True)
    args = parser.parse_args()
    item = capture(args.repository, args.run_id)
    path = store_snapshot(ROOT / 'status/measured-l1-results', item)
    print(f'Captured {path.relative_to(ROOT)}: {json.dumps(item["summary"])} (report-only)')


if __name__ == '__main__':
    main()
