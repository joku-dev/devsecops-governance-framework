"""Whole immutable V1 Store algorithm with explicit path, SQLite and clock ports.

Every original method and SQL statement is retained. This internal model does
not by itself implement the operator, locks, backups or operating authority.
"""
import json


class Store:
    def __init__(self, root, *, path_factory, sqlite_port, clock_port):
        self.paths, self.sqlite, self.clock = path_factory, sqlite_port, clock_port
        self.root = self.paths(root)
        if self.root.is_symlink():
            raise ValueError('Operations root must not be a symlink')
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = self.sqlite.connect(self.root / 'queue.sqlite3', timeout=30)
        # Version 2 has a separate execution namespace and needs its own operator.
        # Never let a legacy worker continue on a migrated candidate.
        if self.db.execute('PRAGMA user_version').fetchone()[0] not in (0, 1):
            self.db.close()
            raise ValueError('Consumer state requires a compatible versioned operator')
        self.db.row_factory = self.sqlite.Row
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
          PRAGMA user_version=1;
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
                                  (self.clock.time(),)).fetchone()
            if row:
                self.update(dict(row), state='working')
        return dict(row) if row else None

    def failure(self, job, code, retryable=False, delay=60):
        retries = job['retries'] + 1
        retry = retryable and retries <= 3
        self.update(job, state='queued' if retry else 'held', retries=retries,
                    next_at=self.clock.time() + delay * 2 ** (retries - 1), error=code)

    def active_batch(self):
        row = self.db.execute("SELECT * FROM batches WHERE state IN ('prepared','open')").fetchone()
        return dict(row) if row else None

    def batch(self, batch_id, **fields):
        if not set(fields) <= {'state', 'commit_sha', 'pr', 'url'}:
            raise ValueError('Invalid batch update')
        with self.db:
            self.db.execute('UPDATE batches SET ' + ','.join(key + '=?' for key in fields) + ' WHERE id=?',
                            (*fields.values(), batch_id))
