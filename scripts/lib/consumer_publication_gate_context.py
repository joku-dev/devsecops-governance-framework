"""Complete consumer publication gate over the same original model composition."""
from lib.lifecycle_preflight_context import PreflightPaths
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.synthetic_ledger_store import SyntheticLedgerStore
from lib.consumer_lifecycle_contracts import ConsumerContracts
from lib.consumer_lifecycle_admission import ConsumerAdmission
from lib.consumer_lifecycle_actions import ConsumerActions
from lib.consumer_lifecycle_acceptance import ConsumerAcceptance
from lib.lifecycle_candidate_preparation import CandidateNormalization, ArchitectureCandidateAdapter


class ConsumerPublicationGate:
    def __init__(self,acceptance):self.acceptance=acceptance
    def validate_publication(self,root,base_ref):
        # Rebind the same explicit source label into the consumer namespace;
        # never transfer a publisher path object across model namespaces.
        return self.acceptance.validate_publication(str(root),base_ref)


def build(source,cwd,owner,*,validator_class,ports_factory,profile_factory,provider_factory,
          evidence_factory,effects_factory,exclusive_factory,temporary_factory):
    paths=PreflightPaths(source,cwd,owner,exclusive_factory);root=paths.path(source)
    context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path)
    ports=ports_factory(owner,root,context);central,evidence,process=ports['central'],ports['evidence'],ports['process']
    temporary=temporary_factory(owner);profile=profile_factory(context,central)
    context.provider=provider_factory(context,central)
    options={'path_factory':paths.path,'profile':profile,'process':process,'temporary':temporary,
             'clock':central.clock,'validator_class':validator_class}
    context.consumer_contracts=ConsumerContracts(root,context,**options)
    context.consumer_admission=ConsumerAdmission(root,context,**options)
    context.consumer_actions=ConsumerActions(root,context,**options)
    context.consumer_acceptance=ConsumerAcceptance(root,context,**options)
    architecture=ArchitectureCandidateAdapter(context,CandidateNormalization(context))
    context.consumer_evidence=evidence_factory(root,context,profile,architecture,evidence,process,temporary,central.clock,validator_class,paths.path)
    effects=effects_factory(owner,source=source,transaction_name=lambda raw:context.kernel.transaction_name(context.adapter.strict_json(raw)))
    context.store=SyntheticLedgerStore(context,path_factory=paths.path,native=effects,locking=effects,temporary=effects)
    owner.consumer_publication_process=process;owner.consumer_publication_effects=effects
    return ConsumerPublicationGate(context.consumer_acceptance)
