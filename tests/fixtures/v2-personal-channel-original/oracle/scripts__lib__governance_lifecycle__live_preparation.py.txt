"""Validate versioned pilot appointments and disabled preparation; never authorize intake."""
from pathlib import Path
import re

from .adapter import strict_json
from .contracts import ROOT, canonical_digest, require, schema_validator, timestamp

PREPARATION_PATH = "model/governance/lifecycle/live-pilot"


def revision_ref(record):
    return {"revision": record["revision"], "digest": canonical_digest(record)}


def validate_bindings(records):
    require(bool(records), "Pilot role history is required")
    previous = None
    for revision, record in enumerate(records, 1):
        schema_validator("pilot-role-binding").validate(record)
        require(record["revision"] == revision, "Role history has a gap or competing revision")
        require(record["previous_ref"] == (revision_ref(previous) if previous else None), "Role predecessor differs")
        if previous:
            require(timestamp(record["recorded_at"]) >= timestamp(previous["recorded_at"]), "Role history time regressed")
        subjects = {s["subject_id"]: s for s in record["subjects"]}
        require(len(subjects) == len(record["subjects"]), "Duplicate pilot subject")
        for subject in subjects.values():
            require(subject["subject_id"] == f"github-user:{subject['provider_user_id']}", "Provider identity differs")
            require(subject["profile_url"] == f"https://github.com/{subject['login']}", "Provider profile differs")
        assigned = list(record["assignments"].values())
        require(set(assigned) <= set(subjects), "Assigned person is missing")
        require(len(set(assigned)) == len(assigned) or record["multiple_roles_confirmed"], "Multiple roles require explicit confirmation")
        previous = record
    return previous


def effective_assignments(records):
    """Describe the confirmed appointment; this is not a runtime authorization API."""
    latest = validate_bindings(records)
    return dict(latest["assignments"]) if latest["status"] == "confirmed" else {}


def load_revision_files(directory):
    root = Path(directory)
    require(root.is_dir() and not root.is_symlink(), "Versioned preparation directory is required")
    paths = sorted(root.iterdir())
    require(bool(paths), "Empty preparation history")
    records = []
    for revision, path in enumerate(paths, 1):
        require(path.is_file() and not path.is_symlink() and path.name == f"{revision:08d}.json", "Unexpected preparation file or revision gap")
        records.append(strict_json(path.read_bytes()))
    return records


def validate_preparation(repo=ROOT):
    root = Path(repo) / PREPARATION_PATH
    require({p.name for p in root.iterdir()} == {"role-bindings", "profiles"}, "Unexpected preparation path")
    bindings = load_revision_files(root / "role-bindings")
    latest = validate_bindings(bindings)
    profiles = load_revision_files(root / "profiles")
    previous = None
    for revision, profile in enumerate(profiles, 1):
        schema_validator("live-profile-preparation").validate(profile)
        require(profile["revision"] == revision, "Profile revision differs")
        require(profile["previous_ref"] == (revision_ref(previous) if previous else None), "Profile predecessor differs")
        binding_revision = profile["role_binding_ref"]["revision"]
        require(binding_revision <= len(bindings), "Profile role binding is missing")
        require(profile["role_binding_ref"] == revision_ref(bindings[binding_revision - 1]), "Profile role binding digest differs")
        previous = profile
    require(profiles[-1]["role_binding_ref"] == revision_ref(latest), "Current preparation must reflect latest role replacement or withdrawal")
    return {"profile": profiles[-1], "binding": latest, "assignments": effective_assignments(bindings),
            "runtime_authorized": False}
