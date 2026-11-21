"""Two fixed engineering capture budgets; never original governance verdicts.

A pilot-run capture admits 25 MiB before base64 encoding and JSON framing.
Its receipt therefore needs a separate 64 MiB ledger-file allowance. Repeated
stable before/after reads share a finite 2 GiB allowance. Existing ledger
operations retain their original 16/128 MiB limits. These are composition-time
profiles, never CLI-controlled or inferred from untrusted receipt contents.
"""
from dataclasses import dataclass
from lib.validation_files import MAX_FILE, MAX_TOTAL
from lib.requirement_validation_budget import InputAdmissionError

@dataclass(frozen=True)
class LedgerBudget:
    file: int
    total: int

DEFAULT = LedgerBudget(MAX_FILE, MAX_TOTAL)
PILOT_RUN = LedgerBudget(64 * 1024**2, 2 * 1024**3)

def admitted(value):
    if type(value) is not LedgerBudget or value not in (DEFAULT, PILOT_RUN):
        raise InputAdmissionError('synthetic_ledger_fixed_budget_profile_required')
    return value
