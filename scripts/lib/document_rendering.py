"""Whole216-line original renderer over explicit data/export/tool/parser ports."""
from __future__ import annotations
from html import escape

class GovernanceDocumentRenderer:

    def __init__(self, root, *, path_factory, yaml_load, which, run_process, argument_parser, argv):
        self.root = root
        self.catalog_path = root / 'model' / 'documents' / 'governance-documents.yaml'
        self.rendering_path = root / 'model' / 'documents' / 'governance-document-rendering.yaml'
        self.out_dir = root / 'generated' / 'documents'
        self.path_factory = path_factory
        self.yaml_load = yaml_load
        self.which = which
        self.run_process = run_process
        self.argument_parser = argument_parser
        self.argv = argv

    def load_yaml(self, path: self.path_factory):
        with path.open('r', encoding='utf-8') as handle:
            return self.yaml_load(handle)

    def markdown_to_html(self, markdown: str) -> str:
        lines = markdown.splitlines()
        html = []
        in_list = False
        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                if in_list:
                    html.append('</ul>')
                    in_list = False
                continue
            if stripped.startswith('### '):
                if in_list:
                    html.append('</ul>')
                    in_list = False
                html.append(f'<h3>{escape(stripped[4:])}</h3>')
            elif stripped.startswith('## '):
                if in_list:
                    html.append('</ul>')
                    in_list = False
                html.append(f'<h2>{escape(stripped[3:])}</h2>')
            elif stripped.startswith('# '):
                if in_list:
                    html.append('</ul>')
                    in_list = False
                html.append(f'<h1>{escape(stripped[2:])}</h1>')
            elif stripped.startswith('- '):
                if not in_list:
                    html.append('<ul>')
                    in_list = True
                html.append(f'<li>{escape(stripped[2:])}</li>')
            else:
                if in_list:
                    html.append('</ul>')
                    in_list = False
                paragraph = escape(stripped).replace('**', '').replace('`', '')
                html.append(f'<p>{paragraph}</p>')
        if in_list:
            html.append('</ul>')
        return '\n'.join(html)

    def build_front_matter(self, document: dict, profile: dict) -> str:
        return '\n'.join([f"# {document['title']}", '', f"Document ID: `{document['id']}`", f"Document Type: `{document['type']}`", f"Status: `{document['status']}`", f"Document Number: `{profile['document_number']}`", '', '| Field | Value |', '| --- | --- |', f"| Prepared by | {profile['prepared_by']} |", f"| Approved by | {profile['approved_by']} |", f"| Endorsed by | {profile['endorsed_by'] or '-'} |", f"| Authorized by | {profile['authorized_by']} |", f"| Area of application | {profile['area_of_application']} |", '', '## Record of Revisions', '', '| Version | Brief description of change | Date |', '| --- | --- | --- |', f"| {profile['version']} | {profile['revision_description']} | {profile['revision_date']} |", '', f'Purpose: {self.profiled_purpose(document)}', ''])

    def profiled_purpose(self, document: dict) -> str:
        return document.get('purpose', '')

    def build_rendered_markdown(self, document: dict, profile: dict, source_markdown: str) -> str:
        front_matter = self.build_front_matter(document, profile)
        tail = '\n'.join(['', '## Entry Into Force', '', profile['entry_into_force'], '', '## Repository Source', '', f"Rendered from `{document['repository_path']}` using `scripts/render_governance_documents.py`.", ''])
        return front_matter + source_markdown.strip() + tail

    def build_html(self, document: dict, rendered_markdown: str) -> str:
        body = self.markdown_to_html(rendered_markdown)
        title = escape(document['title'])
        return '\n'.join(['<!doctype html>', '<html lang="en">', '<head>', '  <meta charset="utf-8">', f'  <title>{title}</title>', '  <style>', '    body { font-family: Arial, sans-serif; margin: 40px auto; max-width: 900px; line-height: 1.6; color: #222; }', '    h1, h2, h3 { color: #0d2b45; }', '    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }', '    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; vertical-align: top; }', '    code { background: #f4f4f4; padding: 0.1rem 0.3rem; }', '  </style>', '</head>', '<body>', body, '</body>', '</html>'])

    def maybe_render_docx(self, markdown_path: self.path_factory, docx_path: self.path_factory) -> bool:
        pandoc = self.which('pandoc')
        if not pandoc:
            return False
        result = self.run_process([pandoc, str(markdown_path), '-o', str(docx_path)], capture_output=True, text=True, check=False)
        return result.returncode == 0

    def render_document(self, document: dict, profile: dict) -> dict:
        source_path = self.root / document['repository_path']
        source_markdown = source_path.read_text(encoding='utf-8')
        rendered_markdown = self.build_rendered_markdown(document, profile, source_markdown)
        stem = document['id'].lower()
        md_path = self.out_dir / f'{stem}.rendered.md'
        html_path = self.out_dir / f'{stem}.html'
        docx_path = self.out_dir / f'{stem}.docx'
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(rendered_markdown, encoding='utf-8')
        html_path.write_text(self.build_html(document, rendered_markdown), encoding='utf-8')
        docx_created = self.maybe_render_docx(md_path, docx_path)
        return {'id': document['id'], 'markdown': md_path, 'html': html_path, 'docx': docx_path if docx_created else None}

    def main(self) -> int:
        parser = self.argument_parser()
        parser.add_argument('--document-id', action='append', dest='document_ids')
        args = parser.parse_args(self.argv)
        catalog = self.load_yaml(self.catalog_path)['documents']
        profiles = self.load_yaml(self.rendering_path)['render_profiles']
        selected = [doc for doc in catalog if doc['type'] in {'policy', 'directive'}]
        if args.document_ids:
            wanted = set(args.document_ids)
            selected = [doc for doc in selected if doc['id'] in wanted]
        rendered = []
        for document in selected:
            profile = profiles[document['id']]
            rendered.append(self.render_document(document, profile))
        for item in rendered:
            print(f"Wrote {item['markdown'].relative_to(self.root)}")
            print(f"Wrote {item['html'].relative_to(self.root)}")
            if item['docx'] is not None:
                print(f"Wrote {item['docx'].relative_to(self.root)}")
            else:
                print(f"Skipped DOCX for {item['id']} because pandoc is not available")
        return 0
