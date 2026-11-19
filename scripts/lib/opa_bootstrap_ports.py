"""Standard-library-only composition for bootstrap before dependencies exist.

This explicit adapter binding is separate from the application composition,
whose dependency-rich providers cannot run before the environment is prepared.
"""
from lib.providers.opa_bootstrap import (Tool as OPABootstrapTool,
    DownloadError as OPABootstrapDownloadError, MAX_BYTES as OPA_BOOTSTRAP_MAX_BYTES,
    select_tool as select_opa_bootstrap_tool, locations as opa_bootstrap_locations,
    matches as opa_bootstrap_matches, download as opa_bootstrap_download,
    install_copy as opa_bootstrap_copy, install as install_opa_bootstrap,
    main as run_opa_bootstrap)
