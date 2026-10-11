"""Project shared technical viewer sections into the Workspace, without scripts.

The existing renderer remains the single source for technical table contents.
This boundary strips executable content and rebases links for the app location.
"""
from html import escape
from html.parser import HTMLParser
import json
import posixpath
from urllib.parse import quote, urlsplit

# One destination for every technical section; no second top-level navigation tree.
SECTIONS = {
    'overview': ('operations', 'overview', 'Integrationsstatus'),
    'governance-graph': ('governance', 'graph', 'Governance-Graph'),
    'runtime-governance': ('governance', 'runtime', 'Runtime-Governance'),
    'controls': ('governance', 'controls', 'Kontrollen'),
    'model': ('governance', 'model', 'Governance-Modell'),
    'source-intake': ('governance', 'sources', 'Quellenaufnahme'),
    'requirement-migration': ('governance', 'requirements', 'Anforderungsmigration'),
    'open-work': ('governance', 'work', 'Offene Aufgaben'),
    'evidence-trust': ('evidence', 'trust', 'Evidence Trust'),
    'replay-triage': ('evidence', 'replay', 'Replay-Prüfung'),
    'evidence-agent-provenance': ('evidence', 'provenance', 'Nachweisherkunft'),
    'runs': ('evidence', 'history', 'Laufhistorie'),
    'artifacts': ('evidence', 'artifacts', 'Artefakte & Daten'),
    'intake-health': ('operations', 'intake', 'Intake-Zustand'),
    'collection-attempts': ('operations', 'collection', 'Sammelversuche'),
    'intake-conflicts': ('operations', 'conflicts', 'Intake-Konflikte'),
    'agent-usage': ('operations', 'agents', 'Agent-Nutzung'),
}
TAGS = set('section div article aside h2 h3 h4 p a span strong em small code pre ul ol li dl dt dd table thead tbody tr th td label select option input button details summary br svg defs marker path g'.split())
ATTRS = set('id class href for type value placeholder role tabindex scope colspan rowspan viewbox markerwidth markerheight refx refy orient markerunits d selected disabled hidden open'.split())
VOID = {'input', 'br'}
CENTRAL = 'https://github.com/joku-dev/devsecops-governance-framework/blob/main/'


def link(value):
    """Preserve safe external URLs; map anchors and generated/Pages/source links."""
    if any(ord(c) < 32 for c in value) or '\\' in value:
        raise ValueError('Unsafe technical viewer URL')
    if value.startswith('#'):
        name = value[1:]
        if name == 'measured-security':
            return '#findings'
        if name in SECTIONS:
            group, tab, _ = SECTIONS[name]
            return f'#{group}/{tab}'
        raise ValueError(f'Unmapped technical viewer anchor: {name}')
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme != 'https' or not parsed.netloc:
            raise ValueError('Technical viewer requires HTTPS links')
        return value
    path = posixpath.normpath(posixpath.join('generated/viewer', parsed.path))
    if path.startswith('../') or path == '..' or path.startswith('/'):
        raise ValueError('Technical viewer URL leaves the site')
    # Source JSON is tracked in Git, but is not copied to Pages by MkDocs.
    if path.startswith(('status/', 'model/', 'schemas/', 'policies/')):
        return CENTRAL + quote(path, safe='/')
    result = posixpath.relpath(path, 'generated/viewer/app')
    return result + ('?' + parsed.query if parsed.query else '') + ('#' + parsed.fragment if parsed.fragment else '')


class SectionProjection(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections = {}
        self.graph = None
        self.current = None
        self.depth = 0
        self.parts = []
        self.script = None
        self.script_text = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if not self.current:
            if tag != 'section' or 'viewer-section' not in values.get('class', '').split():
                return
            self.current = values.get('id')
            if self.current not in SECTIONS and self.current != 'measured-security':
                raise ValueError(f'Unmapped viewer section: {self.current}')
            if self.current in self.sections:
                raise ValueError('Duplicate viewer section')
            self.parts = []
        if tag == 'section':
            self.depth += 1
        if tag == 'script':
            self.script = values.get('id', 'executable')
            self.script_text = []
            return
        if self.script:
            return
        if tag not in TAGS:
            raise ValueError(f'Unsupported technical viewer element: {tag}')
        safe = []
        for key, value in attrs:
            if key not in ATTRS and not key.startswith(('data-', 'aria-')):
                continue
            if key == 'href':
                value = link(value or '')
            safe.append(key if value is None else f'{key}="{escape(value, quote=True)}"')
        self.parts.append('<' + tag + (' ' + ' '.join(safe) if safe else '') + '>')

    def handle_endtag(self, tag):
        if not self.current:
            return
        if self.script:
            if tag == 'script':
                if self.script == 'governance-graph-data':
                    self.graph = json.loads(''.join(self.script_text))
                self.script = None
            return
        if tag in TAGS and tag not in VOID:
            self.parts.append('</' + tag + '>')
        if tag == 'section':
            self.depth -= 1
            if self.depth == 0:
                if self.current != 'measured-security':
                    self.sections[self.current] = ''.join(self.parts)
                self.current = None

    def handle_data(self, data):
        if self.script:
            self.script_text.append(data)
        elif self.current:
            self.parts.append(escape(data))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)


def project_technical(html):
    parser = SectionProjection()
    parser.feed(html)
    parser.close()
    if parser.current or parser.depth:
        raise ValueError('Unclosed technical viewer section')
    return {
        'sections': [{'id': key, 'group': group, 'tab': tab, 'title': title,
                      'html': parser.sections.get(key), 'available': key in parser.sections}
                     for key, (group, tab, title) in SECTIONS.items()],
        'graph': parser.graph,
    }
