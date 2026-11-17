"""Candidate requirement authoring, extracted with explicit workspace context.

Source lineage: V1 6b557fefe295b58272d2271326576ca3a3687197 /
scripts/manage_requirement_lifecycle.py. Pure business rules remain shared in
lib.requirement_lifecycle; source CLI and global root are not used by V2.
Historical payload authority fields describe candidate content only. This module
cannot update the installed source, accepted indexes or publish a decision.
"""
from pathlib import Path
import json
import re
import yaml
from lib.requirement_lifecycle import (
    activate_case, analyze_statement, build_native_case, build_source_case, digest,
    load_yaml, parse_native_requirement, shortlist_candidates, record_decision,
    render_requirement_markdown, write_json, write_yaml,
)


class RequirementWorkspace:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.catalog_path = self.root / 'model/requirements/governance-requirement-catalog.yaml'
        self.ledger_path = self.root / 'model/requirements/requirement-authority-ledger.yaml'
        self.register_path = self.root / 'model/documents/source-document-register.yaml'
        self.case_root = self.root / 'model/requirements/lifecycle-cases'
        self.doc_root = self.root / 'docs/governance/requirements'
        self.publication_root = self.root / 'docs/publishing/governance-requirement-catalog'

    def case_path(self, case_id: str) -> Path:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}', case_id):
            raise ValueError('invalid_requirement_case_id')
        return self.case_root / f'{case_id}.json'

    def load_case(self, case_id: str) -> dict:
        return json.loads(self.case_path(case_id).read_text(encoding='utf-8'))

    def source_entry(self, source_id: str) -> dict:
        register = load_yaml(self.register_path)
        source = next((item for item in register['documents'] if item['id'] == source_id), None)
        if source is None:
            raise ValueError(f'unknown registered source: {source_id}')
        if source['status'] != 'approved':
            raise ValueError(f'source must be approved before migration: {source_id}')
        path = Path(source['source_path'])
        if path.is_absolute() or '..' in path.parts or not (self.root / path).resolve().is_relative_to(self.root):
            raise ValueError('unsafe_registered_requirement_source')
        return source

    def import_source(self, args) -> None:
        source = self.source_entry(args.source_id)
        source_path = self.root / source['source_path']
        catalog = load_yaml(self.catalog_path)
        ledger = load_yaml(self.ledger_path)
        if any((item['source_id'] == source['id'] for item in ledger['sources'])):
            raise ValueError(f"authority ledger already contains {source['id']}")
        if self.case_path(args.case_id).exists():
            raise ValueError(f'lifecycle case already exists: {args.case_id}')
        case = build_source_case(case_id=args.case_id, source=source, source_path=source_path, catalog=catalog)
        write_json(self.case_path(args.case_id), case)
        total = len(case['proposals'])
        ledger['sources'].append({'source_id': source['id'], 'source_version': source['version'], 'source_path': source['source_path'], 'document_sha256': digest(source_path), 'authority_mode': 'migration_in_progress', 'owner': source['owner'], 'decision_ref': 'docs/governance/change-requests/GCR-2026-143-hybrid-requirement-lifecycle.md', 'effective_from': '2026-10-09', 'catalog_release': None, 'coverage': {'total': total, 'analyzed': total, 'decided': 0, 'effective': 0, 'unresolved': total}})
        write_yaml(self.ledger_path, ledger)
        print(f'Created {self.case_path(args.case_id).relative_to(self.root)} with {total} proposals')

    def start_native(self, args) -> None:
        source_path = self.root / args.source_path
        if not source_path.is_file():
            raise ValueError('native source path must exist before the case is created')
        if not source_path.resolve().is_relative_to((self.doc_root / 'native-sources').resolve()):
            raise ValueError('native source must stay under docs/governance/requirements/native-sources/')
        if self.case_path(args.case_id).exists():
            raise ValueError(f'lifecycle case already exists: {args.case_id}')
        native = parse_native_requirement(source_path)
        case = build_native_case(case_id=args.case_id, source_id=native['id'], source_path=Path(args.source_path), source_file=source_path, owner=native['owner'], domain=native['domain'], title=native['title'], statement=native['statement'], strength=native['normative_strength'], decision_ref=native['decision_ref'], catalog=load_yaml(self.catalog_path))
        write_json(self.case_path(args.case_id), case)
        print(f'Created {self.case_path(args.case_id).relative_to(self.root)}')

    def decide(self, args) -> None:
        case = self.load_case(args.case_id)
        record_decision(case, proposal_id=args.proposal_id, disposition=args.disposition, classification=args.classification, target_requirement_id=args.target, decided_by=args.decided_by, decision_role=args.decision_role, rationale=args.rationale, authorized_derivations=args.authorized_derivation, runtime_enforcement=args.runtime_enforcement, decision_ref=args.decision_ref)
        write_json(self.case_path(args.case_id), case)
        self.refresh_ledger(case)
        print(f'Recorded decision for {args.proposal_id}')

    def reanalyze_all(self, _) -> None:
        catalog = load_yaml(self.catalog_path)
        paths = sorted(self.case_root.glob('*.json'))
        cases = [(path, json.loads(path.read_text(encoding='utf-8'))) for path in paths]
        corpus = [(proposal['proposal_id'], proposal['statement']) for (_, case) in cases for proposal in case['proposals']]
        for (path, case) in cases:
            for proposal in case['proposals']:
                candidates = shortlist_candidates(proposal['statement'], [item for item in corpus if item[0] != proposal['proposal_id']])
                proposal['analysis'] = analyze_statement(proposal['statement'], catalog, candidates)
            write_json(path, case)
        print(f'Reanalyzed {len(corpus)} proposals across {len(cases)} lifecycle cases')

    def activate(self, args) -> None:
        case = self.load_case(args.case_id)
        catalog = load_yaml(self.catalog_path)
        activate_case(case, catalog, effective_from=args.effective_from, commit=args.commit, proposal_ids=args.proposal_id or None)
        write_json(self.case_path(args.case_id), case)
        write_yaml(self.catalog_path, catalog)
        self.refresh_ledger(case)
        self.sync_publication(catalog)
        scope = ', '.join(args.proposal_id) if args.proposal_id else 'complete case'
        print(f'Activated {args.case_id}: {scope}')

    def publication_requirement_markdown(self, requirement: dict) -> str:
        revision = next((item for item in requirement['revisions'] if item['revision'] == requirement['active_revision']))
        strength = {'MUST': 'required', 'REQUIREMENT': 'required', 'SHOULD': 'recommended', 'MAY': 'informative'}[revision['normative_strength']]
        supersedes = next((item['target'].split('@rev', 1)[0] for item in revision['relationships'] if item['type'] == 'supersedes'), None)
        metadata = {'id': requirement['id'], 'title': revision['title'], 'status': 'effective', 'normative_level': strength, 'owner': revision['owner'], 'effective_from': revision['effective_from'], 'source_ids': revision['source_refs'], 'control_ids': [], 'evidence_types': ['requirement-lifecycle-decision'], 'supersedes': supersedes}
        return '---\n' + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip() + '\n---\n\n' + revision['statement'] + '\n'

    def sync_publication(self, catalog: dict) -> None:
        requirements_root = self.publication_root / 'requirements'
        requirements_root.mkdir(parents=True, exist_ok=True)
        chapter = self.publication_root / 'chapters/01-authority.md'
        chapter.parent.mkdir(parents=True, exist_ok=True)
        chapter.write_text('# Governance Requirement Catalog\n\nThis publication is generated from the active revisions in `model/requirements/governance-requirement-catalog.yaml`. The Requirement Authority Ledger determines the normative representation for every migrating source. Catalog revisions are authoritative only for their recorded active scope.\n', encoding='utf-8')
        sections = [{'path': 'chapters/01-authority.md', 'kind': 'chapter'}]
        active_ids = set()
        for requirement in sorted(catalog['requirements'], key=lambda item: item['id']):
            if requirement['active_revision'] is None:
                continue
            active_ids.add(requirement['id'])
            canonical = self.doc_root / requirement['id'] / f"v{requirement['active_revision']:04d}.md"
            canonical.parent.mkdir(parents=True, exist_ok=True)
            if not canonical.exists():
                canonical.write_text(render_requirement_markdown(requirement), encoding='utf-8')
            publication = requirements_root / f"{requirement['id']}.md"
            publication.write_text(self.publication_requirement_markdown(requirement), encoding='utf-8')
            sections.append({'path': f"requirements/{requirement['id']}.md", 'kind': 'requirement'})
        for stale in requirements_root.glob('GRQ-*.md'):
            if stale.stem not in active_ids:
                stale.unlink()
        manifest = {'schema_version': 1, 'id': 'GOVERNANCE-REQUIREMENT-CATALOG', 'version': catalog['version'], 'title': 'Governance Requirement Catalog', 'language': 'de-DE', 'status': 'approved', 'publication_class': 'normative', 'source_of_truth': 'canonical_requirement_catalog', 'outputs': ['html', 'docx', 'pdf'], 'sections': sections}
        write_yaml(self.publication_root / 'publication.yaml', manifest)

    def generate_publication(self, _) -> None:
        self.sync_publication(load_yaml(self.catalog_path))
        print(f'Synchronized {self.publication_root.relative_to(self.root)}')

    def refresh_ledger(self, case: dict) -> None:
        if case['intake_type'] != 'source_document':
            return
        ledger = load_yaml(self.ledger_path)
        entry = next((item for item in ledger['sources'] if item['source_id'] == case['source']['source_id']), None)
        if entry is None:
            raise ValueError(f"authority ledger entry missing for {case['source']['source_id']}")
        decided = sum((item['decision'] is not None for item in case['proposals']))
        proposal_activations = {}
        for path in self.case_root.glob('*.json'):
            other = json.loads(path.read_text(encoding='utf-8'))
            proposal_activations.update({item['proposal_id']: item['activation'] for item in other['proposals']})

        def is_effective(item: dict) -> bool:
            if item['activation'] is not None:
                return True
            decision = item['decision']
            if decision is None:
                return False
            if decision['disposition'] == 'reject':
                return True
            if decision['classification'] == 'duplicate':
                target = decision['target_requirement_id'] or ''
                return target.startswith('GRQ-') or proposal_activations.get(target) is not None
            return False
        effective = sum((is_effective(item) for item in case['proposals']))
        entry['coverage'].update(decided=decided, effective=effective, unresolved=len(case['proposals']) - decided)
        write_yaml(self.ledger_path, ledger)

    def complete_migration(self, args) -> None:
        case = self.load_case(args.case_id)
        self.refresh_ledger(case)
        ledger = load_yaml(self.ledger_path)
        entry = next((item for item in ledger['sources'] if item['source_id'] == case['source']['source_id']), None)
        if case['status'] != 'activated' or entry['coverage']['unresolved'] != 0:
            raise ValueError('migration can complete only after all decisions and activation')
        if entry['coverage']['effective'] != entry['coverage']['total']:
            raise ValueError('migration coverage is incomplete')
        expected_release = f"requirement-catalog-v{load_yaml(self.catalog_path)['version']}"
        if args.catalog_release != expected_release:
            raise ValueError(f'catalog release must be {expected_release}')
        decision_path = self.root / args.decision_ref
        if not decision_path.is_file() or not decision_path.resolve().is_relative_to((self.root / 'docs/governance/change-requests').resolve()):
            raise ValueError('migration completion decision must reference an existing governance change request')
        entry['authority_mode'] = 'git_authoritative'
        entry['catalog_release'] = args.catalog_release
        entry['effective_from'] = args.effective_from
        entry['decision_ref'] = args.decision_ref
        write_yaml(self.ledger_path, ledger)
        print(f"Completed migration for {entry['source_id']}")

    def report(self, _) -> None:
        catalog = load_yaml(self.catalog_path)
        ledger = load_yaml(self.ledger_path)
        cases = sorted(self.case_root.glob('*.json')) if self.case_root.exists() else []
        print(f"Authority sources: {len(ledger['sources'])}")
        print(f'Lifecycle cases: {len(cases)}')
        print(f"Canonical requirements: {len(catalog['requirements'])}")
        classification_counts = {}
        open_decisions = 0
        for path in cases:
            case = json.loads(path.read_text(encoding='utf-8'))
            for proposal in case['proposals']:
                key = proposal['analysis']['suggested_classification']
                classification_counts[key] = classification_counts.get(key, 0) + 1
                open_decisions += proposal['decision'] is None
        print(f'Open human decisions: {open_decisions}')
        if classification_counts:
            print('Analysis suggestions: ' + ', '.join((f'{key}={classification_counts[key]}' for key in sorted(classification_counts))))
        for item in ledger['sources']:
            coverage = item['coverage']
            print(f"- {item['source_id']}: {item['authority_mode']} · {coverage['decided']}/{coverage['total']} decided")

    def next_decision(self, args) -> None:
        case = self.load_case(args.case_id)
        proposal = next((item for item in case['proposals'] if item['decision'] is None), None)
        if proposal is None:
            print(f'{args.case_id} has no open decisions')
            return
        analysis = proposal['analysis']
        print(f'Case: {args.case_id}')
        print(f"Proposal: {proposal['proposal_id']} ({proposal['source_requirement_id']})")
        print(f"Title: {proposal['title']}")
        print(f"Strength/domain: {proposal['normative_strength']} / {proposal['domain']}")
        print(f"Statement: {proposal['statement']}")
        print(f"Suggestion: {analysis['suggested_classification']} ({analysis['confidence']:.4f}, {analysis['method']})")
        print('Candidates:')
        for candidate in analysis['candidate_matches']:
            print(f"- {candidate['requirement_id']}: {candidate['similarity']:.4f}")
        print('Human decision required: duplicate | new | extend | change | supersede | conflict')
