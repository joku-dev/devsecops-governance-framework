"""Native original ledger recorded_at sample after fresh action collection."""
from datetime import datetime,timezone
from lib.personal_channel_process import clock_value
from lib.requirement_validation_budget import InputAdmissionError
class NativeActionRecordedClock:
    def __init__(self,owner):self.owner=owner
    def __call__(self):
        def effect():return {'schema_version':1,'clock':'UTC-seconds','value':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')}
        try:return clock_value(self.owner.perform('pilot-action-recorded-clock',{'format':'UTC-seconds'},effect))
        except Exception as error:
            self.owner.record.capture_incomplete=True
            if isinstance(error,InputAdmissionError):raise
            raise InputAdmissionError('pilot_action_recorded_clock_capture_incomplete') from error
