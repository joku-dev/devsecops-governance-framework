"""The explicit composition boundary between neutral applications and adapters.

Core callers consume normalized contracts here. Only this composition module and
provider modules select concrete implementations; no plugin code is discovered
from an application checkout or downloaded configuration.
"""
from typing import Protocol

from lib.providers.workbench import WorkbenchPublication
from lib.providers.context import collect_context, checked_out_revision
from lib.providers.transports import Reader, capture, BoundedAudit
from lib.providers.operations import (SCM, Writer, GitWorkspace, branch, dispatch_ci,
                                     require_compatible, run_link)
from lib.providers.discovery import (discover_page, bootstrap_archive,
                                    validate_discovery_profile, validate_api_endpoint,
                                    physical_job_matches, producer_job_matches,
                                    validate_candidate_composition)
from lib.providers.legacy_interop import (reject_legacy_activity,
                                         legacy_consumer_relinquished, validate_legacy_profiles)


class ReadPort(Protocol):
    """Credential-bound, bounded native reads; no inferred governance decisions."""
    def get(self, path: str): ...
    def pages(self, path: str, field=None, limit=25): ...
    def download(self, path: str, destination): ...


class ProposalPort(Protocol):
    """Normalized change requests, including terminal-state reconciliation."""
    def check_identity(self): ...
    def branch_sha(self, name: str) -> str: ...
    def changes(self, source=None, target=None, *, prefixes=None): ...
    def propose(self, source, target, sha, title, body): ...


class ExecutionPort(Protocol):
    """Discovery and capture keep native identifiers separate from decisions."""
    def discover(self, profile, reader: ReadPort, *, page, start, end): ...
    def capture(self, context, policy, reader: ReadPort, archive, *, at): ...

from lib.providers.discovery import CI_PROVIDERS
