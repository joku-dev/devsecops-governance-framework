"""Complete original consumer lifecycle functions over explicit data/effect ports.

Retained source history is not this node's operating authority.
"""
from __future__ import annotations
from copy import deepcopy
from referencing import Registry,Resource
import base64,hashlib
_OMITTED=object()
_DEFAULT_FETCH=object()
import io,re,zipfile
MAX_BYTES = 10 * 1024 * 1024

class LegacyConsumerEvidence:

    def __init__(self, root, context, *, path_factory, profile, process=None, temporary=None, clock=None, validator_class=None, default_fetch=None, architecture=None, argument_parser=None, argv=(), description=None):
        self.root, self.context, self.Path, self.profile = (root, context, path_factory, profile)
        self.process, self.temporary, self.clock = (process, temporary, clock)
        self.validator_class, self.default_fetch, self.architecture = (validator_class, default_fetch, architecture)
        self.argument_parser, self.argv, self.description = (argument_parser, list(argv), description)
        self.positive_id = profile.positive_id
        self.sha = lambda b: hashlib.sha256(b).hexdigest()
        self.MAX_BYTES = MAX_BYTES

    def verify_capture(self, profile, snapshots, *, captured_at):
        """Replay exact bytes; authenticity additionally requires the independent PR guard."""
        self.context.consumer_contracts.schema_validator('profile').validate(profile)
        source, scope = (profile['source'], profile['scope'])
        expected = {'repository.json', 'run-before.json', 'run-after.json', 'workflow.json', 'artifact-before.json', 'artifact-after.json', 'artifact.zip', 'consumer-workflow.yml', 'baseline-ref.json', 'baseline-tag.json'} | {'producer/' + p for p in source['reference_files']}
        self.context.contracts.require(set(snapshots) == expected, 'Consumer capture inventory differs')
        self.context.contracts.require(sum(map(len, snapshots.values())) <= 3 * self.MAX_BYTES, 'Capture exceeds supported size')
        read = lambda name: self.context.adapter.strict_json(snapshots[name])
        repository, run, workflow, artifact = map(read, ('repository.json', 'run-before.json', 'workflow.json', 'artifact-before.json'))
        self.context.contracts.require(run == read('run-after.json') and artifact == read('artifact-after.json'), 'Provider metadata changed during capture')
        rid = scope['github_repository_id']
        self.context.contracts.require(type(repository['id']) is int and repository['id'] == rid and (repository['full_name'] == scope['repository_id']) and (repository['default_branch'] == 'main'), 'Consumer repository identity differs')
        self.positive_id(run['id'])
        self.positive_id(run['workflow_id'])
        self.positive_id(artifact['id'])
        self.context.contracts.require(run['repository']['id'] == rid and run['head_repository']['id'] == rid, 'Consumer run repository or fork differs')
        self.context.contracts.require(run['head_branch'] == 'main' and run['event'] == 'push', 'Only mainline push evidence is eligible')
        self.context.contracts.require(run['status'] == 'completed' and run['conclusion'] == 'success', 'Completed successful producer required')
        self.context.contracts.require(type(run['run_attempt']) is int and run['run_attempt'] == 1, 'Only first-attempt artifacts are supported')
        commit = run['head_sha']
        self.context.contracts.require(re.fullmatch('[a-f0-9]{40}', commit) is not None, 'Full producer commit required')
        self.context.contracts.require(run['path'] == source['workflow_path'] and workflow['path'] == source['workflow_path'] and (workflow['id'] == run['workflow_id']), 'Consumer workflow differs')
        self.context.contracts.require(self.sha(snapshots['consumer-workflow.yml']) == source['workflow_sha256'], 'Consumer producer implementation changed')
        expected_reference = f"{source['baseline_repository']}/.github/workflows/architecture-baseline-l1-v0.1.0.yml@{source['baseline_ref']}"
        refs = run.get('referenced_workflows', [])
        self.context.contracts.require(len(refs) == 1 and refs[0]['path'] == expected_reference and (refs[0]['sha'] in (source['baseline_tag_object'], source['reference_commit'])), 'Referenced baseline differs')
        tagref, tag = (read('baseline-ref.json'), read('baseline-tag.json'))
        self.context.contracts.require(tagref['ref'] == 'refs/tags/' + source['baseline_ref'] and tagref['object'] == {'sha': source['baseline_tag_object'], 'type': 'tag', 'url': f"https://api.github.com/repos/{source['baseline_repository']}/git/tags/{source['baseline_tag_object']}"}, 'Baseline tag reference changed')
        self.context.contracts.require(tag['sha'] == source['baseline_tag_object'] and tag['object']['type'] == 'commit' and (tag['object']['sha'] == source['reference_commit']), 'Annotated baseline tag resolution differs')
        for path, digest in source['reference_files'].items():
            self.context.contracts.require(self.sha(snapshots['producer/' + path]) == digest, 'Pinned baseline file differs: ' + path)
        self.context.contracts.require(artifact['name'] == source['artifact_name'] and artifact['expired'] is False, 'Artifact name or availability differs')
        archive = snapshots['artifact.zip']
        self.context.contracts.require(type(artifact['size_in_bytes']) is int and 0 < artifact['size_in_bytes'] <= self.MAX_BYTES and (0 < len(archive) <= self.MAX_BYTES), 'Unsupported artifact size')
        self.context.contracts.require(artifact['digest'] == 'sha256:' + self.sha(archive), 'Archive digest does not match GitHub')
        association = artifact['workflow_run']
        self.context.contracts.require(association['id'] == run['id'] and association['repository_id'] == rid and (association['head_repository_id'] == rid) and (association['head_sha'] == commit) and (association['head_branch'] == 'main'), 'Artifact run association differs')
        start, produced, completed, captured = map(self.context.contracts.timestamp, (run['run_started_at'], artifact['created_at'], run['updated_at'], captured_at))
        self.context.contracts.require(start <= produced <= completed <= captured < self.context.contracts.timestamp(artifact['expires_at']), 'Artifact timeline or expiry differs')
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            members = bundle.infolist()
            names = {source['report_path'], source['input_path'], 'architecture-governance-report.md'}
            self.context.contracts.require(len(members) == 3 and {m.filename for m in members} == names, 'Unexpected or duplicate archive members')
            self.context.contracts.require(all((not m.is_dir() and m.file_size <= self.MAX_BYTES and (not m.flag_bits & 1) and (m.external_attr >> 16 & 61440 != 40960) for m in members)), 'Unsafe archive member')
            report_bytes, input_bytes = (bundle.read(source['report_path']), bundle.read(source['input_path']))
        report, data = (self.context.adapter.strict_json(report_bytes), self.context.adapter.strict_json(input_bytes))
        self.validator_class(self.context.adapter.strict_json(snapshots['producer/schemas/architecture-release-candidate.schema.json']), format_checker=self.context.contracts.format_checker).validate(data)
        self.context.contracts.require(data['release_candidate'] is True and (not data['architecture'].get('exceptions')), 'Release gate required; live architecture waivers excluded')
        self.context.contracts.require(data['target_repository'] == report['target'] and report['target']['release_id'] == commit and (len(report['target']['commit']) >= 7) and commit.startswith(report['target']['commit']), 'Architecture input/report target differs')
        context = {'repository_id': scope['repository_id'], 'branch': 'main', 'commit_id': commit, 'producer_id': run['name'], 'run_id': str(run['id']), 'run_attempt': 1, 'baseline_ref': source['baseline_ref'], 'policy_revision': source['reference_commit'], 'event': 'push', 'purpose': 'release', 'release_context': True, 'synthetic': False, 'observed_at': artifact['created_at'], 'report_sha256': self.sha(report_bytes)}
        adapted = self.architecture.adapt_architecture(report_bytes, context, evaluated_at=captured_at)
        gate = next((g for g in adapted['candidates'] if g['subject']['rule_id'] == 'operation_readiness'))
        with self.temporary.TemporaryDirectory() as temp:
            p = self.Path(temp)
            (p / 'input.json').write_bytes(input_bytes)
            (p / 'policy.rego').write_bytes(snapshots['producer/policies/opa/architecture_operation_readiness.rego'])
            result = self.process.run(['opa', 'eval', '--format=json', '--data', str(p / 'policy.rego'), '--input', str(p / 'input.json'), 'data.architecture.operation_readiness.deny'], capture_output=True, check=True, timeout=30)
            denies = self.context.adapter.strict_json(result.stdout)['result'][0]['expressions'][0]['value']
        self.context.contracts.require(sorted(denies) == sorted(gate['source_messages']), 'Gate report differs from independent pinned OPA evaluation')
        return {'profile_ref': self.context.preparation.revision_ref(profile), 'repository_id': scope['repository_id'], 'captured_at': captured_at, 'source': {'run_id': run['id'], 'run_attempt': 1, 'commit_id': commit, 'workflow_id': run['workflow_id'], 'workflow_path': source['workflow_path'], 'artifact_id': artifact['id'], 'artifact_sha256': self.sha(archive), 'report_sha256': self.sha(report_bytes), 'input_sha256': self.sha(input_bytes), 'observed_at': artifact['created_at'], 'policy_revision': source['reference_commit'], 'verified_file_digests': source['reference_files']}, 'criterion': {'id': 'operation_readiness', 'resource': 'repository', 'granularity': 'gate', 'status': 'fail' if denies else 'pass', 'source_status': gate['result'], 'source_messages': gate['source_messages']}}

    def collect_preflight(self, run_id, output_dir, *, repo_root=_OMITTED, fetch=_DEFAULT_FETCH, captured_at=None):
        if repo_root is _OMITTED:
            repo_root = self.root
        if fetch is _DEFAULT_FETCH:
            fetch = self.default_fetch
        profile = self.context.consumer_contracts.load_operating(repo_root)
        source = profile['source']
        self.context.contracts.require(re.fullmatch('[1-9][0-9]*', str(run_id)) is not None, 'Positive run identity required')
        destination = self.Path(output_dir).resolve()
        root = self.Path(repo_root).resolve()
        self.context.contracts.require(not destination.exists(), 'Capture destination already exists')
        if destination.is_relative_to(root):
            self.context.contracts.require(destination.is_relative_to(root / 'generated/reports/consumer-lifecycle-preflight'), 'Dedicated consumer preflight directory required')
        endpoint = 'repos/' + profile['scope']['repository_id']
        baseline = 'repos/' + source['baseline_repository']
        snapshots = {}

        def get(name, path):
            snapshots[name] = fetch(path)
            return self.context.adapter.strict_json(snapshots[name])
        get('repository.json', endpoint)
        run_endpoint = endpoint + '/actions/runs/' + str(run_id)
        run = get('run-before.json', run_endpoint)
        self.context.contracts.require(str(run['id']) == str(run_id) and type(run['run_attempt']) is int and (run['run_attempt'] == 1), 'Run identity or attempt differs')
        self.context.contracts.require(re.fullmatch('[a-f0-9]{40}', run['head_sha']) is not None, 'Full commit required')
        get('workflow.json', endpoint + '/actions/workflows/' + self.positive_id(run['workflow_id']))
        artifacts = []
        for page in range(1, 11):
            listing = self.context.adapter.strict_json(fetch(run_endpoint + f'/artifacts?per_page=100&page={page}'))
            artifacts.extend(listing['artifacts'])
            if len(artifacts) >= listing['total_count']:
                break
        else:
            raise ValueError('Artifact inventory limit exceeded')
        matching = [a for a in artifacts if a['name'] == source['artifact_name']]
        self.context.contracts.require(len(matching) == 1, 'Exactly one architecture artifact required')
        artifact_endpoint = endpoint + '/actions/artifacts/' + self.positive_id(matching[0]['id'])
        artifact = get('artifact-before.json', artifact_endpoint)
        self.context.contracts.require(artifact == matching[0], 'Artifact inventory race')
        self.context.contracts.require(0 < artifact['size_in_bytes'] <= self.MAX_BYTES, 'Artifact too large')
        snapshots['artifact.zip'] = fetch(artifact_endpoint + '/zip')
        snapshots['consumer-workflow.yml'] = fetch(endpoint + '/contents/' + source['workflow_path'] + '?ref=' + run['head_sha'], raw=True)
        get('baseline-ref.json', baseline + '/git/ref/tags/' + source['baseline_ref'])
        get('baseline-tag.json', baseline + '/git/tags/' + source['baseline_tag_object'])
        for path in source['reference_files']:
            snapshots['producer/' + path] = fetch(baseline + '/contents/' + path + '?ref=' + source['reference_commit'], raw=True)
        get('run-after.json', run_endpoint)
        get('artifact-after.json', artifact_endpoint)
        at = captured_at or self.clock()
        result = self.verify_capture(profile, snapshots, captured_at=at)
        result['capture'] = {'method': self.profile.capture_method if fetch is self.default_fetch else 'injected_test_transport', 'snapshot_sha256': {p: self.sha(b) for p, b in snapshots.items()}}
        snapshots['profile.json'] = self.context.adapter.json_bytes(profile)
        destination.mkdir(parents=True)
        for name, data in snapshots.items():
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(data)
        with (destination / 'preflight.json').open('xb') as stream:
            stream.write(self.context.adapter.json_bytes(result))
        return result

    def replay_capture(self, directory):
        root = self.Path(directory)
        self.context.contracts.require(root.is_dir() and (not any((p.is_symlink() for p in (root, *root.rglob('*'))))), 'Capture contains symlink')
        recorded = self.context.adapter.strict_json((root / 'preflight.json').read_bytes())
        profile = self.context.adapter.strict_json((root / 'profile.json').read_bytes())
        manifest = recorded['capture']['snapshot_sha256']
        self.context.contracts.require({str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} == set(manifest) | {'profile.json', 'preflight.json'}, 'Capture inventory differs')
        snapshots = {}
        for name, digest in manifest.items():
            self.context.contracts.require(not self.Path(name).is_absolute() and '..' not in self.Path(name).parts, 'Unsafe capture path')
            data = (root / name).read_bytes()
            self.context.contracts.require(self.sha(data) == digest, 'Capture bytes differ')
            snapshots[name] = data
        expected = self.verify_capture(profile, snapshots, captured_at=recorded['captured_at'])
        self.context.contracts.require({k: v for k, v in recorded.items() if k != 'capture'} == expected, 'Capture projection differs')
        return expected
