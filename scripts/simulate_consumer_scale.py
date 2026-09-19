#!/usr/bin/env python3
"""Benchmark isolated consumer-scale projections without changing official state."""

from __future__ import annotations

import argparse
import copy
from contextlib import redirect_stdout
from datetime import datetime, timezone
import gzip
import importlib
import io
import json
from pathlib import Path
import platform
import sys
import tempfile
import time
import tracemalloc


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

DEVSECOPS_INDEX = ROOT / "status" / "repository-results-index.json"
ARCHITECTURE_INDEX = ROOT / "status" / "architecture-results-index.json"
TYPED_INDEX = ROOT / "status" / "typed-evidence-results-index.json"
DEFAULT_SOURCE_REPOSITORY = "joku-dev/ha-CPsWMS"
LIGHT_VIEWER_REPOSITORY = "joku-dev/governance-framework-demo-consumer"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_payload(root: Path, index: dict, repository_id: str) -> dict:
    row = next(
        (item for item in index.get("repositories", []) if item["repository_id"] == repository_id),
        None,
    )
    if row is None:
        raise ValueError(f"No indexed source repository: {repository_id}")
    return load_json(root / row["latest_result"]["source_file"])


def synthetic_repository_id(index: int) -> str:
    return f"synthetic/team-{index // 100:02d}-repo-{index:04d}"


def set_synthetic_identity(payload: dict, index: int) -> str:
    repository_id = synthetic_repository_id(index)
    payload["repository_id"] = repository_id
    repository = payload.get("repository", {})
    if repository:
        repository["commit_id"] = f"{index:040x}"[-40:]
    pipeline = payload.get("pipeline", {})
    if pipeline:
        pipeline["pipeline_run_id"] = str(10_000_000 + index)
        pipeline["pipeline_url"] = f"https://example.invalid/runs/{10_000_000 + index}"
    return repository_id


def measured_call(callable_) -> tuple[object, float, float]:
    tracemalloc.start()
    started = time.perf_counter()
    result = callable_()
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, elapsed, peak / (1024 * 1024)


def generate_indexes(root: Path, repository_count: int) -> tuple[dict, dict]:
    repository_index = importlib.import_module("generate_repository_results_index")
    architecture_index = importlib.import_module("generate_architecture_results_index")
    typed_index = importlib.import_module("generate_typed_evidence_results_index")
    portfolio = importlib.import_module("generate_portfolio_onboarding_status")

    devsecops_current = load_json(root / "status" / "repository-results-index.json")
    architecture_current = load_json(root / "status" / "architecture-results-index.json")
    typed_current = load_json(root / "status" / "typed-evidence-results-index.json")
    devsecops_template = source_payload(root, devsecops_current, DEFAULT_SOURCE_REPOSITORY)
    architecture_template = source_payload(root, architecture_current, DEFAULT_SOURCE_REPOSITORY)
    typed_row = next(
        item
        for item in typed_current["repositories"]
        if item["repository_id"] == DEFAULT_SOURCE_REPOSITORY
    )
    typed_templates = [load_json(root / item["source_file"]) for item in typed_row["latest_results"]]

    with tempfile.TemporaryDirectory(prefix=f"governance-scale-{repository_count}-") as tempdir:
        simulation_root = Path(tempdir)
        inputs = {
            repository_index: simulation_root / "status" / "results",
            architecture_index: simulation_root / "status" / "architecture-results",
            typed_index: simulation_root / "status" / "typed-evidence-results",
        }
        for path in inputs.values():
            path.mkdir(parents=True)

        seed_started = time.perf_counter()
        for index in range(repository_count):
            directory_name = f"synthetic__repo-{index:04d}"
            for module, template in (
                (repository_index, devsecops_template),
                (architecture_index, architecture_template),
            ):
                target = inputs[module] / directory_name
                target.mkdir()
                payload = copy.deepcopy(template)
                set_synthetic_identity(payload, index)
                (target / "result.json").write_text(json.dumps(payload), encoding="utf-8")
            typed_target = inputs[typed_index] / directory_name
            typed_target.mkdir()
            for typed_number, template in enumerate(typed_templates):
                payload = copy.deepcopy(template)
                set_synthetic_identity(payload, index)
                (typed_target / f"typed-{typed_number}.json").write_text(
                    json.dumps(payload), encoding="utf-8"
                )

        metrics: dict[str, object] = {
            "seed_seconds": time.perf_counter() - seed_started,
            "simulation_storage": "temporary_directory",
        }
        payloads = {}
        for label, module in (
            ("devsecops", repository_index),
            ("architecture", architecture_index),
            ("typed_evidence", typed_index),
        ):
            original = module.ROOT, module.STATUS_RESULTS, module.INDEX_PATH
            module.ROOT = simulation_root
            module.STATUS_RESULTS = inputs[module]
            module.INDEX_PATH = simulation_root / f"{label}.json"
            try:
                with redirect_stdout(io.StringIO()):
                    _, elapsed, peak_mib = measured_call(module.main)
                payload = load_json(module.INDEX_PATH)
                payloads[label] = payload
                metrics[label] = {
                    "seconds": elapsed,
                    "peak_mib": peak_mib,
                    "bytes": module.INDEX_PATH.stat().st_size,
                    "repositories": len(payload["repositories"]),
                    "results": payload["summary"]["result_count"],
                }
            finally:
                module.ROOT, module.STATUS_RESULTS, module.INDEX_PATH = original

        registry = {
            "integrations": [
                {
                    "repository": synthetic_repository_id(index),
                    "owner": f"team-{index // 100:02d}",
                    "action_owner": "platform-operations",
                    "governance_mode": "report-only",
                    "governance_workflow_ref": "l1-baseline-v1.1.3",
                }
                for index in range(repository_count)
            ]
        }
        now = datetime.now(timezone.utc)
        portfolio_payload, elapsed, peak_mib = measured_call(
            lambda: portfolio.build_payload(
                registry,
                payloads["devsecops"],
                payloads["architecture"],
                now,
            )
        )
        metrics["portfolio"] = {
            "seconds": elapsed,
            "peak_mib": peak_mib,
            "bytes": len(json.dumps(portfolio_payload).encode("utf-8")),
            "repositories": len(portfolio_payload["repositories"]),
        }
        return metrics, payloads


