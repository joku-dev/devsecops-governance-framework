"""Finite, private candidate DCR routes; supplied responses never trigger a model."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from jsonschema import Draft202012Validator, ValidationError
from generate_document_consistency_review_model import generate_model
from lib.candidate_workspace import CandidateWorkspace
from lib.consumer_intake_store import atomic_json
from lib.portable.contracts import ROOT
from lib.portable.runtime import read_json


def supplied_input(path):
    path = Path(path)
    limit = 4 * 1024**2
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
            raise ValueError('invalid_dcr_input')
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('invalid_dcr_input')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate_json_key')
            value[key] = item
        return value
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError('dcr_object_required')
    return value, raw


def supplied_json(path):
    return supplied_input(path)[0]


def run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 dcr', allow_abbrev=False)
    parser.add_argument('--workspace', required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    structural = commands.add_parser('structural')
    structural.add_argument('--review-id', required=True)
    structural.add_argument('--source-id', action='append', required=True)
    structural.add_argument('--context', choices=('candidate', 'committed-source'), default='candidate')
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
    commands.add_parser('operations')
    scope = commands.add_parser('scope')
    scope.add_argument('--change-type', action='append', required=True)
    scope.add_argument('--impact-unknown', action='store_true')
    catalog = commands.add_parser('prepare-catalog')
    catalog.add_argument('--review-id', required=True)
    projection = commands.add_parser('project')
    projection.add_argument('--review-id', required=True)
    projection.add_argument('--report', type=Path, required=True)
    projection.add_argument('--manifest', type=Path, required=True)
    projection.add_argument('--decision', type=Path, action='append', required=True)
    projection.add_argument('--comparison-count', type=int, required=True)
    args = parser.parse_args(arguments)
    if hasattr(args, 'review_id') and (len(args.review_id) > 96 or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', args.review_id)):
        raise ValueError('invalid_dcr_review_id')
    workspace = CandidateWorkspace(instance_root, args.workspace, node_id=settings['node_id'])

    def operation(root):
        from lib.dcr_source_context import require_committed_source
        if args.command == 'operations':
            from lib.dcr_operations import validate
            return {'operations': validate(ROOT), 'provider_invoked': False}
        if args.command == 'scope':
            from lib.dcr_operations import plan_scope
            matrix = read_json(ROOT / 'model/governance/document-consistency/trigger-scope-matrix-v1.json')
            return {'scope': plan_scope(matrix, args.change_type, impact_known=not args.impact_unknown)}
        if args.command == 'prepare-catalog':
            from lib.dcr_catalog import prepare
            package = prepare(root / 'dcr/catalog-runs' / args.review_id)
            return {'review_id': args.review_id, 'package': package, 'provider_invoked': False}
        if args.command == 'project':
            from lib.dcr_projection import validate_decisions
            from lib.document_consistency_view import build_redacted_snapshot
            commit = require_committed_source(ROOT)
            target = root / 'dcr/projections' / args.review_id
            if target.exists():
                raise ValueError('fresh_dcr_projection_required')
            target.mkdir(mode=0o700, parents=True)
            report = supplied_json(args.report)
            if report.get('review_id') != args.review_id:
                raise ValueError('dcr_response_review_mismatch')
            # Keep original bytes for the exact manifest hash used by decisions.
            manifest_copy = target / 'manifest.json'
            manifest, manifest_bytes = supplied_input(args.manifest)
            manifest_copy.write_bytes(manifest_bytes)
            validate_decisions(report, manifest, manifest_copy, args.decision)
            snapshot = build_redacted_snapshot(ROOT, report, manifest, manifest_copy.read_bytes(),
                                               args.comparison_count)
            require_committed_source(ROOT, commit)
            atomic_json(target / 'snapshot.json', snapshot)
            # Decision assertions and full semantic prose are deliberately not copied.
            return {'review_id': args.review_id, 'snapshot': snapshot,
                    'context': {'kind': 'committed-source', 'source_revision': commit},
                    'published': False, 'decision_identity_authenticated': False}
        review = root / 'dcr/reviews' / args.review_id
        if args.command == 'structural':
            from lib.dcr_manifest import build_manifest
            from lib.dcr_structure import validate_model
            if review.exists():
                raise ValueError('fresh_dcr_review_required')
            input_root = ROOT if args.context == 'committed-source' else root
            commit = require_committed_source(ROOT) if args.context == 'committed-source' else None
            manifest = build_manifest(input_root, args.source_id,
                repository=('axiom-v2:committed-source:' + commit if commit else
                            'axiom-v2:candidate:' + settings['node_id'] + ':' + args.workspace))
            model = generate_model(input_root, manifest, schema_root=ROOT)
            report = validate_model(input_root, manifest, model)
            if commit is not None:
                require_committed_source(ROOT, commit)
            review.mkdir(mode=0o700, parents=True)
            atomic_json(review / 'manifest.json', manifest)
            atomic_json(review / 'model.json', model)
            atomic_json(review / 'structure.json', report)
            atomic_json(review / 'context.json', {'kind': args.context, 'source_revision': commit})
            return {'review_id': args.review_id, 'report': report}
        manifest_path = review / 'manifest.json'
        if not manifest_path.is_file():
            raise ValueError('dcr_review_required')
        manifest = read_json(manifest_path)
        context = read_json(review / 'context.json')
        input_root = ROOT if context['kind'] == 'committed-source' else root
        if input_root == ROOT:
            require_committed_source(ROOT, context['source_revision'])
        manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        if args.command == 'semantic':
            from lib.dcr_semantics import validate_semantic_response
            response = supplied_json(args.response)
            if response.get('review_id') != args.review_id:
                raise ValueError('dcr_response_review_mismatch')
            report = validate_semantic_response(input_root, manifest, response, manifest_digest)
            if input_root == ROOT:
                require_committed_source(ROOT, context['source_revision'])
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

    marker, output = workspace.execute(operation, write=args.command not in ('operations', 'scope'))
    print(json.dumps({**marker, **output}, ensure_ascii=False))
    return 0
