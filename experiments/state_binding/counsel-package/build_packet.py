"""Build private counsel documents from reviewed Markdown and a fixed source commit."""
from __future__ import annotations

from datetime import datetime
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import textwrap
import zipfile

from markdown_it import MarkdownIt
from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak,
                               PageTemplate, Paragraph, Spacer, Table, TableStyle,
                               XPreformatted)
from reportlab.platypus.tableofcontents import TableOfContents

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
COMMIT = '56ed0c743121fddc9d117b69eb470493dff5046d'
PDF_NAME = 'Patentanwalt-Unterlagen-Zustandsgebundene-Autorisierung.pdf'
ZIP_NAME = 'Patentanwalt-Paket-Zustandsgebundene-Autorisierung.zip'
CHAPTERS = sorted(HERE.glob('0[1-6]-*.md'))
WIDTH = A4[0] - 104
INK = colors.HexColor('#111111')
GREY = colors.HexColor('#D9D9D9')
PALE = colors.HexColor('#F4F6F8')
BLUE = colors.HexColor('#24435A')
EXTERNAL = {
 'E1': 'https://cwe.mitre.org/data/definitions/367.html',
 'E2': 'https://www.rfc-editor.org/rfc/rfc8785',
 'E3': 'https://www.rfc-editor.org/rfc/rfc9162',
 'E4': 'https://in-toto.io/docs/what-is-in-toto/',
 'E5': 'https://docs.langchain.com/oss/python/langgraph/interrupts',
 'E6': 'https://www.rfc-editor.org/rfc/rfc9396',
 'E7': 'https://www.dpma.de/patente/anmeldung/index.html',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def source(name):
    return subprocess.check_output(['git', 'show', f'{COMMIT}:{name}'], cwd=REPO)


def setup_fonts():
    # Read system font files only; no installation or system configuration changes.
    roots = [Path('/System/Library/Fonts/Supplemental'), Path('/usr/share/fonts/truetype/liberation2'),
             Path('/usr/share/fonts/truetype/dejavu')]
    choices = [
      ('Body', ['Arial.ttf', 'LiberationSans-Regular.ttf', 'DejaVuSans.ttf']),
      ('BodyBold', ['Arial Bold.ttf', 'LiberationSans-Bold.ttf', 'DejaVuSans-Bold.ttf']),
      ('BodyItalic', ['Arial Italic.ttf', 'LiberationSans-Italic.ttf', 'DejaVuSans-Oblique.ttf']),
      ('Mono', ['Courier New.ttf', 'LiberationMono-Regular.ttf', 'DejaVuSansMono.ttf']),
    ]
    used = {}
    for family, filenames in choices:
        path = next((root / n for root in roots for n in filenames if (root / n).exists()), None)
        if path is None:
            raise RuntimeError('Install a supported local font for ' + family)
        pdfmetrics.registerFont(TTFont(family, str(path)))
        used[family] = {'file': path.name, 'sha256': sha(path.read_bytes())}
    pdfmetrics.registerFontFamily('Body', normal='Body', bold='BodyBold', italic='BodyItalic', boldItalic='BodyBold')
    return used


def styles():
    return {
      'body': ParagraphStyle('BodyText', fontName='Body', fontSize=10.6, leading=15.1, textColor=INK,
                             spaceAfter=8, splitLongWords=1, allowWidows=0, allowOrphans=0),
      'h1': ParagraphStyle('Chapter', fontName='BodyBold', fontSize=19, leading=24, textColor=INK,
                           spaceAfter=17, keepWithNext=True),
      'h2': ParagraphStyle('Section', fontName='BodyBold', fontSize=12.4, leading=17, textColor=INK,
                           spaceBefore=12, spaceAfter=7, keepWithNext=True),
      'title': ParagraphStyle('PacketTitle', fontName='BodyBold', fontSize=25, leading=31, textColor=INK,
                              spaceAfter=18),
      'small': ParagraphStyle('Small', fontName='Body', fontSize=9.2, leading=12.6, textColor=INK, spaceAfter=9),
      'caption': ParagraphStyle('Caption', fontName='BodyItalic', fontSize=9.2, leading=12, spaceAfter=13),
      'cell': ParagraphStyle('Cell', fontName='Body', fontSize=9.1, leading=12.3, splitLongWords=1),
      'headcell': ParagraphStyle('HeaderCell', fontName='BodyBold', fontSize=9.1, leading=12.3, textColor=colors.white),
      'code': ParagraphStyle('Code', fontName='Mono', fontSize=8.3, leading=11.7, spaceBefore=5, spaceAfter=13),
      'bullet': ParagraphStyle('BulletBody', fontName='Body', fontSize=10.6, leading=15.1,
                               leftIndent=13, firstLineIndent=-10, spaceAfter=7),
    }


def node(d, x, y, w, h, lines, *, dark=False):
    d.add(Rect(x, y, w, h, rx=3, ry=3, fillColor=BLUE if dark else PALE,
               strokeColor=colors.HexColor('#7E8991'), strokeWidth=.7))
    for i, line in enumerate(lines):
        d.add(String(x+w/2, y+h/2 + (len(lines)-1)*6-i*12, line,
                     textAnchor='middle', fontName='BodyBold' if i == 0 else 'Body',
                     fontSize=9.1, fillColor=colors.white if dark else INK))


def arrow(d, x1, y1, x2, y2, *, dashed=False):
    import math
    d.add(Line(x1, y1, x2, y2, strokeColor=BLUE, strokeWidth=1, strokeDashArray=[4,3] if dashed else None))
    a = math.atan2(y2-y1, x2-x1)
    d.add(Polygon([x2,y2,x2-6*math.cos(a-.4),y2-6*math.sin(a-.4),
                   x2-6*math.cos(a+.4),y2-6*math.sin(a+.4)],fillColor=BLUE,strokeColor=BLUE))


def diagrams():
    a=Drawing(WIDTH, 362)
    node(a, 8, 296, 150, 48, ['110 Transaktionshistorie', 'geordnete Dateien'])
    node(a, 8, 210, 150, 48, ['130 History Root H', 'Historienidentität'])
    node(a, 184, 296, 135, 48, ['120 Deterministischer Replay', 'Kette und Zustand prüfen'])
    node(a, 184, 210, 135, 48, ['130 State Root Z', 'definierter Zustand'])
    node(a, 344, 296, 139, 48, ['Implementierungsmanifest', 'ausgewählte Datei-Bytes'])
    node(a, 344, 210, 139, 48, ['130 Implementation Root I', 'Umfang ausdrücklich fixiert'])
    arrow(a, 158, 320,184,320); arrow(a,83,296,83,258)
    arrow(a,414,296,414,258)
    node(a,184,128,135,48,['140 Antrag Q und Digest D','Aktion, Rolle, Profil'],dark=True)
    arrow(a,251,296,251,258); arrow(a,251,210,251,176)
    arrow(a,114,210,184,164); arrow(a,385,210,319,164)
    node(a,8,128,150,48,['150 Freigabeprovider','GitHub / Test-Provider'])
    arrow(a,184,156,158,156); arrow(a,158,141,184,141)
    node(a,184,45,135,48,['160 Prüfkern und 170 Writer','lokale Sperre + Publikation'],dark=True)
    arrow(a,251,128,251,93)
    node(a,344,45,139,48,['180 Nachweisprüfung','Paket, Replay und Digests'])
    arrow(a,319,69,344,69)
    a.add(String(8,15,'Provider und Laufzeitvertrauen liegen außerhalb der lokalen Atomizitätsgarantie.',fontName='BodyItalic',fontSize=9,fillColor=INK))
    b=Drawing(WIDTH, 357)
    b.add(String(8,337,'Vorbereitung',fontName='BodyBold',fontSize=10))
    node(b,126,303,345,45,['Snapshot und H / Z / I bilden; konkreten Antrag fixieren','lokale Sperre während der Vorbereitung'])
    b.add(String(8,250,'Freigabepause',fontName='BodyBold',fontSize=10))
    node(b,126,225,345,45,['Benannte Person prüft Antrag und erklärt Zustimmung','lokale Sperre ist freigegeben'])
    arrow(b,298,303,298,270)
    b.add(String(8,164,'Ausführung',fontName='BodyBold',fontSize=10))
    node(b,126,142,345,49,['Sperre erwerben; aktuellen Kontext und Provider prüfen','Provider doppelt lesen; gesamten lokalen Kontext erneut prüfen'],dark=True)
    arrow(b,298,225,298,191)
    node(b,126,65,345,45,['Bei Übereinstimmung eine vollständige Transaktion publizieren','Artefakt ist Teil derselben lokal atomaren Datei'],dark=True)
    arrow(b,298,142,298,110)
    b.add(String(8,25,'Bei Abweichung: keine Publikation. Nach Erfolg: alter Antrag trifft auf neue Historie.',fontName='BodyItalic',fontSize=9))
    b.add(String(8,10,'Die lokale Sperre sperrt den externen Provider nicht; dessen Race-Fenster bleibt bestehen.',fontName='BodyItalic',fontSize=9))
    c=Drawing(WIDTH, 325)
    c.add(String(8,307,'Entwurf einer Übertragung auf Agentensysteme - noch nicht implementiert',fontName='BodyBold',fontSize=10))
    node(c,8,230,147,50,['Agent / LLM','liefert konkreten Vorschlag','keine eigene Freigabe'])
    node(c,185,230,145,50,['Vertrauenswürdiges Gateway','fixiert Aktion und Kontext','H / Z / I + Request'],dark=True)
    node(c,360,230,123,50,['Freigabestelle','prüft konkreten Antrag','bestätigt Digest'])
    arrow(c,155,255,185,255); arrow(c,330,263,360,263); arrow(c,360,246,330,246)
    node(c,185,134,145,56,['Gateway vor Tool-Effekt','Antrag und Kontext prüfen','Zielversion mitführen'],dark=True)
    arrow(c,258,230,258,190)
    node(c,185,43,298,52,['Kontrolliertes Zielsystem','z. B. Versionsvergleich und Mutation in einer Transaktion','diese Effektkopplung ist zusätzlich zu implementieren'])
    arrow(c,258,134,258,95)
    c.add(String(8,15,'LLM-Ausgaben werden aufgezeichnet; ein deterministischer Replay ruft das Modell nicht neu auf.',fontName='BodyItalic',fontSize=9))
    result={'01-architektur':a,'02-ablauf':b,'03-agententransfer':c}
    for name, drawing in result.items():
        renderSVG.drawToFile(drawing,str(HERE/'figures'/f'{name}.svg'))
    return result


def inline(token):
    pieces=[]
    for child in token.children or []:
        kind=child.type
        if kind == 'text':
            text=html.escape(child.content)
            for ref,url in EXTERNAL.items():
                text=text.replace('['+ref+']',f'<a href="{url}" color="#24435A">[{ref}]</a>')
            pieces.append(text)
        elif kind == 'code_inline':
            pieces.append('<font name="Mono" size="8.7">'+html.escape(child.content)+'</font>')
        elif kind in ('softbreak','hardbreak'):
            pieces.append(' ' if kind=='softbreak' else '<br/>')
        elif kind == 'strong_open': pieces.append('<b>')
        elif kind == 'strong_close': pieces.append('</b>')
        elif kind == 'em_open': pieces.append('<i>')
        elif kind == 'em_close': pieces.append('</i>')
        elif kind == 'link_open':
            url=child.attrGet('href')
            pieces.append('<a href="'+html.escape(url,quote=True)+'" color="#24435A">')
        elif kind == 'link_close': pieces.append('</a>')
        elif kind == 'image': pass
        else: raise ValueError('Unsupported inline token '+kind)
    return ''.join(pieces)


def table_widths(rows):
    n=len(rows[0]); first=rows[0][0]
    if first=='Zeichen': return [WIDTH*.11,WIDTH*.32,WIDTH*.57]
    if first=='Symbol': return [WIDTH*.13,WIDTH*.87]
    if n==2:
        ratio=.29 if any(v in first for v in ('Kennung','Datei','Symbol','Zustandsfeld','Merkmal','Dokumentierter')) else .42
        return [WIDTH*ratio,WIDTH*(1-ratio)]
    if n==3:
        return [WIDTH*.24,WIDTH*.40,WIDTH*.36] if 'Anwendungsfeld' in first else [WIDTH*.27,WIDTH*.53,WIDTH*.20]
    if n==4: return [WIDTH*.35,WIDTH*.31,WIDTH*.23,WIDTH*.11]
    return [WIDTH/n]*n


def make_table(rows, st):
    table=Table([[Paragraph(c, st['headcell' if i==0 else 'cell']) for c in row]
                 for i,row in enumerate(rows)], colWidths=table_widths(rows), repeatRows=1, hAlign='LEFT')
    commands=[('BACKGROUND',(0,0),(-1,0),BLUE),('GRID',(0,0),(-1,-1),.5,GREY),
              ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),7),
              ('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),
              ('BOTTOMPADDING',(0,0),(-1,-1),7)]
    for row in range(1,len(rows)):
        if row%2==0: commands.append(('BACKGROUND',(0,row),(-1,row),PALE))
    table.setStyle(TableStyle(commands))
    return [table,Spacer(1,12)]


