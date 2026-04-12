import json
import streamlit.components.v1 as components


def render_execution_chart(roadmap: dict) -> None:
    """Render an interactive execution roadmap chart inside a Streamlit component."""
    if not roadmap or not roadmap.get("phases"):
        return

    roadmap_json = json.dumps(roadmap)
    max_nodes = max(len(p["nodes"]) for p in roadmap["phases"])
    height = max(560, 160 + max_nodes * 118)

    html = _build_html(roadmap_json)
    components.html(html, height=height, scrolling=True)


def _build_html(roadmap_json: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: #C8E6F7;
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    color: #1A2C3D;
    overflow: hidden;
  }}

  #root {{
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: #C8E6F7;
    padding: 16px 20px 20px;
    gap: 12px;
  }}

  /* ── Progress Bar ── */
  #progress-header {{
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }}

  #progress-label {{
    font-size: 12px;
    color: #4A6D8C;
    white-space: nowrap;
    min-width: 130px;
  }}

  #progress-track {{
    flex: 1;
    height: 4px;
    background: #B8CFE0;
    border-radius: 99px;
    overflow: hidden;
  }}

  #progress-fill {{
    height: 100%;
    background: linear-gradient(90deg, #5AA8E6, #3B8FD4);
    border-radius: 99px;
    transition: width 0.4s ease;
    width: 0%;
  }}

  /* ── Scroll Container ── */
  #scroll-area {{
    flex: 1;
    overflow: auto;
    position: relative;
  }}

  #board {{
    display: flex;
    flex-direction: row;
    gap: 48px;
    padding: 4px 4px 24px 4px;
    position: relative;
    min-width: max-content;
  }}

  /* ── Phase Column ── */
  .phase-col {{
    width: 230px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 0;
  }}

  .phase-header {{
    height: 58px;
    border-radius: 8px 8px 0 0;
    background: linear-gradient(135deg, #3B8FD4 0%, #5AA8E6 100%);
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 3px;
    position: relative;
  }}

  .phase-number {{
    font-size: 10px;
    font-weight: 700;
    color: rgba(255,255,255,0.65);
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }}

  .phase-title {{
    font-size: 13px;
    font-weight: 600;
    color: #FFFFFF;
    line-height: 1.2;
  }}

  .phase-meta {{
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 2px;
  }}

  .phase-timeframe {{
    font-size: 10px;
    color: rgba(255,255,255,0.72);
  }}

  .urgency-badge {{
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    border-radius: 4px;
    padding: 2px 5px;
  }}

  .urgency-critical {{ background: #FDECEA; color: #C0392B; }}
  .urgency-high     {{ background: #FEF3E2; color: #D4850A; }}
  .urgency-medium   {{ background: #E3F0FB; color: #2471A3; }}
  .urgency-low      {{ background: #E8F8F2; color: #1E8449; }}

  .phase-body {{
    background: #EEF2F5;
    border-radius: 0 0 8px 8px;
    padding: 10px 10px 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    border: 1px solid #B8CFE0;
    border-top: none;
  }}

  /* ── Node Card ── */
  .node-card {{
    width: 210px;
    min-height: 88px;
    background: #C8E6F7;
    border: 1px solid #B8CFE0;
    border-radius: 8px;
    padding: 10px 12px;
    cursor: pointer;
    position: relative;
    transition: background 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }}

  .node-card:hover {{
    background: #EEF2F5;
    border-color: #3B8FD4;
  }}

  .node-card.selected {{
    border-color: #5AA8E6;
    box-shadow: 0 0 0 2px rgba(90,168,230,0.25);
  }}

  .node-card.done {{
    border-color: #27AE60 !important;
    background: #EBF8F1 !important;
    box-shadow: none !important;
  }}

  .done-check {{
    position: absolute;
    top: 7px;
    right: 9px;
    font-size: 13px;
    color: #27AE60;
    display: none;
  }}

  .node-card.done .done-check {{
    display: block;
  }}

  .node-title {{
    font-size: 12px;
    font-weight: 600;
    color: #1A2C3D;
    line-height: 1.35;
    padding-right: 18px;
  }}

  .node-owner {{
    font-size: 10px;
    color: #4A6D8C;
  }}

  .node-output-tag {{
    display: inline-block;
    font-size: 9px;
    color: #3B8FD4;
    background: rgba(59,143,212,0.08);
    border: 1px solid rgba(59,143,212,0.22);
    border-radius: 4px;
    padding: 2px 6px;
    margin-top: 2px;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}

  .node-due-tag {{
    display: inline-block;
    font-size: 9px;
    color: #4A6D8C;
    background: #EEF2F5;
    border-radius: 4px;
    padding: 2px 6px;
    margin-top: 2px;
    margin-right: 3px;
    white-space: nowrap;
  }}

  .node-desc-preview {{
    font-size: 10px;
    color: #8AAEC8;
    line-height: 1.4;
    margin-top: 3px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}

  /* ── SVG overlay ── */
  #connections-svg {{
    position: absolute;
    top: 0;
    left: 0;
    pointer-events: none;
    overflow: visible;
  }}

  /* ── Detail Panel ── */
  #detail-panel {{
    position: fixed;
    right: 0;
    top: 0;
    height: 100%;
    width: 280px;
    background: #EEF2F5;
    border-left: 1px solid #C2D4EA;
    z-index: 1000;
    transform: translateX(100%);
    transition: transform 0.28s cubic-bezier(0.4,0,0.2,1);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}

  #detail-panel.open {{
    transform: translateX(0);
  }}

  #detail-panel-header {{
    padding: 16px 16px 12px;
    border-bottom: 1px solid #C2D4EA;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
    flex-shrink: 0;
  }}

  #detail-phase-badge {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #2471A3;
    background: #E3F0FB;
    border-radius: 4px;
    padding: 3px 7px;
    margin-bottom: 6px;
    display: inline-block;
  }}

  #detail-title {{
    font-size: 14px;
    font-weight: 700;
    color: #1A2C3D;
    line-height: 1.4;
  }}

  #detail-close {{
    background: none;
    border: none;
    color: #8AAEC8;
    font-size: 18px;
    cursor: pointer;
    padding: 0 2px;
    flex-shrink: 0;
    line-height: 1;
    transition: color 0.15s;
  }}

  #detail-close:hover {{ color: #1A2C3D; }}

  #detail-body {{
    flex: 1;
    overflow-y: auto;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }}

  .detail-section-label {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #8AAEC8;
    margin-bottom: 4px;
  }}

  .detail-description {{
    font-size: 12px;
    color: #4A6D8C;
    line-height: 1.6;
  }}

  .detail-chip {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    color: #1A2C3D;
    background: #C8E6F7;
    border: 1px solid #B8CFE0;
    border-radius: 6px;
    padding: 5px 9px;
  }}

  .detail-chip-icon {{
    font-size: 12px;
  }}

  /* scrollbar */
  ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: #B8CFE0; border-radius: 4px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: #3B8FD4; }}
