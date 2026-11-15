"""Local Git binding for explicitly selected DCR product-source inputs.

An enclosing checkout never supplies a candidate generation's commit. A clean
index alone is insufficient: source bytes are checked even with skip-worktree.
This is technical provenance, never human review or governance authorization.
"""
import hashlib
from pathlib import Path
import re

from lib.functional_parity import git_read
from lib.v2_boundary import safe_source


def git_head(root):
    root = Path(root).resolve()
    try:
        top = Path(git_read(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
        if top != root:
            return None
        head = git_read(root, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
        return head if re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', head) else None
    except (OSError, ValueError):
        return None


def repository_revision(root):
    root = Path(root).resolve()
    head = git_head(root)
    if head is None:
        return None
    try:
        if git_read(root, 'status', '--porcelain', '--untracked-files=all').strip():
            return None
        entries = git_read(root, 'ls-tree', '-r', '-z', head, '--', 'docs', 'model', 'schemas')
        for entry in entries.split(b'\0'):
            if not entry:
                continue
            metadata, name = entry.split(b'\t', 1)
            mode, kind, blob = metadata.decode().split()
            path = safe_source(root, name.decode())
            if kind != 'blob' or mode not in ('100644', '100755') or not path.is_file():
                return None
            raw = path.read_bytes()
            digest = hashlib.sha1 if len(blob) == 40 else hashlib.sha256
            if digest(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != blob:
                return None
        return head if git_head(root) == head else None
    except (OSError, ValueError):
        return None


def require_committed_source(root, expected=None):
    head = repository_revision(root)
    if head is None or (expected is not None and head != expected):
        raise ValueError('clean_committed_dcr_source_required')
    return head
