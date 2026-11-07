'use strict';
const RequirementReview = (() => {
  function requirementLabel(row) {
    return (row.recognized_requirement_ids || []).join(', ') || row.source_requirement_id || row.extraction_row_id || row.id;
  }
  function partitionRequirements(rows = []) {
    const current = [], historical = [];
    for (const row of rows) {
      const ids = row.recognized_requirement_ids || [row.source_requirement_id || ''];
      const explicit = ['author_identified', 'explicit_identifier'].includes(row.identification_class)
        && ids.some(id => /^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-REQ-[0-9]{3,}$/.test(id) && !/-SRC-[0-9]+-REQ-/.test(id));
      (explicit ? current : historical).push(row);
    }
    return {current, historical};
  }
  function latestNotes(notes = []) {
    const latest = new Map();
    for (const note of notes) latest.set(note.subject, note);
    return latest;
  }
  function reviewProgress(rows = [], notes = []) {
    const current = partitionRequirements(rows).current, latest = latestNotes(notes);
    return {total: current.length, noted: current.filter(r => latest.has(r.id)).length,
      unnoted: current.filter(r => !latest.has(r.id)).length,
      clarification: current.filter(r => latest.get(r.id)?.outcome === 'needs_clarification').length,
      historical: rows.length - current.length};
  }
  function filteredRequirements(rows, notes, query = '', filter = 'all') {
    const latest = latestNotes(notes), q = query.trim().toLocaleLowerCase('de');
    return partitionRequirements(rows).current.filter(row =>
      (!q || `${requirementLabel(row)} ${row.statement}`.toLocaleLowerCase('de').includes(q))
      && (filter === 'unnoted' ? !latest.has(row.id)
        : filter === 'clarification' ? latest.get(row.id)?.outcome === 'needs_clarification' : true));
  }
  function sourceExcerpt(lines = [], requirement) {
    const index = lines.findIndex(line => line.locator === requirement.source_locator);
    return index < 0 ? [] : lines.slice(Math.max(0, index - 1), index + 3);
  }
  return {requirementLabel, partitionRequirements, latestNotes, reviewProgress, filteredRequirements, sourceExcerpt};
})();
if (typeof module !== 'undefined') module.exports = RequirementReview;
