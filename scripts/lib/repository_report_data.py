"""Original report grammar over the captured dataset's explicit path namespace."""
from fnmatch import fnmatchcase
import json
from pathlib import PurePosixPath

import yaml

from lib.source_document_text import SourceDocumentExtractionError, extract_source_document_bytes


class RepositoryReportData:
    def __init__(self, dataset, *, raw_yaml=False):
        self.dataset, self.root, self.raw_yaml = dataset, dataset.root, raw_yaml
        self.files = frozenset(dataset.files)
        self.directories = set(dataset.directories) - {''}

    def relative(self, path):
        value = self.dataset.namespace.path(path)
        name = self.dataset.namespace.relative(value.value)
        return self.dataset.checked(name)

    def exists(self, path):
        name = self.relative(path)
        return name in self.files or name in self.directories

    def is_file(self, path): return self.relative(path) in self.files

    def is_dir(self, path): return self.relative(path) in self.directories

    def iterdir(self, path):
        name = self.relative(path)
        if name not in self.directories:
            raise ValueError('report_directory_missing')
        return [self.root / child for child in sorted(self.files | self.directories)
                if PurePosixPath(child).parent.as_posix() == name]

    def glob(self, path, pattern):
        if '/' in pattern or '\\' in pattern or '**' in pattern:
            raise ValueError('unsupported_report_glob')
        if self.relative(path) not in self.directories:
            return []
        return [value for value in self.iterdir(path) if fnmatchcase(value.name, pattern)]

    def raw(self, path): return self.dataset.read(self.relative(path))

    def json(self, path): return json.loads(self.raw(path).decode('utf-8'))

    def yaml(self, path):
        value = yaml.safe_load(self.raw(path).decode('utf-8'))
        return value if self.raw_yaml else value or {}

    def extract(self, path):
        if not self.is_file(path):
            raise SourceDocumentExtractionError('source document does not exist or is not a file')
        return extract_source_document_bytes(self.relative(path), self.raw(path))
