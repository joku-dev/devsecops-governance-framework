"""Complete local result-index projections extracted from frozen V1 6b557fef.

Time, branch/event classification and consumer profile IDs are explicit data.
The application materializes only node-owned private records as the input root;
this module neither publishes nor writes a product status index.
"""
from pathlib import Path
from lib.evidence_verification import project_trust
from lib.portable.runtime import read_json as load_json


def devsecops_index(root, at, *, main_branch, push_events, manual_events, container_profiles,
                    trust_projection=project_trust):
    root = Path(root)
    STATUS_RESULTS = root / 'status/results'
    STATUS_RESULTS.mkdir(parents=True, exist_ok=True)
    repositories = []
    result_count = 0
    passing_results = 0
    failing_results = 0
    mainline_results = 0
    branch_results = 0
    manual_results = 0
    trust_level_counts = {}

    for repo_dir in sorted(path for path in STATUS_RESULTS.iterdir() if path.is_dir()):
        results = sorted(repo_dir.glob("*.json"))
        if not results:
            continue
        parsed = [(load_json(path), path) for path in results]
        parsed.sort(key=lambda pair: (pair[0].get("generated_at", ""), str(pair[1])))
        latest = parsed[-1][0]
        latest_main = None
        for item, _ in reversed(parsed):
            if item.get("repository", {}).get("branch") == main_branch and item.get("pipeline", {}).get("event") in push_events:
                latest_main = item
                break
        representative = latest_main or latest
        result_count += len(parsed)
        for item, _ in parsed:
            level = trust_projection(item)["effective_level"]
            trust_level_counts[level] = trust_level_counts.get(level, 0) + 1
            if item.get("overall_status") == "pass":
                passing_results += 1
            else:
                failing_results += 1
            if item.get("pipeline", {}).get("event") in manual_events:
                manual_results += 1
            elif item.get("repository", {}).get("branch") == main_branch:
                mainline_results += 1
            else:
                branch_results += 1
        history = []
        for item, path in parsed:
            control_summary = item.get("control_evaluation_summary", {})
            history.append(
                {
                    "generated_at": item.get("generated_at", ""),
                    "status": item.get("overall_status", "unknown"),
                    "pipeline_run_id": item.get("pipeline", {}).get("pipeline_run_id", "unknown"),
                    "pipeline_event": item.get("pipeline", {}).get("event", "unknown"),
                    "pipeline_url": item.get("pipeline", {}).get("pipeline_url", ""),
                    "branch": item.get("repository", {}).get("branch", "unknown"),
                    "commit_id": item.get("repository", {}).get("commit_id", "unknown"),
                    "governance_baseline_ref": item.get("governance_baseline_ref", "unknown"),
                    "control_evaluation_summary": control_summary,
                    "trust": trust_projection(item),
                    "source_file": str(path.relative_to(root)),
                }
            )
        repositories.append(
            {
                "repository_id": latest["repository_id"],
                "baseline_level": representative.get("baseline_level", "unknown"),
                "results_path": f"status/results/{repo_dir.name}/",
                "latest_result": {
                    "status": representative.get("overall_status", "unknown"),
                    "pipeline_run_id": representative.get("pipeline", {}).get("pipeline_run_id", "unknown"),
                    "commit_id": representative.get("repository", {}).get("commit_id", "unknown"),
                    "generated_at": representative.get("generated_at", ""),
                    "governance_baseline_ref": representative.get("governance_baseline_ref", "unknown"),
                    "source_file": next(
                        str(path.relative_to(root))
                        for item, path in parsed
                        if item == representative
                    ),
                    "control_evaluation_summary": representative.get("control_evaluation_summary", {}),
                    "trust": trust_projection(representative),
                },
                "history": history,
            }
        )

    payload = {
        "schema_version": "1.0.0",
        "generated_at": at,
        "summary": {
            "repository_count": len(repositories),
            "result_count": result_count,
            "passing_results": passing_results,
            "failing_results": failing_results,
            "mainline_results": mainline_results,
            "branch_results": branch_results,
            "manual_results": manual_results,
            "trust_level_counts": trust_level_counts,
        },
        "repositories": repositories,
    }
    return payload

