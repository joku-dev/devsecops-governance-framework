"""Explicit legacy diagnostic preflight capture over fixed GET, clock and exclusive path ports."""
import re
from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture,MAX_BYTES
_OMITTED=object()
class LegacyLifecyclePreflight(LegacyRepositoryLifecycleCapture):
    def __init__(self,context,*,path_factory=None,transport,clock):
        super().__init__(context,path_factory=path_factory)
        self.transport,self.clock=transport,clock
        self.default_fetch=self.github_get
    def github_get(self,endpoint,*,raw=False):
        return self.transport.fetch(endpoint,raw=raw)

    def collect_preflight(self, run_id, output_dir, *, repo_root=_OMITTED, fetch=_OMITTED, captured_at=None):
        if repo_root is _OMITTED:
            repo_root = self.context.root
        if fetch is _OMITTED:
            fetch = self.default_fetch
        prepared = self.context.preparation.validate_preparation(repo_root)
        self.context.contracts.require(prepared['assignments'], 'Pilot appointments have been withdrawn')
        profile = prepared['profile']
        source = profile['source']
        self.context.contracts.require(re.fullmatch('[1-9][0-9]*', str(run_id)) is not None, 'Positive run ID required')
        destination = self.path_factory(output_dir).resolve()
        self.context.contracts.require(not destination.exists(), 'Capture directory already exists; snapshots are immutable')
        root = self.path_factory(repo_root).resolve()
        if destination.is_relative_to(root):
            self.context.contracts.require(destination.is_relative_to(root / 'generated/reports/lifecycle-live-preflight'), 'Dedicated diagnostic capture directory required')
        endpoint = 'repos/' + profile['scope']['repository_id']
        snapshots = {}

        def get(name, path):
            data = fetch(path)
            snapshots[name] = data
            return self.context.adapter.strict_json(data)
        repository = get('repository.json', endpoint)
        run_endpoint = endpoint + '/actions/runs/' + str(run_id)
        run = get('run-before.json', run_endpoint)
        self.context.contracts.require(str(run['id']) == str(run_id), 'Requested run identity differs')
        self.context.contracts.require(type(run['run_attempt']) is int and run['run_attempt'] == 1, 'Rerun artifact-to-attempt binding is not supported')
        self.context.contracts.require(re.fullmatch('[a-f0-9]{40}', run['head_sha']) is not None, 'Full run commit required')
        workflow = get('workflow.json', endpoint + '/actions/workflows/' + self.positive_id(run['workflow_id']))
        artifacts = []
        for page in range(1, 11):
            listing = get(f'artifacts-page-{page}.json', run_endpoint + f'/artifacts?per_page=100&page={page}')
            artifacts.extend(listing['artifacts'])
            if len(artifacts) >= listing['total_count']:
                break
        else:
            raise ValueError('Artifact listing exceeds supported size')
        matches = [a for a in artifacts if a['name'] == source['artifact_name']]
        self.context.contracts.require(len(matches) == 1, 'Exactly one named run artifact is required')
        artifact_endpoint = endpoint + '/actions/artifacts/' + self.positive_id(matches[0]['id'])
        artifact = get('artifact-before.json', artifact_endpoint)
        self.context.contracts.require(artifact == matches[0], 'Artifact listing changed during capture')
        self.context.contracts.require(type(artifact['size_in_bytes']) is int and 0 < artifact['size_in_bytes'] <= MAX_BYTES, 'Unsupported artifact size')
        archive = fetch(artifact_endpoint + '/zip')
        files = {p: fetch(endpoint + '/contents/' + p + '?ref=' + run['head_sha'], raw=True) for p in source['reference_files']}
        run_after = get('run-after.json', run_endpoint)
        artifact_after = get('artifact-after.json', artifact_endpoint)
        self.context.contracts.require(run_after == run and artifact_after == artifact, 'Provider metadata changed during capture')
        at = captured_at or self.clock()
        result, report_bytes = self.verify_capture(profile, repository=repository, run=run, workflow=workflow, artifact=artifact, archive=archive, files=files, captured_at=at)
        snapshots.update({'profile.json': self.context.adapter.json_bytes(profile), 'artifact.zip': archive, 'report.json': report_bytes, **{'producer/' + p: b for p, b in files.items()}})
        result['capture'] = {'method': 'github_api_get_via_gh' if fetch is self.default_fetch else 'injected_test_transport', 'api_origin': source['api_origin'], 'snapshot_sha256': {p: self.sha(b) for p, b in snapshots.items()}}
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.mkdir()
        for name, data in snapshots.items():
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(data)
        with (destination / 'preflight.json').open('xb') as stream:
            stream.write(self.context.adapter.json_bytes(result))
        return result
