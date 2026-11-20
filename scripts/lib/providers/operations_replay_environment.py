"""Same explicit provider normalization over retained whole-operation calls."""
from datetime import datetime
from types import SimpleNamespace

from lib.operations_collection import collect
from lib.operations_input_binding import check_bytes
from lib.operations_sources import text
from lib.providers import operations_report_profile as profile
from lib.providers.operations_files import RetainedSources
from lib.providers.operations_http import ProviderReads, ReplayBackend
from lib.providers.operations_security import RetainedSecurity


class ReplayEnvironment:
    def __init__(self, calls, request, source):
        self.calls = calls
        self.request = request
        self.source = source

    def input(self, kind):
        label = self.request[kind + '_label']
        raw = self.calls.call('operations_input', {'kind': kind, 'label': label}, encoding='bytes')
        check_bytes(kind, label, raw, self.source, profile.PRODUCT_INPUTS)
        return text(raw)

    def config_text(self):
        return self.input('config')

    def schema_text(self):
        return self.input('schema')

    def observation_text(self):
        return self.input('observation')

    def utc_now(self):
        value = datetime.fromisoformat(self.calls.call('operations_clock', {}))
        if value.utcoffset() is None or value.utcoffset().total_seconds() != 0 or value.microsecond:
            raise ValueError('operations_retained_clock_changed')
        return value

    def checkout_sha(self):
        value = self.calls.call('operations_checkout', {})
        if value != self.source['node_context']['source_revision']:
            raise ValueError('operations_product_revision_changed')
        return value

    def collect(self, config, now):
        if not self.request['live_admitted']:
            raise ValueError('operations_null_observation_requires_explicit_live_fallback')
        reads = ProviderReads(ReplayBackend(self.calls), config['repository'], profile.workflow_queries(config))
        local = RetainedSources(self.calls, profile.INDEXES)
        security = RetainedSecurity(self.calls, local,
            binding={**self.source['node_context'], 'source_tree': self.source['product_tree']}, source_root=self.request['source_label'])
        environment = SimpleNamespace(main_reference=reads.main_reference, workflow_queries=profile.workflow_queries,
            workflow_runs=reads.workflow_runs, pull_requests=reads.pull_requests, registry=local.registry,
            index_domains=local.index_domains, index=local.index, records=local.records, security=security.security)
        return collect(config, now, environment)
