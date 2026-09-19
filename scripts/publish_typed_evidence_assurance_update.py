#!/usr/bin/env python3
"""Extend typed-evidence publication for measured L1 and control assurance ledgers."""

import publish_operational_update as publisher


ADDITIONAL_LEDGERS = (
    "status/measured-security-results/",
    "status/measured-l1-results/",
    "status/control-evidence-assurance/",
)


def configure() -> None:
    publisher.LEDGERS = (*publisher.LEDGERS, *ADDITIONAL_LEDGERS)
    publisher.SCOPES["typed-evidence"] = (
        *publisher.SCOPES["typed-evidence"],
        *ADDITIONAL_LEDGERS,
    )


def main() -> int:
    configure()
    return publisher.main()


if __name__ == "__main__":
    raise SystemExit(main())
