"""Bind an approved external OPA binary through a stable environment alias.

Only a virtual-environment selection alias may have a private-looking label.
The actual canonical target still passes the ordinary tool/private-path guards,
the approved content hash and the source/node exclusion checks.
"""
from pathlib import Path, PurePosixPath
from lib.providers.document_rendering_tools import program_identity
from lib.repository_capture import private_name
from lib.requirement_validation_budget import InputAdmissionError


def approved_external_program(label, cwd, source, private_state, approved_hashes):
    requested = Path(label)
    if not requested.is_absolute():
        requested = Path(cwd) / requested
    if private_name(str(requested)):
        # Preserve credential/cache/key restrictions. A venv alias alone is
        # not itself evidence that the executable target is a private file.
        ordinary_parts = [p for p in PurePosixPath(str(requested)).parts
                          if p.casefold() != 'venv' and not p.casefold().startswith('.venv')]
        if private_name(str(PurePosixPath(*ordinary_parts))):
            raise InputAdmissionError('consumer_opa_private_selection_forbidden')
    resolved = requested.resolve(strict=True)
    identity = program_identity(str(resolved), cwd)
    if requested.resolve(strict=True) != resolved:
        raise InputAdmissionError('consumer_opa_selection_alias_changed')
    if (identity['sha256'] not in approved_hashes
            or resolved.is_relative_to(Path(source)) or resolved.is_relative_to(Path(private_state))):
        raise InputAdmissionError('consumer_opa_pinned_external_executable_required')
    return {**identity, 'label': label}