def chapter_flow(path, st, drawings):
    tokens=MarkdownIt('commonmark').enable('table').parse(path.read_text())
    result=[]; i=0; list_stack=[]; counter=0
    while i<len(tokens):
        token=tokens[i]; kind=token.type
        if kind=='heading_open':
            level=int(token.tag[1]); content=inline(tokens[i+1]); style=st['h1' if level==1 else 'h2']
            paragraph=Paragraph(content,style)
            paragraph._heading=(level, tokens[i+1].content)
            result.append(paragraph); i+=3; continue
        if kind=='paragraph_open':
            text_token=tokens[i+1]
            images=[c for c in text_token.children or [] if c.type=='image']
            if images:
                img=images[0]; drawing=drawings[Path(img.attrGet('src')).stem]
                result.append(KeepTogether([drawing,Spacer(1,6),Paragraph(html.escape(img.content),st['caption'])]))
            else:
                prefix=''
                if list_stack:
                    prefix=f'{counter}. ' if list_stack[-1]=='ordered' else '- '
                result.append(Paragraph(prefix+inline(text_token),st['bullet'] if list_stack else st['body']))
            i+=3; continue
        if kind in ('bullet_list_open','ordered_list_open'):
            list_stack.append('ordered' if kind.startswith('ordered') else 'bullet'); counter=0
        elif kind in ('bullet_list_close','ordered_list_close'): list_stack.pop()
        elif kind=='list_item_open': counter+=1
        elif kind=='table_open':
            rows=[]; row=[]; i+=1
            while tokens[i].type!='table_close':
                if tokens[i].type=='tr_open': row=[]
                elif tokens[i].type=='inline': row.append(inline(tokens[i]))
                elif tokens[i].type=='tr_close': rows.append(row)
                i+=1
            result.extend(make_table(rows,st))
        elif kind=='fence':
            lines=[]
            for line in token.content.rstrip().splitlines():
                lines.extend(textwrap.wrap(line, width=91, subsequent_indent='  ', replace_whitespace=False,
                                           drop_whitespace=False, break_long_words=True) or [''])
            result.append(XPreformatted(html.escape('\n'.join(lines)),st['code']))
        elif kind in ('list_item_close','html_block','hr'): pass
        else: raise ValueError(f'Unsupported block token {kind} in {path.name}')
        i+=1
    return result


