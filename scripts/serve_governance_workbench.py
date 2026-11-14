#!/usr/bin/env python3
"""Authenticated loopback workbench. Repository writes occur only in a PR worktree."""
from __future__ import annotations

import argparse
import base64
import binascii
from datetime import datetime, timezone
import hashlib
import hmac
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from functools import wraps
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlparse
import zipfile

import jsonschema
import yaml
from lib.source_document_text import extract_source_document, SourceDocumentExtractionError
from generate_source_document_requirement_delta import extract_requirements, compare_requirements
from generate_source_document_process_status import build_report
from lib.document_consistency_view import project_public
from lib.explicit_requirements import is_requirement_id
from lib.workbench_impact import ImpactProjection

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).resolve().parent / 'workbench'
REGISTER = 'model/documents/source-document-register.yaml'
MAX_UPLOAD = 5 * 1024 * 1024
MAX_BODY = 8 * 1024 * 1024
ID_PATTERN = re.compile(r'^[A-Z0-9]+(?:-[A-Z0-9]+)*-[0-9]{3}$')
DRAFT_PATTERN = re.compile(r'^[0-9a-f]{32}$')
DOMAIN_SET = {'policy', 'directive', 'devsecops', 'platform', 'architecture'}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def current_requirements(data):
    return [row for row in data.get('requirements', [])
            if row.get('identification_class') in {'author_identified', 'explicit_identifier'}
            and any(is_requirement_id(value) for value in row.get('recognized_requirement_ids', [row.get('source_requirement_id', '')]))]


def preparation_summary(data):
    current = current_requirements(data)
    latest = {note['subject']: note for note in data['notes']}
    unnoted = [row['source_requirement_id'] for row in current if row['id'] not in latest]
    clarification = [row['source_requirement_id'] for row in current
                     if latest.get(row['id'], {}).get('outcome') == 'needs_clarification']
    return ('\n## Local preparation (proposal-only)\n\n'
            f'Explicit requirements: {len(current)}; with item notes: {len(current) - len(unnoted)}.\n\n'
            f'Without item notes: {", ".join(unnoted) or "none"}.\n\n'
            f'Clarification required: {", ".join(clarification) or "none"}.\n\n'
            'These counts do not confirm complete extraction, requirement approval or source authority.\n')


def read_json(path):
    return json.loads(path.read_text()) if path.is_file() else {}


def atomic_json(path, value):
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def run(args, cwd, timeout=30):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        # Never propagate subprocess stderr, which may contain credentials or source text.
        raise ValueError('Repository operation failed; inspect the local checkout and Git authentication.')
    return result.stdout.strip()


def serialized_request(method):
    @wraps(method)
    def handle(self):
        # A browser's idle/preconnected socket must not hold this lock. Headers
        # are read before do_GET/do_POST; actual session/draft operations remain
        # serialized so concurrent note requests cannot overwrite one another.
        with self.server.request_lock:
            return method(self)
    return handle


