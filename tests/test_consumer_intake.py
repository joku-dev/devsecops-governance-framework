"""Deterministic VM operations tests; no GitHub credentials or live consumer runs."""
import copy
from datetime import datetime, timezone, timedelta
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, Mock
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.consumer_intake_store import Store, lock, disk_ready, backup, verify_backup, atomic_json
from lib.consumer_github import Client, AppToken, AccessFailure, retry_delay, collection_error
from lib import consumer_intake as intake
from lib.consumer_view import read_projection
from lib import consumer_publisher
from intake_github_actions_run import check_expected_run, github_pages
import consumer_intake as cli


def run(number=10, attempt=1, status='completed', **extra):
    return {'id': number, 'run_attempt': attempt, 'status': status, 'conclusion': 'success',
            'head_branch': 'main', 'head_sha': 'a' * 40, 'event': 'push', 'path': intake.WORKFLOW,
            'repository': {'full_name': intake.CONSUMER}, 'created_at': intake.now(), 'updated_at': intake.now(), **extra}


def fixture():
    path = ROOT / 'status/results/joku-dev__ha-CPsWMS/2026-09-19T07-20-05Z-run-35428988040.json'
    value = json.loads(path.read_text())
    value['pipeline']['pipeline_run_id'] = '10'
    value['repository']['commit_id'] = 'a' * 40
    value['governance_baseline_ref'] = intake.BASELINE
    value['trust']['capture']['source'].update(run_id='10', run_attempt=1, artifact_name=intake.ARTIFACT, commit_id='a' * 40)
    # Fresh synthetic successful verifier output, built from the full schema fixture.
    for check in value['trust']['checks']:
        if check['result'] == 'fail' or check['id'] in {'baseline_ref_resolved', 'custody_recorded'}:
            check['result'] = 'pass'
    return value


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'ops')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_duplicate_rerun_waiting_and_restart(self):
        self.store.discover(intake.CONSUMER, run(status='in_progress'))
        self.store.discover(intake.CONSUMER, run())
        self.store.discover(intake.CONSUMER, run())
        self.assertEqual(len(self.store.jobs()), 1)
        self.assertEqual(self.store.claim()['attempt'], 1)
        self.store.close()
        self.store = Store(self.root / 'ops')
        self.store.recover()
        self.assertEqual(self.store.claim()['run_id'], 10)
        self.store.discover(intake.CONSUMER, run(attempt=2))
        self.assertEqual(len(self.store.jobs()), 2)

    def test_three_automatic_retries_then_manual_hold(self):
        self.store.discover(intake.CONSUMER, run())
        for number in range(1, 5):
            self.store.failure(self.store.jobs()[0], 'network_unavailable', True, 1)
            self.assertEqual(self.store.jobs()[0]['state'], 'queued' if number <= 3 else 'held')
        self.assertIsNone(self.store.claim())

    def test_permanent_access_failure_is_held(self):
        self.store.discover(intake.CONSUMER, run())
        self.store.failure(self.store.jobs()[0], 'http_403', False)
        self.assertEqual(self.store.jobs()[0]['state'], 'held')

    def test_worker_lock_does_not_block_discovery_but_excludes_second_worker(self):
        with lock(self.store.root / 'worker.lock'):
            with lock(self.store.root / 'poll.lock'):
                self.store.discover(intake.CONSUMER, run())
            with self.assertRaises(ValueError), lock(self.store.root / 'worker.lock'):
                pass

    def test_synthetic_queue_1000_and_2000_consumers(self):
        started = time.monotonic()
        for number in range(2000):
            self.store.discover('synthetic/repo-' + str(number), run(number + 1))
            if number == 999:
                self.assertEqual(len(self.store.jobs()), 1000)
        self.assertEqual(len(self.store.jobs()), 2000)
        self.assertEqual(self.store.claim()['run_id'], 1)
        # Generous regression ceiling, not a production throughput claim.
        self.assertLess(time.monotonic() - started, 30)

    def test_low_disk_and_cache_budget(self):
        with patch('lib.consumer_intake_store.shutil.disk_usage', return_value=Mock(free=8 * 1024 ** 3)):
            self.assertFalse(disk_ready(self.store.root))
        (self.store.root / 'raw').mkdir()
        (self.store.root / 'raw/a').write_bytes(b'12345')
        self.assertFalse(disk_ready(self.store.root, cache_limit=5, reserve=0))

    def test_consistent_backup_restore_and_checksum_failure(self):
        self.store.discover(intake.CONSUMER, run())
        (self.store.root / 'raw').mkdir()
        (self.store.root / 'raw/artifact.zip').write_bytes(b'archive')
        destination = self.root / 'backup'
        backup(self.store, destination)
        verify_backup(destination)
        target = self.root / 'restored'
        self.assertEqual(cli.main(['restore', '--root', str(target), '--destination', str(destination)]), 0)
        restored = Store(target)
        self.assertEqual(len(restored.jobs()), 1)
        restored.close()
        (destination / 'raw/artifact.zip').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            verify_backup(destination)

    def test_backup_rejects_escape_and_extra_files(self):
        destination = self.root / 'backup'
        backup(self.store, destination)
        (destination / 'unexpected').write_text('extra')
        with self.assertRaisesRegex(ValueError, 'file set'):
            verify_backup(destination)

    def test_projection_redacts_private_state_and_keeps_accepted_timestamp(self):
        self.store.put('http:/secret', {'token': 'never-expose'})
        self.store.put('accepted', {'source_commit': 'b' * 40, 'synced_at': '2020-01-01', 'latest': None})
        self.store.discover(intake.CONSUMER, run(secret='never-expose'))
        projection = self.root / 'view'
        intake.project(self.store, projection, 'shadow')
        self.assertNotIn('never-expose', (projection / 'consumers.json').read_text())
        data = read_projection(projection)
        self.assertEqual(data['accepted']['synced_at'], '2020-01-01')
        self.assertEqual((projection / 'consumers.json').stat().st_mode & 0o777, 0o640)
        (projection / 'consumers.json').unlink()
        (projection / 'consumers.json').symlink_to(self.store.root / 'queue.sqlite3')
        with self.assertRaises(ValueError):
            read_projection(projection)

    def test_bootstrap_newest_completed_only_and_active_runs(self):
        api = Mock()
        api.pages.return_value = iter([[run(13, status='in_progress'), run(12, conclusion='failure'), run(11)]])
        api.request.side_effect = lambda method, endpoint, **kw: {'sha': 'b' * 40} if '/commits/' in endpoint else run(int(endpoint.rsplit('/', 1)[1]))
        intake.discover(self.store, api)
        self.assertEqual([row['run_id'] for row in self.store.jobs()], [12, 13])
        self.assertIsNotNone(self.store.get('last_poll'))

    def test_window_pagination_and_foreign_runs(self):
        api = Mock()
        api.request.return_value = {'total_count': 101}
        api.pages.return_value = iter([[run(n) for n in range(100)], [run(101), run(102, head_branch='foreign')]])
        end = datetime.now(timezone.utc)
        intake.discover_window(self.store, api, '/runs?branch=main', end - timedelta(hours=1), end)
        self.assertEqual(len(self.store.jobs()), 101)

    def test_discovery_splits_github_thousand_result_cap(self):
        api = Mock()
        api.request.side_effect = [{'total_count': 1001}, {'total_count': 1}, {'total_count': 1}]
        api.pages.side_effect = [iter([[run(1)]]), iter([[run(2)]])]
        end = datetime.now(timezone.utc)
        intake.discover_window(self.store, api, '/runs?event=push', end - timedelta(hours=1), end)
        self.assertEqual(len(self.store.jobs()), 2)

    def test_snapshot_identity_and_failed_trust_are_not_promoted(self):
        value = fixture()
        self.store.discover(intake.CONSUMER, run())
        job = self.store.jobs()[0]
        intake.validate_snapshot(ROOT, value, job)
        value['trust']['capture']['source']['run_attempt'] = 2
        with self.assertRaises(AccessFailure):
            intake.validate_snapshot(ROOT, value, job)
        value = fixture()
        value['trust']['checks'][0]['result'] = 'fail'
        with self.assertRaises(AccessFailure):
            intake.validate_snapshot(ROOT, value, job)

    def test_failed_governance_is_valid_evidence(self):
        value = fixture()
        value['overall_status'] = 'fail'
        self.store.discover(intake.CONSUMER, run())
        intake.validate_snapshot(ROOT, value, self.store.jobs()[0])

    def test_attempt_guard_and_paginated_legacy_artifacts(self):
        check_expected_run(run(), 1)
        for value in (run(attempt=2), run(status='in_progress')):
            with self.assertRaises(ValueError):
                check_expected_run(value, 1)
        with patch('intake_github_actions_run.github_get_json', side_effect=[{'artifacts': list(range(100))}, {'artifacts': [100]}]):
            self.assertEqual(len(github_pages('https://api.github.com/test', 'private', 'artifacts')), 101)

    def test_shadow_gate_requires_elapsed_time_and_real_match(self):
        self.store.put('shadow_started', time.time() - 25 * 3600)
        self.assertFalse(intake.shadow_ready(self.store))
        self.store.put('shadow_match', {'run_id': 10})
        self.assertTrue(intake.shadow_ready(self.store))
        self.store.put('shadow_started', time.time())
        self.assertFalse(intake.shadow_ready(self.store))

    def test_comparison_ignores_capture_clock_not_digests(self):
        before = fixture()
        after = copy.deepcopy(before)
        after['trust']['capture']['captured_at'] = intake.now()
        self.assertEqual(intake.comparison(before), intake.comparison(after))
        after['trust']['capture']['subjects'][0]['digest'] = 'd' * 64
        self.assertNotEqual(intake.comparison(before), intake.comparison(after))

    def test_compatibility_blocks_changed_code_but_not_status(self):
        installed, staged = self.root / 'installed', self.root / 'stage'
        for path in (installed, staged):
            (path / 'scripts').mkdir(parents=True)
            (path / 'scripts/job.py').write_text('print(1)')
        intake.compatible(installed, staged)
        (staged / 'status').mkdir()
        (staged / 'status/index.json').write_text('{}')
        intake.compatible(installed, staged)
        (staged / 'scripts/job.py').write_text('print(2)')
        with self.assertRaises(AccessFailure):
            intake.compatible(installed, staged)

    def test_accepted_sync_validates_before_atomic_publication(self):
        old = {'source_commit': 'a' * 40}
        self.store.put('accepted', old)
        with patch.object(intake, 'command', side_effect=AccessFailure('validation_failed')):
            with self.assertRaises(AccessFailure):
                intake.sync_accepted(self.store, ROOT, 'b' * 40)
        self.assertEqual(self.store.get('accepted'), old)
        with patch.object(intake, 'command'):
            intake.sync_accepted(self.store, ROOT, 'b' * 40)
        self.assertEqual(self.store.get('accepted')['source_commit'], 'b' * 40)
        produced = self.store.get('accepted')['latest']['produced_at']
        self.assertLess(produced, '2026-11-14')

    def test_missing_expired_artifact_and_attempt_race(self):
        self.store.discover(intake.CONSUMER, run())
        job, api = self.store.jobs()[0], Mock()
        api.request.return_value = run(attempt=2)
        with patch.object(intake, 'disk_ready', return_value=True):
            with self.assertRaisesRegex(AccessFailure, 'run_attempt_changed'):
                intake.collect(self.store, ROOT, api, job)
            api.request.return_value = run()
            for artifacts in ([], [{'name': intake.ARTIFACT, 'expired': True}]):
                api.pages.return_value = iter([artifacts])
                with self.assertRaisesRegex(AccessFailure, 'artifact_missing_or_expired'):
                    intake.collect(self.store, ROOT, api, job)

    def test_one_batch_at_most_25_and_pr_recovery(self):
        for number in range(30):
            self.store.discover(intake.CONSUMER, run(number + 1))
            row = self.store.jobs()[-1]
            self.store.update(row, state='verified', snapshot=json.dumps(fixture()), snapshot_path=f'status/results/x/{number}.json')
        reader, publisher = Mock(), Mock()
        reader.pages.return_value = iter([[]])
        reader.request.return_value = [{'number': 8, 'html_url': 'https://github.com/o/r/pull/8'}]
        consumer_publisher.publish(self.store, ROOT, reader, publisher, 'a' * 40)
        self.assertEqual(len(self.store.jobs('batched')), 25)
        self.assertEqual(len(self.store.jobs('verified')), 5)
        self.assertEqual(self.store.active_batch()['pr'], 8)
        publisher.request.assert_not_called()
        # Closed unmerged is terminal, never reopens automatically.
        reader.pages.return_value = iter([[]])
        reader.request.return_value = {'state': 'closed', 'merged_at': None}
        consumer_publisher.publish(self.store, ROOT, reader, publisher, 'a' * 40)
        self.assertIsNone(self.store.active_batch())
        self.assertEqual(len(self.store.jobs('not_accepted')), 25)
        publisher.request.assert_not_called()

    def test_no_second_active_batch(self):
        with self.store.db:
            self.store.db.execute("INSERT INTO batches(id,base,state,manifest) VALUES ('one','abc','open','[]')")
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.db:
                self.store.db.execute("INSERT INTO batches(id,base,state,manifest) VALUES ('two','abc','prepared','[]')")

    def test_recovers_remote_branch_and_pr_when_api_response_is_lost(self):
        for fail_at in ('branch', 'pr'):
            with self.subTest(fail_at=fail_at):
                with self.store.db:
                    self.store.db.execute('DELETE FROM batches')
                    self.store.db.execute("INSERT INTO batches(id,base,state,manifest,commit_sha) VALUES ('batch','aaa','prepared','[]','bbb')")
                remote = {'branch': False, 'pr': None, 'failed': False}
                reader, publisher = Mock(), Mock()
                reader.pages.side_effect = lambda *a: iter([[]])
                def read(method, endpoint, **kwargs):
                    if '/pulls?' in endpoint:
                        return [remote['pr']] if remote['pr'] else []
                    if '/git/ref/' in endpoint:
                        if not remote['branch']:
                            raise AccessFailure('http_404')
                        return {'object': {'sha': 'bbb'}}
                    self.fail('Unexpected read: ' + endpoint)
                def write(method, endpoint, payload):
                    self.assertEqual(method, 'POST')
                    if endpoint.endswith('/git/refs'):
                        self.assertTrue(payload['ref'].startswith('refs/heads/automation/vm-consumer/'))
                        remote['branch'] = True
                        if fail_at == 'branch' and not remote['failed']:
                            remote['failed'] = True
                            raise AccessFailure('network_unavailable', True)
                        return {}
                    if endpoint.endswith('/pulls'):
                        remote['pr'] = {'number': 5, 'html_url': 'https://github.com/owner/repo/pull/5'}
                        if fail_at == 'pr' and not remote['failed']:
                            remote['failed'] = True
                            raise AccessFailure('network_unavailable', True)
                        return remote['pr']
                    self.fail('Unexpected write: ' + endpoint)
                reader.request.side_effect = read
                publisher.request.side_effect = write
                with self.assertRaises(AccessFailure):
                    consumer_publisher.publish(self.store, ROOT, reader, publisher, 'aaa')
                consumer_publisher.publish(self.store, ROOT, reader, publisher, 'aaa')
                self.assertEqual(self.store.active_batch()['pr'], 5)
                endpoints = [call.args[1] for call in publisher.request.call_args_list]
                self.assertEqual(sum(endpoint.endswith('/git/refs') for endpoint in endpoints), 1)
                self.assertEqual(sum(endpoint.endswith('/pulls') for endpoint in endpoints), 1)

    def test_legacy_pr_prevents_handoff_and_route_defaults(self):
        reader = Mock()
        reader.pages.return_value = iter([[{'head': {'ref': 'automation/devsecops/10-1'}}]])
        with self.assertRaisesRegex(AccessFailure, 'legacy_intake_pr_open'):
            consumer_publisher.publish(self.store, ROOT, reader, Mock(), 'a' * 40)
        self.assertEqual(intake.owner(ROOT), 'github-actions')
        self.assertEqual(intake.owner(ROOT, 'other/consumer', 'architecture'), 'github-actions')

    def test_restored_database_cannot_create_second_remote_vm_pr(self):
        reader = Mock()
        reader.pages.return_value = iter([[{'head': {'ref': 'automation/vm-consumer/unrecorded'}}]])
        publisher = Mock()
        with self.assertRaisesRegex(AccessFailure, 'unreconciled_vm_pr_open'):
            consumer_publisher.publish(self.store, ROOT, reader, publisher, 'a' * 40)
        publisher.request.assert_not_called()

    def test_inflight_legacy_intake_blocks_vm_publication(self):
        reader, publisher = Mock(), Mock()
        reader.pages.side_effect = lambda endpoint, *args: iter([[{'id': 1}]]) if 'status=in_progress' in endpoint else iter([[]])
        with self.assertRaisesRegex(AccessFailure, 'legacy_intake_running'):
            consumer_publisher.publish(self.store, ROOT, reader, publisher, 'a' * 40)
        publisher.request.assert_not_called()

    def test_reconciliation_requires_paused_mode_and_preserves_old_batch(self):
        with self.store.db:
            self.store.db.execute("INSERT INTO batches(id,base,state,manifest) VALUES ('old','aaa','prepared','[]')")
        self.store.put('accepted_commit', 'bbb')
        config = self.root / 'operator.json'
        atomic_json(config, {'mode': 'shadow'})
        args = ['reconcile-batch', '--root', str(self.store.root), '--projection', str(self.root / 'view'),
                '--config', str(config), '--batch-id', 'old']
        with self.assertRaises(ValueError):
            cli.main(args)
        atomic_json(config, {'mode': 'paused'})
        self.assertEqual(cli.main(args), 0)
        self.assertIsNone(self.store.active_batch())
        self.assertEqual(self.store.db.execute("SELECT state FROM batches WHERE id='old'").fetchone()[0], 'abandoned')