class PacketDoc(BaseDocTemplate):
    def __init__(self,path):
        super().__init__(str(path),pagesize=A4,leftMargin=52,rightMargin=52,topMargin=53,bottomMargin=48,
                         title='Zustandsgebundene Autorisierung - Technische Unterlagen zur Patentprüfung',
                         author='Technische Dokumentation im Auftrag des Repository-Maintainers')
        self.heading_number=0
        frame=Frame(52,48,WIDTH,A4[1]-101,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        self.addPageTemplates(PageTemplate(id='normal',frames=frame,onPage=self.decorate))
    def beforeDocument(self): self.heading_number=0
    def decorate(self,canvas,doc):
        canvas.setFillColor(INK); canvas.setFont('Body',8)
        if doc.page>1: canvas.drawString(52,A4[1]-30,'Zustandsgebundene Autorisierung | Referenzstand 56ed0c7')
        canvas.drawString(52,27,'VERTRAULICH | Technische Unterlagen zur Patentprüfung')
        canvas.drawRightString(A4[0]-52,27,str(doc.page))
    def afterFlowable(self,flowable):
        if hasattr(flowable,'_heading'):
            level,text=flowable._heading; self.heading_number+=1
            key='heading-'+str(self.heading_number)
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text,key,level=level-1,closed=False)
            if level==1: self.notify('TOCEntry',(0,text,self.page,key))


