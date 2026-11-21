"""Single ordered pure cursor for receipt-ledger and diagnostic capture observations."""
from lib.synthetic_ledger_budget import PILOT_RUN
from lib.synthetic_ledger_io import ReplayIO as LedgerReplay
from lib.lifecycle_preflight_io import ReplayPreflightIO

class ReplayRunIO(LedgerReplay,ReplayPreflightIO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, ledger_budget=PILOT_RUN, **kwargs)
