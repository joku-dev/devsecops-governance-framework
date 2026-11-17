"""Native source-layout observations; no API call or enforcement inference."""
from pathlib import Path

SOURCE_CI_PROFILES = ('github-actions', 'gitlab-ci', 'bamboo')


def local_source_signals(profile, root):
    root = Path(root)
    if profile == 'github-actions':
        present = (root / '.github/workflows/ci.yml').is_file()
        security = any((root / '.github/workflows').glob('*security*'))
    elif profile == 'gitlab-ci':
        present = (root / '.gitlab-ci.yml').is_file()
        security = any((root / '.gitlab').glob('**/*security*'))
    elif profile == 'bamboo':
        present = any((root / 'bamboo-specs').glob('bamboo.y*ml'))
        security = any((root / 'bamboo-specs').glob('**/*security*'))
    else:
        raise ValueError('unsupported_source_ci_profile')
    return {'ci_definition_present': bool(present), 'security_workflow_present': bool(security)}


INTAKE_SIGNATURE_FILES = ('.github/workflows/intake-governance-result.yml',
    '.github/workflows/intake-architecture-result.yml', '.github/workflows/intake-evidence-trust.yml')


def committed_intake_signatures(provider, read_bytes):
    if provider != 'github-actions':
        raise ValueError('unsupported_intake_configuration_profile')
    observations = {}
    for name in INTAKE_SIGNATURE_FILES:
        content = read_bytes(name).decode('utf-8')
        observations[name] = {
            'repository_scope_expression_present': 'github.event.client_payload.repository_id || inputs.repository_id' in content,
            'run_scope_expression_present': 'github.event.client_payload.run_id || inputs.run_id' in content,
            'cancellation_disabled_signature_present': 'cancel-in-progress: false' in content}
    return observations


CONFIGURATION_PROVIDERS = ('github-actions',)
CONFIGURATION_SOURCE_FILES = INTAKE_SIGNATURE_FILES


def configuration_source_profile(provider):
    if provider not in CONFIGURATION_PROVIDERS:
        raise ValueError('unsupported_source_configuration_profile')
    return {'kind': 'legacy-central-intake-signatures-v1', 'provider': provider, 'source_signature_only': True}


def iter_ci_files(target_repo: Path):
    patterns = [
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
        "*.gitlab-ci.yml",
        "Jenkinsfile",
        "azure-pipelines.yml",
        "azure-pipelines.yaml",
    ]
    seen = set()
    for pattern in patterns:
        for path in target_repo.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path

