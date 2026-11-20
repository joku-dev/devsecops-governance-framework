"""Whole advisory review entrypoints over explicit data and output ports."""
from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import PurePosixPath

from lib.repository_paths import RepositoryPaths
from lib.requirement_migration_generation import ImplementedRequirementMigration
from lib.requirement_platform_generation import PRARequirementPlatformReview
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError


class ReviewOutputPath:
    """Logical original output labels; every effect is delegated to its port."""
    def __init__(self, root_label, port, relative=''):
        self.root = PurePosixPath(root_label)
        self.port = port
        self.relative = PurePosixPath(relative)
        if (not self.root.is_absolute() or '..' in self.root.parts
                or self.relative.is_absolute() or '..' in self.relative.parts):
            raise ValueError('requirement_review_output_namespace_invalid')

    def __str__(self):
        return str(self.root / self.relative)

    def __truediv__(self, name):
        return ReviewOutputPath(str(self.root), self.port, str(self.relative / name))

    def relative_to(self, other):
        return (self.root / self.relative).relative_to(PurePosixPath(str(other)))

    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        return self.port.mkdir(self.relative.as_posix(), mode, parents, exist_ok)

    def write_text(self, data, encoding=None, errors=None, newline=None):
        if encoding != 'utf-8' or errors is not None or newline is not None:
            raise ValueError('requirement_review_original_utf8_write_required')
        if not isinstance(data, str) or len(data) > 64 * 1024**2:
            raise InputAdmissionError('requirement_review_output_budget')
        return self.port.write_text(self.relative.as_posix(), data, encoding)


def execute(kind, source_label, data_port, output_port, *, inventory_roots=None, empty_min_error=None):
    namespace = RepositoryPaths(source_label, data_port)
    output = ReviewOutputPath(source_label, output_port)
    if kind == 'implemented-migration':
        if inventory_roots is None:
            raise ValueError('requirement_review_explicit_inventory_required')
        roots = tuple((namespace.root / name, category, pattern)
                      for name, category, pattern in inventory_roots)
        engine = ImplementedRequirementMigration(namespace.root, output, roots)
    elif kind == 'pra-platform':
        if inventory_roots is not None:
            raise ValueError('requirement_review_inventory_not_applicable')
        def minimum(values):
            if not values and empty_min_error is not None:
                raise ValueError(empty_min_error)
            return min(values)
        engine = PRARequirementPlatformReview(namespace.root, output, minimum=minimum)
    else:
        raise ValueError('requirement_review_kind_not_selected')
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code, error = engine.main(), None
        except (InputAdmissionError, IntegrityError):
            raise
        except RetainedOutputError as failure:
            code, error = 1, {'type': failure.original_type, 'message': failure.original_message}
        except Exception as failure:
            message = str(failure)
            if len(message) > 65536:
                message = 'requirement_review_exception_message_budget'
            code, error = 1, {'type': type(failure).__name__, 'message': message}
    return {'exit_code': code, 'stdout': stdout.getvalue(),
            'stderr': stderr.getvalue(), 'kernel_exception': error}
