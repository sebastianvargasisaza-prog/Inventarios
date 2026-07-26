"""Vista comparativa · cronograma de Alejandro vs lo que está en Calendar.

Muestra 3 secciones:
  1. Matches (verde) · ambos coinciden
  2. En Alejandro pero falta en Calendar (rojo) · cargar
  3. En Calendar pero Alejandro no mencionó (amarillo) · revisar
"""

CRONOGRAMA_COMPARAR_HTML = r'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🔍 Cronograma · Alejandro vs Calendar</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f5; color: #1f2937; padding: 20px;
  }
  .container { max-width: 1400px; margin: 0 auto; }
  h1 { font-size: 24px; margin: 0 0 4px 0; color: var(--cx-text); }
  .subtitle { font-size: 13px; color: var(--cx-text-mute); }
  .nav { font-size: 12px; margin: 8px 0 18px 0; }
  .nav a { color: #2B7A78; text-decoration: none; margin-right: 14px; }

  .resumen {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px; margin-bottom: 20px;
  }
  .pill {
    background: var(--cx-card); border: 1px solid var(--cx-border); border-radius: 10px;
    padding: 14px 16px; text-align: center;
  }
  .pill .num { font-size: 28px; font-weight: 800; line-height: 1; }
  .pill .lbl { font-size: 11px; color: var(--cx-text-mute); text-transform: uppercase;
                letter-spacing: 0.4px; margin-top: 6px; }
  .pill.ok      { border-left: 4px solid var(--cx-success); }
  .pill.ok .num { color: var(--cx-success-text); }
  .pill.warn    { border-left: 4px solid var(--cx-warn); }
  .pill.warn .num { color: var(--cx-warn-text); }
  .pill.err     { border-left: 4px solid var(--cx-danger); }
  .pill.err .num { color: var(--cx-danger-text); }
  .pill.info    { border-left: 4px solid var(--cx-info); }
  .pill.info .num { color: var(--cx-info-text); }

  .seccion {
    background: var(--cx-card); border: 1px solid var(--cx-border); border-radius: 10px;
    margin-bottom: 18px; overflow: hidden;
  }
  .seccion-header {
    padding: 14px 18px; font-weight: 700; font-size: 15px;
    border-bottom: 1px solid var(--cx-border);
  }
  .seccion.ok .seccion-header { background: var(--cx-success-pale); color: var(--cx-success-text);
    border-bottom-color: #bbf7d0; }
  .seccion.err .seccion-header { background: var(--cx-danger-pale); color: var(--cx-danger-text);
    border-bottom-color: #fecaca; }
  .seccion.warn .seccion-header { background: var(--cx-warn-pale); color: var(--cx-warn-text);
    border-bottom-color: #fde68a; }
  .seccion-body { padding: 0; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--cx-border-soft); }
  th { background: var(--cx-bg-alt); font-weight: 600; color: var(--cx-text-soft);
       font-size: 11px; text-transform: uppercase; letter-spacing: 0.4px; }
  tr:last-child td { border-bottom: none; }
  tr:hover { background: #fafbfc; }
  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 600;
  }
  .badge.urg { background: var(--cx-danger-pale); color: var(--cx-danger-text); border: 1px solid #fca5a5; }
  .badge.area { background: var(--cx-info-pale); color: var(--cx-info-text); }
  .badge.area-mismatch { background: var(--cx-warn-pale); color: var(--cx-warn-text); }
  .empty {
    padding: 30px; text-align: center; color: var(--cx-text-faint); font-style: italic;
  }
  .spinner {
    display: inline-block; width: 14px; height: 14px;
    border: 2px solid var(--cx-border); border-top-color: var(--cx-info);
    border-radius: 50%; animation: spin 0.8s linear infinite;
    margin-right: 8px; vertical-align: middle;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .hint-otra-fecha { color: var(--cx-warn-text); font-size: 11px; margin-top: 2px; }
</style>
</head>
<body>
<div class="container">
  <h1>🔍 Comparación · Alejandro vs Calendar</h1>
  <div class="subtitle">
    Cronograma que Alejandro mandó (mayo 2026) cruzado con producciones reales en
    <code>produccion_programada</code> (Calendar sync).
  </div>
  <div class="nav">
    <a href="/programacion-areas">← Volver al cronograma</a>
    <a href="/asignar-areas">📌 Asignar áreas</a>
    <a href="/planta">Planta</a>
    <a href="https://animuslab.neocities.org/programacion_mayo_areas" target="_blank">HTML original de Alejandro ↗</a>
  </div>

  <div id="resumen" class="resumen">
    <div class="pill"><div class="num">…</div><div class="lbl">cargando</div></div>
  </div>

  <div id="content">
    <div class="empty"><span class="spinner"></span> Cargando comparación…</div>
  </div>
</div>

<script>
function _esc(s){
  return String(s||'').replace(/[&<>"']/g, ch => (
    {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]
  ));
}

var AREA_NAMES = {
  'PROD1': 'Producción 1', 'PROD2': 'Producción 2',
  'PROD3': 'Producción 3', 'PROD4': 'Producción 4',
  'ENV1':  'Envasado 1',
};
function fmtArea(cod) { return AREA_NAMES[cod] || cod || '-'; }

function fmtFecha(iso) {
  if (!iso) return '-';
  var d = new Date(iso + 'T00:00:00');
  var dias = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];
  return dias[d.getDay()] + ' ' + d.getDate() + '/' + (d.getMonth()+1);
}

function buildResumen(r) {
  var html = '';
  html += '<div class="pill info"><div class="num">' + r.total_alejandro + '</div><div class="lbl">Alejandro programó</div></div>';
  html += '<div class="pill info"><div class="num">' + r.total_calendar + '</div><div class="lbl">En Calendar</div></div>';
  html += '<div class="pill ok"><div class="num">' + r.matches_completos + '</div><div class="lbl">✓ Match completo</div></div>';
  if (r.matches_fecha_distinto_area > 0) {
    html += '<div class="pill warn"><div class="num">' + r.matches_fecha_distinto_area + '</div><div class="lbl">⚠ Distinta área</div></div>';
  }
  html += '<div class="pill err"><div class="num">' + r.falta_en_calendar + '</div><div class="lbl">⊗ Falta cargar</div></div>';
  html += '<div class="pill warn"><div class="num">' + r.extra_en_calendar + '</div><div class="lbl">+ Calendar tiene extra</div></div>';
  return html;
}

function buildMatches(items) {
  if (!items.length) {
    return '<div class="empty">Sin matches todavía. Cargá producciones en Calendar para ver coincidencias.</div>';
  }
  var html = '<table><thead><tr>';
  html += '<th>Fecha</th><th>Producto Alejandro</th><th>Producto Calendar</th>';
  html += '<th>Área Alejandro</th><th>Área Calendar</th><th>Estado</th>';
  html += '</tr></thead><tbody>';
  items.forEach(function(it) {
    var area_match_html = it.area_match
      ? '<span class="badge area">' + _esc(fmtArea(it.area_calendar)) + '</span>'
      : '<span class="badge area-mismatch">⚠ ' + _esc(fmtArea(it.area_calendar)) + '</span>';
    html += '<tr>';
    html += '<td><b>' + _esc(fmtFecha(it.fecha)) + '</b><br><small style="color:var(--cx-text-faint)">' + _esc(it.fecha) + '</small></td>';
    html += '<td>' + _esc(it.producto_alejandro);
    if (it.urgente_alejandro) html += ' <span class="badge urg">⚡ URGENTE</span>';
    html += '</td>';
    html += '<td>' + _esc(it.producto_calendar) + '</td>';
    html += '<td>' + _esc(fmtArea(it.area_alejandro)) + '</td>';
    html += '<td>' + area_match_html + '</td>';
    html += '<td><span class="badge area">' + _esc(it.estado) + '</span></td>';
    html += '</tr>';
  });
  html += '</tbody></table>';
  return html;
}

function buildFaltaEnCalendar(items) {
  if (!items.length) {
    return '<div class="empty">✓ Todo lo de Alejandro está en Calendar.</div>';
  }
  var html = '<table><thead><tr>';
  html += '<th>Fecha</th><th>Producto</th><th>Área</th><th>Detalle</th>';
  html += '</tr></thead><tbody>';
  items.forEach(function(it) {
    var detalle = '';
    if (it.match_otra_fecha) {
      detalle = '<span class="hint-otra-fecha">⚠ Calendar sí lo tiene pero el ' + _esc(fmtFecha(it.match_otra_fecha)) + ' (cambio de fecha?) - "' + _esc(it.producto_calendar_otra_fecha || '') + '"</span>';
    } else {
      detalle = '<span style="color:var(--cx-text-mute)">No existe en Calendar · cargar</span>';
    }
    html += '<tr>';
    html += '<td><b>' + _esc(fmtFecha(it.fecha)) + '</b><br><small style="color:var(--cx-text-faint)">' + _esc(it.fecha) + '</small></td>';
    html += '<td>' + _esc(it.producto);
    if (it.urgente) html += ' <span class="badge urg">⚡ URGENTE</span>';
    html += '</td>';
    html += '<td>' + _esc(fmtArea(it.area)) + '</td>';
    html += '<td>' + detalle + '</td>';
    html += '</tr>';
  });
  html += '</tbody></table>';
  return html;
}

function buildExtraEnCalendar(items) {
  if (!items.length) {
    return '<div class="empty">✓ Calendar no tiene producciones que Alejandro no haya mencionado.</div>';
  }
  var html = '<table><thead><tr>';
  html += '<th>Fecha</th><th>Producto</th><th>Área</th><th>Estado</th><th>Observaciones</th>';
  html += '</tr></thead><tbody>';
  items.forEach(function(it) {
    html += '<tr>';
    html += '<td><b>' + _esc(fmtFecha(it.fecha)) + '</b><br><small style="color:var(--cx-text-faint)">' + _esc(it.fecha) + '</small></td>';
    html += '<td>' + _esc(it.producto || '-') + '</td>';
    html += '<td>' + _esc(fmtArea(it.area)) + '</td>';
    html += '<td><span class="badge area">' + _esc(it.estado) + '</span></td>';
    html += '<td style="color:var(--cx-text-mute);font-size:11px">' + _esc((it.observaciones || '').slice(0, 80)) + '</td>';
    html += '</tr>';
  });
  html += '</tbody></table>';
  return html;
}

async function cargar() {
  var content = document.getElementById('content');
  var resumen = document.getElementById('resumen');
  try {
    var r = await fetch('/api/planta/cronograma-comparar-alejandro');
    if (!r.ok) {
      content.innerHTML = '<div class="empty" style="color:var(--cx-danger-text)">Error ' + r.status + '</div>';
      return;
    }
    var d = await r.json();
    resumen.innerHTML = buildResumen(d.resumen);
    var html = '';
    html += '<div class="seccion ok">';
    html += '<div class="seccion-header">✓ Matches · Alejandro y Calendar coinciden (' + d.matches.length + ')</div>';
    html += '<div class="seccion-body">' + buildMatches(d.matches) + '</div>';
    html += '</div>';
    html += '<div class="seccion err">';
    html += '<div class="seccion-header">⊗ Alejandro programó pero Calendar NO tiene (' + d.en_alejandro_no_calendar.length + ')</div>';
    html += '<div class="seccion-body">' + buildFaltaEnCalendar(d.en_alejandro_no_calendar) + '</div>';
    html += '</div>';
    html += '<div class="seccion warn">';
    html += '<div class="seccion-header">+ Calendar tiene pero Alejandro NO mencionó (' + d.en_calendar_no_alejandro.length + ')</div>';
    html += '<div class="seccion-body">' + buildExtraEnCalendar(d.en_calendar_no_alejandro) + '</div>';
    html += '</div>';
    content.innerHTML = html;
  } catch(e) {
    content.innerHTML = '<div class="empty" style="color:var(--cx-danger-text)">Error red: ' + _esc(e.message) + '</div>';
  }
}

cargar();
</script>
</body>
</html>'''
