"""Read-only Self-Security preflight: verify captured bindings, never accept lifecycle state."""
from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import re
import subprocess
import zipfile

from jsonschema import Draft202012Validator
import yaml

from .adapter import json_bytes, strict_json
from .contracts import FORMAT_CHECKER, ROOT, require, timestamp
from .live_preparation import validate_preparation, revision_ref

MAX_BYTES = 10 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def positive_id(value):
    require(type(value) is int and value > 0, "Expected positive provider integer identity")
    return str(value)


def verify_capture(profile, *, repository, run, workflow, artifact, archive, files, captured_at):
    """Check supplied metadata/bytes. Offline callers do not establish provider authenticity."""
    from .contracts import schema_validator
    schema_validator("live-profile-preparation").validate(profile)
    scope, source = profile["scope"], profile["source"]
    repo_id = scope["github_repository_id"]
    require(repository["id"] == repo_id and repository["full_name"] == scope["repository_id"], "Repository identity differs")
    require(repository["default_branch"] == source["allowed_branch"], "Default branch differs")
    positive_id(run["id"]); positive_id(run["workflow_id"])
    require(run["repository"]["id"] == repo_id and run["head_repository"]["id"] == repo_id, "Run repository or fork differs")
    require(run["head_branch"] == source["allowed_branch"] and run["event"] == source["allowed_event"], "Only selected mainline pushes are supported")
    require(run["status"] == "completed" and run["conclusion"] == "success", "Run is not successfully completed")
    require(type(run["run_attempt"]) is int and run["run_attempt"] == 1, "Rerun artifact-to-attempt binding is not supported")
    commit = run["head_sha"]
    require(re.fullmatch(r"[a-f0-9]{40}", commit) is not None, "Full run commit required")
    require(run["path"] == source["workflow_path"] and workflow["path"] == source["workflow_path"]
            and workflow["id"] == run["workflow_id"], "Workflow identity differs")
    positive_id(artifact["id"])
    require(artifact["name"] == source["artifact_name"] and artifact["expired"] is False, "Artifact name or availability differs")
    require(type(artifact["size_in_bytes"]) is int and 0 < artifact["size_in_bytes"] <= MAX_BYTES
            and 0 < len(archive) <= MAX_BYTES, "Artifact exceeds supported size")
    require(artifact["digest"] == "sha256:" + sha(archive), "Raw archive digest differs from GitHub metadata")
    arun = artifact["workflow_run"]
    require(arun["id"] == run["id"] and arun["repository_id"] == repo_id and arun["head_repository_id"] == repo_id
            and arun["head_sha"] == commit and arun["head_branch"] == source["allowed_branch"], "Artifact run association differs")
    require(set(files) == set(source["reference_files"]), "Pinned producer file set differs")
    for path, digest in source["reference_files"].items():
        require(sha(files[path]) == digest, "Producer revision differs: " + path)
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        members = bundle.infolist()
        expected = {source["report_path"], "governance-repository-security.md"}
        require(len(members) == len(expected) and {m.filename for m in members} == expected, "Unexpected or duplicate archive member")
        require(all(not m.is_dir() and m.file_size <= MAX_BYTES and not m.flag_bits & 1 for m in members), "Unsupported archive member")
        report_bytes = bundle.read(source["report_path"])
    report = strict_json(report_bytes)
    schema_path = "schemas/governance-repository-security-report.schema.json"
    Draft202012Validator(strict_json(files[schema_path]), format_checker=FORMAT_CHECKER).validate(report)
    model = yaml.safe_load(files["model/controls/governance-repository-security.yaml"])
    require(report["repository_id"] == scope["repository_id"] and report["profile_id"] == model["profile_id"]
            and report["profile_version"] == model["version"], "Report source profile or repository differs")
    observation = report["observation"]
    require(observation.get("synthetic", False) is False, "Synthetic observation is not a live capture")
    require(observation["repository_id"] == scope["repository_id"] and observation["observed_at"] == report["observed_at"], "Observation identity differs")
    start, observed, created, completed, captured = map(timestamp, (run["run_started_at"], report["observed_at"],
        artifact["created_at"], run["updated_at"], captured_at))
    require(start <= observed <= created <= completed <= captured, "Producer observation/artifact timeline differs")
    require(captured < timestamp(artifact["expires_at"]), "Artifact is expired at capture time")
    definitions = {c["id"]: c for c in model["criteria"]}
    criteria = report["criteria"]
    require(len(criteria) == len(definitions) and {c["id"] for c in criteria} == set(definitions), "Criterion coverage differs")
    for criterion in criteria:
        definition = definitions[criterion["id"]]
        require(all(criterion[k] == definition[k] for k in ("id", "key", "title", "severity", "expected")), "Criterion definition differs")
    criterion = next(c for c in criteria if c["id"] == "GRS-002")
    reviews = observation["repository"]["required_approving_reviews"]
    require(type(reviews) is int and reviews >= 0, "Review count is missing or ambiguous")
    require(criterion["key"] == "pull_request_review_required" and criterion["observed"] is (reviews >= 1)
            and criterion["status"] == ("pass" if reviews >= 1 else "fail"), "GRS-002 contradicts captured review count")
    failures = [c for c in criteria if c["status"] == "fail"]
    expected_summary = {"criteria": len(criteria), "pass": len(criteria) - len(failures), "fail": len(failures),
        "critical_failures": sum(c["severity"] == "critical" for c in failures),
        "high_failures": sum(c["severity"] == "high" for c in failures)}
    require(report["summary"] == expected_summary and report["overall_status"] == ("findings" if failures else "pass"), "Report summary differs")
    result = {"schema_version": "0.1.0", "record_type": "lifecycle-live-evidence-preflight", "environment": "diagnostic",
        "official_state": False, "enforcement": "report_only", "acceptance_status": "not_evaluated",
        "verification_scope": "captured_metadata_and_bytes", "captured_at": captured_at,
        "profile_ref": revision_ref(profile), "repository_id": scope["repository_id"],
        "source": {"run_id": run["id"], "run_attempt": run["run_attempt"], "commit_id": commit,
            "workflow_id": run["workflow_id"], "workflow_path": source["workflow_path"],
            "artifact_id": artifact["id"], "artifact_sha256": sha(archive), "report_sha256": sha(report_bytes),
            "observed_at": report["observed_at"], "age_seconds": int((captured - observed).total_seconds()),
            "source_profile_version": report["profile_version"], "verified_file_digests": {p:sha(b) for p,b in files.items()}},
        "criterion": {"id": "GRS-002", "resource": scope["resource"], "status": criterion["status"],
            "required_approving_reviews": reviews},
        "checks": {name:"pass" for name in ("repository_identity", "mainline_run_context", "workflow_identity",
            "first_attempt_binding", "artifact_run_association", "archive_integrity", "pinned_producer_revision",
            "source_profile_and_criterion", "producer_timeline", "report_consistency")},
        "remaining_acceptance": ["approved_trust_roots_and_custody_retention", "approved_freshness_skew_and_replay_policy",
            "durable_live_replay_and_conflict_acceptance", "personal_consent_verifier", "accountable_live_acceptance"],
        "limits": ["captured_provider_metadata_is_not_independently_authenticated_by_offline_replay",
            "branch_protection_is_observed_at_run_time_not_proven_for_every_instant_of_the_commit",
            "source_api_errors_are_preserved_in_the_report", "no_lifecycle_observation_or_state_transition"]}
    return result, report_bytes


