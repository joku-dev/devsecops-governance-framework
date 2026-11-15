"""Private general result snapshots with indexed V1 replay and append semantics.

Native reads and operator declarations occupy separate histories. Repository
names remain descriptive; native IDs and instance origins define identities.
This ledger never writes accepted product status or confers operating authority.
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
from lib.result_ledger import (apply_replay_assessment, evidence_identity,
    evidence_identities_compatible, replay_context, replay_key, subject_digests)

APPLICATION_ID = 0x41585253
MAX_RECORD = 16 * 1024**2
MAX_PAGE = 128 * 1024**2
MAX_REPLAY_ROWS = 10000
ORIGINS = ('operator_bundle', 'native_reader')
DOMAINS = ('devsecops', 'architecture')


def explicit_time(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('explicit_result_timezone_required')
    return parsed


def logical_identity(value):
    identity = evidence_identity(value)
    if isinstance(identity.get('context'), dict):
        identity = deepcopy(identity)
        identity['context'].pop('artifact_digest', None)
    return canonical_digest(identity)


def decode_record(row):
    value = decode_json(row['payload'])
    descriptor = decode_json(row['descriptor'])
    if (canonical_digest(value) != row['digest']
            or canonical_digest(descriptor) != row['descriptor_digest']
            or repository_key(descriptor) != row['repository']
            or descriptor.get('path') != value['repository_id']
            or logical_identity(value) != row['logical_identity']):
        raise ValueError('result_ledger_payload_changed')
    return value


class ResultLedger:
    def __init__(self, root):
        self.root = Path(root).absolute()
        if any(path.is_symlink() for path in (self.root, *self.root.parents)):
            raise ValueError('unsafe_result_ledger_root')
        private_directory(self.root)
        path = self.root / 'results.sqlite3'
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError('unsafe_result_ledger_database')
        self.db = sqlite3.connect(path, timeout=30)
        self.db.row_factory = sqlite3.Row
        path.chmod(0o600)
        try:
            self.db.execute('BEGIN IMMEDIATE')
            version = self.db.execute('PRAGMA user_version').fetchone()[0]
            application = self.db.execute('PRAGMA application_id').fetchone()[0]
            tables = self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if version == application == 0 and not tables:
                statements = f'''
                CREATE TABLE repositories (key TEXT PRIMARY KEY, realm TEXT NOT NULL, identity TEXT NOT NULL);
                CREATE TABLE records (repository TEXT NOT NULL REFERENCES repositories(key),
                    realm TEXT NOT NULL, origin TEXT NOT NULL, domain TEXT NOT NULL,
                    slot TEXT NOT NULL, digest TEXT NOT NULL, payload TEXT NOT NULL,
                    descriptor TEXT NOT NULL, descriptor_digest TEXT NOT NULL, display_path TEXT NOT NULL,
                    assessment TEXT NOT NULL, assessed_at TEXT NOT NULL, produced_at REAL NOT NULL,
                    logical_identity TEXT NOT NULL, context_digest TEXT,
                    PRIMARY KEY(repository,origin,domain,slot));
                CREATE INDEX result_identity ON records(repository,origin,domain,logical_identity);
                CREATE INDEX result_context ON records(realm,origin,domain,context_digest);
                CREATE INDEX result_alias ON records(realm,origin,domain,display_path);
                CREATE TABLE subjects (realm TEXT NOT NULL, origin TEXT NOT NULL, domain TEXT NOT NULL,
                    digest TEXT NOT NULL, repository TEXT NOT NULL, slot TEXT NOT NULL,
                    FOREIGN KEY(repository,origin,domain,slot) REFERENCES records(repository,origin,domain,slot));
                CREATE INDEX result_subject_digest ON subjects(realm,origin,domain,digest);
                CREATE TABLE conflicts (key TEXT PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL);
                PRAGMA application_id={APPLICATION_ID};
                PRAGMA user_version=1;
                '''
                for statement in statements.split(';'):
                    if statement.strip(): self.db.execute(statement)
            elif version != 1 or application != APPLICATION_ID:
                raise ValueError('incompatible_result_ledger_schema')
            self.db.commit()
        except sqlite3.DatabaseError:
            self.db.close()
            raise ValueError('invalid_result_ledger_database') from None
        except BaseException:
            self.db.rollback(); self.db.close(); raise
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA journal_mode=WAL')

    def close(self):
        self.db.close()

    def relevant_history(self, realm, origin, domain, trust):
        """Select exactly the contexts/digests that can affect the V1 replay rule."""
        if replay_key(trust) is None:
            return []
        digests = sorted(set(subject_digests(trust).values()))
        if len(digests) > 128:
            raise ValueError('result_replay_subject_limit')
        condition = 'context_digest=?'
        parameters = [realm, origin, domain, canonical_digest(replay_context(trust))]
        if digests:
            condition += f''' OR (repository,slot) IN (SELECT repository,slot FROM subjects
                WHERE realm=? AND origin=? AND domain=? AND digest IN ({','.join('?' for _ in digests)}))'''
            parameters += [realm, origin, domain, *digests]
        query = 'SELECT * FROM records WHERE realm=? AND origin=? AND domain=? AND (' + condition + ')'
        history = []; size = 0
        for row in self.db.execute(query + ' ORDER BY repository,slot', parameters):
            size += len(row['payload'].encode())
            if len(history) >= MAX_REPLAY_ROWS or size > MAX_PAGE:
                raise ValueError('result_replay_history_budget_exhausted')
            history.append(decode_record(row))
        return history

    def admit(self, repository, snapshots, *, origin, assessment_id, at):
        if origin not in ORIGINS or not snapshots or set(snapshots) - set(DOMAINS):
            raise ValueError('invalid_result_intake_scope')
        explicit_time(at)
        if not isinstance(assessment_id, str) or len(assessment_id) != 64 or any(c not in '0123456789abcdef' for c in assessment_id):
            raise ValueError('invalid_result_assessment_id')
        key = repository_key(repository)
        core = {name: repository[name] for name in ('provider', 'native_id')}
        core['instance'] = endpoint(repository['instance'])
        realm = canonical_digest({name: core[name] for name in ('provider', 'instance')})
        encoded_core = json.dumps(core, sort_keys=True)
        validator = Draft202012Validator(read_json(ROOT / 'schemas/axiom-v2-result-snapshot.schema.json'), format_checker=FormatChecker())
        for domain, value in snapshots.items():
            validator.validate(value)
            kind = 'governance-baseline-run' if domain == 'devsecops' else 'architecture-runtime-governance-run'
            if (value['result_type'] != kind or value['repository_id'] != repository.get('path')
                    or 'model_id' in value):
                raise ValueError('result_snapshot_subject_mismatch')
            explicit_time(value['generated_at'])
            if len(json.dumps(value).encode()) > MAX_RECORD:
                raise ValueError('result_intake_record_limit')
        results = {}
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old_core = self.db.execute('SELECT identity FROM repositories WHERE key=?', (key,)).fetchone()
            if old_core and old_core['identity'] != encoded_core:
                raise ValueError('result_native_repository_mapping_changed')
            self.db.execute('INSERT OR IGNORE INTO repositories VALUES (?,?,?)', (key, realm, encoded_core))
            for domain, snapshot in sorted(snapshots.items()):
                value = deepcopy(snapshot)
                if isinstance(value.get('trust'), dict):
                    trust = apply_replay_assessment(value['trust'], self.relevant_history(realm, origin, domain, value['trust']))
                    aliases = sorted({row['repository'] for row in self.db.execute('''SELECT DISTINCT repository
                        FROM records WHERE realm=? AND origin=? AND domain=? AND display_path=? AND repository!=?''',
                        (realm, origin, domain, value['repository_id'], key))})
                    if aliases:
                        check = next(item for item in trust['checks'] if item['id'] == 'replay_key_unique')
                        check.update(result='fail', reason='The display repository identity was reused by a different native repository.',
                                     related_native_repository_keys=aliases)
                    trust['effective_level'] = promote_effective_level(trust.get('effective_level', 'unverified'), trust['checks'], root=ROOT)
                    value['trust'] = trust
                # Preserve the V1 target collision rule without using input strings as paths.
                timestamp = value['generated_at'].replace(':', '-').replace('+', '-')
                slot = canonical_digest({'timestamp': timestamp, 'run': value['pipeline']['pipeline_run_id']})
                logical = logical_identity(value)
                # First compatible identity wins across target timestamps, as in V1.
                existing_row = None
                for row in self.db.execute('''SELECT * FROM records WHERE repository=? AND origin=?
                        AND domain=? AND logical_identity=? ORDER BY slot''', (key, origin, domain, logical)):
                    if evidence_identities_compatible(decode_record(row), value):
                        existing_row = row; break
                if existing_row:
                    results[domain] = self.record_receipt(existing_row, 'idempotent')
                    continue
                existing_row = self.db.execute('''SELECT * FROM records WHERE repository=? AND origin=?
                    AND domain=? AND slot=?''', (key, origin, domain, slot)).fetchone()
                digest = canonical_digest(value)
                if existing_row:
                    existing = decode_record(existing_row)
                    conflict = {'schema_version': 1, 'kind': 'result-append-only-conflict',
                        'repository_key': key, 'origin': origin, 'domain': domain, 'identity': slot,
                        'existing_payload_digest': existing_row['digest'], 'incoming_payload_digest': digest,
                        'existing_evidence_identity': evidence_identity(existing), 'incoming_evidence_identity': evidence_identity(value),
                        'assessment_id': assessment_id, 'assessed_at': at, 'mode': 'report-only', 'official_acceptance': False}
                    conflict_key = canonical_digest({k: v for k, v in conflict.items() if k not in ('assessment_id', 'assessed_at')})
                    self.db.execute('INSERT OR IGNORE INTO conflicts VALUES (?,?,?)',
                        (conflict_key, json.dumps(conflict, sort_keys=True), canonical_digest(conflict)))
                    results[domain] = {'status': 'conflict', 'identity': slot, 'conflict_id': conflict_key,
                                       'existing_payload_digest': existing_row['digest']}
                    continue
                context = canonical_digest(replay_context(value['trust'])) if isinstance(value.get('trust'), dict) else None
                self.db.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (key, realm, origin, domain, slot, digest, json.dumps(value, sort_keys=True), json.dumps(repository, sort_keys=True),
                     canonical_digest(repository), value['repository_id'], assessment_id, at,
                     explicit_time(value['generated_at']).timestamp(), logical, context))
                if context is not None:
                    for subject in sorted(set(subject_digests(value['trust']).values())):
                        self.db.execute('INSERT INTO subjects VALUES (?,?,?,?,?,?)', (realm, origin, domain, subject, key, slot))
                row = self.db.execute('SELECT * FROM records WHERE repository=? AND origin=? AND domain=? AND slot=?',
                                      (key, origin, domain, slot)).fetchone()
                results[domain] = self.record_receipt(row, 'recorded')
            self.db.commit()
        except BaseException:
            self.db.rollback(); raise
        return {'repository_key': key, 'origin': origin, 'results': results, 'mode': 'report-only', 'official_acceptance': False}

    @staticmethod
    def record_receipt(row, status):
        value = decode_record(row)
        reported = value.get('trust', {}).get('effective_level', 'unverified')
        return {'status': status, 'identity': row['slot'], 'payload_digest': row['digest'],
                'assessment_id': row['assessment'], 'reported_trust': reported,
                'effective_trust': reported if row['origin'] == 'native_reader' else 'unverified'}

    def records(self, *, origin, domain, limit=100, offset=0, realm=None):
        if origin not in ORIGINS or domain not in DOMAINS or type(limit) is not int or not 1 <= limit <= 1000 or type(offset) is not int or offset < 0:
            raise ValueError('invalid_result_index_page')
        condition = 'origin=? AND domain=?'; parameters = [origin, domain]
        if realm is not None:
            condition += ' AND realm=?'; parameters.append(realm)
        count = self.db.execute('SELECT count(*) FROM records WHERE ' + condition, parameters).fetchone()[0]
        rows = []; size = 0
        for row in self.db.execute('SELECT * FROM records WHERE ' + condition + ' ORDER BY repository,slot LIMIT ? OFFSET ?',
                                   [*parameters, limit, offset]):
            size += len(row['payload'].encode())
            if size > MAX_PAGE: raise ValueError('result_index_page_budget_exhausted')
            value = decode_record(row)
            descriptor = decode_json(row['descriptor'])
            if repository_key(descriptor) != row['repository'] or descriptor.get('path') != value['repository_id']:
                raise ValueError('result_ledger_descriptor_changed')
            rows.append({**self.record_receipt(row, 'recorded'), 'repository_key': row['repository'],
                'repository': descriptor, 'origin': origin, 'domain': domain, 'payload': value})
        return {'record_count': count, 'records': rows, 'limit': limit, 'offset': offset, 'official_acceptance': False}
