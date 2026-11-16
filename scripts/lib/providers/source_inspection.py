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
