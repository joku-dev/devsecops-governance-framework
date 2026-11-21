"""One selected receipt ledger plus complete diagnostic preflight path observations."""
from lib.synthetic_ledger_budget import PILOT_RUN
from lib.providers.synthetic_ledger_io import NativeIO as LedgerIO
from lib.providers.lifecycle_preflight_io import NativePreflightIO

class NativeRunIO(LedgerIO,NativePreflightIO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, ledger_budget=PILOT_RUN, **kwargs)
