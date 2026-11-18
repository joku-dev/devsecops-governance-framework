"""Inert captured data plus ordered generator effects, without native writes."""
from copy import deepcopy
import base64
import errno
import hashlib
from pathlib import PurePosixPath

from lib import repository_capture as contract
from lib.repository_paths import RepositoryPaths
from lib.validation_files import MAX_FILE, MAX_FILES, MAX_TOTAL


class RepositoryDataset:
    def __init__(self, manifest, files, commit, *, append_effect):
        if not callable(append_effect):
            raise ValueError('repository_effect_journal_required')
        contract.check_capture(manifest, files, commit, revision=manifest['revision'])
        self.manifest = deepcopy(manifest)
        self.files = {}
        def retain(directory):
            for child in manifest['directories'][directory]:
                name = '/'.join(filter(None, (directory, child)))
                if name in files:self.files[name] = files[name]
                else:retain(name)
        retain('')
        self.modes = {name: row['mode'] for name, row in manifest['files'].items()}
        self.directories = deepcopy(manifest['directories'])
        self.append_effect = append_effect
        self.contents = {}
        self.namespace = RepositoryPaths(manifest['source_root'], self)
        self.root = self.namespace.root

    def checked(self, name):
        if name and not contract.admitted(name, self.manifest['inventory']):
            raise ValueError('repository_input_reference_outside_capture_scope')
        return name

    def label(self, name):
        return str(self.root / name) if name else str(self.root)

    def stat(self, name):
        self.checked(name)
        if name in self.files:
            return {'kind': 'file', 'bytes': len(self.files[name]),
                    'mode': 0o100755 if self.modes[name] == '100755' else 0o100644}
        if name in self.directories:
            return {'kind': 'directory', 'bytes': 0, 'mode': 0o40700}
        return None

    def parent(self, name):
        path = PurePosixPath(name)
        parent = '' if str(path.parent) == '.' else str(path.parent)
        parts = PurePosixPath(parent).parts
        for index in range(1, len(parts) + 1):
            prefix = '/'.join(parts[:index])
            if prefix in self.files:
                raise NotADirectoryError(errno.ENOTDIR, 'Not a directory', self.label(name))
            if prefix not in self.directories:
                raise FileNotFoundError(errno.ENOENT, 'No such file or directory', self.label(name))
        return parent

    def read(self, name):
        self.checked(name)
        if name in self.directories:
            raise IsADirectoryError(errno.EISDIR, 'Is a directory', self.label(name))
        self.parent(name)
        try:
            return self.files[name]
        except KeyError:
            raise FileNotFoundError(errno.ENOENT, 'No such file or directory', self.label(name)) from None

    def entries(self, name):
        self.checked(name)
        if name in self.files:
            raise NotADirectoryError(errno.ENOTDIR, 'Not a directory', self.label(name))
        if name not in self.directories:
            self.parent(name)
            raise FileNotFoundError(errno.ENOENT, 'No such file or directory', self.label(name))
        return [{'name': child, **self.stat('/'.join(filter(None, (name, child))))}
                for child in self.directories[name]]

    def output(self, name):
        contract.path_name(name)
        if contract.private_name(name) or PurePosixPath(name).parts[0] != 'generated':
            raise ValueError('repository_generator_write_outside_output_scope')
        return name

    def effect(self, request, callback):
        self.append_effect({'phase': 'intent', 'effect': request})
        try:
            result = callback()
        except BaseException as error:
            self.append_effect({'phase': 'incomplete', 'effect': request, 'error_type': type(error).__name__})
            raise
        self.append_effect({'phase': 'completed', 'effect': request, 'result': result})
        return result

    def mkdir(self, name, *, parents=True, exist_ok=True):
        self.output(name)
        if type(parents) is not bool or type(exist_ok) is not bool:
            raise ValueError('explicit_repository_mkdir_options_required')
        def perform():
            created = []
            def create(path, recursive, existing):
                if path in self.files or path in self.directories and not existing:
                    raise FileExistsError(errno.EEXIST, 'File exists', self.label(path))
                if path in self.directories:
                    return
                parent = '' if str(PurePosixPath(path).parent) == '.' else str(PurePosixPath(path).parent)
                if parent not in self.directories:
                    try:
                        self.parent(path)
                    except FileNotFoundError:
                        if not recursive:
                            raise
                        create(parent, True, True)
                if len(self.files) + len(self.directories) >= MAX_FILES:
                    raise ValueError('repository_dataset_membership_budget')
                self.directories[path] = []
                self.directories[parent].append(PurePosixPath(path).name)
                created.append(path)
            create(name, parents, exist_ok)
            return {'directories_created': created}
        return self.effect({'operation': 'mkdir', 'path': name, 'parents': parents, 'exist_ok': exist_ok}, perform)

    def write(self, name, raw):
        self.output(name)
        if type(raw) is not bytes or len(raw) > MAX_FILE:
            raise ValueError('repository_dataset_file_budget')
        request = {'operation': 'write-bytes', 'path': name, 'bytes': len(raw),
                   'sha256': hashlib.sha256(raw).hexdigest()}
        digest = request['sha256']
        if digest not in self.contents:
            if sum(map(len, self.contents.values())) + len(raw) > MAX_TOTAL:
                raise ValueError('repository_effect_content_budget')
            self.append_effect({'phase': 'content', 'sha256': digest, 'bytes': len(raw),
                                'base64': base64.b64encode(raw).decode('ascii')})
            self.contents[digest] = raw
        elif self.contents[digest] != raw:
            raise ValueError('repository_effect_content_collision')
        def perform():
            if name in self.directories:
                raise IsADirectoryError(errno.EISDIR, 'Is a directory', self.label(name))
            parent = self.parent(name)
            if sum(map(len, self.files.values())) - len(self.files.get(name, b'')) + len(raw) > MAX_TOTAL:
                raise ValueError('repository_dataset_total_budget')
            if name not in self.files:
                if len(self.files) + len(self.directories) >= MAX_FILES:
                    raise ValueError('repository_dataset_membership_budget')
                self.directories[parent].append(PurePosixPath(name).name)
                self.modes[name] = '100644'
            self.files[name] = raw
            return {'bytes_written': len(raw)}
        return self.effect(request, perform)

    def membership(self):
        return {name: {'mode': self.modes[name]} for name in self.files}
