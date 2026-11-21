"""Observed original exclusive-directory creation, including a competing ordinary entry.

An externally created directory is an observation, never an owned product write.
All other mkdir operations retain the existing path/output guards and budgets.
"""
import errno
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import snapshot, RetainedOutputError
from lib.synthetic_lifecycle_io import ReplayIO, path_spec
ACTION = 'preflight-exclusive-directory'

def original_options(mode, parents, exist_ok):
    return type(mode) is int and mode == 511 and (parents is False) and (exist_ok is False)

def finish(owner, path, before, after, *, created, appeared):
    owner.output.observed[path] = after
    if created:
        owner.touched[path] = after
        owner.output.invalidate([path], parents=True)
    elif appeared:
        owner.preflight_external_changes = getattr(owner, 'preflight_external_changes', {})
        owner.preflight_external_changes[path] = after
        owner.output.invalidate([path], parents=True)

def verify(before, after, *, created, appeared, failure):
    if type(created) is not bool or type(appeared) is not bool or (created and appeared):
        raise IntegrityError('preflight_directory_progress_changed')
    if created:
        if before['kind'] != 'missing' or after['kind'] != 'directory' or failure is not None:
            raise IntegrityError('preflight_directory_creation_changed')
    elif appeared:
        if before['kind'] != 'missing' or after['kind'] not in ('file', 'directory') or type(failure) is not dict or (failure.get('type') != 'FileExistsError') or (failure.get('errno') != errno.EEXIST):
            raise IntegrityError('preflight_competing_directory_changed')
    elif after != before or failure is None:
        raise IntegrityError('preflight_failed_directory_changed')

def admit_preimage(owner,path,before,prior):
    # The original exclusive mkdir accepts a newly appeared ordinary target as
    # an EEXIST result. This explicit port owns no such entry and never follows
    # an alias or relaxes checks for other previously observed input paths.
    if owner.metadata.get(path)!=prior:
        raise IntegrityError('preflight_directory_prior_input_changed')
    external=prior=={'kind':'missing'} and before['kind'] in ('file','directory')
    if external:
        if owner.output.observed.get(path) not in (None,{'kind':'missing'}):
            raise IntegrityError('preflight_owned_output_replaced')
        owner.metadata.pop(path,None)
        owner.output.observed.pop(path,None)
        if hasattr(owner,'reads'):owner.reads.pop(path,None)
        if hasattr(owner,'data'):owner.data.observed.pop(path,None)
    owner.output.prior(path,before)
    if external:
        owner.preflight_external_changes=getattr(owner,'preflight_external_changes',{})
        owner.preflight_external_changes[path]=before

class ReplayPreflightIO(ReplayIO):

    def mkdir(self, path, mode, parents, exist_ok, label):
        if self.mode != 'selected-files' or not original_options(mode, parents, exist_ok):
            return super().mkdir(path, mode, parents, exist_ok, label)
        spec = self.output.admit(path,label)
        before = self.row()
        if type(before) is not dict or set(before) != {'kind', 'selection', 'anchor', 'snapshot','input_before'} or before['kind'] != ACTION + '-before' or (before['selection'] != spec):
            raise IntegrityError('preflight_directory_preimage_changed')
        paths = self.output.anchor(before['anchor'], path)
        if paths != [path]:
            raise IntegrityError('preflight_exclusive_directory_parent_required')
        admit_preimage(self,path,before['snapshot'],before['input_before'])
        args = {'selection': spec, 'mode': mode, 'parents': False, 'exist_ok': False, 'export_mode': self.mode}
        (ok, value) = self.outcome(ACTION, args, 'json')
        after = self.row()
        if type(after) is not dict or set(after) != {'kind', 'selection', 'snapshot', 'created', 'external_appearance', 'failure'} or after['kind'] != ACTION + '-after' or (after['selection'] != spec):
            raise IntegrityError('preflight_directory_observation_changed')
        snapshot(after['snapshot'], self.blob)
        verify(before['snapshot'], after['snapshot'], created=after['created'], appeared=after['external_appearance'], failure=after['failure'])
        if ok:
            if value is not None or not after['created']:
                raise IntegrityError('preflight_directory_result_changed')
        else:
            self.output.failure(after['failure'], value)
        finish(self, path, before['snapshot'], after['snapshot'], created=after['created'], appeared=after['external_appearance'])
        if not ok:
            raise RetainedOutputError(value['exception'], value['message'])
        return None
