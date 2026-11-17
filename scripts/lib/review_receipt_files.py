"""Explicit external metadata-file effects; no checkout writes or private packet publication."""
import os
from pathlib import Path
import stat
from lib import review_receipts as logic
from lib.review_git import directory
from lib.ci_bundle_storage import reserve


def destination(path, excluded):
    try: path = Path(path).expanduser()
    except RuntimeError: raise ValueError('invalid_review_output_destination') from None
    if path.is_symlink(): raise ValueError('receipt_symlink_destination_forbidden')
    path = path.resolve()
    if not path.name or any(path.is_relative_to(Path(root).resolve()) for root in excluded):
        raise ValueError('review_outputs_must_stay_outside_checkout')
    # Create every missing ancestor privately; never chmod an existing directory.
    parent = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.parent.parts[1:]:
            try: following = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            except FileNotFoundError:
                try: os.mkdir(component, 0o700, dir_fd=parent)
                except FileExistsError: pass
                following = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent); parent = following
    finally: os.close(parent)
    return path


def optional_read(parent, name, limit):
    try: fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    except FileNotFoundError: return None
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode): raise ValueError('review_metadata_regular_file_required')
        if before.st_size > limit: raise ValueError('review_metadata_external_byte_budget')
        with os.fdopen(fd, 'rb', closefd=False) as stream: raw = stream.read(limit + 1)
        after = os.fstat(fd)
        if len(raw) > limit: raise ValueError('review_metadata_external_byte_budget')
        if any(getattr(before, key) != getattr(after, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode')):
            raise ValueError('review_metadata_file_changed_during_read')
        return raw
    finally: os.close(fd)


def write_receipt(path, candidate, schema, excluded):
    path = destination(path, excluded); reserve(path.parent, logic.MAX_RECEIPT)
    parent = directory(path.parent, '')
    try:
        # Validate and bound before making any external effect.
        selected, expected, _ = logic.choose_receipt(candidate, None, schema)
        if len(expected) > logic.MAX_RECEIPT: raise ValueError('review_receipt_byte_budget')
        try: fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        except FileExistsError:
            before = optional_read(parent, path.name, logic.MAX_RECEIPT)
            if before is None: raise ValueError('review_receipt_destination_changed')
            selected, expected, _ = logic.choose_receipt(candidate, before, schema)
            if optional_read(parent, path.name, logic.MAX_RECEIPT) != before: raise ValueError('review_receipt_destination_changed')
            return selected, before, expected, False, path
        with os.fdopen(fd, 'wb') as stream:
            stream.write(expected); stream.flush(); os.fsync(stream.fileno())
        if optional_read(parent, path.name, logic.MAX_RECEIPT) != expected: raise ValueError('review_receipt_destination_changed')
        return selected, None, expected, True, path
    finally: os.close(parent)


def append_usage(path, receipt, schema, excluded):
    path = destination(path, excluded); reserve(path.parent, logic.MAX_RECEIPT)
    parent = directory(path.parent, ''); lock_name = path.name + '.lock'; lock = None
    try:
        try: lock = os.open(lock_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        except FileExistsError: raise ValueError('review_usage_locked_retry_after_exporter') from None
        before = optional_read(parent, path.name, logic.MAX_LOG)
        after, appended = logic.usage_projection(before, receipt, schema)
        if appended:
            flags = os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK
            if before is None: flags |= os.O_CREAT | os.O_EXCL
            fd = os.open(path.name, flags, 0o600, dir_fd=parent)
            try:
                current = os.fstat(fd)
                if not stat.S_ISREG(current.st_mode) or current.st_size != len(before or b''): raise ValueError('review_usage_destination_changed')
                if optional_read(parent, path.name, logic.MAX_LOG) != (before if before is not None else b''): raise ValueError('review_usage_destination_changed')
                with os.fdopen(fd, 'wb', closefd=False) as stream:
                    stream.write(after[len(before or b''):]); stream.flush(); os.fsync(stream.fileno())
            finally: os.close(fd)
        if optional_read(parent, path.name, logic.MAX_LOG) != after: raise ValueError('review_usage_destination_changed')
        return before, after, appended, path
    finally:
        try:
            if lock is not None:
                try:
                    current = os.stat(lock_name, dir_fd=parent, follow_symlinks=False); original = os.fstat(lock)
                    if (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino): raise ValueError('review_usage_lock_changed')
                    os.unlink(lock_name, dir_fd=parent)
                finally: os.close(lock)
        finally: os.close(parent)
