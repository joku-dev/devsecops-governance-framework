"""Atomic private typed intake with opaque repository/realm identities.

V1 replay/identity rules are shared unchanged. Operator replays and native reads
occupy separate histories so a supplied bundle cannot preempt a native receipt.
No record here is an official governance or operating approval.
"""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import sqlite3

from jsonschema import Draft202012Validator, FormatChecker

from lib.candidate_workspace import private_directory
from lib.evidence_verification import promote_effective_level
from lib.measurement_logic import decode_json
from lib.portable.contracts import ROOT, canonical_digest, endpoint, repository_key
from lib.portable.runtime import read_json
from lib.result_ledger import (apply_replay_assessment, evidence_identities_compatible,
                               evidence_identity)

MAX_RECORD = 16 * 1024**2
MAX_HISTORY = 128 * 1024**2
APPLICATION_ID = 0x41585459


class TypedLedger:
    def __init__(self, root):
        self.root = Path(root).absolute()
        if any(p.is_symlink() for p in (self.root, *self.root.parents)):
            raise ValueError('unsafe_typed_ledger_root')
        private_directory(self.root)
        database = self.root / 'typed.sqlite3'
        if database.is_symlink() or (database.exists() and not database.is_file()):
            raise ValueError('unsafe_typed_ledger_database')
        self.db = sqlite3.connect(database, timeout=30)
        self.db.row_factory = sqlite3.Row
        database.chmod(0o600)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            version = self.db.execute('PRAGMA user_version').fetchone()[0]
            application = self.db.execute('PRAGMA application_id').fetchone()[0]
            tables = self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if version == application == 0 and not tables:
                statements = f'''
                CREATE TABLE repositories (key TEXT PRIMARY KEY, realm TEXT NOT NULL, identity TEXT NOT NULL);
                CREATE TABLE records (repository TEXT NOT NULL REFERENCES repositories(key),
                    realm TEXT NOT NULL, origin TEXT NOT NULL, kind TEXT NOT NULL,
                    identity TEXT NOT NULL, digest TEXT NOT NULL, payload TEXT NOT NULL,
                    assessment TEXT NOT NULL, assessed_at TEXT NOT NULL,
                    produced_at REAL NOT NULL, run_sort TEXT NOT NULL, attempt INTEGER NOT NULL,
                    PRIMARY KEY(repository,origin,kind,identity));
                CREATE INDEX typed_history ON records(realm,origin,kind);
                CREATE TABLE conflicts (key TEXT PRIMARY KEY, repository TEXT NOT NULL,
                    origin TEXT NOT NULL, kind TEXT NOT NULL, identity TEXT NOT NULL,
                    record TEXT NOT NULL);
                PRAGMA application_id={APPLICATION_ID};
                PRAGMA user_version=1;
                '''
                for statement in statements.split(';'):
                    if statement.strip():
                        self.db.execute(statement)
            elif version != 1 or application != APPLICATION_ID:
                raise ValueError('incompatible_typed_ledger_schema')
            self.db.commit()
        except BaseException:
            self.db.rollback()
            self.db.close()
            raise
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA journal_mode=WAL')

    def close(self):
        self.db.close()

    def _history(self, realm, origin, kind):
        # Keep the original within-realm V1 replay semantics; never compare native
        # identifiers from unrelated providers/instances or operator/native stores.
        count, size = self.db.execute('''SELECT count(*),coalesce(sum(length(cast(payload AS BLOB))),0)
            FROM records WHERE realm=? AND origin=? AND kind=?''', (realm, origin, kind)).fetchone()
        if count > 10000 or size > MAX_HISTORY:
            raise ValueError('typed_replay_history_budget_exhausted')
        values = []
        for row in self.db.execute('''SELECT payload,digest,repository FROM records
                WHERE realm=? AND origin=? AND kind=? ORDER BY repository,identity''', (realm, origin, kind)):
            value = decode_json(row['payload'])
            if canonical_digest(value) != row['digest']:
                raise ValueError('typed_ledger_payload_changed')
            value['_native_repository_key'] = row['repository']
            values.append(value)
        return values

    def admit(self, repository, snapshots, *, origin, assessment_id, at):
        if origin not in ('operator_bundle', 'native_reader'):
            raise ValueError('invalid_typed_intake_origin')
        if datetime.fromisoformat(at.replace('Z', '+00:00')).tzinfo is None:
            raise ValueError('explicit_typed_timezone_required')
        if not isinstance(assessment_id, str) or len(assessment_id) != 64 or any(c not in '0123456789abcdef' for c in assessment_id):
            raise ValueError('invalid_typed_assessment_id')
        if not snapshots or set(snapshots) - {'sbom', 'vulnerability_scan'}:
            raise ValueError('invalid_typed_intake_scope')
        key = repository_key(repository)
        realm = canonical_digest({'provider': repository['provider'], 'instance': endpoint(repository['instance'])})
        encoded_identity = json.dumps(repository, sort_keys=True)
        validator = Draft202012Validator(read_json(ROOT / 'schemas/typed-evidence-result.schema.json'),
                                         format_checker=FormatChecker())
        for kind, value in snapshots.items():
            validator.validate(value)
            if (value['evidence_type'] != kind or value['repository_id'] != repository['path']
                    or value['pipeline']['event'] != 'push' or value['repository']['branch'] != 'main'):
                raise ValueError('typed_mainline_subject_required')
            if len(json.dumps(value).encode()) > MAX_RECORD:
                raise ValueError('typed_intake_record_limit')
        results = {}
        self.db.execute('BEGIN IMMEDIATE')
        try:
            current = self.db.execute('SELECT identity FROM repositories WHERE key=?', (key,)).fetchone()
            if current and current['identity'] != encoded_identity:
                raise ValueError('typed_native_repository_mapping_changed')
            self.db.execute('INSERT OR IGNORE INTO repositories VALUES (?,?,?)', (key, realm, encoded_identity))
            for kind, snapshot in sorted(snapshots.items()):
                value = deepcopy(snapshot)
                prior = self._history(realm, origin, kind)
                value['trust'] = apply_replay_assessment(value['trust'], prior)
                aliases = {row['_native_repository_key'] for row in prior
                    if row['_native_repository_key'] != key and row['repository_id'] == value['repository_id']}
                if aliases:
                    check = next(row for row in value['trust']['checks'] if row['id'] == 'replay_key_unique')
                    check.update(result='fail', reason='The display repository identity was reused by a different native repository.',
                                 related_native_repository_keys=sorted(aliases))
                value['trust']['effective_level'] = promote_effective_level(
                    value['trust']['effective_level'], value['trust']['checks'], root=ROOT)
                identity = canonical_digest({'repository': key, 'kind': kind,
                    'run_id': value['pipeline']['pipeline_run_id'], 'attempt': value['pipeline']['run_attempt']})
                old = self.db.execute('''SELECT payload,digest,assessment FROM records
                    WHERE repository=? AND origin=? AND kind=? AND identity=?''',
                    (key, origin, kind, identity)).fetchone()
                digest = canonical_digest(value)
                status = 'recorded'
                if old:
                    existing = decode_json(old['payload'])
                    if evidence_identities_compatible(existing, value):
                        # Keep first verification time, Trust and source receipt.
                        value, digest, status = existing, old['digest'], 'idempotent'
                    else:
                        conflict = {'schema_version': 1, 'kind': 'typed-append-only-conflict',
                            'repository_key': key, 'origin': origin, 'evidence_type': kind,
                            'identity': identity, 'existing_payload_digest': old['digest'],
                            'incoming_payload_digest': digest,
                            'existing_evidence_identity': evidence_identity(existing),
                            'incoming_evidence_identity': evidence_identity(value),
                            'assessed_at': at, 'assessment_id': assessment_id,
                            'official_acceptance': False, 'mode': 'report-only'}
                        conflict_key = canonical_digest({k: v for k, v in conflict.items() if k not in ('assessed_at', 'assessment_id')})
                        self.db.execute('INSERT OR IGNORE INTO conflicts VALUES (?,?,?,?,?,?)',
                            (conflict_key, key, origin, kind, identity, json.dumps(conflict, sort_keys=True)))
                        results[kind] = {'status': 'conflict', 'identity': identity,
                            'conflict_id': conflict_key, 'existing_payload_digest': old['digest']}
                        continue
                else:
                    self.db.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                        (key, realm, origin, kind, identity, digest, json.dumps(value, sort_keys=True), assessment_id, at,
                         datetime.fromisoformat(value['generated_at'].replace('Z', '+00:00')).timestamp(),
                         value['pipeline']['pipeline_run_id'], value['pipeline']['run_attempt']))
                results[kind] = {'status': status, 'identity': identity, 'payload_digest': digest,
                    'reported_trust': value['trust']['effective_level'],
                    'effective_trust': value['trust']['effective_level'] if origin == 'native_reader' else 'unverified'}
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        return {'repository_key': key, 'origin': origin, 'results': results,
                'official_acceptance': False, 'mode': 'report-only'}

    def projection(self, *, limit=100, offset=0):
        if type(limit) is not int or type(offset) is not int or not 1 <= limit <= 1000 or offset < 0:
            raise ValueError('invalid_typed_index_page')
        items = []
        page_bytes = 0
        for row in self.db.execute('''SELECT r.*,p.identity AS repository_identity FROM records r
                JOIN repositories p ON p.key=r.repository ORDER BY r.repository,r.origin,r.kind,r.identity LIMIT ? OFFSET ?''',
                (limit, offset)):
            page_bytes += len(row['payload'].encode())
            if page_bytes > MAX_HISTORY:
                raise ValueError('typed_index_page_budget_exhausted')
            value = decode_json(row['payload'])
            if canonical_digest(value) != row['digest']:
                raise ValueError('typed_ledger_payload_changed')
            items.append({'repository_key': row['repository'], 'repository': decode_json(row['repository_identity']),
                'origin': row['origin'], 'evidence_type': row['kind'], 'identity': row['identity'],
                'payload_digest': row['digest'], 'assessment_id': row['assessment'],
                'payload': value, 'effective_trust': value['trust']['effective_level']
                if row['origin'] == 'native_reader' else 'unverified'})
        # Native and replay latest are deliberately separate. Trust does not
        # change chronological result selection or any underlying outcome.
        latest = self.db.execute('''SELECT repository,origin,kind,identity FROM (
            SELECT repository,origin,kind,identity,row_number() OVER (
                PARTITION BY repository,origin,kind ORDER BY produced_at DESC,run_sort DESC,attempt DESC,identity) AS row_order
            FROM records) WHERE row_order=1 ORDER BY repository,origin,kind''').fetchall()
        return {'schema_version': 1, 'kind': 'private-typed-evidence-index',
            'official_acceptance': False, 'mode': 'report-only', 'records': items,
            'limit': limit, 'offset': offset,
            'record_count': self.db.execute('SELECT count(*) FROM records').fetchone()[0],
            'latest': [{'repository_key': row['repository'], 'origin': row['origin'],
                       'evidence_type': row['kind'], 'identity': row['identity']} for row in latest],
            'conflict_count': self.db.execute('SELECT count(*) FROM conflicts').fetchone()[0]}
