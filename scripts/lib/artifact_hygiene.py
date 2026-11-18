"""Pure ordered text assessment for the original public-artifact hygiene profile."""


def configured_terms(cli_terms, environment):
    env_terms = [term.strip() for term in environment.split(',') if term.strip()]
    return [term.casefold() for term in [*cli_terms, *env_terms] if term]


def assess(path_count, texts, terms):
    """Return the entire original exit/stdout/stderr; no terms or content persisted."""
    if not terms:
        return 1, '', 'No forbidden terms configured\n'
    if sum(len(text) for _, text in texts) * len(terms) > 256 * 1024**2:
        raise ValueError('artifact_hygiene_matching_budget')
    findings = []
    for location, text in texts:
        folded = text.casefold()
        if any(term in folded for term in terms):
            findings.append(location)
    if findings:
        return 1, ('Public artifact hygiene failed; forbidden content detected in:\n'
                   + ''.join(f'- {location}\n' for location in findings)), ''
    return 0, f'Public artifact hygiene passed for {path_count} paths\n', ''
