"""All original publisher lifecycle gates over one explicitly supplied context.

Reading source acceptance never grants this node publishing authority.
"""
from lib.operating_publication_validation import OperatingPublicationValidation

class OperationalPublicationGates:
    def __init__(self,context,*,path_factory,prefix,receipts,actions,operating,git):
        self.context,self.prefix=context,prefix
        self.publication=OperatingPublicationValidation(context,path_factory=path_factory,
            prefix=prefix,receipts=receipts,actions=actions,operating=operating,git=git)
    def validate_publication(self,root,base_ref):
        return self.publication.validate_publication(str(root),base_ref)
    def check_accepted_prefix(self,root,base_ref):
        return self.prefix.check_accepted_prefix(str(root),base_ref)
    def validate_pilot(self,root):
        return self.context.ledger.validate_pilot(str(root))
    def validate_overview(self,root):
        return self.context.governance_lifecycle_overview.validate_overview(str(root))
    def validate_viewer(self,root,*,overview):
        return self.context.governance_lifecycle_viewer.validate_viewer(str(root),overview=overview)
