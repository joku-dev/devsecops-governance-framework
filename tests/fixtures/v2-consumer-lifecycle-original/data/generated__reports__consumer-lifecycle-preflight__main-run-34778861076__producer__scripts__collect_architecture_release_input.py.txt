#!/usr/bin/env python3
"""Collect a demo architecture release-readiness input from a target repo.

This collector is intentionally conservative. It does not claim compliance from
intent alone; it translates observable repository signals into marker scores and
evidence flags that the OPA release-readiness policy can evaluate.
"""

from argparse import ArgumentParser
from pathlib import Path
import json
import re
import subprocess


RELEASE_CRITICAL_MARKERS = ["E6", "E7", "E8", "S3", "S5", "S6", "S8", "P5", "P6", "P8", "P9", "P10", "P13"]

DETAILED_EVIDENCE_TO_COARSE = {
    "architecture_document": "solution_baseline",
    "context_view": "solution_baseline",
    "building_block_view": "solution_baseline",
    "architecture_decision_record": "solution_baseline",
    "architecture_ownership_record": "solution_baseline",
    "model_based_architecture": "solution_baseline",
    "sysml_model": "solution_baseline",
    "uml_model": "solution_baseline",
    "model_export": "solution_baseline",
    "model_baseline_record": "solution_baseline",
    "model_review_record": "review_evidence",
    "interface_catalogue": "solution_baseline",
    "interface_contract": "release_compatibility_declaration",
    "data_contract": "release_compatibility_declaration",
    "contract_test_result": "release_compatibility_declaration",
    "compatibility_matrix": "release_compatibility_declaration",
    "product_baseline": "solution_baseline",
    "baseline_delta_assessment": "release_compatibility_declaration",
    "migration_impact_assessment": "release_compatibility_declaration",
    "security_architecture_review": "security_evidence",
    "threat_model": "security_evidence",
    "trust_zone_model": "security_evidence",
    "identity_and_access_model": "security_evidence",
    "crypto_assumption_record": "security_evidence",
    "security_test_evidence": "security_evidence",
    "deployment_document": "deployment_evidence",
    "deployment_manifest": "deployment_evidence",
    "runtime_configuration_evidence": "deployment_evidence",
    "observability_evidence": "operation_evidence",
    "operations_runbook": "operation_evidence",
    "rollback_evidence": "deployment_evidence",
    "resilience_scenario": "resilience_evidence",
    "resilience_test_evidence": "resilience_evidence",
    "backup_restore_evidence": "resilience_evidence",
    "failure_mode_evidence": "resilience_evidence",
    "operational_recovery_record": "resilience_evidence",
    "architecture_review_record": "review_evidence",
    "approval_record": "review_evidence",
    "design_authority_decision": "review_evidence",
    "quality_gate_result": "review_evidence",
    "owner_assignment": "review_evidence",
    "architecture_exception": "exception_evidence",
    "risk_acceptance_record": "exception_evidence",
    "mitigation_plan": "exception_evidence",
    "expiry_review_record": "exception_evidence",
    "operational_finding": "feedback_evidence",
    "demo_or_review_finding": "feedback_evidence",
    "technical_debt_item": "feedback_evidence",
    "improvement_backlog_item": "feedback_evidence",
    "closed_improvement_action": "feedback_evidence",
}


def exists(repo: Path, relative: str) -> bool:
    return (repo / relative).exists()


def any_exists(repo: Path, patterns: list[str]) -> bool:
    return any(any(repo.glob(pattern)) for pattern in patterns)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def git_commit(repo: Path) -> str:
    result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip()


def score(present: bool, verified: bool = False, continuous: bool = False) -> int:
    if continuous:
        return 5
    if verified:
        return 4
    if present:
        return 3
    return 1


def evidence_ref(repo: Path, relative: str) -> str | None:
    if exists(repo, relative):
        return relative
    return None


