#!/usr/bin/env python3
"""V1 CLI compatibility; GitHub security acquisition belongs to its adapter."""
import sys
from lib.providers import github_security as implementation
if __name__ == '__main__':
    raise SystemExit(implementation.main())
sys.modules[__name__] = implementation
