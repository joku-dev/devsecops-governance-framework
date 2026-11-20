"""Explicit original provider-specific workflow inventory, never source programs."""
LEGACY_MIGRATION_INVENTORY = (
    ('schemas', 'schemas', '*.json'),
    ('.github/workflows', 'workflows', '*.yml'),
    ('releases', 'releases', '*'),
)


def empty_min_error():
    """Retain the actual producer builtin diagnostic, without selecting a provider."""
    from lib.requirement_review_output import EMPTY_MIN_ERRORS
    from lib.requirement_validation_budget import InputAdmissionError
    try:
        min([])
    except ValueError as error:
        value=str(error)
    if value not in EMPTY_MIN_ERRORS:
        raise InputAdmissionError('requirement_review_unsupported_builtin_diagnostic')
    return value
