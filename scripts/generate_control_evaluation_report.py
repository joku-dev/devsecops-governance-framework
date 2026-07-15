#!/usr/bin/env python3
"""Generate a control-by-control evaluation report for a governance run input."""

from __future__ import annotations

from pathlib import Path
import argparse
import json

from control_evaluation import generate_control_evaluation_report, render_control_evaluation_markdown


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--markdown-file")
    args = parser.parse_args()

    input_path = Path(args.input_file).resolve()
    output_path = Path(args.output_file).resolve()
    markdown_path = Path(args.markdown_file).resolve() if args.markdown_file else output_path.with_suffix(".md")

    report = generate_control_evaluation_report(input_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_control_evaluation_markdown(report), encoding="utf-8")

    print(f"Wrote {output_path}")
    print(f"Wrote {markdown_path}")
    return 0 if report["summary"]["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
