"""Whole release child reconstruction from complete retained data, never a macro report."""
from lib.retained_security_tree import RetainedTree,MAX_FILES,MAX_BYTES,MAX_FILE
from lib.retained_security import release
from lib.requirement_validation_replay import IntegrityError
from pathlib import PurePosixPath
import re


def context_valid(source,node):
    if (type(source) is not str or not PurePosixPath(source).is_absolute() or str(PurePosixPath(source))!=source or '..' in PurePosixPath(source).parts
            or type(node) is not dict or set(node)!={'node_id','runtime_source_digest'}
            or type(node['node_id']) is not str or not re.fullmatch('[a-f0-9]{32}',node['node_id'])
            or type(node['runtime_source_digest']) is not str or not re.fullmatch('[a-f0-9]{64}',node['runtime_source_digest'])):
        raise IntegrityError('provider_observation_release_context_changed')


def report(value,blob,*,source,revision,at,node_context):
    context_valid(source,node_context)
    def require(ok):
        if not ok:raise IntegrityError('provider_observation_release_child_changed')
    require(type(value) is dict and set(value)=={'schema_version','binding','operation','label','directories','files'} and type(value['schema_version']) is int and value['schema_version']==1)
    binding=value['binding'];require(type(binding) is dict and set(binding)=={'node_id','runtime_source_digest','source_revision','source_tree'} and binding['source_revision']==revision and {k:binding[k] for k in node_context}==node_context)
    require(type(value['files']) is dict and len(value['files'])<=MAX_FILES)
    files={};total=0
    try:
        for name,ref in value['files'].items():
            raw=blob(ref);require(type(raw) is bytes and len(raw)<=MAX_FILE);total+=len(raw);require(total<=MAX_BYTES);files[name]=raw
        tree=RetainedTree(value['label'],files,value['directories']);assessment,result=release(tree,binding,value['operation'])
    except IntegrityError:raise
    except (KeyError,ValueError,OSError,TypeError):raise IntegrityError('provider_observation_release_child_changed') from None
    require(assessment['source_root']==source and assessment['assessed_at']==at)
    return result


class ReplayObservationRelease:
    def __init__(self,owner,source,*,node_context):
        context_valid(str(source),node_context);self.owner,self.source,self.node_context=owner,str(source),dict(node_context);self.failure=None
    def report(self,revision,at):
        if self.failure is not None:raise self.failure
        try:
            args={'source_root':self.source,'revision':revision,'observed_at':at,'node_context':self.node_context}
            ok,value=self.owner.outcome('provider-observation-release-child',args,'json')
            if not ok:raise IntegrityError('provider_observation_release_child_incomplete')
            return report(value,self.owner.blob,source=self.source,revision=revision,at=at,node_context=self.node_context)
        except (IntegrityError,ValueError,KeyError,TypeError) as error:
            self.failure=error if isinstance(error,IntegrityError) else IntegrityError('provider_observation_release_child_changed');raise self.failure
