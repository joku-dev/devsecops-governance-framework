"""Original pipeline evidence/gate projection over explicitly retained input facts.

Inner success, enforced gates and approval/waiver fields are declarations only.
No workflow is executed and no approval or signature is verified here.
"""
from pathlib import PurePosixPath
from types import SimpleNamespace

SEVERITY_ORDER = {'none': 0, 'info': 1, 'low': 2, 'medium': 3, 'high': 4, 'critical': 5}

def as_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

def run_purpose(event: str, release_candidate: bool, branch: str) -> tuple[str, bool]:
    release_context = release_candidate and event == "push" and branch == "main"
    if release_context:
        return "release", True
    if event in {"workflow_dispatch", "manual", "manual_build"}:
        return "diagnostic", False
    if event in {"pull_request", "pr"}:
        return "pull_request_validation", False
    return "branch_validation", False

class FileFact:
    def __init__(self, label, facts):
        self.label = label; self.facts = facts; self.name = PurePosixPath(label).name
        self.sha256 = facts['sha256'] if facts else ''
    def __str__(self): return self.label
    def is_file(self): return self.facts is not None


def project(context, selector, parameters, observations, inputs, at):
    args = SimpleNamespace(**parameters)
    artifact = FileFact(args.artifact_path, inputs.get('artifact'))
    sbom = FileFact(args.sbom_path, inputs.get('sbom'))
    vulnerability_scan = FileFact(args.vulnerability_scan_path, inputs.get('scan'))
    signature = FileFact(args.signature_path, inputs.get('signature')) if args.signature_path else None
    max_seen = inputs['scan']['max_severity'] if inputs.get('scan') else observations['scan_fallback']
    max_allowed = args.max_allowed_severity.lower()
    purpose, release_context = run_purpose(str(context.get('event', 'unknown')), args.release_candidate, str(context.get('branch', 'unknown')))
    artifact_exists = artifact.is_file()
    protected_branch = None if args.protected_branch == "" else as_bool(args.protected_branch)
    direct_push_allowed = None if args.direct_push_allowed == "" else as_bool(args.direct_push_allowed)
    review_required = None if args.review_required == "" else as_bool(args.review_required)

    repository = {
        "repository_id": context.get("repository_id", "unknown"),
        "branch": context.get("branch", "unknown"),
        "branch_protection_lookup": {"status": args.branch_protection_status},
    }
    if protected_branch is not None:
        repository["protected_branch"] = protected_branch
    if direct_push_allowed is not None:
        repository["direct_push_allowed"] = direct_push_allowed
    if review_required is not None:
        repository["review_required"] = review_required

    evidence = {
        "contract_version": "1.0",
        "release_candidate": args.release_candidate,
        "run_context": {
            "event": context.get("event", "unknown"),
            "purpose": purpose,
            "release_context": release_context,
            "source": context.get("source", selector),
        },
        "pipeline": {
            "pipeline_id": context.get("pipeline_id", selector),
            "pipeline_run_id": str(context.get("pipeline_run_id", "unknown")),
            "pipeline_url": context.get("pipeline_url", ""),
            "commit_id": context.get("commit_id", "unknown"),
            "event": context.get("event", "unknown"),
            "governance_mode": args.governance_mode,
            "status": "success",
            "security_gates": {
                "enforced": True,
                "blocks_merge": args.governance_mode in {"block-on-error", "waiver-required"},
            },
            "security_thresholds_exceeded": SEVERITY_ORDER.get(max_seen, 99) > SEVERITY_ORDER.get(max_allowed, 99),
            "external_direct_downloads_detected": observations['external_direct_downloads_detected'],
        },
        "repository": repository,
        "artifact": {
            "artifact_id": artifact.name,
            "artifact_type": args.artifact_type,
            "artifact_version": str(context.get("commit_id", "unknown"))[:12],
            "digest": {
                "exists": artifact_exists,
                "linked_to_artifact": artifact_exists,
                "algorithm": "sha256",
                "path": str(artifact),
                "value": artifact.sha256 if artifact_exists else "",
            },
            "signature": {
                "exists": bool(signature and signature.is_file()),
                "path": str(signature) if signature else "",
            },
        },
        "evidence": {
            "sbom": {
                "exists": sbom.is_file(),
                "linked_to_artifact": sbom.is_file() and artifact_exists,
                "path": str(sbom),
            },
            "vulnerability_scan": {
                "exists": vulnerability_scan.is_file(),
                "path": str(vulnerability_scan),
                "max_severity": max_seen,
            },
            "pipeline_execution": {
                "evidence_id": f"{selector}-{context.get('pipeline_run_id', 'unknown')}",
                "pipeline_run_id": str(context.get("pipeline_run_id", "unknown")),
                "status": "success",
                "generated_at": at,
            },
        },
        "release": {
            "release_id": f"{context.get('repository_id', 'unknown')}@{str(context.get('commit_id', 'unknown'))[:12]}",
            "approval_status": "not_required",
            "approved_waiver": {"exists": observations['approved_waiver_exists']},
        },
        "waivers": [],
    }

    errors = []
    if not artifact_exists:
        errors.append(f"artifact not found: {artifact}")
    if not sbom.is_file():
        errors.append(f"SBOM not found: {sbom}")
    if not vulnerability_scan.is_file():
        errors.append(f"vulnerability scan not found: {vulnerability_scan}")
    if evidence["pipeline"]["security_thresholds_exceeded"]:
        errors.append(f"vulnerability severity threshold exceeded: max_seen={max_seen}, allowed={max_allowed}")
    if direct_push_allowed is True:
        errors.append("direct pushes are allowed on the target branch")

    gate = {
        "status": "fail" if errors else "pass",
        "governance_mode": args.governance_mode,
        "blocks_merge": args.governance_mode in {"block-on-error", "waiver-required"},
        "errors": errors,
    }

    return evidence, gate
