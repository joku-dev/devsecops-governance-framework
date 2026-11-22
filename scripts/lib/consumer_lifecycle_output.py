"""Finite native output reconstruction for a whole consumer operation."""
from lib.synthetic_lifecycle_output import ReplayOutput
from lib.synthetic_lifecycle_io import path_spec
from lib.requirement_validation_replay import IntegrityError

MAX_OUTPUT_OPERATIONS = 4096


class ConsumerReplayOutput(ReplayOutput):
    def admit(self, path, label):
        spec = path_spec(path, label, self.io.cwd)
        if self.io.mode != 'selected-files':
            raise IntegrityError('consumer_native_output_mode_changed')
        self.operations += 1
        if self.operations > MAX_OUTPUT_OPERATIONS:
            raise IntegrityError('consumer_output_operation_budget')
        return spec
