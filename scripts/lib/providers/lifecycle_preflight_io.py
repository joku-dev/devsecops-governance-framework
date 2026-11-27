"""Native observed exclusive preflight mkdir, including ordinary concurrent appearance."""
import errno
from lib.providers.synthetic_lifecycle_io import NativeIO,capture_port
from lib.providers.workbook_import_io import original_error,failure_value
from lib.lifecycle_preflight_io import ACTION,original_options,verify,finish,admit_preimage
class NativePreflightIO(NativeIO):

    def make_exclusive_directory(self, anchor, path, mode):
        parts = anchor.parts(path)
        with anchor.root_fd() as root:
            with anchor.parent(root, parts[:-1]) as parent:
                import os
                os.mkdir(parts[-1], mode, dir_fd=parent)

    @capture_port
    def mkdir(self, path, mode, parents, exist_ok, label):
        if self.mode != 'selected-files' or not original_options(mode, parents, exist_ok):
            return super().mkdir(path, mode, parents, exist_ok, label)
        spec = self.output.admit(path, label)
        anchor = self.output.anchor(path)
        before = anchor.snapshot(path);prior=self.metadata.get(path)
        admit_preimage(self,path,before,prior)
        self.append({'kind': ACTION + '-before', 'selection': spec, 'anchor': anchor.frame, 'snapshot': before,'input_before':prior})
        args = {'selection': spec, 'mode': mode, 'parents': False, 'exist_ok': False, 'export_mode': self.mode}
        created = False
        failure = None
        appeared = False

        def effect():
            nonlocal created
            try:
                self.make_exclusive_directory(anchor, path, mode)
            except OSError as error:
                raise original_error(error, label) from None
            created = True
        try:
            return self.perform(ACTION, args, effect)
        except OSError as error:
            failure = failure_value(error)
            raise
        finally:
            try:
                after = anchor.snapshot(path)
                appeared = not created and before['kind'] == 'missing' and (after['kind'] in ('file', 'directory')) and (failure is not None) and (failure['type'] == 'FileExistsError') and (failure['errno'] == errno.EEXIST)
                verify(before, after, created=created, appeared=appeared, failure=failure)
                self.append({'kind': ACTION + '-after', 'selection': spec, 'snapshot': after, 'created': created, 'external_appearance': appeared, 'failure': failure})
                finish(self, path, before, after, created=created, appeared=appeared)
            except Exception:
                self.record.capture_incomplete = True
                raise