def architecture_index(root, at, *, main_branch, push_events, manual_events, container_profiles,
                    trust_projection=project_trust):
    root = Path(root)
    STATUS_RESULTS = root / 'status/architecture-results'
    STATUS_RESULTS.mkdir(parents=True, exist_ok=True)
    repositories = []
    result_count = 0
    passing_results = 0
    findings_results = 0
    mainline_results = 0
    branch_results = 0
    manual_results = 0
    trust_level_counts = {}

    if not STATUS_RESULTS.exists():
        STATUS_RESULTS.mkdir(parents=True)

    for repo_dir in sorted(path for path in STATUS_RESULTS.iterdir() if path.is_dir()):
        results = sorted(repo_dir.glob("*.json"))
        if not results:
            continue
        parsed = [(load_json(path), path) for path in results]
        parsed.sort(key=lambda pair: (pair[0].get("generated_at", ""), str(pair[1])))
        latest = parsed[-1][0]
        latest_main = None
        for item, _ in reversed(parsed):
            if item.get("repository", {}).get("branch") == main_branch and item.get("pipeline", {}).get("event") in push_events:
                latest_main = item
                break
        representative = latest_main or latest
        result_count += len(parsed)
        for item, _ in parsed:
            level = trust_projection(item)["effective_level"]
            trust_level_counts[level] = trust_level_counts.get(level, 0) + 1
            if item.get("overall_status") == "pass":
                passing_results += 1
            else:
                findings_results += 1
            if item.get("pipeline", {}).get("event") in manual_events:
                manual_results += 1
            elif item.get("repository", {}).get("branch") == main_branch:
                mainline_results += 1
            else:
                branch_results += 1

        history = []
        for item, path in parsed:
            history.append(
                {
                    "generated_at": item.get("generated_at", ""),
                    "status": item.get("overall_status", "unknown"),
                    "pipeline_run_id": item.get("pipeline", {}).get("pipeline_run_id", "unknown"),
                    "pipeline_event": item.get("pipeline", {}).get("event", "unknown"),
                    "pipeline_url": item.get("pipeline", {}).get("pipeline_url", ""),
                    "branch": item.get("repository", {}).get("branch", "unknown"),
                    "commit_id": item.get("repository", {}).get("commit_id", "unknown"),
                    "architecture_baseline_ref": item.get("architecture_baseline_ref", "unknown"),
                    "architecture_summary": item.get("architecture_summary", {}),
                    "trust": trust_projection(item),
                    "source_file": str(path.relative_to(root)),
                }
            )

        repositories.append(
            {
                "repository_id": latest["repository_id"],
                "architecture_baseline_ref": representative.get("architecture_baseline_ref", "unknown"),
                "results_path": f"status/architecture-results/{repo_dir.name}/",
                "latest_result": {
                    "status": representative.get("overall_status", "unknown"),
                    "pipeline_run_id": representative.get("pipeline", {}).get("pipeline_run_id", "unknown"),
                    "commit_id": representative.get("repository", {}).get("commit_id", "unknown"),
                    "generated_at": representative.get("generated_at", ""),
                    "architecture_baseline_ref": representative.get("architecture_baseline_ref", "unknown"),
                    "pipeline_url": representative.get("pipeline", {}).get("pipeline_url", ""),
                    "branch": representative.get("repository", {}).get("branch", "unknown"),
                    "pipeline_event": representative.get("pipeline", {}).get("event", "unknown"),
                    "source_file": next(
                        str(path.relative_to(root))
                        for item, path in parsed
                        if item == representative
                    ),
                    "architecture_summary": representative.get("architecture_summary", {}),
                    "trust": trust_projection(representative),
                },
                "history": history,
            }
        )

    payload = {
        "schema_version": "1.0.0",
        "generated_at": at,
        "summary": {
            "repository_count": len(repositories),
            "result_count": result_count,
            "passing_results": passing_results,
            "findings_results": findings_results,
            "mainline_results": mainline_results,
            "branch_results": branch_results,
            "manual_results": manual_results,
            "trust_level_counts": trust_level_counts,
        },
        "repositories": repositories,
    }
    return payload

def check_result(trust: dict, check_id: str) -> str:
    for check in trust.get("checks", []):
        if check.get("id") == check_id:
            return check.get("result", "not_evaluated")
    return "not_evaluated"


