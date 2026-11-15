"""Private VM deployment utilities. No governance decisions or remote shell input."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import socket
import stat
import subprocess
import tempfile
import zipfile

MAX_ARCHIVE = 512 * 1024 * 1024
DRAFT_ID = re.compile(r"[0-9a-f]{32}")
REVISION = re.compile(r"[0-9a-f]{40}")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def private_directory(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Private directory must not be a symlink")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)
    return path


def regular_bytes(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected a regular file")
    if path.stat().st_size > MAX_ARCHIVE:
        raise ValueError("Private file exceeds archive limit")
    with path.open('rb') as stream:
        data = stream.read(MAX_ARCHIVE + 1)
    if len(data) > MAX_ARCHIVE:
        raise ValueError("Private file exceeds archive limit")
    return data


def write_archive(destination, files):
    """Exclusive private archive; a failed write never looks like a complete backup."""
    destination = Path(destination)
    private_directory(destination.parent)
    manifest = {name: {"sha256": digest(data), "size": len(data)} for name, data in files.items()}
    if sum(len(data) for data in files.values()) > MAX_ARCHIVE:
        raise ValueError("Private archive exceeds 512 MiB; export smaller batches")
    fd, temporary = tempfile.mkstemp(dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as stream, zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
            archive.writestr("manifest.json", json.dumps(manifest, sort_keys=True).encode())
        # link is exclusive and atomic, unlike replace which could overwrite a backup.
        os.link(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    verify_archive(destination)
    return {"sha256": digest(destination.read_bytes()), "files": len(files)}


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [entry.filename for entry in infos]
        if len(names) != len(set(names)) or "manifest.json" not in names:
            raise ValueError("Duplicate entries or missing manifest")
        if sum(entry.file_size for entry in infos) > MAX_ARCHIVE + 1024 * 1024:
            raise ValueError("Private archive exceeds limit")
        for entry in infos:
            name = PurePosixPath(entry.filename)
            mode = entry.external_attr >> 16
            if (name.is_absolute() or ".." in name.parts or "\\" in entry.filename
                    or str(name) != entry.filename or not name.parts
                    or entry.is_dir() or stat.S_ISLNK(mode)
                    or (stat.S_IFMT(mode) not in (0, stat.S_IFREG))):
                raise ValueError("Unsafe archive entry")
        manifest = json.loads(archive.read("manifest.json"))
        if not isinstance(manifest, dict) or set(manifest) != set(names) - {"manifest.json"}:
            raise ValueError("Archive inventory mismatch")
        files = {}
        for name, expected in manifest.items():
            data = archive.read(name)
            if expected != {"sha256": digest(data), "size": len(data)}:
                raise ValueError("Archive checksum mismatch")
            files[name] = data
        return files


def backup(state, config, receipt, unit, destination):
    files = {}
    size = 0
    state = Path(state)
    if state.is_symlink():
        raise ValueError("State directory must not be a symlink")
    if state.exists():
        for path in sorted(state.rglob("*")):
            if path.is_symlink():
                raise ValueError("Symlinks are not supported in VM state backups")
            if path.is_file():
                size += path.stat().st_size
                if size > MAX_ARCHIVE:
                    raise ValueError("Private state exceeds backup limit")
                files["state/" + path.relative_to(state).as_posix()] = regular_bytes(path)
    for name, path in (("workbench.env", config), ("deployment.json", receipt),
                       ("axiom-workbench.service", unit)):
        if Path(path).exists():
            files["config/" + name] = regular_bytes(path)
    return write_archive(destination, files)


def bundle_drafts(source, ids, destination):
    source = Path(source).resolve()
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Select unique draft IDs explicitly")
    files = {}
    for draft_id in ids:
        if not DRAFT_ID.fullmatch(draft_id):
            raise ValueError("Invalid draft ID")
        folder = source / draft_id
        if folder.is_symlink():
            raise ValueError("Draft directory must not be a symlink")
        raw = regular_bytes(folder / "draft.json")
        data = json.loads(raw)
        if data.get("draft_id") != draft_id:
            raise ValueError("Draft ID mismatch")
        files[f"drafts/{draft_id}/draft.json"] = raw
        if data.get("kind") == "source_candidate":
            name = data.get("upload_name", "")
            if not re.fullmatch(r"source\.(md|markdown|pdf|docx)", name):
                raise ValueError("Invalid upload name")
            upload = regular_bytes(folder / name)
            if digest(upload) != data.get("sha256"):
                raise ValueError("Uploaded document checksum mismatch")
            files[f"drafts/{draft_id}/{name}"] = upload
    return write_archive(destination, files)


def import_drafts(archive, state, schema):
    import jsonschema
    files = verify_archive(archive)
    groups = {}
    for name, raw in files.items():
        parts = PurePosixPath(name).parts
        if len(parts) != 3 or parts[0] != "drafts" or not DRAFT_ID.fullmatch(parts[1]):
            raise ValueError("Not a draft transfer bundle")
        groups.setdefault(parts[1], {})[parts[2]] = raw
    if not groups:
        raise ValueError("Empty draft transfer bundle")
    state = private_directory(state)
    schema = json.loads(regular_bytes(schema))
    for draft_id, content in groups.items():
        if (state / draft_id).exists() or (state / draft_id).is_symlink():
            raise ValueError("Draft collision; nothing imported")
        if "draft.json" not in content:
            raise ValueError("Missing draft metadata")
        data = json.loads(content["draft.json"])
        jsonschema.validate(data, schema)
        if data["draft_id"] != draft_id:
            raise ValueError("Draft ID mismatch")
        expected = {"draft.json"}
        if data["kind"] == "source_candidate":
            expected.add(data["upload_name"])
            if digest(content.get(data["upload_name"], b"")) != data["sha256"]:
                raise ValueError("Uploaded document checksum mismatch")
        if set(content) != expected:
            raise ValueError("Unexpected files in draft bundle")
    # Validate the complete batch before making anything visible.
    temporary = Path(tempfile.mkdtemp(prefix=".import-", dir=state))
    committed = []
    try:
        for draft_id, content in groups.items():
            folder = private_directory(temporary / draft_id)
            for name, raw in content.items():
                target = folder / name
                target.write_bytes(raw)
                os.chmod(target, 0o600)
        for draft_id in groups:
            os.rename(temporary / draft_id, state / draft_id)
            committed.append(state / draft_id)
    except BaseException:
        for folder in committed:
            shutil.rmtree(folder)
        raise
    finally:
        shutil.rmtree(temporary)
    return {"imported": sorted(groups)}


def restore_backup(archive, destination):
    """Recovery rehearsal only: never overwrite an existing destination."""
    files = verify_archive(archive)
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError("Recovery destination must not exist")
    for name in files:
        if PurePosixPath(name).parts[0] not in {"state", "config"}:
            raise ValueError("Not a VM backup")
    destination.mkdir(mode=0o700, parents=True)
    for name, data in files.items():
        target = destination / name
        private_directory(target.parent)
        target.write_bytes(data)
        os.chmod(target, 0o600)
    return {"restored_files": len(files)}


def smoke(port, environment, logout=False):
    """Verify real authentication and data reads without printing credentials/content."""
    values = dict(line.split("=", 1) for line in regular_bytes(environment).decode().splitlines()
                  if line and not line.startswith("#"))
    key = values["AXIOM_WORKBENCH_KEY"]
    host = f"127.0.0.1:{port}"
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    try:
        connection.request("GET", "/api/state", headers={"Host": host})
        response = connection.getresponse()
        response.read()
        if response.status != 401:
            raise ValueError("Unauthenticated API boundary failed")
        connection.request("POST", "/api/login", json.dumps({"key": key}),
                           {"Host": host, "Origin": "http://" + host,
                            "Content-Type": "application/json"})
        response = connection.getresponse()
        cookie = response.getheader("Set-Cookie", "").split(";", 1)[0]
        response.read()
        if response.status != 200 or not cookie:
            raise ValueError("Workbench login failed")
        connection.request("GET", "/api/state", headers={"Host": host, "Cookie": cookie})
        response = connection.getresponse()
        data = json.loads(response.read())
        if response.status != 200 or "csrf" not in data:
            raise ValueError("Authenticated state read failed")
        # The current single-maintainer logout clears all sessions. Never log an
        # existing maintainer out during an otherwise unchanged installation.
        if logout:
            connection.request("POST", "/api/logout", "{}", {"Host": host, "Cookie": cookie,
                               "Origin": "http://" + host, "Content-Type": "application/json",
                               "X-CSRF-Token": data["csrf"]})
            response = connection.getresponse()
            response.read()
            if response.status != 200:
                raise ValueError("Workbench logout failed")
    finally:
        connection.close()
    return {"authenticated_read": "pass", "anonymous_boundary": "pass"}


def preflight(port, reserve_bytes, base):
    system = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            system[key] = value.strip('"')
    if system.get("ID") != "ubuntu" or system.get("VERSION_ID") != "24.04":
        raise ValueError("Only Ubuntu 24.04 is supported by this profile")
    parent = Path(base)
    while not parent.exists():
        parent = parent.parent
    used_by_state = 0
    state = Path(base) / "repository/.local/governance-workbench"
    if state.exists():
        used_by_state = sum(p.stat().st_size for p in state.rglob("*") if p.is_file())
    # Reserve includes staging/download budget plus two uncompressed state copies.
    required = reserve_bytes + 2 * used_by_state + 2 * 1024**3
    if shutil.disk_usage(parent).free < required:
        raise ValueError("Insufficient free space for staging, backups and 8 GiB reserve")
    active = subprocess.run(["systemctl", "is-active", "--quiet", "axiom-workbench"], check=False).returncode == 0
    with socket.socket() as probe:
        occupied = probe.connect_ex(("127.0.0.1", port)) == 0
    if occupied and not active:
        raise ValueError("Workbench port is occupied by another service")
    return {"ubuntu": "24.04", "service_active": active, "required_bytes": required}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("verify", "restore", "import"):
        p = sub.add_parser(action)
        p.add_argument("--archive", required=True)
        if action == "restore":
            p.add_argument("--destination", required=True)
        if action == "import":
            p.add_argument("--state", required=True)
            p.add_argument("--schema", required=True)
    p = sub.add_parser("bundle")
    p.add_argument("--source", required=True)
    p.add_argument("--ids", nargs="+", required=True)
    p.add_argument("--destination", required=True)
    p = sub.add_parser("backup")
    for name in ("state", "config", "receipt", "unit", "destination"):
        p.add_argument("--" + name, required=True)
    p = sub.add_parser("smoke")
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--environment", required=True)
    p.add_argument("--logout", action="store_true", help="Only after restart; current logout clears all sessions")
    p = sub.add_parser("preflight")
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--reserve-bytes", type=int, default=8 * 1024**3)
    args = vars(parser.parse_args(argv))
    action = args.pop("action")
    if action == "verify":
        result = {"verified_files": len(verify_archive(args["archive"]))}
    else:
        operation = {"bundle": bundle_drafts, "backup": backup, "restore": restore_backup,
                     "import": import_drafts, "smoke": smoke, "preflight": preflight}[action]
        result = operation(**args)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never propagate parser/source/credential text into Ansible or journal logs.
        raise SystemExit("VM operation failed; inspect private inputs and operator guide")
