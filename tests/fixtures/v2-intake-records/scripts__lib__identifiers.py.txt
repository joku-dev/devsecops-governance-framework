"""Identifier and timestamp helpers used by governance intake scripts."""

from __future__ import annotations

import re


def slugify_repository(repository_id: str) -> str:
    """Convert an owner/repository identifier into a status directory name."""
    return repository_id.replace("/", "__")


def sanitize_timestamp(value: str) -> str:
    """Make an ISO-like timestamp safe for use in evidence filenames."""
    return re.sub(r"[:+]", "-", value)
