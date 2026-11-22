"""Complete consumer model composition over explicit IO, clocks and verifier ports."""
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.consumer_lifecycle_contracts import ConsumerContracts
from lib.consumer_lifecycle_admission import ConsumerAdmission
from lib.consumer_lifecycle_actions import ConsumerActions
from lib.consumer_lifecycle_acceptance import ConsumerAcceptance
from lib.consumer_lifecycle_program import ConsumerLifecycleProgram
from lib.lifecycle_candidate_preparation import CandidateNormalization,ArchitectureCandidateAdapter

def compose(root,*,path_factory,validator_class,profile_factory,provider_factory,evidence_factory,
            process,temporary,clock,argument_parser,argv=(),description=None,store_factory=None):
    context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=path_factory)
    profile=profile_factory(context);context.provider=provider_factory(context)
    if store_factory is not None:context.store=store_factory(context)
    options={'path_factory':path_factory,'profile':profile,'process':process,'temporary':temporary,'clock':clock,'validator_class':validator_class}
    context.consumer_contracts=ConsumerContracts(root,context,**options)
    context.consumer_admission=ConsumerAdmission(root,context,**options)
    context.consumer_actions=ConsumerActions(root,context,**options)
    context.consumer_acceptance=ConsumerAcceptance(root,context,**options)
    architecture=ArchitectureCandidateAdapter(context,CandidateNormalization(context))
    context.consumer_evidence=evidence_factory(context,profile,architecture)
    program=ConsumerLifecycleProgram(root,context,**options,argument_parser=argument_parser,argv=argv,description=description)
    return context,program
