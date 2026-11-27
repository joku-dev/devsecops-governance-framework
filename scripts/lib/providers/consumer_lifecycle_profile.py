"""Whole legacy wording, guard and isolated read-token selection; no inherited authority."""
LITERALS = {'legacy_52a2d060d5b766a6': 'New receipt differs from independently retrieved GitHub evidence', 'legacy_23e9b3bf4fa896bc': 'New action requires an actual GitHub capture', 'legacy_88eda6a67b47f06e': 'Operating acceptance changed or was withdrawn at GitHub; capture the correction first', 'legacy_d9e4219f7cabd9ef': 'New operating acceptance differs from GitHub', 'legacy_78f9096520382e56': 'joku-dev/devsecops-governance-framework', 'legacy_adf37aa1af6a2392': 'https://github.com/joku-dev/devsecops-governance-framework/pull/87#issuecomment-5653982008'}
import re

MANIFEST_PATHS = ('.github/workflows/consumer-lifecycle-guard.yml', '.github/workflows/consumer-lifecycle-update.yml', 'docs/operations/evidence/consumer-lifecycle-operation.md', 'requirements-validation.txt', 'schemas/governance-consumer-acceptance.schema.json', 'schemas/governance-consumer-action-receipt.schema.json', 'schemas/governance-consumer-action-request.schema.json', 'schemas/governance-consumer-profile.schema.json', 'schemas/governance-consumer-receipt.schema.json', 'schemas/governance-consumer-roles.schema.json', 'schemas/governance-lifecycle-action-index.schema.json', 'schemas/governance-lifecycle-action-transaction.schema.json', 'schemas/governance-lifecycle-architecture-source.schema.json', 'schemas/governance-lifecycle-candidate-context.schema.json', 'schemas/governance-lifecycle-candidates.schema.json', 'schemas/governance-lifecycle-closure-index.schema.json', 'schemas/governance-lifecycle-closure-transaction.schema.json', 'schemas/governance-lifecycle-closure-v0.2.schema.json', 'schemas/governance-lifecycle-closure.schema.json', 'schemas/governance-lifecycle-common.schema.json', 'schemas/governance-lifecycle-decision-v0.2.schema.json', 'schemas/governance-lifecycle-decision.schema.json', 'schemas/governance-lifecycle-devsecops-source.schema.json', 'schemas/governance-lifecycle-event-v0.2.schema.json', 'schemas/governance-lifecycle-event.schema.json', 'schemas/governance-lifecycle-exception-index.schema.json', 'schemas/governance-lifecycle-exception-profile.schema.json', 'schemas/governance-lifecycle-exception-transaction.schema.json', 'schemas/governance-lifecycle-exception.schema.json', 'schemas/governance-lifecycle-index.schema.json', 'schemas/governance-lifecycle-live-profile-preparation.schema.json', 'schemas/governance-lifecycle-observation.schema.json', 'schemas/governance-lifecycle-operating-acceptance.schema.json', 'schemas/governance-lifecycle-overview.schema.json', 'schemas/governance-lifecycle-personal-channel-probe.schema.json', 'schemas/governance-lifecycle-pilot-action-receipt.schema.json', 'schemas/governance-lifecycle-pilot-action-request.schema.json', 'schemas/governance-lifecycle-pilot-operating.schema.json', 'schemas/governance-lifecycle-pilot-receipt.schema.json', 'schemas/governance-lifecycle-pilot-role-binding.schema.json', 'schemas/governance-lifecycle-profile.schema.json', 'schemas/governance-lifecycle-remediation-v0.2.schema.json', 'schemas/governance-lifecycle-remediation.schema.json', 'schemas/governance-lifecycle-transaction.schema.json', 'scripts/bootstrap_validation_env.sh', 'scripts/lib/governance_lifecycle/__init__.py', 'scripts/lib/governance_lifecycle/adapter.py', 'scripts/lib/governance_lifecycle/architecture_candidates.py', 'scripts/lib/governance_lifecycle/candidates.py', 'scripts/lib/governance_lifecycle/closure.py', 'scripts/lib/governance_lifecycle/consumer_acceptance.py', 'scripts/lib/governance_lifecycle/consumer_actions.py', 'scripts/lib/governance_lifecycle/consumer_admission.py', 'scripts/lib/governance_lifecycle/consumer_contracts.py', 'scripts/lib/governance_lifecycle/consumer_evidence.py', 'scripts/lib/governance_lifecycle/contracts.py', 'scripts/lib/governance_lifecycle/decisions.py', 'scripts/lib/governance_lifecycle/devsecops_candidates.py', 'scripts/lib/governance_lifecycle/exceptions.py', 'scripts/lib/governance_lifecycle/kernel.py', 'scripts/lib/governance_lifecycle/live_admission.py', 'scripts/lib/governance_lifecycle/live_evidence.py', 'scripts/lib/governance_lifecycle/live_preparation.py', 'scripts/lib/governance_lifecycle/operating_acceptance.py', 'scripts/lib/governance_lifecycle/personal_probe.py', 'scripts/lib/governance_lifecycle/pilot_actions.py', 'scripts/lib/governance_lifecycle/store.py', 'scripts/lib/governance_lifecycle/synthetic.py', 'scripts/lib/governance_lifecycle/synthetic_actions.py', 'scripts/lib/governance_lifecycle/synthetic_exceptions.py', 'scripts/publish_consumer_lifecycle.py', 'scripts/run_consumer_lifecycle.py', 'scripts/validate_all.sh', 'scripts/validation-toolchain.env')

