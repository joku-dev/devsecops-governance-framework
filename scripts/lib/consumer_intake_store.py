"""Private VM operations state. This is not the GitHub Actions evidence ledger."""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time


def atomic_json(path, value, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


@contextmanager
def lock(path, blocking=False):
    """Separate discovery and worker locks; SQLite serializes short transactions."""
    with Path(path).open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            raise ValueError('Operation already running') from None
        yield


class Store:
    def __init__(self, root):
        self.root = Path(root)
        if self.root.is_symlink():
            raise ValueError('Operations root must not be a symlink')
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(self.root / 'queue.sqlite3', timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
          PRAGMA journal_mode=WAL;
          PRAGMA foreign_keys=ON;
          CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS jobs (
            repository TEXT NOT NULL, domain TEXT NOT NULL, run_id INTEGER NOT NULL,
            attempt INTEGER NOT NULL, payload TEXT NOT NULL, state TEXT NOT NULL,
            retries INTEGER NOT NULL DEFAULT 0, next_at REAL NOT NULL DEFAULT 0,
            error TEXT, snapshot TEXT, snapshot_path TEXT, batch TEXT,
            PRIMARY KEY(repository,domain,run_id,attempt));
          CREATE INDEX IF NOT EXISTS runnable ON jobs(state,next_at);
          CREATE TABLE IF NOT EXISTS batches (
            id TEXT PRIMARY KEY, base TEXT NOT NULL, state TEXT NOT NULL,
            manifest TEXT NOT NULL, commit_sha TEXT, pr INTEGER, url TEXT);
          CREATE UNIQUE INDEX IF NOT EXISTS one_active_batch ON batches((1))
            WHERE state IN ('prepared','open');
        ''')

    def close(self):
        self.db.close()

    def get(self, key, default=None):
        row = self.db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key, value):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', (key, json.dumps(value)))

    def discover(self, repository, run):
        state = 'queued' if run['status'] == 'completed' else 'waiting'
        with self.db:
            self.db.execute("UPDATE jobs SET state='held',error='superseded_attempt' WHERE repository=? AND domain='devsecops' AND run_id=? AND attempt<? AND state IN ('waiting','queued')",
                            (repository, int(run['id']), int(run['run_attempt'])))
            self.db.execute('''INSERT INTO jobs(repository,domain,run_id,attempt,payload,state)
              VALUES (?,?,?,?,?,?) ON CONFLICT(repository,domain,run_id,attempt)
              DO UPDATE SET payload=excluded.payload,
                state=CASE WHEN jobs.state='waiting' THEN excluded.state ELSE jobs.state END''',
                            (repository, 'devsecops', int(run['id']), int(run['run_attempt']), json.dumps(run), state))

    def jobs(self, state=None):
        query = 'SELECT * FROM jobs' + (' WHERE state=?' if state else '') + ' ORDER BY run_id,attempt'
        return [dict(row) for row in self.db.execute(query, (state,) if state else ())]

    def update(self, job, **fields):
        allowed = {'state', 'retries', 'next_at', 'error', 'snapshot', 'snapshot_path', 'batch'}
        if not fields or not set(fields) <= allowed:
            raise ValueError('Invalid queue update')
        with self.db:
            self.db.execute('UPDATE jobs SET ' + ','.join(key + '=?' for key in fields)
                            + ' WHERE repository=? AND domain=? AND run_id=? AND attempt=?',
                            (*fields.values(), job['repository'], job['domain'], job['run_id'], job['attempt']))

    def recover(self):
        # Called only while holding the worker lock. Verified snapshots are immutable.
        with self.db:
            self.db.execute("UPDATE jobs SET state='queued' WHERE state='working'")

    def claim(self):
        with self.db:
            row = self.db.execute("SELECT * FROM jobs WHERE state='queued' AND next_at<=? ORDER BY run_id,attempt LIMIT 1",
                                  (time.time(),)).fetchone()
            if row:
                self.update(dict(row), state='working')
        return dict(row) if row else None

    def failure(self, job, code, retryable=False, delay=60):
        retries = job['retries'] + 1
        retry = retryable and retries <= 3
        self.update(job, state='queued' if retry else 'held', retries=retries,
                    next_at=time.time() + delay * 2 ** (retries - 1), error=code)

    def active_batch(self):
        row = self.db.execute("SELECT * FROM batches WHERE state IN ('prepared','open')").fetchone()
        return dict(row) if row else None

    def batch(self, batch_id, **fields):
        if not set(fields) <= {'state', 'commit_sha', 'pr', 'url'}:
            raise ValueError('Invalid batch update')
        with self.db:
            self.db.execute('UPDATE batches SET ' + ','.join(key + '=?' for key in fields) + ' WHERE id=?',
                            (*fields.values(), batch_id))


def disk_ready(root, cache_limit=1024 ** 3, reserve=8 * 1024 ** 3):
    raw = Path(root) / 'raw'
    used = sum(path.stat().st_size for path in raw.rglob('*') if path.is_file()) if raw.exists() else 0
    # Reserve a full artifact budget before downloading, including transient copies.
    return used < cache_limit and shutil.disk_usage(root).free >= reserve + cache_limit


def file_digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024 ** 2):
            result.update(block)
    return result.hexdigest()


def backup(store, destination):
    """Consistent database and immutable raw cache, separate from Workbench ZIPs.

    Caller holds both operation locks, so no cache/snapshot publication can race.
    Credentials are deliberately excluded. No retention deletion is performed.
    """
    destination = Path(destination)
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    target = sqlite3.connect(destination / 'queue.sqlite3')
    try:
        store.db.backup(target)
    finally:
        target.close()
    for name in ('raw', 'verified', 'accepted'):
        origin = store.root / name
        if origin.exists():
            if any(path.is_symlink() for path in (origin, *origin.rglob('*'))):
                raise ValueError('Symlinks are not supported in operations backups')
            shutil.copytree(origin, destination / name, symlinks=False)
    manifest = {}
    for path in destination.rglob('*'):
        if path.is_file():
            manifest[str(path.relative_to(destination))] = {
                'size': path.stat().st_size, 'sha256': file_digest(path)}
    atomic_json(destination / 'manifest.json', manifest)
    return manifest


def verify_backup(destination):
    destination = Path(destination)
    if any(path.is_symlink() for path in (destination, *destination.rglob('*'))):
        raise ValueError('Symlinks are not supported in operations backups')
    manifest = json.loads((destination / 'manifest.json').read_text())
    actual = {str(p.relative_to(destination)) for p in destination.rglob('*') if p.is_file()} - {'manifest.json'}
    if actual != set(manifest):
        raise ValueError('Backup file set mismatch')
    for name, expected in manifest.items():
        path = destination / name
        if path.is_symlink() or not path.resolve().is_relative_to(destination.resolve()):
            raise ValueError('Unsafe backup path')
        if path.stat().st_size != expected['size'] or file_digest(path) != expected['sha256']:
            raise ValueError('Backup checksum mismatch')
    db = sqlite3.connect((destination / 'queue.sqlite3').resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    try:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Backup database integrity failure')
    finally:
        db.close()
    return manifest
