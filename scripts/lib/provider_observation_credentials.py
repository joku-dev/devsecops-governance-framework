"""Opaque credential read capabilities, bound to prior full private-file checks."""
import codecs,json
from lib.provider_observation_context import SecretText
from lib.provider_observation_private_ports import require
from lib.intake_atomic_effects import original_error
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError


def intent(metadata,path,credential,position):
    selected=metadata.selection(metadata.path(path))
    require(selected['path']==credential and credential in metadata.successful_private_checks,'credential_private_check_missing')
    return {'kind':'provider-credential-read-intent','operation':position,'selection':selected,
        'private_stat':metadata.successful_private_checks[credential],'identifier':'credential-1'}


class ReplayCredentialCapability:
    def __init__(self,cursor,metadata,*,credential):self.cursor,self.metadata,self.credential=cursor,metadata,credential;self.used=False;self.failure=None
    def read(self,path):
        if self.failure is not None:raise self.failure
        try:
            require(not self.used,'credential_read_repeated');expected=intent(self.metadata,path,self.credential,self.cursor.position);row=self.cursor.row()
            require(json.dumps(row,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False),'credential_intent_changed');row=self.cursor.row()
            require(type(row) is dict and set(row)=={'kind','operation','encoding','error'} and row['kind']=='provider-credential-read-outcome'
                and type(row['operation']) is int and row['operation']==expected['operation'],'credential_completion_changed');self.used=True
            if row['error'] is not None:
                require(row['encoding'] is None,'failed_credential_has_encoding');raise original_error(row['error'])
            require(type(row['encoding']) is str and 1<=len(row['encoding'])<=128,'credential_codec_changed')
            try:codecs.lookup(row['encoding'])
            except LookupError:raise IntegrityError('provider_private_credential_codec_unknown') from None
            return SecretText('credential-1')
        except (IntegrityError,InputAdmissionError) as error:self.failure=error;raise
