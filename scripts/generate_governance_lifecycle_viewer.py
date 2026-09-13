#!/usr/bin/env python3
"""Generate a standalone read-only viewer from the verified synthetic overview."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re

from generate_governance_lifecycle_overview import validate_overview
from lib.governance_lifecycle.contracts import ROOT, require, schema_validator

TEMPLATE = ROOT / "scripts/templates/governance-lifecycle-viewer.html"
OUTPUT = "generated/viewer/governance-lifecycle-viewer.html"


def safe_json(value):
    """Preserve exact JSON values while preventing HTML script-element termination."""
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    for char, escaped in (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
                          ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        payload = payload.replace(char, escaped)
    return payload


def render_viewer(overview):
    schema_validator("overview").validate(overview)
    template = TEMPLATE.read_text(encoding="utf-8")
    require(template.count("@@DATA@@") == template.count("@@SCRIPT_HASH@@") == 1, "Invalid viewer template placeholders")
    scripts = re.findall(r'<script id="app">(.*?)</script>', template, re.S)
    require(len(scripts) == 1, "Viewer must contain one fixed executable script")
    digest = base64.b64encode(hashlib.sha256(scripts[0].encode("utf-8")).digest()).decode("ascii")
    return template.replace("@@SCRIPT_HASH@@", digest).replace("@@DATA@@", safe_json(overview))


def generate(repo=ROOT, *, output=None):
    root = Path(repo)
    path = Path(output) if output else root / OUTPUT
    for protected in ("governance/lifecycle", "model", "status", "scripts", "schemas"):
        require(not path.resolve().is_relative_to((root / protected).resolve()), "Viewer output cannot overwrite its inputs")
    require(path.resolve() != (root / "generated/viewer/status-viewer.html").resolve(), "Official status viewer is separate")
    html = render_viewer(validate_overview(root))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return html


def validate_viewer(repo=ROOT, *, overview=None):
    root = Path(repo)
    # A supplied overview must already have been verified by validate_overview.
    if overview is None:
        overview = validate_overview(root)
    expected = render_viewer(overview)
    require((root / OUTPUT).read_text(encoding="utf-8") == expected, "Lifecycle viewer differs from verified overview")
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    generate(output=args.output)
    print("Generated read-only synthetic lifecycle viewer; official consumer status is separate.")


if __name__ == "__main__":
    main()
