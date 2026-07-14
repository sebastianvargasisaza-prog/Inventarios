MARKETING_HTML = r"""<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Marketing — HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:var(--cx-bg);color:var(--cx-text);min-height:100vh;font-size:14px;}
::-webkit-scrollbar{width:6px;height:6px;}::-webkit-scrollbar-track{background:var(--cx-card);}::-webkit-scrollbar-thumb{background:#475569;border-radius:3px;}

/* ─── Header ─── */
.hdr{background:var(--cx-card);border-bottom:1px solid #e7e5e4;padding:14px 20px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}
.hdr-brand{display:flex;align-items:center;gap:10px;}
.hdr-brand h1{font-size:16px;font-weight:800;color:#fff;}
.hdr-brand span{font-size:11px;color:var(--cx-text-mute);background:var(--cx-bg-alt);padding:2px 8px;border-radius:20px;border:1px solid #e7e5e4;}
.hdr-user{font-size:12px;color:var(--cx-text-mute);}
.hdr-user strong{color:var(--cx-text);}
.back-link{font-size:12px;color:#667eea;text-decoration:none;display:flex;align-items:center;gap:4px;}
.back-link:hover{color:#818cf8;}

/* ─── Tabs ─── */
.tabs-bar{background:var(--cx-card);border-bottom:1px solid #e7e5e4;display:flex;overflow-x:auto;padding:0 20px;}
.tab-btn{padding:12px 20px;font-size:13px;font-weight:600;color:var(--cx-text-mute);border:none;background:none;cursor:pointer;white-space:nowrap;border-bottom:3px solid transparent;transition:.15s;}
.tab-btn:hover{color:#6d28d9;background:#faf7ff;}
.tab-btn.active{color:#6d28d9;border-bottom-color:#6d28d9;}
.tab-panel{display:none;padding:24px 20px;}
.tab-panel.active{display:block;}

/* ─── Cards & Layout ─── */
.page-title{font-size:18px;font-weight:700;color:var(--cx-text);margin-bottom:4px;}
.page-sub{font-size:12px;color:var(--cx-text-mute);margin-bottom:24px;}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:14px;margin-bottom:24px;}
.kpi-card{background:var(--cx-card);border:1px solid #eef0f2;border-top:3px solid #cbd5e1;border-radius:14px;padding:16px;box-shadow:0 1px 3px rgba(15,23,42,.05);transition:box-shadow .15s,transform .1s;}
.kpi-card:hover{box-shadow:0 8px 20px rgba(15,23,42,.08);transform:translateY(-2px);}
.kpi-label{font-size:11px;color:var(--cx-text-mute);font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;}
.kpi-val{font-size:26px;font-weight:800;color:var(--cx-text);line-height:1;letter-spacing:-.01em;}
.kpi-sub{font-size:11px;color:var(--cx-text-mute);margin-top:5px;}
.kpi-card.green{border-top-color:#16a34a;} .kpi-card.green .kpi-val{color:#16a34a;}
.kpi-card.red{border-top-color:#dc2626;} .kpi-card.red .kpi-val{color:#dc2626;}
.kpi-card.blue{border-top-color:#2563eb;} .kpi-card.blue .kpi-val{color:#2563eb;}
.kpi-card.yellow{border-top-color:#f59e0b;} .kpi-card.yellow .kpi-val{color:#b45309;}
.kpi-card.purple{border-top-color:#6d28d9;} .kpi-card.purple .kpi-val{color:#6d28d9;}

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
.badge-green{background:var(--cx-success-pale);color:#16a34a;border:1px solid var(--cx-hairline);}
.badge-blue{background:var(--cx-info-pale);color:#2563eb;border:1px solid var(--cx-hairline);}
.badge-yellow{background:var(--cx-warn-pale);color:#b45309;border:1px solid var(--cx-hairline);}
.badge-red{background:#2d0000;color:#dc2626;border:1px solid #7f1d1d;}
.badge-gray{background:var(--cx-card);color:var(--cx-text-mute);border:1px solid #e7e5e4;}
.badge-purple{background:var(--cx-primary-soft);color:#6d28d9;border:1px solid #4c1d95;}

/* ─── Buttons ─── */
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:600;transition:.15s;}
.btn-primary{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;}
.btn-primary:hover{opacity:.9;}
.btn-sm{padding:5px 12px;font-size:12px;}
.btn-outline{background:transparent;border:1px solid #e7e5e4;color:var(--cx-text-mute);}
.btn-outline:hover{border-color:var(--cx-text-faint);color:var(--cx-text);}
.btn-danger{background:#7f1d1d;color:#dc2626;}
.btn-danger:hover{background:#991b1b;}
.btn-agent{background:var(--cx-primary-grad);border:none;color:#fff;width:100%;padding:14px;font-size:14px;font-weight:700;border-radius:10px;cursor:pointer;transition:.2s;display:flex;align-items:center;justify-content:center;gap:8px;}
.btn-agent:hover{filter:brightness(1.06);}
.btn-agent.running{opacity:.6;cursor:not-allowed;}

/* ─── Forms ─── */
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;}
.form-row.full{grid-template-columns:1fr;}
.form-group{display:flex;flex-direction:column;gap:4px;}
label{font-size:11px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.4px;}
input,select,textarea{background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:8px;padding:8px 12px;color:var(--cx-text);font-size:13px;width:100%;}
input:focus,select:focus,textarea:focus{outline:none;border-color:#667eea;}
textarea{resize:vertical;min-height:80px;}

/* ─── Modal ─── */
.modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;}
.modal-bg.open{display:flex;}
.modal{background:var(--cx-card);border:1px solid #e7e5e4;border-radius:16px;width:min(600px,95vw);max-height:90vh;overflow-y:auto;padding:24px;}
.modal-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;}
.modal-title{font-size:16px;font-weight:700;color:var(--cx-text);}
.modal-close{background:none;border:none;color:var(--cx-text-mute);cursor:pointer;font-size:20px;padding:4px;}
.modal-close:hover{color:#dc2626;}

/* ─── Agent cards ─── */
.agents-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;}
.agent-card{background:var(--cx-card);border:1px solid #e7e5e4;border-radius:14px;padding:20px;}
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
.alert-success{background:var(--cx-success-pale);color:#16a34a;border:1px solid var(--cx-hairline);}
.alert-error{background:#2d0000;color:#dc2626;border:1px solid #7f1d1d;}
.alert-info{background:var(--cx-info-pale);color:#2563eb;border:1px solid var(--cx-hairline);}

/* ─── Spinner ─── */
.spin{display:inline-block;width:16px;height:16px;border:2px solid #e7e5e4;border-top-color:#667eea;border-radius:50%;animation:spin .7s linear infinite;}
@keyframes spin{to{transform:rotate(360deg);}}

/* ─── Trend item ─── */
.trend-item{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--cx-hairline);}
.trend-item:last-child{border-bottom:none;}
.trend-sku{font-weight:700;color:var(--cx-text);font-size:13px;}
.trend-bar{flex:1;margin:0 12px;}
.trend-pct{font-size:12px;font-weight:700;min-width:60px;text-align:right;}
.trend-up{color:#16a34a;}
.trend-dn{color:#dc2626;}
.trend-flat{color:var(--cx-text-mute);}

/* ─── Topbar actions ─── */
.actions-bar{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:10px;}
.search-box{background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:8px;padding:7px 12px;color:var(--cx-text);font-size:13px;width:240px;}
.search-box:focus{outline:none;border-color:#667eea;}

/* ─── Content calendar ─── */
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin-top:12px;}
.cal-day-hdr{text-align:center;font-size:10px;font-weight:700;color:var(--cx-text-mute);padding:6px 0;}
.cal-day{background:var(--cx-bg-alt);border-radius:6px;min-height:70px;padding:6px;position:relative;}
.cal-day-num{font-size:10px;color:var(--cx-text-mute);margin-bottom:4px;}
.cal-item{background:#4c1d95;border-radius:3px;padding:2px 4px;font-size:9px;color:#ddd6fe;margin-bottom:2px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.cal-item.published{background:#065f46;color:#6ee7b7;}
.cal-item.draft{background:#e7e5e4;color:var(--cx-text-mute);}
.cal-item.scheduled{background:var(--cx-info-pale);color:#2563eb;}
.platform-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;cursor:default;transition:all .2s;}
.pill-off{background:var(--cx-card);color:var(--cx-text-faint);border:1px solid #e7e5e4;}
.pill-shopify{background:#0d2e1a;color:#16a34a;border:1px solid var(--cx-hairline);}
.pill-ghl{background:#1a1033;color:#6d28d9;border:1px solid #4c1d95;}
.pill-ig{background:#2d1520;color:#f9a8d4;border:1px solid #831843;}
</style>
</head>

<div id="toast-container" style="position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none;"></div>
<!-- Banner de errores JS — visible para diagnosticar en prod cuando un botón
     no responde. Si ves este banner, hay un bug específico para reportar. -->
<div id="js-error-banner" style="display:none;position:fixed;top:0;left:0;right:0;z-index:10000;background:#7f1d1d;color:#fef2f2;padding:10px 16px;font-size:12px;font-family:monospace;border-bottom:2px solid #ef4444;"></div>
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
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
  <div>
    <div class="cx-mod-header__title">Marketing</div>
    <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; campañas, influencers &amp; ROI &middot; <span style="color:#a8a29e">{usuario}</span></div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">&larr; Módulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
    </button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>

<div class="tabs-bar">
  <!-- Sebastián 13-jul · quitados Hoy + CMO IA (no se usaban) · Inteligencia fusionada
       dentro de Dashboard (sub-nav). Dashboard = inicio. -->
  <button class="tab-btn active" data-tab="dashboard" onclick="switchTab('dashboard')">&#x1F4CA; Dashboard</button>
  <button class="tab-btn" data-tab="campanas" onclick="switchTab('campanas')">&#x1F4E2; Campañas</button>
  <button class="tab-btn" data-tab="influencers" onclick="switchTab('influencers')">&#x1F465; Influencers &amp; Pagos</button>
  <button class="tab-btn" data-tab="contenido" onclick="switchTab('contenido')">&#x1F4C5; Contenido</button>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: DASHBOARD -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: HOY — Centro de ejecución (Fase 2/4 marketing)             -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-hoy" class="tab-panel">
  <div class="actions-bar">
    <div>
      <div class="page-title">&#x1F3AF; Hoy — Centro de ejecución</div>
      <div style="color:var(--cx-text-mute);font-size:13px;margin-top:2px;">Lo que la IA detecta + lo que requiere tu acción HOY · ejecuta agentes y aprueba con un click</div>
    </div>
    <div style="display:flex;gap:8px;">
      <button class="btn btn-primary" onclick="hoyEjecutarTodos()">&#x26A1; Ejecutar todos los agentes</button>
      <button class="btn btn-outline btn-sm" onclick="hoyCargarResumen()">&#x21BB; Refresh</button>
    </div>
  </div>

  <!-- KPIs principales del día -->
  <div id="hoy-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:16px;">
    <div style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:10px;padding:12px 16px">
      <div style="font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.5px">Influencers pendientes pago</div>
      <div id="hoy-kpi-pend" style="font-size:24px;font-weight:800;color:#f59e0b;margin-top:4px">—</div>
    </div>
    <div style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:10px;padding:12px 16px">
      <div style="font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.5px">Eventos cosméticos próximos</div>
      <div id="hoy-kpi-eventos" style="font-size:24px;font-weight:800;color:#6d28d9;margin-top:4px">—</div>
    </div>
    <div style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:10px;padding:12px 16px">
      <div style="font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.5px">SKUs en riesgo (stock)</div>
      <div id="hoy-kpi-riesgo" style="font-size:24px;font-weight:800;color:#dc2626;margin-top:4px">—</div>
    </div>
    <div style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:10px;padding:12px 16px">
      <div style="font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.5px">Campañas activas</div>
      <div id="hoy-kpi-campanas" style="font-size:24px;font-weight:800;color:#16a34a;margin-top:4px">—</div>
    </div>
  </div>

  <!-- Acciones recomendadas (cards con botón "Aprobar y ejecutar") -->
  <div class="card" style="margin-bottom:16px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
      <div style="font-size:14px;font-weight:700;color:#6d28d9">&#x1F916; Acciones recomendadas por la IA</div>
      <button class="btn btn-outline btn-sm" onclick="hoyEjecutarTodos()" title="Ejecutar todos los agentes y refrescar">&#x21BB; Refrescar análisis</button>
    </div>
    <div id="hoy-acciones" style="display:flex;flex-direction:column;gap:10px">
      <div style="color:var(--cx-text-mute);text-align:center;padding:20px;font-size:12px">Click "⚡ Ejecutar todos los agentes" arriba para iniciar.</div>
    </div>
  </div>

  <!-- Refresh metrics socialblade (Fase 1) -->
  <div class="card" style="margin-bottom:16px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
      <div>
        <div style="font-size:14px;font-weight:700;color:#16a34a">&#x1F4E1; Auto-refresh datos de influencers (Socialblade)</div>
        <div style="color:var(--cx-text-mute);font-size:12px;margin-top:2px">Trae seguidores, engagement rate, rank y grade de TODOS los influencers con usuario_red. ~5s por influencer.</div>
      </div>
      <button class="btn btn-primary btn-sm" onclick="hoyRefreshMetricas()">&#x1F504; Refresh todos</button>
    </div>
    <div id="hoy-metrics-result" style="margin-top:6px;font-size:12px;color:var(--cx-text-mute)"></div>
  </div>

  <!-- Log de ejecución -->
  <div class="card">
    <div style="font-size:13px;font-weight:700;color:var(--cx-text-mute);margin-bottom:8px">Log de ejecución</div>
    <div id="hoy-log" style="font-family:monospace;font-size:11px;color:var(--cx-text-mute);max-height:200px;overflow-y:auto;background:#0a0a0b;border:1px solid var(--cx-hairline);border-radius:6px;padding:8px">Sin actividad reciente.</div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: 🤖 CMO IA · Plan del día generado por Claude director  -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-cmo" class="tab-panel">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:18px;">
    <div>
      <div class="page-title" style="margin-bottom:2px;">🤖 CMO IA · Agencia de Marketing Autónoma</div>
      <div class="page-sub" id="cmo-fecha">El director IA de marketing analiza tus datos cada mañana 7 AM y propone acciones priorizadas.</div>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <button class="btn btn-outline" onclick="cmoCargarPlan()" title="Cargar plan del día">🔄 Recargar</button>
      <button class="btn btn-outline" onclick="cmoAbrirHistorial()" title="Ver planes anteriores y desempeño del agente">📚 Historial</button>
      <button class="btn btn-primary" onclick="cmoGenerarPlanForzar()" title="Regenerar el plan ahora con datos frescos">⚡ Generar plan ahora</button>
    </div>
  </div>

  <!-- KPIs · resumen del plan -->
  <div id="cmo-kpi-bar" style="display:none;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:18px;"></div>

  <!-- Mensaje sin plan -->
  <div id="cmo-empty" style="display:none;background:linear-gradient(135deg,rgba(167,139,250,.08),rgba(14,116,144,.06));border:1px solid rgba(167,139,250,.3);border-radius:12px;padding:24px;text-align:center;">
    <div style="font-size:40px;margin-bottom:10px">🤖</div>
    <div style="font-size:16px;font-weight:700;color:var(--cx-text);margin-bottom:8px;">Sin plan generado para hoy</div>
    <div style="font-size:13px;color:var(--cx-text-mute);margin-bottom:16px;line-height:1.5;">El cron CMO IA corre todos los días a las <b>7:00 AM</b> automático. También podés generar uno ahora con datos frescos.</div>
    <button class="btn btn-primary" onclick="cmoGenerarPlanForzar()" style="padding:10px 22px;font-size:14px;">⚡ Generar plan del día</button>
  </div>

  <!-- Lista de acciones -->
  <div id="cmo-acciones-list" style="display:flex;flex-direction:column;gap:12px;"></div>

  <div id="cmo-alert" style="display:none;margin-top:12px;"></div>
</div>

<!-- Modal: Historial planes CMO IA · 27-may-2026 PM -->
<div class="modal-bg" id="modal-cmo-historial">
  <div class="modal" style="max-width:920px;max-height:88vh;overflow-y:auto;">
    <div class="modal-title">📚 Historial de planes CMO IA</div>
    <button class="modal-close" onclick="closeModal('modal-cmo-historial')">&times;</button>
    <div style="font-size:11px;color:var(--cx-text-mute);margin:6px 0 12px;">Click en una fila para ver el plan completo de ese día.</div>
    <div id="cmo-hist-body" style="font-size:12px;color:var(--cx-text-soft);">Cargando...</div>
  </div>
</div>

<div id="tab-dashboard" class="tab-panel active">
  <!-- Inteligencia fusionada (Sebastián 13-jul): sub-nav a las 4 secciones · el top-tab
       Dashboard vuelve al panorama. -->
  <!-- Sebastián 13-jul · quitado el sub-nav de Análisis (Estrategia/Agentes IA/Score de
       creadores/Histórico inversión): innecesario + rasgo de IA. Dashboard = solo lo esencial. -->

  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:6px;">
    <div>
      <div class="page-title" style="margin-bottom:2px;">&#x1F4CA; Marketing · Dashboard</div>
      <div class="page-sub" id="dash-fecha">Cargando...</div>
    </div>
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
      <div id="pill-shopify" class="platform-pill pill-off">🛍️ Shopify</div>
      <div id="pill-ghl" class="platform-pill pill-off">📋 GHL</div>
      <div id="pill-ig" class="platform-pill pill-off">📸 Instagram</div>
      <button id="btn-sync-shopify" class="btn btn-outline btn-sm" onclick="syncPlatform('shopify')">↻ Shopify</button>
      <button class="btn btn-outline btn-sm" style="color:#f59e0b;border-color:#f59e0b;font-size:10px;" onclick="syncPlatform('shopify',true)" title="Trae todo el historial">📥 Histórico</button>
      <button id="btn-sync-ghl" class="btn btn-outline btn-sm" onclick="syncPlatform('ghl')">↻ GHL</button>
      <button id="btn-sync-instagram" class="btn btn-outline btn-sm" onclick="syncPlatform('instagram')">↻ IG</button>
      <button class="btn btn-outline btn-sm" style="border-color:#e1306c;color:#e1306c;" onclick="refreshIgToken()">🔑 Renovar token IG</button>
      <span id="ig-token-status" style="font-size:10px;padding:2px 8px;border-radius:10px;display:none;"></span>
      <span id="sync-status" style="font-size:11px;color:var(--cx-text-mute);"></span>
    </div>
  </div>

  <!-- KPIs Shopify -->
  <div style="font-size:11px;font-weight:700;color:#d4af37;text-transform:uppercase;letter-spacing:.8px;margin:16px 0 8px;">🛍️ Shopify · Ventas reales</div>
  <div id="sh-cobertura-banner" style="display:none;background:#78350f;color:#fde68a;border-radius:8px;padding:8px 14px;font-size:11px;margin-bottom:10px;"></div>
<div class="kpi-grid" id="dash-shopify-kpis">
    <div class="kpi-card yellow"><div class="kpi-label" id="sh-rev30-label">Revenue</div><div class="kpi-val" id="sh-rev30">—</div><div class="kpi-sub" id="sh-rev7">vs período ant.: —</div></div>
    <div class="kpi-card blue"><div class="kpi-label" id="sh-ped30-label">Pedidos</div><div class="kpi-val" id="sh-ped30">—</div><div class="kpi-sub" id="sh-ped-total">Total: —</div></div>
    <div class="kpi-card green"><div class="kpi-label">Ticket promedio</div><div class="kpi-val" id="sh-ticket">—</div><div class="kpi-sub" id="sh-clientes">Clientes: —</div></div>
    <div class="kpi-card purple"><div class="kpi-label">Clientes nuevos 30d</div><div class="kpi-val" id="sh-nuevos">—</div><div class="kpi-sub" id="sh-recurrentes">Recurrentes: —</div></div>
    <div class="kpi-card"><div class="kpi-label">Revenue total</div><div class="kpi-val" id="sh-rev-total" style="font-size:16px;">—</div><div class="kpi-sub">Histórico</div></div>
    <div class="kpi-card blue"><div class="kpi-label">Contactos GHL</div><div class="kpi-val" id="ghl-total">—</div><div class="kpi-sub" id="ghl-nuevos">Nuevos 30d: —</div></div>
  </div>

  <!-- AUDIT 26-may · Widget Meta del mes (#4 sprint marketing-superior) -->
  <div style="font-size:11px;font-weight:700;color:#10b981;text-transform:uppercase;letter-spacing:.8px;margin:16px 0 8px;display:flex;align-items:center;gap:8px">
    <span>🎯 Meta del mes</span>
    <button class="btn btn-outline btn-sm" onclick="openMetaModal()" style="font-size:10px;padding:2px 8px">⚙ Editar meta</button>
    <button class="btn btn-outline btn-sm" onclick="openCalendarioCosmeticoModal()" style="font-size:10px;padding:2px 8px">📅 Calendario cosmético</button>
  </div>
  <div id="dash-meta-progreso" style="background:var(--cx-bg-alt);border:1px solid var(--cx-hairline);border-radius:10px;padding:14px 16px;margin-bottom:16px;color:var(--cx-text-mute);font-size:12px">Cargando meta del mes…</div>

  <!-- Sebastián 13-jul · quitado el widget "Sentiment de la comunidad (IA)" · rasgo de IA -->
  <div id="dash-sentiment" style="display:none"></div>

  <!-- Instagram KPIs -->
  <div style="font-size:11px;font-weight:700;color:#e1306c;text-transform:uppercase;letter-spacing:.8px;margin:16px 0 8px;">📸 Instagram · Engagement real</div>
  <div class="kpi-grid" id="dash-ig-kpis">
    <div class="kpi-card" style="border-color:#e1306c33;"><div class="kpi-label">Posts 30d</div><div class="kpi-val" id="ig-posts30">—</div><div class="kpi-sub" id="ig-posts-total">Total: —</div></div>
    <div class="kpi-card" style="border-color:#e1306c33;"><div class="kpi-label">Likes 30d</div><div class="kpi-val" id="ig-likes30">—</div><div class="kpi-sub" id="ig-avg-likes">Promedio: —</div></div>
    <div class="kpi-card" style="border-color:#e1306c33;"><div class="kpi-label">Comentarios 30d</div><div class="kpi-val" id="ig-comments30">—</div><div class="kpi-sub">@animuslb</div></div>
  </div>

  <!-- Gráfica de ventas + Top SKUs -->
  <div class="grid2" style="margin:20px 0;">
    <div class="card">
      <div class="card-hdr"><span class="card-title">📈 Ventas mensuales Shopify</span></div>
      <div class="card-body" id="dash-chart" style="min-height:160px;">Cargando...</div>
    </div>
    <div class="card">
      <div class="card-hdr"><span class="card-title">🏆 Top SKUs por revenue (30d)</span></div>
      <div class="card-body" id="dash-top-skus">Cargando...</div>
    </div>
  </div>

  <!-- Sebastián 13-jul · quitado "Campañas activas" del dashboard (ya está su tab) ·
       ids ocultos para no romper loadDashboard. -->
  <div style="display:none;"><div id="dash-kpis"></div><table><tbody id="dash-campanas"></tbody></table></div>
  <div class="card" style="margin-bottom:20px;">
    <div class="card-hdr"><span class="card-title">🌎 Top ciudades Shopify</span></div>
    <div class="card-body" id="dash-ciudades">Cargando...</div>
  </div>

  <!-- Instagram token update form -->
  <div id="ig-token-form" style="background:var(--cx-bg-alt);border:1px solid #e1306c44;border-radius:8px;padding:12px 16px;margin-bottom:12px;display:none;">
    <div style="font-size:11px;color:#e1306c;font-weight:700;margin-bottom:8px;">🔑 Token expirado — pega un nuevo token de Graph API Explorer</div>
    <div style="display:flex;gap:8px;align-items:center;">
      <input id="ig-token-input" type="text" placeholder="EAANXh..." 
        style="flex:1;background:var(--cx-card);border:1px solid #e7e5e4;color:var(--cx-text);padding:7px 10px;border-radius:6px;font-size:11px;font-family:monospace;">
      <button onclick="saveIgToken()" class="btn btn-sm" style="background:#e1306c;color:#fff;border:none;white-space:nowrap;">Guardar y activar</button>
      <button onclick="document.getElementById('ig-token-form').style.display='none'" class="btn btn-outline btn-sm">✕</button>
    </div>
    <div style="font-size:10px;color:var(--cx-text-mute);margin-top:6px;">
      Ve a <a href="https://developers.facebook.com/tools/explorer" target="_blank" style="color:#6366f1;">Graph API Explorer</a> → selecciona "Inventario ÁNIMUS" → Generate Access Token → pega aquí
    </div>
  </div>

  <!-- Sebastián 13-jul · quitados del dashboard: Top posts IG, Contenido reciente (ya está
       su tab) y Presupuesto por canal · innecesarios. ids ocultos para no romper el JS. -->
  <div style="display:none;" id="dash-ig-posts-section">
    <div id="dash-ig-posts"></div>
    <table><tbody id="dash-contenido"></tbody></table>
    <div id="dash-canales"></div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: CAMPAÑAS -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-campanas" class="tab-panel">
  <div class="actions-bar">
    <div>
      <div class="page-title">&#x1F4E2; Campañas</div>
    </div>
    <div style="display:flex;gap:10px;">
      <select id="camp-filtro-estado" onchange="loadCampanas()" style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:8px;padding:7px 12px;color:var(--cx-text);font-size:13px;">
        <option value="">Todos los estados</option>
        <option value="Planificada">Planificada</option>
        <option value="Activa">Activa</option>
        <option value="Pausada">Pausada</option>
        <option value="Finalizada">Finalizada</option>
      </select>
      <button class="btn btn-primary" onclick="openCampanaModal()">+ Nueva Campaña</button>
    </div>
  </div>
  <div id="camp-alert" style="display:none;"></div>
  <div class="card">
    <div class="tbl-wrap">
      <table>
        <thead><tr><th class="mob-hide">#</th><th>Nombre</th><th class="mob-hide">Tipo</th><th class="mob-hide">Canal</th><th>Estado</th><th class="mob-hide">Presupuesto</th><th class="mob-hide">Gastado</th><th>Ventas</th><th>ROI</th><th class="mob-hide">Infls</th><th>Acciones</th></tr></thead>
        <tbody id="camp-body"><tr class="empty-row"><td colspan="11"><span class="spin"></span></td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: INFLUENCERS & PAGOS (fusionado) -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-influencers" class="tab-panel">
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
    <button id="infsub-pagos" onclick="infSubView('pagos')" style="border:none;background:none;cursor:pointer;padding:10px 18px;font-size:13px;font-weight:800;color:#6d28d9;border-bottom:3px solid #6d28d9;">💸 Centro de pagos</button>
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
        <div style="font-size:14px;font-weight:700;color:#16a34a;">&#x1F3AF; Atribución de ventas — últimos 90 días</div>
        <div style="font-size:11px;color:var(--cx-text-mute);margin-top:2px;">Revenue Shopify por discount code · click para ver</div>
      </div>
      <span onclick="event.preventDefault();loadAtribucion(true);" title="Refrescar atribución" style="font-size:16px;color:#16a34a;padding:4px 8px;">&#x21BB;</span>
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
    <select id="pag-mes" onchange="renderInfluencersTable()" style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:6px;padding:5px 9px;color:var(--cx-text);font-size:12px;">
      <option value="">Todos los meses</option>
    </select>
    <select id="pag-estado" onchange="renderInfluencersTable()" style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:6px;padding:5px 9px;color:var(--cx-text);font-size:12px;">
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

<!-- Tab "tab-pagos" eliminado — fusionado al de Influencers (Sebastian 30-abr-2026) -->
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
.kanban-col{background:var(--cx-card,#fff);border:1px solid #eef0f2;border-radius:14px;padding:10px 10px 12px;min-height:300px;display:flex;flex-direction:column;box-shadow:0 2px 12px rgba(15,23,42,.05);border-top:3px solid #e5e7eb;}
.kanban-col-hdr{display:flex;justify-content:space-between;align-items:center;padding:4px 6px 10px;border-bottom:1px solid var(--cx-hairline);margin-bottom:8px;}
.kanban-col-hdr .name{font-weight:800;font-size:13px;color:var(--cx-text);letter-spacing:-.01em;}
.kanban-col-hdr .count{background:var(--cx-bg-alt);color:var(--cx-text-mute);padding:2px 10px;border-radius:20px;font-size:11px;font-weight:800;}
.kanban-col[data-estado="Brief"]       .name{color:#2563eb;} .kanban-col[data-estado="Brief"]{border-top-color:#2563eb;}
.kanban-col[data-estado="Produccion"]  .name{color:#b45309;} .kanban-col[data-estado="Produccion"]{border-top-color:#f59e0b;}
.kanban-col[data-estado="Pendiente"]   .name{color:#6d28d9;} .kanban-col[data-estado="Pendiente"]{border-top-color:#7c3aed;}
.kanban-col[data-estado="Publicado"]   .name{color:#16a34a;} .kanban-col[data-estado="Publicado"]{border-top-color:#16a34a;}
.kanban-col[data-estado="Performance"] .name{color:#f472b6;} .kanban-col[data-estado="Performance"]{border-top-color:#f472b6;}
.kanban-card{background:var(--cx-card);border:1px solid #eef0f2;border-radius:10px;padding:10px;margin-bottom:8px;cursor:pointer;transition:transform .12s,box-shadow .15s,border-color .15s;font-size:12px;box-shadow:0 1px 4px rgba(15,23,42,.04);}
.kanban-card:hover{border-color:#7c3aed;transform:translateY(-2px);box-shadow:0 8px 18px rgba(124,58,237,.10);}
.kanban-card .sku{font-family:monospace;color:#16a34a;font-size:11px;font-weight:700;}
.kanban-card .titulo{font-weight:700;color:var(--cx-text);margin:4px 0;line-height:1.3;}
.kanban-card .meta{display:flex;flex-wrap:wrap;gap:6px;font-size:10px;color:var(--cx-text-mute);margin-top:6px;}
.kanban-card .meta span{background:var(--cx-bg-alt);padding:1px 7px;border-radius:6px;}
.kanban-card .perf{display:flex;gap:8px;font-size:10px;margin-top:6px;color:var(--cx-text-mute);}
.kanban-card .perf b{color:var(--cx-text);}
.kanban-empty{color:var(--cx-text-faint);font-size:11px;text-align:center;padding:20px 0;font-style:italic;}
.kanban-add-btn{background:var(--cx-bg-alt);color:var(--cx-text-mute);border:1px dashed #e7e5e4;border-radius:6px;padding:6px;font-size:11px;cursor:pointer;width:100%;margin-top:auto;transition:.15s;}
.kanban-add-btn:hover{color:#6d28d9;border-color:#7c3aed;}
</style>

<div id="tab-contenido" class="tab-panel">
  <div class="actions-bar">
    <div>
      <div class="page-title">&#x1F4C5; Calendario de Contenido</div>
      <div style="color:var(--cx-text-mute);font-size:12px;margin-top:2px;">Pipeline visual del contenido — desde el brief hasta el performance medido.</div>
    </div>
    <div style="display:flex;gap:10px;align-items:center;">
      <button class="btn btn-outline btn-sm" onclick="loadContenido()" title="Refrescar">&#x21BB;</button>
      <button class="btn btn-outline btn-sm" onclick="openABTestsModal()" title="A/B testing de creatividades" style="border-color:#6d28d9;color:#6d28d9">&#x1F52C; A/B Tests</button>
      <button class="btn btn-primary btn-sm" onclick="openContenidoModal()">+ Nueva pieza</button>
    </div>
  </div>
  <div id="cont-alert" style="display:none;"></div>

  <div class="kanban-wrap" id="kanban-wrap">
    <div class="kanban-col" data-estado="Brief">
      <div class="kanban-col-hdr"><span class="name">&#x1F4DD; Brief</span><span class="count" id="kb-c-Brief">0</span></div>
      <div class="kanban-items" id="kb-Brief"></div>
      <button class="kanban-add-btn" onclick="openContenidoModal('Brief')">+ Agregar</button>
    </div>
    <div class="kanban-col" data-estado="Produccion">
      <div class="kanban-col-hdr"><span class="name">&#x1F3AC; Producción</span><span class="count" id="kb-c-Produccion">0</span></div>
      <div class="kanban-items" id="kb-Produccion"></div>
      <button class="kanban-add-btn" onclick="openContenidoModal('Produccion')">+ Agregar</button>
    </div>
    <div class="kanban-col" data-estado="Pendiente">
      <div class="kanban-col-hdr"><span class="name">&#x23F0; Pendiente</span><span class="count" id="kb-c-Pendiente">0</span></div>
      <div class="kanban-items" id="kb-Pendiente"></div>
      <button class="kanban-add-btn" onclick="openContenidoModal('Pendiente')">+ Agregar</button>
    </div>
    <div class="kanban-col" data-estado="Publicado">
      <div class="kanban-col-hdr"><span class="name">&#x2705; Publicado</span><span class="count" id="kb-c-Publicado">0</span></div>
      <div class="kanban-items" id="kb-Publicado"></div>
      <button class="kanban-add-btn" onclick="openContenidoModal('Publicado')">+ Agregar</button>
    </div>
    <div class="kanban-col" data-estado="Performance">
      <div class="kanban-col-hdr"><span class="name">&#x1F4CA; Performance</span><span class="count" id="kb-c-Performance">0</span></div>
      <div class="kanban-items" id="kb-Performance"></div>
      <button class="kanban-add-btn" onclick="openContenidoModal('Performance')">+ Agregar</button>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: INTELIGENCIA (envuelve Agentes IA + Histórico + Creadores) -->
<!-- Es un contenedor lógico — los 3 sub-paneles (tab-agentes, tab-analytics,
     tab-agencia) viven debajo y se alternan con showSub() / sub-nav.        -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<style>
.intel-subnav{display:flex;gap:4px;background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:10px;padding:4px;margin-bottom:18px;flex-wrap:wrap;}
.intel-subnav button{flex:1;min-width:130px;padding:9px 16px;background:transparent;color:var(--cx-text-mute);border:none;border-radius:7px;cursor:pointer;font-size:13px;font-weight:600;transition:.15s;}
.intel-subnav button:hover{color:var(--cx-text);background:var(--cx-card);}
.intel-subnav button.intel-active{background:linear-gradient(135deg,#7c3aed,#4c1d95);color:#fff;}
</style>

<!-- Sub-tab dedicada para el resultado de Estrategia (agente master).
     Persiste el último output para que el jefe pueda volver y accionar
     sin tener que regenerar. Si nunca se generó, invita a generarlo. -->
<div id="tab-estrategia" class="tab-panel intel-sub">
  <div class="intel-subnav" data-intel-nav="1">
    <button class="intel-active" onclick="showSub('estrategia')">&#x1F9E0; Estrategia del mes</button>
    <button onclick="showSub('agentes')">&#x1F916; Agentes IA</button>
    <button onclick="showSub('agencia')">&#x1F3C6; Score de creadores</button>
    <button onclick="showSub('analytics')">&#x1F4CA; Histórico de inversión</button>
  </div>
  <div id="estrategia-vista" style="margin-top:12px;">
    <div style="background:var(--cx-hero-grad);border:1px solid #7c3aed;border-radius:14px;padding:36px 24px;text-align:center;">
      <div style="font-size:48px;margin-bottom:12px;">&#x1F9E0;</div>
      <div style="font-size:22px;font-weight:800;color:#fff;margin-bottom:8px;">Estrategia del mes</div>
      <div style="font-size:13px;color:var(--cx-text-soft);max-width:560px;margin:0 auto 18px;line-height:1.6;">
        Aún no generaste la estrategia este mes. El agente cruza ventas Shopify, engagement IG, stock, producción programada, influencers activos y eventos cosméticos para devolver el plan accionable.
      </div>
      <button onclick="runAgent('estrategia')"
        style="background:linear-gradient(135deg,#7c3aed,#4c1d95);color:#fff;border:none;padding:14px 28px;font-size:14px;font-weight:800;border-radius:10px;cursor:pointer;box-shadow:0 8px 24px rgba(124,58,237,.4);">
        &#x25B6; Generar estrategia ahora
      </button>
    </div>
  </div>
</div>

<div id="tab-agentes" class="tab-panel intel-sub">
  <div class="intel-subnav" data-intel-nav="1">
    <button onclick="showSub('estrategia')">&#x1F9E0; Estrategia del mes</button>
    <button class="intel-active" onclick="showSub('agentes')">&#x1F916; Agentes IA</button>
    <button onclick="showSub('agencia')">&#x1F3C6; Score de creadores</button>
    <button onclick="showSub('analytics')">&#x1F4CA; Histórico de inversión</button>
  </div>
  <div class="page-title">&#x1F916; Agentes IA — Marketing</div>
  <div class="page-sub">11 agentes inteligentes con Claude AI — análisis real de datos ERP + Shopify + GHL + Instagram.</div>

  <!-- ═══ Agente destacado: Estrategia (master) ════════════════════════════ -->
  <div style="background:var(--cx-hero-grad);border:1px solid #7c3aed;border-radius:14px;padding:22px;margin-bottom:22px;position:relative;overflow:hidden;">
    <div style="position:absolute;top:-40%;right:-10%;width:300px;height:300px;background:radial-gradient(circle,#7c3aed33 0%,transparent 70%);pointer-events:none;"></div>
    <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;position:relative;z-index:1;">
      <div style="font-size:36px;line-height:1;">&#x1F9E0;</div>
      <div style="flex:1;min-width:240px;">
        <div style="font-size:11px;color:#6d28d9;font-weight:700;text-transform:uppercase;letter-spacing:.1em;margin-bottom:2px;">Master agent · cruza todo</div>
        <div style="font-size:18px;font-weight:800;color:#fff;margin-bottom:4px;">Estrategia del mes</div>
        <div style="font-size:12px;color:var(--cx-text-soft);line-height:1.5;">Analiza ventas Shopify, engagement IG, stock, producción programada, influencers activos y eventos cosméticos. Devuelve: foco del mes · calendario de publicaciones (4 semanas) · 3 oportunidades de venta · 3 riesgos · recomendación al fundador.</div>
      </div>
      <button class="btn-agent" id="btn-estrategia" onclick="runAgent('estrategia')" style="background:linear-gradient(135deg,#7c3aed,#4c1d95);color:#fff;border:none;padding:14px 22px;font-size:14px;font-weight:800;border-radius:10px;white-space:nowrap;">
        <span>&#x25B6; Generar estrategia</span>
      </button>
    </div>
    <div class="agent-result" id="result-estrategia" style="margin-top:18px;"></div>
  </div>

  <div class="agents-grid">

    <div class="agent-card">
      <div class="agent-icon">&#x1F4C6;</div>
      <div class="agent-name">Estacionalidad</div>
      <div class="agent-desc">Cruza stock PT vs demanda proyectada para eventos del calendario cosmético (Día de la Madre, Black Friday...). Detecta déficits y calcula deadlines de producción.</div>
      <button class="btn-agent" id="btn-estacionalidad" onclick="runAgent('estacionalidad')">
        <span>&#x25B6; Analizar estacionalidad</span>
      </button>
      <div class="agent-result" id="result-estacionalidad"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x1F50D;</div>
      <div class="agent-name">Oportunidad</div>
      <div class="agent-desc">Detecta SKUs con alto stock, baja rotación o sin ventas en Shopify. Propone acciones de campaña urgentes o recomendadas con canal sugerido.</div>
      <button class="btn-agent" id="btn-oportunidad" onclick="runAgent('oportunidad')">
        <span>&#x25B6; Detectar oportunidades</span>
      </button>
      <div class="agent-result" id="result-oportunidad"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x1F4B0;</div>
      <div class="agent-name">ROI</div>
      <div class="agent-desc">Calcula el ROI real por campaña cruzando inversión vs ventas atribuidas. Incluye revenue Shopify de los últimos 30 días.</div>
      <button class="btn-agent" id="btn-roi" onclick="runAgent('roi')">
        <span>&#x25B6; Calcular ROI</span>
      </button>
      <div class="agent-result" id="result-roi"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x1F4C8;</div>
      <div class="agent-name">Tendencias</div>
      <div class="agent-desc">Compara liberaciones ERP e histórico Shopify mes a mes. Identifica SKUs en alza, en caída y estables con variación porcentual.</div>
      <button class="btn-agent" id="btn-tendencias" onclick="runAgent('tendencias')">
        <span>&#x25B6; Ver tendencias</span>
      </button>
      <div class="agent-result" id="result-tendencias"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x1F4CB;</div>
      <div class="agent-name">Brief de Contenido</div>
      <div class="agent-desc">Genera briefs por SKU top: canal recomendado, claim científico, formato, menciones en Instagram. Listo para enviar a influencers.</div>
      <div style="margin-bottom:10px;">
        <label style="font-size:11px;color:var(--cx-text-mute);">Campaña (opcional)</label>
        <select id="brief-campana-sel" style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:8px;padding:7px 12px;color:var(--cx-text);font-size:13px;width:100%;margin-top:4px;">
          <option value="">Sin campaña específica</option>
        </select>
      </div>
      <button class="btn-agent" id="btn-brief" onclick="runAgent('brief')">
        <span>&#x25B6; Generar brief</span>
      </button>
      <div class="agent-result" id="result-brief"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x1F3F7;&#xFE0F;</div>
      <div class="agent-name">Pricing</div>
      <div class="agent-desc">Calcula el descuento máximo seguro por SKU manteniendo margen ≥40%. Para SKUs con >4 meses de cobertura — activa promociones sin destruir rentabilidad.</div>
      <button class="btn-agent" id="btn-pricing" onclick="runAgent('pricing')">
        <span>&#x25B6; Calcular precios promo</span>
      </button>
      <div class="agent-result" id="result-pricing"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x1F504;</div>
      <div class="agent-name">Reorden B2B</div>
      <div class="agent-desc">Analiza patrones de compra de clientes B2B en Shopify. Predice cuándo hará su próximo pedido cada cliente y clasifica urgencia (hoy / esta semana / este mes).</div>
      <button class="btn-agent" id="btn-reorden" onclick="runAgent('reorden')">
        <span>&#x25B6; Predecir reórdenes</span>
      </button>
      <div class="agent-result" id="result-reorden"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x26A0;&#xFE0F;</div>
      <div class="agent-name">Canibalización</div>
      <div class="agent-desc">Detecta campañas activas que compiten por el mismo SKU o canal en fechas solapadas. Propone calendario optimizado para evitar conflictos.</div>
      <button class="btn-agent" id="btn-canibal" onclick="runAgent('canibal')">
        <span>&#x25B6; Detectar conflictos</span>
      </button>
      <div class="agent-result" id="result-canibal"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x270D;&#xFE0F;</div>
      <div class="agent-name">Contenido Auto</div>
      <div class="agent-desc">Genera captions para Instagram, asuntos de email y textos de WhatsApp para los 3 SKUs con mayor rotación del último mes.</div>
      <button class="btn-agent" id="btn-contenido_auto" onclick="runAgent('contenido_auto')">
        <span>&#x25B6; Generar contenido</span>
      </button>
      <div class="agent-result" id="result-contenido_auto"></div>
    </div>

    <div class="agent-card">
      <div class="agent-icon">&#x1F6A8;</div>
      <div class="agent-name">Alerta Stock</div>
      <div class="agent-desc">Cruza stock ERP + demanda Shopify para detectar SKUs con cobertura crítica (≤7d) o en advertencia (≤21d). Dispara alertas de reposición urgente.</div>
      <button class="btn-agent" id="btn-alerta_stock" onclick="runAgent('alerta_stock')">
        <span>&#x25B6; Ver alertas stock</span>
      </button>
      <div class="agent-result" id="result-alerta_stock"></div>
    </div>

  </div>

  <div style="margin-top:28px;">
    <div class="card">
      <div class="card-hdr"><span class="card-title">&#x1F4DC; Historial de Agentes</span>
        <button class="btn btn-outline btn-sm" onclick="loadAgentLog()">&#x21BB; Actualizar</button>
      </div>
      <div class="card-body">
        <table>
          <thead><tr><th>Fecha</th><th>Agente</th><th>Acción</th><th>Ejecutado por</th><th>Ver</th></tr></thead>
          <tbody id="agent-log-body"><tr class="empty-row"><td colspan="5">Cargando historial...</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: ANALYTICS -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-analytics" class="tab-panel intel-sub">
  <div class="intel-subnav" data-intel-nav="1">
    <button onclick="showSub('estrategia')">&#x1F9E0; Estrategia del mes</button>
    <button onclick="showSub('agentes')">&#x1F916; Agentes IA</button>
    <button onclick="showSub('agencia')">&#x1F3C6; Score de creadores</button>
    <button class="intel-active" onclick="showSub('analytics')">&#x1F4CA; Histórico de inversión</button>
  </div>
  <div class="page-title">&#x1F4CA; Analytics — Programa de Influencers</div>
  <div class="page-sub">Inversión histórica, rendimiento por creador y Shopify revenue.</div>

  <!-- KPI fila 1: histórico -->
  <div style="font-size:11px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Histórico total</div>
  <div class="kpi-grid" style="grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin-bottom:20px;">
    <div class="kpi-card blue"><div class="kpi-label">Invertido total</div><div class="kpi-val" id="an-total-hist">—</div></div>
    <div class="kpi-card green"><div class="kpi-label">Colaboraciones</div><div class="kpi-val" id="an-colabs-hist">—</div></div>
    <div class="kpi-card purple"><div class="kpi-label">Creadores únicos</div><div class="kpi-val" id="an-creadores-hist">—</div></div>
    <div class="kpi-card yellow"><div class="kpi-label">Promedio / colab</div><div class="kpi-val" id="an-avg-colab">—</div></div>
    <div class="kpi-card red"><div class="kpi-label">Pendiente pago</div><div class="kpi-val" id="an-pendiente-total">—</div></div>
    <div class="kpi-card" style="border-color:#6366f1;"><div class="kpi-label">Top creador</div><div class="kpi-val" id="an-top-creador" style="font-size:13px;color:#818cf8;">—</div></div>
  </div>

  <!-- KPI fila 2: Shopify -->
  <div style="font-size:11px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Shopify — Revenue actual</div>
  <div class="kpi-grid" style="grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin-bottom:24px;">
    <div class="kpi-card blue"><div class="kpi-label">Revenue últimos 30d</div><div class="kpi-val" id="an-sh-30d">—</div></div>
    <div class="kpi-card green"><div class="kpi-label">Revenue este mes</div><div class="kpi-val" id="an-sh-mes">—</div></div>
    <div class="kpi-card" id="an-sh-crec-card" style="border-color:#16a34a;"><div class="kpi-label">Crecimiento vs mes ant.</div><div class="kpi-val" id="an-sh-crec">—</div></div>
    <div class="kpi-card yellow"><div class="kpi-label">Pedidos últimos 30d</div><div class="kpi-val" id="an-sh-orders">—</div></div>
  </div>

  <div class="grid2" style="margin-bottom:20px;">
    <!-- Gasto mensual chart -->
    <div class="card">
      <div class="card-hdr">
        <span class="card-title">&#x1F4B0; Gasto mensual histórico (COP)</span>
        <span id="an-total-label" style="font-size:12px;color:var(--cx-text-mute);"></span>
      </div>
      <div class="card-body" id="an-gasto-chart" style="min-height:200px;padding:8px 0;"></div>
    </div>
    <!-- Nuevos creadores -->
    <div class="card">
      <div class="card-hdr"><span class="card-title">&#x1F331; Nuevos creadores por mes</span></div>
      <div class="card-body" id="an-nuevos-chart" style="min-height:200px;padding:8px 0;"></div>
    </div>
  </div>

  <!-- Ranking ALL TIME -->
  <div class="card" style="margin-bottom:20px;">
    <div class="card-hdr"><span class="card-title">&#x1F3C6; Ranking — Inversión por creador (histórico)</span></div>
    <div class="card-body">
      <table>
        <thead><tr><th class="mob-hide">#</th><th>Creador</th><th class="mob-hide">Colabs</th><th>Total pagado</th><th>Pendiente</th><th class="mob-hide">Promedio/colab</th><th class="mob-hide">Primer pago</th><th class="mob-hide">Último pago</th><th>Estado</th></tr></thead>
        <tbody id="an-ranking-body"><tr class="empty-row"><td colspan="9">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>

  <!-- Detalle mensual -->
  <div class="card">
    <div class="card-hdr"><span class="card-title">&#x1F4C5; Detalle por mes</span></div>
    <div class="card-body">
      <table>
        <thead><tr><th>Mes</th><th class="mob-hide">Colaboraciones</th><th class="mob-hide">Creadores únicos</th><th>Total pagado</th><th>Pendiente</th><th class="mob-hide">Nuevos creadores</th></tr></thead>
        <tbody id="an-meses-body"><tr class="empty-row"><td colspan="6">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>

  <!-- KPI año actual (hidden label, kept for compat) -->
  <span id="an-total-2025" style="display:none;"></span>
  <span id="an-colabs-2025" style="display:none;"></span>
  <span id="an-creadores-2025" style="display:none;"></span>
</div><!-- /tab-analytics -->

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- MODALS — DEBEN VIVIR FUERA de cualquier tab-panel.               -->
<!-- Bug previo: tab-analytics no cerraba antes de los modales, así    -->
<!-- que cuando esa tab era display:none, todos los modales también.   -->
<!-- El user veía: 'el botón editar solo abre el modal cuando estoy    -->
<!-- en la pestaña Histórico de inversión'.                            -->
<!-- ═══════════════════════════════════════════════════════════════ -->

<!-- Modal: Historial Influencer -->
<div class="modal-bg" id="modal-historial">
  <div class="modal" style="max-width:680px;max-height:85vh;overflow-y:auto;">
    <div class="modal-title" id="hist-title">Historial</div>
    <button class="modal-close" onclick="closeModal('modal-historial')">&times;</button>
    <div id="hist-content" style="margin-top:8px;"></div>
  </div>
</div>

<!-- Modal: Nueva Campaña -->
<div class="modal-bg" id="modal-campana">
  <div class="modal">
    <div class="modal-hdr">
      <div class="modal-title" id="modal-campana-title">Nueva Campaña</div>
      <button class="modal-close" onclick="closeModal('modal-campana')">&times;</button>
    </div>
    <input type="hidden" id="camp-edit-id">
    <div class="form-row">
      <div class="form-group"><label>Nombre *</label><input id="camp-nombre" placeholder="Ej: Lanzamiento Crema Vitamina C"></div>
      <div class="form-group"><label>Tipo</label>
        <select id="camp-tipo">
          <option>Digital</option><option>Influencer</option><option>Email</option><option>OOH</option><option>Mixta</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Canal</label><input id="camp-canal" placeholder="Ej: Instagram, TikTok, Email..."></div>
      <div class="form-group"><label>Estado</label>
        <select id="camp-estado">
          <option>Planificada</option><option>Activa</option><option>Pausada</option><option>Finalizada</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Fecha Inicio</label><input type="date" id="camp-inicio"></div>
      <div class="form-group"><label>Fecha Fin</label><input type="date" id="camp-fin"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Presupuesto (COP)</label><input type="number" id="camp-presupuesto" placeholder="0"></div>
      <div class="form-group"><label>SKU Objetivo</label><input id="camp-sku" placeholder="Ej: LBHA-30, NIAC-50"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Objetivo Unidades</label><input type="number" id="camp-obj-uds" placeholder="0"></div>
      <div class="form-group"><label>Resultado Unidades</label><input type="number" id="camp-res-uds" placeholder="0"></div>
    </div>
    <div class="form-row full">
      <div class="form-group"><label>Resultado Ventas (COP)</label><input type="number" id="camp-res-ventas" placeholder="0"></div>
    </div>
    <div class="form-row full">
      <div class="form-group"><label>Notas</label><textarea id="camp-notas" placeholder="Observaciones..."></textarea></div>
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:4px;">
      <button class="btn btn-outline" onclick="closeModal('modal-campana')">Cancelar</button>
      <button class="btn btn-primary" onclick="saveCampana()">Guardar</button>
    </div>
  </div>
</div>

<!-- Modal: Nuevo Influencer -->
<div class="modal-bg" id="modal-influencer">
  <div class="modal">
    <div class="modal-hdr">
      <div class="modal-title" id="modal-inf-title">Nuevo Influencer</div>
      <button class="modal-close" onclick="closeModal('modal-influencer')">&times;</button>
    </div>
    <input type="hidden" id="inf-edit-id">
    <div class="form-row">
      <div class="form-group"><label>Nombre *</label><input id="inf-nombre" placeholder="Nombre completo"></div>
      <div class="form-group"><label>Red Social</label>
        <select id="inf-red">
          <option>Instagram</option><option>TikTok</option><option>YouTube</option><option>Twitter</option><option>Otro</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>@Usuario</label><input id="inf-usuario" placeholder="@handle"></div>
      <div class="form-group"><label>Seguidores</label><input type="number" id="inf-seguidores" placeholder="0"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Engagement Rate %</label><input type="number" step="0.1" id="inf-er" placeholder="0.0"></div>
      <div class="form-group"><label>Nicho</label><input id="inf-nicho" placeholder="Skincare, Lifestyle..."></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Tarifa por post (COP)</label><input type="number" id="inf-tarifa" placeholder="0"></div>
      <div class="form-group"><label>Estado</label>
        <select id="inf-estado"><option>Activo</option><option>Inactivo</option><option>Bloqueado</option></select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Email <span style="color:#dc2626;">*</span> <span style="font-weight:400;color:var(--cx-text-mute);font-size:11px;">· para enviarle la factura cuando se le pague</span></label><input type="email" id="inf-email" placeholder="correo@ejemplo.com"></div>
      <div class="form-group"><label>Teléfono</label><input id="inf-tel" placeholder="+57..."></div>
    </div>
    <div class="form-row full">
      <div class="form-group"><label>Notas</label><textarea id="inf-notas" placeholder="Observaciones..."></textarea></div>
    </div>
    <div style="border-top:1px solid #e7e5e4;margin:10px 0 6px;padding-top:10px;">
      <div style="font-size:11px;font-weight:700;color:#6d28d9;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">🏦 Datos Bancarios</div>
      <div class="form-row">
        <div class="form-group"><label>Banco</label><input id="inf-banco" placeholder="Bancolombia, Nequi, Daviplata..."></div>
        <div class="form-group"><label>Tipo de cuenta</label>
          <select id="inf-tipo-cta">
            <option>Ahorros</option><option>Corriente</option><option>Nequi</option><option>Daviplata</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Número cuenta / Cel</label><input id="inf-cuenta" placeholder="3114902203 / 0123456789"></div>
        <div class="form-group"><label>Cédula / NIT</label><input id="inf-cedula" placeholder="1234567890"></div>
      </div>
    </div>
    <div style="border-top:1px solid #e7e5e4;margin:10px 0 6px;padding-top:10px;">
      <div style="font-size:11px;font-weight:700;color:#b45309;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">⏰ Ciclo de pago</div>
      <div class="form-row">
        <div class="form-group">
          <label>Frecuencia con la que se le paga</label>
          <select id="inf-ciclo-pago" style="background:var(--cx-bg-alt);color:var(--cx-text);border:1px solid #e7e5e4;border-radius:6px;padding:8px;width:100%;">
            <option value="Mensual">Mensual (cada 30 días)</option>
            <option value="Bimensual">Bimensual (cada 60 días)</option>
            <option value="Trimestral">Trimestral (cada 90 días)</option>
            <option value="Único">Único (no recurrente)</option>
            <option value="Sin ciclo">Sin ciclo definido</option>
          </select>
          <div style="font-size:10px;color:var(--cx-text-mute);margin-top:4px;">
            Cuando se cumple el ciclo y no hay solicitud activa, el panel muestra <span style="color:#fde047;">⏰ Toca pagar</span>.
          </div>
        </div>
      </div>
    </div>
    <div style="border-top:1px solid #e7e5e4;margin:10px 0 6px;padding-top:10px;">
      <div style="font-size:11px;font-weight:700;color:#16a34a;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">🎟️ Atribución de ventas</div>
      <div class="form-row full">
        <div class="form-group">
          <label>Discount code de Shopify</label>
          <input id="inf-discount-code" placeholder="ANIMUS_LAURA10" style="text-transform:uppercase;font-family:monospace;">
          <div style="font-size:10px;color:var(--cx-text-mute);margin-top:4px;line-height:1.4;">
            Cuando un cliente use este código en Shopify, la venta se atribuye automáticamente a este influencer.
            Convención: <code style="background:var(--cx-bg-alt);padding:1px 6px;border-radius:4px;color:#16a34a;">ANIMUS_NOMBRE_PCT</code> (ej: ANIMUS_LAURA10).
          </div>
        </div>
      </div>
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:4px;">
      <button class="btn btn-outline" onclick="closeModal('modal-influencer')">Cancelar</button>
      <button class="btn btn-primary" onclick="saveInfluencer()">Guardar</button>
    </div>
  </div>
</div>

<!-- Modal: Solicitar Pago Influencer -->
<!-- Modal · Gestionar pagos influencer (Jefferson · 27-may-2026 PM) -->
<div class="modal-bg" id="modal-gestionar-pagos">
  <div class="modal" style="max-width:780px;max-height:88vh;overflow-y:auto;">
    <div class="modal-hdr">
      <div class="modal-title">⚙ Gestionar pagos · <span id="gp-inf-nombre" style="color:#6d28d9;"></span></div>
      <button class="modal-close" onclick="closeModal('modal-gestionar-pagos')">&times;</button>
    </div>
    <input type="hidden" id="gp-inf-id">
    <div style="color:var(--cx-text-mute);font-size:12px;line-height:1.5;margin-bottom:12px;background:var(--cx-primary-soft);border:1px solid #4338ca;border-radius:8px;padding:10px 12px;">
      💡 <b>Si un pago está mal</b> (ya se pagó pero aparece pendiente, o aparece pendiente uno que no aplica) podés corregirlo acá. Todo cambio queda registrado en audit_log con motivo (INVIMA · Habeas Data).
    </div>
    <div id="gp-tabla-container" style="overflow-x:auto;">
      <table style="width:100%;border-collapse:collapse;font-size:12px;">
        <thead>
          <tr style="background:var(--cx-bg-alt);color:var(--cx-text-mute);font-size:10px;text-transform:uppercase;letter-spacing:.4px;">
            <th style="text-align:left;padding:8px;">Fecha</th>
            <th style="text-align:left;padding:8px;">Estado</th>
            <th style="text-align:right;padding:8px;">Valor</th>
            <th style="text-align:left;padding:8px;">Concepto</th>
            <th style="text-align:left;padding:8px;">OC</th>
            <th style="text-align:center;padding:8px;">Acciones</th>
          </tr>
        </thead>
        <tbody id="gp-tbody"></tbody>
      </table>
    </div>
    <div id="gp-alert" style="display:none;margin-top:10px;padding:10px;border-radius:6px;font-size:12px;"></div>
    <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:14px;border-top:1px solid #e7e5e4;padding-top:12px;">
      <button class="btn btn-outline" onclick="closeModal('modal-gestionar-pagos')">Cerrar</button>
    </div>
  </div>
</div>

<div class="modal-bg" id="modal-inf-pago">
  <div class="modal" style="max-width:460px;">
    <div class="modal-hdr">
      <div class="modal-title">&#x1F4B8; Solicitar Pago</div>
      <button class="modal-close" onclick="closeModal('modal-inf-pago')">&times;</button>
    </div>
    <input type="hidden" id="pago-inf-id">
    <div style="margin-bottom:14px;">
      <div style="font-size:13px;color:var(--cx-text-mute);margin-bottom:4px;">Influencer</div>
      <div id="pago-inf-nombre" style="font-weight:700;font-size:15px;color:var(--cx-text);"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Valor a pagar (COP) *</label><input type="number" id="pago-valor" placeholder="0"></div>
      <div class="form-group"><label>Concepto</label><input id="pago-concepto" placeholder="Post + Story / Reel..."></div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>&#128226; Fecha de publicaci&oacute;n <span style="color:#dc2626;">*</span></label>
        <input type="date" id="pago-fecha-contenido" onchange="recalcularVencePagoInf()" title="Día real en que el creador publicó el contenido. La promesa de pago (30 días) se cuenta desde esta fecha.">
      </div>
      <div class="form-group">
        <label>Vence pago (auto)</label>
        <input id="pago-vence" disabled style="background:var(--cx-primary-soft);color:#c7d2fe;font-weight:700;" placeholder="—">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group" style="flex:1;"><label>&#128221; De qu&eacute; trat&oacute; el contenido <span style="color:#dc2626;">*</span></label><input id="pago-entregable" placeholder="Ej: 1 Reel + 2 Stories del s&eacute;rum vitamina C"></div>
    </div>
    <div class="form-row">
      <div class="form-group" style="flex:1;"><label>&#128279; Link al post (opcional)</label><input id="pago-link-post" placeholder="https://instagram.com/p/..."></div>
    </div>
    <div style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:8px;padding:12px;margin:8px 0;font-size:12px;color:var(--cx-text-mute);">
      <div style="font-weight:700;color:#6d28d9;margin-bottom:6px;">&#x1F3E6; Datos bancarios</div>
      <div id="pago-banco-preview" style="line-height:1.8;"></div>
    </div>
    <!-- Linea explicativa: que pasa despues de crear la solicitud -->
    <div style="background:var(--cx-primary-soft);border:1px solid #4338ca;border-radius:8px;padding:10px 12px;margin:8px 0;font-size:11px;color:#c7d2fe;line-height:1.5;">
      <b style="color:#a5b4fc;">📌 Qué pasa después:</b><br>
      Esta solicitud va a <b>Sebastián</b> en /compras → tab Influencers para autorizar y pagar.
      Recibirás <b>email automático</b> cuando se haga el pago. Catalina no participa en este flujo.
    </div>
    <div id="pago-inf-alert" style="display:none;margin-bottom:8px;"></div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:8px;">
      <button class="btn btn-outline" onclick="closeModal('modal-inf-pago')">Cancelar</button>
      <button class="btn btn-primary" onclick="confirmarPagoInf()">💸 Enviar a Sebastián</button>
    </div>
  </div>
</div>


<!-- Modal: Dar de Baja Influencer -->
<div class="modal-bg" id="modal-dar-baja">
  <div class="modal" style="max-width:420px;">
    <div class="modal-hdr">
      <div class="modal-title">&#x26D4; Dar de Baja Influencer</div>
      <button class="modal-close" onclick="closeModal('modal-dar-baja')">&times;</button>
    </div>
    <input type="hidden" id="baja-inf-id">
    <div style="margin-bottom:14px;">
      <div style="font-size:13px;color:var(--cx-text-mute);margin-bottom:4px;">Influencer</div>
      <div id="baja-inf-nombre" style="font-weight:700;font-size:15px;color:var(--cx-text);"></div>
    </div>
    <div class="form-group" style="margin-bottom:12px;">
      <label>Motivo de baja *</label>
      <select id="baja-motivo-tipo" style="width:100%;background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:6px;padding:8px;color:var(--cx-text);">
        <option value="Pausa temporal">Pausa temporal</option>
        <option value="No cumplió métricas">No cumplió métricas</option>
        <option value="Conflicto de marca">Conflicto de marca</option>
        <option value="Presupuesto">Presupuesto</option>
        <option value="Solicitud del influencer">Solicitud del influencer</option>
        <option value="Otro">Otro</option>
      </select>
    </div>
    <div class="form-group" style="margin-bottom:12px;">
      <label>Observación (opcional)</label>
      <textarea id="baja-observacion" rows="3" placeholder="Detalles adicionales..." style="width:100%;background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:6px;padding:8px;color:var(--cx-text);resize:vertical;"></textarea>
    </div>
    <div style="background:var(--cx-warn-pale);border:1px solid var(--cx-hairline);border-radius:8px;padding:10px;font-size:12px;color:#b45309;margin-bottom:12px;">
      &#x26A0;&#xFE0F; El influencer quedará en estado <b>Baja</b> y visible en el historial. Podrá reactivarse en cualquier momento.
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;">
      <button class="btn btn-outline" onclick="closeModal('modal-dar-baja')">Cancelar</button>
      <button class="btn btn-danger" onclick="confirmarDarDeBaja()">Dar de Baja</button>
    </div>
  </div>
</div>

<!-- Modal: Nuevo Contenido -->
<div class="modal-bg" id="modal-contenido">
  <div class="modal">
    <div class="modal-hdr">
      <div class="modal-title" id="modal-cont-title">Nueva Pieza de Contenido</div>
      <button class="modal-close" onclick="closeModal('modal-contenido')">&times;</button>
    </div>
    <input type="hidden" id="cont-edit-id">
    <div class="form-row">
      <div class="form-group"><label>Tipo</label>
        <select id="cont-tipo"><option>Post</option><option>Story</option><option>Reel</option><option>Video</option><option>Email</option><option>Banner</option></select>
      </div>
      <div class="form-group"><label>Plataforma</label>
        <select id="cont-plataforma"><option>Instagram</option><option>TikTok</option><option>YouTube</option><option>Email</option><option>Web</option><option>Otro</option></select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Campaña</label>
        <select id="cont-campana-sel"><option value="">Sin campaña</option></select>
      </div>
      <div class="form-group"><label>Influencer</label>
        <select id="cont-influencer-sel"><option value="">Sin influencer (interno)</option></select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Fecha programada</label><input type="date" id="cont-fecha-prog"></div>
      <div class="form-group"><label>Fecha publicación real</label><input type="date" id="cont-fecha"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Estado (Kanban)</label>
        <select id="cont-estado">
          <option value="Brief">📝 Brief</option>
          <option value="Produccion">🎬 Producción</option>
          <option value="Pendiente">⏰ Pendiente publicación</option>
          <option value="Publicado">✅ Publicado</option>
          <option value="Performance">📊 Performance</option>
        </select>
      </div>
      <div class="form-group"><label>SKU objetivo</label><input id="cont-sku" placeholder="Ej: LBHA-30" style="text-transform:uppercase;font-family:monospace;"></div>
    </div>
    <div class="form-row full">
      <div class="form-group"><label>Mensaje principal (claim)</label><input id="cont-mensaje" placeholder="Lo que el creador debe transmitir en una frase"></div>
    </div>
    <div class="form-row full">
      <div class="form-group"><label>URL Publicación (cuando ya se publicó)</label><input id="cont-url" placeholder="https://instagram.com/p/..."></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Likes</label><input type="number" id="cont-likes" value="0"></div>
      <div class="form-group"><label>Comentarios</label><input type="number" id="cont-comentarios" value="0"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Alcance</label><input type="number" id="cont-alcance" value="0"></div>
      <div class="form-group"><label>Conversiones</label><input type="number" id="cont-conversiones" value="0"></div>
    </div>
    <div class="form-row full">
      <div class="form-group"><label>Caption / Descripción completa</label><textarea id="cont-caption"></textarea></div>
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:4px;">
      <button class="btn btn-outline" onclick="closeModal('modal-contenido')">Cancelar</button>
      <button class="btn btn-primary" onclick="saveContenido()">Guardar</button>
    </div>
  </div>
</div>

<!-- Modal: Ver resultado agente -->
<div class="modal-bg" id="modal-agente-result">
  <div class="modal" style="max-width:700px;">
    <div class="modal-hdr">
      <div class="modal-title" id="modal-agent-title">Resultado</div>
      <button class="modal-close" onclick="closeModal('modal-agente-result')">&times;</button>
    </div>
    <div id="modal-agent-content" style="font-size:13px;color:var(--cx-text);white-space:pre-wrap;max-height:500px;overflow-y:auto;background:var(--cx-bg-alt);border-radius:8px;padding:16px;font-family:'Segoe UI',sans-serif;"></div>
  </div>
</div>
<!-- /MODALS -->

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: AGENCIA                                                   -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-agencia" class="tab-panel intel-sub">
  <div class="intel-subnav" data-intel-nav="1">
    <button onclick="showSub('estrategia')">&#x1F9E0; Estrategia del mes</button>
    <button onclick="showSub('agentes')">&#x1F916; Agentes IA</button>
    <button class="intel-active" onclick="showSub('agencia')">&#x1F3C6; Score de creadores</button>
    <button onclick="showSub('analytics')">&#x1F4CA; Histórico de inversión</button>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:6px;">
    <div>
      <div class="page-title" style="margin-bottom:2px;">&#x1F3C6; Score de Creadores &#x2014; Inteligencia de Mercado</div>
      <div class="page-sub">Score de influencers, auditoría de portafolio, análisis competitivo y propuestas de campaña.</div>
    </div>
    <button class="btn-primary" style="font-size:12px;padding:8px 16px;" onclick="loadAgencia(true)">&#x1F504; Actualizar</button>
  </div>
  <div class="kpi-grid" style="grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;margin-bottom:20px;">
    <div class="kpi-card blue"><div class="kpi-label">Influencers activos</div><div class="kpi-val" id="ag-kpi-activos">-</div></div>
    <div class="kpi-card green"><div class="kpi-label">Score promedio</div><div class="kpi-val" id="ag-kpi-score">-</div></div>
    <div class="kpi-card yellow"><div class="kpi-label">En riesgo</div><div class="kpi-val" id="ag-kpi-riesgo">-</div></div>
    <div class="kpi-card red"><div class="kpi-label">Hallazgos criticos</div><div class="kpi-val" id="ag-kpi-critical">-</div></div>
    <div class="kpi-card" style="border-color:#667eea;"><div class="kpi-label">Inversion total</div><div class="kpi-val" id="ag-kpi-inversion" style="color:#667eea;">-</div></div>
  </div>
  <div class="card" style="margin-bottom:20px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <div style="font-weight:700;color:var(--cx-text);font-size:15px;">Score de Influencers</div>
      <div style="font-size:11px;color:var(--cx-text-mute);">engagement 30pct &middot; inversion 25pct &middot; seguidores 20pct &middot; recencia 15pct &middot; contenido 10pct</div>
    </div>
    <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead><tr style="border-bottom:1px solid #e7e5e4;">
        <th style="padding:8px;text-align:left;color:var(--cx-text-mute);font-weight:600;">Influencer</th>
        <th style="padding:8px;text-align:left;color:var(--cx-text-mute);font-weight:600;">Nicho</th>
        <th style="padding:8px;text-align:center;color:var(--cx-text-mute);font-weight:600;">Score</th>
        <th style="padding:8px;text-align:right;color:var(--cx-text-mute);font-weight:600;">Engagement</th>
        <th style="padding:8px;text-align:right;color:var(--cx-text-mute);font-weight:600;">Seguidores</th>
        <th style="padding:8px;text-align:right;color:var(--cx-text-mute);font-weight:600;">Campanas</th>
        <th style="padding:8px;text-align:right;color:var(--cx-text-mute);font-weight:600;">Invertido</th>
        <th style="padding:8px;text-align:center;color:var(--cx-text-mute);font-weight:600;">Estado</th>
      </tr></thead>
      <tbody id="ag-scoring-tbody"><tr class="empty-row"><td colspan="8">Cargando...</td></tr></tbody>
    </table>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
    <div class="card">
      <div style="font-weight:700;color:var(--cx-text);font-size:15px;margin-bottom:14px;">Auditoria de Portafolio</div>
      <div id="ag-audit-list"><div style="color:var(--cx-text-mute);font-size:13px;">Cargando...</div></div>
    </div>
    <div class="card">
      <div style="font-weight:700;color:var(--cx-text);font-size:15px;margin-bottom:14px;">Analisis Competitivo</div>
      <div id="ag-competition"><div style="color:var(--cx-text-mute);font-size:13px;">Cargando...</div></div>
    </div>
  </div>
  <div class="card">
    <div style="font-weight:700;color:var(--cx-text);font-size:15px;margin-bottom:14px;">Propuestas de Campana</div>
    <div id="ag-proposals"><div style="color:var(--cx-text-mute);font-size:13px;">Cargando...</div></div>
  </div>
</div>

<!-- Tab "Agencia Ads" eliminado: no se usaba data HHA y se solapaba con
     el agente master Estrategia (que sí cruza Shopify + IG + stock + calendar
     + influencers). El skill genérico ads_skill.py se conserva en backend
     por si se necesita en el futuro (reusable). -->
<div id="tab-ads" class="tab-panel" style="display:none !important;"></div>


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
  if(r===null||r===undefined||r==='') return '<span class="badge badge-gray">—</span>';
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
// Sub-tab activa dentro de "Inteligencia". Persiste para que cuando el user
// vuelve a la tab Inteligencia se quede en la última vista que estaba viendo.
// Default = 'estrategia' — el master agent es lo que el jefe ve primero.
let _intelSub = 'estrategia';

function switchTab(name) {
  // Resolver: 'inteligencia' es virtual — abre el sub-panel actual (default agentes)
  const realPanel = (name === 'inteligencia') ? _intelSub : name;

  // Highlight botón superior — match por data-tab. Inteligencia se activa
  // cuando estamos viendo cualquiera de sus sub-paneles.
  document.querySelectorAll('.tab-btn').forEach(b => {
    const t = b.dataset.tab;
    const isActive = (t === name) ||
                     (t === 'dashboard' && ['estrategia','agentes','analytics','agencia'].includes(realPanel));
    b.classList.toggle('active', isActive);
  });

  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  const panel = document.getElementById('tab-' + realPanel);
  if (panel) panel.classList.add('active');

  if (!_loaded[realPanel]) { _loaded[realPanel] = true; loadTab(realPanel); }
}

// Sub-navegación dentro de Inteligencia (Agentes / Creadores / Histórico)
function showSub(sub) {
  _intelSub = sub;
  // Highlight de los botones de sub-nav (el activo se sincroniza en TODAS las
  // copias de la sub-nav porque cada panel tiene su propia copia)
  document.querySelectorAll('.intel-subnav button').forEach(btn => {
    const target = (btn.getAttribute('onclick')||'').match(/showSub\('(\w+)'\)/);
    if (!target) return;
    btn.classList.toggle('intel-active', target[1] === sub);
  });
  switchTab(sub);
}

function loadTab(name) {
  if(name==='hoy') hoyCargarResumen();
  else if(name==='cmo') cmoCargarPlan();
  else if(name==='dashboard') loadDashboard();
  else if(name==='campanas') loadCampanas();
  else if(name==='influencers') loadInfluencers();
  else if(name==='pagos') loadPagosInfluencers();
  else if(name==='contenido') loadContenido();
  else if(name==='estrategia') loadUltimaEstrategia();
  else if(name==='agentes') { loadAgentLog(); loadCampanasForSelect(); loadConnections(); loadFeedbackStats(); }
  else if(name==='analytics') loadAnalytics();
  else if(name==='agencia') loadAgencia();
}

// ═══════════════════════════════════════════════════════════════════
// 🤖 TAB CMO IA · Plan del día generado por Claude director
// Sebastián 27-may-2026 PM · "marketing debe ser superior · agencia IA"
// ═══════════════════════════════════════════════════════════════════
// ─── Historial planes CMO IA · 27-may-2026 PM ─────────────────────────
async function cmoAbrirHistorial(){
  const m = document.getElementById('modal-cmo-historial');
  if(!m) return;
  m.classList.add('open');
  const body = document.getElementById('cmo-hist-body');
  body.innerHTML = '<div style="color:var(--cx-text-mute);text-align:center;padding:24px">Cargando…</div>';
  try{
    const r = await fetch('/api/marketing/cmo/historial-planes?limit=60', {credentials:'same-origin'});
    if(!r.ok){ body.innerHTML = '<div style="color:#dc2626">HTTP '+r.status+'</div>'; return; }
    const d = await r.json();
    if(!d.ok){ body.innerHTML = '<div style="color:#dc2626">'+esc(d.error||'error')+'</div>'; return; }
    const planes = d.planes || [];
    if(!planes.length){ body.innerHTML = '<div style="color:var(--cx-text-mute);text-align:center;padding:24px">Sin planes registrados aún · esperá al cron 7 AM o generá uno con ⚡ Generar plan ahora.</div>'; return; }
    // ── Sparkline tendencia tasa aprobación · últimos 30 planes ──
    const ordenados = [...planes].slice().reverse();  // más viejo a izquierda
    const last30 = ordenados.slice(-30);
    let sparkHtml = '';
    if(last30.length >= 2){
      const bars = last30.map(p => {
        const s = p.stats || {};
        const ratio = s.total > 0 ? (s.aprobadas/s.total) : 0;
        const h = Math.max(4, Math.round(ratio * 36));
        const col = ratio >= 0.5 ? '#34d399' : (ratio >= 0.25 ? '#f59e0b' : '#ef4444');
        return `<div title="${esc(p.fecha)} · ${Math.round(ratio*100)}% aprobadas" style="display:inline-block;width:8px;height:${h}px;background:${col};margin-right:2px;border-radius:2px 2px 0 0;vertical-align:bottom;"></div>`;
      }).join('');
      sparkHtml = '<div style="margin-bottom:14px;padding:10px 14px;background:var(--cx-bg-alt);border-radius:8px;">'
        + '<div style="font-size:11px;color:var(--cx-text-mute);margin-bottom:6px;">📈 Tendencia tasa aprobación · últimos '+last30.length+' planes</div>'
        + '<div style="height:40px;display:flex;align-items:flex-end;">'+bars+'</div>'
        + '<div style="font-size:10px;color:var(--cx-text-mute);margin-top:4px;display:flex;justify-content:space-between;">'
        + '<span>'+esc(last30[0].fecha)+'</span><span>'+esc(last30[last30.length-1].fecha)+'</span></div></div>';
    }
    let html = sparkHtml + '<table class="cmo-hist-tbl" style="width:100%;border-collapse:collapse;font-size:12px;">'
      + '<thead><tr style="background:var(--cx-bg-alt);color:var(--cx-text-mute);text-transform:uppercase;font-size:10px;letter-spacing:.4px;">'
      + '<th style="text-align:left;padding:8px 10px;">Fecha</th>'
      + '<th style="text-align:left;padding:8px 10px;">Estado</th>'
      + '<th class="mob-hide" style="text-align:left;padding:8px 10px;">Generado por</th>'
      + '<th style="text-align:right;padding:8px 10px;">Acciones</th>'
      + '<th style="text-align:right;padding:8px 10px;color:#16a34a;">✓ Aprob</th>'
      + '<th class="mob-hide" style="text-align:right;padding:8px 10px;color:#f59e0b;">⏸ Posp</th>'
      + '<th class="mob-hide" style="text-align:right;padding:8px 10px;color:#ef4444;">✕ Desc</th>'
      + '<th style="text-align:right;padding:8px 10px;color:#6d28d9;">⏳ Pend</th>'
      + '</tr></thead><tbody>';
    for(const p of planes){
      const s = p.stats || {};
      const ratioOk = s.total > 0 ? Math.round((s.aprobadas/s.total)*100) : 0;
      const bg = (p.fecha === (new Date().toISOString().slice(0,10))) ? 'background:rgba(167,139,250,.08);' : '';
      html += '<tr style="border-top:1px solid var(--cx-hairline);cursor:pointer;'+bg+'" '
        + 'onclick="cmoCargarPlanPorFecha(\''+esc(p.fecha)+'\')" '
        + 'onmouseover="this.style.background=\'rgba(52,211,153,.05)\'" '
        + 'onmouseout="this.style.background=\''+ (bg ? 'rgba(167,139,250,.08)' : 'transparent') +'\'">';
      html += '<td style="padding:8px 10px;font-weight:600;">'+esc(p.fecha)+'</td>';
      html += '<td style="padding:8px 10px;"><span class="badge" style="font-size:10px;">'+esc(p.estado||'-')+'</span></td>';
      html += '<td class="mob-hide" style="padding:8px 10px;color:var(--cx-text-mute);font-size:11px;">'+esc(p.generado_por||'-')+'</td>';
      html += '<td style="padding:8px 10px;text-align:right;font-weight:700;color:var(--cx-text);">'+(s.total||0)+'</td>';
      html += '<td style="padding:8px 10px;text-align:right;color:#16a34a;font-weight:700;">'+(s.aprobadas||0)
        +'<span style="font-size:10px;opacity:.7;"> ('+ratioOk+'%)</span></td>';
      html += '<td class="mob-hide" style="padding:8px 10px;text-align:right;color:#f59e0b;">'+(s.pospuestas||0)+'</td>';
      html += '<td class="mob-hide" style="padding:8px 10px;text-align:right;color:#ef4444;">'+(s.descartadas||0)+'</td>';
      html += '<td style="padding:8px 10px;text-align:right;color:#6d28d9;">'+(s.pendientes||0)+'</td>';
      html += '</tr>';
    }
    html += '</tbody></table>';
    // Resumen agregado al final
    const agg = planes.reduce((a,p) => {
      const s = p.stats || {};
      a.total += s.total||0; a.aprob += s.aprobadas||0;
      a.posp += s.pospuestas||0; a.desc += s.descartadas||0;
      a.pend += s.pendientes||0;
      return a;
    }, {total:0,aprob:0,posp:0,desc:0,pend:0});
    const taFinal = agg.total > 0 ? Math.round((agg.aprob/agg.total)*100) : 0;
    html += '<div style="margin-top:14px;padding:10px 14px;background:var(--cx-bg-alt);border-radius:8px;font-size:12px;color:var(--cx-text-soft);">'
      + '<b style="color:#6d28d9">Total ' + planes.length + ' planes</b> · '
      + agg.total + ' acciones totales · '
      + '<span style="color:#16a34a;font-weight:700">'+agg.aprob+' aprobadas ('+taFinal+'% tasa)</span> · '
      + '<span style="color:#f59e0b">'+agg.posp+' pospuestas</span> · '
      + '<span style="color:#ef4444">'+agg.desc+' descartadas</span> · '
      + '<span style="color:#6d28d9">'+agg.pend+' pendientes</span>'
      + '</div>';
    body.innerHTML = html;
  } catch(e){
    body.innerHTML = '<div style="color:#dc2626">Error red: '+esc(e.message)+'</div>';
  }
}
async function cmoCargarPlanPorFecha(fecha){
  closeModal('modal-cmo-historial');
  // Setear fecha y disparar carga
  window._CMO_FECHA_FORZADA = fecha;
  await cmoCargarPlan();
  window._CMO_FECHA_FORZADA = null;  // reset al siguiente reload
}

async function cmoCargarPlan(){
  const empty = document.getElementById('cmo-empty');
  const list = document.getElementById('cmo-acciones-list');
  const kpiBar = document.getElementById('cmo-kpi-bar');
  list.innerHTML = '<div style="color:var(--cx-text-mute);text-align:center;padding:18px;">⏳ Cargando plan...</div>';
  empty.style.display = 'none';
  kpiBar.style.display = 'none';
  try {
    const fechaQs = window._CMO_FECHA_FORZADA
      ? ('?fecha='+encodeURIComponent(window._CMO_FECHA_FORZADA))
      : '';
    const r = await fetch('/api/marketing/cmo/plan-diario'+fechaQs, {credentials:'same-origin'});
    const d = await r.json();
    if(d.sin_plan){
      list.innerHTML = '';
      empty.style.display = 'block';
      return;
    }
    // Si estamos viendo plan histórico (no de hoy), banner
    if(window._CMO_FECHA_FORZADA){
      const banner = document.createElement('div');
      banner.style.cssText = 'background:rgba(167,139,250,.15);border:1px solid rgba(167,139,250,.4);border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:12px;color:var(--cx-text-soft);';
      banner.innerHTML = '📜 Plan histórico del <b>'+window._CMO_FECHA_FORZADA+'</b> · <a href="#" onclick="window._CMO_FECHA_FORZADA=null;cmoCargarPlan();return false;" style="color:#6d28d9">↩ volver a hoy</a>';
      list.parentNode.insertBefore(banner, list);
    }
    if(!d.ok || !d.acciones){
      list.innerHTML = '<div style="color:#dc2626;text-align:center;padding:18px;">Error: '+_escHtml(d.error||'desconocido')+'</div>';
      return;
    }
    // KPIs
    const acc = d.acciones || [];
    const criticas = acc.filter(a=>a.prioridad==='critica').length;
    const altas = acc.filter(a=>a.prioridad==='alta').length;
    const pendientes = acc.filter(a=>a.estado==='pendiente').length;
    const ejecutadas = acc.filter(a=>a.estado==='ejecutada').length;
    const descartadas = acc.filter(a=>a.estado==='descartada').length;
    kpiBar.style.display='grid';
    kpiBar.innerHTML = [
      {l:'Acciones del día', v:acc.length, c:'#a78bfa'},
      {l:'🔴 Críticas', v:criticas, c:'#fca5a5'},
      {l:'🟡 Altas', v:altas, c:'#fcd34d'},
      {l:'⏳ Pendientes', v:pendientes, c:'#67e8f9'},
      {l:'✅ Ejecutadas', v:ejecutadas, c:'#86efac'},
      {l:'✕ Descartadas', v:descartadas, c:'#64748b'},
    ].map(k=>`<div style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:10px;padding:12px;">`
      +`<div style="font-size:22px;font-weight:800;color:${k.c}">${k.v}</div>`
      +`<div style="font-size:10px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.4px;margin-top:2px">${k.l}</div></div>`).join('');
    // Lista de acciones
    if(!acc.length){
      list.innerHTML = '<div style="color:var(--cx-text-mute);text-align:center;padding:18px;">El CMO IA no propuso acciones para hoy · datos insuficientes.</div>';
      return;
    }
    list.innerHTML = acc.map(a => cmoRenderAccion(a)).join('');
  } catch(e){
    list.innerHTML = '<div style="color:#dc2626;text-align:center;padding:18px;">Error red: '+_escHtml(e.message)+'</div>';
  }
}
function cmoRenderAccion(a){
  const priCfg = {
    critica:{bg:'#7f1d1d',fg:'#fecaca',label:'🔴 CRÍTICA'},
    alta:{bg:'#854d0e',fg:'#fde047',label:'🟡 ALTA'},
    media:{bg:'#1e3a8a',fg:'#bfdbfe',label:'🔵 MEDIA'},
    baja:{bg:'#e7e5e4',fg:'#cbd5e1',label:'⚪ BAJA'},
  };
  const pri = priCfg[a.prioridad] || priCfg.media;
  const estadoCfg = {
    pendiente:{bg:'#f1f5f9',fg:'#94a3b8',label:'⏳ Pendiente'},
    aprobada:{bg:'#064e3b',fg:'#86efac',label:'✓ Aprobada'},
    ejecutada:{bg:'#064e3b',fg:'#86efac',label:'✅ Ejecutada'},
    pospuesta:{bg:'#854d0e',fg:'#fcd34d',label:'⏸ Pospuesta'},
    descartada:{bg:'#374151',fg:'#9ca3af',label:'✕ Descartada'},
    fallida:{bg:'#7f1d1d',fg:'#fca5a5',label:'⚠ Fallida'},
  };
  const est = estadoCfg[a.estado] || estadoCfg.pendiente;
  let payload = {};
  try { payload = JSON.parse(a.payload_json || '{}'); } catch(_){}
  let resultado = null;
  try { resultado = JSON.parse(a.resultado_ejecucion || 'null'); } catch(_){}
  const ejecutable = a.agente_workflow && a.estado === 'pendiente';
  const decidible = a.estado === 'pendiente';

  let html = '<div style="background:var(--cx-card);border:1px solid #e7e5e4;border-left:4px solid '+pri.bg+';border-radius:10px;padding:14px 16px;">';
  // Header
  html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:8px;flex-wrap:wrap;">';
  html += '<div style="flex:1;min-width:240px;">';
  html += '<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:4px;">';
  html += '<span style="background:'+pri.bg+';color:'+pri.fg+';padding:2px 8px;border-radius:10px;font-size:10px;font-weight:800;">'+pri.label+'</span>';
  html += '<span style="background:'+est.bg+';color:'+est.fg+';padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;">'+est.label+'</span>';
  if (a.agente_workflow) {
    html += '<span style="background:var(--cx-primary-soft);color:#6d28d9;padding:2px 8px;border-radius:10px;font-size:10px;font-family:monospace;">→ '+_escHtml(a.agente_workflow)+'</span>';
  }
  html += '</div>';
  html += '<div style="font-size:15px;font-weight:700;color:var(--cx-text);margin-bottom:4px;">'+_escHtml(a.titulo||'')+'</div>';
  if (a.descripcion) html += '<div style="font-size:12px;color:var(--cx-text-mute);line-height:1.5;">'+_escHtml(a.descripcion)+'</div>';
  html += '</div></div>';
  // Acciones
  if (decidible){
    html += '<div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;">';
    if (ejecutable){
      html += '<button onclick="cmoDecidir('+a.id+',\'aprobar\')" style="background:var(--cx-success-pale);color:#fff;border:0;padding:8px 14px;border-radius:6px;cursor:pointer;font-weight:700;font-size:12px;">✓ Aprobar y ejecutar</button>';
    } else {
      html += '<button onclick="cmoDecidir('+a.id+',\'aprobar\')" style="background:var(--cx-success-pale);color:#fff;border:0;padding:8px 14px;border-radius:6px;cursor:pointer;font-weight:700;font-size:12px;" title="Marcar como aprobada (sin workflow auto)">✓ Aprobar</button>';
    }
    html += '<button onclick="cmoDecidir('+a.id+',\'posponer\')" style="background:#854d0e;color:#b45309;border:0;padding:8px 14px;border-radius:6px;cursor:pointer;font-weight:700;font-size:12px;">⏸ Posponer</button>';
    html += '<button onclick="cmoDecidir('+a.id+',\'descartar\')" style="background:#7f1d1d;color:#fecaca;border:0;padding:8px 14px;border-radius:6px;cursor:pointer;font-weight:700;font-size:12px;">✕ Descartar</button>';
    html += '</div>';
  }
  // Resultado ejecutado
  if (resultado && (resultado.ok === true || resultado.campanas !== undefined)){
    html += '<details style="margin-top:10px;background:var(--cx-bg-alt);border-radius:6px;padding:8px 12px;"><summary style="cursor:pointer;color:#86efac;font-size:11px;font-weight:700;">Ver resultado de ejecución</summary>';
    html += '<pre style="font-size:10px;color:var(--cx-text-mute);margin-top:6px;max-height:200px;overflow:auto;">'+_escHtml(JSON.stringify(resultado, null, 2))+'</pre></details>';
  }
  if (resultado && resultado.ok === false){
    html += '<div style="margin-top:8px;background:#7f1d1d;color:#fecaca;padding:6px 10px;border-radius:6px;font-size:11px;">⚠ Error: '+_escHtml(resultado.error||'desconocido')+'</div>';
  }
  html += '</div>';
  return html;
}
async function cmoGenerarPlanForzar(){
  const list = document.getElementById('cmo-acciones-list');
  const empty = document.getElementById('cmo-empty');
  list.innerHTML = '<div style="color:var(--cx-text-mute);text-align:center;padding:18px;">🤖 Claude generando plan... (esto tarda 15-30s)</div>';
  empty.style.display = 'none';
  try {
    const r = await fetch('/api/marketing/cmo/plan-diario', {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token': window._csrfTok || ''},
      body: JSON.stringify({forzar: true})
    });
    const d = await r.json();
    if (r.ok){ setTimeout(cmoCargarPlan, 400); }
    else { list.innerHTML = '<div style="color:#dc2626;text-align:center;padding:18px;">Error '+r.status+': '+_escHtml(d.error||'')+'</div>'; }
  } catch(e){
    list.innerHTML = '<div style="color:#dc2626;text-align:center;padding:18px;">Error red: '+_escHtml(e.message)+'</div>';
  }
}
async function cmoDecidir(aid, decision){
  if (decision === 'descartar' && !confirm('¿Descartar esta acción? · queda registrada en audit.')) return;
  const motivo = (decision === 'descartar' || decision === 'posponer')
    ? (prompt('Motivo (opcional · ayuda a la IA a aprender):') || '')
    : '';
  try {
    if (!window._csrfTok){
      try { const tr = await fetch('/api/csrf-token',{credentials:'same-origin'}); if(tr.ok){const td=await tr.json(); window._csrfTok=td.csrf_token||'';} } catch(_){}
    }
    const r = await fetch('/api/marketing/cmo/accion/'+aid+'/decidir', {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token': window._csrfTok || ''},
      body: JSON.stringify({decision: decision, motivo: motivo})
    });
    const d = await r.json();
    if (d.ok){ cmoCargarPlan(); }
    else { alert('Error '+r.status+': '+(d.error||'desconocido')); }
  } catch(e){
    alert('Error red: '+e.message);
  }
}

// ═══════════════════════════════════════════════════════════════════
// TAB "HOY" — Centro de ejecución (Fase 2/4 marketing)
// Sebastian (29-abr-2026): "centro de ejecución, agencia de marketing
// con todos los agentes funcionando, tirando todo".
// ═══════════════════════════════════════════════════════════════════

function _hoyLog(msg) {
  const el = document.getElementById('hoy-log');
  if(!el) return;
  const ts = new Date().toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  const line = `<div>[${ts}] ${_escHtml(msg)}</div>`;
  if(el.textContent.trim() === 'Sin actividad reciente.') el.innerHTML = '';
  el.innerHTML = line + el.innerHTML;
  // Cap a 50 líneas para evitar memory leak en sesiones largas
  const children = el.children;
  if(children.length > 50) {
    for(let i = children.length - 1; i >= 50; i--) {
      el.removeChild(children[i]);
    }
  }
}

function _escHtml(s) {
  return String(s||'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
}

async function hoyCargarResumen() {
  // KPIs rápidos · endpoint dedicado /api/marketing/kpis-hoy (fix P0 25-may)
  const setErr = () => {
    ['hoy-kpi-pend','hoy-kpi-eventos','hoy-kpi-riesgo','hoy-kpi-campanas'].forEach(id => {
      const el = document.getElementById(id);
      if(el) { el.textContent='?'; el.title='Error cargando KPI'; el.style.opacity='0.5'; }
    });
  };
  try {
    const r = await fetch('/api/marketing/kpis-hoy', {credentials:'same-origin'});
    if(!r.ok) {
      _hoyLog('❌ KPIs HTTP ' + r.status);
      setErr();
      return;
    }
    const d = await r.json();
    const k = d.kpis || {};
    const set = (id, val) => {
      const el = document.getElementById(id);
      if(!el) return;
      el.textContent = (val ?? 0);
      el.title = '';
      el.style.opacity = '1';
    };
    set('hoy-kpi-pend',     k.influencers_pendientes_pago);
    set('hoy-kpi-eventos',  k.eventos_proximos);
    set('hoy-kpi-riesgo',   k.skus_en_riesgo);
    set('hoy-kpi-campanas', k.campanas_activas);
  } catch(e) {
    _hoyLog('Error cargando KPIs: ' + e.message);
    setErr();
  }
}

async function hoyEjecutarTodos() {
  _hoyLog('⚡ Ejecutando los 11 agentes en paralelo...');
  const acc = document.getElementById('hoy-acciones');
  acc.innerHTML = '<div style="color:var(--cx-text-mute);text-align:center;padding:20px"><span class="spin"></span> Ejecutando agentes...</div>';

  // Lista de agentes a ejecutar (orden de prioridad para mostrar)
  const agentes = [
    {key:'estrategia', label:'Estrategia (master)', icon:'🧠', color:'#7c3aed'},
    {key:'alerta_stock', label:'Alerta Stock', icon:'📦', color:'#dc2626'},
    {key:'estacionalidad', label:'Estacionalidad', icon:'📅', color:'#f59e0b'},
    {key:'oportunidad', label:'Oportunidad', icon:'💡', color:'#0891b2'},
    {key:'roi', label:'ROI', icon:'📊', color:'#16a34a'},
    {key:'canibal', label:'Canibalización', icon:'⚠️', color:'#dc2626'},
    {key:'reorden', label:'Reorden B2B', icon:'🔁', color:'#a78bfa'},
    {key:'tendencias', label:'Tendencias', icon:'📈', color:'#34d399'},
    {key:'pricing', label:'Pricing', icon:'💰', color:'#f59e0b'},
    {key:'contenido_auto', label:'Contenido Auto', icon:'✍️', color:'#7c3aed'},
    {key:'brief', label:'Brief', icon:'📋', color:'#0891b2'},
  ];

  // FIX 7-jul (audit ultracode · M43/M59): SERIAL, no Promise.all. Cada agente llama a Claude SÍNCRONO (hasta
  // 90s con Sonnet); 11 en paralelo ocupaban los 3 workers Gunicorn → 502 app-wide ("Unexpected token <" en
  // cualquier pantalla). En serie solo hay 1 llamada IA en vuelo → el resto del app sigue respondiendo.
  const resultados = [];
  for (const ag of agentes) {
    try {
      const r = await fetch('/api/marketing/agentes/' + ag.key, _fetchOpts('POST'));
      if(!r.ok) { resultados.push({agente:ag, error:`HTTP ${r.status}`}); continue; }
      const d = await r.json();
      resultados.push({agente:ag, data:d});
    } catch(e) {
      resultados.push({agente:ag, error:e.message});
    }
  }

  // Construir cards de "acciones recomendadas" combinando resultados
  let html = '';
  let accionesCount = 0;

  for(const res of resultados) {
    const ag = res.agente;
    if(res.error) {
      _hoyLog(`❌ ${ag.label}: ${res.error}`);
      continue;
    }
    const d = res.data || {};
    _hoyLog(`✓ ${ag.label}: ${d.titulo||'OK'}`);
    // Cache para que "Aplicar" use este payload sin re-ejecutar
    window._hoyUltimoOutput[ag.key] = d;

    // Extraer acciones útiles del agente
    let resumenAccion = null;
    if(ag.key === 'estrategia') {
      const k = d.kpis || {};
      const items = [];
      if(k.skus_en_riesgo > 0) items.push(`${k.skus_en_riesgo} SKU(s) en riesgo`);
      if(k.skus_a_empujar > 0) items.push(`${k.skus_a_empujar} SKU(s) por empujar`);
      if(k.eventos_en_60d > 0) items.push(`${k.eventos_en_60d} evento(s) cosmético(s) en 60d`);
      if(items.length) resumenAccion = items.join(' · ');
    } else if(ag.key === 'alerta_stock') {
      const total = d.total || 0;
      if(total > 0) resumenAccion = `${total} SKU(s) con stock crítico/advertencia`;
    } else if(ag.key === 'estacionalidad') {
      const c = d.criticos || 0;
      if(c > 0) resumenAccion = `${c} SKU(s) en estado crítico para eventos próximos`;
    } else if(ag.key === 'oportunidad') {
      const t = d.total || 0;
      if(t > 0) resumenAccion = `${t} SKU(s) con oportunidad de campaña`;
    } else if(ag.key === 'roi') {
      const cmp = (d.campanas||[]).filter(x => x.roi_pct < 0);
      if(cmp.length) resumenAccion = `${cmp.length} campaña(s) con ROI negativo`;
    } else if(ag.key === 'canibal') {
      const c = (d.conflictos||[]).length;
      if(c > 0) resumenAccion = `${c} conflicto(s) entre campañas`;
    } else if(ag.key === 'reorden') {
      const urg = (d.predicciones||[]).filter(p => p.urgencia==='hoy' || p.urgencia==='esta semana');
      if(urg.length) resumenAccion = `${urg.length} cliente(s) B2B con reorden próxima`;
    } else if(ag.key === 'contenido_auto') {
      const p = (d.piezas||[]).length;
      if(p > 0) resumenAccion = `${p} pieza(s) de contenido sugerida(s) para top SKUs`;
    }

    if(resumenAccion) {
      accionesCount++;
      html += `<div style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-left:4px solid ${ag.color};border-radius:10px;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;gap:14px">
        <div>
          <div style="font-size:13px;font-weight:700;color:var(--cx-text)">${ag.icon} ${_escHtml(ag.label)}</div>
          <div style="font-size:12px;color:var(--cx-text-mute);margin-top:2px">${_escHtml(resumenAccion)}</div>
        </div>
        <div style="display:flex;gap:6px;flex-shrink:0">
          <button class="btn btn-outline btn-sm" onclick="hoyVerDetalleAgente('${ag.key}')" title="Ver detalle del análisis">👁 Ver</button>
          <button class="btn btn-primary btn-sm" onclick="hoyAplicarAgente('${ag.key}')" title="Convertir propuesta en entidad real">✓ Aplicar</button>
        </div>
      </div>`;
    }
  }

  if(accionesCount === 0) {
    acc.innerHTML = '<div style="background:var(--cx-success-pale);color:#16a34a;padding:14px;border-radius:8px;text-align:center;font-size:13px">✅ Sin acciones críticas detectadas. Todo bajo control.</div>';
  } else {
    acc.innerHTML = `<div style="font-size:11px;color:var(--cx-text-mute);margin-bottom:6px">${accionesCount} acción(es) detectada(s) por la IA · click ✓ Aplicar para ejecutar la propuesta</div>` + html;
  }
  _hoyLog(`✓ Análisis completo: ${accionesCount} accion(es) detectadas`);
  hoyCargarResumen(); // refresh KPIs
}

async function hoyVerDetalleAgente(key) {
  // Reusar tab Inteligencia → Agentes (typo fix 25-may: era runAgente)
  switchTab('inteligencia');
  if(typeof showSub === 'function') showSub('agentes');
  if(typeof runAgent === 'function') {
    // Espera que el DOM monte btn-${key} antes de ejecutar
    setTimeout(() => {
      const btn = document.getElementById('btn-' + key);
      if(btn) runAgent(key);
      else _hoyLog('⚠ No se encontró botón btn-' + key + ' en Inteligencia');
    }, 400);
  } else {
    _hoyLog('⚠ runAgent no disponible');
  }
}

// Cache del último output de cada agente (para que hoyAplicarAgente lo
// pase al workflow sin re-ejecutar el agente).
window._hoyUltimoOutput = {};

async function hoyAplicarAgente(key) {
  // Workflow Fase 3: convertir propuesta del agente en entidad real
  if(!confirm(`Convertir las propuestas del agente "${key}" en entidades reales?\\n\\n` +
              `Esto puede crear: campañas (Planificadas), briefs en Kanban, flags de reposición.\\n` +
              `Es idempotente — no duplica si ya existen.`)) return;

  // Si no tenemos cache, re-ejecutar el agente
  let payload = window._hoyUltimoOutput[key];
  if(!payload) {
    _hoyLog(`📤 Re-ejecutando agente ${key} para obtener payload...`);
    try {
      const r0 = await fetch('/api/marketing/agentes/' + key, _fetchOpts('POST'));
      payload = await r0.json();
      window._hoyUltimoOutput[key] = payload;
    } catch(e) {
      _hoyLog(`❌ Error re-ejecutando: ${e.message}`);
      return;
    }
  }

  _hoyLog(`📤 Aplicando workflow ${key}...`);
  try {
    const r = await fetch('/api/marketing/workflow/aplicar-agente', _fetchOpts('POST', {agente: key, payload: payload}));
    const d = await r.json();
    if(!r.ok) {
      _hoyLog(`❌ Workflow ${key} falló: ${d.error || r.status}`);
      alert('Error: ' + (d.error || r.status));
      return;
    }
    _hoyLog(`✅ ${d.mensaje}`);
    alert('✅ ' + d.mensaje);
    hoyCargarResumen(); // refresh KPIs
  } catch(e) {
    _hoyLog(`❌ Error de red: ${e.message}`);
  }
}

async function hoyRefreshMetricas() {
  if(!confirm('Refrescar métricas (followers, engagement, rank) de TODOS los influencers desde Socialblade?\\n\\nTomará ~5s por influencer (rate limit ético). Corre en background.')) return;
  const result = document.getElementById('hoy-metrics-result');
  result.textContent = '⏳ Iniciando refresh...';
  try {
    const r = await fetch('/api/marketing/refresh-all-metrics', _fetchOpts('POST'));
    const d = await r.json();
    if(!r.ok) {
      result.innerHTML = '<span style="color:#dc2626">❌ Error: ' + _escHtml(d.error || r.status) + '</span>';
      return;
    }
    result.innerHTML = `<span style="color:#16a34a">✓ ${d.mensaje}</span>`;
    _hoyLog(`📡 Refresh metrics iniciado: ${d.procesados_en_background} influencers`);
  } catch(e) {
    result.innerHTML = '<span style="color:#dc2626">❌ ' + e.message + '</span>';
  }
}

// ─── Vista persistente de Estrategia ──────────────────────────────────
async function loadUltimaEstrategia() {
  // Buscar la ejecución más reciente del agente 'Estrategia' en el log
  try {
    const rows = await fetch('/api/marketing/agentes/log').then(r=>r.json());
    const latest = (rows||[]).find(r => (r.agente||'').toLowerCase() === 'estrategia');
    if (!latest) return; // no hay corrida previa — vista invitando se mantiene
    const det = await fetch('/api/marketing/agentes/log/' + latest.id).then(r=>r.json());
    const view = document.getElementById('estrategia-vista');
    if (!view) return;
    let resultado = det.resultado;
    if (typeof resultado === 'string') {
      try { resultado = JSON.parse(resultado); } catch (e) { /* keep as string */ }
    }
    // Header con timestamp + botón regenerar
    const fecha = (det.fecha || latest.fecha || '').slice(0, 16).replace('T',' ');
    let html = `<div style="display:flex;justify-content:space-between;align-items:center;background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:10px;padding:12px 18px;margin-bottom:14px;">
      <div>
        <div style="font-size:14px;font-weight:700;color:#6d28d9;">&#x1F9E0; Última estrategia generada</div>
        <div style="font-size:11px;color:var(--cx-text-mute);margin-top:2px;">${fecha} · por ${det.ejecutado_por||'sistema'}</div>
      </div>
      <button onclick="runAgent('estrategia')" style="background:linear-gradient(135deg,#7c3aed,#4c1d95);color:#fff;border:none;padding:8px 16px;font-size:12px;font-weight:700;border-radius:8px;cursor:pointer;">&#x21BB; Regenerar</button>
    </div>`;
    if (typeof resultado === 'object' && resultado) {
      html += formatAgentResult('estrategia', resultado);
      if (latest.id) html += renderFeedbackBar(latest.id);
    } else {
      html += '<div style="color:var(--cx-text-mute);padding:14px;">Sin contenido detallado.</div>';
    }
    view.innerHTML = html;
  } catch(e) {
    console.warn('[loadUltimaEstrategia]', e);
  }
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
      showToast('✅ Token guardado — sincronizando...', 'success');
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

async function loadDashboard() {
  loadConnections();
  loadMetaProgreso();  // AUDIT 26-may · widget meta del mes
  loadSentimentDashboard();  // AUDIT 27-may · widget sentiment IG
  let _dashResp;
  try { _dashResp = await fetch('/api/marketing/dashboard'); }
  catch(e) { showToast('Error red dashboard: '+e.message,'error'); return; }
  if(!_dashResp.ok){
    if(_dashResp.status===401){ location.reload(); return; }
    showToast('Dashboard HTTP '+_dashResp.status,'error');
    // Mostrar guardas en KPIs para no engañar al user
    ['sh-rev30','sh-ped30','sh-ticket','sh-nuevos','sh-rev-total','ghl-total',
     'ig-posts30','ig-likes30','ig-comments30'].forEach(id=>{
      const el=document.getElementById(id); if(el){ el.textContent='?'; el.title='Error '+_dashResp.status; }
    });
    return;
  }
  const data = await _dashResp.json().catch(()=>null);
  if(!data){ showToast('Dashboard: respuesta inválida','error'); return; }
  const k = data.kpis || {};
  const sh = data.shopify || {};
  const ghl = data.ghl || {};

  document.getElementById('dash-fecha').textContent = 'Actualizado: '+new Date().toLocaleString('es-CO');

  // ── Shopify KPIs ──────────────────────────────────────────────────────────
  const fmt2 = v => v==null?'—':String(v);
  const fmtCOP = v => v==null?'—':'$'+Number(v).toLocaleString('es-CO');
  // Cobertura real de datos Shopify
  var shBanner = document.getElementById('sh-cobertura-banner');
  if(sh.datos_desde){
    var dias = sh.cobertura_dias || 0;
    var lRev = dias < 25 ? 'Revenue ('+dias+'d)' : 'Revenue 30d';
    var lPed = dias < 25 ? 'Pedidos ('+dias+'d)' : 'Pedidos 30d';
    if(document.getElementById('sh-rev30-label')) document.getElementById('sh-rev30-label').textContent = lRev;
    if(document.getElementById('sh-ped30-label')) document.getElementById('sh-ped30-label').textContent = lPed;
    if(sh.cobertura_parcial && shBanner){
      shBanner.style.display='block';
      shBanner.innerHTML = '⚠️ Datos Shopify disponibles desde <strong>'+esc(sh.datos_desde||'')+'</strong> ('+esc(String(dias))+' días). '+'Usa <strong>Sync histórico</strong> para traer el historial completo.';
    } else if(shBanner){ shBanner.style.display='none'; }
  }
  document.getElementById('sh-rev30').textContent    = fmtCOP(sh.revenue_30d);
  document.getElementById('sh-rev7').textContent     = 'Últimos 7d: '+fmtCOP(sh.revenue_7d);
  document.getElementById('sh-ped30').textContent    = fmt2(sh.pedidos_30d);
  document.getElementById('sh-ped-total').textContent= 'Total: '+fmt2(sh.pedidos_total);
  document.getElementById('sh-ticket').textContent   = fmtCOP(sh.ticket_promedio);
  document.getElementById('sh-clientes').textContent = 'Clientes: '+fmt2(sh.clientes_total);
  document.getElementById('sh-nuevos').textContent   = fmt2(sh.clientes_nuevos_30d);
  document.getElementById('sh-recurrentes').textContent = 'Recurrentes: '+fmt2(sh.clientes_recurrentes_30d);
  document.getElementById('sh-rev-total').textContent = fmtCOP(sh.revenue_total);
  document.getElementById('ghl-total').textContent   = fmt2(ghl.contactos_total);
  document.getElementById('ghl-nuevos').textContent  = 'Nuevos 30d: '+fmt2(ghl.contactos_nuevos_30d);

  // ── Gráfica ventas mensuales (SVG bar chart) ──────────────────────────────
  const mensual = sh.mensual || [];
  const chartEl = document.getElementById('dash-chart');
  if (!mensual.length) {
    chartEl.innerHTML = '<div style="color:var(--cx-text-mute);text-align:center;padding:32px;">Sin datos de ventas</div>';
  } else {
    const W=560, H=140, PAD_L=52, PAD_B=32, PAD_T=10, PAD_R=10;
    const plotW = W-PAD_L-PAD_R;
    const plotH = H-PAD_T-PAD_B;
    const maxV = Math.max(...mensual.map(m=>m.total||0), 1);
    const barW = Math.max(6, Math.floor(plotW/mensual.length)-4);
    const scale = v => plotH - Math.round((v/maxV)*plotH);
    const fmtK = v => v>=1000000 ? (v/1000000).toFixed(1)+'M' : v>=1000 ? Math.round(v/1000)+'k' : String(v);
    const bars = mensual.map((m,i)=>{
      const x = PAD_L + Math.round(i*(plotW/mensual.length)) + Math.round((plotW/mensual.length-barW)/2);
      const y = PAD_T + scale(m.total||0);
      const bH = plotH - scale(m.total||0);
      const label = (m.mes||'').slice(5,7)+'/'+((m.mes||'').slice(2,4));
      return `<rect x="${x}" y="${y}" width="${barW}" height="${Math.max(2,bH)}" fill="#d4af37" rx="2" opacity="0.85"/>
<text x="${x+barW/2}" y="${PAD_T+plotH+16}" text-anchor="middle" font-size="9" fill="#94a3b8">${label}</text>`;
    }).join('\n');
    // Y axis labels
    const yLabels = [0,0.25,0.5,0.75,1].map(pct=>{
      const val = Math.round(maxV*pct);
      const y = PAD_T + plotH - Math.round(pct*plotH);
      return `<line x1="${PAD_L-4}" y1="${y}" x2="${PAD_L+plotW}" y2="${y}" stroke="#1e293b" stroke-width="1"/>
<text x="${PAD_L-6}" y="${y+3}" text-anchor="end" font-size="9" fill="#64748b">${fmtK(val)}</text>`;
    }).join('\n');
    chartEl.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:${W}px;display:block;">
${yLabels}
${bars}
</svg>`;
  }

  // ── Top SKUs ──────────────────────────────────────────────────────────────
  const skuEl = document.getElementById('dash-top-skus');
  const topSkus = sh.top_skus || [];
  if (!topSkus.length) {
    skuEl.innerHTML = '<div style="color:var(--cx-text-mute);text-align:center;padding:32px;">Sin datos de SKUs</div>';
  } else {
    const maxSku = topSkus[0].total || 1;
    skuEl.innerHTML = topSkus.map((s,i)=>`
      <div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--cx-hairline);">
        <span style="color:#d4af37;font-weight:700;min-width:18px;">#${i+1}</span>
        <span style="flex:1;font-weight:600;font-size:12px;">${esc(s.sku||'—')}</span>
        <div style="flex:2;">
          <div style="background:var(--cx-card);border-radius:3px;height:6px;">
            <div style="background:#d4af37;height:6px;border-radius:3px;width:${Math.round((s.total/maxSku)*100)}%;"></div>
          </div>
        </div>
        <span style="color:#16a34a;font-size:11px;min-width:72px;text-align:right;">${fmtCOP(s.total)}</span>
        <span style="color:var(--cx-text-mute);font-size:11px;min-width:36px;text-align:right;">${fmt2(s.uds)} uds</span>
      </div>`).join('');
  }

  // ── Ciudades ──────────────────────────────────────────────────────────────
  const ciudEl = document.getElementById('dash-ciudades');
  const ciudades = sh.ciudades || [];
  if (!ciudades.length) {
    ciudEl.innerHTML = '<div style="color:var(--cx-text-mute);text-align:center;padding:32px;">Sin datos de ciudades</div>';
  } else {
    const maxCiud = ciudades[0].pedidos || 1;
    ciudEl.innerHTML = ciudades.map((c,i)=>`
      <div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--cx-hairline);">
        <span style="color:var(--cx-text-mute);min-width:18px;font-size:11px;">${i+1}</span>
        <span style="flex:1;font-size:12px;">${esc(c.ciudad||'—')}</span>
        <div style="flex:2;">
          <div style="background:var(--cx-card);border-radius:3px;height:6px;">
            <div style="background:#6366f1;height:6px;border-radius:3px;width:${Math.round((c.pedidos/maxCiud)*100)}%;"></div>
          </div>
        </div>
        <span style="color:var(--cx-text-mute);font-size:11px;min-width:54px;text-align:right;">${fmt2(c.pedidos)} pedidos</span>
      </div>`).join('');
  }

  // ── Campañas activas ──────────────────────────────────────────────────────
  const cBody = document.getElementById('dash-campanas');
  if (!data.campanas_activas || !data.campanas_activas.length) {
    cBody.innerHTML = '<tr class="empty-row"><td colspan="5">Sin campañas</td></tr>';
  } else {
    cBody.innerHTML = data.campanas_activas.map(c=>`
      <tr>
        <td style="font-weight:700;">${esc(c.nombre)}</td>
        <td><span class="badge badge-gray">${esc(c.canal||'—')}</span></td>
        <td>${badgeEstadoCamp(c.estado)}</td>
        <td>${fmtM(c.presupuesto)}</td>
        <td style="color:#16a34a;">${fmtM(c.resultado_ventas)}</td>
      </tr>`).join('');
  }

  // ── Contenido reciente ────────────────────────────────────────────────────
  const coBody = document.getElementById('dash-contenido');
  if (!data.contenido_reciente || !data.contenido_reciente.length) {
    coBody.innerHTML = '<tr class="empty-row"><td colspan="4">Sin contenido</td></tr>';
  } else {
    coBody.innerHTML = data.contenido_reciente.map(c=>`
      <tr><td>${esc(c.tipo)}</td><td>${esc(c.plataforma)}</td><td>${badgeEstadoCont(c.estado)}</td><td>${fmt(c.alcance)}</td></tr>`).join('');
  }

  // ── Instagram KPIs ───────────────────────────────────────────────────────
  const ig = data.instagram || {};
  document.getElementById('ig-posts30').textContent    = fmt2(ig.posts_30d);
  document.getElementById('ig-posts-total').textContent = 'Total: '+fmt2(ig.total_posts);
  document.getElementById('ig-likes30').textContent    = fmt2(ig.likes_30d);
  document.getElementById('ig-avg-likes').textContent  = 'Promedio: '+fmt2(ig.avg_likes)+' ♥/post';
  document.getElementById('ig-comments30').textContent = fmt2(ig.comentarios_30d);

  // ── Instagram Top Posts ───────────────────────────────────────────────────
  const igEl = document.getElementById('dash-ig-posts');
  const topPosts = ig.top_posts || [];
  // ── Token status badge ───────────────────────────────────────────────────
  const igStatusEl = document.getElementById('ig-token-status');
  if (igStatusEl && ig.configurado) {
    const daysLeft = ig.token_days_left || 0;
    const expired  = ig.token_expired;
    const refreshed = ig.token_refreshed;
    const nearExp  = ig.token_near_expiry;
    if (expired) {
      igStatusEl.style.display = '';
      igStatusEl.style.background = '#7f1d1d';
      igStatusEl.style.color = '#fca5a5';
      igStatusEl.textContent = '⚠️ Token expirado — renovar manualmente';
    } else if (refreshed) {
      igStatusEl.style.display = '';
      igStatusEl.style.background = '#14532d';
      igStatusEl.style.color = '#86efac';
      igStatusEl.textContent = '🔄 Token renovado automáticamente (' + daysLeft + 'd)';
    } else if (nearExp) {
      igStatusEl.style.display = '';
      igStatusEl.style.background = '#78350f';
      igStatusEl.style.color = '#fde68a';
      igStatusEl.textContent = '⚠️ Token vence en ' + daysLeft + ' días';
    } else if (daysLeft > 0) {
      igStatusEl.style.display = '';
      igStatusEl.style.background = '#0f2d1a';
      igStatusEl.style.color = '#4ade80';
      igStatusEl.textContent = '🔑 Token válido — ' + daysLeft + 'd restantes';
    } else {
      igStatusEl.style.display = 'none';
    }
    // Si se auto-renovó silenciosamente, notificar una vez
    if (refreshed && !window._igRefreshToastShown) {
      window._igRefreshToastShown = true;
      showToast('🔄 Token de Instagram renovado automáticamente por 60 días', 'success');
    }
  }

  if (!ig.configurado) {
    igEl.innerHTML = '<div style="color:var(--cx-text-mute);text-align:center;padding:20px;">⚠️ Instagram no configurado — agrega INSTAGRAM_TOKEN en Render</div>';
  } else if (!topPosts.length) {
    igEl.innerHTML = '<div style="color:var(--cx-text-mute);text-align:center;padding:20px;">Sin posts — haz clic en ↻ IG para sincronizar</div>';
  } else {
    igEl.innerHTML = '<div style="display:flex;flex-wrap:wrap;gap:12px;">' +
      topPosts.map(p => {
        const eng = (p.likes||0) + (p.comentarios||0)*3;
        const desc = (p.descripcion||'').slice(0,80) + ((p.descripcion||'').length>80?'…':'');
        const date = (p.publicado_en||'').slice(0,10);
        const tipo = p.tipo||'IMAGE';
        const icon = tipo==='VIDEO'?'🎬':tipo==='CAROUSEL_ALBUM'?'🗂️':'📸';
        return `<div style="flex:1;min-width:200px;max-width:260px;background:var(--cx-bg-alt);border:1px solid var(--cx-hairline);border-radius:8px;padding:12px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
            <span style="font-size:11px;color:var(--cx-text-mute);">${icon} ${tipo}</span>
            <span style="font-size:10px;color:var(--cx-text-mute);">${date}</span>
          </div>
          <div style="font-size:11px;color:var(--cx-text-soft);margin-bottom:8px;line-height:1.4;">${esc(desc||'(sin caption)')}</div>
          <div style="display:flex;gap:12px;font-size:11px;">
            <span style="color:#e1306c;">♥ ${p.likes||0}</span>
            <span style="color:var(--cx-text-mute);">💬 ${p.comentarios||0}</span>
            <span style="color:#d4af37;margin-left:auto;">eng ${eng}</span>
          </div>
          ${p.url_permalink?`<a href="${escUrl(p.url_permalink)}" target="_blank" rel="noopener noreferrer" style="display:block;margin-top:6px;font-size:10px;color:#6366f1;">Ver en IG →</a>`:''}
        </div>`;
      }).join('') +
    '</div>';
  }

  // ── Por canal ─────────────────────────────────────────────────────────────
  const chEl = document.getElementById('dash-canales');
  if (!data.por_canal || !data.por_canal.length) {
    chEl.innerHTML = '<div style="color:var(--cx-text-mute);text-align:center;padding:20px;">Sin datos de campañas por canal</div>';
  } else {
    chEl.innerHTML = data.por_canal.map(ch=>`
      <div style="padding:10px 0;border-bottom:1px solid var(--cx-hairline);">
        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
          <span style="font-weight:700;">${esc(ch.canal)}</span>
          <span style="color:#16a34a;">${fmtM(ch.ventas_total)} ventas</span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--cx-text-mute);">
          <span>${ch.campanas} campaña${ch.campanas!=1?'s':''} · ${fmtM(ch.presupuesto_total)} invertido</span>
        </div>
      </div>`).join('');
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
      body.innerHTML='<tr class="empty-row"><td colspan="11" style="color:#dc2626">Error '+r.status+' cargando campañas</td></tr>';
      return;
    }
    rows = await r.json();
  } catch(e){
    body.innerHTML='<tr class="empty-row"><td colspan="11" style="color:#dc2626">Error red: '+esc(e.message)+'</td></tr>';
    return;
  }
  if(!Array.isArray(rows)){
    body.innerHTML='<tr class="empty-row"><td colspan="11" style="color:#dc2626">Respuesta inválida: '+esc(JSON.stringify(rows).slice(0,200))+'</td></tr>';
    return;
  }
  if(!rows.length) { body.innerHTML='<tr class="empty-row"><td colspan="11">Sin campañas. Crea la primera.</td></tr>'; return; }
  // AUDIT 26-may · cache campañas para que generarCuponCampana lea discount_code actual
  CAMPANAS_LIST = rows;
  body.innerHTML = rows.map(r=>{
    const roi = r.presupuesto_gastado>0 ? ((r.resultado_ventas-r.presupuesto_gastado)/r.presupuesto_gastado*100).toFixed(1) : null;
    // Sebastián 25-may-2026 PM · audit P0 · XSS · escape de campos del backend
    const cuponChip = r.discount_code
      ? `<div style="margin-top:3px;font-size:10px"><span style="background:var(--cx-primary-soft);color:#6d28d9;padding:1px 6px;border-radius:6px;font-family:monospace;font-weight:700" title="Atribución activa">${esc(r.discount_code)}</span></div>`
      : '';
    return `<tr>
      <td class="mob-hide" style="color:var(--cx-text-mute);">${esc(r.id)}</td>
      <td style="font-weight:700;">${esc(r.nombre)}${cuponChip}</td>
      <td class="mob-hide"><span class="badge badge-gray">${esc(r.tipo)}</span></td>
      <td class="mob-hide">${esc(r.canal||'—')}</td>
      <td>${badgeEstadoCamp(r.estado)}</td>
      <td class="mob-hide">${fmtM(r.presupuesto)}</td>
      <td class="mob-hide">${fmtM(r.presupuesto_gastado)}</td>
      <td style="color:#16a34a;">${fmtM(r.resultado_ventas)}</td>
      <td>${roiBadge(roi)}</td>
      <td class="mob-hide"><span class="badge badge-purple">${esc(r.num_influencers)}</span></td>
      <td>
        <button class="btn btn-outline btn-sm" onclick="editCampana(${r.id})" title="Editar">✏️</button>
        <button class="btn btn-outline btn-sm" onclick="generarCuponCampana(${r.id})" title="${r.discount_code?'Regenerar':'Generar'} cupón Shopify" style="border-color:#6d28d9;color:#6d28d9">🎟️</button>
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
// ─── PAGOS REALIZADOS — vista cronológica para Marketing ───────────────────
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
      body.innerHTML = '<tr class="empty-row"><td colspan="8" style="color:#dc2626;">Error: ' + _escHtml(d.error||'desconocido') + '</td></tr>';
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
      {label:'ROI global',             val: (k.roi_global_pct==null?'—':k.roi_global_pct+'%'),
        color: k.roi_global_pct==null ? '#64748b' : (k.roi_global_pct >= 100 ? '#34d399' : (k.roi_global_pct >= 0 ? '#fbbf24' : '#ef4444'))},
    ].map(c=>`<div style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:8px;padding:10px 12px;">
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
      const roiTxt = (roi==null) ? '—' : roi + '%';
      return `<tr>
        <td style="font-weight:600;">${x.nombre||'—'}${x.usuario_red?'<div style="font-size:10px;color:var(--cx-text-mute);font-weight:400;">@'+x.usuario_red+'</div>':''}</td>
        <td><code style="background:var(--cx-bg-alt);color:#16a34a;padding:2px 8px;border-radius:4px;font-size:11px;">${x.discount_code}</code></td>
        <td style="text-align:right;">${x.n_pedidos||0}</td>
        <td style="text-align:right;color:var(--cx-text-mute);">${x.unidades||0}</td>
        <td style="text-align:right;font-weight:700;color:#16a34a;">${fmtM(x.revenue_total||0)}</td>
        <td style="text-align:right;color:var(--cx-text-mute);">${fmtM(x.invertido||0)}</td>
        <td style="text-align:right;font-weight:700;color:${roiCol};">${roiTxt}</td>
        <td style="font-size:11px;color:var(--cx-text-mute);">${(x.ultimo_pedido||'').slice(0,10)||'—'}</td>
      </tr>`;
    }).join('');
  } catch (e) {
    body.innerHTML = '<tr class="empty-row"><td colspan="8" style="color:#dc2626;">Error de red: ' + e.message + '</td></tr>';
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
      ? '<span style="background:var(--cx-success-pale);color:#16a34a;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;">&#x2713; Pagada</span>'
      : '<span style="background:#78350f;color:#b45309;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;">&#x23F3; Pendiente</span>';
    let comprobante = '<span style="color:var(--cx-text-faint);font-size:11px;">—</span>';
    if (p.comprobante_id && p.numero_ce) {
      comprobante = '<a href="/api/comprobantes-pago/'+p.comprobante_id+'/pdf" target="_blank" '
        + 'style="color:#1F5F5B;font-weight:700;text-decoration:none;display:inline-flex;align-items:center;gap:4px;background:#f0fdfa;padding:3px 10px;border-radius:6px;font-size:12px;">'
        + '&#x1F4C4; '+p.numero_ce+'</a>';
    } else if (p.estado === 'Pagada') {
      comprobante = '<span style="color:#dc2626;font-size:11px;font-style:italic;" title="Pago hecho antes del feature de comprobantes">sin CE</span>';
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
      : '—';
    return '<tr>'
      + '<td style="font-size:12px;color:var(--cx-text-soft);">'+fecha+'</td>'
      + '<td style="font-weight:700;">'+(p.influencer_nombre||'—')
        + (p.inf_email ? '<div style="font-size:11px;color:var(--cx-text-mute);font-weight:400;">'+p.inf_email+'</div>' : '')
      + '</td>'
      + '<td style="font-size:12px;color:var(--cx-text-mute);">'+(p.concepto||'—')+'</td>'
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
    ? '<div style="background:#fffbeb;border:1px solid #fde68a;border-left:4px solid #f59e0b;border-radius:10px;padding:11px 16px;margin-bottom:14px;font-size:13px;color:#92400e;font-weight:600">⚠ '+_nSinMail+' creador'+(_nSinMail>1?'es':'')+' con pagos y <b>sin correo</b> · no recibirán la factura de pagado. Agregales el correo en <b>Creadores</b>.</div>'
    : '';
  if(!list.length){ lst.innerHTML=_alertMail+'<div style="text-align:center;color:var(--cx-text-mute);padding:30px;">Sin pagos en este estado.</div>'; return; }
  lst.innerHTML=_alertMail+list.slice(0,300).map(function(p){
    var e=_pagoEstadoCat(p); var s=ST[e];
    var ent=(p.entregable||'').trim();
    var hi=ent.indexOf('http'); var link=''; if(hi>=0){ link=ent.slice(hi).split(' ')[0].split('·')[0].trim(); }
    var okLink=(link.indexOf('http://')===0||link.indexOf('https://')===0);
    var entTxt=(hi>=0?ent.slice(0,hi):ent).trim(); if(entTxt.charAt(entTxt.length-1)==='·') entTxt=entTxt.slice(0,-1).trim();
    var noEmail=!(p.inf_email||'').trim();
    return '<div style="background:var(--cx-card,#fff);border:1px solid #eef0f2;border-left:4px solid '+s.color+';border-radius:12px;padding:12px 16px;margin-bottom:10px;box-shadow:0 1px 4px rgba(15,23,42,.05);display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">'
      +'<div style="min-width:200px;flex:1">'
        +'<div style="font-weight:800;color:var(--cx-text)">'+_escHtml(p.influencer_nombre||'—')+(noEmail?' <span title="sin correo · no recibirá la factura de pagado" style="color:#dc2626;font-size:11px;font-weight:700">⚠ sin correo</span>':'')+'</div>'
        +'<div style="font-size:11px;color:var(--cx-text-mute);margin-top:2px">📅 Solicitud: '+((p.fecha||'').slice(0,10))+(p.fecha_publicacion?' · 📢 Publicó: '+p.fecha_publicacion.slice(0,10):'')+(entTxt?' · 📝 '+_escHtml(entTxt):'')+(okLink?' · <a href="'+_escHtml(link)+'" target="_blank" rel="noopener" style="color:#7c3aed;font-weight:700;text-decoration:none">🔗 post</a>':'')+'</div>'
      +'</div>'
      +'<div style="text-align:right;white-space:nowrap">'
        +'<div style="font-size:16px;font-weight:800;color:'+s.color+'">'+fmtM(p.valor||0)+'</div>'
        +'<span style="display:inline-block;margin-top:3px;background:'+s.bg+';color:'+s.fg+';padding:3px 11px;border-radius:999px;font-size:11px;font-weight:700">'+s.emoji+' '+s.one+'</span>'
        +(p.numero_ce?' <div style="font-size:10px;color:#059669;font-family:monospace;margin-top:2px">'+_escHtml(p.numero_ce)+'</div>':'')
      +'</div>'
    +'</div>';
  }).join('');
}

// Cache global de influencers — verHistorial lookup. Antes se serializaba la
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
// (string interpolation con nombre/banco escapaba solo comillas — backslash o
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
      banner.innerHTML = '<b style="color:#b45309;">⏳ ' + conPendiente.length + ' solicitud'
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
      + (vencidos > 0 ? '<span style="background:#dc2626;color:#fff;padding:4px 10px;border-radius:20px;font-weight:700;">🔴 '+vencidos+' atrasado'+(vencidos>1?'s':'')+'</span>' : '')
      + (urgentes > 0 ? '<span style="background:#d97706;color:#fff;padding:4px 10px;border-radius:20px;font-weight:700;">🟡 '+urgentes+' esta semana</span>' : '')
      + (proximos > 0 ? '<span style="background:#475569;color:#fff;padding:4px 10px;border-radius:20px;">🟢 '+proximos+' próx 15d</span>' : '')
      + '</div></div>'
      + (vencidos > 0 ? '<div style="font-size:11px;margin-top:8px;opacity:.85;">Promesa de pago: 30 días desde fecha del contenido. Total atrasado: <b>$'+total+'</b></div>' : '');
  } catch (_) {
    banner.style.display = 'none';
  }
}

// Render de la tabla principal — separado para poder llamar al cambiar filtros
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
        <span><span style="color:#16a34a;font-weight:700;">${idx+1}.</span> ${esc(i.nombre||'(s/n)')}</span>
        <span style="color:#16a34a;font-weight:800;">${er}%</span></div>`;
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
        <span style="color:#f59e0b;font-weight:800;">${i.dias_desde_ultimo_pago||0}d</span></div>`
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
        estadoBadge = '<span style="background:#7f1d1d;color:#dc2626;padding:3px 8px;border-radius:50%;font-size:13px;font-weight:700;display:inline-block;width:24px;height:24px;line-height:18px;text-align:center;white-space:nowrap;border:1.5px solid #dc2626;" title="ATRASADO \u00b7 pago vencido hace '+Math.abs(u.dias||0)+' d. Venc\u00eda '+esc(u.vence||'')+'">\ud83d\udd34</span>';
      } else if (u && u.urgencia === 'urgente') {
        estadoBadge = '<span style="background:#854d0e;color:#fde047;padding:3px 8px;border-radius:50%;font-size:13px;font-weight:700;display:inline-block;width:24px;height:24px;line-height:18px;text-align:center;white-space:nowrap;border:1.5px solid #f59e0b;" title="Urgente \u00b7 vence en '+(u.dias||0)+' d ('+esc(u.vence||'')+')">\ud83d\udfe1</span>';
      } else {
        estadoBadge = '<span style="background:#78350f;color:#b45309;padding:3px 8px;border-radius:50%;font-size:13px;font-weight:700;display:inline-block;width:24px;height:24px;line-height:18px;text-align:center;white-space:nowrap;" title="Esperando pago \u2014 solicitud creada, Sebasti\u00e1n por autorizar">\u23f3</span>';
      }
    } else if(r.toca_pagar) {
      const dias = r.dias_desde_ultimo_pago || 0;
      estadoBadge = '<span style="background:#854d0e;color:#fde047;padding:3px 8px;border-radius:50%;font-size:13px;font-weight:700;display:inline-block;width:24px;height:24px;line-height:18px;text-align:center;white-space:nowrap;" title="Toca solicitar \u2014 hace '+dias+' d\u00edas del \u00faltimo pago (ciclo '+r.ciclo_pago+'). Click \ud83d\udcb8 Solicitar pago para crear cuenta de cobro">\ud83d\udccc</span>';
    } else if(r.pagos_count>0) {
      estadoBadge = '<span style="background:var(--cx-success-pale);color:#16a34a;padding:3px 8px;border-radius:50%;font-size:13px;font-weight:700;display:inline-block;width:24px;height:24px;line-height:18px;text-align:center;white-space:nowrap;" title="Al d\u00eda \u2014 '+(r.pagos_count||0)+' pago(s) confirmado(s)">\u2713</span>';
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
    let pagosBadge = '<button onclick="abrirGestionarPagos('+r.id+', '+esc(JSON.stringify(r.nombre||''))+')" style="background:var(--cx-card);border:1px dashed #475569;color:var(--cx-text-mute);font-size:10px;padding:3px 8px;border-radius:6px;cursor:pointer" title="Sin pagos \u00b7 click para registrar/gestionar">+ Gestionar</button>';
    if(pagosInf.length > 0){
      pagosBadge = '<button onclick="abrirGestionarPagos('+r.id+', '+esc(JSON.stringify(r.nombre||''))+')" style="background:transparent;border:0;padding:0;cursor:pointer;display:inline-flex;gap:4px;align-items:center;font-size:11px" title="Click para gestionar \u00b7 marcar pagado/pendiente, editar o eliminar">';
      if(pendCount>0) pagosBadge += `<span style="background:#78350f;color:#b45309;padding:2px 8px;border-radius:8px;font-weight:700">\u23f3 ${pendCount}</span>`;
      if(paidCount>0) pagosBadge += `<span style="background:var(--cx-success-pale);color:#16a34a;padding:2px 8px;border-radius:8px;font-weight:700">\u2713 ${paidCount}</span>`;
      pagosBadge += '<span style="color:#6d28d9;font-size:13px;margin-left:2px">\u2699</span></button>';
    }
    // AUDIT 26-may \u00b7 cup\u00f3n + atribuci\u00f3n real Shopify
    let cuponBadge = '';
    if(r.discount_code){
      const revAtr = r.revenue_atribuible||0;
      const roi = r.roi_implicito_pct;
      const roiCol = roi==null?'#94a3b8':(roi>=200?'#10b981':roi>=50?'#22c55e':roi>=0?'#f59e0b':'#ef4444');
      const roiTxt = roi==null?'sin pago a\u00fan':roi+'% ROI';
      cuponBadge = `<div style="font-size:10px;margin-top:3px"><span style="background:var(--cx-primary-soft);color:#6d28d9;padding:1px 6px;border-radius:6px;font-family:monospace;font-weight:700" title="C\u00f3digo activo: ${esc(r.discount_code)}">${esc(r.discount_code)}</span>`;
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
          +` <button class="btn btn-outline btn-sm" onclick="generarCuponInf(${r.id})" title="${r.discount_code?'Regenerar':'Generar'} cup\u00f3n Shopify para atribuci\u00f3n de ventas" style="border-color:#6d28d9;color:#6d28d9">&#x1F39F;&#xFE0F;</button> `
          +`<button class="btn btn-outline btn-sm" onclick="abrirOutreachModal(${r.id})" title="Generar mensajes WhatsApp/Email/IG para contactar al influencer" style="border-color:#16a34a;color:#16a34a">&#x1F4E8;</button> `
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
          const pdfBtn = p.has_pdf ? `<a href="/api/marketing/pagos-influencers/${p.id}/pdf" target="_blank" style="color:#16a34a;text-decoration:none;font-size:11px;">\u{1F4C4} PDF</a>` : '<span style="color:var(--cx-text-faint);font-size:11px;">\u2014</span>';
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

// Sebastian (29-abr-2026): "jeferson dice que hay creadores dobles, pero no
// le deja eliminarlos entonces pon una opcion de eliminar".
// AUDIT 26-may PM · outreach automation · mensajes pre-armados WhatsApp/Email/IG
async function abrirOutreachModal(id){
  const p = _INF_ROW_PAYLOAD[id];
  const nombre = p ? p.nombre : 'influencer #'+id;
  // Prompt para SKU (opcional · el más rápido)
  const sku = (prompt('SKU para promocionar (opcional · dejá vacío para mensaje genérico)\n\nEj: GLOSSMOCCA, ECEN, SAH', '')||'').trim().toUpperCase();
  // Modal placeholder
  let modalEl = document.getElementById('modal-outreach');
  if(!modalEl){
    modalEl = document.createElement('div');
    modalEl.id = 'modal-outreach';
    modalEl.className = 'modal';
    document.body.appendChild(modalEl);
  }
  modalEl.innerHTML = `<div class="modal-content" style="max-width:680px;max-height:85vh;overflow-y:auto">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <div class="modal-title">📨 Outreach a ${esc(nombre)}${sku?(' · '+esc(sku)):''}</div>
      <button class="btn btn-outline btn-sm" onclick="closeModal('modal-outreach')">✕</button>
    </div>
    <div style="color:var(--cx-text-mute);padding:30px;text-align:center">Generando mensajes con IA…</div>
  </div>`;
  modalEl.classList.add('open');
  const params = new URLSearchParams({influencer_id: id});
  if(sku) params.set('sku', sku);
  try {
    const r = await fetch('/api/marketing/outreach-mensaje?'+params.toString(), {credentials:'same-origin'});
    const d = await r.json();
    if(!r.ok){
      modalEl.querySelector('.modal-content').innerHTML += '<div style="color:#ef4444;padding:14px">Error: '+esc(d.error||r.status)+'</div>';
      return;
    }
    _renderOutreachModal(modalEl, d);
  } catch(e){
    modalEl.querySelector('.modal-content').innerHTML += '<div style="color:#ef4444;padding:14px">Error red: '+esc(e.message)+'</div>';
  }
}

function _renderOutreachModal(modalEl, d){
  const inf = d.influencer || {};
  const msj = d.mensajes || {};
  const dl = d.deeplinks || {};
  const warning = d.anti_spam_warning;
  const fuente = d.generado_con || 'plantilla';
  const fuenteBadge = fuente.includes('claude')
    ? '<span style="background:var(--cx-primary-soft);color:#6d28d9;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700">🤖 IA Claude</span>'
    : '<span style="background:#3f3f46;color:#a8a29e;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700">📋 Plantilla</span>';
  modalEl.innerHTML = `<div class="modal-content" style="max-width:680px;max-height:85vh;overflow-y:auto">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
      <div class="modal-title">📨 Outreach a ${esc(inf.nombre||'')}${d.sku?(' · '+esc(d.sku.sku||'')):''}</div>
      <button class="btn btn-outline btn-sm" onclick="closeModal('modal-outreach')">✕</button>
    </div>
    <div style="display:flex;gap:8px;font-size:11px;color:var(--cx-text-mute);margin-bottom:14px">
      ${fuenteBadge}
      ${inf.discount_code?'<span style="background:var(--cx-primary-soft);color:#6d28d9;padding:2px 8px;border-radius:6px;font-family:monospace;font-weight:700">'+esc(inf.discount_code)+'</span>':''}
      ${inf.ultima_colab_dias!=null?'<span title="Días desde última colab pagada">⏱ '+inf.ultima_colab_dias+'d sin colab</span>':''}
    </div>
    ${warning?'<div style="background:#7c2d12;color:#fdba74;padding:10px;border-radius:8px;font-size:11px;margin-bottom:14px">'+esc(warning)+'</div>':''}

    <h3 style="font-size:13px;color:#10b981;margin:14px 0 6px">💬 WhatsApp</h3>
    <textarea id="om-whatsapp" rows="3" style="width:100%;padding:10px;background:var(--cx-card);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px;font-family:inherit;font-size:13px;resize:vertical">${esc(msj.whatsapp||'')}</textarea>
    <div style="display:flex;gap:6px;margin-top:6px">
      <button class="btn btn-outline btn-sm" onclick="_copyToClipboard('om-whatsapp','wa')">📋 Copiar</button>
      ${dl.whatsapp_web?'<a class="btn btn-primary btn-sm" href="'+escUrl(dl.whatsapp_web)+'" target="_blank" rel="noopener noreferrer">📱 Abrir WhatsApp Web</a>':'<span style="color:var(--cx-text-mute);font-size:11px;padding:6px">Sin teléfono cargado</span>'}
      <span id="om-wa-status" style="font-size:11px;color:#10b981;padding:6px"></span>
    </div>

    <h3 style="font-size:13px;color:#2563eb;margin:18px 0 6px">📧 Email</h3>
    <input id="om-email-subject" value="${esc(msj.email_subject||'')}" style="width:100%;padding:8px 10px;background:var(--cx-card);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px;font-size:12px;margin-bottom:6px" placeholder="Asunto">
    <textarea id="om-email-body" rows="6" style="width:100%;padding:10px;background:var(--cx-card);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px;font-family:inherit;font-size:13px;resize:vertical">${esc(msj.email_body||'')}</textarea>
    <div style="display:flex;gap:6px;margin-top:6px">
      <button class="btn btn-outline btn-sm" onclick="_copyToClipboard('om-email-body','em')">📋 Copiar cuerpo</button>
      ${dl.mailto?'<a class="btn btn-primary btn-sm" href="'+escUrl(dl.mailto)+'">✉ Abrir email</a>':'<span style="color:var(--cx-text-mute);font-size:11px;padding:6px">Sin email cargado</span>'}
      <span id="om-em-status" style="font-size:11px;color:#10b981;padding:6px"></span>
    </div>

    <h3 style="font-size:13px;color:#e1306c;margin:18px 0 6px">📸 Instagram DM</h3>
    <textarea id="om-igdm" rows="3" style="width:100%;padding:10px;background:var(--cx-card);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px;font-family:inherit;font-size:13px;resize:vertical">${esc(msj.instagram_dm||'')}</textarea>
    <div style="display:flex;gap:6px;margin-top:6px">
      <button class="btn btn-outline btn-sm" onclick="_copyToClipboard('om-igdm','ig')">📋 Copiar</button>
      ${inf.usuario_red?'<a class="btn btn-primary btn-sm" href="'+escUrl('https://instagram.com/'+inf.usuario_red.replace(/^@/,''))+'" target="_blank" rel="noopener noreferrer">📸 Abrir perfil IG</a>':'<span style="color:var(--cx-text-mute);font-size:11px;padding:6px">Sin usuario_red</span>'}
      <span id="om-ig-status" style="font-size:11px;color:#10b981;padding:6px"></span>
    </div>

    <div style="margin-top:20px;padding-top:14px;border-top:1px solid #e7e5e4;font-size:11px;color:var(--cx-text-mute)">
      Cuando envíes, los mensajes quedan registrados en marketing_outreach_log para audit + anti-spam (warn si re-contactás en 14d).
    </div>
  </div>`;
}

function _copyToClipboard(elementId, statusKey){
  const el = document.getElementById(elementId);
  if(!el) return;
  el.select();
  navigator.clipboard.writeText(el.value).then(()=>{
    const st = document.getElementById('om-'+statusKey+'-status');
    if(st){ st.textContent = '✓ Copiado'; setTimeout(()=>{ st.textContent=''; }, 1500); }
  }).catch(()=>{
    document.execCommand('copy');
  });
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
      +'      <button class="btn btn-sm" style="background:#dc2626;color:#fff;" onclick="dedupMergeInfluencers()" title="Fusiona TODOS los duplicados por nombre · conserva el de más pagos · repunta los pagos al conservado (solo admin)">\u{1F9F9} Fusionar duplicados</button>'
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
      body.innerHTML = '<div style="padding:24px;text-align:center;color:#16a34a;">✅ No se detectaron duplicados.</div>';
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
        ? ('Nombre similar: <span style="color:#b45309">'+_escDup(grupo.nombre_normalizado||'?')+'</span>')
        : ('Mismos '+_escDup(grupo.tipo||'datos')+': <span style="color:#b45309">'+_escDup(grupo.valor||'?')+'</span>');
      let rows = items.map(it => {
        const conservar = (it.id === sug);
        const pagos = it.n_pagos || 0;
        return '<tr style="'+(conservar?'background:var(--cx-success-pale)':'')+'">'
          +'<td style="padding:6px 8px;">'+(conservar?'⭐ ':'')+_escDup(it.nombre||'')+(it.usuario_red?' <span style="color:var(--cx-text-mute)">@'+_escDup(it.usuario_red)+'</span>':'')+'</td>'
          +'<td style="padding:6px 8px;font-size:11px;color:var(--cx-text-mute);">'+_escDup(it.cedula_nit||'—')+' / '+_escDup(it.cuenta_bancaria||'—')+'</td>'
          +'<td style="padding:6px 8px;text-align:center;">'+pagos+'</td>'
          +'<td style="padding:6px 8px;text-align:right;white-space:nowrap;">'
            +(conservar
              ? '<span style="color:#16a34a;font-size:11px;">conservar</span>'
              : '<button class="btn btn-danger btn-sm" onclick="eliminarInfluencerDup('+it.id+',\''+_escDup((it.nombre||'').replace(/\x27/g,'’'))+'\')">\u{1F5D1}️ Eliminar</button>')
          +'</td>'
        +'</tr>';
      }).join('');
      return '<div style="margin-bottom:18px;border:1px solid #e7e5e4;border-radius:8px;overflow:hidden;">'
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
    body.innerHTML = '<div style="padding:20px;color:#dc2626;">Error: '+e.message+'</div>';
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
    html += '<td style="padding:8px;text-align:right;font-weight:700;color:#6d28d9;">$'+valor+'</td>';
    html += '<td style="padding:8px;font-size:11px;color:var(--cx-text-mute);">'+esc((p.concepto||'').substring(0,60))+'</td>';
    html += '<td style="padding:8px;font-family:monospace;font-size:11px;color:#67e8f9;">'+esc(p.numero_oc||'—')+'</td>';
    html += '<td style="padding:8px;text-align:center;white-space:nowrap;">';
    // Botón Pagada (si está Pendiente)
    if (estado === 'Pendiente'){
      html += '<button onclick="_gpCambiarEstado('+p.id+',&quot;Pagada&quot;)" title="Marcar como Pagada" style="background:var(--cx-success-pale);color:#fff;border:0;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px;margin-right:3px">✓</button>';
    }
    // Botón Pendiente (si está Pagada)
    if (estado === 'Pagada'){
      html += '<button onclick="_gpCambiarEstado('+p.id+',&quot;Pendiente&quot;)" title="Revertir a Pendiente" style="background:#78350f;color:#b45309;border:0;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px;margin-right:3px">↩</button>';
    }
    html += '<button onclick="_gpEditarValor('+p.id+','+(p.valor||0)+')" title="Editar valor/concepto" style="background:var(--cx-info-pale);color:#fff;border:0;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px;margin-right:3px">✏</button>';
    html += '<button onclick="_gpEliminar('+p.id+')" title="Eliminar este registro" style="background:#7f1d1d;color:#fecaca;border:0;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px">🗑</button>';
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
    prev.innerHTML = '<span style="color:#f59e0b;">\u26a0\ufe0f Sin datos bancarios. Edita el influencer primero.</span>';
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
      + '<div style="font-size:18px;font-weight:800;color:#16a34a;margin-top:6px">Solicitud creada y guardada</div>'
      + '<div id="mpo-numero" style="font-family:monospace;font-size:22px;font-weight:800;color:#6d28d9;background:var(--cx-primary-soft);border:1.5px solid #4338ca;border-radius:10px;padding:10px 16px;margin:12px auto;display:inline-block"></div>'
      + '<div style="font-size:13px;color:var(--cx-text-soft);line-height:1.6;text-align:left;background:var(--cx-bg-alt);border-radius:8px;padding:12px 14px;margin:10px 14px">'
      + '<div><b style="color:var(--cx-text-mute)">Influencer:</b> <span id="mpo-nombre"></span></div>'
      + '<div><b style="color:var(--cx-text-mute)">Monto:</b> <span id="mpo-monto" style="color:#b45309;font-weight:700"></span></div>'
      + '<div><b style="color:var(--cx-text-mute)">Concepto:</b> <span id="mpo-concepto"></span></div>'
      + '<div style="margin-top:8px;border-top:1px solid #e7e5e4;padding-top:8px;color:#6d28d9">'
      + '📌 Ya quedó visible para Sebastián en <b>/compras → tab Influencers</b>. '
      + 'Cuando pague vas a recibir notificación in-app. También aparece ahora en tu tabla con el badge ⏳.'
      + '</div></div>'
      + '<div style="display:flex;gap:10px;justify-content:center;margin:8px 14px 14px">'
      + '<button class="btn btn-primary" onclick="closeModal(\'modal-pago-ok\')" style="min-width:140px">OK, entendido</button>'
      + '</div></div></div>';
    document.body.appendChild(m);
  }
  document.getElementById('mpo-numero').textContent = d.numero || '(sin número)';
  document.getElementById('mpo-nombre').textContent = d.nombre || '—';
  document.getElementById('mpo-monto').textContent = '$' + (d.monto||0).toLocaleString('es-CO') + ' COP';
  document.getElementById('mpo-concepto').textContent = d.concepto || '—';
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
    const code = it.influencer_code ? ` · <code style="color:#16a34a;">${esc(it.influencer_code)}</code>` : '';
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
      ? `<span style="background:var(--cx-info-pale);color:#2563eb;padding:1px 6px;border-radius:6px;font-size:9px;font-weight:700;margin-right:6px" title="Métricas auto-sincronizadas desde Instagram Graph API${it.ig_synced_at?' · sync '+esc(it.ig_synced_at):''}">📡 IG LIVE</span>`
      : (it.url_publicacion && it.estado === 'Publicado'
          ? `<span style="background:#7c2d12;color:#fdba74;padding:1px 6px;border-radius:6px;font-size:9px;font-weight:700;margin-right:6px" title="Esta pieza tiene URL pero no hay match en posts IG sincronizados · refresca IG en Dashboard ↻">⚠ sin sync IG</span>`
          : '');
    if (stats.length || fuenteBadge) perf = `<div class="perf">${fuenteBadge}${stats.join(' · ')}</div>`;
  }

  let urlBtn = '';
  if (it.url_publicacion) {
    urlBtn = `<a href="${escUrl(it.url_publicacion)}" target="_blank" rel="noopener noreferrer" style="color:#2563eb;font-size:11px;text-decoration:none;margin-right:8px;" onclick="event.stopPropagation();">🔗 Ver post</a>`;
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
  if (idx >= 0 && idx < seq.length-1) html += `<button onclick="event.stopPropagation();moveContenido(${it.id},'${seq[idx+1]}')" title="→ ${seq[idx+1]}" style="background:none;border:none;color:#6d28d9;cursor:pointer;padding:2px 4px;font-size:13px;">→</button>`;
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
// HELPERS — SELECT POPULATES
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
        errMsg = '🔑 Token de Instagram expirado — genera uno nuevo en developers.facebook.com/tools/explorer y pégalo abajo';
        det = '';
      } else if(det.includes('400') || det.includes('401')){
        errMsg = '🔑 Error de autenticación Meta — token inválido';
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
      msg = 'La sesión expiró — recarga la página (F5)';
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
    if(!r.ok){ list.innerHTML = '<div style="color:#ef4444">Error '+r.status+'</div>'; return; }
    const d = await r.json();
    const tests = d.tests || [];
    if(!tests.length){
      list.innerHTML = '<div style="color:var(--cx-text-mute);padding:14px;text-align:center;background:var(--cx-bg-alt);border-radius:8px">Sin tests · creá el primero arriba</div>';
      return;
    }
    list.innerHTML = tests.map(t => {
      const gan = t.ganadora;
      const ganChip = gan === 'a'
        ? `<span style="background:var(--cx-success-pale);color:#16a34a;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">🏆 A gana · ${t.ganadora_diff_pct}%</span>`
        : gan === 'b'
        ? `<span style="background:var(--cx-success-pale);color:#16a34a;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">🏆 B gana · ${t.ganadora_diff_pct}%</span>`
        : gan === 'tie'
        ? `<span style="background:#3f3f46;color:#a8a29e;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">⚖ Empate técnico</span>`
        : gan === 'indeterminado'
        ? `<span style="background:#7c2d12;color:#fdba74;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">❓ Sin data</span>`
        : `<span style="background:var(--cx-info-pale);color:#2563eb;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">🟡 Activo</span>`;
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
  } catch(e){ list.innerHTML = '<div style="color:#ef4444">Error: '+esc(e.message)+'</div>'; }
}

function openABTestCrear(){
  // Modal compacto que pide los IDs y campos
  const html = `
    <div style="background:var(--cx-card);padding:14px;border-radius:8px;margin-top:12px">
      <h4 style="font-size:13px;color:var(--cx-text);margin:0 0 10px">Crear nuevo A/B test</h4>
      <div style="display:flex;flex-direction:column;gap:8px">
        <input id="ab-nombre" placeholder="Nombre del test (ej. Reel rutina vs antes/después)" style="width:100%;padding:8px;background:var(--cx-bg-alt);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px;font-size:12px">
        <input id="ab-hipotesis" placeholder="Hipótesis · qué esperás (opcional)" style="width:100%;padding:8px;background:var(--cx-bg-alt);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px;font-size:12px">
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
          <input id="ab-a-id" type="number" placeholder="ID pieza A" style="padding:8px;background:var(--cx-bg-alt);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px;font-size:12px">
          <input id="ab-b-id" type="number" placeholder="ID pieza B" style="padding:8px;background:var(--cx-bg-alt);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px;font-size:12px">
          <select id="ab-metrica" style="padding:8px;background:var(--cx-bg-alt);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px;font-size:12px">
            <option value="engagement">Engagement</option>
            <option value="alcance">Alcance</option>
            <option value="conversiones">Conversiones</option>
          </select>
        </div>
        <div style="display:flex;gap:6px;align-items:center;margin-top:6px">
          <button class="btn btn-primary btn-sm" onclick="saveABTest()">✓ Crear</button>
          <span id="ab-crear-status" style="font-size:11px;color:#10b981"></span>
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

// AUDIT 27-may · Widget Sentiment IG
async function loadSentimentDashboard(){
  const el = document.getElementById('dash-sentiment');
  if(!el) return;
  try {
    const r = await fetch('/api/marketing/sentiment/resumen?dias=30', {credentials:'same-origin'});
    if(!r.ok){
      el.innerHTML = '<span style="color:#ef4444">Error HTTP '+r.status+'</span>';
      return;
    }
    const d = await r.json();
    const tot = d.total_analizados || 0;
    const pend = d.pendientes_analisis || 0;
    if(tot === 0){
      el.innerHTML = `<div style="color:var(--cx-text-mute)">Sin comentarios analizados aún${pend>0?' ('+pend+' pendientes · click 🤖 Analizar)':' · click ↻ Sync + 🤖 Analizar para empezar'}</div>`;
      return;
    }
    const dist = d.distribucion || {};
    const alerta = d.alerta_crisis;
    const fmtPct = v => Math.round((v/tot)*100);
    const alertaHtml = alerta
      ? `<div style="background:#7f1d1d;color:#dc2626;padding:10px 14px;border-radius:8px;font-size:13px;font-weight:700;margin-bottom:10px">${esc(alerta)}</div>`
      : '';
    el.innerHTML = `
      ${alertaHtml}
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <div style="font-size:12px;color:var(--cx-text-mute)">${tot} comentarios analizados · 30 días${pend>0?' · '+pend+' pendientes':''}</div>
        <div style="font-size:11px;color:var(--cx-text-mute)">Quejas: <b style="color:${d.pct_quejas>10?'#ef4444':d.pct_quejas>5?'#f59e0b':'#10b981'}">${d.pct_quejas}%</b></div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin-bottom:10px">
        <div style="background:var(--cx-success-pale);padding:8px;border-radius:6px;text-align:center"><div style="font-size:9px;color:#86efac;text-transform:uppercase">😊 Positivo</div><div style="font-size:16px;font-weight:700;color:#16a34a">${dist.positivo||0}</div><div style="font-size:9px;color:#86efac">${fmtPct(dist.positivo||0)}%</div></div>
        <div style="background:var(--cx-card);padding:8px;border-radius:6px;text-align:center"><div style="font-size:9px;color:var(--cx-text-mute);text-transform:uppercase">😐 Neutro</div><div style="font-size:16px;font-weight:700;color:var(--cx-text-soft)">${dist.neutro||0}</div><div style="font-size:9px;color:var(--cx-text-mute)">${fmtPct(dist.neutro||0)}%</div></div>
        <div style="background:#78350f;padding:8px;border-radius:6px;text-align:center"><div style="font-size:9px;color:#fdba74;text-transform:uppercase">😕 Negativo</div><div style="font-size:16px;font-weight:700;color:#fb923c">${dist.negativo||0}</div><div style="font-size:9px;color:#fdba74">${fmtPct(dist.negativo||0)}%</div></div>
        <div style="background:#7f1d1d;padding:8px;border-radius:6px;text-align:center"><div style="font-size:9px;color:#dc2626;text-transform:uppercase">🚨 Queja</div><div style="font-size:16px;font-weight:700;color:#ef4444">${dist.queja||0}</div><div style="font-size:9px;color:#dc2626">${fmtPct(dist.queja||0)}%</div></div>
        <div style="background:var(--cx-info-pale);padding:8px;border-radius:6px;text-align:center"><div style="font-size:9px;color:#2563eb;text-transform:uppercase">❓ Pregunta</div><div style="font-size:16px;font-weight:700;color:#2563eb">${dist.pregunta||0}</div><div style="font-size:9px;color:#2563eb">${fmtPct(dist.pregunta||0)}%</div></div>
        <div style="background:#3f3f46;padding:8px;border-radius:6px;text-align:center"><div style="font-size:9px;color:#a8a29e;text-transform:uppercase">🗑 Spam</div><div style="font-size:16px;font-weight:700;color:#a1a1aa">${dist.spam||0}</div><div style="font-size:9px;color:#a8a29e">${fmtPct(dist.spam||0)}%</div></div>
      </div>
      ${(d.quejas_por_sku||[]).length ? `
        <div style="font-size:10px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Top SKUs con quejas</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px">
          ${d.quejas_por_sku.map(q => `<span style="background:#7f1d1d;color:#dc2626;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:700">${esc(q.sku_detectado)} · ${q.n}</span>`).join('')}
        </div>` : ''}
      ${(d.ultimas_quejas_top10||[]).length ? `
        <details style="margin-top:8px">
          <summary style="cursor:pointer;font-size:11px;color:var(--cx-text-mute)">Ver últimas ${d.ultimas_quejas_top10.length} quejas</summary>
          <div style="margin-top:8px;display:flex;flex-direction:column;gap:6px;max-height:300px;overflow-y:auto">
            ${d.ultimas_quejas_top10.map(q => `<div style="background:var(--cx-card);padding:8px;border-radius:6px;font-size:11px"><div style="color:#dc2626">"${esc((q.texto||'').slice(0,200))}"</div><div style="color:var(--cx-text-mute);margin-top:3px">@${esc(q.autor_username||'')} · ${esc((q.publicado_en||'').slice(0,10))}${q.sku_detectado?' · '+esc(q.sku_detectado):''}</div></div>`).join('')}
          </div>
        </details>` : ''}
    `;
  } catch(e){
    el.innerHTML = '<span style="color:#ef4444">Error: '+esc(e.message)+'</span>';
  }
}

async function sentimentSyncManual(){
  if(!confirm('¿Sincronizar comentarios IG nuevos? Toma ~30s.')) return;
  const el = document.getElementById('dash-sentiment');
  if(el) el.innerHTML = '<div style="color:var(--cx-text-mute)">Sincronizando comentarios IG…</div>';
  try {
    const r = await fetch('/api/marketing/sentiment/sync', _fetchOpts('POST', {dias:30, limit_por_post:50}));
    const d = await r.json();
    if(!r.ok){ showToast('Error: '+(d.error||r.status),'error'); loadSentimentDashboard(); return; }
    showToast(`✓ ${d.comentarios_nuevos||0} comentarios nuevos · ${d.posts_procesados||0} posts`,'success');
    loadSentimentDashboard();
  } catch(e){ showToast('Error red: '+e.message,'error'); loadSentimentDashboard(); }
}

async function sentimentAnalyzeManual(){
  if(!confirm('¿Analizar comentarios pendientes con Claude? Toma ~30s por lote de 50.')) return;
  const el = document.getElementById('dash-sentiment');
  if(el) el.innerHTML = '<div style="color:var(--cx-text-mute)">Analizando con Claude…</div>';
  try {
    const r = await fetch('/api/marketing/sentiment/analyze', _fetchOpts('POST', {batch:50}));
    const d = await r.json();
    if(!r.ok){ showToast('Error: '+(d.error||r.status),'error'); loadSentimentDashboard(); return; }
    showToast(`✓ ${d.procesados||0} clasificados${d.pendientes_restantes>0?' · '+d.pendientes_restantes+' aún pendientes':''}`,'success');
    loadSentimentDashboard();
  } catch(e){ showToast('Error red: '+e.message,'error'); loadSentimentDashboard(); }
}

async function loadMetaProgreso(){
  const el = document.getElementById('dash-meta-progreso');
  if(!el) return;
  try {
    const r = await fetch('/api/marketing/meta-progreso?mes='+_mesActual(), {credentials:'same-origin'});
    if(!r.ok){
      el.innerHTML = '<span style="color:#ef4444">Error HTTP '+r.status+'</span>';
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
        <div style="font-size:10px;color:var(--cx-text-mute)">Proyección fin de mes: <b style="color:#6d28d9">${fmtCOP(py.revenue||0)}</b> (${py.revenue_pct_meta||0}% meta)</div>
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
    el.innerHTML = '<span style="color:#ef4444">Error: '+esc(e.message)+'</span>';
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
        <input id="meta-rev" type="number" min="0" step="100000" value="${cur.revenue_meta||0}" style="width:100%;padding:10px;background:var(--cx-card);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px">
      </div>
      <div>
        <label style="display:block;font-size:11px;color:var(--cx-text-mute);margin-bottom:4px">📦 Pedidos meta</label>
        <input id="meta-ped" type="number" min="0" step="10" value="${cur.pedidos_meta||0}" style="width:100%;padding:10px;background:var(--cx-card);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px">
      </div>
      <div>
        <label style="display:block;font-size:11px;color:var(--cx-text-mute);margin-bottom:4px">🆕 Clientes nuevos meta</label>
        <input id="meta-cln" type="number" min="0" step="5" value="${cur.clientes_nuevos_meta||0}" style="width:100%;padding:10px;background:var(--cx-card);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px">
      </div>
      <div>
        <label style="display:block;font-size:11px;color:var(--cx-text-mute);margin-bottom:4px">📝 Notas (opcional)</label>
        <textarea id="meta-notas" rows="2" style="width:100%;padding:10px;background:var(--cx-card);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px;resize:vertical">${esc(cur.notas||'')}</textarea>
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
    document.getElementById('meta-alert').innerHTML = '<div style="color:#ef4444;font-size:12px">Valores no pueden ser negativos</div>';
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
      document.getElementById('meta-alert').innerHTML = '<div style="color:#ef4444;font-size:12px">Error: '+esc(d.error||('HTTP '+r.status))+'</div>';
      document.getElementById('meta-alert').style.display = 'block';
    }
  } catch(e){
    document.getElementById('meta-alert').innerHTML = '<div style="color:#ef4444;font-size:12px">Error red: '+esc(e.message)+'</div>';
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
    <div style="border-top:1px solid #e7e5e4;padding-top:12px">
      <div style="font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">➕ Agregar evento</div>
      <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr auto;gap:8px;align-items:end">
        <div><label style="font-size:10px;color:var(--cx-text-mute)">Evento</label><input id="cal-nuevo-evento" placeholder="Ej. Black Friday Animus" style="width:100%;padding:6px 8px;background:var(--cx-card);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px;font-size:12px"></div>
        <div><label style="font-size:10px;color:var(--cx-text-mute)">Fecha</label><input id="cal-nuevo-fecha" type="date" style="width:100%;padding:6px 8px;background:var(--cx-card);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px;font-size:12px"></div>
        <div><label style="font-size:10px;color:var(--cx-text-mute)">Multiplicador</label><input id="cal-nuevo-mult" type="number" step="0.1" min="0.1" max="10" value="2.0" style="width:100%;padding:6px 8px;background:var(--cx-card);border:1px solid #e7e5e4;color:var(--cx-text);border-radius:6px;font-size:12px"></div>
        <div><label style="font-size:10px;color:var(--cx-text-mute)">Color</label><input id="cal-nuevo-color" type="color" value="#a78bfa" style="width:100%;height:32px;padding:0;border:1px solid #e7e5e4;border-radius:6px;background:var(--cx-card)"></div>
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
    if(!r.ok){ list.innerHTML = '<span style="color:#ef4444">Error '+r.status+'</span>'; return; }
    const d = await r.json();
    const evs = d.eventos || [];
    if(!evs.length){ list.innerHTML = '<div style="color:var(--cx-text-mute);padding:14px;text-align:center">Sin eventos · agrega el primero abajo</div>'; return; }
    list.innerHTML = '<table style="width:100%;font-size:12px;border-collapse:collapse"><thead><tr style="color:var(--cx-text-mute);font-weight:700;text-align:left"><th style="padding:6px;border-bottom:1px solid #e7e5e4">Evento</th><th style="padding:6px;border-bottom:1px solid #e7e5e4">Fecha</th><th style="padding:6px;border-bottom:1px solid #e7e5e4">×Mult.</th><th style="padding:6px;border-bottom:1px solid #e7e5e4">Color</th><th style="padding:6px;border-bottom:1px solid #e7e5e4;text-align:center">Activo</th><th style="padding:6px;border-bottom:1px solid #e7e5e4;text-align:right">Acción</th></tr></thead><tbody>'
      + evs.map(e => `<tr style="border-bottom:1px solid var(--cx-hairline);${e.activo?'':'opacity:.45'}">
        <td style="padding:6px">${esc(e.evento)}</td>
        <td style="padding:6px;font-family:monospace;color:var(--cx-text-mute)">${esc(e.fecha)}</td>
        <td style="padding:6px"><span style="background:var(--cx-primary-soft);color:#6d28d9;padding:1px 6px;border-radius:6px;font-weight:700">${e.multiplicador}×</span></td>
        <td style="padding:6px"><div style="width:24px;height:18px;background:${esc(e.color||'#94a3b8')};border-radius:3px;border:1px solid #e7e5e4"></div></td>
        <td style="padding:6px;text-align:center">${e.activo?'✓':'—'}</td>
        <td style="padding:6px;text-align:right">
          ${e.activo
            ? `<button class="btn btn-danger btn-sm" onclick="toggleEventoCal(${parseInt(e.id)||0}, 0)" style="font-size:10px;padding:2px 8px" title="Desactivar">🗑</button>`
            : `<button class="btn btn-outline btn-sm" onclick="toggleEventoCal(${parseInt(e.id)||0}, 1)" style="font-size:10px;padding:2px 8px" title="Reactivar">↻</button>`}
        </td>
      </tr>`).join('')
      + '</tbody></table>';
  } catch(e){ list.innerHTML = '<span style="color:#ef4444">Error: '+esc(e.message)+'</span>'; }
}

async function toggleEventoCal(id, activo){
  if(activo === 0 && !confirm('¿Desactivar este evento? Los agentes ya no lo considerarán.')) return;
  try {
    const r = activo === 0
      ? await fetch('/api/marketing/eventos-calendario/'+id, _fetchOpts('DELETE'))
      : await fetch('/api/marketing/eventos-calendario/'+id, _fetchOpts('PUT', {activo: true}));
    const d = await r.json().catch(()=>({}));
    if(!r.ok){
      document.getElementById('cal-cosm-alert').innerHTML = '<div style="color:#ef4444;font-size:12px">Error: '+esc(d.error||r.status)+'</div>';
      return;
    }
    loadEventosCalendario();
  } catch(e){
    document.getElementById('cal-cosm-alert').innerHTML = '<div style="color:#ef4444;font-size:12px">Error red: '+esc(e.message)+'</div>';
  }
}

async function addEventoCalendario(){
  const ev = document.getElementById('cal-nuevo-evento').value.trim();
  const fc = document.getElementById('cal-nuevo-fecha').value;
  const mult = parseFloat(document.getElementById('cal-nuevo-mult').value)||1;
  const col = document.getElementById('cal-nuevo-color').value;
  const alert = document.getElementById('cal-cosm-alert');
  if(!ev || !fc){ alert.innerHTML = '<div style="color:#ef4444;font-size:12px">Evento y fecha obligatorios</div>'; return; }
  try {
    const r = await fetch('/api/marketing/eventos-calendario', _fetchOpts('POST', {
      evento: ev, fecha: fc, multiplicador: mult, color: col
    }));
    const d = await r.json().catch(()=>({}));
    if(!r.ok){
      alert.innerHTML = '<div style="color:#ef4444;font-size:12px">Error: '+esc(d.error||r.status)+'</div>';
      return;
    }
    alert.innerHTML = '<div style="color:#10b981;font-size:12px">✓ Evento agregado</div>';
    document.getElementById('cal-nuevo-evento').value = '';
    document.getElementById('cal-nuevo-fecha').value = '';
    loadEventosCalendario();
    setTimeout(()=>{ alert.innerHTML = ''; }, 2000);
  } catch(e){
    alert.innerHTML = '<div style="color:#ef4444;font-size:12px">Error red: '+esc(e.message)+'</div>';
  }
}

// ─── Feedback loop sobre agentes IA ────────────────────────────────────
let _AGENT_FEEDBACK_STATS = {};

async function loadFeedbackStats() {
  try {
    const r = await fetch('/api/marketing/agentes/feedback/stats');
    const d = await r.json();
    if (!d.ok) return;
    _AGENT_FEEDBACK_STATS = d.agentes || {};
    // Para cada agente con stats, inyectar/actualizar un tag de tasa de acierto
    // dentro de su card. La card se identifica por el botón btn-<agente>.
    Object.keys(_AGENT_FEEDBACK_STATS).forEach(ag => {
      const stats = _AGENT_FEEDBACK_STATS[ag];
      if (stats.tasa_acierto_pct == null) return;
      const btn = document.getElementById('btn-' + ag);
      if (!btn) return;
      const card = btn.closest('.agent-card') || btn.parentElement;
      if (!card) return;
      let tag = card.querySelector('.agent-feedback-tag');
      if (!tag) {
        tag = document.createElement('div');
        tag.className = 'agent-feedback-tag';
        tag.style.cssText = 'font-size:10px;color:var(--cx-text-mute);margin-bottom:6px;padding:3px 8px;background:var(--cx-bg-alt);border-radius:6px;display:inline-block;';
        // Insertar antes del botón
        btn.parentElement.insertBefore(tag, btn);
      }
      const col = stats.tasa_acierto_pct >= 70 ? '#34d399' :
                  (stats.tasa_acierto_pct >= 40 ? '#fbbf24' : '#ef4444');
      tag.innerHTML = `<span style="color:${col};font-weight:700;">${stats.tasa_acierto_pct}%</span> útil · ${stats.total} feedback`;
    });
  } catch(e) { /* silencioso */ }
}

function renderFeedbackBar(logId) {
  if (!logId) return '';
  return `<div class="feedback-bar" id="fb-bar-${logId}" style="display:flex;align-items:center;gap:8px;margin-top:14px;padding:10px 14px;background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:8px;">
    <span style="font-size:11px;color:var(--cx-text-mute);font-weight:600;">¿Te sirvió este análisis?</span>
    <button onclick="sendFeedback(${logId},'util',event)" style="background:var(--cx-success-pale);color:#16a34a;border:1px solid var(--cx-hairline);padding:5px 12px;border-radius:6px;font-size:11px;cursor:pointer;font-weight:700;">👍 Útil</button>
    <button onclick="sendFeedback(${logId},'ejecutado',event)" style="background:var(--cx-info-pale);color:#2563eb;border:1px solid #1d4ed8;padding:5px 12px;border-radius:6px;font-size:11px;cursor:pointer;font-weight:700;">⚡ Ejecuté la acción</button>
    <button onclick="sendFeedback(${logId},'no_util',event)" style="background:#7f1d1d;color:#dc2626;border:1px solid #991b1b;padding:5px 12px;border-radius:6px;font-size:11px;cursor:pointer;font-weight:700;">👎 No sirvió</button>
    <span id="fb-status-${logId}" style="font-size:10px;color:var(--cx-text-mute);margin-left:auto;"></span>
  </div>`;
}

async function sendFeedback(logId, fb, ev) {
  if (ev) ev.stopPropagation();
  const status = document.getElementById('fb-status-' + logId);
  const bar = document.getElementById('fb-bar-' + logId);
  if (status) status.textContent = 'Enviando...';
  try {
    const r = await fetch('/api/marketing/agentes/feedback', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({log_id: logId, feedback: fb})
    });
    const d = await r.json();
    if (d.ok) {
      const labels = {util:'👍 Marcado como útil', ejecutado:'⚡ Acción registrada', no_util:'👎 Feedback registrado'};
      if (bar) bar.style.opacity = '0.5';
      if (status) status.textContent = labels[fb] || 'Registrado';
      loadFeedbackStats();
    } else {
      if (status) status.textContent = 'Error: ' + (d.error || 'no se pudo guardar');
    }
  } catch (e) {
    if (status) status.textContent = 'Error de red';
  }
}

async function runAgent(agente) {
  const btn = document.getElementById('btn-'+agente);
  const resultDiv = document.getElementById('result-'+agente);
  if(!btn||!resultDiv) return;
  btn.classList.add('running');
  btn.innerHTML = '<span class="spin"></span> Ejecutando...';
  resultDiv.classList.remove('show');

  let body = {};
  if(agente==='brief') {
    const sel = document.getElementById('brief-campana-sel');
    if(sel && sel.value) body.campana_id = parseInt(sel.value);
  }

  try {
    const resp = await fetch(`/api/marketing/agentes/${agente}`, _fetchOpts('POST', body));
    // Audit 25-may PM · validar HTTP antes de parsear · evita JSON parse error si backend 500
    if(!resp.ok){
      const txt = await resp.text().catch(()=>'');
      resultDiv.innerHTML = `<pre style="color:#dc2626;">Error HTTP ${resp.status}: ${_escHtml(txt.slice(0,400))}</pre>`;
      resultDiv.classList.add('show');
      btn.classList.remove('running');
      btn.innerHTML = `<span>&#x25B6; ${AGENT_LABELS[agente]||agente}</span>`;
      return;
    }
    const data = await resp.json();
    if(data.error) {
      resultDiv.innerHTML = `<pre style="color:#dc2626;">Error: ${_escHtml(data.error)}</pre>`;
    } else {
      resultDiv.innerHTML = formatAgentResult(agente, data) + renderFeedbackBar(data.log_id);

      // Master agent Estrategia: redirige a la sub-tab dedicada con el output
      // persistente. Así el jefe puede volver luego sin re-generar.
      if (agente === 'estrategia') {
        // Marcar como cargada y refrescar la vista persistente
        _loaded.estrategia = false; // forzar re-render
        await loadUltimaEstrategia();
        // Ir a la sub-tab Estrategia (dentro de Inteligencia)
        showSub('estrategia');
        // Scroll al inicio de la vista
        setTimeout(() => {
          const view = document.getElementById('estrategia-vista');
          if (view) view.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 250);
        showToast('✅ Estrategia generada — revisá el calendario y oportunidades', 'success');
      }
    }
    resultDiv.classList.add('show');
    loadAgentLog();
    loadFeedbackStats();
  } catch(e) {
    resultDiv.innerHTML = `<pre style="color:#dc2626;">Error: ${e.message}</pre>`;
    resultDiv.classList.add('show');
  } finally {
    btn.classList.remove('running');
    btn.innerHTML = `<span>&#x25B6; ${AGENT_LABELS[agente]||agente}</span>`;
  }
}

function fmtIA(data) {
  if(!data.analisis_ia) return '';
  // Audit 25-may PM · P0 · escapar output de Claude (texto libre, puede tener
  // <script> u otro HTML). white-space:pre-line mantiene los saltos de línea.
  return `<div style="margin-top:14px;padding:14px;background:linear-gradient(135deg,rgba(212,175,55,.08),rgba(212,175,55,.03));border:1px solid rgba(212,175,55,.25);border-radius:10px">
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
      <span style="font-size:15px">🤖</span>
      <span style="font-size:11px;font-weight:700;color:#d4af37;letter-spacing:.5px;text-transform:uppercase">Análisis IA — Claude</span>
    </div>
    <div style="font-size:13px;color:var(--cx-text);line-height:1.7;white-space:pre-line">${esc(data.analisis_ia)}</div>
  </div>`;
}

function formatAgentResult(agente, data) {
  let out = '';

  if(agente==='estacionalidad') {
    if(!data.alertas||!data.alertas.length) { out='✅ Sin alertas de estacionalidad en los próximos 120 días.'; }
    else {
      out += `📅 ${data.titulo}\n${'─'.repeat(40)}\n`;
      out += `Total alertas: ${data.total_alertas} | Críticos: ${data.criticos}\n\n`;
      data.alertas.forEach(a=>{
        const icon = a.estado==='critico'?'🔴':a.estado==='advertencia'?'🟡':'🟢';
        out += `${icon} ${a.evento} (${a.fecha_evento}) — ${a.dias_restantes}d\n`;
        out += `   SKU: ${a.sku} | Stock: ${fmt(a.stock_actual)} | Demanda: ${fmt(a.demanda_proyectada)}\n`;
        if(a.deficit>0) out += `   Déficit: ${fmt(a.deficit)} uds | Deadline prod: ${a.deadline_produccion||'—'}\n`;
        out += '\n';
      });
    }
    return `<pre>${esc(out)}</pre>${fmtIA(data)}`;
  }

  if(agente==='oportunidad') {
    if(!data.recomendaciones||!data.recomendaciones.length) { out='✅ Sin SKUs con oportunidad crítica identificados.'; }
    else {
      out += `🎯 ${data.titulo}\n${'─'.repeat(40)}\n`;
      data.recomendaciones.forEach((r,i)=>{
        out += `${i+1}. ${r.sku} — Score: ${r.score}\n`;
        out += `   Stock: ${fmt(r.stock)} uds | Rotación: ${r.rotacion_mes}/mes | ${r.meses_cobertura}m inventario\n`;
        out += `   Razones: ${r.razones.join(', ')}\n`;
        out += `   ➜ ${r.accion}\n\n`;
      });
    }
    return `<pre>${esc(out)}</pre>${fmtIA(data)}`;
  }

  if(agente==='roi') {
    out += `💰 ${data.titulo}\n${'─'.repeat(40)}\n`;
    out += `Shopify revenue 30d: ${fmtM(data.shopify_revenue_30d||0)}\n\n`;
    if(data.campanas&&data.campanas.length) {
      out += 'CAMPAÑAS:\n';
      data.campanas.forEach(c=>{
        const icon = c.estado_roi==='excelente'?'🟢':c.estado_roi==='bueno'?'🟡':'🔴';
        out += `  ${icon} ${c.nombre}: ROI ${c.roi_pct}% | ${fmtM(c.presupuesto_gastado)} → ${fmtM(c.resultado_ventas)}\n`;
      });
    } else out += 'Sin campañas con inversión registrada.\n';
    return `<pre>${esc(out)}</pre>${fmtIA(data)}`;
  }

  if(agente==='tendencias') {
    out += `📈 ${data.titulo}\n${'─'.repeat(40)}\n`;
    if(data.tendencias_erp&&data.tendencias_erp.length) {
      out += 'ERP — TOP VARIACIONES:\n';
      data.tendencias_erp.forEach(t=>{
        const icon = t.tendencia==='alza'?'🟢':t.tendencia==='baja'?'🔴':'⚪';
        out += `  ${icon} ${t.sku}: ${t.cambio_pct>0?'+':''}${t.cambio_pct}% (${t.reciente} vs ${t.anterior} uds)\n`;
      });
    }
    if(data.shopify_mensual&&data.shopify_mensual.length) {
      out += '\nSHOPIFY MENSUAL:\n';
      data.shopify_mensual.forEach(m=>out+=`  ${m.mes}: ${fmtM(m.ventas)} (${m.pedidos} pedidos)\n`);
    }
    return `<pre>${esc(out)}</pre>${fmtIA(data)}`;
  }

  if(agente==='brief') {
    if(!data.briefs||!data.briefs.length) { out='Sin SKUs con liberaciones recientes.'; }
    else {
      out += `📋 ${data.titulo}\n${'─'.repeat(40)}\n`;
      data.briefs.forEach(b=>{
        out += `\nSKU: ${b.sku} (${fmt(b.uds_90d)} uds / 90d)\n`;
        out += `Precio: ${fmtM(b.precio)} | Menciones IG: ${b.ig_menciones}\n`;
        out += `Brief: ${b.brief}\n`;
      });
    }
    return `<pre>${esc(out)}</pre>${fmtIA(data)}`;
  }

  if(agente==='pricing') {
    if(!data.propuestas||!data.propuestas.length) { out='Sin SKUs elegibles para promoción.'; }
    else {
      out += `🏷️ ${data.titulo}\n${'─'.repeat(40)}\n`;
      data.propuestas.forEach(p=>{
        out += `\n${p.sku} — ${p.meses_cobertura}m de inventario\n`;
        out += `  Precio normal: ${fmtM(p.precio_normal)} → Precio promo: ${fmtM(p.precio_promo)} (-${p.max_descuento_pct}%)\n`;
        out += `  ${p.razon}\n`;
      });
    }
    return `<pre>${esc(out)}</pre>${fmtIA(data)}`;
  }

  if(agente==='reorden') {
    if(!data.predicciones||!data.predicciones.length) { out='Sin clientes B2B con 2+ pedidos detectados.'; }
    else {
      out += `🔄 ${data.titulo}\n${'─'.repeat(40)}\n`;
      data.predicciones.forEach(p=>{
        const icon = p.urgencia==='hoy'?'🔴':p.urgencia==='esta semana'?'🟡':'🟢';
        out += `\n${icon} ${p.email}\n`;
        out += `  Pedidos: ${p.pedidos} | Revenue: ${fmtM(p.revenue_total)} | Ticket: ${fmtM(p.ticket_promedio)}\n`;
        out += `  Intervalo: ${p.intervalo_dias}d | Próximo: ${p.proximo_reorden_estimado} (${p.dias_para_reorden}d) — ${p.urgencia}\n`;
      });
    }
    return `<pre>${esc(out)}</pre>${fmtIA(data)}`;
  }

  if(agente==='canibal') {
    if(!data.conflictos||!data.conflictos.length) {
      out = `✅ Sin conflictos detectados. ${data.campanas_revisadas} campañas revisadas.`;
    } else {
      out += `⚠️ ${data.titulo}\n${'─'.repeat(40)}\n`;
      out += `${data.conflictos.length} conflictos en ${data.campanas_revisadas} campañas.\n\n`;
      data.conflictos.forEach((c,i)=>{
        out += `${i+1}. "${c.campana_a}" vs "${c.campana_b}"\n`;
        out += `   Tipo: ${c.conflicto} | Canal: ${c.canal||'—'} | SKU: ${c.sku||'—'}\n`;
        out += `   ➜ ${c.recomendacion}\n\n`;
      });
    }
    return `<pre>${esc(out)}</pre>${fmtIA(data)}`;
  }

  if(agente==='contenido_auto') {
    if(!data.piezas||!data.piezas.length) { out='Sin SKUs con liberaciones recientes.'; }
    else {
      out += `✍️ ${data.titulo}\n${'─'.repeat(40)}\n`;
      data.piezas.forEach(p=>{
        out += `\n📦 ${p.sku} (${fmt(p.uds_30d)} uds / 30d | ${fmtM(p.precio)})\n`;
        out += `\nINSTAGRAM:\n${p.caption_instagram}\n`;
        out += `\nEMAIL — Asunto: ${p.asunto_email}\n`;
        out += `\nWHATSAPP: ${p.texto_whatsapp}\n`;
        out += '\n'+'─'.repeat(30)+'\n';
      });
    }
    return `<pre>${esc(out)}</pre>${fmtIA(data)}`;
  }

  if(agente==='alerta_stock') {
    if(!data.alertas||!data.alertas.length) { out='✅ Sin alertas de stock. Todos los SKUs tienen cobertura adecuada.'; }
    else {
      out += `🚨 ${data.titulo}\n${'─'.repeat(40)}\n`;
      data.alertas.forEach(a=>{
        const icon = a.nivel==='critico'?'🔴':'🟡';
        out += `${icon} ${a.sku} — ${a.dias_cobertura_real}d de cobertura\n`;
        out += `   Stock: ${fmt(a.stock)} | ERP: ${fmt(a.rotacion_erp)} uds/mes | Shopify: ${fmt(a.demanda_shopify_30d)} uds/30d\n`;
        out += `   ➜ ${a.accion}\n\n`;
      });
    }
    return `<pre>${esc(out)}</pre>${fmtIA(data)}`;
  }

  if(agente==='estrategia') {
    const k = data.kpis || {};
    const snap = data.snapshot || {};
    // KPIs del snapshot
    let html = `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:18px;">`;
    const kpiCards = [
      {label:'SKUs para empujar', val:k.skus_a_empujar||0, color:'#fbbf24'},
      {label:'SKUs en riesgo',    val:k.skus_en_riesgo||0, color:'#ef4444'},
      {label:'Influencers activos', val:k.influencers_activos||0, color:'#34d399'},
      {label:'Eventos próx. 60d', val:k.eventos_en_60d||0, color:'#a78bfa'},
      {label:'Producción planificada', val:k.produccion_planificada||0, color:'#60a5fa'},
    ];
    html += kpiCards.map(c=>`
      <div style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:10px;padding:12px 14px;">
        <div style="font-size:22px;font-weight:800;color:${c.color};line-height:1;">${c.val}</div>
        <div style="font-size:11px;color:var(--cx-text-mute);margin-top:4px;">${c.label}</div>
      </div>`).join('');
    html += '</div>';
    // Análisis IA (markdown del modelo) — render con markdown básico
    if(data.analisis_ia) {
      html += `<div style="background:linear-gradient(135deg,rgba(124,58,237,.10),rgba(124,58,237,.03));border:1px solid rgba(124,58,237,.35);border-radius:12px;padding:18px;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
          <span style="font-size:16px;">🧠</span>
          <span style="font-size:11px;font-weight:700;color:#6d28d9;letter-spacing:.5px;text-transform:uppercase;">Análisis estratégico — Claude Sonnet</span>
        </div>
        <div class="estrategia-md">${renderMarkdownBasic(data.analisis_ia)}</div>
      </div>`;
    } else {
      html += `<div style="padding:14px;color:#f59e0b;background:#78350f33;border:1px solid #f59e0b44;border-radius:8px;font-size:13px;">⚠️ Sin análisis IA — verificá que ANTHROPIC_API_KEY esté configurada en animus_config.</div>`;
    }
    // Datos crudos colapsables (para debug / power user)
    html += `<details style="margin-top:14px;">
      <summary style="cursor:pointer;color:var(--cx-text-mute);font-size:11px;">Ver snapshot crudo (debug)</summary>
      <pre style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:8px;padding:12px;margin-top:8px;font-size:11px;color:var(--cx-text-mute);max-height:300px;overflow:auto;">${esc(JSON.stringify(snap, null, 2))}</pre>
    </details>`;
    return html;
  }

  return `<pre>${JSON.stringify(data, null, 2)}</pre>${fmtIA(data)}`;
}

// ─── Markdown muy básico para output del agente Estrategia ─────────────
function renderMarkdownBasic(md) {
  if(!md) return '';
  // Escape HTML primero
  let h = md.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  // Tablas markdown (| col | col |)
  h = h.replace(/((?:^\|.+\|\s*\n)+)/gm, function(block) {
    const lines = block.trim().split('\n');
    if(lines.length < 2) return block;
    const headers = lines[0].split('|').slice(1,-1).map(s=>s.trim());
    const rowsMd = lines.slice(2);
    let tbl = '<table style="width:100%;margin:10px 0;border-collapse:collapse;font-size:12px;">';
    tbl += '<thead><tr>'+headers.map(h=>`<th style="text-align:left;padding:8px;background:var(--cx-bg-alt);color:#6d28d9;border-bottom:1px solid #e7e5e4;">${h}</th>`).join('')+'</tr></thead>';
    tbl += '<tbody>'+rowsMd.map(r=>{
      const cols = r.split('|').slice(1,-1).map(s=>s.trim());
      return '<tr>'+cols.map(c=>`<td style="padding:7px 8px;color:var(--cx-text-soft);border-bottom:1px solid var(--cx-hairline);">${c}</td>`).join('')+'</tr>';
    }).join('')+'</tbody></table>';
    return tbl;
  });
  // Headings
  h = h.replace(/^## (.+)$/gm, '<h3 style="font-size:14px;color:#6d28d9;margin:18px 0 8px;font-weight:700;">$1</h3>');
  h = h.replace(/^# (.+)$/gm, '<h2 style="font-size:16px;color:var(--cx-text);margin:18px 0 10px;font-weight:800;">$1</h2>');
  // Bold + italic
  h = h.replace(/\*\*(.+?)\*\*/g, '<strong style="color:var(--cx-text);">$1</strong>');
  h = h.replace(/\*(.+?)\*/g, '<em>$1</em>');
  // Listas numeradas
  h = h.replace(/^(\d+)\. (.+)$/gm, '<div style="margin:4px 0;"><span style="color:#6d28d9;font-weight:700;margin-right:6px;">$1.</span>$2</div>');
  // Listas bullets
  h = h.replace(/^[-*] (.+)$/gm, '<div style="margin:4px 0 4px 16px;"><span style="color:#6d28d9;margin-right:6px;">·</span>$1</div>');
  // Saltos de línea (no dentro de tablas/divs ya generados)
  h = h.replace(/\n\n+/g, '<div style="height:8px;"></div>');
  h = h.replace(/\n/g, '<br>');
  // Limpiar dobles <br> alrededor de tablas/headings/divs
  h = h.replace(/<br>\s*(<(?:h[123]|table|div|details))/g, '$1');
  h = h.replace(/(<\/(?:h[123]|table|div|details)>)\s*<br>/g, '$1');
  return `<div style="font-size:13px;color:var(--cx-text);line-height:1.7;">${h}</div>`;
}

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

async function loadAgentLog() {
  const rows = await fetch('/api/marketing/agentes/log').then(r=>r.json());
  const body = document.getElementById('agent-log-body');
  if(!rows.length) { body.innerHTML='<tr class="empty-row"><td colspan="5">Sin ejecuciones registradas</td></tr>'; return; }
  body.innerHTML = rows.map(r=>`
    <tr>
      <td style="color:var(--cx-text-mute);">${r.fecha?.substring(0,16)||'—'}</td>
      <td><span class="badge badge-purple">${r.agente}</span></td>
      <td style="color:var(--cx-text-mute);">${r.accion||'—'}</td>
      <td>${r.ejecutado_por||'—'}</td>
      <td><button class="btn btn-outline btn-sm" onclick="verResultadoLog(${r.id})">Ver</button></td>
    </tr>`).join('');
}

async function verResultadoLog(id) {
  const data = await fetch(`/api/marketing/agentes/log/${id}`).then(r=>r.json());
  document.getElementById('modal-agent-title').textContent = `Resultado: Agente ${data.agente} — ${data.fecha?.substring(0,16)}`;
  let content = '';
  if(typeof data.resultado === 'object') {
    content = formatAgentResult(data.agente?.toLowerCase(), data.resultado);
  } else {
    content = data.resultado || '(sin resultado)';
  }
  document.getElementById('modal-agent-content').innerHTML = content;
  document.getElementById('modal-agente-result').classList.add('open');
}

// ──────────────────────────────────────────────────────────────────────────────
// ANALYTICS
// ──────────────────────────────────────────────────────────────────────────────
async function loadAnalytics() {
  const fmt  = v => v>=1e6?(v/1e6).toFixed(1)+'M':v>=1e3?(v/1e3).toFixed(0)+'K':String(Math.round(v||0));
  const fmtM = v => '$'+fmt(v||0);
  function svgBars(meses, valFn, colorFill, labelFn) {
    if(!meses.length) return '<div style="color:var(--cx-text-mute);text-align:center;padding:40px;">Sin datos</div>';
    const vals = meses.map(valFn);
    const maxV = Math.max(...vals, 1);
    const W=520, H=190, padL=8, padR=8, padB=32, padT=20;
    const n = meses.length;
    const slotW = (W-padL-padR)/n;
    const barW  = Math.max(10, Math.min(36, slotW-6));
    let svg = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;display:block;">`;
    meses.forEach((m, i) => {
      const v = vals[i];
      const bh = Math.max(4, Math.round((v/maxV)*(H-padB-padT)));
      const x  = padL + i*slotW + (slotW-barW)/2;
      const by = H - padB - bh;
      svg += `<rect x="${x.toFixed(1)}" y="${by}" width="${barW}" height="${bh}" rx="3" fill="${colorFill}" opacity="0.88"/>`;
      // month label
      const lbl = (m.mes||'').slice(2); // YY-MM
      svg += `<text x="${(x+barW/2).toFixed(1)}" y="${H-10}" text-anchor="middle" font-size="9" fill="#64748b">${lbl}</text>`;
      // value label if bar is tall enough
      if(v>0) svg += `<text x="${(x+barW/2).toFixed(1)}" y="${Math.max(padT+2,by-4)}" text-anchor="middle" font-size="9" fill="${labelFn}" font-weight="600">${fmtM(v)}</text>`;
    });
    svg += '</svg>';
    return svg;
  }

  // Fetch in parallel
  const [data, roiData] = await Promise.all([
    fetch('/api/marketing/analytics/influencers').then(r=>r.json()).catch(()=>({})),
    fetch('/api/marketing/analytics/roi').then(r=>r.json()).catch(()=>({}))
  ]);

  // ── KPIs histórico ──
  document.getElementById('an-total-hist').textContent     = fmtM(data.total_pagado_historico||0);
  document.getElementById('an-colabs-hist').textContent    = data.colabs_historico||0;
  document.getElementById('an-creadores-hist').textContent = data.creadores_historico||0;
  document.getElementById('an-avg-colab').textContent      = fmtM(data.promedio_por_colab||0);
  document.getElementById('an-pendiente-total').textContent= fmtM(data.total_pendiente||0);
  document.getElementById('an-top-creador').textContent    = data.top_creador||'—';

  // ── KPIs Shopify ──
  const sh = roiData.shopify_kpis||{};
  document.getElementById('an-sh-30d').textContent    = fmtM(sh.revenue_30d||0);
  document.getElementById('an-sh-mes').textContent    = fmtM(sh.revenue_mes||0);
  document.getElementById('an-sh-orders').textContent = sh.pedidos_30d||'—';
  const crec = sh.crecimiento_pct;
  if(crec!=null) {
    const crecEl = document.getElementById('an-sh-crec');
    const crecCard = document.getElementById('an-sh-crec-card');
    const sign = crec>=0?'+':'';
    crecEl.textContent = sign+crec.toFixed(1)+'%';
    crecEl.style.color = crec>=0?'#34d399':'#f87171';
    crecCard.style.borderColor = crec>=0?'#34d399':'#f87171';
  }

  // ── Charts ──
  const meses = data.por_mes||[];
  document.getElementById('an-gasto-chart').innerHTML = svgBars(meses, m=>m.total_pagado, '#6366f1', '#a5b4fc');
  document.getElementById('an-total-label').textContent = 'Histórico: '+fmtM(data.total_pagado_historico||0);
  document.getElementById('an-nuevos-chart').innerHTML  = svgBars(meses, m=>m.nuevos_creadores||0, '#34d399', '#6ee7b7');

  // ── Ranking ALL TIME ──
  const ranking = data.ranking||[];
  const rb = document.getElementById('an-ranking-body');
  rb.innerHTML = ranking.length ? ranking.map((r,i)=>{
    const estadoBadge = r.estado==='Activo'
      ? '<span style="color:#16a34a;">Activo</span>'
      : '<span style="color:#dc2626;">'+r.estado+'</span>';
    const pendBadge = r.pendiente>0
      ? `<span style="color:#f59e0b;font-weight:700;">${fmtM(r.pendiente)}</span>`
      : '<span style="color:var(--cx-text-faint);">—</span>';
    return `<tr>
      <td class="mob-hide" style="color:var(--cx-text-mute);font-weight:700;">${i+1}</td>
      <td style="font-weight:700;">${esc(r.nombre||'—')}</td>
      <td class="mob-hide" style="color:var(--cx-text-mute);">${r.colabs||0}</td>
      <td style="color:#818cf8;font-weight:800;">${fmtM(r.total)}</td>
      <td>${pendBadge}</td>
      <td class="mob-hide" style="color:var(--cx-text-mute);">${fmtM(r.promedio)}</td>
      <td class="mob-hide" style="color:var(--cx-text-mute);font-size:12px;">${esc(r.primer_pago||'—')}</td>
      <td class="mob-hide" style="color:var(--cx-text-mute);font-size:12px;">${esc(r.ultimo_pago||'—')}</td>
      <td>${estadoBadge}</td>
    </tr>`;
  }).join('') : '<tr class="empty-row"><td colspan="9">Sin datos de pagos registrados.</td></tr>';

  // ── Detalle mensual ──
  const mb = document.getElementById('an-meses-body');
  mb.innerHTML = meses.length ? [...meses].reverse().map(m=>
    `<tr>
      <td style="font-weight:700;color:var(--cx-text);">${esc(m.mes)}</td>
      <td class="mob-hide">${m.colabs}</td>
      <td class="mob-hide">${m.creadores_unicos_mes}</td>
      <td style="color:#818cf8;font-weight:700;">${fmtM(m.total_pagado)}</td>
      <td style="color:#f59e0b;">${m.total_pendiente>0?fmtM(m.total_pendiente):'—'}</td>
      <td class="mob-hide" style="color:#16a34a;">${m.nuevos_creadores||0}</td>
    </tr>`
  ).join('') : '<tr class="empty-row"><td colspan="6">Sin datos</td></tr>';
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
    <div style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:8px;padding:12px;text-align:center;">
      <div style="font-size:18px;font-weight:800;color:#16a34a;">${fmtM(inf.total_pagado||0)}</div>
      <div style="font-size:11px;color:var(--cx-text-mute);margin-top:2px;">Total pagado</div>
    </div>
    <div style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:8px;padding:12px;text-align:center;">
      <div style="font-size:18px;font-weight:800;color:#818cf8;">${inf.pagos_count||0}</div>
      <div style="font-size:11px;color:var(--cx-text-mute);margin-top:2px;">Colaboraciones</div>
    </div>
    <div style="background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:8px;padding:12px;text-align:center;">
      <div style="font-size:18px;font-weight:800;color:#f59e0b;">${fmtM(inf.total_pendiente||0)}</div>
      <div style="font-size:11px;color:var(--cx-text-mute);margin-top:2px;">Pendiente pago</div>
    </div>
  </div>`;

  // ── Pagos realizados ──
  if(pagadas.length) {
    html += `<div style="font-size:12px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">✅ Pagos realizados</div>
    <table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px;">
      <thead><tr style="border-bottom:1px solid #e7e5e4;">
        <th style="padding:6px 8px;text-align:left;color:var(--cx-text-mute);">Fecha</th>
        <th style="padding:6px 8px;text-align:left;color:var(--cx-text-mute);">Concepto</th>
        <th style="padding:6px 8px;text-align:right;color:var(--cx-text-mute);">Valor</th>
        <th style="padding:6px 8px;text-align:left;color:var(--cx-text-mute);">OC</th>
      </tr></thead>
      <tbody>`;
    pagadas.forEach(p=>{
      html += `<tr style="border-bottom:1px solid var(--cx-hairline);">
        <td style="padding:6px 8px;color:var(--cx-text-mute);">${p.fecha||'—'}</td>
        <td style="padding:6px 8px;">${p.concepto||'—'}</td>
        <td style="padding:6px 8px;text-align:right;color:#16a34a;font-weight:700;">${fmtM(p.valor||0)}</td>
        <td style="padding:6px 8px;color:var(--cx-text-mute);font-size:11px;">${p.numero_oc||'—'}</td>
      </tr>`;
    });
    html += `</tbody></table>`;
  }

  // ── Pendientes ──
  if(pendientes.length) {
    html += `<div style="font-size:12px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">⏳ Pendientes de pago</div>
    <table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px;">
      <thead><tr style="border-bottom:1px solid #e7e5e4;">
        <th style="padding:6px 8px;text-align:left;color:var(--cx-text-mute);">Fecha</th>
        <th style="padding:6px 8px;text-align:left;color:var(--cx-text-mute);">Concepto</th>
        <th style="padding:6px 8px;text-align:right;color:var(--cx-text-mute);">Valor</th>
      </tr></thead>
      <tbody>`;
    pendientes.forEach(p=>{
      html += `<tr style="border-bottom:1px solid var(--cx-hairline);">
        <td style="padding:6px 8px;color:var(--cx-text-mute);">${p.fecha||'—'}</td>
        <td style="padding:6px 8px;">${p.concepto||'—'}</td>
        <td style="padding:6px 8px;text-align:right;color:#f59e0b;font-weight:700;">${fmtM(p.valor||0)}</td>
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

function scoreColor(s) {
  if (s >= 75) return '#34d399';
  if (s >= 50) return '#667eea';
  if (s >= 25) return '#f59e0b';
  return '#f87171';
}
function scoreBadge(s) {
  const c = scoreColor(s);
  return '<span style="display:inline-block;background:'+c+'22;color:'+c+';border:1px solid '+c+'44;border-radius:20px;padding:2px 10px;font-weight:700;font-size:13px;min-width:42px;text-align:center;">'+s+'</span>';
}
function sevColor(sev) {
  return {critical:'#f87171',high:'#fb923c',medium:'#f59e0b',low:'#34d399'}[sev]||'#94a3b8';
}
function sevLabel(sev) {
  return {critical:'CRITICO',high:'ALTO',medium:'MEDIO',low:'BAJO'}[sev]||sev.toUpperCase();
}

async function loadAgencia(force) {
  if (_agLoaded && !force) return;
  _agLoaded = true;
  var errHtml = '';
  try {
    document.getElementById('ag-scoring-tbody').innerHTML = '<tr class="empty-row"><td colspan="8">Analizando portafolio...</td></tr>';
    document.getElementById('ag-audit-list').innerHTML = '<div style="color:var(--cx-text-mute);font-size:13px;">Calculando...</div>';
    document.getElementById('ag-competition').innerHTML = '<div style="color:var(--cx-text-mute);font-size:13px;">Calculando...</div>';
    document.getElementById('ag-proposals').innerHTML = '<div style="color:var(--cx-text-mute);font-size:13px;">Generando propuestas...</div>';
  } catch(domErr) {
    console.error('[loadAgencia] DOM error:', domErr);
    _agLoaded = false;
    return;
  }
  try {
    var r = await fetch('/api/marketing/agencia/audit');
    var d = await r.json();
    if (!r.ok) { throw new Error(d.error || 'Error del servidor'); }
    renderAgencia(d);
  } catch(fetchErr) {
    errHtml = '<div style="color:#dc2626;font-size:13px;padding:12px;background:#7f1d1d22;border-radius:8px;border:1px solid #f87171;">Error: '+fetchErr.message+'</div>';
    try { document.getElementById('ag-scoring-tbody').innerHTML = '<tr><td colspan="8">'+errHtml+'</td></tr>'; } catch(_){}
    try { document.getElementById('ag-audit-list').innerHTML = errHtml; } catch(_){}
    try { document.getElementById('ag-competition').innerHTML = errHtml; } catch(_){}
    try { document.getElementById('ag-proposals').innerHTML = errHtml; } catch(_){}
    console.error('[loadAgencia]', fetchErr);
    _agLoaded = false;
  }
}

function renderAgencia(d) {
  var influencers = d.influencers || [];
  var audit = d.audit || [];
  var competition = d.competition || {};
  var proposals = d.proposals || [];
  var portfolio = d.portfolio || {};

  // KPIs
  document.getElementById('ag-kpi-activos').textContent = portfolio.activos || 0;
  var avgScore = influencers.length ? Math.round(influencers.reduce(function(s,i){ return s+(i.score||0); },0)/influencers.length) : 0;
  document.getElementById('ag-kpi-score').textContent = avgScore+'/100';
  document.getElementById('ag-kpi-score').style.color = scoreColor(avgScore);
  document.getElementById('ag-kpi-riesgo').textContent = portfolio.en_riesgo || 0;
  var criticals = audit.filter(function(a){ return a.severity==='critical'; }).length;
  document.getElementById('ag-kpi-critical').textContent = criticals;
  var totalInv = influencers.reduce(function(s,i){ return s+(i.total_pagado||0); },0);
  document.getElementById('ag-kpi-inversion').textContent = fmtM(totalInv);

  // Scoring table
  var sorted = influencers.slice().sort(function(a,b){ return (b.score||0)-(a.score||0); });
  var rows = '';
  sorted.forEach(function(inf) {
    var est = inf.estado === 'Activo'
      ? '<span style="color:#16a34a;font-size:11px;font-weight:700;">Activo</span>'
      : '<span style="color:var(--cx-text-mute);font-size:11px;">Inactivo</span>';
    var eng = inf.engagement_rate ? (inf.engagement_rate*100).toFixed(1)+'%' : '&#x2014;';
    var seg = inf.seguidores ? Number(inf.seguidores).toLocaleString('es-CO') : '&#x2014;';
    rows += '<tr style="border-bottom:1px solid var(--cx-hairline);">'
      +'<td style="padding:8px;font-weight:600;color:var(--cx-text);">'+(inf.nombre||'&#x2014;')+'</td>'
      +'<td style="padding:8px;color:var(--cx-text-mute);font-size:12px;">'+(inf.nicho||'&#x2014;')+'</td>'
      +'<td style="padding:8px;text-align:center;">'+scoreBadge(inf.score||0)+'</td>'
      +'<td style="padding:8px;text-align:right;color:var(--cx-text-mute);">'+eng+'</td>'
      +'<td style="padding:8px;text-align:right;color:var(--cx-text-mute);">'+seg+'</td>'
      +'<td style="padding:8px;text-align:right;color:var(--cx-text-mute);">'+(inf.campanas_count||0)+'</td>'
      +'<td style="padding:8px;text-align:right;color:#16a34a;font-weight:600;">'+fmtM(inf.total_pagado||0)+'</td>'
      +'<td style="padding:8px;text-align:center;">'+est+'</td>'
      +'</tr>';
  });
  document.getElementById('ag-scoring-tbody').innerHTML = rows || '<tr class="empty-row"><td colspan="8">Sin influencers.</td></tr>';

  // Audit
  var bySev = {critical:[],high:[],medium:[],low:[]};
  audit.forEach(function(a) { if(bySev[a.severity]) bySev[a.severity].push(a); });
  var auditHtml = '';
  ['critical','high','medium','low'].forEach(function(sev) {
    if (!bySev[sev].length) return;
    var c = sevColor(sev);
    auditHtml += '<div style="margin-bottom:12px;">'
      +'<div style="font-size:11px;font-weight:700;color:'+c+';text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">'+sevLabel(sev)+' ('+bySev[sev].length+')</div>';
    bySev[sev].forEach(function(item) {
      auditHtml += '<div style="display:flex;align-items:flex-start;gap:8px;padding:6px 0;border-bottom:1px solid var(--cx-hairline);">'
        +'<span style="color:'+c+';margin-top:1px;flex-shrink:0;">&#x25CF;</span>'
        +'<div>'
        +'<div style="color:var(--cx-text);font-size:13px;">'+item.finding+'</div>'
        +(item.recommendation ? '<div style="color:var(--cx-text-mute);font-size:11px;margin-top:2px;">'+item.recommendation+'</div>' : '')
        +'</div></div>';
    });
    auditHtml += '</div>';
  });
  document.getElementById('ag-audit-list').innerHTML = auditHtml || '<div style="color:#16a34a;font-size:13px;">Sin hallazgos.</div>';

  // Competition
  var niches = competition.niches || {};
  var gaps = competition.gaps || [];
  var compHtml = '';
  var nicheKeys = Object.keys(niches).sort(function(a,b){ return niches[b]-niches[a]; });
  if (nicheKeys.length) {
    var total = nicheKeys.reduce(function(s,k){ return s+niches[k]; },0);
    compHtml += '<div style="font-size:11px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Distribucion por nicho</div>';
    nicheKeys.forEach(function(nicho) {
      var cnt = niches[nicho];
      var pct = total ? Math.round(cnt/total*100) : 0;
      compHtml += '<div style="margin-bottom:8px;">'
        +'<div style="display:flex;justify-content:space-between;font-size:12px;color:var(--cx-text-mute);margin-bottom:3px;">'
        +'<span>'+nicho+'</span><span>'+cnt+' &middot; '+pct+'%</span></div>'
        +'<div style="background:var(--cx-card);border-radius:4px;height:6px;">'
        +'<div style="background:#667eea;width:'+pct+'%;height:6px;border-radius:4px;"></div></div></div>';
    });
  }
  if (gaps.length) {
    compHtml += '<div style="margin-top:14px;font-size:11px;font-weight:700;color:#f59e0b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Brechas detectadas</div>';
    gaps.forEach(function(g) {
      compHtml += '<div style="padding:5px 0;border-bottom:1px solid var(--cx-hairline);font-size:12px;color:var(--cx-text);">&#x26A0; '+g+'</div>';
    });
  }
  document.getElementById('ag-competition').innerHTML = compHtml || '<div style="color:var(--cx-text-mute);font-size:13px;">Sin datos suficientes.</div>';

  // Proposals
  var propHtml = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;">';
  if (proposals.length) {
    proposals.forEach(function(p) {
      var priCol = p.priority==='alta' ? '#f87171' : (p.priority==='media' ? '#f59e0b' : '#34d399');
      propHtml += '<div style="background:var(--cx-card);border:1px solid #e7e5e4;border-radius:12px;padding:16px;border-left:3px solid '+priCol+';">'
        +'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">'
        +'<div style="font-weight:700;color:var(--cx-text);font-size:14px;">'+(p.title||'')+'</div>'
        +'<span style="font-size:10px;font-weight:700;color:'+priCol+';text-transform:uppercase;background:'+priCol+'22;padding:2px 8px;border-radius:10px;">'+(p.priority||'media')+'</span></div>'
        +'<div style="color:var(--cx-text-mute);font-size:12px;line-height:1.5;margin-bottom:10px;">'+(p.description||'')+'</div>'
        +'<div style="display:flex;gap:8px;flex-wrap:wrap;">'
        +(p.budget_est ? '<span style="font-size:11px;color:#16a34a;background:#34d39922;padding:2px 8px;border-radius:8px;">'+p.budget_est+'</span>' : '')
        +(p.influencers_needed ? '<span style="font-size:11px;color:#667eea;background:#667eea22;padding:2px 8px;border-radius:8px;">'+p.influencers_needed+' influencers</span>' : '')
        +(p.expected_reach ? '<span style="font-size:11px;color:#f59e0b;background:#f59e0b22;padding:2px 8px;border-radius:8px;">'+p.expected_reach+'</span>' : '')
        +'</div></div>';
    });
  } else {
    propHtml += '<div style="color:var(--cx-text-mute);font-size:13px;padding:20px;">Sin propuestas.</div>';
  }
  propHtml += '</div>';
  document.getElementById('ag-proposals').innerHTML = propHtml;
}

// ──────────────────────────────────────────────────────────────────────────────

// ══════════════════════════════════════════════════════════════════════════════
// AGENCIA ADS — Multi-plataforma con claude-ads skill
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

function renderAdsTab() {
  const root = document.getElementById('tab-ads');
  if (!root || root.dataset.rendered === '1') return;
  root.dataset.rendered = '1';

  const platCards = ADS_PLATFORMS.map(p =>
    `<div class="ads-plat-card" data-platform="${p.id}" onclick="selectAdsPlatform('${p.id}')" style="border-color:${p.color}33;">
       <div style="font-size:28px;line-height:1;color:${p.color};">${p.icon}</div>
       <div style="font-weight:700;color:var(--cx-text);font-size:13px;margin-top:8px;">${p.name}</div>
       <div style="font-size:10px;color:var(--cx-text-mute);margin-top:2px;">${p.desc}</div>
     </div>`).join('');

  const actPlatBtns = ADS_ACTIONS_PLATFORM.map(a =>
    `<div class="ads-act-card" data-action="${a.id}" onclick="selectAdsAction('${a.id}',false)">
       <div style="font-size:22px;">${a.icon}</div>
       <div style="font-weight:700;color:var(--cx-text);font-size:13px;margin-top:6px;">${a.label}</div>
       <div style="font-size:10px;color:var(--cx-text-mute);margin-top:2px;">${a.desc}</div>
     </div>`).join('');

  const actGlobBtns = ADS_ACTIONS_GLOBAL.map(a =>
    `<div class="ads-act-card global" data-action="${a.id}" onclick="selectAdsAction('${a.id}',true)">
       <div style="font-size:22px;">${a.icon}</div>
       <div style="font-weight:700;color:var(--cx-text);font-size:13px;margin-top:6px;">${a.label}</div>
       <div style="font-size:10px;color:var(--cx-text-mute);margin-top:2px;">${a.desc}</div>
     </div>`).join('');

  root.innerHTML = `
    <style>
      .ads-hero{background:var(--cx-hero-grad);border:1px solid #4c1d95;border-radius:16px;padding:24px;margin-bottom:18px;position:relative;overflow:hidden;}
      .ads-hero:after{content:'';position:absolute;top:-50%;right:-10%;width:400px;height:400px;background:radial-gradient(circle,#7c3aed44 0%,transparent 70%);pointer-events:none;}
      .ads-hero h2{font-size:22px;font-weight:800;color:#fff;margin-bottom:6px;display:flex;align-items:center;gap:10px;}
      .ads-hero .sub{color:#6d28d9;font-size:13px;max-width:720px;line-height:1.5;}
      .ads-hero .stats{display:flex;gap:18px;margin-top:18px;flex-wrap:wrap;}
      .ads-hero .stat{background:var(--cx-bg-alt)99;border:1px solid #e7e5e4;border-radius:10px;padding:10px 14px;}
      .ads-hero .stat .v{font-size:20px;font-weight:800;color:#6d28d9;line-height:1;}
      .ads-hero .stat .l{font-size:10px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.08em;margin-top:4px;}

      .ads-section-title{font-size:11px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.1em;margin:18px 0 10px;display:flex;align-items:center;gap:8px;}
      .ads-section-title .num{display:inline-flex;width:20px;height:20px;border-radius:50%;background:#4c1d95;color:#fff;font-size:11px;font-weight:800;align-items:center;justify-content:center;}

      .ads-plat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;}
      .ads-plat-card{background:var(--cx-card);border:1px solid #e7e5e4;border-radius:12px;padding:14px;cursor:pointer;text-align:center;transition:.2s;}
      .ads-plat-card:hover{transform:translateY(-2px);background:#e7e5e4;}
      .ads-plat-card.active{background:var(--cx-primary-soft);border-color:#7c3aed!important;box-shadow:0 0 0 3px #7c3aed33;}

      .ads-act-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;}
      .ads-act-card{background:var(--cx-card);border:1px solid #e7e5e4;border-radius:10px;padding:12px;cursor:pointer;text-align:center;transition:.15s;}
      .ads-act-card:hover{background:#e7e5e4;border-color:var(--cx-text-faint);}
      .ads-act-card.active{background:var(--cx-primary-grad);border-color:#7c3aed;}
      .ads-act-card.global{border-style:dashed;}

      .ads-form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:10px;}
      .ads-input{background:var(--cx-bg-alt);border:1px solid #e7e5e4;color:var(--cx-text);padding:9px 12px;border-radius:8px;font-size:13px;width:100%;font-family:inherit;}
      .ads-input:focus{outline:none;border-color:#7c3aed;}
      .ads-textarea{background:var(--cx-bg-alt);border:1px solid #e7e5e4;color:var(--cx-text);padding:12px;border-radius:8px;font-size:12px;width:100%;font-family:'Cascadia Code',Consolas,monospace;min-height:140px;resize:vertical;}
      .ads-textarea:focus{outline:none;border-color:#7c3aed;}
      .ads-label{font-size:11px;color:var(--cx-text-mute);font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;display:block;}

      .ads-run-btn{width:100%;padding:16px;border-radius:12px;border:none;cursor:pointer;background:linear-gradient(135deg,#7c3aed,#4c1d95);color:#fff;font-size:15px;font-weight:800;letter-spacing:.02em;text-transform:uppercase;transition:.2s;display:flex;align-items:center;justify-content:center;gap:10px;}
      .ads-run-btn:hover{filter:brightness(1.1);transform:translateY(-1px);box-shadow:0 8px 24px #7c3aed44;}
      .ads-run-btn:disabled{opacity:.5;cursor:wait;transform:none;}

      .ads-output{background:var(--cx-card);border:1px solid #e7e5e4;border-radius:14px;padding:24px;margin-top:18px;}
      .ads-output h1{font-size:20px;color:var(--cx-text);margin:18px 0 10px;font-weight:800;border-bottom:1px solid #e7e5e4;padding-bottom:8px;}
      .ads-output h2{font-size:16px;color:var(--cx-text);margin:16px 0 8px;font-weight:700;}
      .ads-output h3{font-size:14px;color:#6d28d9;margin:14px 0 6px;font-weight:700;}
      .ads-output p{color:var(--cx-text-soft);font-size:13px;line-height:1.65;margin:6px 0;}
      .ads-output ul,.ads-output ol{margin:8px 0 8px 22px;color:var(--cx-text-soft);font-size:13px;line-height:1.7;}
      .ads-output li{margin:3px 0;}
      .ads-output strong{color:var(--cx-text);font-weight:700;}
      .ads-output code{background:var(--cx-bg-alt);color:#6d28d9;padding:1px 6px;border-radius:4px;font-size:12px;font-family:'Cascadia Code',Consolas,monospace;}
      .ads-output pre{background:var(--cx-bg-alt);border:1px solid #e7e5e4;border-radius:8px;padding:12px;overflow-x:auto;margin:10px 0;}
      .ads-output pre code{background:transparent;color:var(--cx-text);padding:0;font-size:12px;}
      .ads-output table{width:100%;margin:10px 0;border-collapse:collapse;}
      .ads-output th{background:var(--cx-bg-alt);text-align:left;padding:8px 10px;font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;border-bottom:1px solid #e7e5e4;}
      .ads-output td{padding:8px 10px;font-size:12px;color:var(--cx-text-soft);border-bottom:1px solid var(--cx-hairline);}
      .ads-output blockquote{border-left:3px solid #7c3aed;padding:6px 14px;margin:10px 0;color:#6d28d9;background:var(--cx-primary-soft)33;font-style:italic;}
      .ads-meta{display:flex;flex-wrap:wrap;gap:10px;font-size:11px;color:var(--cx-text-mute);margin-top:14px;padding-top:12px;border-top:1px solid #e7e5e4;}
      .ads-meta span{background:var(--cx-bg-alt);padding:3px 9px;border-radius:6px;border:1px solid #e7e5e4;}

      .ads-loader{display:flex;flex-direction:column;align-items:center;gap:14px;padding:60px 20px;}
      .ads-loader .ring{width:48px;height:48px;border:3px solid #e7e5e4;border-top-color:#7c3aed;border-radius:50%;animation:adsspin 0.9s linear infinite;}
      @keyframes adsspin{to{transform:rotate(360deg);}}
      .ads-loader .lbl{color:#6d28d9;font-size:13px;font-weight:600;}
      .ads-loader .sub{color:var(--cx-text-mute);font-size:11px;}

      .ads-history{background:var(--cx-card);border:1px solid #e7e5e4;border-radius:12px;padding:14px;margin-top:18px;}
      .ads-history-item{display:flex;align-items:center;gap:10px;padding:8px 4px;border-bottom:1px solid #e7e5e4;cursor:pointer;font-size:12px;transition:.1s;}
      .ads-history-item:hover{background:var(--cx-bg-alt)44;border-radius:6px;}
      .ads-history-item:last-child{border-bottom:none;}
    </style>

    <div class="ads-hero">
      <h2>&#x1F680; Agencia de Ads — Multi-plataforma</h2>
      <div class="sub">
        Auditoria, planning, creative y budget para 7 plataformas pagadas.
        Powered by claude-sonnet-4-5 con 250+ checks, scoring 0-100, benchmarks por industria,
        y biblioteca de specs creativos. Output en markdown listo para cliente.
      </div>
      <div class="stats">
        <div class="stat"><div class="v">7</div><div class="l">Plataformas</div></div>
        <div class="stat"><div class="v">32</div><div class="l">Capacidades</div></div>
        <div class="stat"><div class="v">~$0.06</div><div class="l">Por audit (con cache)</div></div>
        <div class="stat"><div class="v">~30s</div><div class="l">Tiempo respuesta</div></div>
      </div>
    </div>

    <div class="grid2" style="gap:18px;">
      <div>
        <div class="ads-section-title"><span class="num">1</span> Plataforma</div>
        <div class="ads-plat-grid">${platCards}</div>

        <div class="ads-section-title"><span class="num">2</span> Accion por plataforma</div>
        <div class="ads-act-grid">${actPlatBtns}</div>

        <div class="ads-section-title"><span class="num">2b</span> Acciones globales (sin plataforma)</div>
        <div class="ads-act-grid">${actGlobBtns}</div>

        <div class="ads-section-title"><span class="num">3</span> Contexto del cliente</div>
        <div class="ads-form-grid">
          <div><label class="ads-label">Cliente</label>
            <input class="ads-input" id="ads-client" placeholder="ej. ANIMUS Lab" /></div>
          <div><label class="ads-label">Industria</label>
            <select class="ads-input" id="ads-industry">
              <option value="">Seleccionar...</option>
              <option>SaaS</option><option>E-commerce</option><option>Skincare/Cosmetica</option>
              <option>Local Service</option><option>B2B Enterprise</option><option>Info Products</option>
              <option>Mobile App</option><option>Real Estate</option><option>Healthcare</option>
              <option>Finance</option><option>Agency</option><option>Other</option>
            </select></div>
          <div><label class="ads-label">Spend mensual (USD)</label>
            <input class="ads-input" id="ads-spend" type="number" placeholder="5000" /></div>
          <div><label class="ads-label">Objetivo principal</label>
            <select class="ads-input" id="ads-goal">
              <option value="">Seleccionar...</option>
              <option>Ventas / Revenue</option><option>Leads / Demos</option>
              <option>App Installs</option><option>Calls</option><option>Brand</option>
            </select></div>
        </div>

        <div class="ads-section-title"><span class="num">4</span> Datos / contexto (CSV, metricas, descripcion)</div>
        <textarea class="ads-textarea" id="ads-payload"
          placeholder="Pega aqui datos de la cuenta. Ejemplos:&#10;&#10;- Export CSV de Google Ads (campañas, keywords, search terms)&#10;- Screenshot de Events Manager / Pixel health&#10;- Metricas: CTR, CPC, CVR, CPA, ROAS, impressions, spend&#10;- URL de la landing page o competidor&#10;- Brief del cliente: 'tenemos 3 campañas activas, gastamos $5k/mes en Meta, CPA $35, target $20...'&#10;&#10;Mientras mas contexto, mejor el analisis."></textarea>

        <button class="ads-run-btn" id="ads-run-btn" onclick="runAdsSkill()">
          <span id="ads-run-icon">&#x26A1;</span>
          <span id="ads-run-lbl">Ejecutar analisis</span>
        </button>
      </div>

      <div>
        <div class="ads-section-title"><span class="num">&#x2728;</span> Resultado</div>
        <div id="ads-output-wrap" class="ads-output" style="min-height:300px;">
          <div style="text-align:center;padding:60px 20px;color:var(--cx-text-mute);">
            <div style="font-size:48px;margin-bottom:12px;">&#x1F680;</div>
            <div style="font-size:14px;font-weight:600;color:var(--cx-text-mute);">Configura los pasos 1-4 y ejecuta</div>
            <div style="font-size:11px;margin-top:8px;">El reporte aparecera aqui en markdown</div>
          </div>
        </div>

        <div class="ads-history">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div style="font-size:12px;font-weight:700;color:var(--cx-text-mute);">&#x23F1; Historial reciente</div>
            <button class="btn btn-outline btn-sm" onclick="loadAdsHistory()">Actualizar</button>
          </div>
          <div id="ads-history-list" style="font-size:12px;color:var(--cx-text-mute);">Cargando...</div>
        </div>
      </div>
    </div>
  `;

  selectAdsPlatform('meta');
  selectAdsAction('audit', false);
  loadAdsHistory();
}

function selectAdsPlatform(id) {
  ADS_STATE.platform = id;
  document.querySelectorAll('#tab-ads .ads-plat-card').forEach(el => {
    el.classList.toggle('active', el.dataset.platform === id);
  });
}
function selectAdsAction(id, isGlobal) {
  ADS_STATE.action = id;
  document.querySelectorAll('#tab-ads .ads-act-card').forEach(el => {
    el.classList.toggle('active', el.dataset.action === id);
  });
  if (isGlobal) {
    document.querySelectorAll('#tab-ads .ads-plat-card').forEach(el => el.style.opacity = '0.4');
  } else {
    document.querySelectorAll('#tab-ads .ads-plat-card').forEach(el => el.style.opacity = '1');
  }
}

// Markdown -> HTML minimal renderer (sin dependencias externas)
function adsRenderMarkdown(md) {
  if (!md) return '';
  let html = md;
  html = html.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g,(m,l,c)=>'<pre><code>'+c.trim()+'</code></pre>');
  html = html.replace(/`([^`\n]+)`/g,'<code>$1</code>');
  html = html.replace(/^### (.+)$/gm,'<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm,'<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm,'<h1>$1</h1>');
  html = html.replace(/^&gt; (.+)$/gm,'<blockquote>$1</blockquote>');
  html = html.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
  html = html.replace(/(?<!\*)\*([^\*\n]+)\*(?!\*)/g,'<em>$1</em>');
  // tables
  html = html.replace(/(\|.+\|\n\|[\s\-:|]+\|\n(?:\|.+\|\n?)+)/g,(tbl)=>{
    const lines = tbl.trim().split('\n');
    const head = lines[0].split('|').slice(1,-1).map(s=>s.trim());
    const rows = lines.slice(2).map(r=>r.split('|').slice(1,-1).map(s=>s.trim()));
    let h='<table><thead><tr>'+head.map(c=>'<th>'+c+'</th>').join('')+'</tr></thead><tbody>';
    rows.forEach(r=>h+='<tr>'+r.map(c=>'<td>'+c+'</td>').join('')+'</tr>');
    return h+'</tbody></table>';
  });
  // lists
  html = html.replace(/(^- .+(?:\n- .+)+)/gm,(m)=>'<ul>'+m.split('\n').map(l=>'<li>'+l.replace(/^- /,'')+'</li>').join('')+'</ul>');
  html = html.replace(/(^\d+\. .+(?:\n\d+\. .+)+)/gm,(m)=>'<ol>'+m.split('\n').map(l=>'<li>'+l.replace(/^\d+\. /,'')+'</li>').join('')+'</ol>');
  // paragraphs (lineas que no son ya bloque)
  html = html.split(/\n{2,}/).map(p=>{
    if (/^<(h[1-6]|ul|ol|pre|table|blockquote)/.test(p.trim())) return p;
    return p.trim() ? '<p>'+p.replace(/\n/g,'<br>')+'</p>' : '';
  }).join('\n');
  return html;
}

async function runAdsSkill() {
  if (ADS_STATE.running) return;
  const isGlobal = ['competitor','landing','test','dna'].includes(ADS_STATE.action);
  const platform = isGlobal ? null : ADS_STATE.platform;
  const action = ADS_STATE.action;
  const payload = (document.getElementById('ads-payload')||{}).value || '';
  if (payload.trim().length < 10) {
    alert('Pega al menos 10 caracteres de datos o contexto.');
    return;
  }
  const business_context = {
    client_name: (document.getElementById('ads-client')||{}).value || '',
    industry:    (document.getElementById('ads-industry')||{}).value || '',
    monthly_spend_usd: parseInt((document.getElementById('ads-spend')||{}).value || '0',10) || null,
    goal:        (document.getElementById('ads-goal')||{}).value || '',
    active_platforms: platform ? [platform] : [],
  };

  ADS_STATE.running = true;
  const btn = document.getElementById('ads-run-btn');
  btn.disabled = true;
  document.getElementById('ads-run-icon').innerHTML = '&#x231B;';
  document.getElementById('ads-run-lbl').textContent = 'Analizando con Claude...';

  const out = document.getElementById('ads-output-wrap');
  out.innerHTML = `
    <div class="ads-loader">
      <div class="ring"></div>
      <div class="lbl">Claude esta procesando ${(platform||'').toUpperCase()} ${action.toUpperCase()}</div>
      <div class="sub">Cargando skills (~30k tokens) + analizando tus datos. Suele tardar 20-40s.</div>
    </div>`;

  try {
    const r = await fetch('/api/marketing/ads/run', _fetchOpts('POST', {platform, action, payload, business_context}));
    const data = await r.json();
    if (!r.ok || data.error) {
      out.innerHTML = `<div style="color:#dc2626;font-weight:700;font-size:14px;">&#x26A0; Error</div>
        <div style="color:#dc2626;font-size:12px;margin-top:8px;">${data.error||'Fallo desconocido'}</div>
        ${data.detail ? '<pre style="background:var(--cx-bg-alt);padding:10px;border-radius:8px;font-size:11px;color:var(--cx-text-mute);margin-top:10px;overflow-x:auto;">'+data.detail+'</pre>' : ''}`;
    } else {
      const cacheTag = data.cache_read_tokens ? ` <span style="color:#16a34a;">cache hit ${data.cache_read_tokens.toLocaleString()} tok</span>` : '';
      out.innerHTML = adsRenderMarkdown(data.text || '(sin texto)') +
        `<div class="ads-meta">
          <span>&#x1F916; ${data.model||'?'}</span>
          <span>&#x21AA; in: ${(data.input_tokens||0).toLocaleString()}</span>
          <span>&#x21AA; out: ${(data.output_tokens||0).toLocaleString()}</span>
          ${cacheTag ? '<span>'+cacheTag+'</span>' : ''}
          <span>&#x1F4B5; ~$${(data.cost_usd_estimate||0).toFixed(4)}</span>
        </div>`;
      loadAdsHistory();
    }
  } catch (e) {
    out.innerHTML = `<div style="color:#dc2626;">Error de red: ${e.message}</div>`;
  } finally {
    ADS_STATE.running = false;
    btn.disabled = false;
    document.getElementById('ads-run-icon').innerHTML = '&#x26A1;';
    document.getElementById('ads-run-lbl').textContent = 'Ejecutar analisis';
  }
}

async function loadAdsHistory() {
  const wrap = document.getElementById('ads-history-list');
  if (!wrap) return;
  try {
    const r = await fetch('/api/marketing/ads/log');
    const list = await r.json();
    if (!Array.isArray(list) || list.length === 0) {
      wrap.innerHTML = '<div style="color:var(--cx-text-mute);padding:8px;">Sin ejecuciones aun.</div>';
      return;
    }
    wrap.innerHTML = list.slice(0,12).map(x => {
      const cost = x.cost_usd != null ? '$'+Number(x.cost_usd).toFixed(3) : '';
      const plat = x.platform ? x.platform.toUpperCase() : 'GLOBAL';
      return `<div class="ads-history-item" onclick="loadAdsLogDetail(${x.id})">
        <span style="background:#4c1d95;color:#fff;font-size:10px;font-weight:700;padding:2px 7px;border-radius:6px;">${plat}</span>
        <span style="color:#6d28d9;font-weight:600;">${x.accion||''}</span>
        <span style="color:var(--cx-text-soft);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${x.client||x.preview||''}</span>
        <span style="color:var(--cx-text-mute);font-size:10px;">${(x.fecha||'').slice(5,16)}</span>
        <span style="color:#16a34a;font-size:10px;">${cost}</span>
      </div>`;
    }).join('');
  } catch (e) {
    wrap.innerHTML = '<div style="color:#dc2626;">Error: '+e.message+'</div>';
  }
}

async function loadAdsLogDetail(id) {
  const out = document.getElementById('ads-output-wrap');
  out.innerHTML = `<div class="ads-loader"><div class="ring"></div><div class="lbl">Cargando #${id}</div></div>`;
  try {
    const r = await fetch('/api/marketing/ads/log/'+id);
    const data = await r.json();
    if (!r.ok) {
      out.innerHTML = '<div style="color:#dc2626;">No se pudo cargar</div>';
      return;
    }
    out.innerHTML = adsRenderMarkdown(data.text || '(vacio)') +
      `<div class="ads-meta">
        <span>&#x1F516; #${data.id}</span>
        <span>${(data.platform||'global').toUpperCase()} / ${data.accion}</span>
        <span>&#x1F464; ${data.ejecutado_por||'?'}</span>
        <span>&#x1F4C5; ${data.fecha||''}</span>
        <span>&#x1F4B5; ~$${(data.cost_usd||0).toFixed(4)}</span>
      </div>`;
  } catch (e) {
    out.innerHTML = '<div style="color:#dc2626;">Error: '+e.message+'</div>';
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// INIT
// ──────────────────────────────────────────────────────────────────────────────
loadDashboard();
</script>

<!-- Widget "Mi contraseña" removido 24-may-2026 · vive en /modulos y /hub -->
</body>
</html>"""
