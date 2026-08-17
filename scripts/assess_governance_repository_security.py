#!/usr/bin/env python3
"""Collect and assess the security posture of the governance repository."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "model" / "controls" / "governance-repository-security.yaml"
DEFAULT_JSON = ROOT / "generated" / "reports" / "governance-repository-security.json"
DEFAULT_MD = ROOT / "generated" / "reports" / "governance-repository-security.md"
FULL_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
USES_REF = re.compile(r"^\s*uses:\s*([^\s#]+)@([^\s#]+)", re.MULTILINE)
CRITICAL_CODEOWNER_PATHS = (
    "/.github/workflows/",
    "/model/controls/",
    "/model/evidence/",
    "/policies/opa/",
    "/schemas/",
    "/scripts/",
    "/releases/",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)


def gh_api(path: str) -> tuple[object | None, str | None]:
    result = run(["gh", "api", path])
    if result.returncode != 0:
        return None, result.stderr.strip() or result.stdout.strip() or "GitHub API request failed"
    try:
        return json.loads(result.stdout), None
    except json.JSONDecodeError as error:
        return None, f"GitHub API returned invalid JSON: {error}"


def workflow_files() -> list[Path]:
    return sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))


def scan_workflows() -> dict:
    unpinned = []
    write_workflows = []
    explicit_permissions = []
    for path in workflow_files():
        relative = str(path.relative_to(ROOT))
        content = path.read_text(encoding="utf-8")
        if re.search(r"(?m)^permissions:\s*$", content):
            explicit_permissions.append(relative)
        if re.search(r"(?m)^\s*contents:\s*write\s*$", content) and "git push" in content:
            write_workflows.append(relative)
        for action, ref in USES_REF.findall(content):
            if action.startswith("./") or action.startswith("joku-dev/"):
                continue
            if not FULL_SHA.fullmatch(ref):
                unpinned.append({"workflow": relative, "action": action, "ref": ref})
    return {
        "workflow_count": len(workflow_files()),
        "explicit_permissions_count": len(explicit_permissions),
        "third_party_unpinned_refs": unpinned,
        "direct_main_write_workflows": write_workflows,
    }


def scan_codeowners() -> dict:
    path = ROOT / ".github" / "CODEOWNERS"
    if not path.exists():
        return {"present": False, "missing_critical_paths": list(CRITICAL_CODEOWNER_PATHS)}
    content = path.read_text(encoding="utf-8")
    missing = [item for item in CRITICAL_CODEOWNER_PATHS if item not in content]
    return {"present": True, "missing_critical_paths": missing}


def tag_verification() -> dict:
    tags = run(["git", "tag", "--list", "*baseline*"]).stdout.splitlines()
    tags.extend(run(["git", "tag", "--list", "v*-public-adoption"]).stdout.splitlines())
    tags = sorted(set(tag for tag in tags if tag))
    unverified = []
    for tag in tags:
        if run(["git", "verify-tag", tag]).returncode != 0:
            unverified.append(tag)
    return {"release_tags": tags, "unverified_release_tags": unverified}


def active_rulesets(repository: str) -> tuple[list[dict], list[str]]:
    summaries, error = gh_api(f"repos/{repository}/rulesets")
    if error or not isinstance(summaries, list):
        return [], [error or "Ruleset response was not a list"]
    rulesets = []
    errors = []
    for summary in summaries:
        if summary.get("enforcement") != "active":
            continue
        detail, detail_error = gh_api(f"repos/{repository}/rulesets/{summary['id']}")
        if detail_error or not isinstance(detail, dict):
            errors.append(detail_error or f"Ruleset {summary['id']} response was not an object")
            continue
        rulesets.append(detail)
    return rulesets, errors


def ruleset_rule(rulesets: list[dict], rule_type: str) -> list[dict]:
    return [rule for ruleset in rulesets for rule in ruleset.get("rules", []) if rule.get("type") == rule_type]


def collect_live(repository: str, observed_at: str) -> dict:
    metadata, metadata_error = gh_api(f"repos/{repository}")
    protection, protection_error = gh_api(f"repos/{repository}/branches/main/protection")
    signature_requirement, signature_error = gh_api(
        f"repos/{repository}/branches/main/protection/required_signatures"
    )
    actions_permissions, actions_error = gh_api(f"repos/{repository}/actions/permissions")
    workflow_permissions, workflow_error = gh_api(f"repos/{repository}/actions/permissions/workflow")
    private_reporting, private_reporting_error = gh_api(
        f"repos/{repository}/private-vulnerability-reporting"
    )
    rulesets, ruleset_errors = active_rulesets(repository)

    metadata = metadata if isinstance(metadata, dict) else {}
    protection = protection if isinstance(protection, dict) else {}
    actions_permissions = actions_permissions if isinstance(actions_permissions, dict) else {}
    workflow_permissions = workflow_permissions if isinstance(workflow_permissions, dict) else {}
    private_reporting = private_reporting if isinstance(private_reporting, dict) else {}
    security = metadata.get("security_and_analysis") or {}
    pull_request_rules = ruleset_rule(rulesets, "pull_request")
    status_rules = ruleset_rule(rulesets, "required_status_checks")
    signed_rules = ruleset_rule(rulesets, "required_signatures")

    review_count = (protection.get("required_pull_request_reviews") or {}).get(
        "required_approving_review_count", 0
    )
    review_count = max(
        [review_count]
        + [rule.get("parameters", {}).get("required_approving_review_count", 0) for rule in pull_request_rules]
    )
    required_checks = []
    for check in (protection.get("required_status_checks") or {}).get("checks", []):
        required_checks.append(check.get("context"))
    for rule in status_rules:
        required_checks.extend(
            check.get("context") for check in rule.get("parameters", {}).get("required_status_checks", [])
        )
    required_checks = sorted(set(item for item in required_checks if item))

    branch_protected = bool(protection or rulesets)
    protection_blocks_force_push = bool(protection) and not (
        protection.get("allow_force_pushes") or {}
    ).get("enabled", False)
    ruleset_blocks_force_push = bool(ruleset_rule(rulesets, "non_fast_forward"))
    force_push_blocked = protection_blocks_force_push or ruleset_blocks_force_push
    protection_blocks_deletion = bool(protection) and not (
        protection.get("allow_deletions") or {}
    ).get("enabled", False)
    ruleset_blocks_deletion = bool(ruleset_rule(rulesets, "deletion"))
    deletion_blocked = protection_blocks_deletion or ruleset_blocks_deletion

    signed_changes_required = bool(
        isinstance(signature_requirement, dict) and signature_requirement.get("enabled")
    ) or bool(signed_rules)
    workflow_scan = scan_workflows()
    codeowners = scan_codeowners()
    tags = tag_verification()

    return {
        "repository_id": repository,
        "observed_at": observed_at,
        "api_errors": [
            item
            for item in [
                metadata_error,
                protection_error,
                signature_error,
                actions_error,
                workflow_error,
                private_reporting_error,
                *ruleset_errors,
            ]
            if item
        ],
        "repository": {
            "visibility": metadata.get("visibility"),
            "default_branch": metadata.get("default_branch"),
            "branch_protected": branch_protected,
            "required_approving_reviews": review_count,
            "required_status_checks": required_checks,
            "force_push_blocked": force_push_blocked,
            "deletion_blocked": deletion_blocked,
            "signed_changes_required": signed_changes_required,
        },
        "security_features": {
            "secret_scanning": (security.get("secret_scanning") or {}).get("status"),
            "secret_scanning_push_protection": (
                security.get("secret_scanning_push_protection") or {}
            ).get("status"),
            "dependabot_security_updates": (
                security.get("dependabot_security_updates") or {}
            ).get("status"),
            "dependabot_config_present": (ROOT / ".github" / "dependabot.yml").exists(),
            "codeql_workflow_present": any("codeql" in path.name.lower() for path in workflow_files()),
            "private_vulnerability_reporting": private_reporting.get("enabled"),
        },
        "actions": {
            "allowed_actions": actions_permissions.get("allowed_actions"),
            "sha_pinning_required": actions_permissions.get("sha_pinning_required"),
            "default_workflow_permissions": workflow_permissions.get("default_workflow_permissions"),
            "can_approve_pull_request_reviews": workflow_permissions.get("can_approve_pull_request_reviews"),
            **workflow_scan,
        },
        "ownership": codeowners,
        "release_integrity": tags,
    }


def evidence_refs(key: str) -> list[str]:
    mapping = {
        "default_branch_protected": ["github:branches/main/protection", "github:rulesets"],
        "pull_request_review_required": ["github:branches/main/protection", "github:rulesets"],
        "governance_ci_required": ["github:branches/main/protection", ".github/workflows/governance-ci.yml"],
        "destructive_branch_changes_blocked": ["github:branches/main/protection", "github:rulesets"],
        "signed_changes_required": ["github:branches/main/protection/required_signatures", "github:rulesets"],
        "secret_scanning_enabled": ["github:repository/security_and_analysis"],
        "secret_push_protection_enabled": ["github:repository/security_and_analysis"],
        "dependency_security_enabled": ["github:repository/security_and_analysis", ".github/dependabot.yml"],
        "code_scanning_configured": [".github/workflows/codeql.yml"],
        "third_party_actions_sha_pinned": [".github/workflows/", "github:actions/permissions"],
        "workflow_permissions_restricted": ["github:actions/permissions/workflow", ".github/workflows/"],
        "critical_paths_owned": [".github/CODEOWNERS"],
        "automated_main_writes_absent": [".github/workflows/"],
        "release_tags_verified": ["git:release-tags", "releases/"],
        "private_vulnerability_reporting_enabled": [
            "github:private-vulnerability-reporting",
            "SECURITY.md",
        ],
        "approved_action_sources_restricted": ["github:actions/permissions"],
    }
    return mapping[key]


def observed_values(observation: dict) -> dict[str, object]:
    repository = observation.get("repository", {})
    security = observation.get("security_features", {})
    actions = observation.get("actions", {})
    ownership = observation.get("ownership", {})
    release = observation.get("release_integrity", {})
    return {
        "default_branch_protected": repository.get("branch_protected") is True,
        "pull_request_review_required": repository.get("required_approving_reviews", 0) >= 1,
        "governance_ci_required": "validate-and-report" in repository.get("required_status_checks", []),
        "destructive_branch_changes_blocked": repository.get("force_push_blocked") is True
        and repository.get("deletion_blocked") is True,
        "signed_changes_required": repository.get("signed_changes_required") is True,
        "secret_scanning_enabled": security.get("secret_scanning") == "enabled",
        "secret_push_protection_enabled": security.get("secret_scanning_push_protection") == "enabled",
        "dependency_security_enabled": security.get("dependabot_security_updates") == "enabled"
        and security.get("dependabot_config_present") is True,
        "code_scanning_configured": security.get("codeql_workflow_present") is True,
        "third_party_actions_sha_pinned": not actions.get("third_party_unpinned_refs")
        and actions.get("sha_pinning_required") is True,
        "workflow_permissions_restricted": actions.get("default_workflow_permissions") == "read"
        and actions.get("explicit_permissions_count") == actions.get("workflow_count"),
        "critical_paths_owned": ownership.get("present") is True
        and not ownership.get("missing_critical_paths"),
        "automated_main_writes_absent": not actions.get("direct_main_write_workflows"),
        "release_tags_verified": bool(release.get("release_tags"))
        and not release.get("unverified_release_tags"),
        "private_vulnerability_reporting_enabled": security.get("private_vulnerability_reporting")
        is True,
        "approved_action_sources_restricted": actions.get("allowed_actions") == "selected",
    }


def criterion_detail(key: str, observation: dict) -> str:
    repository = observation.get("repository", {})
    security = observation.get("security_features", {})
    actions = observation.get("actions", {})
    ownership = observation.get("ownership", {})
    release = observation.get("release_integrity", {})
    details = {
        "default_branch_protected": (
            f"branch_protected={str(repository.get('branch_protected')).lower()}"
        ),
        "pull_request_review_required": (
            f"required_approving_reviews={repository.get('required_approving_reviews', 0)}"
        ),
        "governance_ci_required": (
            "required_status_checks=" + json.dumps(repository.get("required_status_checks", []))
        ),
        "destructive_branch_changes_blocked": (
            f"force_push_blocked={str(repository.get('force_push_blocked')).lower()}, "
            f"deletion_blocked={str(repository.get('deletion_blocked')).lower()}"
        ),
        "signed_changes_required": (
            f"signed_changes_required={str(repository.get('signed_changes_required')).lower()}"
        ),
        "secret_scanning_enabled": f"secret_scanning={security.get('secret_scanning')}",
        "secret_push_protection_enabled": (
            f"secret_scanning_push_protection={security.get('secret_scanning_push_protection')}"
        ),
        "dependency_security_enabled": (
            f"dependabot_security_updates={security.get('dependabot_security_updates')}, "
            f"dependabot_config_present={str(security.get('dependabot_config_present')).lower()}"
        ),
        "code_scanning_configured": (
            f"codeql_workflow_present={str(security.get('codeql_workflow_present')).lower()}"
        ),
        "third_party_actions_sha_pinned": (
            f"unpinned_refs={len(actions.get('third_party_unpinned_refs', []))}, "
            f"sha_pinning_required={str(actions.get('sha_pinning_required')).lower()}"
        ),
        "workflow_permissions_restricted": (
            f"default={actions.get('default_workflow_permissions')}, explicit="
            f"{actions.get('explicit_permissions_count')}/{actions.get('workflow_count')}"
        ),
        "critical_paths_owned": (
            "missing_critical_paths=" + json.dumps(ownership.get("missing_critical_paths", []))
        ),
        "automated_main_writes_absent": (
            "direct_main_write_workflows="
            + json.dumps(actions.get("direct_main_write_workflows", []))
        ),
        "release_tags_verified": (
            "unverified_release_tags=" + json.dumps(release.get("unverified_release_tags", []))
        ),
        "private_vulnerability_reporting_enabled": (
            "private_vulnerability_reporting="
            + str(security.get("private_vulnerability_reporting")).lower()
        ),
        "approved_action_sources_restricted": (
            f"allowed_actions={actions.get('allowed_actions')}"
        ),
    }
    return details[key]


def remediation_steps(failed_ids: set[str]) -> list[dict]:
    definitions = [
        {
            "priority": "P0",
            "title": "Migrate automated writes away from direct main pushes",
            "addresses": ["GRS-013"],
            "prerequisites": [],
            "action": (
                "Replace intake and portfolio git pushes with reviewed bot pull requests or a "
                "separately protected operational evidence store. Keep normative governance outside "
                "the automation write authority."
            ),
            "acceptance_criteria": (
                "No active workflow combines contents: write with git push to the default branch."
            ),
        },
        {
            "priority": "P0",
            "title": "Enforce immutable GitHub Action references",
            "addresses": ["GRS-010", "GRS-016"],
            "prerequisites": [],
            "action": (
                "Verify all active workflow references remain pinned to reviewed full commit SHAs, "
                "restrict Actions to approved publishers, then enable repository-level SHA pinning."
            ),
            "acceptance_criteria": (
                "The workflow scan has no mutable third-party references, allowed_actions is selected, "
                "and GitHub reports sha_pinning_required as true."
            ),
        },
        {
            "priority": "P1",
            "title": "Protect the default branch as the governance authority",
            "addresses": ["GRS-001", "GRS-002", "GRS-003", "GRS-004"],
            "prerequisites": ["GRS-013"],
            "action": (
                "Activate a main ruleset requiring pull requests, at least one approving review, "
                "Governance CI, resolved conversations, and protection from deletion and force push."
            ),
            "acceptance_criteria": (
                "A non-bypass test pull request cannot merge without approval and required checks, "
                "and direct force push or branch deletion is rejected."
            ),
        },
        {
            "priority": "P2",
            "title": "Require signed changes on main",
            "addresses": ["GRS-005"],
            "prerequisites": ["GRS-013"],
            "action": (
                "Register accountable human and automation signing identities, validate recovery, "
                "and add the signed-commit rule to the protected default branch."
            ),
            "acceptance_criteria": (
                "Unsigned commits are rejected from main and authorized signed changes remain operable."
            ),
        },
        {
            "priority": "P2",
            "title": "Introduce verified release publication",
            "addresses": ["GRS-014"],
            "prerequisites": ["GRS-005"],
            "action": (
                "Publish future baseline tags through an accountable signed release process with "
                "verification evidence; do not rewrite historical released tags in place."
            ),
            "acceptance_criteria": (
                "New governance baseline tags verify cryptographically and their release packages "
                "retain valid checksums and provenance."
            ),
        },
    ]
    return [step for step in definitions if failed_ids.intersection(step["addresses"])]


def assess(model: dict, observation: dict) -> dict:
    values = observed_values(observation)
    criteria = []
    for definition in model["criteria"]:
        observed = values[definition["key"]]
        criteria.append(
            {
                **definition,
                "status": "pass" if observed is True else "fail",
                "observed": observed,
                "detail": criterion_detail(definition["key"], observation),
                "evidence_refs": evidence_refs(definition["key"]),
            }
        )
    failures = [item for item in criteria if item["status"] == "fail"]
    failed_ids = {item["id"] for item in failures}
    risk_statement = (
        "The repository has active scanning, dependency, permission, ownership, and private-reporting "
        "controls, but it is not yet a protected governance authority because main remains unprotected, "
        "automation can write directly to main, and release authenticity is not enforced."
        if failures
        else "All defined self-security criteria are currently evidenced as satisfied."
    )
    return {
        "schema_version": "0.2.0",
        "assessment_type": "governance-repository-self-security",
        "profile_id": model["profile_id"],
        "profile_version": model["version"],
        "repository_id": model["repository_id"],
        "observed_at": observation["observed_at"],
        "enforcement": "report_only",
        "enforcement_change_authorized": False,
        "overall_status": "findings" if failures else "pass",
        "summary": {
            "criteria": len(criteria),
            "pass": len(criteria) - len(failures),
            "fail": len(failures),
            "critical_failures": sum(item["severity"] == "critical" for item in failures),
            "high_failures": sum(item["severity"] == "high" for item in failures),
        },
        "risk_statement": risk_statement,
        "criteria": criteria,
        "next_steps": remediation_steps(failed_ids),
        "observation": observation,
        "decision_boundary": {
            "blocks_pull_requests": False,
            "changes_repository_settings": False,
            "changes_released_baselines": False,
        },
    }


def render_markdown(report: dict) -> str:
    summary = report["summary"]
    failures = [item for item in report["criteria"] if item["status"] == "fail"]
    passes = [item for item in report["criteria"] if item["status"] == "pass"]
    lines = [
        "# Governance Repository Self-Security Assessment",
        "",
        f"Observed: `{report['observed_at']}`",
        "",
        "## Executive Assessment",
        "",
        report["risk_statement"],
        "",
        "This is a point-in-time, report-only assessment of the repository that defines and",
        "distributes governance. It is not a security certification or an authorization to",
        "switch consumer or repository enforcement to blocking mode.",
        "",
        "## Decision State",
        "",
        f"- Overall status: `{report['overall_status']}`",
        "- Enforcement: `report_only`",
        "- Enforcement change authorized: `false`",
        f"- Criteria: `{summary['criteria']}`",
        f"- Passed: `{summary['pass']}`",
        f"- Failed: `{summary['fail']}`",
        f"- Critical failures: `{summary['critical_failures']}`",
        f"- High failures: `{summary['high_failures']}`",
        "",
        "## Controls Currently Evidenced",
        "",
    ]
    if passes:
        lines.extend(f"- `{item['id']}`: {item['title']}" for item in passes)
    else:
        lines.append("- None.")
    lines.extend(
        [
        "",
        "## Open Findings",
        "",
        "| ID | Severity | Finding | Current observation |",
        "|---|---|---|---|",
        ]
    )
    if failures:
        lines.extend(
            f"| `{item['id']}` | `{item['severity']}` | {item['title']} | "
            f"`{item['detail']}` |" for item in failures
        )
    else:
        lines.append("| - | - | No open findings. | - |")
    lines.extend(
        [
        "",
        "## Recommended Next Steps",
        "",
        ]
    )
    if report["next_steps"]:
        for index, step in enumerate(report["next_steps"], start=1):
            addresses = ", ".join(f"`{item}`" for item in step["addresses"])
            prerequisites = (
                ", ".join(f"`{item}`" for item in step["prerequisites"])
                if step["prerequisites"]
                else "none"
            )
            lines.extend(
                [
                    f"### {index}. {step['title']} (`{step['priority']}`)",
                    "",
                    f"- Addresses: {addresses}",
                    f"- Prerequisites: {prerequisites}",
                    f"- Action: {step['action']}",
                    f"- Acceptance criteria: {step['acceptance_criteria']}",
                    "",
                ]
            )
    else:
        lines.extend(["- No remediation steps are currently required.", ""])
    lines.extend(
        [
        "## Complete Criteria",
        "",
        "| ID | Severity | Status | Criterion | Observed |",
        "|---|---|---|---|---|",
        ]
    )
    for item in report["criteria"]:
        lines.append(
            f"| `{item['id']}` | `{item['severity']}` | `{item['status']}` | "
            f"{item['title']} | `{str(item['observed']).lower()}` |"
        )
    lines.extend(
        [
            "",
            "## Evidence Quality And Limitations",
            "",
            "- GitHub repository settings are collected live through the authenticated GitHub API.",
            "- Workflow pinning, CODEOWNERS, direct writes, and release tags are inspected from the checkout.",
            "- GitHub `404` responses for branch protection or required signatures corroborate a missing",
            "  root control in this assessment; they are retained in the JSON observation for auditability.",
            "- A passing workflow configuration criterion confirms configuration presence, not absence of",
            "  every implementation vulnerability.",
            "",
            "## Release And Consumer Impact",
            "",
            "- Released DevSecOps and architecture baseline packages are unchanged.",
            "- Consumer evidence contracts and enforcement modes are unchanged.",
            "- Report schema `0.2.0` additively introduces a structured remediation plan.",
            "- No baseline release is required for this reporting improvement.",
            "",
            "## Decision Boundary",
            "",
            "This assessment is report-only. It does not edit GitHub settings, block pull requests,",
            "change released baselines, or authorize automated bypass. Missing evidence is reported",
            "as a failed criterion.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", "joku-dev/devsecops-governance-framework"))
    parser.add_argument("--observation", type=Path)
    parser.add_argument("--observed-at")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args()

    model = yaml.safe_load(args.model.read_text(encoding="utf-8"))
    if args.observation:
        observation = json.loads(args.observation.read_text(encoding="utf-8"))
    else:
        observation = collect_live(args.repository, args.observed_at or utc_now())
    report = assess(model, observation)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(
        f"Governance repository self-security: {report['overall_status']} "
        f"({report['summary']['pass']} pass, {report['summary']['fail']} fail)"
    )
    return 1 if args.fail_on_findings and report["overall_status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
