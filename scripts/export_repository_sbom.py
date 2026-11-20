#!/usr/bin/env python3
"""V1 invocation compatibility; the complete native protocol is an adapter."""
import sys
if __package__:
    from .lib.providers import legacy_repository_sbom as implementation
else:
    from lib.providers import legacy_repository_sbom as implementation
if __name__ == '__main__':
    raise SystemExit(implementation.main())
sys.modules[__name__] = implementation
