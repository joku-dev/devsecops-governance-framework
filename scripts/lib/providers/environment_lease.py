"""Shared own-environment lease interoperating with the explicit bootstrap writer."""
import fcntl
import hashlib
import os
import stat
from lib.environment_bootstrap import BootstrapFailure
from lib.providers.environment_bootstrap_native import normalized
from lib.providers.environment_bootstrap_storage import document,inspect as inspect_bootstrap


def shared_environment_lease(target,*,prefix):
    target=normalized(target)
    name='.axiom-bootstrap-'+hashlib.sha256(str(target).encode()).hexdigest()[:24]+'.lock'
    fd=os.open(target.parent/name,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
        row=os.fstat(fd)
        if (not stat.S_ISREG(row.st_mode) or row.st_uid!=os.geteuid()
                or row.st_nlink!=1 or row.st_mode&0o077 or row.st_size>16384):
            raise BootstrapFailure(prefix+'_private_environment_lease_required')
        if row.st_size:
            previous=document(os.read(fd,16385))
            if (set(previous)!={'schema_version','target','record_root'}
                    or type(previous['schema_version']) is not int or previous['schema_version']!=1
                    or previous['target']!=str(target) or type(previous['record_root']) is not str):
                raise BootstrapFailure(prefix+'_previous_bootstrap_owner_invalid')
            retained=inspect_bootstrap(normalized(previous['record_root']))
            if retained['declared_result']!='complete' or retained['incomplete_native_captures']:
                raise BootstrapFailure(prefix+'_bootstrap_reconciliation_required')
    except BaseException:
        os.close(fd);raise
    return fd
