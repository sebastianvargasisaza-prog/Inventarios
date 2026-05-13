"""Template HTML mobile-first para vista del operario · 13-may-2026.

Diseño:
- Mobile-first · botones grandes (min 48x48px) · touch-friendly
- Auto-refresh cada 30s vía fetch (no recarga completa)
- Sin JS frameworks · vanilla JS inline para mínima latencia
- Tipografía generosa para visibilidad en planta (poca luz, gloves)
- Estados con color: gris=pendiente, amarillo=en proceso, verde=hecho
"""

def render_operario():
    return """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="theme-color" content="#0f172a">
<title>Mi Día · Planta</title>
<style>
* { box-sizing: border-box; }
html,body { margin:0; padding:0; background:#0f172a; color:#f1f5f9;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 16px; -webkit-tap-highlight-color: transparent; }
header { background:#1e293b; padding:16px; position:sticky; top:0; z-index:10;
         border-bottom:1px solid #334155; }
h1 { font-size:20px; margin:0 0 4px 0; font-weight:600; }
.muted { color:#94a3b8; font-size:14px; }
.warn { color:#fbbf24; }
.good { color:#22c55e; }
.crit { color:#ef4444; }
main { padding:16px; padding-bottom:80px; max-width:600px; margin:0 auto; }
.card { background:#1e293b; border-radius:16px; padding:16px; margin-bottom:16px;
        border-left:6px solid #475569; box-shadow:0 2px 8px rgba(0,0,0,0.3); }
.card.iniciar { border-left-color:#3b82f6; }
.card.continuar { border-left-color:#f59e0b; }
.card.completar_pp { border-left-color:#10b981; }
.card.ya_completado { border-left-color:#64748b; opacity:0.6; }
.card-title { font-size:18px; font-weight:700; margin-bottom:4px; }
.card-meta { font-size:14px; color:#cbd5e1; margin-bottom:8px; }
.chip { display:inline-block; background:#334155; color:#cbd5e1; padding:3px 10px;
        border-radius:12px; font-size:12px; margin-right:6px; margin-bottom:4px;
        font-family: ui-monospace, SFMono-Regular, monospace; }
.chip-rol { background:#1e40af; color:#dbeafe; }
.chip-area { background:#365314; color:#d9f99d; }
.chip-op { background:#581c87; color:#e9d5ff; }
.btn { display:inline-block; padding:14px 20px; min-height:50px; min-width:120px;
       border-radius:12px; border:none; font-size:16px; font-weight:600;
       cursor:pointer; transition: transform 0.05s, opacity 0.15s;
       -webkit-appearance: none; appearance: none; }
.btn:active { transform: scale(0.97); }
.btn-iniciar { background:#3b82f6; color:white; }
.btn-continuar { background:#f59e0b; color:#1e293b; }
.btn-completar { background:#10b981; color:white; }
.btn-secondary { background:#334155; color:#cbd5e1; }
.btn-big { width:100%; padding:18px; font-size:18px; min-height:60px; margin-top:8px; }
.empty { text-align:center; padding:40px 20px; color:#64748b; }
.empty-icon { font-size:48px; margin-bottom:12px; opacity:0.5; }
.estado-badge { display:inline-block; padding:4px 10px; border-radius:8px;
                font-size:13px; font-weight:600; margin-bottom:8px; }
.estado-pendiente { background:#475569; color:#e2e8f0; }
.estado-en_proceso { background:#854d0e; color:#fef3c7; }
.estado-completado { background:#065f46; color:#d1fae5; }
.progreso { background:#334155; height:6px; border-radius:3px; overflow:hidden;
            margin:8px 0; }
.progreso-fill { background:#10b981; height:100%; transition: width 0.3s; }
.loading { text-align:center; padding:40px; color:#64748b; }
.loading::after { content: "..."; animation: dots 1.5s infinite; }
@keyframes dots { 0%,20% { content:"."; } 40% { content:".."; } 60%,100% { content:"..."; } }
.fab { position:fixed; bottom:16px; right:16px; background:#334155; color:white;
       width:48px; height:48px; border-radius:24px; display:flex;
       align-items:center; justify-content:center; cursor:pointer; font-size:24px;
       box-shadow:0 4px 12px rgba(0,0,0,0.4); z-index:5; border:none; }
.tag-mi-rol { background:#1e40af; color:white; padding:6px 12px; border-radius:8px;
              font-size:14px; font-weight:600; margin-bottom:8px; display:inline-block; }
.banner-msg { background:#7c2d12; color:#fed7aa; padding:12px 16px; border-radius:12px;
              margin-bottom:16px; font-size:14px; }
@media (max-width: 380px) {
  h1 { font-size:18px; }
  .card-title { font-size:16px; }
  .btn { font-size:15px; }
}
</style>
</head>
<body>
<header>
  <h1 id="hdr-saludo">Cargando…</h1>
  <div class="muted" id="hdr-meta"></div>
</header>
<main>
  <div id="contenido" class="loading">Cargando tu día</div>
  <div style="text-align:center;margin-top:32px;padding-top:24px;border-top:1px solid #334155">
    <a href="/inventarios" style="color:#94a3b8;font-size:13px;text-decoration:none">
      &larr; Ver inventario completo de Planta
    </a>
  </div>
</main>
<button class="fab" onclick="refreshNow()" title="Refrescar">↻</button>

<script>
const ROL_NOMBRES = {
  'dispensacion': 'Dispensación',
  'elaboracion': 'Elaboración',
  'envasado': 'Envasado',
  'acondicionamiento': 'Acondicionamiento',
};
const ACCION_LABEL = {
  'iniciar': '▶ Iniciar producción',
  'continuar': '→ Continuar paso',
  'completar_pp': '✓ Reportar cantidad final',
  'ya_completado': '✓ Completado',
};

function escapeHtml(s) {
  if (s === null || s === undefined) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}

function fmt(n, d=0) {
  if (n === null || n === undefined) return '—';
  return Number(n).toLocaleString('es-CO', {maximumFractionDigits: d});
}

async function loadMiDia() {
  try {
    const r = await fetch('/api/operario/mi-dia');
    if (r.status === 401) { window.location.href = '/login'; return; }
    const d = await r.json();
    renderHeader(d);
    renderProducciones(d);
  } catch(e) {
    document.getElementById('contenido').innerHTML =
      '<div class="empty"><div class="empty-icon">⚠️</div>'
      + '<div>Error cargando · ' + escapeHtml(e.message) + '</div>'
      + '<div class="muted" style="margin-top:12px">Reintenta tocando ↻</div></div>';
  }
}

function renderHeader(d) {
  const saludo = d.nombre ? 'Hola, ' + d.nombre.split(' ')[0] : 'Hola';
  document.getElementById('hdr-saludo').textContent = saludo;
  const partes = [];
  if (d.rol_predeterminado) partes.push(ROL_NOMBRES[d.rol_predeterminado] || d.rol_predeterminado);
  if (d.ve_todas) partes.push(d.es_admin ? 'admin · ves todas' : 'jefe · ves todas');
  partes.push(d.fecha);
  document.getElementById('hdr-meta').textContent = partes.join(' · ');
}

function renderProducciones(d) {
  const div = document.getElementById('contenido');
  div.classList.remove('loading');

  if (d.mensaje) {
    div.innerHTML = '<div class="banner-msg">' + escapeHtml(d.mensaje) + '</div>';
    return;
  }

  const prods = d.producciones || [];
  if (!prods.length) {
    div.innerHTML = '<div class="empty">'
      + '<div class="empty-icon">📋</div>'
      + '<div style="font-size:18px;margin-bottom:8px">Sin producciones hoy</div>'
      + '<div class="muted">Ni ayer · ni mañana · descansa</div>'
      + '</div>';
    return;
  }

  let html = '';
  prods.forEach(p => {
    const accion = p.siguiente_accion;
    const cls = 'card ' + accion;
    const ebr = p.ebr;
    const pasosLabel = ebr
      ? (ebr.pasos_total - ebr.pasos_pendientes) + '/' + ebr.pasos_total + ' pasos'
      : '';

    let chips = '';
    if (p.area_codigo) chips += '<span class="chip chip-area">' + escapeHtml(p.area_codigo) + ' · ' + escapeHtml(p.area_nombre) + '</span>';
    if (ebr && ebr.numero_op) chips += '<span class="chip chip-op">' + escapeHtml(ebr.numero_op) + '</span>';

    const miRol = p.mi_rol_aqui
      ? '<div class="tag-mi-rol">Tu fase: ' + (ROL_NOMBRES[p.mi_rol_aqui] || p.mi_rol_aqui) + '</div>'
      : '';

    // Botón principal
    let btn = '';
    if (accion === 'iniciar') {
      btn = '<button class="btn btn-iniciar btn-big" onclick="iniciarProd(' + p.id + ')">' + ACCION_LABEL.iniciar + '</button>';
    } else if (accion === 'continuar') {
      btn = '<button class="btn btn-continuar btn-big" onclick="window.location.href=\\'/brd#ebr-' + (ebr && ebr.id) + '\\'">' + ACCION_LABEL.continuar + ' · ' + pasosLabel + '</button>';
    } else if (accion === 'completar_pp') {
      btn = '<button class="btn btn-completar btn-big" onclick="completarProd(' + p.id + ')">' + ACCION_LABEL.completar_pp + '</button>';
    } else {
      btn = '<div class="muted" style="text-align:center;padding:12px;">' + ACCION_LABEL.ya_completado + ' · ' + (p.kg_real ? fmt(p.kg_real, 1) + ' kg · merma ' + fmt(p.merma_pct, 1) + '%' : 'sin reporte') + '</div>';
    }

    let progreso = '';
    if (ebr && ebr.pasos_total > 0) {
      const pct = Math.round((ebr.pasos_total - ebr.pasos_pendientes) / ebr.pasos_total * 100);
      progreso = '<div class="progreso"><div class="progreso-fill" style="width:' + pct + '%"></div></div>';
    }

    html += '<div class="' + cls + '">'
      + miRol
      + '<div class="card-title">' + escapeHtml(p.producto) + '</div>'
      + '<div class="card-meta">' + fmt(p.cantidad_kg, 1) + ' kg · ' + escapeHtml(p.fecha_programada) + '</div>'
      + chips
      + progreso
      + btn
      + '</div>';
  });
  div.innerHTML = html;
}

async function iniciarProd(id) {
  if (!confirm('¿Iniciar producción ' + id + '?\\nEsto descuenta MPs del inventario y crea el lote.')) return;
  try {
    const r = await fetch('/api/programacion/programar/' + id + '/iniciar', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken()},
      body: '{}',
    });
    const d = await r.json();
    if (!r.ok) {
      alert('Error: ' + (d.error || r.status) + (d.codigo ? ' (' + d.codigo + ')' : ''));
      return;
    }
    if (d.brd_ebr && d.brd_ebr.numero_op) {
      alert('✓ Iniciado · OP ' + d.brd_ebr.numero_op + ' · ' + d.brd_ebr.pasos_clonados + ' pasos creados');
    } else {
      alert('✓ Producción iniciada');
    }
    loadMiDia();
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

async function completarProd(id) {
  const kg = prompt('Reportar kg REAL producidos:');
  if (!kg) return;
  const kgNum = parseFloat(kg);
  if (!isFinite(kgNum) || kgNum <= 0) { alert('kg inválido'); return; }
  const unidades = prompt('Unidades reales (opcional · enter para saltar):');
  const body = {kg_real: kgNum};
  if (unidades) body.unidades_real = parseInt(unidades);
  try {
    const r = await fetch('/api/programacion/programar/' + id + '/completar', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken()},
      body: JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok) {
      alert('Error: ' + (d.error || r.status));
      return;
    }
    alert('✓ Completado · merma ' + (d.merma_pct != null ? d.merma_pct.toFixed(1) + '%' : '—'));
    loadMiDia();
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

function csrfToken() {
  // Lee cookie csrf si existe, sino vacío (defense-in-depth)
  const m = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/);
  return m ? decodeURIComponent(m[1]) : '';
}

function refreshNow() { loadMiDia(); }

// Auto-refresh cada 30s
loadMiDia();
setInterval(loadMiDia, 30000);
</script>
</body>
</html>"""
