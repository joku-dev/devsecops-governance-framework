"""Same ordered two-ledger/preflight cursor and full pilot-receipt byte budget."""
from lib.pilot_action_ledgers import ReplayActionIO
from lib.lifecycle_preflight_io import ReplayPreflightIO
from lib.synthetic_ledger_budget import PILOT_RUN
class ReplayUpdateIO(ReplayActionIO,ReplayPreflightIO):
    def __init__(self,*args,**kwargs):super().__init__(*args,ledger_budget=PILOT_RUN,**kwargs)
