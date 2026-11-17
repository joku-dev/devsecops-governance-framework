"""Finite candidate-only requirement lifecycle application routes."""
import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re

from lib.candidate_workspace import CandidateWorkspace
from lib.portable.contracts import ROOT
from lib.requirement_workspace import RequirementWorkspace
from lib.requirement_lifecycle import parse_native_requirement


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    root.add_argument('--workspace', required=True)
    commands = root.add_subparsers(dest='command', required=True)
    commands.add_parser('init')
    native_file = commands.add_parser('put-native')
    native_file.add_argument('--file', type=Path, required=True)
    native_file.add_argument('--name', required=True)
    source = commands.add_parser('import-source')
    source.add_argument('--case-id', required=True)
    source.add_argument('--source-id', required=True)
    source.set_defaults(handler='import_source')
    native = commands.add_parser('start-native')
    native.add_argument('--case-id', required=True)
    native.add_argument('--source-path', required=True)
    native.set_defaults(handler='start_native')
    decision = commands.add_parser('decide')
    for name in ('case-id', 'proposal-id', 'decided-by', 'decision-role', 'rationale'):
        decision.add_argument(f'--{name}', required=True)
    decision.add_argument('--disposition', choices=['approve', 'reject'], required=True)
    decision.add_argument('--classification', choices=['duplicate', 'new', 'extend', 'change', 'supersede', 'conflict'], required=True)
    decision.add_argument('--target')
    decision.add_argument('--decision-ref', help='Versioned decision record; defaults to the lifecycle case reference')
    decision.add_argument('--authorized-derivation', action='append', default=[])
    decision.add_argument('--runtime-enforcement', choices=['none', 'report_only', 'blocking'], default='none')
    decision.set_defaults(handler='decide')
    reanalyze = commands.add_parser('reanalyze-all')
    reanalyze.set_defaults(handler='reanalyze_all')
    activation = commands.add_parser('activate')
    activation.add_argument('--case-id', required=True)
    activation.add_argument('--effective-from', required=True)
    activation.add_argument('--commit', required=True)
    activation.add_argument('--proposal-id', action='append', default=[], help='Activate only the named approved proposal; repeat for a batch')
    activation.set_defaults(handler='activate')
    completion = commands.add_parser('complete-migration')
    for name in ('case-id', 'catalog-release', 'effective-from', 'decision-ref'):
        completion.add_argument(f'--{name}', required=True)
    completion.set_defaults(handler='complete_migration')
    status = commands.add_parser('report')
    status.set_defaults(handler='report')
    next_item = commands.add_parser('next-decision')
    next_item.add_argument('--case-id', required=True)
    next_item.set_defaults(handler='next_decision')
    publication = commands.add_parser('generate-publication')
    publication.set_defaults(handler='generate_publication')
    return root


def run(arguments, instance_root, settings):
    args = parser().parse_args(arguments)
    workspace = CandidateWorkspace(instance_root, args.workspace, node_id=settings['node_id'])
    if args.command == 'init':
        marker = workspace.initialize(ROOT)
        print(json.dumps({**marker, 'messages': ['Candidate data copied from committed source. Historical authority is not transferred.']}))
        return 0
    def operation(root):
        if args.command == 'put-native':
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}\.md', args.name):
                raise ValueError('invalid_native_requirement_filename')
            path = Path(args.file)
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024**2:
                raise ValueError('invalid_native_requirement_input')
            raw = path.read_bytes()
            if len(raw) > 1024**2:
                raise ValueError('invalid_native_requirement_input')
            destination = root / 'docs/governance/requirements/native-sources' / args.name
            if destination.exists():
                raise ValueError('native_requirement_already_exists')
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            destination.write_bytes(raw)
            parse_native_requirement(destination)
            return {'source_path': destination.relative_to(root).as_posix()}
        domain = RequirementWorkspace(root)
        handlers = {
            'import_source': domain.import_source, 'start_native': domain.start_native,
            'decide': domain.decide, 'reanalyze_all': domain.reanalyze_all,
            'activate': domain.activate, 'complete_migration': domain.complete_migration,
            'report': domain.report, 'next_decision': domain.next_decision,
            'generate_publication': domain.generate_publication,
        }
        output = io.StringIO()
        with redirect_stdout(output):
            handlers[args.handler](args)
        return {'messages': output.getvalue().splitlines()}
    marker, output = workspace.execute(operation, write=args.command not in ('report', 'next-decision'))
    print(json.dumps({**marker, **output}, ensure_ascii=False))
    return 0
