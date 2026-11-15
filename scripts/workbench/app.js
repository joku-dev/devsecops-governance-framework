'use strict';
const reviewTools = typeof module !== 'undefined' ? require('./requirement-review.js') : RequirementReview;
const workspaceTools = typeof module !== 'undefined' ? require('./workspace-navigation.js') : WorkspaceNavigation;
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
let state, page = 'overview', activeDraft, activeSource, toastTimer;
let currentRoute = {page:'overview'}, routeVersion = 0;
const routeMemory = new Map();
const documentListView = {query:'', status:'', focus:'devsecops'};
const reviewViews = new Map();
function tell(text,error=false) { const target=$('review-page').hidden?$('page-message'):$('detail-message');target.classList.toggle('form-error',error);target.classList.toggle('info',!error);target.textContent=text;target.hidden=false; $('message').textContent = text; $('message').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('message').hidden = true, 7000); }
async function api(path, payload) {
  const options = payload === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state?.csrf || ''},body:JSON.stringify(payload)};
  const response = await fetch(path, options); const data = await response.json();
  if (!response.ok) { if(response.status === 401) { $('workspace').hidden = true; $('login').hidden = false; } throw new Error(data.error || 'Aktion fehlgeschlagen'); }
  return data;
}
async function refresh(redraw=true){
 captureWorkspace();
 state=await api('/api/state');$('login').hidden=true;$('workspace').hidden=false;
 if(redraw)await applyRoute(true);
}
function captureWorkspace(){
 captureItemNote();
 if(page==='intake'&&$('intake-form'))captureIntake();
 if(currentRoute.page==='source'||currentRoute.page==='draft'){
  const key=currentRoute.page+':'+currentRoute.id, view=reviewView(key);
  routeMemory.set(workspaceTools.routeHash(currentRoute),{query:view.query,filter:view.filter,selected:view.selected,pane:view.pane});
 }
}
function hasUnsavedWork(){
 captureWorkspace();
 return !!(intakeDraft.file||intakeDraft.title||intakeDraft.version||intakeDraft.owner)
  || [...reviewViews.values()].some(v=>Object.keys(v.unsaved).length||v.generalNote||v.saving.size||v.savingGeneral||v.publishing);
}
function rememberDraft(updated){
 if(state){const index=state.drafts.findIndex(d=>d.draft_id===updated.draft_id);if(index<0)state.drafts.push(updated);else if((state.drafts[index].notes?.length||0)<=updated.notes.length)state.drafts[index]=updated;else return state.drafts[index];}
 return updated;
}
function reviewPage(){
 $('content').hidden=true;$('review-page').hidden=false;$('page-message').hidden=true;$('detail-message').hidden=true;
}
function routeSelection(id,replace=false){
 const next={...currentRoute};if(id)next.item=id;else delete next.item;
 const hash=workspaceTools.routeHash(next);
 if(hash!==location.hash){history[replace?'replaceState':'pushState'](null,'',hash);currentRoute=next;}
}
function navigateRoute(next,replace=false){
 captureWorkspace();
 const hash=workspaceTools.routeHash(next);
 if(location.hash!==hash)history[replace?'replaceState':'pushState'](null,'',hash);
 return applyRoute();
}
async function applyRoute(force=false){
 captureWorkspace();
 const next=workspaceTools.parseRoute(location.hash), version=++routeVersion;
 const same=currentRoute.page===next.page&&currentRoute.id===next.id;
 currentRoute=next;page=next.page;
 if(!state)return;
 const names={overview:'Start',sources:'Dokumente',intake:'Dokument hinzufügen',review:'Dokumentvergleich vorbereiten',baseline:'Freigabevoraussetzungen',source:'Dokument ansehen',draft:'Prüfen',consumers:'Consumer-Repos',invalid:'Seite nicht gefunden'};
 $('breadcrumb').textContent=names[page]||names.invalid;document.title=($('breadcrumb').textContent)+' · AXIOM';
 const navPage=['source','draft'].includes(page)?'sources':page;
 document.querySelectorAll('[data-page]').forEach(button=>{button.classList.toggle('active',button.dataset.page===navPage);if(button.dataset.page===navPage)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');});
 if(page==='source'||page==='draft'){
  reviewPage();
  const view=reviewView(page+':'+next.id), saved=routeMemory.get(workspaceTools.routeHash(next));
  if(saved)Object.assign(view,saved);
  if(next.item)view.selected=next.item;
  if(!force&&same&&(page==='draft'?activeDraft?.draft_id===next.id:activeSource?.source.id===next.id)){
   if(page==='draft')renderDraft(next.tab);else renderSource(activeSource,next.tab);
  }else{
   activeDraft=null;activeSource=null;$('detail-content').innerHTML='<p role="status" class="panel">Arbeitsstand wird geladen …</p>';
   try{
    const data=await api(page==='draft'?'/api/drafts/'+next.id:'/api/sources/'+next.id);
    if(version!==routeVersion)return;
    if(page==='draft'){activeDraft=data;rememberDraft(data);renderDraft(next.tab);}else{activeSource=data;renderSource(data,next.tab);}
   }catch(error){if(version!==routeVersion)return;$('detail-content').innerHTML='<section class="panel"><h1 tabindex="-1">Arbeitsstand nicht verfügbar</h1><p>'+e(error.message)+'</p><p>Prüfe den Link und die registrierte Quelldatei. Vorbereitungen und Historie werden nicht verändert.</p><a href="#/documents">Zur Dokumentübersicht</a></section>';}
  }
 }else{
  activeDraft=null;activeSource=null;$('detail-content').textContent='';$('review-page').hidden=true;$('content').hidden=false;$('page-message').hidden=true;
  if(page==='consumers'){
   $('content').innerHTML='<section class="panel"><h1>Consumer-Repos</h1><p role="status">Stand wird geladen …</p></section>';
   try{const data=await api('/api/consumers');if(version===routeVersion)$('content').innerHTML=ConsumerView.render(data);}
   catch(error){if(version===routeVersion)$('content').innerHTML='<section class="panel"><h1>Consumer-Repos</h1><p>Stand nicht verfügbar: '+e(error.message)+'</p></section>';}
  }
  else if({overview,sources,intake,review,baseline}[page])({overview,sources,intake,review,baseline}[page])();
  else $('content').innerHTML='<section class="panel"><h1>Seite nicht gefunden</h1><p>Dieser Link gehört zu keinem verfügbaren Arbeitsstand.</p><a href="#/start">Zur Startseite</a></section>';
 }
 if(version===routeVersion&&!same){const title=document.querySelector('#main-content h1');if(title){title.tabIndex=-1;title.focus();}}
}
function continueDraft(id){
 const draft=state.drafts.find(d=>d.draft_id===id);if(!draft)return;
 const task=workspaceTools.nextTask(draft), view=reviewView('draft:'+id);
 if(task.filter){view.filter=task.filter;view.query='';view.selected=reviewTools.filteredRequirements(draft.requirements,draft.notes,'',task.filter)[0]?.id||null;}
 const next={page:'draft',id,tab:task.tab,...(view.selected?{item:view.selected}:{})};
 routeMemory.delete(workspaceTools.routeHash(next));
 return navigateRoute(next);
}
function pill(status){return `<span class="pill ${e(status)}">${e(labels[status] || status)}</span>`;}
function heading(kicker,title,text,action=''){return `<div class="intro"><div><p class="eyebrow">${e(kicker)}</p><h1>${e(title)}</h1><p class="muted">${e(text)}</p></div>${action}</div>`;}
function bind(id,event,fn){const el=$(id); if(el) el.addEventListener(event,async ev=>{try{await fn(ev);}catch(error){tell(error.message,true);}});}
function navigate(next){return navigateRoute({page:next});}
function docOptions(includeEmpty=false){return (includeEmpty?'<option value="">Neue, eigenständige Quelle</option>':'')+state.documents.map(d=>`<option value="${e(d.id)}">${e(d.title)} · ${e(d.id)}</option>`).join('');}
function nextAction(d){const draft=workspaceTools.sourceDraft(d.id,state.drafts);return draft?workspaceTools.nextTask(draft).label:'Prüfung beginnen';}
function table(docs){return `<div class="tablewrap"><table><thead><tr><th>Quelle</th><th>Quellenstatus</th><th>Zuständig</th><th>Nächster Schritt</th><th></th></tr></thead><tbody>${docs.map(d=>{const draft=workspaceTools.sourceDraft(d.id,state.drafts);return `<tr><td><a href="${workspaceTools.routeHash({page:'source',id:d.id})}"><strong>${e(d.title)}</strong></a><div class="muted">${e(d.id)} · ${e(d.version)}</div></td><td>${pill(d.status)}</td><td>${e(d.owner)}</td><td>${e(nextAction(d))}</td><td>${draft?`<button class="quiet" data-continue-draft="${e(draft.draft_id)}">${e(nextAction(d))} →</button>`:`<button class="quiet" data-start-source="${e(d.id)}">Prüfung beginnen →</button>`}</td></tr>`;}).join('')}</tbody></table></div>`;}
function draftCards(drafts=state.drafts){return drafts.length ? drafts.map(d=>{const task=workspaceTools.nextTask(d),p=reviewTools.reviewProgress(d.requirements,d.notes);return `<div class="card row"><div><h3><a href="${workspaceTools.routeHash({page:'draft',id:d.draft_id})}">${e(titleOf(d))}</a></h3><p class="muted">${e(d.created_at.slice(0,10))} · ${d.pr?'PR eingereicht':d.stale?'Quellenstand geändert':'Lokale Vorbereitung'}${d.source?` · ${p.noted}/${p.total} mit Prüfnotiz · ${p.clarification} Klärungen`:''}</p></div><button class="quiet" data-continue-draft="${e(d.draft_id)}">${e(task.label)} →</button></div>`;}).join('') : '<div class="empty">Noch keine Vorbereitung in diesem Arbeitsumfang. Beginne mit „Dokument wählen“.</div>';}
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
function focusControl(){return `<label class="focus-control">Arbeitsumfang<select id="work-focus"><option value="devsecops" ${documentListView.focus==='devsecops'?'selected':''}>DevSecOps · Policy, Directive und Baseline</option><option value="all" ${documentListView.focus==='all'?'selected':''}>Alle Dokumente einschließlich Architektur</option></select></label>`;}
function bindFocus(redraw){bind('work-focus','change',()=>{documentListView.focus=$('work-focus').value;redraw();});}
function overview(){
 const visible=state.drafts.filter(d=>!d.source||workspaceTools.inFocus(d.source,documentListView.focus)).sort((a,b)=>Number(!!a.pr)-Number(!!b.pr)||Number(!!a.stale)-Number(!!b.stale)||String(b.created_at).localeCompare(String(a.created_at)));
 $('content').innerHTML=heading('Start','Deine Dokumentprüfung.','Dokument wählen → Prüfen → Weitergeben. Setze deine Arbeit fort oder beginne eine neue Prüfung.')+
 `<section class="panel"><div class="sectionhead"><h2>Weiterarbeiten</h2>${focusControl()}</div>${draftCards(visible)}${visible.length!==state.drafts.length?'<p class="muted">Weitere Arbeitsstände bleiben unter „Alle Dokumente einschließlich Architektur“ erreichbar.</p>':''}</section>`+
 `<section class="panel task-card"><h2>Prüfung beginnen</h2><p>Wähle ein registriertes Dokument oder füge eine neue Datei hinzu.</p><button id="browse-documents">Dokument wählen →</button></section>`+
 `<details class="panel"><summary>Hintergrund und weitere Werkzeuge</summary><div class="actions"><button id="open-comparison" class="quiet">Dokumentvergleich vorbereiten</button><button id="open-readiness" class="quiet">Freigabevoraussetzungen</button></div>${processPhases()}</details>`;
 bind('browse-documents','click',()=>navigate('sources'));bindFocus(overview);
 bind('open-comparison','click',()=>navigate('review'));bind('open-readiness','click',()=>navigate('baseline'));
}
function sources(){
 $('content').innerHTML=heading('Schritt 1 von 3','Dokument wählen.','Wähle ein vorhandenes Dokument oder lade eine neue Datei beziehungsweise Version hoch.')+
 `<section class="panel"><div class="sectionhead">${focusControl()}<button id="new-intake">Neue Datei hinzufügen →</button></div><div class="toolbar"><input id="search" aria-label="Quellen suchen" placeholder="Titel, Dokument-ID oder Team suchen …"><select id="status-filter" aria-label="Status filtern"><option value="">Alle Status</option>${Object.entries(labels).filter(([k])=>['candidate','draft','intake','review','approved','superseded','retired'].includes(k)).map(([k,v])=>`<option value="${e(k)}">${e(v)}</option>`).join('')}</select></div><div id="source-table"></div></section>`;
 const filter=()=>{const q=$('search').value.toLowerCase();const docs=state.documents.filter(d=>workspaceTools.inFocus(d,documentListView.focus)&&(!$('status-filter').value||d.status===$('status-filter').value)&&`${d.id} ${d.title} ${d.owner}`.toLowerCase().includes(q));$('source-table').innerHTML=docs.length?table(docs):'<p class="empty">Keine Dokumente in dieser Auswahl. Ändere Suche oder Arbeitsumfang.</p>';};
 $('search').value=documentListView.query;$('status-filter').value=documentListView.status;filter();
 bind('search','input',()=>{documentListView.query=$('search').value;filter();});bind('status-filter','change',()=>{documentListView.status=$('status-filter').value;filter();});
 bind('new-intake','click',()=>navigate('intake'));bindFocus(sources);
}
async function beginSourceReview(id){
 const draft=workspaceTools.sourceDraft(id,state.drafts);
 if(draft)return continueDraft(draft.draft_id);
 const prepared=await api('/api/source-reviews',{source_id:id});await refresh(false);return showDraft(prepared.draft_id);
}
function workflowSteps(step,draft){
 const stages=[['Dokument wählen','#/documents'],['Prüfen',draft?workspaceTools.routeHash({page:'draft',id:draft.draft_id,tab:'requirements'}):null],['Weitergeben',draft?workspaceTools.routeHash({page:'draft',id:draft.draft_id,tab:'packet'}):null]];
 return `<nav aria-label="Prüfablauf"><ol class="wizard-progress review-steps">${stages.map(([title,url],i)=>`<li class="${i+1===step?'current':i+1<step?'visited':''}" ${i+1===step?'aria-current="step"':''}><span>${i+1}</span>${url?`<a href="${e(url)}">${title}</a>`:title}</li>`).join('')}</ol></nav>`;
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
   intakeDraft=emptyIntake();intakeStep=1;await refresh(false);await showDraft(draft.draft_id);tell(`Dokument vorbereitet: ${draft.requirements.length} gekennzeichnete Anforderungen gefunden.`);
  }catch(error){showIntakeError({message:error.message});}finally{if($('upload-button')){$('upload-button').disabled=false;$('upload-button').textContent='Dokument vorbereiten →';}}
 });
}
function review(){
 $('content').innerHTML=heading('Dokumentvergleich vorbereiten','Vergleichen und ein Review vorbereiten.','Hier kontrollierst du erkannte Anforderungen, prüfst mögliche Widersprüche und erstellst einen klar abgegrenzten Review-Umfang.')+
 `<div class="notice info"><strong>Gekennzeichnete Anforderungen prüfen:</strong> Ob die Kennung aus dem Original stammt, wird im Review bestätigt. Freitext und technische Zeilen-IDs erzeugen keine Anforderungen. Auswahl von Quellen erstellt nur ein Paket; sie startet keine automatische oder semantische Prüfung.</div><div class="grid2"><section class="panel"><h2>1. Quellen für ein Review auswählen</h2><p class="muted">Wähle nur Quellen, die gemeinsam geprüft werden sollen. Das Paket hält Quellenstand und Umfang per Hash fest.</p><form id="review-form">${state.documents.map(d=>`<div class="card"><label class="checks"><input type="checkbox" name="review-source" value="${e(d.id)}">${e(d.title)}</label><p class="muted">${e(d.id)} · ${e(d.owner)} · ${e(labels[d.status])}</p></div>`).join('')}<button id="package-button" type="submit">Gewählten Umfang vorbereiten →</button></form></section><section class="panel"><h2>2. Vorhandene Prüfergebnisse</h2><p>${pill(state.dcr.overall_status||'not_run')}</p><p class="muted">Review: ${e(state.dcr.review_id||'Kein Snapshot')}<br>Quellenstand: ${e(state.dcr.freshness?.status||'unbekannt')}</p><p class="small">Dieser gespeicherte Snapshot deckt nur seinen eigenen Umfang ab. Deine Auswahl links führt keine neue Prüfung aus.</p>${(state.dcr.findings||[]).map(f=>`<div class="card"><div class="row"><h3>${e(f.id)}</h3>${pill(f.disposition)}</div><p>${e(f.category)} · Belegstatus: ${e(f.evidence_status)}</p><p class="muted">Diese Ansicht enthält keine Originalbelege oder vollständige Interpretation. Prüfe die fachliche Entscheidung im zugehörigen privaten Review-Datensatz.</p></div>`).join('')||'<p class="muted">In dieser Projektion sind keine Befunde enthalten. Das beweist nicht, dass die Quellen widerspruchsfrei sind.</p>'}<h3>Originaltexte nebeneinander lesen</h3><p class="muted">Der Direktvergleich erleichtert das Auffinden von Unterschieden. Er bewertet sie nicht.</p><label>Erstes Dokument<select id="compare-a">${docOptions()}</select></label><label>Zweites Dokument<select id="compare-b">${docOptions()}</select></label><div class="actions"><button id="compare-button" class="quiet">Dokumente anzeigen →</button></div></section></div>`;
 bind('review-form','submit',async ev=>{ev.preventDefault();const ids=[...document.querySelectorAll('[name=review-source]:checked')].map(x=>x.value);if(!ids.length)throw new Error('Wähle mindestens eine Quelle.');const d=await api('/api/review-packages',{source_ids:ids});await refresh(false);await showDraft(d.draft_id);});
 bind('compare-button','click',async()=>{const [a,b]=await Promise.all([api('/api/sources/'+$('compare-a').value),api('/api/sources/'+$('compare-b').value)]);$('comparison-content').innerHTML='<p class="eyebrow">Originalvergleich · kein semantischer Review</p><h2>Fundstellen im direkten Vergleich</h2><div class="grid2">'+[a,b].map(v=>`<section><h3>${e(v.source.title)}</h3><details class="technical-details"><summary>Technischer Dateinachweis</summary><p class="hash">SHA-256: ${e(v.sha256)}</p></details>${sourceLines(v.lines)}</section>`).join('')+'</div>';$('detail').showModal();});
}
function baseline(){
 const baseline=state.process.authorized_source_baseline||{};
 $('content').innerHTML=heading('Freigabevoraussetzungen','Freigabeentscheidung vorbereiten.','Diese Ansicht zeigt die vorhandene Bereitschaft und fehlende Voraussetzungen. Sie startet keine neue Vollständigkeits- oder Konsistenzprüfung und erteilt keine Freigabe.')+
 `<section class="panel"><div class="sectionhead"><h2>Gemeldeter Stand und offene Voraussetzungen</h2>${pill(baseline.status||'unknown')}</div><p class="muted">Berichtsstand: ${e(state.process.generated_at||'Nicht verfügbar')} · vorhandene Projektion, keine neue Prüfung.</p>${(baseline.blocking_reasons||[]).map(x=>`<div class="baseline-blocker">${e(humanReason(x))}</div>`).join('')||'<p class="muted">Der Bericht nennt keine Blocker. Die formale Baseline-Entscheidung muss trotzdem durch die zuständige Autorität erfolgen.</p>'}<h3>Worauf bezieht sich dieser Stand?</h3><p>Auf den Checkout und das Quellenregister mit den folgenden Identitäten:</p><p class="hash">Checkout: ${e(state.context.commit)}<br>Quellenregister: ${e(state.context.register_sha256)}</p></section><section class="panel"><h2>Vor der formalen Freigabe</h2>${[['1','Quellenumfang und Autorität bestätigen','Genau die geprüften Quellen und Versionen festlegen.'],['2','Anforderungsentscheidungen abschließen','Offene Lifecycle- und Kandidatenentscheidungen klären.'],['3','Konsistenznachweise prüfen','Vollständigen, aktuellen Prüfumfang und die Behandlung aller Befunde belegen.'],['4','Freigabe versioniert dokumentieren','Zuständige Autorität, Datum, Entscheidung und Quellenhash erfassen.']].map(([n,t,s])=>`<div class="step"><b>${n}</b><div><h3>${t}</h3><p>${s}</p></div></div>`).join('')}<div class="notice info">Die Workbench bereitet die Entscheidung vor. Die formale Baseline-Freigabe wird außerhalb dieser App durch die benannte Autorität dokumentiert.</div></section>`;
}
function sourceLines(lines){return lines.map(x=>`<div class="line"><small>${e(locatorLabel(x.locator))}</small>${e(x.text)}</div>`).join('');}
function reqClassName(value){return ({author_identified:'Autorenkennung bestätigt',explicit_identifier:'explizite Kennung · Herkunft ungeprüft',extraction_row_id:'historische Extraktionskennung',inferred_candidate:'historischer Freitextvorschlag'})[value]||String(value||'Klasse ungeklärt').replaceAll('_',' ');}
function showSource(id){return navigateRoute({page:'source',id,tab:'current'});}
function statusSummary(data,editable){
 const p=reviewTools.reviewProgress(data.requirements||[],data.notes||[]),formal=data.formal_status;
 return `<section class="work-status" aria-label="Quellenstatus und lokale Vorbereitung"><div><span>Quelle${data.stale?' · gespeicherter Stand':''}</span><strong>${e(labels[data.source?.status]||'Dokumentauswahl')}</strong></div><div><span>Deine Vorbereitung</span><strong>${editable&&data.source?(p.total?`${p.noted} von ${p.total} mit Prüfnotiz`:'Anforderungskennungen klären'):data.source?'Noch keine lokale Prüfung':'Umfang vorbereitet'}</strong><small>Prüfnotizen sind Vorschläge</small></div><div><span>Offene Fragen</span><strong>${editable?`${p.clarification} Anforderungen`:'Noch nicht vorbereitet'}</strong><small>${reviewTools.latestNotes(data.notes||[]).get('source')?.outcome==='needs_clarification'?1:0} offene Dokumentfragen</small></div></section>${formal?`<details class="technical-details formal-history"><summary>Formale Entscheidungen und Historie</summary><p>${formal.recorded_decisions} Entscheidungen aufgezeichnet · ${formal.recorded_activations} Aktivierungen · ${formal.open_historical_proposals} offene historische Vorschläge</p><p>Diese Aufzeichnungen beziehen sich auf den gebundenen Quellenstand. Sie zählen nicht als Ergebnis deiner lokalen Vorbereitung.</p></details>`:''}`;
}
function implementationDetail(item,label='Umsetzung und Auswirkungen'){
 const hints=item||{risk:'unknown',mappings:[],reasons:['Keine bestätigte Verbindung vorhanden.']};
 const mappings=hints.mappings||[],confirmed=mappings.filter(m=>m.confirmed);
 const risk=hints.risk==='review_required'?'Prüfbedarf':'Auswirkung ungeklärt';
 const coverage={equivalent:'gleichwertige Abdeckung bestätigt',partial:'Teilabdeckung bestätigt',not_equivalent:'keine Gleichwertigkeit'};
 const modes={none:'keine Laufzeitwirkung autorisiert',report_only:'Report-only autorisiert',blocking:'Blocking autorisiert'};
 return `<details class="implementation-impact"><summary>${e(label)} · ${confirmed.length} bestätigte Zuordnungen · ${risk}</summary><p>${hints.requirement_ref?`Freigegebene Anforderungsrevision: <strong>${e(hints.requirement_ref)}</strong>`:'Keine exakt gebundene aktive Anforderungsrevision nachgewiesen.'}</p><ul>${(hints.reasons||[]).map(reason=>`<li>${e(reason)}</li>`).join('')}</ul>${mappings.map(m=>`<article class="card"><h3>${e(m.artifact_id||m.id)}</h3><code>${e(m.path)}</code><p>${m.confirmed?e(coverage[m.coverage]||'Abdeckung ungeklärt'):'Zuordnung ungeklärt'} · ${e(m.reason)}</p><p>${m.confirmed?e(modes[m.enforcement_authorization]||'Autorisierter Modus ungeklärt'):`Aufgezeichneter Modus ungeprüft: ${e(m.enforcement_authorization||'unbekannt')}`} · tatsächliche Ausführung separat nachzuweisen.</p><details class="technical-details"><summary>Zuordnungsbelege</summary><p>${e(m.id)} · entschieden am ${e(m.decided_at||'Unbekannt')}</p><p>${e(m.decision_ref)}</p><p class="hash">Erwarteter Artefakt-SHA-256: ${e(m.sha256)}</p></details></article>`).join('')}<p class="muted">Veröffentlichung: ${e(hints.publication||'Nicht verknüpft')}<br>Laufzeit: ${e(hints.runtime||'Nicht verknüpft')}<br>Die Anzeige begründet Prüfbedarf. Sie bewertet keine konkrete Textänderung und bestätigt keine vollständige Umsetzung.</p></details>`;
}
function renderSource(v,tab='current'){
 const id=v.source.id,brief=(state.briefs||[]).find(x=>x.source_id===id),draft=workspaceTools.sourceDraft(id,state.drafts);
 $('detail-content').innerHTML=`<a class="back-link" href="#/documents">← Dokumente</a>${workflowSteps(1)}${heading('Registriertes Dokument',e(v.source.title),'Lies das Dokument oder beginne eine lokale Prüfung mit Prüfnotizen.')}<p>${e(id)} · ${e(v.source.owner)} · ${e(v.source.version)}</p>${statusSummary(v,false)}<div class="actions">${draft?`<button data-continue-draft="${e(draft.draft_id)}">${e(workspaceTools.nextTask(draft).label)} →</button>`:''}<button id="prepare-source-review" class="${draft?'quiet':''}">Prüfung beginnen →</button></div><p class="muted">Eine neue lokale Vorbereitung verändert weder die Quelle noch vorhandene Entscheidungen.</p><details class="technical-details"><summary>Technischer Dateinachweis</summary><p class="hash">SHA-256: ${e(v.sha256)}</p></details>${v.warnings.length?`<div class="notice">${v.warnings.map(e).join('<br>')}</div>`:''}${brief?`<details class="card"><summary>Vorhandenes Aufnahme-Briefing</summary><pre class="line">${e(JSON.stringify(brief,null,2))}</pre></details>`:''}<nav class="tabs" aria-label="Dokumentansichten"><button id="source-current" class="${tab==='current'?'selected':''}" ${tab==='current'?'aria-current="page"':''}>Aktuelle Extraktion</button><button id="source-history" class="${tab==='history'?'selected':''}" ${tab==='history'?'aria-current="page"':''}>Frühere Vorschläge und Entscheidungen</button></nav><div id="source-body"></div>`;
 bind('prepare-source-review','click',async()=>{
  const button=$('prepare-source-review');button.disabled=true;button.textContent='Prüfung wird vorbereitet …';
  try{const prepared=await api('/api/source-reviews',{source_id:id});await refresh(false);await showDraft(prepared.draft_id);}finally{if(button.isConnected){button.disabled=false;button.textContent='Prüfung beginnen →';}}
 });
 bind('source-current','click',()=>navigateRoute({page:'source',id,tab:'current'}));bind('source-history','click',()=>navigateRoute({page:'source',id,tab:'history'}));
 if(tab==='history')loadHistory(id,'source-body',reviewTools.partitionRequirements(v.requirements).historical);
 else{$('source-body').innerHTML='<div id="requirement-workspace"></div>';mountRequirementReview(v,'source:'+id,false);}
}
function staleNotice(d){
 if(!d.stale)return '';
 const reasons=d.stale_details?.reasons||[];
 return `<section class="notice stale-notice" aria-label="Geänderter Quellenstand"><h2>Vorbereitung an einen früheren Stand gebunden</h2><p>Notizen und Export sind gesperrt. Deine bisherige Vorbereitung und Historie bleiben lesbar erhalten.</p><ul>${reasons.map(r=>`<li>${e(workspaceTools.staleMessages[r.code]||'Der gespeicherte Stand weicht vom aktuellen ab.')}${r.source_id?` <strong>${e(r.source_id)}</strong>`:''}${r.previous||r.current?`<details><summary>Änderungsnachweis</summary><p class="hash">Bisher: ${e(r.previous||'Nicht vorhanden')}<br>Aktuell: ${e(r.current||'Nicht vorhanden')}</p></details>`:''}</li>`).join('')||'<li>Der gespeicherte Repository- oder Quellenstand ist nicht mehr aktuell.</li>'}</ul><p>Eine neue Vorbereitung beginnt ohne übernommene Notizen oder Entscheidungen. Vergleiche die beiden Stände, bevor du Vorschläge erneut erfasst.</p><button id="restart-preparation">Neue Vorbereitung starten →</button></section>`;
}
function reviewView(key){
 if(!reviewViews.has(key))reviewViews.set(key,{selected:null,query:'',filter:'all',pane:'requirement',unsaved:{},reviewer:'',saving:new Set(),savingGeneral:false});
 return reviewViews.get(key);
}
function captureItemNote(){
 const form=$('item-note-form');
 if(form){
  const view=reviewView(form.dataset.reviewKey);
  const values={reviewer:$('item-reviewer').value,outcome:$('item-outcome').value,rationale:$('item-rationale').value};
  if(view.unsaved[form.dataset.subject]||JSON.stringify(values)!==form.dataset.initialValues)view.unsaved[form.dataset.subject]=values;
  view.reviewer=$('item-reviewer').value;
 }
 const general=$('note-form');
 if(general){
  const view=reviewView(general.dataset.reviewKey);
  const values={subject:$('note-subject').value,reviewer:$('note-reviewer').value,outcome:$('note-outcome').value,rationale:$('note-rationale').value};
  if(view.generalNote||JSON.stringify(values)!==general.dataset.initialValues)view.generalNote=values;
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
 const documentQuestion=latest.get('source');
 const extra=documentQuestion?.outcome==='needs_clarification'?`<p><strong>Dokumentfrage:</strong> ${e(documentQuestion.rationale)}</p>`:'';
 return extra+(open.length?`<details class="handoff-questions" open><summary>Für den anschließenden Review offen (${open.length})</summary><ul>${open.map(r=>`<li><strong>${e(reviewTools.requirementLabel(r))}</strong>: ${latest.has(r.id)?'Klärungsbedarf – '+e(latest.get(r.id).rationale):'noch ohne Prüfnotiz'}</li>`).join('')}</ul></details>`:'');
}
function syncReadingLayout(){
 const tabs=$('reading-tabs');if(!tabs)return;
 const small=window.innerWidth<=900, key=tabs.dataset.reviewKey, view=reviewView(key);
 tabs.hidden=!small;
 for(const name of ['requirement','original']){
  const panel=$('reading-'+name),button=$('reading-tab-'+name);
  panel.hidden=small&&view.pane!==name;
  panel.setAttribute('role',small?'tabpanel':'region');
  button.setAttribute('aria-selected',String(view.pane===name));button.tabIndex=view.pane===name?0:-1;
 }
}
function mountRequirementReview(data,key,editable){
 const view=reviewView(key),notes=data.notes||[],rows=data.requirements||[];
 const {current,historical}=reviewTools.partitionRequirements(rows);
 const visible=reviewTools.filteredRequirements(rows,notes,view.query,view.filter),latest=reviewTools.latestNotes(notes);
 const invalidItem=!!currentRoute.item&&!current.some(r=>r.id===currentRoute.item);
 if(!invalidItem&&!visible.some(r=>r.id===view.selected)&&visible.length)view.selected=visible[0].id;
 const selected=invalidItem?null:visible.find(r=>r.id===view.selected);
 const locked=data.stale||!!data.pr||view.saving.has(selected?.id);
 const status=r=>latest.has(r.id)?outcomeLabels[latest.get(r.id).outcome]:'Ohne Prüfnotiz';
 let detail=invalidItem?'<div class="notice">Die verlinkte Anforderung gehört nicht zur aktuellen expliziten Extraktion. Frühere Einträge bleiben in der Historie.<button type="button" id="reset-item" class="quiet">Aktuelle Anforderungen ansehen</button></div>':
  '<div class="empty">'+(current.length?'Kein Treffer. Ändere Suche oder Filter; der Originaltext bleibt verfügbar.':'Keine explizit gekennzeichneten Anforderungen gefunden. Lies das Original und halte fest, was für die weitere Prüfung fehlt.')+'</div>';
 let initialValues;
 if(selected){
  const itemNotes=notes.filter(n=>n.subject===selected.id);
  const pending=view.unsaved[selected.id]||{reviewer:view.reviewer||notes.at(-1)?.reviewer||'',outcome:'confirm_candidate',rationale:''};
  initialValues={reviewer:pending.reviewer,outcome:pending.outcome,rationale:pending.rationale};
  detail=`<p class="eyebrow">Anforderung ${current.indexOf(selected)+1} von ${current.length}</p><h2 id="selected-requirement" tabindex="-1">${e(reviewTools.requirementLabel(selected))}</h2><p class="requirement-statement">${e(selected.statement)}</p><p class="muted">${e(reqClassName(selected.identification_class))} · ${e(locatorLabel(selected.source_locator))}</p><p class="muted">Prüfe die Aussage an der markierten Originalstelle.</p>`;
  if(editable){
   detail+=implementationDetail(data.implementation?.[selected.id]);
   if(data.target){const prior=(data.target.requirements||[]).filter(r=>r.source_requirement_id===selected.source_requirement_id);if(prior.length===1)detail+=implementationDetail(data.target.implementation?.[prior[0].id],'Bisherige Version · Umsetzung und Auswirkungen');}
   detail+=`<h3>Deine Einschätzung</h3><p class="muted">${e(status(selected))}</p><form id="item-note-form" data-review-key="${e(key)}" data-subject="${e(selected.id)}"><fieldset id="item-fields" ${locked?'disabled':''}><label>Bearbeiter / Reviewer<input id="item-reviewer" required maxlength="200" autocomplete="name" value="${e(pending.reviewer)}"></label><label>Was schlägst du vor?<select id="item-outcome">${['confirm_candidate','reject_candidate','needs_clarification'].map(outcome=>`<option value="${outcome}" ${pending.outcome===outcome?'selected':''}>${e(outcomeLabels[outcome])}</option>`).join('')}</select></label><label>Begründung oder offene Frage<textarea id="item-rationale" required maxlength="4000">${e(pending.rationale)}</textarea></label><button type="submit" id="save-item-note">${view.saving.has(selected.id)?'Wird gespeichert …':'Speichern und weiter →'}</button></fieldset><p id="item-save-status" class="save-status" role="status" aria-live="polite">${view.saving.has(selected.id)?'Speichern läuft.':view.unsaved[selected.id]?'Ungespeicherte Eingaben':'Bereit für deine Prüfnotiz'}</p></form>`;
  }
  if(!editable)detail+=implementationDetail(data.implementation?.[selected.id]);
  if(itemNotes.length)detail+=`<details class="technical-details"><summary>Alle Prüfnotizen (${itemNotes.length})</summary>${itemNotes.map(n=>`<article class="card"><strong>${e(outcomeLabels[n.outcome])}</strong><p>${e(n.rationale)}</p><small>${e(n.reviewer)} · ${e(n.recorded_at)} · Vorschlag</small></article>`).join('')}</details>`;
  const index=visible.indexOf(selected);
  detail+=`<div class="item-navigation"><button class="quiet" id="review-previous" ${index===0?'disabled':''}>← Vorherige</button><button class="quiet" id="review-next" ${index===visible.length-1?'disabled':''}>${editable?'Überspringen →':'Nächste Anforderung →'}</button></div>`;
 }
 const locator=selected?.source_locator;
 const original=(data.lines||[]).map(line=>`<div class="line ${locator===line.locator?'current-source-line':''}" ${locator===line.locator?'data-selected-locator="true"':''}><small>${e(locatorLabel(line.locator))}</small>${locator===line.locator?`<mark>${e(line.text)}</mark>`:e(line.text)}</div>`).join('');
 $('requirement-workspace').innerHTML=`${editable?(current.length?'':preparationSummary(data)):`<p class="muted">${current.length} explizit gekennzeichnete Anforderungen. Zum Erfassen von Vorschlägen eine lokale Prüfung vorbereiten.</p>`}${historical.length?`<div class="notice">${historical.length} ältere Einträge stehen separat in der Historie und zählen nicht zur aktuellen Extraktion.</div>`:''}<div class="toolbar review-toolbar"><input id="requirement-search" aria-label="Anforderungen suchen" placeholder="Kennung oder Wortlaut suchen …" value="${e(view.query)}">${editable?`<select id="requirement-filter" aria-label="Prüfnotizen filtern"><option value="all">Alle Anforderungen</option><option value="unnoted" ${view.filter==='unnoted'?'selected':''}>Ohne Prüfnotiz</option><option value="clarification" ${view.filter==='clarification'?'selected':''}>Klärungsbedarf</option></select>`:''}</div><div id="reading-tabs" class="reading-tabs" role="tablist" aria-label="Prüfansichten" data-review-key="${e(key)}"><button id="reading-tab-requirement" type="button" role="tab" aria-controls="reading-requirement">Anforderung und Prüfnotiz</button><button id="reading-tab-original" type="button" role="tab" aria-controls="reading-original">Originaltext</button></div><div class="requirement-review-grid"><nav class="requirement-list" aria-label="Anforderungen auswählen">${visible.map(row=>`<button type="button" class="requirement-choice ${row.id===selected?.id?'selected':''}" data-review-select="${e(row.id)}" ${row.id===selected?.id?'aria-current="true"':''}><strong>${e(reviewTools.requirementLabel(row))}</strong><span>${e(row.statement.slice(0,100))}${row.statement.length>100?' …':''}</span>${editable?`<small>${e(status(row))}</small>`:''}</button>`).join('')||'<p class="muted">Keine passenden Anforderungen</p>'}</nav><section id="reading-requirement" class="review-item" aria-label="Anforderung und Prüfnotiz" aria-labelledby="reading-tab-requirement">${detail}</section><section id="reading-original" class="original-pane" aria-label="Originaltext" aria-labelledby="reading-tab-original"><h2>Originaltext</h2><p class="muted">${locator?e(locatorLabel(locator))+' hervorgehoben':'Gespeicherter Textauszug'} · ${e(data.source?.version||'')}</p><div class="original-lines">${original||'<p class="notice">Kein lesbarer Originaltext vorhanden. Prüfe die Quelldatei und dokumentiere diese Lücke.</p>'}</div></section></div>`;
 if($('item-note-form'))$('item-note-form').dataset.initialValues=JSON.stringify(initialValues);
 const redraw=focus=>{captureItemNote();const position=$('requirement-search')?.selectionStart;mountRequirementReview(data,key,editable);if(focus){$(focus)?.focus();if(focus==='requirement-search'&&position!==null)$('requirement-search').setSelectionRange(position,position);}};
 const select=id=>{captureWorkspace();view.selected=id;routeSelection(id);redraw('selected-requirement');const line=document.querySelector('[data-selected-locator]');if(line?.scrollIntoView)line.scrollIntoView({block:'nearest'});};
 bind('requirement-search','input',()=>{view.query=$('requirement-search').value;redraw('requirement-search');});
 bind('requirement-filter','change',()=>{view.filter=$('requirement-filter').value;redraw('requirement-filter');});
 $('requirement-workspace').querySelectorAll('[data-review-select]').forEach(button=>button.addEventListener('click',()=>select(button.dataset.reviewSelect)));
 bind('reset-item','click',()=>{view.query='';view.filter='all';view.selected=current[0]?.id||null;routeSelection(view.selected,true);redraw('selected-requirement');});
 bind('review-previous','click',()=>select(visible[visible.indexOf(selected)-1]?.id));
 bind('review-next','click',()=>select(visible[visible.indexOf(selected)+1]?.id));
 const choosePane=(name,focus=false)=>{view.pane=name;syncReadingLayout();if(focus)$('reading-tab-'+name).focus();};
 for(const name of ['requirement','original']){
  const button=$('reading-tab-'+name);button.addEventListener('click',()=>choosePane(name));
  button.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();choosePane(event.key==='Home'?'requirement':event.key==='End'?'original':name==='original'?'requirement':'original',true);}});
 }
 syncReadingLayout();
 bind('item-note-form','input',()=>{captureItemNote();$('item-save-status').textContent='Ungespeicherte Eingaben';});
 bind('item-note-form','submit',async ev=>{
  ev.preventDefault();if(locked||view.saving.has(selected.id))return;captureItemNote();
  const payload={subject:selected.id,reviewer:$('item-reviewer').value,outcome:$('item-outcome').value,rationale:$('item-rationale').value};
  view.saving.add(selected.id);$('item-fields').disabled=true;$('save-item-note').textContent='Wird gespeichert …';$('item-save-status').textContent='Speichern läuft.';
  try{
   const updated=await api('/api/drafts/'+data.draft_id+'/notes',payload);captureItemNote();rememberDraft(updated);view.saving.delete(selected.id);delete view.unsaved[selected.id];
   if(activeDraft?.draft_id===data.draft_id){activeDraft=rememberDraft(updated);if($('item-note-form')?.dataset.reviewKey===key&&currentRoute.tab==='requirements'){if(view.selected===selected.id){const next=visible.slice(visible.indexOf(selected)+1).find(r=>!reviewTools.latestNotes(updated.notes).has(r.id));if(next){view.selected=next.id;routeSelection(next.id);}}renderDraft('requirements',false);}}
   tell('Einschätzung gespeichert. Die formale Entscheidung bleibt im anschließenden Review.');
  }catch(error){
   try{const fresh=await api('/api/drafts/'+data.draft_id);rememberDraft(fresh);if(activeDraft?.draft_id===data.draft_id){captureItemNote();activeDraft=fresh;renderDraft(currentRoute.tab,false);}}catch(_){}
   throw error;
  }finally{
   view.saving.delete(selected.id);const form=$('item-note-form');
   if(form?.dataset.reviewKey===key){$('item-fields').disabled=!!activeDraft?.stale||!!activeDraft?.pr||view.saving.has(form.dataset.subject);$('save-item-note').textContent='Speichern und weiter →';$('item-save-status').textContent=view.saving.has(form.dataset.subject)?'Speichern läuft.':view.unsaved[form.dataset.subject]?'Ungespeicherte Eingaben':'Bereit für deine Prüfnotiz';}
  }
 });
 bind('add-document-question','click',()=>{renderDraft('notes');$('note-subject').value='source';$('note-rationale').focus();});
 if(selected&&!invalidItem)routeSelection(selected.id,true);
}

