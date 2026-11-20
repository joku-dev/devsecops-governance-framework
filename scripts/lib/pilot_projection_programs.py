"""Whole original diagnostic pilot generation bodies, with explicit context."""
from lib.repository_lifecycle.lifecycle_pilot_actions import LifecycleActionReport
from lib.repository_lifecycle.lifecycle_pilot_validation import LifecyclePilotValidationReport

class PilotActionProgram(LifecycleActionReport):
    def main(self):
        index=self.context.actions.project_actions()
        (self.root/self.INDEX).write_bytes(self.context.adapter.json_bytes(index))
        (self.root/self.REPORT).write_text(self.render(index))
        print('Rendered pilot action validation; no operational activation.')

class PilotValidationProgram(LifecyclePilotValidationReport):
    def main(self):
        index=self.context.admission.project_receipts(self.context.store.load_transactions(self.root/self.context.admission.VALIDATION_LEDGER),self.context.admission.load_operating())
        (self.root/self.INDEX).write_bytes(self.context.adapter.json_bytes(index))
        (self.root/self.REPORT).write_text(self.render(index))
        print(index['counts'])
