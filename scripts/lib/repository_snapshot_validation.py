"""Compose the five original snapshot validators over one retained data root."""
from lib.repository_snapshots_security import SecuritySnapshots
from lib.repository_snapshots_measured import MeasuredSnapshots
from lib.repository_snapshots_assurance import AssuranceSnapshots
from lib.repository_snapshots_staging import StagingSnapshots
from lib.repository_snapshots_consolidated import ConsolidatedSnapshots


class RepositorySnapshotValidation:
    def __init__(self, root, *, validator_class):
        self.security = SecuritySnapshots(root, validator_class=validator_class, peers=self)
        self.measured = MeasuredSnapshots(root, validator_class=validator_class, peers=self)
        self.assurance = AssuranceSnapshots(root, validator_class=validator_class, peers=self)
        self.staging = StagingSnapshots(root, validator_class=validator_class, peers=self)
        self.consolidated = ConsolidatedSnapshots(root, validator_class=validator_class, peers=self)

    def load_measured_security_snapshots(self, root):
        return self.security.load_snapshots(root)

    def load_measured_l1_snapshots(self, root):
        return self.measured.load_snapshots(root)

    def load_assurance_profile(self):
        return self.assurance.load_profile()

    def load_assurance_snapshots(self, root):
        return self.assurance.load_snapshots(root)

    def validate_assurance_source(self, item):
        return self.assurance.validate_assurance_source(item)

    def load_staging_deployment_snapshots(self, root):
        return self.staging.load_snapshots(root)

    def load_consolidated_l1_snapshots(self, root):
        return self.consolidated.load_snapshots(root)

    def validate_consolidated_l1_sources(self, item):
        return self.consolidated.validate_sources(item)
