"""Vista cronograma por área · estilo HTML que mandó Alejandro.

Matriz 5 días Lun-Vie × 10 áreas con chips coloreados por fase.
Auto-alimentada desde /api/planta/cronograma-areas.
"""

PROGRAMACION_AREAS_HTML = r'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>📅 Programación por Área · HHA Group</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: #f8fafc; color: #1e293b; padding: 16px;
  }
  .container { max-width: 1400px; margin: 0 auto; }
  .topbar {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #e2e8f0;
    flex-wrap: wrap; gap: 12px;
  }
  h1 { font-size: 22px; margin: 0; color: #0f172a; }
  .subtitle { font-size: 12px; color: #64748b; margin-top: 2px; }
  .nav { font-size: 12px; }
  .nav a { color: #2B7A78; text-decoration: none; margin-right: 14px; }
  .nav a:hover { text-decoration: underline; }
  .controls {
    display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
  }
  button.semana {
    background: #fff; border: 1px solid #cbd5e1; border-radius: 6px;
    padding: 6px 12px; font-size: 13px; font-weight: 600; cursor: pointer;
    color: #475569;
  }
  button.semana:hover { background: #f1f5f9; }
  button.semana.active {
    background: #1e293b; border-color: #1e293b; color: #fff;
  }
  .legend {
    display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px;
    font-size: 11px;
  }
  .legend .chip {
    padding: 4px 10px; border-radius: 12px; color: #fff; font-weight: 600;
  }
  .chip.fab    { background: #2563eb; }
  .chip.env    { background: #15803d; }
  .chip.micro  { background: #ea580c; }
  .chip.lib    { background: #7c3aed; }
  .chip.acond  { background: #0891b2; }
  .chip.entr   { background: #dc2626; }
  .chip.limp   { background: #64748b; }
  .chip.urg    { background: #b91c1c; box-shadow: 0 0 0 2px #fecaca; }

  .matriz-wrap {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
    overflow-x: auto; padding: 0;
  }
  table.matriz {
    border-collapse: collapse; width: 100%; min-width: 1100px;
    table-layout: fixed;
  }
  table.matriz th, table.matriz td {
    border: 1px solid #e2e8f0; vertical-align: top; padding: 0;
  }
  table.matriz th.area-h {
    background: #f1f5f9; color: #475569; font-size: 11px; font-weight: 700;
    padding: 10px 8px; text-transform: uppercase; letter-spacing: 0.4px;
    width: 120px; text-align: left;
  }
  table.matriz th.day-h {
    background: linear-gradient(180deg, #1e293b, #0f172a); color: #fff;
    font-size: 13px; font-weight: 700; padding: 12px 8px; text-align: center;
  }
  table.matriz td.cell {
    padding: 8px 6px; min-height: 70px; height: 90px; background: #fff;
  }
  table.matriz tr:nth-child(even) td.cell { background: #fafbfc; }
  table.matriz td.empty { background: #fdfdfd; }

  .row-fab1 th.area-h, .row-fye2 th.area-h, .row-fye3 th.area-h {
    background: #dbeafe; color: #1e40af;
  }
  .row-env1 th.area-h, .row-env2 th.area-h {
    background: #dcfce7; color: #166534;
  }
  .row-micro th.area-h { background: #fed7aa; color: #9a3412; }
  .row-lib th.area-h   { background: #ede9fe; color: #5b21b6; }
  .row-acond th.area-h { background: #cffafe; color: #155e75; }
  .row-entr th.area-h  { background: #fee2e2; color: #991b1b; }
  .row-limp th.area-h  { background: #f1f5f9; color: #334155; }

  .chip-cell {
    display: block; padding: 6px 8px; border-radius: 6px; color: #fff;
    font-size: 11px; font-weight: 600; line-height: 1.3; margin-bottom: 4px;
    white-space: pre-wrap; word-break: break-word;
  }
  .chip-cell.fab    { background: #2563eb; }
  .chip-cell.env    { background: #15803d; }
  .chip-cell.micro  { background: #ea580c; }
  .chip-cell.lib    { background: #7c3aed; }
  .chip-cell.acond  { background: #0891b2; }
  .chip-cell.entr   { background: #dc2626; }
  .chip-cell.limp   { background: #64748b; }
  .chip-cell.urg {
    background: linear-gradient(135deg, #b91c1c, #ef4444);
    box-shadow: 0 0 0 1px #fecaca, inset 0 0 0 1px rgba(255,255,255,0.2);
    animation: urg-pulse 2s ease-in-out infinite;
  }
  @keyframes urg-pulse {
    0%, 100% { box-shadow: 0 0 0 1px #fecaca; }
    50% { box-shadow: 0 0 0 3px #fee2e2; }
  }
  .urg-icon { font-size: 9px; vertical-align: super; margin-right: 2px; }

  .empty-msg {
    color: #cbd5e1; font-size: 11px; font-style: italic; text-align: center;
    padding: 4px;
  }
  .spinner {
    display: inline-block; width: 14px; height: 14px;
    border: 2px solid #cbd5e1; border-top-color: #1e293b;
    border-radius: 50%; animation: spin 0.8s linear infinite;
    margin-right: 6px; vertical-align: middle;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loading {
    text-align: center; padding: 40px; color: #64748b; font-size: 14px;
  }
  .footer-note {
    margin-top: 14px; padding: 10px 14px; background: #fef3c7;
    border-left: 4px solid #f59e0b; border-radius: 6px; font-size: 12px;
    color: #78350f;
  }
</style>
</head>
<body>
<div class="container">
  <div class="topbar">
    <div>
      <h1>📅 Programación por Área</h1>
      <div class="subtitle">
        Vista calendario semanal · auto-alimentada desde Calendar + producción
      </div>
      <div class="nav" style="margin-top:6px">
        <a href="/planta">← Planta</a>
        <a href="/aseguramiento">Aseguramiento</a>
        <a href="/admin/system-health">System Health</a>
      </div>
    </div>
    <div class="controls">
      <button class="semana" data-offset="-1" onclick="cambiarSemana(-1)">← Semana ant.</button>
      <span id="semana-label" style="font-weight:700;font-size:14px;color:#0f172a;min-width:160px;text-align:center">
        cargando…
      </span>
      <button class="semana" data-offset="1" onclick="cambiarSemana(1)">Semana sig. →</button>
      <button class="semana" onclick="irHoy()" style="margin-left:8px">📅 Hoy</button>
    </div>
  </div>

  <div class="legend">
    <span class="chip fab">FAB</span>
    <span class="chip env">ENV</span>
    <span class="chip micro">MICRO</span>
    <span class="chip lib">LIB</span>
    <span class="chip acond">ACOND</span>
    <span class="chip entr">ENTR</span>
    <span class="chip limp">LIMP</span>
    <span class="chip urg">⚡ URG</span>
  </div>

  <div id="content">
    <div class="loading"><span class="spinner"></span> Cargando cronograma…</div>
  </div>

  <div class="footer-note">
    💡 <b>Auto-alimentado:</b> esta vista refleja en tiempo real los datos del
    sistema · si una fase aparece vacía, es porque aún no se registró en su
    módulo (ej. envasado lo crea Operario al iniciar envasado).
  </div>
</div>

<script>
var _semanaActual = null;  // string YYYY-MM-DD del lunes

function _esc(s){
  return String(s||'').replace(/[&<>"']/g, ch => (
    {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]
  ));
}

var AREA_LABELS = {
  fab1: ['FABRICACIÓN', 'Sala 1'],
  fye2: ['FAB + ENV', 'Sala 2'],
  fye3: ['FAB + ENV', 'Sala 3'],
  env1: ['ENVASADO', 'Sala 1'],
  env2: ['ENVASADO', 'Sala 2'],
  micro: ['MICROBIOLOGÍA', ''],
  lib: ['LIBERACIÓN', ''],
  acond: ['ACONDICIONAMIENTO', ''],
  entr: ['ENTREGA', ''],
  limp: ['LIMPIEZA PROFUNDA', ''],
};

function buildChip(act) {
  var cls = 'chip-cell ' + (act.t || 'fab');
  if (act.u) cls += ' urg';
  var label = _esc(act.l || '');
  // \n → <br>
  label = label.replace(/\n/g, '<br>');
  var icon = act.u ? '<span class="urg-icon">⚡</span>' : '';
  return `<span class="${cls}">${icon}${label}</span>`;
}

function buildCell(activities) {
  if (!activities || !activities.length) {
    return '<td class="cell empty"></td>';
  }
  var chips = activities.map(buildChip).join('');
  return `<td class="cell">${chips}</td>`;
}

function buildTable(data) {
  var areas = data.areas || {};
  var days = data.days || [];
  var html = '<table class="matriz"><thead><tr>';
  html += '<th class="area-h">Área</th>';
  days.forEach(function(d) {
    html += `<th class="day-h">${_esc(d)}</th>`;
  });
  html += '</tr></thead><tbody>';

  var orden = ['fab1', 'fye2', 'fye3', 'env1', 'env2',
               'micro', 'lib', 'acond', 'entr', 'limp'];
  orden.forEach(function(area) {
    var labels = AREA_LABELS[area] || [area, ''];
    html += `<tr class="row-${area}">`;
    html += `<th class="area-h">${_esc(labels[0])}<br><span style="font-weight:400;font-size:10px;opacity:.7">${_esc(labels[1])}</span></th>`;
    var cells = areas[area] || [[], [], [], [], []];
    for (var i = 0; i < 5; i++) {
      html += buildCell(cells[i] || []);
    }
    html += '</tr>';
  });
  html += '</tbody></table>';
  return html;
}

async function cargarSemana(desde) {
  var content = document.getElementById('content');
  var label = document.getElementById('semana-label');
  content.innerHTML = '<div class="loading"><span class="spinner"></span> Cargando…</div>';
  try {
    var url = '/api/planta/cronograma-areas';
    if (desde) url += '?desde=' + encodeURIComponent(desde);
    var r = await fetch(url);
    if (!r.ok) {
      content.innerHTML = `<div class="loading" style="color:#dc2626">Error ${r.status}</div>`;
      return;
    }
    var d = await r.json();
    label.textContent = (d.rango && d.rango.semana) || '';
    _semanaActual = (d.rango && d.rango.desde) || desde;
    content.innerHTML = '<div class="matriz-wrap">' + buildTable(d) + '</div>';
  } catch(e) {
    content.innerHTML = '<div class="loading" style="color:#dc2626">Error red: ' + _esc(e.message) + '</div>';
  }
}

function cambiarSemana(offset) {
  if (!_semanaActual) return;
  // Sumar offset*7 días al lunes actual
  var d = new Date(_semanaActual + 'T00:00:00');
  d.setDate(d.getDate() + offset * 7);
  var y = d.getFullYear();
  var m = String(d.getMonth() + 1).padStart(2, '0');
  var day = String(d.getDate()).padStart(2, '0');
  cargarSemana(`${y}-${m}-${day}`);
}

function irHoy() {
  cargarSemana(null);  // sin param = lunes de esta semana
}

cargarSemana(null);
</script>
</body>
</html>'''
