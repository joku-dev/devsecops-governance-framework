"""Environment bootstrap application, without SDK/host/transport selection."""
from dataclasses import asdict

from lib.environment_bootstrap import run, BootstrapFailure
from lib.environment_bootstrap_ports import open_environment_bootstrap, inspect_environment_bootstrap


def execute(profile, options):
    """Known failure and incomplete capture remain distinct from successful setup."""
    with open_environment_bootstrap(profile, options) as session:
        try:
            completed=run(profile,session,session.journal)
            session.checkpoint()
            report=session.finish(asdict(completed));exit_code=0
        except BootstrapFailure as error:
            # A failure raised inside a phase already has a failed observation.
            # Source invalidation after all phases returned must stay incomplete;
            # inventing a failed phase would contradict the durable journal.
            state='failed' if session.journal.failed_phase else 'incomplete'
            report=session.finish({'state':state},code=error.code)
            exit_code=1 if state=='failed' else 2
        except Exception:
            report=session.finish({'state':'incomplete'},code='bootstrap_operation_incomplete');exit_code=2
        inspected=inspect_environment_bootstrap(report['record_root'])
        if inspected['declared_result']!=report['state']:
            raise ValueError('bootstrap_recorded_result_changed')
        return {**report,'exit_code':exit_code,'retained_record_inspected':True,
                'current_environment_rechecked_by_inspection':False}


def inspect_record(root):
    return inspect_environment_bootstrap(root)
