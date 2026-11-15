"""Finite, private candidate DCR routes; supplied responses never trigger a model."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator, ValidationError
from generate_document_consistency_review_model import generate_model
from lib.candidate_workspace import CandidateWorkspace
from lib.consumer_intake_store import atomic_json
from lib.portable.contracts import ROOT
from lib.portable.runtime import read_json


def supplied_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024**2:
        raise ValueError('invalid_dcr_input')
    value = read_json(path)
    if not isinstance(value, dict):
        raise ValueError('dcr_object_required')
    return value


def run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 dcr', allow_abbrev=False)
    parser.add_argument('--workspace', required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    structural = commands.add_parser('structural')
    structural.add_argument('--review-id', required=True)
    structural.add_argument('--source-id', action='append', required=True)
    semantic = commands.add_parser('semantic')
    semantic.add_argument('--review-id', required=True)
    semantic.add_argument('--response', type=Path, required=True)
    adapt = commands.add_parser('adapt')
    adapt.add_argument('--review-id', required=True)
    adapt.add_argument('--input', type=Path, required=True)
    for field in ('provider', 'model', 'prompt-version'):
        adapt.add_argument('--' + field, required=True)
    adapt.add_argument('--truncated', action='store_true')
    evaluation = commands.add_parser('evaluate')
    evaluation.add_argument('--review-id', required=True)
    evaluation.add_argument('--catalog-version', choices=('v1', 'v2'), required=True)
    args = parser.parse_args(arguments)
    if len(args.review_id) > 96 or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', args.review_id):
        raise ValueError('invalid_dcr_review_id')
    workspace = CandidateWorkspace(instance_root, args.workspace, node_id=settings['node_id'])

    def operation(root):
        review = root / 'dcr/reviews' / args.review_id
        if args.command == 'structural':
            from lib.dcr_manifest import build_manifest
            from lib.dcr_structure import validate_model
            if review.exists():
                raise ValueError('fresh_dcr_review_required')
            manifest = build_manifest(root, args.source_id,
                repository='axiom-v2:candidate:' + settings['node_id'] + ':' + args.workspace)
            model = generate_model(root, manifest, schema_root=ROOT)
            report = validate_model(root, manifest, model)
            review.mkdir(mode=0o700, parents=True)
            atomic_json(review / 'manifest.json', manifest)
            atomic_json(review / 'model.json', model)
            atomic_json(review / 'structure.json', report)
            return {'review_id': args.review_id, 'report': report}
        manifest_path = review / 'manifest.json'
        if not manifest_path.is_file():
            raise ValueError('dcr_review_required')
        manifest = read_json(manifest_path)
        manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        if args.command == 'semantic':
            from lib.dcr_semantics import validate_semantic_response
            response = supplied_json(args.response)
            if response.get('review_id') != args.review_id:
                raise ValueError('dcr_response_review_mismatch')
            report = validate_semantic_response(root, manifest, response, manifest_digest)
            target = review / 'semantic.json'
            if target.exists():
                raise ValueError('dcr_semantic_result_already_exists')
            atomic_json(target, report)
            return {'review_id': args.review_id, 'report': report}
        if args.command == 'adapt':
            from lib.dcr_response import adapt_provider_response
            config = read_json(ROOT / 'model/governance/document-consistency/provider-adapter-config-v1.json')
            try:
                Draft202012Validator(read_json(ROOT / 'schemas/document-consistency-provider-adapter-config.schema.json')).validate(config)
            except ValidationError:
                raise ValueError('invalid_dcr_adapter_config') from None
            response = adapt_provider_response(supplied_json(args.input), config,
                review_id=args.review_id, source_manifest_sha256=manifest_digest,
                provider=args.provider, model=args.model, prompt_version=args.prompt_version,
                truncated=args.truncated)
            target = review / 'adapted-response.json'
            if target.exists():
                raise ValueError('dcr_adapted_response_already_exists')
            atomic_json(target, response)
            return {'review_id': args.review_id, 'adapted_response': response,
                    'limitations': ['Provider/model labels are operator declarations; no provider was invoked.']}
        from lib.dcr_evaluation import evaluate, require_schema
        catalog = read_json(ROOT / ('model/governance/document-consistency/semantic-evaluation-catalog-' + args.catalog_version + '.json'))
        report = read_json(review / 'semantic.json')
        require_schema(catalog, ROOT / 'schemas/document-consistency-semantic-evaluation-catalog.schema.json', 'catalog')
        require_schema(report, ROOT / 'schemas/document-consistency-semantic-report.schema.json', 'report')
        result = evaluate(catalog, report)
        require_schema(result, ROOT / 'schemas/document-consistency-semantic-evaluation-report.schema.json', 'evaluation')
        target = review / ('evaluation-' + args.catalog_version + '.json')
        if target.exists():
            raise ValueError('dcr_evaluation_already_exists')
        atomic_json(target, result)
        return {'review_id': args.review_id, 'evaluation': result}

    marker, output = workspace.execute(operation, write=True)
    print(json.dumps({**marker, **output}, ensure_ascii=False))
    return 0
