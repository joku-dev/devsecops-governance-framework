#!/usr/bin/env python3
"""Source compatibility facade for the explicit complete legacy renderer."""
import sys
from lib.providers import legacy_document_rendering as _legacy
if __name__ == '__main__':
    raise SystemExit(_legacy.main())
sys.modules[__name__] = _legacy
