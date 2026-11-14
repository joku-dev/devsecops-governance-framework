#!/usr/bin/env python3
"""One-host Ansible entrypoint. Private configuration and backups stay outside Git."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

from lib.vm_deployment import bundle_drafts, private_directory, REVISION

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/joku-dev/devsecops-governance-framework.git"
ACTIONS = ("check", "install", "update", "status", "rollback", "import-drafts")


def configuration(path):
    path = Path(path).expanduser()
    if path.stat().st_mode & 0o077:
        raise ValueError("Private configuration must have permissions 0600")
    data = json.loads(path.read_text())
    allowed = {"host", "user", "ssh_port", "identity_file", "backup_root"}
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError("Unknown private configuration fields")
    for name in ("host", "user"):
        if not isinstance(data.get(name), str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]*", data[name]):
            raise ValueError("Invalid host or SSH user")
    port = data.get("ssh_port", 22)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Invalid SSH port")
    data["ssh_port"] = port
    if data.get("identity_file"):
        identity = Path(data["identity_file"]).expanduser().resolve(strict=True)
        if not identity.is_file() or identity.stat().st_mode & 0o077:
            raise ValueError("SSH identity must be a private regular file")
        data["identity_file"] = str(identity)
    data["backup_root"] = str(Path(data.get("backup_root", "~/.local/state/axiom-deployment")).expanduser().resolve())
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=ACTIONS)
    parser.add_argument("--config", required=True, help="Private 0600 JSON file; see example inventory")
    parser.add_argument("--revision", help="Full approved 40-character commit SHA for install/update")
    parser.add_argument("--source", type=Path, help="Stopped local workbench state directory for import")
    parser.add_argument("--draft-id", action="append", default=[], help="Explicit draft ID; repeat to select more")
    parser.add_argument("--ask-become-pass", action="store_true", help="Prompt once for sudo; never save the password")
    args = parser.parse_args(argv)
    if args.action in {"install", "update"}:
        if not args.revision or not REVISION.fullmatch(args.revision):
            parser.error("install/update require --revision with a full lowercase commit SHA")
    elif args.revision:
        parser.error("--revision is only accepted for install/update")
    if args.action == "import-drafts":
        if not args.source or not args.draft_id:
            parser.error("import-drafts requires --source and explicit --draft-id selections")
    elif args.source or args.draft_id:
        parser.error("Draft arguments are only accepted for import-drafts")
    config = configuration(args.config)
    backup_root = private_directory(config["backup_root"])
    deployment_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:12]
    private_directory(backup_root / "logs")
    private_directory(backup_root / "backups")
    lock = backup_root / "deployment.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError("A deployment lock exists; inspect the prior run before removing it")
    with os.fdopen(fd, 'w') as lockfile:
        json.dump({'pid': os.getpid(), 'deployment_id': deployment_id}, lockfile)
    try:
        with tempfile.TemporaryDirectory(prefix="axiom-deploy-", dir=backup_root) as temporary:
            temporary = Path(temporary)
            host = {"ansible_host": config["host"], "ansible_user": config["user"],
                    "ansible_port": config["ssh_port"], "ansible_python_interpreter": "/usr/bin/python3"}
            if config.get("identity_file"):
                host["ansible_ssh_private_key_file"] = config["identity_file"]
            inventory = {"all": {"children": {"axiom": {"hosts": {"axiom_vm": host}}}}}
            variables = {"vm_action": args.action, "vm_revision": args.revision or "",
                         "vm_deployment_id": deployment_id, "vm_repository_url": REPOSITORY,
                         "vm_controller_backups": str(backup_root / "backups"),
                         "vm_controller_helper": str(ROOT / "scripts/lib/vm_deployment.py")}
            if args.action == "import-drafts":
                transfer = temporary / "draft-transfer.zip"
                bundle_drafts(args.source, args.draft_id, transfer)
                variables["vm_import_bundle"] = str(transfer)
            for name, value in (("inventory.json", inventory), ("variables.json", variables)):
                target = temporary / name
                target.write_text(json.dumps(value))
                target.chmod(0o600)
            executable = Path(sys.executable).parent / "ansible-playbook"
            if not executable.is_file():
                raise ValueError("Use scripts/deploy_vm.sh with the pinned controller environment")
            playbook = "check.yml" if args.action in {"check", "status"} else "site.yml"
            command = [str(executable), "-i", str(temporary / "inventory.json"),
                       str(ROOT / "infra/ansible" / playbook), "--limit", "axiom",
                       "--extra-vars", "@" + str(temporary / "variables.json")]
            if args.action in {"check", "status"}:
                command.append("--check")
            if args.ask_become_pass:
                command.append("--ask-become-pass")
            environment = dict(os.environ, ANSIBLE_CONFIG=str(ROOT / "infra/ansible/ansible.cfg"),
                               ANSIBLE_HOST_KEY_CHECKING="True", ANSIBLE_NOCOLOR="1",
                               ANSIBLE_HOME=str(temporary / "ansible"),
                               ANSIBLE_LOCAL_TEMP=str(temporary / "ansible-tmp"))
            result = subprocess.run(command, env=environment, check=False)
            receipt = {"deployment_id": deployment_id, "action": args.action,
                       "requested_revision": args.revision, "host": config["host"],
                       "ansible_exit_code": result.returncode,
                       "completed_at": datetime.now(timezone.utc).isoformat()}
            log = backup_root / "logs" / (deployment_id + ".json")
            log.write_text(json.dumps(receipt, indent=2) + "\n")
            log.chmod(0o600)
            return result.returncode
    finally:
        lock.unlink()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, TypeError):
        raise SystemExit("Deployment input/setup failed; check private configuration, permissions and operator guide")
