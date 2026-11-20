"""Finite inert security/release trees; labels never select current source paths."""
from pathlib import PurePosixPath

from lib.portable.contracts import canonical_digest
from lib.result_bytes import strict_json
from lib.validation_files import relative

MAX_FILES = 10000
MAX_BYTES = 512 * 1024**2
MAX_FILE = 64 * 1024**2


class RetainedTree:
    def __init__(self, label, files, directories):
        if (not isinstance(label, str) or not PurePosixPath(label).is_absolute()
                or str(PurePosixPath(label)) != label or '..' in PurePosixPath(label).parts
                or len(label) > 8192 or any(ord(c) < 32 for c in label)):
            raise ValueError('retained_security_tree_label_invalid')
        if (not isinstance(files, dict) or len(files) > MAX_FILES or not isinstance(directories, list)
                or len(directories) > MAX_FILES or directories != sorted(set(directories))):
            raise ValueError('retained_security_tree_members_invalid')
        self.label = label
        self.files = dict(files)
        self.directories = set(directories)
        if '' not in self.directories or set(files) & self.directories:
            raise ValueError('retained_security_tree_directories_invalid')
        for name in {*files, *self.directories} - {''}:
            relative(name)
            if len(name.encode()) > 8192:
                raise ValueError('retained_security_tree_name_budget')
            parents = {str(p) for p in PurePosixPath(name).parents if str(p) != '.'}
            if not parents <= self.directories:
                raise ValueError('retained_security_tree_parent_missing')
        if (any(not isinstance(raw, bytes) or len(raw) > MAX_FILE for raw in files.values())
                or sum(map(len, files.values())) > MAX_BYTES):
            raise ValueError('retained_security_tree_byte_budget')

    def children(self, prefix=''):
        start = prefix + '/' if prefix else ''
        return {name[len(start):].split('/')[0] for name in {*self.files, *self.directories}
                if name.startswith(start) and name != prefix}

    def read(self, name, limit=MAX_FILE):
        if name not in self.files or len(self.files[name]) > limit:
            raise ValueError('retained_security_tree_file_missing_or_oversize')
        return self.files[name]

    def json(self, name, limit=MAX_FILE):
        return strict_json(self.read(name, limit))

    def inputs(self, prefix, expected):
        from lib.validation_application import descriptors
        if prefix not in self.directories:
            raise ValueError('retained_security_input_directory_missing')
        files = {name[len(prefix) + 1:]: raw for name, raw in self.files.items() if name.startswith(prefix + '/')}
        if canonical_digest(descriptors(files)) != canonical_digest(expected):
            raise ValueError('retained_security_input_bytes_changed')
        return files

    def child_directories(self, prefix):
        return {name[len(prefix) + 1:] for name in self.directories if name.startswith(prefix + '/')}

    def path(self, name):
        return str(PurePosixPath(self.label) / name)
