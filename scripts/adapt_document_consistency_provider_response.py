#!/usr/bin/env python3
"""Project a provider-neutral response into the authoritative semantic contract."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "model/governance/document-consistency/provider-adapter-config-v1.json"


class ProviderAdapterError(ValueError):
    """Raised when provider output cannot be normalized without ambiguity."""


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderAdapterError(f"cannot read JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise ProviderAdapterError(f"expected JSON object: {path}")
    return value


def validate(value: dict, schema: dict, label: str) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise ProviderAdapterError(f"{label} schema error at {location}: {errors[0].message}")


def adapt_provider_response(
    projection: dict,
    config: dict,
    *,
    review_id: str,
    source_manifest_sha256: str,
    provider: str,
    model: str,
    prompt_version: str,
    truncated: bool = False,
) -> dict:
    """Normalize the bounded projection; never validate evidence or semantics."""
    projection_schema = read_json(ROOT / config["projection_schema"])
    canonical_schema = read_json(ROOT / config["canonical_schema"])
    validate(projection, projection_schema, "provider projection")
    normalized_findings = []
    normalization_notes = []
    aliases = config["normalization"]["misplaced_semantic_states"]

    for original in projection["findings"]:
        finding = deepcopy(original)
        status = finding["applicability"]["status"]
        if status in aliases:
            target = aliases[status]
            if finding["semantic_state"] not in {"proposed", target}:
                raise ProviderAdapterError(
                    f"{finding['finding_id']}: conflicting semantic_state and applicability.status"
                )
            finding["semantic_state"] = target
            finding["applicability"]["status"] = "unknown"
            normalization_notes.append(
                f"{finding['finding_id']}: moved misplaced applicability status {status} to semantic_state"
            )
        finding["recommendation"] = finding["recommendation"] or None
        scope = finding.pop("search_scope")
        if scope["status"] == "not_applicable":
            if scope["source_ids"] or scope["method"] or scope["limitations"]:
                raise ProviderAdapterError(
                    f"{finding['finding_id']}: not_applicable search scope must be empty"
                )
            finding["search_scope"] = None
        else:
            if not scope["source_ids"] or not scope["method"] or not scope["limitations"]:
                raise ProviderAdapterError(
                    f"{finding['finding_id']}: provided search scope is incomplete"
                )
            if len(scope["source_ids"]) != len(set(scope["source_ids"])):
                raise ProviderAdapterError(
                    f"{finding['finding_id']}: search scope contains duplicate source IDs"
                )
            finding["search_scope"] = {
                "source_ids": scope["source_ids"],
                "method": scope["method"],
                "limitations": scope["limitations"],
            }
        normalized_findings.append(finding)

    limitations = list(projection["limitations"])
    limitations.extend(f"Adapter normalization: {note}." for note in normalization_notes)
    result = {
        "schema_version": "1.0.0",
        "response_type": "document_consistency_semantic_response",
        "review_id": review_id,
        "source_manifest_sha256": source_manifest_sha256,
        "execution": {
            "mode": "provider",
            "status": "completed",
            "provider": provider,
            "model": model,
            "prompt_version": prompt_version,
            "configuration_version": config["configuration_id"],
            "truncated": truncated,
        },
        "findings": normalized_findings,
        "limitations": limitations,
    }
    validate(result, canonical_schema, "canonical semantic response")
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--review-id", required=True)
    parser.add_argument("--source-manifest-sha256", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt-version", required=True)
    parser.add_argument("--truncated", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        config = read_json(args.config)
        validate(config, read_json(ROOT / "schemas/document-consistency-provider-adapter-config.schema.json"), "adapter configuration")
        result = adapt_provider_response(
            read_json(args.input), config,
            review_id=args.review_id,
            source_manifest_sha256=args.source_manifest_sha256,
            provider=args.provider,
            model=args.model,
            prompt_version=args.prompt_version,
            truncated=args.truncated,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (OSError, ProviderAdapterError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