def github_get(endpoint, *, raw=False):
    """Use only GitHub's official API host and a fixed GET method; credentials stay in gh."""
    command = ["gh", "api", "--hostname", "github.com", "--method", "GET", endpoint]
    if raw:
        command.extend(["-H", "Accept: application/vnd.github.raw+json"])
    return subprocess.check_output(command, timeout=90)


def collect_preflight(run_id, output_dir, *, repo_root=ROOT, fetch=github_get, captured_at=None):
    prepared = validate_preparation(repo_root)
    require(prepared["assignments"], "Pilot appointments have been withdrawn")
    profile = prepared["profile"]; source = profile["source"]
    require(re.fullmatch(r"[1-9][0-9]*", str(run_id)) is not None, "Positive run ID required")
    destination = Path(output_dir).resolve()
    require(not destination.exists(), "Capture directory already exists; snapshots are immutable")
    root = Path(repo_root).resolve()
    if destination.is_relative_to(root):
        require(destination.is_relative_to(root / "generated/reports/lifecycle-live-preflight"), "Dedicated diagnostic capture directory required")
    endpoint = "repos/" + profile["scope"]["repository_id"]
    snapshots = {}
    def get(name, path):
        data = fetch(path); snapshots[name] = data
        return strict_json(data)
    repository = get("repository.json", endpoint)
    run_endpoint = endpoint + "/actions/runs/" + str(run_id)
    run = get("run-before.json", run_endpoint)
    require(str(run["id"]) == str(run_id), "Requested run identity differs")
    require(type(run["run_attempt"]) is int and run["run_attempt"] == 1, "Rerun artifact-to-attempt binding is not supported")
    require(re.fullmatch(r"[a-f0-9]{40}", run["head_sha"]) is not None, "Full run commit required")
    workflow = get("workflow.json", endpoint + "/actions/workflows/" + positive_id(run["workflow_id"]))
    artifacts = []
    for page in range(1, 11):
        listing = get(f"artifacts-page-{page}.json", run_endpoint + f"/artifacts?per_page=100&page={page}")
        artifacts.extend(listing["artifacts"])
        if len(artifacts) >= listing["total_count"]:
            break
    else:
        raise ValueError("Artifact listing exceeds supported size")
    matches = [a for a in artifacts if a["name"] == source["artifact_name"]]
    require(len(matches) == 1, "Exactly one named run artifact is required")
    artifact_endpoint = endpoint + "/actions/artifacts/" + positive_id(matches[0]["id"])
    artifact = get("artifact-before.json", artifact_endpoint)
    require(artifact == matches[0], "Artifact listing changed during capture")
    require(type(artifact["size_in_bytes"]) is int and 0 < artifact["size_in_bytes"] <= MAX_BYTES, "Unsupported artifact size")
    archive = fetch(artifact_endpoint + "/zip")
    files = {p:fetch(endpoint + "/contents/" + p + "?ref=" + run["head_sha"], raw=True) for p in source["reference_files"]}
    run_after = get("run-after.json", run_endpoint)
    artifact_after = get("artifact-after.json", artifact_endpoint)
    require(run_after == run and artifact_after == artifact, "Provider metadata changed during capture")
    at = captured_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    result, report_bytes = verify_capture(profile, repository=repository, run=run, workflow=workflow,
        artifact=artifact, archive=archive, files=files, captured_at=at)
    snapshots.update({"profile.json":json_bytes(profile), "artifact.zip":archive, "report.json":report_bytes,
        **{"producer/" + p:b for p,b in files.items()}})
    result["capture"] = {"method":"github_api_get_via_gh" if fetch is github_get else "injected_test_transport",
        "api_origin": source["api_origin"], "snapshot_sha256": {p:sha(b) for p,b in snapshots.items()}}
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive directory creation protects existing captures, including races.
    # The completion manifest is written last; incomplete directories are not replayable.
    destination.mkdir()
    for name, data in snapshots.items():
        path = destination / name; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
    with (destination / "preflight.json").open("xb") as stream:
        stream.write(json_bytes(result))
    return result