def compact(items: list[str | None]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def load_app_evidence(repo: Path) -> dict[str, dict]:
    evidence_dir = repo / ".governance" / "architecture"
    evidence = {}
    if not evidence_dir.exists():
        return evidence

    for path in sorted(evidence_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        evidence_type = payload.get("evidence_type")
        if evidence_type:
            payload["_path"] = str(path.relative_to(repo))
            evidence[evidence_type] = payload
    return evidence


def evidence_approved(evidence: dict, evidence_type: str) -> bool:
    return evidence.get(evidence_type, {}).get("status") == "approved"


def evidence_present(evidence: dict, evidence_type: str) -> bool:
    return evidence_type in evidence


def evidence_refs(evidence: dict, evidence_type: str) -> list[str]:
    item = evidence.get(evidence_type, {})
    refs = [item.get("_path")]
    refs.extend(item.get("evidence_refs", []))
    return compact(refs)


def evidence_types_for_coarse(coarse_type: str) -> list[str]:
    detailed_types = [item for item, mapped in DETAILED_EVIDENCE_TO_COARSE.items() if mapped == coarse_type]
    return [coarse_type, *sorted(detailed_types)]


def evidence_any_present(evidence: dict, evidence_types: list[str]) -> bool:
    return any(evidence_present(evidence, evidence_type) for evidence_type in evidence_types)


def evidence_any_approved(evidence: dict, evidence_types: list[str]) -> bool:
    return any(evidence_approved(evidence, evidence_type) for evidence_type in evidence_types)


def evidence_refs_for_types(evidence: dict, evidence_types: list[str]) -> list[str]:
    refs: list[str] = []
    for evidence_type in evidence_types:
        refs.extend(evidence_refs(evidence, evidence_type))
    return list(dict.fromkeys(refs))


def summarize_detailed_evidence(evidence: dict) -> dict:
    by_type = {}
    by_coarse_type: dict[str, list[str]] = {}
    for evidence_type, item in sorted(evidence.items()):
        coarse_type = DETAILED_EVIDENCE_TO_COARSE.get(evidence_type, evidence_type)
        by_type[evidence_type] = {
            "coarse_type": coarse_type,
            "status": item.get("status", ""),
            "owner": item.get("owner", ""),
            "path": item.get("_path", ""),
            "evidence_refs": evidence_refs(evidence, evidence_type),
        }
        by_coarse_type.setdefault(coarse_type, []).append(evidence_type)

    return {
        "report_only": True,
        "declared_types": sorted(evidence),
        "by_type": by_type,
        "by_coarse_type": dict(sorted((key, sorted(value)) for key, value in by_coarse_type.items())),
    }


def collect(repo: Path, release_id: str, baseline: str) -> dict:
    app_evidence = load_app_evidence(repo)
    solution_evidence_types = evidence_types_for_coarse("solution_baseline")
    compatibility_evidence_types = evidence_types_for_coarse("release_compatibility_declaration")
    security_evidence_types = evidence_types_for_coarse("security_evidence")
    resilience_evidence_types = evidence_types_for_coarse("resilience_evidence")
    operation_evidence_types = evidence_types_for_coarse("operation_evidence")
    review_evidence_types = evidence_types_for_coarse("review_evidence")
    exception_evidence_types = evidence_types_for_coarse("exception_evidence")
    feedback_evidence_types = evidence_types_for_coarse("feedback_evidence")
    deployment_evidence_types = [
        "deployment_document",
        "deployment_manifest",
        "runtime_configuration_evidence",
        "rollback_evidence",
    ]

    architecture_doc = exists(repo, "docs/ARCHITECTURE.md")
    deployment_doc = exists(repo, "docs/DEPLOYMENT.md")
    compose_file = exists(repo, "docker-compose.yml")
    dockerfiles = sorted(str(path.relative_to(repo)) for path in repo.glob("**/Dockerfile"))
    requirements = sorted(str(path.relative_to(repo)) for path in repo.glob("**/requirements.txt"))
    tests = sorted(str(path.relative_to(repo)) for path in repo.glob("tests/**/*.py"))
    schemas = sorted(str(path.relative_to(repo)) for path in repo.glob("**/schemas/*.json"))
    benchmark_reports = sorted(str(path.relative_to(repo)) for path in repo.glob("benchmark/reports/*benchmark.json"))

    architecture_text = read_text(repo / "docs/ARCHITECTURE.md").lower()
    deployment_text = read_text(repo / "docs/DEPLOYMENT.md").lower()
    compose_text = read_text(repo / "docker-compose.yml").lower()

    has_interfaces = any(keyword in architecture_text for keyword in ["http", "rest", "websocket", "bolt", "api", "endpoint"])
    has_security_notes = any(keyword in deployment_text for keyword in ["secret", "token", "password", "api_key", "nie committen"])
    has_health_checks = "health-check" in deployment_text or "docker compose ps" in deployment_text
    has_rollback = "rollback" in deployment_text
    has_resilience = any(keyword in architecture_text + deployment_text for keyword in ["restart", "failure", "failover", "recovery", "degraded"])
    has_performance = bool(benchmark_reports)
    has_runtime_observability = any(keyword in deployment_text + compose_text for keyword in ["logs", "health", "metrics", "monitor", "dashboard"])
    has_feedback_evidence = evidence_any_present(app_evidence, feedback_evidence_types) or any_exists(repo, ["*incident*", "docs/*FEEDBACK*", "docs/*feedback*", "benchmark/reports/performance_evolution_summary.md"])
    has_release_baseline = evidence_any_present(app_evidence, solution_evidence_types) or any_exists(repo, ["*baseline*", "docs/*BASELINE*", "docs/*baseline*"])
    has_compatibility_declaration = evidence_present(app_evidence, "release_compatibility_declaration") or any_exists(repo, ["*compatibility*", "docs/*COMPATIBILITY*", "docs/*compatibility*"])
    has_compatibility_evidence = evidence_any_present(app_evidence, compatibility_evidence_types) or has_compatibility_declaration
    has_security_tests = any_exists(repo, ["*security*", "tests/**/*security*.py", ".github/workflows/*security*"])
    has_security_evidence = evidence_any_present(app_evidence, security_evidence_types) or has_security_notes
    has_resilience_evidence = evidence_any_present(app_evidence, resilience_evidence_types) or has_resilience
    has_operation_evidence = evidence_any_present(app_evidence, operation_evidence_types) or has_runtime_observability
    has_review_evidence = evidence_any_present(app_evidence, review_evidence_types)
    has_exception_evidence = evidence_any_present(app_evidence, exception_evidence_types)

    deployment_evidence_refs = compact(
        [
            *evidence_refs_for_types(app_evidence, deployment_evidence_types),
            evidence_ref(repo, "docs/DEPLOYMENT.md"),
            evidence_ref(repo, "docker-compose.yml"),
            *dockerfiles,
        ]
    )
    compatibility_refs = compact(
        [
            *evidence_refs(app_evidence, "release_compatibility_declaration"),
            *evidence_refs(app_evidence, "solution_baseline"),
            *evidence_refs_for_types(app_evidence, compatibility_evidence_types),
            evidence_ref(repo, "docs/ARCHITECTURE.md"),
            *schemas[:20],
        ]
    )
    security_refs = compact(
        [
            *evidence_refs_for_types(app_evidence, security_evidence_types),
            evidence_ref(repo, "docs/DEPLOYMENT.md") if has_security_evidence else None,
            *[path for path in tests if "security" in path.lower()],
        ]
    )
    resilience_refs = compact(
        [
            *evidence_refs_for_types(app_evidence, resilience_evidence_types),
            *deployment_evidence_refs,
        ]
    )
    runtime_refs = compact(
        [
            *evidence_refs_for_types(app_evidence, operation_evidence_types),
            evidence_ref(repo, "docs/DEPLOYMENT.md") if has_operation_evidence else None,
            evidence_ref(repo, "docker-compose.yml") if has_operation_evidence else None,
        ]
    )
    feedback_refs = compact(
        [
            *evidence_refs_for_types(app_evidence, feedback_evidence_types),
            evidence_ref(repo, "benchmark/reports/performance_evolution_summary.md") if has_feedback_evidence else None,
        ]
    )
    review_refs = compact(
        [
            *evidence_refs_for_types(app_evidence, review_evidence_types),
        ]
    )
    exception_refs = compact(
        [
            *evidence_refs_for_types(app_evidence, exception_evidence_types),
        ]
    )

    minimum_architecture_refs = compact(
        [
            evidence_ref(repo, "docs/ARCHITECTURE.md"),
            evidence_ref(repo, "README.md"),
            evidence_ref(repo, "docs/DEPLOYMENT.md"),
        ]
    )
    has_component_description = architecture_doc and all(component in architecture_text for component in ["neo4j", "ha-sync", "semantic-enrichment", "query-api"])
    has_process_description = deployment_doc and compose_file
    has_ownership_hint = any(keyword in architecture_text for keyword in ["verantwortung", "responsibility", "owner"])

    marker_assessments = [
        {"id": "B1", "score": score(architecture_doc), "evidence": minimum_architecture_refs},
        {"id": "B2", "score": score(architecture_doc and deployment_doc), "evidence": minimum_architecture_refs},
        {"id": "B3", "score": score(has_process_description), "evidence": minimum_architecture_refs},
        {"id": "B4", "score": score(has_ownership_hint), "evidence": minimum_architecture_refs},
        {"id": "B5", "score": score(has_feedback_evidence, evidence_any_approved(app_evidence, feedback_evidence_types)), "evidence": feedback_refs},
        {"id": "P0", "score": score(architecture_doc), "evidence": minimum_architecture_refs},
        {"id": "P1", "score": score(architecture_doc), "evidence": minimum_architecture_refs},
        {"id": "P2", "score": score(architecture_doc), "evidence": minimum_architecture_refs},
        {"id": "P3", "score": score(has_component_description), "evidence": minimum_architecture_refs},
        {"id": "P7", "score": score("designentscheidungen" in architecture_text or "decision" in architecture_text), "evidence": minimum_architecture_refs},
        {"id": "S0", "score": score(architecture_doc), "evidence": minimum_architecture_refs},
        {"id": "S1", "score": score(architecture_doc and has_component_description), "evidence": minimum_architecture_refs},
        {"id": "S2", "score": score(has_component_description), "evidence": minimum_architecture_refs},
        {"id": "E3", "score": score(has_interfaces, bool(schemas)), "evidence": compatibility_refs},
        {"id": "E5", "score": score(bool(schemas), bool(schemas)), "evidence": compatibility_refs},
        {"id": "S4", "score": score(bool(schemas), bool(schemas)), "evidence": compatibility_refs},
        {"id": "S7", "score": score(bool(tests), bool(tests)), "evidence": tests[:20]},
        {"id": "P4", "score": score(architecture_doc), "evidence": minimum_architecture_refs},
        {"id": "E6", "score": score(has_security_evidence, has_security_tests or evidence_any_approved(app_evidence, security_evidence_types)), "evidence": security_refs},
        {"id": "E7", "score": score(bool(tests or requirements), bool(tests)), "evidence": tests[:20] + requirements},
        {"id": "E8", "score": score(compose_file or bool(dockerfiles), deployment_doc), "evidence": deployment_evidence_refs},
        {"id": "S3", "score": score(has_interfaces, bool(schemas)), "evidence": compatibility_refs},
        {"id": "S5", "score": score(has_security_evidence, has_security_tests or evidence_any_approved(app_evidence, security_evidence_types)), "evidence": security_refs},
        {"id": "S6", "score": score(has_release_baseline, has_compatibility_declaration and evidence_approved(app_evidence, "release_compatibility_declaration")), "evidence": compatibility_refs},
        {"id": "S8", "score": score(has_resilience_evidence, evidence_any_approved(app_evidence, resilience_evidence_types)), "evidence": resilience_refs},
        {"id": "P5", "score": score(compose_file or bool(dockerfiles), deployment_doc and compose_file), "evidence": deployment_evidence_refs},
        {"id": "P6", "score": score(has_interfaces or bool(schemas), bool(schemas)), "evidence": compatibility_refs},
        {"id": "P8", "score": score(has_security_evidence, has_security_tests or evidence_any_approved(app_evidence, security_evidence_types)), "evidence": security_refs},
        {"id": "P9", "score": score(has_performance, has_performance), "evidence": benchmark_reports[-10:]},
        {"id": "P10", "score": score(has_resilience_evidence, evidence_any_approved(app_evidence, resilience_evidence_types)), "evidence": resilience_refs},
        {"id": "P11", "score": score(has_operation_evidence, evidence_any_approved(app_evidence, operation_evidence_types)), "evidence": runtime_refs},
        {"id": "P13", "score": score(has_compatibility_declaration, evidence_approved(app_evidence, "release_compatibility_declaration")), "evidence": compatibility_refs},
    ]

    service_count = len(re.findall(r"^  [a-zA-Z0-9_-]+:", read_text(repo / "docker-compose.yml"), flags=re.MULTILINE))

    return {
        "release_candidate": True,
        "target_repository": {
            "path": str(repo),
            "commit": git_commit(repo),
            "release_id": release_id,
            "detected_services": service_count,
        },
        "architecture": {
            "marker_assessments": marker_assessments,
            "release_compatibility_declaration": {
                "exists": has_compatibility_declaration,
                "baseline_version": app_evidence.get("release_compatibility_declaration", {}).get("baseline_version", baseline),
                "approved": evidence_approved(app_evidence, "release_compatibility_declaration"),
                "declaration_id": app_evidence.get("release_compatibility_declaration", {}).get("_path", ""),
                "approved_by": app_evidence.get("release_compatibility_declaration", {}).get("approved_by", ""),
                "approval_date": app_evidence.get("release_compatibility_declaration", {}).get("approval_date", ""),
            },
            "solution_baseline": {
                "exists": has_release_baseline,
                "baseline_id": app_evidence.get("solution_baseline", {}).get("_path", baseline),
                "version": app_evidence.get("solution_baseline", {}).get("baseline_version", baseline),
            },
            "compatibility_evidence": {
                "exists": bool(compatibility_refs) or has_compatibility_evidence,
                "evidence_refs": compatibility_refs,
            },
            "security_evidence": {
                "exists": bool(security_refs),
                "evidence_refs": security_refs,
            },
            "deployment_evidence": {
                "exists": bool(deployment_evidence_refs),
                "evidence_refs": deployment_evidence_refs,
            },
            "runtime_evidence": {
                "exists": bool(runtime_refs),
                "evidence_refs": runtime_refs,
            },
            "review_evidence": {
                "exists": has_review_evidence,
                "evidence_refs": review_refs,
            },
            "exception_evidence": {
                "exists": has_exception_evidence,
                "evidence_refs": exception_refs,
            },
            "feedback_evidence": {
                "exists": bool(feedback_refs),
                "evidence_refs": feedback_refs,
            },
            "exceptions": [],
            "detailed_evidence": summarize_detailed_evidence(app_evidence),
        },
    }


def main() -> int:
    parser = ArgumentParser(description="Collect architecture release-readiness input from a target repository.")
    parser.add_argument("--repo", required=True, help="Target repository path")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--release-id", default="demo-release-candidate", help="Release candidate identifier")
    parser.add_argument("--baseline", default="demo-solution-baseline", help="Expected solution baseline")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.exists():
        raise SystemExit(f"Target repository does not exist: {repo}")

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = collect(repo, args.release_id, args.baseline)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Generated {output}")
    print(f"- target repo: {repo}")
    print(f"- marker assessments: {len(payload['architecture']['marker_assessments'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
