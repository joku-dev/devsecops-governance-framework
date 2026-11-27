"""Native observation of the original two-ledger lock/publication sequence."""
from pathlib import Path
from lib.providers.synthetic_ledger_io import NativeIO as LedgerIO
from lib.providers.synthetic_ledger_files import LedgerFiles
from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
from lib.synthetic_ledger_private import PrivateLedgerPort
from lib.pilot_action_ledgers import roots,select,NativeEffectRouter

class LedgerFileRouter:
    def __init__(self,owner,ledgers,transaction_name):
        self.parts={name:LedgerFiles(owner,name,transaction_name=transaction_name) for name in ledgers}
    def read(self,path,label):return self.parts[select(path,self.parts)].read(path,label)
    def directory(self,path):return self.parts[select(str(path),self.parts)].directory(path)

class NativeActionIO(LedgerIO):
    def __init__(self,*args,source,transaction_name,**kw):
        self.ledgers=roots(source)
        super().__init__(*args,ledger=self.ledgers[0],transaction_name=transaction_name,**kw)
        self.ledger_files=LedgerFileRouter(self,self.ledgers,transaction_name)
    def ledger_path(self,path):return any(Path(path).parent==Path(name)/'transactions' for name in self.ledgers)

def native_effects(owner,*,source,transaction_name):
    if owner.mode=='private-candidate':return PrivateLedgerPort(owner,str(Path(source)/'governance/lifecycle'))
    return NativeEffectRouter(owner,roots(source),factory=NativeLedgerEffects,transaction_name=transaction_name)