</style>
</head>
<body>
<div id="root">
  <div id="progress-header">
    <span id="progress-label">0 / 0 tasks completed</span>
    <div id="progress-track"><div id="progress-fill"></div></div>
  </div>
  <div id="scroll-area">
    <div id="board">
      <svg id="connections-svg"></svg>
    </div>
  </div>
</div>

<div id="detail-panel">
  <div id="detail-panel-header">
    <div style="flex:1; min-width:0;">
      <span id="detail-phase-badge"></span>
      <div id="detail-title"></div>
    </div>
    <button id="detail-close" title="Close">&#x2715;</button>
  </div>
  <div id="detail-body">
    <div id="detail-desc-section">
      <div class="detail-section-label">Description</div>
      <div class="detail-description" id="detail-desc"></div>
    </div>
    <div id="detail-owner-section">
      <div class="detail-section-label">Owner</div>
      <div class="detail-chip"><span class="detail-chip-icon">&#128100;</span><span id="detail-owner"></span></div>
    </div>
    <div id="detail-due-section">
      <div class="detail-section-label">Due</div>
      <div class="detail-chip"><span class="detail-chip-icon">&#128337;</span><span id="detail-due"></span></div>
    </div>
    <div id="detail-output-section">
      <div class="detail-section-label">Output / Deliverable</div>
      <div class="detail-chip"><span class="detail-chip-icon">&#128196;</span><span id="detail-output"></span></div>
    </div>
  </div>
</div>

