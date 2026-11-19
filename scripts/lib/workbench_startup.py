"""Finite neutral first/repeated Workbench startup; execution belongs to ports.

An existing interpreter skips dependency setup exactly as the original starter.
A handoff observation is an intention, never evidence that a server is ready or
that an operating approval, source approval or publishing right was granted.
"""
from lib.environment_bootstrap import BootstrapFailure

PROFILE='workbench-startup-v1'


def run(ports,observer):
    def step(action,kind=type(None)):
        token=observer.before(action)
        try:
            value=ports.perform(action)
            if type(value) is not kind:
                raise BootstrapFailure('workbench_startup_invalid_port_result')
        except BootstrapFailure as error:
            observer.failed(token,error.code);raise
        observer.after(token,value);return value
    step('preflight')
    existing=step('environment_python_executable',bool)
    if not existing:step('bootstrap_environment')
    step('admit_environment')
    step('admit_instance')
    # Must be durable before the native adapter replaces this process. A real
    # exec never returns to create a fictional ready/closed process observation.
    return step('handoff_workbench',int)


class RecordedPorts:
    def __init__(self,rows):
        if type(rows) is not list:raise ValueError('workbench_startup_rows_required')
        self.rows=rows;self.position=0
    def perform(self,action):
        if self.position==len(self.rows):raise ValueError('workbench_startup_rows_incomplete')
        row=self.rows[self.position];self.position+=1
        if type(row) is not dict or set(row) not in ({'action','value'},{'action','failure'}) or row['action']!=action:
            raise ValueError('workbench_startup_row_order_changed')
        if 'failure' in row:raise BootstrapFailure(row['failure'])
        return row['value']
    def complete(self):
        if self.position!=len(self.rows):raise ValueError('workbench_startup_unused_rows')


def replay(rows):
    ports=RecordedPorts(rows)
    class Observer:
        def before(self,value):return value
        def after(self,*ignored):pass
        def failed(self,*ignored):pass
    try:return run(ports,Observer())
    finally:ports.complete()
