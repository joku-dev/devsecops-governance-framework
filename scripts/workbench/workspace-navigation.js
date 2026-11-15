'use strict';
const WorkspaceNavigation = (() => {
  const review = typeof module !== 'undefined' ? require('./requirement-review.js') : RequirementReview;
  const pages = {overview:'start', sources:'documents', intake:'intake', review:'comparison', baseline:'readiness', consumers:'consumers'};
  const draftTabs = ['requirements', 'delta', 'notes', 'history', 'packet'];
  function routeHash(route) {
    let path;
    if (pages[route.page]) path = pages[route.page];
    else if (route.page === 'source') path = `documents/${encodeURIComponent(route.id)}/${route.tab || 'current'}`;
    else if (route.page === 'draft') path = `reviews/${encodeURIComponent(route.id)}/${route.tab || 'requirements'}`;
    else return '#/invalid';
    return '#/' + path + (route.item ? '?item=' + encodeURIComponent(route.item) : '');
  }
  function parseRoute(hash) {
    if (!hash || hash === '#' || hash === '#/') return {page:'overview'};
    try {
      const [path, query = ''] = hash.replace(/^#\/?/, '').split('?');
      const parts = path.split('/').map(decodeURIComponent);
      const simple = Object.keys(pages).find(key => pages[key] === parts[0]);
      if (simple && parts.length === 1) return {page:simple};
      const params = new URLSearchParams(query), item = params.get('item');
      if (item && (item.length > 300 || /[\x00-\x1f]/.test(item))) return {page:'invalid'};
      const suffix = item ? {item} : {};
      if (parts[0] === 'documents' && parts.length <= 3 && /^[A-Z0-9]+(?:-[A-Z0-9]+)*-[0-9]{3}$/.test(parts[1]) && (!parts[2] || ['current','history'].includes(parts[2])))
        return {page:'source', id:parts[1], tab:parts[2] || 'current', ...suffix};
      if (parts[0] === 'reviews' && parts.length <= 3 && /^[a-f0-9]{32}$/.test(parts[1]) && (!parts[2] || draftTabs.includes(parts[2])))
        return {page:'draft', id:parts[1], tab:parts[2] || 'requirements', ...suffix};
    } catch (_) { /* A malformed URL is an empty state, never an API path. */ }
    return {page:'invalid'};
  }
  function safePR(url) {
    return typeof url === 'string' && /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/pull\/[0-9]+$/.test(url);
  }
  function nextTask(draft) {
    if (draft.pr) return {label:'Veröffentlichung ansehen', tab:'packet'};
    if (draft.stale) return {label:'Änderung nachvollziehen', tab:'requirements'};
    if (!draft.source) return {label:'Dokumentauswahl prüfen', tab:'requirements'};
    const progress = review.reviewProgress(draft.requirements, draft.notes);
    if (!progress.total) return {label:'Kennzeichnungen im Original prüfen', tab:'requirements'};
    if (progress.unnoted) return {label:'Nächste offene Anforderung prüfen', tab:'requirements', filter:'unnoted'};
    if (progress.clarification) return {label:'Klärungen bearbeiten', tab:'requirements', filter:'clarification'};
    return {label:'Weitergabe vorbereiten', tab:'packet'};
  }
  function sourceDraft(sourceId, drafts) {
    const matches = drafts.filter(d => d.kind === 'source_review' && d.source?.id === sourceId)
      .sort((a,b) => String(b.created_at).localeCompare(String(a.created_at)) || b.draft_id.localeCompare(a.draft_id));
    return matches.find(d => !d.stale && !d.pr) || matches.find(d => !d.pr) || matches[0];
  }
  function inFocus(document, focus) {
    if (focus === 'all') return true;
    const domains = document?.governance_domains || [];
    return ['DEVSECOPS-POL-REQ-001','DEVSECOPS-DIR-REQ-001','DSCB-STD-REQ-001','DEVSECOPS-POL-CAND-002'].includes(document?.id)
      || (!domains.includes('architecture') && !domains.includes('platform'));
  }
  const staleMessages = {
    repository_changed:'Der Repository-Stand hat sich geändert. Die bisherige Prüfung bleibt an ihren gespeicherten Stand gebunden.',
    register_changed:'Das Quellenregister hat sich geändert.',
    source_changed:'Eine registrierte Quelldatei wurde geändert oder aus dem Register entfernt.',
    source_missing:'Eine registrierte Quelldatei fehlt. Stelle die Datei beziehungsweise die Registrierung wieder her.',
    uploaded_source_missing:'Die gespeicherte Originaldatei dieses Uploads fehlt. Wähle das Original erneut aus und bereite einen neuen Entwurf vor.',
    uploaded_source_changed:'Die gespeicherte Originaldatei dieses Uploads wurde verändert. Bereite einen neuen Entwurf mit dem aktuellen Original vor.',
    source_metadata_changed:'Die Registrierung dieses Dokuments wurde geändert oder entfernt.'
  };
  return {routeHash, parseRoute, safePR, nextTask, sourceDraft, inFocus, staleMessages};
})();
if (typeof module !== 'undefined') module.exports = WorkspaceNavigation;
