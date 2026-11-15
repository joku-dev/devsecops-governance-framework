"""V1 import compatibility; provider implementation lives at the adapter boundary."""
import sys
from lib.providers import context as implementation
sys.modules[__name__] = implementation
