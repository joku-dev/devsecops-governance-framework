"""Two original ledger scopes plus bounded preflight/exclusive-output observations."""
from lib.providers.pilot_action_ledgers import NativeActionIO
from lib.providers.lifecycle_preflight_io import NativePreflightIO
from lib.providers.synthetic_ledger_files import LedgerFiles
from lib.synthetic_ledger_budget import PILOT_RUN
class NativeUpdateIO(NativeActionIO,NativePreflightIO):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,ledger_budget=PILOT_RUN,**kwargs)
        self.ledger_files.parts={name:LedgerFiles(self,name,transaction_name=self.transaction_name,budget=self.ledger_budget) for name in self.ledgers}
