#!/usr/bin/env python3
"""Source-only compatibility facade for the complete original reconciler."""
import sys
from lib.providers.documentation_reconciliation_compatibility import legacy as _legacy
_legacy.__file__=__file__
if __name__=='__main__':
    raise SystemExit(_legacy.main())
sys.modules[__name__]=_legacy