class LegacyConsumerProfile:
    manifest_paths = MANIFEST_PATHS
    capture_method = 'github_api_get_via_gh'

    def __init__(self, context, *, default_fetch=None):
        self.context, self.default_fetch = (context, default_fetch)

    def verify_required_guard(self, *, fetch=None):
        rules = self.context.adapter.strict_json((fetch or self.default_fetch)('repos/joku-dev/devsecops-governance-framework/rules/branches/main'))
        self.context.contracts.require(isinstance(rules, list), 'Effective main rules must be a list')
        required = any((rule.get('type') == 'required_status_checks' and rule.get('parameters', {}).get('strict_required_status_checks_policy') is True and any((check.get('context') == 'Consumer Lifecycle Guard' and check.get('integration_id') == 15368 for check in rule['parameters'].get('required_status_checks', []))) for rule in rules))
        self.context.contracts.require(required, 'Consumer Lifecycle Guard must be a strict required GitHub Actions check on main')

    def render(self, index):
        acceptance = index['operating_acceptance']
        return '\n'.join(['# Consumer Operation-Readiness Lifecycle', '', f"Operating acceptance: **{acceptance['status']}**. Effective: **{str(acceptance['effective']).lower()}**.", f"Implementation matches the acceptance request: `{str(acceptance['implementation_matches']).lower()}`.", f"Finding state: `{index['finding_state']}`. Pilot state as of `{index['as_of']}`; evidence as of `{index['evidence_as_of']}`.", f"Receipts: {index['counts']['receipts']}; action records: {index['counts']['actions']}.", '', 'The report reflects retained captures. Recheck GitHub before any new operational proposal.', index['promotion_basis'] + '.', index['limitation'], ''])

    def statement_template(self, value, body):
        return f"# Persönliche Consumer-Betriebsabnahme\n\nBitte zuerst den vollständigen Antrag und den Betriebsleitfaden prüfen. Diese Erklärung gibt den beschriebenen manuellen Operation-Readiness-Piloten im Report-only-Modus frei. Behebung und Abschluss benötigen weiterhin eigene persönliche Erklärungen.\n\nDiskussion: https://github.com/{value['repository_id']}/pull/{value['discussion_number']}\n\n```text\n" + body(value) + '```\n\nDie benannte Person gibt den Kommentar selbst ab. Codex darf ihn vorbereiten, aber nicht stellvertretend posten.\n'

    def positive_id(self, value):
        self.context.contracts.require(type(value) is int and value > 0, 'Expected positive provider integer identity')
        return str(value)

    def literal(self, key):
        return LITERALS[key]

class LegacyConsumerReader:

    def __init__(self, process, environment_factory):
        self.process, self.environment_factory = (process, environment_factory)

    def github_get(self, endpoint, *, raw=False):
        """Read cross-repository evidence without changing the publisher's write token."""
        command = ['gh', 'api', '--hostname', 'github.com', '--method', 'GET', endpoint]
        if raw:
            command.extend(['-H', 'Accept: application/vnd.github.raw+json'])
        environment = self.environment_factory()
        if environment.get('CONSUMER_EVIDENCE_TOKEN'):
            environment['GH_TOKEN'] = environment['CONSUMER_EVIDENCE_TOKEN']
        return self.process.check_output(command, env=environment, timeout=90)
