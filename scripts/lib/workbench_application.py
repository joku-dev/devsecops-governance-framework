"""Complete Workbench HTTP flow and explicit draft backup/restore per instance."""
import argparse
import json
from pathlib import Path

from lib.private_credentials import check_private_file
from lib.portable.runtime import read_json
from lib.provider_ports import WorkbenchPublication, workbench_data, workbench_workspace


def run(instance, settings, arguments):
    root = Path(instance).resolve()
    action = arguments[0] if arguments and arguments[0] in ('backup', 'verify-backup', 'restore') else 'serve'
    workspace = workbench_workspace(root, settings, create=action != 'verify-backup')
    if action != 'serve':
        parser = argparse.ArgumentParser(prog='axiom-v2 workbench ' + action, allow_abbrev=False)
        parser.add_argument('--output' if action == 'backup' else '--archive', type=Path, required=True)
        if action != 'backup':
            parser.add_argument('--sha256', required=True)
            parser.add_argument('--allow-source-change', action='store_true',
                help='Explicitly import only schema-compatible historical draft data; no code or authority')
        args = parser.parse_args(arguments[1:])
        if action == 'backup': value = workspace.backup(args.output)
        elif action == 'restore': value = workspace.restore(args.archive, args.sha256, allow_source_change=args.allow_source_change)
        else:
            raw, manifest, _ = workspace.inspect(args.archive, args.sha256, allow_source_change=args.allow_source_change)
            value = workspace.receipt(raw, manifest, 'verify-backup')
        print(json.dumps(value, sort_keys=True)); return 0
    args = arguments[1:] if arguments and arguments[0] == 'serve' else arguments
    parser = argparse.ArgumentParser(prog='axiom-v2 workbench', allow_abbrev=False,
        description='Private local source intake, review preparation and explicit proposal publication.')
    parser.add_argument('--enable-pr', action='store_true')
    parser.add_argument('--publication-profile', type=Path)
    parser.add_argument('--port', type=int, default=settings['port'])
    parser.add_argument('--state-dir', type=Path, default=workspace.root)
    parser.add_argument('--consumer-projection', type=Path, default=root/'projection')
    from lib.v2_application import set_option
    for name, value in (('--port', settings['port']), ('--state-dir', workspace.root), ('--consumer-projection', root/'projection')):
        args = set_option(args, name, value)
    options = parser.parse_args(args)
    if (options.port != settings['port'] or options.state_dir.absolute() != workspace.root
            or options.consumer_projection.absolute() != root/'projection'):
        raise ValueError('v2_instance_path_override_rejected')
    if settings['development'] and options.enable_pr:
        raise ValueError('development_v2_instance_cannot_publish')
    if options.enable_pr and options.publication_profile is None:
        raise ValueError('explicit_workbench_publication_profile_required')
    publisher = WorkbenchPublication.from_file(options.publication_profile) if options.publication_profile else None
    check_private_file(root/'workbench-key.json')
    key = read_json(root/'workbench-key.json')['key']
    import serve_governance_workbench as http
    with workspace.lease():
        workspace.capture()
        backend = workbench_data(Path(settings['source_root']), workspace.root, instance=root)
        application = http.Workbench(root=settings['source_root'], state_dir=workspace.root,
            consumer_projection=root/'projection', publisher=publisher, enable_pr=options.enable_pr,
            backend=backend)
        return http.main(['--port', str(settings['port'])], application=application, access_key=key)