async function loadHistory(sourceId,containerId,olderRows=[],notes=[]){
 const container=$(containerId);container.innerHTML='<p class="muted">Frühere Aufzeichnungen werden geladen …</p>';
 try {
  const history=sourceId?await api('/api/sources/'+sourceId+'/history'):{cases:[]};
  if(!container.isConnected)return;
  container.innerHTML=`<h3>Frühere Vorschläge und Entscheidungen</h3><p class="muted">Diese Aufzeichnungen bleiben unverändert erhalten. Sie sind keine aktuelle Extraktion und zählen nicht zum lokalen Prüffortschritt.</p>${history.cases.map(c=>`<section class="history-case"><h4>${e(c.case_id)}</h4><p class="muted">${e(c.source.source_id)} · ${c.proposals.length} aufgezeichnete Vorschläge</p>${!c.source_matches?'<div class="notice">Der aufgezeichnete Quellenstand weicht vom heutigen Dokument ab. Entscheidungen nicht ungeprüft auf die aktuelle Extraktion übertragen.</div>':''}<details class="technical-details"><summary>Quellenbindung des früheren Falls</summary><p class="hash">${e(c.path)}<br>SHA-256: ${e(c.source.source_sha256)}</p></details>${c.proposals.map(p=>`<details class="history-record"><summary>${e(p.source_requirement_id)} · ${p.decision?'Entscheidung aufgezeichnet':'Ohne aufgezeichnete Entscheidung'}${p.activation?' · Umsetzung aufgezeichnet':''}</summary><p>${e(p.statement)}</p>${p.decision?`<h4>Aufgezeichnete Entscheidung</h4><p>${e(p.decision.rationale)}</p><p class="muted">${e(p.decision.decided_by)} · ${e(p.decision.decided_at)} · ${e(p.decision.disposition)}</p>`:''}<details class="technical-details"><summary>Vollständiger früherer Datensatz</summary><pre class="line">${e(JSON.stringify(p,null,2))}</pre></details></details>`).join('')}</section>`).join('')}${olderRows.length?`<h4>Ältere Einträge dieses lokalen Entwurfs (${olderRows.length})</h4>${olderRows.map(r=>`<details class="history-record"><summary>${e(reviewTools.requirementLabel(r))} · ${e(reqClassName(r.identification_class))}</summary><p>${e(r.statement)}</p>${notes.filter(n=>n.subject===r.id).map(n=>`<p>${e(outcomeLabels[n.outcome])}: ${e(n.rationale)} · ${e(n.reviewer)}</p>`).join('')}</details>`).join('')}`:''}${!history.cases.length&&!olderRows.length?'<div class="empty">Keine früheren Lifecycle-Vorschläge für dieses Dokument gespeichert.</div>':''}`;
 }catch(error){if(container.isConnected)container.innerHTML='<div class="notice">Frühere Aufzeichnungen konnten nicht geladen werden. Versuche es erneut; die aktuelle Extraktion bleibt davon getrennt.</div>';}
}
function showDraft(id){return navigateRoute({page:'draft',id,tab:'requirements'});}
function renderDraft(tab,capture=true){
 if(!activeDraft)return;
 if(currentRoute.page==='draft'&&currentRoute.tab!==tab)return navigateRoute({...currentRoute,tab});
 if(capture)captureItemNote();
 const d=activeDraft, source=d.source;
 const link=d.pr?.url;const safePR=workspaceTools.safePR(link);
 $('detail-content').innerHTML=`<a class="back-link" href="#/start">← Vorbereitungen</a><p class="eyebrow">${d.kind==='source_candidate'?'Lokaler Dokumententwurf':source?'Lokale Prüfung eines registrierten Dokuments':'Vorbereitetes gemeinsames Review'}</p><h1 tabindex="-1">${e(titleOf(d))}</h1><p class="muted">${source?e(source.id)+' · '+e(source.owner)+' · ':''}${e(d.created_at)} · lokale Vorbereitung</p>${workflowSteps(tab==='packet'?3:2,d)}${statusSummary(d,true)}${staleNotice(d)}${d.warnings?.length?`<div class="notice">${d.warnings.map(e).join('<br>')}</div>`:''}<details class="review-tools" ${['delta','notes','history'].includes(tab)?'open':''}><summary>Notizen, Vergleich und Historie</summary><div class="tabs"><button data-tab="requirements" class="${tab==='requirements'?'selected':''}">${source?'Anforderungen prüfen':'Dokumentauswahl'}</button>${d.target?`<button data-tab="delta" class="${tab==='delta'?'selected':''}">Änderungen ansehen</button>`:''}<button data-tab="notes" class="${tab==='notes'?'selected':''}">Alle Notizen (${d.notes.length})</button>${source?`<button data-tab="history" class="${tab==='history'?'selected':''}">Frühere Vorschläge</button>`:''}<button data-tab="packet" class="${tab==='packet'?'selected':''}">Weitergeben</button></div></details><div id="draft-body"></div>`;
 bind('restart-preparation','click',async()=>{
  if(d.kind==='source_review'&&state.documents.some(x=>x.id===d.source.id))return showSource(d.source.id);
  if(d.kind==='review_package')return navigate('review');
  intakeDraft=emptyIntake();intakeStep=1;await navigate('intake');tell('Wähle die aktuelle Originaldatei und bestätige ihre Angaben erneut. Der frühere Entwurf bleibt erhalten.');
 });
 const body=$('draft-body');
 if(tab==='requirements'){
  body.innerHTML=source?'<div id="requirement-workspace"></div>':
  `<div class="notice info">Quellenumfang vorbereitet · semantische Ausführung: <strong>not_run</strong>. Kein genehmigtes Providerpaket und keine Baseline-Freigabe.</div>${d.manifest.map(m=>`<div class="card"><h3>${e(m.source_id)}</h3><p>${pill(m.status)} · ${e(m.owner)} · ${m.requirements_count} extrahierte Kandidaten</p><p class="hash">${e(m.sha256)}</p>${m.warnings.length?`<p class="error">${m.warnings.map(e).join(', ')}</p>`:''}</div>`).join('')}`;
  if(source)mountRequirementReview(d,'draft:'+d.draft_id,true);
 }
 if(tab==='history')loadHistory(d.kind==='source_review'?source.id:d.target?.source.id,'draft-body',reviewTools.partitionRequirements(d.requirements).historical,d.notes);
 if(tab==='delta')body.innerHTML=d.target?`<p class="muted">Abgleich mit ${e(d.target.source.title)}. Explizite Requirement-Kennungen verbinden Einträge derselben Anforderung auch bei abweichendem Wortlaut. Gleichwertigkeit und Änderungen benötigen fachliche Bestätigung.</p>${d.deltas.map(x=>`<div class="card"><div class="reqhead">${pill(x.status)}${x.matched_identifier?`<strong>Kennung ${e(x.matched_identifier)}</strong>`:`<small>Abgleich: ${e(x.match_basis==='text_similarity'?'Textähnlichkeit':x.match_basis==='unmatched'?'keine Zuordnung':'Kennung')}</small>`}<small>Review-Priorität: ${e(x.review_priority)}</small></div><div class="grid2"><div><h3>Bisher · ${e(x.target_requirement?.source_requirement_id||x.target_requirement?.extraction_row_id||'')}</h3><p>${e(x.target_requirement?.statement||'—')}</p><span class="muted">${e(x.target_requirement?.source_locator||'')}</span></div><div><h3>Kandidat · ${e((x.candidate_requirement?.recognized_requirement_ids||[]).join(', ')||x.candidate_requirement?.source_requirement_id||x.candidate_requirement?.extraction_row_id||'')}</h3><p>${e(x.candidate_requirement?.statement||'—')}</p><span class="muted">${e(x.candidate_requirement?.source_locator||'')}</span></div></div></div>`).join('')}`:'<div class="empty">Keine Vorgängerquelle ausgewählt. Keine Ersatzentscheidung wird angenommen.</div>';
 if(tab==='notes'){
  const noteView=reviewView('draft:'+d.draft_id);
  const options=source?[{id:'source',name:'Dokument insgesamt'},...reviewTools.partitionRequirements(d.requirements).current.map(x=>({id:x.id,name:reviewTools.requirementLabel(x)}))]:d.manifest.map(m=>({id:m.source_id,name:m.source_id}));
  body.innerHTML=`<div class="notice info">Deine Einschätzung wird als Vorschlag gespeichert. Die formale Entscheidung erfolgt im anschließenden Review.</div>${d.notes.map(n=>`<div class="card"><h3>${e(outcomeLabels[n.outcome])}</h3><p>${e(n.rationale)}</p><span class="muted">${e(n.subject)} · ${e(n.reviewer)} · ${e(n.recorded_at)}</span></div>`).join('')}<form id="note-form" data-review-key="${e('draft:'+d.draft_id)}"><fieldset id="general-note-fields" ${d.stale||d.pr||noteView.savingGeneral?'disabled':''}><div class="formgrid"><label>Bezug<select id="note-subject">${options.map(o=>`<option value="${e(o.id)}">${e(o.name)}</option>`).join('')}</select></label><label>Reviewer / Bearbeiter<input id="note-reviewer" maxlength="200" required placeholder="Name oder eindeutige Kennung"></label><label class="full">Vorschlag<select id="note-outcome">${Object.entries(outcomeLabels).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label><label class="full">Begründung und offene Fragen<textarea id="note-rationale" required maxlength="4000"></textarea></label></div><div class="actions"><button ${d.stale||d.pr?'disabled':''} type="submit">${noteView.savingGeneral?'Wird gespeichert …':'Notiz speichern'}</button></div></fieldset><p id="general-save-status" role="status" class="save-status">${noteView.savingGeneral?'Speichern läuft.':noteView.generalNote?'Ungespeicherte Eingaben':'Bereit für deine Prüfnotiz'}</p></form>`;
  const saved=reviewView('draft:'+d.draft_id).generalNote;
  if(saved){for(const field of ['subject','reviewer','outcome','rationale'])$('note-'+field).value=saved[field];}
  else $('note-reviewer').value=reviewView('draft:'+d.draft_id).reviewer||d.notes.at(-1)?.reviewer||'';
  $('note-form').dataset.initialValues=JSON.stringify({subject:$('note-subject').value,reviewer:$('note-reviewer').value,outcome:$('note-outcome').value,rationale:$('note-rationale').value});
  bind('note-form','input',()=>{captureItemNote();$('general-save-status').textContent='Ungespeicherte Eingaben';});
  bind('note-form','submit',async ev=>{
   ev.preventDefault();if(d.stale||d.pr||noteView.savingGeneral)return;captureItemNote();noteView.savingGeneral=true;$('general-note-fields').disabled=true;$('general-save-status').textContent='Speichern läuft.';
   try {const updated=await api('/api/drafts/'+d.draft_id+'/notes',noteView.generalNote);captureItemNote();rememberDraft(updated);delete noteView.generalNote;noteView.savingGeneral=false;if(activeDraft?.draft_id===d.draft_id){activeDraft=rememberDraft(updated);if($('note-form')?.dataset.reviewKey==='draft:'+d.draft_id)renderDraft('notes',false);}tell('Prüfnotiz gespeichert.');}
   catch(error){try{const fresh=await api('/api/drafts/'+d.draft_id);rememberDraft(fresh);if(activeDraft?.draft_id===d.draft_id){captureItemNote();activeDraft=fresh;renderDraft(currentRoute.tab,false);}}catch(_){}throw error;}
   finally {noteView.savingGeneral=false;if($('note-form')?.dataset.reviewKey==='draft:'+d.draft_id){$('general-note-fields').disabled=!!activeDraft?.stale||!!activeDraft?.pr;$('general-save-status').textContent=noteView.generalNote?'Ungespeicherte Eingaben':'Bereit für deine Prüfnotiz';}}
  });
 }
 if(tab==='packet'){
  const packetView=reviewView('draft:'+d.draft_id);
  const progress=reviewTools.reviewProgress(d.requirements||[],d.notes||[]),documentQuestion=reviewTools.latestNotes(d.notes||[]).get('source');
  const handoffTitle=!progress.total?'Zur Klärung weitergeben':progress.unnoted||progress.clarification||documentQuestion?.outcome==='needs_clarification'?'Teilweise Vorbereitung weitergeben':'Zur Übergabe vorbereitet';
  body.innerHTML=`<h2>${handoffTitle}</h2><div class="notice">Das Paket enthält private Quelldaten und Vorschläge. Vor einem PR prüfen, ob diese Inhalte in das Zielrepo dürfen. Der PR bleibt ein Draft und wird nicht durch die App gemergt.</div><h3>Vorbereitung zur Übergabe</h3>${source?preparationSummary(d)+handoffQuestions(d):''}<h3>Das enthält dein Review-Paket</h3><p>${d.kind==='source_candidate'?'Originaldatei · Vorschlag für das Quellenregister · Änderungsbeschreibung · Prüfnotizen':source?'Unveränderte registrierte Originaldatei · Änderungsbeschreibung · Prüfnotizen':'Liste der ausgewählten Dokumente mit Dateinachweisen · Änderungsbeschreibung · Prüfnotizen'}</p><details class="technical-details"><summary>Technische Paketdaten und weiterführende Prüfungen</summary><p class="hash">Basis-Commit: ${e(d.context.commit)}<br>Register: ${e(d.context.register_sha256)}</p><p class="muted">Das Paket startet keine inhaltliche Konsistenzprüfung. Dafür sind ein festgelegter Prüfumfang und eine gesonderte Laufentscheidung erforderlich.</p></details><div class="actions"><button id="export-packet" ${d.stale||packetView.exporting?'disabled':''}>${packetView.exporting?'Paket wird geladen …':'Review-Paket herunterladen'}</button></div>${safePR?`<p class="actions"><a href="${e(link)}" target="_blank" rel="noopener noreferrer">Draft-PR öffnen →</a></p>`:!d.pr&&state.pr_enabled?`<form id="pr-form"><div class="checks actions"><label><input id="publish-confirm" type="checkbox" required>Ich habe die Inhalte geprüft und möchte sie im Repository als Draft-PR veröffentlichen.</label></div><div class="actions"><button id="pr-button" ${d.stale||packetView.publishing?'disabled':''}>${packetView.publishing?'Draft-PR wird vorbereitet …':'Draft-PR erstellen'}</button></div></form>`:'<p class="muted actions">Die direkte PR-Erstellung ist hier nicht aktiviert. Lade das Review-Paket herunter und gib es über euren üblichen Review-Weg weiter.</p>'}`;
  bind('export-packet','click',async()=>{
   if(d.stale||packetView.exporting)return;packetView.exporting=true;$('export-packet').disabled=true;$('export-packet').textContent='Paket wird geladen …';
   try{const r=await fetch('/api/drafts/'+d.draft_id+'/packet');if(!r.ok){const error=await r.json();throw new Error(error.error);}const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download=`AXIOM-${d.draft_id}.zip`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);tell('Review-Paket heruntergeladen.');}
   finally{packetView.exporting=false;if(activeDraft?.draft_id===d.draft_id&&$('export-packet')){$('export-packet').disabled=!!activeDraft.stale;$('export-packet').textContent='Review-Paket herunterladen';}}
  });
  bind('pr-form','submit',async ev=>{
   ev.preventDefault();if(d.stale||d.pr||packetView.publishing)return;packetView.publishing=true;const confirmation=$('publish-confirm').checked;$('pr-button').disabled=true;$('pr-button').textContent='Draft-PR wird vorbereitet …';
   try{await api('/api/drafts/'+d.draft_id+'/pr',{confirm_publication:confirmation});const updated=await api('/api/drafts/'+d.draft_id);rememberDraft(updated);if(activeDraft?.draft_id===d.draft_id){captureItemNote();activeDraft=rememberDraft(updated);renderDraft(currentRoute.tab,false);}tell('Draft-PR erstellt. Die formale Freigabe erfolgt im Repository.');}
   finally{packetView.publishing=false;if(activeDraft?.draft_id===d.draft_id&&$('pr-button')){$('pr-button').disabled=!!activeDraft.stale;$('pr-button').textContent='Draft-PR erstellen';}}
  });
 }
 const order=source?(d.target?['requirements','delta','packet']:['requirements','packet']):['requirements','notes','packet'];
 const next=tab==='notes'?'packet':tab==='requirements'?'packet':order[order.indexOf(tab)+1];
 if(next&&tab!=='history'){body.insertAdjacentHTML('beforeend',`<div class="review-next"><button id="draft-next" type="button">${next==='delta'?'Weiter: Änderungen ansehen →':next==='notes'?'Weiter: Notizen ergänzen →':(reviewTools.reviewProgress(d.requirements||[],d.notes||[]).total?'Weitergeben →':'Zur Klärung weitergeben →')}</button></div>`);bind('draft-next','click',()=>renderDraft(next));}
 document.querySelectorAll('[data-tab]').forEach(button=>{if(button.dataset.tab===tab)button.setAttribute('aria-current','page');button.addEventListener('click',()=>renderDraft(button.dataset.tab));});
 if(tab==='packet')bind('add-document-question','click',()=>{renderDraft('notes');$('note-subject').value='source';$('note-rationale').focus();});
}
function render(){return applyRoute();}
if(typeof document!=='undefined'){
 bind('skip-to-workspace','click',event=>{event.preventDefault();$('main-content').focus();});
 bind('login-form','submit',async ev=>{ev.preventDefault();await api('/api/login',{key:$('key').value});$('key').value='';await refresh();});
 bind('refresh','click',async()=>{await refresh();tell('Aktueller Checkout geladen.');});
 bind('logout','click',async()=>{await api('/api/logout',{});state=null;activeDraft=null;activeSource=null;reviewViews.clear();routeMemory.clear();documentListView.query='';documentListView.status='';documentListView.focus='devsecops';intakeDraft=emptyIntake();intakeStep=1;$('detail-content').textContent='';$('comparison-content').textContent='';$('content').textContent='';$('workspace').hidden=true;$('login').hidden=false;if($('detail').open)$('detail').close();});
 bind('close-detail','click',()=>{if($('detail').open)$('detail').close();});
 document.querySelectorAll('[data-page]').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.page).catch(error=>tell(error.message,true))));
 document.addEventListener('click',async ev=>{const start=ev.target.closest('[data-start-source]'),source=ev.target.closest('[data-source]'),draft=ev.target.closest('[data-draft]'),resume=ev.target.closest('[data-continue-draft]'),note=ev.target.closest('[data-note-subject]'),phase=ev.target.closest('[data-process-target]');try{if(start)await beginSourceReview(start.dataset.startSource);if(source)await showSource(source.dataset.source);if(draft)await showDraft(draft.dataset.draft);if(resume)await continueDraft(resume.dataset.continueDraft);if(note){renderDraft('notes');$('note-subject').value=note.dataset.noteSubject;$('note-rationale').focus();}if(phase)await navigate(phase.dataset.processTarget);}catch(error){tell(error.message,true);}});
 window.addEventListener('hashchange',()=>applyRoute().catch(error=>tell(error.message,true)));
 window.addEventListener('beforeunload',event=>{if(state&&hasUnsavedWork()){event.preventDefault();event.returnValue='';}});
 window.addEventListener('resize',syncReadingLayout);
 refresh().catch(()=>{});
}
if(typeof module!=='undefined')module.exports={escapeHTML,emptyIntake,suggestDocumentId,suggestFileMetadata,validateIntake,locatorLabel,humanReason};
