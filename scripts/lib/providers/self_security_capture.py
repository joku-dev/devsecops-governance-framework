"""Explicit read-only legacy security profile; captured inputs are inert data.

The original seven-response normalization and source scanners are retained here.
No source program, publisher or repository-setting command is selected.
"""
from copy import deepcopy
import json
from pathlib import Path
import re
FULL_SHA = re.compile(r"^[0-9a-fA-F]{40}$")

USES_REF = re.compile(r"^\s*uses:\s*([^\s#]+)@([^\s#]+)", re.MULTILINE)

CRITICAL_CODEOWNER_PATHS = (
    "/.github/workflows/",
    "/model/controls/",
    "/model/evidence/",
    "/model/governance/",
    "/policies/opa/",
    "/schemas/",
    "/scripts/",
    "/releases/",
)

REVIEWED_PUBLISHER_COMMANDS = (
    re.compile(
        r"scripts/publish_operational_update\.py\s+--scope\s+"
        r"(?:devsecops|architecture|lifecycle-pilot|portfolio)\b"
    ),
    re.compile(
        r"scripts/publish_typed_evidence_assurance_update\.py\s+--scope\s+typed-evidence\b"
    ),
    re.compile(r"scripts/publish_consumer_lifecycle\.py\b"),
    re.compile(r"scripts/publish_self_security_refresh\.py\b"),
)

def ruleset_rule(rulesets: list[dict], rule_type: str) -> list[dict]:
    return [rule for ruleset in rulesets for rule in ruleset.get("rules", []) if rule.get("type") == rule_type]

PROFILE='legacy-repository-self-security-v1'


def request_paths(repository):
    if (not isinstance(repository,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository)
            or any(part in ('.','..') for part in repository.split('/'))):
        raise ValueError('invalid_security_repository')
    prefix='repos/'+repository
    return [prefix+suffix for suffix in ('','/branches/main/protection',
        '/branches/main/protection/required_signatures','/actions/permissions',
        '/actions/permissions/workflow','/private-vulnerability-reporting','/rules/branches/main')]


class SecurityCollector:
    def __init__(self,root,api,release_report):
        self.root=Path(root);self.gh_api=api;self.release_report=deepcopy(release_report) if not callable(release_report) else release_report

    def tag_verification(self):return self.release_report() if callable(self.release_report) else deepcopy(self.release_report)
    def workflow_files(self) -> list[Path]:
        return sorted((self.root / ".github" / "workflows").glob("*.y*ml"))

    def scan_workflows(self) -> dict:
        unpinned = []
        write_workflows = []
        review_workflows = []
        explicit_permissions = []
        for path in self.workflow_files():
            relative = str(path.relative_to(self.root))
            content = path.read_text(encoding="utf-8")
            if re.search(r"(?m)^permissions:\s*$", content):
                explicit_permissions.append(relative)
            if re.search(r"(?m)^\s*contents:\s*write\s*$", content):
                reviewed_writer = any(pattern.search(content) for pattern in REVIEWED_PUBLISHER_COMMANDS)
                if reviewed_writer and "git push" not in content:
                    review_workflows.append(relative)
                else:
                    # An unknown write-capable workflow is not evidence of a safe route.
                    write_workflows.append(relative)
            for action, ref in USES_REF.findall(content):
                if action.startswith("./") or action.startswith("joku-dev/"):
                    continue
                if not FULL_SHA.fullmatch(ref):
                    unpinned.append({"workflow": relative, "action": action, "ref": ref})
        return {
            "workflow_count": len(self.workflow_files()),
            "explicit_permissions_count": len(explicit_permissions),
            "third_party_unpinned_refs": unpinned,
            "direct_main_write_workflows": write_workflows,
            "operational_review_workflows": review_workflows,
        }

    def scan_codeowners(self) -> dict:
        path = self.root / ".github" / "CODEOWNERS"
        if not path.exists():
            return {"present": False, "missing_critical_paths": list(CRITICAL_CODEOWNER_PATHS)}
        content = path.read_text(encoding="utf-8")
        missing = [item for item in CRITICAL_CODEOWNER_PATHS if item not in content]
        return {"present": True, "missing_critical_paths": missing}

    def active_rulesets(self, repository: str) -> tuple[list[dict], list[str]]:
        # GitHub resolves inclusion/exclusion and inherited rules for the actual branch.
        # Rules protecting a test or release branch must not make main appear protected.
        rules, error = self.gh_api(f"repos/{repository}/rules/branches/main")
        if error or not isinstance(rules, list):
            return [], [error or "Applicable branch rules response was not a list"]
        return ([{"rules": rules}] if rules else []), []

    def collect_live(self, repository: str, observed_at: str) -> dict:
        metadata, metadata_error = self.gh_api(f"repos/{repository}")
        protection, protection_error = self.gh_api(f"repos/{repository}/branches/main/protection")
        signature_requirement, signature_error = self.gh_api(
            f"repos/{repository}/branches/main/protection/required_signatures"
        )
        actions_permissions, actions_error = self.gh_api(f"repos/{repository}/actions/permissions")
        workflow_permissions, workflow_error = self.gh_api(f"repos/{repository}/actions/permissions/workflow")
        private_reporting, private_reporting_error = self.gh_api(
            f"repos/{repository}/private-vulnerability-reporting"
        )
        rulesets, ruleset_errors = self.active_rulesets(repository)

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
        code_owner_review_required = any(
            rule.get("parameters", {}).get("require_code_owner_review") is True
            for rule in pull_request_rules
        )
        last_push_approval_required = any(
            rule.get("parameters", {}).get("require_last_push_approval") is True
            for rule in pull_request_rules
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
        workflow_scan = self.scan_workflows()
        codeowners = self.scan_codeowners()
        tags = self.tag_verification()

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
                "code_owner_review_required": code_owner_review_required,
                "last_push_approval_required": last_push_approval_required,
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
                "dependabot_config_present": (self.root / ".github" / "dependabot.yml").exists(),
                "codeql_workflow_present": any("codeql" in path.name.lower() for path in self.workflow_files()),
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
