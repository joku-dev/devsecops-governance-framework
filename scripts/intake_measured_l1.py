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
from lib.control_evidence_assurance import (
    RESULT_ROOT as ASSURANCE_ROOT,
    build_assurance,
    store_snapshot as store_assurance_snapshot,
)


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
    # nosemgrep: python.lang.security.insecure-hash-algorithms.insecure-hash-algorithm-sha1 -- Git object IDs require SHA-1 here.
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
    typed = []
    for typed_path in sorted((ROOT / 'status/typed-evidence-results').rglob('*.json')):
        payload = json.loads(typed_path.read_text(encoding='utf-8'))
        if (payload.get('repository_id') == item['repository_id']
                and payload.get('pipeline', {}).get('pipeline_run_id') == item['run']['id']
                and payload.get('pipeline', {}).get('run_attempt') == item['run']['attempt']
                and payload.get('repository', {}).get('commit_id') == item['run']['commit']):
            payload['_source_file'] = typed_path.relative_to(ROOT).as_posix()
            typed.append(payload)
    assurance = build_assurance(
        item,
        typed,
        measured_source_file=path.relative_to(ROOT).as_posix(),
    )
    assurance_path = store_assurance_snapshot(ASSURANCE_ROOT, assurance)
    print(f'Captured {path.relative_to(ROOT)}: {json.dumps(item["summary"])} (report-only)')
    print(f'Captured {assurance_path.relative_to(ROOT)}: {json.dumps(assurance["summary"])} (report-only)')


if __name__ == '__main__':
    main()