def load_texts(paths):
    texts = []
    for path in paths:
        try:
            texts.append((path, path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue
    return texts

def build_check(check_id: str, description: str, passed: bool, details: str):
    return {
        "check_id": check_id,
        "description": description,
        "status": "pass" if passed else "fail",
        "details": details,
    }

def integration_report(target_repo, *, product_label, target_label, at, canonical_order=False, ci_files=None):
    ci_files = list(iter_ci_files(target_repo)) if ci_files is None else list(ci_files)
    if canonical_order:
        ci_files.sort(key=lambda path: path.relative_to(target_repo).as_posix().encode('utf-8'))
    ci_texts = load_texts(ci_files)
    governance_reference_patterns = ['devsecops-governance-framework', 'devsecops-governance-as-code', 'validate_governance_repo.py', 'check_repo_governance_integration.py', 'governance-compliance-result.json']
    governance_command_patterns = ['validate_governance_repo.py', 'unittest discover -s tests', 'opa check']
    governance_workflow_patterns = ['uses: joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-reusable.yml', 'uses: joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-reusable.yml@', 'uses: joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-reusable.yml', 'uses: joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-reusable.yml@', 'application_evidence_artifact_name:', 'artifact_path:', 'sbom_path:', 'vulnerability_scan_path:']
    reference_hits = []
    command_hits = []
    workflow_hits = []
    for path, text in ci_texts:
        for pattern in governance_reference_patterns:
            if pattern in text:
                reference_hits.append(f'{path.relative_to(target_repo)} -> {pattern}')
        for pattern in governance_command_patterns:
            if pattern in text:
                command_hits.append(f'{path.relative_to(target_repo)} -> {pattern}')
        for pattern in governance_workflow_patterns:
            if pattern in text:
                workflow_hits.append(f'{path.relative_to(target_repo)} -> {pattern}')
    checks = [build_check('governance_ci_file_present', 'A CI pipeline file is present in the target repository.', len(ci_files) > 0, 'Found CI files: ' + ', '.join((str(path.relative_to(target_repo)) for path in ci_files)) if ci_files else 'No supported CI files were found.'), build_check('governance_reference_present', 'The target repository references the governance repository or governance templates.', len(reference_hits) > 0, '; '.join(reference_hits) if reference_hits else 'No governance repository or template references found in CI files.'), build_check('governance_commands_present', 'The target repository CI includes expected governance validation commands or a reusable governance workflow integration.', len(command_hits) >= 2 or len(workflow_hits) >= 2, '; '.join(command_hits + workflow_hits) if command_hits or workflow_hits else 'No expected governance command references or reusable governance workflow markers found in CI files.')]
    status = 'pass' if all((check['status'] == 'pass' for check in checks)) else 'fail'
    result = {'schema_version': '1.0.0', 'governance_repo': product_label, 'target_repo': Path(target_label).name, 'timestamp': at, 'status': status, 'checks': checks}
    return result


INSPECTION_PROFILES = ('legacy-ci-signatures-v1', 'canonical-ci-signatures-v2')


def source_inspection_profile(profile):
    if profile not in INSPECTION_PROFILES: raise ValueError('unsupported_source_inspection_profile')
    kind = 'canonical-ci-source-signatures-v2' if profile == 'canonical-ci-signatures-v2' else 'legacy-ci-source-signatures-v1'
    return {'kind': kind, 'profile': profile, 'source_signature_only': True}


def source_inspection_ci_paths(profile, root, observed=None):
    """Bind finite CI iteration as input metadata; source content remains Git-only."""
    source_inspection_profile(profile); root = Path(root)
    current = [path.relative_to(root).as_posix() for path in iter_ci_files(root)]
    if profile == 'canonical-ci-signatures-v2': current.sort(key=lambda name: name.encode('utf-8'))
    if observed is None: return current
    if (not isinstance(observed, list) or len(observed) > 10000 or any(not isinstance(name, str) for name in observed)
            or len(set(observed)) != len(observed) or set(observed) != set(current)):
        raise ValueError('source_inspection_ci_iteration_members_changed')
    if profile == 'canonical-ci-signatures-v2' and observed != current:
        raise ValueError('source_inspection_canonical_ci_order_required')
    return list(observed)


def source_inspection_facts(profile, root, *, product_label, target_label, at, ci_paths=None):
    source_inspection_profile(profile)
    root = Path(root)
    selected_ci = source_inspection_ci_paths(profile, root, ci_paths)
    # This is the original union of source-layout signatures, not live provider
    # support or effective pipeline configuration. The old two tools used
    # deliberately different file patterns; preserve both finite selections.
    paths = sorted({path for pattern in ('.github/workflows/*.yml', '.github/workflows/*.yaml',
        '*.gitlab-ci.yml', 'Jenkinsfile') for path in root.glob(pattern) if path.is_file()})
    texts = []
    for path in paths:
        try: texts.append(path.read_text(encoding='utf-8'))
        except UnicodeDecodeError: texts.append('')
    return {'integration': integration_report(root, product_label=product_label, target_label=target_label, at=at,
                canonical_order=profile == 'canonical-ci-signatures-v2',
                ci_files=[root/name for name in selected_ci]),
            'onboarding_ci_files': [path.relative_to(root).as_posix() for path in paths],
            'onboarding_ci_text': '\n'.join(texts)}
