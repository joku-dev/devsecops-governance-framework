"""SQLite v2 namespace, opaque queue identities and atomic replay receipts."""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

from lib.consumer_intake_store import atomic_json, backup, verify_backup, file_digest
from lib.portable.contracts import canonical_digest, execution_key, repository_key

SCHEMA = 2


class Store:
    def __init__(self, root, *, create=True):
        self.root = Path(root)
        if self.root.is_symlink():
            raise ValueError('unsafe_operations_root')
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        database = self.root / 'queue.sqlite3'
        if database.is_symlink():
            raise ValueError('unsafe_operations_database')
        self.db = sqlite3.connect(database, timeout=30)
        database.chmod(0o600)
        self.db.row_factory = sqlite3.Row
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        tables = {row[0] for row in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if version != SCHEMA:
            if version != 0 or tables or not create:
                self.db.close()
                raise ValueError('explicit_state_migration_required')
            self.initialize()
        if 'jobs' in tables:
            marker=self.root/'migration.json'
            if not marker.is_file() or marker.is_symlink() or json.loads(marker.read_text()).get('status')!='candidate':
                self.db.close()
                raise ValueError('incomplete_state_migration')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA foreign_keys=ON')

    def initialize(self):
        self.db.executescript('''
          BEGIN IMMEDIATE;
          CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
          CREATE TABLE executions (
            key TEXT PRIMARY KEY, repository_key TEXT NOT NULL, context TEXT NOT NULL,
            state TEXT NOT NULL, discovered_at REAL NOT NULL, next_at REAL NOT NULL DEFAULT 0,
            retries INTEGER NOT NULL DEFAULT 0, error TEXT, receipt TEXT, batch TEXT);
          CREATE INDEX portable_runnable ON executions(state,next_at,discovered_at,key);
          CREATE TABLE receipts (key TEXT PRIMARY KEY, digest TEXT NOT NULL, receipt TEXT NOT NULL);
          CREATE TABLE portable_batches (
            id TEXT PRIMARY KEY, base TEXT NOT NULL, state TEXT NOT NULL, manifest TEXT NOT NULL,
            commit_sha TEXT, change_id TEXT, url TEXT, target TEXT NOT NULL);
          CREATE UNIQUE INDEX portable_one_batch ON portable_batches((1)) WHERE state IN ('prepared','open');
          CREATE TABLE legacy_mapping (kind TEXT NOT NULL, legacy_key TEXT NOT NULL,
            new_key TEXT NOT NULL, record TEXT NOT NULL, PRIMARY KEY(kind,legacy_key));
          PRAGMA user_version=2;
          COMMIT;
        ''')

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def history(self):
        return {row['key']:row['digest'] for row in self.db.execute('SELECT key,digest FROM receipts')}

    def record(self, receipt):
        """Every valid import consumes its unique processing/replay slot.

        Re-import does not replace a prior receipt or raise historical Trust. A conflicting
        payload for the same execution fails even if the caller's earlier history was stale.
        """
        from .bundle import validate_v2
        validate_v2('receipt',receipt)
        if execution_key(receipt['producer']) != receipt['execution_key']:
            raise ValueError('receipt_identity_mismatch')
        with self.transaction():
            old = self.db.execute('SELECT digest,receipt FROM receipts WHERE key=?', (receipt['execution_key'],)).fetchone()
            if old:
                if old['digest'] != receipt['bundle_digest']:
                    raise ValueError('execution_content_conflict')
                return json.loads(old['receipt']), False
            self.db.execute('INSERT INTO receipts VALUES (?,?,?)',
                            (receipt['execution_key'], receipt['bundle_digest'], json.dumps(receipt,sort_keys=True)))
            return receipt, True

    def discover(self, context, *, at, completed=True):
        key, repo = execution_key(context), repository_key(context['scm'])
        payload = json.dumps(context, sort_keys=True)
        with self.transaction():
            existing = self.db.execute('SELECT context,state FROM executions WHERE key=?', (key,)).fetchone()
            if existing and existing['context'] != payload:
                raise ValueError('execution_identity_conflict')
            if not existing:
                self.db.execute('INSERT INTO executions(key,repository_key,context,state,discovered_at) VALUES (?,?,?,?,?)',
                                (key,repo,payload,'queued' if completed else 'waiting',at))
            elif completed and existing['state']=='waiting':
                self.db.execute("UPDATE executions SET state='queued' WHERE key=?", (key,))
        return key

    def claim(self, *, at):
        with self.transaction():
            row = self.db.execute("SELECT * FROM executions WHERE state='queued' AND next_at<=? ORDER BY discovered_at,key LIMIT 1",(at,)).fetchone()
            if row:
                self.db.execute("UPDATE executions SET state='working' WHERE key=?",(row['key'],))
            return dict(row) if row else None

    def recover(self):
        # Caller holds the single worker lock; no second live worker is displaced.
        with self.transaction():
            self.db.execute("UPDATE executions SET state='queued' WHERE state='working'")

    def finish(self, key, receipt):
        job=self.db.execute('SELECT context FROM executions WHERE key=?',(key,)).fetchone()
        if not job or key!=receipt['execution_key'] or json.loads(job['context'])!=receipt['producer']:
            raise ValueError('queue_receipt_binding_mismatch')
        saved, _ = self.record(receipt)
        with self.transaction():
            self.db.execute('UPDATE executions SET state=?,receipt=?,error=NULL WHERE key=?',
                            ('verified' if saved['candidate_eligible'] else 'held',json.dumps(saved,sort_keys=True),key))

    def fail(self, key, code, *, at, retryable=False, delay=60):
        with self.transaction():
            row = self.db.execute('SELECT retries FROM executions WHERE key=?',(key,)).fetchone()
            if not row:
                raise ValueError('execution_not_found')
            count = row['retries'] + 1
            self.db.execute('UPDATE executions SET retries=?,state=?,error=?,next_at=? WHERE key=?',
                            (count,'queued' if retryable and count<=3 else 'held',code,at+min(delay*2**(count-1),86400),key))

    def counts(self):
        return dict(self.db.execute('SELECT state,count(*) FROM executions GROUP BY state'))


def migrate_legacy(root, mapping, destination, *, fault=None):
    """Stopped-writer, backup-first v1 -> v2 migration; original history stays byte intact.

    Caller holds BOTH legacy poll/worker locks. The original root is never changed.
    The destination is a candidate restored from a verified consistent backup. Activation
    is separate. An interrupted candidate is discarded/recreated; it cannot become active.
    Every legacy file/meta/batch/job receives a provider-bound mapping, not a fabricated job.
    """
    from lib.portable.contracts import endpoint
    root, destination = Path(root), Path(destination)
    if not (root/'queue.sqlite3').is_file() or root.is_symlink() or (root/'queue.sqlite3').is_symlink():
        raise ValueError('existing_legacy_database_required')
    allowed={'queue.sqlite3','queue.sqlite3-shm','queue.sqlite3-wal','raw','verified','accepted','poll.lock','worker.lock','backups'}
    if {path.name for path in root.iterdir()}-allowed:
        raise ValueError('unclassified_legacy_state')
    if mapping.get('schema_version') != 2 or not mapping.get('repositories'):
        raise ValueError('legacy_mapping_required')
    # Configuration must explicitly establish the legacy GitHub origin and aggregate scope.
    profiles = mapping['repositories']
    from lib.provider_ports import validate_legacy_profiles
    validate_legacy_profiles(profiles)
    if destination.exists():
        raise ValueError('migration_requires_fresh_destination')
    if destination.resolve().is_relative_to(root.resolve()) or root.resolve().is_relative_to(destination.resolve()):
        raise ValueError('migration_requires_separate_data_roots')
    # Read-only connection preserves an unversioned v0 source database exactly.
    legacy = object.__new__(Store)
    legacy.root = root
    legacy.db = sqlite3.connect((root/'queue.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
    legacy.db.row_factory = sqlite3.Row
    try:
        if legacy.db.execute('PRAGMA user_version').fetchone()[0] not in (0,1):
            raise ValueError('unsupported_legacy_schema')
        jobs = [dict(row) for row in legacy.db.execute('SELECT * FROM jobs ORDER BY run_id,attempt')]
        if any(job['repository'] not in profiles for job in jobs):
            raise ValueError('ambiguous_legacy_repository')
        backup(legacy, destination)
        verify_backup(destination)
    finally:
        legacy.close()
    if fault:
        fault('backup_verified')
    # Retain the exact backed-up v1 database before transforming the candidate DB.
    import shutil
    shutil.copyfile(destination/'queue.sqlite3',destination/'legacy-database.sqlite3')
    db = sqlite3.connect(destination/'queue.sqlite3')
    try:
        # Create v2 tables transactionally; legacy jobs/batches/meta and bytes are retained.
        holder = object.__new__(Store);holder.db=db
        holder.initialize()
        with db:
            for job in jobs:
                identity=profiles[job['repository']]
                key=canonical_digest({'repository':repository_key(identity['scm']), 'ci_provider':identity['ci_provider'],
                    'ci_instance':endpoint(identity['ci_instance']), 'domain':job['domain'],
                    'legacy_scope':'workflow-aggregate', 'run_id':str(job['run_id']), 'attempt':job['attempt']})
                old=canonical_digest({k:job[k] for k in ('repository','domain','run_id','attempt')})
                db.execute('INSERT INTO legacy_mapping VALUES (?,?,?,?)',('job',old,key,json.dumps(job,sort_keys=True)))
            for table in ('meta','batches'):
                cursor=db.execute('SELECT * FROM '+table)
                names=[col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    record=dict(zip(names,row))
                    old=record['key'] if table=='meta' else record['id']
                    # Batch IDs, branch names, PR numbers/URLs and all cache keys stay original.
                    db.execute('INSERT INTO legacy_mapping VALUES (?,?,?,?)',
                               (table,str(old),canonical_digest({'mapping':mapping,'kind':table,'legacy':str(old)}),json.dumps(record,sort_keys=True)))
            manifest=json.loads((destination/'manifest.json').read_text())
            for name, info in manifest.items():
                if name!='queue.sqlite3':
                    db.execute('INSERT INTO legacy_mapping VALUES (?,?,?,?)',
                               ('file',name,canonical_digest({'mapping':mapping,'path':name}),json.dumps(info,sort_keys=True)))
            db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('portable_migration',json.dumps({'version':2,'mapping_digest':canonical_digest(mapping),'legacy_batches':'manual_reconciliation_required'})))
        if fault:
            fault('database_migrated')
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('migration_integrity_failure')
    finally:
        db.close()
    (destination/'manifest.json').rename(destination/'legacy-backup-manifest.json')
    atomic_json(destination/'migration.json',{'schema_version':2,'status':'candidate','mapping_digest':canonical_digest(mapping),
        'files':{str(p.relative_to(destination)):file_digest(p) for p in destination.rglob('*') if p.is_file()}})
    return destination


def backup_v2(store, destination):
    """Caller holds poll and worker locks. Include migration/lineage metadata too."""
    destination=Path(destination)
    backup(store,destination)
    for name in ('migration.json','legacy-backup-manifest.json','legacy-database.sqlite3'):
        source=store.root/name
        if source.exists():
            if source.is_symlink():
                raise ValueError('unsafe_migration_metadata')
            import shutil
            shutil.copyfile(source,destination/name)
    manifest={str(path.relative_to(destination)):{'size':path.stat().st_size,'sha256':file_digest(path)}
              for path in destination.rglob('*') if path.is_file() and path!=destination/'manifest.json'}
    atomic_json(destination/'manifest.json',manifest)
    verify_backup(destination)
    return manifest


def restore_legacy(verified_v2_backup, destination):
    """Create a separate exact legacy restore; retain all later v2 evidence in backup.

    Never switches services or publication ownership. Open remote publications must be
    reconciled before separately authorized activation of the restored v1 root.
    """
    import shutil
    source,destination=Path(verified_v2_backup),Path(destination)
    verify_backup(source)
    if destination.exists():
        raise ValueError('legacy_restore_requires_fresh_root')
    manifest=json.loads((source/'legacy-backup-manifest.json').read_text())
    selected=[]
    from .bundle import safe_path
    for name,info in manifest.items():
        original=safe_path(source,'legacy-database.sqlite3' if name=='queue.sqlite3' else name)
        if original.stat().st_size!=info['size'] or file_digest(original)!=info['sha256']:
            raise ValueError('legacy_backup_content_mismatch')
        selected.append((name,original))
    destination.mkdir(mode=0o700,parents=True)
    for name,original in selected:
        target=destination/name;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        shutil.copyfile(original,target)
    atomic_json(destination/'manifest.json',manifest)
    verify_backup(destination)
    (destination/'manifest.json').unlink()
    return destination