class Workbench:
    def __init__(self, root=ROOT, state_dir=None, enable_pr=False):
        self.root = Path(root).resolve()
        self.state_dir = Path(state_dir or self.root / '.local/governance-workbench').resolve()
        # Existing extraction uses repository-relative source locations. Keep drafts inside the checkout.
        self.state_dir.relative_to(self.root)
        self.state_dir.relative_to((self.root / '.local/governance-workbench').resolve())
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.state_dir, 0o700)
        self.enable_pr = enable_pr

    def register(self):
        return yaml.safe_load((self.root / REGISTER).read_text())

    def source_path(self, source):
        path = (self.root / source['source_path']).resolve()
        path.relative_to((self.root / 'docs/governance/source-documents').resolve())
        return path

    def head(self):
        return run(['git', 'rev-parse', 'HEAD'], self.root)

    def context(self):
        return {'commit': self.head(), 'register_sha256': digest((self.root / REGISTER).read_bytes()),
                'sources': {x['id']: digest(self.source_path(x).read_bytes()) for x in self.register()['documents']
                            if self.source_path(x).is_file()}}

    def document(self, source_id):
        for source in self.register()['documents']:
            if source['id'] == source_id:
                return source
        raise ValueError('Unknown registered source')

    def inspect(self, source):
        path = self.source_path(source)
        extracted = extract_source_document(path)
        origin = source.get('requirement_identifier_origin', self.register().get('requirement_identifier_origin_default', 'unverified'))
        detail = {'source': source, 'sha256': digest(path.read_bytes()),
                'lines': [vars(x) for x in extracted.lines], 'warnings': list(extracted.warnings),
                'requirements': extract_requirements(source['id'], path, origin),
                'formal_status': self.formal_status(source, digest(path.read_bytes())),
                'extraction_limit': 'Only explicitly labelled requirements (for example DSCB-L1-REQ-001); no prose inference. Identifier provenance and source authority still require review.'}
        detail['implementation'] = self.implementation(detail)
        return detail

    def implementation(self, data):
        return ImpactProjection(self.root).project(data['source'], data.get('sha256'),
                                                  data.get('requirements', []), self.register()['documents'])

    def requirement_history(self, source_id):
        source = next((s for s in self.register()['documents'] if s['id'] == source_id), None)
        current_hash = digest(self.source_path(source).read_bytes()) if source and self.source_path(source).is_file() else None
        directory = self.root / 'model/requirements/lifecycle-cases'
        cases = []
        for path in sorted(directory.glob('*.json')):
            case = read_json(path)
            binding = case.get('source', {})
            if binding.get('source_id') != source_id:
                continue
            cases.append({'path': str(path.relative_to(self.root)), 'case_id': case['case_id'],
                          'status': case['status'], 'source': binding,
                          'source_matches': bool(source) and binding.get('source_sha256') == current_hash
                          and binding.get('source_path') == source['source_path'],
                          'proposals': case.get('proposals', [])})
        if source is None and not cases:
            raise ValueError('Unknown registered source')
        return {'source_id': source_id, 'available': directory.is_dir(), 'cases': cases}

    def formal_status(self, source, source_hash):
        """Read recorded decisions for an exact source binding, not review progress."""
        directory = self.root / 'model/requirements/lifecycle-cases'
        matching, other = [], 0
        for path in sorted(directory.glob('*.json')):
            case = read_json(path)
            binding = case.get('source', {})
            if binding.get('source_id') != source['id']:
                continue
            if (source_hash and binding.get('source_sha256') == source_hash
                    and binding.get('source_path') == source['source_path']):
                matching.extend(case.get('proposals', []))
            else:
                other += 1
        return {'recorded_proposals': len(matching),
                'recorded_decisions': sum(bool(p.get('decision')) for p in matching),
                'recorded_activations': sum(bool(p.get('activation')) for p in matching),
                'open_historical_proposals': sum(not p.get('decision') for p in matching),
                'other_source_cases': other, 'source_sha256': source_hash,
                'authority': 'recorded_history_only'}

    def source_review(self, payload):
        source_id = payload.get('source_id')
        if not isinstance(source_id, str):
            raise ValueError('Choose a registered source')
        context = self.context()
        detail = self.inspect(self.document(source_id))
        if context != self.context() or detail['sha256'] != context['sources'][source_id]:
            raise ValueError('Source changed while preparing review; refresh and try again')
        data = {'schema_version': '1.0.0', 'draft_id': secrets.token_hex(16), 'kind': 'source_review',
                'created_at': now(), 'status': 'local_draft', 'context': context,
                'source': detail['source'], 'sha256': detail['sha256'],
                'original_filename': Path(detail['source']['source_path']).name,
                'lines': detail['lines'], 'warnings': detail['warnings'],
                'requirements': detail['requirements'], 'target': None, 'deltas': [],
                'notes': [], 'pr': None,
                'limits': ['Registered-source review preparation only; source status and recorded lifecycle decisions remain unchanged.',
                           'Item notes and preparation progress are proposal-only, not requirement or source approval.']}
        folder = self.state_dir / data['draft_id']
        folder.mkdir(mode=0o700)
        try:
            self.save(folder, data)
        except Exception:
            shutil.rmtree(folder)
            raise
        return self.draft(data['draft_id'])

    def draft_dir(self, draft_id):
        if not DRAFT_PATTERN.fullmatch(draft_id):
            raise ValueError('Invalid draft identifier')
        path = self.state_dir / draft_id
        if not (path / 'draft.json').is_file():
            raise ValueError('Unknown draft')
        return path

    def draft(self, draft_id):
        data = read_json(self.draft_dir(draft_id) / 'draft.json')
        context = self.context()
        old = data['context']
        reasons = []
        if old['commit'] != context['commit']:
            reasons.append({'code': 'repository_changed', 'previous': old['commit'], 'current': context['commit']})
        if old['register_sha256'] != context['register_sha256']:
            reasons.append({'code': 'register_changed', 'previous': old['register_sha256'], 'current': context['register_sha256']})
        registered = {s['id']: s for s in self.register()['documents']}
        for source_id in sorted(set(old['sources']) | set(context['sources']) | set(registered)):
            previous, current = old['sources'].get(source_id), context['sources'].get(source_id)
            if source_id in registered and current is None:
                reasons.append({'code': 'source_missing', 'source_id': source_id, 'previous': previous, 'current': None})
            elif previous != current:
                reasons.append({'code': 'source_changed', 'source_id': source_id, 'previous': previous, 'current': current})
        data['stale'] = bool(reasons) or old != context
        if data['kind'] == 'source_review':
            source_id = data['source']['id']
            current_source = registered.get(source_id)
            if data['source'] != current_source:
                reasons.append({'code': 'source_metadata_changed', 'source_id': source_id})
            data['stale'] = (data['stale'] or data['source'] != current_source
                             or data['sha256'] != context['sources'].get(source_id))
        if data['kind'] == 'source_candidate':
            uploaded = self.draft_dir(draft_id) / data['upload_name']
            current_hash = digest(uploaded.read_bytes()) if uploaded.is_file() else None
            if current_hash != data['sha256']:
                reasons.append({'code': 'uploaded_source_missing' if current_hash is None else 'uploaded_source_changed',
                                'previous': data['sha256'], 'current': current_hash})
                data['stale'] = True
        # Additive response-only diagnostics; old drafts and notes stay byte-identical.
        data['stale_details'] = {'reasons': reasons, 'current_commit': context['commit']}
        data['formal_status'] = self.formal_status(data['source'], data.get('sha256')) if data.get('source') else None
        if data.get('source'):
            data['implementation'] = self.implementation(data)
        if data.get('target'):
            data['target']['implementation'] = self.implementation(data['target'])
        return data

    def state(self):
        context = self.context()
        drafts = [self.draft(p.name) for p in sorted(self.state_dir.iterdir()) if p.is_dir() and DRAFT_PATTERN.fullmatch(p.name) and (p / 'draft.json').is_file()]
        # Existing readiness generator is read-only and uses the same repository checkout.
        process = build_report() if self.root == ROOT else read_json(self.root / 'generated/reports/source-document-process-status.json')
        projection = project_public(self.root) if (self.root / 'status/document-consistency-public-projection.json').is_file() else {}
        return {'context': context, 'documents': self.register()['documents'], 'drafts': drafts,
                'process': process, 'dcr': projection,
                'briefs': read_json(self.root / 'generated/reports/source-document-intake-review-briefs.json').get('review_briefs', []),
                'pr_enabled': self.enable_pr and shutil.which('gh') is not None,
                'limits': ['Single local maintainer session; no enterprise role authentication.',
                           'Reports retain their original generated timestamps and may be partial or stale.',
                           'No semantic provider execution, source promotion or baseline approval.']}

    def create_draft(self, payload):
        metadata = payload.get('metadata', {})
        if not isinstance(metadata, dict):
            raise ValueError('Metadata must be an object')
        source_id = metadata.get('id', '')
        if not isinstance(source_id, str) or not ID_PATTERN.fullmatch(source_id):
            raise ValueError('Source ID must use uppercase segments and a three-digit suffix')
        if source_id in {x['id'] for x in self.register()['documents']}:
            raise ValueError('Use a new source ID for a version candidate; existing source history is preserved')
        for field in ('title', 'owner', 'version'):
            if not isinstance(metadata.get(field), str) or not 1 <= len(metadata[field].strip()) <= 200:
                raise ValueError(f'{field} is required (maximum 200 characters)')
        domains = metadata.get('governance_domains', [])
        if not isinstance(domains, list) or not domains or any(not isinstance(x, str) or x not in DOMAIN_SET for x in domains):
            raise ValueError('Choose at least one supported governance domain')
        replacement = metadata.get('replacement_for', '')
        if not isinstance(replacement, str):
            raise ValueError('Replacement source must be a registered source ID')
        if replacement:
            self.document(replacement)
        filename = payload.get('filename', '')
        if not isinstance(filename, str) or Path(filename).name != filename or '\\' in filename:
            raise ValueError('Filename must not contain a path')
        suffix = Path(filename).suffix.lower()
        if suffix not in {'.md', '.markdown', '.docx', '.pdf'}:
            raise ValueError('Supported formats: Markdown, DOCX, PDF')
        try:
            raw = base64.b64decode(payload.get('content_base64', ''), validate=True)
        except (ValueError, binascii.Error, TypeError) as exc:
            raise ValueError('Invalid upload encoding') from exc
        if not raw or len(raw) > MAX_UPLOAD:
            raise ValueError('File must contain data and be at most 5 MiB')
        if suffix == '.docx':
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    sizes = [x.file_size for x in archive.infolist()]
                    if len(sizes) > 1000 or sum(sizes) > 20 * 1024 * 1024:
                        raise ValueError('DOCX exceeds decompressed size limits')
            except zipfile.BadZipFile as exc:
                raise ValueError('Invalid DOCX package') from exc
        draft_id = secrets.token_hex(16)
        folder = self.state_dir / draft_id
        folder.mkdir(mode=0o700)
        upload = folder / ('source' + suffix)
        upload.write_bytes(raw)
        os.chmod(upload, 0o600)
        try:
            extraction = extract_source_document(upload)
            requirements = extract_requirements(source_id, upload)
            target = self.inspect(self.document(replacement)) if replacement else None
            if target:
                target.pop('formal_status', None)  # A live projection is not part of the saved predecessor.
                target.pop('implementation', None)
            deltas = compare_requirements(requirements, target['requirements']) if target else []
            entry = {'id': source_id, 'title': metadata['title'].strip(), 'owner': metadata['owner'].strip(),
                     'version': metadata['version'].strip(), 'governance_domains': sorted(set(domains)),
                     'status': 'candidate', 'source_path': f'docs/governance/source-documents/{source_id}{suffix}',
                     'intake_date': now()[:10], 'supersedes': None, 'derived_artifact_areas': [],
                     'requirement_identifier_origin': 'unverified', 'candidate_replacement_for': [replacement] if replacement else [],
                     'similarity_assessment': {'assessment': 'replacement_candidate' if replacement else 'not_assessed', 'compared_to': []},
                     'notes': 'Workbench candidate. No source authority, requirement confirmation or derivation is authorized.'}
            jsonschema.validate({'schema_version': '1.0.0', 'documents': [entry]}, read_json(self.root / 'schemas/source-document-register.schema.json'))
            data = {'schema_version': '1.0.0', 'draft_id': draft_id, 'kind': 'source_candidate', 'created_at': now(),
                    'status': 'local_draft', 'source': entry, 'original_filename': filename, 'upload_name': upload.name,
                    'sha256': digest(raw), 'context': self.context(), 'warnings': list(extraction.warnings),
                    'lines': [vars(x) for x in extraction.lines], 'requirements': requirements, 'deltas': deltas,
                    'target': target, 'notes': [], 'pr': None,
                    'limits': ['Only explicitly labelled requirements are extracted; prose, synthetic row IDs and reference-only mentions do not create requirements.',
                               'Local draft is not registered or approved. Notes are decision proposals only.']}
            self.save(folder, data)
            return data
        except Exception:
            shutil.rmtree(folder)
            raise

    @staticmethod
    def persisted(data):
        clean = {k: v for k, v in data.items() if k not in {'stale', 'stale_details', 'formal_status', 'implementation'}}
        if clean.get('target'):
            clean['target'] = {k: v for k, v in clean['target'].items() if k not in {'formal_status', 'implementation'}}
        return clean

    def save(self, folder, data):
        clean = self.persisted(data)
        jsonschema.validate(clean, read_json(self.root / 'schemas/governance-workbench-draft.schema.json'))
        atomic_json(folder / 'draft.json', clean)

    def note(self, draft_id, payload):
        folder = self.draft_dir(draft_id)
        data = self.draft(draft_id)
        if data['stale']:
            raise ValueError('Repository changed. Create a fresh draft/package before recording proposals.')
        if data['pr']:
            raise ValueError('A PR has already been submitted. Continue review in that PR.')
        fields = {k: payload.get(k, '').strip() if isinstance(payload.get(k, ''), str) else '' for k in ('subject', 'reviewer', 'outcome', 'rationale')}
        if not all(fields.values()) or any(len(v) > 4000 for v in fields.values()):
            raise ValueError('Subject, reviewer, outcome and rationale are required (maximum 4000 characters)')
        if fields['outcome'] not in {'confirm_candidate', 'reject_candidate', 'needs_clarification', 'propose_resolution'}:
            raise ValueError('Unsupported proposal outcome')
        allowed = {x['id'] for x in current_requirements(data)} | {'source'}
        if data['kind'] == 'review_package':
            allowed = {x['source_id'] for x in data['manifest']}
        if fields['subject'] not in allowed:
            raise ValueError('Proposal must refer to a current item in this exact package; historical entries are read-only')
        fields.update({'recorded_at': now(), 'authority': 'proposal_only'})
        data['notes'].append(fields)
        self.save(folder, data)
        return self.draft(draft_id)

    def review_package(self, payload):
        ids = payload.get('source_ids')
        if not isinstance(ids, list) or not ids or len(ids) > 30 or any(not isinstance(x, str) for x in ids) or len(set(ids)) != len(ids):
            raise ValueError('Choose a non-empty, unique source set')
        manifest = []
        for sid in sorted(ids):
            source = self.document(sid)
            detail = self.inspect(source)
            manifest.append({'source_id': sid, 'source_path': source['source_path'], 'status': source['status'],
                             'version': source['version'], 'owner': source['owner'], 'sha256': detail['sha256'],
                             'warnings': detail['warnings'], 'requirements_count': len(detail['requirements'])})
        data = {'schema_version': '1.0.0', 'draft_id': secrets.token_hex(16), 'kind': 'review_package',
                'created_at': now(), 'status': 'local_draft', 'context': self.context(), 'manifest': manifest,
                'manifest_sha256': digest(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()),
                'execution': 'not_run', 'notes': [], 'pr': None,
                'limits': ['Preparation only. Separate authorization must bind provider/model, data flow, retention, scope, reviewer and cost limit.',
                           'This is a workbench scope package, not an approved DCR manifest or baseline decision.']}
        folder = self.state_dir / data['draft_id']
        folder.mkdir(mode=0o700)
        self.save(folder, data)
        return data

    def packet_files(self, draft_id):
        data = self.draft(draft_id)
        if data['stale']:
            if any(r['code'].startswith('uploaded_source_') for r in data['stale_details']['reasons']):
                raise ValueError('Local upload bytes changed or are missing; prepare a fresh draft')
            raise ValueError('Package is stale; repository identity or source bytes changed')
        files = {'workbench-package.json': json.dumps(self.persisted(data), ensure_ascii=False, indent=2).encode()}
        notes = '\n'.join(f"- {x['subject']}: {x['outcome']} ({x['reviewer']}) — {x['rationale']}" for x in data['notes']) or '- No proposal recorded.'
        if data['kind'] == 'source_candidate':
            source = data['source']
            uploaded = (self.draft_dir(draft_id) / data['upload_name']).read_bytes()
            if digest(uploaded) != data['sha256']:
                raise ValueError('Local upload bytes changed; prepare a fresh draft')
            register = self.register()
            if source['id'] in {x['id'] for x in register['documents']} or (self.root / source['source_path']).exists():
                raise ValueError('Candidate ID/path already exists')
            register['documents'].append(source)
            files[source['source_path']] = uploaded
            files[REGISTER] = yaml.safe_dump(register, sort_keys=False, allow_unicode=True).encode()
            title = source['title'].replace('\n', ' ')
            summary = f'Candidate intake: {title}\n\nSource ID: `{source["id"]}`\n\nSHA-256: `{data["sha256"]}`'
        elif data['kind'] == 'source_review':
            source = data['source']
            original = self.source_path(source).read_bytes()
            if digest(original) != data['sha256']:
                raise ValueError('Registered source changed; prepare a fresh review')
            files[source['source_path']] = original
            summary = (f'Registered source review: {source["id"]}\n\n'
                       f'Existing version: `{source["version"]}`\n\nSHA-256: `{data["sha256"]}`\n\n'
                       'Existing source bytes and source authority are retained; no new-source register proposal.')
        else:
            summary = 'Review scope preparation only. No semantic review has run.\n\n' + '\n'.join(f'- `{x["source_id"]}`: `{x["sha256"]}` ({x["status"]})' for x in data['manifest'])
        gcr = (f'# Workbench Change Proposal\n\n{summary}\n\n## State and authority\n\n'
               'Candidate / proposal only. No promotion, supersession, source approval, semantic execution, baseline approval or governance derivation.\n\n'
               f'Base commit: `{data["context"]["commit"]}`\n\n## Review notes (unconfirmed proposals)\n\n{notes}\n\n'
               f'{preparation_summary(data) if data.get("source") else ""}\n'
               '## Validation before merge\n\nRun `./scripts/bootstrap_validation_env.sh` and `./scripts/validate_all.sh`. '
               'Inspect extraction warnings, source authority, lineage, requirement decisions and exact review scope. '
               'A PR merge admitting a candidate does not approve the source.\n')
        files[f'docs/governance/change-requests/GCR-WB-{draft_id}.md'] = gcr.encode()
        files['README.txt'] = ('Private decision-support package. Inspect every byte before copying into a repository or submitting a PR. '
                               'workbench-package.json and this README are local packet metadata, not normative repository artifacts.').encode()
        return files

    def packet(self, draft_id):
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, content in self.packet_files(draft_id).items():
                archive.writestr(name, content)
        return output.getvalue()

    def submit_pr(self, draft_id, payload):
        if not self.enable_pr or not shutil.which('gh'):
            raise ValueError('PR adapter is disabled. Start with --enable-pr and an authenticated GitHub CLI, or export the package.')
        if payload.get('confirm_publication') is not True:
            raise ValueError('Explicit source publication confirmation is required')
        data = self.draft(draft_id)
        if data.get('pr'):
            return data['pr']
        files = self.packet_files(draft_id)
        if run(['git', 'status', '--porcelain', '--untracked-files=no'], self.root):
            raise ValueError('PR publication requires a clean tracked checkout. Commit or restore unrelated edits first.')
        repository = run(['gh', 'repo', 'view', '--json', 'nameWithOwner,defaultBranchRef'], self.root)
        info = json.loads(repository)
        base = info['defaultBranchRef']['name']
        # Reject stale remote base instead of overwriting another maintainer's register edits.
        remote = run(['git', 'ls-remote', 'origin', f'refs/heads/{base}'], self.root).split()[0]
        if remote != data['context']['commit']:
            raise ValueError('Remote default branch differs from this draft. Update checkout and prepare a fresh package.')
        branch = f'workbench/intake-{draft_id}'
        worktree = self.state_dir / f'pr-{draft_id}'
        if worktree.exists():
            raise ValueError('A prior PR attempt exists. Inspect/recover it manually before retrying; do not publish twice.')
        run(['git', 'worktree', 'add', '-b', branch, str(worktree), data['context']['commit']], self.root)
        for name, content in files.items():
            if name in {'workbench-package.json', 'README.txt'}:
                continue
            dest = worktree / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
        run(['git', 'add', '--', 'docs/governance/change-requests'], worktree)
        if data['kind'] == 'source_candidate':
            run(['git', 'add', '--', REGISTER, data['source']['source_path']], worktree)
        run(['git', 'commit', '-m', 'Prepare workbench candidate and review proposals'], worktree)
        run(['git', 'push', 'origin', branch], worktree, 60)
        body = worktree / '.workbench-pr-body.txt'
        body.write_text('Guided candidate intake / review preparation. Human review remains required.\n\n'
                        'Report-only; no promotion, enforcement, semantic execution or baseline release.\n\n'
                        'Local complete validation has not been run by the webapp. Run required CI and inspect original sources before merging.\n')
        url = run(['gh', 'pr', 'create', '--repo', info['nameWithOwner'], '--base', base, '--head', branch, '--draft',
                   '--title', 'Workbench: candidate intake and review preparation', '--body-file', str(body)], worktree, 60)
        body.unlink()
        pr = {'url': url, 'branch': branch, 'commit': run(['git', 'rev-parse', 'HEAD'], worktree)}
        data['pr'] = pr
        self.save(self.draft_dir(draft_id), data)
        return pr


