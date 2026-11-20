#!/usr/bin/env python3
"""Source compatibility facade for the complete original synthetic ledger program."""
import sys
from lib.providers import legacy_synthetic_ledger_action as _legacy
_legacy.__file__ = __file__
if __name__ == '__main__':
    raise SystemExit(_legacy.main())
sys.modules[__name__] = _legacy
