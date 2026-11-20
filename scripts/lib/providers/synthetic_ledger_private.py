"""Read-only selected preimages for the complete private ledger model."""
from lib.providers.synthetic_lifecycle_projection import CaptureProjection as ReportCapture
from lib.synthetic_ledger_private import ProjectionMixin
from lib.requirement_validation_budget import InputAdmissionError
from lib.workbook_import_io import ancestor_paths


class CaptureProjection(ProjectionMixin, ReportCapture):
    def __init__(self, owner):
        super().__init__(owner)
        self.ledger_tree(self.resolve)

    def obtain(self, path, label):
        self.io.check(path, label, write=True)
        anchor = self.observer.anchor(path)
        paths = ancestor_paths(str(anchor.root), path)
        if len(paths) > 100: raise InputAdmissionError('synthetic_ledger_private_preimage_depth_budget')
        values = {}
        for name in paths:
            try: value = anchor.snapshot(name)
            except InputAdmissionError as error:
                if str(error) != 'workbook_regular_bounded_output_required': raise
                _, observed = self.io.ledger_files.read(name, name)
                if observed['metadata']['nlink'] != 2:
                    raise InputAdmissionError('synthetic_ledger_private_alias_observation_changed')
                self.emit({'kind': 'synthetic-ledger-private-alias-preimage', 'path': name, 'observation': observed})
                value = observed['snapshot']
                if name in self.observer.observed and self.observer.observed[name] != value:
                    raise InputAdmissionError('synthetic_ledger_private_alias_preimage_changed')
                if name in self.io.metadata and self.io.metadata[name] != observed['metadata']:
                    raise InputAdmissionError('synthetic_ledger_private_alias_input_changed')
                self.observer.observed[name] = value
            else: self.observer.prior(name, value)
            values[name] = value
        return anchor.frame, values
