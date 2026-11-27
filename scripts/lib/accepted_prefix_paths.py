"""Pure original prefix path-probe observations, including symlinks and non-files."""
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError
from lib.workbook_import_io import READ_ERRORS
from lib.accepted_prefix_protocol import LegacyAcceptedPrefixProtocol


def probe_value(wire,spec):
    def need(value,reason):
        if not value:raise IntegrityError('accepted_prefix_path_'+reason)
    need(type(wire) is dict and set(wire)=={'schema_version','specification','before','after','result','failure'} and type(wire['schema_version']) is int and wire['schema_version']==1 and wire['specification']==spec,'wire_changed')
    need(type(wire['before']) is dict and wire['before']==wire['after'],'path_changed')
    state=wire['before'];need(state.get('kind') in ('missing','file','directory','symlink','other','unavailable'),'kind_changed')
    if state['kind']=='missing':need(state=={'kind':'missing'},'missing_shape')
    elif state['kind']=='unavailable':
        need(set(state)=={'kind','failure'} and type(state['failure']) is dict,'unavailable_shape')
        diagnostic=state['failure']
        need(set(diagnostic)=={'type','message','errno','strerror','filename'} and diagnostic['type'] in READ_ERRORS
            and type(diagnostic['errno']) is int and type(diagnostic['strerror']) is str and diagnostic['filename']==spec['path'],'unavailable_error')
        need(str(READ_ERRORS[diagnostic['type']](diagnostic['errno'],diagnostic['strerror'],diagnostic['filename']))==diagnostic['message'],'unavailable_diagnostic')
    else:
        fields={'kind','identity','mode','uid','nlink','bytes','mtime_ns','ctime_ns','link'}
        need(set(state)==fields and type(state['identity']) is list and len(state['identity'])==2 and all(type(n) is int and n>=0 for n in state['identity']),'metadata_shape')
        need(all(type(state[k]) is int for k in fields-{'kind','identity','link'}) and 0<=state['mode']<=0o777,'metadata_values')
        need(type(state['link']) is str if state['kind']=='symlink' else state['link'] is None,'link_changed')
    error=wire['failure']
    if error is not None:
        need(wire['result'] is None and type(error) is dict and set(error)=={'type','message','errno','strerror','filename'} and error['type'] in READ_ERRORS,'error_shape')
        need(type(error['errno']) is int and type(error['strerror']) is str and error['filename'] in (None,spec['label']),'error_binding')
        actual=READ_ERRORS[error['type']](error['errno'],error['strerror'],error['filename']);need(str(actual)==error['message'],'error_diagnostic')
        raise RetainedOutputError(error['type'],error['message'])
    need(type(wire['result']) is bool,'result_changed')
    if state['kind']=='unavailable':return wire['result']
    if spec['probe']=='is_symlink':need(wire['result']==(state['kind']=='symlink'),'symlink_result_changed')
    elif state['kind']!='symlink':need(wire['result']==(state['kind']=='file'),'file_result_changed')
    # For a symlink, is_file follows the target. The captured boolean is an
    # external filesystem observation, not an independent target attestation.
    return wire['result']

class ReplayPrefixPaths:
    def __init__(self,owner,root,context):self.owner,self.root,self.profile=owner,str(root),LegacyAcceptedPrefixProtocol(context)
    def probe(self,path,kind,label):
        self.profile.hashed_path(path,self.root)
        spec={'path':path,'probe':kind,'label':label}
        if kind not in ('is_file','is_symlink'):raise IntegrityError('accepted_prefix_path_probe_changed')
        ok,wire=self.owner.outcome('accepted-prefix-path-probe',spec,'json')
        if not ok:raise IntegrityError('accepted_prefix_path_capture_incomplete')
        return probe_value(wire,spec)
