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
.badge-red{background:var(--cx-danger-pale);color:var(--cx-danger-text);border:1px solid var(--cx-danger);}
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
.alert-error{background:var(--cx-danger-pale);color:var(--cx-danger-text);border:1px solid var(--cx-danger);}
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
.pill-shopify{background:var(--cx-success-pale);color:var(--cx-success-text);border:1px solid var(--cx-hairline);}
.pill-ghl{background:var(--cx-primary-soft);color:var(--cx-primary-text);border:1px solid var(--cx-primary-dark);}
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
      <input class="search-box" id="inf-search" placeholder="Buscar nombre, @usuario, nicho..." oninput="infBuscar()">
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

  <!-- ── DIRECTORIO DE CREADORES ────────────────────────────────────────────────
       Sebastián 27-jul: "cada influencer puede ser cada mes un pago diferente,
       entonces debería haber un directorio perfecto y premium". El centro de pagos
       ordena por FECHA (qué pago sigue); esto ordena por PERSONA: cuánto le llevamos
       puesto, con qué ritmo mes a mes, y qué devolvió. -->
  <style>
    .dir-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px;}
    .dir-card{background:var(--cx-card,#fff);border:1px solid var(--cx-border,#ececf1);border-radius:16px;padding:16px 18px 14px;box-shadow:0 2px 14px rgba(15,23,42,.05);transition:box-shadow .18s,transform .18s;position:relative;overflow:hidden;}
    .dir-card:hover{box-shadow:0 8px 28px rgba(15,23,42,.11);transform:translateY(-2px);}
    .dir-card::before{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--dir-ac,var(--cx-primary));}
    .dir-top{display:flex;align-items:center;gap:11px;margin-bottom:12px;}
    .dir-ini{width:42px;height:42px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:16px;color:#fff;background:var(--cx-primary-grad,var(--cx-primary));flex:0 0 auto;letter-spacing:-.02em;}
    .dir-nom{font-weight:800;font-size:15px;color:var(--cx-text);letter-spacing:-.01em;line-height:1.2;}
    .dir-sub{font-size:11px;color:var(--cx-text-mute);margin-top:2px;}
    .dir-chip{display:inline-block;font-size:10px;font-weight:800;padding:2px 8px;border-radius:999px;letter-spacing:.02em;}
    .dir-kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px;}
    .dir-k{background:var(--cx-bg-alt,#f8f8fb);border-radius:10px;padding:8px 9px;}
    .dir-k .lbl{font-size:9.5px;color:var(--cx-text-mute);font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
    .dir-k .val{font-size:15px;font-weight:800;color:var(--cx-text);margin-top:2px;letter-spacing:-.02em;}
    .dir-bars{display:flex;align-items:flex-end;gap:3px;height:42px;margin:2px 0 8px;}
    .dir-bar{flex:1;border-radius:3px 3px 0 0;min-height:2px;background:var(--cx-border,#e6e6ee);position:relative;}
    .dir-bar.on{background:var(--cx-primary);}
    .dir-bar.pend{background:var(--cx-warn,#f59e0b);}
    .dir-meses{display:flex;gap:3px;font-size:8.5px;color:var(--cx-text-mute);margin-bottom:10px;}
    .dir-meses span{flex:1;text-align:center;}
    .dir-foot{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:11px;color:var(--cx-text-mute);border-top:1px solid var(--cx-hairline,#f0f0f5);padding-top:9px;}
    .dir-det{margin-top:12px;border-top:1px dashed var(--cx-border,#e6e6ee);padding-top:10px;}
    .dir-det table{width:100%;font-size:11.5px;border-collapse:collapse;}
    .dir-det td{padding:5px 4px;border-bottom:1px solid var(--cx-hairline,#f4f4f8);vertical-align:top;}
    @media (max-width:768px){ .dir-grid{grid-template-columns:1fr;} }
  </style>

  <div class="card" style="margin-bottom:16px;padding:18px 20px;">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;margin-bottom:14px;">
      <div>
        <div style="font-size:16px;font-weight:800;color:var(--cx-text);letter-spacing:-.01em;">&#x1F4D2; Directorio de creadores</div>
        <div style="font-size:12px;color:var(--cx-text-mute);margin-top:3px;">Cuánto le llevamos puesto a cada uno, con qué ritmo mes a mes, y qué devolvió. Click en una tarjeta para ver pago por pago.</div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <div style="position:relative;">
          <span style="position:absolute;left:11px;top:50%;transform:translateY(-50%);font-size:13px;opacity:.5;pointer-events:none;">&#x1F50D;</span>
          <input id="dir-buscar" type="search" placeholder="Buscar creador por nombre..." oninput="dirBuscarLocal()"
                 style="background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:999px;padding:8px 14px 8px 32px;color:var(--cx-text);font-size:12.5px;min-width:230px;outline:none;">
        </div>
        <select id="dir-orden" onchange="renderDirectorio()" style="background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:8px;padding:7px 11px;color:var(--cx-text);font-size:12px;font-weight:600;">
          <option value="alfa" selected>Orden alfabético</option>
          <option value="plata">Más pagado primero</option>
          <option value="pendiente">Con pendiente primero</option>
          <option value="reciente">Pago más reciente</option>
        </select>
        <select id="dir-meses" onchange="loadDirectorio()" style="background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:8px;padding:7px 11px;color:var(--cx-text);font-size:12px;font-weight:600;">
          <option value="6">Últimos 6 meses</option>
          <option value="12" selected>Últimos 12 meses</option>
          <option value="24">Últimos 24 meses</option>
        </select>
        <button class="btn btn-primary btn-sm" onclick="openInfluencerModal()">+ Creador</button>
        <button class="btn btn-outline btn-sm" onclick="loadDirectorio()" title="Refrescar directorio">&#x21BB;</button>
      </div>
    </div>
    <div id="dir-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px;"></div>
    <div id="dir-filtros" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px;"></div>
    <div id="dir-grid" class="dir-grid"><div style="grid-column:1/-1;text-align:center;color:var(--cx-text-mute);padding:26px;"><span class="spin"></span></div></div>
  </div>

  <details class="card" style="margin-bottom:16px;">
    <summary style="cursor:pointer;list-style:none;font-size:13px;font-weight:700;color:var(--cx-text);">&#x2699; Catálogo y edición <span style="font-weight:500;color:var(--cx-text-mute);font-size:11.5px;">- datos de contacto, banco, cupón, alta y baja</span></summary>
    <div style="margin-top:14px;">

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
    </div>
  </details><!-- /Catálogo y edición -->
  </div><!-- /inf-view-creadores -->
</div>

<!-- ARRANQUE DE LA PÁGINA
     Acá vivía un bloque de JS heredado que 100 ms después de cargar llamaba a
     `switchTab('dashboard')`. Cuando saqué la pestaña Dashboard, ese tab dejó de
     existir: switchTab le quitaba `active` a TODOS los paneles, no encontraba
     `tab-dashboard`, y la pantalla se quedaba EN BLANCO hasta que uno hacía click
     en la pestaña. Además, como loadTab nunca corría, tampoco se cargaban los datos.
     Ahora la única pestaña se abre sola. -->
<script>
document.addEventListener('DOMContentLoaded', function(){
  if(typeof switchTab === 'function') switchTab('influencers');
});
</script>

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

<!-- ═══════════════════════════════════════════════════════════════════════════
     MODALES
     RESTAURADOS 27-jul. Al reducir Marketing a pagos (f977be35) me llevé por
     delante los 8 modales de la página, pero dejé vivos los botones que los
     abren: "+ Nuevo Influencer", "Solicitar pago", "Dar de baja", "Gestionar
     pagos" y el historial quedaron tirando `getElementById(...) es null` -- o
     sea, botones que desde afuera "no hacen nada". Solicitar pago es JUSTO el
     único flujo que Sebastián dijo que este módulo tiene que tener.
     Vuelven los 5 que pertenecen a pagos y creadores; los de campañas,
     contenido y agentes IA NO vuelven (esas features sí se retiraron).
     ══════════════════════════════════════════════════════════════════════ -->
<div class="modal-bg" id="modal-historial">
  <div class="modal" style="max-width:680px;max-height:85vh;overflow-y:auto;">
    <div class="modal-title" id="hist-title">Historial</div>
    <button class="modal-close" onclick="closeModal('modal-historial')">&times;</button>
    <div id="hist-content" style="margin-top:8px;"></div>
  </div>
</div>

<!-- Modal: Nueva Campaña -->

<!-- Ficha del creador · en pop-up, no dentro de la tarjeta: apretada en una columna de
     340px no se podía leer y empujaba toda la grilla hacia abajo. -->
<div class="modal-bg" id="modal-ficha-creador" onclick="if(event.target===this)dirCerrarFicha()">
  <div class="modal" style="max-width:780px;max-height:88vh;overflow:auto;">
    <div class="modal-hdr" style="position:sticky;top:0;background:var(--cx-card,#fff);z-index:2;">
      <div class="modal-title">&#x1F464; Ficha del creador</div>
      <button class="modal-close" onclick="dirCerrarFicha()">&times;</button>
    </div>
    <div id="dir-ficha-body"></div>
  </div>
</div>

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
      <div class="form-group"><label>Email <span style="color:var(--cx-danger-text);">*</span> <span style="font-weight:400;color:var(--cx-text-mute);font-size:11px;">· para enviarle la factura cuando se le pague</span></label><input type="email" id="inf-email" placeholder="correo@ejemplo.com"></div>
      <div class="form-group"><label>Teléfono</label><input id="inf-tel" placeholder="+57..."></div>
    </div>
    <div class="form-row full">
      <div class="form-group"><label>Notas</label><textarea id="inf-notas" placeholder="Observaciones..."></textarea></div>
    </div>
    <div style="border-top:1px solid var(--cx-border);margin:10px 0 6px;padding-top:10px;">
      <div style="font-size:11px;font-weight:700;color:var(--cx-primary-text);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">🏦 Datos Bancarios</div>
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
    <div style="border-top:1px solid var(--cx-border);margin:10px 0 6px;padding-top:10px;">
      <div style="font-size:11px;font-weight:700;color:var(--cx-warn-text);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">⏰ Ciclo de pago</div>
      <div class="form-row">
        <div class="form-group">
          <label>Frecuencia con la que se le paga</label>
          <select id="inf-ciclo-pago" style="background:var(--cx-bg-alt);color:var(--cx-text);border:1px solid var(--cx-border);border-radius:6px;padding:8px;width:100%;">
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
    <div style="border-top:1px solid var(--cx-border);margin:10px 0 6px;padding-top:10px;">
      <div style="font-size:11px;font-weight:700;color:var(--cx-success-text);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">🎟️ Atribución de ventas</div>
      <div class="form-row full">
        <div class="form-group">
          <label>Discount code de Shopify</label>
          <input id="inf-discount-code" placeholder="ANIMUS_LAURA10" style="text-transform:uppercase;font-family:monospace;">
          <div style="font-size:10px;color:var(--cx-text-mute);margin-top:4px;line-height:1.4;">
            Cuando un cliente use este código en Shopify, la venta se atribuye automáticamente a este influencer.
            Convención: <code style="background:var(--cx-bg-alt);padding:1px 6px;border-radius:4px;color:var(--cx-success-text);">ANIMUS_NOMBRE_PCT</code> (ej: ANIMUS_LAURA10).
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
      <div class="modal-title">⚙ Gestionar pagos · <span id="gp-inf-nombre" style="color:var(--cx-primary-text);"></span></div>
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
    <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:14px;border-top:1px solid var(--cx-border);padding-top:12px;">
      <button class="btn btn-outline" onclick="closeModal('modal-gestionar-pagos')">Cerrar</button>
    </div>
  </div>
</div>

<div class="modal-bg" id="modal-inf-pago">
  <div class="modal" style="max-width:580px;">
    <div class="modal-hdr">
      <div class="modal-title">&#x1F4B8; Solicitar Pago</div>
      <button class="modal-close" onclick="closeModal('modal-inf-pago')">&times;</button>
    </div>
    <input type="hidden" id="pago-inf-id">
    <div style="display:flex;align-items:center;gap:12px;background:var(--cx-bg-alt);border-radius:12px;padding:12px 14px;margin-bottom:16px;">
      <div style="width:40px;height:40px;border-radius:12px;background:var(--cx-primary-grad,var(--cx-primary));flex:0 0 auto;display:flex;align-items:center;justify-content:center;font-size:18px;">&#x1F4B8;</div>
      <div style="min-width:0;">
        <div style="font-size:10px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.05em;">Se le va a pagar a</div>
        <div id="pago-inf-nombre" style="font-weight:800;font-size:16px;color:var(--cx-text);letter-spacing:-.01em;margin-top:1px;"></div>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Valor a pagar (COP) *</label><input type="number" id="pago-valor" placeholder="0"></div>
      <div class="form-group"><label>Concepto</label><input id="pago-concepto" placeholder="Post + Story / Reel..."></div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>&#128226; Fecha de publicaci&oacute;n <span style="color:var(--cx-danger-text);">*</span></label>
        <input type="date" id="pago-fecha-contenido" onchange="recalcularVencePagoInf()" title="Día real en que el creador publicó el contenido. La promesa de pago (30 días) se cuenta desde esta fecha.">
      </div>
      <div class="form-group">
        <label>Vence pago (auto)</label>
        <!-- El color del texto era `#c7d2fe`, pensado para caja OSCURA; sobre el lavanda
             claro quedaba lavanda-sobre-lavanda, ilegible (M104). -->
        <input id="pago-vence" disabled style="background:var(--cx-primary-soft);color:var(--cx-primary-text);font-weight:700;" placeholder="-">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group" style="flex:1;"><label>&#128221; De qu&eacute; trat&oacute; el contenido <span style="color:var(--cx-danger-text);">*</span></label><input id="pago-entregable" placeholder="Ej: 1 Reel + 2 Stories del s&eacute;rum vitamina C"></div>
    </div>
    <div class="form-row">
      <div class="form-group" style="flex:1;"><label>&#128279; Link al post (opcional)</label><input id="pago-link-post" placeholder="https://instagram.com/p/..."></div>
    </div>
    <div style="background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:8px;padding:12px;margin:8px 0;font-size:12px;color:var(--cx-text-mute);">
      <div style="font-weight:700;color:var(--cx-primary-text);margin-bottom:6px;">&#x1F3E6; Datos bancarios</div>
      <div id="pago-banco-preview" style="line-height:1.8;"></div>
    </div>
    <!-- Qué pasa después de enviar la solicitud.
         El texto decía "/compras → tab Influencers": esa sub-vista se retiró el 27-jul y el
         pago pasó a decidirse en Centro de Mando. Una instrucción que manda a un lugar que ya
         no existe es peor que no tenerla. Y los colores (#c7d2fe sobre lavanda claro) venían
         de una caja oscura: quedaban lavanda sobre lavanda, ilegibles (M104). -->
    <div style="background:var(--cx-primary-soft);border:1px solid var(--cx-primary);border-radius:10px;padding:11px 13px;margin:10px 0;font-size:11.5px;color:var(--cx-text);line-height:1.55;">
      <b style="color:var(--cx-primary-text);">📌 Qué pasa después</b><br>
      La solicitud le llega a <b>Sebastián</b> en su Centro de Mando &rarr; pestaña <b>Pagos</b>,
      donde la paga o la rechaza. Si la rechaza, acá vas a ver el motivo.
      Cuando se pague recibís <b>email automático</b>. Catalina no participa en este flujo.
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
      <select id="baja-motivo-tipo" style="width:100%;background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:6px;padding:8px;color:var(--cx-text);">
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
      <textarea id="baja-observacion" rows="3" placeholder="Detalles adicionales..." style="width:100%;background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:6px;padding:8px;color:var(--cx-text);resize:vertical;"></textarea>
    </div>
    <div style="background:var(--cx-warn-pale);border:1px solid var(--cx-hairline);border-radius:8px;padding:10px;font-size:12px;color:var(--cx-warn-text);margin-bottom:12px;">
      &#x26A0;&#xFE0F; El influencer quedará en estado <b>Baja</b> y visible en el historial. Podrá reactivarse en cualquier momento.
    </div>
    <div style="display:flex;gap:10px;justify-content:flex-end;">
      <button class="btn btn-outline" onclick="closeModal('modal-dar-baja')">Cancelar</button>
      <button class="btn btn-danger" onclick="confirmarDarDeBaja()">Dar de Baja</button>
    </div>
  </div>
</div>

<!-- Modal: Nuevo Contenido -->

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






// AUDIT 26-may · cache global de campañas
var CAMPANAS_LIST = [];





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


// ─── Centro de pagos por estados (Sebastián 13-jul) ───────────────────────────
// ═══════════════════════════════════════════════════════════════════════════════
// DIRECTORIO DE CREADORES
// Sebastian 27-jul: "cada influencer puede ser cada mes un pago diferente, entonces
// deberia haber un directorio perfecto y premium". Todo lo que se ve aca esta DERIVADO
// de los pagos y de las ventas: no hay ningun campo que alguien tenga que acordarse de
// actualizar, asi que no puede quedar viejo.
window._DIR_DATA = null;
window._DIR_FILTRO = 'todos';

function _dirMoneda(n){
  n = Number(n||0);
  if(n >= 1000000) return '$' + (n/1000000).toFixed(n >= 10000000 ? 0 : 1) + 'M';
  if(n >= 1000)    return '$' + Math.round(n/1000) + 'k';
  return '$' + n.toLocaleString('es-CO');
}
function _dirMesCorto(m){
  var M=['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
  var p=(m||'').split('-'); if(p.length<2) return m||'';
  return M[parseInt(p[1],10)-1] || '';
}

function infBuscar(){
  // La busqueda alimenta el catalogo Y el directorio. El directorio recorre 12 meses de
  // pagos, asi que va con espera: disparar un fetch por tecla lo convertiria en el
  // endpoint mas llamado de la app sin que nadie lo pidiera.
  loadInfluencers();
  clearTimeout(window._DIR_BUSCA_T);
  window._DIR_BUSCA_T=setTimeout(function(){
    if(window._DIR_DATA) loadDirectorio();
  }, 400);
}

async function loadDirectorio(){
  var grid=document.getElementById('dir-grid'); if(!grid) return;
  var meses=(document.getElementById('dir-meses')||{}).value || '12';
  var q=((document.getElementById('inf-search')||{}).value || '').trim();
  grid.innerHTML='<div style="grid-column:1/-1;text-align:center;color:var(--cx-text-mute);padding:26px;"><span class="spin"></span></div>';
  try{
    var r=await fetch('/api/marketing/directorio-creadores?meses='+encodeURIComponent(meses)
                      +'&q='+encodeURIComponent(q), {credentials:'same-origin'});
    var js=await r.json();
    if(!r.ok || js.error){ throw new Error(js.error || ('HTTP '+r.status)); }
    window._DIR_DATA=js;
    renderDirectorio();
  }catch(e){
    grid.innerHTML='<div style="grid-column:1/-1;text-align:center;color:var(--cx-danger-text);padding:22px;font-size:13px;">No se pudo cargar el directorio: '+_escHtml(e.message)+'</div>';
  }
}

function dirFiltro(f){ window._DIR_FILTRO=f; renderDirectorio(); }

function renderDirectorio(){
  var js=window._DIR_DATA; if(!js) return;
  var k=js.kpis||{};
  var kw=document.getElementById('dir-kpis');
  if(kw){
    // El ROI global va en gris cuando no hay con que calcularlo: un "0%" ahi se leeria
    // como "no rindio", que es distinto de "todavia no se midio".
    var roi = (k.roi_global_pct===null || k.roi_global_pct===undefined)
      ? '<span style="color:var(--cx-text-mute)">sin dato</span>'
      : (k.roi_global_pct>=0?'+':'') + k.roi_global_pct + '%';
    var tarjetas=[
      ['Creadores con pago', (k.con_pago||0)+' <span style="font-size:12px;font-weight:600;color:var(--cx-text-mute)">de '+(k.creadores||0)+'</span>', 'var(--cx-primary-text)'],
      ['Pagado en el periodo', _dirMoneda(k.pagado_total), 'var(--cx-text)'],
      ['Por pagar', _dirMoneda(k.pendiente_total)+' <span style="font-size:12px;font-weight:600;color:var(--cx-text-mute)">('+(k.n_pendientes||0)+')</span>', (k.pendiente_total>0?'var(--cx-warn-text)':'var(--cx-text-mute)')],
      ['Venta atribuida', _dirMoneda(k.revenue_total), 'var(--cx-success-text)'],
      ['Retorno global', roi, 'var(--cx-success-text)'],
      ['Sin fecha de publicacion', (k.sin_publicacion||0), (k.sin_publicacion>0?'var(--cx-danger-text)':'var(--cx-text-mute)')]
    ];
    kw.innerHTML=tarjetas.map(function(t){
      return '<div style="background:var(--cx-bg-alt,#f8f8fb);border-radius:12px;padding:11px 13px;">'
        +'<div style="font-size:10px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.04em;">'+t[0]+'</div>'
        +'<div style="font-size:19px;font-weight:800;margin-top:3px;letter-spacing:-.02em;color:'+t[2]+'">'+t[1]+'</div>'
      +'</div>';
    }).join('');
  }

  var todos=js.creadores||[];
  var conts={
    todos:      todos.length,
    con_pago:   todos.filter(function(x){return x.n_pagos>0;}).length,
    pendiente:  todos.filter(function(x){return x.n_pendientes>0;}).length,
    revisar:    todos.filter(function(x){return x.sin_publicacion>0;}).length,
    baja:       todos.filter(function(x){return (x.estado||'').toLowerCase()==='baja';}).length
  };
  var fw=document.getElementById('dir-filtros');
  if(fw){
    var defs=[['todos','Todos'],['con_pago','Con pago'],['pendiente','Con pendiente'],
              ['revisar','Sin fecha de publicacion'],['baja','Dados de baja']];
    fw.innerHTML=defs.map(function(d){
      var on=(window._DIR_FILTRO===d[0]);
      return '<button onclick="dirFiltro(\''+d[0]+'\')" style="border:1px solid '+(on?'var(--cx-primary)':'var(--cx-border)')
        +';background:'+(on?'var(--cx-primary)':'transparent')+';color:'+(on?'#fff':'var(--cx-text-mute)')
        +';border-radius:999px;padding:5px 13px;font-size:11.5px;font-weight:700;cursor:pointer;">'
        +d[1]+' <span style="opacity:.75">'+(conts[d[0]]||0)+'</span></button>';
    }).join('');
  }

  var f=window._DIR_FILTRO;
  // La busqueda es LOCAL (sobre lo ya traido): filtrar mientras se escribe no puede costar
  // un viaje al servidor por tecla, y el directorio entero ya esta en memoria.
  var q=((document.getElementById('dir-buscar')||{}).value||'').trim().toLowerCase();
  var lista=todos.filter(function(x){
    if(q){
      var heno=((x.nombre||'')+' '+(x.usuario_red||'')+' '+(x.discount_code||'')+' '
                +(x.ciudad||'')+' '+(x.nicho||'')).toLowerCase();
      if(heno.indexOf(q)<0) return false;
    }
    if(f==='con_pago')  return x.n_pagos>0;
    if(f==='pendiente') return x.n_pendientes>0;
    if(f==='revisar')   return x.sin_publicacion>0;
    if(f==='baja')      return (x.estado||'').toLowerCase()==='baja';
    return true;
  });
  // El backend ordena por plata puesta; el orden que se VE lo elige el usuario. Alfabetico
  // es el default: con 751 creadores, buscar a alguien por nombre es lo mas frecuente.
  var ord=((document.getElementById('dir-orden')||{}).value)||'alfa';
  var _cmpNom=function(a,b){ return String(a.nombre||'').localeCompare(String(b.nombre||''),'es',{sensitivity:'base'}); };
  lista=lista.slice();
  if(ord==='alfa')          lista.sort(_cmpNom);
  else if(ord==='plata')    lista.sort(function(a,b){ return (b.pagado-a.pagado)||_cmpNom(a,b); });
  else if(ord==='pendiente')lista.sort(function(a,b){ return (b.pendiente-a.pendiente)||_cmpNom(a,b); });
  else if(ord==='reciente') lista.sort(function(a,b){
    var fa=(a.ultimo_pago&&a.ultimo_pago.fecha)||'', fb=(b.ultimo_pago&&b.ultimo_pago.fecha)||'';
    return fb.localeCompare(fa)||_cmpNom(a,b);
  });
  window._DIR_VIS=lista;

  var grid=document.getElementById('dir-grid');
  if(!lista.length){
    grid.innerHTML='<div style="grid-column:1/-1;text-align:center;color:var(--cx-text-mute);padding:26px;font-size:13px;">No hay creadores con ese filtro.</div>';
    return;
  }
  // Escala comun para las barras de TODAS las tarjetas: si cada una se normalizara
  // a su propio maximo, un creador de $100k y uno de $3M se verian iguales.
  var tope=1;
  lista.forEach(function(x){ (x.serie||[]).forEach(function(s){
    var v=(s.pagado||0)+(s.pendiente||0); if(v>tope) tope=v; }); });

  grid.innerHTML=lista.map(function(x,ix){ return _dirCard(x,ix,tope); }).join('');
}

function _dirCard(x, ix, tope){
  var esBaja=((x.estado||'').toLowerCase()==='baja');
  var ac = esBaja ? 'var(--cx-text-mute)'
         : (x.n_pendientes>0 ? 'var(--cx-warn)'
         : (x.n_pagos>0 ? 'var(--cx-primary)' : 'var(--cx-border)'));
  var ini=(x.nombre||'?').trim().charAt(0).toUpperCase();
  var chips='';
  if(esBaja){
    chips+='<span class="dir-chip" style="background:var(--cx-danger-pale,#fee2e2);color:var(--cx-danger-text);">Dado de baja</span> ';
  }
  if(x.n_pendientes>0){
    chips+='<span class="dir-chip" style="background:var(--cx-warn-pale,#fef3c7);color:var(--cx-warn-text);">'+x.n_pendientes+' por pagar</span> ';
  }
  if(x.sin_publicacion>0){
    chips+='<span class="dir-chip" style="background:var(--cx-danger-pale,#fee2e2);color:var(--cx-danger-text);" title="Pagos sin fecha de publicacion: no se pueden verificar">'+x.sin_publicacion+' sin publicacion</span> ';
  }
  if(x.discount_code){
    chips+='<span class="dir-chip" style="background:var(--cx-success-pale,#d1fae5);color:var(--cx-success-text);">'+_escHtml(x.discount_code)+'</span>';
  }

  // Retorno: sin codigo de descuento NO hay como atribuir venta -> "sin dato", no 0%.
  var retorno = (x.roi_pct===null || x.roi_pct===undefined)
    ? '<span style="color:var(--cx-text-mute);font-size:13px;">sin dato</span>'
    : '<span style="color:'+(x.roi_pct>=0?'var(--cx-success-text)':'var(--cx-danger-text)')+'">'
      +(x.roi_pct>=0?'+':'')+x.roi_pct+'%</span>';

  var barras=(x.serie||[]).map(function(s){
    var tot=(s.pagado||0)+(s.pendiente||0);
    var h=tot>0 ? Math.max(3, Math.round(tot/tope*40)) : 2;
    var cls=(s.pendiente>0 && !s.pagado) ? 'dir-bar pend' : (tot>0 ? 'dir-bar on' : 'dir-bar');
    return '<div class="'+cls+'" style="height:'+h+'px" title="'+s.mes+': '+_dirMoneda(tot)+'"></div>';
  }).join('');
  // Sólo se rotula 1 de cada 3 meses: con 12 barras las etiquetas se pisan.
  var rotulos=(x.serie||[]).map(function(s,i){
    return '<span>'+(((x.serie.length-1-i)%3===0)?_dirMesCorto(s.mes):'')+'</span>';
  }).join('');

  var ult = x.ultimo_pago
    ? ('Ultimo pago '+_escHtml((x.ultimo_pago.fecha||'').slice(0,10))
        + (x.dias_sin_pago!==null && x.dias_sin_pago!==undefined ? ' ('+x.dias_sin_pago+'d)' : '')
        + (x.ultimo_pago.entregable ? ' &middot; '+_escHtml(x.ultimo_pago.entregable.slice(0,42)) : ''))
    : 'Sin pagos en el periodo';

  return '<div class="dir-card" style="--dir-ac:'+ac+'">'
    +'<div class="dir-top">'
      +'<div class="dir-ini" style="'+(esBaja?'filter:grayscale(1);opacity:.6;':'')+'">'+_escHtml(ini)+'</div>'
      +'<div style="min-width:0;flex:1;">'
        +'<div class="dir-nom">'+_escHtml(x.nombre||'-')+'</div>'
        +'<div class="dir-sub">'+_escHtml(x.usuario_red? '@'+x.usuario_red : (x.red_social||''))
          +(x.ciudad? ' &middot; '+_escHtml(x.ciudad):'')+'</div>'
      +'</div>'
    +'</div>'
    +(chips? '<div style="margin-bottom:11px;display:flex;gap:5px;flex-wrap:wrap;">'+chips+'</div>' : '')
    +'<div class="dir-kpis">'
      +'<div class="dir-k"><div class="lbl">Pagado</div><div class="val">'+_dirMoneda(x.pagado)+'</div></div>'
      +'<div class="dir-k"><div class="lbl">Pagos</div><div class="val">'+(x.n_pagos||0)
        +(x.ticket_prom? '<span style="font-size:10px;font-weight:600;color:var(--cx-text-mute)"> &middot; '+_dirMoneda(x.ticket_prom)+' c/u</span>':'')+'</div></div>'
      +'<div class="dir-k"><div class="lbl">Retorno</div><div class="val">'+retorno+'</div></div>'
    +'</div>'
    +'<div class="dir-bars">'+barras+'</div>'
    +'<div class="dir-meses">'+rotulos+'</div>'
    +'<div class="dir-foot">'
      +'<span style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+ult+'</span>'
      +'<button onclick="dirToggle('+ix+')" id="dir-btn-'+ix+'" style="border:1px solid var(--cx-border);background:transparent;color:var(--cx-primary-text);border-radius:8px;padding:4px 11px;font-size:11px;font-weight:700;cursor:pointer;white-space:nowrap;">Ver ficha</button>'
    +'</div>'
  +'</div>';
}

function _dirDato(lbl, val, resalta){
  if(val===null || val===undefined || val==='' || val===0) return '';
  return '<div style="min-width:0;">'
    +'<div style="font-size:9.5px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.04em;">'+lbl+'</div>'
    +'<div style="font-size:12.5px;color:'+(resalta?'var(--cx-primary-text)':'var(--cx-text)')+';margin-top:1px;overflow:hidden;text-overflow:ellipsis;">'+_escHtml(String(val))+'</div>'
  +'</div>';
}

function dirCerrarFicha(){
  var m=document.getElementById('modal-ficha-creador');
  if(m) m.classList.remove('open');
}

function dirToggle(ix){
  // La ficha se abre en POP-UP, no dentro de la tarjeta: metida en una columna de 340px
  // quedaba apretada y empujaba toda la grilla (Sebastian 27-jul: "esto se ve horrible,
  // deberia abrirse como un pop up"). En el modal cabe la ficha completa y se lee.
  var x=(window._DIR_VIS||[])[ix];
  var box=document.getElementById('dir-ficha-body');
  var modal=document.getElementById('modal-ficha-creador');
  if(!x || !box || !modal) return;

  var esBaja=((x.estado||'').toLowerCase()==='baja');
  var datos=[
    _dirDato('Red',        (x.usuario_red? '@'+x.usuario_red : '') || x.red_social),
    _dirDato('Seguidores', x.seguidores? Number(x.seguidores).toLocaleString('es-CO') : ''),
    _dirDato('Engagement', x.engagement_rate? (x.engagement_rate+'%') : ''),
    _dirDato('Nicho',      x.nicho),
    _dirDato('Ciudad',     x.ciudad),
    _dirDato('Email',      x.email),
    _dirDato('Telefono',   x.telefono),
    _dirDato('Cupon',      x.discount_code, true),
    _dirDato('Tarifa',     x.tarifa? ('$'+Number(x.tarifa).toLocaleString('es-CO')) : ''),
    _dirDato('Ciclo',      x.ciclo_pago),
    _dirDato('Banco',      x.banco),
    _dirDato('Cuenta',     x.cuenta_bancaria),
    _dirDato('Tipo cuenta',x.tipo_cuenta),
    _dirDato('Cedula/NIT', x.cedula_nit),
    _dirDato('Venta atribuida', (x.revenue===null||x.revenue===undefined)? '' : ('$'+Number(x.revenue).toLocaleString('es-CO'))),
    _dirDato('Pedidos con su cupon', x.n_pedidos),
    _dirDato('Registrado', x.fecha_registro)
  ].filter(Boolean).join('');

  // Las acciones van por INDICE, no interpolando el nombre dentro del onclick: un creador
  // que se llame "D'Angelo" rompería el atributo (y peor, es dato de usuario dentro de HTML).
  var bot=function(accion,txt,estilo){
    return '<button onclick="event.stopPropagation();dirAccion('+ix+',\''+accion+'\')" style="'+estilo+'">'+txt+'</button>';
  };
  var neutro='border:1px solid var(--cx-border);background:transparent;color:var(--cx-text);border-radius:8px;padding:6px 13px;font-size:11.5px;font-weight:700;cursor:pointer;';
  var acciones='<div style="display:flex;gap:7px;flex-wrap:wrap;margin:12px 0 4px;">'
    + bot('editar','&#9998; Editar', neutro)
    + (esBaja? '' : bot('pago','&#128176; Solicitar pago',
        'border:none;background:var(--cx-primary-grad,var(--cx-primary));color:#fff;border-radius:8px;padding:6px 13px;font-size:11.5px;font-weight:700;cursor:pointer;'))
    + bot('gestionar','Gestionar pagos', neutro)
    + (esBaja? '' : bot('baja','Dar de baja',
        'border:1px solid var(--cx-danger);background:transparent;color:var(--cx-danger-text);border-radius:8px;padding:6px 13px;font-size:11.5px;font-weight:700;cursor:pointer;'))
  +'</div>';

  var motivo = esBaja && x.motivo_baja
    ? '<div style="background:var(--cx-danger-pale,#fee2e2);color:var(--cx-danger-text);border-radius:9px;padding:8px 11px;font-size:11.5px;margin-bottom:10px;">Baja'
        +(x.fecha_baja? ' el '+_escHtml(x.fecha_baja.slice(0,10)) : '')+': '+_escHtml(x.motivo_baja)+'</div>'
    : '';

  var det=x.detalle||[];
  var tabla = det.length
    ? '<div style="font-size:10px;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.04em;margin:12px 0 4px;">Pagos del periodo ('+det.length+')</div>'
      +'<table>'+det.map(function(d){
        var pagado=(d.estado==='Pagada');
        return '<tr>'
          +'<td style="white-space:nowrap;color:var(--cx-text-mute);">'+_escHtml((d.fecha||'').slice(0,10))+'</td>'
          +'<td style="font-weight:700;white-space:nowrap;">$'+Number(d.valor||0).toLocaleString('es-CO')+'</td>'
          +'<td><span class="dir-chip" style="background:'+(pagado?'var(--cx-success-pale,#d1fae5)':'var(--cx-warn-pale,#fef3c7)')
            +';color:'+(pagado?'var(--cx-success-text)':'var(--cx-warn-text)')+'">'+_escHtml(d.estado||'')+'</span></td>'
          +'<td>'+(d.fecha_publicacion
              ? '<span style="color:var(--cx-text-mute);">publico '+_escHtml(d.fecha_publicacion.slice(0,10))+'</span>'
              : '<span style="color:var(--cx-danger-text);font-weight:700;" title="Sin fecha de publicacion no se puede verificar que se entrego">sin fecha</span>')
            +(d.entregable? '<div style="color:var(--cx-text);">'+_escHtml(d.entregable)+'</div>':'')
            +(d.numero_oc? '<div style="font-size:10px;color:var(--cx-text-mute);">'+_escHtml(d.numero_oc)+'</div>':'')
          +'</td>'
        +'</tr>';
      }).join('')+'</table>'
    : '<div style="color:var(--cx-text-mute);font-size:12px;padding:6px 0;">Sin pagos registrados en el periodo.</div>';

  // Encabezado del pop-up: quien es, de un vistazo, con sus tres numeros.
  var ini=(x.nombre||'?').trim().charAt(0).toUpperCase();
  var retorno = (x.roi_pct===null||x.roi_pct===undefined)
    ? '<span style="color:var(--cx-text-mute)">sin dato</span>'
    : '<span style="color:'+(x.roi_pct>=0?'var(--cx-success-text)':'var(--cx-danger-text)')+'">'+(x.roi_pct>=0?'+':'')+x.roi_pct+'%</span>';
  var cabeza='<div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;">'
    +'<div style="width:52px;height:52px;border-radius:15px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:20px;color:#fff;background:var(--cx-primary-grad,var(--cx-primary));flex:0 0 auto;'+(esBaja?'filter:grayscale(1);opacity:.6;':'')+'">'+_escHtml(ini)+'</div>'
    +'<div style="min-width:0;flex:1;">'
      +'<div style="font-size:19px;font-weight:800;color:var(--cx-text);letter-spacing:-.02em;line-height:1.15;">'+_escHtml(x.nombre||'-')+'</div>'
      +'<div style="font-size:12.5px;color:var(--cx-text-mute);margin-top:2px;">'
        +_escHtml(x.usuario_red? '@'+x.usuario_red : (x.red_social||''))
        +(x.ciudad? ' &middot; '+_escHtml(x.ciudad):'')
        +(x.discount_code? ' &middot; cupón '+_escHtml(x.discount_code):'')+'</div>'
    +'</div>'
  +'</div>'
  +'<div class="dir-kpis" style="margin-bottom:14px;">'
    +'<div class="dir-k"><div class="lbl">Pagado</div><div class="val">'+_dirMoneda(x.pagado)+'</div></div>'
    +'<div class="dir-k"><div class="lbl">Pagos</div><div class="val">'+(x.n_pagos||0)+(x.ticket_prom?'<span style="font-size:10px;font-weight:600;color:var(--cx-text-mute)"> &middot; '+_dirMoneda(x.ticket_prom)+' c/u</span>':'')+'</div></div>'
    +'<div class="dir-k"><div class="lbl">Por pagar</div><div class="val" style="color:'+((x.pendiente>0)?'var(--cx-warn-text)':'var(--cx-text-mute)')+'">'+_dirMoneda(x.pendiente)+'</div></div>'
    +'<div class="dir-k"><div class="lbl">Retorno</div><div class="val">'+retorno+'</div></div>'
  +'</div>';

  box.innerHTML = cabeza
    + motivo
    + '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px 18px;">'+datos+'</div>'
    + acciones
    + (x.notas? '<div style="background:var(--cx-bg-alt);border-radius:9px;padding:9px 12px;font-size:12px;color:var(--cx-text-mute);margin-bottom:8px;">'+_escHtml(x.notas)+'</div>' : '')
    + tabla;
  modal.classList.add('open');
}

function dirAccion(ix, accion){
  // Reusa los MISMOS flujos del catalogo (M3: una sola via por accion, no una segunda copia
  // que despues diverja). El directorio solo los invoca con los datos que ya tiene.
  var x=(window._DIR_VIS||[])[ix]; if(!x) return;
  var id=x.influencer_id, nom=x.nombre||'';
  // La ficha se cierra antes: dos modales apilados no se entienden.
  dirCerrarFicha();
  if(accion==='editar')    return editInfluencer(id);
  if(accion==='gestionar') return abrirGestionarPagos(id, nom);
  if(accion==='baja')      return abrirDarDeBaja(id, nom);
  if(accion==='pago'){
    // La ficha ya trae banco/cuenta (enmascarados si el usuario no puede verlos), asi que
    // el modal se llena sin depender del cache que arma la tabla del catalogo.
    return solicitarPagoInf(id, nom, x.tarifa||'', x.banco||'', x.cuenta_bancaria||'',
                            x.cedula_nit||'', x.tipo_cuenta||'');
  }
}

function dirBuscarLocal(){
  clearTimeout(window._DIR_Q_T);
  window._DIR_Q_T=setTimeout(renderDirectorio, 120);
}

function infSubView(v){
  window._INF_SUBVIEW=v;
  var vp=document.getElementById('inf-view-pagos'), vc=document.getElementById('inf-view-creadores');
  var bp=document.getElementById('infsub-pagos'), bc=document.getElementById('infsub-creadores');
  if(vp) vp.style.display=(v==='pagos')?'':'none';
  if(vc) vc.style.display=(v==='creadores')?'':'none';
  if(bp){ bp.style.color=(v==='pagos')?'#6d28d9':'var(--cx-text-mute)'; bp.style.borderBottomColor=(v==='pagos')?'#6d28d9':'transparent'; }
  if(bc){ bc.style.color=(v==='creadores')?'#6d28d9':'var(--cx-text-mute)'; bc.style.borderBottomColor=(v==='creadores')?'#6d28d9':'transparent'; }
  if(v==='pagos') renderCentroPagos();
  // El directorio se pide SOLO al abrir su vista, y una vez: recorre 12 meses de pagos
  // y las ventas del periodo, y no tiene por que pagarse en la carga de la pantalla (M43).
  if(v==='creadores' && !window._DIR_DATA) loadDirectorio();
}
// `pagarDesdeMarketing` se retiro el 27-jul junto con su boton. Quedaba la funcion sin
// llamador: codigo muerto que mueve PLATA, que es peor que codigo muerto a secas (una
// pantalla futura podria engancharla sin saber que el backend la rechaza). El pago lo
// decide y ejecuta el CEO en Centro de Mando, contra el endpoint canonico de Compras.
// Jefferson pide desde aca y ve el estado de lo que pidio.

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
      // Y si lo RECHAZARON, ve por que: sin eso vuelve a pedir lo mismo la semana siguiente.
      +(e==='rechazado'
          ? '<div style="flex-basis:100%;background:var(--cx-danger-pale);border-left:3px solid var(--cx-danger);border-radius:9px;padding:9px 13px;margin-top:8px;font-size:12.5px;color:var(--cx-danger-text);line-height:1.45">'
              +'<b>Rechazado</b>'
              +(p.rechazado_por? ' por '+_escHtml(p.rechazado_por) : '')
              +(p.rechazado_at? ' el '+_escHtml(String(p.rechazado_at).slice(0,10)) : '')
              +(p.motivo_rechazo
                  ? '<div style="margin-top:3px;font-weight:600">'+_escHtml(p.motivo_rechazo)+'</div>'
                  : '<div style="margin-top:3px;opacity:.85">Sin motivo registrado (rechazo anterior a que se guardara el motivo).</div>')
            +'</div>'
          : '')
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
        + 'Sebastián las paga o rechaza desde su Centro de Mando &rarr; Pagos. '
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
  if(!dry.duplicados_a_eliminar){ alert('No hay duplicados para fusionar.'); return; }
  // El confirm dice EXACTAMENTE lo que va a pasar, separando los dos criterios: fusionar
  // por cédula es juntar fichas de la MISMA PERSONA cargada con nombres distintos, y eso
  // hay que verlo antes de aceptar. La cuenta bancaria a secas no fusiona nada (dos
  // personas pueden cobrar en la misma cuenta).
  var det = 'Se van a fusionar '+dry.grupos_n+' grupo(s):\n'
    + '  · '+(dry.grupos_por_nombre||0)+' por nombre repetido\n'
    + '  · '+(dry.grupos_por_cedula||0)+' por MISMA CÉDULA (misma persona, nombres distintos)\n\n'
    + 'Se eliminan '+dry.duplicados_a_eliminar+' ficha(s) duplicada(s).\n'
    + 'Se MUEVEN '+(dry.pagos_que_se_mueven||0)+' pago(s) a la ficha que se conserva '
    + '(la de más pagos). Ningún pago se borra: si se perdiera alguno, la operación se cancela sola.\n\n'
    + 'Queda en auditoría, pero no hay botón de deshacer.\n\n¿Continuar?';
  if(!confirm(det)) return;
  try {
    const r2 = await fetch('/api/marketing/influencers/dedup-merge', {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token': window._csrfTok||''},
      body: JSON.stringify({apply:true})
    });
    const d2 = await r2.json();
    if(!r2.ok || !d2.ok){ alert('Error: '+((d2&&d2.error)||r2.status)); return; }
    alert('✅ '+d2.duplicados_eliminados+' ficha(s) fusionada(s) · '
      +(d2.por_nombre||0)+' por nombre, '+(d2.por_cedula||0)+' por cédula\n'
      +d2.pagos_repuntados+' pago(s) movido(s) a la ficha que se conserva'
      +(d2.unique_index?'\n\n🔒 Protección anti-duplicados ACTIVADA: el panel ya no puede volver a crearlos.'
                       :'\n\n⚠ La protección anti-duplicados NO se pudo activar · quedan fichas con el mismo nombre. Volvé a abrir Duplicados.'));
    closeModal('modal-duplicados');
    if(typeof loadInfluencers==='function') loadInfluencers();
    // El directorio también cambió: se recarga para que no muestre las fichas ya fusionadas.
    if(typeof loadDirectorio==='function' && window._DIR_DATA) loadDirectorio();
  } catch(e){ alert('Error red: '+e.message); }
}

async function abrirDuplicados() {
  const modalId = 'modal-duplicados';
  let modal = document.getElementById(modalId);
  if(!modal) {
    modal = document.createElement('div');
    modal.id = modalId;
    // El contrato de modales de ESTA página es `.modal-bg` (la capa oscura, que es la que
    // tiene `display:none` y se muestra con `.open`) conteniendo un `.modal` (la caja).
    // Acá estaba al revés: la capa se creaba con class "modal" y adentro un "modal-content"
    // que no existe en el CSS. Resultado: la ventana SÍ se creaba y el fetch SÍ corría, pero
    // se dibujaba pegada al final del body en vez de encima -- desde afuera, "no se abre nada".
    // Es el mismo patrón de M112: código escrito contra un sistema de modales distinto del
    // que la página usa hoy.
    modal.className = 'modal-bg';
    modal.innerHTML = ''
      +'<div class="modal" style="max-width:900px;width:min(900px,95vw);">'
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
      + '📌 Ya le quedó visible a Sebastián en su <b>Centro de Mando &rarr; Pagos</b>. '
      + 'Cuando pague vas a recibir notificación in-app. Si lo rechaza, acá vas a ver el motivo.'
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



// ═══════════════════════════════════════════════════════════════════════
// AUDIT 26-may · Meta del mes + Calendario cosmético (sprint #4)
// ═══════════════════════════════════════════════════════════════════════
















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


# ── El JS grande se sirve como ARCHIVO EXTERNO cacheable ────────────────────────────────
# PERF 15-ago-2026 (Sebastián: *"están lentos en cada cosa, cargando y mostrando"*). Medido:
# esta pantalla bajaba 115 KB de JavaScript incrustado en CADA carga -- el navegador no lo
# puede guardar en caché ni reusar compilado. Ahora va como archivo con ?v=HASH: cambia el
# JS, cambia la URL, y el navegador baja lo nuevo sin quedarse con una copia vieja.
#
# El bloque no lleva NINGÚN dato por usuario (verificado antes de moverlo), así que el
# archivo es el mismo para todos y se puede cachear sin riesgo de servirle a alguien los
# permisos de otro.
#
# El CÓDIGO FUENTE no cambia: el JS sigue escrito acá. Fallback BLINDADO: si el bloque no
# aparece o no mide lo esperado, se deja inline y la pantalla funciona igual que antes.
MARKETING_APP_JS = ""
MARKETING_APP_JS_HASH = ""
try:
    import hashlib as _hl_market
    _mk_market = "const fmt = n => Number(n||0).toLocaleString('es-CO');"
    _i_market = MARKETING_HTML.find(_mk_market)
    if _i_market > 0:
        _open_market = MARKETING_HTML.rfind("<script>", 0, _i_market)
        _close_market = MARKETING_HTML.find("</script>", _i_market)
        if _open_market > 0 and _close_market > _open_market:
            _js_market = MARKETING_HTML[_open_market + len("<script>"):_close_market]
            if len(_js_market) > 90000:      # sanity: el bloque grande, no un script chico
                MARKETING_APP_JS = _js_market
                MARKETING_APP_JS_HASH = _hl_market.md5(
                    _js_market.encode("utf-8")).hexdigest()[:10]
                MARKETING_HTML = (
                    MARKETING_HTML[:_open_market]
                    + '<script src="/marketing-app.js?v=' + MARKETING_APP_JS_HASH + '"></script>'
                    + MARKETING_HTML[_close_market + len("</script>"):]
                )
except Exception:
    MARKETING_APP_JS = ""
    MARKETING_APP_JS_HASH = ""
