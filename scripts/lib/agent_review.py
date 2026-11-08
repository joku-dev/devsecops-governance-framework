"""Prepare revision-bound role reviews and check declared completion evidence.

This module never invokes a model, executes validation commands or grants approval.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import jsonschema
from .agent_routing import ROLE_CONTRACTS, load_yaml, normalize_path, routing_reasons


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "Git read failed")
    return result.stdout


def changed_files(root: Path, base_ref: str | None = None) -> list[str]:
    """Include committed branch changes, staged/unstaged edits and untracked files.

    --no-renames keeps both old and new paths for ownership routing. NUL separators
    preserve spaces, Unicode and newlines in repository filenames.
    """
    paths = set()
    if base_ref:
        base = merge_base(root, base_ref)
        paths.update(git_output(root, "diff", "--name-only", "--no-renames", "-z", base, "HEAD").split("\0"))
    # Keep both sets: a staged edit can be undone in the worktree while remaining
    # in the next commit. Comparing only HEAD to the worktree would miss it.
    for args in (("--cached",), ()):
        paths.update(git_output(root, "diff", "--name-only", "--no-renames", "-z", *args).split("\0"))
    paths.update(git_output(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0"))
    return sorted(normalize_path(path) for path in paths if path)


def merge_base(root: Path, base_ref: str) -> str:
    revision = git_output(root, "rev-parse", "--verify", "--end-of-options", f"{base_ref}^{{commit}}").strip()
    return git_output(root, "merge-base", revision, "HEAD").strip()


def fingerprint(root: Path, name: str) -> str | None:
    path = root / normalize_path(name)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Review input escapes repository through a symlink: {name}")
    if path.is_symlink():
        raise ValueError(f"Review input must be a regular file, not a symlink: {name}")
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError(f"Review input must be a file: {name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def prepare_plan(root: Path, dispatch: dict, goal: str, *, base_ref: str | None = None,
                 explicit_paths: bool = False) -> dict:
    if not goal.strip() or not dispatch["changed_files"]:
        raise ValueError("A review plan requires a goal and at least one changed file")
    protocol_path = ".agents/review-protocol.yaml"
    protocol = load_yaml(root / protocol_path)
    final_role = protocol["execution"]["final_role"]
    if final_role != "repo-steward" or protocol["execution"]["default_access"] != "read_only":
        raise ValueError("Review protocol requires read-only tasks and final repo-steward synthesis")
    selected = dispatch["selected_agents"]
    if final_role not in selected:
        raise ValueError("Review plan requires the final repo-steward role")
    reasons = routing_reasons(dispatch["changed_files"])
    tasks = []
    contracts = {protocol_path, ".agents/routing/governance-agent-routing.yaml",
                 "AGENTS.md", "docs/governance/governance-roles-and-agent-profiles.md",
                 "scripts/lib/agent_review.py", "scripts/lib/agent_routing.py",
                 "scripts/dispatch_governance_agents.py"}
    for role_id in sorted(set(selected) - {final_role}) + [final_role]:
        role = ROLE_CONTRACTS[role_id]
        role_path = f".agents/roles/{role_id}.yaml"
        skill_path = f".agents/skills/{role['skill']}/SKILL.md"
        contracts.update((role_path, skill_path))
        tasks.append({
            "role_id": role_id, "phase": "final_review" if role_id == final_role else "specialist_review",
            "role_contract": role_path, "skill": skill_path,
            "selection_reasons": reasons[role_id],
            "scope": [path for path in dispatch["changed_files"]
                      if role_id in routing_reasons([path])],
            "access": protocol["execution"]["default_access"],
            "required_output": role["output_contract"],
            "validations": role["validations"],
        })
    head = git_output(root, "rev-parse", "HEAD").strip()
    plan = {
        "schema_version": "1.0.0", "user_goal": goal.strip(), "head_commit": head,
        "base_commit": merge_base(root, base_ref) if base_ref else None,
        "selection_mode": "explicit_paths" if explicit_paths else "working_tree",
        "execution_status": "not_started", "default_mode": protocol["execution"]["default_mode"],
        "changed_files": dispatch["changed_files"], "release_impact": dispatch["release_impact"],
        "source_fingerprints": {name: fingerprint(root, name) for name in dispatch["changed_files"]},
        "index_entries": {name: git_output(root, "--literal-pathspecs", "ls-files", "--stage", "-z", "--", name).split("\0")[:-1]
                          for name in dispatch["changed_files"]},
        "source_modes": {name: (root / name).stat().st_mode & 0o777 if (root / name).exists() else None
                         for name in dispatch["changed_files"]},
        "contract_fingerprints": {name: fingerprint(root, name) for name in sorted(contracts)},
        "required_validations": dispatch["required_validations"], "reviews": tasks,
        "authority": protocol["authority"],
    }
    plan["plan_digest"] = digest(plan)
    return plan


def results_template(plan: dict) -> dict:
    return {
        "plan_digest": plan["plan_digest"],
        "reviews": [{"role_id": task["role_id"], "status": "pending", "execution_kind": "role_lens",
                     "executor": "", "provider": "", "model": None, "summary": "",
                     "outputs": {key: "" for key in task["required_output"]},
                     "reviewed_paths": [], "reviewed_roles": [], "findings": []} for task in plan["reviews"]],
        "validations": [{"command": cmd, "status": "not_run", "evidence": ""}
                        for cmd in plan["required_validations"]],
    }


RESULT_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["plan_digest", "reviews", "validations"],
    "properties": {
        "plan_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "reviews": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["role_id", "status", "execution_kind", "executor", "provider", "model", "summary", "outputs", "reviewed_paths", "reviewed_roles", "findings"],
            "properties": {
                "role_id": {"type": "string"},
                "status": {"enum": ["pending", "completed", "failed", "skipped"]},
                "execution_kind": {"enum": ["role_lens", "subagent", "human"]},
                "executor": {"type": "string"}, "provider": {"type": "string"},
                "model": {"type": ["string", "null"]}, "summary": {"type": "string"},
                "outputs": {"type": "object", "additionalProperties": {"type": "string"}},
                "reviewed_paths": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
                "reviewed_roles": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
                "findings": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["severity", "path", "issue", "status"],
                    "properties": {"severity": {"enum": ["low", "medium", "high", "critical"]},
                                   "path": {"type": "string", "minLength": 1},
                                   "issue": {"type": "string", "minLength": 1},
                                   "status": {"enum": ["open", "resolved"]}},
                }},
            },
        }},
        "validations": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["command", "status", "evidence"],
            "properties": {"command": {"type": "string"}, "status": {"enum": ["passed", "failed", "not_run"]},
                           "evidence": {"type": "string"}},
        }},
    },
}


def check_results(root: Path, plan: dict, results: dict) -> dict:
    """Check binding and completeness; all execution/validation claims are declarations."""
    if not isinstance(plan, dict):
        raise ValueError("Review plan must be a JSON object")
    jsonschema.Draft202012Validator(RESULT_SCHEMA).validate(results)
    unsigned = {key: value for key, value in plan.items() if key != "plan_digest"}
    if digest(unsigned) != plan.get("plan_digest") or results["plan_digest"] != plan["plan_digest"]:
        raise ValueError("Review plan/result digest mismatch")
    # Reconstruct plan from the current neutral contracts rather than trusting its roles/commands.
    from .agent_routing import evaluate_scenario
    expected = prepare_plan(root, {"changed_files": plan["changed_files"], **evaluate_scenario({"changed_files": plan["changed_files"]})},
                            plan["user_goal"], base_ref=plan["base_commit"], explicit_paths=plan["selection_mode"] == "explicit_paths")
    if expected != plan:
        raise ValueError("Review plan is stale: revision, source bytes or role contracts changed")
    if plan["selection_mode"] == "working_tree" and changed_files(root, plan["base_commit"]) != plan["changed_files"]:
        raise ValueError("Review scope is stale: changed paths have been added or removed")
    role_ids = [task["role_id"] for task in plan["reviews"]]
    if [review["role_id"] for review in results["reviews"]] != role_ids:
        raise ValueError("Every selected role must appear exactly once, with repo-steward last")
    if sorted(v["command"] for v in results["validations"]) != plan["required_validations"]:
        raise ValueError("Every required validation must appear exactly once")
    incomplete = []
    findings = []
    for task, review in zip(plan["reviews"], results["reviews"]):
        if review["status"] != "completed" or any(not review[k].strip() for k in ("executor", "provider", "summary")):
            incomplete.append(f"Incomplete role review: {review['role_id']}")
        if set(review["outputs"]) != set(task["required_output"]) or any(not value.strip() for value in review["outputs"].values()):
            incomplete.append(f"Missing required role outputs: {review['role_id']}")
        if sorted(review["reviewed_paths"]) != sorted(task["scope"]):
            incomplete.append(f"Unreviewed role scope: {review['role_id']}")
        findings.extend({"role_id": review["role_id"], **finding} for finding in review["findings"])
    if set(results["reviews"][-1]["reviewed_roles"]) != set(role_ids[:-1]):
        incomplete.append("Final repo-steward must explicitly account for all specialist reviews")
    for validation in results["validations"]:
        if validation["status"] != "passed" or not validation["evidence"].strip():
            incomplete.append(f"Missing declared passing validation with evidence: {validation['command']}")
    if any(f["status"] == "open" and f["severity"] in ("high", "critical") for f in findings):
        incomplete.append("Open high/critical findings require resolution")
    return {"eligible_for_human_review": not incomplete, "scope": plan["selection_mode"],
            "evidence_kind": "self_reported_review_evidence", "independent_human_approval": False,
            "incomplete": incomplete, "findings": findings}
