"""Separate whole-consumer output count; byte/identity/progress guards unchanged."""
from lib.providers.synthetic_lifecycle_output import NativeOutput
from lib.consumer_lifecycle_output import MAX_OUTPUT_OPERATIONS
from lib.requirement_validation_budget import InputAdmissionError


class ConsumerNativeOutput(NativeOutput):
    def admit(self, path, label):
        spec = self.io.check(path, label, write=True)
        if self.io.mode != 'selected-files':
            raise InputAdmissionError('consumer_explicit_native_output_mode_required')
        self.operations += 1
        if self.operations > MAX_OUTPUT_OPERATIONS:
            raise InputAdmissionError('consumer_output_operation_budget')
        return spec
