"""Retained V1 historical consistency over explicit data and capture adapters.

Historical outputs describe their original scope; they confer no operating
acceptance, personal consent or authority on the executing V2 node.
"""
_OMITTED = object()
PREPARATION_PATH = 'model/governance/lifecycle/live-pilot'

class LifecyclePreparation:

    def __init__(self, root, context, *, path_factory):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.PREPARATION_PATH = PREPARATION_PATH

    def revision_ref(self, record):
        return {'revision': record['revision'], 'digest': self.context.contracts.canonical_digest(record)}

    def validate_bindings(self, records):
        self.context.contracts.require(bool(records), 'Pilot role history is required')
        previous = None
        for revision, record in enumerate(records, 1):
            self.context.contracts.schema_validator('pilot-role-binding').validate(record)
            self.context.contracts.require(record['revision'] == revision, 'Role history has a gap or competing revision')
            self.context.contracts.require(record['previous_ref'] == (self.revision_ref(previous) if previous else None), 'Role predecessor differs')
            if previous:
                self.context.contracts.require(self.context.contracts.timestamp(record['recorded_at']) >= self.context.contracts.timestamp(previous['recorded_at']), 'Role history time regressed')
            subjects = {s['subject_id']: s for s in record['subjects']}
            self.context.contracts.require(len(subjects) == len(record['subjects']), 'Duplicate pilot subject')
            for subject in subjects.values():
                self.context.contracts.require(subject['subject_id'] == self.context.provider.subject_id(subject['provider_user_id']), 'Provider identity differs')
                self.context.contracts.require(subject['profile_url'] == self.context.provider.profile_url(subject['login']), 'Provider profile differs')
            assigned = list(record['assignments'].values())
            self.context.contracts.require(set(assigned) <= set(subjects), 'Assigned person is missing')
            self.context.contracts.require(len(set(assigned)) == len(assigned) or record['multiple_roles_confirmed'], 'Multiple roles require explicit confirmation')
            previous = record
        return previous

    def effective_assignments(self, records):
        """Describe the confirmed appointment; this is not a runtime authorization API."""
        latest = self.validate_bindings(records)
        return dict(latest['assignments']) if latest['status'] == 'confirmed' else {}

    def load_revision_files(self, directory):
        root = self.path_factory(directory)
        self.context.contracts.require(root.is_dir() and (not root.is_symlink()), 'Versioned preparation directory is required')
        paths = sorted(root.iterdir())
        self.context.contracts.require(bool(paths), 'Empty preparation history')
        records = []
        for revision, path in enumerate(paths, 1):
            self.context.contracts.require(path.is_file() and (not path.is_symlink()) and (path.name == f'{revision:08d}.json'), 'Unexpected preparation file or revision gap')
            records.append(self.context.adapter.strict_json(path.read_bytes()))
        return records

    def validate_preparation(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.path_factory(repo) / PREPARATION_PATH
        self.context.contracts.require({p.name for p in root.iterdir()} == {'role-bindings', 'profiles'}, 'Unexpected preparation path')
        bindings = self.load_revision_files(root / 'role-bindings')
        latest = self.validate_bindings(bindings)
        profiles = self.load_revision_files(root / 'profiles')
        previous = None
        for revision, profile in enumerate(profiles, 1):
            self.context.contracts.schema_validator('live-profile-preparation').validate(profile)
            self.context.contracts.require(profile['revision'] == revision, 'Profile revision differs')
            self.context.contracts.require(profile['previous_ref'] == (self.revision_ref(previous) if previous else None), 'Profile predecessor differs')
            binding_revision = profile['role_binding_ref']['revision']
            self.context.contracts.require(binding_revision <= len(bindings), 'Profile role binding is missing')
            self.context.contracts.require(profile['role_binding_ref'] == self.revision_ref(bindings[binding_revision - 1]), 'Profile role binding digest differs')
            previous = profile
        self.context.contracts.require(profiles[-1]['role_binding_ref'] == self.revision_ref(latest), 'Current preparation must reflect latest role replacement or withdrawal')
        return {'profile': profiles[-1], 'binding': latest, 'assignments': self.effective_assignments(bindings), 'runtime_authorized': False}