def build_pdf(st, drawings):
    content=[Spacer(1,20),Paragraph('Zustandsgebundene Autorisierung',st['title']),
      Paragraph('Technische Unterlagen für die Patentberatung',st['h2']),
      Paragraph('Vertraulich · Fassung 1.0 · 20. September 2026',st['small']),
      Paragraph('Eine Freigabe wird an den geprüften Verlauf, einen definierten Zustand und die ausgewählte Implementierung gebunden. Vor einer lokalen Testpublikation werden diese Werte und die Providererklärung erneut geprüft. Ein ausführbarer Prototyp und aufbewahrte Rohdaten belegen das beschriebene Verhalten im angegebenen Modell.',st['body']),
      Paragraph('Dieses Paket erläutert das technische Problem, den Lösungsansatz, die Architektur, mögliche Anwendungen außerhalb des Repositorys und die konkreten Implementierungsreferenzen. Es dient der anwaltlichen Beurteilung des technischen Gegenstands; die abschließende patentrechtliche Prüfung bleibt offen.',st['body']),
      Paragraph('Belegter Stand: 18 bestandene Dateisystemversuche, ein erfolgreicher persönlicher Demonstrationslauf und 640 bestandene Repository-Tests. Anwendungen in KI- und Agentensystemen sind als noch nicht implementierte Übertragungsentwürfe beschrieben.',st['body']),
      Paragraph('Referenzcommit: <font name="Mono" size="8.4">'+COMMIT+'</font><br/>Repository: joku-dev/devsecops-governance-framework · privater PR 176',st['small']),
      Spacer(1,12),Paragraph('Leseführung',st['h2'])]
    toc=TableOfContents(); toc.levelStyles=[ParagraphStyle('TOC',fontName='Body',fontSize=10,leading=16,spaceBefore=4,leftIndent=0,firstLineIndent=0)]
    content.extend([toc,Spacer(1,15),Paragraph('Zusätzliche Dateien im Weitergabepaket: editierbare Kapitel, SVG-Abbildungen, Quellcodeauszug, originale Evidence-Pakete und eine lesende Integritätsprüfung. Die GitHub-Verweise sind auf feste Quellstände gebunden und erfordern privaten Zugriff.',st['small'])])
    for chapter in CHAPTERS: content.extend([PageBreak(),*chapter_flow(chapter,st,drawings)])
    PacketDoc(HERE/PDF_NAME).multiBuild(content)


