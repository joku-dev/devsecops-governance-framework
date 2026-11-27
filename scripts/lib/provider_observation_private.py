"""All original private credential decisions over explicit native/path/system ports."""
import re,stat,struct


class PrivateCredentialCheck:
    def __init__(self,*,path_factory,native,system):self.path,self.native,self.system=path_factory,native,system

    def _service_acl(self, value, uid, permission):
        if len(value) != 44 or struct.unpack('<I', value[:4])[0] != 2:
            return False
        entries = [struct.unpack('<HHI', value[offset:offset + 8]) for offset in range(4, len(value), 8)]
        undefined = 4294967295
        expected = {(1, permission, undefined), (2, permission, uid), (4, 0, undefined), (16, permission, undefined), (32, 0, undefined)}
        return len(set(entries)) == 5 and set(entries) == expected

    def _readonly_memory_mount(self, directory):
        for line in self.path('/proc/self/mountinfo').read_text().splitlines():
            before, after = line.split(' - ', 1)
            fields, filesystem = (before.split(), after.split()[0])
            if fields[4] == str(directory):
                return 'ro' in fields[5].split(',') and filesystem in {'tmpfs', 'ramfs'}
        return False

    def check_private_file(self, path):
        """Reject public files; accept ACL credentials only in their real service mount."""
        path = self.path(path)
        if path.is_symlink():
            raise ValueError('Private file must not be a symlink')
        fd = self.native.open(path, self.native.O_RDONLY | self.native.O_NOFOLLOW)
        try:
            info = self.native.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid not in {0, self.native.geteuid()}:
                raise ValueError('Expected an owned private regular file')
            if not info.st_mode & 63:
                return
            directory = path.parent
            credential_directory = self.native.environ.get('CREDENTIALS_DIRECTORY')
            if self.system.platform != 'linux' or stat.S_IMODE(info.st_mode) != 288 or info.st_uid != 0 or (not credential_directory) or (directory != self.path(credential_directory)) or (directory.parent != self.path('/run/credentials')) or (not re.fullmatch('[A-Za-z0-9_.@:-]+\\.service', directory.name)) or (directory.resolve() != directory):
                raise ValueError('Private file has unsafe permissions')
            parent = directory.stat()
            if parent.st_uid != 0 or stat.S_IMODE(parent.st_mode) != 360 or (not self._readonly_memory_mount(directory)) or (not self._service_acl(self.native.getxattr(fd, 'system.posix_acl_access'), self.native.geteuid(), 4)) or (not self._service_acl(self.native.getxattr(directory, 'system.posix_acl_access'), self.native.geteuid(), 5)):
                raise ValueError('Credential is not isolated to this service UID')
        finally:
            self.native.close(fd)
