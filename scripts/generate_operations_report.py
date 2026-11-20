#!/usr/bin/env python3
"""V1 invocation compatibility; native collection lives in its explicit adapter."""
import sys
if __package__:
    from .lib.providers import legacy_operations_report as implementation
else:
    from lib.providers import legacy_operations_report as implementation
if __name__ == '__main__':
    raise SystemExit(implementation.main())
sys.modules[__name__] = implementation
