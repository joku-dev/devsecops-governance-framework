"""Explicit stdlib-only environment bootstrap composition before dependencies."""
from lib.providers.environment_bootstrap_native import NativeEnvironmentSession as open_environment_bootstrap
from lib.providers.environment_bootstrap_storage import inspect as inspect_environment_bootstrap
