"""The whole original private-intake atomic JSON helper over explicit ports.

The complete temporary/write/flush/fsync/close/chmod/replace/final-unlink sequence
is retained. Ports own files, descriptor tokens and actual side effects. This
helper alone grants no state, credential, publication or operating authority.
"""
import json


class IntakeAtomicJSON:
    def __init__(self, *, path_factory, native, temporary):
        self.path_factory = path_factory
        self.native = native
        self.temporary = temporary

    def atomic_json(self, path, value, mode=384):
        path = self.path_factory(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = self.temporary.mkstemp(dir=path.parent)
        try:
            with self.native.fdopen(fd, 'w') as stream:
                json.dump(value, stream, sort_keys=True, indent=2)
                stream.write('\n')
                stream.flush()
                self.native.fsync(stream.fileno())
            self.native.chmod(temporary, mode)
            self.native.replace(temporary, path)
        finally:
            self.path_factory(temporary).unlink(missing_ok=True)
