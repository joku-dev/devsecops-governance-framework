'use strict';
const reviewTools = typeof module !== 'undefined' ? require('./requirement-review.js') : RequirementReview;
const $ = (id) => document.getElementById(id);
const escapeHTML = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const e = escapeHTML;
function locatorLabel(value=''){
 return String(value).replace(/^line:(\d+)$/, 'Zeile $1').replace(/^paragraph:(\d+)$/, 'Absatz $1').replace(/^table:(\d+)\/row:(\d+)$/, 'Tabelle $1, Zeile $2').replace(/^page:(\d+)\/line:(\d+)$/, 'Seite $1, Zeile $2');
}
function humanReason(reason){
 const messages={
  'requirement identifier origin remains unverified for explicit identifiers':'Die Herkunft der Requirement-Kennungen muss noch belegt werden.',
  'requirement identifier origin remains unverified for extracted row IDs':'Die Herkunft bisheriger Extraktionskennungen muss noch belegt werden.',
  'approved-source requirement lifecycle decisions remain open':'Zu bestehenden Anforderungen sind noch fachliche Entscheidungen offen.',
  'Document Consistency Review scope does not expose an exact approved-source set':'Der Konsistenzreview benennt die geprüften freigegebenen Dokumente noch nicht vollständig.',
  'semantic consistency review is not exhaustive for the approved source set':'Die freigegebenen Dokumente sind noch nicht vollständig inhaltlich auf Widersprüche geprüft.',
  'proposed or unresolved consistency findings remain':'Mögliche Widersprüche müssen noch geprüft und entschieden werden.',
  'Document Consistency Review projection is not current':'Der gespeicherte Konsistenzreview passt nicht mehr zum aktuellen Dokumentstand.',
  'registered source files are missing':'Dateien registrierter Dokumente fehlen.',
  'source-document folder contains unregistered files':'Einige Dokumentdateien fehlen noch im Quellenregister.',
  'one or more source documents could not be extracted':'Bei mindestens einem Dokument konnte der Text nicht gelesen werden.',
  'one or more approved source inputs have withheld source text':'Für mindestens ein freigegebenes Dokument ist der Originaltext hier nicht verfügbar.',
  'approved sources are missing requirement lifecycle cases':'Für einige freigegebene Dokumente fehlt die Bearbeitung ihrer Anforderungen.',
  'one or more requirement lifecycle cases are stale':'Bestehende Anforderungsentscheidungen müssen mit dem geänderten Dokumentstand abgeglichen werden.'
 };
 return messages[reason]||reason;
}
const labels = {candidate:'Kandidat',draft:'Entwurf',intake:'Aufgenommen',review:'In Prüfung',approved:'Quelle freigegeben',superseded:'Ersetzt',retired:'Stillgelegt',local_draft:'Lokaler Entwurf',partial:'Teilweise geprüft',not_run:'Noch nicht geprüft',not_assessed:'Noch nicht bewertet',unknown:'Unbekannt',unconfirmed:'Noch nicht bestätigt',proposed:'Vorschlag',valid:'Belegt',blocked:'Voraussetzungen offen',current:'Passend zum Dokumentstand',added:'Neu hinzugekommen',changed:'Geändert',removed:'Im neuen Dokument nicht gefunden',equivalent:'Vergleichbar',ready_for_human_approval:'Bereit für menschlichen Review'};
const phaseLabels = {complete:'Abgeschlossen',partial:'Teilweise',blocked:'Blockiert',review_required:'Review nötig',decision_required:'Entscheidung offen',in_progress:'In Umsetzung',not_started:'Noch nicht begonnen',ready_for_human_approval:'Bereit für menschlichen Review'};
const phaseTargets = {source_intake:'sources',extract_and_classify:'sources',p1_requirement_lifecycle:'review',p2_inferred_review:'review',consistency_review:'review',decision_proposals:'review',source_baseline:'baseline',governance_implementation:'baseline'};
const phaseGuides = {
 source_intake:{why:'Sicherstellen, dass jede Quelle eindeutig registriert und einer verantwortlichen Stelle zugeordnet ist.',do:'Kandidaten, Owner und Quellenstatus prüfen. Neue Dokumente über „Dokument hinzufügen“ vorbereiten.',done:'Quelle, Version, Owner und Aufnahmeentscheidung sind nachvollziehbar dokumentiert.'},
 extract_and_classify:{why:'Den Dokumentinhalt und mögliche Anforderungen mit Fundstellen sichtbar machen.',do:'Extraktionswarnungen prüfen und Kandidaten immer mit dem Originaltext vergleichen. Die Extraktion kann Anforderungen übersehen.',done:'Extraktionslücken sind geprüft; jede erkannte Anforderung hat eine nachvollziehbare Fundstelle und Klasse.'},
 p1_requirement_lifecycle:{why:'Zuerst Anforderungen prüfen, die der Autor mit einer Kennung markiert hat. Eine erkannte Kennung gilt erst nach Herkunftsprüfung als author-identifiziert.',do:'Kennungsherkunft belegen und danach Status, Gültigkeit und mögliche Ablösung jedes P1-Kandidaten entscheiden.',done:'Kennung und Lifecycle-Entscheidung sind belegt; offene Fälle sind einer zuständigen Rolle zugewiesen.'},
 p2_inferred_review:{why:'Die Aufnahme verwendet ausschließlich explizit gekennzeichnete Anforderungen.',do:'Freitext bleibt als Originaltext sichtbar und erzeugt keine Requirement-Vorschläge.',done:'Es werden keine Anforderungen aus Freitext abgeleitet.'},
 consistency_review:{why:'Widersprüchliche oder unvereinbare Aussagen verhindern eine verlässliche gemeinsame Quellenbaseline.',do:'Den vollständigen autorisierten Quellenumfang mit frischen Nachweisen prüfen. Jeden möglichen Widerspruch mit Originalfundstellen erfassen.',done:'Der Prüfumfang ist vollständig und aktuell; alle Befunde sind entschieden oder als offen zur Entscheidung vorgelegt.'},
 decision_proposals:{why:'Fachliche Entscheidungen benötigen eine zuständige, nachvollziehbare menschliche Entscheidung.',do:'Offene Anforderungen und Konsistenzbefunde an die zuständigen Rollen geben. Vorschlag, Begründung und offene Frage dokumentieren.',done:'Jeder Fall hat eine dokumentierte Entscheidung oder einen klar benannten offenen Entscheidungsbedarf.'},
 source_baseline:{why:'Die Baseline legt fest, welche autorisierten Quellen und Versionen gemeinsam als widerspruchsfrei gelten.',do:'Blockierungsgründe prüfen, Quellenumfang und Hashes bestätigen und eine versionierte Freigabe durch die zuständige Autorität vorbereiten.',done:'Vollständige Nachweise liegen vor und die benannte Autorität hat die Baseline versioniert freigegeben.'},
 governance_implementation:{why:'Erst freigegebene Anforderungen dürfen in Controls, Plattformmodelle, Architekturregeln und OPA-Policies umgesetzt werden.',do:'Freigegebene Anforderungen den Governance-Artefakten zuordnen und die Umsetzung mit passenden Nachweisen belegen.',done:'Jede umgesetzte Anforderung ist rückverfolgbar; offene Umsetzungslücken sind sichtbar.'}
};
const countLabels = {registered:'registriert',approved:'freigegeben',missing_files:'Dateien fehlen',unregistered_files:'nicht registriert',scanned:'geprüft',withheld:'zurückgehalten',extraction_blocked:'Extraktion blockiert',confirmed_author_ids:'bestätigte Kennungen',unverified_extraction_ids:'historische Kennungen ungeprüft',unverified_explicit_ids:'explizite Kennungen ungeprüft',decided:'entschieden',undecided:'offen',activated:'aktiviert',inferred_candidates:'Textkandidaten',review_scope_sources:'Quellen im Prüfumfang',proposed_or_unresolved_findings:'offene Befunde',semantically_assessed_requirements:'semantisch geprüfte Anforderungen',consistency_findings_open:'offene Konsistenzbefunde',requirements_undecided:'Anforderungen ohne Entscheidung',authorized_sources:'autorisierte Quellen',blocking_reasons:'Blockierungsgründe',effective_requirement_artifact_links:'wirksame Zuordnungen',all_links:'Zuordnungen'};
const outcomeLabels = {confirm_candidate:'Bestätigung vorschlagen',reject_candidate:'Ablehnung vorschlagen',needs_clarification:'Klärung erforderlich',propose_resolution:'Lösung vorschlagen'};
const titleOf = d => d.source ? d.source.title : `Review-Paket · ${d.manifest.length} Quellen`;
let state, page = 'overview', activeDraft, toastTimer;
const reviewViews = new Map();
function tell(text) { if($('detail').open){$('detail-message').textContent=text;$('detail-message').hidden=false;} $('message').textContent = text; $('message').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('message').hidden = true, 7000); }
async function api(path, payload) {
  const options = payload === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state?.csrf || ''},body:JSON.stringify(payload)};
  const response = await fetch(path, options); const data = await response.json();
  if (!response.ok) { if(response.status === 401) { $('workspace').hidden = true; $('login').hidden = false; } throw new Error(data.error || 'Aktion fehlgeschlagen'); }
  return data;
}
async function refresh(){if(page==='intake'&&$('intake-form'))captureIntake();state = await api('/api/state'); $('login').hidden = true; $('workspace').hidden = false; render();}
function pill(status){return `<span class="pill ${e(status)}">${e(labels[status] || status)}</span>`;}
function heading(kicker,title,text,action=''){return `<div class="intro"><div><p class="eyebrow">${e(kicker)}</p><h1>${e(title)}</h1><p class="muted">${e(text)}</p></div>${action}</div>`;}
function bind(id,event,fn){const el=$(id); if(el) el.addEventListener(event,async ev=>{try{await fn(ev);}catch(error){tell(error.message);}});}
function navigate(next){if(page==='intake'&&$('intake-form'))captureIntake();page=next;render();}
function docOptions(includeEmpty=false){return (includeEmpty?'<option value="">Neue, eigenständige Quelle</option>':'')+state.documents.map(d=>`<option value="${e(d.id)}">${e(d.title)} · ${e(d.id)}</option>`).join('');}
function nextAction(d){if(d.status==='candidate')return 'Autorität und Aufnahmeentscheidung klären';if(d.status==='review'||d.status==='draft')return 'Owner-Review abschließen';if(d.status==='approved')return 'Anforderungsentscheidungen / Baseline prüfen';return 'Historie und Ablösung beachten';}
function table(docs){return `<div class="tablewrap"><table><thead><tr><th>Quelle</th><th>Status</th><th>Zuständig</th><th>Nächster Schritt</th><th></th></tr></thead><tbody>${docs.map(d=>`<tr><td><strong>${e(d.title)}</strong><div class="muted">${e(d.id)} · ${e(d.version)}</div></td><td>${pill(d.status)}</td><td>${e(d.owner)}</td><td>${e(nextAction(d))}</td><td><button class="quiet" data-source="${e(d.id)}">Öffnen →</button></td></tr>`).join('')}</tbody></table></div>`;}
function draftCards(){return state.drafts.length ? state.drafts.map(d=>`<div class="card row"><div><h3>${e(titleOf(d))}</h3><span class="muted">${e(d.created_at.slice(0,10))} · ${d.notes.length} Notizen · ${d.pr?'PR eingereicht':d.stale?'Quellenstand geändert':'Lokaler Entwurf'}</span></div><button class="quiet" data-draft="${e(d.draft_id)}">Bearbeiten →</button></div>`).join('') : '<div class="empty">Hier erscheinen deine vorbereiteten Dokumente. Beginne mit „Dokument auswählen“ oder bereite ein gemeinsames Review vor.</div>';}
const historicalCountKeys = new Set(['decided','undecided','activated','requirements_undecided']);
function phaseCounts(counts={},historical=false){return Object.entries(counts).filter(([key,value])=>value!==null&&value!==undefined&&historicalCountKeys.has(key)===historical).slice(0,3).map(([key,value])=>`${countLabels[key]||key.replaceAll('_',' ')}: ${Number(value).toLocaleString('de-DE')}`).join(' · ');}
function phaseAction(phase){return humanReason(phase.next_action||'Status prüfen.');}
function nextPhase(phases){return phases.find(phase=>phase.status!=='complete')||phases[phases.length-1];}
function processPhases(){
 const process=state.process||{}, phases=process.phases||[];
 if(!phases.length)return '<div class="notice">Der Intake-Phasenbericht ist in diesem Checkout nicht verfügbar.</div>';
 const current=nextPhase(phases), currentTarget=phaseTargets[current.id]||'review';
 return `<section class="panel phase-panel"><div class="sectionhead"><div><p class="eyebrow">Durchgängiger Prozess</p><h2>Von der Quelle bis zur Umsetzung</h2></div><span class="muted">Berichtsstand ${e(process.generated_at||'unbekannt')}</span></div><div class="next-step"><div><p class="eyebrow">Nächster offener Schritt</p><h3>${e(current.title)}</h3><p>${e(phaseAction(current))}</p></div><button data-process-target="${e(currentTarget)}">Diesen Schritt öffnen →</button></div><ol class="workflow">${phases.map((phase,index)=>{const guide=phaseGuides[phase.id]||{};return `<li class="workflow-step status-${e(phase.status)}"><span class="workflow-mark" aria-hidden="true">${phase.status==='complete'?'✓':index+1}</span><div class="workflow-content"><div class="workflow-title"><strong>${e(phase.title)}</strong><span class="phase-status">${e(phaseLabels[phase.status]||phase.status)}</span></div><p>${e(phaseAction(phase))}</p><small>${e(phaseCounts(phase.counts))}</small>${phaseCounts(phase.counts,true)?`<details class="phase-help"><summary>Frühere Lifecycle-Aufzeichnungen</summary><p>${e(phaseCounts(phase.counts,true))}</p><p>Diese Zähler enthalten frühere Vorschläge und Entscheidungen. Sie zählen keine neu extrahierten Anforderungen.</p></details>`:''}<details class="phase-help"><summary>Was bedeutet dieser Schritt?</summary><dl><dt>Wozu?</dt><dd>${e(guide.why||'Dieser Schritt trägt zu einer nachvollziehbaren Governance-Entscheidung bei.')}</dd><dt>Was ist zu tun?</dt><dd>${e(guide.do||'Prüfe den angezeigten Status und dokumentiere offene Punkte.')}</dd><dt>Erledigt, wenn</dt><dd>${e(guide.done||'Ergebnis und offene Punkte sind nachvollziehbar festgehalten.')}</dd></dl></details></div><button class="quiet phase-action" data-process-target="${e(phaseTargets[phase.id]||'review')}">Bereich öffnen →</button></li>`;}).join('')}</ol><p class="muted phase-footnote">Status und Zahlen stammen aus dem Intake-Bericht (${e(process.generated_at||'unbekannt')}); die Workbench hat diese Phasen nicht selbst abgeschlossen. Ein Entwurf, Review-Paket oder Snapshot ist keine formale Freigabe.</p></section>`;
}
function overview(){
 const open=state.documents.filter(d=>['candidate','draft','review'].includes(d.status));
 $('content').innerHTML=heading('Start','Was möchtest du tun?','Bereite ein Dokument vor oder setze deine Arbeit an einem vorhandenen Entwurf fort.')+
 `<div class="task-grid"><section class="panel task-card"><p class="eyebrow">Neu beginnen</p><h2>Ein Dokument hinzufügen</h2><p>Neue Dokumente und neue Versionen in drei kurzen Schritten vorbereiten.</p><button id="new-intake">Dokument auswählen →</button></section><section class="panel task-card"><p class="eyebrow">Weiterarbeiten</p><h2>Vorhandene Dokumente ansehen</h2><p>${state.documents.length} registrierte Dokumente mit Originaltext, Anforderungen und zuständigem Team.</p><button id="browse-documents" class="quiet">Dokumente öffnen →</button></section></div>`+
 `<section class="panel"><div class="sectionhead"><h2>Deine Entwürfe</h2><span class="muted">${state.drafts.length} lokal gespeichert</span></div><p class="muted">Öffne einen Entwurf, um Anforderungen anzusehen, Notizen zu ergänzen oder dein Review-Paket herunterzuladen.</p>${draftCards()}</section>`+
 `<details class="panel"><summary>Dokumente mit offenem Review (${open.length})</summary><p class="muted">Diese Einträge kommen aus dem Quellenregister. Eine offene Aufnahme ist von deinen lokalen Entwürfen getrennt.</p>${table(open)}</details>`+
 `<details class="panel process-disclosure"><summary>Gesamtprozess und Voraussetzungen für eine Freigabe</summary><p class="muted">Hier siehst du den gespeicherten Stand aller Governance-Schritte. Die Übersicht erteilt keine Freigabe.</p>${processPhases()}</details>`;
 bind('new-intake','click',()=>navigate('intake'));bind('browse-documents','click',()=>navigate('sources'));
}
function sources(){
 $('content').innerHTML=heading('Dokumente','Registrierte Dokumente ansehen.','Öffne ein Dokument, um den Originaltext und seine gekennzeichneten Anforderungen zu lesen.')+
 `<section class="panel"><div class="toolbar"><input id="search" aria-label="Quellen suchen" placeholder="Titel, Dokument-ID oder Team suchen …"><select id="status-filter" aria-label="Status filtern"><option value="">Alle Status</option>${Object.entries(labels).filter(([k])=>['candidate','draft','intake','review','approved','superseded','retired'].includes(k)).map(([k,v])=>`<option value="${e(k)}">${e(v)}</option>`).join('')}</select></div><div id="source-table">${table(state.documents)}</div></section>`;
 const filter=()=>{const q=$('search').value.toLowerCase();$('source-table').innerHTML=table(state.documents.filter(d=>(!$('status-filter').value||d.status===$('status-filter').value)&&`${d.id} ${d.title} ${d.owner}`.toLowerCase().includes(q)));};
 bind('search','input',filter);bind('status-filter','change',filter);
}
const domainLabels = {devsecops:'Entwicklung & Sicherheit',architecture:'Architektur',platform:'Plattform',policy:'Richtlinien',directive:'Verbindliche Vorgaben'};
function emptyIntake(){return {file:null,title:'',sourceId:'',idEdited:false,version:'',owner:'',domains:[],mode:'new',replacement:''};}
function suggestDocumentId(title,used=[]){
 const slug=title.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toUpperCase().replace(/[^A-Z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,48).replace(/-$/,'')||'DOKUMENT';
 for(let i=1;i<=999;i++){const id=`DOC-${slug}-${String(i).padStart(3,'0')}`;if(!used.includes(id))return id;}
 return '';
}
function suggestFileMetadata(name){
 const title=name.replace(/\.(md|markdown|docx|pdf)$/i,'').replace(/[_]+/g,' ').trim();
 const version=title.match(/(?:^|[\s-])v(\d+(?:\.\d+)*)(?:$|[\s-])/i);
 return {title,version:version?`v${version[1]}`:''};
}
function validateIntake(step,draft,documents=[]){
 if(step===1||step===3){
  if(!draft.file)return {field:'source-file',message:'Bitte wähle zuerst ein Dokument aus.'};
  if(!/\.(md|markdown|docx|pdf)$/i.test(draft.file.name))return {field:'source-file',message:'Bitte verwende Markdown, DOCX oder ein PDF mit lesbarem Text.'};
  if(draft.file.size===0)return {field:'source-file',message:'Die ausgewählte Datei ist leer. Bitte wähle ein Dokument mit Inhalt.'};
  if(draft.file.size>5*1024*1024)return {field:'source-file',message:'Die Datei ist zu groß. Erlaubt sind höchstens 5 MiB.'};
  if(!draft.title.trim()||draft.title.trim().length>200)return {field:'title',message:'Bitte gib einen Dokumenttitel mit höchstens 200 Zeichen ein.'};
 }
 if(step===2||step===3){
  if(!draft.version.trim()||draft.version.trim().length>200)return {field:'version',message:'Welche Version hat das Dokument? Übernimm die Angabe aus dem Original.'};
  if(!draft.owner.trim()||draft.owner.trim().length>200)return {field:'owner',message:'Bitte benenne das verantwortliche Team oder die zuständige Rolle.'};
  if(!draft.domains.length||draft.domains.some(d=>!Object.hasOwn(domainLabels,d)))return {field:'domain-group',message:'Bitte wähle mindestens einen betroffenen Bereich aus.'};
  if(draft.mode==='replacement'&&!documents.some(d=>d.id===draft.replacement))return {field:'replacement',message:'Bitte wähle das bisherige Dokument aus.'};
  if(!/^[A-Z0-9]+(?:-[A-Z0-9]+)*-[0-9]{3}$/.test(draft.sourceId))return {field:'source-id',message:'Bitte verwende für die Dokument-ID Großbuchstaben, Ziffern und Bindestriche mit drei Ziffern am Ende.'};
  if(documents.some(d=>d.id===draft.sourceId))return {field:'source-id',message:'Diese Dokument-ID ist bereits vergeben. Auch eine neue Version braucht eine neue Dokument-ID.'};
 }
 return null;
}
let intakeDraft=emptyIntake(), intakeStep=1;
function intakeUsedIds(){return [...state.documents.map(d=>d.id),...state.drafts.filter(d=>d.source).map(d=>d.source.id)];}
function captureIntake(){
 const fields={title:'title',version:'version',owner:'owner','source-id':'sourceId',replacement:'replacement'};
 for(const [id,key] of Object.entries(fields))if($(id))intakeDraft[key]=$(id).value;
 if($('domain-group'))intakeDraft.domains=[...document.querySelectorAll('[name=domain]:checked')].map(x=>x.value);
 if(!intakeDraft.idEdited)intakeDraft.sourceId=suggestDocumentId(intakeDraft.title,intakeUsedIds());
}
function showIntakeError(error){
 const box=$('intake-error');box.textContent=error.message;box.hidden=false;
 const target=$(error.field);if(target){for(let p=target.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;target.focus();}else box.focus();
}
function intake(){
 const d=intakeDraft, stages=['Datei auswählen','Dokument einordnen','Angaben prüfen'];
 const ownerOptions=[...new Set(state.documents.map(x=>x.owner))].sort().map(owner=>`<option value="${e(owner)}"></option>`).join('');
 const selected=state.documents.find(x=>x.id===d.replacement);
 let fields='';
 if(intakeStep===1)fields=`<h2 id="intake-step-title" tabindex="-1">Welches Dokument möchtest du vorbereiten?</h2><label class="upload">Dokument auswählen<input id="source-file" type="file" accept=".md,.markdown,.pdf,.docx"><span class="field-help">Markdown, DOCX oder PDF mit lesbarem Text · maximal 5 MiB</span></label>${d.file?`<p class="selected-file">Ausgewählt: <strong>${e(d.file.name)}</strong> · ${(d.file.size/1024).toLocaleString('de-DE',{maximumFractionDigits:1})} KiB</p>`:''}<label class="spaced-label">Dokumenttitel<input id="title" maxlength="200" value="${e(d.title)}" placeholder="Zum Beispiel: DevSecOps Control Baseline"><span class="field-help">Den vorgeschlagenen Dateinamen kannst du durch den offiziellen Titel ersetzen.</span></label><p class="muted">Anforderungen im Dokument brauchen eine Kennung wie <code>DSCB-L1-REQ-001</code>. Aus dem übrigen Text werden keine Anforderungen abgeleitet.</p>`;
 if(intakeStep===2)fields=`<h2 id="intake-step-title" tabindex="-1">Wie gehört das Dokument eingeordnet?</h2><fieldset class="choice-group"><legend>Was möchtest du hinzufügen?</legend><label><input type="radio" name="source-mode" value="new" ${d.mode==='new'?'checked':''}>Ein neues, eigenständiges Dokument</label><label><input type="radio" name="source-mode" value="replacement" ${d.mode==='replacement'?'checked':''}>Eine neue Version eines vorhandenen Dokuments</label></fieldset>${d.mode==='replacement'?`<label class="spaced-label">Bisheriges Dokument<select id="replacement"><option value="">Bitte auswählen …</option>${state.documents.map(x=>`<option value="${e(x.id)}" ${d.replacement===x.id?'selected':''}>${e(x.title)} · ${e(x.version)}</option>`).join('')}</select><span class="field-help">Die bisherige Version bleibt erhalten. Die Ablösung wird später im Review entschieden.</span></label>`:''}<div class="formgrid spaced-label"><label>Version laut Dokument<input id="version" maxlength="200" value="${e(d.version)}" placeholder="Zum Beispiel: v0.5 oder 6. November 2026"></label><label>Verantwortliches Team oder Rolle<input id="owner" list="known-owners" maxlength="200" value="${e(d.owner)}" placeholder="Auswählen oder eingeben"><datalist id="known-owners">${ownerOptions}</datalist></label><fieldset id="domain-group" tabindex="-1" class="full"><legend>Welche Bereiche betrifft das Dokument?</legend><div class="checks">${Object.entries(domainLabels).map(([value,label])=>`<label><input type="checkbox" name="domain" value="${value}" ${d.domains.includes(value)?'checked':''}>${e(label)}</label>`).join('')}</div></fieldset></div><details id="document-id-options" class="technical-details"><summary>Technische Dokument-ID anpassen</summary><p class="muted">Wir schlagen eine freie Kennung vor. Sie bezeichnet das Dokument und ist keine Requirement-Kennung.</p><label>Dokument-ID<input id="source-id" value="${e(d.sourceId)}" aria-describedby="document-id-help"><span id="document-id-help" class="field-help">Du kannst den Vorschlag übernehmen oder eine eigene, noch freie ID eingeben.</span></label></details>`;
 if(intakeStep===3)fields=`<h2 id="intake-step-title" tabindex="-1">Stimmen die Angaben?</h2><dl class="intake-summary"><dt>Datei</dt><dd>${e(d.file?.name||'—')}</dd><dt>Dokument</dt><dd>${e(d.title)}</dd><dt>Version</dt><dd>${e(d.version)}</dd><dt>Verantwortlich</dt><dd>${e(d.owner)}</dd><dt>Bereiche</dt><dd>${d.domains.map(x=>e(domainLabels[x])).join(', ')}</dd><dt>Einordnung</dt><dd>${d.mode==='replacement'?`Neue Version von ${e(selected?.title||d.replacement)}`:'Neues, eigenständiges Dokument'}</dd><dt>Dokument-ID</dt><dd><code>${e(d.sourceId)}</code></dd></dl><div class="notice info"><strong>Als Nächstes: Anforderungen ansehen.</strong> Wir lesen die gekennzeichneten Anforderungen und legen einen lokalen Entwurf an. Danach kannst du sie prüfen, Notizen ergänzen und ein Review-Paket herunterladen.</div>`;
 $('content').innerHTML=heading('Dokument hinzufügen','In drei Schritten vorbereiten.','Deine Angaben bleiben beim Vor- und Zurückgehen erhalten. Erst am Ende wird ein lokaler Entwurf angelegt.')+
 `<section class="panel intake-wizard"><ol class="wizard-progress" aria-label="Dokument vorbereiten">${stages.map((name,i)=>`<li class="${i+1===intakeStep?'current':i+1<intakeStep?'visited':''}" ${i+1===intakeStep?'aria-current="step"':''}><span aria-hidden="true">${i+1}</span>${e(name)}</li>`).join('')}</ol><form id="intake-form" novalidate><p class="eyebrow">Schritt ${intakeStep} von 3</p><div id="intake-error" class="notice form-error" role="alert" tabindex="-1" hidden></div>${fields}<div class="wizard-actions">${intakeStep>1?'<button type="button" id="intake-back" class="quiet">← Zurück</button>':''}<button id="upload-button" type="submit">${intakeStep===1?'Weiter zur Einordnung →':intakeStep===2?'Angaben prüfen →':'Dokument vorbereiten →'}</button></div></form><p class="muted wizard-footnote">Der Entwurf bleibt lokal. Die Aufnahme ins Quellenregister erfolgt im anschließenden Repository-Review.</p></section>`;
 bind('source-file','change',()=>{const file=$('source-file').files[0];if(!file)return;captureIntake();const previous=d.file?suggestFileMetadata(d.file.name):{};d.file=file;const suggestion=suggestFileMetadata(file.name);if(!d.title||d.title===previous.title)d.title=suggestion.title;if(!d.version||d.version===previous.version)d.version=suggestion.version;if(!d.idEdited)d.sourceId=suggestDocumentId(d.title,intakeUsedIds());intake();});
 bind('source-id','input',()=>{d.idEdited=true;captureIntake();});
 document.querySelectorAll('[name=source-mode]').forEach(input=>input.addEventListener('change',()=>{captureIntake();d.mode=input.value;if(d.mode==='new')d.replacement='';intake();}));
 bind('replacement','change',()=>{captureIntake();const original=state.documents.find(x=>x.id===d.replacement);if(original){if(!d.owner)d.owner=original.owner;if(!d.domains.length)d.domains=[...(original.governance_domains||[])];}intake();});
 bind('intake-back','click',()=>{captureIntake();intakeStep--;intake();$('intake-step-title').focus();});
 bind('intake-form','submit',async ev=>{
  ev.preventDefault();captureIntake();const error=validateIntake(intakeStep,d,state.documents);if(error){showIntakeError(error);return;}
  if(intakeStep<3){intakeStep++;intake();$('intake-step-title').focus();return;}
  const button=$('upload-button');button.disabled=true;button.textContent='Dokument wird vorbereitet …';
  try{
   const buffer=new Uint8Array(await d.file.arrayBuffer());let binary='';for(let i=0;i<buffer.length;i+=8192)binary+=String.fromCharCode(...buffer.subarray(i,i+8192));
   const draft=await api('/api/drafts',{filename:d.file.name,content_base64:btoa(binary),metadata:{id:d.sourceId,title:d.title.trim(),version:d.version.trim(),owner:d.owner.trim(),governance_domains:d.domains,replacement_for:d.mode==='replacement'?d.replacement:''}});
   intakeDraft=emptyIntake();intakeStep=1;await refresh();await showDraft(draft.draft_id);tell(`Dokument vorbereitet: ${draft.requirements.length} gekennzeichnete Anforderungen gefunden.`);
  }catch(error){showIntakeError({message:error.message});}finally{if($('upload-button')){$('upload-button').disabled=false;$('upload-button').textContent='Dokument vorbereiten →';}}
 });
}
function review(){
 $('content').innerHTML=heading('Dokumente gemeinsam prüfen','Vergleichen und ein Review vorbereiten.','Hier kontrollierst du erkannte Anforderungen, prüfst mögliche Widersprüche und erstellst einen klar abgegrenzten Review-Umfang.')+
 `<div class="notice info"><strong>Gekennzeichnete Anforderungen prüfen:</strong> Ob die Kennung aus dem Original stammt, wird im Review bestätigt. Freitext und technische Zeilen-IDs erzeugen keine Anforderungen. Auswahl von Quellen erstellt nur ein Paket; sie startet keine automatische oder semantische Prüfung.</div><div class="grid2"><section class="panel"><h2>1. Quellen für ein Review auswählen</h2><p class="muted">Wähle nur Quellen, die gemeinsam geprüft werden sollen. Das Paket hält Quellenstand und Umfang per Hash fest.</p><form id="review-form">${state.documents.map(d=>`<div class="card"><label class="checks"><input type="checkbox" name="review-source" value="${e(d.id)}">${e(d.title)}</label><p class="muted">${e(d.id)} · ${e(d.owner)} · ${e(labels[d.status])}</p></div>`).join('')}<button id="package-button" type="submit">Gewählten Umfang vorbereiten →</button></form></section><section class="panel"><h2>2. Vorhandene Prüfergebnisse</h2><p>${pill(state.dcr.overall_status||'not_run')}</p><p class="muted">Review: ${e(state.dcr.review_id||'Kein Snapshot')}<br>Quellenstand: ${e(state.dcr.freshness?.status||'unbekannt')}</p><p class="small">Dieser gespeicherte Snapshot deckt nur seinen eigenen Umfang ab. Deine Auswahl links führt keine neue Prüfung aus.</p>${(state.dcr.findings||[]).map(f=>`<div class="card"><div class="row"><h3>${e(f.id)}</h3>${pill(f.disposition)}</div><p>${e(f.category)} · Belegstatus: ${e(f.evidence_status)}</p><p class="muted">Diese Ansicht enthält keine Originalbelege oder vollständige Interpretation. Prüfe die fachliche Entscheidung im zugehörigen privaten Review-Datensatz.</p></div>`).join('')||'<p class="muted">In dieser Projektion sind keine Befunde enthalten. Das beweist nicht, dass die Quellen widerspruchsfrei sind.</p>'}<h3>Originaltexte nebeneinander lesen</h3><p class="muted">Der Direktvergleich erleichtert das Auffinden von Unterschieden. Er bewertet sie nicht.</p><label>Erstes Dokument<select id="compare-a">${docOptions()}</select></label><label>Zweites Dokument<select id="compare-b">${docOptions()}</select></label><div class="actions"><button id="compare-button" class="quiet">Dokumente anzeigen →</button></div></section></div>`;
 bind('review-form','submit',async ev=>{ev.preventDefault();const ids=[...document.querySelectorAll('[name=review-source]:checked')].map(x=>x.value);if(!ids.length)throw new Error('Wähle mindestens eine Quelle.');const d=await api('/api/review-packages',{source_ids:ids});await refresh();await showDraft(d.draft_id);});
 bind('compare-button','click',async()=>{const [a,b]=await Promise.all([api('/api/sources/'+$('compare-a').value),api('/api/sources/'+$('compare-b').value)]);$('detail-content').innerHTML='<p class="eyebrow">Originalvergleich · kein semantischer Review</p><h2>Fundstellen im direkten Vergleich</h2><div class="grid2">'+[a,b].map(v=>`<section><h3>${e(v.source.title)}</h3><details class="technical-details"><summary>Technischer Dateinachweis</summary><p class="hash">SHA-256: ${e(v.sha256)}</p></details>${sourceLines(v.lines)}</section>`).join('')+'</div>';$('detail').showModal();});
}
function baseline(){
 const baseline=state.process.authorized_source_baseline||{};
 $('content').innerHTML=heading('Freigabestand','Freigabeentscheidung vorbereiten.','Diese Ansicht zeigt die vorhandene Bereitschaft und fehlende Voraussetzungen. Sie startet keine neue Vollständigkeits- oder Konsistenzprüfung und erteilt keine Freigabe.')+
 `<section class="panel"><div class="sectionhead"><h2>Gemeldeter Stand und offene Voraussetzungen</h2>${pill(baseline.status||'unknown')}</div><p class="muted">Berichtsstand: ${e(state.process.generated_at||'Nicht verfügbar')} · vorhandene Projektion, keine neue Prüfung.</p>${(baseline.blocking_reasons||[]).map(x=>`<div class="baseline-blocker">${e(humanReason(x))}</div>`).join('')||'<p class="muted">Der Bericht nennt keine Blocker. Die formale Baseline-Entscheidung muss trotzdem durch die zuständige Autorität erfolgen.</p>'}<h3>Worauf bezieht sich dieser Stand?</h3><p>Auf den Checkout und das Quellenregister mit den folgenden Identitäten:</p><p class="hash">Checkout: ${e(state.context.commit)}<br>Quellenregister: ${e(state.context.register_sha256)}</p></section><section class="panel"><h2>Vor der formalen Freigabe</h2>${[['1','Quellenumfang und Autorität bestätigen','Genau die geprüften Quellen und Versionen festlegen.'],['2','Anforderungsentscheidungen abschließen','Offene Lifecycle- und Kandidatenentscheidungen klären.'],['3','Konsistenznachweise prüfen','Vollständigen, aktuellen Prüfumfang und die Behandlung aller Befunde belegen.'],['4','Freigabe versioniert dokumentieren','Zuständige Autorität, Datum, Entscheidung und Quellenhash erfassen.']].map(([n,t,s])=>`<div class="step"><b>${n}</b><div><h3>${t}</h3><p>${s}</p></div></div>`).join('')}<div class="notice info">Die Workbench bereitet die Entscheidung vor. Die formale Baseline-Freigabe wird außerhalb dieser App durch die benannte Autorität dokumentiert.</div></section>`;
}
function sourceLines(lines){return lines.map(x=>`<div class="line"><small>${e(locatorLabel(x.locator))}</small>${e(x.text)}</div>`).join('');}
function reqClassName(value){return ({author_identified:'Autorenkennung bestätigt',explicit_identifier:'explizite Kennung · Herkunft ungeprüft',extraction_row_id:'historische Extraktionskennung',inferred_candidate:'historischer Freitextvorschlag'})[value]||String(value||'Klasse ungeklärt').replaceAll('_',' ');}
async function showSource(id){
 captureItemNote();
 const v=await api('/api/sources/'+id);
 const brief=(state.briefs||[]).find(x=>x.source_id===id);
 $('detail-message').hidden=true;
 $('detail-content').innerHTML=`<p class="eyebrow">Registriertes Dokument</p><h2>${e(v.source.title)}</h2><p>${pill(v.source.status)} <span class="muted">${e(v.source.owner)} · ${e(v.source.version)}</span></p><div class="actions"><button id="prepare-source-review">Prüfung vorbereiten →</button></div><p class="muted">Lege einen lokalen Prüfentwurf für diese Version an. Das Dokument und sein Quellenstatus bleiben erhalten.</p><details class="technical-details"><summary>Technischer Dateinachweis</summary><p class="hash">SHA-256: ${e(v.sha256)}</p></details>${v.warnings.length?`<div class="notice">${v.warnings.map(e).join('<br>')}</div>`:''}${brief?`<details class="card"><summary>Vorhandenes Aufnahme-Briefing</summary><pre class="line">${e(JSON.stringify(brief,null,2))}</pre></details>`:''}<div class="tabs"><button id="source-current" class="selected">Aktuelle Extraktion</button><button id="source-history">Frühere Vorschläge und Entscheidungen</button></div><div id="source-body"></div>`;
 bind('prepare-source-review','click',async()=>{
  $('prepare-source-review').disabled=true;
  try {const draft=await api('/api/source-reviews',{source_id:id});await refresh();await showDraft(draft.draft_id);}
  finally {if($('prepare-source-review'))$('prepare-source-review').disabled=false;}
 });
 const selectTab=historical=>{
  $('source-current').classList.toggle('selected',!historical);$('source-history').classList.toggle('selected',historical);
  if(historical)loadHistory(id,'source-body',reviewTools.partitionRequirements(v.requirements).historical);
  else {$('source-body').innerHTML='<div id="requirement-workspace"></div>';mountRequirementReview(v,'source:'+id,false);}
 };
 bind('source-current','click',()=>selectTab(false));bind('source-history','click',()=>selectTab(true));selectTab(false);
 if(!$('detail').open)$('detail').showModal();
}
function reviewView(key){
 if(!reviewViews.has(key))reviewViews.set(key,{selected:null,query:'',filter:'all',unsaved:{},reviewer:''});
 return reviewViews.get(key);
}
function captureItemNote(){
 const form=$('item-note-form');
 if(form){
  const view=reviewView(form.dataset.reviewKey);
  view.unsaved[form.dataset.subject]={reviewer:$('item-reviewer').value,outcome:$('item-outcome').value,rationale:$('item-rationale').value};
  view.reviewer=$('item-reviewer').value;
 }
 const general=$('note-form');
 if(general){
  const view=reviewView(general.dataset.reviewKey);
  view.generalNote={subject:$('note-subject').value,reviewer:$('note-reviewer').value,outcome:$('note-outcome').value,rationale:$('note-rationale').value};
  view.reviewer=$('note-reviewer').value;
 }
}
function preparationSummary(data){
 const p=reviewTools.reviewProgress(data.requirements,data.notes);
 if(!p.total)return '<div class="notice">Keine explizit gekennzeichneten Anforderungen gefunden. Vergleiche den Originaltext mit den Kennungen im Dokument. Eine vollständige Prüfung wird damit nicht bestätigt.<div class="actions"><button type="button" id="add-document-question" class="quiet">Frage zum Dokument notieren →</button></div></div>';
 return `<div class="review-progress" role="status"><strong>${p.noted} von ${p.total} Anforderungen mit Prüfnotiz</strong><span>${p.unnoted} ohne Prüfnotiz · ${p.clarification} mit Klärungsbedarf</span></div><p class="muted">Die Zahlen beschreiben die lokale Vorbereitung. Eine Prüfnotiz ist ein Vorschlag; die formale Entscheidung folgt im Review.</p>`;
}
function handoffQuestions(data){
 const current=reviewTools.partitionRequirements(data.requirements).current, latest=reviewTools.latestNotes(data.notes);
 const open=current.filter(r=>!latest.has(r.id)||latest.get(r.id).outcome==='needs_clarification');
 return open.length?`<details class="handoff-questions" open><summary>Für den anschließenden Review offen (${open.length})</summary><ul>${open.map(r=>`<li><strong>${e(reviewTools.requirementLabel(r))}</strong>: ${latest.has(r.id)?'Klärungsbedarf – '+e(latest.get(r.id).rationale):'noch ohne Prüfnotiz'}</li>`).join('')}</ul></details>`:'';
}
function mountRequirementReview(data,key,editable){
 const view=reviewView(key), notes=data.notes||[], rows=data.requirements||[];
 const {current,historical}=reviewTools.partitionRequirements(rows);
 const visible=reviewTools.filteredRequirements(rows,notes,view.query,view.filter), latest=reviewTools.latestNotes(notes);
 if(!visible.some(r=>r.id===view.selected))view.selected=visible[0]?.id||null;
 const selected=visible.find(r=>r.id===view.selected), locked=data.stale||!!data.pr;
 const status=r=>latest.has(r.id)?outcomeLabels[latest.get(r.id).outcome]:'Ohne Prüfnotiz';
 let detail='';
 if(selected){
  const excerpt=reviewTools.sourceExcerpt(data.lines,selected), itemNotes=notes.filter(n=>n.subject===selected.id);
  const pending=view.unsaved[selected.id]||{reviewer:view.reviewer||notes.at(-1)?.reviewer||'',outcome:'confirm_candidate',rationale:''};
  detail=`<section class="review-item" aria-label="Ausgewählte Anforderung"><p class="eyebrow">Anforderung ${current.indexOf(selected)+1} von ${current.length}</p><h3 id="selected-requirement" tabindex="-1">${e(reviewTools.requirementLabel(selected))}</h3><p class="requirement-statement">${e(selected.statement)}</p><p class="muted">${e(reqClassName(selected.identification_class))} · ${e(locatorLabel(selected.source_locator))}</p><h4>Originalfundstelle</h4><div class="source-context">${excerpt.length?excerpt.map(line=>`<div class="line"><small>${e(locatorLabel(line.locator))}</small>${line.locator===selected.source_locator?`<mark>${e(line.text)}</mark>`:e(line.text)}</div>`).join(''):'<p class="notice">Die Fundstelle ist im gespeicherten Textauszug nicht verfügbar. Prüfe den vollständigen Originaltext und halte den Klärungsbedarf fest.</p>'}</div><p class="muted">Vergleiche Wortlaut und Fundstelle. Eine erkannte Kennung bestätigt weder ihre Herkunft noch die fachliche Freigabe.</p>`;
  if(editable){
   detail+=`<h4>Deine Einschätzung</h4><p class="muted">${e(status(selected))}</p><form id="item-note-form" data-review-key="${e(key)}" data-subject="${e(selected.id)}"><fieldset ${locked?'disabled':''}><label>Bearbeiter / Reviewer<input id="item-reviewer" required maxlength="200" autocomplete="name" value="${e(pending.reviewer)}"></label><label>Was schlägst du vor?<select id="item-outcome">${['confirm_candidate','reject_candidate','needs_clarification'].map(outcome=>`<option value="${outcome}" ${pending.outcome===outcome?'selected':''}>${e(outcomeLabels[outcome])}</option>`).join('')}</select></label><label>Begründung oder offene Frage<textarea id="item-rationale" required maxlength="4000">${e(pending.rationale)}</textarea></label><button type="submit" id="save-item-note">Einschätzung speichern</button></fieldset></form>`;
  }
  if(itemNotes.length)detail+=`<details class="technical-details"><summary>Alle Prüfnotizen zu dieser Anforderung (${itemNotes.length})</summary>${itemNotes.map(n=>`<article class="card"><strong>${e(outcomeLabels[n.outcome])}</strong><p>${e(n.rationale)}</p><small>${e(n.reviewer)} · ${e(n.recorded_at)} · Vorschlag</small></article>`).join('')}</details>`;
  const index=visible.indexOf(selected);
  detail+=`<div class="item-navigation"><button class="quiet" id="review-previous" ${index===0?'disabled':''}>← Vorherige</button><button class="quiet" id="review-next" ${index===visible.length-1?'disabled':''}>Nächste Anforderung →</button></div></section>`;
 }
 $('requirement-workspace').innerHTML=`${editable?preparationSummary(data):`<p class="muted">${current.length} explizit gekennzeichnete Anforderungen aus diesem Dokumentstand. Wähle „Prüfung vorbereiten“, um Einschätzungen festzuhalten.</p>`}${historical.length?`<div class="notice">${historical.length} ältere Einträge stehen separat unter „Frühere Vorschläge“. Sie zählen nicht zur aktuellen Extraktion.</div>`:''}<div class="toolbar review-toolbar"><input id="requirement-search" aria-label="Anforderungen suchen" placeholder="Kennung oder Wortlaut suchen …" value="${e(view.query)}">${editable?`<select id="requirement-filter" aria-label="Prüfnotizen filtern"><option value="all">Alle Anforderungen</option><option value="unnoted" ${view.filter==='unnoted'?'selected':''}>Ohne Prüfnotiz</option><option value="clarification" ${view.filter==='clarification'?'selected':''}>Klärungsbedarf</option></select>`:''}</div>${visible.length?`<div class="requirement-review-grid"><nav class="requirement-list" aria-label="Anforderungen auswählen">${visible.map(row=>`<button type="button" class="requirement-choice ${row.id===view.selected?'selected':''}" data-review-select="${e(row.id)}" ${row.id===view.selected?'aria-current="true"':''}><strong>${e(reviewTools.requirementLabel(row))}</strong><span>${e(row.statement.slice(0,100))}${row.statement.length>100?' …':''}</span>${editable?`<small>${e(status(row))}</small>`:''}</button>`).join('')}</nav>${detail}</div>`:current.length?'<div class="empty">Kein Treffer für diese Suche oder diesen Filter. Ändere die Auswahl, um weitere Anforderungen zu sehen.</div>':'<div class="empty">Keine expliziten Anforderungen erkannt. Prüfe die Kennungen im Originaltext.</div>'}<details class="technical-details"><summary>Gesamten Originaltext anzeigen</summary>${sourceLines(data.lines||[])}</details>`;
 const redraw=focus=>{captureItemNote();const position=$('requirement-search')?.selectionStart;mountRequirementReview(data,key,editable);if(focus){$(focus)?.focus();if(focus==='requirement-search'&&position!==null)$('requirement-search').setSelectionRange(position,position);}};
 bind('requirement-search','input',()=>{view.query=$('requirement-search').value;redraw('requirement-search');});
 bind('requirement-filter','change',()=>{view.filter=$('requirement-filter').value;redraw('requirement-filter');});
 $('requirement-workspace').querySelectorAll('[data-review-select]').forEach(button=>button.addEventListener('click',()=>{view.selected=button.dataset.reviewSelect;redraw('selected-requirement');}));
 const move=offset=>{view.selected=visible[visible.indexOf(selected)+offset]?.id;redraw('selected-requirement');};
 bind('review-previous','click',()=>move(-1));bind('review-next','click',()=>move(1));
 bind('item-note-form','submit',async ev=>{
  ev.preventDefault();if(locked)return;captureItemNote();$('save-item-note').disabled=true;
  try {const updated=await api('/api/drafts/'+data.draft_id+'/notes',{subject:selected.id,...view.unsaved[selected.id]});delete view.unsaved[selected.id];if(activeDraft?.draft_id===data.draft_id){activeDraft=updated;if($('item-note-form')?.dataset.reviewKey===key)renderDraft('requirements',false);}tell('Einschätzung gespeichert. Die formale Entscheidung bleibt im anschließenden Review.');}
  finally {if($('save-item-note'))$('save-item-note').disabled=!!activeDraft?.stale||!!activeDraft?.pr;}
 });
}
async function loadHistory(sourceId,containerId,olderRows=[],notes=[]){
 const container=$(containerId);container.innerHTML='<p class="muted">Frühere Aufzeichnungen werden geladen …</p>';
 try {
  const history=sourceId?await api('/api/sources/'+sourceId+'/history'):{cases:[]};
  if(!container.isConnected)return;
  container.innerHTML=`<h3>Frühere Vorschläge und Entscheidungen</h3><p class="muted">Diese Aufzeichnungen bleiben unverändert erhalten. Sie sind keine aktuelle Extraktion und zählen nicht zum lokalen Prüffortschritt.</p>${history.cases.map(c=>`<section class="history-case"><h4>${e(c.case_id)}</h4><p class="muted">${e(c.source.source_id)} · ${c.proposals.length} aufgezeichnete Vorschläge</p>${!c.source_matches?'<div class="notice">Der aufgezeichnete Quellenstand weicht vom heutigen Dokument ab. Entscheidungen nicht ungeprüft auf die aktuelle Extraktion übertragen.</div>':''}<details class="technical-details"><summary>Quellenbindung des früheren Falls</summary><p class="hash">${e(c.path)}<br>SHA-256: ${e(c.source.source_sha256)}</p></details>${c.proposals.map(p=>`<details class="history-record"><summary>${e(p.source_requirement_id)} · ${p.decision?'Entscheidung aufgezeichnet':'Ohne aufgezeichnete Entscheidung'}${p.activation?' · Umsetzung aufgezeichnet':''}</summary><p>${e(p.statement)}</p>${p.decision?`<h4>Aufgezeichnete Entscheidung</h4><p>${e(p.decision.rationale)}</p><p class="muted">${e(p.decision.decided_by)} · ${e(p.decision.decided_at)} · ${e(p.decision.disposition)}</p>`:''}<details class="technical-details"><summary>Vollständiger früherer Datensatz</summary><pre class="line">${e(JSON.stringify(p,null,2))}</pre></details></details>`).join('')}</section>`).join('')}${olderRows.length?`<h4>Ältere Einträge dieses lokalen Entwurfs (${olderRows.length})</h4>${olderRows.map(r=>`<details class="history-record"><summary>${e(reviewTools.requirementLabel(r))} · ${e(reqClassName(r.identification_class))}</summary><p>${e(r.statement)}</p>${notes.filter(n=>n.subject===r.id).map(n=>`<p>${e(outcomeLabels[n.outcome])}: ${e(n.rationale)} · ${e(n.reviewer)}</p>`).join('')}</details>`).join('')}`:''}${!history.cases.length&&!olderRows.length?'<div class="empty">Keine früheren Lifecycle-Vorschläge für dieses Dokument gespeichert.</div>':''}`;
 }catch(error){if(container.isConnected)container.innerHTML='<div class="notice">Frühere Aufzeichnungen konnten nicht geladen werden. Versuche es erneut; die aktuelle Extraktion bleibt davon getrennt.</div>';}
}
async function showDraft(id){
 captureItemNote();activeDraft=await api('/api/drafts/'+id);$('detail-message').hidden=true;renderDraft('requirements');if(!$('detail').open)$('detail').showModal();
}
function renderDraft(tab,capture=true){
 if(capture)captureItemNote();
 const d=activeDraft, source=d.source;
 const link=d.pr?.url;const safePR=typeof link==='string'&&/^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/pull\/\d+$/.test(link);
 $('detail-content').innerHTML=`<p class="eyebrow">${d.kind==='source_candidate'?'Lokaler Dokumententwurf':source?'Lokale Prüfung eines registrierten Dokuments':'Vorbereitetes gemeinsames Review'}</p><h2>${e(titleOf(d))}</h2><p class="muted">${source?e(source.id)+' · '+e(source.owner)+' · ':''}${e(d.created_at)} · Entwurf</p>${d.stale?'<div class="notice">Der Repository-Stand hat sich geändert. Export und Notizen sind gesperrt. Erstelle einen neuen Entwurf auf dem aktuellen Stand.</div>':''}${d.warnings?.length?`<div class="notice">${d.warnings.map(e).join('<br>')}</div>`:''}<div class="tabs"><button data-tab="requirements" class="${tab==='requirements'?'selected':''}">${source?'Anforderungen prüfen':'Dokumentauswahl'}</button>${d.target?`<button data-tab="delta" class="${tab==='delta'?'selected':''}">Änderungen ansehen</button>`:''}<button data-tab="notes" class="${tab==='notes'?'selected':''}">Alle Notizen (${d.notes.length})</button>${source?`<button data-tab="history" class="${tab==='history'?'selected':''}">Frühere Vorschläge</button>`:''}<button data-tab="packet" class="${tab==='packet'?'selected':''}">Weitergeben</button></div><div id="draft-body"></div>`;
 const body=$('draft-body');
 if(tab==='requirements'){
  body.innerHTML=source?'<div id="requirement-workspace"></div>':
  `<div class="notice info">Quellenumfang vorbereitet · semantische Ausführung: <strong>not_run</strong>. Kein genehmigtes Providerpaket und keine Baseline-Freigabe.</div>${d.manifest.map(m=>`<div class="card"><h3>${e(m.source_id)}</h3><p>${pill(m.status)} · ${e(m.owner)} · ${m.requirements_count} extrahierte Kandidaten</p><p class="hash">${e(m.sha256)}</p>${m.warnings.length?`<p class="error">${m.warnings.map(e).join(', ')}</p>`:''}</div>`).join('')}`;
  if(source)mountRequirementReview(d,'draft:'+d.draft_id,true);
 }
 if(tab==='history')loadHistory(d.kind==='source_review'?source.id:d.target?.source.id,'draft-body',reviewTools.partitionRequirements(d.requirements).historical,d.notes);
 if(tab==='delta')body.innerHTML=d.target?`<p class="muted">Abgleich mit ${e(d.target.source.title)}. Explizite Requirement-Kennungen verbinden Einträge derselben Anforderung auch bei abweichendem Wortlaut. Gleichwertigkeit und Änderungen benötigen fachliche Bestätigung.</p>${d.deltas.map(x=>`<div class="card"><div class="reqhead">${pill(x.status)}${x.matched_identifier?`<strong>Kennung ${e(x.matched_identifier)}</strong>`:`<small>Abgleich: ${e(x.match_basis==='text_similarity'?'Textähnlichkeit':x.match_basis==='unmatched'?'keine Zuordnung':'Kennung')}</small>`}<small>Review-Priorität: ${e(x.review_priority)}</small></div><div class="grid2"><div><h3>Bisher · ${e(x.target_requirement?.source_requirement_id||x.target_requirement?.extraction_row_id||'')}</h3><p>${e(x.target_requirement?.statement||'—')}</p><span class="muted">${e(x.target_requirement?.source_locator||'')}</span></div><div><h3>Kandidat · ${e((x.candidate_requirement?.recognized_requirement_ids||[]).join(', ')||x.candidate_requirement?.source_requirement_id||x.candidate_requirement?.extraction_row_id||'')}</h3><p>${e(x.candidate_requirement?.statement||'—')}</p><span class="muted">${e(x.candidate_requirement?.source_locator||'')}</span></div></div></div>`).join('')}`:'<div class="empty">Keine Vorgängerquelle ausgewählt. Keine Ersatzentscheidung wird angenommen.</div>';
 if(tab==='notes'){
  const options=source?[{id:'source',name:'Dokument insgesamt'},...reviewTools.partitionRequirements(d.requirements).current.map(x=>({id:x.id,name:reviewTools.requirementLabel(x)}))]:d.manifest.map(m=>({id:m.source_id,name:m.source_id}));
  body.innerHTML=`<div class="notice info">Deine Einschätzung wird als Vorschlag gespeichert. Die formale Entscheidung erfolgt im anschließenden Review.</div>${d.notes.map(n=>`<div class="card"><h3>${e(outcomeLabels[n.outcome])}</h3><p>${e(n.rationale)}</p><span class="muted">${e(n.subject)} · ${e(n.reviewer)} · ${e(n.recorded_at)}</span></div>`).join('')}<form id="note-form" data-review-key="${e('draft:'+d.draft_id)}"><div class="formgrid"><label>Bezug<select id="note-subject">${options.map(o=>`<option value="${e(o.id)}">${e(o.name)}</option>`).join('')}</select></label><label>Reviewer / Bearbeiter<input id="note-reviewer" maxlength="200" required placeholder="Name oder eindeutige Kennung"></label><label class="full">Vorschlag<select id="note-outcome">${Object.entries(outcomeLabels).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label><label class="full">Begründung und offene Fragen<textarea id="note-rationale" required maxlength="4000"></textarea></label></div><div class="actions"><button ${d.stale||d.pr?'disabled':''} type="submit">Notiz speichern</button></div></form>`;
  const saved=reviewView('draft:'+d.draft_id).generalNote;
  if(saved){for(const field of ['subject','reviewer','outcome','rationale'])$('note-'+field).value=saved[field];}
  else $('note-reviewer').value=reviewView('draft:'+d.draft_id).reviewer||d.notes.at(-1)?.reviewer||'';
  bind('note-form','submit',async ev=>{ev.preventDefault();activeDraft=await api('/api/drafts/'+d.draft_id+'/notes',{subject:$('note-subject').value,reviewer:$('note-reviewer').value,outcome:$('note-outcome').value,rationale:$('note-rationale').value});delete reviewView('draft:'+d.draft_id).generalNote;renderDraft('notes',false);tell('Prüfnotiz gespeichert.');});
 }
 if(tab==='packet'){
  body.innerHTML=`<div class="notice">Das Paket enthält private Quelldaten und Vorschläge. Vor einem PR prüfen, ob diese Inhalte in das Zielrepo dürfen. Der PR bleibt ein Draft und wird nicht durch die App gemergt.</div><h3>Vorbereitung zur Übergabe</h3>${source?preparationSummary(d)+handoffQuestions(d):''}<h3>Das enthält dein Review-Paket</h3><p>${d.kind==='source_candidate'?'Originaldatei · Vorschlag für das Quellenregister · Änderungsbeschreibung · Prüfnotizen':source?'Unveränderte registrierte Originaldatei · Änderungsbeschreibung · Prüfnotizen':'Liste der ausgewählten Dokumente mit Dateinachweisen · Änderungsbeschreibung · Prüfnotizen'}</p><details class="technical-details"><summary>Technische Paketdaten und weiterführende Prüfungen</summary><p class="hash">Basis-Commit: ${e(d.context.commit)}<br>Register: ${e(d.context.register_sha256)}</p><p class="muted">Das Paket startet keine inhaltliche Konsistenzprüfung. Dafür sind ein festgelegter Prüfumfang und eine gesonderte Laufentscheidung erforderlich.</p></details><div class="actions"><button id="export-packet" ${d.stale?'disabled':''}>Review-Paket herunterladen</button></div>${safePR?`<p class="actions"><a href="${e(link)}" target="_blank" rel="noopener noreferrer">Draft-PR öffnen →</a></p>`:state.pr_enabled?`<form id="pr-form"><div class="checks actions"><label><input id="publish-confirm" type="checkbox" required>Ich habe die Inhalte geprüft und möchte sie im Repository als Draft-PR veröffentlichen.</label></div><div class="actions"><button id="pr-button" ${d.stale?'disabled':''}>Draft-PR erstellen</button></div></form>`:'<p class="muted actions">Die direkte PR-Erstellung ist hier nicht aktiviert. Lade das Review-Paket herunter und gib es über euren üblichen Review-Weg weiter.</p>'}`;
  bind('export-packet','click',async()=>{const r=await fetch('/api/drafts/'+d.draft_id+'/packet');if(!r.ok){const error=await r.json();throw new Error(error.error);}const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download=`AXIOM-${d.draft_id}.zip`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  bind('pr-form','submit',async ev=>{ev.preventDefault();$('pr-button').disabled=true;$('pr-button').textContent='Draft-PR wird vorbereitet …';try{await api('/api/drafts/'+d.draft_id+'/pr',{confirm_publication:$('publish-confirm').checked});await showDraft(d.draft_id);renderDraft('packet');}finally{if($('pr-button')){$('pr-button').disabled=false;$('pr-button').textContent='Draft-PR erstellen';}}});
 }
 const order=source?(d.target?['requirements','delta','packet']:['requirements','packet']):['requirements','notes','packet'];
 const next=tab==='notes'?'packet':order[order.indexOf(tab)+1];
 if(next&&tab!=='history'){body.insertAdjacentHTML('beforeend',`<div class="review-next"><button id="draft-next" type="button">${next==='delta'?'Weiter: Änderungen ansehen →':next==='notes'?'Weiter: Notizen ergänzen →':'Weiter: Übergabe vorbereiten →'}</button></div>`);bind('draft-next','click',()=>renderDraft(next));}
 document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>renderDraft(button.dataset.tab)));
 bind('add-document-question','click',()=>{renderDraft('notes');$('note-subject').value='source';$('note-rationale').focus();});
}
function render(){
 const names={overview:'Start',sources:'Dokumente',intake:'Dokument hinzufügen',review:'Dokumente gemeinsam prüfen',baseline:'Freigabestand'};
 $('breadcrumb').textContent=names[page];document.querySelectorAll('[data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===page));
 ({overview,sources,intake,review,baseline}[page])();
}
if(typeof document!=='undefined'){
 bind('login-form','submit',async ev=>{ev.preventDefault();await api('/api/login',{key:$('key').value});$('key').value='';await refresh();});
 bind('refresh','click',async()=>{await refresh();tell('Aktueller Checkout geladen.');});
 bind('logout','click',async()=>{await api('/api/logout',{});state=null;activeDraft=null;reviewViews.clear();intakeDraft=emptyIntake();intakeStep=1;$('detail-content').textContent='';$('content').textContent='';$('workspace').hidden=true;$('login').hidden=false;$('detail').close();});
 bind('close-detail','click',()=>{captureItemNote();$('detail').close();});
 bind('detail','close',captureItemNote);
 document.querySelectorAll('[data-page]').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.page)));
 document.addEventListener('click',async ev=>{const source=ev.target.closest('[data-source]'),draft=ev.target.closest('[data-draft]'),note=ev.target.closest('[data-note-subject]'),phase=ev.target.closest('[data-process-target]');try{if(source)await showSource(source.dataset.source);if(draft)await showDraft(draft.dataset.draft);if(note){renderDraft('notes');$('note-subject').value=note.dataset.noteSubject;$('note-rationale').focus();}if(phase)navigate(phase.dataset.processTarget);}catch(error){tell(error.message);}});
 refresh().catch(()=>{});
}
if(typeof module!=='undefined')module.exports={escapeHTML,emptyIntake,suggestDocumentId,suggestFileMetadata,validateIntake,locatorLabel,humanReason};
