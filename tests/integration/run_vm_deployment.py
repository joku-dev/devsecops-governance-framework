#!/usr/bin/env python3
"""Destructive integration test ONLY on a disposable Ubuntu 24.04 host.

Uses real Ansible, Git, pip, OPA and systemd with a loopback fixture Git origin.
Never run on the Proxmox target or a workstation with an AXIOM installation.
"""
import argparse
import contextlib
import functools
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import vm_deployment as vm


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-disposable-host', action='store_true', required=True)
    args = parser.parse_args()
    if Path('/srv/axiom').exists() or Path('/etc/axiom').exists():
        raise SystemExit('Refusing an existing installation; use a fresh disposable host')
    if 'VERSION_ID="24.04"' not in Path('/etc/os-release').read_text():
        raise SystemExit('Requires disposable Ubuntu 24.04 with systemd')
    os.umask(0o077)
    temporary = Path(tempfile.mkdtemp(prefix='axiom-iac-integration-'))
    print('Private integration logs:', temporary, flush=True)
    fixture = temporary / 'fixture'
    run(['git', 'clone', '--no-hardlinks', str(ROOT), str(fixture)])
    # Include the current worktree changes, so this runner also works before commit.
    paths = run(['git', 'ls-files', '--cached', '--others', '--exclude-standard'], cwd=ROOT).splitlines()
    for name in paths:
        source = ROOT / name
        if source.is_file() and not source.is_symlink():
            target = fixture / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    run(['git', 'config', 'user.name', 'AXIOM disposable integration'], cwd=fixture)
    run(['git', 'config', 'user.email', 'integration@example.invalid'], cwd=fixture)
    run(['git', 'add', '-A'], cwd=fixture)
    run(['git', 'commit', '--allow-empty', '-m', 'Disposable installation fixture'], cwd=fixture)
    first = run(['git', 'rev-parse', 'HEAD'], cwd=fixture)
    style = fixture / 'scripts/workbench/style.css'
    style.write_text(style.read_text() + '\n/* Disposable update fixture. */\n')
    run(['git', 'commit', '-am', 'Disposable update fixture'], cwd=fixture)
    second = run(['git', 'rev-parse', 'HEAD'], cwd=fixture)
    server = fixture / 'scripts/serve_governance_workbench.py'
    server.write_text(server.read_text().replace('def main():\n',
        'def main():\n    if str(ROOT) == "/srv/axiom/repository":\n        raise SystemExit("Synthetic activation failure")\n', 1))
    run(['git', 'commit', '-am', 'Disposable activation-failure fixture'], cwd=fixture)
    broken = run(['git', 'rev-parse', 'HEAD'], cwd=fixture)
    origin = temporary / 'origin.git'
    run(['git', 'clone', '--bare', str(fixture), str(origin)])
    run(['git', 'update-server-info'], cwd=origin)

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *unused):
            pass

    handler = functools.partial(QuietHandler, directory=str(temporary))
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    inventory = temporary / 'inventory.json'
    inventory.write_text(json.dumps({'all': {'children': {'axiom': {'hosts': {'axiom_vm': {
        'ansible_connection': 'local', 'ansible_python_interpreter': '/usr/bin/python3'}}}}}}))
    backups = vm.private_directory(temporary / 'backups')
    counter = 0

    def apply(action, revision='', expected=0, **extra):
        nonlocal counter
        counter += 1
        variables = {'vm_action': action, 'vm_revision': revision,
            'vm_deployment_id': f'20261114T0000{counter:02}Z-{counter:012x}',
            'vm_repository_url': f'http://127.0.0.1:{httpd.server_port}/origin.git',
            'vm_controller_backups': str(backups),
            'vm_controller_helper': str(ROOT/'scripts/lib/vm_deployment.py'), **extra}
        path = temporary / 'variables.json'
        path.write_text(json.dumps(variables))
        command = [str(Path(sys.executable).parent/'ansible-playbook'), '-i', str(inventory),
                   str(ROOT/'infra/ansible/site.yml'), '--extra-vars', '@'+str(path)]
        environment = dict(os.environ, ANSIBLE_CONFIG=str(ROOT/'infra/ansible/ansible.cfg'),
                           ANSIBLE_LOCAL_TEMP=str(temporary/'ansible-tmp'))
        result = subprocess.run(command, text=True, capture_output=True, env=environment)
        log = temporary / f'{counter:02}-{action}.log'
        log.write_text(result.stdout + result.stderr)
        if (result.returncode == 0) != (expected == 0):
            print(result.stdout[-5000:] + result.stderr[-2000:], flush=True)
            raise AssertionError(f'{action}: unexpected exit {result.returncode}; private log {log}')
        print(f'{counter:02} {action}: expected exit {result.returncode}', flush=True)
        return result.stdout

    def receipt():
        return json.loads(run(['sudo', 'cat', '/etc/axiom/deployment.json']))

    def pid():
        return run(['systemctl', 'show', 'axiom-workbench', '-p', 'MainPID', '--value'])

    try:
        apply('install', broken, expected=1)
        assert subprocess.run(['systemctl','is-active','--quiet','axiom-workbench']).returncode != 0
        enabled = subprocess.run(['systemctl','is-enabled','axiom-workbench'], capture_output=True, text=True)
        assert enabled.stdout.strip() == 'disabled'
        assert not Path('/etc/axiom/deployment.json').exists()
        apply('install', first)
        assert receipt()['current_revision'] == first
        initial_pid = pid()
        initial_backups = len(list(backups.iterdir()))
        apply('install', first)
        assert pid() == initial_pid, 'Idempotent installation restarted the service'
        assert len(list(backups.iterdir())) == initial_backups, 'Idempotent run created unnecessary backup'
        key_hash = run(['sudo', 'sha256sum', '/etc/axiom/workbench.env']).split()[0]
        # Generate a real source review using the installed Workbench and a real registered source.
        create = """import sys;sys.path.insert(0,'scripts');import serve_governance_workbench as w; a=w.Workbench(); s=a.register()['documents'][0]; print(a.source_review({'source_id':s['id']})['draft_id'])"""
        draft_id = run(['sudo', '-u', 'axiom', '/srv/axiom/venvs/'+first+'/bin/python', '-c', create], cwd='/srv/axiom/repository')
        state = Path('/srv/axiom/repository/.local/governance-workbench')
        before = run(['sudo', 'sha256sum', str(state/draft_id/'draft.json')]).split()[0]
        apply('update', second)
        assert receipt()['current_revision'] == second
        assert receipt()['previous_revision'] == first
        assert run(['sudo', 'sha256sum', str(state/draft_id/'draft.json')]).split()[0] == before
        apply('rollback')
        assert receipt()['current_revision'] == first
        apply('update', broken, expected=1)
        assert receipt()['current_revision'] == first, 'Failed activation changed the accepted receipt'
        assert run(['systemctl', 'is-active', 'axiom-workbench']) == 'active'
        assert run(['sudo', 'sha256sum', str(state/draft_id/'draft.json')]).split()[0] == before
        assert run(['sudo', 'sha256sum', '/etc/axiom/workbench.env']).split()[0] == key_hash
        # Explicit import: a valid source review, unchanged original retained on the controller.
        source = vm.private_directory(temporary / 'local-drafts')
        selected = 'a'*32
        folder = vm.private_directory(source / selected)
        draft = json.loads(run(['sudo', 'cat', str(state/draft_id/'draft.json')]))
        draft['draft_id'] = selected
        (folder/'draft.json').write_text(json.dumps(draft))
        bundle = temporary/'transfer.zip'
        vm.bundle_drafts(source, [selected], bundle)
        apply('import-drafts', vm_import_bundle=str(bundle))
        assert run(['sudo', 'cat', str(state/selected/'draft.json')]) == (folder/'draft.json').read_text()
        apply('import-drafts', expected=1, vm_import_bundle=str(bundle))
        assert run(['systemctl', 'is-active', 'axiom-workbench']) == 'active'
        # A failed controller-side backup verification must prevent import and
        # recover the service, even though stopping it was already necessary.
        blocked = 'b'*32
        blocked_folder = vm.private_directory(source / blocked)
        draft['draft_id'] = blocked
        (blocked_folder/'draft.json').write_text(json.dumps(draft))
        blocked_bundle = temporary/'blocked-transfer.zip'
        vm.bundle_drafts(source, [blocked], blocked_bundle)
        bad_verifier = temporary/'failed-verifier.py'
        bad_verifier.write_text('import sys,runpy\n'
            'if sys.argv[1] == "verify": raise SystemExit("Synthetic backup-verification failure")\n'
            + 'runpy.run_path('+repr(str(ROOT/'scripts/lib/vm_deployment.py'))+',run_name="__main__")\n')
        apply('import-drafts', expected=1, vm_import_bundle=str(blocked_bundle),
              vm_controller_helper=str(bad_verifier))
        assert subprocess.run(['sudo','test','-e',str(state/blocked)]).returncode != 0
        assert run(['systemctl','is-active','axiom-workbench']) == 'active'
        for archive in backups.glob('*.zip'):
            vm.verify_archive(archive)
        recovery = temporary/'recovery'
        vm.restore_backup(next(backups.glob('*.zip')), recovery)
        run(['sudo', 'systemctl', 'restart', 'axiom-workbench'])
        # Main helper retries are exercised by activation; after restart wait through its retry loop.
        import time
        for attempt in range(12):
            result = subprocess.run(['sudo','/usr/bin/python3','/usr/local/lib/axiom/vm_deployment.py','smoke',
                '--port','8766','--environment','/etc/axiom/workbench.env'], capture_output=True)
            if result.returncode == 0:
                break
            time.sleep(1)
        else:
            raise AssertionError('Restart did not recover authenticated Workbench access')
        listeners = run(['ss', '-ltn'])
        assert '127.0.0.1:8766' in listeners and '0.0.0.0:8766' not in listeners
        assert run(['systemctl','is-enabled','axiom-workbench']) == 'enabled'
        print('PASS: install, idempotence, update, rollback, failed activation recovery, draft preservation, import/collision, blocked backup recovery, backup restore, restart and loopback boundary', flush=True)
    finally:
        httpd.shutdown()


if __name__ == '__main__':
    main()
