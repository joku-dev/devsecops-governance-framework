"""Whole original provider POST helper, selected only by legacy composition."""
from __future__ import annotations
import json

class LegacyOperationalPublicationAPI:

    def __init__(self, process, profile):
        self.process, self.profile = (process, profile)

    def __call__(self, endpoint: str, payload: dict) -> dict:
        result = self.process.run(self.profile.api_command(endpoint), input=json.dumps(payload), text=True, capture_output=True, check=True)
        return json.loads(result.stdout) if result.stdout.strip() else {}
