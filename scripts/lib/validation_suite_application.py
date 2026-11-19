"""Complete local suite application; no provider/host/tool selection here."""
from lib.validation_suite import run
from lib.validation_suite_ports import open_validation_suite,inspect_validation_suite


def execute(options):
    with open_validation_suite(options) as session:
        try:
            session.handoff_if_needed()
            code=run(session.arguments,session,session.journal,session.sink,
                environment_label=str(session.target),expected_opa_version=session.expected_opa_version)
            session.checkpoint()
            report=session.finish('complete',code)
        except Exception as error:
            report=session.finish('incomplete',None,error=error)
            code=2
        if report['state']=='complete':
            inspected=inspect_validation_suite(report['record_root'])
            if not inspected['retained_declared_replay_consistent']:raise ValueError('validation_suite_finished_replay_failed')
        return report,session.sink.bytes(),code


def inspect(root):return inspect_validation_suite(root)