def replay_capture(directory):
    """Recompute a saved capture without making any provider-authentication claim."""
    root = Path(directory)
    require(root.is_dir() and not root.is_symlink(), "Capture directory is required")
    require(all(not path.is_symlink() for path in root.rglob("*")), "Capture symlinks are not supported")
    recorded = strict_json((root / "preflight.json").read_bytes())
    manifest = recorded["capture"]["snapshot_sha256"]
    require({str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()} == set(manifest) | {"preflight.json"},
            "Capture inventory differs")
    for name, digest in manifest.items():
        require(not Path(name).is_absolute() and ".." not in Path(name).parts, "Invalid capture path")
        require(sha((root / name).read_bytes()) == digest, "Captured bytes differ: " + name)
    def read(name):
        return strict_json((root / name).read_bytes())
    profile = read("profile.json")
    run, artifact = read("run-before.json"), read("artifact-before.json")
    require(read("run-after.json") == run and read("artifact-after.json") == artifact, "Captured metadata race")
    expected, report_bytes = verify_capture(profile, repository=read("repository.json"), run=run,
        workflow=read("workflow.json"), artifact=artifact, archive=(root / "artifact.zip").read_bytes(),
        files={p:(root / "producer" / p).read_bytes() for p in profile["source"]["reference_files"]},
        captured_at=recorded["captured_at"])
    require((root / "report.json").read_bytes() == report_bytes, "Report extraction differs")
    require({k:v for k,v in recorded.items() if k != "capture"} == expected, "Preflight projection differs")
    return expected
