"""Closed private legacy module semantics over the admitted security kernel.

The original loader call sequence is retained as an explicit port. No selected
source program is imported, fetched or executed by this factory or its replay.
"""
from types import ModuleType,SimpleNamespace
from lib.requirement_validation_budget import InputAdmissionError


class PrivateSecurityModules:
    def __init__(self,root,*,collector_factory,observed_values,timed_collector_factory=None):
        self.root,self.collector_factory,self.values=root,collector_factory,observed_values
        self.timed_collector_factory=timed_collector_factory
        self.util=self;self.specifications=[];self.modules=[]
    def spec_from_file_location(self,name,path):
        expected=str(self.root)+'/scripts/assess_governance_repository_security.py'
        if name!='axiom_private_github_security' or str(path)!=expected:
            raise InputAdmissionError('provider_observation_private_module_profile_changed')
        spec=SimpleNamespace(name=name,origin=str(path),loader=self,owner=self)
        self.specifications.append(spec);return spec
    def module_from_spec(self,spec):
        if not any(spec is known for known in self.specifications):
            raise InputAdmissionError('provider_observation_foreign_module_specification')
        module=ModuleType(spec.name);module.__spec__=spec;module.ROOT=self.root
        module.gh_api=None;module._observation_initialized=False
        module.observed_values=self.values
        def collect_live(repository,observed_at):
            if not module._observation_initialized or not callable(module.gh_api):
                raise InputAdmissionError('provider_observation_private_module_not_bound')
            collector=self.collector_factory(module.gh_api) if self.timed_collector_factory is None else self.timed_collector_factory(module.gh_api,observed_at)
            return collector.collect_live(repository,observed_at)
        module.collect_live=collect_live;self.modules.append(module);return module
    def exec_module(self,module):
        if not any(module is known for known in self.modules) or module.__spec__.loader is not self:
            raise InputAdmissionError('provider_observation_foreign_private_module')
        module._observation_initialized=True
