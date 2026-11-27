"""Pure reconstruction of the explicitly sampled original request-creation time."""
from lib.personal_channel_process import clock_value
from lib.requirement_validation_replay import IntegrityError

class ReplayPreparationClock:
    def __init__(self,owner):self.owner=owner
    def __call__(self):
        ok,value=self.owner.outcome('pilot-action-preparation-clock',{'format':'UTC-seconds'},'json')
        if not ok:raise IntegrityError('pilot_action_preparation_clock_incomplete')
        return clock_value(value)
