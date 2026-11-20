"""Complete operational observation assembly over explicit acquisition ports.

All source/API/program selection belongs to adapters. The supplied environment
may fail individual reads; partial observations retain original error families.
"""
from lib.report_intake_health import build_payload as intake_health


class AcquisitionFailure(ValueError):
    """An adapter-declared legacy transport family with a retained native cause."""
    FAMILIES=frozenset(('CalledProcessError','TimeoutExpired','SubprocessError'))
    def __init__(self,family):
        if family not in self.FAMILIES:raise ValueError('operations_unknown_transport_family')
        self.family=family
        super().__init__('operations_read_unavailable')


def collect(config,now,environment):
    repository=config['repository']
    observation={'observed_at':now.isoformat(),'errors':[],'workflow_runs':{},'indexes':{}}

    def capture(source,operation):
        try:return operation()
        except (OSError,ValueError,KeyError,TypeError) as error:
            family=error.family if isinstance(error,AcquisitionFailure) else type(error).__name__
            observation['errors'].append({'source':source,'error':family})
            return None

    observation['main_head']=capture('main_head',lambda:environment.main_reference(repository)['object']['sha'])
    for name,event in environment.workflow_queries(config).items():
        runs=capture('workflow:'+name,lambda:environment.workflow_runs(repository,name,event)['workflow_runs'])
        observation['workflow_runs'][name]=runs
        if runs is not None and len(runs)==100:
            observation['errors'].append({'source':'workflow:'+name,'error':'ResultLimitReached'})
    observation['pull_requests']=capture('pull_requests',lambda:environment.pull_requests(repository))
    if observation['pull_requests'] is not None and len(observation['pull_requests'])==1000:
        observation['errors'].append({'source':'pull_requests','error':'ResultLimitReached'})
    observation['registry']=capture('registry',environment.registry)
    for domain in environment.index_domains():
        observation['indexes'][domain]=capture('index:'+domain,lambda:environment.index(domain))

    def health():
        if any(index is None for index in observation['indexes'].values()):
            raise ValueError('Missing result index')
        return intake_health(events=environment.records('intake-events'),
            attempts=environment.records('collection-attempts'),
            snapshots=environment.records('results')+environment.records('architecture-results')+environment.records('typed-evidence-results'),
            intake_conflict_count=len(environment.records('intake-conflicts')),
            indexes=observation['indexes'],as_of=now)
    observation['intake_health']=capture('intake_health',health)
    observation['security']=capture('security',lambda:environment.security(repository,now.isoformat()))
    return observation
