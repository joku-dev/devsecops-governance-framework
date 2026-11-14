#!/usr/bin/env python3
"""Real systemd credentials/UID/queue test ONLY on a marked disposable Ubuntu host.

Uses paused fake App credentials: no GitHub calls and no production keys.
The API, shadow comparison and publisher recovery are covered by deterministic tests.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[2]


def run(*args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-disposable-host', action='store_true', required=True)
    parser.add_argument('--restore-orbstack-hardening', action='store_true',
                        help='Override global OrbStack service exceptions for these disposable fixture units only')
    options = parser.parse_args()
    if os.geteuid() != 0 or (os.environ.get('GITHUB_ACTIONS') != 'true' and not Path('/run/axiom-disposable-integration').is_file()):
        raise SystemExit('Requires root on explicitly marked disposable host; never the Proxmox target')
    if 'VERSION_ID="24.04"' not in Path('/etc/os-release').read_text():
        raise SystemExit('Requires Ubuntu 24.04 with real systemd')
    if options.restore_orbstack_hardening and not Path('/run/systemd/system/service.d/zzz-lxc-service.conf').exists():
        raise SystemExit('The explicit OrbStack option requires its known global service exception file')
    credentials = [Path('/etc/axiom/consumer-intake.json'), Path('/etc/axiom/consumer-reader.pem')]
    if any(path.exists() for path in credentials):
        raise SystemExit('Refusing existing consumer configuration or credentials')
    os.umask(0o077)
    receipt = json.loads(Path('/etc/axiom/deployment.json').read_text())
    runtime = Path('/srv/axiom/venvs') / receipt['current_revision']
    run('id', 'axiom')
    if run('id', 'axiom-intake', check=False).returncode:
        run('useradd', '--system', '--no-create-home', '--shell', '/usr/sbin/nologin', 'axiom-intake')
    temporary = Path(tempfile.mkdtemp(prefix='axiom-consumer-linux-', dir='/srv'))
    temporary.chmod(0o755)
    source = temporary / 'repository'
    shutil.copytree(ROOT / 'scripts', source / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
    for path in source.rglob('*'):
        path.chmod(0o755 if path.is_dir() else 0o644)
    source.chmod(0o755)
    operations, projection = temporary / 'private', temporary / 'view'
    operations.mkdir(mode=0o700)
    projection.mkdir(mode=0o750)
    run('chown', 'axiom-intake:axiom-intake', str(operations))
    run('chown', 'axiom-intake:axiom', str(projection))
    projection.chmod(0o2750)
    credentials[0].write_text(json.dumps({'mode': 'paused'}))
    run('openssl', 'genrsa', '-out', str(credentials[1]), '2048')
    for path in credentials:
        path.chmod(0o600)
    units = []
    previous = {}
    active = {}
    overrides = []
    environment = Environment(undefined=StrictUndefined, keep_trailing_newline=True, trim_blocks=True)
    try:
        workbench_template = environment.from_string((ROOT / 'infra/ansible/templates/axiom-workbench.service.j2').read_text())
        for supported in (True, False):
            rendered = workbench_template.render(vm_user='axiom', vm_repo=str(source), vm_venv=str(runtime),
                vm_environment='/etc/axiom/workbench.env', vm_port=8766, vm_state='/private-workbench',
                vm_consumer_support={'stat': {'exists': supported}}, vm_consumer_projection=str(projection))
            assert 'Restart=on-failure' in rendered.splitlines()
            command = next(line for line in rendered.splitlines() if line.startswith('ExecStart='))
            assert command.endswith(str(projection) if supported else '8766')
        for operation in ('poll', 'work'):
            for kind in ('service', 'timer'):
                name = f'axiom-consumer-{operation}.{kind}'
                path = Path('/etc/systemd/system') / name
                previous[path] = path.read_bytes() if path.exists() else None
                active[name] = run('systemctl', 'is-active', '--quiet', name, check=False).returncode == 0
                run('systemctl', 'stop', name, check=False)
                template = (ROOT / f'infra/ansible/templates/axiom-consumer.{kind}.j2').read_text()
                rendered = environment.from_string(template).render(
                    consumer_operation=operation, vm_repo=str(source), vm_venv=str(runtime),
                    vm_consumer_user='axiom-intake', vm_user='axiom', vm_consumer_root=str(operations),
                    vm_consumer_projection=str(projection),
                    vm_consumer_credentials={'results': [{'item': 'reader', 'stat': {'exists': True}}]})
                path.write_text(rendered)
                path.chmod(0o644)
                units.append(name)
                if kind == 'service' and options.restore_orbstack_hardening:
                    # The global container exception clears credentials and hardening.
                    # Reapply the actual unit settings only to our marked test services.
                    directory = path.parent / (name + '.d')
                    directory.mkdir(exist_ok=True)
                    override = directory / 'zzzz-axiom-disposable-test.conf'
                    if override.exists():
                        raise ValueError('Refusing an existing test override')
                    override.write_text('[Service]\nExecStart=\n' + rendered)
                    overrides.append(override)
        run('systemctl', 'daemon-reload')
        run('systemd-analyze', 'verify', *[str(path) for path in previous])
        assert run('systemctl', 'show', '--value', '-p', 'ProtectSystem', 'axiom-consumer-poll.service').stdout.strip() == 'strict'
        assert run('systemctl', 'show', '--value', '-p', 'NoNewPrivileges', 'axiom-consumer-poll.service').stdout.strip() == 'yes'
        run('systemctl', 'start', 'axiom-consumer-poll.service')
        assert (operations / 'queue.sqlite3').is_file()
        view = json.loads((projection / 'consumers.json').read_text())
        assert view['mode'] == 'paused' and view['accepted'] is None
        seed = ("import sys;sys.path.insert(0,sys.argv[1]);from lib.consumer_intake_store import Store;"
                "s=Store(sys.argv[2]);s.discover('synthetic/consumer',{'id':1,'run_attempt':1,'status':'completed'});s.close()")
        run('runuser', '-u', 'axiom-intake', '--', str(runtime / 'bin/python'), '-c', seed,
            str(source / 'scripts'), str(operations))
        run('systemctl', 'start', 'axiom-consumer-work.service')
        status = run('runuser', '-u', 'axiom-intake', '--', str(runtime / 'bin/python'),
                     str(source / 'scripts/consumer_intake.py'), 'status', '--root', str(operations))
        assert json.loads(status.stdout)['counts'] == {'queued': 1}
        assert run('runuser', '-u', 'axiom', '--', 'cat', str(operations / 'queue.sqlite3'), check=False).returncode != 0
        assert run('runuser', '-u', 'axiom', '--', 'cat', str(credentials[1]), check=False).returncode != 0
        assert run('runuser', '-u', 'axiom', '--', 'cat', str(projection / 'consumers.json')).returncode == 0
        assert run('runuser', '-u', 'axiom', '--', 'touch', str(projection / 'forbidden'), check=False).returncode != 0
        assert (projection / 'consumers.json').stat().st_mode & 0o777 == 0o640
        for operation in ('poll', 'work'):
            run('systemctl', 'start', f'axiom-consumer-{operation}.timer')
            run('systemctl', 'is-active', '--quiet', f'axiom-consumer-{operation}.timer')
        print('PASS: real systemd credentials, isolated UIDs, queue persistence, readonly projection and both timers')
    finally:
        for name in reversed(units):
            run('systemctl', 'stop', name, check=False)
        for path in overrides:
            path.unlink()
            if not list(path.parent.iterdir()):
                path.parent.rmdir()
        for path, data in previous.items():
            if data is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(data)
        for path in credentials:
            path.unlink(missing_ok=True)
        run('systemctl', 'daemon-reload')
        for name, was_active in active.items():
            if was_active:
                run('systemctl', 'start', name, check=False)
        shutil.rmtree(temporary)


if __name__ == '__main__':
    main()
