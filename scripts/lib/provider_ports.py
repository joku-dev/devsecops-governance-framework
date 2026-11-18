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
from lib.providers.source_inspection import SOURCE_CI_PROFILES, local_source_signals, committed_intake_signatures, CONFIGURATION_PROVIDERS, CONFIGURATION_SOURCE_FILES, configuration_source_profile
from lib.providers.measured_ports import (MEASURED_PROVIDERS, measured_import, measured_capture_live,
                                          measured_export, measured_validate, measured_supplement_profile)

from lib.providers.typed_ports import TYPED_PROVIDERS, typed_import, typed_verify, typed_capture_live
from lib.providers.result_profiles import RESULT_EVENT_PROFILES, result_index_profile
from lib.providers.general_result_ports import (NATIVE_RESULT_PROVIDERS, general_result_capture,
                                                general_result_verify)

from lib.providers.source_inspection import (INSPECTION_PROFILES, source_inspection_profile, source_inspection_facts, source_inspection_ci_paths, onboarding_source_surface)

from lib.providers.pipeline_environment import (PROFILES as DECLARED_PIPELINE_PROFILES,
                                               declared_environment as declared_pipeline_environment)
from lib.providers.review_metadata import REVIEW_EVENT_PROFILES, review_event, committed_review_event

from lib.providers.review_planning import PROFILES as REVIEW_PLAN_PROFILES, review_plan_profile, review_commit_profile, resolve_review_base
from lib.providers.review_planning import DISPATCH_PROFILES as REVIEW_DISPATCH_PROFILES, review_dispatch_profile
from lib.providers.review_dispatch import (capture as capture_dispatch_source,
    observe as observe_dispatch_source, validate as validate_dispatch_source)
from lib.providers.review_dispatch_files import (PROFILES as DISPATCH_FILE_PROFILES,
    profile as dispatch_file_profile, legacy_label as dispatch_file_label,
    capture as capture_dispatch_files, validate as validate_dispatch_files,
    write_rows as apply_dispatch_files, verify_outputs as verify_dispatch_file_outputs)

from lib.providers.local_source_observation import (PROFILES as LOCAL_SOURCE_PROFILES,
    profile as local_source_profile, capture as capture_local_source,
    validate as validate_local_source, facts as local_source_facts,
    MAX_FILE as LOCAL_SOURCE_MAX_FILE, MAX_TEXT as LOCAL_SOURCE_MAX_TEXT,
    MAX_FACTS as LOCAL_SOURCE_MAX_FACTS)

from lib.providers.review_execution import (PROFILES as REVIEW_EXECUTION_PROFILES,
    profile as review_execution_profile, adapter as review_execution_adapter,
    command as review_execution_command, observations as review_execution_observations,
    OutputDirectory as ReviewExecutionOutput, execute as execute_review_process)

from lib.providers.attestation_verification import (PROFILES as ATTESTATION_PROFILES,
    profile as attestation_profile, verify as verify_attestation_signature,
    initial_observation as attestation_crypto_initial, outcome as attestation_crypto_outcome)

from lib.providers.intake_recording import (PROFILES as INTAKE_RECORD_PROFILES,
    profile as intake_record_profile,event_defaults as intake_record_event_defaults,
    token_value as intake_record_token,endpoint as intake_record_endpoint,
    selected_endpoint as intake_record_api_selection,
    acquire as acquire_intake_record_metadata,metadata_projection as intake_record_metadata,
    attempt_source as intake_attempt_source,event_sources as intake_event_sources,
    initial_observation as intake_record_initial_observation)

from lib.providers.process_groups import consistent as native_cleanup_observation_valid
from lib.providers.validation_tools import ValidationOPA
from lib.providers.validation_worktree import ValidationWorktree
from lib.providers.release_references import ReleaseReferences,ReleaseSource
from lib.providers.release_verification import ReleaseVerificationEnvironment
from lib.providers.repository_acquisition_replay import audit_acquisition as audit_repository_acquisition
from lib.providers.repository_profiles import (REPOSITORY_ENGINE_PROFILES, repository_engine_profile, repository_git_tool)


def execute_repository_operation(*args, **options):
    # The native composition uses neutral engine modules. Delay its imports
    # until the explicit application call, after provider ports are available.
    from lib.providers.repository_runner import execute_repository_operation as execute
    return execute(*args, **options)


def load_repository_operation(*args, **options):
    from lib.providers.repository_operations import load_operation
    return load_operation(*args, **options)


def repository_operation_header(root):
    from lib.providers.repository_journal import read_journal
    return read_journal(root)[0]['payload']['binding']


def inspect_repository_worker(root, header):
    from lib.providers.repository_worker import inspect_operation
    return inspect_operation(root, header)
