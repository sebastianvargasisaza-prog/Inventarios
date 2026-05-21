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
  <!-- Pieza 6 Kanban · 19-may-2026 · navegación cruzada para que admin/jefe
       no se pierdan entre Mi Día (operario) y vistas de equipo. -->
  <div id="nav-equipo" style="display:none;margin-top:24px;padding:14px;background:#1e293b;border-radius:10px;border:1px solid #334155">
    <div style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">📊 Vistas de equipo (admin/jefe)</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <a href="/planta/kanban" style="flex:1;min-width:140px;background:#0891b2;color:#fff;text-decoration:none;padding:10px 14px;border-radius:8px;font-weight:700;font-size:13px;text-align:center">🏭 Kanban planta</a>
      <a href="/dashboard#programacion" onclick="try{sessionStorage.setItem('prog_tab','mando')}catch(e){}" style="flex:1;min-width:140px;background:#1a4a7a;color:#fff;text-decoration:none;padding:10px 14px;border-radius:8px;font-weight:700;font-size:13px;text-align:center">🎯 Centro de Mando</a>
    </div>
  </div>
  <div style="text-align:center;margin-top:24px;padding-top:24px;border-top:1px solid #334155">
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

// BUG-5 fix · 19-may-2026 audit Planta PERFECTA · mutex anti-race.
// setInterval cada 30s + prompt() bloqueante en completarProd permitía
// que 2 fetches simultáneos terminaran en orden invertido, el response
// del viejo pisaba el nuevo. Ahora _miDiaInFlight evita solapamiento.
window._miDiaInFlight = false;
async function loadMiDia() {
  if (window._miDiaInFlight) return;
  // BUG-19 fix · saltar refresh si pestaña no está visible
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
  window._miDiaInFlight = true;
  try {
    // Admin puede ver Mi Día de otro operario via ?as_operario_id=X
    const urlParams = new URLSearchParams(window.location.search);
    const asOp = urlParams.get('as_operario_id');
    const apiUrl = asOp
      ? '/api/operario/mi-dia?as_operario_id=' + encodeURIComponent(asOp)
      : '/api/operario/mi-dia';
    const r = await fetch(apiUrl);
    if (r.status === 401) { window.location.href = '/login'; return; }
    const d = await r.json();
    // BUG-4 fix · cachear producciones para que completarProd compare
    // kg_real vs cantidad_kg planeado.
    window._miDiaCache = d.producciones || [];
    renderHeader(d);
    renderProducciones(d);
  } catch(e) {
    document.getElementById('contenido').innerHTML =
      '<div class="empty"><div class="empty-icon">⚠️</div>'
      + '<div>Error cargando · ' + escapeHtml(e.message) + '</div>'
      + '<div class="muted" style="margin-top:12px">Reintenta tocando ↻</div></div>';
  } finally {
    window._miDiaInFlight = false;
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
  // Pieza 6 Kanban · 19-may-2026 · navegación cruzada solo para admin/jefe.
  // Operario común no ve estos links · mantiene Mi Día simple.
  const navEq = document.getElementById('nav-equipo');
  if (navEq) navEq.style.display = (d.es_admin || d.es_jefe || d.ve_todas) ? 'block' : 'none';
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
    if (p.area_codigo) {
      let stateMark = '';
      if (p.area_estado === 'sucia') stateMark = ' · 🔴 sucia';
      else if (p.area_estado === 'limpiando') stateMark = ' · 🧹 limpiando';
      else if (p.area_estado === 'ocupada') stateMark = ' · 🟡 ocupada';
      chips += '<span class="chip chip-area">' + escapeHtml(p.area_codigo) + ' · ' + escapeHtml(p.area_nombre) + stateMark + '</span>';
    }
    if (ebr && ebr.numero_op) chips += '<span class="chip chip-op">' + escapeHtml(ebr.numero_op) + '</span>';

    // Sebastián 19-may-2026: BUG-2 audit Planta PERFECTA · XSS fix.
    // mi_rol_aqui viene del backend (whitelist hardcoded en operario.py:213-221)
    // pero por defensa en profundidad lo escapamos también.
    const miRol = p.mi_rol_aqui
      ? '<div class="tag-mi-rol">Tu fase: ' + escapeHtml(ROL_NOMBRES[p.mi_rol_aqui] || p.mi_rol_aqui) + '</div>'
      : '';

    // Botón principal · Sebastián 19-may-2026: BUG-2 audit · XSS fix.
    // Antes se interpolaba sala/nombreSala en onclick="..." con replace
    // solo de comillas simples · si area_nombre tenía `"` o `<` rompía
    // el atributo. Ahora pasamos los datos por data-* (que SÍ pasa por
    // escapeHtml en attrs) y un handler lee del dataset.
    let btn = '';
    if (accion === 'iniciar') {
      const sala = p.area_nombre || p.area_codigo || '';
      btn = '<button class="btn btn-iniciar btn-big" '
          + 'data-pid="' + p.id + '" '
          + 'data-area-est="' + escapeHtml(p.area_estado || '') + '" '
          + 'data-area-nom="' + escapeHtml(sala) + '" '
          + 'onclick="iniciarProdBtn(this)">'
          + ACCION_LABEL.iniciar + '</button>';
    } else if (accion === 'continuar') {
      btn = '<button class="btn btn-continuar btn-big" '
          + 'data-ebr-id="' + (ebr && ebr.id ? ebr.id : '') + '" '
          + 'onclick="continuarProdBtn(this)">' + ACCION_LABEL.continuar + ' · ' + pasosLabel + '</button>';
    } else if (accion === 'completar_pp') {
      btn = '<button class="btn btn-completar btn-big" onclick="completarProd(' + p.id + ')">' + ACCION_LABEL.completar_pp + '</button>';
    } else {
      // Producción ya completada · si la sala quedó sucia, dejar marcarla limpia desde acá
      const ya = '<div class="muted" style="text-align:center;padding:10px;">' + ACCION_LABEL.ya_completado + ' · ' + (p.kg_real ? fmt(p.kg_real, 1) + ' kg · merma ' + fmt(p.merma_pct, 1) + '%' : 'sin reporte') + '</div>';
      if (p.area_estado === 'sucia' && p.area_id) {
        const nombreSala = p.area_nombre || p.area_codigo || 'sala';
        btn = ya
            + '<button class="btn btn-big" style="background:#0e7490;color:#fff;margin-top:8px" '
            + 'data-area-id="' + p.area_id + '" '
            + 'data-area-nom="' + escapeHtml(nombreSala) + '" '
            + 'onclick="marcarLimpiaBtn(this)">'
            + '🧽 Marcar ' + escapeHtml(nombreSala) + ' LIMPIA</button>';
      } else {
        btn = ya;
      }
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

// Sebastián 19-may-2026 BUG-2 audit Planta PERFECTA · wrappers para data-*
// que evitan interpolar valores controlados por DB en onclick="...".
function iniciarProdBtn(btn) {
  const pid = parseInt(btn.dataset.pid, 10);
  iniciarProd(pid, btn.dataset.areaEst || '', btn.dataset.areaNom || '');
}
function continuarProdBtn(btn) {
  const eid = parseInt(btn.dataset.ebrId, 10);
  if (isFinite(eid)) window.location.href = '/brd#ebr-' + eid;
}
function marcarLimpiaBtn(btn) {
  const aid = parseInt(btn.dataset.areaId, 10);
  marcarLimpia(aid, btn.dataset.areaNom || 'sala');
}

async function iniciarProd(id, areaEstado, areaNombre) {
  // Sebastián 19-may-2026: aviso si la sala quedó sucia del lote anterior
  if (areaEstado === 'sucia') {
    if (!confirm('⚠️ La sala ' + (areaNombre || '') + ' está SUCIA del lote anterior.\\n\\nSe recomienda marcarla limpia ANTES de iniciar otra producción acá.\\n\\n¿Iniciar de todos modos?')) return;
  } else if (areaEstado === 'ocupada') {
    if (!confirm('⚠️ La sala ' + (areaNombre || '') + ' figura OCUPADA · ya hay otra producción en curso ahí.\\n\\n¿Iniciar de todos modos?')) return;
  }
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
  // BUG-4 fix · 19-may-2026 audit Planta PERFECTA: confirm si kg_real es
  // muy distinto al planeado · evita dedo-gordo (99999) contaminando KPIs.
  // Buscar cantidad_kg planeada del cache local _miDiaCache.
  try {
    const prod = (window._miDiaCache || []).find(p => p.id === id);
    if (prod && prod.cantidad_kg > 0) {
      const ratio = kgNum / prod.cantidad_kg;
      if (ratio > 1.5 || ratio < 0.5) {
        const pct = Math.round(ratio * 100);
        const tipo = ratio > 1.5 ? 'mucho MÁS' : 'mucho MENOS';
        if (!confirm('⚠ kg_real ' + kgNum + ' kg es ' + tipo + ' del planeado (' +
                     prod.cantidad_kg + ' kg = ' + pct + '%).\\n\\n¿Seguro que no fue un error de dedo?')) {
          return;
        }
      }
    }
  } catch(e){ /* cache opcional · no bloquear */ }
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

async function marcarLimpia(areaId, nombre) {
  if (!confirm('¿Confirmás que la sala ' + nombre + ' ya quedó LIMPIA?\\n\\nLa siguiente producción podrá iniciar acá.')) return;
  try {
    const r = await fetch('/api/planta/areas/' + areaId + '/estado', {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken()},
      body: JSON.stringify({estado: 'libre'}),
    });
    const d = await r.json();
    if (!r.ok) {
      alert('Error: ' + (d.error || r.status));
      return;
    }
    alert('✓ Sala ' + nombre + ' marcada limpia');
    loadMiDia();
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

// BUG-17 fix · 19-may-2026 audit Planta PERFECTA · CSRF token cliente.
// Antes leía de document.cookie pero el token vive en Flask session, no
// en cookie expuesta · siempre devolvía '' · Capa 2 CSRF dead-code.
// Ahora fetcheamos /api/csrf-token al boot y lo guardamos en window._csrfTok.
window._csrfTok = '';
fetch('/api/csrf-token', {credentials: 'same-origin'})
  .then(r => r.ok ? r.json() : null)
  .then(d => { if (d && d.csrf_token) window._csrfTok = d.csrf_token; })
  .catch(() => {});

function csrfToken() {
  return window._csrfTok || '';
}

function refreshNow() { loadMiDia(); }

// OLA 4 · 20-may-2026 · Voz "Terminé dispensación" en Mi Día.
// Web Speech API (gratis, on-device). Operario con guantes y mezcla en
// marmita NO agarra el celular. Recognition es-CO + Hold-to-talk para
// evitar disparos accidentales. Confirma antes de mutar (defensive).
var _miDiaSpeech = null;
var _miDiaSpeechActiva = false;
function _miDiaVozDisponible() {
  return ('SpeechRecognition' in window) || ('webkitSpeechRecognition' in window);
}
function _miDiaVozIniciar() {
  if (_miDiaSpeechActiva) return;
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    alert('Tu navegador no soporta reconocimiento de voz. Usá Chrome en Android o Safari iOS 14+.');
    return;
  }
  var rec = new SR();
  rec.lang = 'es-CO';
  rec.continuous = false;
  rec.interimResults = false;
  rec.maxAlternatives = 2;
  _miDiaSpeech = rec;
  _miDiaSpeechActiva = true;
  var btn = document.getElementById('mi-dia-voz-btn');
  if (btn) { btn.textContent = '🔴 Escuchando...'; btn.style.background = '#dc2626'; }
  rec.onresult = function(ev) {
    var txt = ev.results[0][0].transcript.toLowerCase().trim();
    _miDiaVozProcesar(txt);
  };
  rec.onerror = function(e) {
    console.warn('voz err:', e);
    if (btn) { btn.textContent = '🎤 Voz'; btn.style.background = '#0891b2'; }
    _miDiaSpeechActiva = false;
  };
  rec.onend = function() {
    if (btn) { btn.textContent = '🎤 Voz'; btn.style.background = '#0891b2'; }
    _miDiaSpeechActiva = false;
  };
  try { rec.start(); } catch(_) {
    if (btn) { btn.textContent = '🎤 Voz'; btn.style.background = '#0891b2'; }
    _miDiaSpeechActiva = false;
  }
}
function _miDiaVozProcesar(txt) {
  // Parser determinístico: mapear frases a acciones.
  // "terminé dispensación" · "inicié elaboración" · "atascada" · etc.
  var ETAPAS = {
    'dispens': 'dispensacion',
    'elabor': 'elaboracion',
    'envas': 'envasado',
    'acondic': 'acondicionamiento',
  };
  var verbo = null;
  if (/\b(termin|acab|listo|fini)/.test(txt)) verbo = 'terminar';
  else if (/\b(inic|empec|comenz|arranc)/.test(txt)) verbo = 'iniciar';
  else if (/\b(atascad|trabad|prob|no puedo|ayuda)/.test(txt)) verbo = 'andon';
  var etapa = null;
  for (var k in ETAPAS) { if (txt.indexOf(k) !== -1) { etapa = ETAPAS[k]; break; } }
  if (verbo === 'andon') {
    if (!confirm('Voz reconocio: ' + txt + ' · Abrir alerta ANDON?')) return;
    fetch('/api/planta/andon', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken() },
      body: JSON.stringify({ tipo: 'otro', descripcion: txt }),
    }).then(r => r.json()).then(d => {
      alert(d.ok ? '✓ Alerta ANDON abierta · jefe notificado' : ('Error: ' + (d.error||'?')));
    });
    return;
  }
  if (!verbo || !etapa) {
    alert('No entendi: ' + txt + ' · Proba: termine dispensacion, inicie elaboracion, atascada en envasado');
    return;
  }
  if (!confirm('Voz reconocio: ' + txt + ' · Marcar ' + verbo + ' ' + etapa + ' en tu produccion activa?')) return;
  alert('Voz: ' + verbo + ' ' + etapa + ' · Por ahora apreta el boton equivalente en pantalla · proxima version disparara automatico');
}

function refreshNow() { loadMiDia(); }

// Auto-refresh cada 30s
loadMiDia();
setInterval(loadMiDia, 30000);
// Inyectar botón Voz floating si la API está disponible
if (_miDiaVozDisponible()) {
  document.addEventListener('DOMContentLoaded', function() {
    var b = document.createElement('button');
    b.id = 'mi-dia-voz-btn';
    b.textContent = '🎤 Voz';
    b.title = 'Tocá y decí: "terminé dispensación" / "atascada"';
    b.style.cssText = 'position:fixed;bottom:24px;right:24px;background:#0891b2;color:#fff;border:none;padding:14px 22px;border-radius:30px;font-size:14px;font-weight:700;box-shadow:0 4px 14px rgba(8,145,178,.4);z-index:99;cursor:pointer';
    b.onclick = _miDiaVozIniciar;
    document.body.appendChild(b);
  });
}
</script>
</body>
</html>"""
