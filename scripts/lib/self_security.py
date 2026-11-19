"""Pure report-only security decisions over explicit captured observations.

The legacy governance profile keeps its evidence labels and diagnostic wording;
collection, source inspection, clocks and export effects belong to adapters.
A report is neither a certification nor an enforcement/operating authorization.
"""
import json


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
        "release_tags_verified": [
            "git:release-tags",
            "model/governance/release-signing-policy.yaml",
            "releases/release-tag-integrity.json",
            "releases/release-tag-integrity.json.sig",
        ],
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
        "pull_request_review_required": repository.get("required_approving_reviews", 0) >= 2
        and repository.get("code_owner_review_required") is True
        and repository.get("last_push_approval_required") is True,
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
            f"required_approving_reviews={repository.get('required_approving_reviews', 0)}, "
            f"code_owner_review_required="
            f"{str(repository.get('code_owner_review_required')).lower()}, "
            f"last_push_approval_required="
            f"{str(repository.get('last_push_approval_required')).lower()}"
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
            "direct_verified="
            + json.dumps(release.get("direct_verified_release_tags", []))
            + ", legacy_manifest_verified="
            + json.dumps(release.get("legacy_manifest_verified_tags", []))
            + ", unverified="
            + json.dumps(release.get("unverified_release_tags", []))
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


def remediation_steps(failures: list[dict]) -> list[dict]:
    failed_ids = {item["id"] for item in failures}
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
                "Activate a main ruleset requiring pull requests, two independent approving reviews, "
                "CODEOWNER and last-push approval, Governance CI, resolved conversations, and "
                "protection from deletion and force push."
            ),
            "acceptance_criteria": (
                "A non-bypass test pull request cannot merge without two independent approvals, "
                "CODEOWNER and last-push approval, and required checks; direct force push or branch "
                "deletion is rejected."
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
    steps = [step for step in definitions if failed_ids.intersection(step["addresses"])]
    addressed = {criterion for step in steps for criterion in step["addresses"]}
    for item in failures:
        if item["id"] not in addressed:
            steps.append({
                "priority": "P1" if item["severity"] in {"critical", "high"} else "P2",
                "title": f"Restore criterion: {item['title']}",
                "addresses": [item["id"]],
                "prerequisites": [],
                "action": (
                    f"Review {', '.join(item['evidence_refs'])}, remediate the observed gap "
                    f"({item['detail']}), and collect a fresh assessment."
                ),
                "acceptance_criteria": (
                    f"A fresh observation satisfies {item['id']} ({item['title']}) "
                    "and the criterion reports pass."
                ),
            })
    return sorted(steps, key=lambda step: step["priority"])


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
    risk_statement = (
        f"{len(failures)} of {len(criteria)} self-security criteria are not evidenced as satisfied: "
        + "; ".join(f"{item['id']} ({item['title']})" for item in failures)
        + ". Review the observations and remediation steps below."
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
        "next_steps": remediation_steps(failures),
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
            "- Current release tags require a direct trusted signature. The explicitly bounded historical",
            "  tag set is verified against a signed retrospective integrity manifest; this does not claim",
            "  that those historical tags carried an original publication-time signature.",
            "- API errors are retained in the JSON observation. A `404` on a legacy branch-protection",
            "  endpoint does not negate protection established by the effective branch rulesets;",
            "  unavailable administrative observations are not proof that a feature is disabled.",
            "- A passing workflow configuration criterion confirms configuration presence, not absence of",
            "  every implementation vulnerability.",
            "",
            "## Release And Consumer Impact",
            "",
            "- Released DevSecOps and architecture baseline packages are unchanged.",
            "- Consumer evidence contracts and enforcement modes are unchanged.",
            "- Self-Security profile `0.4.0` adds structured release-integrity verification;",
            "  report schema `0.2.0` remains compatible.",
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
