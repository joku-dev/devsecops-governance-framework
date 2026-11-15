'use strict';
const ConsumerView = (() => {
  const escape = value => String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels = {waiting:'Lauf läuft noch',queued:'Zur Sammlung vorgemerkt',working:'Wird gesammelt',verified:'Für Review gesammelt',shadow_matched:'Schattenvergleich belegt',reviewed_candidate:'Geprüfter Kandidat',batched:'Übernahme vorbereitet',accepted:'Offiziell übernommen',accepted_pending_sync:'Zusammengeführt · Abgleich ausstehend',held:'Sammlung angehalten',not_accepted:'PR/MR geschlossen · nicht übernommen'};
  function date(value) { return value ? escape(value) : 'Noch nicht erfolgt'; }
  function evidence(value, clock) {
    if (!value) return '<p>Noch kein akzeptiertes Ergebnis vorhanden.</p>';
    const old = !Number.isFinite(Date.parse(value.produced_at)) || clock - Date.parse(value.produced_at) > 86400000;
    return `<p>Governance-Ergebnis: <strong>${escape(value.governance_status)}</strong> · Evidence Trust: <strong>${escape(value.evidence_trust)}</strong></p><p>Erzeugt: ${date(value.produced_at)}${old?' · <strong>älter als 24 Stunden / Aktualität prüfen</strong>':''}<br>Lauf ${escape(value.run_id)}, Versuch ${escape(value.attempt)}</p>`;
  }
  function render(data, clock=Date.now()) {
    if(data.engine==='portable-v1')return renderPortable(data,clock);
    let html='<section class="panel"><h1>Consumer-Repos</h1><p>Hier siehst du, was offiziell übernommen wurde und welche Ergebnisse noch auf Prüfung warten.</p>';
    if (!data.configured) return html+'<div class="empty">Die automatische Sammlung ist auf diesem Host noch nicht eingerichtet.</div></section>';
    const blocked = data.sync_error || data.poll_error;
    html+=`<h2>${escape(data.repository)} · DevSecOps L1</h2><p>Betrieb: <strong>${data.mode==='publish'?'Übernahme-PRs aktiv':data.mode==='paused'?'Pausiert':'Schattenbetrieb · keine eigenen PRs'}</strong></p>`;
    if(data.mode==='shadow')html+=`<p>${data.shadow_ready?'Schattenvergleich erfüllt; die Routenumschaltung benötigt weiterhin einen geprüften PR.':'Schattenvergleich ausstehend: mindestens 24 Stunden und ein übereinstimmender neuer Mainline-Lauf sind erforderlich.'}</p>`;
    if (blocked) html+=`<p role="status" class="notice">Abgleich blockiert: ${data.sync_error==='application_update_required'?'Anwendungsupdate erforderlich':escape(blocked)}. Der angezeigte akzeptierte Stand bleibt an den unten genannten Commit gebunden.</p>`;
    if (!data.last_poll || clock-Date.parse(data.last_poll)>1800000) html+='<p class="notice">Die Sammlung hat seit mehr als 30 Minuten keinen erfolgreichen Abgleich gemeldet.</p>';
    html+=`<p>Letzte Abfrage: ${date(data.last_poll)}<br>Letzte erfolgreiche Sammlung: ${date(data.last_success)}</p><h2>Offiziell übernommen${blocked?' · Abgleich blockiert':''}</h2>`;
    html+=evidence(data.accepted?.latest,clock)+`<p class="muted">Zentraler Quell-Commit: ${escape(data.accepted?.source_commit)}<br>Übernommen am: ${date(data.accepted?.synced_at)}</p>`;
    if(data.batch){const b=data.batch,safe=safeLink(b.url,b.instance);html+=`<h2>${b.state==='open'?'PR offen':'Übernahme vorbereitet'}</h2><p>${safe?`<a href="${escape(b.url)}" target="_blank" rel="noopener noreferrer">PR #${escape(b.pr)} ansehen</a>`:escape(b.id)} · wird erst nach Review und Merge offiziell.</p>`;}
    html+=`<h2>Sammlung und Review</h2><p>${escape(data.queue_count)} Einträge insgesamt; höchstens 100 letzte Einträge sichtbar. Ein frischer Abruf macht alte Evidence nicht aktuell.</p>`;
    html+=(data.jobs||[]).map(row=>`<details class="card"><summary>Lauf ${escape(row.run_id)} / ${escape(row.attempt)} · ${escape(labels[row.state]||row.state)}</summary>${row.governance_status?evidence(row,clock):''}${row.error?`<p>Hinweis: ${escape(row.error)}</p>`:''}</details>`).join('') || '<p>Noch keine Läufe entdeckt.</p>';
    return html+'</section>';
  }
  function safeLink(url,instance) {
    try {const u=new URL(url),origin=new URL(instance);return u.protocol==='https:'&&origin.protocol==='https:'&&u.origin===origin.origin&&!u.username&&!u.password&&!u.search&&!u.hash;}catch{return false;}
  }
  function renderPortable(data,clock) {
    let html='<section class="panel"><h1>Consumer-Repos</h1><p>Portable Sammlung · DevSecOps Pipeline L1 (5 Controls). Die Ergebnisse sind Kandidaten; die offizielle Baseline umfasst weitere Controls.</p>';
    html+=`<p>Betrieb: <strong>${data.mode==='publish'?'Review-PRs/MRs angefordert':data.mode==='paused'?'Pausiert':'Schattenbetrieb'}</strong> · Stand ${date(data.generated_at)}</p>`;
    html+='<p>Offizielle Ergebnisse bleiben in der bestehenden Governance-Ansicht. Ein zusammengeführter Kandidat ist keine Compliance-Freigabe.</p>';
    if(data.sync_error)html+=`<p role="status" class="notice">Abgleich angehalten: ${data.sync_error==='application_update_required'?'Anwendungsupdate erforderlich':escape(data.sync_error)}</p>`;
    html+=`<p>${escape(data.queue_count)} Einträge · älteste vorgemerkte Arbeit: ${escape(Math.round(data.queue_age_seconds||0))} Sekunden.</p>`;
    if(data.legacy_reconciliation_required)html+='<p class="notice">Zusätzlich sind frühere Collector-Datensätze erhalten. Ihre ursprünglichen Batches und Veröffentlichungen müssen vor einer Übergabe abgeglichen werden.</p>';
    if(data.batch){const b=data.batch;html+=`<p>Review-Batch: ${safeLink(b.url,b.instance)?`<a href="${escape(b.url)}" target="_blank" rel="noopener noreferrer">PR/MR ${escape(b.change_id)}</a>`:escape(b.id)} · ${escape(labels[b.state]||b.state)}</p>`;}
    html+=(data.jobs||[]).map(row=>`<details class="card"><summary>${escape(row.repository)} · ${escape(row.ci_provider)} · Lauf ${escape(row.run_id)} / Versuch ${escape(row.attempt)} · ${escape(labels[row.state]||row.state)}</summary><p>Native Job-ID: ${escape(row.job_id)}</p>${row.governance_status?evidence(row,clock):''}${safeLink(row.run_url,row.ci_instance)?`<p><a href="${escape(row.run_url)}" target="_blank" rel="noopener noreferrer">Producer-Lauf öffnen</a></p>`:''}${row.error?`<p>Hinweis: ${escape(row.error)}</p>`:''}</details>`).join('')||'<p>Noch keine Ausführungen entdeckt.</p>';
    return html+'</section>';
  }
  return {render};
})();
if(typeof module!=='undefined')module.exports=ConsumerView;
