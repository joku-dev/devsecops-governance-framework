"""Explicit native composition; callers supply the actual lifecycle gate object.

This library does not activate a publisher service or grant operating consent.
Native invocation can leave committed/pushed branches and remote proposals after
partial failure, exactly as the original flow. There is no automatic rollback.
"""
import argparse,os
from pathlib import Path
from lib.operational_publication import OperationalPublisher
from lib.providers.operational_publication_profile import LegacyOperationalPublicationProfile
from lib.providers.operational_publication_process import NativeOperationalPublicationProcess
from lib.providers.operational_publication_api import LegacyOperationalPublicationAPI

def native_publisher(root,*,scope,repository,run_id,attempt,gates,argv=(),environment=None,provider_executable='gh',local_origin_root=None):
    profile=LegacyOperationalPublicationProfile();environment=dict(os.environ if environment is None else environment)
    process=NativeOperationalPublicationProcess(root,scope=scope,repository=repository,run_id=run_id,attempt=attempt,profile=profile,environment=environment,provider_executable=provider_executable,local_origin_root=local_origin_root)
    publisher=OperationalPublisher(Path(root),path_factory=Path,process=process,api=LegacyOperationalPublicationAPI(process,profile),gates=gates,profile=profile,environment=environment,argument_parser=lambda **kw:argparse.ArgumentParser(prog='publish_operational_update.py',**kw),argv=argv)
    return publisher,process
