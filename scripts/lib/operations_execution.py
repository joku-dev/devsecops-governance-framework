"""Complete original execution order over selected source, clock and output ports.

The environment owns acquisition admission, including any null-observation
fallback. A provided observation never grants permission for external effects.
"""
import json
from jsonschema import Draft202012Validator
from lib.operations_reporting import timestamp,build_report,render_markdown


FILES=('governance-operations.json','operations-observation.json','governance-operations.md')


def execute(*,provided_observation,as_of,environment,output,profile):
    config=json.loads(environment.config_text())
    schema=json.loads(environment.schema_text())
    Draft202012Validator(schema['properties']['thresholds']).validate(config)
    observation=json.loads(environment.observation_text()) if provided_observation else None
    requested=as_of or (observation or {}).get('observed_at')
    now=timestamp(requested) if requested else environment.utc_now()
    if observation is None:
        # This is an explicit port; the outer selected mode must admit live
        # collection before it can call any native source/API operation.
        observation=environment.collect(config,now)
    checkout_sha=environment.checkout_sha()
    report=build_report(observation,config,now,checkout_sha,profile=profile)
    Draft202012Validator(schema,format_checker=Draft202012Validator.FORMAT_CHECKER).validate(report)
    output.mkdir()
    for name,value in ((FILES[0],report),(FILES[1],observation)):
        output.write(name,(json.dumps(value,indent=2)+'\n').encode('utf-8'))
    output.write(FILES[2],render_markdown(report).encode('utf-8'))
    return {'exit_code':0,'stdout':f"Operations report: {report['overall_status']} {report['summary']}\n",'stderr':''}