def serialize_viewer_rows(
    viewer_data: dict,
    source_row: dict,
    repository_count: int,
) -> dict:
    def materialize() -> tuple[bytes, bytes]:
        repositories = []
        for index in range(repository_count):
            row = copy.deepcopy(source_row)
            row["id"] = synthetic_repository_id(index)
            repositories.append(row)
        model = {
            "version": 1,
            "repositories": repositories,
            "repository_security": viewer_data["repository_security"],
            "technical": viewer_data["technical"],
        }
        pretty = json.dumps(model, ensure_ascii=False, indent=2).encode("utf-8")
        return pretty, gzip.compress(pretty, compresslevel=6)

    (pretty, compressed), elapsed, peak_mib = measured_call(materialize)
    return {
        "mode": "materialized",
        "seconds": elapsed,
        "peak_mib": peak_mib,
        "bytes": len(pretty),
        "gzip_bytes": len(compressed),
        "findings_per_repository": len(source_row.get("findings", [])),
    }


def estimate_viewer_rows(source_row: dict, repository_count: int) -> dict:
    pretty_row = len(json.dumps(source_row, ensure_ascii=False, indent=2).encode("utf-8"))
    compact_row = len(
        json.dumps(source_row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    return {
        "mode": "lower_bound_estimate",
        "pretty_bytes": pretty_row * repository_count,
        "compact_bytes": compact_row * repository_count,
        "findings_per_repository": len(source_row.get("findings", [])),
    }


def load_current_viewer_projection(root: Path) -> dict:
    viewer = importlib.import_module("lib.viewer_app")

    def read_index(name: str) -> dict:
        return load_json(root / "status" / name)

    data = viewer.project(
        read_index("repository-results-index.json"),
        read_index("architecture-results-index.json"),
        viewer.load_snapshots(root / "status" / "measured-security-results"),
        viewer.load_l1_snapshots(root / "status" / "measured-l1-results"),
        viewer.load_assurance_snapshots(root / "status" / "control-evidence-assurance"),
        viewer.load_staging_snapshots(root / "status" / "staging-deployment-results"),
        viewer.load_consolidated_l1_snapshots(root / "status" / "consolidated-l1-results"),
    )
    data["repository_security"] = viewer.load_repository_security(root)
    legacy = root / "generated" / "viewer" / "status-viewer.html"
    data["technical"] = viewer.project_technical(legacy.read_text(encoding="utf-8"))
    return data


def run_simulation(
    root: Path,
    repository_counts: list[int],
    detailed_materialize_limit: int = 300,
) -> dict:
    viewer_data = load_current_viewer_projection(root)
    detailed_row = next(
        row for row in viewer_data["repositories"] if row["id"] == DEFAULT_SOURCE_REPOSITORY
    )
    light_row = next(
        row for row in viewer_data["repositories"] if row["id"] == LIGHT_VIEWER_REPOSITORY
    )
    scenarios = {}
    for repository_count in repository_counts:
        generation, _ = generate_indexes(root, repository_count)
        detailed = (
            serialize_viewer_rows(viewer_data, detailed_row, repository_count)
            if repository_count <= detailed_materialize_limit
            else estimate_viewer_rows(detailed_row, repository_count)
        )
        scenarios[str(repository_count)] = {
            "generation": generation,
            "viewer_light": serialize_viewer_rows(viewer_data, light_row, repository_count),
            "viewer_detailed": detailed,
        }
    return {
        "schema_version": "1.0.0",
        "simulation_type": "isolated_consumer_scale",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "source_repository": DEFAULT_SOURCE_REPOSITORY,
        "official_state_modified": False,
        "scope": {
            "included": [
                "DevSecOps index generation",
                "architecture index generation",
                "typed-evidence index generation",
                "portfolio projection",
                "static viewer JSON serialization",
            ],
            "excluded": [
                "GitHub API and artifact download latency",
                "GitHub Actions queue and runner limits",
                "branch, pull-request and review throughput",
                "browser rendering latency",
                "long-term history growth",
            ],
        },
        "scenarios": scenarios,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an isolated scale benchmark using current repository-shaped data."
    )
    parser.add_argument(
        "--repositories",
        nargs="+",
        type=int,
        default=[300, 1500],
        help="One or more positive consumer counts (default: 300 1500).",
    )
    parser.add_argument(
        "--detailed-materialize-limit",
        type=int,
        default=300,
        help="Materialize detailed viewer rows only up to this count; larger scenarios are estimated.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON output path; stdout is always used.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if any(value < 1 for value in args.repositories):
        raise SystemExit("Repository counts must be positive")
    if args.detailed_materialize_limit < 0:
        raise SystemExit("--detailed-materialize-limit must be non-negative")
    if args.output:
        resolved_output = args.output.resolve()
        protected_roots = ((ROOT / "status").resolve(), (ROOT / "generated").resolve())
        if any(resolved_output == path or path in resolved_output.parents for path in protected_roots):
            raise SystemExit("Simulation output must not be written below status/ or generated/")
    result = run_simulation(ROOT, args.repositories, args.detailed_materialize_limit)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
