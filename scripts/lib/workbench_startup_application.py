"""Finite first/repeat startup application with explicit native composition."""
from lib.environment_bootstrap import BootstrapFailure
from lib.workbench_startup import run
from lib.workbench_startup_ports import open_workbench_startup


def execute(options):
    with open_workbench_startup(options) as session:
        try:
            # A real native exec replaces this process and does not return here.
            return run(session,session.journal)
        except BootstrapFailure as error:
            session.diagnostic(error.code,'failed')
            return 1
        except Exception:
            session.diagnostic('workbench_startup_incomplete','incomplete')
            return 2
