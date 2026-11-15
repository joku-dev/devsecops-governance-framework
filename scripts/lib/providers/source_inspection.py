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
