#!/usr/bin/env python3
"""Source compatibility facade for the complete original synthetic lifecycle generator."""
import sys
from lib.providers import legacy_synthetic_lifecycle_overview as _legacy
if __name__ == '__main__':
    raise SystemExit(_legacy.main())
sys.modules[__name__] = _legacy