def pack(fonts):
    evidence_root='experiments/state_binding/evidence/'
    automated=source(evidence_root+'run-001.zip')
    import io
    with zipfile.ZipFile(io.BytesIO(automated)) as archive:
        manifest=json.loads(archive.read('results.json'))['source_manifest']
    source_files={}
    for name,expected in manifest.items():
        raw=source(name)
        if sha(raw)!=expected: raise ValueError('Source manifest differs at '+name)
        source_files[name]=raw
    for name in ('tests/test_state_binding_prototype.py',): source_files[name]=source(name)
    for name in ('LICENSE','LICENSE.md','LICENSE.txt'):
        exists=subprocess.run(['git','cat-file','-e',f'{COMMIT}:{name}'],cwd=REPO,capture_output=True)
        if exists.returncode==0: source_files[name]=source(name)
    payload={PDF_NAME:(HERE/PDF_NAME).read_bytes(), 'verify_package.py':(HERE/'verify_package.py').read_bytes()}
    for path in CHAPTERS: payload['documents/'+path.name]=path.read_bytes()
    for path in sorted((HERE/'figures').glob('*.svg')): payload['documents/figures/'+path.name]=path.read_bytes()
    for name,raw in source_files.items(): payload['source/'+name]=raw
    evidence_names=['run-001.zip','verification.json','validation.json','validation-final.log','validation-initial.log',
                    'docs-build.log','PERSONAL-DEMO.md','personal-demo-001.zip','personal-demo-verification.json',
                    'personal-demo-validation.log','personal-demo-request.json','personal-demo-statement.txt','CI-LIMITATIONS.md']
    for name in evidence_names: payload['evidence/'+name]=source(evidence_root+name)
    payload['SOURCE-MANIFEST.json']=json_bytes({'reference_commit':COMMIT,'files':{n:sha(b) for n,b in sorted(source_files.items())},
        'scope':'Selected implementation sources and tests for inspection; not a full repository checkout'})
    payload['START-HERE.md']=('''# Vertrauliche Unterlagen für die Patentberatung

Zuerst das PDF im Hauptverzeichnis lesen. Die sechs Kapitel liegen editierbar
unter documents/. source/ enthält die ausgewählten unveränderten Quelldateien;
evidence/ enthält die originalen Versuche und Prüfberichte.

Paketintegrität prüfen (lesend, ohne Entpacken des geprüften ZIPs):

    python3 verify_package.py PFAD_ZUM_ZIP --expect-zip-sha256 EXTERN_AUFBEWAHRTER_DIGEST

Automatisierte Versuche unabhängig prüfen (nach Entpacken dieses Pakets):

    python3 source/experiments/state_binding/verify_evidence.py evidence/run-001.zip --expect-manifest-sha256 e8a903751e3e3f040371329f8f8ef2910376f72decd42a033f3620b50caf4628

Der technische Quellcodeauszug ist kein vollständiger Repository-Checkout.
Die persönliche Offline-Prüfung und eine Wiederholung der Gesamttests sind im
vollständigen privaten Repository beschrieben. Den Code aus einer tatsächlichen
persönlichen Freigabe nicht nochmals zur Ausführung verwenden.

Das Paket ist nicht verschlüsselt. Für den vereinbarten vertraulichen Kanal
bestimmt. Es wurde nicht automatisch an einen Empfänger versendet.
''').encode()
    package_manifest={'format_version':'1','classification':'confidential_counsel_packet',
                      'reference_commit':COMMIT,'files':{n:sha(b) for n,b in sorted(payload.items())}}
    payload['MANIFEST.json']=json_bytes(package_manifest)
    with zipfile.ZipFile(HERE/ZIP_NAME,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,raw in sorted(payload.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,9,20,12,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            archive.writestr(info,raw)
    from verify_package import verify
    result=verify(HERE/ZIP_NAME)
    metadata={'document_version':'1.0','reference_commit':COMMIT,'pdf':PDF_NAME,
              'pdf_sha256':sha((HERE/PDF_NAME).read_bytes()),'archive':ZIP_NAME,
              'manifest_sha256':sha(payload['MANIFEST.json']),'verification':result,
              'fonts':fonts,'visual_review':'pending','repository_validation':'pending',
              'source_file_count':len(source_files)}
    (HERE/'PACKAGE.json').write_bytes(json_bytes(metadata))
    print(json.dumps(metadata,indent=2))


def main():
    if len(CHAPTERS)!=6: raise ValueError('Expected the six reviewed chapters')
    fonts=setup_fonts(); drawings=diagrams(); build_pdf(styles(),drawings); pack(fonts)


if __name__=='__main__': main()
