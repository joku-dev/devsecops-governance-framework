#!/usr/bin/env python3
"""Compatibility entrypoint for the explicit pinned OPA bootstrap adapter.

The active facade keeps the existing CLI and callable API. Provider locations,
transport, cache repair and native installation belong to the selected adapter.
"""
from pathlib import Path
import subprocess
import time

from lib.opa_bootstrap_ports import (OPABootstrapTool as Tool,
    OPABootstrapDownloadError as DownloadError, OPA_BOOTSTRAP_MAX_BYTES as MAX_BYTES,
    select_opa_bootstrap_tool, opa_bootstrap_locations as locations,
    opa_bootstrap_matches as matches, opa_bootstrap_download as download,
    opa_bootstrap_copy as install_copy, install_opa_bootstrap, run_opa_bootstrap)

ROOT = Path(__file__).resolve().parents[1]


def select_tool(toolchain=ROOT / 'scripts/validation-toolchain.env',
                sources=ROOT / 'scripts/opa-download-sources.json', *, system=None, machine=None):
    return select_opa_bootstrap_tool(toolchain, sources, system=system, machine=machine)


def install(tool, destination, cache, *, mirror='', offline=False, attempts=3, timeout=120,
            fetch=download, sleep=time.sleep):
    # Preserve explicit fetch/sleep and the existing copy seam for callers/tests.
    return install_opa_bootstrap(tool, destination, cache, mirror=mirror, offline=offline,
        attempts=attempts, timeout=timeout, fetch=fetch, sleep=sleep, copier=install_copy)


def main():
    return run_opa_bootstrap()


if __name__ == '__main__':
    raise SystemExit(main())
