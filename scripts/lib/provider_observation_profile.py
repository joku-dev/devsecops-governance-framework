"""Recorded explicitly checked profile data, including root-owned service ACL files."""
import io,json
from lib.provider_observation_private_ports import require
from lib.intake_atomic_effects import original_error
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError

MAX_PROFILE=32*1024**2


def read_intent(metadata,path,profile,position,encoding,errors):
    selected=metadata.selection(metadata.path(path))
    require(selected['path']==profile and profile in metadata.successful_private_checks,'profile_private_check_missing')
    require(encoding=='utf-8' and errors is None,'original_profile_text_contract_changed')
    return {'kind':'provider-profile-read-intent','operation':position,'selection':selected,
        'private_stat':metadata.successful_private_checks[profile],'encoding':encoding,'errors':errors}


def decoded(raw,encoding,errors):
    with io.TextIOWrapper(io.BytesIO(raw),encoding=encoding,errors=errors) as stream:return stream.read()


class ReplayCheckedProfile:
    def __init__(self,cursor,metadata,blob,*,profile):self.cursor,self.metadata,self.blob,self.profile=cursor,metadata,blob,profile;self.failure=None
    def read(self,path,encoding,errors):
        if self.failure is not None:raise self.failure
        try:
            expected=read_intent(self.metadata,path,self.profile,self.cursor.position,encoding,errors);row=self.cursor.row()
            require(json.dumps(row,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False),'profile_intent_changed');row=self.cursor.row()
            require(type(row) is dict and set(row)=={'kind','operation','content','error'} and row['kind']=='provider-profile-read-outcome'
                and type(row['operation']) is int and row['operation']==expected['operation'],'profile_completion_changed')
            if row['error'] is not None:
                require(row['content'] is None,'failed_profile_has_content');raise original_error(row['error'])
            try:raw=self.blob(row['content'])
            except (ValueError,OSError,KeyError,TypeError):raise IntegrityError('provider_private_profile_blob_changed') from None
            require(type(raw) is bytes and len(raw)<=MAX_PROFILE and len(raw)==expected['private_stat']['st_size'],'profile_bytes_changed')
        except (IntegrityError,InputAdmissionError) as error:self.failure=error;raise
        # A genuine original UnicodeDecodeError is recomputed from profile data,
        # never confused with an integrity failure or a credential payload.
        return decoded(raw,encoding,errors)
