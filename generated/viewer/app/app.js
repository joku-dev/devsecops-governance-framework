'use strict';
(() => {
  const content = document.getElementById('content');
  const central = 'https://github.com/joku-dev/devsecops-governance-framework/blob/main/';
  // Keep untrusted UI values separate from the validated, read-only report model.
  // Besides making the trust boundary explicit, this prevents filter text from
  // being confused with repository data by data-flow analysis.
  const uiState = { page: 0, query: '', severity: 'all', image: 'all', repo: 'all' };
  let dataModel = null;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const count = value => Number.isFinite(value) ? value.toLocaleString('de-DE') : '—';
  const short = value => esc((value || '').slice(0, 12));
  const date = value => value ? esc(new Date(value).toLocaleString('de-DE', {timeZone:'UTC', dateStyle:'medium', timeStyle:'short'})) + ' UTC' : 'Kein Stand erfasst';
  const age = value => {
    const days = Math.max(0, Math.floor((Date.now() - Date.parse(value)) / 86400000));
    return Number.isFinite(days) ? (days === 0 ? 'heute' : `vor ${days} Tagen`) : 'Alter unbekannt';
  };
  const repoURL = id => 'https://github.com/' + id.split('/').map(encodeURIComponent).join('/');
  const runURL = (id, run) => repoURL(id) + '/actions/runs/' + encodeURIComponent(run);
  const sourceURL = path => central + String(path).split('/').map(encodeURIComponent).join('/');
  const route = (repo, tab = 'summary') => '#repository/' + encodeURIComponent(repo.id) + '/' + tab;
  const badge = value => `<span class="badge ${['pass','fail','findings','critical','high'].includes(String(value).toLowerCase()) ? String(value).toLowerCase() : ''}">${esc(value ? String(value).toUpperCase() : 'Nicht erfasst')}</span>`;
  const metric = (label, value, note, tone = '') => `<article class="metric ${tone}"><div class="label">${esc(label)}</div><div class="value">${count(value)}</div><small>${esc(note)}</small></article>`;
  const metricText = (label, value, note, tone = '') => `<article class="metric ${tone}"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div><small>${esc(note)}</small></article>`;
  const heading = (eyebrow, title, subtitle, action = '') => `<div class="heading"><div><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1><p class="subtitle">${esc(subtitle)}</p></div>${action}</div>`;
  const snapshotPath = (repo, s) => `status/measured-security-results/${repo.id.replace('/', '__')}/run-${s.run.id}-attempt-${s.run.attempt}.json`;
  const table = (labels, rows) => `<div class="table-scroll"><table><thead><tr>${labels.map(l => `<th scope="col">${esc(l)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
  function previous(repo) { return (repo.security_history || []).find(s => s.run.id !== repo.security?.run.id); }
  function securityCards(repo) {
    const s = repo.security, before = previous(repo);
    if (!s) return '<div class="notice">Keine gemessenen Container-Scans erfasst. Daraus lässt sich keine Schwachstellenfreiheit ableiten.</div>';
    const unique = new Set(repo.findings.map(f => f.id)).size;
    return `<div class="metrics">${metric('Kritische Meldungen', s.counts.CRITICAL, before ? `Vorher ${before.counts.CRITICAL} · Image-/Paketmeldungen` : 'Kein vorheriger Scan erfasst', 'critical')}${metric('Hohe Meldungen', s.counts.HIGH, before ? `Vorher ${before.counts.HIGH} · Image-/Paketmeldungen` : 'Kein vorheriger Scan erfasst', 'high')}${metric('Unterschiedliche CVE-IDs', unique, 'HIGH / CRITICAL über alle Images')}${metric('Erfolgreiche Tests', s.tests_passed, 'Im selben Lauf gemeldet', 'good')}</div>`;
  }
  function repositoryTable(repos) {
    return table(['Repository', 'DevSecOps', 'Architektur', 'Container-Sicherheit', 'Erfasste Stände'], repos.map(repo => {
      const s = repo.security;
      return `<tr><td><a class="repo-name" href="${route(repo)}">${esc(repo.id.split('/')[1])} →</a><small>${esc(repo.id.split('/')[0])}</small></td><td>${badge(repo.devsecops?.status)}</td><td>${badge(repo.architecture?.status)}</td><td>${s ? `${badge(s.counts.CRITICAL ? 'critical' : s.counts.HIGH ? 'high' : 'Keine hohen / kritischen Meldungen')}<small>${count(s.counts.CRITICAL)} kritisch · ${count(s.counts.HIGH)} hoch</small>` : '<span class="muted">Nicht erfasst</span>'}</td><td><small>Governance: ${date(repo.devsecops?.generated_at || repo.architecture?.generated_at)}</small><small>Scan: ${date(s?.run.updated_at)}</small></td></tr>`;
    }));
  }
  function actions(repos, includeRepositorySecurity = false) {
    const items = [];
    const repositorySecurity = dataModel.repository_security;
    if (includeRepositorySecurity && repositorySecurity?.summary?.fail) items.push({title:'Governance-Repository: Security-Anforderungen bearbeiten', text:`${repositorySecurity.summary.fail} von ${repositorySecurity.summary.criteria} Kriterien offen · ${repositorySecurity.summary.critical_failures} kritisch · ${repositorySecurity.summary.high_failures} hoch.`, url:'#repository-security', label:'Repository Security öffnen'});
    for (const repo of repos) {
      if (repo.l1_assessment) items.push({title:`${repo.id.split('/')[1]}: L1-Nachweislücken bearbeiten`, text:`${repo.l1_assessment.summary.gap} Kontrollen mit fehlenden Nachweisen · ${repo.l1_assessment.summary.partial} teilweise belegt.`, url:route(repo,'l1'), label:'Kontrollen und Nachweise öffnen'});
      if (repo.security && (repo.security.counts.CRITICAL || repo.security.counts.HIGH)) items.push({title:`${repo.id.split('/')[1]}: Sicherheitsbefunde bewerten`, text:`${repo.security.counts.CRITICAL} kritische und ${repo.security.counts.HIGH} hohe Image-/Paketmeldungen. Technische Bewertung ist keine Risikofreigabe.`, url:route(repo,'findings'), label:'Befunde untersuchen'});
      if (['devsecops','architecture'].some(d => repo[d]?.trust?.replay === 'fail')) items.push({title:`${repo.id.split('/')[1]}: Replay-Befund prüfen`, text:'Das Governance-Ergebnis und die Prüfung der Nachweisherkunft sind getrennte Signale.', url:'#evidence/replay', label:'Replay-Prüfung öffnen'});
      if (['devsecops','architecture'].some(d => ['fail','findings'].includes(String(repo[d]?.status).toLowerCase()))) items.push({title:`${repo.id.split('/')[1]}: Governance-Befunde bearbeiten`, text:'Mindestens ein erfasster Governance-Bereich enthält Befunde.', url:route(repo), label:'Ergebnisse ansehen'});
    }
    return items.length ? items.map((item,i) => `<div class="action"><span class="action-number">${String(i+1).padStart(2,'0')}</span><div><h3>${esc(item.title)}</h3><p>${esc(item.text)}</p><a href="${item.url}">${item.label} →</a></div></div>`).join('') : '<p class="muted">Aus den erfassten Ergebnissen ist kein Handlungsbedarf abgeleitet. Fehlende Nachweise separat prüfen.</p>';
  }
  function overview() {
    const repos = dataModel.repositories, measured = repos.filter(r => r.security), primary = repos.find(r => r.id === 'joku-dev/ha-CPsWMS') || repos[0];
    const critical = measured.reduce((n,r) => n+r.security.counts.CRITICAL,0), high = measured.reduce((n,r) => n+r.security.counts.HIGH,0);
    const affected = repos.filter(r => ['devsecops','architecture'].some(d => ['fail','findings'].includes(String(r[d]?.status).toLowerCase()))).length;
    content.innerHTML = heading('Portfolio · gespeicherter Stand', 'Governance im Überblick', 'Ergebnisse einordnen, offene Befunde erkennen und den passenden Nachweis finden.', primary ? `<a class="button primary" href="${route(primary)}">${esc(primary.id.split('/')[1])} öffnen →</a>` : '') +
      `<div class="metrics">${metric('Repositories', repos.length, `${measured.length} mit gemessenen Container-Scans`)}${metric('Kritische Meldungen', measured.length ? critical : null, 'Nur erfasste Container-Scans', 'critical')}${metric('Hohe Meldungen', measured.length ? high : null, 'Image-/Paketmeldungen, nicht eindeutige CVEs','high')}${metric('Governance mit Befunden', affected, 'Repositories mit FAIL oder FINDINGS')}</div>
      <div class="grid-two"><section class="panel"><div class="panel-head"><h2>Was Aufmerksamkeit braucht</h2><span class="badge">Aus Ergebnissen abgeleitet</span></div>${actions(repos,true)}</section><section class="panel"><h2>Den Stand richtig lesen</h2><ul class="scope-list"><li><div>Governance<small>Bewertung gegen die jeweilige Baseline</small></div><span class="badge">Eigener Status</span></li><li><div>Repository Security<small>Schutz des Governance-Repositories</small></div><span class="badge">Report-only</span></li><li><div>Container-Sicherheit<small>Tatsächliche Scanner-Meldungen</small></div><span class="badge">Report-only</span></li><li><div>Nachweisqualität<small>Integrität und Replay separat prüfen</small></div><span class="badge">Eigene Prüfung</span></li></ul><div class="notice">Ein Governance-PASS bedeutet nicht schwachstellenfrei oder für Produktion freigegeben.</div><p class="muted">Es werden gespeicherte Ergebnisse gezeigt. Fehlende Scans zählen nicht als null Befunde.</p></section></div>
      <section class="panel"><div class="panel-head"><h2>Repositories im Vergleich</h2><a href="#repositories">Alle ansehen →</a></div>${repositoryTable(repos)}</section>`;
  }
  function repositories() {
    content.innerHTML = heading('Portfolio', 'Repositories', 'Offizielle Mainline-Ergebnisse und gemessene Sicherheit je Repository.') + `<section class="panel"><div class="filters"><label class="search">Repository suchen<input id="repo-search" type="search" placeholder="Name oder Organisation"></label></div><div id="repo-results">${repositoryTable(dataModel.repositories)}</div></section>`;
    document.getElementById('repo-search').addEventListener('input', e => {
      const matches = dataModel.repositories.filter(r => r.id.toLowerCase().includes(e.target.value.toLowerCase()));
      document.getElementById('repo-results').innerHTML = matches.length ? repositoryTable(matches) : '<p class="empty">Keine passenden Repositories.</p>';
    });
  }
  function governanceCard(repo, key, title) {
    const r = repo[key];
    if (!r) return `<section class="panel"><h2>${title}</h2><p class="muted">Kein offizielles Mainline-Ergebnis erfasst.</p></section>`;
    const summary = key === 'devsecops' ? r.control_evaluation_summary : r.architecture_summary;
    const text = key === 'devsecops' ? `${count(summary?.pass)} Kontrollen bestanden · ${count(summary?.fail)} fehlgeschlagen` : `${count(summary?.passed)} / ${count(summary?.gate_count)} Gates bestanden · ${count(summary?.finding_count)} Befunde`;
    return `<section class="panel"><div class="panel-head"><h2>${title}</h2>${badge(r.status)}</div><p>${text}</p><p class="muted">${date(r.generated_at)} · ${age(r.generated_at)}</p><dl><dt>Baseline</dt><dd>${esc(r.governance_baseline_ref || r.architecture_baseline_ref)}</dd><dt>Commit</dt><dd><a href="${repoURL(repo.id)}/commit/${encodeURIComponent(r.commit_id)}"><code>${short(r.commit_id)}</code></a></dd><dt>Evidence Trust</dt><dd><a href="${route(repo,'trust')}">${esc(r.trust?.effective_level || 'nicht erfasst')} →</a></dd><dt>Replay</dt><dd>${badge(r.trust?.replay)}</dd></dl><a href="${runURL(repo.id,r.pipeline_run_id)}">Run ${esc(r.pipeline_run_id)} ↗</a> · <a href="${sourceURL(r.source_file)}">Snapshot ↗</a></section>`;
  }
  function summary(repo) {
    const s = repo.security;
    return `<div class="grid-two">${governanceCard(repo,'devsecops','DevSecOps')}${governanceCard(repo,'architecture','Architektur')}</div>
      <section class="panel"><div class="panel-head"><h2>Gemessene Container-Sicherheit</h2><a href="${route(repo,'security')}">Images &amp; Vergleich →</a></div>${s ? `<p class="muted">${date(s.run.updated_at)} · Commit <code>${short(s.run.commit)}</code> · Report-only</p>` : ''}${securityCards(repo)}${s && [repo.devsecops,repo.architecture].some(r=>r && r.commit_id!==s.run.commit) ? '<div class="notice warn">Governance und Scan beziehen sich auf unterschiedliche Commits. Sie bilden keine gemeinsame Freigabe dieses Softwarestands.</div>' : ''}</section>
      ${l1Summary(repo)}${stagingSummary(repo)}<section class="panel"><h2>Nächste Prüfungen</h2>${actions([repo])}</section>`;
  }
  const l1Names = {measured:'Technisch belegt', partial:'Teilweise belegt', findings:'Befunde offen', gap:'Nachweis fehlt'};
  const l1Path = (repo, run, consolidated = false) => `status/${consolidated?'consolidated-l1-results':'measured-l1-results'}/${repo.id.replace('/', '__')}/run-${run.id}-attempt-${run.attempt}.json`;
  const assurancePath = (repo, run) => `status/control-evidence-assurance/${repo.id.replace('/', '__')}/run-${run.id}-attempt-${run.attempt}.json`;
  const l1Badge = status => `<span class="badge l1-${Object.hasOwn(l1Names,status)?status:'gap'}">${esc(l1Names[status] || 'Unbekannt')}</span>`;
  const assuranceBadge = level => `<span class="badge assurance-${esc(level || 'unverified')}">${esc(level || 'unverified')}</span>`;
  const assuranceFor = (repo, assessment) => {
    const item=repo.control_assurance;
    if(assessment?.result_type==='consolidated-l1-assessment') return null;
    return item && assessment && item.run.id===assessment.run.id && item.run.attempt===assessment.run.attempt && item.run.commit===assessment.run.commit ? item : null;
  };
  function l1Summary(repo) {
    const a=repo.l1_assessment;
    if(!a) return `<section class="panel"><h2>L1-Nachweise</h2><p class="muted">Keine gemessene L1-Bewertung erfasst.</p></section>`;
    const q=assuranceFor(repo,a);
    const consolidated=a.result_type==='consolidated-l1-assessment';
    return `<section class="panel l1-summary"><div class="panel-head"><h2>L1-Nachweise aus echten Prüfungen</h2><a href="${route(repo,'l1')}">Alle 16 Kontrollen →</a></div>${consolidated?'<p><span class="badge">Konsolidiert</span> CI-Messung und exakt zugeordnetes Staging-Deployment.</p>':''}<p>${Object.entries(l1Names).map(([key,label])=>`<strong>${count(a.summary[key])}</strong> ${esc(label.toLowerCase())}`).join(' · ')}</p>${q?`<p><strong>Nachweisqualität:</strong> ${count(q.summary.trust_levels.integrity_verified)} integrity_verified · ${count(q.summary.trust_levels.unverified)} unverified · ${count(q.summary.freshness.pass)} Freshness-Prüfungen bestanden</p>`:'<p class="muted">Für diesen Lauf ist noch keine Assurance pro Kontrolle erfasst.</p>'}<p class="muted">${date(a.run.updated_at)} · Commit <code>${short(a.run.commit)}</code>. Separate Report-only-Bewertung; technisch belegt bedeutet keine vollständige Kontrollfreigabe.</p></section>`;
  }
  function stagingSummary(repo) {
    const d=repo.staging_deployment;
    if(!d) return '<section class="panel"><h2>Staging</h2><p class="muted">Kein realer Staging-Deployment-Nachweis erfasst.</p></section>';
    return `<section class="panel"><div class="panel-head"><h2>Reales Staging-Deployment</h2><a href="${route(repo,'staging')}">Lauf und Nachweise →</a></div><p>${badge(d.deployment.status)} <strong>${count(d.tests.pass)} / ${count(d.tests.pass+d.tests.fail)} Prüfungen bestanden</strong></p><p class="muted">${date(d.deployment.finished_at)} · ${esc(d.environment.hostname)} · deployter Commit <code>${short(d.deployed_subject.commit)}</code> · Report-only</p><p>Evidence Trust: <code>${esc(d.trust.effective_level)}</code> · Freshness ${badge(d.trust.freshness)} · Replay ${badge(d.trust.replay)}</p></section>`;
  }
  function l1View(repo) {
    const a=repo.l1_assessment;
    if(!a) return '<section class="panel"><h2>L1-Nachweise</h2><p>Keine gemessene L1-Bewertung erfasst. Fehlende Daten gelten nicht als bestandene Kontrolle.</p></section>';
    const matching=repo.devsecops?.commit_id===a.run.commit, q=assuranceFor(repo,a);
    const consolidated=a.result_type==='consolidated-l1-assessment';
    return `<div class="notice">Zentrale Bewertung ausgewählter Rohdaten: Tests, SAST, SBOMs, Scans und Plattformabfragen. Report-only; keine Produktionsfreigabe, Risikoakzeptanz oder Änderung der offiziellen Baseline.</div>
      ${consolidated?`<section class="panel"><div class="panel-head"><h2>Konsolidierter Staging-Nachweis</h2><a href="${route(repo,'staging')}">Deploymentdetails →</a></div><p>Die Kontrollen 013, 014 und 016 enthalten das reale Staging-Ergebnis, weil Repository, Commit, Producer-Run und Versuch exakt mit der CI-Messung übereinstimmen.</p><p>Trust: <code>${esc(a.source_assessments.staging.effective_level)}</code> · Freshness ${badge(a.source_assessments.staging.freshness)} · Replay ${badge(a.source_assessments.staging.replay)}</p></section>`:''}
      <section class="panel"><div class="panel-head"><h2>L1-Nachweise</h2><a href="${sourceURL(l1Path(repo,a.run,consolidated))}">Bewertung als JSON ↗</a></div><p>${date(a.run.updated_at)} · <a href="${runURL(repo.id,a.run.id)}">Run ${esc(a.run.id)} ↗</a> · Versuch ${a.run.attempt} · Commit <code>${short(a.run.commit)}</code></p><p>${matching ? `Offizielle Baseline: ${badge(repo.devsecops.status)} · ${count(repo.devsecops.control_evaluation_summary?.pass)} Kontrollen bestanden für denselben Commit.` : 'Die offizielle Baseline und diese Bewertung haben keinen bestätigten gemeinsamen Commit.'} Die offizielle Bewertung verwendet eigene Eingaben und deckt Nachweislücken dieser Messung nicht automatisch ab.</p>
      <div class="metrics l1-metrics">${Object.entries(l1Names).map(([key,label])=>metric(label,a.summary[key],key==='measured'?'Für den beschriebenen technischen Umfang':'Weitere Prüfung erforderlich',key==='gap'?'critical':'')).join('')}</div>
      ${q?`<div class="assurance-overview"><div><strong>Trust je Kontrolle</strong><br>${count(q.summary.trust_levels.integrity_verified)} integrity_verified · ${count(q.summary.trust_levels.unverified)} unverified</div><div><strong>Freshness</strong><br>${count(q.summary.freshness.pass)} bestanden · ${count(q.summary.freshness.fail)} fehlgeschlagen · ${count(q.summary.freshness.not_evaluated)} nicht bewertet</div><a href="${sourceURL(assurancePath(repo,q.run))}">Assurance als JSON ↗</a></div>`:'<div class="notice warn">Für diesen Lauf ist noch keine Assurance pro Kontrolle erfasst. Fehlende Trust- und Freshness-Werte gelten nicht als bestanden.</div>'}
      <div class="filters"><label class="search">Kontrolle suchen<input id="l1-query" type="search" placeholder="Kontrolle, Werkzeug oder offener Punkt"></label><label>Nachweisstatus<select id="l1-status"><option value="all">Alle Kontrollen</option>${Object.entries(l1Names).map(([key,label])=>`<option value="${key}">${esc(label)}</option>`).join('')}</select></label></div><p id="l1-count" role="status"></p><div id="l1-controls"></div></section>
      <section class="panel"><h2>Herkunft und Grenzen</h2><p>Repository, Commit, Lauf, Versuch und ausgewählte Datei-Hashes wurden geprüft. Die Runtime-Tests nutzen die gescannten Query-API-/Neo4j-Image-IDs in kurzlebiger CI. Vollständige Image-Archive wurden zentral nicht erneut gehasht; keine unabhängige Attestation.</p><p>Trust beschreibt die Qualität und Bindung eines Nachweises. Der fachliche Kontrollstatus, Replay und offene Nachweisanteile bleiben eigene Signale. <a href="#evidence/replay">Replay-Prüfung öffnen →</a></p><details><summary>Technische Nachweisbindung</summary><dl><dt>Bewertungsprofil</dt><dd>${esc(a.profile)}</dd><dt>Nachweisbindung SHA-256</dt><dd><code>${esc(a.evidence_binding)}</code></dd>${q?`<dt>Assurance-Profil</dt><dd>${esc(q.profile)}</dd><dt>Assurance-Bindung SHA-256</dt><dd><code>${esc(q.assurance_binding)}</code></dd>`:''}</dl></details><h3>Erfasste Bewertungen</h3>${(repo.l1_history||[]).map(h=>`<p><a href="${sourceURL(l1Path(repo,h.run))}">Run ${esc(h.run.id)}, Versuch ${h.run.attempt} ↗</a> · ${date(h.run.updated_at)} · Commit <code>${short(h.run.commit)}</code></p>`).join('')}</section>`;
  }
  function stagingView(repo) {
    const d=repo.staging_deployment;
    if(!d) return '<section class="panel"><h2>Staging</h2><p>Kein realer Staging-Deployment-Nachweis erfasst. Fehlende Daten gelten nicht als erfolgreicher Lauf.</p></section>';
    const evidenceURL=`${repoURL(repo.id)}/tree/${encodeURIComponent(d.evidence_repository.commit)}/${d.evidence_repository.path}`;
    return `<div class="notice">Realer Lauf in einer isolierten Staging-VM. Die Freigabe gilt nur für den genannten Commit und diese Umgebung; sie ist keine Produktionsfreigabe oder allgemeine Risikoakzeptanz.</div>
      <div class="metrics">${metricText('Deployment',d.deployment.status.toUpperCase(),`${date(d.deployment.finished_at)} · ${d.environment.hostname}`,'good')}${metricText('Prüfungen',`${d.tests.pass}/${d.tests.pass+d.tests.fail}`,'Start, Funktion, Persistenz und Recovery','good')}${metricText('Trust',d.trust.effective_level,`Freshness ${d.trust.freshness} · Replay ${d.trust.replay}`,'good')}${metric('Beobachtungen',d.observations.length,'Offene technische Hinweise',d.observations.some(o=>['high','critical'].includes(o.severity))?'critical':'')}</div>
      <section class="panel"><div class="panel-head"><h2>Deployment-Identität</h2>${badge(d.deployment.status)}</div><dl><dt>Ziel</dt><dd>${esc(d.environment.hostname)} · ${esc(d.environment.address)}</dd><dt>Projekt</dt><dd><code>${esc(d.deployment.project)}</code></dd><dt>Deployter Commit</dt><dd><a href="${repoURL(repo.id)}/commit/${encodeURIComponent(d.deployed_subject.commit)}"><code>${short(d.deployed_subject.commit)}</code></a></dd><dt>Quelllauf</dt><dd><a href="${runURL(repo.id,d.deployed_subject.source_run_id)}">${esc(d.deployed_subject.source_run_id)} ↗</a></dd><dt>API-Bindung</dt><dd><code>${esc(d.deployment.api_binding)}</code></dd><dt>Freigabe</dt><dd>${esc(d.approval.decision)} · ${date(d.approval.approved_at)}</dd></dl><p><a href="${sourceURL(d.source_file)}">Zentralen Snapshot öffnen ↗</a> · <a href="${evidenceURL}">Rohnachweise im Anwendungs-Repository ↗</a></p></section>
      <section class="panel"><h2>Ausgeführte Prüfungen</h2><p><strong>${count(d.tests.pass)} bestanden · ${count(d.tests.fail)} fehlgeschlagen</strong></p><p>Datenbankausfall: HTTP ${count(d.tests.database_outage_http_status)} · Wiederherstellung: HTTP ${count(d.tests.database_recovery_http_status)}</p>${table(['Komponente','Runtime-Image','Health'],Object.entries(d.components).map(([name,item])=>`<tr><td>${esc(name)}</td><td><code>${short(item.runtime_image_id.replace('sha256:',''))}</code></td><td>${badge(item.health)}</td></tr>`))}</section>
      <section class="panel"><h2>L1-Ergänzungsnachweise</h2>${table(['Kontrolle','Bewertung','Beobachtung / Grenze'],d.controls.map(c=>`<tr><td><code>${esc(c.control_id)}</code></td><td>${l1Badge(c.assessment)}</td><td>${esc(c.observation)}<small>${esc(c.remaining)}</small></td></tr>`))}</section>
      <section class="panel"><h2>Trust, Grenzen und Beobachtungen</h2><p>Evidence Trust <code>${esc(d.trust.effective_level)}</code> · Integrität ${badge(d.trust.content_integrity)} · Freshness ${badge(d.trust.freshness)} · Replay ${badge(d.trust.replay)}</p>${d.observations.map(o=>`<div class="notice ${['high','critical'].includes(o.severity)?'warn':''}"><strong>${esc(o.id)} · ${esc(o.severity)}</strong> ${esc(o.summary)}</div>`).join('')||'<p class="muted">Keine technischen Beobachtungen erfasst.</p>'}<p class="muted">Vorhandene Schwachstellen bleiben getrennte report-only Befunde. Der Nachweis bestätigt den ausgeführten Staging-Lauf, nicht Schwachstellenfreiheit.</p></section>`;
  }
  function bindL1(repo) {
    const a=repo.l1_assessment;
    if(!a)return;
    const q=assuranceFor(repo,a), assuranceByControl=new Map((q?.controls||[]).map(row=>[row.control_id,row]));
    function draw() {
      const query=document.getElementById('l1-query').value.toLowerCase(), status=document.getElementById('l1-status').value;
      const rows=a.controls.filter(c=>{const assurance=assuranceByControl.get(c.control_id);return (status==='all'||c.assessment===status)&&`${c.control_id} ${c.title} ${c.tools.join(' ')} ${c.observation} ${c.remaining} ${assurance?.effective_level||''} ${assurance?.freshness?.result||''}`.toLowerCase().includes(query);});
      document.getElementById('l1-count').textContent=`${rows.length} / ${a.controls.length} Kontrollen`;
      document.getElementById('l1-controls').innerHTML=rows.map(c=>{const assurance=assuranceByControl.get(c.control_id);return `<details class="l1-control"><summary class="l1-control-heading"><span class="l1-control-title"><span class="muted">${esc(c.control_id)}</span> · ${esc(c.title)}</span><span class="badge-pair">${l1Badge(c.assessment)}${assuranceBadge(assurance?.effective_level)}</span></summary><p>${esc(c.observation)}</p><p><strong>Offen / Geltungsbereich:</strong> ${esc(c.remaining)}</p><p class="muted">Prüfmittel: ${esc(c.tools.join(', '))}</p>${assurance?`<div class="assurance-grid"><div><strong>Abdeckung</strong><span>${esc(assurance.coverage)}</span></div><div><strong>Freshness</strong><span>${esc(assurance.freshness.result)} · ${esc(assurance.freshness.policy_id)}</span></div><div><strong>Integrität</strong><span>${esc(assurance.content_integrity)}</span></div><div><strong>Provenienz</strong><span>${esc(assurance.provenance)}</span></div><div><strong>Replay</strong><span>${esc(assurance.replay)}</span></div><div><strong>Custody / Attestation</strong><span>${esc(assurance.custody)} / ${esc(assurance.attestation)}</span></div><div><strong>Entscheidungskontext</strong><span>${esc(assurance.decision_context)}</span></div><div><strong>Subjektbindung</strong><span>${esc(assurance.subject_binding)}</span></div></div><details class="assurance-evidence"><summary>Assurance-Nachweisgruppen (${assurance.evidence.length})</summary>${assurance.evidence.map(item=>`<article><div>${assuranceBadge(item.effective_level)} <strong>${esc(item.evidence_type)}</strong> · ${esc(item.status)}</div><small>Freshness ${esc(item.freshness.result)} · Integrität ${esc(item.content_integrity)} · Provenienz ${esc(item.provenance)} · Replay ${esc(item.replay)}</small>${item.typed_source_file?`<a href="${sourceURL(item.typed_source_file)}">Typisierten Trust-Nachweis öffnen ↗</a>`:''}</article>`).join('')}</details>`:'<div class="notice warn">Keine Assurance für diese Kontrolle erfasst.</div>'}<details><summary>Nachweise und Prüfsummen (${c.evidence_refs.length})</summary><p><a href="${sourceURL('model/controls/dscb-l1.yaml')}">Kontrollanforderung im Modell ↗</a></p><ul class="l1-sources">${c.evidence_refs.map(ref=>{const raw=a.sources[ref];const url=raw.artifact_id==='repository'?`${repoURL(repo.id)}/blob/${encodeURIComponent(a.run.commit)}/quality/traceability.json`:`${runURL(repo.id,a.run.id)}/artifacts/${encodeURIComponent(raw.artifact_id)}`;return `<li><a href="${url}">${esc(ref)} ↗</a><small>${raw.bytes} Bytes · ${esc(raw.verification)}</small><code>${esc(raw.sha256)}</code></li>`;}).join('')}</ul><p class="muted">Originale Actions-Artefakte können ablaufen oder eine Anmeldung erfordern. Die gespeicherte Bewertung behält Identitäten und Hashes.</p></details></details>`;}).join('')||'<p class="empty">Keine passenden Kontrollen.</p>';
    }
    document.getElementById('l1-query').addEventListener('input',draw);
    document.getElementById('l1-status').addEventListener('change',draw);
    draw();
  }
  function security(repo) {
    const s = repo.security;
    if (!s) return securityCards(repo);
    const old = previous(repo);
    return securityCards(repo) + `<div class="notice">Scan vom ${date(s.run.updated_at)} · <a href="${runURL(repo.id,s.run.id)}">Run ${esc(s.run.id)}</a> · ${age(s.run.updated_at)}. HIGH / CRITICAL sind als Einzelbefunde erfasst; andere Schweregrade als Summen.</div>
      <section class="panel"><div class="panel-head"><h2>Images im aktuellen Scan</h2><a href="${route(repo,'findings')}">Befunde öffnen →</a></div>${table(['Image','Kritisch','Hoch','Mittel','Niedrig','Unbekannt','Info'],Object.entries(s.images).map(([name,image])=>`<tr><td><strong>${esc(name)}</strong></td>${['CRITICAL','HIGH','MEDIUM','LOW','UNKNOWN','INFO'].map(k=>`<td>${count(image.counts[k])}</td>`).join('')}</tr>`))}<details><summary>Image-Identitäten und Scan-Hashes</summary>${Object.entries(s.images).map(([name,image])=>`<h3>${esc(name)}</h3><dl><dt>Image</dt><dd><code>${esc(image.image_id)}</code></dd><dt>Scan SHA-256</dt><dd><code>${esc(image.scan_sha256)}</code></dd></dl>`).join('')}</details></section>
      <section class="panel"><h2>Vergleich der erfassten Läufe</h2>${old ? `<p>Run <a href="${runURL(repo.id,old.run.id)}">${esc(old.run.id)}</a> (${date(old.run.updated_at)}) → <a href="${runURL(repo.id,s.run.id)}">${esc(s.run.id)}</a> (${date(s.run.updated_at)}).</p><p>Kritisch: <strong>${old.counts.CRITICAL} → ${s.counts.CRITICAL}</strong> · Hoch: <strong>${old.counts.HIGH} → ${s.counts.HIGH}</strong></p><p class="muted">Unterschiede können durch Paketänderungen und aktualisierte Scanner-Daten entstehen. Dies ist kein automatischer Nachweis behobener CVEs.</p>` : '<p>Kein früherer Lauf für einen Vergleich erfasst.</p>'}<a href="${repoURL(repo.id)}/blob/main/docs/quality/CONTAINER_SECURITY_REMEDIATION.md">Technische Bewertung der Paketkorrekturen ↗</a></section>`;
  }
  function filters(repos, fixed) {
    const allImages = [...new Set(repos.flatMap(r=>Object.keys(r.security?.images || {})))].sort();
    return `<div class="filters"><label class="search">Suche<input id="finding-query" type="search" placeholder="CVE, Paket oder Image" value="${esc(uiState.query)}"></label><label>Schweregrad<select id="finding-severity"><option value="all">Kritisch &amp; hoch</option><option value="CRITICAL">Kritisch</option><option value="HIGH">Hoch</option></select></label><label>Image<select id="finding-image"><option value="all">Alle Images</option>${allImages.map(i=>`<option value="${esc(i)}">${esc(i)}</option>`).join('')}</select></label>${fixed?'':`<label>Repository<select id="finding-repo"><option value="all">Alle Repositories</option>${repos.map(r=>`<option value="${esc(r.id)}">${esc(r.id.split('/')[1])}</option>`).join('')}</select></label>`}</div>`;
  }
  function findings(repos, fixed = false) {
    return `<div class="notice">Container-Scans · HIGH / CRITICAL · Status: technische Prüfung offen. Mehrere Image-/Paketmeldungen können dieselbe CVE betreffen. Eine technische Einordnung ist keine Risikofreigabe.</div><section class="panel"><h2>Hohe und kritische Befunde</h2>${repos.filter(r=>r.security).map(r=>`<p class="muted">${esc(r.id)} · ${date(r.security.run.updated_at)} · <a href="${runURL(r.id,r.security.run.id)}">Run ${esc(r.security.run.id)}</a> · <a href="${route(r,'evidence')}">Nachweise →</a></p>`).join('')}${filters(repos,fixed)}<div id="finding-results"></div></section>`;
  }
  function bindFindings(repos) {
    const items = repos.flatMap(r=>r.findings.map(f=>({...f,repo:r.id}))).sort((a,b)=>Number(b.severity==='CRITICAL')-Number(a.severity==='CRITICAL'));
    const controls = {'finding-query':'query','finding-severity':'severity','finding-image':'image','finding-repo':'repo'};
    function draw() {
      const matches = items.filter(f=>(uiState.severity==='all'||uiState.severity===f.severity)&&(uiState.image==='all'||f.images.includes(uiState.image))&&(uiState.repo==='all'||uiState.repo===f.repo)&&`${f.id} ${f.package} ${f.images.join(' ')} ${f.repo}`.toLowerCase().includes(uiState.query.toLowerCase()));
      const pages = Math.max(1,Math.ceil(matches.length/20)); uiState.page=Math.min(uiState.page,pages-1);
      const rows=matches.slice(uiState.page*20,uiState.page*20+20).map(f=>`<tr data-finding><td>${badge(f.severity)}</td><td>${/^CVE-\d{4}-\d+$/.test(f.id)?`<a class="row-link" href="https://security-tracker.debian.org/tracker/${encodeURIComponent(f.id)}">${esc(f.id)} ↗</a>`:esc(f.id)}<small>${esc(f.package)} · ${esc(f.installed_version)}</small></td><td>${esc(f.images.join(', '))}<small>${esc(f.repo)} · ${count(f.occurrences)} Meldungen</small></td><td>${esc(f.fixed_version || 'Im Scan nicht angegeben')}</td><td>${esc(f.assessment)}<small>Prüfung offen</small></td></tr>`);
      document.getElementById('finding-results').innerHTML=`<p class="count" role="status" aria-live="polite">${matches.length} / ${items.length} Paket-/Versionsgruppen · ${new Set(matches.map(f=>f.id)).size} unterschiedliche CVE-IDs</p>${rows.length?table(['Schweregrad','CVE / Paket','Betroffene Images','Korrigiert laut Scan','Offene Prüfung'],rows):'<p class="empty">Keine passenden Befunde. Filter anpassen; fehlende Scans sind kein Nachweis von Schwachstellenfreiheit.</p>'}<div class="pager"><button id="prev" ${uiState.page===0?'disabled':''}>← Zurück</button><span>Seite ${uiState.page+1} von ${pages}</span><button id="next" ${uiState.page===pages-1?'disabled':''}>Weiter →</button></div>`;
      document.getElementById('prev').onclick=()=>{uiState.page--;draw();};document.getElementById('next').onclick=()=>{uiState.page++;draw();};
    }
    Object.entries(controls).forEach(([id,key])=>{const el=document.getElementById(id);if(el){el.value=uiState[key];el.addEventListener(key==='query'?'input':'change',()=>{uiState[key]=el.value;uiState.page=0;draw();});}});
    draw();
  }
  function evidence(repos) {
    return `<div class="notice">Herkunft, Commit und Erfassungszeit gehören zu jedem Ergebnis. Scan-Intake prüft Rohdatei-Hashes gegen Producer-Manifeste und die Image-Zuordnung; keine unabhängige Attestation und keine erneute Prüfung kompletter Image-Archive. Originalartefakte können ablaufen.</div>` + repos.map(repo=>`<section class="panel"><div class="panel-head"><h2>${esc(repo.id)}</h2><a href="${route(repo,'trust')}">Evidence Trust öffnen →</a></div>${['devsecops','architecture'].map(key=>{const r=repo[key];return r?`<article class="evidence-item"><div class="panel-head"><h3>${key==='devsecops'?'DevSecOps':'Architektur'} · offizieller Mainline-Stand</h3>${badge(r.status)}</div><p class="muted">${date(r.generated_at)} · Commit <code>${short(r.commit_id)}</code></p><a href="${runURL(repo.id,r.pipeline_run_id)}">Run ${esc(r.pipeline_run_id)} ↗</a> · <a href="${sourceURL(r.source_file)}">Gespeicherten Snapshot öffnen ↗</a></article>`:'';}).join('')}${(repo.security_history||[]).map(s=>`<article class="evidence-item"><div class="panel-head"><h3>Gemessene Container-Sicherheit · ${esc(s.run.branch)}</h3><span class="badge">Report-only</span></div><p class="muted">${date(s.run.updated_at)} · Commit <code>${short(s.run.commit)}</code> · Versuch ${s.run.attempt}</p><p>${s.counts.CRITICAL} kritisch · ${s.counts.HIGH} hoch · ${s.tests_passed} erfolgreiche Tests</p><a href="${runURL(repo.id,s.run.id)}">Run ${esc(s.run.id)} &amp; Scan-/SBOM-Artefakte ↗</a> · <a href="${sourceURL(snapshotPath(repo,s))}">Gespeicherten Snapshot öffnen ↗</a></article>`).join('')}${!repo.security?'<p class="muted">Keine gemessenen Container-Scans erfasst.</p>':''}</section>`).join('') + '<p class="muted">Hier: offizielle Governance-Stände und erfasste Scan-Historie. Weitere Branch-, PR- und manuelle Läufe im <a href="#evidence/history">Bereich Laufhistorie</a>.</p>';
  }
  function trustView(repo) {
    const cards=['devsecops','architecture'].map(key=>{
      const r=repo[key], t=r?.trust, title=key==='devsecops'?'DevSecOps':'Architektur';
      if(!t)return `<section class="panel trust-card"><h2>${title}</h2><p class="muted">Kein Evidence-Trust-Status erfasst. Fehlende Prüfungen gelten nicht als bestanden.</p></section>`;
      const level=t.effective_level || 'nicht erfasst';
      const explanation=level==='integrity_verified'?'Die Integrität der erfassten Nachweise wurde geprüft. Das ist keine vollständige Bestätigung aller Trust-Dimensionen.':level==='unverified'?'Für diese Nachweise liegt keine verifizierte Trust-Stufe vor.':'Die gespeicherte Trust-Stufe gilt für diesen Lauf; Einzelprüfungen und Grenzen im Quellnachweis beachten.';
      return `<section class="panel trust-card" data-trust-domain="${key}"><div class="panel-head"><h2>${title}</h2><span class="badge">Report-only</span></div><p><strong>Evidence Trust</strong> · <code>${esc(level)}</code></p><p>${explanation}</p><dl><dt>Bewertet am</dt><dd>${date(t.verified_at)}</dd><dt>Commit</dt><dd><code>${short(r.commit_id)}</code></dd><dt>Prüfstatus</dt><dd>${esc(t.assessment_status || 'nicht erfasst')}</dd><dt>Replay</dt><dd>${badge(t.replay)}</dd></dl>
        ${table(['Einzelprüfungen','Anzahl'],[['Bestanden',t.check_summary?.pass],['Fehlgeschlagen',t.check_summary?.fail],['Nicht bewertet',t.check_summary?.not_evaluated]].map(([label,n])=>`<tr><td>${label}</td><td>${count(n)}</td></tr>`))}
        ${t.replay==='fail'?'<div class="notice warn">Replay-Befund offen: Die verifizierte Integrität hebt diesen Befund nicht auf. <a href="#evidence/replay">Replay-Abweichung ansehen →</a></div>':''}
        <p><a href="${runURL(repo.id,r.pipeline_run_id)}">Run ${esc(r.pipeline_run_id)} ↗</a> · <a href="${sourceURL(r.source_file)}">Snapshot mit allen Trust-Prüfungen ↗</a></p><p class="muted">Gespeicherte Bewertung zum angegebenen Zeitpunkt; keine Aussage über heutige Freshness oder Produktionsfreigabe.</p></section>`;
    }).join('');
    const q=assuranceFor(repo,repo.l1_assessment);
    const d=repo.staging_deployment;
    return `<div class="notice">Evidence Trust bewertet Herkunft und Integrität der Nachweise. Governance-Ergebnis, Replay und nicht bewertete Prüfungen bleiben eigenständige Signale.</div><div class="grid-two">${cards}</div><section class="panel"><div class="panel-head"><h2>Assurance der 16 L1-Kontrollen</h2>${q?'<span class="badge">Report-only</span>':''}</div>${q?`<p><strong>${count(q.summary.trust_levels.integrity_verified)}</strong> integrity_verified · <strong>${count(q.summary.trust_levels.unverified)}</strong> unverified · <strong>${count(q.summary.freshness.pass)}</strong> Freshness-Prüfungen bestanden</p><p class="muted">Stand ${date(q.verified_at)} · Run ${esc(q.run.id)} · fehlende Nachweisanteile stufen die jeweilige Kontrolle konservativ auf unverified zurück.</p><p><a href="${route(repo,'l1')}">Assurance je Kontrolle öffnen →</a> · <a href="${sourceURL(assurancePath(repo,q.run))}">Assurance-Snapshot ↗</a></p>`:'<p>Für den aktuellen gemessenen L1-Lauf ist noch keine Assurance pro Kontrolle erfasst. Fehlende Prüfungen gelten nicht als bestanden.</p>'}<p><a href="${route(repo,'evidence')}">Quelldaten und Scan-Historie →</a> · <a href="#evidence/trust">Evidence Trust aller Repositories →</a></p></section>${d?`<section class="panel trust-card"><div class="panel-head"><h2>Staging Deployment</h2><span class="badge">Report-only</span></div><p><strong>Evidence Trust</strong> · <code>${esc(d.trust.effective_level)}</code></p><dl><dt>Bewertet am</dt><dd>${date(d.trust.verified_at)}</dd><dt>Integrität</dt><dd>${badge(d.trust.content_integrity)}</dd><dt>Freshness</dt><dd>${badge(d.trust.freshness)}</dd><dt>Replay</dt><dd>${badge(d.trust.replay)}</dd></dl><p><a href="${route(repo,'staging')}">Deployment-Nachweis öffnen →</a></p></section>`:''}`;
  }
  function repositorySecurity() {
    const report=dataModel.repository_security;
    if(!report) {
      content.innerHTML=heading('Sicherheit','Repository Security','Schutzstatus des zentralen Governance-Repositories.')+'<section class="panel"><div class="notice warn">Kein validierter Self-Security-Bericht erfasst. Fehlende Daten gelten nicht als bestandene Anforderungen.</div></section>';
      return;
    }
    const failed=report.criteria.filter(item=>item.status==='fail');
    const criteriaRows=report.criteria.map(item=>`<tr data-security-criterion="${esc(item.id)}"><td><strong>${esc(item.id)}</strong><small>${esc(item.key)}</small></td><td>${esc(item.title)}<small>${esc(item.detail)}</small></td><td>${badge(item.severity)}</td><td>${badge(item.status)}</td><td>${item.evidence_refs.map(ref=>`<code>${esc(ref)}</code>`).join('<br>')}</td></tr>`);
    const openItems=failed.map(item=>`<article class="security-finding"><div class="panel-head"><h3>${esc(item.id)} · ${esc(item.title)}</h3>${badge(item.severity)}</div><p>${esc(item.detail)}</p><small>Nachweise: ${esc(item.evidence_refs.join(', '))}</small></article>`).join('');
    const nextSteps=report.next_steps.map(step=>`<article class="action"><span class="action-number">${esc(step.priority)}</span><div><h3>${esc(step.title)}</h3><p>${esc(step.action)}</p><p><strong>Abnahme:</strong> ${esc(step.acceptance_criteria)}</p><small>Adressiert ${esc(step.addresses.join(', '))}${step.prerequisites.length?` · Voraussetzung ${esc(step.prerequisites.join(', '))}`:''}</small></div></article>`).join('');
    content.innerHTML=heading('Sicherheit · zentraler Stand','Repository Security','Self-Security des Governance-Repositories mit Kriterien, Beobachtungen und offenen Maßnahmen.',`<a class="button" href="${sourceURL(report.human_report)}">Vollständigen Bericht öffnen ↗</a>`)+
      `<div class="metrics repository-security-metrics">${metric('Erfüllt',report.summary.pass,`${report.summary.criteria} Kriterien insgesamt`,'good')}${metric('Offen',report.summary.fail,'Weitere Bearbeitung erforderlich','critical')}${metric('Kritisch offen',report.summary.critical_failures,'Fehlgeschlagene kritische Kriterien','critical')}${metric('Hoch offen',report.summary.high_failures,'Fehlgeschlagene hohe Kriterien','high')}</div>
      <div class="notice warn"><strong>${badge(report.overall_status)}</strong> ${esc(report.risk_statement)}</div>
      <div class="grid-two repository-security-overview"><section class="panel"><div class="panel-head"><h2>Bewertungsrahmen</h2><span class="badge">${esc(report.enforcement)}</span></div><dl><dt>Repository</dt><dd>${esc(report.repository_id)}</dd><dt>Beobachtet</dt><dd>${date(report.observed_at)} · ${age(report.observed_at)}</dd><dt>Profil</dt><dd><code>${esc(report.profile_version)}</code></dd><dt>Wirkung</dt><dd>Report-only; keine automatische Freigabe oder Einstellungsänderung</dd></dl><p><a href="${sourceURL(report.source_file)}">Validierten JSON-Bericht öffnen ↗</a></p></section><section class="panel"><h2>Offene Kriterien</h2>${openItems||'<p class="muted">Keine offenen Kriterien im gespeicherten Bericht.</p>'}</section></div>
      <section class="panel"><div class="panel-head"><h2>Alle Self-Security-Kriterien</h2><span class="badge">${count(report.criteria.length)} Kriterien</span></div>${table(['ID','Anforderung / Beobachtung','Schweregrad','Status','Nachweisquellen'],criteriaRows)}</section>
      <section class="panel"><div class="panel-head"><h2>Dokumentierte nächste Schritte</h2><span class="badge">Aus dem Bericht</span></div>${nextSteps||'<p class="muted">Keine nächsten Schritte erfasst.</p>'}<div class="notice">Die Ansicht zeigt einen gespeicherten Zeitpunkt. Änderungen an GitHub-Einstellungen werden erst nach einer neuen Self-Security-Bewertung sichtbar.</div></section>`;
  }
  function repository(repo, tab) {
    const tabs={summary:'Zusammenfassung',trust:'Evidence Trust',l1:'L1-Nachweise',staging:'Staging',security:'Container-Sicherheit',findings:'Befunde',evidence:'Nachweise'};
    if(!tabs[tab])tab='summary';
    content.innerHTML=heading(repo.id.split('/')[0],repo.id.split('/')[1],'Erfasste Ergebnisse mit ihrem jeweiligen Softwarestand.',`<a class="button" href="${repoURL(repo.id)}">Repository auf GitHub ↗</a>`)+`<nav class="tabs" aria-label="Repository-Ansichten">${Object.entries(tabs).map(([key,label])=>`<a href="${route(repo,key)}" ${tab===key?'aria-current="page"':''}>${label}</a>`).join('')}</nav>`+(tab==='summary'?summary(repo):tab==='trust'?trustView(repo):tab==='l1'?l1View(repo):tab==='staging'?stagingView(repo):tab==='security'?security(repo):tab==='findings'?findings([repo],true):evidence([repo]));
    if(tab==='findings')bindFindings([repo]);
    if(tab==='l1')bindL1(repo);
  }
  const groupNames = {evidence:'Nachweise', governance:'Governance', operations:'Betrieb'};
  const groupDescriptions = {
    evidence:'Herkunft, Qualität und Verlauf der gespeicherten Nachweise prüfen.',
    governance:'Kontrollen, Modelle und ihre Beziehungen zu Quellen und Laufzeitergebnissen untersuchen.',
    operations:'Integrationen, Nachweisaufnahme und Betriebsbefunde im Zusammenhang verfolgen.'
  };
  function workspaceTabs(group, tab) {
    const sections = (dataModel.technical?.sections || []).filter(s => s.group === group);
    const entries = group === 'evidence' ? [{tab:'summary',title:'Ergebnisnachweise'}, ...sections] : group === 'operations' ? [...sections, {tab:'lifecycle',title:'Lifecycle-Nächster Schritt'}] : sections;
    return `<nav class="tabs workspace-tabs" aria-label="${groupNames[group]}-Bereiche">${entries.map(s=>`<a href="#${encodeURIComponent(group)}/${encodeURIComponent(s.tab)}" ${s.tab===tab?'aria-current="page"':''}>${esc(s.title)}</a>`).join('')}</nav><label class="section-picker">Bereich auswählen<select id="section-picker">${entries.map(s=>`<option value="#${encodeURIComponent(group)}/${encodeURIComponent(s.tab)}" ${s.tab===tab?'selected':''}>${esc(s.title)}</option>`).join('')}</select></label>`;
  }
  function lifecycleNextStepView() {
    const model=dataModel.consumer_lifecycle_next_step;
    if(!model) {
      content.insertAdjacentHTML('beforeend','<section class="panel"><div class="notice warn">Der Consumer-Lifecycle-Status ist nicht verfügbar. Fehlende Daten gelten nicht als geschlossen.</div></section>');
      return;
    }
    const s=model.next_step, counts=model.counts;
    const links=(items)=>items.map(item=>`<a href="${esc(item.url)}">${esc(item.label)} ↗</a>`).join(' · ');
    const history=model.history.map(item=>`<tr><td>${date(item.recorded_at)}</td><td>${esc(item.kind)}</td><td>${esc(item.detail)}</td><td>${badge(item.status)}</td><td>${links(item.links)}</td></tr>`);
    content.insertAdjacentHTML('beforeend',`
      <section class="panel"><div class="panel-head"><h2>${esc(s.title)}</h2>${badge(model.finding_state)}</div>
        <div class="notice">${esc(s.detail)}</div>
        <dl><dt>Consumer</dt><dd>${esc(model.scope.repository_id)}</dd><dt>Regel</dt><dd><code>${esc(model.scope.rule_id)}</code></dd><dt>Erzwingung</dt><dd>${esc(model.enforcement)}</dd><dt>Indexstand</dt><dd>${date(model.as_of)}</dd></dl>
        <div class="metrics">${metric('Receipts',counts.receipts,'Akzeptierte Observationen')}${metric('Aktionen',counts.actions,'Persönlich gebundene Aktionen')}${metric('Historische Fehler',counts.failures,'Im Ledger erhalten')}${metric('Quarantäne',counts.quarantined,'Muss vor Aktionen geklärt werden')}</div>
        <p><strong>Nächste Operation:</strong> ${s.operation?`<code>${esc(s.operation)}</code>`:'Keine offen'}</p><p>${links(s.links)}</p>
        <p><a href="${esc(model.source_url)}">Offiziellen Lifecycle-Index öffnen ↗</a></p>
        <p class="muted">Read-only-Hinweis aus dem akzeptierten Ledger. Er erteilt keine Zustimmung, führt keinen Workflow aus und ersetzt nicht die Frische- und Rollenprüfung beim Intake.</p>
      </section>
      <section class="panel"><div class="panel-head"><h2>Beleg- und PR-Verlauf</h2><span class="badge">${count(model.history.length)} Einträge</span></div>${table(['Zeit','Typ','Schritt','Status','Direktlinks'],history)}</section>`);
  }
  function technicalView(group, tab) {
    const section = (dataModel.technical?.sections || []).find(s => s.group === group && s.tab === tab);
    const lifecyclePage=group==='operations'&&tab==='lifecycle';
    if (!(group === 'evidence' && tab === 'summary') && !section && !lifecyclePage) { notFound(); return; }
    content.innerHTML = heading(groupNames[group], lifecyclePage?'Lifecycle-Nächster Schritt':tab==='summary'?'Nachweise':section.title, groupDescriptions[group]) + workspaceTabs(group,tab);
    document.getElementById('section-picker')?.addEventListener('change', e => {location.hash=e.target.value;});
    if(lifecyclePage){lifecycleNextStepView();return;}
    if (group==='evidence' && tab==='summary') {
      content.insertAdjacentHTML('beforeend', evidence(dataModel.repositories));
      return;
    }
    const boundaries = {
      'replay-triage':'Replay prüft die Wiederverwendung von Nachweisen. FAIL kennzeichnet einen ungeklärten Kontextwechsel oder Widerspruch. Governance-Ergebnis und Replay bleiben getrennt; diese Prüfung ist report-only.',
      'runtime-governance':'Diese Ansicht enthält gespeicherte Runtime- und Demo-Artefakte. Für den offiziellen Repository-Stand die Repository-Detailansicht und ihre Quellläufe verwenden.',
      'controls':'Die Kontrollansicht zeigt den gespeicherten Kontrollbericht und die Automatisierungsabdeckung. Die Repository-Ansichten weisen ihre offiziellen Ergebnisse jeweils mit eigener Quelle aus.',
      'runs':'Mainline-, Branch-, Pull-Request- und manuelle Läufe bleiben unterscheidbar. Ein neuerer Diagnoselauf ersetzt nicht automatisch das offizielle Mainline-Ergebnis.'
    };
    if (boundaries[section.id]) content.insertAdjacentHTML('beforeend', `<div class="notice">${esc(boundaries[section.id])}</div>`);
    const host=document.createElement('div');host.className='technical';content.append(host);
    window.GovernanceTechnical.mount(host,section,dataModel.technical.graph);
  }
  function render() {
    let parts;
    try { parts=(location.hash.slice(1)||'overview').split('/').map(decodeURIComponent); } catch { parts=['invalid']; }
    const alias=(dataModel.technical?.sections || []).find(s=>s.id===parts[0]);
    if(alias && parts[0]!=='overview' && !parts[1]) parts=[alias.group,alias.tab];
    const view=parts[0], names={overview:'Übersicht',repositories:'Repositories',repository:'Repositories',findings:'Befunde','repository-security':'Repository Security',evidence:'Nachweise',governance:'Governance',operations:'Betrieb'};
    document.querySelectorAll('[data-nav]').forEach(el=>{if(el.dataset.nav===(view==='repository'?'repositories':view))el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
    document.getElementById('breadcrumb').textContent=names[view]||'Seite nicht gefunden';
    document.title=(names[view]||'Seite nicht gefunden')+' · Governance Workspace';
    Object.assign(uiState,{page:0,query:'',severity:'all',image:'all',repo:'all'});
    if(view==='overview')overview();
    else if(view==='repositories')repositories();
    else if(view==='repository') {const repo=dataModel.repositories.find(r=>r.id===parts[1]);if(repo)repository(repo,parts[2]||'summary');else notFound();}
    else if(view==='findings'){content.innerHTML=heading('Sicherheit','Befunde','Gemessene Container-Befunde durchsuchen und die weitere Prüfung vorbereiten.')+findings(dataModel.repositories);bindFindings(dataModel.repositories);}
    else if(view==='repository-security')repositorySecurity();
    else if(view==='evidence')technicalView(view,parts[1]||'summary');
    else if(view==='governance')technicalView(view,parts[1]||'controls');
    else if(view==='operations')technicalView(view,parts[1]||'intake');
    else notFound();
    window.scrollTo(0,0);content.focus({preventScroll:true});
  }
  function notFound(){content.innerHTML='<div class="empty"><h1>Ansicht nicht gefunden</h1><p>Diese Repository-Ansicht ist nicht vorhanden.</p><a href="#overview">Zur Übersicht</a></div>';}
  async function start(){
    try{
      const response=await fetch('data.json',{cache:'no-store'});if(!response.ok)throw new Error('HTTP '+response.status);
      const data=await response.json();if(data.version!==1||!Array.isArray(data.repositories))throw new Error('Unbekanntes Datenformat');
      dataModel=data;render();window.addEventListener('hashchange',render);
    }catch(error){
      content.innerHTML='<section class="panel error" role="alert"><h1>Ergebnisse nicht verfügbar</h1><p>Die gespeicherten Daten konnten nicht geladen werden. Es wird kein grüner Status angenommen.</p><button id="retry">Erneut laden</button> · <a href="../status-viewer.html">Technischen Viewer öffnen</a></section>';
      document.getElementById('retry').onclick=()=>location.reload();
    }
  }
  start();
})();
