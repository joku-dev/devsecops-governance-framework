"""V1 import compatibility; provider implementation lives at the adapter boundary."""
import sys
from lib.providers import operations as implementation
sys.modules[__name__] = implementation
