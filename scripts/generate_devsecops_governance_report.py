#!/usr/bin/env python3
"""Generate a DevSecOps governance report from OPA release-readiness results."""

from argparse import ArgumentParser
from pathlib import Path
import json
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def run_opa(input_path: Path) -> list[str]:
    if not shutil.which("opa"):
        raise SystemExit("OPA executable not found")
    result = subprocess.run(
        [
            "opa",
            "eval",
            "--format=json",
            "--data",
            str(ROOT / "policies" / "opa" / "devsecops_release_readiness.rego"),
            "--input",
            str(input_path),
            "data.devsecops.release_readiness.deny",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip())
    payload = json.loads(result.stdout)
    return payload["result"][0]["expressions"][0]["value"]


def render_markdown(payload: dict, findings: list[str]) -> str:
    target = payload.get("target_repository", {})
    status = "PASS" if not findings else "FINDINGS"
    lines = [
        "# DevSecOps Governance Report",
        "",
        "## Target",
        "",
        f"- Repository: `{target.get('path', 'unknown')}`",
        f"- Commit: `{target.get('commit', 'unknown')}`",
        f"- Release ID: `{target.get('release_id', 'unknown')}`",
        "",
        "## Gate Summary",
        "",
        "| Gate | Status | Findings |",
        "|---|---:|---:|",
        f"| DevSecOps Release Readiness | {status} | {len(findings)} |",
        "",
        "## Findings",
        "",
    ]
    if not findings:
        lines.append("No findings.")
    else:
        for finding in findings:
            lines.append(f"- {finding}")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = ArgumentParser(description="Generate DevSecOps governance report.")
    parser.add_argument("--input", required=True, help="DevSecOps release input JSON")
    parser.add_argument("--output-json", required=True, help="Output JSON report path")
    parser.add_argument("--output-md", required=True, help="Output Markdown report path")
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Return a non-zero exit code when the report contains findings.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_json = Path(args.output_json).resolve()
    output_md = Path(args.output_md).resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    findings = run_opa(input_path)
    report = {
        "target": payload.get("target_repository", {}),
        "gate": {
            "id": "devsecops_release_readiness",
            "status": "pass" if not findings else "findings",
            "findings": findings,
        },
        "summary": {
            "finding_count": len(findings),
        },
    }
    output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(render_markdown(payload, findings), encoding="utf-8")

    print(f"Generated {output_json}")
    print(f"Generated {output_md}")
    print(f"- findings: {len(findings)}")
    if findings and args.fail_on_findings:
        print("Failing because --fail-on-findings is enabled.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
