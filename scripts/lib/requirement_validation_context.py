"""Read-only structural namespace and full requirement-validation outcome."""
from fnmatch import fnmatchcase
from lib.repository_paths import RepositoryPaths
from lib.requirement_validation import RequirementValidation
from lib.requirement_validation_replay import IntegrityError


def validate(source_label, io_port, history, *, base_ref=None, resource=None):
    namespace = RepositoryPaths(source_label, io_port)
    root = namespace.root

    def reviews(pattern):
        # The original has exactly these two component-wise glob operations.
        if pattern not in ('OPA-*/review.json', 'PRA-*/review.json'):
            raise ValueError('requirement_review_pattern_not_selected')
        parent = root / 'docs/governance/review-packets'
        if not parent.is_dir():
            return []
        first, leaf = pattern.split('/')
        return [child / leaf for child in parent.iterdir()
                if fnmatchcase(child.name, first) and child.is_dir() and (child / leaf).exists()]

    try:
        value = RequirementValidation(root, history, reviews, resource).validate(base_ref)
        return {**value, 'kernel_exception': None}
    except IntegrityError:
        raise
    except Exception as error:
        # Original uncaught errors exit1 before any summary. This finite capture
        # records their type/message without inventing a historical traceback.
        message = str(error)
        if len(message) > 65536:
            message = 'requirement_validation_exception_message_budget'
        return {'exit_code': 1, 'stdout': '', 'stderr': '',
                'kernel_exception': {'type': type(error).__name__, 'message': message}}