<script>
(function() {{
  const ROADMAP = {roadmap_json};

  // ── State ──
  const doneSet = new Set();
  let selectedNodeId = null;
  let totalNodes = 0;

  // ── Helpers ──
  function phaseLabel(i) {{
    return String(i + 1).padStart(2, '0');
  }}

  function urgencyClass(u) {{
    if (!u) return 'urgency-medium';
    const v = u.toLowerCase();
    if (v === 'critical') return 'urgency-critical';
    if (v === 'high')     return 'urgency-high';
    if (v === 'low')      return 'urgency-low';
    return 'urgency-medium';
  }}

  // ── Build Board ──
  const board = document.getElementById('board');
  const svg   = document.getElementById('connections-svg');

  // nodeId → DOM element map
  const nodeEls = {{}};
  // phaseIndex → array of nodeIds (in order)
  const phaseNodeIds = [];

  (ROADMAP.phases || []).forEach(function(phase, pi) {{
    const col = document.createElement('div');
    col.className = 'phase-col';
    col.id = 'phase-col-' + pi;

    // Header
    const hdr = document.createElement('div');
    hdr.className = 'phase-header';
    const urgCls = urgencyClass(phase.urgency);
    hdr.innerHTML =
      '<div class="phase-number">Phase ' + phaseLabel(pi) + '</div>' +
      '<div class="phase-title">' + escHtml(phase.title || '') + '</div>' +
      '<div class="phase-meta">' +
        (phase.timeframe ? '<span class="phase-timeframe">' + escHtml(phase.timeframe) + '</span>' : '') +
        (phase.urgency   ? '<span class="urgency-badge ' + urgCls + '">' + escHtml(phase.urgency) + '</span>' : '') +
      '</div>';
    col.appendChild(hdr);

    // Body
    const body = document.createElement('div');
    body.className = 'phase-body';
    body.id = 'phase-body-' + pi;

    const ids = [];
    (phase.nodes || []).forEach(function(node, ni) {{
      const nodeId = 'node-' + pi + '-' + ni;
      ids.push(nodeId);
      totalNodes++;

      const card = document.createElement('div');
      card.className = 'node-card';
      card.id = nodeId;
      card.dataset.phaseIndex = pi;
      card.dataset.nodeIndex  = ni;
      card.dataset.nodeTitle  = node.title || '';
      card.dataset.nodeDesc   = node.description || '';
      card.dataset.nodeOwner  = node.owner || '';
      card.dataset.nodeOutput = node.output || '';
      card.dataset.nodeDue    = node.due || '';
      card.dataset.phaseTitle = phase.title || '';
      card.dataset.urgency    = phase.urgency || '';

      const descPreview = (node.description || '').replace(/\s+/g, ' ').slice(0, 90);

      card.innerHTML =
        '<span class="done-check">&#10003;</span>' +
        '<div class="node-title">' + escHtml(node.title || '') + '</div>' +
        (descPreview ? '<div class="node-desc-preview">' + escHtml(descPreview) + '</div>' : '') +
        '<div style="display:flex;flex-wrap:wrap;gap:2px;margin-top:4px;">' +
        (node.due    ? '<span class="node-due-tag">&#128337; ' + escHtml(node.due) + '</span>' : '') +
        (node.owner  ? '<span class="node-due-tag">&#128100; ' + escHtml(node.owner.split('/')[0].trim()) + '</span>' : '') +
        '</div>' +
        (node.output ? '<div class="node-output-tag">&#128196; ' + escHtml(node.output) + '</div>' : '');

      card.addEventListener('click', function() {{ onNodeClick(nodeId, card); }});
      body.appendChild(card);
      nodeEls[nodeId] = card;
    }});

    phaseNodeIds.push(ids);
    col.appendChild(body);
    board.appendChild(col);
  }});

  updateProgress();

  // ── Connections ──
  function drawConnections() {{
    svg.innerHTML = '';
    const boardRect = board.getBoundingClientRect();

    // Arrowhead marker
    const defs = makeSVGEl('defs');
    const marker = makeSVGEl('marker');
    marker.setAttribute('id', 'arrow');
    marker.setAttribute('markerWidth', '8');
    marker.setAttribute('markerHeight', '8');
    marker.setAttribute('refX', '6');
    marker.setAttribute('refY', '3');
    marker.setAttribute('orient', 'auto');
    const poly = makeSVGEl('polygon');
    poly.setAttribute('points', '0 0, 6 3, 0 6');
    poly.setAttribute('fill', 'rgba(59,143,212,0.7)');
    marker.appendChild(poly);
    defs.appendChild(marker);
    svg.appendChild(defs);

    phaseNodeIds.forEach(function(ids, pi) {{
      // Vertical dashed connectors within phase
      for (let ni = 0; ni < ids.length - 1; ni++) {{
        const fromEl = nodeEls[ids[ni]];
        const toEl   = nodeEls[ids[ni + 1]];
        if (!fromEl || !toEl) continue;
        const fr = fromEl.getBoundingClientRect();
        const tr = toEl.getBoundingClientRect();
        const x  = fr.left + fr.width / 2 - boardRect.left;
        const y1 = fr.bottom - boardRect.top;
        const y2 = tr.top    - boardRect.top;
        if (y2 <= y1) continue;
        const line = makeSVGEl('line');
        line.setAttribute('x1', x);
        line.setAttribute('y1', y1);
        line.setAttribute('x2', x);
        line.setAttribute('y2', y2);
        line.setAttribute('stroke', 'rgba(59,143,212,0.4)');
        line.setAttribute('stroke-width', '1.5');
        line.setAttribute('stroke-dasharray', '4 4');
        svg.appendChild(line);
      }}

      // Horizontal bezier to next phase
      const nextIds = phaseNodeIds[pi + 1];
      if (!nextIds || nextIds.length === 0 || ids.length === 0) return;
      const fromEl = nodeEls[ids[ids.length - 1]];
      const toEl   = nodeEls[nextIds[0]];
      if (!fromEl || !toEl) return;
      const fr = fromEl.getBoundingClientRect();
      const tr = toEl.getBoundingClientRect();
      const x1 = fr.right  - boardRect.left;
      const y1 = fr.top + fr.height / 2 - boardRect.top;
      const x2 = tr.left   - boardRect.left - 6; // arrowhead offset
      const y2 = tr.top + tr.height / 2 - boardRect.top;
      const cx = (x1 + x2) / 2;
      const path = makeSVGEl('path');
      path.setAttribute('d', 'M ' + x1 + ' ' + y1 + ' C ' + cx + ' ' + y1 + ', ' + cx + ' ' + y2 + ', ' + x2 + ' ' + y2);
      path.setAttribute('stroke', 'rgba(59,143,212,0.65)');
      path.setAttribute('stroke-width', '1.5');
      path.setAttribute('fill', 'none');
      path.setAttribute('marker-end', 'url(#arrow)');
      svg.appendChild(path);
    }});

    // Size SVG to board
    svg.setAttribute('width',  board.scrollWidth);
    svg.setAttribute('height', board.scrollHeight);
  }}

  function makeSVGEl(tag) {{
    return document.createElementNS('http://www.w3.org/2000/svg', tag);
  }}

  window.addEventListener('load', drawConnections);
  window.addEventListener('resize', drawConnections);

  // ── Node click ──
  function onNodeClick(nodeId, card) {{
    // Toggle done
    if (doneSet.has(nodeId)) {{
      doneSet.delete(nodeId);
      card.classList.remove('done');
    }} else {{
      doneSet.add(nodeId);
      card.classList.add('done');
    }}
    updateProgress();

    // Toggle selected
    if (selectedNodeId && selectedNodeId !== nodeId) {{
      const prev = nodeEls[selectedNodeId];
      if (prev) prev.classList.remove('selected');
    }}
    if (selectedNodeId === nodeId) {{
      card.classList.remove('selected');
      selectedNodeId = null;
      closePanel();
    }} else {{
      card.classList.add('selected');
      selectedNodeId = nodeId;
      openPanel(card);
    }}
  }}

  // ── Progress ──
  function updateProgress() {{
    const done  = doneSet.size;
    const total = totalNodes;
    document.getElementById('progress-label').textContent = done + ' / ' + total + ' tasks completed';
    const pct = total > 0 ? (done / total) * 100 : 0;
    document.getElementById('progress-fill').style.width = pct + '%';
  }}

  // ── Detail Panel ──
  const panel = document.getElementById('detail-panel');

  function openPanel(card) {{
    document.getElementById('detail-phase-badge').textContent = 'Phase ' + (parseInt(card.dataset.phaseIndex) + 1) + ' — ' + (card.dataset.phaseTitle || '');
    document.getElementById('detail-title').textContent  = card.dataset.nodeTitle  || '';
    document.getElementById('detail-desc').textContent   = card.dataset.nodeDesc   || 'No description provided.';
    document.getElementById('detail-owner').textContent  = card.dataset.nodeOwner  || '—';
    document.getElementById('detail-due').textContent    = card.dataset.nodeDue    || '—';
    document.getElementById('detail-output').textContent = card.dataset.nodeOutput || '—';

    const urgEl = document.getElementById('detail-phase-badge');
    urgEl.className = '';
    const u = (card.dataset.urgency || '').toLowerCase();
    if (u === 'critical') urgEl.style.cssText = 'font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;border-radius:4px;padding:3px 7px;margin-bottom:6px;display:inline-block;background:#FDECEA;color:#C0392B;';
    else if (u === 'high') urgEl.style.cssText = 'font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;border-radius:4px;padding:3px 7px;margin-bottom:6px;display:inline-block;background:#FEF3E2;color:#D4850A;';
    else if (u === 'low')  urgEl.style.cssText = 'font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;border-radius:4px;padding:3px 7px;margin-bottom:6px;display:inline-block;background:#E8F8F2;color:#1E8449;';
    else                   urgEl.style.cssText = 'font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;border-radius:4px;padding:3px 7px;margin-bottom:6px;display:inline-block;background:#E3F0FB;color:#2471A3;';

    panel.classList.add('open');
  }}

  function closePanel() {{
    panel.classList.remove('open');
    if (selectedNodeId) {{
      const prev = nodeEls[selectedNodeId];
      if (prev) prev.classList.remove('selected');
      selectedNodeId = null;
    }}
  }}

  document.getElementById('detail-close').addEventListener('click', closePanel);

  // ── Escape key closes panel ──
  document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closePanel();
  }});

  // ── HTML escape ──
  function escHtml(str) {{
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }}
}})();
</script>
</body>
</html>"""
