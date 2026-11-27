"""Entire original GET/PATCH/POST helper; command formatting is explicitly legacy."""
import json
class LegacySelfSecurityPublicationAPI:
 def __init__(self,process,profile):self.process,self.profile=process,profile
 def __call__(self,method,endpoint,payload=None):
  result=self.process.run(self.profile.api_command(method,endpoint,payload),input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True)
  return json.loads(result.stdout) if result.stdout.strip() else {}