def project_result(item: dict, source_file: Path, *, root: Path, container_profiles,
                   trust_projection=project_trust) -> dict:
    trust = item.get("trust", {})
    capture = trust.get("capture", {})
    observations = capture.get("observations", {})
    binding = observations.get("subject_binding", {})
    evidence_type = item.get("evidence_type", "unknown")
    projection = {
        "generated_at": item.get("generated_at", ""),
        "evidence_type": evidence_type,
        "pipeline_run_id": item.get("pipeline", {}).get("pipeline_run_id", "unknown"),
        "pipeline_event": item.get("pipeline", {}).get("event", "unknown"),
        "pipeline_url": item.get("pipeline", {}).get("pipeline_url", ""),
        "branch": item.get("repository", {}).get("branch", "unknown"),
        "commit_id": item.get("repository", {}).get("commit_id", "unknown"),
        "collector_status": capture.get("status", "unknown"),
        "enforcement": capture.get("enforcement", "report_only"),
        "subject_binding": {
            "mode": binding.get("mode", "unknown"),
            "producer_attested": binding.get("producer_attested", binding.get("scanner_attested", False)),
        },
        "freshness": check_result(trust, "freshness_evaluated"),
        "content_integrity": check_result(trust, "content_digest_verified"),
        "replay": check_result(trust, "replay_key_unique"),
        "trust": trust_projection(item),
        "source_file": str(source_file.relative_to(root)),
    }
    if evidence_type == "vulnerability_scan":
        projection.update({
            "producer": observations.get("scanner", {}),
            "finding_count": observations.get("finding_count", 0),
            "max_severity": observations.get("observed_max_severity", "unknown"),
            "severity_consistent": observations.get("severity_consistent"),
        })
    elif evidence_type == "sbom":
        projection.update({
            "producer": observations.get("generator", {}),
            "format": observations.get("format", {}),
            "component_count": observations.get("component_count", 0),
        })
    if observations.get('profile') in container_profiles:
        projection['container_images'] = observations['container_images']
    return projection


def typed_index(root, at, *, main_branch, push_events, manual_events, container_profiles,
                    trust_projection=project_trust):
    root = Path(root)
    STATUS_RESULTS = root / 'status/typed-evidence-results'
    STATUS_RESULTS.mkdir(parents=True, exist_ok=True)
    repositories = []
    result_count = 0
    mainline_results = 0
    branch_results = 0
    manual_results = 0
    freshness_failures = 0
    replay_failures = 0
    trust_level_counts: dict[str, int] = {}
    evidence_type_counts: dict[str, int] = {}

    if STATUS_RESULTS.exists():
        repo_dirs = sorted(path for path in STATUS_RESULTS.iterdir() if path.is_dir())
    else:
        repo_dirs = []
    for repo_dir in repo_dirs:
        paths = sorted(repo_dir.glob("*.json"))
        parsed = [(load_json(path), path) for path in paths]
        parsed.sort(key=lambda pair: pair[0].get("generated_at", ""))
        if not parsed:
            continue
        result_count += len(parsed)
        projections = []
        for item, path in parsed:
            projection = project_result(item, path, root=root, container_profiles=container_profiles,
                                        trust_projection=trust_projection)
            projections.append(projection)
            evidence_type = projection["evidence_type"]
            evidence_type_counts[evidence_type] = evidence_type_counts.get(evidence_type, 0) + 1
            level = projection["trust"]["effective_level"]
            trust_level_counts[level] = trust_level_counts.get(level, 0) + 1
            if projection["freshness"] == "fail":
                freshness_failures += 1
            if projection["replay"] == "fail":
                replay_failures += 1
            if projection["pipeline_event"] in manual_events:
                manual_results += 1
            elif projection["branch"] == main_branch and projection["pipeline_event"] in push_events:
                mainline_results += 1
            else:
                branch_results += 1
        latest_results = []
        evidence_types = sorted({projection["evidence_type"] for projection in projections},
                                key=lambda value: (value != "vulnerability_scan", value))
        for evidence_type in evidence_types:
            candidates = [projection for projection in projections if projection["evidence_type"] == evidence_type]
            latest_main = next((projection for projection in reversed(candidates)
                                if projection["branch"] == main_branch and projection["pipeline_event"] in push_events), None)
            latest_results.append(latest_main or candidates[-1])
        latest = next((result for result in latest_results if result["evidence_type"] == "vulnerability_scan"),
                      max(latest_results, key=lambda result: result["generated_at"]))
        repositories.append(
            {
                "repository_id": parsed[-1][0].get("repository_id", "unknown"),
                "results_path": f"status/typed-evidence-results/{repo_dir.name}/",
                "latest_result": latest,
                "latest_results": latest_results,
                "history": projections,
            }
        )

    payload = {
        "schema_version": "1.0.0",
        "generated_at": at,
        "summary": {
            "repository_count": len(repositories),
            "result_count": result_count,
            "mainline_results": mainline_results,
            "branch_results": branch_results,
            "manual_results": manual_results,
            "freshness_failures": freshness_failures,
            "replay_failures": replay_failures,
            "trust_level_counts": trust_level_counts,
            "evidence_type_counts": evidence_type_counts,
        },
        "repositories": repositories,
    }
    return payload
