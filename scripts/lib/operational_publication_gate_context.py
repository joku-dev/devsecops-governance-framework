"""Shared full model and helper composition; native/replay transports are ports."""
from lib.lifecycle_preflight_context import PreflightPaths
from lib.synthetic_lifecycle_context import LifecyclePaths
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.lifecycle_ledger_validation_context import PrefixRootBinding
from lib.accepted_prefix import AcceptedPrefix
from lib.pilot_receipt_verification import PilotReceiptVerification
from lib.pilot_action_verification import PilotActionVerification
from lib.operating_verification import OperatingVerification
from lib.operational_publication_gates import OperationalPublicationGates

def build(source,cwd,owner,*,validator_class,ports_factory,provider_factory,
          fresh_factory,prefix_paths_factory,temporary_factory,exclusive_factory):
    paths=PreflightPaths(source,cwd,owner,exclusive_factory);root=paths.path(source)
    context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path)
    ports=ports_factory(owner,root,context)
    context.provider=provider_factory(context,ports['personal'])
    prefix_paths=LifecyclePaths(source,cwd,prefix_paths_factory(owner,root,context))
    prefix=PrefixRootBinding(source,AcceptedPrefix(context,path_factory=prefix_paths.path,transport=ports['prefix']))
    receipts=PilotReceiptVerification(context,fresh_factory(context,ports['receipts']),path_factory=paths.path,
        temporary=temporary_factory(owner),clock=ports['receipts'].clock,git=ports['receipts'])
    actions=PilotActionVerification(context,path_factory=paths.path,git=ports['actions'])
    operating=OperatingVerification(root,context,path_factory=paths.path,git=ports['operating'])
    return OperationalPublicationGates(context,path_factory=paths.path,prefix=prefix,
        receipts=receipts,actions=actions,operating=operating,git=ports['publication'])
