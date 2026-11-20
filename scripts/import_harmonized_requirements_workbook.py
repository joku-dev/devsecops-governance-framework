#!/usr/bin/env python3
"""V1 invocation compatibility; whole workbook import lives in its explicit adapter."""
import sys
if __package__:
    from .lib.providers import legacy_workbook_import as implementation
else:
    from lib.providers import legacy_workbook_import as implementation
if __name__ == '__main__':
    raise SystemExit(implementation.main())
sys.modules[__name__] = implementation
