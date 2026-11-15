#!/usr/bin/env python3
"""Real portable systemd credential isolation on a disposable Ubuntu runner only."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from jinja2 import Environment,StrictUndefined

ROOT=Path(__file__).resolve().parents[2]


def run(*args,check=True):return subprocess.run(args,check=check,capture_output=True,text=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-disposable-host',required=True,action='store_true');parser.parse_args()
    if (os.geteuid()!=0 or os.environ.get('GITHUB_ACTIONS')!='true'
            or 'VERSION_ID="24.04"' not in Path('/etc/os-release').read_text()):
        raise SystemExit('Requires root on a disposable GitHub Ubuntu runner, never the target VM')
    if Path('/etc/axiom/portable-consumer-intake.json').exists():raise SystemExit('Refusing existing portable configuration')
    receipt=json.loads(Path('/etc/axiom/deployment.json').read_text())
    runtime=Path('/srv/axiom/venvs')/receipt['current_revision']
    # The independent legacy smoke runtime contains only stdlib; add exact locked imports.
    run('runuser','-u','axiom','--',str(runtime/'bin/python'),'-m','pip','install','--require-hashes',
        '-r',str(ROOT/'requirements-validation.lock'))
    os.umask(0o077)
    temporary=Path(tempfile.mkdtemp(prefix='axiom-portable-linux-',dir='/srv'));temporary.chmod(0o755)
    source=temporary/'repository'
    for directory in ('scripts','config','schemas'):
        shutil.copytree(ROOT/directory,source/directory,ignore=shutil.ignore_patterns('__pycache__'))
    for path in source.rglob('*'):path.chmod(0o755 if path.is_dir() else 0o644)
    source.chmod(0o755)
    run('git','init','--template=','-q',str(source))
    run('git','-C',str(source),'-c','user.name=Synthetic fixture','-c','user.email=fixture@localhost',
        '-c','commit.gpgsign=false','commit','--allow-empty','-qm','Synthetic disposable service fixture')
    for path in (source/'.git').rglob('*'):path.chmod(0o755 if path.is_dir() else 0o644)
    (source/'.git').chmod(0o755)
    private,view=temporary/'private',temporary/'view';private.mkdir(mode=0o700);view.mkdir(mode=0o750)
    run('chown','axiom-intake:axiom-intake',str(private));run('chown','axiom-intake:axiom',str(view));view.chmod(0o2750)
    credentials=temporary/'credentials';credentials.mkdir(mode=0o700)
    for name in ('reader-fixture','publisher-fixture'):
        (credentials/name).write_text('synthetic-'+name);(credentials/name).chmod(0o600)
    config=Path('/etc/axiom/portable-consumer-intake.json')
    config.write_text(json.dumps({'schema_version':1,'mode':'paused','registry':str(source/'config/portable-consumer-profiles.json'),
        'credentials_directory':'systemd','request_budget':30,'node_id':'f'*32}));config.chmod(0o600)
    # Assert the production private-file ACL validator and phase credential separation inside
    # the actual systemd credential mount, before calling the real production CLI main().
    entry=source/'scripts/portable_fixture_entry.py'
    entry.write_text('import os,sys\nfrom pathlib import Path\nfrom lib.private_credentials import check_private_file\n'
        'credentials=Path(os.environ["CREDENTIALS_DIRECTORY"])\n'
        'for path in credentials.iterdir(): check_private_file(path)\n'
        'assert (credentials/"reader-fixture").is_file()\n'
        'assert (credentials/"publisher-fixture").is_file() == (sys.argv[1]=="work")\n'
        'from portable_consumer_intake import main\nraise SystemExit(main())\n');entry.chmod(0o644)
    template=Environment(undefined=StrictUndefined).from_string((ROOT/'infra/ansible/templates/axiom-consumer.service.j2').read_text())
    units=[]
    try:
        for operation in ('poll','work'):
            name='axiom-portable-fixture-'+operation+'.service';path=Path('/etc/systemd/system')/name
            if path.exists():raise ValueError('Refusing existing fixture unit')
            text=template.render(consumer_operation=operation,vm_consumer_engine='portable-v1',vm_repo=str(source),
                vm_venv=str(runtime),vm_consumer_user='axiom-intake',vm_user='axiom',vm_consumer_root=str(private),
                vm_consumer_projection=str(view),vm_portable_credentials={'files':[{'path':str(p)} for p in credentials.iterdir()]})
            path.write_text(text.replace('/scripts/portable_consumer_intake.py','/scripts/portable_fixture_entry.py'))
            path.chmod(0o644);units.append(path)
        run('systemctl','daemon-reload');run('systemd-analyze','verify',*[str(path) for path in units])
        for path in units:
            run('systemctl','start',path.name)
            assert run('systemctl','show','--value','-p','Result',path.name).stdout.strip()=='success'
        projection=json.loads((view/'consumers.json').read_text())
        assert projection['mode']=='paused' and projection['engine']=='portable-v1' and projection['accepted'] is None
        assert run('runuser','-u','axiom','--','cat',str(view/'consumers.json')).returncode==0
        assert run('runuser','-u','axiom','--','cat',str(private/'queue.sqlite3'),check=False).returncode!=0
        assert run('runuser','-u','axiom','--','cat',str(credentials/'publisher-fixture'),check=False).returncode!=0
        assert run('runuser','-u','axiom','--','touch',str(view/'forbidden'),check=False).returncode!=0
        print('PASS: portable production CLI under systemd, reader/publisher isolation, private v2 queue, public projection')
    except Exception:
        for path in units:print(run('journalctl','--no-pager','-n','40','-u',path.name,check=False).stdout)
        raise
    finally:
        for path in units:run('systemctl','stop',path.name,check=False);path.unlink()
        config.unlink();run('systemctl','daemon-reload');shutil.rmtree(temporary)


if __name__=='__main__':main()
