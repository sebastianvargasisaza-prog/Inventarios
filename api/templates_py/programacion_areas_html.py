"""Vista cronograma por área · réplica EXACTA del HTML de Alejandro.

Matriz 5 días Lun-Vie × 10 áreas con tarjetas pastel por fase.
Auto-alimentada desde /api/planta/cronograma-areas.

Estilo visual matchea animuslab.neocities.org/programacion_mayo_areas:
- Tarjetas con fondo pastel suave (no chips coloreados sólidos)
- Tipo (FAB/ENV/MICRO/...) como label en mayúsculas arriba
- Producto en texto regular debajo, multilínea
- URGENTE: borde rojo grueso + ⚡ icon (sin animación)
- Headers de área con ícono pequeño + nombre + subtítulo
"""

PROGRAMACION_AREAS_HTML = r'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>📅 Programación Mayo — Por Área</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f5; color: #1f2937; padding: 20px;
  }
  .container { max-width: 1500px; margin: 0 auto; }
  .topbar {
    margin-bottom: 18px;
  }
  h1 { font-size: 26px; margin: 0; color: #0f172a; font-weight: 700; }
  .subtitle { font-size: 13px; color: #64748b; margin-top: 4px; }
  .nav { font-size: 12px; margin-top: 8px; }
  .nav a { color: #2B7A78; text-decoration: none; margin-right: 14px; }
  .nav a:hover { text-decoration: underline; }

  /* Leyenda chips arriba */
  .legend {
    display: flex; gap: 10px; flex-wrap: wrap;
    margin: 14px 0; align-items: center;
  }
  .legend .lg-chip {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 12px; border-radius: 14px;
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.4px;
  }
  .lg-chip .dot { width: 10px; height: 10px; border-radius: 50%; }
  .lg-chip.fab    { background: #fef9c3; color: #854d0e; }
  .lg-chip.fab .dot    { background: #facc15; }
  .lg-chip.env    { background: #dbeafe; color: #1e40af; }
  .lg-chip.env .dot    { background: #3b82f6; }
  .lg-chip.micro  { background: #fed7aa; color: #9a3412; }
  .lg-chip.micro .dot  { background: #f97316; }
  .lg-chip.lib    { background: #dcfce7; color: #166534; }
  .lg-chip.lib .dot    { background: #22c55e; }
  .lg-chip.acond  { background: #f3e8ff; color: #6b21a8; }
  .lg-chip.acond .dot  { background: #a855f7; }
  .lg-chip.entr   { background: #fce7f3; color: #9d174d; }
  .lg-chip.entr .dot   { background: #ec4899; }
  .lg-chip.limp   { background: #fff7ed; color: #9a3412; }
  .lg-chip.limp .dot   { background: #fb923c; }
  .lg-chip.urg {
    background: #fee2e2; color: #991b1b;
    border: 2px solid #dc2626;
  }
  .lg-chip.urg .dot { background: #dc2626; }

  /* Botones de semana */
  .semanas {
    display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 18px;
  }
  button.semana {
    background: #fff; border: 1px solid #cbd5e1; border-radius: 8px;
    padding: 10px 20px; font-size: 14px; font-weight: 600;
    cursor: pointer; color: #475569;
    transition: all 0.15s ease;
  }
  button.semana:hover { background: #f1f5f9; border-color: #94a3b8; }
  button.semana.active {
    background: #2563eb; border-color: #2563eb; color: #fff;
    box-shadow: 0 2px 6px rgba(37,99,235,0.3);
  }

  /* Tabla matriz */
  .matriz-wrap {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
    overflow-x: auto; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  }
  table.matriz {
    border-collapse: collapse; width: 100%; min-width: 1200px;
    table-layout: fixed;
  }
  table.matriz th, table.matriz td {
    border: 1px solid #e5e7eb; vertical-align: top; padding: 0;
  }
  table.matriz th.area-h {
    background: #f9fafb; color: #374151;
    padding: 12px 14px; text-align: left;
    width: 180px; font-weight: 600; font-size: 13px;
  }
  table.matriz th.area-h .area-icon {
    font-size: 18px; margin-right: 4px; vertical-align: middle;
  }
  table.matriz th.area-h .area-sub {
    font-weight: 400; font-size: 11px; color: #6b7280;
    margin-top: 2px;
  }
  table.matriz th.day-h {
    background: #fff; color: #374151;
    font-weight: 600; padding: 14px 8px; text-align: center;
    border-bottom: 2px solid #e5e7eb;
  }
  table.matriz th.day-h .day-name { font-size: 14px; }
  table.matriz th.day-h .day-date {
    font-size: 12px; font-weight: 400; color: #9ca3af; margin-top: 2px;
  }
  table.matriz td.cell {
    padding: 6px; min-height: 95px; height: 95px; background: #fff;
    vertical-align: top;
  }
  table.matriz td.cell.empty { background: #fff; }

  /* Tarjetas dentro de cada celda */
  .act-card {
    display: block; padding: 8px 10px; border-radius: 6px;
    margin-bottom: 5px; line-height: 1.3;
    border: 1px solid transparent;
  }
  .act-card .act-type {
    display: inline-block; font-size: 9.5px; font-weight: 800;
    text-transform: uppercase; letter-spacing: 0.6px;
    margin-bottom: 3px;
  }
  .act-card .act-label {
    font-size: 11.5px; font-weight: 500; color: #1f2937;
    white-space: pre-wrap; word-break: break-word; line-height: 1.3;
  }

  /* Colores pastel por tipo · matchea HTML de Alejandro */
  .act-card.fab    { background: #fef9c3; }
  .act-card.fab .act-type    { color: #854d0e; }
  .act-card.env    { background: #dbeafe; }
  .act-card.env .act-type    { color: #1e40af; }
  .act-card.micro  { background: #fed7aa; }
  .act-card.micro .act-type  { color: #9a3412; }
  .act-card.lib    { background: #dcfce7; }
  .act-card.lib .act-type    { color: #166534; }
  .act-card.acond  { background: #f3e8ff; }
  .act-card.acond .act-type  { color: #6b21a8; }
  .act-card.entr   { background: #fce7f3; }
  .act-card.entr .act-type   { color: #9d174d; }
  .act-card.limp   { background: #fff7ed; }
  .act-card.limp .act-type   { color: #9a3412; }

  /* URGENTE · borde rojo grueso (sin animación) */
  .act-card.urg {
    border: 2px solid #dc2626;
    box-shadow: 0 0 0 1px #fecaca;
  }
  .urg-icon {
    color: #dc2626; font-weight: 700; margin-right: 3px; font-size: 11px;
  }

  /* Headers de área con color de borde izquierdo según tipo */
  .row-fab1 th.area-h, .row-fye2 th.area-h, .row-fye3 th.area-h {
    border-left: 4px solid #facc15;
  }
  .row-env1 th.area-h, .row-env2 th.area-h {
    border-left: 4px solid #3b82f6;
  }
  .row-micro th.area-h { border-left: 4px solid #f97316; }
  .row-lib th.area-h   { border-left: 4px solid #22c55e; }
  .row-acond th.area-h { border-left: 4px solid #a855f7; }
  .row-entr th.area-h  { border-left: 4px solid #ec4899; }
  .row-limp th.area-h  { border-left: 4px solid #fb923c; }

  .spinner {
    display: inline-block; width: 14px; height: 14px;
    border: 2px solid #cbd5e1; border-top-color: #2563eb;
    border-radius: 50%; animation: spin 0.8s linear infinite;
    margin-right: 8px; vertical-align: middle;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loading {
    text-align: center; padding: 50px; color: #64748b; font-size: 14px;
  }
  .footer-note {
    margin-top: 18px; padding: 12px 16px; background: #fffbeb;
    border-left: 4px solid #f59e0b; border-radius: 6px; font-size: 12px;
    color: #78350f;
  }
</style>
</head>
<body>
<div class="container">
  <div class="topbar">
    <h1>📅 Programación — Por Área</h1>
    <div class="subtitle">
      Actividades asignadas a cada área por día de trabajo · auto-alimentado en tiempo real
    </div>
    <div class="nav">
      <a href="/planta">← Planta</a>
      <a href="/programacion-comparar">🔍 Comparar con Alejandro</a>
      <a href="/aseguramiento">Aseguramiento</a>
      <a href="/admin/system-health">System Health</a>
    </div>
  </div>

  <div class="legend">
    <span class="lg-chip fab"><span class="dot"></span>FABRICACIÓN</span>
    <span class="lg-chip env"><span class="dot"></span>ENVASADO</span>
    <span class="lg-chip micro"><span class="dot"></span>MICROBIOLOGÍA</span>
    <span class="lg-chip lib"><span class="dot"></span>LIBERACIÓN</span>
    <span class="lg-chip acond"><span class="dot"></span>ACONDICIONAMIENTO</span>
    <span class="lg-chip entr"><span class="dot"></span>ENTREGA</span>
    <span class="lg-chip limp"><span class="dot"></span>LIMPIEZA PROFUNDA</span>
    <span class="lg-chip urg"><span class="dot"></span>⚡ URGENTE</span>
  </div>

  <div class="semanas" id="semanas-tabs">
    <!-- generado por JS -->
  </div>

  <div id="content">
    <div class="loading"><span class="spinner"></span> Cargando cronograma…</div>
  </div>

  <div class="footer-note">
    💡 <b>Auto-alimentado:</b> esta vista refleja en tiempo real los datos del
    sistema. Si una fase aparece vacía, es porque aún no se registró en su
    módulo (ej. envasado lo crea Operario al iniciar envasado · liberación
    aparece en su fecha estimada de +5 días post-MICRO).
  </div>
</div>

<script>
var _semanaActual = null;  // string YYYY-MM-DD del lunes

function _esc(s){
  return String(s||'').replace(/[&<>"']/g, ch => (
    {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]
  ));
}

var AREA_INFO = {
  fab1:  {icon: '🏭', label: 'Fabricación 1', sub: ''},
  fye2:  {icon: '🔄', label: 'Fab. y Env. 2', sub: ''},
  fye3:  {icon: '🔄', label: 'Fab. y Env. 3', sub: ''},
  env1:  {icon: '📦', label: 'Envasado 1', sub: ''},
  env2:  {icon: '📦', label: 'Envasado 2', sub: ''},
  micro: {icon: '🧪', label: 'Microbiología', sub: ''},
  lib:   {icon: '✅', label: 'Liberación', sub: ''},
  acond: {icon: '🎀', label: 'Acondicionamiento', sub: ''},
  entr:  {icon: '🚚', label: 'Entrega', sub: ''},
  limp:  {icon: '🧽', label: 'Limpieza', sub: 'Profunda'},
};

var TIPO_LABEL = {
  fab: 'FAB', env: 'ENV', micro: 'MICRO',
  lib: 'LIB', acond: 'ACOND', entr: 'ENTREGA',
  limp: 'LIMPIEZA',
};

function buildCard(act) {
  var tipo = act.t || 'fab';
  var cls = 'act-card ' + tipo;
  if (act.u) cls += ' urg';
  var typeLabel = TIPO_LABEL[tipo] || tipo.toUpperCase();
  var icon = act.u ? '<span class="urg-icon">⚡</span>' : '';
  var label = _esc(act.l || '').replace(/\n/g, '<br>');
  return `<div class="${cls}">
    <div class="act-type">${icon}${typeLabel}</div>
    <div class="act-label">${label}</div>
  </div>`;
}

function buildCell(activities) {
  if (!activities || !activities.length) {
    return '<td class="cell empty"></td>';
  }
  var cards = activities.map(buildCard).join('');
  return `<td class="cell">${cards}</td>`;
}

function buildDayHeader(label) {
  // label es ej "Lun 04" — separar nombre de fecha
  var parts = String(label).split(' ');
  var dayName = parts[0] || '';
  var dayDate = parts.slice(1).join(' ');
  return `<th class="day-h">
    <div class="day-name">${_esc(dayName)}</div>
    <div class="day-date">${_esc(dayDate)} may</div>
  </th>`;
}

function buildTable(data) {
  var areas = data.areas || {};
  var days = data.days || [];
  var html = '<table class="matriz"><thead><tr>';
  html += '<th class="area-h">ÁREA</th>';
  days.forEach(function(d) {
    html += buildDayHeader(d);
  });
  html += '</tr></thead><tbody>';

  var orden = ['fab1', 'fye2', 'fye3', 'env1', 'env2',
               'micro', 'lib', 'acond', 'entr', 'limp'];
  orden.forEach(function(area) {
    var info = AREA_INFO[area] || {icon: '·', label: area, sub: ''};
    html += `<tr class="row-${area}">`;
    html += `<th class="area-h">
      <span class="area-icon">${info.icon}</span>${_esc(info.label)}
      ${info.sub ? `<div class="area-sub">${_esc(info.sub)}</div>` : ''}
    </th>`;
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
    _semanaActual = (d.rango && d.rango.desde) || desde;
    content.innerHTML = '<div class="matriz-wrap">' + buildTable(d) + '</div>';
    pintarTabsSemana(d.rango && d.rango.desde);
  } catch(e) {
    content.innerHTML = '<div class="loading" style="color:#dc2626">Error red: ' + _esc(e.message) + '</div>';
  }
}

// Genera 4 botones de semana centrados en el lunes actual ± 1 (-1, hoy, +1, +2)
function pintarTabsSemana(lunesActualISO) {
  var tabs = document.getElementById('semanas-tabs');
  if (!tabs) return;
  if (!lunesActualISO) { tabs.innerHTML = ''; return; }
  var d = new Date(lunesActualISO + 'T00:00:00');
  var meses = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
  var html = '';
  // Generar 4 semanas: -1, actual, +1, +2
  for (var offset = -1; offset <= 2; offset++) {
    var dl = new Date(d.getTime());
    dl.setDate(dl.getDate() + offset * 7);
    var dv = new Date(dl.getTime());
    dv.setDate(dv.getDate() + 4);  // viernes
    var iso = dl.toISOString().slice(0, 10);
    var label = `${dl.getDate()}–${dv.getDate()} ${meses[dl.getMonth()]}`;
    var num = (offset === -1) ? '0' : (offset === 0 ? '1' : (offset === 1 ? '2' : '3'));
    var active = (offset === 0) ? ' active' : '';
    html += `<button class="semana${active}" onclick="cargarSemana('${iso}')">Sem · ${label}</button>`;
  }
  // Botón "← Sem ant." y "Sem sig. →" extras
  html += `<button class="semana" onclick="cambiarSemana(-1)" title="Semana anterior">←</button>`;
  html += `<button class="semana" onclick="cambiarSemana(1)" title="Semana siguiente">→</button>`;
  html += `<button class="semana" onclick="irHoy()" style="background:#1e293b;color:#fff;border-color:#1e293b">📅 Hoy</button>`;
  tabs.innerHTML = html;
}

function cambiarSemana(offset) {
  if (!_semanaActual) return;
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
