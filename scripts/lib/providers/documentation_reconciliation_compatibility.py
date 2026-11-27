"""Source-only binding of original module constants to the facade's root."""
from pathlib import Path
from lib.providers import legacy_documentation_reconciliation as legacy
legacy.ROOT=Path(__file__).resolve().parents[3]
legacy.README=legacy.ROOT/'README.md'
legacy.CATALOG=legacy.ROOT/'docs/operations/guides/repository-function-catalog.md'
legacy.INVENTORY=legacy.ROOT/'docs/operations/guides/repository-technical-function-inventory.md'
legacy.AUDIT=legacy.ROOT/'generated/reports/documentation-refresh-audit.md'
