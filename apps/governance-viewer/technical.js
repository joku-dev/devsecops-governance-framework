'use strict';
// Technical views use the same generated contents as the retained static viewer.
// Only this module binds behavior; projected fragments never contain scripts.
window.GovernanceTechnical = (() => {
  const allowedTags = new Set('SECTION DIV ARTICLE ASIDE H2 H3 H4 P A SPAN STRONG EM SMALL CODE PRE UL OL LI DL DT DD TABLE THEAD TBODY TR TH TD LABEL SELECT OPTION INPUT BUTTON DETAILS SUMMARY BR svg defs marker path g'.split(' '));
  const allowedAttrs = new Set('id class href for type value placeholder role tabindex scope colspan rowspan viewbox markerwidth markerheight refx refy orient markerunits d selected disabled hidden open'.split(' '));
  function fragment(html) {
    const template = document.createElement('template');
    template.innerHTML = html;
    for (const node of template.content.querySelectorAll('*')) {
      if (!allowedTags.has(node.tagName)) { node.remove(); continue; }
      for (const attr of [...node.attributes]) {
        const key = attr.name.toLowerCase();
        if (!allowedAttrs.has(key) && !key.startsWith('data-') && !key.startsWith('aria-')) node.removeAttribute(attr.name);
        else if (key === 'href') {
          try {
            const url = new URL(attr.value, location.href);
            if (url.protocol !== 'https:' && !(url.protocol === 'http:' && url.origin === location.origin)) node.removeAttribute('href');
          } catch { node.removeAttribute('href'); }
        }
      }
    }
    return template.content;
  }

  function tableTools(root) {
    // Preserve domain filters and compose them with a local text search and pager.
    root.querySelectorAll('table').forEach((table, index) => {
      if (!table.tBodies.length) return;
      const rows = [...table.tBodies[0].rows];
      if (rows.length < 8 && !rows.some(row => row.dataset.controlRow || row.dataset.historyRow)) return;
      const host = document.createElement('div');
      host.className = 'table-tools';
      const label = document.createElement('label');
      label.textContent = 'Tabelle durchsuchen';
      const input = document.createElement('input');
      input.type = 'search'; input.placeholder = 'Repository, ID oder Begriff';
      input.setAttribute('aria-label', `Tabelle ${index + 1} durchsuchen`);
      label.append(input);
      if (rows[0]?.dataset.controlRow || rows[0]?.dataset.historyRow) label.hidden = true;
      const status = document.createElement('span');
      status.className = 'count'; status.setAttribute('role', 'status');
      status.setAttribute('aria-live', 'polite'); host.append(label, status);
      const scroll = table.closest('.table-scroll') || table;
      scroll.before(host);
      const pager = document.createElement('div'); pager.className = 'pager';
      const prev = document.createElement('button'); prev.textContent = '← Zurück';
      const position = document.createElement('span');
      const next = document.createElement('button'); next.textContent = 'Weiter →';
      pager.append(prev, position, next); scroll.after(pager);
      let page = 0;
      function domainMatch(row) {
        if (row.dataset.controlRow) {
          const status = root.querySelector('#control-status-filter')?.value || 'all';
          const query = root.querySelector('#control-search-filter')?.value.toLowerCase() || '';
          return (status === 'all' || status === row.dataset.status) && row.textContent.toLowerCase().includes(query);
        }
        if (row.dataset.historyRow) {
          const rules = [['history-scope-filter','scope'],['history-status-filter','status'],['history-baseline-filter','baseline']];
          const query = root.querySelector('#history-search-filter')?.value.toLowerCase() || '';
          return rules.every(([id,key]) => {
            const value = root.querySelector('#'+id)?.value || 'all';
            return value === 'all' || value === row.dataset[key];
          }) && `${row.textContent} ${row.dataset.repository} ${row.dataset.branch} ${row.dataset.runId}`.toLowerCase().includes(query);
        }
        return true;
      }
      function draw() {
        const matches = rows.filter(row => domainMatch(row) && row.textContent.toLowerCase().includes(input.value.toLowerCase()));
        const pages = Math.max(1, Math.ceil(matches.length / 10)); page = Math.min(page, pages - 1);
        const shown = new Set(matches.slice(page * 10, page * 10 + 10));
        rows.forEach(row => { row.hidden = !shown.has(row); });
        status.textContent = `${matches.length} / ${rows.length} Treffer`;
        position.textContent = `Seite ${page + 1} von ${pages}`;
        prev.disabled = page === 0; next.disabled = page === pages - 1;
        const domainSummary = rows[0]?.dataset.controlRow ? '#control-filter-summary' : rows[0]?.dataset.historyRow ? '#history-filter-summary' : null;
        if (domainSummary && root.querySelector(domainSummary)) root.querySelector(domainSummary).textContent = `${matches.length} / ${rows.length} Treffer · ${shown.size} auf dieser Seite`;
      }
      input.addEventListener('input', () => { page = 0; draw(); });
      root.querySelectorAll('[id^="control-"][id$="-filter"], [id^="history-"][id$="-filter"]').forEach(el => {
        el.addEventListener(el.tagName === 'SELECT' ? 'change' : 'input', () => { page = 0; draw(); });
      });
      prev.addEventListener('click', () => { page--; draw(); });
      next.addEventListener('click', () => { page++; draw(); });
      draw();
    });
  }

  function mount(root, section, graph) {
    if (!section?.available || !section.html) {
      root.innerHTML = '<section class="panel empty"><h2>Keine Daten erfasst</h2><p>Für diesen Bereich ist keine Projektion verfügbar. Daraus wird kein PASS abgeleitet.</p></section>';
      return;
    }
    root.replaceChildren(fragment(section.html));
    // The application supplies the page heading; retain the original scope text.
    root.querySelector('.section-title h2')?.remove();
    root.querySelectorAll('table').forEach(table => {
      if (!table.closest('.table-scroll')) {
        const wrap = document.createElement('div'); wrap.className = 'table-scroll';
        table.before(wrap); wrap.append(table);
      }
    });
    tableTools(root);
    if (section.id === 'governance-graph' && graph) mountGraph(graph);
  }

    function mountGraph(graph) {
      const canvas = document.getElementById('governance-graph-canvas');
      const edgeLayer = document.getElementById('governance-graph-edges');
      const nodeLayer = document.getElementById('governance-graph-nodes');
      const scopeFilter = document.getElementById('graph-scope-filter');
      const typeFilter = document.getElementById('graph-type-filter');
      const searchFilter = document.getElementById('graph-search-filter');
      const resetButton = document.getElementById('graph-reset');
      const summary = document.getElementById('graph-filter-summary');
      const details = document.getElementById('graph-selection-details');
      const legend = document.getElementById('graph-legend');
      if (!canvas || !edgeLayer || !nodeLayer) return;

      const nodeById = new Map(graph.nodes.map(node => [node.id, node]));
      const colors = {
        SourceDocument: '#7c3aed', Artifact: '#64748b', Repository: '#0284c7',
        WorkflowRun: '#0f766e', Baseline: '#d97706', TrustAssessment: '#16a34a',
        EvidenceRecord: '#db2777', ResultSnapshot: '#475569', Commit: '#2563eb', Scanner: '#9333ea'
      };
      const operationalTypes = new Set(['Repository', 'WorkflowRun', 'Baseline', 'TrustAssessment', 'EvidenceRecord', 'ResultSnapshot', 'Commit', 'Scanner']);
      const lineageTypes = new Set(['SourceDocument', 'Artifact']);
      const svgNS = 'http://www.w3.org/2000/svg';
      let selectedId = null;

      const stableNumber = value => {
        let hash = 2166136261;
        for (let index = 0; index < value.length; index += 1) {
          hash ^= value.charCodeAt(index);
          hash = Math.imul(hash, 16777619);
        }
        return hash >>> 0;
      };

      const labelText = value => value.length > 28 ? `${value.slice(0, 25)}...` : value;

      const filteredGraph = () => {
        const scope = scopeFilter.value;
        const selectedType = typeFilter.value;
        const query = searchFilter.value.trim().toLowerCase();
        let candidates = graph.nodes.filter(node => {
          const scopeMatch = scope === 'all' || (scope === 'operational' ? operationalTypes.has(node.type) : lineageTypes.has(node.type));
          const typeMatch = selectedType === 'all' || node.type === selectedType;
          return scopeMatch && typeMatch;
        });
        if (query) {
          const matches = new Set(candidates.filter(node => JSON.stringify(node).toLowerCase().includes(query)).map(node => node.id));
          const neighbors = new Set(matches);
          for (const edge of graph.edges) {
            if (matches.has(edge.source)) neighbors.add(edge.target);
            if (matches.has(edge.target)) neighbors.add(edge.source);
          }
          candidates = candidates.filter(node => neighbors.has(node.id));
        }
        const truncated = candidates.length > 140;
        candidates = candidates.slice(0, 140);
        const ids = new Set(candidates.map(node => node.id));
        const edges = graph.edges.filter(edge => ids.has(edge.source) && ids.has(edge.target));
        return {nodes: candidates, edges, truncated};
      };

      const layout = (nodes, edges) => {
        const positions = new Map(nodes.map(node => {
          const seed = stableNumber(node.id);
          return [node.id, {x: 90 + (seed % 920), y: 70 + ((seed >>> 10) % 480), vx: 0, vy: 0}];
        }));
        const edgePairs = edges.map(edge => [positions.get(edge.source), positions.get(edge.target)]).filter(pair => pair[0] && pair[1]);
        for (let iteration = 0; iteration < 90; iteration += 1) {
          const cooling = 1 - iteration / 100;
          for (let left = 0; left < nodes.length; left += 1) {
            const a = positions.get(nodes[left].id);
            for (let right = left + 1; right < nodes.length; right += 1) {
              const b = positions.get(nodes[right].id);
              let dx = a.x - b.x;
              let dy = a.y - b.y;
              const distanceSquared = Math.max(dx * dx + dy * dy, 100);
              const force = 900 / distanceSquared;
              const distance = Math.sqrt(distanceSquared);
              dx /= distance; dy /= distance;
              a.vx += dx * force; a.vy += dy * force;
              b.vx -= dx * force; b.vy -= dy * force;
            }
          }
          for (const [a, b] of edgePairs) {
            const dx = b.x - a.x;
            const dy = b.y - a.y;
            const distance = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
            const force = (distance - 115) * 0.0018;
            a.vx += dx * force; a.vy += dy * force;
            b.vx -= dx * force; b.vy -= dy * force;
          }
          for (const position of positions.values()) {
            position.vx += (550 - position.x) * 0.0008;
            position.vy += (310 - position.y) * 0.0008;
            position.x = Math.max(45, Math.min(1055, position.x + position.vx * cooling));
            position.y = Math.max(35, Math.min(585, position.y + position.vy * cooling));
            position.vx *= 0.75; position.vy *= 0.75;
          }
        }
        // Spread the deterministic layout over the available canvas instead of
        // retaining the force solver's small cluster around the centre.
        const xs = [...positions.values()].map(p => p.x);
        const ys = [...positions.values()].map(p => p.y);
        const minX = Math.min(...xs), maxX = Math.max(...xs);
        const minY = Math.min(...ys), maxY = Math.max(...ys);
        for (const position of positions.values()) {
          position.x = maxX > minX ? 45 + (position.x - minX) / (maxX - minX) * 860 : 450;
          position.y = maxY > minY ? 40 + (position.y - minY) / (maxY - minY) * 520 : 310;
        }
        return positions;
      };

      const showDetails = node => {
        const incoming = graph.edges.filter(edge => edge.target === node.id).map(edge => ({type: edge.type, from: nodeById.get(edge.source)?.label || edge.source}));
        const outgoing = graph.edges.filter(edge => edge.source === node.id).map(edge => ({type: edge.type, to: nodeById.get(edge.target)?.label || edge.target}));
        details.textContent = JSON.stringify({type: node.type, label: node.label, properties: node.properties, incoming, outgoing}, null, 2);
      };

      const render = () => {
        const filtered = filteredGraph();
        const positions = layout(filtered.nodes, filtered.edges);
        edgeLayer.replaceChildren();
        nodeLayer.replaceChildren();
        const connected = new Set();
        if (selectedId) {
          connected.add(selectedId);
          for (const edge of filtered.edges) {
            if (edge.source === selectedId) connected.add(edge.target);
            if (edge.target === selectedId) connected.add(edge.source);
          }
        }
        for (const edge of filtered.edges) {
          const source = positions.get(edge.source);
          const target = positions.get(edge.target);
          if (!source || !target) continue;
          const line = document.createElementNS(svgNS, 'line');
          line.setAttribute('x1', source.x); line.setAttribute('y1', source.y);
          line.setAttribute('x2', target.x); line.setAttribute('y2', target.y);
          line.setAttribute('class', 'graph-edge');
          line.setAttribute('marker-end', 'url(#graph-arrow)');
          if (selectedId && edge.source !== selectedId && edge.target !== selectedId) line.classList.add('graph-muted');
          edgeLayer.appendChild(line);
        }
        for (const node of filtered.nodes) {
          const position = positions.get(node.id);
          const group = document.createElementNS(svgNS, 'g');
          group.setAttribute('class', 'graph-node');
          group.setAttribute('transform', `translate(${position.x},${position.y})`);
          group.setAttribute('tabindex', '0');
          group.setAttribute('role', 'button');
          group.setAttribute('aria-label', `${node.type}: ${node.label}`);
          if (selectedId && !connected.has(node.id)) group.classList.add('graph-muted');
          if (node.id === selectedId) group.classList.add('graph-selected');
          const circle = document.createElementNS(svgNS, 'circle');
          circle.setAttribute('r', node.type === 'Repository' || node.type === 'SourceDocument' ? 13 : 9);
          circle.setAttribute('fill', colors[node.type] || '#64748b');
          const text = document.createElementNS(svgNS, 'text');
          text.setAttribute('x', 15); text.setAttribute('y', 4);
          text.textContent = labelText(node.label);
          const select = () => { selectedId = node.id; showDetails(node); render(); };
          group.addEventListener('click', select);
          group.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(); } });
          group.append(circle, text);
          nodeLayer.appendChild(group);
        }
        summary.textContent = `${filtered.nodes.length} Knoten und ${filtered.edges.length} Beziehungen sichtbar${filtered.truncated ? ' (auf 140 Knoten begrenzt; bitte Filter eingrenzen)' : ''}`;
      };

      for (const [type, color] of Object.entries(colors)) {
        const item = document.createElement('span');
        const dot = document.createElementNS(svgNS, 'svg');
        dot.setAttribute('width', '10'); dot.setAttribute('height', '10');
        const circle = document.createElementNS(svgNS, 'circle');
        circle.setAttribute('cx', '5'); circle.setAttribute('cy', '5'); circle.setAttribute('r', '5'); circle.setAttribute('fill', color);
        dot.append(circle); item.append(dot, document.createTextNode(type));
        legend.appendChild(item);
      }
      for (const element of [scopeFilter, typeFilter]) element.addEventListener('change', () => { selectedId = null; details.textContent = 'Keine Auswahl.'; render(); });
      searchFilter.addEventListener('input', () => { selectedId = null; details.textContent = 'Keine Auswahl.'; render(); });
      resetButton.addEventListener('click', () => {
        scopeFilter.value = 'operational'; typeFilter.value = 'all'; searchFilter.value = '';
        selectedId = null; details.textContent = 'Keine Auswahl.'; render();
      });
      render();
    }
  
  return { mount };
})();
