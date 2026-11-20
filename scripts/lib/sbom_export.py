"""Complete commit-bound SPDX export decisions over explicit finite ports.

Collection, credential admission, polling waits, time, output paths and durable
native effects belong to selected adapters. This module selects no URL, provider,
program, environment variable, authority or canonical result destination.
"""
import json
import re

POLL_ATTEMPTS=18
POLL_INTERVAL_SECONDS=5

def validate_spdx(raw: bytes, identity: dict) -> dict:
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(identity["invalid_json_message"]) from error
    if isinstance(document, dict) and isinstance(document.get("sbom"), dict):
        document = document["sbom"]
    if not isinstance(document, dict):
        raise ValueError("SBOM must be an SPDX JSON object")
    if document.get("spdxVersion") not in {"SPDX-2.2", "SPDX-2.3"}:
        raise ValueError("SBOM has no supported SPDX version")
    if not isinstance(document.get("documentNamespace"), str) or not document["documentNamespace"].startswith("https://"):
        raise ValueError("SBOM has no valid SPDX document namespace")
    creation = document.get("creationInfo")
    if not isinstance(creation, dict) or not isinstance(creation.get("created"), str):
        raise ValueError("SBOM has no SPDX creation timestamp")
    packages = document.get("packages")
    if not isinstance(packages, list) or not packages:
        raise ValueError("SBOM contains no dependency packages")
    if not all(isinstance(item, dict) and item.get("name") and item.get("SPDXID") for item in packages):
        raise ValueError("SBOM contains a malformed package entry")
    relationships = document.get("relationships")
    if isinstance(relationships, list):
        described_ids = {
            item.get("relatedSpdxElement")
            for item in relationships
            if isinstance(item, dict)
            and item.get("spdxElementId") == "SPDXRef-DOCUMENT"
            and item.get("relationshipType") == "DESCRIBES"
        }
    else:
        described_ids = set()
    described_packages = [item for item in packages if item.get("SPDXID") in described_ids]
    if not described_packages:
        raise ValueError("SBOM does not identify the repository root package")
    expected_names = {name.casefold() for name in identity["root_names"]}
    expected_purl_prefix = identity["root_purl_prefix"].casefold()
    matching_roots = []
    for package in described_packages:
        name_matches = str(package.get("name", "")).casefold() in expected_names
        external_refs = package.get("externalRefs")
        if not isinstance(external_refs, list):
            external_refs = []
        purl_matches = any(
            isinstance(reference, dict)
            and reference.get("referenceType") == "purl"
            and isinstance(reference.get("referenceLocator"), str)
            and reference["referenceLocator"].casefold().startswith(expected_purl_prefix)
            for reference in external_refs
        )
        if name_matches or purl_matches:
            matching_roots.append(package)
    if len(matching_roots) != 1:
        raise ValueError("SBOM repository identity does not match the requested repository")
    return document


def current_default_branch_sha(repository, environment):
    status, metadata = environment.repository_metadata(repository)
    if status != 200 or not isinstance(metadata.get('default_branch'), str):
        raise RuntimeError('Could not determine the repository default branch')
    branch = metadata['default_branch']
    status, commit = environment.branch_commit(repository, branch)
    sha = commit.get('sha') if status == 200 else None
    if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise RuntimeError('Could not determine the current default-branch commit')
    return branch, sha


def validate_request(request, errors):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', request['repository']):
        raise ValueError(errors['repository'])
    if not re.fullmatch(r'[0-9a-f]{40}', request['expected_sha']):
        raise ValueError(errors['commit'])
    if not request['token_available'] and not request.get('anonymous_public',False):
        raise ValueError(errors['token'])


def generate(request, environment, output):
    """The complete original branch/write/clock order, without native effects."""
    repository, expected_sha = request['repository'], request['expected_sha']
    validate_request(request, {name:environment.request_error(name) for name in ('repository','commit','token')})
    event_ref = request['event_ref']
    branch, before_sha = current_default_branch_sha(repository, environment)
    if event_ref and event_ref != f'refs/heads/{branch}':
        raise ValueError('SBOM generation must run from the default branch')
    if before_sha != expected_sha:
        raise ValueError('Workflow commit is not the current default-branch HEAD')
    status, payload = environment.generate_report(repository)
    locator = environment.report_locator(payload) if status == 201 else None
    identifier = environment.report_identifier(repository, locator)
    download = None
    for attempt in range(POLL_ATTEMPTS):
        try:
            download = environment.poll_report(repository, identifier)
            break
        except RuntimeError as error:
            if 'HTTP 202' not in str(error) or attempt == POLL_ATTEMPTS - 1:
                raise
            environment.sleep(POLL_INTERVAL_SECONDS)
    if not download:
        raise RuntimeError(environment.generation_timeout_error())
    raw = environment.download(download)
    document = validate_spdx(raw, environment.spdx_identity(repository))
    after_branch, after_sha = current_default_branch_sha(repository, environment)
    if after_branch != branch or after_sha != expected_sha:
        raise RuntimeError('Default branch moved while the SBOM was being generated; retry the workflow')
    output.mkdir()
    sbom_path = output.write('sbom.spdx.json', (json.dumps(document, indent=2, sort_keys=True)+'\n').encode('utf-8'))
    metadata = {
        'schema_version':'1.0.0', 'repository':repository, 'default_branch':branch,
        'commit_sha':expected_sha, 'workflow_ref':event_ref,
        'generated_at':environment.now().isoformat().replace('+00:00','Z'),
        'format':document['spdxVersion'], 'document_namespace':document['documentNamespace'],
        'package_count':len(document['packages']), 'source':environment.source_label(),
    }
    metadata_path = output.write('sbom-metadata.json', (json.dumps(metadata, indent=2, sort_keys=True)+'\n').encode('utf-8'))
    return sbom_path, metadata_path


def run(request, environment, output):
    """Original completed 0/known-failure1 streams; unknown failures stay uncaught."""
    missing = request.get('missing_environment')
    if missing is not None:
        return {'exit_code':2,'stdout':'','stderr':f'Missing required environment variable: {missing}\n'}
    try:
        sbom_path, metadata_path = generate(request, environment, output)
    except (OSError, ValueError, RuntimeError) as error:
        return {'exit_code':1,'stdout':'','stderr':f'SBOM generation failed: {error}\n'}
    return {'exit_code':0,'stdout':f'Validated SPDX SBOM: {sbom_path} ({metadata_path})\n','stderr':''}
