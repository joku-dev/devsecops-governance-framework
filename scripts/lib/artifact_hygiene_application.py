"""Read-only public-artifact check; no publication, stored secret terms or authority."""
import argparse
from pathlib import Path
import sys

from lib.artifact_hygiene import assess, configured_terms
from lib.provider_ports import artifact_hygiene_capture, artifact_hygiene_environment

PROFILE = 'legacy-public-artifact-hygiene-v1'


def run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 artifact-hygiene', allow_abbrev=False)
    parser.add_argument('command', choices=('check',))
    parser.add_argument('--profile', choices=(PROFILE,), required=True)
    parser.add_argument('--forbidden-term', action='append', default=[])
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args(arguments)
    environment = artifact_hygiene_environment()
    if (len(environment) > 65536 or len(args.forbidden_term) > 1024
            or any(len(term) > 4096 for term in args.forbidden_term)):
        raise ValueError('artifact_hygiene_term_budget')
    terms = configured_terms(args.forbidden_term, environment)
    if len(terms) > 1024 or sum(map(len, terms)) > 65536:
        raise ValueError('artifact_hygiene_term_budget')
    # Original validates terms before touching any path.
    texts = artifact_hygiene_capture(args.paths) if terms else []
    code, stdout, stderr = assess(len(args.paths), texts, terms)
    sys.stdout.write(stdout)
    sys.stderr.write(stderr)
    return code
