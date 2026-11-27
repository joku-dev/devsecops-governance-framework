"""Retained original recorded_at sample, distinct from the preceding GET capture clock."""
from lib.personal_channel_process import clock_value
from lib.requirement_validation_replay import IntegrityError
class ReplayActionRecordedClock:
    def __init__(self,owner):self.owner=owner
    def __call__(self):
        ok,value=self.owner.outcome('pilot-action-recorded-clock',{'format':'UTC-seconds'},'json')
        if not ok:raise IntegrityError('pilot_action_recorded_clock_incomplete')
        return clock_value(value)
