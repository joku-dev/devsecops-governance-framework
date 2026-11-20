"""Whole original kernel outcome, including captured exceptions and partial writes."""
from lib.operations_execution import execute


def run_kernel(request, environment, output, profile):
    try:
        value = execute(provided_observation=request['provided_observation'], as_of=request['as_of'],
                        environment=environment, output=output, profile=profile)
        return {**value, 'kernel_exception': None}
    except Exception as error:
        detail = str(error)
        if len(detail.encode('utf-8')) > 65536:
            raise ValueError('operations_kernel_error_message_budget') from None
        return {'exit_code': 1, 'stdout': '', 'stderr': '',
                'kernel_exception': {'type': type(error).__name__, 'message': detail}}