class Handler(BaseHTTPRequestHandler):
    server_version = 'AXIOMWorkbench/1'

    def setup(self):
        super().setup()
        self.connection.settimeout(15)
    def log_message(self, *args):
        pass  # Avoid logging paths, source metadata or session credentials.

    def send(self, status, value, mime='application/json'):
        raw = json.dumps(value, ensure_ascii=False).encode() if mime == 'application/json' else value
        self.send_response(status)
        self.send_header('Content-Type', mime + ('; charset=utf-8' if mime.startswith('text/') else ''))
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if getattr(self, 'new_cookie', None):
            self.send_header('Set-Cookie', self.new_cookie)
        self.end_headers()
        self.wfile.write(raw)

    def boundary(self):
        host = self.headers.get('Host', '')
        if host not in self.server.allowed_hosts:
            self.send(403, {'error': 'Invalid local host'})
            return False
        return True

    def session(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
        except Exception:
            return None
        sid = cookie.get('axiom_session')
        value = self.server.sessions.get(sid.value) if sid else None
        if value and value['expires'] > time.time():
            return value
        return None

    @serialized_request
    def do_GET(self):
        if not self.boundary():
            return
        path = urlparse(self.path).path
        static = {
            '/': (ASSETS / 'index.html', 'text/html'),
            '/app.js': (ASSETS / 'app.js', 'text/javascript'),
            '/requirement-review.js': (ASSETS / 'requirement-review.js', 'text/javascript'),
            '/workspace-navigation.js': (ASSETS / 'workspace-navigation.js', 'text/javascript'),
            '/style.css': (ASSETS / 'style.css', 'text/css'),
            '/axiom-logo.png': (ROOT / 'docs/publishing/branding/axiom-logo.png', 'image/png'),
        }
        if path in static:
            asset, mime = static[path]
            return self.send(200, asset.read_bytes(), mime)
        session = self.session()
        if not session:
            return self.send(401, {'error': 'Sign in with the local access key'})
        try:
            if path == '/api/state':
                return self.send(200, {**self.server.workbench.state(), 'csrf': session['csrf']})
            history = re.fullmatch(r'/api/sources/([A-Z0-9-]+)/history', path)
            if history:
                return self.send(200, self.server.workbench.requirement_history(history[1]))
            if path.startswith('/api/sources/'):
                return self.send(200, self.server.workbench.inspect(self.server.workbench.document(path.rsplit('/', 1)[1])))
            match = re.fullmatch(r'/api/drafts/([0-9a-f]{32})(/packet)?', path)
            if match:
                if match[2]:
                    return self.send(200, self.server.workbench.packet(match[1]), 'application/zip')
                return self.send(200, self.server.workbench.draft(match[1]))
            self.send(404, {'error': 'Not found'})
        except (ValueError, OSError, SourceDocumentExtractionError) as exc:
            self.send(409, {'error': str(exc)})

    @serialized_request
    def do_POST(self):
        if not self.boundary():
            return
        if self.headers.get('Origin') not in self.server.allowed_origins:
            return self.send(403, {'error': 'Same-origin requests required'})
        if self.headers.get('Content-Type') != 'application/json':
            return self.send(415, {'error': 'JSON required'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY:
                raise ValueError('Request exceeds size limit')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('JSON object required')
        except (ValueError, UnicodeDecodeError):
            return self.send(400, {'error': 'Invalid or oversized request'})
        path = urlparse(self.path).path
        if path == '/api/login':
            if time.time() < self.server.login_retry_after:
                return self.send(429, {'error': 'Please wait before trying again'})
            key = payload.get('key', '')
            if not isinstance(key, str) or not hmac.compare_digest(key, self.server.access_key):
                self.server.login_retry_after = time.time() + 2
                return self.send(401, {'error': 'Invalid access key'})
            self.server.sessions = {k: v for k, v in self.server.sessions.items() if v['expires'] > time.time()}
            sid = secrets.token_urlsafe(32)
            self.server.sessions[sid] = {'csrf': secrets.token_urlsafe(32), 'expires': time.time() + 8 * 3600}
            self.new_cookie = f'axiom_session={sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'
            return self.send(200, {'signed_in': True})
        session = self.session()
        if not session:
            return self.send(401, {'error': 'Sign in required'})
        if not hmac.compare_digest(self.headers.get('X-CSRF-Token', ''), session['csrf']):
            return self.send(403, {'error': 'Invalid request token'})
        try:
            if path == '/api/logout':
                self.server.sessions.clear()
                self.new_cookie = 'axiom_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'
                return self.send(200, {'signed_in': False})
            if path == '/api/drafts':
                return self.send(201, self.server.workbench.create_draft(payload))
            if path == '/api/source-reviews':
                return self.send(201, self.server.workbench.source_review(payload))
            if path == '/api/review-packages':
                return self.send(201, self.server.workbench.review_package(payload))
            match = re.fullmatch(r'/api/drafts/([0-9a-f]{32})/(notes|pr)', path)
            if match:
                operation = self.server.workbench.note if match[2] == 'notes' else self.server.workbench.submit_pr
                return self.send(200, operation(match[1], payload))
            self.send(404, {'error': 'Not found'})
        except (ValueError, OSError, SourceDocumentExtractionError, jsonschema.ValidationError, subprocess.TimeoutExpired) as exc:
            # Parser and validation errors must not expose source content in browser error messages.
            message = str(exc) if isinstance(exc, ValueError) and not isinstance(exc, jsonschema.ValidationError) else 'Operation failed; inspect local input and repository validation.'
            self.send(409, {'error': message})


def make_server(workbench, key, port=8765):
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.request_lock = threading.RLock()
    actual_port = server.server_address[1]
    server.workbench = workbench
    server.access_key = key
    server.sessions = {}
    server.login_retry_after = 0
    server.allowed_hosts = {f'127.0.0.1:{actual_port}', f'localhost:{actual_port}'}
    server.allowed_origins = {'http://' + x for x in server.allowed_hosts}
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--enable-pr', action='store_true', help='Enable explicit publication through local GitHub CLI authentication')
    args = parser.parse_args()
    os.umask(0o077)
    key = os.environ.get('AXIOM_WORKBENCH_KEY') or secrets.token_urlsafe(24)
    if len(key) < 24:
        parser.error('AXIOM_WORKBENCH_KEY must contain at least 24 characters')
    server = make_server(Workbench(enable_pr=args.enable_pr), key, args.port)
    print(f'AXIOM Workbench: http://127.0.0.1:{server.server_address[1]}', flush=True)
    if 'AXIOM_WORKBENCH_KEY' not in os.environ:
        print(f'Local access key: {key}', flush=True)
    print('Local drafts only. Ctrl+C to stop. No automatic semantic execution or source approval.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
