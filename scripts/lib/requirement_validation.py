"""Whole original requirement validation over explicit read-only data/history ports.

The kernel retains original declared authority checks without transferring any
recorded decision, activation, source approval or operating authority to a node.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import PurePosixPath
import re
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from referencing.exceptions import NoSuchResource
import yaml
from lib.operations_sources import text
from lib.requirement_validation_budget import yaml_text
from lib.requirement_lifecycle import parse_native_requirement


def refused_resource(uri):
    raise NoSuchResource(ref=uri)


def local_validator(schema, *, retrieve=None, **options):
    def selected_resource(uri):
        if retrieve is None:
            return refused_resource(uri)
        return Resource.from_contents(json.loads(text(retrieve(uri))), default_specification=DRAFT202012)
    return Draft202012Validator(schema, registry=Registry(retrieve=selected_resource), **options)


class NativePath:
    def __init__(self,path): self.path=path
    def __str__(self): return str(self.path)
    def read_text(self,encoding='utf-8'):
        value=self.path.read_text(encoding=encoding)
        match=re.match(r'\A---\s*\n(.*?)\n---\s*(?:\n|$)(.*)\Z',value,re.DOTALL)
        if match: yaml_text(match.group(1))
        return value


def bounded_native_requirement(path):
    return parse_native_requirement(NativePath(path))


class RequirementValidation:
    def __init__(self,root,history,review_paths,resource=None):
        self.validator=lambda schema,**options:local_validator(schema,retrieve=resource,**options)
        self.root=root
        self.history=history
        self.review_paths=review_paths
        self.catalog=root/'model/requirements/governance-requirement-catalog.yaml'
        self.ledger=root/'model/requirements/requirement-authority-ledger.yaml'
        self.cases=root/'model/requirements/lifecycle-cases'
        self.publication=root/'docs/publishing/governance-requirement-catalog/publication.yaml'
        self.artifact_register=root/'model/requirements/requirement-to-artifact-register.yaml'
        self.policy_review_root=root/'docs/governance/review-packets'
        self.derived_prefixes=('model/controls/','model/platform/','architecture/','policies/opa/')

    def git_value(self,base_ref,path):
        raw=self.history.previous(base_ref,path.relative_to(self.root).as_posix())
        if raw is None:return None
        return json.loads(raw) if path.suffix=='.json' else yaml_text(raw)

    def git_path_exists(self,base_ref,path):
        return self.history.existed(base_ref,path)

    def changed_paths(self,base_ref):
        return self.history.changed(base_ref)

    def read(self, path: PurePosixPath):
        if path.suffix == '.json':
            return json.loads(path.read_text(encoding='utf-8'))
        return yaml_text(path.read_text(encoding='utf-8'))

    def validate_schema(self, path: PurePosixPath, schema_name: str, errors: list[str]) -> None:
        schema = self.read(self.root / 'schemas' / schema_name)
        validator = self.validator(schema, format_checker=FormatChecker())
        for issue in sorted(validator.iter_errors(self.read(path)), key=lambda item: list(item.absolute_path)):
            location = '.'.join((str(part) for part in issue.absolute_path)) or '<root>'
            errors.append(f'{path.relative_to(self.root)} at {location}: {issue.message}')

    def validate_instance(self, instance: dict, schema_name: str, label: str, errors: list[str]) -> None:
        validator = self.validator(self.read(self.root / 'schemas' / schema_name), format_checker=FormatChecker())
        for issue in sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path)):
            location = '.'.join((str(part) for part in issue.absolute_path)) or '<root>'
            errors.append(f'{label} at {location}: {issue.message}')

    def validate_immutable_history(self, base_ref: str, catalog: dict, case_paths: list[PurePosixPath], errors: list[str]) -> None:
        previous_catalog = self.git_value(base_ref, self.catalog)
        if previous_catalog:
            current_by_id = {item['id']: item for item in catalog['requirements']}
            for old in previous_catalog['requirements']:
                current = current_by_id.get(old['id'])
                if current is None:
                    errors.append(f"previous requirement deleted: {old['id']}")
                elif current['revisions'][:len(old['revisions'])] != old['revisions']:
                    errors.append(f"immutable requirement revision changed: {old['id']}")
        for path in case_paths:
            old = self.git_value(base_ref, path)
            if old is None:
                continue
            current = self.read(path)
            if old['source'] != current['source'] or len(old['proposals']) != len(current['proposals']):
                errors.append(f"immutable lifecycle intake changed: {current['case_id']}")
                continue
            for before, after in zip(old['proposals'], current['proposals']):
                for field in ('proposal_id', 'source_requirement_id', 'title', 'statement', 'normative_strength', 'domain'):
                    if before[field] != after[field]:
                        errors.append(f"immutable proposal field changed: {before['proposal_id']}.{field}")
                if before['decision'] is not None and before['decision'] != after['decision']:
                    errors.append(f"recorded decision changed: {before['proposal_id']}")
                if before['decision'] is not None and before['analysis'] != after['analysis']:
                    errors.append(f"analysis changed after decision: {before['proposal_id']}")
                if before['activation'] is not None and before['activation'] != after['activation']:
                    errors.append(f"recorded activation changed: {before['proposal_id']}")

    def validate_artifact_register(self, register: dict, catalog: dict, ledger: dict, base_ref: str | None, errors: list[str], source_map: dict[str, str] | None=None) -> None:
        active: dict[str, dict] = {}
        for requirement in catalog['requirements']:
            revision = next((item for item in requirement['revisions'] if item['revision'] == requirement['active_revision']), None)
            if revision and revision['status'] == 'effective':
                active[f"{requirement['id']}@rev{revision['revision']}"] = revision
        effective_entries: dict[str, list[dict]] = {}
        ids = set()
        for entry in register['entries']:
            if entry['id'] in ids:
                errors.append(f"duplicate artifact register ID: {entry['id']}")
            ids.add(entry['id'])
            revision = active.get(entry['requirement_ref'])
            if revision is None:
                errors.append(f"{entry['id']} references an unknown or inactive requirement revision")
                continue
            artifact = entry['artifact']
            if artifact['type'] not in revision['authorized_derivations']:
                errors.append(f"{entry['id']} uses unauthorized artifact type {artifact['type']}")
            if entry['enforcement'] != revision['runtime_enforcement']:
                errors.append(f"{entry['id']} enforcement differs from its exact requirement revision")
            path = self.root / artifact['path']
            if not path.is_file():
                errors.append(f"{entry['id']} artifact is missing: {artifact['path']}")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != artifact['sha256']:
                errors.append(f"{entry['id']} artifact hash changed: {artifact['path']}")
            decision_ref = self.root / entry['decision']['decision_ref']
            if not decision_ref.is_file():
                errors.append(f"{entry['id']} decision reference is missing")
            if entry['decision']['status'] == 'effective':
                if entry['decision']['equivalence'] != 'equivalent':
                    errors.append(f"{entry['id']} is effective without confirmed equivalence")
                effective_entries.setdefault(artifact['path'], []).append(entry)
        git_sources = {item['source_id'] for item in ledger['sources'] if item['authority_mode'] == 'git_authoritative'}
        source_map = source_map or {}
        for entry in register['entries']:
            entry_sources = {source_map.get(ref, ref) for ref in entry['source_requirement_refs']}
            if git_sources.intersection(entry_sources) and entry['decision']['kind'] != 'derivation':
                errors.append(f"{entry['id']} retains legacy adoption after source became git_authoritative")
        if not base_ref:
            return
        changes = self.changed_paths(base_ref)
        for path in sorted(changes):
            if path.startswith('releases/') and self.git_path_exists(base_ref, path):
                errors.append(f'published release artifact changed: {path}')
            if path.startswith(self.derived_prefixes):
                current = self.root / path
                if current.is_file() and path not in effective_entries:
                    errors.append(f'new or changed normative artifact requires an effective GRQ mapping: {path}')

    def validate_policy_reviews(self, catalog: dict, artifact_register: dict, errors: list[str]) -> None:
        active = {f"{requirement['id']}@rev{requirement['active_revision']}": next((item for item in requirement['revisions'] if item['revision'] == requirement['active_revision'])) for requirement in catalog['requirements'] if requirement['active_revision'] is not None}
        for path in sorted(self.review_paths('OPA-*/review.json')):
            self.validate_schema(path, 'requirement-policy-equivalence-review.schema.json', errors)
            review = self.read(path)
            mappings = review.get('mappings', [])
            pairs = set()
            for mapping in mappings:
                pair = (mapping['requirement_ref'], mapping['policy_path'])
                if pair in pairs:
                    errors.append(f"{review['review_id']} contains duplicate mapping {pair}")
                pairs.add(pair)
                revision = active.get(mapping['requirement_ref'])
                if revision is None:
                    errors.append(f"{review['review_id']} references inactive requirement {mapping['requirement_ref']}")
                elif 'policies' not in revision['authorized_derivations']:
                    errors.append(f"{mapping['requirement_ref']} does not authorize policy derivation")
                policy = self.root / mapping['policy_path']
                if not policy.is_file():
                    errors.append(f"{review['review_id']} policy is missing: {mapping['policy_path']}")
                elif hashlib.sha256(policy.read_bytes()).hexdigest() != mapping['policy_sha256']:
                    errors.append(f"{review['review_id']} policy hash changed: {mapping['policy_path']}")
            counts = {name: sum((item['assessment'] == name for item in mappings)) for name in ('equivalent', 'partial', 'not_equivalent')}
            summary = review['summary']
            if summary['mapping_count'] != len(mappings) or any((summary[name] != value for name, value in counts.items())):
                errors.append(f"{review['review_id']} summary does not match its mappings")
            if summary['policy_file_count'] != len({item['policy_path'] for item in mappings}):
                errors.append(f"{review['review_id']} policy file count is incorrect")
            decision = review.get('decision')
            if review['status'] == 'decided' and decision:
                decision_ref = self.root / decision['decision_ref']
                if not decision_ref.is_file():
                    errors.append(f"{review['review_id']} decision reference is missing")
                dispositions = decision['approved'] + decision['withheld'] + decision['rejected'] + decision['correction_required']
                refs = [item['requirement_ref'] for item in mappings]
                if len(dispositions) != len(set(dispositions)) or set(dispositions) != set(refs):
                    errors.append(f"{review['review_id']} decision does not disposition every mapping exactly once")
                assessment = {item['requirement_ref']: item['assessment'] for item in mappings}
                if any((assessment.get(ref) != 'equivalent' for ref in decision['approved'])):
                    errors.append(f"{review['review_id']} approves a mapping not assessed equivalent")
                effective = {entry['requirement_ref'] for entry in artifact_register['entries'] if entry['decision']['status'] == 'effective' and entry['artifact']['type'] == 'policies' and (entry['decision']['decision_ref'] == decision['decision_ref'])}
                if effective != set(decision['approved']) or summary['effective_register_entries'] != len(effective):
                    errors.append(f"{review['review_id']} effective register entries do not match its approvals")

    def validate_pra_reviews(self, errors: list[str]) -> None:
        for path in sorted(self.review_paths('PRA-*/review.json')):
            self.validate_schema(path, 'pra-requirement-platform-review.schema.json', errors)
            review = self.read(path)
            source_path = self.root / review['source']['source_path']
            if not source_path.is_file():
                errors.append(f"{review['review_id']} source is missing")
            elif hashlib.sha256(source_path.read_bytes()).hexdigest() != review['source']['source_sha256']:
                errors.append(f"{review['review_id']} source hash changed")
            ids = [row['source_requirement_id'] for row in review['requirements']]
            if len(ids) != len(set(ids)):
                errors.append(f"{review['review_id']} contains duplicate source requirements")
            if review['status'] == 'review_required' and any((row['requirement_decision'] is not None or row['platform_equivalence_decision'] is not None for row in review['requirements'])):
                errors.append(f"{review['review_id']} records decisions while review is still required")

    def validate(self, base_ref=None) -> dict:
        errors: list[str] = []
        self.validate_schema(self.catalog, 'governance-requirement-catalog.schema.json', errors)
        self.validate_schema(self.ledger, 'requirement-authority-ledger.schema.json', errors)
        self.validate_schema(self.artifact_register, 'requirement-artifact-register.schema.json', errors)
        case_paths = sorted(self.cases.glob('*.json')) if self.cases.exists() else []
        for path in case_paths:
            self.validate_schema(path, 'requirement-lifecycle-case.schema.json', errors)
        catalog = self.read(self.catalog)
        ledger = self.read(self.ledger)
        artifact_register = self.read(self.artifact_register)
        self.validate_policy_reviews(catalog, artifact_register, errors)
        self.validate_pra_reviews(errors)
        ids = [item['id'] for item in catalog['requirements']]
        if len(ids) != len(set(ids)):
            errors.append('canonical requirement IDs must be unique')
        expected_next = max([int(item.split('-')[-1]) for item in ids], default=0) + 1
        if catalog['next_sequence'] != expected_next:
            errors.append('catalog next_sequence does not follow the highest allocated ID')
        known = set(ids)
        source_refs = set()
        for requirement in catalog['requirements']:
            revision_numbers = [item['revision'] for item in requirement['revisions']]
            if revision_numbers != list(range(1, len(revision_numbers) + 1)):
                errors.append(f"{requirement['id']} revisions must be contiguous and ordered")
            active = next((item for item in requirement['revisions'] if item['revision'] == requirement['active_revision']), None)
            if active is None or active['status'] != 'effective':
                errors.append(f"{requirement['id']} active revision must exist and be effective")
            for revision in requirement['revisions']:
                for source_ref in revision['source_refs']:
                    source_refs.add(source_ref)
                for relation in revision['relationships']:
                    relation_id = relation['target'].split('@rev', 1)[0]
                    if relation_id.startswith('GRQ-') and relation_id not in known:
                        errors.append(f"{requirement['id']} references unknown requirement {relation['target']}")
                if revision['runtime_enforcement'] == 'blocking':
                    errors.append(f"{requirement['id']} activates blocking without a separate enforcement contract")
        ledger_ids = [item['source_id'] for item in ledger['sources']]
        if len(ledger_ids) != len(set(ledger_ids)):
            errors.append('authority ledger source IDs must be unique')
        for source in ledger['sources']:
            path = self.root / source['source_path']
            if not path.is_file():
                errors.append(f"authority source missing: {source['source_path']}")
            else:
                import hashlib
                if hashlib.sha256(path.read_bytes()).hexdigest() != source['document_sha256']:
                    errors.append(f"authority source hash changed: {source['source_id']}")
            coverage = source['coverage']
            if coverage['unresolved'] != coverage['total'] - coverage['decided']:
                errors.append(f"authority coverage arithmetic invalid: {source['source_id']}")
            if coverage['effective'] > coverage['decided'] or coverage['decided'] > coverage['total']:
                errors.append(f"authority coverage ordering invalid: {source['source_id']}")
            if source['authority_mode'] == 'git_authoritative':
                if coverage['unresolved'] != 0 or coverage['effective'] == 0 or (not source['catalog_release']):
                    errors.append(f"git-authoritative source is incomplete: {source['source_id']}")
        activated_refs = set()
        source_map = {}
        proposal_ids = {proposal['proposal_id'] for path in case_paths for proposal in self.read(path)['proposals']}
        proposal_activations = {proposal['proposal_id']: proposal['activation'] for path in case_paths for proposal in self.read(path)['proposals']}
        for path in case_paths:
            case = self.read(path)
            source_map.update({item['source_requirement_id']: case['source']['source_id'] for item in case['proposals']})
            source_path = self.root / case['source']['source_path']
            if not source_path.is_file():
                errors.append(f"lifecycle source missing: {case['source']['source_path']}")
            else:
                import hashlib
                if hashlib.sha256(source_path.read_bytes()).hexdigest() != case['source']['source_sha256']:
                    errors.append(f"lifecycle source hash changed: {case['case_id']}")
            decision_ref = self.root / case['source']['decision_ref']
            if not decision_ref.is_file() or not decision_ref.resolve().is_relative_to((self.root / 'docs/governance/change-requests').resolve()):
                errors.append(f"lifecycle decision reference is invalid: {case['case_id']}")
            if case['intake_type'] == 'native_git' and source_path.is_file():
                try:
                    self.validate_instance(bounded_native_requirement(source_path), 'native-requirement-source.schema.json', case['case_id'], errors)
                except (OSError, ValueError, yaml.YAMLError) as exc:
                    errors.append(f"{case['case_id']} native source invalid: {exc}")
            for proposal in case['proposals']:
                decision = proposal['decision']
                if decision:
                    proposal_decision_ref = self.root / decision['decision_ref']
                    if not proposal_decision_ref.is_file() or not proposal_decision_ref.resolve().is_relative_to((self.root / 'docs/governance/change-requests').resolve()):
                        errors.append(f"{proposal['proposal_id']} decision reference is invalid")
                if decision and decision['disposition'] == 'approve' and (decision['classification'] != 'new'):
                    target = decision['target_requirement_id']
                    valid_targets = known | proposal_ids if decision['classification'] == 'duplicate' else known
                    if target not in valid_targets:
                        errors.append(f"{proposal['proposal_id']} has invalid decision target {target}")
                    if decision['classification'] == 'duplicate' and target in proposal_ids and (proposal_activations[target] is None):
                        errors.append(f"{proposal['proposal_id']} duplicate target is not canonically activated: {target}")
                activation = proposal['activation']
                if activation:
                    activated_refs.add(proposal['source_requirement_id'])
                    if activation['requirement_id'] not in known:
                        errors.append(f"{case['case_id']} activates unknown requirement")
                if proposal['decision'] is None and activation is not None:
                    errors.append(f"{proposal['proposal_id']} activated without decision")
            if case['status'] == 'activated' and any((item['decision'] is None for item in case['proposals'])):
                errors.append(f"{case['case_id']} activated with open decisions")
        if not activated_refs.issubset(source_refs):
            errors.append('activated proposal source references are missing from the canonical catalog')
        if base_ref:
            self.validate_immutable_history(base_ref, catalog, case_paths, errors)
        self.validate_artifact_register(artifact_register, catalog, ledger, base_ref, errors, source_map)
        if not self.publication.is_file():
            errors.append('canonical catalog publication manifest is missing')
        else:
            publication = self.read(self.publication)
            published = {PurePosixPath(item['path']).stem for item in publication['sections'] if item['kind'] == 'requirement'}
            active_ids = {item['id'] for item in catalog['requirements'] if item['active_revision'] is not None}
            if published != active_ids:
                errors.append('canonical catalog publication does not match active catalog requirements')
        if errors:
            return {'exit_code': 1, 'stdout': '', 'stderr': 'Requirement lifecycle validation failed:\n' + ''.join(('- ' + str(error) + '\n' for error in errors))}
        return {'exit_code': 0, 'stdout': 'Requirement lifecycle validation passed\n' + f"- authority sources: {len(ledger['sources'])}\n" + f'- lifecycle cases: {len(case_paths)}\n' + f"- canonical requirements: {len(catalog['requirements'])}\n", 'stderr': ''}
