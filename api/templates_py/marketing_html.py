MARKETING_HTML = r"""<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Marketing - HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:var(--cx-bg);color:var(--cx-text);min-height:100vh;font-size:14px;}
::-webkit-scrollbar{width:6px;height:6px;}::-webkit-scrollbar-track{background:var(--cx-card);}::-webkit-scrollbar-thumb{background:var(--cx-text-soft);border-radius:3px;}

/* ─── Header ─── */
.hdr{background:var(--cx-card);border-bottom:1px solid var(--cx-border);padding:14px 20px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}
.hdr-brand{display:flex;align-items:center;gap:10px;}
.hdr-brand h1{font-size:16px;font-weight:800;color:#fff;}
.hdr-brand span{font-size:11px;color:var(--cx-text-mute);background:var(--cx-bg-alt);padding:2px 8px;border-radius:20px;border:1px solid var(--cx-border);}
.hdr-user{font-size:12px;color:var(--cx-text-mute);}
.hdr-user strong{color:var(--cx-text);}
.back-link{font-size:12px;color:#667eea;text-decoration:none;display:flex;align-items:center;gap:4px;}
.back-link:hover{color:#818cf8;}

/* ─── Tabs ─── */
.tabs-bar{background:var(--cx-card);border-bottom:1px solid var(--cx-border);display:flex;overflow-x:auto;padding:0 20px;}
.tab-btn{padding:12px 20px;font-size:13px;font-weight:600;color:var(--cx-text-mute);border:none;background:none;cursor:pointer;white-space:nowrap;border-bottom:3px solid transparent;transition:.15s;}
.tab-btn:hover{color:var(--cx-primary-text);background:#faf7ff;}
.tab-btn.active{color:var(--cx-primary-text);border-bottom-color:var(--cx-primary);}
.tab-panel{display:none;padding:24px 20px;}
.tab-panel.active{display:block;}

/* ─── Cards & Layout ─── */
.page-title{font-size:18px;font-weight:700;color:var(--cx-text);margin-bottom:4px;}
.page-sub{font-size:12px;color:var(--cx-text-mute);margin-bottom:24px;}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:14px;margin-bottom:24px;}
.kpi-card{background:var(--cx-card);border:1px solid #eef0f2;border-top:3px solid var(--cx-border);border-radius:14px;padding:16px;box-shadow:0 1px 3px rgba(15,23,42,.05);transition:box-shadow .15s,transform .1s;}
.kpi-card:hover{box-shadow:0 8px 20px rgba(15,23,42,.08);transform:translateY(-2px);}
.kpi-label{font-size:11px;color:var(--cx-text-mute);font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;}
.kpi-val{font-size:26px;font-weight:800;color:var(--cx-text);line-height:1;letter-spacing:-.01em;}
.kpi-sub{font-size:11px;color:var(--cx-text-mute);margin-top:5px;}
.kpi-card.green{border-top-color:var(--cx-success);} .kpi-card.green .kpi-val{color:var(--cx-success-text);}
.kpi-card.red{border-top-color:var(--cx-danger);} .kpi-card.red .kpi-val{color:var(--cx-danger-text);}
.kpi-card.blue{border-top-color:var(--cx-info);} .kpi-card.blue .kpi-val{color:var(--cx-info-text);}
.kpi-card.yellow{border-top-color:var(--cx-warn);} .kpi-card.yellow .kpi-val{color:var(--cx-warn-text);}
.kpi-card.purple{border-top-color:var(--cx-primary);} .kpi-card.purple .kpi-val{color:var(--cx-primary-text);}

.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;}
@media(max-width:800px){.grid2,.grid3{grid-template-columns:1fr;}}

.card{background:var(--cx-card);border:1px solid #eef0f2;border-radius:14px;overflow:hidden;box-shadow:0 2px 12px rgba(15,23,42,.05);}
.card-hdr{padding:14px 16px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #f1f2f5;background:#fbfbfd;}
.card-title{font-size:13px;font-weight:800;color:var(--cx-text);letter-spacing:-.01em;}
.card-body{padding:16px;}

/* ─── Table ─── */
.tbl-wrap{overflow-x:auto;}
table{width:100%;border-collapse:collapse;}
th{font-size:10px;font-weight:800;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.5px;padding:11px 14px;text-align:left;background:#fbfbfd;border-bottom:1px solid #eef0f2;}
td{padding:11px 14px;border-bottom:1px solid #f4f4f8;font-size:13px;}
tr:hover td{background:#faf9ff;}
.empty-row td{text-align:center;color:var(--cx-text-mute);padding:32px;}

/* ─── Badges ─── */
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;}
.badge-green{background:var(--cx-success-pale);color:var(--cx-success-text);border:1px solid var(--cx-hairline);}
.badge-blue{background:var(--cx-info-pale);color:var(--cx-info-text);border:1px solid var(--cx-hairline);}
.badge-yellow{background:var(--cx-warn-pale);color:var(--cx-warn-text);border:1px solid var(--cx-hairline);}
.badge-red{background:#2d0000;color:var(--cx-danger-text);border:1px solid var(--cx-danger);}
.badge-gray{background:var(--cx-card);color:var(--cx-text-mute);border:1px solid var(--cx-border);}
.badge-purple{background:var(--cx-primary-soft);color:var(--cx-primary-text);border:1px solid var(--cx-primary-dark);}

/* ─── Buttons ─── */
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:600;transition:.15s;}
.btn-primary{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;}
.btn-primary:hover{opacity:.9;}
.btn-sm{padding:5px 12px;font-size:12px;}
.btn-outline{background:transparent;border:1px solid var(--cx-border);color:var(--cx-text-mute);}
.btn-outline:hover{border-color:var(--cx-text-faint);color:var(--cx-text);}
.btn-danger{background:var(--cx-danger);color:var(--cx-danger-text);}
.btn-danger:hover{background:var(--cx-danger);}
.btn-agent{background:var(--cx-primary-grad);border:none;color:#fff;width:100%;padding:14px;font-size:14px;font-weight:700;border-radius:10px;cursor:pointer;transition:.2s;display:flex;align-items:center;justify-content:center;gap:8px;}
.btn-agent:hover{filter:brightness(1.06);}
.btn-agent.running{opacity:.6;cursor:not-allowed;}

/* ─── Forms ─── */
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;}
.form-row.full{grid-template-columns:1fr;}
.form-group{display:flex;flex-direction:column;gap:4px;}
label{font-size:11px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.4px;}
input,select,textarea{background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:8px;padding:8px 12px;color:var(--cx-text);font-size:13px;width:100%;}
input:focus,select:focus,textarea:focus{outline:none;border-color:#667eea;}
textarea{resize:vertical;min-height:80px;}

/* ─── Modal ─── */
.modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;}
.modal-bg.open{display:flex;}
.modal{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:16px;width:min(600px,95vw);max-height:90vh;overflow-y:auto;padding:24px;}
.modal-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;}
.modal-title{font-size:16px;font-weight:700;color:var(--cx-text);}
.modal-close{background:none;border:none;color:var(--cx-text-mute);cursor:pointer;font-size:20px;padding:4px;}
.modal-close:hover{color:var(--cx-danger-text);}

/* ─── Agent cards ─── */
.agents-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;}
.agent-card{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:14px;padding:20px;}
.agent-icon{font-size:32px;margin-bottom:12px;}
.agent-name{font-size:15px;font-weight:700;color:var(--cx-text);margin-bottom:4px;}
.agent-desc{font-size:12px;color:var(--cx-text-mute);margin-bottom:16px;line-height:1.5;}
.agent-result{margin-top:16px;background:var(--cx-bg-alt);border-radius:8px;padding:14px;font-size:12px;color:var(--cx-text-mute);max-height:240px;overflow-y:auto;display:none;}
.agent-result.show{display:block;}
.agent-result pre{white-space:pre-wrap;word-break:break-word;font-family:'Segoe UI',sans-serif;font-size:12px;}

/* ─── Progress bar ─── */
.progress-bar{background:var(--cx-bg-alt);border-radius:4px;height:8px;overflow:hidden;}
.progress-fill{height:100%;border-radius:4px;background:linear-gradient(90deg,#667eea,#764ba2);transition:width .5s;}

/* ─── Alert ─── */
.alert{padding:12px 16px;border-radius:8px;font-size:13px;margin-bottom:16px;}
.alert-success{background:var(--cx-success-pale);color:var(--cx-success-text);border:1px solid var(--cx-hairline);}
.alert-error{background:#2d0000;color:var(--cx-danger-text);border:1px solid var(--cx-danger);}
.alert-info{background:var(--cx-info-pale);color:var(--cx-info-text);border:1px solid var(--cx-hairline);}

/* ─── Spinner ─── */
.spin{display:inline-block;width:16px;height:16px;border:2px solid var(--cx-border);border-top-color:#667eea;border-radius:50%;animation:spin .7s linear infinite;}
@keyframes spin{to{transform:rotate(360deg);}}

/* ─── Trend item ─── */
.trend-item{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--cx-hairline);}
.trend-item:last-child{border-bottom:none;}
.trend-sku{font-weight:700;color:var(--cx-text);font-size:13px;}
.trend-bar{flex:1;margin:0 12px;}
.trend-pct{font-size:12px;font-weight:700;min-width:60px;text-align:right;}
.trend-up{color:var(--cx-success-text);}
.trend-dn{color:var(--cx-danger-text);}
.trend-flat{color:var(--cx-text-mute);}

/* ─── Topbar actions ─── */
.actions-bar{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:10px;}
.search-box{background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:8px;padding:7px 12px;color:var(--cx-text);font-size:13px;width:240px;}
.search-box:focus{outline:none;border-color:#667eea;}

/* ─── Content calendar ─── */
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin-top:12px;}
.cal-day-hdr{text-align:center;font-size:10px;font-weight:700;color:var(--cx-text-mute);padding:6px 0;}
.cal-day{background:var(--cx-bg-alt);border-radius:6px;min-height:70px;padding:6px;position:relative;}
.cal-day-num{font-size:10px;color:var(--cx-text-mute);margin-bottom:4px;}
.cal-item{background:var(--cx-primary-dark);border-radius:3px;padding:2px 4px;font-size:9px;color:#ddd6fe;margin-bottom:2px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.cal-item.published{background:var(--cx-success);color:#6ee7b7;}
.cal-item.draft{background:var(--cx-border);color:var(--cx-text-mute);}
.cal-item.scheduled{background:var(--cx-info-pale);color:var(--cx-info-text);}
.platform-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;cursor:default;transition:all .2s;}
.pill-off{background:var(--cx-card);color:var(--cx-text-faint);border:1px solid var(--cx-border);}
.pill-shopify{background:#0d2e1a;color:var(--cx-success-text);border:1px solid var(--cx-hairline);}
.pill-ghl{background:#1a1033;color:var(--cx-primary-text);border:1px solid var(--cx-primary-dark);}
.pill-ig{background:#2d1520;color:#f9a8d4;border:1px solid #831843;}
</style>
</head>

<div id="toast-container" style="position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none;"></div>
<!-- Banner de errores JS - visible para diagnosticar en prod cuando un botón
     no responde. Si ves este banner, hay un bug específico para reportar. -->
<div id="js-error-banner" style="display:none;position:fixed;top:0;left:0;right:0;z-index:10000;background:var(--cx-danger);color:var(--cx-danger-pale);padding:10px 16px;font-size:12px;font-family:monospace;border-bottom:2px solid var(--cx-danger);"></div>
<script>
// CSRF defense-in-depth · Sebastian 3-may-2026
function _csrf() {
  // FIX 2-jun-2026 (Jefferson "no me deja cargar pago influencer"): el token vive
  // en window._csrfTok (traído de /api/csrf-token), NO en una cookie (esa cookie
  // nunca se setea → _fetchOpts mandaba token vacío). Preferimos el real.
  if (window._csrfTok) return window._csrfTok;
  var m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}
function _fetchOpts(method, body) {
  var headers = {};
  var tok = _csrf();
  if (tok) headers['X-CSRF-Token'] = tok;
  var opts = {method: method || 'GET', headers: headers, credentials: 'same-origin'};
  if (body !== undefined && body !== null) {
    headers['Content-Type'] = 'application/json';
    opts.body = (typeof body === 'string') ? body : JSON.stringify(body);
  }
  return opts;
}
fetch('/api/csrf-token', {credentials: 'same-origin'}).then(function(r){return r.ok?r.json():null;}).then(function(d){if(d&&d.csrf_token)window._csrfTok=d.csrf_token;}).catch(function(){});

function showToast(msg, type) {
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  const bg = type==='error'?'#7f1d1d':type==='success'?'#064e3b':type==='warning'?'#78350f':'#f1f5f9';
  const border = type==='error'?'#ef4444':type==='success'?'#10b981':type==='warning'?'#f59e0b':'#475569';
  t.style.cssText = `background:${bg};border:1px solid ${border};color:var(--cx-text);padding:12px 18px;border-radius:8px;font-size:13px;font-weight:600;min-width:220px;max-width:360px;box-shadow:0 4px 20px rgba(0,0,0,.4);pointer-events:auto;`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(()=>{ t.style.opacity='0'; t.style.transition='opacity .4s'; setTimeout(()=>t.remove(), 400); }, 3200);
}

// Captura errores globales y los muestra en banner para no esconder
// problemas silenciosos en producción.
window.addEventListener('error', function(ev) {
  try {
    const banner = document.getElementById('js-error-banner');
    if (!banner) return;
    const msg = (ev.message || ev.error?.message || 'Error desconocido') +
                ' @ ' + (ev.filename || '').split('/').pop() + ':' + (ev.lineno||'?');
    banner.style.display = 'block';
    banner.innerHTML = '⚠️ Error JS: ' + msg.substring(0, 280) +
      ' <button onclick="this.parentElement.style.display=\'none\'" style="float:right;background:transparent;border:1px solid #fca5a5;color:#fff;padding:1px 8px;border-radius:4px;cursor:pointer;font-size:11px;">cerrar</button>';
    console.error('[marketing] global error', ev);
  } catch (e) { /* swallow */ }
});
window.addEventListener('unhandledrejection', function(ev) {
  console.error('[marketing] unhandled rejection', ev.reason);
});
</script>
<body>

<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:var(--cx-primary-text);"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
  <div>
    <div class="cx-mod-header__title">Marketing</div>
    <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; campañas, influencers &amp; ROI &middot; <span style="color:var(--cx-text-faint)">{usuario}</span></div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">Módulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
    </button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>

<div class="tabs-bar">
  <!-- Sebastián 13-jul · quitados Hoy + CMO IA (no se usaban) · Inteligencia fusionada
       dentro de Dashboard (sub-nav). Dashboard = inicio. -->
  <button class="tab-btn active" data-tab="influencers" onclick="switchTab('influencers')">&#x1F465; Influencers &amp; Pagos</button>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: DASHBOARD -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: HOY - Centro de ejecución (Fase 2/4 marketing)             -->

<div id="tab-influencers" class="tab-panel active">
  <div class="actions-bar">
    <div>
      <div class="page-title">&#x1F465; Influencers &amp; Pagos</div>
      <div style="color:var(--cx-text-mute);font-size:13px;margin-top:2px;">Catálogo + historial de pagos por influencer · click en una fila para expandir su historial.</div>
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;">
      <input class="search-box" id="inf-search" placeholder="Buscar nombre, @usuario, nicho..." oninput="loadInfluencers()">
      <button class="btn btn-outline" onclick="abrirDuplicados()" title="Detectar creadores duplicados (mismo nombre o mismos datos bancarios)">&#x1F50D; Duplicados</button>
      <button class="btn btn-primary" onclick="openInfluencerModal()">+ Nuevo Influencer</button>
    </div>
  </div>

  <!-- KPIs unificados (catálogo + pagos) -->
  <div id="inf-kpi-bar" style="display:none;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;"></div>

  <!-- Sub-nav · Centro de pagos vs Catálogo (Sebastián 13-jul) -->
  <div style="display:flex;gap:6px;margin:4px 0 18px;border-bottom:1px solid #ececf1;">
    <button id="infsub-pagos" onclick="infSubView('pagos')" style="border:none;background:none;cursor:pointer;padding:10px 18px;font-size:13px;font-weight:800;color:var(--cx-primary-text);border-bottom:3px solid var(--cx-primary);">💸 Centro de pagos</button>
    <button id="infsub-creadores" onclick="infSubView('creadores')" style="border:none;background:none;cursor:pointer;padding:10px 18px;font-size:13px;font-weight:700;color:var(--cx-text-mute);border-bottom:3px solid transparent;">👥 Creadores</button>
  </div>

  <!-- VISTA · Centro de pagos (default) -->
  <div id="inf-view-pagos">
    <!-- Banner flujo urgencia pagos (promesa 30d desde fecha_contenido) · vive con los pagos -->
    <div id="inf-urgencias-banner" style="display:none;border-radius:12px;margin-bottom:12px;padding:12px 16px;font-size:13px;line-height:1.5;"></div>
    <!-- Banner de solicitudes pendientes (visible si hay alguna) -->
    <div id="inf-pendientes-banner" style="display:none;margin-bottom:14px;padding:14px 18px;border-radius:12px;font-size:13px;line-height:1.5;"></div>
    <div id="inf-pagos-cards" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px;margin-bottom:16px;"></div>
    <div id="inf-pagos-filtros" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px;"></div>
    <div id="inf-pagos-lista"><div style="text-align:center;color:var(--cx-text-mute);padding:30px;"><span class="spin"></span></div></div>
  </div>

  <!-- VISTA · Catálogo de creadores (oculta por defecto) -->
  <div id="inf-view-creadores" style="display:none;">

  <!-- Sebastián 13-jul · quitado el bloque "Mi semana · vista community manager"
       (Top engagement / Dormidos / Top ROI) · sobrecargaba el centro de pagos.
       Los ids quedan ocultos para que cargarMiSemanaKPIs no truene. -->
  <div id="inf-mi-semana" style="display:none;">
    <span id="mis-top-count"></span><span id="mis-top-list"></span>
    <span id="mis-dormi-count"></span><span id="mis-dormi-list"></span>
    <span id="mis-roi-count"></span><span id="mis-roi-list"></span>
  </div>

  <!-- Bulk pagos · barra de acciones flotante (aparece si hay selección) -->
  <div id="inf-bulk-bar" style="display:none;background:linear-gradient(90deg,#a78bfa,#6d28d9);color:#fff;padding:10px 16px;border-radius:10px;margin-bottom:10px;font-size:13px;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
    <div><b id="inf-bulk-count">0</b> influencer(s) seleccionado(s)</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <button onclick="bulkSolicitarPagosInf()" style="background:var(--cx-success-pale);color:#fff;border:0;padding:8px 14px;border-radius:6px;cursor:pointer;font-weight:700;font-size:13px;">💸 Solicitar pago de seleccionados</button>
      <button onclick="bulkLimpiarSeleccionInf()" style="background:rgba(109,40,217,.06);color:#fff;border:1px solid rgba(255,255,255,.3);padding:8px 14px;border-radius:6px;cursor:pointer;font-size:13px;">✕ Limpiar</button>
    </div>
  </div>

  <div id="inf-alert" style="display:none;"></div>

  <!-- Atribución ventas (colapsable · analítica secundaria · Sebastián 13-jul declutter) -->
  <details class="card" style="margin-bottom:16px;background:linear-gradient(135deg,rgba(52,211,153,.06),rgba(52,211,153,.02));border:1px solid rgba(52,211,153,.25);" ontoggle="if(this.open&&typeof loadAtribucion==='function'){loadAtribucion();}">
    <summary style="cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
      <div>
        <div style="font-size:14px;font-weight:700;color:var(--cx-success-text);">&#x1F3AF; Atribución de ventas - últimos 90 días</div>
        <div style="font-size:11px;color:var(--cx-text-mute);margin-top:2px;">Revenue Shopify por discount code · click para ver</div>
      </div>
      <span onclick="event.preventDefault();loadAtribucion(true);" title="Refrescar atribución" style="font-size:16px;color:var(--cx-success-text);padding:4px 8px;">&#x21BB;</span>
    </summary>
    <div style="margin-top:14px;">
    <div id="atrib-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:12px;"></div>
    <div class="tbl-wrap">
      <table style="font-size:12px;">
        <thead><tr>
          <th>Influencer</th>
          <th>Discount code</th>
          <th style="text-align:right;">Pedidos</th>
          <th style="text-align:right;">Unidades</th>
          <th style="text-align:right;">Revenue</th>
          <th style="text-align:right;">Invertido</th>
          <th style="text-align:right;">ROI</th>
          <th>Último</th>
        </tr></thead>
        <tbody id="atrib-body"><tr class="empty-row"><td colspan="8" style="color:var(--cx-text-mute);text-align:center;padding:14px;">Cargando atribución...</td></tr></tbody>
      </table>
    </div>
    </div>
  </details>

  <!-- Filtros para historial de pagos (que sale al expandir cada fila) -->
  <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px;font-size:12px;color:var(--cx-text-mute)">
    <span style="font-weight:600">📊 Filtros para historial expandido:</span>
    <select id="pag-mes" onchange="renderInfluencersTable()" style="background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:6px;padding:5px 9px;color:var(--cx-text);font-size:12px;">
      <option value="">Todos los meses</option>
    </select>
    <select id="pag-estado" onchange="renderInfluencersTable()" style="background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:6px;padding:5px 9px;color:var(--cx-text);font-size:12px;">
      <option value="">Todos los pagos</option>
      <option value="Pendiente">⏳ Solo pendientes</option>
      <option value="Pagada">✅ Solo pagados</option>
    </select>
    <button class="btn btn-outline btn-sm" onclick="loadPagosInfluencers()" title="Refrescar pagos">&#x21BB; Pagos</button>
    <details style="margin-left:auto;position:relative;">
      <summary style="cursor:pointer;list-style:none;color:var(--cx-text-mute);font-size:12px;padding:4px 8px;border:1px solid #ececf1;border-radius:8px;">&#x2699; Utilidades</summary>
      <div style="position:absolute;right:0;top:calc(100% + 4px);z-index:10;background:var(--cx-card,#fff);border:1px solid #ececf1;border-radius:10px;box-shadow:0 8px 24px rgba(15,23,42,.12);padding:8px;display:flex;flex-direction:column;gap:6px;min-width:190px;">
        <button id="btn-bulk-fix-empresa" onclick="bulkRegenerarLegacy()" title="Fix comprobantes que dicen Espagiria → ANIMUS Lab" style="background:none;border:none;text-align:left;cursor:pointer;font-size:12px;padding:6px 8px;border-radius:6px;color:var(--cx-text);">&#x1F527; Fix comprobantes legacy</button>
        <button onclick="cleanupHistoricoImportado()" title="Marcar como Pagada los 'Pago histórico importado' atrapados en Pendiente" style="background:none;border:none;text-align:left;cursor:pointer;font-size:12px;padding:6px 8px;border-radius:6px;color:var(--cx-text);">&#x1F9F9; Limpiar histórico importado</button>
      </div>
    </details>
  </div>

  <!-- Tabla principal: catálogo influencers (rows expandibles) -->
  <!-- Sebastián 27-may PM · clases mob-* ocultan cols no críticas en móvil -->
  <!-- En móvil quedan: ☐ Nombre · Estado Pago · Pagos · Acciones -->
  <div class="card">
    <style>
      @media (max-width: 768px) {
        .inf-tbl .mob-hide { display: none !important; }
        .inf-tbl table { font-size: 12px; }
        .inf-tbl th, .inf-tbl td { padding: 6px 4px !important; }
        .inf-tbl input[type=checkbox] { width: 18px; height: 18px; }
      }
    </style>
    <div class="tbl-wrap inf-tbl">
      <table>
        <thead><tr>
          <th style="width:32px;text-align:center;"><input type="checkbox" id="inf-sel-all" onchange="bulkToggleAllInf(this.checked)" title="Seleccionar todos" style="cursor:pointer;width:16px;height:16px;"></th>
          <th style="width:24px"></th>
          <th class="mob-hide">#</th>
          <th>Nombre</th>
          <th class="mob-hide">Red</th>
          <th class="mob-hide">@Usuario</th>
          <th class="mob-hide">Seguidores</th>
          <th class="mob-hide">ER%</th>
          <th class="mob-hide">Nicho</th>
          <th class="mob-hide">Tarifa/post</th>
          <th class="mob-hide">Email</th>
          <th class="mob-hide">Banco / Cuenta</th>
          <th>Estado Pago</th>
          <th>Pagos</th>
          <th>Acciones</th>
        </tr></thead>
        <tbody id="inf-body"><tr class="empty-row"><td colspan="15"><span class="spin"></span></td></tr></tbody>
      </table>
    </div>
  </div>
  </div><!-- /inf-view-creadores -->
</div>

<!-- Tab "tab-pagos" eliminado - fusionado al de Influencers (Sebastian 30-abr-2026) -->
<div id="tab-pagos" class="tab-panel" style="display:none">
  <!-- LEGACY: por compatibilidad si algún link viejo apunta a este tab,
       redirige al de Influencers. -->
  <script>setTimeout(function(){ if(typeof switchTab==='function') switchTab(location.hash==='#pagos'?'influencers':'dashboard'); }, 100);</script>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: CONTENIDO (Kanban Brief→Producción→Pendiente→Publicado→Performance) -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<style>
.kanban-wrap{display:grid;grid-template-columns:repeat(5,minmax(220px,1fr));gap:12px;overflow-x:auto;padding-bottom:10px;}
.kanban-col{background:var(--cx-card,#fff);border:1px solid #eef0f2;border-radius:14px;padding:10px 10px 12px;min-height:300px;display:flex;flex-direction:column;box-shadow:0 2px 12px rgba(15,23,42,.05);border-top:3px solid var(--cx-border);}
.kanban-col-hdr{display:flex;justify-content:space-between;align-items:center;padding:4px 6px 10px;border-bottom:1px solid var(--cx-hairline);margin-bottom:8px;}
.kanban-col-hdr .name{font-weight:800;font-size:13px;color:var(--cx-text);letter-spacing:-.01em;}
.kanban-col-hdr .count{background:var(--cx-bg-alt);color:var(--cx-text-mute);padding:2px 10px;border-radius:20px;font-size:11px;font-weight:800;}
.kanban-col[data-estado="Brief"]       .name{color:var(--cx-info-text);} .kanban-col[data-estado="Brief"]{border-top-color:var(--cx-info);}
.kanban-col[data-estado="Produccion"]  .name{color:var(--cx-warn-text);} .kanban-col[data-estado="Produccion"]{border-top-color:var(--cx-warn);}
.kanban-col[data-estado="Pendiente"]   .name{color:var(--cx-primary-text);} .kanban-col[data-estado="Pendiente"]{border-top-color:var(--cx-primary);}
.kanban-col[data-estado="Publicado"]   .name{color:var(--cx-success-text);} .kanban-col[data-estado="Publicado"]{border-top-color:var(--cx-success);}
.kanban-col[data-estado="Performance"] .name{color:#f472b6;} .kanban-col[data-estado="Performance"]{border-top-color:#f472b6;}
.kanban-card{background:var(--cx-card);border:1px solid #eef0f2;border-radius:10px;padding:10px;margin-bottom:8px;cursor:pointer;transition:transform .12s,box-shadow .15s,border-color .15s;font-size:12px;box-shadow:0 1px 4px rgba(15,23,42,.04);}
.kanban-card:hover{border-color:var(--cx-primary);transform:translateY(-2px);box-shadow:0 8px 18px rgba(124,58,237,.10);}
.kanban-card .sku{font-family:monospace;color:var(--cx-success-text);font-size:11px;font-weight:700;}
.kanban-card .titulo{font-weight:700;color:var(--cx-text);margin:4px 0;line-height:1.3;}
.kanban-card .meta{display:flex;flex-wrap:wrap;gap:6px;font-size:10px;color:var(--cx-text-mute);margin-top:6px;}
.kanban-card .meta span{background:var(--cx-bg-alt);padding:1px 7px;border-radius:6px;}
.kanban-card .perf{display:flex;gap:8px;font-size:10px;margin-top:6px;color:var(--cx-text-mute);}
.kanban-card .perf b{color:var(--cx-text);}
.kanban-empty{color:var(--cx-text-faint);font-size:11px;text-align:center;padding:20px 0;font-style:italic;}
.kanban-add-btn{background:var(--cx-bg-alt);color:var(--cx-text-mute);border:1px dashed var(--cx-border);border-radius:6px;padding:6px;font-size:11px;cursor:pointer;width:100%;margin-top:auto;transition:.15s;}
.kanban-add-btn:hover{color:var(--cx-primary-text);border-color:var(--cx-primary);}
</style>

<script>
// ──────────────────────────────────────────────────────────────────────────────
// UTILS
// ──────────────────────────────────────────────────────────────────────────────
const fmt = n => Number(n||0).toLocaleString('es-CO');
const fmtM = n => {
  const v = Number(n||0);
  if(v>=1000000) return '$'+(v/1000000).toFixed(1)+'M';
  if(v>=1000) return '$'+(v/1000).toFixed(0)+'K';
  return '$'+fmt(v);
};
const badgeEstadoCamp = e => {
  const m = {Activa:'green',Planificada:'blue',Pausada:'yellow',Finalizada:'gray'};
  return `<span class="badge badge-${m[e]||'gray'}">${e}</span>`;
};
const badgeEstadoCont = e => {
  const m = {Publicado:'green',Programado:'blue',Borrador:'gray',Archivado:'gray'};
  return `<span class="badge badge-${m[e]||'gray'}">${e}</span>`;
};
const badgeEstadoInf = e => {
  const m = {Activo:'green',Inactivo:'yellow',Bloqueado:'red'};
  return `<span class="badge badge-${m[e]||'gray'}">${e}</span>`;
};
const roiBadge = r => {
  if(r===null||r===undefined||r==='') return '<span class="badge badge-gray">-</span>';
  const v = parseFloat(r);
  const cl = v>100?'green':v>0?'blue':v>-50?'yellow':'red';
  return `<span class="badge badge-${cl}">${v>0?'+':''}${v}%</span>`;
};
function showAlert(containerId, msg, type='success') {
  const el = document.getElementById(containerId);
  el.className = `alert alert-${type}`;
  el.textContent = msg;
  el.style.display = 'block';
  setTimeout(()=>el.style.display='none', 4000);
}

// ──────────────────────────────────────────────────────────────────────────────
// TABS
// ──────────────────────────────────────────────────────────────────────────────
const _loaded = {};

function switchTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === name);
  });

  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  const panel = document.getElementById('tab-' + name);
  if (panel) panel.classList.add('active');

  if (!_loaded[name]) { _loaded[name] = true; loadTab(name); }
}


function loadTab(name) {
  // Marketing quedo SOLO para subir pagos (Sebastian 27-jul): se quitaron las pestanas
  // Dashboard, Campanas y Contenido. Lo pesado era que abrir el modulo disparaba
  // /api/marketing/dashboard (25 consultas) aunque nadie mirara esos numeros.
  if(name==='influencers') loadInfluencers();
  else if(name==='pagos') loadPagosInfluencers();
}


// ═══════════════════════════════════════════════════════════════════
// TAB "HOY" - Centro de ejecución (Fase 2/4 marketing)
// Sebastian (29-abr-2026): "centro de ejecución, agencia de marketing
// con todos los agentes funcionando, tirando todo".
// ═══════════════════════════════════════════════════════════════════


function _escHtml(s) {
  return String(s||'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
}


// ──────────────────────────────────────────────────────────────────────────────
// DASHBOARD
// ──────────────────────────────────────────────────────────────────────────────
async function saveIgToken() {
  const token = document.getElementById('ig-token-input').value.trim();
  if (!token || !token.startsWith('EAA')) { showToast('Token invalido', 'error'); return; }
  try {
    const r = await fetch('/api/marketing/ig-update-token', _fetchOpts('POST', {token}));
    const d = await r.json();
    if (d.ok) {
      showToast('✅ Token guardado - sincronizando...', 'success');
      document.getElementById('ig-token-form').style.display = 'none';
      document.getElementById('ig-token-input').value = '';
      setTimeout(() => syncPlatform('instagram'), 800);
    } else {
      showToast('❌ ' + (d.error||'Error'), 'error');
    }
  } catch(e) { showToast('❌ Error de conexion', 'error'); }
}

async function refreshIgToken() {
  const btn = event.target;
  btn.disabled = true; btn.textContent = '⏳ Renovando...';
  try {
    const r = await fetch('/api/marketing/ig-refresh', _fetchOpts('POST'));
    const d = await r.json();
    if (d.ok) {
      showToast('✅ ' + d.msg, 'success');
    } else {
      showToast('❌ ' + (d.error||'Error al renovar'), 'error');
    }
  } catch(e) {
    showToast('❌ Error de conexion', 'error');
  } finally {
    btn.disabled = false; btn.textContent = '🔑 Renovar token IG';
  }
}



// ──────────────────────────────────────────────────────────────────────────────
// CAMPAÑAS
// ──────────────────────────────────────────────────────────────────────────────
async function loadCampanas() {
  const estado = document.getElementById('camp-filtro-estado').value;
  const url = '/api/marketing/campanas'+(estado?'?estado='+estado:'');
  const body = document.getElementById('camp-body');
  let rows;
  try {
    const r = await fetch(url, {credentials:'same-origin'});
    if(!r.ok){
      body.innerHTML='<tr class="empty-row"><td colspan="11" style="color:var(--cx-danger-text)">Error '+r.status+' cargando campañas</td></tr>';
      return;
    }
    rows = await r.json();
  } catch(e){
    body.innerHTML='<tr class="empty-row"><td colspan="11" style="color:var(--cx-danger-text)">Error red: '+esc(e.message)+'</td></tr>';
    return;
  }
  if(!Array.isArray(rows)){
    body.innerHTML='<tr class="empty-row"><td colspan="11" style="color:var(--cx-danger-text)">Respuesta inválida: '+esc(JSON.stringify(rows).slice(0,200))+'</td></tr>';
    return;
  }
  if(!rows.length) { body.innerHTML='<tr class="empty-row"><td colspan="11">Sin campañas. Crea la primera.</td></tr>'; return; }
  // AUDIT 26-may · cache campañas para que generarCuponCampana lea discount_code actual
  CAMPANAS_LIST = rows;
  body.innerHTML = rows.map(r=>{
    const roi = r.presupuesto_gastado>0 ? ((r.resultado_ventas-r.presupuesto_gastado)/r.presupuesto_gastado*100).toFixed(1) : null;
    // Sebastián 25-may-2026 PM · audit P0 · XSS · escape de campos del backend
    const cuponChip = r.discount_code
      ? `<div style="margin-top:3px;font-size:10px"><span style="background:var(--cx-primary-soft);color:var(--cx-primary-text);padding:1px 6px;border-radius:6px;font-family:monospace;font-weight:700" title="Atribución activa">${esc(r.discount_code)}</span></div>`
      : '';
    return `<tr>
      <td class="mob-hide" style="color:var(--cx-text-mute);">${esc(r.id)}</td>
      <td style="font-weight:700;">${esc(r.nombre)}${cuponChip}</td>
      <td class="mob-hide"><span class="badge badge-gray">${esc(r.tipo)}</span></td>
      <td class="mob-hide">${esc(r.canal||'-')}</td>
      <td>${badgeEstadoCamp(r.estado)}</td>
      <td class="mob-hide">${fmtM(r.presupuesto)}</td>
      <td class="mob-hide">${fmtM(r.presupuesto_gastado)}</td>
      <td style="color:var(--cx-success-text);">${fmtM(r.resultado_ventas)}</td>
      <td>${roiBadge(roi)}</td>
      <td class="mob-hide"><span class="badge badge-purple">${esc(r.num_influencers)}</span></td>
      <td>
        <button class="btn btn-outline btn-sm" onclick="editCampana(${r.id})" title="Editar">✏️</button>
        <button class="btn btn-outline btn-sm" onclick="generarCuponCampana(${r.id})" title="${r.discount_code?'Regenerar':'Generar'} cupón Shopify" style="border-color:var(--cx-primary);color:var(--cx-primary-text)">🎟️</button>
        <button class="btn btn-danger btn-sm" onclick="deleteCampana(${r.id},'${String(r.nombre||'').replace(/[\\\\']/g,'\\\\$&')}')" title="Eliminar">🗑</button>
      </td>
    </tr>`;
  }).join('');
}
// AUDIT 26-may · cache global de campañas
var CAMPANAS_LIST = [];

function openCampanaModal(data) {
  document.getElementById('camp-edit-id').value = '';
  document.getElementById('modal-campana-title').textContent = 'Nueva Campaña';
  ['nombre','canal','sku','notas'].forEach(f=>document.getElementById('camp-'+f).value='');
  ['presupuesto','obj-uds','res-uds','res-ventas'].forEach(f=>document.getElementById('camp-'+f).value=0);
  document.getElementById('camp-inicio').value='';
  document.getElementById('camp-fin').value='';
  document.getElementById('camp-tipo').value='Digital';
  document.getElementById('camp-estado').value='Planificada';
  document.getElementById('modal-campana').classList.add('open');
}

async function editCampana(id) {
  let r;
  try {
    const resp = await fetch(`/api/marketing/campanas/${id}`, {credentials:'same-origin'});
    if(!resp.ok){ showToast('Campaña HTTP '+resp.status,'error'); return; }
    r = await resp.json();
  } catch(e){ showToast('Error red editar campaña: '+e.message,'error'); return; }
  if(!r || r.error){ showToast('Error: '+(r&&r.error||'sin respuesta'),'error'); return; }
  document.getElementById('camp-edit-id').value = id;
  document.getElementById('modal-campana-title').textContent = 'Editar Campaña';
  document.getElementById('camp-nombre').value = r.nombre||'';
  document.getElementById('camp-canal').value = r.canal||'';
  document.getElementById('camp-sku').value = r.sku_objetivo||'';
  document.getElementById('camp-notas').value = r.notas||'';
  document.getElementById('camp-presupuesto').value = r.presupuesto||0;
  document.getElementById('camp-obj-uds').value = r.objetivo_unidades||0;
  document.getElementById('camp-res-uds').value = r.resultado_unidades||0;
  document.getElementById('camp-res-ventas').value = r.resultado_ventas||0;
  document.getElementById('camp-inicio').value = r.fecha_inicio||'';
  document.getElementById('camp-fin').value = r.fecha_fin||'';
  document.getElementById('camp-tipo').value = r.tipo||'Digital';
  document.getElementById('camp-estado').value = r.estado||'Planificada';
  document.getElementById('modal-campana').classList.add('open');
}

async function saveCampana() {
  const id = document.getElementById('camp-edit-id').value;
  const body = {
    nombre: document.getElementById('camp-nombre').value.trim(),
    tipo: document.getElementById('camp-tipo').value,
    estado: document.getElementById('camp-estado').value,
    canal: document.getElementById('camp-canal').value.trim(),
    presupuesto: parseFloat(document.getElementById('camp-presupuesto').value)||0,
    fecha_inicio: document.getElementById('camp-inicio').value||null,
    fecha_fin: document.getElementById('camp-fin').value||null,
    sku_objetivo: document.getElementById('camp-sku').value.trim(),
    objetivo_unidades: parseInt(document.getElementById('camp-obj-uds').value)||0,
    resultado_unidades: parseInt(document.getElementById('camp-res-uds').value)||0,
    resultado_ventas: parseFloat(document.getElementById('camp-res-ventas').value)||0,
    notas: document.getElementById('camp-notas').value.trim()
  };
  if(!body.nombre) { showAlert('camp-alert','El nombre es obligatorio','error'); return; }
  // Validaciones cliente · audit 25-may PM
  if(body.fecha_inicio && body.fecha_fin && body.fecha_inicio > body.fecha_fin){
    if(!confirm('La fecha de inicio ('+body.fecha_inicio+') es posterior a la fecha fin ('+body.fecha_fin+'). ¿Continuar?')) return;
  }
  if(body.presupuesto < 0 || body.objetivo_unidades < 0 || body.resultado_unidades < 0 || body.resultado_ventas < 0){
    showAlert('camp-alert','Los valores no pueden ser negativos','error'); return;
  }
  const url = id ? `/api/marketing/campanas/${id}` : '/api/marketing/campanas';
  const method = id ? 'PUT' : 'POST';
  let resp, data;
  try {
    resp = await fetch(url,{method, headers:_csrfHdr(), credentials:'same-origin', body:JSON.stringify(body)});
    data = await resp.json().catch(()=>({error:'Respuesta no es JSON ('+resp.status+')'}));
  } catch(e){
    showAlert('camp-alert','Error red: '+e.message,'error'); return;
  }
  if(resp.ok && (data.ok || data.id)) {
    closeModal('modal-campana');
    const msg = id?'Campaña actualizada':'Campaña creada exitosamente';
    showAlert('camp-alert', data.warning ? msg+' ⚠ '+data.warning : msg);
    loadCampanas();
  } else { showAlert('camp-alert', data.error||('Error HTTP '+resp.status),'error'); }
}

async function deleteCampana(id, nombre) {
  if(!confirm(`¿Eliminar campaña "${nombre}"? Se borrarán todas las asignaciones y contenido relacionado.`)) return;
  let resp, data;
  try {
    resp = await fetch(`/api/marketing/campanas/${id}`,_fetchOpts('DELETE'));
    data = await resp.json().catch(()=>({error:'Respuesta no es JSON'}));
  } catch(e){ showAlert('camp-alert','Error red: '+e.message,'error'); return; }
  // 409 · backend pide confirmación porque hay gasto/ventas registradas
  if(resp.status === 409 && (data.presupuesto_gastado>0 || data.resultado_ventas>0)){
    const fmtN = v => '$'+Number(v||0).toLocaleString('es-CO');
    if(!confirm(`⚠ Esta campaña tiene:\n  • Gastado: ${fmtN(data.presupuesto_gastado)}\n  • Ventas: ${fmtN(data.resultado_ventas)}\n\nBorrarla destruirá ese histórico financiero. ¿Confirmar?`)) return;
    try {
      resp = await fetch(`/api/marketing/campanas/${id}?force=1`,_fetchOpts('DELETE'));
      data = await resp.json().catch(()=>({error:'Respuesta no es JSON'}));
    } catch(e){ showAlert('camp-alert','Error red (force): '+e.message,'error'); return; }
  }
  if(resp.ok && data.ok) { showAlert('camp-alert','Campaña eliminada'); loadCampanas(); }
  else showAlert('camp-alert',data.error||('Error HTTP '+resp.status),'error');
}

// ──────────────────────────────────────────────────────────────────────────────
// INFLUENCERS
// ──────────────────────────────────────────────────────────────────────────────
// ─── PAGOS REALIZADOS - vista cronológica para Marketing ───────────────────
let _PAGOS_INF_CACHE = [];

async function cleanupHistoricoImportado() {
  try {
    var r = await fetch('/api/marketing/pagos-historico-cleanup', _fetchOpts('POST', {}));  // dry-run
    var d = await r.json();
    if (!r.ok) { alert('Error: '+(d.error||r.status)); return; }
    if (!d.total) {
      alert('✓ Sin pagos históricos atrapados en Pendiente.');
      return;
    }
    var lista = d.candidatos.slice(0,15).map(function(x){
      return '  · '+(x.influencer_nombre||'(sin nombre)')+' $'+Number(x.valor||0).toLocaleString('es-CO')+' ['+(x.fecha||'')+']';
    }).join('\n');
    if (d.total > 15) lista += '\n  ... y '+(d.total-15)+' más';
    if (!confirm('Vas a marcar '+d.total+' pagos históricos como Pagada (dejar de aparecer en Pendientes):\n\n'+lista+'\n\n¿Confirmar?')) return;
    var r2 = await fetch('/api/marketing/pagos-historico-cleanup', _fetchOpts('POST', {confirm: true}));
    var d2 = await r2.json();
    if (d2.ok) {
      alert('✓ '+d2.actualizados+' pagos históricos marcados como Pagada');
      if (typeof loadPagosInfluencers === 'function') loadPagosInfluencers();
    } else {
      alert('Error: '+(d2.error||'?'));
    }
  } catch(e) { alert('Error de red: '+e.message); }
}

async function bulkRegenerarLegacy() {
  // Paso 1: dry_run para listar candidatos
  let drylist;
  try {
    const r = await fetch('/api/comprobantes-pago/regenerar-legacy', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({dry_run: true})
    });
    if (r.status === 403) {
      showToast('Solo administradores pueden corregir comprobantes en bloque.', 'error');
      return;
    }
    drylist = await r.json();
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
    return;
  }
  const cands = (drylist && drylist.candidatos) || [];
  if (cands.length === 0) {
    showToast('No hay comprobantes legacy con dispatch incorrecto. Todo en orden.', 'ok');
    return;
  }
  // Paso 2: confirmar con el listado
  const preview = cands.slice(0, 6).map(x => '· ' + x.numero_ce + ' (' + (x.beneficiario||'?') + ')').join('\n');
  const extra = cands.length > 6 ? '\n  + ' + (cands.length-6) + ' mas...' : '';
  if (!confirm('Se detectaron ' + cands.length + ' comprobante(s) marcados como Espagiria que deberian ser ANIMUS Lab:\n\n' + preview + extra + '\n\nRegenerar todos? El PDF de cada uno se reemplaza con la version correcta.')) return;
  // Paso 3: aplicar
  showToast('Regenerando ' + cands.length + ' PDFs...', 'info');
  try {
    const r = await fetch('/api/comprobantes-pago/regenerar-legacy', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({dry_run: false})
    });
    const d = await r.json();
    const ok = (d.count_corregidos || 0);
    const err = (d.count_errores || 0);
    if (err > 0) {
      showToast(ok + ' corregidos, ' + err + ' con error. Ver consola.', 'error');
      console.warn('Errores bulk regenerar:', d.errores);
    } else {
      showToast(ok + ' comprobantes corregidos. Ahora dicen ANIMUS Lab.', 'ok');
    }
    setTimeout(() => loadPagosInfluencers(), 800);
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

async function regenerarCE(compId, numCE) {
  if (!confirm('Re-generar PDF del ' + numCE + '?\n\nEsto corrige empresa (ANIMUS vs Espagiria), datos bancarios y montos en el PDF almacenado.')) return;
  try {
    const r = await fetch('/api/comprobantes-pago/' + compId + '/regenerar', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({forzar_obs: true})
    });
    const d = await r.json();
    if (d.ok) {
      showToast('PDF regenerado: ' + d.numero_ce + ' · ' + d.empresa + ' · ' + d.pdf_size_kb + ' KB', 'ok');
      setTimeout(() => loadPagosInfluencers(), 600);
    } else {
      showToast('Error: ' + (d.error || 'Fallo al regenerar'), 'error');
    }
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

// ─── Atribución de ventas via discount codes ───────────────────────────
async function loadAtribucion(force) {
  const body = document.getElementById('atrib-body');
  const kpiEl = document.getElementById('atrib-kpis');
  if (body) body.innerHTML = '<tr class="empty-row"><td colspan="8"><span class="spin"></span></td></tr>';
  try {
    const r = await fetch('/api/marketing/atribucion-influencers' + (force ? '?force=1' : ''));
    const d = await r.json();
    if (!d.ok) {
      body.innerHTML = '<tr class="empty-row"><td colspan="8" style="color:var(--cx-danger-text);">Error: ' + _escHtml(d.error||'desconocido') + '</td></tr>';
      return;
    }
    const k = d.kpis || {};
    const list = d.influencers || [];

    // KPIs
    kpiEl.innerHTML = [
      {label:'Influencers con código', val: k.influencers_con_code||0, color:'#34d399'},
      {label:'Pedidos atribuidos',     val: k.pedidos_atribuidos||0,   color:'#60a5fa'},
      {label:'Revenue atribuido',      val: fmtM(k.revenue_atribuido||0), color:'#f59e0b'},
      {label:'Inversión total',        val: fmtM(k.inversion_total||0),  color:'#a78bfa'},
      {label:'ROI global',             val: (k.roi_global_pct==null?'-':k.roi_global_pct+'%'),
        color: k.roi_global_pct==null ? '#64748b' : (k.roi_global_pct >= 100 ? '#34d399' : (k.roi_global_pct >= 0 ? '#fbbf24' : '#ef4444'))},
    ].map(c=>`<div style="background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:8px;padding:10px 12px;">
      <div style="font-size:18px;font-weight:800;color:${c.color};line-height:1;">${c.val}</div>
      <div style="font-size:10px;color:var(--cx-text-mute);margin-top:4px;">${c.label}</div>
    </div>`).join('');

    if (!list.length) {
      body.innerHTML = '<tr class="empty-row"><td colspan="8" style="color:var(--cx-text-mute);text-align:center;padding:18px;">Ningún influencer tiene discount code asignado todavía. Editá un influencer y agregá el código (ej: ANIMUS_LAURA10).</td></tr>';
      return;
    }
    body.innerHTML = list.map(x => {
      const roi = x.roi_pct;
      const roiCol = (roi==null) ? '#64748b' : (roi >= 100 ? '#34d399' : (roi >= 0 ? '#fbbf24' : '#ef4444'));
      const roiTxt = (roi==null) ? '-' : roi + '%';
      return `<tr>
        <td style="font-weight:600;">${x.nombre||'-'}${x.usuario_red?'<div style="font-size:10px;color:var(--cx-text-mute);font-weight:400;">@'+x.usuario_red+'</div>':''}</td>
        <td><code style="background:var(--cx-bg-alt);color:var(--cx-success-text);padding:2px 8px;border-radius:4px;font-size:11px;">${x.discount_code}</code></td>
        <td style="text-align:right;">${x.n_pedidos||0}</td>
        <td style="text-align:right;color:var(--cx-text-mute);">${x.unidades||0}</td>
        <td style="text-align:right;font-weight:700;color:var(--cx-success-text);">${fmtM(x.revenue_total||0)}</td>
        <td style="text-align:right;color:var(--cx-text-mute);">${fmtM(x.invertido||0)}</td>
        <td style="text-align:right;font-weight:700;color:${roiCol};">${roiTxt}</td>
        <td style="font-size:11px;color:var(--cx-text-mute);">${(x.ultimo_pedido||'').slice(0,10)||'-'}</td>
      </tr>`;
    }).join('');
  } catch (e) {
    body.innerHTML = '<tr class="empty-row"><td colspan="8" style="color:var(--cx-danger-text);">Error de red: ' + e.message + '</td></tr>';
  }
}

async function loadPagosInfluencers() {
  // Atribución ahora es colapsable (carga al abrir · ontoggle) · no la disparamos en el load
  try {
    const r = await fetch('/api/marketing/pagos-influencers');
    const d = await r.json();
    _PAGOS_INF_CACHE = d.pagos || [];
    // Poblar PAGOS_BY_INF_ID y PAGOS_BY_INF_NAME para la vista fusionada
    PAGOS_BY_INF_ID = {};
    PAGOS_BY_INF_NAME = {};
    for (const p of _PAGOS_INF_CACHE) {
      if (p.influencer_id) {
        if (!PAGOS_BY_INF_ID[p.influencer_id]) PAGOS_BY_INF_ID[p.influencer_id] = [];
        PAGOS_BY_INF_ID[p.influencer_id].push(p);
      }
      const nm = (p.influencer_nombre||'').toLowerCase().trim();
      if (nm) {
        if (!PAGOS_BY_INF_NAME[nm]) PAGOS_BY_INF_NAME[nm] = [];
        PAGOS_BY_INF_NAME[nm].push(p);
      }
    }
    // Llenar select de meses con los disponibles
    const mesSel = document.getElementById('pag-mes');
    if (mesSel) {
      const cur = mesSel.value;
      mesSel.innerHTML = '<option value="">Todos los meses</option>'
        + (d.meses_disponibles || []).map(m => '<option value="' + m + '"' + (m===cur?' selected':'') + '>' + m + '</option>').join('');
    }
    // Re-render tabla principal con cache pagos actualizado
    if (typeof renderInfluencersTable === 'function') renderInfluencersTable();
    if (typeof renderCentroPagos === 'function') renderCentroPagos();  // centro de pagos por estados
  } catch(e) {
    console.warn('loadPagosInfluencers fallo:', e);
  }
}

function renderPagos() {
  const body = document.getElementById('pag-body');
  if (!body) return;
  const q = (document.getElementById('pag-search')||{value:''}).value.toLowerCase();
  const mes = (document.getElementById('pag-mes')||{value:''}).value;
  const estado = (document.getElementById('pag-estado')||{value:''}).value;
  const list = _PAGOS_INF_CACHE.filter(p => {
    if (estado && p.estado !== estado) return false;
    if (mes && (p.fecha||'').slice(0,7) !== mes) return false;
    if (q) {
      const hay = ((p.influencer_nombre||'')+(p.concepto||'')+(p.numero_oc||'')).toLowerCase();
      if (hay.indexOf(q) < 0) return false;
    }
    return true;
  });
  if (!list.length) {
    body.innerHTML = '<tr class="empty-row"><td colspan="7" style="color:var(--cx-text-mute);text-align:center;padding:24px;">Sin pagos para los filtros seleccionados.</td></tr>';
    return;
  }
  body.innerHTML = list.map(p => {
    const fecha = (p.fecha || '').slice(0,10);
    const estadoBadge = p.estado === 'Pagada'
      ? '<span style="background:var(--cx-success-pale);color:var(--cx-success-text);padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;">&#x2713; Pagada</span>'
      : '<span style="background:var(--cx-accent-dark);color:var(--cx-warn-text);padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;">&#x23F3; Pendiente</span>';
    let comprobante = '<span style="color:var(--cx-text-faint);font-size:11px;">-</span>';
    if (p.comprobante_id && p.numero_ce) {
      comprobante = '<a href="/api/comprobantes-pago/'+p.comprobante_id+'/pdf" target="_blank" '
        + 'style="color:#1F5F5B;font-weight:700;text-decoration:none;display:inline-flex;align-items:center;gap:4px;background:#f0fdfa;padding:3px 10px;border-radius:6px;font-size:12px;">'
        + '&#x1F4C4; '+p.numero_ce+'</a>';
    } else if (p.estado === 'Pagada') {
      comprobante = '<span style="color:var(--cx-danger-text);font-size:11px;font-style:italic;" title="Pago hecho antes del feature de comprobantes">sin CE</span>';
    }
    // Botón regenerar siempre visible junto al comprobante (corrige PDFs viejos)
    if (p.comprobante_id) {
      comprobante += ' <button onclick="regenerarCE('+p.comprobante_id+',\''+(p.numero_ce||'')+'\')" '
        + 'title="Re-generar PDF (corrige empresa, banco, monto)" '
        + 'style="background:none;border:none;cursor:pointer;font-size:13px;padding:0 2px;opacity:0.55;" '
        + '>&#x1F504;</button>';
    }
    const ocStr = p.numero_oc
      ? '<span style="font-family:monospace;font-size:11px;color:var(--cx-text-mute);">'+p.numero_oc+'</span>'
      : '-';
    return '<tr>'
      + '<td style="font-size:12px;color:var(--cx-text-soft);">'+fecha+'</td>'
      + '<td style="font-weight:700;">'+(p.influencer_nombre||'-')
        + (p.inf_email ? '<div style="font-size:11px;color:var(--cx-text-mute);font-weight:400;">'+p.inf_email+'</div>' : '')
      + '</td>'
      + '<td style="font-size:12px;color:var(--cx-text-mute);">'+(p.concepto||'-')+'</td>'
      + '<td style="text-align:right;font-weight:700;color:#1F5F5B;">'+fmtM(p.valor||0)+'</td>'
      + '<td>'+ocStr+'</td>'
      + '<td>'+comprobante+'</td>'
      + '<td>'+estadoBadge+'</td>'
      + '</tr>';
  }).join('');
}

// ─── Centro de pagos por estados (Sebastián 13-jul) ───────────────────────────
function infSubView(v){
  window._INF_SUBVIEW=v;
  var vp=document.getElementById('inf-view-pagos'), vc=document.getElementById('inf-view-creadores');
  var bp=document.getElementById('infsub-pagos'), bc=document.getElementById('infsub-creadores');
  if(vp) vp.style.display=(v==='pagos')?'':'none';
  if(vc) vc.style.display=(v==='creadores')?'':'none';
  if(bp){ bp.style.color=(v==='pagos')?'#6d28d9':'var(--cx-text-mute)'; bp.style.borderBottomColor=(v==='pagos')?'#6d28d9':'transparent'; }
  if(bc){ bc.style.color=(v==='creadores')?'#6d28d9':'var(--cx-text-mute)'; bc.style.borderBottomColor=(v==='creadores')?'#6d28d9':'transparent'; }
  if(v==='pagos') renderCentroPagos();
}
async function pagarDesdeMarketing(idx){
  // Pagar SIN salir del modulo (Sebastian 27-jul: "asi no tengo que entrar alli").
  //
  // Llama al MISMO endpoint canonico que usa Compras (PATCH /api/ordenes-compra/<oc>/pagar).
  // No se reimplementa el pago aca: seria una segunda via para mover plata, y las dos
  // terminarian divergiendo (el espejo a egresos, el comprobante, la auditoria, el guard de
  // sobre-pago). Esta pantalla decide; Compras sigue siendo quien ejecuta.
  var p = (window._PAGOS_VISIBLES||[])[idx];
  if(!p) return;
  if(!p.numero_oc){ showToast('Este pago no tiene orden asociada · no se puede pagar desde aca','error'); return; }

  // Si hay sospecha de cobro repetido, se pone DELANTE antes de dejar confirmar. Ese es el
  // punto de todo esto: que no se pueda pagar de corrido por encima de una alerta.
  var graves=(p.alertas||[]).filter(function(a){return a.nivel==='alto';});
  if(graves.length){
    var det=graves.map(function(a){
      var pv=a.pago_previo;
      return '• '+a.mensaje+(pv?('\n   anterior: '+fmtM(pv.valor||0)+' del '+(pv.fecha||'').slice(0,10)+(pv.entregable?' · '+pv.entregable:'')):'');
    }).join('\n');
    if(!confirm('OJO con este pago:\n\n'+det+'\n\n¿Pagar igual a '+(p.influencer_nombre||'')+' '+fmtM(p.valor||0)+'?')) return;
  } else {
    if(!confirm('Pagar '+fmtM(p.valor||0)+' a '+(p.influencer_nombre||'')+'?')) return;
  }

  // La referencia bancaria ancla el pago al movimiento real del banco: sin eso, despues no hay
  // como cruzar lo que dice EOS con lo que salio de la cuenta.
  var ref = prompt('Referencia de la transferencia (numero de transaccion del banco):','');
  if(ref===null) return;
  if(!String(ref).trim()){ showToast('La referencia es obligatoria para poder cruzar el pago con el banco','error'); return; }
  var medio = prompt('Medio de pago:','Transferencia') || 'Transferencia';

  try{
    var r = await fetch('/api/ordenes-compra/'+encodeURIComponent(p.numero_oc)+'/pagar',
      _fetchOpts('PATCH', {monto: p.valor||0, medio: medio,
                           numero_transaccion: String(ref).trim(),
                           observaciones: 'Pagado desde Marketing · '+(p.entregable||'')}));
    var d = await r.json();
    if(!r.ok || d.error){ showToast('No se pudo pagar: '+(d.error||('HTTP '+r.status)),'error'); return; }
    showToast('Pagado '+fmtM(p.valor||0)+' a '+(p.influencer_nombre||''),'success');
    loadPagosInfluencers();
  }catch(e){ showToast('Error de red: '+e.message,'error'); }
}

function _pagoAlertas(p){
  // Sin paso de aprobacion, estas alertas son LO UNICO que separa un pago legitimo de pagar dos
  // veces el mismo contenido. Por eso cada una muestra el PAGO ANTERIOR concreto al lado: se
  // decide comparando los dos de frente, no de memoria.
  var A=(p.alertas||[]); if(!A.length) return '';
  var C={alto:{bg:'var(--cx-danger-pale)',bd:'var(--cx-danger)',fg:'var(--cx-danger-text)',ic:'&#9888;'},
         medio:{bg:'var(--cx-warn-pale)',bd:'var(--cx-warn)',fg:'var(--cx-warn-text)',ic:'&#9888;'},
         info:{bg:'var(--cx-info-pale)',bd:'var(--cx-info)',fg:'var(--cx-info-text)',ic:'&#8505;'}};
  return '<div style="flex-basis:100%;margin-top:8px;display:flex;flex-direction:column;gap:6px">'
    + A.map(function(a){
        var c=C[a.nivel]||C.info;
        var prev=a.pago_previo;
        var det = prev
          ? '<div style="font-size:11px;opacity:.85;margin-top:3px">Pago anterior: <b>'
            + fmtM(prev.valor||0) + '</b> del ' + _escHtml((prev.fecha||'').slice(0,10))
            + (prev.fecha_publicacion ? ' &middot; public&oacute; ' + _escHtml(prev.fecha_publicacion.slice(0,10)) : '')
            + (prev.entregable ? ' &middot; ' + _escHtml(prev.entregable) : '')
            + (prev.numero_oc ? ' &middot; ' + _escHtml(prev.numero_oc) : '')
            + '</div>'
          : '';
        return '<div style="background:'+c.bg+';border-left:3px solid '+c.bd+';color:'+c.fg
          + ';border-radius:8px;padding:8px 12px;font-size:12px;font-weight:600">'
          + c.ic + ' ' + _escHtml(a.mensaje||'') + det + '</div>';
      }).join('')
    + '</div>';
}
function _pagoEstadoCat(p){
  var oc=(p.oc_estado||'').toLowerCase(), est=(p.estado||'').toLowerCase();
  if(est==='pagada'||oc==='pagada'||p.comprobante_id) return 'pagado';
  if(oc==='rechazada'||oc==='cancelada'||est==='rechazada') return 'rechazado';
  if(oc==='aprobada'||oc==='autorizada') return 'por_pagar';
  return 'solicitado';
}
window._INF_PAGO_FILTRO='todos';
function _setPagoFiltro(f){ window._INF_PAGO_FILTRO=f; renderCentroPagos(); }
function renderCentroPagos(){
  if((window._INF_SUBVIEW||'pagos')!=='pagos' && window._INF_SUBVIEW) { /* igual computa */ }
  var pagos=(_PAGOS_INF_CACHE||[]);
  var ST={
    solicitado:{lbl:'Solicitados',one:'Solicitado',emoji:'⏳',color:'#b45309',bg:'#fef3c7',fg:'#92400e'},
    por_pagar:{lbl:'Por pagar',one:'Por pagar',emoji:'💸',color:'#6d28d9',bg:'#ede9fe',fg:'#5b21b6'},
    pagado:{lbl:'Pagados',one:'Pagado',emoji:'✅',color:'#059669',bg:'#d1fae5',fg:'#065f46'},
    rechazado:{lbl:'Rechazados',one:'Rechazado',emoji:'❌',color:'#dc2626',bg:'#fee2e2',fg:'#991b1b'}
  };
  var counts={solicitado:0,por_pagar:0,pagado:0,rechazado:0}, sums={solicitado:0,por_pagar:0,pagado:0,rechazado:0};
  pagos.forEach(function(p){ var e=_pagoEstadoCat(p); counts[e]++; sums[e]+=(p.valor||0); });
  var cardsEl=document.getElementById('inf-pagos-cards');
  if(cardsEl){
    cardsEl.innerHTML=['solicitado','por_pagar','pagado','rechazado'].map(function(k){
      var s=ST[k];
      return '<div onclick="_setPagoFiltro(\''+k+'\')" style="cursor:pointer;background:var(--cx-card,#fff);border:1px solid #eef0f2;border-top:3px solid '+s.color+';border-radius:14px;padding:15px 16px;box-shadow:0 2px 12px rgba(15,23,42,.05);transition:transform .1s" onmouseover="this.style.transform=\'translateY(-2px)\'" onmouseout="this.style.transform=\'\'">'
        +'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.4px;font-weight:800;color:'+s.color+'">'+s.emoji+' '+s.lbl+'</div>'
        +'<div style="font-size:24px;font-weight:800;color:'+s.color+';line-height:1;margin-top:5px">'+counts[k]+'</div>'
        +'<div style="font-size:11px;color:var(--cx-text-mute);margin-top:3px">'+fmtM(sums[k])+'</div>'
      +'</div>';
    }).join('');
  }
  var fl=document.getElementById('inf-pagos-filtros');
  if(fl){
    var opts=[['todos','Todos'],['solicitado','⏳ Solicitados'],['por_pagar','💸 Por pagar'],['pagado','✅ Pagados'],['rechazado','❌ Rechazados']];
    fl.innerHTML=opts.map(function(o){
      var on=(window._INF_PAGO_FILTRO||'todos')===o[0];
      return '<button onclick="_setPagoFiltro(\''+o[0]+'\')" style="border:1px solid '+(on?'#6d28d9':'#e2e8f0')+';background:'+(on?'#6d28d9':'#fff')+';color:'+(on?'#fff':'#64748b')+';border-radius:999px;padding:6px 14px;font-size:12px;font-weight:700;cursor:pointer">'+o[1]+'</button>';
    }).join('');
  }
  var filtro=window._INF_PAGO_FILTRO||'todos';
  var list=pagos.filter(function(p){ return filtro==='todos' || _pagoEstadoCat(p)===filtro; });
  var ord={solicitado:0,por_pagar:1,pagado:2,rechazado:3};
  list.sort(function(a,b){ var ea=ord[_pagoEstadoCat(a)],eb=ord[_pagoEstadoCat(b)]; if(ea!==eb) return ea-eb; return (b.fecha||'').localeCompare(a.fecha||''); });
  var lst=document.getElementById('inf-pagos-lista');
  if(!lst) return;
  // Alerta: creadores con pagos pero SIN correo → no recibirán la factura de pagado.
  var _sinMail={};
  pagos.forEach(function(p){ if(!(p.inf_email||'').trim() && p.influencer_nombre) _sinMail[p.influencer_nombre.toLowerCase()]=1; });
  var _nSinMail=Object.keys(_sinMail).length;
  var _alertMail=_nSinMail>0
    ? '<div style="background:var(--cx-warn-pale);border:1px solid #fde68a;border-left:4px solid var(--cx-warn);border-radius:10px;padding:11px 16px;margin-bottom:14px;font-size:13px;color:var(--cx-warn-text);font-weight:600">⚠ '+_nSinMail+' creador'+(_nSinMail>1?'es':'')+' con pagos y <b>sin correo</b> · no recibirán la factura de pagado. Agregales el correo en <b>Creadores</b>.</div>'
    : '';
  // Cuantos pendientes vienen con una alerta ALTA. Va arriba porque es lo que hay que mirar
  // antes de despachar la cola, no algo que se descubra tarjeta por tarjeta.
  var _nAlta=0;
  pagos.forEach(function(p){ if((p.alertas||[]).some(function(a){return a.nivel==='alto';})) _nAlta++; });
  var _alertDup=_nAlta>0
    ? '<div style="background:var(--cx-danger-pale);border:1px solid #fca5a5;border-left:4px solid var(--cx-danger);border-radius:10px;padding:11px 16px;margin-bottom:14px;font-size:13px;color:var(--cx-danger-text);font-weight:700">&#9888; '+_nAlta+' pago'+(_nAlta>1?'s':'')+' con posible cobro repetido &middot; revisalos antes de pagar.</div>'
    : '';
  _alertMail = _alertDup + _alertMail;
  if(!list.length){ lst.innerHTML=_alertMail+'<div style="text-align:center;color:var(--cx-text-mute);padding:30px;">Sin pagos en este estado.</div>'; return; }
  // Las filas quedan accesibles por INDICE: el boton pasa el indice, no el id ni el nombre,
  // asi no hay texto del usuario interpolado dentro del onclick (nada que escapar).
  window._PAGOS_VISIBLES = list.slice(0,300);
  lst.innerHTML=_alertMail+window._PAGOS_VISIBLES.map(function(p,_ix){
    var e=_pagoEstadoCat(p); var s=ST[e];
    var ent=(p.entregable||'').trim();
    var hi=ent.indexOf('http'); var link=''; if(hi>=0){ link=ent.slice(hi).split(' ')[0].split('·')[0].trim(); }
    var okLink=(link.indexOf('http://')===0||link.indexOf('https://')===0);
    var entTxt=(hi>=0?ent.slice(0,hi):ent).trim(); if(entTxt.charAt(entTxt.length-1)==='·') entTxt=entTxt.slice(0,-1).trim();
    var noEmail=!(p.inf_email||'').trim();
    return '<div style="background:var(--cx-card,#fff);border:1px solid #eef0f2;border-left:4px solid '+s.color+';border-radius:12px;padding:12px 16px;margin-bottom:10px;box-shadow:0 1px 4px rgba(15,23,42,.05);display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">'
      +'<div style="min-width:200px;flex:1">'
        +'<div style="font-weight:800;color:var(--cx-text)">'+_escHtml(p.influencer_nombre||'-')+(noEmail?' <span title="sin correo · no recibirá la factura de pagado" style="color:var(--cx-danger-text);font-size:11px;font-weight:700">⚠ sin correo</span>':'')+'</div>'
        +'<div style="font-size:11px;color:var(--cx-text-mute);margin-top:2px">📅 Solicitud: '+((p.fecha||'').slice(0,10))+(p.fecha_publicacion?' · 📢 Publicó: '+p.fecha_publicacion.slice(0,10):'')+(entTxt?' · 📝 '+_escHtml(entTxt):'')+(okLink?' · <a href="'+_escHtml(link)+'" target="_blank" rel="noopener" style="color:var(--cx-primary-text);font-weight:700;text-decoration:none">🔗 post</a>':'')+'</div>'
      +'</div>'
      +'<div style="text-align:right;white-space:nowrap">'
        +'<div style="font-size:16px;font-weight:800;color:'+s.color+'">'+fmtM(p.valor||0)+'</div>'
        +'<span style="display:inline-block;margin-top:3px;background:'+s.bg+';color:'+s.fg+';padding:3px 11px;border-radius:999px;font-size:11px;font-weight:700">'+s.emoji+' '+s.one+'</span>'
        +(p.numero_ce?' <div style="font-size:10px;color:var(--cx-success-text);font-family:monospace;margin-top:2px">'+_escHtml(p.numero_ce)+'</div>':'')
      +'</div>'
      // El boton de pagar NO va aca: Marketing es el modulo de Jefferson y el pago lo decide el
      // CEO desde Centro de Mando. Ademas el backend lo rechazaria (no esta en OC_AUTORIZA_USERS),
      // asi que seria un boton que falla. Jefferson SI ve el estado de lo que pidio.
      +_pagoAlertas(p)
    +'</div>';
  }).join('');
}

// Cache global de influencers - verHistorial lookup. Antes se serializaba la
// fila completa en el atributo onclick, lo cual corrompía el HTML porque las
// comillas dobles del JSON cerraban el atributo prematuramente. Eso hacía
// que TODOS los botones de la fila (Editar, Pagar, Dar de baja) dejaran de
// funcionar visualmente.
let _INFLUENCERS_CACHE = {};

// Estado global compartido entre catalogo + historial pagos (post-fusión)
var INFLUENCERS_LIST = [];
var PAGOS_BY_INF_ID = {};      // influencer_id → array de pagos
var PAGOS_BY_INF_NAME = {};    // nombre lowercase → array de pagos (fallback)
var EXPANDED_INF = new Set();  // ids de influencers con historial expandido
// Audit 25-may PM · cache de payload por id para evitar XSS en onclick handlers
// (string interpolation con nombre/banco escapaba solo comillas - backslash o
// unicode podía romper el JS y permitir injection)
var _INF_ROW_PAYLOAD = {};

// Wrappers seguros · leen del cache en vez de interpolar strings en el onclick
function solicitarPagoInfById(id){
  const p = _INF_ROW_PAYLOAD[id];
  if(!p){ showToast('Influencer no encontrado en cache','error'); return; }
  solicitarPagoInf(id, p.nombre, p.tarifa, p.banco, p.cuenta_bancaria, p.cedula_nit, p.tipo_cuenta);
}
function abrirDarDeBajaById(id){
  const p = _INF_ROW_PAYLOAD[id];
  if(!p){ showToast('Influencer no encontrado en cache','error'); return; }
  abrirDarDeBaja(id, p.nombre);
}
function eliminarInfluencerById(id){
  const p = _INF_ROW_PAYLOAD[id];
  if(!p){ showToast('Influencer no encontrado en cache','error'); return; }
  eliminarInfluencer(id, p.nombre);
}

async function loadInfluencers() {
  const q = document.getElementById('inf-search').value;
  const url = '/api/marketing/influencers-panel'+(q?'?q='+encodeURIComponent(q):'');
  let data;
  try {
    const r = await fetch(url, {credentials:'same-origin'});
    if(!r.ok){
      showToast('Influencers HTTP '+r.status, 'error');
      data = {influencers:[], kpis:{}};
    } else {
      data = await r.json();
    }
  } catch(e) {
    showToast('Error red influencers: '+e.message, 'error');
    data = {influencers:[], kpis:{}};
  }
  if(data._error) { showToast('Backend influencers: '+(data._error||'').slice(0,160),'error'); }
  INFLUENCERS_LIST = data.influencers || [];
  _INFLUENCERS_CACHE = {};
  for (const inf of INFLUENCERS_LIST) _INFLUENCERS_CACHE[inf.id] = inf;
  const kpis = data.kpis || {};
  const kpiBar = document.getElementById('inf-kpi-bar');
  if(kpiBar) {
    kpiBar.style.display = 'grid';
    kpiBar.innerHTML = [
      {label:'Influencers activos', val: kpis.total_activos||0, color:'#34d399'},
      {label:'Pagado 2025', val: fmtM(kpis.pagado_anio||0), color:'#818cf8'},
      {label:'Pagado este mes', val: fmtM(kpis.pagado_mes||0), color:'#60a5fa'},
      {label:'Pendiente pago', val: fmtM(kpis.total_pendiente||0), color:'#f59e0b'},
    ].map(k=>`<div style="background:var(--cx-card,#fff);border:1px solid #eef0f2;border-top:3px solid ${k.color};border-radius:14px;padding:16px 18px;box-shadow:0 2px 12px rgba(15,23,42,.05);transition:transform .1s,box-shadow .15s;" onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 8px 20px rgba(15,23,42,.09)'" onmouseout="this.style.transform='';this.style.boxShadow='0 2px 12px rgba(15,23,42,.05)'">`
      +`<div style="font-size:24px;font-weight:800;color:${k.color};line-height:1;letter-spacing:-.01em;">${k.val}</div>`
      +`<div style="font-size:11px;color:var(--cx-text-mute);margin-top:5px;font-weight:600;">${k.label}</div>`
      +'</div>').join('');
  }
  const banner = document.getElementById('inf-pendientes-banner');
  if(banner) {
    const conPendiente = INFLUENCERS_LIST.filter(x => x.tiene_pendiente);
    if(conPendiente.length > 0) {
      const totalPend = kpis.total_pendiente || 0;
      banner.style.display = 'block';
      banner.style.background = 'linear-gradient(135deg,rgba(245,158,11,.10),rgba(245,158,11,.03))';
      banner.style.border = '1px solid rgba(245,158,11,.28)';
      banner.style.color = 'var(--cx-text)';
      banner.innerHTML = '<b style="color:var(--cx-warn-text);">⏳ ' + conPendiente.length + ' solicitud'
        + (conPendiente.length>1?'es':'') + ' esperando pago</b> · '
        + 'Total: <b>' + fmtM(totalPend) + '</b>'
        + '<br><span style="font-size:11px;color:var(--cx-text-mute);">'
        + 'Sebastián las autoriza y paga desde /compras → tab Influencers. '
        + 'Cuando se paguen recibirás email automático.</span>';
    } else {
      banner.style.display = 'none';
    }
  }
  // Cargar pagos y urgencias en paralelo, luego render (los chips dependen del mapa)
  await Promise.all([
    loadPagosInfluencers(),
    loadUrgenciasInfluencers(),  // popula INF_URGENCIA_MAP antes del render
  ]);
  renderInfluencersTable();
  bulkLimpiarSeleccionInf();  // limpiar selección al recargar
  // cargarMiSemanaKPIs();  // Sebastián 13-jul · bloque "Mi semana" quitado (clutter)
}

// Mapa influencer_id → urgencia más severa de sus pagos pendientes
window.INF_URGENCIA_MAP = window.INF_URGENCIA_MAP || {};

async function loadUrgenciasInfluencers() {
  const banner = document.getElementById('inf-urgencias-banner');
  window.INF_URGENCIA_MAP = {};
  try {
    const r = await fetch('/api/marketing/pagos-influencer/urgencias', {credentials:'same-origin'});
    if (!r.ok) { if(banner) banner.style.display='none'; return; }
    const d = await r.json();
    // Severidad: vencido > urgente > proximo > normal · guardar la más severa por influencer
    const sev = {vencido:3, urgente:2, proximo:1, normal:0};
    for (const p of (d.pagos||[])) {
      const iid = p.influencer_id;
      const cur = window.INF_URGENCIA_MAP[iid];
      if (!cur || sev[p.urgencia] > sev[cur.urgencia]) {
        window.INF_URGENCIA_MAP[iid] = {urgencia: p.urgencia, dias: p.dias_para_vencer, vence: p.vence_pago_at};
      }
    }
    if (!banner) return;
    const k = d.kpis || {};
    const vencidos = k.vencidos||0, urgentes = k.urgentes||0, proximos = k.proximos||0;
    if (vencidos === 0 && urgentes === 0) { banner.style.display='none'; return; }
    let bg, border, color, icon;
    if (vencidos > 0) {
      bg = 'linear-gradient(135deg,rgba(220,38,38,.10),rgba(220,38,38,.03))'; border = 'rgba(220,38,38,.30)'; color = '#b91c1c'; icon = '🚨';
    } else {
      bg = 'linear-gradient(135deg,rgba(245,158,11,.10),rgba(245,158,11,.03))'; border = 'rgba(245,158,11,.30)'; color = '#b45309'; icon = '⚠️';
    }
    banner.style.background = bg;
    banner.style.border = '1px solid '+border;
    banner.style.color = color;
    banner.style.display = 'block';
    const total = (k.valor_vencido_total||0).toLocaleString('es-CO');
    banner.innerHTML =
      '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">'
      + '<div><b style="font-size:14px;">'+icon+' Flujo urgencia pagos</b><br>'
      + '<span style="font-size:12px;opacity:.9;">'+esc(d.mensaje_estado||'')+'</span></div>'
      + '<div style="display:flex;gap:8px;font-size:11px;">'
      + (vencidos > 0 ? '<span style="background:var(--cx-danger);color:#fff;padding:4px 10px;border-radius:20px;font-weight:700;">🔴 '+vencidos+' atrasado'+(vencidos>1?'s':'')+'</span>' : '')
      + (urgentes > 0 ? '<span style="background:var(--cx-accent-dark);color:#fff;padding:4px 10px;border-radius:20px;font-weight:700;">🟡 '+urgentes+' esta semana</span>' : '')
      + (proximos > 0 ? '<span style="background:var(--cx-text-soft);color:#fff;padding:4px 10px;border-radius:20px;">🟢 '+proximos+' próx 15d</span>' : '')
      + '</div></div>'
      + (vencidos > 0 ? '<div style="font-size:11px;margin-top:8px;opacity:.85;">Promesa de pago: 30 días desde fecha del contenido. Total atrasado: <b>$'+total+'</b></div>' : '');
  } catch (_) {
    banner.style.display = 'none';
  }
}

// Render de la tabla principal - separado para poder llamar al cambiar filtros
// ═══════════════════════════════════════════════════════════════════
// 🎯 BULK PAGOS + KPIs Community Manager · Sebastián 27-may-2026 PM
// ═══════════════════════════════════════════════════════════════════
window._BULK_INF_SEL = window._BULK_INF_SEL || new Set();
function bulkToggleInf(id, checked){
  if(checked) window._BULK_INF_SEL.add(id);
  else window._BULK_INF_SEL.delete(id);
  bulkActualizarBarra();
}
function bulkToggleAllInf(checked){
  document.querySelectorAll('input.inf-sel').forEach(cb => {
    cb.checked = checked;
    const id = parseInt(cb.dataset.id || '0');
    if(id){ if(checked) window._BULK_INF_SEL.add(id); else window._BULK_INF_SEL.delete(id); }
  });
  bulkActualizarBarra();
}
function bulkLimpiarSeleccionInf(){
  window._BULK_INF_SEL.clear();
  document.querySelectorAll('input.inf-sel').forEach(cb => { cb.checked = false; });
  const selAll = document.getElementById('inf-sel-all'); if(selAll) selAll.checked = false;
  bulkActualizarBarra();
}
function bulkActualizarBarra(){
  const bar = document.getElementById('inf-bulk-bar');
  const count = window._BULK_INF_SEL.size;
  if(!bar) return;
  if(count > 0){
    bar.style.display = 'flex';
    document.getElementById('inf-bulk-count').textContent = count;
  } else {
    bar.style.display = 'none';
  }
}
async function bulkSolicitarPagosInf(){
  const ids = [...window._BULK_INF_SEL];
  if(!ids.length){ alert('Sin influencers seleccionados'); return; }
  // Pre-calcular total $$ para que Jefferson sepa qué está autorizando
  let totalPrev = 0, sinTarifa = 0;
  for(const id of ids){
    const inf = (INFLUENCERS_LIST||[]).find(x => x.id===id);
    if(!inf) continue;
    const t = parseFloat(inf.tarifa)||0;
    if(t > 0) totalPrev += t; else sinTarifa++;
  }
  const msgConf = `¿Solicitar pago para ${ids.length} influencer(s)?\n\n`
    + `💰 Total estimado: $${totalPrev.toLocaleString('es-CO')} COP\n`
    + (sinTarifa > 0 ? `⚠ ${sinTarifa} sin tarifa configurada (se omitirán)\n` : '')
    + `\nUsará la tarifa de cada uno · podés revisar/editar después en /compras`;
  if(!confirm(msgConf)) return;
  // Cargar tokens CSRF
  if(!window._csrfTok){
    try { const tr = await fetch('/api/csrf-token',{credentials:'same-origin'}); if(tr.ok){const td=await tr.json(); window._csrfTok=td.csrf_token||'';} } catch(_){}
  }
  // Progress UI · sobreescribe la barra bulk con texto live
  const bar = document.getElementById('inf-bulk-bar');
  const barOrig = bar ? bar.innerHTML : '';
  let ok = 0, errs = [];
  // En serie para no spamear backend ni explotar CSRF
  for(let i = 0; i < ids.length; i++){
    const id = ids[i];
    const inf = (INFLUENCERS_LIST||[]).find(x => x.id===id);
    const nombre = inf ? (inf.nombre || '#'+id) : '#'+id;
    if(bar){
      bar.innerHTML = `<div style="flex:1">⏳ Procesando ${i+1}/${ids.length} · <b>${nombre}</b></div>`
        + `<div style="background:rgba(109,40,217,.10);border-radius:10px;width:100%;max-width:200px;height:8px;overflow:hidden">`
        + `<div style="background:#34d399;height:100%;width:${Math.round((i/ids.length)*100)}%;transition:width .2s"></div></div>`;
    }
    try {
      if(!inf){ errs.push(`#${id}: no encontrado`); continue; }
      const tarifa = parseFloat(inf.tarifa)||0;
      if(tarifa <= 0){ errs.push(`${inf.nombre}: sin tarifa configurada · editá perfil primero`); continue; }
      const concepto = 'Pago periódico ' + new Date().toLocaleDateString('es-CO',{month:'short',year:'numeric'});
      const r = await fetch(`/api/marketing/influencers/${id}/solicitar-pago`, {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRF-Token': window._csrfTok || ''},
        // FIX 7-jul (idempotencia): token DETERMINISTA por influencer+período → re-correr el bulk del mismo mes
        // no crea pagos duplicados (el backend lo reclama con UNIQUE → 409 SOLICITUD_DUPLICADA, no doble egreso).
        body: JSON.stringify({valor: tarifa, concepto: concepto, solicitud_id: 'BULK-'+id+'-'+concepto})
      });
      const d = await r.json();
      if(r.ok && d.ok) ok++;
      else errs.push(`${inf.nombre}: ${d.error||r.status}`);
    } catch(e){ errs.push(`#${id}: red ${e.message}`); }
  }
  // Restaurar bar antes del alert
  if(bar) bar.innerHTML = barOrig;
  // Mostrar resumen prominent
  let msg = `✅ ${ok} solicitudes creadas · $${totalPrev.toLocaleString('es-CO')} COP estimado`;
  if(errs.length){ msg += `\n\n⚠ ${errs.length} fallaron:\n` + errs.slice(0,5).join('\n'); }
  alert(msg);
  bulkLimpiarSeleccionInf();
  loadInfluencers();
}

// ─── KPIs Community Manager (Mi Semana) ─────────────────────────────
async function cargarMiSemanaKPIs(){
  const box = document.getElementById('inf-mi-semana');
  if(!box) return;
  const infs = INFLUENCERS_LIST || [];
  if(!infs.length) { box.style.display='none'; return; }
  box.style.display = 'block';

  // 1) Top engagement 7d · usar engagement_rate como proxy si no hay data IG 7d real
  // Ordena desc por ER% (todos activos con ER>0)
  const topEng = infs
    .filter(i => (i.estado||'Activo')==='Activo' && parseFloat(i.engagement_rate||0) > 0)
    .sort((a,b) => parseFloat(b.engagement_rate||0) - parseFloat(a.engagement_rate||0))
    .slice(0, 3);
  const topEl = document.getElementById('mis-top-list');
  const topCt = document.getElementById('mis-top-count');
  if(topEng.length){
    topEl.innerHTML = topEng.map((i, idx) => {
      const er = parseFloat(i.engagement_rate||0).toFixed(2);
      return `<div style="display:flex;justify-content:space-between;gap:6px;padding:3px 0;border-bottom:1px solid rgba(52,211,153,.15);">
        <span><span style="color:var(--cx-success-text);font-weight:700;">${idx+1}.</span> ${esc(i.nombre||'(s/n)')}</span>
        <span style="color:var(--cx-success-text);font-weight:800;">${er}%</span></div>`;
    }).join('');
    topCt.textContent = `${topEng.length} de ${infs.length}`;
  } else {
    topEl.innerHTML = '<span style="color:var(--cx-text-mute);">Sin engagement registrado · editá influencers para agregar ER%.</span>';
    topCt.textContent = '0';
  }

  // 2) Sin actividad >45d · proxy: dias_desde_ultimo_pago > 45 (heurística)
  // (en futuro: usar última publicación IG real cuando esté el sync)
  const dormidos = infs
    .filter(i => (i.estado||'Activo')==='Activo'
                  && (i.dias_desde_ultimo_pago||0) > 45
                  && !i.tiene_pendiente)
    .sort((a,b) => (b.dias_desde_ultimo_pago||0) - (a.dias_desde_ultimo_pago||0))
    .slice(0, 5);
  const dormEl = document.getElementById('mis-dormi-list');
  const dormCt = document.getElementById('mis-dormi-count');
  if(dormidos.length){
    dormEl.innerHTML = dormidos.map(i =>
      `<div style="display:flex;justify-content:space-between;gap:6px;padding:3px 0;border-bottom:1px solid rgba(245,158,11,.15);">
        <span>${esc(i.nombre||'(s/n)')}</span>
        <span style="color:var(--cx-warn-text);font-weight:800;">${i.dias_desde_ultimo_pago||0}d</span></div>`
    ).join('');
    dormCt.textContent = `${dormidos.length} activos`;
  } else {
    dormEl.innerHTML = '<span style="color:var(--cx-text-mute);">✓ Sin influencers dormidos &gt;45d.</span>';
    dormCt.textContent = '0';
  }

  // 3) Top ROI · revenue_atribuible vs total_pagado (data del backend)
  const topRoi = infs
    .filter(i => (i.roi_implicito_pct != null) && parseFloat(i.total_pagado||0) > 0)
    .sort((a,b) => (b.roi_implicito_pct||-999) - (a.roi_implicito_pct||-999))
    .slice(0, 3);
  const roiEl = document.getElementById('mis-roi-list');
  const roiCt = document.getElementById('mis-roi-count');
  if(topRoi.length){
    roiEl.innerHTML = topRoi.map(i => {
      const roi = i.roi_implicito_pct;
      const col = roi >= 200 ? '#10b981' : (roi >= 50 ? '#22c55e' : (roi >= 0 ? '#f59e0b' : '#ef4444'));
      const rev = fmtM(i.revenue_atribuible||0);
      return `<div style="display:flex;justify-content:space-between;gap:6px;padding:3px 0;border-bottom:1px solid rgba(167,139,250,.15);">
        <span>${esc(i.nombre||'(s/n)')}<br><span style="font-size:10px;color:var(--cx-text-mute);">${rev} rev</span></span>
        <span style="color:${col};font-weight:800;">${roi}%</span></div>`;
    }).join('');
    roiCt.textContent = `${topRoi.length} con datos`;
  } else {
    roiEl.innerHTML = '<span style="color:var(--cx-text-mute);">Sin ROI calculado · asigná códigos de descuento a influencers para medir.</span>';
    roiCt.textContent = '0';
  }
}

function renderInfluencersTable() {
  const infs = INFLUENCERS_LIST || [];
  const body = document.getElementById('inf-body');
  if(!body) return;
  if(!infs.length) {
    body.innerHTML = `<tr class="empty-row"><td colspan="15">Sin influencers registrados.</td></tr>`;
    return;
  }
  body.innerHTML = infs.map((r, idx)=>{
    const seg = r.seguidores>=1000?(r.seguidores/1000).toFixed(1)+'K':r.seguidores;
    const banco = r.banco
      ? `<span style="color:var(--cx-text-mute);">${esc(r.banco)}</span><br><span style="font-size:11px;color:var(--cx-text-mute);">${esc(r.cuenta_bancaria||'\u2014')}</span>`
      : '<span style="color:var(--cx-text-faint);">Sin datos</span>';
    let estadoBadge;
    // Sebastian (30-abr-2026): badges compactos solo-\u00edcono con tooltip,
    // antes el texto "Al d\u00eda" se romp\u00eda en 2 l\u00edneas en columnas estrechas.
    // El color comunica el estado, hover muestra el detalle.
    if(r.tiene_pendiente) {
      // Chip urgencia \u00b7 prioriza color de vencimiento sobre amarillo gen\u00e9rico
      const u = (window.INF_URGENCIA_MAP||{})[r.id];
      if (u && u.urgencia === 'vencido') {
        estadoBadge = '<span style="background:var(--cx-danger);color:var(--cx-danger-text);padding:3px 8px;border-radius:50%;font-size:13px;font-weight:700;display:inline-block;width:24px;height:24px;line-height:18px;text-align:center;white-space:nowrap;border:1.5px solid var(--cx-danger);" title="ATRASADO \u00b7 pago vencido hace '+Math.abs(u.dias||0)+' d. Venc\u00eda '+esc(u.vence||'')+'">\ud83d\udd34</span>';
      } else if (u && u.urgencia === 'urgente') {
        estadoBadge = '<span style="background:#854d0e;color:#fde047;padding:3px 8px;border-radius:50%;font-size:13px;font-weight:700;display:inline-block;width:24px;height:24px;line-height:18px;text-align:center;white-space:nowrap;border:1.5px solid var(--cx-warn);" title="Urgente \u00b7 vence en '+(u.dias||0)+' d ('+esc(u.vence||'')+')">\ud83d\udfe1</span>';
      } else {
        estadoBadge = '<span style="background:var(--cx-accent-dark);color:var(--cx-warn-text);padding:3px 8px;border-radius:50%;font-size:13px;font-weight:700;display:inline-block;width:24px;height:24px;line-height:18px;text-align:center;white-space:nowrap;" title="Esperando pago \u2014 solicitud creada, Sebasti\u00e1n por autorizar">\u23f3</span>';
      }
    } else if(r.toca_pagar) {
      const dias = r.dias_desde_ultimo_pago || 0;
      estadoBadge = '<span style="background:#854d0e;color:#fde047;padding:3px 8px;border-radius:50%;font-size:13px;font-weight:700;display:inline-block;width:24px;height:24px;line-height:18px;text-align:center;white-space:nowrap;" title="Toca solicitar \u2014 hace '+dias+' d\u00edas del \u00faltimo pago (ciclo '+r.ciclo_pago+'). Click \ud83d\udcb8 Solicitar pago para crear cuenta de cobro">\ud83d\udccc</span>';
    } else if(r.pagos_count>0) {
      estadoBadge = '<span style="background:var(--cx-success-pale);color:var(--cx-success-text);padding:3px 8px;border-radius:50%;font-size:13px;font-weight:700;display:inline-block;width:24px;height:24px;line-height:18px;text-align:center;white-space:nowrap;" title="Al d\u00eda \u2014 '+(r.pagos_count||0)+' pago(s) confirmado(s)">\u2713</span>';
    } else {
      estadoBadge = '<span style="color:var(--cx-text-faint);font-size:11px;" title="Sin actividad de pago a\u00fan">\u2014</span>';
    }
    // Audit 25-may PM · cache de payload por id para evitar string interpolation
    // en onclick (XSS si nombre tiene comillas/backslashes). Handler lee por id.
    _INF_ROW_PAYLOAD[r.id] = {
      nombre: r.nombre||'',
      banco: r.banco||'',
      cuenta_bancaria: r.cuenta_bancaria||'',
      cedula_nit: r.cedula_nit||'',
      tipo_cuenta: r.tipo_cuenta||'Ahorros',
      tarifa: r.tarifa||0,
    };
    // Resumen pagos del influencer (cache desde loadPagosInfluencers)
    const pagosInf = (PAGOS_BY_INF_ID[r.id] || PAGOS_BY_INF_NAME[(r.nombre||'').toLowerCase()] || []);
    const pendCount = pagosInf.filter(p => (p.estado||'').toLowerCase()==='pendiente').length;
    const paidCount = pagosInf.filter(p => (p.estado||'').toLowerCase()==='pagada').length;
    const totalPaidVal = pagosInf
      .filter(p => (p.estado||'').toLowerCase()==='pagada')
      .reduce((s,p) => s + (p.valor||0), 0);
    // FIX 27-may-2026 PM \u00b7 Sebasti\u00e1n/Jefferson \u00b7 "que el lo modifique en caso
    // tal de que este mal \u00b7 alli donde dice pagos es confuso, debemos darle
    // mejor version". Badge clickable \u2192 abre modal Gestionar Pagos con lista
    // editable (Marcar Pagada/Pendiente, Editar valor, Eliminar err\u00f3neos).
    let pagosBadge = '<button onclick="abrirGestionarPagos('+r.id+', '+esc(JSON.stringify(r.nombre||''))+')" style="background:var(--cx-card);border:1px dashed var(--cx-text-soft);color:var(--cx-text-mute);font-size:10px;padding:3px 8px;border-radius:6px;cursor:pointer" title="Sin pagos \u00b7 click para registrar/gestionar">+ Gestionar</button>';
    if(pagosInf.length > 0){
      pagosBadge = '<button onclick="abrirGestionarPagos('+r.id+', '+esc(JSON.stringify(r.nombre||''))+')" style="background:transparent;border:0;padding:0;cursor:pointer;display:inline-flex;gap:4px;align-items:center;font-size:11px" title="Click para gestionar \u00b7 marcar pagado/pendiente, editar o eliminar">';
      if(pendCount>0) pagosBadge += `<span style="background:var(--cx-accent-dark);color:var(--cx-warn-text);padding:2px 8px;border-radius:8px;font-weight:700">\u23f3 ${pendCount}</span>`;
      if(paidCount>0) pagosBadge += `<span style="background:var(--cx-success-pale);color:var(--cx-success-text);padding:2px 8px;border-radius:8px;font-weight:700">\u2713 ${paidCount}</span>`;
      pagosBadge += '<span style="color:var(--cx-primary-text);font-size:13px;margin-left:2px">\u2699</span></button>';
    }
    // AUDIT 26-may \u00b7 cup\u00f3n + atribuci\u00f3n real Shopify
    let cuponBadge = '';
    if(r.discount_code){
      const revAtr = r.revenue_atribuible||0;
      const roi = r.roi_implicito_pct;
      const roiCol = roi==null?'#94a3b8':(roi>=200?'#10b981':roi>=50?'#22c55e':roi>=0?'#f59e0b':'#ef4444');
      const roiTxt = roi==null?'sin pago a\u00fan':roi+'% ROI';
      cuponBadge = `<div style="font-size:10px;margin-top:3px"><span style="background:var(--cx-primary-soft);color:var(--cx-primary-text);padding:1px 6px;border-radius:6px;font-family:monospace;font-weight:700" title="C\u00f3digo activo: ${esc(r.discount_code)}">${esc(r.discount_code)}</span>`;
      if(revAtr>0){
        cuponBadge += ` <span style="color:${roiCol};font-weight:700" title="${r.pedidos_atribuibles||0} pedidos \u00b7 ${r.unidades_atribuibles||0} uds">${fmtM(revAtr)}</span>`;
        cuponBadge += ` <span style="color:${roiCol};font-size:9px">(${esc(roiTxt)})</span>`;
      } else {
        cuponBadge += ` <span style="color:var(--cx-text-mute)">sin ventas a\u00fan</span>`;
      }
      cuponBadge += `</div>`;
    }
    const isExpanded = EXPANDED_INF.has(r.id);
    const expandIcon = isExpanded ? '\u25bc' : '\u25b6';
    const expandColor = pagosInf.length>0 ? '#818cf8' : '#475569';
    const checked = window._BULK_INF_SEL && window._BULK_INF_SEL.has(r.id) ? 'checked' : '';
    const mainRow = `<tr style="cursor:pointer" onclick="toggleExpandInf(${r.id})" title="Click para ver historial pagos">`
      +`<td style="text-align:center;width:32px;" onclick="event.stopPropagation()">`
        +`<input type="checkbox" class="inf-sel" data-id="${r.id}" ${checked} onchange="bulkToggleInf(${r.id}, this.checked)" style="width:16px;height:16px;cursor:pointer;"></td>`
      +`<td style="color:${expandColor};font-weight:700;font-size:14px;text-align:center;width:24px;">${pagosInf.length>0?expandIcon:''}</td>`
      +`<td class="mob-hide" style="color:var(--cx-text-mute);">${idx+1}</td>`
      +`<td style="font-weight:700;">${esc(r.nombre)}</td>`
      +`<td class="mob-hide"><span class="badge badge-gray">${esc(r.red_social)}</span></td>`
      +`<td class="mob-hide" style="color:#818cf8;">${esc(r.usuario_red||'\u2014')}</td>`
      +`<td class="mob-hide">${seg}</td>`
      +`<td class="mob-hide">${r.engagement_rate?esc(r.engagement_rate)+'%':'\u2014'}</td>`
      +`<td class="mob-hide">${esc(r.nicho||'\u2014')}</td>`
      +`<td class="mob-hide">${r.tarifa?fmtM(r.tarifa):'\u2014'}</td>`
      +`<td class="mob-hide" style="font-size:12px;color:var(--cx-text-mute);">${esc(r.email||'\u2014')}</td>`
      +`<td class="mob-hide" style="font-size:12px;">${banco}</td>`
      +`<td>${estadoBadge}</td>`
      +`<td>${pagosBadge}${cuponBadge}</td>`
      +`<td style="white-space:nowrap;" onclick="event.stopPropagation()">`
        +`<button class="btn btn-primary btn-sm" onclick="solicitarPagoInfById(${r.id})" title="Crear cuenta de cobro y enviar a Sebasti\u00e1n para que la pague" style="font-weight:700;padding:5px 11px;">&#x1F4B8; Solicitar pago</button> `
        +`<button class="btn btn-outline btn-sm" onclick="editInfluencer(${r.id})" title="Editar datos bancarios y de contacto">&#x270F;&#xFE0F;</button> `
        +`<button class="btn btn-outline btn-sm" onclick="var m=document.getElementById('acc-more-${r.id}');m.style.display=m.style.display==='none'?'inline':'none';" title="M\u00e1s acciones" style="color:var(--cx-text-mute);">&#x22EF;</button>`
        +`<span id="acc-more-${r.id}" style="display:none;">`
          +` <button class="btn btn-outline btn-sm" onclick="generarCuponInf(${r.id})" title="${r.discount_code?'Regenerar':'Generar'} cup\u00f3n Shopify para atribuci\u00f3n de ventas" style="border-color:var(--cx-primary);color:var(--cx-primary-text)">&#x1F39F;&#xFE0F;</button> `
          +`<button class="btn btn-danger btn-sm" onclick="abrirDarDeBajaById(${r.id})" title="Dar de baja">&#x26D4;</button> `
          +`<button class="btn btn-danger btn-sm" onclick="eliminarInfluencerById(${r.id})" title="Eliminar duplicado (solo sin pagos efectuados)">&#x1F5D1;&#xFE0F;</button>`
        +`</span>`
      +'</td>'
      +'</tr>';
    let expandedRows = '';
    if(isExpanded && pagosInf.length>0){
      const fEstado = (document.getElementById('pag-estado')||{value:''}).value;
      const fMes = (document.getElementById('pag-mes')||{value:''}).value;
      let filtered = pagosInf;
      if(fEstado) filtered = filtered.filter(p => (p.estado||'')===fEstado);
      if(fMes) filtered = filtered.filter(p => (p.fecha||'').startsWith(fMes));
      if(filtered.length){
        expandedRows = filtered.map(p => {
          const est = p.estado||'Pendiente';
          const estColor = est.toLowerCase()==='pagada' ? '#34d399' : (est.toLowerCase()==='pendiente'?'#fcd34d':'#94a3b8');
          const pdfBtn = p.has_pdf ? `<a href="/api/marketing/pagos-influencers/${p.id}/pdf" target="_blank" style="color:var(--cx-success-text);text-decoration:none;font-size:11px;">\u{1F4C4} PDF</a>` : '<span style="color:var(--cx-text-faint);font-size:11px;">\u2014</span>';
          return `<tr style="background:var(--cx-bg)">`
            +`<td colspan="2" style="color:var(--cx-text-mute);font-size:11px;padding-left:42px;">${esc(p.fecha||'\u2014')}</td>`
            +`<td colspan="3" style="font-size:12px;color:var(--cx-text-mute)">${esc((p.concepto||'(sin concepto)').substring(0,80))}</td>`
            +`<td colspan="3" style="text-align:right;font-weight:700;">${fmtM(p.valor||0)}</td>`
            +`<td colspan="2" style="font-size:11px;color:#818cf8;font-family:monospace">${esc(p.numero_oc||'\u2014')}</td>`
            +`<td colspan="2">${pdfBtn}</td>`
            +`<td colspan="2"><span style="color:${estColor};font-size:11px;font-weight:700;">${esc(est)}</span></td>`
            +`</tr>`;
        }).join('');
      } else {
        expandedRows = `<tr style="background:var(--cx-bg)"><td colspan="14" style="color:var(--cx-text-mute);text-align:center;padding:14px;font-size:11px;font-style:italic;padding-left:42px">Sin pagos para los filtros seleccionados.</td></tr>`;
      }
    }
    return mainRow + expandedRows;
  }).join('');
}

function toggleExpandInf(id){
  if(EXPANDED_INF.has(id)) EXPANDED_INF.delete(id);
  else EXPANDED_INF.add(id);
  renderInfluencersTable();
}

function openInfluencerModal() {
  document.getElementById('inf-edit-id').value='';
  document.getElementById('modal-inf-title').textContent='Nuevo Influencer';
  ['nombre','usuario','nicho','email','tel','notas','banco','cuenta','cedula'].forEach(f=>document.getElementById('inf-'+f).value='');
  ['seguidores','er','tarifa'].forEach(f=>document.getElementById('inf-'+f).value=0);
  document.getElementById('inf-red').value='Instagram';
  document.getElementById('inf-estado').value='Activo';
  document.getElementById('inf-tipo-cta').value='Ahorros';
  document.getElementById('modal-influencer').classList.add('open');
}

async function editInfluencer(id) {
  let r;
  try {
    const resp = await fetch(`/api/marketing/influencers/${id}`, {credentials:'same-origin'});
    if(!resp.ok){ showToast('Influencer HTTP '+resp.status,'error'); return; }
    r = await resp.json();
  } catch(e){ showToast('Error red editar influencer: '+e.message,'error'); return; }
  if(!r || r.error){ showToast('Error: '+(r&&r.error||'sin respuesta'),'error'); return; }
  document.getElementById('inf-edit-id').value=id;
  document.getElementById('modal-inf-title').textContent='Editar Influencer';
  document.getElementById('inf-nombre').value=r.nombre||'';
  document.getElementById('inf-usuario').value=r.usuario_red||'';
  document.getElementById('inf-nicho').value=r.nicho||'';
  document.getElementById('inf-email').value=r.email||'';
  document.getElementById('inf-tel').value=r.telefono||'';
  document.getElementById('inf-notas').value=r.notas||'';
  document.getElementById('inf-seguidores').value=r.seguidores||0;
  document.getElementById('inf-er').value=r.engagement_rate||0;
  document.getElementById('inf-tarifa').value=r.tarifa||0;
  document.getElementById('inf-red').value=r.red_social||'Instagram';
  document.getElementById('inf-estado').value=r.estado||'Activo';
  document.getElementById('inf-banco').value=r.banco||'';
  document.getElementById('inf-tipo-cta').value=r.tipo_cuenta||'Ahorros';
  document.getElementById('inf-cuenta').value=r.cuenta_bancaria||'';
  document.getElementById('inf-cedula').value=r.cedula_nit||'';
  const dcEl = document.getElementById('inf-discount-code');
  if(dcEl) dcEl.value = r.discount_code || '';
  const ccEl = document.getElementById('inf-ciclo-pago');
  if(ccEl) ccEl.value = r.ciclo_pago || 'Mensual';
  document.getElementById('modal-influencer').classList.add('open');
}

async function saveInfluencer() {
  const id = document.getElementById('inf-edit-id').value;
  const body = {
    nombre: document.getElementById('inf-nombre').value.trim(),
    red_social: document.getElementById('inf-red').value,
    usuario_red: document.getElementById('inf-usuario').value.trim(),
    seguidores: parseInt(document.getElementById('inf-seguidores').value)||0,
    engagement_rate: parseFloat(document.getElementById('inf-er').value)||0,
    nicho: document.getElementById('inf-nicho').value.trim(),
    tarifa: parseFloat(document.getElementById('inf-tarifa').value)||0,
    estado: document.getElementById('inf-estado').value,
    email: document.getElementById('inf-email').value.trim(),
    telefono: document.getElementById('inf-tel').value.trim(),
    notas: document.getElementById('inf-notas').value.trim(),
    banco: document.getElementById('inf-banco').value.trim(),
    tipo_cuenta: document.getElementById('inf-tipo-cta').value,
    cuenta_bancaria: document.getElementById('inf-cuenta').value.trim(),
    cedula_nit: document.getElementById('inf-cedula').value.trim(),
    discount_code: (document.getElementById('inf-discount-code')||{value:''}).value.trim().toUpperCase(),
    ciclo_pago: (document.getElementById('inf-ciclo-pago')||{value:'Mensual'}).value
  };
  if(!body.nombre) { showAlert('inf-alert','El nombre es obligatorio','error'); return; }
  // Sebastián 13-jul · correo OBLIGATORIO: sin él no le llega la factura al pagarle.
  if(!body.email || body.email.indexOf('@')<0) { showAlert('inf-alert','El correo es obligatorio (para enviarle la factura cuando se le pague)','error'); return; }
  const url = id ? `/api/marketing/influencers/${id}` : '/api/marketing/influencers';
  const method = id?'PUT':'POST';
  const resp = await fetch(url,{method, headers:_csrfHdr(), credentials:'same-origin', body:JSON.stringify(body)});
  const data = await resp.json();
  if(data.ok||data.id) { closeModal('modal-influencer'); showAlert('inf-alert',id?'Influencer actualizado':'Influencer creado'); loadInfluencers(); }
  else showAlert('inf-alert',data.error||'Error','error');
}

function abrirDarDeBaja(id, nombre) {
  document.getElementById('baja-inf-id').value = id;
  document.getElementById('baja-inf-nombre').textContent = nombre;
  document.getElementById('baja-motivo-tipo').value = 'Pausa temporal';
  document.getElementById('baja-observacion').value = '';
  document.getElementById('modal-dar-baja').classList.add('open');
}
async function confirmarDarDeBaja() {
  const id = document.getElementById('baja-inf-id').value;
  const motivo = document.getElementById('baja-motivo-tipo').value;
  const obs    = document.getElementById('baja-observacion').value;
  const resp = await fetch(`/api/marketing/influencers/${id}/dar-baja`, _fetchOpts('POST', {motivo, observacion: obs}));
  const data = await resp.json();
  if(data.ok) {
    closeModal('modal-dar-baja');
    showAlert('inf-alert',`Influencer dado de baja: ${motivo}`,'warning');
    loadInfluencers();
  } else showAlert('inf-alert', data.error||'Error','error');
}


// AUDIT 26-may · generar/regenerar cupón Shopify para atribución
async function generarCuponInf(id) {
  const p = _INF_ROW_PAYLOAD[id];
  const nombre = p ? p.nombre : 'influencer #'+id;
  const inf = (INFLUENCERS_LIST || []).find(x => x.id === id) || {};
  const yaTiene = !!inf.discount_code;
  let pct = prompt('% de descuento del cupón (1-99) para "'+nombre+'":\n\n'
                    +(yaTiene?'⚠ Ya tiene: '+inf.discount_code+'\nIngresá nuevo % para regenerar.\n\n':'')
                    +'Convención: ANIMUS_<NOMBRE>15 · 15% es el estándar.', yaTiene?'':'15');
  if(pct === null) return;
  pct = parseInt(pct);
  if(isNaN(pct) || pct < 1 || pct > 99){ alert('% inválido (1-99)'); return; }
  const body = {pct: pct};
  if(yaTiene) body.force = true;
  try {
    const r = await fetch('/api/marketing/influencers/'+id+'/generar-cupon', _fetchOpts('POST', body));
    const d = await r.json().catch(()=>({}));
    if(!r.ok){
      if(r.status === 409 && d.conflicto){
        alert('Código ya en uso por '+d.conflicto.tipo+' "'+d.conflicto.nombre+'" · usá otro %');
      } else {
        alert('Error: '+(d.error||r.status));
      }
      return;
    }
    showAlert('inf-alert', '🎟 Cupón ' + d.discount_code + ' asignado · ahora crealo manualmente en Shopify Admin → Descuentos', 'success');
    loadInfluencers();
  } catch(e){ alert('Error red: '+e.message); }
}

// Equivalente para campañas
async function generarCuponCampana(id) {
  const camps = (typeof CAMPANAS_LIST !== 'undefined' && CAMPANAS_LIST) ? CAMPANAS_LIST : [];
  const cmp = camps.find(x => x.id === id) || {};
  const yaTiene = !!cmp.discount_code;
  let pct = prompt('% de descuento del cupón para la campaña "'+(cmp.nombre||'#'+id)+'":\n\n'
                    +(yaTiene?'⚠ Ya tiene: '+cmp.discount_code+'\nIngresá nuevo % para regenerar.\n\n':'')
                    +'Convención: ANIMUS_<NOMBRECAMP>15', yaTiene?'':'10');
  if(pct === null) return;
  pct = parseInt(pct);
  if(isNaN(pct) || pct < 1 || pct > 99){ alert('% inválido (1-99)'); return; }
  const body = {pct: pct};
  if(yaTiene) body.force = true;
  try {
    const r = await fetch('/api/marketing/campanas/'+id+'/generar-cupon', _fetchOpts('POST', body));
    const d = await r.json().catch(()=>({}));
    if(!r.ok){
      if(r.status === 409 && d.conflicto){
        alert('Código ya en uso por '+d.conflicto.tipo+' "'+d.conflicto.nombre+'" · usá otro %');
      } else {
        alert('Error: '+(d.error||r.status));
      }
      return;
    }
    showAlert('camp-alert', '🎟 Cupón ' + d.discount_code + ' asignado · ahora crealo manualmente en Shopify Admin → Descuentos', 'success');
    if(typeof loadCampanas === 'function') loadCampanas();
  } catch(e){ alert('Error red: '+e.message); }
}

async function eliminarInfluencer(id, nombre) {
  const ok = confirm('¿ELIMINAR DEFINITIVAMENTE a "'+nombre+'"?\n\n'
    +'Esto borra el influencer y sus pagos NO pagados/registros vinculados.\n'
    +'Solo se permite si NO tiene pagos efectivamente realizados.\n\n'
    +'(Si tiene pagos históricos, usa el botón ⛔ Dar de baja en su lugar.)');
  if(!ok) return;
  try {
    const resp = await fetch('/api/marketing/influencers/'+id, _fetchOpts('DELETE'));
    const data = await resp.json().catch(()=>({}));
    if(resp.ok && (data.ok || data.deleted)) {
      showAlert('inf-alert','Influencer "'+nombre+'" eliminado correctamente.','success');
      loadInfluencers();
    } else if(resp.status === 403) {
      showAlert('inf-alert', (data.error||'No autorizado')+'. Usa ⛔ Dar de baja.', 'error');
    } else {
      showAlert('inf-alert', data.error || ('Error '+resp.status), 'error');
    }
  } catch(e) {
    showAlert('inf-alert','Error de red: '+e.message,'error');
  }
}

// FIX 1-jun-2026 · fusiona en bloque los duplicados por nombre (caso 'todos
// juanito rebel') · dry-run → confirmar → apply. Repunta pagos al conservado.
async function dedupMergeInfluencers() {
  if(!window._csrfTok){ try{const tr=await fetch('/api/csrf-token',{credentials:'same-origin'}); if(tr.ok){const td=await tr.json(); window._csrfTok=td.csrf_token||'';}}catch(_){} }
  let dry;
  try {
    const r = await fetch('/api/marketing/influencers/dedup-merge', {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token': window._csrfTok||''},
      body: JSON.stringify({})
    });
    dry = await r.json();
    if(!r.ok || !dry.ok){ alert('Error: '+((dry&&dry.error)||r.status)); return; }
  } catch(e){ alert('Error red: '+e.message); return; }
  if(!dry.duplicados_a_eliminar){ alert('No hay duplicados por nombre para fusionar.'); return; }
  if(!confirm('Se fusionarán '+dry.grupos_n+' grupo(s) de nombre · se eliminarán '
      +dry.duplicados_a_eliminar+' duplicado(s).\n\nSe conserva el de MÁS pagos y se repuntan'
      +' los pagos/solicitudes al conservado. Acción irreversible (queda en auditoría).\n\n¿Continuar?')) return;
  try {
    const r2 = await fetch('/api/marketing/influencers/dedup-merge', {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token': window._csrfTok||''},
      body: JSON.stringify({apply:true})
    });
    const d2 = await r2.json();
    if(!r2.ok || !d2.ok){ alert('Error: '+((d2&&d2.error)||r2.status)); return; }
    alert('✅ '+d2.duplicados_eliminados+' duplicados fusionados · '+d2.pagos_repuntados
      +' pago(s) repuntado(s)'+(d2.unique_index?' · protección anti-duplicados ACTIVADA':''));
    closeModal('modal-duplicados');
    if(typeof loadInfluencers==='function') loadInfluencers();
  } catch(e){ alert('Error red: '+e.message); }
}

async function abrirDuplicados() {
  const modalId = 'modal-duplicados';
  let modal = document.getElementById(modalId);
  if(!modal) {
    modal = document.createElement('div');
    modal.id = modalId;
    modal.className = 'modal';
    modal.innerHTML = ''
      +'<div class="modal-content" style="max-width:900px;">'
      +'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">'
      +'    <div class="modal-title">\u{1F50D} Posibles influencers duplicados</div>'
      +'    <div style="display:flex;gap:6px;">'
      +'      <button class="btn btn-sm" style="background:var(--cx-danger);color:#fff;" onclick="dedupMergeInfluencers()" title="Fusiona TODOS los duplicados por nombre · conserva el de más pagos · repunta los pagos al conservado (solo admin)">\u{1F9F9} Fusionar duplicados</button>'
      +'      <button class="btn btn-outline btn-sm" onclick="closeModal(\''+modalId+'\')">Cerrar</button>'
      +'    </div>'
      +'  </div>'
      +'  <div id="dup-body" style="max-height:65vh;overflow:auto;font-size:13px;"></div>'
      +'</div>';
    document.body.appendChild(modal);
  }
  const body = document.getElementById('dup-body');
  body.innerHTML = '<div style="padding:20px;color:var(--cx-text-mute);">Buscando duplicados…</div>';
  modal.classList.add('open');
  try {
    const r = await fetch('/api/marketing/influencers/duplicados');
    const d = await r.json();
    const gN = d.duplicados_por_nombre || [];
    const gD = d.duplicados_por_datos || [];
    if(!gN.length && !gD.length) {
      body.innerHTML = '<div style="padding:24px;text-align:center;color:var(--cx-success-text);">✅ No se detectaron duplicados.</div>';
      return;
    }
    let html = '';
    const renderGrupo = (grupo, kind) => {
      const items = grupo.rows || [];
      // Sugerido conservar: backend lo manda en 'nombre'; en 'datos' calculamos aquí (más pagos)
      let sug = grupo.sugerido_conservar;
      if(!sug && items.length) {
        const sorted = items.slice().sort((a,b)=>(b.n_pagos||0)-(a.n_pagos||0));
        sug = sorted[0].id;
      }
      const titulo = kind==='nombre'
        ? ('Nombre similar: <span style="color:var(--cx-warn-text)">'+_escDup(grupo.nombre_normalizado||'?')+'</span>')
        : ('Mismos '+_escDup(grupo.tipo||'datos')+': <span style="color:var(--cx-warn-text)">'+_escDup(grupo.valor||'?')+'</span>');
      let rows = items.map(it => {
        const conservar = (it.id === sug);
        const pagos = it.n_pagos || 0;
        return '<tr style="'+(conservar?'background:var(--cx-success-pale)':'')+'">'
          +'<td style="padding:6px 8px;">'+(conservar?'⭐ ':'')+_escDup(it.nombre||'')+(it.usuario_red?' <span style="color:var(--cx-text-mute)">@'+_escDup(it.usuario_red)+'</span>':'')+'</td>'
          +'<td style="padding:6px 8px;font-size:11px;color:var(--cx-text-mute);">'+_escDup(it.cedula_nit||'-')+' / '+_escDup(it.cuenta_bancaria||'-')+'</td>'
          +'<td style="padding:6px 8px;text-align:center;">'+pagos+'</td>'
          +'<td style="padding:6px 8px;text-align:right;white-space:nowrap;">'
            +(conservar
              ? '<span style="color:var(--cx-success-text);font-size:11px;">conservar</span>'
              : '<button class="btn btn-danger btn-sm" onclick="eliminarInfluencerDup('+it.id+',\''+_escDup((it.nombre||'').replace(/\x27/g,'’'))+'\')">\u{1F5D1}️ Eliminar</button>')
          +'</td>'
        +'</tr>';
      }).join('');
      return '<div style="margin-bottom:18px;border:1px solid var(--cx-border);border-radius:8px;overflow:hidden;">'
        +'<div style="padding:8px 12px;background:var(--cx-card);font-weight:600;">'+titulo+'</div>'
        +'<table style="width:100%;border-collapse:collapse;">'
        +'<thead><tr style="background:var(--cx-bg-alt);color:var(--cx-text-mute);font-size:11px;">'
        +'<th style="padding:6px 8px;text-align:left;">Influencer</th>'
        +'<th style="padding:6px 8px;text-align:left;">CC/NIT / Cuenta</th>'
        +'<th style="padding:6px 8px;text-align:center;">Pagos</th>'
        +'<th style="padding:6px 8px;text-align:right;">Acción</th>'
        +'</tr></thead><tbody>'+rows+'</tbody></table></div>';
    };
    if(gN.length) {
      html += '<div style="font-weight:600;color:var(--cx-text-soft);margin-bottom:8px;">Por nombre similar ('+gN.length+')</div>';
      html += gN.map(g => renderGrupo(g,'nombre')).join('');
    }
    if(gD.length) {
      html += '<div style="font-weight:600;color:var(--cx-text-soft);margin:14px 0 8px 0;">Por datos bancarios o cédula iguales ('+gD.length+')</div>';
      html += gD.map(g => renderGrupo(g,'datos')).join('');
    }
    body.innerHTML = html;
  } catch(e) {
    body.innerHTML = '<div style="padding:20px;color:var(--cx-danger-text);">Error: '+e.message+'</div>';
  }
}

function _escDup(s){
  return (s==null?'':String(s)).replace(/[<>&"']/g,function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c];});
}

async function eliminarInfluencerDup(id, nombre) {
  await eliminarInfluencer(id, nombre);
  // Refrescar el panel
  setTimeout(abrirDuplicados, 400);
}

function recalcularVencePagoInf() {
  // Promesa 30d desde fecha_contenido \u2192 muestra fecha de vencimiento + dias restantes
  const fc = document.getElementById('pago-fecha-contenido').value;
  const out = document.getElementById('pago-vence');
  if (!fc) { out.value=''; out.style.color='#c7d2fe'; return; }
  const base = new Date(fc + 'T00:00:00');
  if (isNaN(base.getTime())) { out.value='\u2014'; return; }
  const vence = new Date(base.getTime() + 30*24*3600*1000);
  const hoy = new Date(); hoy.setHours(0,0,0,0);
  const diff = Math.round((vence - hoy)/(24*3600*1000));
  const yyyy = vence.getFullYear();
  const mm = String(vence.getMonth()+1).padStart(2,'0');
  const dd = String(vence.getDate()).padStart(2,'0');
  let etiqueta;
  if (diff < 0)       { etiqueta = `${yyyy}-${mm}-${dd} \u00b7 \ud83d\udd34 +${Math.abs(diff)}d`; out.style.color='#fca5a5'; }
  else if (diff <= 7) { etiqueta = `${yyyy}-${mm}-${dd} \u00b7 \ud83d\udfe1 ${diff}d`;            out.style.color='#fcd34d'; }
  else                { etiqueta = `${yyyy}-${mm}-${dd} \u00b7 \ud83d\udfe2 ${diff}d`;            out.style.color='#86efac'; }
  out.value = etiqueta;
}

// ─── Gestionar pagos influencer (Jefferson · 27-may-2026 PM) ──────────────
async function abrirGestionarPagos(infId, infNombre){
  document.getElementById('gp-inf-id').value = infId;
  document.getElementById('gp-inf-nombre').textContent = infNombre || '(sin nombre)';
  document.getElementById('gp-alert').style.display = 'none';
  document.getElementById('modal-gestionar-pagos').classList.add('open');
  await _cargarGestionarPagos(infId, infNombre);
}
async function _cargarGestionarPagos(infId, infNombre){
  const tbody = document.getElementById('gp-tbody');
  tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;color:var(--cx-text-mute);">⏳ Cargando...</td></tr>';
  // Re-usa cache de pagos (PAGOS_BY_INF_ID + PAGOS_BY_INF_NAME)
  let pagos = (PAGOS_BY_INF_ID[infId] || PAGOS_BY_INF_NAME[(infNombre||'').toLowerCase()] || []).slice();
  // Si cache vacío, intentar fetch fresco al endpoint /pagos-influencers
  if (!pagos.length){
    try {
      const r = await fetch('/api/marketing/pagos-influencers?q='+encodeURIComponent(infNombre||''), {credentials:'same-origin'});
      const d = await r.json();
      pagos = (d.pagos || []).filter(p => (p.influencer_id===infId) || ((p.influencer_nombre||'').toLowerCase()===(infNombre||'').toLowerCase()));
    } catch(_){}
  }
  if (!pagos.length){
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;color:var(--cx-text-mute);">Sin pagos registrados para este influencer.</td></tr>';
    return;
  }
  // Ordenar por fecha desc
  pagos.sort((a,b)=> (b.fecha||'').localeCompare(a.fecha||''));
  let html = '';
  for (const p of pagos){
    const estado = p.estado || 'Pendiente';
    const estadoBg = estado==='Pagada' ? '#064e3b' : (estado==='Anulada' ? '#374151' : '#78350f');
    const estadoCol = estado==='Pagada' ? '#34d399' : (estado==='Anulada' ? '#9ca3af' : '#fcd34d');
    const valor = (p.valor||0).toLocaleString('es-CO');
    html += '<tr style="border-bottom:1px solid var(--cx-hairline);">';
    html += '<td style="padding:8px;color:var(--cx-text-soft);">'+esc((p.fecha||'').substring(0,10))+'</td>';
    html += '<td style="padding:8px;"><span style="background:'+estadoBg+';color:'+estadoCol+';padding:3px 9px;border-radius:10px;font-weight:700;font-size:11px;">'+esc(estado)+'</span></td>';
    html += '<td style="padding:8px;text-align:right;font-weight:700;color:var(--cx-primary-text);">$'+valor+'</td>';
    html += '<td style="padding:8px;font-size:11px;color:var(--cx-text-mute);">'+esc((p.concepto||'').substring(0,60))+'</td>';
    html += '<td style="padding:8px;font-family:monospace;font-size:11px;color:#67e8f9;">'+esc(p.numero_oc||'-')+'</td>';
    html += '<td style="padding:8px;text-align:center;white-space:nowrap;">';
    // Botón Pagada (si está Pendiente)
    if (estado === 'Pendiente'){
      html += '<button onclick="_gpCambiarEstado('+p.id+',&quot;Pagada&quot;)" title="Marcar como Pagada" style="background:var(--cx-success-pale);color:#fff;border:0;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px;margin-right:3px">✓</button>';
    }
    // Botón Pendiente (si está Pagada)
    if (estado === 'Pagada'){
      html += '<button onclick="_gpCambiarEstado('+p.id+',&quot;Pendiente&quot;)" title="Revertir a Pendiente" style="background:var(--cx-accent-dark);color:var(--cx-warn-text);border:0;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px;margin-right:3px">↩</button>';
    }
    html += '<button onclick="_gpEditarValor('+p.id+','+(p.valor||0)+')" title="Editar valor/concepto" style="background:var(--cx-info-pale);color:#fff;border:0;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px;margin-right:3px">✏</button>';
    html += '<button onclick="_gpEliminar('+p.id+')" title="Eliminar este registro" style="background:var(--cx-danger);color:#fecaca;border:0;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px">🗑</button>';
    html += '</td></tr>';
  }
  tbody.innerHTML = html;
}
async function _gpCambiarEstado(pagoId, nuevoEstado){
  const motivo = prompt('Motivo del cambio a "'+nuevoEstado+'" (mínimo 10 caracteres · queda en audit INVIMA):');
  if (!motivo || motivo.trim().length < 10){ alert('Motivo requerido (≥10 caracteres)'); return; }
  await _gpEnviarPatch(pagoId, {estado: nuevoEstado, motivo: motivo.trim()});
}
async function _gpEditarValor(pagoId, valorActual){
  const nuevoStr = prompt('Nuevo valor (COP) · actual: '+valorActual+':', valorActual);
  if (nuevoStr === null) return;
  const nuevoVal = parseFloat(nuevoStr);
  if (isNaN(nuevoVal) || nuevoVal < 0){ alert('Valor inválido'); return; }
  const motivo = prompt('Motivo del ajuste (≥10 caracteres · INVIMA):');
  if (!motivo || motivo.trim().length < 10){ alert('Motivo requerido (≥10 caracteres)'); return; }
  await _gpEnviarPatch(pagoId, {valor: nuevoVal, motivo: motivo.trim()});
}
async function _gpEliminar(pagoId){
  if (!confirm('¿Eliminar este registro de pago? · NO se puede deshacer.')) return;
  const motivo = prompt('Motivo de la eliminación (≥10 caracteres · INVIMA):');
  if (!motivo || motivo.trim().length < 10){ alert('Motivo requerido (≥10 caracteres)'); return; }
  const csrf = await _ensureCsrfMkt();
  try {
    const r = await fetch('/api/marketing/pagos-influencer/'+pagoId, {
      method:'DELETE', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},
      body: JSON.stringify({motivo: motivo.trim()})
    });
    const d = await r.json();
    if (r.ok && d.ok){
      const alert = document.getElementById('gp-alert');
      alert.style.display='block'; alert.style.background='#064e3b'; alert.style.color='#86efac';
      alert.textContent = '✓ Pago eliminado · audit registrado';
      // Recargar lista del modal
      const infId = parseInt(document.getElementById('gp-inf-id').value);
      const infNombre = document.getElementById('gp-inf-nombre').textContent;
      // Invalidar cache y recargar
      if (typeof loadPagosInfluencers === 'function') await loadPagosInfluencers();
      await _cargarGestionarPagos(infId, infNombre);
      // Refrescar tabla influencers en background
      if (typeof loadInfluencers === 'function') setTimeout(loadInfluencers, 500);
    } else {
      const alert = document.getElementById('gp-alert');
      alert.style.display='block'; alert.style.background='#7f1d1d'; alert.style.color='#fecaca';
      alert.textContent = 'Error '+r.status+': '+(d.error||'desconocido');
    }
  } catch(e){
    alert('Error red: '+e.message);
  }
}
async function _gpEnviarPatch(pagoId, body){
  const csrf = await _ensureCsrfMkt();
  try {
    const r = await fetch('/api/marketing/pagos-influencer/'+pagoId, {
      method:'PATCH', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},
      body: JSON.stringify(body)
    });
    const d = await r.json();
    if (r.ok && d.ok){
      const alert = document.getElementById('gp-alert');
      alert.style.display='block'; alert.style.background='#064e3b'; alert.style.color='#86efac';
      alert.textContent = '✓ Actualizado · audit registrado';
      const infId = parseInt(document.getElementById('gp-inf-id').value);
      const infNombre = document.getElementById('gp-inf-nombre').textContent;
      if (typeof loadPagosInfluencers === 'function') await loadPagosInfluencers();
      await _cargarGestionarPagos(infId, infNombre);
      if (typeof loadInfluencers === 'function') setTimeout(loadInfluencers, 500);
    } else {
      const alert = document.getElementById('gp-alert');
      alert.style.display='block'; alert.style.background='#7f1d1d'; alert.style.color='#fecaca';
      alert.textContent = 'Error '+r.status+': '+(d.error||'desconocido');
    }
  } catch(e){
    alert('Error red: '+e.message);
  }
}
async function _ensureCsrfMkt(){
  if (window._csrfTok) return window._csrfTok;
  try {
    const r = await fetch('/api/csrf-token', {credentials:'same-origin'});
    if (r.ok){ const d = await r.json(); window._csrfTok = d.csrf_token || ''; }
  } catch(_){}
  return window._csrfTok || '';
}

function solicitarPagoInf(id, nombre, tarifa, banco, cuenta, cedula, tipoCta) {
  document.getElementById('pago-inf-id').value = id;
  document.getElementById('pago-inf-nombre').textContent = nombre;
  document.getElementById('pago-valor').value = tarifa||'';
  document.getElementById('pago-concepto').value = '';
  document.getElementById('pago-entregable').value = '';
  var _lpReset=document.getElementById('pago-link-post'); if(_lpReset) _lpReset.value='';
  // Default fecha de publicaci\u00f3n = hoy \u00b7 usuario ajusta al d\u00eda real que public\u00f3
  const hoy = new Date();
  const todayStr = hoy.getFullYear()+'-'+String(hoy.getMonth()+1).padStart(2,'0')+'-'+String(hoy.getDate()).padStart(2,'0');
  const fc = document.getElementById('pago-fecha-contenido');
  if (fc && !fc.value) fc.value = todayStr;
  recalcularVencePagoInf();
  const prev = document.getElementById('pago-banco-preview');
  if(banco) {
    // FIX 7-jul (audit ultracode \u00b7 XSS almacenado): escapar los datos del influencer antes de innerHTML (un
    // nombre/banco con <img onerror=...> ejecutar\u00eda al abrir el modal). _escHtml ya se usa en todo el archivo.
    prev.innerHTML = '<b>Beneficiario:</b> '+_escHtml(nombre)+'<br>'
      +'<b>Banco:</b> '+_escHtml(banco)+'<br>'
      +'<b>Tipo:</b> '+_escHtml(tipoCta||'Ahorros')+'<br>'
      +'<b>Cuenta/Cel:</b> '+_escHtml(cuenta||'\u2014')+'<br>'
      +'<b>C\u00e9dula/NIT:</b> '+_escHtml(cedula||'\u2014');
  } else {
    prev.innerHTML = '<span style="color:var(--cx-warn-text);">\u26a0\ufe0f Sin datos bancarios. Edita el influencer primero.</span>';
  }
  document.getElementById('pago-inf-alert').style.display='none';
  document.getElementById('modal-inf-pago').classList.add('open');
}

async function confirmarPagoInf() {
  const id = document.getElementById('pago-inf-id').value;
  const valor = parseFloat(document.getElementById('pago-valor').value)||0;
  const concepto = document.getElementById('pago-concepto').value.trim()||'Cuenta de cobro influencer';
  const nombreInf = document.getElementById('pago-inf-nombre').textContent || '';
  if(!valor) { showAlert('pago-inf-alert','Ingresa el valor a pagar','error'); return; }
  // Rediseño 13-jul (Sebastián) · EXIGIR fecha de publicación real + de qué trató el
  // contenido → fluye a la tarjeta de pago en Compras para verificar que se hizo antes de pagar.
  const fechaPub   = document.getElementById('pago-fecha-contenido').value;  // fecha de publicación (única)
  const entregTxt  = document.getElementById('pago-entregable').value.trim();
  const linkPost   = (document.getElementById('pago-link-post')||{value:''}).value.trim();
  if(!fechaPub){ showAlert('pago-inf-alert','Indicá la fecha en que el creador publicó','error'); return; }
  if(!entregTxt){ showAlert('pago-inf-alert','Indicá de qué trató el contenido (entregable)','error'); return; }
  const entregable = entregTxt + (linkPost ? ' · ' + linkPost : '');
  const fechaCont  = fechaPub;  // la promesa de 30d se cuenta desde la publicación
  // FIX 27-may-2026 PM · Sebastián/Jefferson · "cuando solicita un pago desde
  // marketing no sabe si estan quedando guardados". Antes el showAlert
  // transitorio + cerrar modal hacía que pareciera que no quedó · ahora:
  //  1) botón con spinner "Procesando..." mientras espera
  //  2) success modal prominente con número GRANDE visible
  //  3) auto-refresh tabla influencers · el ⏳ aparece inmediato
  const btn = document.querySelector('#modal-inf-pago .btn-primary');
  let btnTxt = '';
  if (btn) { btnTxt = btn.textContent; btn.disabled = true; btn.textContent = '⏳ Procesando...'; }
  try {
    // Asegurar token CSRF real antes de enviar (mismo patrón que cmoDecidir/bulk)
    if(!window._csrfTok){ try{ const tr=await fetch('/api/csrf-token',{credentials:'same-origin'}); if(tr.ok){ const td=await tr.json(); window._csrfTok=td.csrf_token||''; } }catch(_){} }
    // FIX 7-jul (idempotencia): token estable por envío (mismo en doble-click/retry) · se limpia al éxito.
    window._pagoInfTok = window._pagoInfTok || (crypto.randomUUID ? crypto.randomUUID() : String(Date.now())+'-'+Math.random());
    const resp = await fetch(`/api/marketing/influencers/${id}/solicitar-pago`,_fetchOpts('POST', {valor, concepto, fecha_publicacion:fechaPub, entregable, fecha_contenido:fechaCont, solicitud_id: window._pagoInfTok}));
    const data = await resp.json();
    if(data.ok) {
      window._pagoInfTok=null;
      closeModal('modal-inf-pago');
      // Mostrar modal de confirmación prominente
      _mostrarPagoSolicitadoOk({
        numero: data.numero,
        monto: (data.monto || valor),
        nombre: nombreInf,
        concepto: concepto,
      });
      // Refrescar tabla + cache de pagos inmediatamente · badge ⏳ aparece
      try { if(typeof loadPagosInfluencers === 'function') await loadPagosInfluencers(); } catch(_){}
      try { if(typeof cargarPagosInfluencers === 'function') cargarPagosInfluencers(); } catch(_){}
      loadInfluencers();
    } else {
      showAlert('pago-inf-alert', data.error||'Error al crear solicitud','error');
    }
  } catch(e){
    showAlert('pago-inf-alert', 'Error de red: '+e.message,'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = btnTxt || '💸 Solicitar pago'; }
  }
}
// Modal de confirmación prominente · Jefferson sabe que QUEDÓ GUARDADO
function _mostrarPagoSolicitadoOk(d){
  // Crear el modal dinámicamente (solo cuando hace falta)
  let m = document.getElementById('modal-pago-ok');
  if (!m){
    m = document.createElement('div');
    m.id = 'modal-pago-ok';
    m.className = 'modal-bg';
    m.innerHTML =
      '<div class="modal" style="max-width:540px;">'
      + '<div style="text-align:center;padding:18px 6px 8px;">'
      + '<div style="font-size:54px;line-height:1">✅</div>'
      + '<div style="font-size:18px;font-weight:800;color:var(--cx-success-text);margin-top:6px">Solicitud creada y guardada</div>'
      + '<div id="mpo-numero" style="font-family:monospace;font-size:22px;font-weight:800;color:var(--cx-primary-text);background:var(--cx-primary-soft);border:1.5px solid #4338ca;border-radius:10px;padding:10px 16px;margin:12px auto;display:inline-block"></div>'
      + '<div style="font-size:13px;color:var(--cx-text-soft);line-height:1.6;text-align:left;background:var(--cx-bg-alt);border-radius:8px;padding:12px 14px;margin:10px 14px">'
      + '<div><b style="color:var(--cx-text-mute)">Influencer:</b> <span id="mpo-nombre"></span></div>'
      + '<div><b style="color:var(--cx-text-mute)">Monto:</b> <span id="mpo-monto" style="color:var(--cx-warn-text);font-weight:700"></span></div>'
      + '<div><b style="color:var(--cx-text-mute)">Concepto:</b> <span id="mpo-concepto"></span></div>'
      + '<div style="margin-top:8px;border-top:1px solid var(--cx-border);padding-top:8px;color:var(--cx-primary-text)">'
      + '📌 Ya quedó visible para Sebastián en <b>/compras → tab Influencers</b>. '
      + 'Cuando pague vas a recibir notificación in-app. También aparece ahora en tu tabla con el badge ⏳.'
      + '</div></div>'
      + '<div style="display:flex;gap:10px;justify-content:center;margin:8px 14px 14px">'
      + '<button class="btn btn-primary" onclick="closeModal(\'modal-pago-ok\')" style="min-width:140px">OK, entendido</button>'
      + '</div></div></div>';
    document.body.appendChild(m);
  }
  document.getElementById('mpo-numero').textContent = d.numero || '(sin número)';
  document.getElementById('mpo-nombre').textContent = d.nombre || '-';
  document.getElementById('mpo-monto').textContent = '$' + (d.monto||0).toLocaleString('es-CO') + ' COP';
  document.getElementById('mpo-concepto').textContent = d.concepto || '-';
  m.classList.add('open');
}


// ──────────────────────────────────────────────────────────────────────────────
// CONTENIDO
// ──────────────────────────────────────────────────────────────────────────────
// ─── Kanban de Contenido ───────────────────────────────────────────────
async function loadContenido() {
  try {
    const r = await fetch('/api/marketing/contenido/kanban');
    const d = await r.json();
    if (!d.ok) {
      showAlert('cont-alert', 'Error: ' + (d.error||'desconocido'), 'error');
      return;
    }
    const cols = d.columnas || [];
    cols.forEach(col => {
      const target = document.getElementById('kb-' + col.estado);
      const counter = document.getElementById('kb-c-' + col.estado);
      if (counter) counter.textContent = col.count;
      if (!target) return;
      if (!col.items.length) {
        target.innerHTML = '<div class="kanban-empty">Sin contenido</div>';
        return;
      }
      target.innerHTML = col.items.map(it => renderKanbanCard(it)).join('');
    });
  } catch (e) {
    showAlert('cont-alert', 'Error de red: ' + e.message, 'error');
  }
}

function renderKanbanCard(it) {
  const sku = it.sku_objetivo ? `<div class="sku">${esc(it.sku_objetivo)}</div>` : '';
  const titulo = it.mensaje_principal || it.caption || '(sin mensaje)';
  const tituloShort = titulo.length > 90 ? titulo.slice(0,90)+'…' : titulo;
  const meta = [];
  if (it.tipo) meta.push(`<span>${esc(it.tipo)}</span>`);
  if (it.plataforma && it.plataforma !== 'Instagram') meta.push(`<span>${esc(it.plataforma)}</span>`);
  if (it.influencer_nombre) {
    const code = it.influencer_code ? ` · <code style="color:var(--cx-success-text);">${esc(it.influencer_code)}</code>` : '';
    meta.push(`<span>👤 ${esc(it.influencer_nombre)}${code}</span>`);
  }
  if (it.campana_nombre) meta.push(`<span>📢 ${esc(it.campana_nombre)}</span>`);
  if (it.fecha_programada) meta.push(`<span>📅 ${esc(it.fecha_programada)}</span>`);
  if (it.fecha_publicacion && it.estado === 'Publicado') meta.push(`<span>✅ ${esc(it.fecha_publicacion)}</span>`);

  let perf = '';
  if (it.estado === 'Performance' || it.estado === 'Publicado') {
    const stats = [];
    if (it.likes) stats.push(`❤️ <b>${fmt(it.likes)}</b>`);
    if (it.comentarios) stats.push(`💬 <b>${fmt(it.comentarios)}</b>`);
    if (it.alcance) stats.push(`👁 <b>${fmt(it.alcance)}</b>`);
    if (it.impresiones) stats.push(`📊 <b>${fmt(it.impresiones)}</b>`);
    if (it.guardados) stats.push(`🔖 <b>${fmt(it.guardados)}</b>`);
    // AUDIT 26-may · marca de origen métricas · IG live = automático del Graph API
    const fuenteBadge = it.ig_match
      ? `<span style="background:var(--cx-info-pale);color:var(--cx-info-text);padding:1px 6px;border-radius:6px;font-size:9px;font-weight:700;margin-right:6px" title="Métricas auto-sincronizadas desde Instagram Graph API${it.ig_synced_at?' · sync '+esc(it.ig_synced_at):''}">📡 IG LIVE</span>`
      : (it.url_publicacion && it.estado === 'Publicado'
          ? `<span style="background:#7c2d12;color:#fdba74;padding:1px 6px;border-radius:6px;font-size:9px;font-weight:700;margin-right:6px" title="Esta pieza tiene URL pero no hay match en posts IG sincronizados · refresca IG en Dashboard ↻">⚠ sin sync IG</span>`
          : '');
    if (stats.length || fuenteBadge) perf = `<div class="perf">${fuenteBadge}${stats.join(' · ')}</div>`;
  }

  let urlBtn = '';
  if (it.url_publicacion) {
    urlBtn = `<a href="${escUrl(it.url_publicacion)}" target="_blank" rel="noopener noreferrer" style="color:var(--cx-info-text);font-size:11px;text-decoration:none;margin-right:8px;" onclick="event.stopPropagation();">🔗 Ver post</a>`;
  }

  return `<div class="kanban-card" onclick="editContenido(${it.id})">
    ${sku}
    <div class="titulo">${esc(tituloShort)}</div>
    <div class="meta">${meta.join('')}</div>
    ${perf}
    <div style="margin-top:6px;display:flex;justify-content:space-between;align-items:center;">
      ${urlBtn}
      <span style="margin-left:auto;">${kanbanMoveButtons(it)}</span>
    </div>
  </div>`;
}

function kanbanMoveButtons(it) {
  const seq = ['Brief','Produccion','Pendiente','Publicado','Performance'];
  const idx = seq.indexOf(it.estado_kanban || it.estado);
  let html = '';
  if (idx > 0) html += `<button onclick="event.stopPropagation();moveContenido(${it.id},'${seq[idx-1]}')" title="← ${seq[idx-1]}" style="background:none;border:none;color:var(--cx-text-mute);cursor:pointer;padding:2px 4px;font-size:13px;">←</button>`;
  if (idx >= 0 && idx < seq.length-1) html += `<button onclick="event.stopPropagation();moveContenido(${it.id},'${seq[idx+1]}')" title="→ ${seq[idx+1]}" style="background:none;border:none;color:var(--cx-primary-text);cursor:pointer;padding:2px 4px;font-size:13px;">→</button>`;
  return html;
}

async function moveContenido(id, nuevoEstado) {
  try {
    const r = await fetch(`/api/marketing/contenido/${id}`, _fetchOpts('PUT', {estado: nuevoEstado}));
    const d = await r.json();
    if (d.ok) {
      loadContenido();
    } else {
      showAlert('cont-alert', 'Error: ' + (d.error||'no se pudo mover'), 'error');
    }
  } catch (e) {
    showAlert('cont-alert', 'Error de red: ' + e.message, 'error');
  }
}

async function openContenidoModal(estadoInicial) {
  document.getElementById('cont-edit-id').value='';
  document.getElementById('modal-cont-title').textContent='Nueva pieza de contenido';
  ['url','caption','sku','mensaje'].forEach(f=>{const el=document.getElementById('cont-'+f);if(el)el.value='';});
  ['likes','comentarios','alcance','conversiones'].forEach(f=>document.getElementById('cont-'+f).value=0);
  document.getElementById('cont-fecha').value='';
  const fp = document.getElementById('cont-fecha-prog'); if(fp) fp.value='';
  document.getElementById('cont-tipo').value='Reel';
  document.getElementById('cont-plataforma').value='Instagram';
  document.getElementById('cont-estado').value = (typeof estadoInicial === 'string' ? estadoInicial : 'Brief');
  await loadCampanasForSelect('cont-campana-sel');
  await loadInfluencersForSelect('cont-influencer-sel');
  document.getElementById('modal-contenido').classList.add('open');
}

async function editContenido(id) {
  const r_ = await fetch('/api/marketing/contenido/kanban').then(r=>r.json());
  let r = null;
  for (const col of (r_.columnas||[])) {
    const found = (col.items||[]).find(x=>x.id===id);
    if (found) { r = found; break; }
  }
  if(!r) return;
  document.getElementById('cont-edit-id').value=id;
  document.getElementById('modal-cont-title').textContent='Editar contenido';
  document.getElementById('cont-url').value=r.url_publicacion||'';
  document.getElementById('cont-caption').value=r.caption||'';
  const sku = document.getElementById('cont-sku'); if(sku) sku.value = r.sku_objetivo||'';
  const mens = document.getElementById('cont-mensaje'); if(mens) mens.value = r.mensaje_principal||'';
  const fp = document.getElementById('cont-fecha-prog'); if(fp) fp.value = r.fecha_programada||'';
  document.getElementById('cont-likes').value=r.likes||0;
  document.getElementById('cont-comentarios').value=r.comentarios||0;
  document.getElementById('cont-alcance').value=r.alcance||0;
  document.getElementById('cont-conversiones').value=r.conversiones||0;
  document.getElementById('cont-fecha').value=r.fecha_publicacion||'';
  document.getElementById('cont-tipo').value=r.tipo||'Reel';
  document.getElementById('cont-plataforma').value=r.plataforma||'Instagram';
  document.getElementById('cont-estado').value=(r.estado_kanban||r.estado||'Brief');
  await loadCampanasForSelect('cont-campana-sel');
  await loadInfluencersForSelect('cont-influencer-sel');
  if(r.campana_id) document.getElementById('cont-campana-sel').value=r.campana_id;
  if(r.influencer_id) document.getElementById('cont-influencer-sel').value=r.influencer_id;
  document.getElementById('modal-contenido').classList.add('open');
}

async function saveContenido() {
  const id = document.getElementById('cont-edit-id').value;
  const campSel = document.getElementById('cont-campana-sel').value;
  const infSel = document.getElementById('cont-influencer-sel').value;
  const body = {
    tipo: document.getElementById('cont-tipo').value,
    plataforma: document.getElementById('cont-plataforma').value,
    campana_id: campSel ? parseInt(campSel) : null,
    influencer_id: infSel ? parseInt(infSel) : null,
    fecha_publicacion: document.getElementById('cont-fecha').value||null,
    fecha_programada: (document.getElementById('cont-fecha-prog')||{value:''}).value||'',
    estado: document.getElementById('cont-estado').value,
    sku_objetivo: ((document.getElementById('cont-sku')||{value:''}).value||'').trim().toUpperCase(),
    mensaje_principal: ((document.getElementById('cont-mensaje')||{value:''}).value||'').trim(),
    url_publicacion: document.getElementById('cont-url').value.trim(),
    caption: document.getElementById('cont-caption').value.trim(),
    likes: parseInt(document.getElementById('cont-likes').value)||0,
    comentarios: parseInt(document.getElementById('cont-comentarios').value)||0,
    alcance: parseInt(document.getElementById('cont-alcance').value)||0,
    conversiones: parseInt(document.getElementById('cont-conversiones').value)||0,
  };
  // Validación cliente · URL no puede ser javascript:/data:
  if(body.url_publicacion){
    const lo = body.url_publicacion.toLowerCase();
    if(lo.startsWith('javascript:') || lo.startsWith('data:') || lo.startsWith('vbscript:')){
      showAlert('cont-alert','URL inválida','error'); return;
    }
  }
  const url = id ? `/api/marketing/contenido/${id}` : '/api/marketing/contenido';
  const method = id?'PUT':'POST';
  // Fix audit 25-may: usar _csrfHdr() consistente con campañas e influencers
  let resp, data;
  try {
    resp = await fetch(url,{method, headers:_csrfHdr(), credentials:'same-origin', body:JSON.stringify(body)});
    data = await resp.json().catch(()=>({error:'Respuesta no es JSON ('+resp.status+')'}));
  } catch(e){
    showAlert('cont-alert','Error red: '+e.message,'error'); return;
  }
  if(resp.ok && (data.ok||data.id)) { closeModal('modal-contenido'); showAlert('cont-alert',id?'Contenido actualizado':'Contenido registrado'); loadContenido(); }
  else showAlert('cont-alert',data.error||('Error HTTP '+resp.status),'error');
}

async function deleteContenido(id) {
  if(!confirm('¿Eliminar esta pieza de contenido?')) return;
  let resp, data;
  try {
    resp = await fetch(`/api/marketing/contenido/${id}`,_fetchOpts('DELETE'));
    data = await resp.json().catch(()=>({error:'Respuesta no es JSON ('+resp.status+')'}));
  } catch(e){
    showAlert('cont-alert','Error red: '+e.message,'error'); return;
  }
  if(resp.ok && data.ok) { showAlert('cont-alert','Contenido eliminado'); loadContenido(); }
  else showAlert('cont-alert', data.error||('Error HTTP '+resp.status), 'error');
}

// ──────────────────────────────────────────────────────────────────────────────
// HELPERS - SELECT POPULATES
// ──────────────────────────────────────────────────────────────────────────────
async function loadCampanasForSelect(selId='brief-campana-sel') {
  let camps = [];
  try {
    const r = await fetch('/api/marketing/campanas', {credentials:'same-origin'});
    if(r.ok) camps = await r.json();
  } catch(_){}
  if(!Array.isArray(camps)) camps = [];
  const sel = document.getElementById(selId);
  if(!sel) return;
  const current = sel.value;
  sel.innerHTML = '<option value="">Sin campaña</option>' +
    camps.map(c=>`<option value="${parseInt(c.id)||0}">${esc(c.nombre||'')}</option>`).join('');
  if(current) sel.value=current;
}
async function loadInfluencersForSelect(selId) {
  let infs = [];
  try {
    const r = await fetch('/api/marketing/influencers', {credentials:'same-origin'});
    if(r.ok) infs = await r.json();
  } catch(_){}
  if(!Array.isArray(infs)) infs = [];
  const sel = document.getElementById(selId);
  if(!sel) return;
  const current = sel.value;
  sel.innerHTML = '<option value="">Sin influencer (interno)</option>' +
    infs.map(i=>`<option value="${parseInt(i.id)||0}">${esc(i.nombre||'')} (${esc(i.red_social||'')})</option>`).join('');
  if(current) sel.value=current;
}

// ──────────────────────────────────────────────────────────────────────────────
// AGENTES IA
// ──────────────────────────────────────────────────────────────────────────────
const AGENT_LABELS = {
  estacionalidad: 'Analizar estacionalidad', oportunidad: 'Detectar oportunidades',
  roi: 'Calcular ROI', tendencias: 'Ver tendencias', brief: 'Generar brief',
  pricing: 'Calcular precios promo', reorden: 'Predecir reórdenes',
  canibal: 'Detectar conflictos', contenido_auto: 'Generar contenido',
  alerta_stock: 'Ver alertas stock',
  estrategia: 'Generar estrategia del mes'
};

async function syncPlatform(platform, full) {
  const btn = document.getElementById('btn-sync-'+platform);
  const status = document.getElementById('sync-status');
  btn.disabled = true; btn.textContent = 'Sincronizando...';
  status.textContent = '';
  try {
    const resp = await fetch(`/api/marketing/sync/${platform}${full?'?full=1':''}`, _fetchOpts('POST'));
    const data = await resp.json();
    if(data.ok) {
      status.style.color = '#34d399';
      status.textContent = `✓ ${platform}: ${data.synced} registros sincronizados`;
      loadConnections();
      setTimeout(loadDashboard, 600);
    } else {
      status.style.color = '#f87171';
      let errMsg = data.error || 'Error al sincronizar';
      let det = data.detalle || '';
      // Detectar token Meta expirado (code 190) y mostrar mensaje claro
      if(det.includes('190') || det.includes('Session has expired') || det.includes('OAuthException')){
        errMsg = '🔑 Token de Instagram expirado - genera uno nuevo en developers.facebook.com/tools/explorer y pégalo abajo';
        det = '';
      } else if(det.includes('400') || det.includes('401')){
        errMsg = '🔑 Error de autenticación Meta - token inválido';
        det = '';
      } else if(det.length > 120){
        det = ' → ' + det.slice(0,120) + '...';
      } else if(det){
        det = ' → ' + det;
      }
      status.textContent = errMsg + det;
      // Si falla Instagram por auth, mostrar formulario de token
      if (platform === 'instagram') {
        document.getElementById('ig-token-form').style.display = 'block';
      }
    }
  } catch(e) {
    status.style.color = '#f87171';
    let msg = e.message || 'Error desconocido';
    if(msg.includes('<!DOCTYPE') || msg.includes('JSON')){
      msg = 'La sesión expiró - recarga la página (F5)';
    }
    status.textContent = '⚠️ ' + msg;
  } finally {
    btn.disabled = false; btn.textContent = '↻ Sync ' + (platform==='instagram'?'IG':platform.charAt(0).toUpperCase()+platform.slice(1));
  }
}

async function loadConnections() {
  try {
    const data = await fetch('/api/marketing/connections').then(r=>r.json());
    const conn = data.connected || {};
    [['shopify','shopify'],['ghl','ghl'],['instagram','ig']].forEach(([k,pid])=>{
      const el = document.getElementById('pill-'+pid);
      if(!el) return;
      el.className = 'platform-pill ' + (conn[k] ? 'pill-'+pid : 'pill-off');
    });
  } catch(e) {}
}

// ═══════════════════════════════════════════════════════════════════════
// AUDIT 26-may · Meta del mes + Calendario cosmético (sprint #4)
// ═══════════════════════════════════════════════════════════════════════

function _mesActual(){ return new Date().toISOString().substr(0,7); }

function _fmtPctBar(pct, color){
  if(pct == null) return '<span style="color:var(--cx-text-mute)">sin meta</span>';
  const cap = Math.min(pct, 100);
  const col = pct >= 100 ? '#10b981' : pct >= 70 ? '#22c55e' : pct >= 40 ? '#f59e0b' : '#ef4444';
  return `<div style="display:flex;align-items:center;gap:8px">
    <div style="flex:1;background:var(--cx-card);border-radius:4px;height:8px;overflow:hidden;min-width:60px">
      <div style="background:${col};height:100%;width:${cap}%;transition:width .3s"></div>
    </div>
    <span style="color:${col};font-weight:700;font-size:11px;min-width:46px;text-align:right">${pct}%</span>
  </div>`;
}

// AUDIT 27-may · A/B testing UI
async function openABTestsModal(){
  let modalEl = document.getElementById('modal-ab-tests');
  if(!modalEl){
    modalEl = document.createElement('div');
    modalEl.id = 'modal-ab-tests';
    modalEl.className = 'modal';
    document.body.appendChild(modalEl);
  }
  modalEl.innerHTML = `<div class="modal-content" style="max-width:880px;max-height:88vh;overflow-y:auto">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <div class="modal-title">🔬 A/B Tests · creatividades</div>
      <button class="btn btn-outline btn-sm" onclick="closeModal('modal-ab-tests')">✕</button>
    </div>
    <p style="color:var(--cx-text-mute);font-size:12px;margin-bottom:14px">
      Compará 2 piezas del Kanban para descubrir cuál convierte mejor. Score con métricas IG live (likes + comentarios×3 + alcance÷10).
    </p>
    <button class="btn btn-primary btn-sm" onclick="openABTestCrear()" style="margin-bottom:12px">+ Nuevo A/B test</button>
    <div id="ab-tests-list" style="margin-top:8px">Cargando…</div>
  </div>`;
  modalEl.classList.add('open');
  await loadABTests();
}

async function loadABTests(){
  const list = document.getElementById('ab-tests-list');
  if(!list) return;
  try {
    const r = await fetch('/api/marketing/ab-tests', {credentials:'same-origin'});
    if(!r.ok){ list.innerHTML = '<div style="color:var(--cx-danger-text)">Error '+r.status+'</div>'; return; }
    const d = await r.json();
    const tests = d.tests || [];
    if(!tests.length){
      list.innerHTML = '<div style="color:var(--cx-text-mute);padding:14px;text-align:center;background:var(--cx-bg-alt);border-radius:8px">Sin tests · creá el primero arriba</div>';
      return;
    }
    list.innerHTML = tests.map(t => {
      const gan = t.ganadora;
      const ganChip = gan === 'a'
        ? `<span style="background:var(--cx-success-pale);color:var(--cx-success-text);padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">🏆 A gana · ${t.ganadora_diff_pct}%</span>`
        : gan === 'b'
        ? `<span style="background:var(--cx-success-pale);color:var(--cx-success-text);padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">🏆 B gana · ${t.ganadora_diff_pct}%</span>`
        : gan === 'tie'
        ? `<span style="background:#3f3f46;color:var(--cx-text-faint);padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">⚖ Empate técnico</span>`
        : gan === 'indeterminado'
        ? `<span style="background:#7c2d12;color:#fdba74;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">❓ Sin data</span>`
        : `<span style="background:var(--cx-info-pale);color:var(--cx-info-text);padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">🟡 Activo</span>`;
      const aScore = (parseInt(t.a_likes)||0)+(parseInt(t.a_com)||0)*3+(parseInt(t.a_alc)||0)/10;
      const bScore = (parseInt(t.b_likes)||0)+(parseInt(t.b_com)||0)*3+(parseInt(t.b_alc)||0)/10;
      return `<div style="background:var(--cx-bg-alt);border:1px solid var(--cx-hairline);border-radius:10px;padding:14px;margin-bottom:10px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:8px">
          <div>
            <div style="font-size:14px;font-weight:700;color:var(--cx-text)">${esc(t.nombre||'')}</div>
            ${t.hipotesis?'<div style="font-size:11px;color:var(--cx-text-mute);margin-top:2px">'+esc(t.hipotesis)+'</div>':''}
            <div style="font-size:10px;color:var(--cx-text-mute);margin-top:4px">Métrica: <b>${esc(t.metrica_objetivo||'engagement')}</b> · creado ${esc((t.fecha_creacion||'').slice(0,10))}</div>
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
            ${ganChip}
            <button class="btn btn-outline btn-sm" onclick="calcularGanadorAB(${t.id})" style="font-size:10px;padding:2px 8px">🔄 Recalcular</button>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px">
          <div style="background:${gan==='a'?'#064e3b':'#f1f5f9'};padding:10px;border-radius:8px;border:${gan==='a'?'2px solid #10b981':'1px solid #e7e5e4'}">
            <div style="font-size:10px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.5px">Pieza A · #${t.contenido_a_id}</div>
            <div style="display:flex;gap:8px;font-size:11px;margin-top:4px"><span>❤️ ${parseInt(t.a_likes)||0}</span><span>💬 ${parseInt(t.a_com)||0}</span><span>👁 ${parseInt(t.a_alc)||0}</span></div>
            <div style="font-size:11px;color:${gan==='a'?'#34d399':'#94a3b8'};margin-top:4px;font-weight:700">Score: ${Math.round(aScore)}</div>
          </div>
          <div style="background:${gan==='b'?'#064e3b':'#f1f5f9'};padding:10px;border-radius:8px;border:${gan==='b'?'2px solid #10b981':'1px solid #e7e5e4'}">
            <div style="font-size:10px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.5px">Pieza B · #${t.contenido_b_id}</div>
            <div style="display:flex;gap:8px;font-size:11px;margin-top:4px"><span>❤️ ${parseInt(t.b_likes)||0}</span><span>💬 ${parseInt(t.b_com)||0}</span><span>👁 ${parseInt(t.b_alc)||0}</span></div>
            <div style="font-size:11px;color:${gan==='b'?'#34d399':'#94a3b8'};margin-top:4px;font-weight:700">Score: ${Math.round(bScore)}</div>
          </div>
        </div>
      </div>`;
    }).join('');
  } catch(e){ list.innerHTML = '<div style="color:var(--cx-danger-text)">Error: '+esc(e.message)+'</div>'; }
}

function openABTestCrear(){
  // Modal compacto que pide los IDs y campos
  const html = `
    <div style="background:var(--cx-card);padding:14px;border-radius:8px;margin-top:12px">
      <h4 style="font-size:13px;color:var(--cx-text);margin:0 0 10px">Crear nuevo A/B test</h4>
      <div style="display:flex;flex-direction:column;gap:8px">
        <input id="ab-nombre" placeholder="Nombre del test (ej. Reel rutina vs antes/después)" style="width:100%;padding:8px;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);border-radius:6px;font-size:12px">
        <input id="ab-hipotesis" placeholder="Hipótesis · qué esperás (opcional)" style="width:100%;padding:8px;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);border-radius:6px;font-size:12px">
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
          <input id="ab-a-id" type="number" placeholder="ID pieza A" style="padding:8px;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);border-radius:6px;font-size:12px">
          <input id="ab-b-id" type="number" placeholder="ID pieza B" style="padding:8px;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);border-radius:6px;font-size:12px">
          <select id="ab-metrica" style="padding:8px;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);border-radius:6px;font-size:12px">
            <option value="engagement">Engagement</option>
            <option value="alcance">Alcance</option>
            <option value="conversiones">Conversiones</option>
          </select>
        </div>
        <div style="display:flex;gap:6px;align-items:center;margin-top:6px">
          <button class="btn btn-primary btn-sm" onclick="saveABTest()">✓ Crear</button>
          <span id="ab-crear-status" style="font-size:11px;color:var(--cx-success-text)"></span>
        </div>
        <div style="font-size:10px;color:var(--cx-text-mute);margin-top:6px">
          💡 Los IDs de las piezas los ves en la URL al hacer click en una card del Kanban, o en el botón "✏️ Editar"
        </div>
      </div>
    </div>`;
  const list = document.getElementById('ab-tests-list');
  if(list) list.insertAdjacentHTML('afterbegin', html);
}

async function saveABTest(){
  const body = {
    nombre: document.getElementById('ab-nombre').value.trim(),
    hipotesis: document.getElementById('ab-hipotesis').value.trim(),
    contenido_a_id: parseInt(document.getElementById('ab-a-id').value)||0,
    contenido_b_id: parseInt(document.getElementById('ab-b-id').value)||0,
    metrica_objetivo: document.getElementById('ab-metrica').value,
  };
  const status = document.getElementById('ab-crear-status');
  if(!body.nombre || !body.contenido_a_id || !body.contenido_b_id){
    status.style.color = '#ef4444';
    status.textContent = 'Nombre + ambos IDs obligatorios';
    return;
  }
  try {
    const r = await fetch('/api/marketing/ab-tests', _fetchOpts('POST', body));
    const d = await r.json();
    if(!r.ok){
      status.style.color = '#ef4444';
      status.textContent = 'Error: '+esc(d.error||r.status);
      return;
    }
    status.style.color = '#10b981';
    status.textContent = '✓ Test creado · refrescando…';
    setTimeout(()=>{ openABTestsModal(); }, 800);
  } catch(e){
    status.style.color = '#ef4444';
    status.textContent = 'Error red: '+e.message;
  }
}

async function calcularGanadorAB(tid){
  try {
    const r = await fetch('/api/marketing/ab-tests/'+tid+'/calcular-ganador', _fetchOpts('POST', {}));
    const d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    alert(d.mensaje + '\n\nConfianza: ' + d.confianza + '\nMétrica: ' + d.metrica_usada);
    loadABTests();
  } catch(e){ alert('Error red: '+e.message); }
}


async function loadMetaProgreso(){
  const el = document.getElementById('dash-meta-progreso');
  if(!el) return;
  try {
    const r = await fetch('/api/marketing/meta-progreso?mes='+_mesActual(), {credentials:'same-origin'});
    if(!r.ok){
      el.innerHTML = '<span style="color:var(--cx-danger-text)">Error HTTP '+r.status+'</span>';
      return;
    }
    const d = await r.json();
    if(!d.meta){
      el.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;gap:12px">
        <span style="color:var(--cx-text-mute)">No hay meta configurada para ${esc(d.mes)} · click "⚙ Editar meta" para crearla.</span>
        <button class="btn btn-primary btn-sm" onclick="openMetaModal()">⚙ Configurar meta</button>
      </div>`;
      return;
    }
    const fmtCOP = v => '$'+Number(v||0).toLocaleString('es-CO');
    const av = d.avance || {};
    const py = d.proyeccion_fin_de_mes || {};
    el.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <div style="font-size:12px;color:var(--cx-text-mute)">${esc(d.mes)} · ${d.dias_transcurridos}/${d.dias_mes} días</div>
        <div style="font-size:10px;color:var(--cx-text-mute)">Proyección fin de mes: <b style="color:var(--cx-primary-text)">${fmtCOP(py.revenue||0)}</b> (${py.revenue_pct_meta||0}% meta)</div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px">
        <div>
          <div style="font-size:10px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">💰 Revenue · ${fmtCOP(av.revenue)} / ${fmtCOP(d.meta.revenue)}</div>
          ${_fmtPctBar(av.revenue_pct)}
        </div>
        <div>
          <div style="font-size:10px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">📦 Pedidos · ${av.pedidos||0} / ${d.meta.pedidos||0}</div>
          ${_fmtPctBar(av.pedidos_pct)}
        </div>
        <div>
          <div style="font-size:10px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">🆕 Clientes nuevos · ${av.clientes_nuevos||0} / ${d.meta.clientes_nuevos||0}</div>
          ${_fmtPctBar(av.clientes_nuevos_pct)}
        </div>
      </div>`;
  } catch(e){
    el.innerHTML = '<span style="color:var(--cx-danger-text)">Error: '+esc(e.message)+'</span>';
  }
}

async function openMetaModal(){
  const mes = _mesActual();
  let actual = null;
  try {
    const r = await fetch('/api/marketing/metas?mes='+mes, {credentials:'same-origin'});
    if(r.ok){ const d = await r.json(); actual = d.meta; }
  } catch(_){}
  const cur = actual || {revenue_meta:0, pedidos_meta:0, clientes_nuevos_meta:0, notas:''};
  let modalEl = document.getElementById('modal-meta-mensual');
  if(!modalEl){
    modalEl = document.createElement('div');
    modalEl.id = 'modal-meta-mensual';
    modalEl.className = 'modal';
    document.body.appendChild(modalEl);
  }
  modalEl.innerHTML = `<div class="modal-content" style="max-width:520px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <div class="modal-title">🎯 Meta del mes · ${esc(mes)}</div>
      <button class="btn btn-outline btn-sm" onclick="closeModal('modal-meta-mensual')">✕</button>
    </div>
    <div style="display:flex;flex-direction:column;gap:12px">
      <div>
        <label style="display:block;font-size:11px;color:var(--cx-text-mute);margin-bottom:4px">💰 Revenue meta (COP)</label>
        <input id="meta-rev" type="number" min="0" step="100000" value="${cur.revenue_meta||0}" style="width:100%;padding:10px;background:var(--cx-card);border:1px solid var(--cx-border);color:var(--cx-text);border-radius:6px">
      </div>
      <div>
        <label style="display:block;font-size:11px;color:var(--cx-text-mute);margin-bottom:4px">📦 Pedidos meta</label>
        <input id="meta-ped" type="number" min="0" step="10" value="${cur.pedidos_meta||0}" style="width:100%;padding:10px;background:var(--cx-card);border:1px solid var(--cx-border);color:var(--cx-text);border-radius:6px">
      </div>
      <div>
        <label style="display:block;font-size:11px;color:var(--cx-text-mute);margin-bottom:4px">🆕 Clientes nuevos meta</label>
        <input id="meta-cln" type="number" min="0" step="5" value="${cur.clientes_nuevos_meta||0}" style="width:100%;padding:10px;background:var(--cx-card);border:1px solid var(--cx-border);color:var(--cx-text);border-radius:6px">
      </div>
      <div>
        <label style="display:block;font-size:11px;color:var(--cx-text-mute);margin-bottom:4px">📝 Notas (opcional)</label>
        <textarea id="meta-notas" rows="2" style="width:100%;padding:10px;background:var(--cx-card);border:1px solid var(--cx-border);color:var(--cx-text);border-radius:6px;resize:vertical">${esc(cur.notas||'')}</textarea>
      </div>
      <div id="meta-alert" style="display:none"></div>
      <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:8px">
        <button class="btn btn-outline" onclick="closeModal('modal-meta-mensual')">Cancelar</button>
        <button class="btn btn-primary" onclick="saveMetaMensual()">${actual?'Actualizar':'Crear'}</button>
      </div>
    </div>
  </div>`;
  modalEl.classList.add('open');
}

async function saveMetaMensual(){
  const mes = _mesActual();
  const body = {
    mes: mes,
    revenue_meta: parseFloat(document.getElementById('meta-rev').value)||0,
    pedidos_meta: parseInt(document.getElementById('meta-ped').value)||0,
    clientes_nuevos_meta: parseInt(document.getElementById('meta-cln').value)||0,
    notas: document.getElementById('meta-notas').value||'',
  };
  if(body.revenue_meta < 0 || body.pedidos_meta < 0 || body.clientes_nuevos_meta < 0){
    document.getElementById('meta-alert').innerHTML = '<div style="color:var(--cx-danger-text);font-size:12px">Valores no pueden ser negativos</div>';
    document.getElementById('meta-alert').style.display = 'block';
    return;
  }
  try {
    const r = await fetch('/api/marketing/metas', _fetchOpts('POST', body));
    const d = await r.json().catch(()=>({}));
    if(r.ok && d.ok){
      closeModal('modal-meta-mensual');
      showToast('Meta de '+mes+' guardada','success');
      loadMetaProgreso();
    } else {
      document.getElementById('meta-alert').innerHTML = '<div style="color:var(--cx-danger-text);font-size:12px">Error: '+esc(d.error||('HTTP '+r.status))+'</div>';
      document.getElementById('meta-alert').style.display = 'block';
    }
  } catch(e){
    document.getElementById('meta-alert').innerHTML = '<div style="color:var(--cx-danger-text);font-size:12px">Error red: '+esc(e.message)+'</div>';
    document.getElementById('meta-alert').style.display = 'block';
  }
}

async function openCalendarioCosmeticoModal(){
  let modalEl = document.getElementById('modal-cal-cosm');
  if(!modalEl){
    modalEl = document.createElement('div');
    modalEl.id = 'modal-cal-cosm';
    modalEl.className = 'modal';
    document.body.appendChild(modalEl);
  }
  modalEl.innerHTML = `<div class="modal-content" style="max-width:760px;max-height:85vh;overflow-y:auto">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <div class="modal-title">📅 Calendario cosmético editable</div>
      <button class="btn btn-outline btn-sm" onclick="closeModal('modal-cal-cosm')">✕</button>
    </div>
    <div style="font-size:11px;color:var(--cx-text-mute);margin-bottom:10px">
      Eventos cosméticos que los agentes IA usan para calcular demanda proyectada · multiplicador = factor vs día normal (Black Friday típico 3.5).
    </div>
    <div id="cal-cosm-list" style="margin-bottom:14px">Cargando…</div>
    <div style="border-top:1px solid var(--cx-border);padding-top:12px">
      <div style="font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">➕ Agregar evento</div>
      <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr auto;gap:8px;align-items:end">
        <div><label style="font-size:10px;color:var(--cx-text-mute)">Evento</label><input id="cal-nuevo-evento" placeholder="Ej. Black Friday Animus" style="width:100%;padding:6px 8px;background:var(--cx-card);border:1px solid var(--cx-border);color:var(--cx-text);border-radius:6px;font-size:12px"></div>
        <div><label style="font-size:10px;color:var(--cx-text-mute)">Fecha</label><input id="cal-nuevo-fecha" type="date" style="width:100%;padding:6px 8px;background:var(--cx-card);border:1px solid var(--cx-border);color:var(--cx-text);border-radius:6px;font-size:12px"></div>
        <div><label style="font-size:10px;color:var(--cx-text-mute)">Multiplicador</label><input id="cal-nuevo-mult" type="number" step="0.1" min="0.1" max="10" value="2.0" style="width:100%;padding:6px 8px;background:var(--cx-card);border:1px solid var(--cx-border);color:var(--cx-text);border-radius:6px;font-size:12px"></div>
        <div><label style="font-size:10px;color:var(--cx-text-mute)">Color</label><input id="cal-nuevo-color" type="color" value="#a78bfa" style="width:100%;height:32px;padding:0;border:1px solid var(--cx-border);border-radius:6px;background:var(--cx-card)"></div>
        <button class="btn btn-primary btn-sm" onclick="addEventoCalendario()">+ Agregar</button>
      </div>
      <div id="cal-cosm-alert" style="margin-top:8px"></div>
    </div>
  </div>`;
  modalEl.classList.add('open');
  await loadEventosCalendario();
}

async function loadEventosCalendario(){
  const list = document.getElementById('cal-cosm-list');
  if(!list) return;
  try {
    const r = await fetch('/api/marketing/eventos-calendario?incluir_inactivos=1', {credentials:'same-origin'});
    if(!r.ok){ list.innerHTML = '<span style="color:var(--cx-danger-text)">Error '+r.status+'</span>'; return; }
    const d = await r.json();
    const evs = d.eventos || [];
    if(!evs.length){ list.innerHTML = '<div style="color:var(--cx-text-mute);padding:14px;text-align:center">Sin eventos · agrega el primero abajo</div>'; return; }
    list.innerHTML = '<table style="width:100%;font-size:12px;border-collapse:collapse"><thead><tr style="color:var(--cx-text-mute);font-weight:700;text-align:left"><th style="padding:6px;border-bottom:1px solid var(--cx-border)">Evento</th><th style="padding:6px;border-bottom:1px solid var(--cx-border)">Fecha</th><th style="padding:6px;border-bottom:1px solid var(--cx-border)">×Mult.</th><th style="padding:6px;border-bottom:1px solid var(--cx-border)">Color</th><th style="padding:6px;border-bottom:1px solid var(--cx-border);text-align:center">Activo</th><th style="padding:6px;border-bottom:1px solid var(--cx-border);text-align:right">Acción</th></tr></thead><tbody>'
      + evs.map(e => `<tr style="border-bottom:1px solid var(--cx-hairline);${e.activo?'':'opacity:.45'}">
        <td style="padding:6px">${esc(e.evento)}</td>
        <td style="padding:6px;font-family:monospace;color:var(--cx-text-mute)">${esc(e.fecha)}</td>
        <td style="padding:6px"><span style="background:var(--cx-primary-soft);color:var(--cx-primary-text);padding:1px 6px;border-radius:6px;font-weight:700">${e.multiplicador}×</span></td>
        <td style="padding:6px"><div style="width:24px;height:18px;background:${esc(e.color||'#94a3b8')};border-radius:3px;border:1px solid var(--cx-border)"></div></td>
        <td style="padding:6px;text-align:center">${e.activo?'✓':'-'}</td>
        <td style="padding:6px;text-align:right">
          ${e.activo
            ? `<button class="btn btn-danger btn-sm" onclick="toggleEventoCal(${parseInt(e.id)||0}, 0)" style="font-size:10px;padding:2px 8px" title="Desactivar">🗑</button>`
            : `<button class="btn btn-outline btn-sm" onclick="toggleEventoCal(${parseInt(e.id)||0}, 1)" style="font-size:10px;padding:2px 8px" title="Reactivar">↻</button>`}
        </td>
      </tr>`).join('')
      + '</tbody></table>';
  } catch(e){ list.innerHTML = '<span style="color:var(--cx-danger-text)">Error: '+esc(e.message)+'</span>'; }
}

async function toggleEventoCal(id, activo){
  if(activo === 0 && !confirm('¿Desactivar este evento? Los agentes ya no lo considerarán.')) return;
  try {
    const r = activo === 0
      ? await fetch('/api/marketing/eventos-calendario/'+id, _fetchOpts('DELETE'))
      : await fetch('/api/marketing/eventos-calendario/'+id, _fetchOpts('PUT', {activo: true}));
    const d = await r.json().catch(()=>({}));
    if(!r.ok){
      document.getElementById('cal-cosm-alert').innerHTML = '<div style="color:var(--cx-danger-text);font-size:12px">Error: '+esc(d.error||r.status)+'</div>';
      return;
    }
    loadEventosCalendario();
  } catch(e){
    document.getElementById('cal-cosm-alert').innerHTML = '<div style="color:var(--cx-danger-text);font-size:12px">Error red: '+esc(e.message)+'</div>';
  }
}

async function addEventoCalendario(){
  const ev = document.getElementById('cal-nuevo-evento').value.trim();
  const fc = document.getElementById('cal-nuevo-fecha').value;
  const mult = parseFloat(document.getElementById('cal-nuevo-mult').value)||1;
  const col = document.getElementById('cal-nuevo-color').value;
  const alert = document.getElementById('cal-cosm-alert');
  if(!ev || !fc){ alert.innerHTML = '<div style="color:var(--cx-danger-text);font-size:12px">Evento y fecha obligatorios</div>'; return; }
  try {
    const r = await fetch('/api/marketing/eventos-calendario', _fetchOpts('POST', {
      evento: ev, fecha: fc, multiplicador: mult, color: col
    }));
    const d = await r.json().catch(()=>({}));
    if(!r.ok){
      alert.innerHTML = '<div style="color:var(--cx-danger-text);font-size:12px">Error: '+esc(d.error||r.status)+'</div>';
      return;
    }
    alert.innerHTML = '<div style="color:var(--cx-success-text);font-size:12px">✓ Evento agregado</div>';
    document.getElementById('cal-nuevo-evento').value = '';
    document.getElementById('cal-nuevo-fecha').value = '';
    loadEventosCalendario();
    setTimeout(()=>{ alert.innerHTML = ''; }, 2000);
  } catch(e){
    alert.innerHTML = '<div style="color:var(--cx-danger-text);font-size:12px">Error red: '+esc(e.message)+'</div>';
  }
}

// ─── Feedback loop sobre agentes IA ────────────────────────────────────
let _AGENT_FEEDBACK_STATS = {};


// Sebastián 25-may-2026 PM · audit P0 · esc reforzado para XSS.
// Antes solo escapaba &<> · permitía romper atributos HTML con " y '
// (ej. nombre="<img src=x onerror=...>" en innerHTML de campañas).
// Ahora cubre los 5 caracteres peligrosos · usar en TODO innerHTML.
function esc(s) {
  return String(s||'').replace(/&/g,'&amp;')
                       .replace(/</g,'&lt;')
                       .replace(/>/g,'&gt;')
                       .replace(/"/g,'&quot;')
                       .replace(/'/g,'&#39;');
}

// Sebastián 25-may-2026 PM · audit P1 · CSRF token cache.
// Antes saveInfluencer/saveCampana hacían POST/PUT sin X-CSRF-Token.
// auth.py:365 global check de Origin/Referer ya protege · este header
// es defense in depth.
window._csrfTokMkt = '';
fetch('/api/csrf-token', {credentials:'same-origin'})
  .then(r => r.ok ? r.json() : null)
  .then(d => { if(d && d.csrf_token) window._csrfTokMkt = d.csrf_token; })
  .catch(() => {});
function _csrfHdr() {
  return {'Content-Type':'application/json', 'X-CSRF-Token': (window._csrfTokMkt||'')};
}
// Sanitiza URL · rechaza javascript:, data:, vbscript: scripts maliciosos
function escUrl(u) {
  const s = String(u||'').trim();
  if(!s) return '';
  const lc = s.toLowerCase();
  if(lc.startsWith('javascript:') || lc.startsWith('data:') ||
     lc.startsWith('vbscript:')) return '#';
  return esc(s);
}


// ──────────────────────────────────────────────────────────────────────────────
// HISTORIAL INFLUENCER
// ──────────────────────────────────────────────────────────────────────────────
function verHistorial(id, infOptional) {
  // Resolver desde cache si no llega el objeto completo (caso normal ahora)
  const inf = infOptional || _INFLUENCERS_CACHE[id];
  if (!inf) {
    showToast('Datos del influencer no disponibles. Recargá la página.', 'error');
    return;
  }
  const fmtM = v => v>=1e6?'$'+(v/1e6).toFixed(1)+'M':v>=1e3?'$'+(v/1e3).toFixed(0)+'K':'$'+Number(v||0).toLocaleString('es-CO');
  document.getElementById('hist-title').textContent = '📋 ' + (inf.nombre||'Influencer');
  const pagos  = inf.pagos || [];
  const pagadas   = pagos.filter(p=>p.estado==='Pagada');
  const pendientes= pagos.filter(p=>p.estado==='Pendiente');

  let html = '';

  // ── KPI resumen ──
  html += `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px;">
    <div style="background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:8px;padding:12px;text-align:center;">
      <div style="font-size:18px;font-weight:800;color:var(--cx-success-text);">${fmtM(inf.total_pagado||0)}</div>
      <div style="font-size:11px;color:var(--cx-text-mute);margin-top:2px;">Total pagado</div>
    </div>
    <div style="background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:8px;padding:12px;text-align:center;">
      <div style="font-size:18px;font-weight:800;color:#818cf8;">${inf.pagos_count||0}</div>
      <div style="font-size:11px;color:var(--cx-text-mute);margin-top:2px;">Colaboraciones</div>
    </div>
    <div style="background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:8px;padding:12px;text-align:center;">
      <div style="font-size:18px;font-weight:800;color:var(--cx-warn-text);">${fmtM(inf.total_pendiente||0)}</div>
      <div style="font-size:11px;color:var(--cx-text-mute);margin-top:2px;">Pendiente pago</div>
    </div>
  </div>`;

  // ── Pagos realizados ──
  if(pagadas.length) {
    html += `<div style="font-size:12px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">✅ Pagos realizados</div>
    <table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px;">
      <thead><tr style="border-bottom:1px solid var(--cx-border);">
        <th style="padding:6px 8px;text-align:left;color:var(--cx-text-mute);">Fecha</th>
        <th style="padding:6px 8px;text-align:left;color:var(--cx-text-mute);">Concepto</th>
        <th style="padding:6px 8px;text-align:right;color:var(--cx-text-mute);">Valor</th>
        <th style="padding:6px 8px;text-align:left;color:var(--cx-text-mute);">OC</th>
      </tr></thead>
      <tbody>`;
    pagadas.forEach(p=>{
      html += `<tr style="border-bottom:1px solid var(--cx-hairline);">
        <td style="padding:6px 8px;color:var(--cx-text-mute);">${p.fecha||'-'}</td>
        <td style="padding:6px 8px;">${p.concepto||'-'}</td>
        <td style="padding:6px 8px;text-align:right;color:var(--cx-success-text);font-weight:700;">${fmtM(p.valor||0)}</td>
        <td style="padding:6px 8px;color:var(--cx-text-mute);font-size:11px;">${p.numero_oc||'-'}</td>
      </tr>`;
    });
    html += `</tbody></table>`;
  }

  // ── Pendientes ──
  if(pendientes.length) {
    html += `<div style="font-size:12px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">⏳ Pendientes de pago</div>
    <table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px;">
      <thead><tr style="border-bottom:1px solid var(--cx-border);">
        <th style="padding:6px 8px;text-align:left;color:var(--cx-text-mute);">Fecha</th>
        <th style="padding:6px 8px;text-align:left;color:var(--cx-text-mute);">Concepto</th>
        <th style="padding:6px 8px;text-align:right;color:var(--cx-text-mute);">Valor</th>
      </tr></thead>
      <tbody>`;
    pendientes.forEach(p=>{
      html += `<tr style="border-bottom:1px solid var(--cx-hairline);">
        <td style="padding:6px 8px;color:var(--cx-text-mute);">${p.fecha||'-'}</td>
        <td style="padding:6px 8px;">${p.concepto||'-'}</td>
        <td style="padding:6px 8px;text-align:right;color:var(--cx-warn-text);font-weight:700;">${fmtM(p.valor||0)}</td>
      </tr>`;
    });
    html += `</tbody></table>`;
  }

  if(!pagadas.length && !pendientes.length) {
    html += `<div style="text-align:center;color:var(--cx-text-mute);padding:32px;">Sin pagos registrados aún.</div>`;
  }

  document.getElementById('hist-content').innerHTML = html;
  document.getElementById('modal-historial').classList.add('open');
}

// ──────────────────────────────────────────────────────────────────────────────
// MODAL HELPERS
// ──────────────────────────────────────────────────────────────────────────────
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
document.querySelectorAll('.modal-bg').forEach(m=>m.addEventListener('click',e=>{ if(e.target===m) m.classList.remove('open'); }));


// ──────────────────────────────────────────────────────────────────────────────
// AGENCIA
// ──────────────────────────────────────────────────────────────────────────────
let _agLoaded = false;

function sevColor(sev) {
  return {critical:'#f87171',high:'#fb923c',medium:'#f59e0b',low:'#34d399'}[sev]||'#94a3b8';
}
function sevLabel(sev) {
  return {critical:'CRITICO',high:'ALTO',medium:'MEDIO',low:'BAJO'}[sev]||sev.toUpperCase();
}


// ──────────────────────────────────────────────────────────────────────────────

// ══════════════════════════════════════════════════════════════════════════════
// AGENCIA ADS - Multi-plataforma con claude-ads skill
// ══════════════════════════════════════════════════════════════════════════════
const ADS_PLATFORMS = [
  {id:'google',    name:'Google Ads',     icon:'&#x1F50D;', color:'#4285F4', desc:'Search · PMax · YouTube'},
  {id:'meta',      name:'Meta Ads',       icon:'&#x1F4F1;', color:'#1877F2', desc:'Facebook · Instagram'},
  {id:'linkedin',  name:'LinkedIn Ads',   icon:'&#x1F4BC;', color:'#0A66C2', desc:'B2B · Lead Gen'},
  {id:'tiktok',    name:'TikTok Ads',     icon:'&#x1F3B5;', color:'#FE2C55', desc:'Creative · Smart+'},
  {id:'youtube',   name:'YouTube Ads',    icon:'&#x25B6;',  color:'#FF0000', desc:'Video · Shorts'},
  {id:'apple',     name:'Apple Search',   icon:'&#xF8FF;',  color:'#000000', desc:'iOS App Store'},
  {id:'microsoft', name:'Microsoft Ads',  icon:'&#x1F50E;', color:'#00A4EF', desc:'Bing · Edge · LinkedIn'},
];
const ADS_ACTIONS_PLATFORM = [
  {id:'audit',    label:'Audit',    icon:'&#x1F50D;', desc:'Diagnostico completo + score 0-100'},
  {id:'plan',     label:'Plan',     icon:'&#x1F5FA;', desc:'Estrategia 90 dias por industria'},
  {id:'creative', label:'Creative', icon:'&#x1F3A8;', desc:'Copy + briefs + specs por formato'},
  {id:'budget',   label:'Budget',   icon:'&#x1F4B0;', desc:'Asignacion + bidding strategy'},
];
const ADS_ACTIONS_GLOBAL = [
  {id:'competitor', label:'Competitor',  icon:'&#x1F575;', desc:'Inteligencia competitiva'},
  {id:'landing',    label:'Landing',     icon:'&#x1F310;', desc:'Auditoria de pagina destino'},
  {id:'test',       label:'A/B Test',    icon:'&#x1F9EA;', desc:'Diseno de experimentos'},
  {id:'dna',        label:'Brand DNA',   icon:'&#x1F9EC;', desc:'Extrae perfil de marca de URL'},
];
let ADS_STATE = { platform: 'meta', action: 'audit', running: false };


// ──────────────────────────────────────────────────────────────────────────────
// INIT
// ──────────────────────────────────────────────────────────────────────────────
loadInfluencers();   // el modulo abre directo en lo unico que se usa: pagos
</script>

<!-- Widget "Mi contraseña" removido 24-may-2026 · vive en /modulos y /hub -->
</body>
</html>"""