class TransportTests(unittest.TestCase):
    def test_synthetic_api_pagination_1000_and_2000_consumers(self):
        for count in (1000, 2000):
            calls = []
            def opener(request, **kwargs):
                from urllib.parse import parse_qs, urlsplit
                page = int(parse_qs(urlsplit(request.full_url).query)['page'][0])
                calls.append(page)
                rows = [{'repository': f'synthetic/repo-{number}'} for number in range((page-1)*100, min(page*100, count))]
                response = io.BytesIO(json.dumps(rows).encode())
                response.headers = {}
                return response
            api = Client(lambda: 'synthetic', opener=opener)
            rows = [row for page in api.pages('/repos') for row in page]
            self.assertEqual(len(rows), count)
            self.assertEqual(len(calls), count // 100 + 1)

    def test_conditional_request_304_reuses_persisted_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(temporary)
            store.put('http:/runs', {'etag': 'version-1', 'data': {'runs': []}})
            def opener(request, **kwargs):
                self.assertEqual(request.get_header('If-none-match'), 'version-1')
                raise HTTPError(request.full_url, 304, '', {}, None)
            self.assertEqual(Client(lambda: 'hidden', store, opener).request('GET', '/runs'), {'runs': []})
            store.close()

    def test_401_403_429_and_500_redact_response_and_classify(self):
        for status, headers, retry in ((401, {}, False), (403, {}, False), (429, {'Retry-After': '120'}, True),
                                       (403, {'X-RateLimit-Remaining': '0'}, True), (500, {}, True)):
            def opener(request, **kwargs):
                raise HTTPError(request.full_url, status, 'secret-response', headers, io.BytesIO(b'secret'))
            with self.assertRaises(AccessFailure) as caught:
                Client(lambda: 'secret-token', opener=opener).request('GET', '/runs')
            self.assertEqual(caught.exception.retryable, retry)
            self.assertNotIn('secret', str(caught.exception))
        self.assertEqual(retry_delay({'Retry-After': '120'}), 120)
        original = HTTPError('https://api.github.com/private', 429, 'private', {'Retry-After': '250'}, None)
        wrapped = RuntimeError('private wrapper')
        wrapped.__cause__ = original
        classified = collection_error(wrapped)
        self.assertTrue(classified.retryable)
        self.assertEqual(classified.delay, 250)
        self.assertNotIn('private', classified.code)

    def test_tokens_refresh_and_permissions_are_scoped(self):
        with tempfile.TemporaryDirectory() as temporary:
            key = Path(temporary) / 'key.pem'
            key.write_text('not-a-real-key')
            key.chmod(0o600)
            response = {'token': 'private', 'expires_at': '2099-01-01T00:00:00Z'}
            request = Mock(return_value=response)
            token = AppToken(1, 2, key, ['central-only'], {'contents': 'write'}, request)
            with patch('lib.consumer_github.subprocess.run', return_value=Mock(returncode=0, stdout=b'signature')):
                self.assertEqual(token(), 'private')
                self.assertEqual(token(), 'private')
                request.assert_called_once()
                token.expires = 0
                token()
                self.assertEqual(request.call_count, 2)
            self.assertEqual(request.call_args.args[2]['repositories'], ['central-only'])
            key.chmod(0o644)
            token.expires = 0
            with self.assertRaises(AccessFailure):
                token()


if __name__ == '__main__':
    unittest.main()
