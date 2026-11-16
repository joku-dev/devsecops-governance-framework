"""Read inert report inputs and committed membership without restoring code."""
from datetime import timezone
from fnmatch import fnmatchcase
from pathlib import Path

import yaml

from lib.result_bytes import safe_bytes, strict_json
from lib.result_snapshot_store import explicit_time
from lib.v2_boundary import safe_source


def report_time(at):
    return explicit_time(at).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


class ReportData:
    def __init__(self, root, membership):
        self.root = Path(root).resolve()
        self.files = frozenset(membership)
        self.directories = set()
        for name, row in membership.items():
            safe_source(self.root, name)
            if row['mode'] not in ('100644', '100755'):
                raise ValueError('unsafe_report_member')
            self.directories.update(p.as_posix() for p in Path(name).parents if p != Path('.'))

    def relative(self, path):
        name = Path(path).relative_to(self.root).as_posix()
        safe_source(self.root, name)
        return name

    def exists(self, path):
        name = self.relative(path)
        return name in self.files or name in self.directories

    def is_file(self, path):
        return self.relative(path) in self.files

    def iterdir(self, path):
        name = self.relative(path)
        if name not in self.directories:
            raise ValueError('report_directory_missing')
        return [self.root / child for child in sorted(self.files | self.directories)
                if Path(child).parent.as_posix() == name]

    def glob(self, path, pattern):
        if '/' in pattern or '\\' in pattern or '**' in pattern:
            raise ValueError('unsupported_report_glob')
        name = self.relative(path)
        if name not in self.directories:
            return []
        return [p for p in self.iterdir(path) if fnmatchcase(p.name, pattern)]

    def raw(self, path):
        name = self.relative(path)
        if name not in self.files:
            raise ValueError('uncommitted_report_input')
        return safe_bytes(safe_source(self.root, name), limit=16 * 1024**2)

    def yaml(self, path):
        return yaml.safe_load(self.raw(path)) or {}

    def json(self, path):
        return strict_json(self.raw(path))
