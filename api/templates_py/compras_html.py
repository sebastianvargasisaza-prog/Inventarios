# Auto-extraído de index.py — Fase A refactor
COMPRAS_HTML = """<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Compras HHA</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#f5f4f2;color:#1C1917;font-size:14px;}
.topbar{background:#292524;color:#fff;padding:12px 20px;display:flex;align-items:center;gap:16px;}
.topbar h1{font-size:17px;font-weight:600;flex:1;}
.topbar a{color:#d6d3d1;text-decoration:none;font-size:13px;}
.topbar a:hover{color:#fff;}
.tab-nav{background:#fff;border-bottom:2px solid #e7e5e4;display:flex;gap:0;overflow-x:auto;white-space:nowrap;}
.tn{padding:11px 14px;font-size:13px;font-weight:500;color:#78716c;border:none;background:none;cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-2px;}
.tn:hover{color:#6d28d9;background:#faf7ff;}
.tn.on{color:#6d28d9;border-bottom-color:#6d28d9;font-weight:700;}
.sp-tab{padding:9px 18px;font-size:13px;font-weight:600;color:#78716c;border:none;background:none;cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-2px;}
.sp-tab:hover{color:#292524;}
.sp-tab.sp-on{color:#7c3aed;border-bottom-color:#7c3aed;font-weight:800;}
.pane{display:none;padding:18px 24px;max-width:1680px;margin:0 auto;}
#pane-planta{max-width:96vw;}
#pane-dash{max-width:1900px;}  /* Sebastián 13-jul · el dashboard usa casi todo el ancho */
.pane.on{display:block;}
/* KPI */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:18px;}
.kpi{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:14px;}
.kpi-l{font-size:10px;color:#78716c;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px;}
.kpi-v{font-size:22px;font-weight:800;color:#292524;}
.kpi-v.w{color:#d97706;} .kpi-v.r{color:#dc2626;} .kpi-v.g{color:#16a34a;}
.kpi-s{font-size:11px;color:#78716c;margin-top:2px;}
/* Cards */
.bar{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:10px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px;}
.bar input,.bar select{padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;color:#292524;}
.bar input{min-width:190px;}
.pills{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px;}
.pill{padding:3px 11px;border-radius:12px;font-size:11px;font-weight:600;background:#f3f4f6;color:#374151;}
.pill.y{background:#fef3c7;color:#92400e;} .pill.b{background:#dbeafe;color:#1e40af;} .pill.g{background:#dcfce7;color:#166534;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px;}
.card{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:14px;display:flex;flex-direction:column;gap:7px;}
.card:hover{border-color:#a8a29e;}
.ch{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;}
.cnum{font-weight:700;font-size:13px;} .cprov{font-size:13px;color:#1c1917;font-weight:600;margin-top:2px;}
.cprov-label{font-size:9px;color:#a8a29e;text-transform:uppercase;letter-spacing:0.05em;display:block;}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;}
.b-bor{background:#f3f4f6;color:#6b7280;} .b-rev{background:#fef3c7;color:#92400e;}
.b-aut{background:#dbeafe;color:#1e40af;} .b-pag{background:#dcfce7;color:#166534;}
.b-rec{background:#f0fdf4;color:#14532d;border:1px solid #bbf7d0;}
.cmeta{font-size:11px;color:#78716c;display:flex;gap:10px;flex-wrap:wrap;}
.cval{font-size:15px;font-weight:800;color:#292524;}
.cobs{font-size:11px;color:#78716c;font-style:italic;}
.acts{display:flex;gap:7px;flex-wrap:wrap;margin-top:3px;}
.btn{padding:6px 13px;border-radius:6px;font-size:12px;font-weight:600;border:none;cursor:pointer;}
.bp{background:#292524;color:#fff;} .bp:hover{background:#44403c;}
.bg{background:#16a34a;color:#fff;} .bg:hover{background:#15803d;}
.bw{background:#d97706;color:#fff;} .bw:hover{background:#b45309;}
.bi{background:#2563eb;color:#fff;} .bi:hover{background:#1d4ed8;}
.bo{background:#fff;color:#292524;border:1px solid #d6d3d1;} .bo:hover{background:#f5f4f2;}
.bs{padding:4px 10px;font-size:11px;}
.empty{text-align:center;padding:36px;color:#78716c;font-size:13px;}
.err{text-align:center;padding:20px;color:#dc2626;font-size:13px;}
/* Prov */
.pg{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px;}
.pc{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:14px;}
.pn{font-weight:700;font-size:14px;margin-bottom:3px;}
.pnit{font-size:11px;color:#78716c;margin-bottom:8px;}
.pd{font-size:12px;color:#57534e;display:flex;flex-direction:column;gap:2px;}
/* Queue */
.queue-row{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:18px;}
@media(max-width:700px){.queue-row{grid-template-columns:1fr;}}
.qbox{background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:14px;}
.qtit{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#78716c;margin-bottom:10px;}
/* Modal */
.ov{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:900;display:none;align-items:center;justify-content:center;padding:16px;}
.ov.on{display:flex;}
.mdl{background:#fff;border-radius:10px;width:100%;max-width:560px;max-height:92vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.3);}
.mdl-lg{max-width:700px;}
.mh{padding:16px 20px;border-bottom:1px solid #e7e5e4;display:flex;align-items:center;justify-content:space-between;}
.mh h3{font-size:15px;font-weight:700;}
.mx{background:none;border:none;font-size:20px;cursor:pointer;color:#78716c;line-height:1;}
.mb{padding:18px 20px;display:flex;flex-direction:column;gap:12px;}
.mf{padding:12px 20px;border-top:1px solid #e7e5e4;display:flex;gap:8px;justify-content:flex-end;}
.fg label{display:block;font-size:11px;font-weight:600;color:#44403c;margin-bottom:4px;}
.fg input,.fg select,.fg textarea{width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;}
.fg textarea{min-height:65px;resize:vertical;}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.ibox{background:#f9f8f7;border:1px solid #e7e5e4;border-radius:6px;padding:10px;font-size:12px;color:#57534e;display:grid;grid-template-columns:auto 1fr;gap:4px 10px;margin-top:4px;}
.ibox .lbl{color:#78716c;font-weight:600;white-space:nowrap;}
.itbl{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px;}
.itbl th{background:#f5f4f2;padding:5px 7px;text-align:left;font-size:11px;font-weight:700;color:#44403c;}
.itbl td{padding:5px 7px;border-bottom:1px solid #f3f4f6;}
.itbl input{width:100%;border:1px solid #e7e5e4;border-radius:4px;padding:3px 6px;font-size:12px;}
.total-row{text-align:right;margin-top:10px;font-size:15px;font-weight:700;}
.fab{position:fixed;bottom:22px;right:22px;background:#292524;color:#fff;border:none;width:50px;height:50px;border-radius:50%;font-size:22px;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.3);display:flex;align-items:center;justify-content:center;}
.mh-ent{background:linear-gradient(135deg,#1c1917 0%,#292524 100%)!important;border-bottom:2px solid #57534e;}
.mh-ent h3{color:#f5f5f4!important;}
.mh-ent .mx{color:#d6d3d1!important;}
.cat-pills{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px;}
.pill{background:#44403c;border:1px solid #57534e;color:#d6d3d1;padding:4px 10px;border-radius:20px;cursor:pointer;font-size:11px;transition:all .15s;}
.pill:hover{background:#57534e;}
.pill-on{background:#ea580c!important;border-color:#ea580c!important;color:#fff!important;font-weight:700;}
.btn.br{background:#dc2626;color:#fff;border:1px solid #b91c1c;}
.btn.br:hover{background:#b91c1c;}
.ocs-cpill{padding:5px 13px;border-radius:20px;font-size:12px;font-weight:600;border:1.5px solid #d6d3d1;background:#fff;color:#57534e;cursor:pointer;transition:all .15s;white-space:nowrap;}
.ocs-cpill:hover{background:#f5f5f4;border-color:#a8a29e;}
.ocs-cpill.on{background:#ea580c;border-color:#ea580c;color:#fff;}
.ptbl{width:100%;border-collapse:collapse;font-size:13px;}
.ptbl th{background:#f5f5f4;color:#78716c;font-weight:600;padding:8px 10px;text-align:left;border-bottom:2px solid #e7e5e4;}
.ptbl td{padding:8px 10px;border-bottom:1px solid #f0edec;vertical-align:middle;}
.ptbl tr:hover td{background:#fafafa;}
.pgrp-card{background:#fff;border:1px solid #e7e5e4;border-radius:8px;margin-bottom:14px;overflow:hidden;}
/* Mobile responsive · Catalina/Mayra tablet · 27-may-2026 */
@media (max-width: 768px) {
  .pane { padding: 12px 10px; }
  .topbar { padding: 10px 12px; gap: 8px; flex-wrap: wrap; }
  .topbar h1 { font-size: 15px; }
  .tab-nav { font-size: 12px; }
  .tn { padding: 9px 10px; font-size: 12px; }
  .grid { grid-template-columns: 1fr; gap: 10px; }
  .pg { grid-template-columns: 1fr; }
  .kpis { grid-template-columns: 1fr 1fr; gap: 8px; }
  .kpi { padding: 10px; }
  .kpi-v { font-size: 18px; }
  .g2 { grid-template-columns: 1fr !important; }
  .mdl { max-width: 96vw !important; }
  .mf { flex-direction: column-reverse; gap: 8px; }
  .mf .btn { width: 100%; }
  .ptbl .mob-hide, .itbl .mob-hide { display: none !important; }
  .ptbl th, .ptbl td { padding: 6px 7px; font-size: 12px; }
  .ptbl { font-size: 12px; }
  .bar { gap: 6px; padding: 8px 10px; }
  .bar input { min-width: 0; width: 100%; }
  .acts { gap: 5px; }
  .acts .btn { padding: 7px 11px; font-size: 11px; }
  /* Cards items consolidados grupo · scroll horizontal explicito */
  .pgrp-card table { display: block; overflow-x: auto; white-space: nowrap; }
}
@media (max-width: 480px) {
  .kpis { grid-template-columns: 1fr; }
  .pane { padding: 10px 8px; }
}
</style>
</head>
<body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
  <div>
    <div class="cx-mod-header__title">Compras</div>
    <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; OCs, proveedores &amp; pagos &middot; <span style="color:#a8a29e">{usuario}</span></div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">&larr; Módulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
    </button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>

<!-- Sebastián 21-may-2026 · 11 tabs → 4 grupos top (como hicimos con
     Programación 8→4). Catalina ya tenía muscular memory · IDs originales
     (data-tab) se mantienen para que las funciones loadX no se rompan. -->
<!-- Compras MAX · 21-may-2026 · Botón flotante IA Agente + acciones rápidas -->
<!-- Sebastián 24-may-2026 · botón IA chat movido a bottom-LEFT · antes
     tapaba el FAB "+ Nueva OC" (ambos en bottom-right). Modal sigue
     anclado a la izquierda matching el botón. -->
<button id="cx-ia-btn" onclick="cxAbrirIA()" style="position:fixed;bottom:24px;left:24px;width:54px;height:54px;border-radius:50%;background:linear-gradient(135deg,#0f766e,#0891b2);color:#fff;border:none;cursor:pointer;font-size:22px;box-shadow:0 6px 20px rgba(15,118,110,.4);z-index:9999" title="Pregúntale a Compras (IA)">💬</button>
<div id="cx-ia-modal" style="display:none;position:fixed;bottom:90px;left:24px;width:400px;max-height:600px;background:#fff;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.25);z-index:9999;flex-direction:column;border:1px solid #cbd5e1">
  <div style="background:linear-gradient(135deg,#0f766e,#0891b2);color:#fff;padding:12px 16px;border-radius:14px 14px 0 0;display:flex;justify-content:space-between;align-items:center">
    <b style="font-size:14px">💬 Pregúntale a Compras</b>
    <button onclick="cxCerrarIA()" style="background:none;border:none;color:#fff;font-size:1.3em;cursor:pointer;padding:0 4px">×</button>
  </div>
  <div id="cx-ia-hist" style="flex:1;overflow-y:auto;padding:12px;font-size:12px;min-height:200px;max-height:380px"></div>
  <div style="padding:8px;border-top:1px solid #e2e8f0">
    <div style="display:flex;gap:6px;margin-bottom:6px;flex-wrap:wrap">
      <button onclick="cxIAPreguntar('¿Qué proveedor me conviene más este mes?')" style="background:#f1f5f9;border:1px solid #cbd5e1;padding:4px 8px;border-radius:5px;font-size:10px;cursor:pointer">Top proveedor</button>
      <button onclick="cxIAPreguntar('¿Cuánto tengo por pagar?')" style="background:#f1f5f9;border:1px solid #cbd5e1;padding:4px 8px;border-radius:5px;font-size:10px;cursor:pointer">Por pagar</button>
      <button onclick="cxIAPreguntar('¿Hay alertas urgentes?')" style="background:#f1f5f9;border:1px solid #cbd5e1;padding:4px 8px;border-radius:5px;font-size:10px;cursor:pointer">Alertas</button>
    </div>
    <div style="display:flex;gap:6px">
      <input id="cx-ia-input" type="text" placeholder="¿qué proveedor me conviene?" onkeydown="if(event.key==='Enter')cxIAPreguntar()" style="flex:1;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:12px">
      <button onclick="cxIAPreguntar()" id="cx-ia-send" style="padding:7px 12px;background:#0891b2;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:700">Enviar</button>
    </div>
  </div>
</div>
<script>
// P0 audit 26-may · helper esc local (este script tag es independiente
// del que define _esc en línea ~1927 · ámbito JS distinto).
function _esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function cxAbrirIA(){var m=document.getElementById('cx-ia-modal');if(m){m.style.display='flex';document.getElementById('cx-ia-input').focus();}}
function cxCerrarIA(){var m=document.getElementById('cx-ia-modal');if(m)m.style.display='none';}
async function cxIAPreguntar(pregunta){
  var inp=document.getElementById('cx-ia-input');
  var hist=document.getElementById('cx-ia-hist');
  var btn=document.getElementById('cx-ia-send');
  if(typeof pregunta!=='string') pregunta=(inp.value||'').trim();
  if(pregunta.length<3) return;
  if(!document.getElementById('cx-ia-modal').style.display||document.getElementById('cx-ia-modal').style.display==='none') cxAbrirIA();
  // P0 audit 26-may · escape user input (auto-XSS si pregunta tiene HTML)
  hist.innerHTML+='<div style="text-align:right;margin-bottom:6px"><span style="background:#0891b2;color:#fff;padding:6px 10px;border-radius:10px;display:inline-block;max-width:85%">'+_esc(pregunta)+'</span></div>';
  hist.innerHTML+='<div id="cx-ia-pend" style="margin-bottom:6px"><span style="background:#f1f5f9;color:#475569;padding:6px 10px;border-radius:10px;font-style:italic">pensando…</span></div>';
  hist.scrollTop=hist.scrollHeight;
  if(inp) inp.value='';
  btn.disabled=true;
  // Cap log a 200 turns para evitar memory leak en sesiones largas (anti-patrón documentado feedback_audit_marketing_25may)
  while(hist.children.length > 200) hist.removeChild(hist.firstChild);
  try{
    var r=await fetch('/api/compras/asistente-ia',_fetchOpts('POST',{pregunta:pregunta}));
    var d=await r.json();
    var pend=document.getElementById('cx-ia-pend');if(pend) pend.remove();
    if(!r.ok){
      // ALTA-6 fix · NO_API_KEY mensaje user-friendly (no exponer detalle interno)
      var msgErr = (d.codigo === 'NO_API_KEY')
        ? '⚠ Asistente IA temporalmente no disponible · configurar en Render'
        : ('⚠ '+(d.error||r.status));
      hist.innerHTML+='<div style="margin-bottom:6px"><span style="background:#fee2e2;color:#991b1b;padding:6px 10px;border-radius:10px">'+_esc(msgErr)+'</span></div>';
    } else {
      // P0 26-may · output del LLM (Claude) ya puede contener HTML/scripts
      hist.innerHTML+='<div style="margin-bottom:6px"><span style="background:#f0fdfa;color:#134e4a;padding:6px 10px;border-radius:10px;display:inline-block;max-width:90%;white-space:pre-wrap">'+_esc(d.respuesta||'(sin respuesta)')+'</span></div>';
    }
    hist.scrollTop=hist.scrollHeight;
  }catch(e){
    var p=document.getElementById('cx-ia-pend');if(p) p.remove();
    hist.innerHTML+='<div style="margin-bottom:6px"><span style="background:#fee2e2;color:#991b1b;padding:6px 10px;border-radius:10px">⚠ red: '+_esc(e.message)+'</span></div>';
  }
  btn.disabled=false;
}
</script>

<!-- Compras PRO · Sebastián 21-may-2026 · reagrupación 11 sub-tabs → 5 grupos.
     De 4 grupos top a 4 con menos sub-tabs cada uno · "Mis Solicitudes" pasa a
     widget en Dashboard · default landing = Dashboard (consolidado · KPIs grandes
     arriba). Influencers solo admin. -->
<div class="tab-nav" id="cx-grp-bar" style="display:flex;gap:8px;padding:8px 0;border-bottom:2px solid #e2e8f0;margin-bottom:12px">
  <button class="cx-grp-btn on" data-cx-grp="analitica"  data-default-tab="dash"
    style="padding:9px 22px;border:none;border-radius:8px 8px 0 0;font-size:14px;font-weight:800;cursor:pointer;background:linear-gradient(135deg,#0e7490,#0891b2);color:#fff;box-shadow:0 3px 10px rgba(8,145,178,.35)"
    title="Vista ejecutiva · 4 KPIs + alertas + tus solicitudes">📊 Dashboard</button>
  <button class="cx-grp-btn" data-cx-grp="entradas"      data-default-tab="planta"
    style="padding:9px 22px;border:none;border-radius:8px 8px 0 0;font-size:14px;font-weight:800;cursor:pointer;background:#e2e8f0;color:#475569"
    title="Bandeja: SOLs de Planta (MP+Empaque) y Solicitudes generales">📋 Bandeja</button>
  <button class="cx-grp-btn" data-cx-grp="ocs"           data-default-tab="consol"
    style="padding:9px 22px;border:none;border-radius:8px 8px 0 0;font-size:14px;font-weight:800;cursor:pointer;background:#e2e8f0;color:#475569"
    title="Órdenes de Compra · OCs activas · pagos · servicios">📦 OCs</button>
  <button class="cx-grp-btn" data-cx-grp="maestros"      data-default-tab="prov"
    style="padding:9px 22px;border:none;border-radius:8px 8px 0 0;font-size:14px;font-weight:800;cursor:pointer;background:#e2e8f0;color:#475569"
    title="Maestro de Proveedores + scorecard + ROI">🏭 Proveedores</button>
  <button class="cx-grp-btn" data-cx-grp="catalogo" data-default-tab="catalogo"
    style="padding:9px 22px;border:none;border-radius:8px 8px 0 0;font-size:14px;font-weight:800;cursor:pointer;background:#e2e8f0;color:#475569"
    title="Catálogo de consumibles + crear compra + reporte de gasto por categoría">🗂️ Catálogo / Gastos</button>
  <span data-cx-sub="catalogo" style="display:none;gap:6px;flex-wrap:wrap">
    <button class="tn" data-tab="catalogo" id="tn-catalogo"
      onclick="(function(f){ if(f && !f.getAttribute('src')) f.setAttribute('src', f.getAttribute('data-src')); })(document.getElementById('cat-iframe'))"
      title="Catálogo de consumibles + reporte de gasto (papelería, EPP, servicios…)">🗂️ Catálogo / Gastos</button>
  </span>
</div>

<!-- Sub-barras por grupo (1 visible a la vez) -->
<div class="tab-nav" id="cx-sub-bar" style="display:none;padding:6px 4px;border-bottom:1px dashed #cbd5e1;margin-bottom:14px;flex-wrap:wrap">
  <!-- Sub-tabs del grupo ENTRADAS (default visible) -->
  <!-- Sebastián 21-may-2026 · INFLUENCERS quitado de Compras · solo
       lo paga Sebastián · Catalina no tiene visibilidad. Botón sigue
       en DOM (display:none) para deep links · página standalone vive
       en /admin/influencers. -->
  <span data-cx-sub="entradas" style="display:none;gap:6px;flex-wrap:wrap">
    <button class="tn"      data-tab="planta" id="tn-planta" title="MP+Empaque · Centro Programación + Pre-Producción fusionado">🏭 Planta</button>
    <button class="tn"      data-tab="solic" id="tn-solic" title="Solicitudes generales (papelería, servicios, EPP, mantenimiento)">📋 Solicitudes</button>
    <!-- Producción · OCULTO 21-may-2026 · fusionado en Planta con badge Pre-Prod -->
    <button class="tn" data-tab="solprod" id="tn-solprod" style="display:none">🛠️ Producción <span id="solprod-badge" style="display:none;background:#dc2626;color:#fff;font-size:9px;font-weight:800;padding:1px 6px;border-radius:8px;margin-left:4px"></span></button>
    <!-- Influencers · visible SOLO para Sebastián / Alejandro (data-admin-only)
         · Catalina nunca lo ve · JS lo desoculta al boot si el user es admin. -->
    <button class="tn" data-tab="influencer" id="tn-influencer" data-admin-only="1"
      style="display:none" title="Privado · pagos influencers (solo admin)">💸 Influencers <span style="font-size:9px;background:#dc2626;color:#fff;padding:1px 5px;border-radius:6px;margin-left:2px;font-weight:700">admin</span></button>
  </span>
  <!-- Sub-tabs del grupo OCs Y PAGOS -->
  <span data-cx-sub="ocs" style="display:none;gap:6px;flex-wrap:wrap">
    <button class="tn"      data-tab="consol" id="tn-consol" title="OCs activas (Borrador/Revisada/Autorizada) agrupadas por proveedor">📦 OCs Activas <span style="font-size:9px;background:#cbd5e1;color:#475569;padding:1px 5px;border-radius:6px;margin-left:2px;font-weight:600">activas</span></button>
    <button class="tn"      data-tab="por-pagar" id="tn-por-pagar" title="Pendientes · OCs autorizadas sin pagar">💰 Por Pagar</button>
    <button class="tn"      data-tab="pagos" id="tn-pagos" title="Histórico · pagos ya ejecutados">💸 Pagos</button>
    <button class="tn"      data-tab="historico" id="tn-historico" title="Histórico · TODO lo que se ha pedido (todas las OCs, cualquier estado · buscable)">📜 Histórico</button>
    <button class="tn"      data-tab="facprov" id="tn-facprov" title="Libro de facturas de proveedor · cuentas por pagar formales con retenciones, vencimiento y saldos">🧾 Facturas <span id="facprov-badge" style="display:none;background:#dc2626;color:#fff;font-size:9px;font-weight:800;padding:1px 6px;border-radius:8px;margin-left:4px"></span></button>
    <button class="tn"      data-tab="atrasadas" id="tn-atrasadas" title="OCs sin recibir tras lead_time + buffer · Sebastián 23-may">🚨 Atrasadas <span id="atrasadas-badge" style="display:none;background:#dc2626;color:#fff;font-size:9px;font-weight:800;padding:1px 6px;border-radius:8px;margin-left:4px"></span></button>
    <button class="tn" style="display:none" data-tab="feedneed" id="tn-feedneed" title="Necesidades de compra · materias primas y envases por debajo del mínimo, en un solo lugar">🔔 Necesidades <span id="feedneed-badge" style="display:none;background:#dc2626;color:#fff;font-size:9px;font-weight:800;padding:1px 6px;border-radius:8px;margin-left:4px"></span></button>
    <button class="tn"      data-tab="discrep" id="tn-discrep" title="Recepciones con faltante · ranking calidad proveedor · Sebastián 23-may">📋 Calidad recepción <span id="discrep-badge" style="display:none;background:#dc2626;color:#fff;font-size:9px;font-weight:800;padding:1px 6px;border-radius:8px;margin-left:4px"></span></button>
    <button class="tn" style="display:none" data-tab="mailbox" id="tn-mailbox" title="Facturas detectadas por el cron mailbox · revisar/completar/descartar · Sebastián 23-may">📧 Mailbox <span id="mailbox-badge" style="display:none;background:#7c3aed;color:#fff;font-size:9px;font-weight:800;padding:1px 6px;border-radius:8px;margin-left:4px"></span></button>
    <!-- COT comparador · Sebastián 23-may-2026 PM · backend ya estaba listo, UI nueva -->
    <button class="tn"      data-tab="cotiz" id="tn-cotiz" title="Rondas de cotizaciones · comparar proveedores lado a lado · elegir ganadora">💬 Cotizaciones <span id="cotiz-badge" style="display:none;background:#0891b2;color:#fff;font-size:9px;font-weight:800;padding:1px 6px;border-radius:8px;margin-left:4px"></span></button>
    <!-- Sebastián 21-may-2026 · Órdenes de Servicio (serigrafía/tampografía) -->
    <button class="tn" style="display:none" data-tab="ordserv" id="tn-ordserv" title="Órdenes de Servicio · serigrafía, tampografía, etiquetado">🎨 Órdenes de Servicio</button>
    <button class="tn"      data-tab="prepenv" id="tn-prepenv" title="Preparar envases · jalona los envases de las producciones próximas para mandar a serigrafía/tampografía con anticipación">📦 Preparar envases</button>
  </span>
  <!-- Sub-tabs del grupo MAESTROS -->
  <span data-cx-sub="maestros" style="display:none;gap:6px;flex-wrap:wrap">
    <button class="tn"      data-tab="prov" id="tn-prov" title="Maestro de proveedores">🏭 Proveedores</button>
  </span>
  <!-- Sub-tabs del grupo DASHBOARD (consolidado · sin sub-tabs)
       Sebastián 21-may-2026 · Mis Solicitudes pasa a widget · Alertas pasa
       a banner arriba · todo unificado en una sola vista ejecutiva. -->
  <span data-cx-sub="analitica" style="display:flex;gap:6px;flex-wrap:wrap">
    <button class="tn on"   data-tab="dash" id="tn-dash" style="display:none" title="KPIs grandes · alertas · tus solicitudes · todo en uno">📊 Vista consolidada</button>
    <!-- Mantener data-tab="mis-sol" + "alertas" en DOM oculto para no romper deep links -->
    <button class="tn" data-tab="alertas" id="tn-alertas" style="display:none">🚨 Alertas</button>
    <button class="tn" data-tab="mis-sol" id="tn-mis-sol" style="display:none">👤 Mis Solicitudes</button>
  </span>
</div>

<!-- PANES -->
<div id="pane-catalogo" class="pane">
  <div style="font-size:12px;color:#64748b;margin-bottom:8px">🗂️ Catálogo de consumibles + gastos generales · sin salir de Compras. Aquí viven papelería, EPP, servicios, aseo… con su proveedor y precio, editables y reutilizables.</div>
  <iframe id="cat-iframe" data-src="/compras/consumos" title="Catálogo / Gastos"
    style="width:100%;height:80vh;border:1px solid #e2e8f0;border-radius:12px;background:#fff"></iframe>
</div>
<div id="pane-dash" class="pane on">
  <!-- Compras PRO · Sebastián 21-may-2026 · Dashboard CONSOLIDADO con 4 KPIs grandes. -->
  <!-- Franja superior · 4 KPIs CLAVE que el consultor procurement recomendó:
       1. Cash a pagar 30d · 2. OCs en riesgo · 3. SOLs sin tocar · 4. Salud score -->
  <div id="dash-kpis-grandes" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:14px"></div>
  <div id="dash-alertas-banner" style="margin-bottom:10px"></div>
  <div id="dash-home-2" style="margin-bottom:14px"></div>
  <div id="dash-consumos-elev" style="margin-bottom:14px"></div>
  <div id="dash-mis-solic-widget" style="margin-bottom:14px"></div>
  <!-- Fallback legacy widgets (oculto por default · solo si dash-home falla) -->
  <div id="dashboard-ejecutivo" style="display:none"></div>
  <div id="kpi-area" class="kpis" style="display:none"></div>
  <div class="queue-row" style="display:none">
    <div class="qbox">
      <div class="qtit">&#x26A1; SOLs esperando aprobaci&#xF3;n</div>
      <div id="q-aut"></div>
    </div>
    <div class="qbox">
      <div class="qtit">&#x1F4B8; OCs en proceso</div>
      <div id="q-pag"></div>
    </div>
  </div>
  <div id="dash-chart-wrap"></div>
</div>


<div id="pane-historico" class="pane">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap;">
    <span style="font-weight:800;color:#1e293b;font-size:15px;">&#x1F4DC; Histórico · todo lo que se ha pedido</span>
    <input type="text" id="q-historico" placeholder="Buscar OC, proveedor, categoría..." oninput="renderHistorico()" style="padding:7px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;min-width:220px">
    <select id="f-historico-est" onchange="renderHistorico()" style="padding:7px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px">
      <option value="">Todos los estados</option>
      <option value="Borrador">Borrador</option><option value="Revisada">Revisada</option>
      <option value="Autorizada">Autorizada</option><option value="Recibida">Recibida</option>
      <option value="Parcial">Parcial</option><option value="Pagada">Pagada</option>
    </select>
    <button class="btn bp" onclick="loadData().then(renderHistorico)" style="padding:6px 12px;font-size:12px">&#x21BA; Actualizar</button>
  </div>
  <div id="historico-body"><div class="empty">Cargando&hellip;</div></div>
</div>
<script>
function renderHistorico(){
  var wrap=document.getElementById('historico-body'); if(!wrap) return;
  var q=((document.getElementById('q-historico')||{}).value||'').toLowerCase().trim();
  var est=((document.getElementById('f-historico-est')||{}).value||'');
  var _f=function(n){return '$'+(Math.round(n||0)).toLocaleString('es-CO');};
  var _e=function(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});};
  var list=(typeof OCS!=='undefined'?OCS:[]).filter(function(o){
    if(est && (o.estado||'')!==est) return false;
    if(!q) return true;
    return ((o.numero_oc||'')+' '+(o.proveedor||'')+' '+(o.categoria||'')+' '+(o.observaciones||'')).toLowerCase().indexOf(q)>=0;
  });
  list.sort(function(a,b){return String(b.fecha||'').localeCompare(String(a.fecha||''));});
  var tot=list.reduce(function(s,o){return s+(parseFloat(o.valor_total)||0);},0);
  var h='<div style="margin:4px 0 10px;color:#475569;font-size:13px"><b>'+list.length+'</b> órdenes · total <b>'+_f(tot)+'</b></div>';
  if(!list.length){ wrap.innerHTML=h+'<div class="empty">No hay órdenes que coincidan.</div>'; return; }
  h+='<table style="width:100%;border-collapse:collapse;font-size:13px"><tr style="text-align:left;color:#6d28d9"><th style="padding:6px 8px">N° OC</th><th style="padding:6px 8px">Fecha</th><th style="padding:6px 8px">Proveedor</th><th style="padding:6px 8px">Categoría</th><th style="padding:6px 8px">Estado</th><th style="padding:6px 8px;text-align:right">Valor</th></tr>';
  list.forEach(function(o){
    h+='<tr style="border-bottom:1px solid #eee"><td style="padding:6px 8px;font-weight:700">'+_e(o.numero_oc)+'</td><td style="padding:6px 8px">'+_e(String(o.fecha||'').slice(0,10))+'</td><td style="padding:6px 8px">'+_e(o.proveedor)+'</td><td style="padding:6px 8px">'+_e(o.categoria||'—')+'</td><td style="padding:6px 8px">'+_e(o.estado)+'</td><td style="padding:6px 8px;text-align:right">'+_f(parseFloat(o.valor_total)||0)+'</td></tr>';
  });
  wrap.innerHTML=h+'</table>';
}
</script>

<div id="pane-pagos" class="pane">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
    <div style="font-weight:700;font-size:15px;color:#1c1917;">&#x1F4B8; Registro de Pagos</div>
    <input type="text" id="q-pagos" placeholder="Buscar proveedor, OC, medio, factura, referencia..." oninput="renderPagos()"
      style="flex:1;min-width:180px;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
    <select id="s-pagos-cat" onchange="renderPagos()" style="padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
      <option value="">Todas las categorias</option>
      <option value="mp">Mat. Primas</option><option value="mee">Empaque</option>
      <option value="svc">Servicios</option><option value="adm">Adm</option>
      <option value="inf">Infra</option><option value="cc">CC</option>
    </select>
    <button onclick="abrirOCRFactura()" style="padding:7px 14px;background:#7c3aed;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer" title="Subí foto de factura · la IA extrae items, totales · auto-match con OC pendiente">📤 Subir factura</button>
  </div>
  <div id="pagos-kpis" style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;"></div>
  <div id="pagos-bar-extra"></div>
  <div id="pagos-wrap">
    <div class="empty">Cargando pagos...</div>
  </div>
</div>

<div id="pane-influencer" class="pane">
  <div id="kpi-influencer" style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;"></div>
  <div class="bar" style="flex-wrap:wrap;gap:8px;">
    <input type="text" id="q-influencer" placeholder="Buscar influencer, solicitante..." oninput="renderInfluencers()">
    <select id="s-influencer" onchange="renderInfluencers()" title="Filtrar por estado">
      <option value="ACCION">⚡ Requieren acción (Pendientes + Por pagar)</option>
      <option value="Pendiente">⏳ Pendientes — definir valor / aprobar</option>
      <option value="Aprobada">💸 Por pagar</option>
      <option value="">Todos los estados</option>
      <option value="Pagada">✅ Pagadas</option>
      <option value="Rechazada">❌ Rechazadas</option>
    </select>
    <select id="order-influencer" onchange="renderInfluencers()" title="Ordenar por" style="background:#faf5ff;border:1px solid #c4b5fd;color:#5b21b6;font-weight:600;">
      <option value="urgente">⏰ Más urgente arriba (default · vence antes)</option>
      <option value="estado_fecha">📌 Por pagar primero (estado + fecha)</option>
      <option value="valor_desc">💰 Mayor valor primero</option>
      <option value="valor_asc">💵 Menor valor primero</option>
      <option value="reciente">🆕 Más reciente arriba</option>
      <option value="antiguo">📜 Más antiguo arriba</option>
    </select>
    <button onclick="limpiarSolsNoPagadas()" style="margin-left:auto;background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;padding:7px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer" title="Eliminar SOLs Influencer/Marketing/CC NO pagadas (preserva las Pagadas)">🧹 Limpiar no-pagadas</button>
  </div>
  <div id="pills-influencer-help" style="font-size:11px;color:#64748b;padding:0 4px 8px;"></div>
  <div id="pills-influencer" class="pills"></div>
  <div id="grid-influencer"></div>
  <div id="grid-influencer-pagadas"></div>
</div>
<!-- Modal rechazo influencer -->
<div id="m-rechazar-inf" class="ov">
  <div class="mdl" style="max-width:440px;">
    <div class="mh" style="background:#fef2f2;border-bottom:1px solid #fecaca;">
      <div style="display:flex;align-items:center;gap:10px;">
        <span style="font-size:22px;line-height:1;">&#x274C;</span>
        <div>
          <div style="font-size:15px;font-weight:700;color:#991b1b;">Rechazar solicitud</div>
          <div id="m-rechazar-inf-sub" style="font-size:12px;color:#b91c1c;margin-top:1px;"></div>
        </div>
      </div>
      <button class="mx" onclick="closeModal('m-rechazar-inf')">&#x2715;</button>
    </div>
    <div class="mb">
      <div class="fg">
        <label>Motivo del rechazo <span style="color:#dc2626;">*</span> <span style="font-weight:400;color:#78716c;">(visible para el solicitante)</span></label>
        <textarea id="motivo-rechazo-inf" rows="4" placeholder="Ej: Falta información de cuenta, monto incorrecto, valor no coincide..."></textarea>
      </div>
      <div style="background:#fef9c3;border:1px solid #fde047;border-radius:6px;padding:10px 12px;font-size:12px;color:#854d0e;">
        ⚠️ El solicitante recibirá un correo con este motivo. Sé específico para evitar reenvíos innecesarios.
      </div>
    </div>
    <div class="mf">
      <button class="btn" onclick="closeModal('m-rechazar-inf')" style="background:#f5f5f4;color:#44403c;border:1px solid #d6d3d1;">Cancelar</button>
      <button class="btn" id="btn-confirmar-rechazo" style="background:#dc2626;color:#fff;">&#x274C; Confirmar Rechazo</button>
    </div>
  </div>
</div>

<!-- Modal rechazo influencer -->
<!-- MEDIA-8 fix · Modal m-rechazar-inf duplicado eliminado (ya existe en línea 311) -->

<div id="pane-prov" class="pane">
  <div class="bar">
    <input type="text" id="q-prov" placeholder="Buscar proveedor..." oninput="renderProv()">
    <button class="btn bp" onclick="openModal('m-nprov')">+ Nuevo Proveedor</button>
    <button onclick="abrirROIProveedores()" style="padding:6px 14px;background:#0e7490;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;margin-left:8px" title="Ver ROI 12 meses · cumplimiento · top por monto">📊 ROI 12m</button>
    <!-- Sebastián 25-may-2026 · detector de duplicados case-insensitive ·
         agrupa "Agenquimicos" vs "AGENQUIMICOS" y permite fusionarlos
         conservando el más completo (con NIT) y traspasando OCs/SOLs/
         cotizaciones del huérfano -->
    <button onclick="abrirProvDuplicados()" style="padding:6px 14px;background:#dc2626;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;margin-left:8px" title="Detectar y fusionar proveedores duplicados (case-insensitive)">🔗 Detectar duplicados</button>
  </div>
  <div id="prov-grid" class="pg"><div class="empty">Cargando...</div></div>
</div>

<div id="pane-solic" class="pane">
  <!-- Filtros de categoria -->
  <div id="solic-cat-bar" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">
    <button class="ocs-cpill on" data-scat="ALL" onclick="setSolicCat(this)">&#x1F4CB; Todas</button>
    <button class="ocs-cpill" data-scat="svc" onclick="setSolicCat(this)">&#x1F527; Servicios</button>
    <button class="ocs-cpill" data-scat="adm" onclick="setSolicCat(this)">&#x1F4CB; Adm</button>
    <button class="ocs-cpill" data-scat="inf" onclick="setSolicCat(this)">&#x1F3DB; Infra</button>
    <button class="ocs-cpill" data-scat="cc" onclick="setSolicCat(this)">&#x1F4B3; CC</button>
  </div>
  <div class="bar">
    <input type="text" id="q-solic" placeholder="Buscar SOL, OC, solicitante, proveedor..." oninput="renderSolicitudes()">
    <select id="s-solic" onchange="if(_VISTA_AGRUPADA){ renderSolicitudesAgrupadas(); } else { renderSolicitudes(); }">
      <option value="">Todos los estados</option>
      <option value="Pendiente">Pendiente</option>
      <option value="Aprobada">Aprobada</option>
      <option value="Pagada">Pagada</option>
      <option value="Rechazada">Rechazada</option>
    </select>
    <button class="btn bp" onclick="openNuevaOC('')">&#x1F4DD; Nueva OC</button>
    <button class="btn" onclick="descargarSolicitudesPDF()" style="background:#1F5F5B;color:#fff;" title="PDF ejecutivo">&#x1F4C4; PDF</button>
    <button class="btn" onclick="regenerarSolicitudesAuto()" style="background:#7c3aed;color:#fff;" title="Regenerar solicitudes auto">&#x1F504; Regenerar</button>
    <!-- Sebastian 4-may-2026 (Catalina): toggle vista agrupada por proveedor -->
    <button id="btn-toggle-vista" class="btn" onclick="toggleVistaSolicitudes()" style="background:#0e7490;color:#fff;" title="Agrupar todas las solicitudes pendientes por proveedor — crea una sola OC para todas las del mismo proveedor">&#x1F4E6; Agrupar por proveedor</button>
    <!-- Sebastian 4-may-2026 (Catalina): consolidar AUTO-XXXX legacy 1-MP-cada-una en agrupadas por proveedor -->
    <button id="btn-consolidar-auto" class="btn" onclick="consolidarAutoPendientes()" style="background:#16a34a;color:#fff;" title="Consolida las AUTO-XXXX existentes (1 MP cada una) en una solicitud por proveedor (no toca data fuente)">&#x1F517; Consolidar AUTO</button>
    <!-- Sebastian 4-may-2026 (Catalina): solo limpiar AUTO-XXXX + SOL-YYYY-XXXX auto-gen + OCs Borrador, dejar que cron regenere -->
    <button id="btn-solo-limpiar-auto" class="btn" onclick="soloLimpiarAuto()" style="background:#475569;color:#fff;" title="Borra TODAS las solicitudes auto-generadas Pendientes (AUTO-XXXX + SOL-YYYY-XXXX) y sus OCs en Borrador. NO toca las que tienen OC Autorizada/Pagada. Cuando planta vuelva a pedir, ya vienen agrupadas por proveedor.">&#x1F5D1;&#xFE0F; Solo limpiar</button>
    <!-- Sebastian 4-may-2026 (Catalina): limpiar + regenerar inmediato con logica nueva COALESCE -->
    <button id="btn-limpiar-regenerar-auto" class="btn" onclick="limpiarYRegenerarAutoPlan()" style="background:#dc2626;color:#fff;" title="Borra solicitudes auto-generadas Pendientes y regenera ahora mismo (lee proveedor de maestro_mps si mp_lead_time_config esta vacio)">&#x1F525; Limpiar y regenerar</button>
  </div>
  <div id="pills-solic" class="pills"></div>
  <div id="grid-solic" class="grid"></div>
  <!-- Vista agrupada por proveedor (oculta por defecto) -->
  <div id="grid-solic-grouped" style="display:none;"></div>
</div>

<!-- Pane: Solicitudes de Producción (cola de Catalina desde el checklist Pre-Produccion) -->
<!-- Sebastián 21-may-2026 · Órdenes de Servicio (serigrafía/tampografía) -->
<div id="pane-ordserv" class="pane">
  <div class="bar" style="flex-wrap:wrap;gap:8px">
    <div>
      <span style="font-weight:700;color:#1e293b;font-size:15px">🎨 Órdenes de Servicio</span>
      <div style="font-size:11px;color:#64748b;margin-top:2px">Serigrafía · Tampografía · Etiquetado · cualquier servicio sobre envases existentes</div>
    </div>
    <div style="margin-left:auto;display:flex;gap:6px;align-items:center">
      <select id="os-filtro-estado" onchange="loadOrdenesServicio()" style="padding:6px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:12px">
        <option value="">Todos los estados</option>
        <option value="Borrador">Borrador</option>
        <option value="Enviada">Enviada</option>
        <option value="Recogida">Recogida</option>
        <option value="En proceso">En proceso</option>
        <option value="Entregada">Entregada</option>
        <option value="Confirmada">Confirmada</option>
        <option value="Cancelada">Cancelada</option>
      </select>
      <button class="btn bp" onclick="loadOrdenesServicio()" style="padding:6px 14px;font-size:12px">↺ Actualizar</button>
      <button class="btn" onclick="abrirNuevaOS()" style="padding:6px 14px;font-size:12px;background:#0f766e;color:#fff;font-weight:700">➕ Nueva OS</button>
    </div>
  </div>
  <div id="os-counts" style="display:flex;gap:6px;flex-wrap:wrap;margin:10px 0;font-size:11px"></div>
  <div style="overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead><tr style="background:#0f766e;color:#fff">
        <th style="padding:8px">N° OS</th>
        <th style="padding:8px">Proveedor</th>
        <th style="padding:8px">Servicio</th>
        <th style="padding:8px">Producto</th>
        <th style="padding:8px">Envase</th>
        <th style="padding:8px;text-align:center">Uds</th>
        <th style="padding:8px">Fecha sol.</th>
        <th style="padding:8px">F. requerida</th>
        <th style="padding:8px">Estado</th>
        <th style="padding:8px;text-align:center">Acciones</th>
      </tr></thead>
      <tbody id="os-tbody"><tr><td colspan="10" style="text-align:center;padding:18px;color:#94a3b8">Cargando…</td></tr></tbody>
    </table>
  </div>
</div>

<!-- Sebastián 31-may-2026 · Preparar envases (Pieza 1) -->
<div id="pane-prepenv" class="pane">
  <div class="bar" style="flex-wrap:wrap;gap:8px">
    <div>
      <span style="font-weight:700;color:#1e293b;font-size:15px">&#128230; Preparar envases &middot; serigrafía / tampografía</span>
      <div style="font-size:11px;color:#64748b;margin-top:2px">Jalona los envases de las producciones próximas. Elegí cuáles preparar, proveedor y tipo &middot; la fecha lista ya viene con 30 días de anticipación. "Generar OS" crea la orden y queda asignada.</div>
    </div>
    <div style="margin-left:auto;display:flex;gap:6px;align-items:center">
      <label style="font-size:12px;color:#475569">Horizonte
        <select id="prep-dias" onchange="loadPreparacionEnvases()" style="padding:6px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:12px">
          <option value="60">60d</option><option value="90" selected>90d</option><option value="120">120d</option><option value="180">180d</option>
        </select>
      </label>
      <button class="btn bp" onclick="loadPreparacionEnvases()" style="padding:6px 14px;font-size:12px">&#8635; Actualizar</button>
      <button class="btn" onclick="recalcularMinimosEnvases()" style="padding:6px 14px;font-size:12px;background:#7c3aed;color:#fff;font-weight:700" title="Calcula el mínimo de cada envase según el consumo real del plan (en vez del estático)">&#9881; Mínimos de envases</button>
    </div>
  </div>
  <div id="prep-tabla-wrap" style="overflow-x:auto;margin-top:10px">Cargando&hellip;</div>
</div>

<!-- Sebastián 31-may-2026 · Feed de necesidades (Pieza 2) -->
<div id="pane-feedneed" class="pane">
  <div class="bar" style="flex-wrap:wrap;gap:8px">
    <div>
      <span style="font-weight:700;color:#1e293b;font-size:15px">&#128276; Necesidades de compra</span>
      <div style="font-size:11px;color:#64748b;margin-top:2px">Materias primas y envases por debajo del mínimo, en un solo lugar &middot; lo más crítico arriba.</div>
    </div>
    <div style="margin-left:auto;display:flex;gap:6px;align-items:center">
      <button class="btn bp" onclick="loadFeedNecesidades()" style="padding:6px 14px;font-size:12px">&#8635; Actualizar</button>
    </div>
  </div>
  <div id="feedneed-kpis" style="display:flex;gap:8px;flex-wrap:wrap;margin:10px 0"></div>
  <div id="feedneed-wrap" style="overflow-x:auto">Cargando&hellip;</div>
</div>

<!-- Sebastián 1-jun-2026 · Libro de facturas de proveedor (cuentas por pagar) -->
<div id="pane-facprov" class="pane">
  <div class="bar" style="flex-wrap:wrap;gap:8px">
    <div>
      <span style="font-weight:700;color:#1e293b;font-size:15px">&#129534; Facturas de proveedor &middot; cuentas por pagar</span>
      <div style="font-size:11px;color:#64748b;margin-top:2px">Cada factura es un documento del proveedor (con retenciones y vencimiento) que se va saldando con pagos. Lo vencido arriba.</div>
    </div>
    <div style="margin-left:auto;display:flex;gap:6px;align-items:center;flex-wrap:wrap">
      <input type="text" id="fp-q" placeholder="Buscar nº, proveedor, OC…" oninput="_fpDeb()" style="padding:6px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:12px;min-width:180px">
      <select id="fp-estado" onchange="loadFacturasProv()" style="padding:6px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:12px">
        <option value="todas">Todos los estados</option>
        <option value="pendiente">Pendiente</option>
        <option value="parcial">Parcial</option>
        <option value="pagada">Pagada</option>
        <option value="anulada">Anulada</option>
      </select>
      <button class="btn bp" onclick="loadFacturasProv()" style="padding:6px 14px;font-size:12px">&#8635; Actualizar</button>
      <button class="btn" onclick="fpNuevaModal()" style="padding:6px 14px;font-size:12px;background:#0f766e;color:#fff;font-weight:700">&#10133; Nueva factura</button>
    </div>
  </div>
  <div id="fp-kpis" style="display:flex;gap:8px;flex-wrap:wrap;margin:10px 0"></div>
  <div id="fp-wrap" style="overflow-x:auto">Cargando&hellip;</div>
</div>

<div id="pane-solprod" class="pane">
  <div class="bar" style="flex-wrap:wrap;gap:8px;">
    <div>
      <span style="font-weight:700;color:#1e293b;font-size:15px;">&#128737;&#65039; Solicitudes desde Producción</span>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">Llegan del checklist Pre-Producción · Decide ruta: inventario / OC / serigrafía / tampografía</div>
    </div>
    <div style="margin-left:auto;display:flex;gap:6px;align-items:center;">
      <select id="solprod-filtro-estado" onchange="loadSolicitudesProduccion()" style="padding:6px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:12px">
        <option value="pendiente">Pendientes</option>
        <option value="decidida">Decididas</option>
        <option value="completada">Completadas</option>
        <option value="todas">Todas</option>
      </select>
      <button class="btn bp" onclick="loadSolicitudesProduccion()" style="padding:6px 14px;font-size:12px;">&#x21BA; Actualizar</button>
    </div>
  </div>
  <div id="solprod-lista" style="display:flex;flex-direction:column;gap:10px;margin-top:14px"></div>
  <div id="solprod-empty" style="display:none;text-align:center;color:#94a3b8;padding:40px;font-size:13px">Sin solicitudes en este estado.</div>
</div>

<!-- ════════════ TAB: MIS SOLICITUDES ════════════ -->
<div id="pane-mis-sol" class="pane">
  <div class="bar" style="flex-wrap:wrap;gap:8px;">
    <span style="font-weight:700;color:#1e293b;font-size:15px;">&#128100; Mis solicitudes — ciclo completo</span>
    <div style="display:flex;gap:8px;margin-left:auto;align-items:center;">
      <label style="font-size:12px;color:#64748b;">Mostrar:</label>
      <select id="mis-sol-filtro" onchange="loadMisSolicitudes()" style="padding:5px 10px;font-size:12px;border:1px solid #cbd5e1;border-radius:6px;cursor:pointer">
        <option value="abiertas" selected>Abiertas (en ciclo)</option>
        <option value="cerradas">Cerradas (recibidas / canceladas)</option>
        <option value="todas">Todas</option>
      </select>
      <button class="btn bp" onclick="loadMisSolicitudes()" style="padding:6px 14px;font-size:12px;">&#x21BA; Actualizar</button>
    </div>
  </div>
  <div style="padding:8px 0 14px;color:#64748b;font-size:12px;line-height:1.5">
    Aquí ves <b>tus</b> solicitudes con el seguimiento completo: pendiente → aprobada → OC → pagada → en tránsito → recibida.<br>
    Cuando te llegue la mercancía, click <b>✅ Marcar Recibido</b> para cerrar el ciclo sin esperar a Catalina.
  </div>
  <div id="mis-sol-body">
    <div style="color:#94a3b8;text-align:center;padding:40px;">Cargando...</div>
  </div>
</div>

<!-- ════════════ TAB: PLANTA (MP + Empaque agrupado por proveedor) ════════════
     Sebastian 5-may-2026: separación de fuentes — esto es lo que SALE del
     Centro de Programación (calendar.py). Catalina ve aquí TODO lo de planta
     ya agrupado por proveedor, puede editar inline (proveedor / cantidad /
     valor), y los cambios se sincronizan globalmente a maestro_mps +
     mp_lead_time_config + precio_referencia (aplican en TODA la app). -->
<div id="pane-planta" class="pane">
  <div style="display:flex;gap:6px;margin-bottom:16px;border-bottom:2px solid #e2e8f0;padding-top:2px">
    <button type="button" class="sp-tab sp-on" id="sptn-mp" onclick="showSubPlanta('mp')">&#129514; Materias Primas</button>
    <button type="button" class="sp-tab" id="sptn-env" onclick="showSubPlanta('env')">&#128230; Envases</button>
  </div>
  <div id="subplanta-mp">
  <!-- Alertas MP/envases en déficit (Centro de Programación) · 23-jun: movidas desde Solicitudes — son de PLANTA -->
  <div id="mp-alert-banner" style="display:none;background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;padding:10px 14px;margin-bottom:10px;">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <span style="font-size:18px;">&#x26A0;&#xFE0F;</span>
      <div id="mp-alert-text" style="flex:1;font-size:13px;font-weight:600;color:#92400e;"></div>
      <button class="btn" style="background:#f59e0b;color:#fff;font-size:12px;padding:4px 12px;white-space:nowrap;" onclick="openOCSugerida()">&#x1F4CB; Crear OC Sugerida</button>
    </div>
    <div id="mp-alert-list" style="margin-top:6px;display:flex;flex-wrap:wrap;gap:6px;"></div>
  </div>
  <div id="prog-alert-banner" style="display:none;background:#fde8e8;border:1px solid #dc3545;border-radius:8px;padding:10px 14px;margin-bottom:10px;">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <span style="font-size:18px;">&#x1F4E1;</span>
      <div style="flex:1;">
        <div id="prog-alert-text" style="font-size:13px;font-weight:600;color:#7f1d1d;"></div>
        <div style="font-size:11px;color:#991b1b;margin-top:2px;">Centro de Programaci&#xF3;n &mdash; velocidad Shopify + f&#xF3;rmulas + stock MP</div>
      </div>
      <a href="/planta" style="background:#dc3545;color:#fff;font-size:12px;padding:5px 12px;border-radius:5px;text-decoration:none;white-space:nowrap;font-weight:600;">&#x1F4CA; Ver Programaci&#xF3;n</a>
      <button onclick="generarOCDesdeCompras(this)" style="background:#7f1d1d;color:#fff;border:none;border-radius:5px;font-size:12px;padding:5px 12px;cursor:pointer;font-weight:600;white-space:nowrap;">&#x1F6D2; Generar OC</button>
    </div>
  </div>
  <div style="background:#fef9c3;border:1px solid #fde047;border-radius:8px;padding:10px 14px;margin-bottom:10px;display:flex;gap:10px;align-items:flex-start;">
    <span style="font-size:18px;line-height:1;">&#x1F4E1;</span>
    <div style="flex:1;font-size:12px;color:#713f12;line-height:1.5;">
      <b>Pedidos de planta agrupados por proveedor.</b> Vienen del Centro de Programación · Materia Prima + Empaque.
      Editá <b>proveedor / cantidad / valor</b> de cada item · al guardar se sincroniza globalmente con la app
      (maestro_mps, lead time, precio de referencia).
    </div>
  </div>
  <div class="bar" style="flex-wrap:wrap;gap:8px;">
    <input type="text" id="q-planta" placeholder="Buscar SOL, proveedor, MP..." oninput="renderPlanta()" style="flex:1;min-width:220px;">
    <select id="s-planta-estado" onchange="loadPlanta()" title="Estado de la solicitud">
      <option value="Pendiente">Pendiente</option>
      <option value="Aprobada">Aprobada</option>
      <option value="all">Todos</option>
    </select>
    <button class="btn bp" onclick="loadPlanta()" style="padding:6px 14px;font-size:12px;">&#x21BA; Actualizar</button>
    <button class="btn" onclick="limpiarSolsPlantaLegacy()" style="background:#dc2626;color:#fff;font-size:12px;padding:7px 14px;" title="Borra TODAS las SOLs Pendientes de planta sin OC vinculada · útil para borrón y cuenta nueva">&#x1F5D1;&#xFE0F; Limpiar SOLs planta</button>
  </div>
  <div id="planta-kpis" style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;font-size:11px;color:#64748b;"></div>
  <div id="planta-body" style="display:flex;flex-direction:column;gap:12px;">
    <div style="color:#94a3b8;text-align:center;padding:40px;">Cargando...</div>
  </div>
  </div>
  <div id="subplanta-env" style="display:none">
    <iframe id="marcacion-iframe" src="about:blank" style="width:100%;height:86vh;border:none;border-radius:8px" title="Marcación de envases"></iframe>
  </div>
</div>
<script>
function showSubPlanta(w){
  document.getElementById('subplanta-mp').style.display=(w==='mp')?'':'none';
  document.getElementById('subplanta-env').style.display=(w==='env')?'':'none';
  var a=document.getElementById('sptn-mp'),b=document.getElementById('sptn-env');
  if(a)a.className='sp-tab'+(w==='mp'?' sp-on':'');if(b)b.className='sp-tab'+(w==='env'?' sp-on':'');
  if(w==='env'){var f=document.getElementById('marcacion-iframe');if(f&&(f.src||'').indexOf('marcacion-envases')<0)f.src='/admin/marcacion-envases';}
}
</script>

<div id="pane-consol" class="pane">
  <div class="bar" style="flex-wrap:wrap;gap:8px;">
    <div>
      <span style="font-weight:700;color:#1e293b;font-size:15px;">&#x1F4E6; Órdenes de compra activas · agrupadas por proveedor</span>
      <div style="font-size:11px;color:#64748b;margin-top:2px">OCs ya creadas (Borrador / Revisada / Autorizada) · NO la cola de SOLs pendientes (esa va en tab "🏭 Planta")</div>
    </div>
    <button class="btn bp" onclick="openNuevaOC('')" style="background:#16a34a;color:#fff;font-weight:800;padding:8px 18px;font-size:14px;border:none;border-radius:7px;cursor:pointer" title="Crear una orden de compra de CUALQUIER cosa · elegí la categoría (MP, empaque, servicios, EPP, papelería…) + ítems · autorizar al crear va directo a Por Pagar">&#10133; Crear OC</button>
    <div style="display:flex;gap:8px;margin-left:auto;align-items:center;flex-wrap:wrap;">
      <label style="font-size:12px;color:#64748b;">Estados:</label>
      <label style="font-size:12px;"><input type="checkbox" class="consol-est" value="Borrador" checked> Borrador</label>
      <label style="font-size:12px;"><input type="checkbox" class="consol-est" value="Revisada" checked> Revisada</label>
      <label style="font-size:12px;"><input type="checkbox" class="consol-est" value="Autorizada" checked> Autorizada</label>
      <button class="btn bp" onclick="loadConsolidado()" style="padding:6px 14px;font-size:12px;">&#x21BA; Actualizar</button>
      <button class="btn" onclick="imprimirTodas()" style="padding:6px 14px;font-size:12px;background:#0f766e;color:#fff;border:none;border-radius:5px;font-weight:700;cursor:pointer;" title="Imprime TODAS las órdenes juntas (cada proveedor en su propia hoja) en un solo documento">&#x1F5A8; Imprimir todas</button>
      <!-- Sebastián 24-may-2026 · link directo al módulo /recepcion · bodega
           necesita acceso rápido para registrar mercancía que llega · evita
           que tengan que volver a /modulos para encontrarlo. -->
      <a href="/recepcion" target="_blank" rel="noopener" class="btn" style="background:#7c3aed;color:#fff;padding:6px 14px;font-size:12px;font-weight:700;text-decoration:none;border-radius:5px;display:inline-flex;align-items:center;gap:4px" title="Abrir página dedicada de recepción · escaneo lotes · cuarentena · trazabilidad">📦 Ir a Recepción</a>
    </div>
  </div>
  <div id="consol-body" style="padding:16px 0;">
    <div style="color:#94a3b8;text-align:center;padding:40px;">Cargando consolidado...</div>
  </div>
</div>

<!-- ════════════ TAB: POR PAGAR ════════════ -->
<div id="pane-por-pagar" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px;">
    <div>
      <h2 style="margin:0;font-size:18px;color:#1e293b;">&#x1F4B0; Pendiente de pago</h2>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">
        Mercanc&iacute;a recibida + servicios sin recepci&oacute;n (Influencers, Cuentas de Cobro)
      </div>
    </div>
    <div style="display:flex;gap:6px;">
      <button class="btn" onclick="exportOcsConsolidado()" style="padding:6px 14px;font-size:12px;background:#059669;color:#fff;border:0;border-radius:5px;font-weight:700;cursor:pointer;" title="Excel consolidado de todas las OCs activas (estados, info bancaria, recepción, discrepancia)">&#x1F4CA; Excel consolidado</button>
      <button class="btn bp" onclick="loadPorPagar()" style="padding:6px 14px;font-size:12px;">&#x21BA; Actualizar</button>
    </div>
  </div>

  <div id="por-pagar-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:16px;">
    <div style="background:#1e1b4b;border:1px solid #4c1d95;border-radius:10px;padding:14px;">
      <div style="font-size:10px;color:#a78bfa;text-transform:uppercase;letter-spacing:0.05em;">Total pendiente</div>
      <div style="font-size:22px;font-weight:800;color:#fff;" id="por-pagar-total">-</div>
    </div>
    <div style="background:#0c1a4d;border:1px solid #1e3a8a;border-radius:10px;padding:14px;">
      <div style="font-size:10px;color:#93c5fd;text-transform:uppercase;letter-spacing:0.05em;">Mercanc&iacute;a recibida</div>
      <div style="font-size:18px;font-weight:800;color:#fff;" id="por-pagar-merc">-</div>
    </div>
    <div style="background:#3a2a00;border:1px solid #92400e;border-radius:10px;padding:14px;">
      <div style="font-size:10px;color:#fbbf24;text-transform:uppercase;letter-spacing:0.05em;">Pago directo (servicios)</div>
      <div style="font-size:18px;font-weight:800;color:#fff;" id="por-pagar-svc">-</div>
    </div>
  </div>

  <!-- Sección destacada: pagos directos (Influencers) -->
  <div id="por-pagar-directos-wrap" style="display:none;margin-bottom:20px;">
    <div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:10px;padding:14px 16px;margin-bottom:10px;">
      <div style="font-weight:700;color:#92400e;font-size:14px;">&#x1F4B8; Pagos directos (Influencers, Cuentas de Cobro)</div>
      <div style="font-size:11px;color:#78350f;margin-top:4px;">Estas OCs no requieren recepci&oacute;n f&iacute;sica — son servicios listos para pagar.</div>
    </div>
    <div id="por-pagar-directos" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;"></div>
  </div>

  <!-- Mercancía recibida -->
  <div style="margin-bottom:14px;">
    <div style="font-weight:700;color:#1e293b;font-size:14px;margin-bottom:10px;">&#x1F4E6; Mercanc&iacute;a recibida pendiente de pago</div>
    <div id="por-pagar-merc-list" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;">
      <div style="color:#94a3b8;text-align:center;padding:20px;">Cargando...</div>
    </div>
  </div>
</div>

<!-- ════════════ TAB: ATRASADAS · Sebastián 23-may-2026 ════════════ -->
<!-- OCs Autorizada/Parcial sin recibir tras lead_time+buffer · cierre flujo -->
<div id="pane-atrasadas" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px;">
    <div>
      <h2 style="margin:0;font-size:18px;color:#1e293b;">&#x1F6A8; OCs atrasadas</h2>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">
        OCs Autorizada/Parcial sin recibir tras
        <input type="number" id="atrasadas-buffer" value="7" min="0" max="90" style="width:50px;padding:2px 6px;border:1px solid #cbd5e1;border-radius:4px;font-size:12px" onchange="cargarOcsAtrasadas()"> d&iacute;as de buffer sobre el lead_time del proveedor
      </div>
    </div>
    <button class="btn bp" onclick="cargarOcsAtrasadas()" style="padding:6px 14px;font-size:12px;">&#x21BA; Actualizar</button>
  </div>

  <div id="atrasadas-resumen" style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;font-size:12px;color:#475569"></div>
  <div id="atrasadas-contenido" style="background:white;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto">
    <div style="text-align:center;color:#94a3b8;padding:30px">Click &#x21BA; Actualizar para cargar</div>
  </div>
</div>

<!-- ════════════ TAB: CALIDAD RECEPCIÓN · Sebastián 23-may-2026 ════════════ -->
<!-- Histórico de OCs recibidas con discrepancia + ranking proveedores -->
<div id="pane-discrep" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px;">
    <div>
      <h2 style="margin:0;font-size:18px;color:#1e293b;">&#x1F4CB; Calidad de recepción</h2>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">
        OCs recibidas con faltante en últimos
        <input type="number" id="discrep-dias" value="30" min="7" max="365" style="width:50px;padding:2px 6px;border:1px solid #cbd5e1;border-radius:4px;font-size:12px" onchange="cargarDiscrepancias()"> d&iacute;as &middot;
        ranking proveedores por tasa de discrepancia
      </div>
    </div>
    <button class="btn bp" onclick="cargarDiscrepancias()" style="padding:6px 14px;font-size:12px;">&#x21BA; Actualizar</button>
  </div>

  <div id="discrep-resumen" style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;font-size:12px;color:#475569"></div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px">
    <!-- Ranking proveedores -->
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px;">
      <div style="font-weight:700;font-size:13px;color:#1e293b;margin-bottom:10px;">&#x1F3C6; Ranking proveedores (tasa discrepancia)</div>
      <div id="discrep-ranking" style="font-size:12px;max-height:340px;overflow-y:auto">Cargando&hellip;</div>
    </div>
    <!-- Tip educativo -->
    <div style="background:#eff6ff;border:1px solid #93c5fd;border-radius:10px;padding:14px;font-size:12px;color:#1e40af">
      <div style="font-weight:700;margin-bottom:6px">&#x1F4A1; C&oacute;mo se detectan</div>
      <div>1. Receptor marca <strong>tiene_discrepancias</strong> en /recibir</div>
      <div>2. <strong>Auto-detecci&oacute;n</strong>: si alg&uacute;n item recibe &lt;95% de lo pedido, sistema marca discrepancia + push_notif a creador OC + admins</div>
      <div style="margin-top:6px;color:#64748b">Cron diario notifica OCs atrasadas. Pesta&ntilde;a vecina 🚨 Atrasadas.</div>
    </div>
  </div>

  <div id="discrep-contenido" style="background:white;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto">
    <div style="text-align:center;color:#94a3b8;padding:30px">Click &#x21BA; Actualizar</div>
  </div>
</div>

<!-- ════════════ TAB: MAILBOX FACTURAS · Sebastián 23-may-2026 ════════════ -->
<!-- Facturas detectadas por cron mailbox IMAP · admin las completa o descarta -->
<div id="pane-mailbox" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px;">
    <div>
      <h2 style="margin:0;font-size:18px;color:#1e293b;">&#x1F4E7; Mailbox facturas proveedor</h2>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">
        Facturas detectadas por el cron IMAP (compras@hhagroup.co) ·
        ventana
        <input type="number" id="mailbox-dias" value="30" min="7" max="180" style="width:50px;padding:2px 6px;border:1px solid #cbd5e1;border-radius:4px;font-size:12px" onchange="cargarMailbox()"> d&iacute;as
      </div>
    </div>
    <button class="btn bp" onclick="cargarMailbox()" style="padding:6px 14px;font-size:12px;">&#x21BA; Actualizar</button>
  </div>

  <div id="mailbox-resumen" style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;font-size:12px;color:#475569"></div>
  <div id="mailbox-contenido" style="background:white;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto">
    <div style="text-align:center;color:#94a3b8;padding:30px">Click &#x21BA; Actualizar</div>
  </div>
</div>

<!-- ════════════ TAB: COTIZACIONES · Sebastián 23-may-2026 PM ════════════ -->
<!-- Comparador lado-a-lado · backend listo desde mig 29 · solo faltaba UI -->
<div id="pane-cotiz" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px;">
    <div>
      <h2 style="margin:0;font-size:18px;color:#1e293b;">&#x1F4AC; Rondas de cotizaciones</h2>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">
        Compar&aacute; precios de hasta 3 proveedores lado a lado &middot; eleg&iacute; ganadora &middot; gener&aacute; OC autom&aacute;ticamente.
      </div>
    </div>
    <button class="btn bp" onclick="cargarCotizaciones()" style="padding:6px 14px;font-size:12px;">&#x21BA; Actualizar</button>
  </div>
  <div id="cotiz-resumen" style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;font-size:12px;color:#475569"></div>
  <div id="cotiz-contenido" style="background:white;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto">
    <div style="text-align:center;color:#94a3b8;padding:30px">Click &#x21BA; Actualizar</div>
  </div>
</div>

<!-- ════════════ TAB: ALERTAS ════════════ -->
<div id="pane-alertas" class="pane">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px;">
    <div>
      <h2 style="margin:0;font-size:18px;color:#1e293b;">&#x1F6A8; Alertas vivas de Compras</h2>
      <div style="font-size:12px;color:#64748b;margin-top:2px;">
        Lo que requiere atenci&oacute;n hoy. Revisa cada secci&oacute;n y ataca las cr&iacute;ticas primero.
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
      <span id="alertas-sev-pill" style="padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700;background:#e2e8f0;color:#64748b;">cargando...</span>
      <button class="btn bp" onclick="loadAlertasCompras()" style="padding:6px 14px;font-size:12px;">&#x21BA; Actualizar</button>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;">
    <!-- Card 1: OCs sin recibir -->
    <div style="background:#fff;border:1px solid #fcd34d;border-radius:12px;padding:14px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="font-weight:700;font-size:13px;color:#92400e;">&#x23F3; OCs sin recibir &gt; 15 d&iacute;as</div>
        <span id="alertas-sin-recibir-count" style="background:#f59e0b;color:#fff;border-radius:12px;padding:2px 10px;font-size:11px;font-weight:700;">0</span>
      </div>
      <div id="alertas-sin-recibir" style="font-size:12px;color:#1e293b;max-height:280px;overflow-y:auto;">Cargando...</div>
    </div>

    <!-- Card 2: Pagos por vencer -->
    <div style="background:#fff;border:1px solid #fca5a5;border-radius:12px;padding:14px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="font-weight:700;font-size:13px;color:#7f1d1d;">&#x1F4B5; Pagos por vencer</div>
        <span id="alertas-pagos-vencer-count" style="background:#dc2626;color:#fff;border-radius:12px;padding:2px 10px;font-size:11px;font-weight:700;">0</span>
      </div>
      <div id="alertas-pagos-vencer" style="font-size:12px;color:#1e293b;max-height:280px;overflow-y:auto;">Cargando...</div>
    </div>

    <!-- Card 3: Solicitudes Pendientes -->
    <div style="background:#fff;border:1px solid #93c5fd;border-radius:12px;padding:14px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="font-weight:700;font-size:13px;color:#1e3a8a;">&#x1F4DD; Solicitudes pendientes &gt; 3 d&iacute;as</div>
        <span id="alertas-solic-count" style="background:#3b82f6;color:#fff;border-radius:12px;padding:2px 10px;font-size:11px;font-weight:700;">0</span>
      </div>
      <div id="alertas-solic" style="font-size:12px;color:#1e293b;max-height:280px;overflow-y:auto;">Cargando...</div>
    </div>

    <!-- Card 4: Borradores estancados -->
    <div style="background:#fff;border:1px solid #d4d4d8;border-radius:12px;padding:14px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="font-weight:700;font-size:13px;color:#52525b;">&#x1F4D1; OCs Borrador &gt; 7 d&iacute;as</div>
        <span id="alertas-borrador-count" style="background:#71717a;color:#fff;border-radius:12px;padding:2px 10px;font-size:11px;font-weight:700;">0</span>
      </div>
      <div id="alertas-borrador" style="font-size:12px;color:#1e293b;max-height:280px;overflow-y:auto;">Cargando...</div>
    </div>
  </div>
</div>
<!-- MODAL: Proveedor 360 -->
<div id="m-ficha360" class="ov">
<div class="mdl mdl-lg" style="max-width:780px;max-height:88vh;overflow-y:auto;">
  <div class="mh"><h3>&#x1F4CA; Proveedor 360</h3><button class="mx" onclick="closeModal('m-ficha360')">&times;</button></div>
  <div class="mb" id="ficha360-content" style="padding:0 4px;">
    <div style="text-align:center;color:#a8a29e;padding:40px;">Cargando ficha...</div>
  </div>
  <div class="mf" id="ficha360-footer" style="gap:8px;justify-content:flex-end;"></div>
</div>
</div>

<!-- MODAL: Nueva OC -->
<div id="m-noc" class="ov">
<div class="mdl mdl-lg">
  <div class="mh mh-ent">
    <div>
      <h3 id="noc-title">&#x1F4DD; Nueva Orden de Compra</h3>
      <div id="noc-cat-pills" class="cat-pills"></div>
    </div>
    <button class="mx" onclick="closeModal('m-noc')">&times;</button>
  </div>
  <div class="mb">
    <input type="hidden" id="noc-cat" value="MP">
    <div class="g2">
      <div class="fg">
        <label id="noc-prov-lbl">Proveedor</label>
        <select id="noc-prov" onchange="fillProv('noc-prov','noc-ibox')"><option value="">-- Seleccionar --</option></select>
        <input type="text" id="noc-prov-txt" list="prov-dl" placeholder="Nombre del proveedor o beneficiario" style="display:none">
        <datalist id="prov-dl"></datalist>
        <div id="noc-add-prov-link" style="display:none;margin-top:4px;">
          <button type="button" class="btn bo" style="font-size:11px;padding:3px 10px;" onclick="showNewProvForm()">&#x2795; Crear proveedor nuevo</button>
        </div>
        <div id="noc-ibox" class="ibox" style="display:none"></div>
        <div id="noc-new-prov-form" style="display:none;background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:12px;margin-top:8px;">
          <div style="font-weight:700;font-size:12px;color:#166534;margin-bottom:8px;">&#x2795; Nuevo Proveedor (form completo · queda cargado para todo el sistema)</div>
          <div id="np-dup-warning" style="display:none;background:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:8px 10px;margin-bottom:8px;font-size:11px;color:#92400e;"></div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
            <div><label style="font-size:11px;font-weight:600;">Nombre *</label><input id="np-nombre" placeholder="Razon social o nombre" oninput="checkProvDuplicado()" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:600;">NIT / Cedula</label><input id="np-nit" placeholder="NIT" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:600;">Contacto</label><input id="np-contacto" placeholder="Persona de contacto" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:600;">Telefono</label><input id="np-tel" placeholder="Telefono" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:600;">Email</label><input id="np-email" placeholder="Email" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:600;">Direccion</label><input id="np-direccion" placeholder="Direccion completa" style="width:100%"></div>
          </div>
          <div style="font-weight:700;font-size:11px;color:#166534;margin:6px 0 4px;">Datos bancarios (para pagos)</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
            <div><label style="font-size:11px;font-weight:600;">Banco</label><input id="np-banco" placeholder="Bancolombia, Davivienda..." style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:600;">Tipo cuenta</label><select id="np-tipo-cuenta" style="width:100%;padding:6px 8px;border:1px solid #d6d3d1;border-radius:6px;font-size:12px;"><option value="">Seleccionar...</option><option value="Ahorros">Ahorros</option><option value="Corriente">Corriente</option><option value="Nequi">Nequi</option><option value="Daviplata">Daviplata</option></select></div>
            <div><label style="font-size:11px;font-weight:600;">Numero de cuenta</label><input id="np-num-cuenta" placeholder="Numero de cuenta o celular" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:600;">Condiciones pago</label><select id="np-cond-pago" style="width:100%;padding:6px 8px;border:1px solid #d6d3d1;border-radius:6px;font-size:12px;"><option value="Contado">Contado</option><option value="15 dias">15 dias</option><option value="30 dias" selected>30 dias</option><option value="45 dias">45 dias</option><option value="60 dias">60 dias</option></select></div>
          </div>
          <div style="margin-bottom:8px;"><label style="font-size:11px;font-weight:600;">Concepto de compra</label><input id="np-concepto" placeholder="Ej: Materias primas cosmeticas" style="width:100%"></div>
          <div style="display:flex;gap:8px;">
            <button class="btn bg" style="font-size:12px;" onclick="guardarNuevoProv()">Guardar proveedor</button>
            <button class="btn bo" style="font-size:12px;" onclick="cancelarNuevoProv()">Cancelar</button>
          </div>
        </div>
        <div id="noc-cc-pago" style="display:none;background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:12px;margin-top:8px;">
          <div style="font-weight:700;font-size:12px;color:#92400e;margin-bottom:8px;">&#x1F4B3; Datos bancarios del beneficiario</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
            <div><label style="font-size:11px;font-weight:600;">Banco *</label><input id="noc-cc-banco" placeholder="Bancolombia, Davivienda..." style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:600;">Tipo de cuenta</label><select id="noc-cc-tipo" style="width:100%;padding:6px 8px;border:1px solid #d6d3d1;border-radius:6px;font-size:12px;"><option value="Ahorros">Ahorros</option><option value="Corriente">Corriente</option><option value="Ahorros Damas">Ahorros Damas</option><option value="Nequi / Daviplata">Nequi / Daviplata</option></select></div>
            <div><label style="font-size:11px;font-weight:600;">N\u00BA de cuenta / Cel</label><input id="noc-cc-cuenta" placeholder="Numero de cuenta" style="width:100%"></div>
            <div><label style="font-size:11px;font-weight:600;">NIT / CC</label><input id="noc-cc-nit" placeholder="Documento de identidad" style="width:100%"></div>
          </div>
        </div>
      </div>
      <div class="fg"><label>Fecha entrega est.</label><input type="date" id="noc-fent"></div>
    </div>
    <div class="fg"><label>Concepto / Observaciones</label><textarea id="noc-obs" placeholder="Descripcion del pedido..."></textarea></div>
    <div>
      <label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:6px;">Items del pedido</label>
      <datalist id="mp-noc-dl"></datalist>
      <table class="itbl"><thead><tr><th>Codigo</th><th>Descripcion</th><th>Cantidad</th><th>Precio U.</th><th>Subtotal</th><th></th></tr></thead>
      <tbody id="noc-tbody"></tbody></table>
      <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;">
        <button class="btn bo bs" onclick="addRow()">+ Item</button>
        <button class="btn bs" style="background:#10b981;color:#fff;border-color:#10b981;font-weight:600;" onclick="abrirNuevaMP()" title="Crear MP nueva sin cerrar la OC">+ Nueva MP</button>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;margin:10px 0 4px;">
      <input type="checkbox" id="noc-iva-chk" onchange="calcTot()" style="width:16px;height:16px;cursor:pointer;">
      <label for="noc-iva-chk" style="cursor:pointer;font-weight:600;font-size:13px;">Aplica IVA (19%)</label>
    </div>
    <div id="noc-iva-row" style="display:none;background:#fefce8;border:1px solid #fde047;border-radius:6px;padding:8px 12px;font-size:12px;margin-bottom:4px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:2px;"><span>Subtotal sin IVA</span><span id="noc-sub">$0</span></div>
      <div style="display:flex;justify-content:space-between;margin-bottom:2px;color:#92400e;"><span>IVA 19%</span><span id="noc-iva-monto">$0</span></div>
      <div style="display:flex;justify-content:space-between;font-weight:700;border-top:1px solid #fde047;padding-top:4px;"><span>Total con IVA</span><span id="noc-iva-total">$0</span></div>
    </div>
    <div class="total-row">Total: <span id="noc-tot">$0</span></div>
  </div>
  <div class="mf">
    <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:#475569;margin-right:auto;cursor:pointer" title="Autoriza la OC al crearla → va directo a Por Pagar (dentro de tu límite). Si el monto la excede, queda en Borrador para gerencia.">
      <input type="checkbox" id="noc-autorizar" checked> Autorizar al crear (va directo a Por Pagar)
    </label>
    <button class="btn bo" onclick="closeModal('m-noc')">Cancelar</button>
    <button class="btn bp" id="noc-submit-btn" onclick="submitOC()">Crear OC</button>
  </div>
</div>
</div>

<!-- MODAL: Revisar y Asignar -->
<div id="m-rev" class="ov">
<div class="mdl">
  <div class="mh"><h3>&#x270F; Revisar &amp; Asignar</h3><button class="mx" onclick="closeModal('m-rev')">&times;</button></div>
  <div class="mb">
    <div id="rev-info" style="background:#f9f8f7;border:1px solid #e7e5e4;border-radius:6px;padding:10px;font-size:13px;"></div>
    <div class="fg">
      <label>Proveedor / Beneficiario</label>
      <select id="rev-prov" onchange="fillProv('rev-prov','rev-ibox')"><option value="">-- Seleccionar --</option></select>
      <div id="rev-ibox" class="ibox" style="display:none"></div>
    </div>
    <div class="g2">
      <div class="fg"><label>Valor base / subtotal ($)</label><input type="number" id="rev-val" min="0" step="0.01" placeholder="0" oninput="calcRevIva()"></div>
      <div class="fg"><label>Fecha entrega</label><input type="date" id="rev-fent"></div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;margin:6px 0 2px;">
      <input type="checkbox" id="rev-iva-chk" onchange="calcRevIva()" style="width:16px;height:16px;cursor:pointer;">
      <label for="rev-iva-chk" style="cursor:pointer;font-weight:600;font-size:13px;">Aplica IVA (19%)</label>
    </div>
    <div id="rev-iva-breakdown" style="display:none;background:#fefce8;border:1px solid #fde047;border-radius:6px;padding:8px 12px;font-size:12px;margin-bottom:4px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:2px;"><span>Subtotal</span><span id="rev-iva-sub">$0</span></div>
      <div style="display:flex;justify-content:space-between;margin-bottom:2px;color:#92400e;"><span>IVA 19%</span><span id="rev-iva-monto">$0</span></div>
      <div style="display:flex;justify-content:space-between;font-weight:700;border-top:1px solid #fde047;padding-top:4px;"><span>Total con IVA</span><span id="rev-iva-total">$0</span></div>
    </div>
    <div class="fg"><label>Observaciones</label><textarea id="rev-obs" placeholder="Notas de revision..."></textarea></div>
    <input type="hidden" id="rev-num">
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-rev')">Cancelar</button>
    <button class="btn bw" onclick="confirmarRev()">Marcar Revisada</button>
  </div>
</div>
</div>

<!-- MODAL: Registrar Pago -->
<div id="m-pago" class="ov">
<div class="mdl">
  <div class="mh"><h3>&#x1F4B8; Registrar Pago</h3><button class="mx" onclick="closeModal('m-pago')">&times;</button></div>
  <div class="mb">
    <div id="pago-info" style="background:#f9f8f7;border:1px solid #e7e5e4;border-radius:6px;padding:10px;font-size:13px;"></div>
    <div class="g2">
      <div class="fg"><label>Monto Pagado ($)</label><input type="number" id="pago-monto" min="0" step="0.01" placeholder="0"></div>
      <div class="fg"><label>Medio de Pago</label>
        <select id="pago-medio"><option>Transferencia</option><option>Efectivo</option><option>Cheque</option><option>PSE</option><option>Nequi</option></select>
      </div>
    </div>
    <div class="fg">
      <label>&#x1F4C4; N&uacute;mero factura proveedor (3-way matching)</label>
      <input type="text" id="pago-factura" placeholder="Ej: FAC-12345" style="text-transform:uppercase;">
      <div style="font-size:11px;color:#64748b;margin-top:3px;">Si esta factura ya fue usada en otro pago, el sistema te avisa antes de continuar.</div>
    </div>
    <!-- Toggles fiscales (retefuente/retica/IVA) — para legalidad -->
    <div class="fg" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 12px;">
      <label style="display:block;font-weight:700;color:#1e293b;margin-bottom:6px;">&#x1F4CA; Retenciones e IVA (opcional)</label>
      <div style="display:flex;gap:14px;flex-wrap:wrap;font-size:12px;">
        <label style="display:flex;align-items:center;gap:6px;cursor:pointer;">
          <input type="checkbox" id="pago-aplicar-retefuente"> Aplicar ReteFuente 10%
        </label>
        <label style="display:flex;align-items:center;gap:6px;cursor:pointer;">
          <input type="checkbox" id="pago-aplicar-retica"> Aplicar ReteICA 0.66 x mil (Cali)
        </label>
        <label style="display:flex;align-items:center;gap:6px;cursor:pointer;">
          <input type="checkbox" id="pago-aplicar-iva"> Aplicar IVA 19%
        </label>
      </div>
      <div style="font-size:11px;color:#64748b;margin-top:6px;">
        Por defecto NO se aplican (pago bruto al proveedor). Activa solo cuando corresponda fiscalmente.
      </div>
    </div>
    <div class="fg"><label>Comprobante / Referencia</label><textarea id="pago-obs" rows="2" placeholder="No. transaccion, referencia..."></textarea></div>
    <div class="fg"><label>&#x1F5BC; Captura de transferencia (opcional)</label>
      <input type="file" id="pago-img-file" accept="image/*" onchange="previewPagoImg()" style="display:block;margin-bottom:6px;font-size:12px;">
      <img id="pago-img-preview" src="" alt="" style="display:none;max-width:100%;max-height:160px;border-radius:6px;border:1px solid #e7e5e4;">
    </div>
    <!-- Historial de pagos previos (pagos parciales) -->
    <div id="pago-historial" style="display:none;margin-top:10px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:10px;">
      <div style="font-size:12px;font-weight:700;color:#1e293b;margin-bottom:6px;">&#x1F4DC; Pagos previos de esta OC</div>
      <div id="pago-historial-list" style="font-size:11px;color:#64748b;"></div>
    </div>
    <input type="hidden" id="pago-num">
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-pago')">Cancelar</button>
    <button class="btn bg" onclick="confirmarPago()">Registrar Pago</button>
  </div>
</div>
</div>

<!-- MODAL: Nuevo Proveedor -->
<div id="m-nprov" class="ov">
<div class="mdl mdl-lg">
  <div class="mh"><h3>&#x1F3ED; Nuevo Proveedor</h3><button class="mx" onclick="closeModal('m-nprov')">&times;</button></div>
  <div class="mb">
    <div class="g2">
      <div class="fg"><label>Nombre / Razon Social *</label><input id="np-nom" placeholder="EMPRESA SAS"></div>
      <div class="fg"><label>NIT / CC</label><input id="np-nit" placeholder="800.000.000-0"></div>
    </div>
    <div class="g2">
      <div class="fg"><label>Categoria</label><select id="np-cat"><option value="MP">Mat. Primas</option><option value="MEE">Empaque</option><option value="Servicios">Servicios</option><option value="General">General</option></select></div>
      <div class="fg"><label>Condiciones de Pago</label><select id="np-cond"><option>Contado</option><option>15 dias</option><option>30 dias</option><option>45 dias</option><option>60 dias</option></select></div>
    </div>
    <div class="g2">
      <div class="fg"><label>Contacto</label><input id="np-ctc" placeholder="Nombre representante"></div>
      <div class="fg"><label>Telefono</label><input id="np-tel" placeholder="300 000 0000"></div>
    </div>
    <div class="g2">
      <div class="fg"><label>Email</label><input id="np-email" type="email" placeholder="ventas@empresa.co"></div>
      <div class="fg"><label>Direccion</label><input id="np-dir" placeholder="Calle / Carrera..."></div>
    </div>
    <div class="g2">
      <div class="fg"><label>Banco</label><input id="np-banco" placeholder="Bancolombia..."></div>
      <div class="fg"><label>Tipo Cuenta</label><select id="np-tcta"><option>Ahorros</option><option>Corriente</option></select></div>
    </div>
    <div class="g2">
      <div class="fg"><label>No. Cuenta</label><input id="np-ncta" placeholder="000-000000-00"></div>
      <div class="fg"><label>Concepto habitual</label><input id="np-conc" placeholder="Compra materias primas..."></div>
    </div>
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-nprov')">Cancelar</button>
    <button class="btn bp" onclick="crearProv()">Guardar</button>
  </div>
</div>
</div>


<!-- MODAL: Detalle OC -->
<div id="m-oc-det" class="ov">
<div class="mdl mdl-lg">
  <div class="mh"><h3>&#128203; Detalle Orden de Compra</h3><button class="mx" onclick="closeModal('m-oc-det')">&times;</button></div>
  <div class="mb" id="oc-det-body" style="padding:0 4px;"><div style="text-align:center;padding:40px;color:#78716c;">Cargando...</div></div>
  <div class="mf" id="oc-det-footer">
    <button class="btn bo" onclick="closeModal('m-oc-det')">Cerrar</button>
  </div>
</div>
</div>

<!-- MODAL: Aprobar / Rechazar OC -->
<div id="m-aut" class="ov">
<div class="mdl">
  <div class="mh"><h3>&#9997; Decision sobre OC</h3><button class="mx" onclick="closeModal('m-aut')">&times;</button></div>
  <div class="mb">
    <div id="m-aut-info" style="background:#f9f8f7;border:1px solid #e7e5e4;border-radius:6px;padding:10px;font-size:13px;margin-bottom:4px;"></div>
    <div class="fg"><label>Motivo / Comentario (recomendado)</label>
      <textarea id="aut-motivo" placeholder="Razon de la aprobacion o rechazo..." rows="3"></textarea>
    </div>
    <input type="hidden" id="aut-num">
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-aut')">Cancelar</button>
    <button class="btn" style="background:#dc2626;color:#fff;font-weight:700;" onclick="decidirOC('Rechazada')">&#10005; Rechazar</button>
    <button class="btn bi" onclick="decidirOC('Autorizada')">&#10003; Autorizar</button>
  </div>
</div>
</div>

<!-- MODAL: Cambiar proveedor de UNA MP del catalogo -->
<div id="m-edit-prov-mp" class="ov" style="z-index:10000;">
<div class="mdl" style="max-width:480px;width:96vw;">
  <div style="background:#1F5F5B;color:#fff;padding:14px 18px;border-radius:14px 14px 0 0;display:flex;justify-content:space-between;align-items:center;">
    <h3 style="color:#fff;margin:0;font-size:16px;">&#9999;&#65039; Cambiar proveedor de la MP</h3>
    <button onclick="closeModal('m-edit-prov-mp')" style="background:none;border:none;color:#fff;font-size:22px;cursor:pointer;">&times;</button>
  </div>
  <div class="mb" style="padding:18px;">
    <div style="background:#f0fdfa;border:1px solid #99f6e4;border-radius:8px;padding:10px 14px;margin-bottom:12px;">
      <div style="font-size:11px;color:#0f766e;font-weight:700;text-transform:uppercase;letter-spacing:.5px;">MP</div>
      <div id="epm-info" style="font-weight:700;color:#0f172a;font-size:14px;">&mdash;</div>
      <div id="epm-prov-actual" style="color:#64748b;font-size:12px;margin-top:2px;">&mdash;</div>
    </div>
    <p style="font-size:12px;color:#64748b;margin-bottom:6px;">Solo afecta la MP seleccionada en el cat&aacute;logo (maestro_mps). Las dem&aacute;s MPs de la solicitud no se tocan. Audit log captura el cambio.</p>
    <div style="margin-bottom:10px;">
      <label style="font-size:12px;color:#374151;font-weight:600;display:block;margin-bottom:4px;">Proveedor *</label>
      <input type="text" id="epm-input" list="prov-dl" placeholder="Selecciona o escribe nuevo" autocomplete="off" style="width:100%;padding:8px 12px;border:1px solid #d6d3d1;border-radius:8px;font-size:13px;">
      <small id="epm-hint" style="color:#94a3b8;font-size:11px;display:block;margin-top:4px;">Usa el desplegable para evitar duplicados por typo.</small>
    </div>
    <div style="display:flex;gap:8px;">
      <button onclick="guardarProvItemMP()" style="flex:1;background:#0f766e;color:#fff;border:none;border-radius:8px;padding:9px;font-weight:700;cursor:pointer;">&#10003; Guardar</button>
      <button onclick="closeModal('m-edit-prov-mp')" style="flex:1;background:#e7e5e4;color:#374151;border:none;border-radius:8px;padding:9px;cursor:pointer;">Cancelar</button>
    </div>
    <div id="epm-msg" style="margin-top:10px;font-size:12px;"></div>
  </div>
</div>
</div>

<!-- MODAL: Detalle Solicitud (Catalina) -->
<div id="m-sol-det" class="ov">
<div class="mdl" style="max-width:1200px;width:96vw;max-height:94vh;overflow-y:auto;position:relative;">
  <div class="mh" style="display:none;"><h3>&#128203; Solicitud de Compra</h3><button class="mx" onclick="closeModal('m-sol-det')">&times;</button></div>
  <button onclick="closeModal('m-sol-det')" style="position:absolute;top:14px;right:16px;background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.3);color:#fff;width:34px;height:34px;border-radius:50%;cursor:pointer;font-size:20px;font-weight:700;z-index:10;display:flex;align-items:center;justify-content:center;">&times;</button>
  <div class="mb" id="sol-det-body" style="padding:0;"><div style="text-align:center;padding:60px 40px;color:#78716c;">Cargando...</div></div>
  <div class="mf" id="sol-det-footer" style="padding:14px 26px;background:#fafaf9;border-top:1px solid #e7e5e4;">
    <button class="btn bo" onclick="closeModal('m-sol-det')">Cerrar</button>
  </div>
</div>
</div>

<!-- MODAL: Nueva OC Materias Primas (con catalogo) -->
<div id="m-noc-mp" class="ov">
<div class="mdl mdl-lg">
  <div class="mh"><h3>&#x1F9EA; Nueva OC &#x2014; Materias Primas</h3><button class="mx" onclick="closeModal('m-noc-mp')">&times;</button></div>
  <div class="mb">
    <div id="nmp-alert-info" style="display:none;background:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:8px 12px;margin-bottom:10px;font-size:12px;color:#92400e;"></div>
    <div class="fg" style="margin-bottom:12px;">
      <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Proveedor</label>
      <select id="nmp-prov" onchange="fillProv('nmp-prov','nmp-ibox')" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;"></select>
      <div id="nmp-ibox" class="ibox" style="display:none;margin-top:6px;"></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">
      <div>
        <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Fecha entrega estimada</label>
        <input type="date" id="nmp-fent" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
      </div>
      <div>
        <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Observaciones</label>
        <input type="text" id="nmp-obs" placeholder="Opcional..." style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
      </div>
    </div>
    <datalist id="mp-codes-dl"></datalist>
    <table style="width:100%;border-collapse:collapse;font-size:12px;">
      <thead><tr style="background:#f5f5f4;font-weight:600;color:#44403c;">
        <th style="padding:6px 4px;text-align:left;width:100px;">Codigo MP</th>
        <th style="padding:6px 4px;text-align:left;">Material</th>
        <th style="padding:6px 4px;text-align:center;width:85px;">Cant (g)</th>
        <th style="padding:6px 4px;text-align:center;width:90px;">Precio/g</th>
        <th style="padding:6px 4px;text-align:right;width:85px;">Subtotal</th>
        <th style="padding:6px 4px;width:30px;"></th>
      </tr></thead>
      <tbody id="nmp-tbody"></tbody>
    </table>
    <div style="display:flex;align-items:center;justify-content:space-between;margin-top:10px;flex-wrap:wrap;gap:8px;">
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <button class="btn bo" style="font-size:12px;" onclick="addRowMP(null)">+ Agregar item</button>
        <button class="btn bo" style="font-size:12px;background:#10b981;color:#fff;border-color:#10b981;" onclick="abrirNuevaMP()" title="Crear MP nueva sin salir del form">+ Nueva MP</button>
      </div>
      <div style="font-size:15px;font-weight:700;color:#1c1917;">Total: <span id="nmp-tot">$0</span></div>
    </div>
  </div>
  <div class="mf">
    <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:#475569;margin-right:auto;cursor:pointer" title="Si lo dejás marcado, la OC se autoriza al crearla y va directo a Por Pagar (dentro de tu límite). Si el monto la excede, queda en Borrador para que la apruebe gerencia.">
      <input type="checkbox" id="noc-mp-autorizar" checked> Autorizar al crear (va directo a Por Pagar)
    </label>
    <button class="btn bo" onclick="closeModal('m-noc-mp')">Cancelar</button>
    <button class="btn bp" onclick="crearOCMP()">&#x2713; Crear Orden de Compra</button>
  </div>
</div>
</div>

<!-- MODAL: Nueva MP rapida (Catalina · 4-may-2026) -->
<div id="m-nueva-mp" class="ov">
<div class="mdl">
  <div class="mh"><h3>&#x1F195; Nueva Materia Prima</h3><button class="mx" onclick="closeModal('m-nueva-mp')">&times;</button></div>
  <div class="mb">
    <div style="background:#f0f9ff;border-left:4px solid #0e7490;padding:10px 14px;border-radius:6px;margin-bottom:14px;font-size:12px;color:#0c4a6e;">
      💡 Crea una MP nueva sin salir del form de OC. Los precios y stock que ingreses despues quedaran cargados en planta.
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">
      <div>
        <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Codigo MP *</label>
        <input id="nmp-codigo" placeholder="MP-NUEVA-001" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;text-transform:uppercase;">
      </div>
      <div>
        <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Tipo material *</label>
        <select id="nmp-tipomat" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
          <option value="MP">Materia Prima</option>
          <option value="Envase Primario">Envase Primario</option>
          <option value="Envase Secundario">Envase Secundario</option>
          <option value="Empaque">Empaque</option>
        </select>
      </div>
    </div>
    <div style="margin-bottom:10px;">
      <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Nombre comercial *</label>
      <input id="nmp-nomcomer" placeholder="Ej: Glicerina vegetal USP" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
    </div>
    <div style="margin-bottom:10px;">
      <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Nombre INCI (opcional)</label>
      <input id="nmp-nominci" placeholder="Glycerin" oninput="checkInciNuevaMP()" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
      <div id="nmp-inci-warn" style="font-size:12px;margin-top:4px;"></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">
      <div>
        <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Tipo (categoria)</label>
        <input id="nmp-tipo" placeholder="Ej: Humectante, Surfactante..." style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
      </div>
      <div>
        <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Proveedor preferido</label>
        <input id="nmp-prov-pref" placeholder="(opcional)" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">
      <div>
        <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Stock minimo (g)</label>
        <input id="nmp-stockmin" type="number" min="0" placeholder="0" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
      </div>
      <div>
        <label style="font-size:12px;font-weight:600;color:#57534e;display:block;margin-bottom:4px;">Precio referencia ($/g)</label>
        <input id="nmp-precio" type="number" min="0" step="0.001" placeholder="0" style="width:100%;padding:8px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">
      </div>
    </div>
    <div id="nmp-msg" style="font-size:12px;margin-top:8px;"></div>
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-nueva-mp')">Cancelar</button>
    <button class="btn bp" onclick="guardarNuevaMP()">&#x2713; Crear MP</button>
  </div>
</div>
</div>

<!-- MODAL: OC Sugerida desde alertas de stock -->
<div id="m-oc-sug" class="ov">
<div class="mdl mdl-lg" style="max-width:980px;">
  <div class="mh"><h3>&#x26A0;&#xFE0F; OC Sugerida &#x2014; MPs Bajo Stock</h3><button class="mx" onclick="closeModal('m-oc-sug')">&times;</button></div>
  <div class="mb">
    <div style="font-size:12px;color:#78716c;margin-bottom:12px;">Cantidades incluyen 20% buffer sobre deficit. Ajusta, selecciona proveedor y crea cada OC individualmente &#x2014; o usa <strong>Crear Todas</strong> para agrupar por proveedor automaticamente.</div>
    <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:12px;">
      <thead><tr style="background:#fef3c7;font-weight:600;color:#78350f;">
        <th style="padding:6px 8px;text-align:left;">Material</th>
        <th style="padding:6px 4px;text-align:right;width:72px;">Stock</th>
        <th style="padding:6px 4px;text-align:right;width:68px;">Deficit</th>
        <th style="padding:6px 4px;text-align:center;width:95px;">Cant. (g)</th>
        <th style="padding:6px 4px;text-align:center;width:78px;">$/g</th>
        <th style="padding:6px 4px;text-align:left;width:200px;">Proveedor</th>
        <th style="padding:6px 4px;text-align:right;width:82px;">Subtotal</th>
        <th style="padding:6px 4px;text-align:center;width:84px;">Accion</th>
      </tr></thead>
      <tbody id="sug-tbody"></tbody>
    </table>
    </div>
    <div style="display:flex;justify-content:flex-end;margin-top:10px;font-size:15px;font-weight:700;color:#1c1917;">
      Total: <span id="sug-tot" style="margin-left:6px;">$0</span>
    </div>
  </div>
  <div class="mf">
    <button class="btn bo" onclick="closeModal('m-oc-sug')">Cancelar</button>
    <button class="btn bp" onclick="crearOCSugerida()">&#x1F4E6; Crear Todas (por proveedor)</button>
  </div>
</div>
</div>

<button class="fab" id="fab-btn" onclick="openNuevaOC('')" title="Nueva OC">+</button>

<script>
// ── CSRF defense-in-depth · Sebastian 3-may-2026 ──────────────────
// FIX 31-may-2026 · el token vive en la sesión del servidor (no en una cookie
// legible por JS) y se obtiene de /api/csrf-token. Antes _csrf() leía la cookie
// (vacía) y la carga inicial descartaba la respuesta → los endpoints /api/admin/*
// (ej. fusionar proveedores) rechazaban con "CSRF token requerido".
window._csrfTok = window._csrfTok || '';
function _csrf() {
  if (window._csrfTok) return window._csrfTok;
  var m = document.cookie.match(/(?:^|;\\s*)csrf_token=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}
async function _ensureCsrf() {
  if (window._csrfTok) return window._csrfTok;
  try {
    var r = await fetch('/api/csrf-token', {credentials: 'same-origin'});
    if (r.ok) { var d = await r.json(); window._csrfTok = (d && d.csrf_token) || ''; }
  } catch (e) {}
  return window._csrfTok;
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
fetch('/api/csrf-token', {credentials: 'same-origin'}).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){ if (d && d.csrf_token) window._csrfTok = d.csrf_token; }).catch(function(){});

// ── Filtros + Paginacion (client-side) ────────────────────────────
var TBL_STATE = {
  ocs:    {q: '', page: 1, size: 50, fields: ['numero_oc','proveedor','estado','fecha','solicitante']},
  scs:    {q: '', page: 1, size: 50, fields: ['solicitante','area','urgencia','estado','justificacion']},
  prov:   {q: '', page: 1, size: 50, fields: ['nombre','nit','contacto','email','telefono']},
  mp:     {q: '', page: 1, size: 50, fields: ['codigo_mp','descripcion','clase','proveedor']},
  pagos:  {q: '', page: 1, size: 50, fields: ['numero_oc','proveedor','metodo','observaciones']},
};
function _filtrar(data, query, fields) {
  if (!query) return data || [];
  var q = query.toLowerCase().trim();
  return (data || []).filter(function(r) {
    return fields.some(function(f) {
      var v = r[f]; return v != null && String(v).toLowerCase().indexOf(q) !== -1;
    });
  });
}
function _paginar(data, page, size) {
  if (size >= 999) return {items: data, total: data.length, totalPages: 1, page: 1};
  var total = data.length;
  var totalPages = Math.max(1, Math.ceil(total / size));
  var p = Math.min(Math.max(1, page), totalPages);
  return {items: data.slice((p-1)*size, p*size), total: total, totalPages: totalPages, page: p};
}
function _renderPag(tabla, info) {
  var s = TBL_STATE[tabla];
  if (info.total <= s.size && info.total < 51) {
    return '<div style="font-size:11px;color:#64748b;padding:6px 0;">' + info.total + ' filas</div>';
  }
  var html = '<div style="display:flex;align-items:center;gap:8px;padding:8px 0;font-size:12px;color:#64748b;">';
  html += '<span>Pag ' + info.page + '/' + info.totalPages + ' &middot; ' + info.total + '</span>';
  html += '<span style="flex:1"></span>';
  html += '<button data-act="prev" data-tbl="' + tabla + '"' +
          (info.page <= 1 ? ' disabled' : '') + ' style="padding:4px 10px;font-size:12px;border:1px solid #cbd5e1;border-radius:5px;background:#fff;cursor:pointer">&larr;</button>';
  html += '<button data-act="next" data-tbl="' + tabla + '"' +
          (info.page >= info.totalPages ? ' disabled' : '') + ' style="padding:4px 10px;font-size:12px;border:1px solid #cbd5e1;border-radius:5px;background:#fff;cursor:pointer">&rarr;</button>';
  html += '<select data-act="size" data-tbl="' + tabla + '" style="border:1px solid #cbd5e1;padding:4px 6px;border-radius:5px;font-size:12px;">';
  ['50','100','200','999'].forEach(function(o){
    var label = o === '999' ? 'Todas' : o;
    html += '<option value="' + o + '"' + (String(s.size)===o?' selected':'') + '>' + label + '</option>';
  });
  html += '</select></div>';
  return html;
}
function cambiarPag(tabla, delta){ TBL_STATE[tabla].page = Math.max(1, TBL_STATE[tabla].page + delta); _refreshTbl(tabla); }
function cambiarPagSize(tabla, valor){ TBL_STATE[tabla].size = parseInt(valor,10)||50; TBL_STATE[tabla].page = 1; _refreshTbl(tabla); }
function buscarTabla(tabla, valor){ TBL_STATE[tabla].q = valor||''; TBL_STATE[tabla].page = 1; _refreshTbl(tabla); }
function _refreshTbl(tabla){
  // Resolver loader de cada tabla
  var fns = {
    ocs: ['cargarOCs','loadOCs','renderOCs'],
    scs: ['cargarSCs','loadSCs','renderSCs'],
    prov: ['cargarProveedores','loadProveedores','renderProveedores'],
    mp: ['cargarMaestroMP','loadMaestroMP'],
    pagos: ['cargarPagos','loadPagos'],
  };
  var arr = fns[tabla] || [];
  for (var i=0; i<arr.length; i++) {
    if (typeof window[arr[i]] === 'function') { window[arr[i]](); return; }
  }
}
document.addEventListener('click', function(ev){
  var btn = ev.target.closest('[data-act][data-tbl]');
  if (!btn || btn.tagName === 'SELECT') return;
  var tbl = btn.dataset.tbl, act = btn.dataset.act;
  if (act === 'prev') cambiarPag(tbl, -1);
  else if (act === 'next') cambiarPag(tbl, 1);
});
document.addEventListener('change', function(ev){
  var sel = ev.target.closest('select[data-act="size"][data-tbl]');
  if (!sel) return;
  cambiarPagSize(sel.dataset.tbl, sel.value);
});

// ─── Estado global ────────────────────────────────────────────────
var OCS = [];
var PROVS = [];
var ES_C = {es_contadora};
var ES_ADMIN = {es_admin};
// es_autorizador: puede AUTORIZAR OCs (admin o Catalina · OC_AUTORIZA_USERS). Reemplaza el
// gate viejo !ES_C que ocultaba el botón a Catalina (es contadora pero SÍ autoriza).
var ES_AUTORIZA = {es_autorizador};
// Sebastián 21-may-2026 · mostrar [data-admin-only] solo a admins (Influencers)
if(ES_ADMIN){
  document.addEventListener('DOMContentLoaded',function(){
    document.querySelectorAll('[data-admin-only]').forEach(function(el){
      el.style.display = 'inline-block';
    });
  });
}
// Sebastian (29-abr-2026): "influencers no lo gestiona la asistente solo yo".
// Tab Influencers oculto para Catalina; visible para Sebastian + Alejandro.
if (ES_C) {
  document.addEventListener('DOMContentLoaded', function(){
    var tab = document.getElementById('tn-influencer');
    if (tab) tab.style.display = 'none';
  });
}
var ITMS = 0;
var MP_ITMS = 0;
var _MPCAT = [];
var _CONSUM = [];  // catálogo de consumibles (papelería/EPP/servicios) para el buscador de Crear OC
var _ALERTAS_MP = [];
var _ALERTAS_MEE = [];   // envases (MEE) en déficit · consumo-horizontes?tipo=mee · 18-jun
var _ocsCatFilter = 'ALL';
var PAGOS = [];

// Mapa categoria → grupos de strings
var CMAP = {
  mp:  ['MPs','MP','Materia Prima','Materias Primas'],
  mee: ['Envase','Insumos','MEE','Empaque','Material de Empaque'],
  svc: ['Servicios','Analisis','Acondicionamiento','SVC','Servicio',
        'Servicios Profesionales','Software/Tecnologia'],
  adm: ['Admin','Nomina','ADM','Administrativo',
        'EPP','Aseo/Limpieza','Papeleria/Oficina','Dotacion','Otro'],
  inf: ['Infraestructura','INF','Mantenimiento','Repuestos','Reactivos/Laboratorio'],
  cc:  ['CC','Cuenta de Cobro','Cuentas de Cobro']
};
// Acepta tildes normalizando
function inGroup(cat, grp){
  var c = (cat||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
  var list = CMAP[grp]||[];
  for(var i=0;i<list.length;i++){
    if(list[i].normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase()===c) return true;
  }
  return false;
}

// ─── Utilidades ───────────────────────────────────────────────────
function fmt(n){ return '$'+parseFloat(n||0).toLocaleString('es-CO',{minimumFractionDigits:0,maximumFractionDigits:0}); }
function fdate(d){ if(!d) return '-'; var p=d.substring(0,10).split('-'); return p.length===3?p[2]+'/'+p[1]+'/'+p[0]:d.substring(0,10); }
function esc(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function badge(e){
  var m={'Borrador':'b-bor','Revisada':'b-rev','Autorizada':'b-aut','Pagada':'b-pag','Recibida':'b-rec'};
  return '<span class="badge '+(m[e]||'b-bor')+'">'+e+'</span>';
}

// ─── Grupos top · Sebastián 21-may-2026 ────────────────────────────
// 11 tabs → 4 grupos top con sub-bars (mismo patrón Programación 8→4).
// Cada grupo muestra solo SUS sub-tabs · al cambiar grupo, se activa
// su sub-tab por defecto (data-default-tab).
function _cxSwitchGroup(grp){
  // Activar botón top + visualmente
  document.querySelectorAll('.cx-grp-btn').forEach(function(b){
    var on = b.getAttribute('data-cx-grp') === grp;
    b.classList.toggle('on', on);
    if(on){
      b.style.background = 'linear-gradient(135deg,#0e7490,#0891b2)';
      b.style.color = '#fff';
      b.style.boxShadow = '0 3px 10px rgba(8,145,178,.35)';
    } else {
      b.style.background = '#e2e8f0';
      b.style.color = '#475569';
      b.style.boxShadow = 'none';
    }
  });
  // Mostrar sub-bar del grupo · ocultar otras
  document.querySelectorAll('[data-cx-sub]').forEach(function(span){
    span.style.display = (span.getAttribute('data-cx-sub') === grp) ? 'flex' : 'none';
  });
  // Activar default-tab del grupo
  var btn = document.querySelector('.cx-grp-btn[data-cx-grp="'+grp+'"]');
  if(!btn) return;
  var defaultTab = btn.getAttribute('data-default-tab');
  if(defaultTab){
    var subBtn = document.querySelector('.tn[data-tab="'+defaultTab+'"]');
    if(subBtn && !subBtn.classList.contains('on')) subBtn.click();
  }
  // Sebastián 13-jul · si el grupo no tiene sub-tabs reales (≤1 visible), ocultar
  // la barra entera · una sola pestaña huérfana ("Vista consolidada"/"Proveedores")
  // no se ve premium. Con 2+ (Bandeja, OCs) la barra vuelve a mostrarse.
  var _bar = document.getElementById('cx-sub-bar');
  if(_bar){
    var _span = document.querySelector('[data-cx-sub="'+grp+'"]');
    var _vis = _span ? Array.prototype.filter.call(_span.querySelectorAll('.tn'), function(b){ return b.style.display !== 'none'; }).length : 0;
    _bar.style.display = (_vis >= 2) ? 'flex' : 'none';
  }
}
document.querySelectorAll('.cx-grp-btn').forEach(function(b){
  b.addEventListener('click', function(){
    _cxSwitchGroup(b.getAttribute('data-cx-grp'));
  });
});
// Auto-detectar grupo cuando se activa un sub-tab via deep link / código
window._cxTabToGrp = {
  // Entradas
  'planta':'entradas', 'solic':'entradas', 'solprod':'entradas',
  'influencer':'entradas',  // por compat · aunque oculto
  // OCs y Pagos
  'consol':'ocs', 'por-pagar':'ocs', 'pagos':'ocs', 'historico':'ocs', 'ordserv':'ocs',
  'atrasadas':'ocs', 'discrep':'ocs', 'mailbox':'ocs',
  // Maestros
  'prov':'maestros',
  // Dashboard (consolidado · alertas + mis-sol son widgets dentro)
  'dash':'analitica', 'alertas':'analitica', 'mis-sol':'analitica',
  // PRO Fase 1: estos 2 ya no son tabs visibles · siguen en map por deep links
};

// ─── Tabs ─────────────────────────────────────────────────────────
document.querySelectorAll('.tn').forEach(function(btn){
  btn.addEventListener('click', function(){
    var tab = this.getAttribute('data-tab');
    // Sebastián 21-may-2026 · si el click viene de código externo
    // (deep link, querySelector(...).click()), mostrar el grupo correcto.
    var grp = (window._cxTabToGrp || {})[tab];
    if(grp){
      var bar = document.querySelector('[data-cx-sub="'+grp+'"]');
      if(bar && bar.style.display === 'none'){
        _cxSwitchGroup(grp);
      }
    }
    document.querySelectorAll('.tn').forEach(function(b){ b.classList.remove('on'); });
    document.querySelectorAll('.pane').forEach(function(p){ p.classList.remove('on'); });
    this.classList.add('on');
    var pane = document.getElementById('pane-'+tab);
    if(pane) pane.classList.add('on');
    if(tab==='dash'){
      // Compras PRO · 4 KPIs grandes + widgets consolidados
      // Velocidad: dashboard-home y cash-flow se piden UNA sola vez y se
      // comparten entre KPIs + panel + widgets (antes se pedían 2× c/u).
      window._dashHomeP = null; window._cashFlowP = null;
      if(typeof renderKpisGrandes==='function') renderKpisGrandes();
      renderDashHome2();
      if(typeof renderAlertasBanner==='function') renderAlertasBanner();
      if(typeof renderMisSolicWidget==='function') renderMisSolicWidget();
    }
    else if(tab==='prov') renderProv();
    else if(tab==='solic') loadSolicitudes();
    else if(tab==='planta') loadPlanta();
    else if(tab==='influencer') loadInfluencers();
    else if(tab==='consol') loadConsolidado();
    else if(tab==='pagos'){ loadPagos(); }
    else if(tab==='historico'){ renderHistorico(); }
    else if(tab==='por-pagar'){ loadPorPagar(); }
    else if(tab==='atrasadas'){ cargarOcsAtrasadas(); }
    else if(tab==='discrep'){ cargarDiscrepancias(); }
    else if(tab==='mailbox'){ cargarMailbox(); }
    else if(tab==='cotiz'){ cargarCotizaciones(); }
    else if(tab==='alertas'){ loadAlertasCompras(); }
    else if(tab==='solprod'){ loadSolicitudesProduccion(); }
    else if(tab==='mis-sol'){ loadMisSolicitudes(); }
    else if(tab==='ordserv'){ loadOrdenesServicio(); }
    else if(tab==='prepenv'){ loadPreparacionEnvases(); }
    else if(tab==='feedneed'){ loadFeedNecesidades(); }
    else if(tab==='facprov'){ loadFacturasProv(); }
    var fab = document.getElementById('fab-btn');
    if(tab==='prov'||tab==='solic'||tab==='planta'||tab==='influencer'||tab==='consol'||tab==='pagos'||tab==='por-pagar'||tab==='alertas'||tab==='mis-sol'||tab==='prepenv'||tab==='ordserv'||tab==='feedneed'||tab==='facprov'){ fab.style.display='none'; }
    else{ fab.style.display='flex'; fab.onclick=function(){
      var cat=tab==='dash'?'':tab.toUpperCase();
      openNuevaOC(cat);
    }; }
  });
});

// ─── Carga de datos ───────────────────────────────────────────────
// ════════════════════════════════════════════════════════════════════════
// Órdenes de Servicio · Sebastián 21-may-2026
// Catalina crea · proveedor procesa · planta confirma recepción
// ════════════════════════════════════════════════════════════════════════
// Sebastián 1-jun-2026 · Libro de facturas de proveedor (cuentas por pagar)
window._FP = [];
var _fpT=null;
function _fpDeb(){ clearTimeout(_fpT); _fpT=setTimeout(loadFacturasProv, 350); }
function _fpMoney(n){ return '$'+(Math.round(n||0)).toLocaleString('es-CO'); }
async function loadFacturasProv(){
  var wrap=document.getElementById('fp-wrap'), kpis=document.getElementById('fp-kpis');
  if(!wrap) return;
  wrap.innerHTML='Cargando…';
  var est=(document.getElementById('fp-estado')||{}).value||'todas';
  var q=((document.getElementById('fp-q')||{}).value||'').trim();
  try{
    var r=await fetch('/api/compras/facturas-proveedor?estado='+encodeURIComponent(est)+'&q='+encodeURIComponent(q),{cache:'no-store'});
    if(r.status===401){ location.href='/login'; return; }
    var d=await r.json();
    if(!d.ok){ wrap.innerHTML='<div style="color:#dc2626;padding:14px">Error: '+_esc((d&&d.error)||r.status)+'</div>'; return; }
    window._FP=d.items||[];
    if(kpis){
      kpis.innerHTML=
        '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:8px 14px;min-width:150px;text-align:center"><div style="font-size:20px;font-weight:800;color:#991b1b">'+_fpMoney(d.total_vencido)+'</div><div style="font-size:10px;color:#64748b;text-transform:uppercase">Vencido</div></div>'+
        '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:8px 14px;min-width:150px;text-align:center"><div style="font-size:20px;font-weight:800;color:#1e293b">'+_fpMoney(d.total_saldo)+'</div><div style="font-size:10px;color:#64748b;text-transform:uppercase">Saldo total</div></div>'+
        '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:8px 14px;min-width:120px;text-align:center"><div style="font-size:20px;font-weight:800;color:#1e293b">'+d.n+'</div><div style="font-size:10px;color:#64748b;text-transform:uppercase">Facturas</div></div>';
    }
    var b=document.getElementById('facprov-badge'); var nv=window._FP.filter(function(x){return x.vencida;}).length;
    if(b){ if(nv>0){ b.textContent=nv; b.style.display='inline-block'; } else b.style.display='none'; }
    if(!window._FP.length){ wrap.innerHTML='<div style="padding:18px;color:#64748b">No hay facturas registradas. Usá "➕ Nueva factura".</div>'; return; }
    var html='<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#0f766e;color:#fff">';
    ['Nº Factura','Proveedor','OC','Vence','Total','Pagado','Saldo','Estado','Acciones'].forEach(function(h,i){ html+='<th style="padding:7px;text-align:'+((i>=4&&i<=6)?'right':'left')+'">'+h+'</th>'; });
    html+='</tr></thead><tbody>';
    window._FP.forEach(function(it){
      var estMap={'pendiente':['#64748b','Pendiente'],'parcial':['#b45309','Parcial'],'pagada':['#15803d','Pagada'],'anulada':['#94a3b8','Anulada'],'vencida':['#b91c1c','Vencida']};
      var ef=it.estado_efectivo||it.estado; var em=estMap[ef]||['#475569',ef];
      var venc=it.fecha_vencimiento||'—';
      var diasTxt=(it.dias_vencimiento!=null&&ef!=='pagada'&&ef!=='anulada')?(' <span style="font-size:10px;color:'+(it.dias_vencimiento<0?'#b91c1c':'#64748b')+'">('+(it.dias_vencimiento<0?Math.abs(it.dias_vencimiento)+'d venc':it.dias_vencimiento+'d')+')</span>'):'';
      var sobre=it.sobre_facturada?' <span title="total factura &gt; valor OC" style="background:#fee2e2;color:#991b1b;font-size:9px;padding:1px 4px;border-radius:3px">⚠ &gt;OC</span>':'';
      html+='<tr style="border-top:1px solid #f1f5f9'+(it.vencida?';background:#fff1f2':'')+(it.estado==='anulada'?';opacity:.55':'')+'">';
      html+='<td style="padding:6px;font-weight:700">'+_esc(it.numero_factura)+sobre+(it.tiene_pdf?' <a href="/api/compras/facturas-proveedor/'+it.id+'/pdf" target="_blank" title="ver PDF" style="text-decoration:none">📎</a>':'')+'</td>';
      html+='<td style="padding:6px">'+_esc(it.proveedor||'')+'</td>';
      html+='<td style="padding:6px;font-size:11px;color:#64748b">'+_esc(it.numero_oc||'—')+'</td>';
      html+='<td style="padding:6px;white-space:nowrap">'+_esc(venc)+diasTxt+'</td>';
      html+='<td style="padding:6px;text-align:right">'+_fpMoney(it.total)+'</td>';
      html+='<td style="padding:6px;text-align:right;color:#15803d">'+_fpMoney(it.pagado)+'</td>';
      html+='<td style="padding:6px;text-align:right;font-weight:700">'+_fpMoney(it.saldo)+'</td>';
      html+='<td style="padding:6px"><span style="color:'+em[0]+';font-weight:700">'+em[1]+'</span></td>';
      html+='<td style="padding:6px;white-space:nowrap">';
      if(it.estado!=='anulada'){
        if(it.saldo>0.5) html+='<button onclick="fpPagarModal('+it.id+')" style="background:#0f766e;color:#fff;border:none;padding:4px 10px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer;margin-right:4px">Pagar</button>';
        html+='<button onclick="fpDetalle('+it.id+')" style="background:#e2e8f0;color:#334155;border:none;padding:4px 10px;border-radius:5px;font-size:11px;cursor:pointer;margin-right:4px">Ver</button>';
        html+='<button onclick="fpAnular('+it.id+')" style="background:#fff;color:#dc2626;border:1px solid #dc2626;padding:4px 8px;border-radius:5px;font-size:11px;cursor:pointer">Anular</button>';
      } else { html+='<span style="color:#94a3b8;font-size:11px">—</span>'; }
      html+='</td></tr>';
    });
    html+='</tbody></table>';
    wrap.innerHTML=html;
  }catch(e){ wrap.innerHTML='<div style="color:#dc2626;padding:14px">Error red: '+_esc(e.message||e)+'</div>'; }
}
function _fpModalShell(inner, maxw){
  var m=document.getElementById('fp-modal'); if(m) m.remove();
  m=document.createElement('div'); m.id='fp-modal';
  m.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:99999;display:flex;align-items:flex-start;justify-content:center;padding:20px;overflow:auto';
  m.innerHTML='<div style="background:#fff;border-radius:12px;max-width:'+(maxw||640)+'px;width:100%;box-shadow:0 12px 40px rgba(0,0,0,.3);padding:24px">'+inner+'</div>';
  document.body.appendChild(m);
  m.addEventListener('click',function(e){ if(e.target===m) m.remove(); });
  return m;
}
function _fpClose(){ var m=document.getElementById('fp-modal'); if(m) m.remove(); }
function fpNuevaModal(){
  function fld(lbl,id,tp,ph){ return '<div><label style="font-size:11px;color:#64748b;font-weight:700;display:block;margin-bottom:3px">'+lbl+'</label><input id="'+id+'" type="'+(tp||'text')+'" placeholder="'+(ph||'')+'" oninput="_fpRecalc()" style="width:100%;padding:7px;border:1px solid #cbd5e1;border-radius:5px;box-sizing:border-box"></div>'; }
  var h='<div style="display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #e2e8f0;padding-bottom:10px;margin-bottom:14px"><h2 style="margin:0;font-size:17px;color:#0f766e">🧾 Nueva factura de proveedor</h2><button onclick="_fpClose()" style="background:#e2e8f0;border:none;width:32px;height:32px;border-radius:50%;font-size:18px;cursor:pointer">×</button></div>';
  h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">';
  h+=fld('Nº Factura *','fp-n-num')+fld('Proveedor *','fp-n-prov')+fld('NIT','fp-n-nit')+fld('OC vinculada','fp-n-oc','text','OC-2026-...')+fld('Fecha emisión','fp-n-emi','date')+fld('Fecha vencimiento','fp-n-venc','date');
  h+='</div>';
  h+='<div style="margin-top:12px;font-weight:700;color:#334155;font-size:13px">Valores (el total se calcula solo)</div>';
  h+='<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:6px">';
  h+=fld('Subtotal','fp-n-sub','number')+fld('IVA','fp-n-iva','number')+fld('Retefuente','fp-n-rf','number')+fld('ReteICA','fp-n-ri','number');
  h+='<div><label style="font-size:11px;color:#64748b;font-weight:700;display:block;margin-bottom:3px">Total a pagar</label><input id="fp-n-total" type="number" style="width:100%;padding:7px;border:2px solid #0f766e;border-radius:5px;box-sizing:border-box;font-weight:700"></div>';
  h+='</div>';
  h+='<div style="margin-top:10px"><label style="font-size:11px;color:#64748b;font-weight:700;display:block;margin-bottom:3px">Observaciones</label><input id="fp-n-obs" style="width:100%;padding:7px;border:1px solid #cbd5e1;border-radius:5px;box-sizing:border-box"></div>';
  h+='<div id="fp-n-msg" style="margin-top:8px;font-size:12px"></div>';
  h+='<div style="margin-top:14px;text-align:right"><button onclick="_fpClose()" style="background:#e2e8f0;color:#334155;border:none;padding:8px 16px;border-radius:6px;margin-right:6px;cursor:pointer">Cancelar</button><button onclick="fpGuardar()" style="background:#0f766e;color:#fff;border:none;padding:8px 18px;border-radius:6px;font-weight:700;cursor:pointer">Guardar factura</button></div>';
  _fpModalShell(h, 700);
}
function _fpRecalc(){
  var g=function(id){ return parseFloat((document.getElementById(id)||{}).value||'0')||0; };
  var t=g('fp-n-sub')+g('fp-n-iva')-g('fp-n-rf')-g('fp-n-ri');
  var el=document.getElementById('fp-n-total'); if(el && document.activeElement!==el) el.value=Math.round(t*100)/100;
}
async function fpGuardar(){
  var g=function(id){ return (document.getElementById(id)||{}).value||''; };
  var body={numero_factura:g('fp-n-num').trim(), proveedor:g('fp-n-prov').trim(), nit:g('fp-n-nit').trim(),
    numero_oc:g('fp-n-oc').trim(), fecha_emision:g('fp-n-emi'), fecha_vencimiento:g('fp-n-venc'),
    subtotal:parseFloat(g('fp-n-sub'))||0, iva:parseFloat(g('fp-n-iva'))||0,
    retefuente:parseFloat(g('fp-n-rf'))||0, retica:parseFloat(g('fp-n-ri'))||0,
    total:parseFloat(g('fp-n-total'))||0, observaciones:g('fp-n-obs').trim()};
  if(!body.numero_factura||!body.proveedor){ document.getElementById('fp-n-msg').innerHTML='<span style="color:#dc2626">Nº factura y proveedor son obligatorios</span>'; return; }
  try{
    var r=await fetch('/api/compras/facturas-proveedor', _fetchOpts('POST', body));
    var d=await r.json();
    if(!r.ok||!d.ok){ document.getElementById('fp-n-msg').innerHTML='<span style="color:#dc2626">'+_esc((d&&(d.detail||d.error))||r.status)+'</span>'; return; }
    if(d.warning) alert('⚠ '+d.warning);
    _fpClose(); loadFacturasProv();
  }catch(e){ document.getElementById('fp-n-msg').innerHTML='<span style="color:#dc2626">Error red: '+_esc(e.message||e)+'</span>'; }
}
function fpPagarModal(fid){
  var it=(window._FP||[]).find(function(x){return x.id===fid;}); if(!it) return;
  var h='<div style="display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #e2e8f0;padding-bottom:10px;margin-bottom:14px"><h2 style="margin:0;font-size:16px;color:#0f766e">Pagar factura '+_esc(it.numero_factura)+'</h2><button onclick="_fpClose()" style="background:#e2e8f0;border:none;width:32px;height:32px;border-radius:50%;font-size:18px;cursor:pointer">×</button></div>';
  h+='<div style="font-size:12px;color:#64748b;margin-bottom:10px">'+_esc(it.proveedor)+(it.numero_oc?' · OC '+_esc(it.numero_oc):'')+' · saldo <b>'+_fpMoney(it.saldo)+'</b></div>';
  h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">';
  h+='<div><label style="font-size:11px;color:#64748b;font-weight:700">Monto</label><input id="fp-p-monto" type="number" value="'+(it.saldo||0)+'" style="width:100%;padding:7px;border:1px solid #cbd5e1;border-radius:5px;box-sizing:border-box"></div>';
  h+='<div><label style="font-size:11px;color:#64748b;font-weight:700">Medio</label><select id="fp-p-medio" style="width:100%;padding:7px;border:1px solid #cbd5e1;border-radius:5px;box-sizing:border-box"><option>Transferencia</option><option>Nequi</option><option>Daviplata</option><option>Efectivo</option><option>Cheque</option><option>Tarjeta</option></select></div>';
  h+='</div>';
  h+='<div style="margin-top:10px"><label style="font-size:11px;color:#64748b;font-weight:700">Observaciones</label><input id="fp-p-obs" style="width:100%;padding:7px;border:1px solid #cbd5e1;border-radius:5px;box-sizing:border-box"></div>';
  h+='<div id="fp-p-msg" style="margin-top:8px;font-size:12px"></div>';
  h+='<div style="margin-top:14px;text-align:right"><button onclick="_fpClose()" style="background:#e2e8f0;color:#334155;border:none;padding:8px 16px;border-radius:6px;margin-right:6px;cursor:pointer">Cancelar</button><button onclick="fpDoPagar('+fid+')" style="background:#0f766e;color:#fff;border:none;padding:8px 18px;border-radius:6px;font-weight:700;cursor:pointer">Registrar pago</button></div>';
  _fpModalShell(h, 480);
}
async function fpDoPagar(fid){
  var monto=parseFloat((document.getElementById('fp-p-monto')||{}).value||'0')||0;
  var medio=(document.getElementById('fp-p-medio')||{}).value||'Transferencia';
  var obs=(document.getElementById('fp-p-obs')||{}).value||'';
  if(monto<=0){ document.getElementById('fp-p-msg').innerHTML='<span style="color:#dc2626">Monto inválido</span>'; return; }
  try{
    var r=await fetch('/api/compras/facturas-proveedor/'+fid+'/pagar', _fetchOpts('POST', {monto:monto, medio:medio, observaciones:obs}));
    var d=await r.json();
    if(!r.ok||!d.ok){ document.getElementById('fp-p-msg').innerHTML='<span style="color:#dc2626">'+_esc((d&&d.error)||r.status)+(d&&d.saldo!=null?' (saldo '+_fpMoney(d.saldo)+')':'')+'</span>'; return; }
    if(d.oc_estado) alert('✅ Pago registrado · la OC quedó "'+d.oc_estado+'"');
    _fpClose(); loadFacturasProv();
  }catch(e){ document.getElementById('fp-p-msg').innerHTML='<span style="color:#dc2626">Error red: '+_esc(e.message||e)+'</span>'; }
}
async function fpDetalle(fid){
  try{
    var r=await fetch('/api/compras/facturas-proveedor/'+fid,{cache:'no-store'});
    var d=await r.json();
    if(!r.ok||!d.ok){ alert('Error: '+((d&&d.error)||r.status)); return; }
    var f=d.factura;
    function rw(k,v){ return '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f1f5f9"><span style="color:#64748b">'+k+'</span><span style="font-weight:600">'+v+'</span></div>'; }
    var h='<div style="display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #e2e8f0;padding-bottom:10px;margin-bottom:14px"><h2 style="margin:0;font-size:16px;color:#0f766e">Factura '+_esc(f.numero_factura)+'</h2><button onclick="_fpClose()" style="background:#e2e8f0;border:none;width:32px;height:32px;border-radius:50%;font-size:18px;cursor:pointer">×</button></div>';
    h+=rw('Proveedor', _esc(f.proveedor||'')+(f.nit?' · '+_esc(f.nit):''));
    h+=rw('OC', _esc(f.numero_oc||'—'));
    h+=rw('Emisión / Vence', _esc(f.fecha_emision||'—')+' → '+_esc(f.fecha_vencimiento||'—'));
    h+=rw('Subtotal', _fpMoney(f.subtotal))+rw('IVA', _fpMoney(f.iva))+rw('Retefuente', '-'+_fpMoney(f.retefuente))+rw('ReteICA', '-'+_fpMoney(f.retica));
    h+=rw('Total', '<b>'+_fpMoney(f.total)+'</b>')+rw('Pagado', _fpMoney(f.pagado))+rw('Saldo', '<b>'+_fpMoney(f.saldo)+'</b>');
    if(f.observaciones) h+=rw('Obs', _esc(f.observaciones));
    h+='<div style="margin-top:12px;font-weight:700;color:#334155;font-size:13px">Pagos ('+f.pagos.length+')</div>';
    if(f.pagos.length){ h+='<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:4px">'; f.pagos.forEach(function(p){ h+='<tr style="border-bottom:1px solid #f1f5f9"><td style="padding:4px">'+_esc((p.fecha_pago||'').slice(0,10))+'</td><td style="padding:4px">'+_esc(p.medio||'')+'</td><td style="padding:4px;text-align:right;font-weight:600">'+_fpMoney(p.monto)+'</td><td style="padding:4px;color:#64748b;font-size:11px">'+_esc(p.registrado_por||'')+'</td></tr>'; }); h+='</table>'; }
    else h+='<div style="color:#94a3b8;font-size:12px;padding:6px 0">Sin pagos aún.</div>';
    if(f.tiene_pdf) h+='<div style="margin-top:10px"><a href="/api/compras/facturas-proveedor/'+fid+'/pdf" target="_blank" style="color:#0f766e;font-weight:700">📎 Ver PDF de la factura</a></div>';
    _fpModalShell(h, 560);
  }catch(e){ alert('Error: '+(e.message||e)); }
}
async function fpAnular(fid){
  var mot=prompt('¿Anular esta factura? Motivo (opcional):'); if(mot===null) return;
  try{
    var r=await fetch('/api/compras/facturas-proveedor/'+fid, _fetchOpts('PATCH', {anular:true, motivo:mot}));
    var d=await r.json();
    if(!r.ok||!d.ok){ alert('Error: '+((d&&d.error)||r.status)); return; }
    loadFacturasProv();
  }catch(e){ alert('Error: '+(e.message||e)); }
}

// Sebastián 31-may-2026 · Feed de necesidades (Pieza 2) · MP + envases bajo mínimo
async function loadFeedNecesidades(){
  var wrap=document.getElementById('feedneed-wrap'), kpis=document.getElementById('feedneed-kpis');
  if(!wrap) return;
  wrap.innerHTML='Cargando…';
  try{
    var r=await fetch('/api/compras/feed-necesidades',{cache:'no-store'});
    if(r.status===401){ location.href='/login'; return; }
    var d=await r.json();
    if(!d.ok){ wrap.innerHTML='<div style="color:#dc2626;padding:14px">Error: '+_esc((d&&d.error)||r.status)+'</div>'; return; }
    if(kpis){
      kpis.innerHTML=
        '<div style="background:#fee2e2;border:1px solid #fecaca;border-radius:8px;padding:8px 14px;min-width:120px;text-align:center"><div style="font-size:22px;font-weight:800;color:#991b1b">'+d.n+'</div><div style="font-size:10px;color:#64748b;text-transform:uppercase">Necesidades</div></div>'+
        '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:8px 14px;min-width:120px;text-align:center"><div style="font-size:22px;font-weight:800;color:#1e293b">'+d.n_mp+'</div><div style="font-size:10px;color:#64748b;text-transform:uppercase">Materias primas</div></div>'+
        '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:8px 14px;min-width:120px;text-align:center"><div style="font-size:22px;font-weight:800;color:#1e293b">'+d.n_mee+'</div><div style="font-size:10px;color:#64748b;text-transform:uppercase">Envases</div></div>';
    }
    var bdg=document.getElementById('feedneed-badge'); if(bdg){ if(d.n>0){ bdg.textContent=d.n; bdg.style.display='inline-block'; } else bdg.style.display='none'; }
    if(!d.items.length){ wrap.innerHTML='<div style="padding:18px;color:#15803d">✓ Todo por encima del mínimo · nada urgente por comprar.</div>'; return; }
    var html='<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#0f766e;color:#fff">';
    ['Tipo','Código','Nombre','Stock','Mínimo','Falta','Cobertura','Proveedor'].forEach(function(h,i){ html+='<th style="padding:7px;text-align:'+((i>=3&&i<=5)?'right':'left')+'">'+h+'</th>'; });
    html+='</tr></thead><tbody>';
    d.items.forEach(function(it){
      var pct=it.pct||0, col=pct<25?'#991b1b':(pct<60?'#b45309':'#475569'), bg=pct<25?'#fff1f2':'';
      var tip=it.tipo==='MP'?'<span style="background:#dbeafe;color:#1e40af;padding:1px 6px;border-radius:4px;font-weight:700;font-size:10px">MP</span>':'<span style="background:#ede9fe;color:#5b21b6;padding:1px 6px;border-radius:4px;font-weight:700;font-size:10px">Envase</span>';
      html+='<tr style="border-top:1px solid #f1f5f9'+(bg?';background:'+bg:'')+'">';
      html+='<td style="padding:6px">'+tip+'</td>';
      html+='<td style="padding:6px;font-family:ui-monospace;font-size:11px">'+_esc(it.codigo)+'</td>';
      html+='<td style="padding:6px">'+_esc(it.nombre||'')+'</td>';
      html+='<td style="padding:6px;text-align:right">'+it.stock+(it.unidad==='g'?'g':'')+'</td>';
      html+='<td style="padding:6px;text-align:right">'+it.minimo+'</td>';
      html+='<td style="padding:6px;text-align:right;color:#b91c1c;font-weight:700">'+it.faltante+'</td>';
      html+='<td style="padding:6px;text-align:right;color:'+col+';font-weight:700">'+pct+'%</td>';
      html+='<td style="padding:6px">'+_esc(it.proveedor||'—')+'</td>';
      html+='</tr>';
    });
    html+='</tbody></table>';
    wrap.innerHTML=html;
  }catch(e){ wrap.innerHTML='<div style="color:#dc2626;padding:14px">Error red: '+_esc(e.message||e)+'</div>'; }
}

// Sebastián 31-may-2026 · Preparar envases (Pieza 1) · jalona producciones → OS
window._PREP_ITEMS = [];
async function loadPreparacionEnvases(){
  var wrap = document.getElementById('prep-tabla-wrap');
  if(!wrap) return;
  var dias = (document.getElementById('prep-dias')||{}).value || 90;
  wrap.innerHTML = 'Cargando…';
  try{
    var r = await fetch('/api/compras/preparacion-envases?dias='+dias+'&anticipo=30', {cache:'no-store'});
    if(r.status===401){ location.href='/login'; return; }
    var d = await r.json();
    if(!d.ok){ wrap.innerHTML='<div style="color:#dc2626;padding:14px">Error: '+_esc((d&&d.error)||r.status)+'</div>'; return; }
    // Sebastián 7-jul (Catalina) · AGRUPADO por envase: la próxima producción + las siguientes (acumulado) para
    // consolidar el envío a serigrafía. Fallback a items si el backend viejo no manda grupos.
    window._PREP_ITEMS = d.grupos || d.items || [];
    if(!window._PREP_ITEMS.length){ wrap.innerHTML='<div style="padding:18px;color:#64748b">No hay envases en producciones próximas ('+dias+'d).</div>'; return; }
    var h='<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#0f766e;color:#fff">'+
      '<th style="padding:7px;text-align:left">Producto</th><th style="padding:7px;text-align:left">Envase · próximas</th>'+
      '<th style="padding:7px;text-align:right">Uds a preparar</th><th style="padding:7px">Próxima prod.</th>'+
      '<th style="padding:7px">Lista para</th><th style="padding:7px">Proveedor</th>'+
      '<th style="padding:7px">Tipo</th><th style="padding:7px;text-align:center">Acción</th></tr></thead><tbody>';
    window._PREP_ITEMS.forEach(function(it,i){
      var fl = it.fecha_lista_sugerida||'';
      var flStyle = it.lista_atrasada ? 'background:#fee2e2;color:#991b1b;font-weight:700' : '';
      var osTag = it.os_existentes ? ' <span title="ya hay OS para este envase" style="background:#fef3c7;color:#92400e;padding:1px 5px;border-radius:4px;font-size:10px">OS×'+it.os_existentes+'</span>' : '';
      // Sebastián 2-jul · desglose COLAPSABLE por cliente (Animus vs cada B2B) · solo si hay B2B
      var pc = it.por_cliente||[];
      var hasB2B = pc.some(function(x){ return !x.es_dtc; });
      var pcHtml = '';
      if(pc.length && hasB2B){
        var pcRows = pc.map(function(x){
          return '<div style="display:flex;justify-content:space-between;gap:10px;padding:1px 0">'+
                 '<span>'+(x.es_dtc?'🛍️':'📦')+' '+_esc(x.cliente||'')+'</span>'+
                 '<b>'+(x.uds||0).toLocaleString('es-CO')+' uds</b></div>';
        }).join('');
        pcHtml = '<details style="margin-top:4px"><summary style="cursor:pointer;color:#0f766e;font-size:10px;font-weight:700">&#9656; por cliente ('+pc.length+')</summary>'+
                 '<div style="font-size:10px;color:#475569;padding:4px 0 0 10px;border-left:2px solid #99f6e4;margin-top:2px">'+pcRows+'</div></details>';
      }
      // Sebastián 7-jul (Catalina) · próximas producciones del MISMO envase · consolidar (preparar para N de una)
      var prods = it.producciones||[];
      var proxHtml = '';
      if(prods.length > 1){
        var prows = prods.map(function(p,j){
          var atr = p.lista_atrasada ? 'color:#b91c1c;font-weight:700' : '';
          return '<div style="display:flex;justify-content:space-between;gap:8px;padding:2px 0;align-items:center">'+
                 '<span style="'+atr+'">'+_esc(p.fecha_produccion||'')+' &rarr; '+(p.uds||0).toLocaleString('es-CO')+'</span>'+
                 '<span style="color:#64748b">&sum; '+(p.uds_acumulado||0).toLocaleString('es-CO')+'</span>'+
                 '<button onclick="prepSetUds('+i+','+(p.uds_acumulado||0)+')" style="background:#e0f2fe;color:#0369a1;border:none;padding:2px 7px;border-radius:4px;font-size:10px;font-weight:700;cursor:pointer;white-space:nowrap">preparar '+(j+1)+'</button></div>';
        }).join('');
        proxHtml = '<details style="margin-top:4px"><summary style="cursor:pointer;color:#7c3aed;font-size:10px;font-weight:700">&#9656; próximas '+prods.length+' producciones · consolidar</summary>'+
                   '<div style="font-size:10px;color:#475569;padding:4px 0 0 8px;border-left:2px solid #ddd6fe;margin-top:2px">'+prows+
                   '<div style="color:#94a3b8;font-size:9px;margin-top:3px">Apretá "preparar N" → deja el Uds para cubrir esas N producciones (1 solo envío = más barato).</div></div></details>';
      }
      h+='<tr id="prep-row-'+i+'" style="border-top:1px solid #e2e8f0">'+
        '<td style="padding:6px">'+_esc(it.producto||'')+osTag+'</td>'+
        '<td style="padding:6px;font-family:ui-monospace;font-size:11px">'+_esc(it.envase_codigo||'')+'<div style="color:#64748b;font-size:10px">'+_esc(it.presentacion||'')+'</div>'+pcHtml+proxHtml+'</td>'+
        '<td style="padding:6px;text-align:right"><input id="prep-cant-'+i+'" type="number" min="1" value="'+(it.uds||0)+'" style="width:78px;padding:3px;border:1px solid #cbd5e1;border-radius:4px;text-align:right"></td>'+
        '<td style="padding:6px;white-space:nowrap;color:#475569">'+_esc(it.fecha_produccion||'')+'</td>'+
        '<td style="padding:6px"><input id="prep-fecha-'+i+'" type="date" value="'+_esc(fl)+'" style="padding:3px;border:1px solid #cbd5e1;border-radius:4px;'+flStyle+'"></td>'+
        '<td style="padding:6px"><input id="prep-prov-'+i+'" placeholder="proveedor" style="width:140px;padding:3px;border:1px solid #cbd5e1;border-radius:4px"></td>'+
        '<td style="padding:6px"><select id="prep-tipo-'+i+'" style="padding:3px;border:1px solid #cbd5e1;border-radius:4px"><option>Serigrafía</option><option>Tampografía</option><option>Etiquetado</option></select></td>'+
        '<td style="padding:6px;text-align:center"><button onclick="generarOSDesdePrep('+i+')" style="background:#0f766e;color:#fff;border:none;padding:5px 12px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">Generar OS</button></td>'+
        '</tr>';
    });
    h+='</tbody></table>';
    wrap.innerHTML=h;
  }catch(e){ wrap.innerHTML='<div style="color:#dc2626;padding:14px">Error red: '+_esc(e.message||e)+'</div>'; }
}
function prepSetUds(i, uds){
  var el=document.getElementById('prep-cant-'+i);
  if(el){ el.value=uds; el.style.background='#dcfce7'; setTimeout(function(){ el.style.background=''; }, 900); }
}
async function generarOSDesdePrep(i){
  var it=(window._PREP_ITEMS||[])[i]; if(!it) return;
  var prov=((document.getElementById('prep-prov-'+i)||{}).value||'').trim();
  var tipo=(document.getElementById('prep-tipo-'+i)||{}).value||'Serigrafía';
  var cant=parseInt((document.getElementById('prep-cant-'+i)||{}).value||'0',10);
  var fecha=(document.getElementById('prep-fecha-'+i)||{}).value||'';
  if(!prov){ alert('Elegí un proveedor para '+it.envase_codigo); return; }
  if(!cant||cant<=0){ alert('Cantidad inválida'); return; }
  var data={tipo_servicio:tipo, producto_final:(it.producto||'')+' · '+(it.presentacion||''),
            envase_codigo_mee:it.envase_codigo||'', envase_descripcion:it.envase_descripcion||'',
            cantidad_unidades:cant, proveedor:prov, fecha_requerida_entrega:fecha,
            observaciones:'Preparación envase · lote #'+it.lote_id+' · producción '+it.fecha_produccion};
  try{
    var r=await fetch('/api/compras/ordenes-servicio', _fetchOpts('POST', data));
    var d=await r.json();
    if(!r.ok || (d&&d.error)){ alert('Error: '+((d&&d.error)||r.status)); return; }
    var row=document.getElementById('prep-row-'+i);
    if(row){ row.style.opacity='0.55'; var ac=row.querySelector('td:last-child'); if(ac) ac.innerHTML='<span style="color:#15803d;font-weight:700;font-size:11px">✓ '+_esc(d.numero_os||'OS creada')+'</span>'; }
  }catch(e){ alert('Error red: '+(e.message||e)); }
}

// Sebastián 31-may-2026 · Pieza 3 · mínimos de envases dinámicos (consumo del plan)
window._MINENV = [];
async function recalcularMinimosEnvases(){
  var m=document.getElementById('modal-min-env'); if(m) m.remove();
  m=document.createElement('div'); m.id='modal-min-env';
  m.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9999;display:flex;align-items:flex-start;justify-content:center;padding:20px;overflow:auto';
  m.innerHTML='<div style="background:#fff;border-radius:12px;max-width:1000px;width:100%;box-shadow:0 12px 40px rgba(0,0,0,.3);padding:24px"><div style="text-align:center;padding:40px;color:#94a3b8">Calculando mínimos…</div></div>';
  document.body.appendChild(m);
  m.addEventListener('click',function(e){ if(e.target===m) m.remove(); });
  try{
    var r=await fetch('/api/compras/minimos-envases-sugeridos?dias=90&cobertura_dias=45',{cache:'no-store'});
    if(r.status===401){ location.href='/login'; return; }
    var d=await r.json();
    if(!d.ok){ m.querySelector('div').innerHTML='<div style="color:#dc2626;padding:30px">Error: '+_esc((d&&d.error)||r.status)+'</div>'; return; }
    window._MINENV=d.items||[];
    var html='';
    html+='<div style="display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #e2e8f0;padding-bottom:12px;margin-bottom:14px">';
    html+='<div><h2 style="margin:0;font-size:18px;color:#7c3aed">⚙ Mínimos de envases · sugeridos por consumo</h2><div style="font-size:11px;color:#64748b;margin-top:3px">Mínimo = consumo diario del plan × '+d.cobertura_dias+'d de cobertura · horizonte '+d.dias+'d. Marcá los que querés aplicar.</div></div>';
    html+='<button onclick="document.getElementById(&quot;modal-min-env&quot;).remove()" style="background:#e2e8f0;color:#475569;border:none;width:36px;height:36px;border-radius:50%;font-size:20px;cursor:pointer">×</button></div>';
    html+='<div style="overflow-x:auto;border:1px solid #e2e8f0;border-radius:8px"><table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#f8fafc;color:#475569">';
    html+='<th style="padding:7px;text-align:center"><input type="checkbox" id="min-all" onchange="_minToggleAll(this.checked)"></th>';
    ['Envase','Consumo '+d.dias+'d','Diario','Mín actual','Mín sugerido','Stock'].forEach(function(h,i){ html+='<th style="padding:7px;text-align:'+(i===0?'left':'right')+'">'+h+'</th>'; });
    html+='</tr></thead><tbody>';
    window._MINENV.forEach(function(it,i){
      var sube=it.minimo_sugerido>it.minimo_actual, baja=it.minimo_sugerido<it.minimo_actual;
      var difCol=sube?'#b45309':(baja?'#15803d':'#475569'), noM=!it.en_maestro;
      html+='<tr style="border-top:1px solid #f1f5f9'+(noM?';background:#fff7ed':'')+'">';
      html+='<td style="padding:6px;text-align:center"><input type="checkbox" class="min-chk" data-i="'+i+'"'+(((sube||baja)&&!noM)?' checked':'')+(noM?' disabled':'')+'></td>';
      html+='<td style="padding:6px;font-family:ui-monospace;font-size:11px">'+_esc(it.envase_codigo)+(noM?' <span style="color:#b45309;font-size:10px">⚠ no en maestro</span>':'')+'<div style="color:#64748b;font-size:10px">'+_esc(it.descripcion||'')+'</div></td>';
      html+='<td style="padding:6px;text-align:right">'+it.consumo_horizonte+'</td>';
      html+='<td style="padding:6px;text-align:right">'+it.consumo_diario+'</td>';
      html+='<td style="padding:6px;text-align:right">'+it.minimo_actual+'</td>';
      html+='<td style="padding:6px;text-align:right;font-weight:700;color:'+difCol+'">'+it.minimo_sugerido+(sube?' ↑':(baja?' ↓':''))+'</td>';
      html+='<td style="padding:6px;text-align:right">'+it.stock_actual+'</td>';
      html+='</tr>';
    });
    if(!window._MINENV.length) html+='<tr><td colspan="7" style="padding:20px;text-align:center;color:#94a3b8">Sin consumo de envases en el horizonte.</td></tr>';
    html+='</tbody></table></div>';
    html+='<div style="margin-top:12px;text-align:right"><button onclick="_aplicarMinimosEnvases()" style="background:#7c3aed;color:#fff;border:none;padding:8px 18px;border-radius:6px;font-weight:700;cursor:pointer">Aplicar seleccionados</button></div>';
    html+='<div id="min-out" style="margin-top:8px;font-size:12px"></div>';
    m.querySelector('div').innerHTML=html;
  }catch(e){ m.querySelector('div').innerHTML='<div style="color:#dc2626;padding:30px">Error red: '+_esc(e.message||e)+'</div>'; }
}
function _minToggleAll(ch){ document.querySelectorAll('.min-chk:not([disabled])').forEach(function(x){ x.checked=ch; }); }
async function _aplicarMinimosEnvases(){
  var sel=[]; document.querySelectorAll('.min-chk:checked').forEach(function(x){ var it=window._MINENV[parseInt(x.dataset.i,10)]; if(it) sel.push({codigo:it.envase_codigo, stock_minimo:it.minimo_sugerido}); });
  if(!sel.length){ alert('Marcá al menos uno'); return; }
  if(!confirm('¿Aplicar el mínimo sugerido a '+sel.length+' envase(s)?')) return;
  var out=document.getElementById('min-out'); if(out) out.textContent='Aplicando…';
  try{
    var r=await fetch('/api/compras/minimos-envases-aplicar', _fetchOpts('POST', {items:sel}));
    var d=await r.json();
    if(!r.ok||!d.ok){ if(out) out.innerHTML='<span style="color:#dc2626">Error: '+_esc((d&&d.error)||r.status)+'</span>'; return; }
    if(out) out.innerHTML='<span style="color:#15803d;font-weight:700">✓ '+d.actualizados+' mínimos actualizados</span>';
    setTimeout(recalcularMinimosEnvases, 800);
  }catch(e){ if(out) out.innerHTML='<span style="color:#dc2626">Error red: '+_esc(e.message||e)+'</span>'; }
}

async function loadOrdenesServicio(){
  var tb = document.getElementById('os-tbody');
  if(!tb) return;
  var estado = (document.getElementById('os-filtro-estado')||{}).value || '';
  try{
    var url = '/api/compras/ordenes-servicio' + (estado ? '?estado='+encodeURIComponent(estado) : '');
    var r = await fetch(url, {credentials:'same-origin'});
    var d = await r.json();
    if(!r.ok){
      // FIX 27-may (P0 XSS) · esc del error · server podría devolver HTML en d.error
      tb.innerHTML = '<tr><td colspan="10" style="color:#dc2626;text-align:center;padding:14px">Error: '+esc(d.error||r.status)+'</td></tr>';
      return;
    }
    var items = d.items || [];
    var counts = d.counts || {};
    // Pills counts
    var pillsCont = document.getElementById('os-counts');
    var estados_ord = ['Borrador','Enviada','Recogida','En proceso','Entregada','Confirmada','Cancelada'];
    var colorEst = {Borrador:'#94a3b8',Enviada:'#0891b2','Recogida':'#ca8a04','En proceso':'#7c3aed',Entregada:'#16a34a','Confirmada':'#0f766e','Cancelada':'#dc2626'};
    pillsCont.innerHTML = estados_ord.map(function(e){
      var n = counts[e] || 0;
      var color = colorEst[e] || '#475569';
      return '<span style="background:'+color+';color:#fff;padding:3px 10px;border-radius:10px;font-weight:700">'+e+' · '+n+'</span>';
    }).join(' ');
    if(!items.length){
      tb.innerHTML = '<tr><td colspan="10" style="color:#94a3b8;text-align:center;padding:18px">Sin órdenes de servicio</td></tr>';
      return;
    }
    tb.innerHTML = items.map(function(o){
      var col = colorEst[o.estado] || '#475569';
      var acc = '';
      if(o.estado === 'Borrador'){
        acc = '<button class="btn" data-os-act="estado" data-num="'+_esc(o.numero_os)+'" data-nuevo="Enviada" style="background:#0891b2;color:#fff;padding:3px 8px;font-size:10px;border:none;border-radius:4px;cursor:pointer">📧 Enviar</button>';
      } else if(o.estado === 'Enviada'){
        acc = '<button class="btn" data-os-act="estado" data-num="'+_esc(o.numero_os)+'" data-nuevo="Recogida" style="background:#ca8a04;color:#fff;padding:3px 8px;font-size:10px;border:none;border-radius:4px;cursor:pointer">🚚 Recogida</button>';
      } else if(o.estado === 'Recogida'){
        acc = '<button class="btn" data-os-act="estado" data-num="'+_esc(o.numero_os)+'" data-nuevo="En proceso" style="background:#7c3aed;color:#fff;padding:3px 8px;font-size:10px;border:none;border-radius:4px;cursor:pointer">⚙️ En proceso</button>';
      } else if(o.estado === 'En proceso'){
        acc = '<button class="btn" data-os-act="estado" data-num="'+_esc(o.numero_os)+'" data-nuevo="Entregada" style="background:#16a34a;color:#fff;padding:3px 8px;font-size:10px;border:none;border-radius:4px;cursor:pointer">✓ Entregada</button>';
      } else if(o.estado === 'Entregada'){
        acc = '<span style="color:#16a34a;font-size:10px;font-weight:700">⏳ Esperando confirmación planta</span>';
      } else if(o.estado === 'Confirmada'){
        acc = '<span style="color:#0f766e;font-size:10px;font-weight:700">✓ '+_esc(o.planta_confirmado_por||'')+' confirmó</span>';
      }
      acc += ' <button data-os-act="detalle" data-num="'+_esc(o.numero_os)+'" style="background:#475569;color:#fff;padding:3px 8px;font-size:10px;border:none;border-radius:4px;cursor:pointer">📋</button>';
      return '<tr style="border-bottom:1px solid #e7e5e4">'+
        '<td style="padding:6px;font-family:monospace;font-weight:700;color:#0f766e">'+_esc(o.numero_os)+'</td>'+
        '<td style="padding:6px">'+_esc(o.proveedor)+'</td>'+
        '<td style="padding:6px;font-size:11px">'+_esc(o.tipo_servicio)+'</td>'+
        '<td style="padding:6px;font-size:12px">'+_esc(o.producto_final)+'</td>'+
        '<td style="padding:6px;font-size:11px">'+_esc(o.envase_descripcion||o.envase_codigo_mee||'—')+'</td>'+
        '<td style="padding:6px;text-align:center;font-weight:700">'+o.cantidad_unidades+'</td>'+
        '<td style="padding:6px;font-size:11px">'+_esc((o.fecha_solicitud||'').substring(0,10))+'</td>'+
        '<td style="padding:6px;font-size:11px">'+_esc((o.fecha_requerida_entrega||'').substring(0,10))+'</td>'+
        '<td style="padding:6px"><span style="background:'+col+';color:#fff;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700">'+_esc(o.estado)+'</span></td>'+
        '<td style="padding:6px;text-align:center;white-space:nowrap">'+acc+'</td>'+
      '</tr>';
    }).join('');
  }catch(e){
    tb.innerHTML = '<tr><td colspan="10" style="color:#dc2626;text-align:center;padding:14px">Error red: '+_esc(e.message)+'</td></tr>';
  }
}

function abrirNuevaOS(){
  var ex = document.getElementById('modal-nueva-os'); if(ex) ex.remove();
  var m = document.createElement('div');
  m.id = 'modal-nueva-os';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
  m.innerHTML = '<div style="background:#fff;border-radius:14px;padding:24px;max-width:560px;width:100%;max-height:90vh;overflow-y:auto">'+
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h3 style="margin:0;color:#0f766e">🎨 Nueva Orden de Servicio</h3>'+
    '<button id="os-close" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>'+
    '<div style="font-size:11px;color:#64748b;margin-bottom:12px">Para serigrafía, tampografía, etiquetado u otro servicio sobre envases existentes (NO compra de material)</div>'+
    '<div style="display:grid;gap:10px">'+
      '<div><label style="font-size:12px;font-weight:600;color:#475569">Tipo de servicio *</label><select id="os-tipo" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:5px;margin-top:4px">'+
        '<option>Serigrafía</option><option>Tampografía</option><option>Etiquetado</option><option>Sleeve termoencogible</option><option>Hot stamping</option><option>Otro</option>'+
      '</select></div>'+
      '<div><label style="font-size:12px;font-weight:600;color:#475569">Proveedor *</label><input id="os-proveedor" type="text" list="planta-prov-datalist" placeholder="Nombre del taller" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:5px;margin-top:4px"></div>'+
      '<div><label style="font-size:12px;font-weight:600;color:#475569">Producto final *</label><input id="os-producto" type="text" placeholder="Ej: Renova C 10 30ml" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:5px;margin-top:4px"></div>'+
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'+
        '<div><label style="font-size:12px;font-weight:600;color:#475569">Envase (cód MEE)</label><input id="os-envase-cod" type="text" placeholder="MEE0023" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:5px;margin-top:4px"></div>'+
        '<div><label style="font-size:12px;font-weight:600;color:#475569">Cantidad uds *</label><input id="os-cantidad" type="number" min="1" placeholder="500" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:5px;margin-top:4px"></div>'+
      '</div>'+
      '<div><label style="font-size:12px;font-weight:600;color:#475569">Envase descripción</label><input id="os-envase-desc" type="text" placeholder="Frasco vidrio ambar 30ml gotero" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:5px;margin-top:4px"></div>'+
      '<div><label style="font-size:12px;font-weight:600;color:#475569">Arte / descripción del trabajo *</label><textarea id="os-arte" rows="3" placeholder="Logo Espagiria + lote + fecha venc · color blanco · ubicación frente" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:5px;margin-top:4px"></textarea></div>'+
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'+
        '<div><label style="font-size:12px;font-weight:600;color:#475569">Fecha requerida entrega</label><input id="os-fecha-req" type="date" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:5px;margin-top:4px"></div>'+
        '<div><label style="font-size:12px;font-weight:600;color:#475569">Costo estimado ($)</label><input id="os-costo" type="number" min="0" placeholder="450000" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:5px;margin-top:4px"></div>'+
      '</div>'+
      '<div><label style="font-size:12px;font-weight:600;color:#475569">Observaciones</label><textarea id="os-obs" rows="2" placeholder="(opcional)" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:5px;margin-top:4px"></textarea></div>'+
    '</div>'+
    '<div style="margin-top:14px;display:flex;gap:8px;justify-content:flex-end">'+
      '<button id="os-cancel" style="background:#94a3b8;color:#fff;padding:8px 16px;border:none;border-radius:6px;cursor:pointer">Cancelar</button>'+
      '<button id="os-crear" style="background:#0f766e;color:#fff;padding:8px 20px;border:none;border-radius:6px;font-weight:700;cursor:pointer">✓ Crear OS</button>'+
    '</div></div>';
  document.body.appendChild(m);
  document.getElementById('os-close').onclick = function(){ m.remove(); };
  document.getElementById('os-cancel').onclick = function(){ m.remove(); };
  document.getElementById('os-crear').onclick = async function(){
    var btn = this;
    var data = {
      tipo_servicio: (document.getElementById('os-tipo')||{value:''}).value,
      proveedor: (document.getElementById('os-proveedor')||{value:''}).value.trim(),
      producto_final: (document.getElementById('os-producto')||{value:''}).value.trim(),
      envase_codigo_mee: (document.getElementById('os-envase-cod')||{value:''}).value.trim(),
      envase_descripcion: (document.getElementById('os-envase-desc')||{value:''}).value.trim(),
      cantidad_unidades: parseInt((document.getElementById('os-cantidad')||{value:'0'}).value) || 0,
      arte_descripcion: (document.getElementById('os-arte')||{value:''}).value.trim(),
      fecha_requerida_entrega: (document.getElementById('os-fecha-req')||{value:''}).value,
      costo_estimado_cop: parseFloat((document.getElementById('os-costo')||{value:'0'}).value) || 0,
      observaciones: (document.getElementById('os-obs')||{value:''}).value.trim(),
    };
    if(!data.proveedor || !data.producto_final || !data.cantidad_unidades || !data.arte_descripcion){
      alert('Proveedor · producto · cantidad · arte son obligatorios');
      return;
    }
    btn.disabled = true; btn.textContent = 'Creando...';
    try{
      var r = await fetch('/api/compras/ordenes-servicio', _fetchOpts('POST', data));
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); btn.disabled = false; btn.textContent='✓ Crear OS'; return; }
      alert('✓ OS creada: '+d.numero_os+'\\n\\nSiguiente paso: apretar "📧 Enviar" para mandar al proveedor');
      m.remove();
      loadOrdenesServicio();
    }catch(e){ alert('Error red: '+e.message); btn.disabled = false; btn.textContent='✓ Crear OS'; }
  };
}

if(typeof document !== 'undefined' && !window._OS_DELEG){
  window._OS_DELEG = true;
  document.addEventListener('click', async function(ev){
    var b = ev.target && ev.target.closest && ev.target.closest('[data-os-act]');
    if(!b) return;
    var act = b.getAttribute('data-os-act');
    var num = b.getAttribute('data-num');
    if(act === 'estado'){
      var nuevo = b.getAttribute('data-nuevo');
      var obs = '';
      if(nuevo === 'Enviada'){
        if(!confirm('¿Marcar OS '+num+' como Enviada al proveedor?')) return;
      } else if(nuevo === 'Entregada'){
        obs = prompt('Observaciones de la entrega (ej. cantidad recibida real):') || '';
      }
      try{
        var r = await fetch('/api/compras/ordenes-servicio/'+encodeURIComponent(num)+'/estado',
          _fetchOpts('PATCH', {estado_nuevo: nuevo, observaciones: obs}));
        var d = await r.json();
        if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
        loadOrdenesServicio();
      }catch(e){ alert('Error red: '+e.message); }
    } else if(act === 'detalle'){
      verDetalleOS(num);
    }
  });
}
async function verDetalleOS(num){
  try{
    var r = await fetch('/api/compras/ordenes-servicio/'+encodeURIComponent(num));
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    var ex = document.getElementById('modal-os-det'); if(ex) ex.remove();
    var m = document.createElement('div');
    m.id = 'modal-os-det';
    m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
    var tl = (d.timeline||[]).map(function(e){
      return '<div style="border-left:3px solid #0891b2;padding:6px 10px;margin-bottom:6px;background:#f8fafc;font-size:12px"><b>'+_esc(e.estado_nuevo)+'</b> <span style="color:#94a3b8">'+(e.ts||'').substring(0,16)+' · '+_esc(e.usuario)+'</span>'+(e.observaciones?'<br><span style="color:#475569">'+_esc(e.observaciones)+'</span>':'')+'</div>';
    }).join('');
    m.innerHTML = '<div style="background:#fff;border-radius:12px;padding:20px;max-width:640px;width:100%;max-height:90vh;overflow-y:auto">'+
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h3 style="margin:0;color:#0f766e">🎨 '+_esc(d.numero_os)+'</h3><button id="osd-close" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>'+
      '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;background:#f8fafc;padding:12px;border-radius:8px;margin-bottom:14px;font-size:12px">'+
        '<div><b>Proveedor</b><br>'+_esc(d.proveedor||'')+'</div>'+
        '<div><b>Tipo</b><br>'+_esc(d.tipo_servicio||'')+'</div>'+
        '<div><b>Producto</b><br>'+_esc(d.producto_final||'')+'</div>'+
        '<div><b>Envase</b><br>'+_esc(d.envase_descripcion||d.envase_codigo_mee||'—')+'</div>'+
        '<div><b>Unidades</b><br><span style="font-size:18px;font-weight:800;color:#0f766e">'+(d.cantidad_unidades||0)+'</span></div>'+
        '<div><b>Estado</b><br>'+_esc(d.estado||'')+'</div>'+
        '<div><b>F. solicitud</b><br>'+_esc((d.fecha_solicitud||'').substring(0,10))+'</div>'+
        '<div><b>F. requerida</b><br>'+_esc((d.fecha_requerida_entrega||'').substring(0,10) || '—')+'</div>'+
        '<div><b>Costo est.</b><br>'+fmt((d.costo_estimado_cop||0).toFixed(0))+'</div>'+
        '<div><b>Costo real</b><br>'+fmt((d.costo_real_cop||0).toFixed(0))+'</div>'+
      '</div>'+
      '<div style="margin-bottom:10px;background:#fef3c7;border-left:3px solid #ca8a04;padding:10px;font-size:12px"><b>Arte solicitado:</b><br>'+_esc(d.arte_descripcion||'—')+'</div>'+
      (d.observaciones ? '<div style="margin-bottom:10px;padding:8px;background:#f1f5f9;font-size:12px"><b>Observaciones:</b><br>'+_esc(d.observaciones)+'</div>' : '')+
      '<h4 style="margin:14px 0 6px;color:#475569">📜 Timeline</h4>'+
      (tl || '<div style="color:#94a3b8;font-size:12px">Sin eventos</div>')+
      '</div>';
    document.body.appendChild(m);
    document.getElementById('osd-close').onclick = function(){ m.remove(); };
    m.addEventListener('click', function(e){ if(e.target === m) m.remove(); });
  }catch(e){ alert('Error red: '+e.message); }
}

// Compras PRO · Sebastián 21-may-2026 · 4 KPIs grandes franja superior
// Consultor procurement: "Sebas debería ver 4 KPIs que importan al entrar, no 20"
// Fetchers memoizados por carga del dashboard · el dashboard-home preserva el
// status (para el manejo de 401 en renderDashHome2). Se resetean a null al
// entrar a la pestaña dash → 1 sola llamada de red compartida por 3 renders.
function _fetchDashHome(){
  if(!window._dashHomeP){
    window._dashHomeP = fetch('/api/compras/dashboard-home').then(function(r){
      return r.json().then(function(j){ return {status:r.status, ok:r.ok, data:j}; })
        .catch(function(){ return {status:r.status, ok:r.ok, data:{}}; });
    }).catch(function(){ return {status:0, ok:false, data:{}}; });
  }
  return window._dashHomeP;
}
function _fetchCashFlow(){
  if(!window._cashFlowP){
    window._cashFlowP = fetch('/api/compras/cash-flow').then(function(r){
      return r.ok ? r.json() : {};
    }).catch(function(){ return {}; });
  }
  return window._cashFlowP;
}
async function renderKpisGrandes(){
  var cont = document.getElementById('dash-kpis-grandes');
  if(!cont) return;
  try{
    var [hHome, rCash] = await Promise.all([ _fetchDashHome(), _fetchCashFlow() ]);
    var rHome = hHome.data || {};
    var p30 = ((rCash.proyecciones||[]).find(function(x){return x.dias===30;})) || {};
    var kpis = rHome.kpis || {};
    var counts = rHome.counts || {};
    var cashCol = p30.total_salida > 50000000 ? '#dc2626' : (p30.total_salida > 20000000 ? '#ca8a04' : '#16a34a');
    var ocsRiesgo = (rHome.alertas_ocs_viejas||[]).length;
    var solsSinTocar = kpis.sols_sin_tocar_3d || 0;
    var salud = kpis.salud_score || 0;
    var saludCol = salud >= 80 ? '#16a34a' : (salud >= 60 ? '#ca8a04' : '#dc2626');
    // UI v2 · cards CLARAS con el color semántico como acento de borde (no
    // relleno pesado) · preserva la lógica ok/riesgo (verde/rojo/ámbar).
    var _kc='background:var(--cx-card);color:var(--cx-text);padding:14px;border-radius:12px;border:1px solid var(--cx-hairline);box-shadow:var(--cx-sh-card)';
    cont.innerHTML = ''+
      '<div style="'+_kc+';border-left:4px solid '+cashCol+'">'+
        '<div style="font-size:10px;text-transform:uppercase;color:var(--cx-text-mute);font-weight:700">💰 Cash 30 días</div>'+
        '<div style="font-size:1.9em;font-weight:800;line-height:1;margin-top:2px">'+fmt(p30.total_salida||0)+'</div>'+
        '<div style="font-size:10px;color:var(--cx-text-faint);margin-top:2px">'+((p30.ocs_por_pagar||{}).count||0)+' OCs + '+((p30.influencers||{}).count||0)+' infl.</div>'+
      '</div>'+
      '<div style="'+_kc+';border-left:4px solid '+(ocsRiesgo>0?'#dc2626':'#16a34a')+'">'+
        '<div style="font-size:10px;text-transform:uppercase;color:var(--cx-text-mute);font-weight:700">🚨 OCs en riesgo</div>'+
        '<div style="font-size:1.9em;font-weight:800;line-height:1;margin-top:2px;color:'+(ocsRiesgo>0?'#dc2626':'var(--cx-text)')+'">'+ocsRiesgo+'</div>'+
        '<div style="font-size:10px;color:var(--cx-text-faint);margin-top:2px">>10d sin recibir</div>'+
      '</div>'+
      '<div style="'+_kc+';border-left:4px solid '+(solsSinTocar>0?'#ca8a04':'#16a34a')+'">'+
        '<div style="font-size:10px;text-transform:uppercase;color:var(--cx-text-mute);font-weight:700">⏰ SOLs sin tocar</div>'+
        '<div style="font-size:1.9em;font-weight:800;line-height:1;margin-top:2px">'+solsSinTocar+'</div>'+
        '<div style="font-size:10px;color:var(--cx-text-faint);margin-top:2px">>3 días pendientes</div>'+
      '</div>'+
      '<div style="'+_kc+';border-left:4px solid '+saludCol+'">'+
        '<div style="font-size:10px;text-transform:uppercase;color:var(--cx-text-mute);font-weight:700">📊 Salud Compras</div>'+
        '<div style="font-size:1.9em;font-weight:800;line-height:1;margin-top:2px">'+salud+'/100</div>'+
        '<div style="font-size:10px;color:var(--cx-text-faint);margin-top:2px">'+(counts.por_pagar||0)+' por pagar · '+((counts.planta||0)+(counts.solic||0))+' SOLs</div>'+
      '</div>';
  }catch(e){
    cont.innerHTML = '<div style="color:#64748b;padding:10px;text-align:center;font-size:12px">⚠ KPIs no disponibles</div>';
  }
}

// Compras PRO · Sebastián 21-may-2026 · widgets consolidados Dashboard
async function renderAlertasBanner(){
  var cont = document.getElementById('dash-alertas-banner');
  if(!cont) return;
  try{
    var r = await fetch('/api/compras/alertas-vivas');
    if(!r.ok){ cont.innerHTML = ''; return; }
    var d = await r.json();
    // /api/compras/alertas-vivas devuelve listas categorizadas con severidad
    // 'critico'/'alto'/'medio'/'bajo'. Aplanamos a mensajes y mostramos solo
    // las críticas/altas (banner de atención inmediata).
    var esCrit = function(s){ return s === 'critico' || s === 'alto'; };
    var alertas = [];
    (d.ocs_sin_recibir || []).forEach(function(a){
      if(esCrit(a.severidad)) alertas.push('OC '+(a.numero_oc||'')+' sin recibir '+(a.dias_sin_recibir||'?')+'d');
    });
    (d.pagos_por_vencer || []).forEach(function(a){
      if(esCrit(a.severidad)) alertas.push('Pago OC '+(a.numero_oc||'')+' por vencer');
    });
    (d.solicitudes_pendientes || []).forEach(function(a){
      if(esCrit(a.severidad)) alertas.push('SOL '+(a.numero||'')+' pendiente '+(a.dias_pendiente||'?')+'d');
    });
    (d.ocs_borrador_estancadas || []).forEach(function(a){
      if(esCrit(a.severidad)) alertas.push('OC borrador '+(a.numero_oc||'')+' estancada');
    });
    alertas = alertas.slice(0, 5);
    if(!alertas.length){ cont.innerHTML = ''; return; }
    cont.innerHTML = '<div style="background:#fef2f2;border:2px solid #dc2626;border-radius:10px;padding:12px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">'+
      '<div style="font-size:1.4em">🚨</div>'+
      '<div style="flex:1;font-size:13px;color:#991b1b"><b>'+alertas.length+' alerta(s) críticas:</b> '+
      alertas.map(function(m){return _esc(m);}).join(' · ')+
      '</div></div>';
  }catch(e){ cont.innerHTML = ''; }
}
async function renderMisSolicWidget(){
  var cont = document.getElementById('dash-mis-solic-widget');
  if(!cont) return;
  try{
    var r = await fetch('/api/solicitudes-compra/mis');
    if(!r.ok){ cont.innerHTML = ''; return; }
    var d = await r.json();
    var sols = (d.solicitudes || d.items || []).slice(0, 5);
    if(!sols.length){ cont.innerHTML = ''; return; }
    var html = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-weight:800;color:#0f172a;font-size:13px;margin-bottom:8px">👤 Solicitudes recientes</div>';
    html += '<div style="font-size:12px">';
    sols.forEach(function(s){
      var col = s.estado === 'Aprobada' ? '#16a34a' : (s.estado === 'Rechazada' ? '#dc2626' : (s.estado === 'Pendiente' ? '#ca8a04' : '#64748b'));
      html += '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f1f5f9"><span><b style="font-family:monospace">'+_esc(s.numero)+'</b> · '+_esc((s.observaciones||s.categoria||'').substring(0,60))+'</span><span style="background:'+col+';color:#fff;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700">'+_esc(s.estado)+'</span></div>';
    });
    html += '</div></div>';
    cont.innerHTML = html;
  }catch(e){ cont.innerHTML = ''; }
}

// Compras 2.0 · 21-may-2026 · Dashboard HOME dual por rol
async function renderDashHome2(){
  var cont = document.getElementById('dash-home-2');
  if(!cont) return;
  try{
    var hHome = await _fetchDashHome();
    if(hHome.status === 401){
      cont.innerHTML = '<div style="background:#fef2f2;color:#991b1b;padding:14px;border-radius:8px;font-weight:700">⚠ Sesión expirada · <a href="/login?next=/compras" style="color:#dc2626;text-decoration:underline">re-loguear</a></div>';
      return;
    }
    if(!hHome.ok){
      cont.innerHTML = '<div style="color:#dc2626;padding:14px">Error '+hHome.status+' al cargar dashboard</div>';
      return;
    }
    var d = hHome.data || {};
    // Actualizar badges en sub-tabs
    var counts = d.counts || {};
    function _setBadge(tabId, n){
      var btn = document.getElementById('tn-'+tabId);
      if(!btn) return;
      // Limpiar badges previos
      var b = btn.querySelector('.cx-tab-badge');
      if(b) b.remove();
      if(n > 0){
        var span = document.createElement('span');
        span.className = 'cx-tab-badge';
        span.style.cssText = 'background:#dc2626;color:#fff;font-size:10px;font-weight:800;padding:1px 6px;border-radius:8px;margin-left:6px';
        span.textContent = n;
        btn.appendChild(span);
      }
    }
    _setBadge('planta', counts.planta||0);
    _setBadge('solic', counts.solic||0);
    _setBadge('por-pagar', counts.por_pagar||0);
    if(d.role === 'admin') _setBadge('influencer', counts.influencer||0);

    var html = '';
    if(d.role === 'admin'){
      // VISTA ADMIN · Panel ejecutivo + Influencers prominente
      // Panel Influencers (privado · Sebastián entra a pagar aquí) · a ancho
      // completo. La Salud Compras + OCs en riesgo ya viven en las 4 KPIs de
      // arriba (no se duplican). Top proveedores 30d va como pie del panel.
      var inflTot = (d.influencers_monto_total || 0);
      var inflList = d.influencers_pendientes || [];
      html += '<div style="background:linear-gradient(135deg,#fdf2f8,#f5f3ff);border:1px solid #ddd6fe;border-radius:12px;padding:18px;box-shadow:var(--cx-sh-card)">'+
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><div style="font-weight:800;font-size:15px;color:#9f1239">💸 Influencers <span style="font-weight:600;font-size:11px;color:#a78bfa">privado · solo tú</span></div>'+
        '<a href="/admin/influencers" style="font-size:11px;color:#9f1239;font-weight:700;text-decoration:none">Ver todos →</a></div>'+
        '<div style="display:grid;grid-template-columns:minmax(160px,220px) 1fr;gap:14px;align-items:start">'+
          '<div style="background:#fff;padding:12px 14px;border-radius:10px;border:1px solid #f5d0e8"><div style="font-size:10px;text-transform:uppercase;letter-spacing:.03em;color:#9f1239;font-weight:700">Por pagar</div><div style="font-size:2em;font-weight:800;color:#be185d;line-height:1.1">'+fmt(inflTot.toFixed(0))+'</div><div style="font-size:11px;color:#9f1239">'+inflList.length+' pendiente(s)</div></div>';
      html += '<div style="font-size:11px;color:#9f1239">';
      if(inflList.length){
        html += '<div style="max-height:170px;overflow-y:auto;display:flex;flex-direction:column;gap:5px">';
        inflList.slice(0,6).forEach(function(it){
          html += '<div style="background:#fff;padding:7px 10px;border-radius:7px;display:flex;justify-content:space-between;align-items:center"><div><b>'+_esc(it.solicitante||'?')+'</b> <span style="color:#94a3b8;font-size:10px">'+_esc(it.concepto||'')+'</span></div><div style="text-align:right;white-space:nowrap;margin-left:8px"><b style="color:#be185d">'+fmt(it.monto.toFixed(0))+'</b> <a href="/admin/influencers" style="font-size:9px;color:#0e7490">pagar</a></div></div>';
        });
        html += '</div>';
      } else {
        html += '<div style="color:#a78bfa;text-align:center;padding:18px 0">✓ Sin pagos pendientes</div>';
      }
      html += '</div>';   // fin col derecha
      html += '</div>';   // fin grid interno
      // Top proveedores 30d (pie · dato útil que estaba en el panel Salud)
      html += '<div style="margin-top:12px;padding-top:10px;border-top:1px solid #f5d0e8;font-size:11px;color:#475569">'+
        '<b>Top proveedores 30d:</b> '+
        ((d.top_proveedores_30d||[]).map(function(p){
          return '<span style="background:#fff;padding:3px 8px;border-radius:8px;margin:2px 3px 0 0;display:inline-block;border:1px solid #eee">'+_esc(p.proveedor)+' · '+fmt(p.monto.toFixed(0))+'</span>';
        }).join('') || '<span style="color:#cbd5e1">sin datos</span>')+
      '</div>';
      html += '</div>';   // fin panel influencers
    } else {
      // VISTA CATALINA · Buzón de pedidos priorizado
      html += '<div style="background:linear-gradient(135deg,#ecfdf5,#dcfce7);border:1px solid #16a34a;border-radius:10px;padding:16px;margin-bottom:14px">'+
        '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">'+
          '<div><h2 style="margin:0;color:#166534;font-size:18px">📥 Tu buzón de hoy</h2><div style="font-size:12px;color:#15803d;margin-top:2px">SOLs nuevas que requieren acción</div></div>'+
          '<div style="text-align:right"><div style="font-size:2em;font-weight:800;color:#166534">'+((counts.planta||0) + (counts.solic||0))+'</div><div style="font-size:11px;color:#15803d">total pendientes</div></div>'+
        '</div></div>';
      // Cards de las 2 fuentes
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px">';
      html += '<div onclick="document.querySelector(\\'[data-tab=planta]\\').click()" style="background:#fff;border:1px solid #0e7490;border-radius:10px;padding:14px;cursor:pointer;transition:transform .15s" onmouseover="this.style.transform=\\'translateY(-2px)\\'" onmouseout="this.style.transform=\\'\\'">'+
        '<div style="font-size:11px;color:#0e7490;font-weight:700;text-transform:uppercase">🏭 Planta</div>'+
        '<div style="font-size:2.4em;font-weight:800;color:#0e7490;line-height:1">'+(counts.planta||0)+'</div>'+
        '<div style="font-size:11px;color:#64748b;margin-top:4px">MP+Empaque pendientes · agrupar por proveedor</div>'+
      '</div>';
      html += '<div onclick="document.querySelector(\\'[data-tab=solic]\\').click()" style="background:#fff;border:1px solid #475569;border-radius:10px;padding:14px;cursor:pointer;transition:transform .15s" onmouseover="this.style.transform=\\'translateY(-2px)\\'" onmouseout="this.style.transform=\\'\\'">'+
        '<div style="font-size:11px;color:#475569;font-weight:700;text-transform:uppercase">📋 Solicitudes</div>'+
        '<div style="font-size:2.4em;font-weight:800;color:#475569;line-height:1">'+(counts.solic||0)+'</div>'+
        '<div style="font-size:11px;color:#64748b;margin-top:4px">Generales (papelería, EPP, servicios)</div>'+
      '</div>';
      html += '<div onclick="document.querySelector(\\'[data-tab=por-pagar]\\').click()" style="background:#fff;border:1px solid #ca8a04;border-radius:10px;padding:14px;cursor:pointer;transition:transform .15s" onmouseover="this.style.transform=\\'translateY(-2px)\\'" onmouseout="this.style.transform=\\'\\'">'+
        '<div style="font-size:11px;color:#ca8a04;font-weight:700;text-transform:uppercase">💰 Por pagar</div>'+
        '<div style="font-size:2.4em;font-weight:800;color:#ca8a04;line-height:1">'+(counts.por_pagar||0)+'</div>'+
        '<div style="font-size:11px;color:#64748b;margin-top:4px">OCs autorizadas sin pago</div>'+
      '</div>';
      html += '</div>';
      // Lista de últimas SOLs entrantes
      if((d.buzon_recientes||[]).length){
        html += '<div style="margin-top:14px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px"><b style="color:#0f172a;font-size:13px">Últimas SOLs (48h):</b>';
        html += '<div style="margin-top:8px;display:flex;flex-direction:column;gap:5px;font-size:12px">';
        d.buzon_recientes.slice(0,5).forEach(function(s){
          html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 8px;background:#f8fafc;border-radius:5px"><div><b style="font-family:monospace">'+_esc(s.numero)+'</b> · '+_esc(s.solicitante)+' <span style="color:#94a3b8;font-size:10px">('+_esc(s.categoria)+')</span></div><div style="font-weight:700;color:#0f172a">'+fmt(s.valor.toFixed(0))+'</div></div>';
        });
        html += '</div></div>';
      }
    }

    // Widget Predicción demanda (solo admin) · el Cash Flow proyectado ya vive
    // en el KPI "Cash 30 días"; las OCs >10d en el KPI "OCs en riesgo".
    if(d.role === 'admin'){
      html += '<div id="dash-extra-widgets" style="margin-top:14px"></div>';
    }

    cont.innerHTML = html;
    cargarConsumosElevados();
    // Cargar widgets extra (Cash Flow + Predicción) si admin
    if(d.role === 'admin'){
      cargarWidgetsExtra();
    }
  }catch(e){
    cont.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+_esc(e.message)+'</div>';
  }
}
// Consumos elevados (gasto que sube) · reusa /api/compras/consumos/tendencia · Catalina + admin
async function cargarConsumosElevados(){
  var cont=document.getElementById('dash-consumos-elev'); if(!cont) return;
  try{
    var j=await (await fetch('/api/compras/consumos/tendencia?meses=8',{credentials:'same-origin'})).json();
    var al=(j&&j.alertas)?j.alertas:[];
    if(!al.length){ cont.innerHTML=''; return; }
    var _f=function(n){return '$'+(Math.round(n||0)).toLocaleString('es-CO');};
    var h='<div style="background:#fff7ed;border:1px solid #fdba74;border-radius:10px;padding:12px 16px">'+
      '<div style="font-weight:800;color:#9a3412;font-size:14px;margin-bottom:6px">&#128200; Consumos elevados <span style="font-size:11px;font-weight:600;color:#b45309">· gasto que subió este mes</span></div>';
    al.slice(0,5).forEach(function(a){
      h+='<div style="font-size:13px;color:#7c2d12;padding:3px 0">&#9888;&#65039; <b>'+_esc(a.categoria)+'</b> subió <b>+'+a.variacion_pct+'%</b> ('+_f(a.ultimo)+' vs prom '+_f(a.promedio_previo)+')</div>';
    });
    h+='<a href="/compras/consumos" style="font-size:12px;color:#9a3412;font-weight:700">ver tendencia completa &rarr;</a></div>';
    cont.innerHTML=h;
  }catch(e){ cont.innerHTML=''; }
}
// Gap #4 · widgets Cash Flow + Predicción demanda
async function cargarWidgetsExtra(){
  var cont = document.getElementById('dash-extra-widgets');
  if(!cont) return;
  // Predicción demanda · top 5 urgentes (el Cash Flow proyectado ya está en el KPI)
  try{
    var rp = await fetch('/api/compras/prediccion-demanda');
    var dp = await rp.json();
    var urgentes = (dp.items||[]).filter(function(x){return x.accion==='URGENTE';}).slice(0,5);
    var pronto = (dp.items||[]).filter(function(x){return x.accion==='PEDIR_PRONTO';}).slice(0,5);
    var predHtml = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px">'+
      '<div style="font-weight:800;color:#0f172a;font-size:13px;margin-bottom:8px">🔮 Predicción demanda</div>'+
      '<div style="display:flex;gap:8px;margin-bottom:8px;font-size:11px">'+
        '<span style="background:#fee2e2;color:#991b1b;padding:3px 10px;border-radius:8px;font-weight:700">🔴 '+((dp.counts||{}).URGENTE||0)+' urgentes</span>'+
        '<span style="background:#fef3c7;color:#78350f;padding:3px 10px;border-radius:8px;font-weight:700">🟡 '+((dp.counts||{}).PEDIR_PRONTO||0)+' pronto</span>'+
        '<span style="background:#dcfce7;color:#166534;padding:3px 10px;border-radius:8px;font-weight:700">🟢 '+((dp.counts||{}).OK||0)+' OK</span>'+
      '</div>';
    if(urgentes.length){
      predHtml += '<div style="font-size:11px"><b style="color:#991b1b">🔴 Pedir AHORA:</b>';
      urgentes.forEach(function(it){
        predHtml += '<div style="background:#fef2f2;padding:4px 8px;border-radius:5px;margin-top:3px;display:flex;justify-content:space-between"><span><b>'+_esc(it.nombre)+'</b> <span style="color:#94a3b8;font-size:10px">'+_esc(it.codigo_mp)+'</span></span><span style="color:#dc2626;font-weight:700">'+it.dias_hasta_quiebre+'d · '+fmt(it.cantidad_sugerida_g)+'g</span></div>';
      });
      predHtml += '</div>';
    }
    if(pronto.length){
      predHtml += '<div style="margin-top:6px;font-size:11px"><b style="color:#78350f">🟡 Pedir pronto:</b>';
      pronto.forEach(function(it){
        predHtml += '<div style="background:#fffbeb;padding:4px 8px;border-radius:5px;margin-top:3px;display:flex;justify-content:space-between"><span>'+_esc(it.nombre)+'</span><span style="color:#92400e">'+it.dias_hasta_quiebre+'d</span></div>';
      });
      predHtml += '</div>';
    }
    if(!urgentes.length && !pronto.length){
      predHtml += '<div style="color:#166534;text-align:center;padding:14px;font-size:12px">✓ Stock adecuado · sin urgencias</div>';
    }
    predHtml += '</div>';
    cont.innerHTML += predHtml;
  }catch(_){}
}
function _esc(s){return String(s||'').replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}

async function loadDashboardEjecutivo(){
  // Sprint Compras N3 · 21-may-2026
  var cont = document.getElementById('dashboard-ejecutivo');
  if(!cont) return;
  try{
    var r = await fetch('/api/compras/dashboard-ejecutivo');
    if(!r.ok) return;
    var d = await r.json();
    var k = d.kpis || {};
    var color = k.salud_color === 'verde' ? '#16a34a' :
                (k.salud_color === 'amarillo' ? '#ca8a04' : '#dc2626');
    var topProv = (d.top_proveedores_mes||[]).slice(0,3);
    var topHtml = topProv.map(function(p){
      return '<span style="background:#f1f5f9;padding:3px 8px;border-radius:8px;font-size:11px;margin-right:5px"><b>'+esc(p.proveedor)+'</b> · '+p.ocs+' OCs · '+fmt(p.monto.toFixed(0))+'</span>';
    }).join('');
    cont.innerHTML =
      '<div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:10px">'+
        '<div style="font-weight:700;font-size:14px;color:#0f172a">📊 Dashboard ejecutivo Catalina</div>'+
        '<div style="background:'+color+';color:#fff;padding:3px 10px;border-radius:10px;font-size:12px;font-weight:700">Salud '+k.salud_score+'/100</div>'+
      '</div>'+
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px">'+
        _wkpi('⏰ SOLs sin tocar', k.sols_sin_tocar_3d, '>3 días', k.sols_sin_tocar_3d > 0 ? '#dc2626' : '#475569')+
        _wkpi('📝 OCs sin autorizar', k.ocs_sin_autorizar_5d, '>5 días', k.ocs_sin_autorizar_5d > 0 ? '#ca8a04' : '#475569')+
        _wkpi('💸 Influencers vencidos', k.influencers_vencidos, 'pagar ya', k.influencers_vencidos > 0 ? '#dc2626' : '#475569')+
        _wkpi('📋 Cotizaciones', k.cotizaciones_pendientes, 'sin respuesta', '#0e7490')+
        _wkpi('📄 OCs Borrador', k.ocs_borrador, 'sin enviar', '#475569')+
      '</div>'+
      (topHtml ? '<div style="margin-top:10px;font-size:11px;color:#64748b">Top proveedores 30d: '+topHtml+'</div>' : '');
  }catch(e){ /* silenciar · widget opcional */ }
}
function _wkpi(label, valor, sub, color){
  return '<div style="background:#fff;border:1px solid #e7e5e4;border-radius:6px;padding:7px 9px">'+
    '<div style="font-size:10px;color:#64748b">'+label+'</div>'+
    '<div style="font-size:1.4em;font-weight:800;color:'+color+'">'+(valor||0)+'</div>'+
    '<div style="font-size:9px;color:#94a3b8">'+sub+'</div>'+
  '</div>';
}

async function loadData(){
  // PERF (16-jun · audit velocidad): los 4 fetches son independientes → en
  // PARALELO (antes en serie, sumaban latencias) + se quitó el legacy
  // loadDashboardEjecutivo (pintaba en un <div display:none>, trabajo perdido).
  // mps-deficit usa caché de calendario server-side (60s) para no saturar workers.
  await Promise.all([
    fetch('/api/ordenes-compra').then(function(r){ if(!r.ok) throw new Error('OC API '+r.status); return r.json(); })
      .then(function(d){ OCS = d.ordenes||[]; })
      .catch(function(e){ console.error('OC load error:',e); OCS=[]; }),
    fetch('/api/proveedores-compras').then(function(r){ if(!r.ok) throw new Error('Prov API '+r.status); return r.json(); })
      .then(function(d){ PROVS = d.proveedores||[]; })
      .catch(function(e){ console.error('Prov load error:',e); PROVS=[]; }),
    fetch('/api/maestro-mps').then(function(r){ if(!r.ok) throw new Error('Cat API '+r.status); return r.json(); })
      .then(function(d){ _MPCAT = d.mps||[]; })
      .catch(function(e){ console.error('MPCAT load error:',e); _MPCAT=[]; }),
    // Catálogo de CONSUMIBLES (papelería/EPP/servicios) para el buscador de Crear OC · Sebastián 1-jul
    fetch('/api/compras/consumibles').then(function(r){ return r.ok?r.json():{consumibles:[]}; })
      .then(function(d){ _CONSUM = d.consumibles||[]; if(typeof buildConsumDL==='function') buildConsumDL(); })
      .catch(function(e){ console.error('Consumibles load error:',e); _CONSUM=[]; }),
    // Centro de Programación: déficit real (velocidad Shopify + producciones futuras)
    fetch('/api/programacion/mps-deficit').then(function(r){ if(!r.ok) throw new Error('Programacion deficit API '+r.status); return r.json(); })
      .then(function(d4){
        _ALERTAS_MP = (d4.mps||[]).map(function(m){
          return {
            codigo_mp: m.codigo_mp,
            nombre: m.nombre,
            stock_actual: m.stock_actual_g === -1 ? Infinity : m.stock_actual_g,
            stock_minimo: 0,
            deficit: m.deficit_g,
            proveedor: m.proveedor || '',
            productos: m.productos_afectados || [],
            tipo: 'MP',
            es_china: m.es_china || false,
          };
        });
      })
      .catch(function(e){ console.error('MPs deficit load error:',e); _ALERTAS_MP=[]; }),
    // Déficit de ENVASES (MEE) · 18-jun · misma fuente unificada (producto_presentaciones)
    fetch('/api/abastecimiento/consumo-horizontes?tipo=mee').then(function(r){ return r.ok ? r.json() : {mees:[],horizontes:[]}; })
      .then(function(dm){
        var hm=(dm.horizontes||[]); var hmax=hm.length?String(hm[hm.length-1]):'90';
        _ALERTAS_MEE=(dm.mees||[]).filter(function(m){ return m.deficit && parseFloat(m.deficit[hmax]||0)>0.5; }).map(function(m){
          return { codigo:m.codigo, nombre:m.nombre, deficit:parseFloat((m.deficit||{})[hmax]||0),
                   proveedor:m.proveedor_sugerido||'', urgencia:m.urgencia||'' };
        });
      })
      .catch(function(e){ console.error('MEE deficit load error:',e); _ALERTAS_MEE=[]; })
  ]);
  renderDash();
  renderMPAlerts();
  // Alertas de programación (no bloquea la carga)
  cargarAlertasProgramacion();
}

async function cargarAlertasProgramacion(){
  try{
    var r = await fetch('/api/programacion/n-alertas');
    var d = await r.json();
    var banner = document.getElementById('prog-alert-banner');
    var text = document.getElementById('prog-alert-text');
    if(!banner || !text) return;
    if(d.n > 0){
      banner.style.display = 'block';
      var label = d.criticos > 0
        ? d.criticos + ' alerta(s) CR\u00EDTICA(S) — ' + d.n + ' total'
        : d.n + ' alerta(s) de programaci\u00F3n activas';
      text.textContent = '\u26A0\uFE0F ' + label + ' — MPs faltantes o stock insuficiente a 60 d\u00EDas';
    } else {
      banner.style.display = 'none';
    }
  }catch(e){ /* silencioso si programacion no est\u00E1 disponible */ }
}

async function generarOCDesdeCompras(btnEl){
  if(!confirm('Crear solicitud de compra autom\u00E1tica para todos los MPs con d\u00E9ficit de producci\u00F3n?')) return;
  if(btnEl){ btnEl.disabled = true; btnEl.textContent = 'Generando...'; }
  try{
    var r = await fetch('/api/programacion/generar-oc', {
      method: 'POST', headers: {'Content-Type': 'application/json'}
    });
    var d = await r.json();
    if(d.ok){
      alert('\u2705 ' + d.mensaje);
      // Refresh dashboard
      renderDash();
    } else {
      alert('Error: ' + (d.error || 'desconocido'));
    }
  }catch(e){
    alert('Error de red: ' + e.message);
  }finally{
    if(btnEl){ btnEl.disabled = false; btnEl.textContent = '🛒 Generar OC'; }
  }
}

// ─── Dashboard ────────────────────────────────────────────────────
async function renderDash(){
  // Compras PRO · 21-may-2026 · renderDash legacy · no-op (paneles ocultos)
  // Antes corría 2 fetches + actualizaba DOM oculto · ahora skip silencioso
  // Las funciones widgets nuevas (renderDashHome2, renderKpisGrandes...) cubren.
  if(true) return;
  if(!SOLIC||!SOLIC.length){
    try{
      var _r1=await fetch('/api/solicitudes-compra');
      var _d1=await _r1.json();
      var _r2=await fetch('/api/solicitudes-compra?categoria=Cuenta+de+Cobro');
      var _d2=await _r2.json();
      var _all=(_d1.solicitudes||[]).concat(_d2.solicitudes||[]);
      var _seen={};
      SOLIC=_all.filter(function(s){ if(_seen[s.numero]) return false; _seen[s.numero]=1; return true; });
    }catch(e){ SOLIC=[]; }
  }

  // KPI data
  var mes=new Date().toISOString().substring(0,7);
  // Sebastian (30-abr-2026): SOLs y OCs de influencers NO deben salir en
  // el dashboard de Compras — Catalina no las gestiona. El flujo correcto es
  // Jefferson (Marketing) solicita pago → aparece en tab Influencers (admin
  // only) → Sebastian paga. Las cantidades SI se cuentan en el KPI total
  // para que el panorama financiero quede completo.
  function _esInflLike(x){
    var c = (x && (x.categoria||'') ).toString().toLowerCase();
    return c.indexOf('influencer')>=0 || c.indexOf('marketing')>=0
        || c.indexOf('cuenta de cobro')>=0;
  }
  var solicPend=SOLIC.filter(function(s){ return s.estado==='Pendiente'; });
  var solicPendVisible=solicPend.filter(function(s){ return !_esInflLike(s); });
  var solicPendInfl=solicPend.length - solicPendVisible.length;

  // Estados que cuentan como "OC abierta / por procesar" — KPI cuenta TODAS
  // (incluyendo influencer), pero la lista visual oculta las de influencer.
  var _OC_ABIERTA = ['Borrador','Revisada','Aprobada','Autorizada','Parcial'];
  var ocsPorPagar=OCS.filter(function(o){ return _OC_ABIERTA.indexOf(o.estado)>=0; });
  var ocsPorPagarVisible=ocsPorPagar.filter(function(o){ return !_esInflLike(o); });
  var ocsPorPagarInfl=ocsPorPagar.length - ocsPorPagarVisible.length;
  var pagMes=OCS.filter(function(o){ return o.estado==='Pagada'&&(o.fecha_pago||o.fecha||'').startsWith(mes); });
  var vPorPagar=ocsPorPagar.reduce(function(s,o){ return s+parseFloat(o.valor_total||0); },0);
  var vMes=pagMes.reduce(function(s,o){ return s+parseFloat(o.valor_total||0); },0);
  var nDeficit=(_ALERTAS_MP||[]).filter(function(a){ return a.estado==='deficit'; }).length;

  // KPIs
  document.getElementById('kpi-area').innerHTML=
    mkKpi('SOLs pendientes',solicPend.length+' solicitudes','Esperando aprobación',solicPend.length>0?'w':'')+
    mkKpi('OCs en proceso',ocsPorPagar.length+' abiertas',fmt(vPorPagar),ocsPorPagar.length>0?'w':'')+
    mkKpi('Pagado este mes',pagMes.length+' OCs',fmt(vMes),'g')+
    mkKpi('MPs en déficit',nDeficit+' materiales','Stock bajo punto reorden',nDeficit>0?'w':'');

  // Left queue: SOLs pending approval
  var urgColor={'Alta':'#dc2626','Media':'#f59e0b','Normal':'#64748b'};
  var stBg={'Pendiente':'#fef3c7','Aprobada':'#d1fae5','Rechazada':'#fee2e2','Pagada':'#e0f2fe'};
  var stFg={'Pendiente':'#92400e','Aprobada':'#065f46','Rechazada':'#991b1b','Pagada':'#075985'};
  // Cards de SOL ENRIQUECIDAS — Catalina pidio ver TODOS los datos sin abrir
  // cada modal: items, observaciones completas, justificacion, total estimado.
  // Footer cuando hay influencer items ocultos: link al tab Influencers (admin only).
  var _hintInflSol = (solicPendInfl>0)
    ? '<div style="margin-top:8px;padding:8px 10px;background:#f3e8ff;border-left:3px solid #8b5cf6;border-radius:0 6px 6px 0;font-size:11px;color:#5b21b6;">'
      +'+ '+solicPendInfl+' SOL de influencers ocultas — ver tab '
      +'<button onclick="document.querySelector(&quot;[data-tab=influencer]&quot;).click()" '
      +'style="background:none;border:none;color:#7c3aed;text-decoration:underline;cursor:pointer;font-weight:700;padding:0;font-size:11px;">Influencers</button>'
      +'</div>' : '';
  var _hintInflOC = (ocsPorPagarInfl>0)
    ? '<div style="margin-top:8px;padding:8px 10px;background:#f3e8ff;border-left:3px solid #8b5cf6;border-radius:0 6px 6px 0;font-size:11px;color:#5b21b6;">'
      +'+ '+ocsPorPagarInfl+' OC de influencers ocultas — ver tab '
      +'<button onclick="document.querySelector(&quot;[data-tab=influencer]&quot;).click()" '
      +'style="background:none;border:none;color:#7c3aed;text-decoration:underline;cursor:pointer;font-weight:700;padding:0;font-size:11px;">Influencers</button>'
      +'</div>' : '';
  document.getElementById('q-aut').innerHTML=(solicPendVisible.length
    ? solicPendVisible.slice(0,8).map(function(s){
        var urg=s.urgencia||'Normal';
        var urgC=urgColor[urg]||'#78716c';
        var obs = (s.observaciones||'').trim();
        var valTot = parseFloat(s.valor||0);
        // Items resumidos (los carga get_solicitud_estado al hacer click,
        // aqui solo mostramos lo que ya viene en el listado)
        var itemsHint = '';
        if (s.numero) {
          itemsHint = '<div id="solitems-'+esc(s.numero)+'" style="margin-top:6px;font-size:11px;color:#57534e;line-height:1.5;"></div>';
          // Lazy-load items para esta SOL
          (function(num){
            setTimeout(function(){
              fetch('/api/solicitudes-compra/'+encodeURIComponent(num))
                .then(function(r){return r.json();})
                .then(function(d){
                  var box = document.getElementById('solitems-'+num);
                  if (!box || !d.items || !d.items.length) return;
                  var html = '<div style="background:#fafaf9;border-radius:6px;padding:6px 8px;margin-top:4px;">';
                  html += '<div style="font-size:10px;font-weight:700;color:#78716c;text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px;">'
                       + d.items.length + ' item(s) solicitados</div>';
                  d.items.slice(0,6).forEach(function(it){
                    var prov = it.proveedor||it.proveedor_sugerido||'';
                    html += '<div style="font-size:11px;display:flex;justify-content:space-between;gap:6px;padding:2px 0;">'
                         + '<span style="flex:1;">&bull; '+esc((it.nombre_mp||it.codigo_mp||'?').substring(0,40))+'</span>'
                         + '<span style="color:#78716c;white-space:nowrap;">'+(parseFloat(it.cantidad_g||0).toLocaleString('es-CO'))+' '+esc(it.unidad||'g')+'</span>'
                         + (prov?'<span style="color:#6d28d9;font-size:10px;">'+esc(prov.substring(0,12))+'</span>':'')
                         + '</div>';
                  });
                  if (d.items.length > 6) html += '<div style="font-size:10px;color:#a8a29e;margin-top:2px;">... y '+(d.items.length-6)+' mas</div>';
                  html += '</div>';
                  box.innerHTML = html;
                }).catch(function(){});
            }, 50);
          })(s.numero);
        }
        return '<div class="card" style="margin-bottom:10px;">'
          +'<div class="ch"><div><div class="cnum" style="font-family:monospace;">'+esc(s.numero)+'</div>'
          +'<div class="cprov">'+esc(s.solicitante||'-')+' &middot; '+esc(s.categoria||'-')+'</div></div>'
          +'<span class="badge" style="background:#fef3c7;color:#92400e;">Pendiente</span></div>'
          +'<div class="cmeta" style="flex-wrap:wrap;gap:8px;">'
          +'<span>&#128197; '+fdate(s.fecha)+'</span>'
          +(s.fecha_requerida?'<span style="color:#dc2626;">Requiere: '+esc(s.fecha_requerida)+'</span>':'')
          +(valTot>0?'<span style="font-weight:700;color:#15803d;">$'+valTot.toLocaleString('es-CO')+'</span>':'')
          +'<span style="color:'+urgC+';font-weight:700;">'+esc(urg)+'</span>'
          +'</div>'
          // Justificacion / observaciones COMPLETAS (no truncadas)
          +(obs?'<div style="margin-top:6px;background:#fffbeb;border-left:3px solid #f59e0b;padding:6px 10px;border-radius:0 6px 6px 0;font-size:11px;color:#78350f;line-height:1.5;">'+esc(obs)+'</div>':'')
          // Items lazy-loaded
          + itemsHint
          +'<div class="acts" style="margin-top:8px;"><button class="btn bi bs" onclick="revisarSolicitudPendiente(&quot;'+esc(s.numero)+'&quot;)">Revisar / Editar</button></div>'
          +'</div>';
      }).join('')
    : '<div class="empty" style="padding:20px;text-align:center;color:#a8a29e;">Sin solicitudes pendientes ✓</div>') + _hintInflSol;

  // Right queue: OCs autorizadas (ready to pay) — sin influencers
  document.getElementById('q-pag').innerHTML=(ocsPorPagarVisible.length
    ? ocsPorPagarVisible.slice(0,8).map(function(o){ return miniCard(o); }).join('')
    : '<div class="empty" style="padding:20px;text-align:center;color:#a8a29e;">Sin OCs autorizadas ✓</div>') + _hintInflOC;

  // Spending chart by category
  var _catLabels=['MP','MEE','SVC','ADM','INF','CC'];
  var _catColors=['#f59e0b','#3b82f6','#8b5cf6','#10b981','#ef4444','#7c3aed'];
  var _catTotals=_catLabels.map(function(g){ return OCS.filter(function(o){ return inGroup(o.categoria,g.toLowerCase())&&o.estado==='Pagada'; }).reduce(function(s,o){ return s+parseFloat(o.valor_total||0); },0); });
  var _maxV=Math.max.apply(null,_catTotals)||1;
  var _chartHTML='<div style="background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:14px 16px;margin-top:14px;">';
  _chartHTML+='<div style="font-weight:700;font-size:13px;color:#1c1917;margin-bottom:12px;">&#x1F4CA; Gasto acumulado por categoría (OCs Pagadas)</div>';
  _chartHTML+='<div style="display:grid;gap:7px;">';
  _catLabels.forEach(function(g,i){
    var pct=_catTotals[i]/_maxV*100;
    _chartHTML+='<div style="display:grid;grid-template-columns:48px 1fr 80px;align-items:center;gap:8px;">';
    _chartHTML+='<span style="font-size:11px;font-weight:600;color:#57534e;">'+g+'</span>';
    _chartHTML+='<div style="background:#f5f5f4;border-radius:4px;height:18px;overflow:hidden;"><div style="background:'+_catColors[i]+';width:'+pct.toFixed(1)+'%;height:100%;border-radius:4px;transition:width .4s;"></div></div>';
    _chartHTML+='<span style="font-size:11px;color:#57534e;text-align:right;">'+fmt(_catTotals[i])+'</span>';
    _chartHTML+='</div>';
  });
  _chartHTML+='</div></div>';
  var _chartWrap=document.getElementById('dash-chart-wrap');
  if(!_chartWrap){ _chartWrap=document.createElement('div'); _chartWrap.id='dash-chart-wrap'; document.getElementById('kpi-area').after(_chartWrap); }
  _chartWrap.innerHTML=_chartHTML;
}
function mkKpi(l,v,s,c){
  return '<div class="kpi"><div class="kpi-l">'+l+'</div><div class="kpi-v'+(c?' '+c:'')+'" >'+v+'</div><div class="kpi-s">'+s+'</div></div>';
}
// Click "Revisar" en la mini-card del Centro de Mando — abre el tab Solicitudes
// y hace scroll suave a la solicitud específica. Antes esto vivía como onclick
// inline con triple-escape de comillas que rompía el parser de JS al render
// (SyntaxError "Invalid left-hand side in assignment") y dejaba TODO el
// <script> de compras inerte — todos los botones quedaban sin handlers.
function revisarSolicitudPendiente(numero){
  var tabBtn = document.querySelector('[data-tab=solic]');
  if (tabBtn) tabBtn.click();
  setTimeout(function(){
    var el = document.querySelector('[data-num="'+(numero||'')+'"]');
    if (el) el.scrollIntoView({behavior:'smooth', block:'center'});
  }, 400);
}

function miniCard(o){
  var btns='<button class="btn bo bs" data-act="det" data-oc="'+esc(o.numero_oc)+'">Ver detalle</button>';
  // Sebastian (29-abr-2026): admin puede autorizar directo desde Borrador
  // (skip "Revisada" cuando es Sebastian/admin creando OC manual). El endpoint
  // /autorizar acepta cualquier estado, lo unico que faltaba era el boton.
  if((o.estado==='Borrador'||o.estado==='Revisada')&&ES_AUTORIZA) btns+='<button class="btn bi bs" data-act="aut" data-oc="'+esc(o.numero_oc)+'">Autorizar</button>';
  if(o.estado==='Autorizada'&&ES_AUTORIZA) btns+='<button class="btn bg bs" data-act="pago" data-oc="'+esc(o.numero_oc)+'" data-val="'+parseFloat(o.valor_total||0)+'" data-prov="'+esc(o.proveedor||'')+'">Pagar</button>';
  return '<div class="card" style="margin-bottom:8px;">'+
    '<div class="ch"><div><div class="cnum">'+esc(o.numero_oc)+'</div><div class="cprov">'+esc(o.proveedor||'-')+'</div></div>'+badge(o.estado)+'</div>'+
    '<div class="cval">'+fmt(o.valor_total)+(o.con_iva?'<span style="font-size:10px;background:#fde047;color:#92400e;border-radius:3px;padding:1px 5px;margin-left:5px;">+IVA</span>':'')+'</div>'+
    '<div class="cmeta"><span>'+fdate(o.fecha)+'</span>'+(o.fecha_entrega_est?'<span>&#x23F0; '+fdate(o.fecha_entrega_est)+'</span>':'')+'</div>'+
    (btns?'<div class="acts">'+btns+'</div>':'')+'</div>';
}

function renderCat(grp){
  var q=(document.getElementById('q-'+grp)||{value:''}).value.toLowerCase();
  var st=(document.getElementById('s-'+grp)||{value:''}).value;
  var list = OCS.filter(function(o){
    if(!inGroup(o.categoria,grp)) return false;
    if(st && o.estado!==st) return false;
    if(q && (o.numero_oc||'').toLowerCase().indexOf(q)<0 && (o.proveedor||'').toLowerCase().indexOf(q)<0 && (o.observaciones||'').toLowerCase().indexOf(q)<0) return false;
    return true;
  });
  var counts={total:list.length};
  ['Borrador','Revisada','Autorizada','Pagada','Recibida'].forEach(function(e){ counts[e]=list.filter(function(o){ return o.estado===e; }).length; });
  var vTotal=list.reduce(function(s,o){ return s+parseFloat(o.valor_total||0); },0);
  var pills='<span class="pill">'+list.length+' OCs</span>';
  if(counts.Borrador) pills+='<span class="pill">Borrador: '+counts.Borrador+'</span>';
  if(counts.Revisada) pills+='<span class="pill y">Revisada: '+counts.Revisada+'</span>';
  if(counts.Autorizada) pills+='<span class="pill b">Autorizada: '+counts.Autorizada+'</span>';
  if(counts.Pagada) pills+='<span class="pill g">Pagada: '+counts.Pagada+'</span>';
  pills+='<span class="pill" style="background:#e7e5e4;">'+fmt(vTotal)+'</span>';
  document.getElementById('pills-'+grp).innerHTML=pills;
  if(!list.length){
    document.getElementById('grid-'+grp).innerHTML='<div class="empty">No hay OCs en esta categoria</div>'; return;
  }
  document.getElementById('grid-'+grp).innerHTML=list.map(function(o){ return fullCard(o,grp); }).join('');
}
function fullCard(o,grp){
  var btns='<button class="btn bo bs" data-act="det" data-oc="'+esc(o.numero_oc)+'">&#128203; Ver</button>';
  if(o.estado==='Borrador'&&ES_C) btns+='<button class="btn bw bs" data-act="rev" data-oc="'+esc(o.numero_oc)+'" data-prov="'+esc(o.proveedor||'')+'" data-val="'+parseFloat(o.valor_total||0)+'" data-obs="'+esc((o.observaciones||'').substring(0,80))+'">Revisar &amp; Asignar</button>';
  if((o.estado==='Revisada'||o.estado==='Borrador')&&ES_AUTORIZA) btns+='<button class="btn bi bs" data-act="aut" data-oc="'+esc(o.numero_oc)+'">Autorizar</button>';
  if(o.estado==='Autorizada'&&ES_AUTORIZA) btns+='<button class="btn bg bs" data-act="pago" data-oc="'+esc(o.numero_oc)+'" data-val="'+parseFloat(o.valor_total||0)+'" data-prov="'+esc(o.proveedor||'')+'">Registrar Pago</button>';
  var _effGrp=grp==='ocs'?(Object.keys(CMAP).find(function(k){return inGroup(o.categoria,k);})||'svc'):grp;
  if(o.estado==='Pagada'&&!ES_C&&(_effGrp==='mp'||_effGrp==='mee')) btns+='<button class="btn bo bs" data-act="rec" data-oc="'+esc(o.numero_oc)+'">Marcar Recibida</button>';
  // Botón Editar disponible en TODOS los estados editables (decision Catalina 2026-04-28).
  // Borrador/Pendiente/Revisada/Aprobada/Autorizada → edicion completa.
  // Recibida/Parcial → edicion limitada (observaciones, fecha entrega).
  // Pagada → solo agregar nota al historial. Cancelada/Rechazada → bloqueado.
  var EDITABLES = ['Borrador','Pendiente','Revisada','Aprobada','Autorizada','Recibida','Parcial','Pagada'];
  if(EDITABLES.indexOf(o.estado) >= 0) btns+='<button class="btn bi bs" data-act="edit" data-oc="'+esc(o.numero_oc)+'">&#9998; Editar</button>';
  if(o.estado==='Borrador'||o.estado==='Rechazada') btns+='<button class="btn br bs" data-act="del" data-oc="'+esc(o.numero_oc)+'">&#128465; Eliminar</button>';
  // Para OCs Autorizadas, hacer EXTRA prominente quien recibe el pago.
  // Catalina pidio ver al beneficiario sin entrar a detalle.
  var provLabel = (o.estado==='Autorizada' || o.estado==='Aprobada')
    ? '<span class="cprov-label">Pagar a:</span>'
    : '';
  return '<div class="card">'+
    '<div class="ch"><div><div class="cnum">'+esc(o.numero_oc)+'</div>'+provLabel+'<div class="cprov">'+esc(o.proveedor||'-')+'</div></div>'+badge(o.estado)+'</div>'+
    '<div class="cmeta"><span>&#x1F4C5; '+fdate(o.fecha)+'</span>'+(o.fecha_entrega_est?'<span>&#x23F0; '+fdate(o.fecha_entrega_est)+'</span>':'')+'<span>'+o.num_items+' item(s)</span></div>'+
    (o.observaciones?'<div class="cobs" title="'+esc(o.observaciones||'')+'">&#128172; '+esc((o.observaciones||'').substring(0,120))+(o.observaciones.length>120?'...':'')+'</div>':'')+
    '<div class="cval">'+fmt(o.valor_total)+(o.con_iva?'<span style="font-size:10px;background:#fde047;color:#92400e;border-radius:3px;padding:1px 5px;margin-left:5px;">+IVA</span>':'')+'</div>'+
    (btns?'<div class="acts">'+btns+'</div>':'')+'</div>';
}

// ─── OCS unified tab ─────────────────────────────────────────────────────────
function renderOCS(){
  // Wire up category filter pill clicks (idempotent)
  document.querySelectorAll('.ocs-cpill').forEach(function(btn){
    btn.onclick=function(){
      document.querySelectorAll('.ocs-cpill').forEach(function(b){ b.classList.remove('on'); });
      this.classList.add('on');
      _ocsCatFilter=this.getAttribute('data-cat');
      renderOCS();
    };
  });
  var q=(document.getElementById('q-ocs')||{value:''}).value.toLowerCase();
  var st=(document.getElementById('s-ocs')||{value:''}).value;
  // Show/hide context sections
  var mpBanner=document.getElementById('mp-alert-banner');
  var ccSolic=document.getElementById('cc-solic-wrap');
  if(mpBanner) mpBanner.style.display=(_ocsCatFilter==='ALL'||_ocsCatFilter==='mp')?'':'none';
  if(ccSolic){
    if(_ocsCatFilter==='ALL'||_ocsCatFilter==='cc'){
      ccSolic.style.display='';
      loadCCSolicitudes();
    } else {
      ccSolic.style.display='none';
    }
  }
  if(_ocsCatFilter==='mp'||_ocsCatFilter==='ALL') renderMPAlerts();
  var list;
  if(_ocsCatFilter==='ALL'){
    list=OCS.filter(function(o){ return (o.categoria||'').indexOf('Influencer')<0; });
  } else {
    list=OCS.filter(function(o){ return inGroup(o.categoria,_ocsCatFilter); });
  }
  if(q) list=list.filter(function(o){ return (o.numero_oc||'').toLowerCase().indexOf(q)>=0||(o.proveedor||'').toLowerCase().indexOf(q)>=0||(o.observaciones||'').toLowerCase().indexOf(q)<0?false:true; });
  if(q) list=OCS.filter(function(o){
    if(_ocsCatFilter!=='ALL'&&!inGroup(o.categoria,_ocsCatFilter)) return false;
    if((o.categoria||'').indexOf('Influencer')>=0) return false;
    var sq=(o.numero_oc||'').toLowerCase().indexOf(q)>=0||(o.proveedor||'').toLowerCase().indexOf(q)>=0||(o.observaciones||'').toLowerCase().indexOf(q)>=0;
    return sq;
  });
  if(st) list=list.filter(function(o){ return o.estado===st; });
  var counts={};
  ['Borrador','Revisada','Autorizada','Pagada','Recibida'].forEach(function(e){ counts[e]=(list.filter(function(o){ return o.estado===e; })).length; });
  var vTotal=list.reduce(function(s,o){ return s+parseFloat(o.valor_total||0); },0);
  var pills='<span class="pill">'+list.length+' OCs</span>';
  if(counts.Borrador) pills+='<span class="pill">Borrador: '+counts.Borrador+'</span>';
  if(counts.Revisada) pills+='<span class="pill y">Revisada: '+counts.Revisada+'</span>';
  if(counts.Autorizada) pills+='<span class="pill b">Autorizada: '+counts.Autorizada+'</span>';
  if(counts.Pagada) pills+='<span class="pill g">Pagada: '+counts.Pagada+'</span>';
  if(counts.Recibida) pills+='<span class="pill">Recibida: '+counts.Recibida+'</span>';
  pills+='<span class="pill" style="background:#e7e5e4;">'+fmt(vTotal)+'</span>';
  document.getElementById('pills-ocs').innerHTML=pills;
  if(!list.length){
    document.getElementById('grid-ocs').innerHTML='<div class="empty">No hay OCs'+(q?' para esa busqueda':_ocsCatFilter!=='ALL'?' en esta categor\u00EDa':'')+'</div>';
    return;
  }
  document.getElementById('grid-ocs').innerHTML=list.map(function(o){ return fullCard(o,'ocs'); }).join('');
}

// ─── Pagos tab ────────────────────────────────────────────────────────────────
async function loadPagos(){
  document.getElementById('pagos-wrap').innerHTML='<div class="empty">Cargando...</div>';
  try{
    var r=await fetch('/api/compras/pagos');
    if(!r.ok) throw new Error('Pagos '+r.status);
    var d=await r.json();
    PAGOS=d.pagos||[];
  }catch(e){ PAGOS=[]; console.error('loadPagos:',e); }
  // Sebastián 24-may-2026 · paralelo · KPIs mes/año/medio (no bloquea render)
  try{
    var rk=await fetch('/api/compras/pagos-kpis');
    if(rk.ok) window.PAGOS_KPIS=await rk.json();
  }catch(_){ window.PAGOS_KPIS={}; }
  renderPagos();
}
function renderPagos(){
  var q=(document.getElementById('q-pagos')||{value:''}).value.toLowerCase();
  var catF=(document.getElementById('s-pagos-cat')||{value:''}).value;
  var list=PAGOS.filter(function(p){
    if(catF&&!inGroup(p.categoria,catF)) return false;
    // Bug #9 fix · 21-may-2026 · buscar también por numero_factura_proveedor (3-way matching)
    if(q&&(p.numero_oc||'').toLowerCase().indexOf(q)<0&&(p.proveedor||'').toLowerCase().indexOf(q)<0&&(p.medio_pago||'').toLowerCase().indexOf(q)<0&&(p.numero_factura_proveedor||'').toLowerCase().indexOf(q)<0&&(p.referencia||'').toLowerCase().indexOf(q)<0) return false;
    return true;
  });
  // Bug #2 fix · 21-may-2026 · sin fallback a valor_total (race condition daba doble cuenta)
  var vTotal=list.reduce(function(s,p){ return s+parseFloat(p.monto||0); },0);
  // Sebastián 24-may-2026 · audit Pagos · KPIs ampliados (mes/año/medio)
  // + botón Excel.
  var K=window.PAGOS_KPIS||{};
  var kMes=K.mes_actual||{}, kAnio=K.anio_actual||{};
  var medios=K.breakdown_medios||[];
  var topMedio=medios.length?(medios[0].medio+' '+fmt(medios[0].total)):'-';
  var kpiHTML=''
    +'<div class="kpi" style="background:#0c4a6e;color:#fff"><div class="kpi-l" style="color:#7dd3fc">Pagos filtrados</div><div class="kpi-v">'+list.length+'</div><div style="font-size:11px;color:#bae6fd">'+fmt(vTotal)+'</div></div>'
    +'<div class="kpi" style="background:#14532d;color:#fff"><div class="kpi-l" style="color:#86efac">Mes actual ('+(kMes.mes||'')+')</div><div class="kpi-v">'+fmt(kMes.total||0)+'</div><div style="font-size:11px;color:#bbf7d0">'+(kMes.n_ocs||0)+' OCs</div></div>'
    +'<div class="kpi" style="background:#1e1b4b;color:#fff"><div class="kpi-l" style="color:#a78bfa">Año actual ('+(kAnio.anio||'')+')</div><div class="kpi-v">'+fmt(kAnio.total||0)+'</div><div style="font-size:11px;color:#c4b5fd">'+(kAnio.n_ocs||0)+' OCs</div></div>'
    +'<div class="kpi" style="background:#7c2d12;color:#fff"><div class="kpi-l" style="color:#fdba74">Top medio (año)</div><div class="kpi-v" style="font-size:14px">'+esc(topMedio)+'</div><div style="font-size:11px;color:#fed7aa">'+medios.length+' medios</div></div>';
  document.getElementById('pagos-kpis').innerHTML=kpiHTML;
  // Botón Excel + breakdown medios (colapsable)
  var medBd=medios.map(function(m){
    return '<span style="background:#f1f5f9;padding:3px 8px;border-radius:6px;margin-right:4px;font-size:11px;color:#475569">'+esc(m.medio)+' · <b>'+m.n_pagos+'</b> · '+fmt(m.total)+'</span>';
  }).join('');
  var bar=document.getElementById('pagos-bar-extra');
  if(bar){
    bar.innerHTML='<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">'
      +'<div style="font-size:11px;color:#64748b">'+medBd+'</div>'
      +'<button onclick="descargarPagosExcel()" class="btn" style="background:#059669;color:#fff;font-size:12px;padding:6px 14px;border:0;border-radius:5px;font-weight:700;cursor:pointer">📊 Descargar Excel</button>'
      +'</div>';
  }
  if(!list.length){
    document.getElementById('pagos-wrap').innerHTML='<div class="empty">No hay pagos registrados</div>';
    return;
  }
  var rows=list.map(function(p){
    var tieneImg=p.tiene_comprobante;
    var imgBtn=tieneImg?'<button class="btn bo bs" data-oc="'+esc(p.numero_oc)+'" onclick="verComprobante(this.dataset.oc)">&#x1F4F8; Ver</button>':'<span style="color:#a8a29e;font-size:11px;">Sin imagen</span>';
    // Sebastián 24-may-2026 · botón Regenerar CE inline · invoca endpoint
    // existente /api/comprobantes-pago/<id>/regenerar (datos bancarios
    // refrescados desde maestro). Solo si hay comprobante_id.
    var regenBtn=p.comprobante_id?'<button class="btn bs" style="background:#7c3aed;color:#fff;font-size:10px;padding:3px 8px;margin-left:3px" data-cid="'+p.comprobante_id+'" data-oc="'+esc(p.numero_oc)+'" onclick="regenerarCEInline(this.dataset.cid, this.dataset.oc)" title="Regenerar PDF con datos bancarios actuales">🔄</button>':'';
    // Botón revertir pago · solo si ES_ADMIN (cargado en boot template)
    var revBtn=(typeof ES_ADMIN!=='undefined' && ES_ADMIN)?'<button class="btn bs" style="background:#dc2626;color:#fff;font-size:10px;padding:3px 8px;margin-left:3px" data-oc="'+esc(p.numero_oc)+'" onclick="revertirPagoOC(this.dataset.oc)" title="Revertir pago (admin · ventana 24h)">↩️</button>':'';
    return '<tr>'
      +'<td><strong>'+esc(p.numero_oc)+'</strong></td>'
      +'<td>'+esc(p.proveedor||'-')+'</td>'
      +'<td class="mob-hide"><span style="font-size:10px;background:#e7e5e4;border-radius:3px;padding:2px 6px;">'+esc(p.categoria||'-')+'</span></td>'
      +'<td style="font-weight:600;color:#16a34a;">'+fmt(p.monto||p.valor_total)+'</td>'
      +'<td class="mob-hide">'+esc(p.medio_pago||'-')+'</td>'
      +'<td>'+fdate(p.fecha_pago)+'</td>'
      +'<td class="mob-hide">'+esc(p.pagado_por||'-')+'</td>'
      +'<td>'+imgBtn+regenBtn+revBtn+'</td>'
      +'</tr>';
  }).join('');
  document.getElementById('pagos-wrap').innerHTML='<div style="overflow-x:auto;"><table class="ptbl"><thead><tr><th>OC</th><th>Proveedor</th><th class="mob-hide">Categoría</th><th>Monto</th><th class="mob-hide">Medio</th><th>Fecha</th><th class="mob-hide">Por</th><th>Acciones</th></tr></thead><tbody>'+rows+'</tbody></table></div>';
}

// Sebastián 24-may-2026 · descarga Excel hist. pagos · soporta ?mes=YYYY-MM
function descargarPagosExcel(){
  var mes=prompt('Mes a exportar (YYYY-MM) · vacío = todo:','');
  var url='/api/compras/pagos-excel';
  if(mes && /^\\d{4}-\\d{2}$/.test(mes.trim())) url+='?mes='+encodeURIComponent(mes.trim());
  window.location.href=url;
}

// Regenerar CE PDF inline · usa endpoint existente
async function regenerarCEInline(comprobante_id, numero_oc){
  if(!confirm('¿Regenerar PDF del CE de '+numero_oc+'? Esto refresca datos bancarios + empresa pagadora desde el maestro.')) return;
  try{
    var r=await fetch('/api/comprobantes-pago/'+comprobante_id+'/regenerar',
      _fetchOpts('POST', {}));
    var d=await r.json();
    if(r.ok && d.ok){
      alert('✅ CE '+d.numero_ce+' regenerado · '+d.pdf_size_kb+' KB');
    } else {
      alert('Error: '+(d.error||'desconocido'));
    }
  }catch(e){ alert('Error red: '+e.message); }
}

// Revertir pago de OC · admin only · backend valida ventana
async function revertirPagoOC(numero_oc){
  var motivo=prompt('REVERTIR pago de '+numero_oc+'\\n\\nMotivo (≥15 chars · queda en audit):','');
  if(!motivo) return;
  motivo=motivo.trim();
  if(motivo.length<15){ alert('Motivo debe tener ≥15 chars'); return; }
  if(!confirm('⚠️ REVERTIR pago de '+numero_oc+'\\n\\nEsto deshace:\\n• pagos_oc (último pago)\\n• comprobantes_pago (CE)\\n• flujo_egresos\\n• Estado OC volverá a Recibida/Parcial\\n\\n¿Confirmar?')) return;
  try{
    var r=await fetch('/api/ordenes-compra/'+encodeURIComponent(numero_oc)+'/revertir-pago',
      _fetchOpts('POST', {motivo: motivo}));
    var d=await r.json();
    if(r.ok && d.ok){
      alert('✅ Pago revertido · OC '+numero_oc+' → estado '+d.nuevo_estado+'\\n'+d.detalle);
      loadPagos();
      loadData();
    } else {
      alert('Error: '+(d.error||'desconocido'));
    }
  }catch(e){ alert('Error red: '+e.message); }
}
async function verComprobante(num){
  try{
    var r=await fetch('/api/ordenes-compra/'+encodeURIComponent(num)+'/comprobante');
    if(!r.ok){ alert('Sin comprobante guardado'); return; }
    var d=await r.json();
    if(!d.imagen){ alert('Sin comprobante guardado'); return; }
    var w=window.open('','_blank','width=700,height=600');
    w.document.write('<html><body style="margin:0;background:#111;display:flex;align-items:center;justify-content:center;min-height:100vh;"><img src="'+d.imagen+'" style="max-width:100%;max-height:100vh;"></body></html>');
    w.document.close();
  }catch(e){ alert('Error: '+e); }
}

function renderProv(){
  var q=(document.getElementById('q-prov')||{value:''}).value.toLowerCase();
  var list=PROVS.filter(function(p){ return !q||(p.nombre||'').toLowerCase().indexOf(q)>=0||(p.nit||'').toLowerCase().indexOf(q)>=0; });
  if(!list.length){ document.getElementById('prov-grid').innerHTML='<div class="empty">No hay proveedores</div>'; return; }
  document.getElementById('prov-grid').innerHTML=list.map(function(p){
    return '<div class="pc"><div style="display:flex;justify-content:space-between;align-items:flex-start;">'
      +'<div><div class="pn">'+esc(p.nombre)+'</div><div class="pnit">NIT: '+esc(p.nit||'-')+'</div></div>'
      // Fase 3 · 21-may-2026 · botón scorecard inline (5 métricas live)
      +'<div style="display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end">'
      +'<button class="btn" style="font-size:11px;padding:4px 10px;white-space:nowrap;background:#7c3aed;color:#fff" data-scorecard="'+esc(p.nombre)+'" title="Score · cumplimiento · on-time · rechazo QC · variación precio">🎯 Score</button>'
      +'<button class="btn" style="font-size:11px;padding:4px 10px;white-space:nowrap;" data-ficha360="'+esc(p.nombre)+'">&#x1F4CA; Ver 360</button>'
      +'</div>'
      +'</div><div class="pd">'+
      (p.contacto?'<span>&#x1F464; '+esc(p.contacto)+'</span>':'')+
      (p.telefono?'<span>&#x1F4F1; '+esc(p.telefono)+'</span>':'')+
      (p.email?'<span>&#x1F4E7; '+esc(p.email)+'</span>':'')+
      (p.banco?'<span>&#x1F3E6; '+esc(p.banco)+' '+esc(p.tipo_cuenta||'')+'</span>':'')+
      (p.num_cuenta?'<span>&#x1F4B3; '+esc(p.num_cuenta)+'</span>':'')+
    '</div></div>';
  }).join('');
}

// ─── Proveedor 360 ────────────────────────────────────────────────
document.addEventListener('click', function(e){
  var btn = e.target.closest('[data-ficha360]');
  if (!btn) return;
  abrirFicha360(btn.getAttribute('data-ficha360'));
});

async function abrirFicha360(nombre) {
  openModal('m-ficha360');
  var el = document.getElementById('ficha360-content');
  el.innerHTML = '<div style="text-align:center;color:#a8a29e;padding:40px;">Cargando ficha 360...</div>';
  try {
    var r = await fetch('/api/proveedores-compras/' + encodeURIComponent(nombre) + '/ficha');
    var d = await r.json();
    if (d.error) { el.innerHTML = '<p style="color:#dc2626;">'+esc(d.error)+'</p>'; return; }
    var p = d.proveedor, s = d.stats;
    var scoreColor = s.score >= 80 ? '#16a34a' : s.score >= 50 ? '#d97706' : '#dc2626';
    var scoreLbl = s.score >= 80 ? 'Excelente' : s.score >= 50 ? 'Aceptable' : 'Critico';
    var catColor = (p.categoria||'').indexOf('Critico') >= 0 ? '#dc2626' : (p.categoria||'').indexOf('Mayor') >= 0 ? '#d97706' : '#16a34a';
    var h = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">'
      // Card: Info
      +'<div style="background:#fafaf9;border:1px solid #e7e5e4;border-radius:10px;padding:14px;">'
      +'<div style="font-weight:700;font-size:14px;margin-bottom:8px;">&#x1F3ED; Datos del Proveedor</div>'
      +'<div style="font-size:13px;line-height:1.9;">'
      +(p.nit?'<div><span style="color:#78716c;">NIT:</span> <strong>'+esc(p.nit)+'</strong></div>':'')+
      (p.contacto?'<div><span style="color:#78716c;">Contacto:</span> '+esc(p.contacto)+'</div>':'')+
      (p.email?'<div><span style="color:#78716c;">Email:</span> '+esc(p.email)+'</div>':'')+
      (p.telefono?'<div><span style="color:#78716c;">Tel:</span> '+esc(p.telefono)+'</div>':'')+
      (p.concepto_compra?'<div><span style="color:#78716c;">Concepto:</span> '+esc(p.concepto_compra)+'</div>':'')+
      (p.condiciones_pago?'<div><span style="color:#78716c;">Pago:</span> '+esc(p.condiciones_pago)+'</div>':'')+
      (p.banco?'<div><span style="color:#78716c;">Banco:</span> '+esc(p.banco)+'</div>':'')+
      (p.num_cuenta?'<div><span style="color:#78716c;">Cuenta:</span> '+esc((p.tipo_cuenta||'')+' '+p.num_cuenta)+'</div>':'')+
      (p.acuerdo_calidad?'<div><span style="color:#78716c;">Acuerdo calidad:</span> '+esc(p.acuerdo_calidad)+'</div>':'')+
      '<div><span style="color:#78716c;">Categoria:</span> <span style="color:'+catColor+';font-weight:600;">'+esc(p.categoria||'N/A')+'</span></div>'
      +'</div></div>'
      // Card: Score
      +'<div style="background:#fafaf9;border:1px solid #e7e5e4;border-radius:10px;padding:14px;">'
      +'<div style="font-weight:700;font-size:14px;margin-bottom:12px;">&#x2B50; Score Proveedor</div>'
      +'<div style="text-align:center;margin-bottom:12px;">'
      +'<div style="font-size:42px;font-weight:800;color:'+scoreColor+';">'+s.score+'</div>'
      +'<div style="font-size:12px;color:'+scoreColor+';font-weight:600;">'+scoreLbl+'</div>'
      +'</div>'
      +'<div style="font-size:12px;line-height:2;">'
      +'<div style="display:flex;justify-content:space-between;"><span>OCs totales</span><strong>'+s.oc_total+'</strong></div>'
      +'<div style="display:flex;justify-content:space-between;"><span>Recibidas/Pagadas</span><strong>'+s.oc_recibidas+'</strong></div>'
      +'<div style="display:flex;justify-content:space-between;"><span>Cumplimiento</span><strong style="color:'+scoreColor+';">'+s.cumplimiento+'%</strong></div>'
      +'<div style="display:flex;justify-content:space-between;"><span>Discrepancias</span><strong style="color:'+(s.tasa_discrepancias>0?'#dc2626':'#16a34a')+';">'+s.tasa_discrepancias+'%</strong></div>'
      +'<div style="display:flex;justify-content:space-between;"><span>Valor total comprado</span><strong>$'+Number(s.valor_total).toLocaleString('es-CO',{maximumFractionDigits:0})+'</strong></div>'
      +(s.ultima_oc?'<div style="display:flex;justify-content:space-between;"><span>Ultima OC</span><strong>'+(s.ultima_oc||'').slice(0,10)+'</strong></div>':'')+
      '</div></div>'
      +'</div>';
    // OCs recientes
    if (d.ocs_recientes && d.ocs_recientes.length) {
      h += '<div style="margin-bottom:16px;"><div style="font-weight:700;font-size:13px;margin-bottom:8px;">&#x1F4CB; Ultimas Ordenes de Compra</div>'
        +'<div style="overflow-x:auto;"><table><thead><tr><th>OC</th><th>Fecha</th><th>Estado</th><th>Categoria</th><th style="text-align:right;">Valor</th><th>Discrepancia</th></tr></thead><tbody>';
      d.ocs_recientes.forEach(function(o){
        var estColor = o.estado==='Recibida'||o.estado==='Pagada' ? '#16a34a' : o.estado==='Autorizada' ? '#2563eb' : o.estado==='Parcial' ? '#d97706' : '#78716c';
        h += '<tr><td style="font-family:monospace;font-size:12px;">'+esc(o.numero_oc)+'</td>'
          +'<td>'+(o.fecha||'').slice(0,10)+'</td>'
          +'<td style="color:'+estColor+';font-weight:600;">'+esc(o.estado)+'</td>'
          +'<td>'+esc(o.categoria||'')+'</td>'
          +'<td style="text-align:right;">$'+Number(o.valor_total||0).toLocaleString('es-CO',{maximumFractionDigits:0})+'</td>'
          +'<td style="text-align:center;">'+(o.tiene_discrepancias?'<span style="color:#dc2626;">&#x26A0; Si</span>':'<span style="color:#16a34a;">&#x2713;</span>')+'</td>'
          +'</tr>';
      });
      h += '</tbody></table></div></div>';
    }
    // Materiales comprados
    if (d.materiales && d.materiales.length) {
      h += '<div><div style="font-weight:700;font-size:13px;margin-bottom:8px;">&#x1F9EA; Materiales / Items Comprados</div>'
        +'<div style="overflow-x:auto;"><table><thead><tr><th>Codigo</th><th>Material</th><th style="text-align:center;">Veces</th><th style="text-align:right;">Total (g)</th></tr></thead><tbody>';
      d.materiales.forEach(function(m){
        h += '<tr><td style="font-family:monospace;font-size:12px;">'+esc(m.codigo||'')+'</td>'
          +'<td>'+esc(m.nombre||'')+'</td>'
          +'<td style="text-align:center;">'+m.veces+'</td>'
          +'<td style="text-align:right;">'+Number(m.total_g).toLocaleString('es-CO',{maximumFractionDigits:0})+'</td>'
          +'</tr>';
      });
      h += '</tbody></table></div></div>';
    }
    el.innerHTML = h;
    // Footer buttons
    var ft=document.getElementById('ficha360-footer');
    if(ft){
      ft.innerHTML=
        '<button class="btn bo" onclick="closeModal(\\'m-ficha360\\')">Cerrar</button>'
        +'<button class="btn bw" style="background:#2563eb;" onclick="editarProv360(\\''+ nombre.replace(/'/g,\"&#39;\")+'\\')">'
        +'&#x270F; Editar</button>'
        +'<button class="btn" style="background:#dc2626;color:#fff;font-weight:700;" '
        +'onclick="bajaProv360(\\''+ nombre.replace(/'/g,\"&#39;\")+'\\')">'
        +'&#x1F6AB; Dar de baja</button>';
    }
  } catch(e) { el.innerHTML = '<p style="color:#dc2626;">Error: '+e.message+'</p>'; }
}

// ─── Editar proveedor 360 ──────────────────────────────────────────
function editarProv360(nombre){
  var el=document.getElementById('ficha360-content');
  var ft=document.getElementById('ficha360-footer');
  // Pre-fill from PROVS cache
  var p=PROVS.find(function(x){ return x.nombre===nombre; })||{};
  function fld(id,lbl,val,ph){
    return '<div class="fg" style="margin-bottom:8px;">'
      +'<label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:3px;">'+lbl+'</label>'
      +'<input id="ep-'+id+'" value="'+esc(val||'')+'" placeholder="'+ph+'" '
      +'style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;"></div>';
  }
  var h='<div style="padding:16px 20px;">';
  h+='<div style="font-weight:800;font-size:14px;margin-bottom:14px;">&#x270F; Editar: '+esc(nombre)+'</div>';
  h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:0 14px;">';
  h+=fld('contacto','Contacto',p.contacto,'Nombre contacto');
  h+=fld('email','Email',p.email,'correo@ejemplo.com');
  h+=fld('telefono','Teléfono',p.telefono,'300 000 0000');
  h+=fld('nit','NIT / CC',p.nit,'NIT o cédula');
  h+='<div style="grid-column:span 2;">'+fld('direccion','Dirección',p.direccion,'Dirección completa')+'</div>';
  h+=fld('banco','Banco',p.banco,'Bancolombia, Davivienda...');
  h+='<div class="fg" style="margin-bottom:8px;"><label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:3px;">Tipo de cuenta</label>'
    +'<select id="ep-tipo_cuenta" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">'
    +'<option value="Ahorros"'+(p.tipo_cuenta==='Ahorros'?' selected':'')+ '>Ahorros</option>'
    +'<option value="Corriente"'+(p.tipo_cuenta==='Corriente'?' selected':'')+'>Corriente</option>'
    +'<option value="Ahorros Damas"'+(p.tipo_cuenta==='Ahorros Damas'?' selected':'')+'>Ahorros Damas</option>'
    +'<option value="Nequi / Daviplata"'+(p.tipo_cuenta==='Nequi / Daviplata'?' selected':'')+'>Nequi / Daviplata</option>'
    +'</select></div>';
  h+=fld('num_cuenta','N° de cuenta',p.num_cuenta,'Número de cuenta');
  h+=fld('concepto_compra','Concepto de compra',p.concepto_compra,'Ej: Materias primas');
  h+='<div class="fg" style="margin-bottom:8px;"><label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:3px;">Categoría LPA</label>'
    +'<select id="ep-categoria" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;">'
    +'<option value="">-- Sin categoría --</option>'
    +'<option value="\U0001F534 Crítico"'+(( p.categoria||'').indexOf('rico')>=0?' selected':'')+'>🔴 Crítico</option>'
    +'<option value="\U0001F7E0 Mayor"'+((p.categoria||'').indexOf('ayor')>=0?' selected':'')+'>🟠 Mayor</option>'
    +'<option value="\U0001F7E2 No crítico"'+((p.categoria||'').indexOf('No')>=0?' selected':'')+'>🟢 No crítico</option>'
    +'</select></div>';
  h+='</div></div>';
  el.innerHTML=h;
  if(ft) ft.innerHTML=
    '<button class="btn bo" onclick="abrirFicha360(\\''+ nombre.replace(/'/g,\"&#39;\")+'\\')">'
    +'&#x2190; Volver</button>'
    +'<button class="btn bg" onclick="guardarEditProv360(\\''+ nombre.replace(/'/g,\"&#39;\")+'\\')">'
    +'&#x1F4BE; Guardar cambios</button>';
}
async function guardarEditProv360(nombre){
  var body={};
  var ids=['contacto','email','telefono','nit','direccion','banco','tipo_cuenta','num_cuenta','concepto_compra','categoria'];
  ids.forEach(function(id){ var el=document.getElementById('ep-'+id); if(el) body[id]=el.value.trim(); });
  try{
    var r=await fetch('/api/proveedores-compras/'+encodeURIComponent(nombre),
      _fetchOpts('PATCH', body));
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    // Refresh PROVS and reload 360
    var rp=await fetch('/api/proveedores-compras'); var dp=await rp.json();
    PROVS=dp.proveedores||[];
    abrirFicha360(nombre);
  }catch(e){ alert('Error: '+e.message); }
}
function bajaProv360(nombre){
  var el=document.getElementById('ficha360-content');
  var ft=document.getElementById('ficha360-footer');
  var h='<div style="padding:24px 20px;">';
  h+='<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:10px;padding:20px;">';
  h+='<div style="font-size:28px;text-align:center;margin-bottom:8px;">&#x1F6AB;</div>';
  h+='<div style="font-weight:800;font-size:15px;color:#dc2626;text-align:center;margin-bottom:4px;">Dar de baja al proveedor</div>';
  h+='<div style="font-size:13px;color:#7f1d1d;text-align:center;margin-bottom:16px;">'
    +'<strong>'+esc(nombre)+'</strong> dejará de aparecer en nuevas OCs.'
    +'<br>El historial de compras se conserva intacto.</div>';
  h+='<div class="fg"><label style="font-size:12px;font-weight:700;color:#7f1d1d;display:block;margin-bottom:6px;">'
    +'Motivo de baja <span style="color:#dc2626;">*</span></label>';
  h+='<textarea id="baja-motivo" rows="3" placeholder="Ej: Incumplimiento reiterado de fechas, pérdida de confianza, mejor alternativa disponible..." '
    +'style="width:100%;padding:8px 10px;border:1px solid #fca5a5;border-radius:6px;font-size:13px;resize:vertical;"></textarea></div>';
  h+='</div></div>';
  el.innerHTML=h;
  if(ft) ft.innerHTML=
    '<button class="btn bo" onclick="abrirFicha360(\\''+ nombre.replace(/'/g,\"&#39;\")+'\\')">'
    +'&#x2190; Cancelar</button>'
    +'<button class="btn" style="background:#dc2626;color:#fff;font-weight:700;" '
    +'onclick="confirmarBajaProv360(\\''+ nombre.replace(/'/g,\"&#39;\")+'\\')">'
    +'&#x26A0; Confirmar baja definitiva</button>';
}
async function confirmarBajaProv360(nombre){
  var motivo=(document.getElementById('baja-motivo')||{value:''}).value.trim();
  if(!motivo){ alert('El motivo de baja es obligatorio'); return; }
  try{
    var r=await fetch('/api/proveedores-compras/'+encodeURIComponent(nombre),
      _fetchOpts('DELETE', {motivo:motivo}));
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    // Refresh PROVS and close modal
    var rp=await fetch('/api/proveedores-compras'); var dp=await rp.json();
    PROVS=dp.proveedores||[];
    fillProvSelect('noc-prov');
    closeModal('m-ficha360');
    renderProveedores();
    alert('Proveedor dado de baja. Historial conservado.');
  }catch(e){ alert('Error: '+e.message); }
}

// ─── Proveedor autofill ────────────────────────────────────────────
function fillProvSelect(selId){
  var sel=document.getElementById(selId); if(!sel) return;
  var cur=sel.value;
  sel.innerHTML='<option value="">-- Seleccionar proveedor --</option>';
  PROVS.forEach(function(p){ var o=document.createElement('option'); o.value=p.nombre; o.textContent=p.nombre; sel.appendChild(o); });
  // Append inline-create option (only for noc-prov)
  if(selId==='noc-prov'){
    var no=document.createElement('option');
    no.value='__NEW__'; no.textContent='+ Crear proveedor nuevo';
    no.style.fontWeight='700'; no.style.color='#16a34a';
    sel.appendChild(no);
  }
  if(cur&&cur!=='__NEW__') sel.value=cur;
}
function fillProv(selId, boxId){
  var nombre=document.getElementById(selId).value;
  var box=document.getElementById(boxId);
  // Intercept inline-create selection
  if(nombre==='__NEW__'){
    box.style.display='none';
    var frm=document.getElementById('noc-new-prov-form');
    if(frm){
      frm.style.display='block';
      // PROV-FIX#7 · 21-may-2026 · limpiar TODOS los 11 campos del form
      // antes solo limpiaba 5 · datos bancarios se filtraban entre proveedores.
      ['np-nombre','np-nit','np-tel','np-email','np-concepto',
       'np-contacto','np-direccion','np-banco','np-tipo-cuenta',
       'np-num-cuenta','np-cond-pago'].forEach(function(id){
        var el=document.getElementById(id); if(el) el.value='';
      });
    }
    return;
  }
  var p=PROVS.find(function(x){ return x.nombre===nombre; });
  if(!p||!nombre){ box.style.display='none'; return; }
  var rows=[['NIT',p.nit],['Tel',p.telefono],['Email',p.email],['Contacto',p.contacto],['Banco',p.banco],['Cuenta',(p.tipo_cuenta||'')+' '+(p.num_cuenta||'')],['Concepto',p.concepto_compra],['Direccion',p.direccion]];
  box.innerHTML=rows.filter(function(r){ return r[1]; }).map(function(r){ return '<span class="lbl">'+r[0]+'</span><span>'+esc(r[1])+'</span>'; }).join('');
  box.style.display='grid';
}

// ─── Modal helpers ─────────────────────────────────────────────────
function openModal(id){ document.getElementById(id).classList.add('on'); }
function closeModal(id){ document.getElementById(id).classList.remove('on'); }
document.querySelectorAll('.ov').forEach(function(ov){ ov.addEventListener('click',function(e){ if(e.target===ov) ov.classList.remove('on'); }); });

// ─── Nueva OC (enterprise) ───────────────────────────────────────────
var _catMap={'mp':'MP','mee':'MEE','svc':'SVC','adm':'ADM','inf':'INF','cc':'CC'};
var _ocMode='create';
var _ocEditNum='';
var _ocCatCode='MP';
var _MP_LIST=[];
var _OC_CATS=[
  {k:'MP',ico:'🧪',l:'Mat. Primas'},
  {k:'MEE',ico:'📦',l:'Empaque'},
  {k:'SVC',ico:'🔧',l:'Servicios'},
  {k:'ADM',ico:'📋',l:'Administrativo'},
  {k:'INF',ico:'🏗️',l:'Infraestructura'},
  {k:'CC',ico:'💳',l:'Cta. Cobro'},
];
function initCatPills(activeCat){
  var html='';
  _OC_CATS.forEach(function(c){
    var on=c.k===activeCat?' pill-on':'';
    html+='<button class="pill'+on+'" data-cat="'+c.k+'">'+c.ico+' '+c.l+'</button>';
  });
  document.getElementById('noc-cat-pills').innerHTML=html;
  document.getElementById('noc-cat-pills').querySelectorAll('.pill').forEach(function(p){
    p.addEventListener('click',function(){ setCat(this.getAttribute('data-cat')); });
  });
}
function setCat(k){
  _ocCatCode=k;
  document.getElementById('noc-cat').value=k;
  var pills=document.getElementById('noc-cat-pills').querySelectorAll('.pill');
  pills.forEach(function(p){
    p.classList.toggle('pill-on',p.getAttribute('data-cat')===k);
  });
  if(k==='MP') loadMPLookup();
  // ── Column header ──
  var colH={'MP':'Codigo MP','MEE':'Ref. MEE','SVC':'Servicio',
    'ADM':'Concepto','INF':'Ref.','CC':'Concepto'};
  var th=document.querySelector('#m-noc .itbl thead tr th');
  if(th) th.textContent=colH[k]||'Codigo';
  // ── Provider field: select for MP/MEE, free-text for the rest ──
  var isCatalog=(k==='MP'||k==='MEE');
  var sel=document.getElementById('noc-prov');
  var txt=document.getElementById('noc-prov-txt');
  var lbl=document.getElementById('noc-prov-lbl');
  var ibox=document.getElementById('noc-ibox');
  if(sel) sel.style.display=isCatalog?'':'none';
  if(txt) txt.style.display=isCatalog?'none':'';
  if(ibox) ibox.style.display='none';
  if(lbl) lbl.textContent=isCatalog?'Proveedor':(k==='CC'?'Beneficiario / Proveedor':'Proveedor / Beneficiario');
  var ccPago=document.getElementById('noc-cc-pago');
  if(ccPago) ccPago.style.display=(k==='CC'?'block':'none');
  var addProvLink=document.getElementById('noc-add-prov-link');
  if(addProvLink) addProvLink.style.display=isCatalog?'none':'block';
  if(!isCatalog&&txt){
    var dl=document.getElementById('prov-dl');
    if(dl&&typeof PROVS!=='undefined'){
      dl.innerHTML=PROVS.map(function(p){
        return '<option value="'+esc(p.nombre)+'">';
      }).join('');
    }
  }
  // ── Rebuild item rows ──
  document.getElementById('noc-tbody').innerHTML='';
  ITMS=0;
  addRow(); addRow();
}
function openNuevaOC(catCode){
  _ocMode='create'; _ocEditNum='';
  var key=(catCode||'').toLowerCase();
  _ocCatCode=_catMap[key]||catCode||'MP';
  document.getElementById('noc-cat').value=_ocCatCode;
  document.getElementById('noc-title').textContent='📝 Nueva Orden de Compra';
  document.getElementById('noc-submit-btn').textContent='Crear OC';
  document.getElementById('noc-fent').value='';
  document.getElementById('noc-obs').value='';
  var ic=document.getElementById('noc-iva-chk');
  if(ic) ic.checked=false;
  var ir=document.getElementById('noc-iva-row');
  if(ir) ir.style.display='none';
  document.getElementById('noc-tot').textContent='$0';
  document.getElementById('noc-tbody').innerHTML='';
  ITMS=0;
  fillProvSelect('noc-prov');
  document.getElementById('noc-prov').value='';
  initCatPills(_ocCatCode);
  setCat(_ocCatCode);
  openModal('m-noc');
}
function addRow(){
  ITMS++;
  var n=ITMS;
  var isMP=(document.getElementById('noc-cat').value==='MP');
  // Gastos generales (papelería/EPP/servicios/aseo…) usan el catálogo de consumibles · NO MP/MEE/INF/CC.
  var isGasto=(['MP','MEE','INF','CC'].indexOf(document.getElementById('noc-cat').value)<0);
  var _ph={'MP':'Buscar MP...','MEE':'Ref. MEE','SVC':'Servicio','ADM':'Concepto','INF':'Ref.','CC':'Concepto'};
  var _ph_val=_ph[document.getElementById('noc-cat').value]||'COD';
  var _w=isMP?'width:115px':'width:80px';
  var codCell=isMP
    ?'<td><input id="ic'+n+'" list="mp-dl" placeholder="Buscar MP..." style="'+_w+'" oninput="autoFillMP('+n+')" autocomplete="off"></td>'
    :'<td><input id="ic'+n+'" placeholder="'+_ph_val+'" style="'+_w+'"></td>';
  var tr=document.createElement('tr');
  tr.id='ir'+n;
  tr.innerHTML=codCell+
    (isGasto
      ? '<td><input id="in'+n+'" list="consum-dl" placeholder="Buscar en catálogo o escribir…" oninput="autoFillConsumible('+n+')" autocomplete="off" style="width:150px"></td>'
      : '<td><input id="in'+n+'" placeholder="Descripcion" style="width:150px"></td>')+
    '<td><input id="iq'+n+'" type="number" value="1" min="0" oninput="calcTot()" style="width:55px"></td>'+
    '<td><input id="ip'+n+'" type="number" value="0" min="0" step="0.01" oninput="calcTot()" style="width:75px"></td>'+
    '<td id="is'+n+'" style="white-space:nowrap">$0</td>'+
    '<td><button class="btn bo" style="padding:2px 7px;font-size:11px;" onclick="rmRow('+n+')">x</button></td>';
  document.getElementById('noc-tbody').appendChild(tr);
}
function rmRow(n){var e=document.getElementById('ir'+n);if(e)e.remove();calcTot();}
function calcTot(){
  var tot=0;
  for(var i=1;i<=ITMS;i++){
    var q=document.getElementById('iq'+i),p=document.getElementById('ip'+i);
    if(!q||!p) continue;
    var s=parseFloat(q.value||0)*parseFloat(p.value||0);
    var el=document.getElementById('is'+i); if(el) el.textContent=fmt(s);
    tot+=s;
  }
  var ivaChk=document.getElementById('noc-iva-chk');
  var ivaRow=document.getElementById('noc-iva-row');
  if(ivaChk&&ivaChk.checked){
    var iva=tot*0.19;
    var total=tot+iva;
    if(ivaRow) ivaRow.style.display='block';
    var es=document.getElementById('noc-sub'); if(es) es.textContent=fmt(tot);
    var em=document.getElementById('noc-iva-monto'); if(em) em.textContent=fmt(iva);
    var et=document.getElementById('noc-iva-total'); if(et) et.textContent=fmt(total);
    document.getElementById('noc-tot').textContent=fmt(total);
  } else {
    if(ivaRow) ivaRow.style.display='none';
    document.getElementById('noc-tot').textContent=fmt(tot);
  }
}
async function submitOC(){
  var cat=document.getElementById('noc-cat').value;
  var _isCat=(cat==='MP'||cat==='MEE');
  var prov=_isCat
    ?document.getElementById('noc-prov').value
    :((document.getElementById('noc-prov-txt')||{value:''}).value||'').trim();
  var obs=document.getElementById('noc-obs').value;
  var fent=document.getElementById('noc-fent').value;
  if(!prov){ alert('Selecciona un proveedor o beneficiario'); return; }
  // For CC: encode banking data into observaciones
  if(cat==='CC'){
    var _banco=(document.getElementById('noc-cc-banco')||{value:''}).value.trim();
    var _tipo=(document.getElementById('noc-cc-tipo')||{value:''}).value.trim();
    var _cuenta=(document.getElementById('noc-cc-cuenta')||{value:''}).value.trim();
    var _nit=(document.getElementById('noc-cc-nit')||{value:''}).value.trim();
    var _pagoStr='';
    if(_banco) _pagoStr+='BANCO: '+_banco+' '+_tipo;
    if(_cuenta) _pagoStr+=(_pagoStr?' | ':'')+'CUENTA/CEL: '+_cuenta;
    if(_nit) _pagoStr+=(_pagoStr?' | ':'')+'CED/NIT: '+_nit;
    if(_pagoStr) obs=(_pagoStr+(obs?' | '+obs:'')).trim();
  }
  var items=[];
  for(var i=1;i<=ITMS;i++){
    var n=document.getElementById('in'+i);
    if(!n||(n.value||'').trim()==='') continue;
    items.push({codigo_mp:(document.getElementById('ic'+i)||{value:''}).value,
      nombre_mp:n.value.trim(),
      cantidad_g:parseFloat((document.getElementById('iq'+i)||{value:1}).value||1),
      precio_unitario:parseFloat((document.getElementById('ip'+i)||{value:0}).value||0)});
  }
  if(!items.length){ alert('Agrega al menos un item con descripcion'); return; }
  var ivaChk=document.getElementById('noc-iva-chk');
  var conIva=ivaChk&&ivaChk.checked?1:0;
  var sub=items.reduce(function(a,it){return a+(it.cantidad_g||0)*(it.precio_unitario||0);},0);
  try{
    var url,method;
    if(_ocMode==='edit'){
      url='/api/ordenes-compra/'+encodeURIComponent(_ocEditNum)+'/editar';
      method='PATCH';
    } else {
      url='/api/ordenes-compra';
      method='POST';
    }
    var r=await fetch(url,{method:method,headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proveedor:prov,categoria:cat,observaciones:obs,
        fecha_entrega_est:fent,items:items,creado_por:'{usuario}',
        con_iva:conIva,valor_sin_iva:sub})});
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    // Save-back al catálogo (Sebastián 1-jul): los ítems de GASTO GENERAL (no MP/MEE/INF/CC) que
    // no estén ya en el catálogo se guardan en maestro_consumibles → reutilizables + su precio la
    // próxima vez. Así Catalina nunca crea lo mismo desde cero.
    if(_ocMode!=='edit' && ['MP','MEE','INF','CC'].indexOf(cat)<0){
      for(var _si=0; _si<items.length; _si++){
        var _nm=((items[_si].nombre_mp)||'').trim();
        if(!_nm) continue;
        if((_CONSUM||[]).some(function(x){ return (x.nombre||'').trim().toLowerCase()===_nm.toLowerCase(); })) continue;
        try{
          await fetch('/api/compras/consumibles', _fetchOpts('POST', {nombre:_nm, categoria:cat, proveedor:prov, precio_referencia:items[_si].precio_unitario||0}));
          _CONSUM.push({nombre:_nm, categoria:cat, proveedor:prov, precio_referencia:items[_si].precio_unitario||0});
        }catch(e){}
      }
      if(typeof buildConsumDL==='function') buildConsumDL();
    }
    var _msg=(_ocMode==='edit'?'OC actualizada: '+_ocEditNum:'Creada: '+d.numero_oc);
    // 1-clic Catalina: autorizar al CREAR → va directo a Por Pagar (reusa el autorizar canónico).
    var _auto=document.getElementById('noc-autorizar');
    if(_ocMode!=='edit' && _auto && _auto.checked && d.numero_oc){
      try{
        var ra=await fetch('/api/ordenes-compra/'+encodeURIComponent(d.numero_oc)+'/autorizar',_fetchOpts('PATCH', {}));
        var da=await ra.json();
        if(ra.ok && !da.error){ _msg='✓ OC '+d.numero_oc+' creada y enviada a Por Pagar'; }
        else{ _msg='OC '+d.numero_oc+' creada · quedó en Borrador (no se autorizó: '+(da.error||'monto/permiso')+')'; }
      }catch(e){}
    }
    closeModal('m-noc');
    await loadData();
    renderDash();
    alert(_msg);
  }catch(e){ alert('Error de conexion: '+e); }
}
var crearOC=submitOC;
async function editarOC(oc){
  try{
    var r=await fetch('/api/ordenes-compra/'+encodeURIComponent(oc));
    var d=await r.json();
    if(d.error){ alert(d.error); return; }
    _ocMode='edit'; _ocEditNum=oc;
    _ocCatCode=d.categoria||'MP';
    document.getElementById('noc-cat').value=_ocCatCode;
    document.getElementById('noc-title').textContent='Editar OC '+oc;
    document.getElementById('noc-submit-btn').textContent='Guardar Cambios';
    document.getElementById('noc-fent').value=d.fecha_entrega_est||'';
    document.getElementById('noc-obs').value=d.observaciones||'';
    var ic=document.getElementById('noc-iva-chk');
    if(ic) ic.checked=!!d.con_iva;
    document.getElementById('noc-tbody').innerHTML='';
    ITMS=0;
    fillProvSelect('noc-prov');
    initCatPills(_ocCatCode);
    // Toggle provider field and set value
    var _isCat=(_ocCatCode==='MP'||_ocCatCode==='MEE');
    var _sel=document.getElementById('noc-prov');
    var _txt=document.getElementById('noc-prov-txt');
    var _lbl=document.getElementById('noc-prov-lbl');
    if(_sel) _sel.style.display=_isCat?'':'none';
    if(_txt) _txt.style.display=_isCat?'none':'';
    if(_lbl) _lbl.textContent=_isCat?'Proveedor':'Proveedor / Beneficiario';
    if(_isCat){
      setTimeout(function(){ document.getElementById('noc-prov').value=d.proveedor||''; },80);
    } else {
      if(_txt) _txt.value=d.proveedor||'';
    }
    if(_ocCatCode==='MP') loadMPLookup();
    (d.items||[]).forEach(function(it){
      addRow();
      var n=ITMS,el;
      el=document.getElementById('ic'+n); if(el) el.value=it.codigo_mp||'';
      el=document.getElementById('in'+n); if(el) el.value=it.nombre_mp||'';
      el=document.getElementById('iq'+n); if(el) el.value=it.cantidad_g||1;
      el=document.getElementById('ip'+n); if(el) el.value=it.precio_unitario||0;
    });
    if(!d.items||!d.items.length) addRow();
    calcTot();
    openModal('m-noc');
  }catch(e){ alert('Error cargando OC: '+e); }
}
async function eliminarOC(oc){
  if(!confirm('Eliminar OC '+oc+'? Esta accion no se puede deshacer.')) return;
  try{
    var r=await fetch('/api/ordenes-compra/'+encodeURIComponent(oc),_fetchOpts('DELETE'));
    var d=await r.json();
    if(d.error){ alert(d.error); return; }
    await loadData();
    var at=document.querySelector('.tn.on');
    if(at){
      var _tab=at.getAttribute('data-tab');
      if(_tab) try{renderCat(_tab);}catch(_){}
    }
    alert('OC '+oc+' eliminada');
  }catch(e){ alert('Error: '+e); }
}
async function loadMPLookup(){
  if(_MP_LIST.length) return;
  try{
    // /api/maestro-mps devuelve {mps:[{codigo_mp,nombre_comercial,...}]}.
    // Antes apuntaba a /api/materiales (404) con keys incorrectos
    // (codigo_interno/nombre_material) — el datalist quedaba vacío y
    // autoFillMP nunca acertaba ningún MP.
    var r=await fetch('/api/maestro-mps?tipo_material=MP');
    var d=await r.json();
    _MP_LIST=(d.mps||d.items||d||[]);
    var dl=document.getElementById('mp-dl');
    if(!dl){ dl=document.createElement('datalist'); dl.id='mp-dl'; document.body.appendChild(dl); }
    dl.innerHTML=_MP_LIST.map(function(m){
      var cod=m.codigo_mp||m.codigo_interno||'';
      var nom=m.nombre_inci||m.nombre_comercial||m.nombre_material||'';
      return '<option value="'+cod+'">'+nom+'</option>';
    }).join('');
  }catch(e){ console.warn('MP lookup unavailable',e); }
}
function autoFillMP(n){
  var codEl=document.getElementById('ic'+n);
  if(!codEl) return;
  var val=codEl.value.trim();
  var mp=_MP_LIST.find(function(m){ return (m.codigo_mp||m.codigo_interno)===val; });
  if(mp){
    var nameEl=document.getElementById('in'+n);
    if(nameEl&&!nameEl.value) nameEl.value=mp.nombre_comercial||mp.nombre_material||'';
  }
}
// ─── Catálogo de consumibles en Crear OC (Sebastián 1-jul) · papelería/EPP/servicios ───
// Buscar en el catálogo (maestro_consumibles) al escribir la descripción → autocompleta el
// precio (y proveedor si está vacío). Los ítems nuevos se guardan al catálogo al crear la OC.
function buildConsumDL(){
  var dl=document.getElementById('consum-dl');
  if(!dl){ dl=document.createElement('datalist'); dl.id='consum-dl'; document.body.appendChild(dl); }
  dl.innerHTML=(_CONSUM||[]).map(function(x){
    var meta=(x.proveedor||'')+((x.precio_referencia>0)?(' · $'+parseFloat(x.precio_referencia).toLocaleString('es-CO')):'');
    return '<option value="'+esc(x.nombre)+'">'+esc(meta)+'</option>';
  }).join('');
}
function autoFillConsumible(n){
  var nomEl=document.getElementById('in'+n);
  if(!nomEl) return;
  var val=(nomEl.value||'').trim().toLowerCase();
  if(!val) return;
  var hit=(_CONSUM||[]).find(function(x){ return (x.nombre||'').trim().toLowerCase()===val; });
  if(!hit) return;
  var pEl=document.getElementById('ip'+n);
  if(pEl && (!pEl.value||parseFloat(pEl.value)===0) && hit.precio_referencia>0){ pEl.value=parseFloat(hit.precio_referencia).toFixed(2); }
  var provEl=document.getElementById('noc-prov');
  if(provEl && !provEl.value && hit.proveedor){ provEl.value=hit.proveedor; }
  if(typeof calcTot==='function') calcTot();
}
// ─── Inline provider creation ─────────────────────────────────────────
function showNewProvForm(){
  var frm=document.getElementById('noc-new-prov-form');
  if(!frm) return;
  frm.style.display='block';
  // Pre-fill nombre from free-text field if something was typed
  var txt=document.getElementById('noc-prov-txt');
  var nomEl=document.getElementById('np-nombre');
  if(nomEl&&txt&&txt.value.trim()&&!nomEl.value) nomEl.value=txt.value.trim();
  frm.scrollIntoView({behavior:'smooth',block:'nearest'});
}
function guardarNuevoProv(){
  var nombre=(document.getElementById('np-nombre').value||'').trim();
  if(!nombre){ alert('El nombre del proveedor es requerido'); return; }
  var btn=document.querySelector('#noc-new-prov-form .btn.bg');
  if(btn){ btn.disabled=true; btn.textContent='Guardando...'; }
  // Form completo · Sebastian 4-may-2026 (todos los campos para no quedar pelado)
  var payload = {
    nombre:nombre,
    nit:(document.getElementById('np-nit').value||'').trim(),
    contacto:(document.getElementById('np-contacto')||{value:''}).value.trim(),
    telefono:(document.getElementById('np-tel').value||'').trim(),
    email:(document.getElementById('np-email').value||'').trim(),
    direccion:(document.getElementById('np-direccion')||{value:''}).value.trim(),
    banco:(document.getElementById('np-banco')||{value:''}).value.trim(),
    tipo_cuenta:(document.getElementById('np-tipo-cuenta')||{value:''}).value.trim(),
    num_cuenta:(document.getElementById('np-num-cuenta')||{value:''}).value.trim(),
    condiciones_pago:(document.getElementById('np-cond-pago')||{value:'30 dias'}).value,
    concepto_compra:(document.getElementById('np-concepto').value||'').trim()
  };
  fetch('/api/proveedores-compras', _fetchOpts('POST', payload)).then(function(r){ return r.json(); }).then(function(d){
    if(d.error){ alert('Error: '+d.error);
      if(btn){ btn.disabled=false; btn.textContent='Guardar proveedor'; } return; }
    reloadProvs(nombre);
  }).catch(function(e){
    alert('Error de conexion: '+e);
    if(btn){ btn.disabled=false; btn.textContent='Guardar proveedor'; }
  });
}

// Detector de duplicados por similitud (LOWER+TRIM) · Catalina 4-may-2026
// Cuando Catalina escribe el nombre, compara contra PROVS (cargado al inicio)
// y le sugiere si parece ser uno existente con typo distinto.
function _normProvName(s){
  return (s||'').toLowerCase().trim()
    .normalize('NFD').replace(/[̀-ͯ]/g,'')  // sin acentos
    .replace(/[^a-z0-9 ]/g,' ').replace(/\\s+/g,' ').trim();
}
function checkProvDuplicado(){
  var input = document.getElementById('np-nombre');
  var warning = document.getElementById('np-dup-warning');
  if (!input || !warning) return;
  var nombre = (input.value||'').trim();
  if (nombre.length < 4) { warning.style.display='none'; return; }
  var norm = _normProvName(nombre);
  // Buscar en PROVS los que tengan el mismo nombre normalizado
  var sospechosos = (PROVS||[]).filter(function(p){
    var pnorm = _normProvName(p.nombre);
    if (!pnorm) return false;
    if (pnorm === norm) return true;  // exacto
    // Containment: una contiene a otra (>=4 chars)
    if (norm.length >= 4 && pnorm.length >= 4) {
      if (pnorm.indexOf(norm) >= 0 || norm.indexOf(pnorm) >= 0) return true;
    }
    return false;
  });
  if (sospechosos.length === 0) { warning.style.display='none'; return; }
  warning.style.display='block';
  warning.innerHTML = '⚠ Posible duplicado de proveedor existente: <b>' +
    sospechosos.slice(0,3).map(function(p){ return esc(p.nombre); }).join('</b>, <b>') +
    '</b>. Si es el mismo, selecciona del dropdown arriba en lugar de crearlo de nuevo.';
}
function cancelarNuevoProv(){
  var frm=document.getElementById('noc-new-prov-form');
  if(frm) frm.style.display='none';
  var sel=document.getElementById('noc-prov');
  if(sel) sel.value='';
  var box=document.getElementById('noc-ibox');
  if(box) box.style.display='none';
}
function reloadProvs(selectAfter){
  fetch('/api/proveedores-compras').then(function(r){ return r.json(); })
  .then(function(d){
    PROVS=d.proveedores||[];
    fillProvSelect('noc-prov');
    // Also refresh datalist for free-text categories
    var dl=document.getElementById('prov-dl');
    if(dl) dl.innerHTML=PROVS.map(function(p){
      return '<option value="'+esc(p.nombre)+'">';
    }).join('');
    var frm=document.getElementById('noc-new-prov-form');
    if(frm) frm.style.display='none';
    if(selectAfter){
      var isCat=(_ocCatCode==='MP'||_ocCatCode==='MEE');
      if(isCat){
        var sel=document.getElementById('noc-prov');
        if(sel) sel.value=selectAfter;
        fillProv('noc-prov','noc-ibox');
      } else {
        var txt=document.getElementById('noc-prov-txt');
        if(txt) txt.value=selectAfter;
      }
    }
  }).catch(function(e){ console.error('Error recargando proveedores',e); });
}


// ─── MP: Banner de alertas ──────────────────────────────────
// Fuente: Centro de Programación (velocidad Shopify + producciones futuras
// del calendario + stock real). Lista MPs con déficit operacional REAL,
// no items que tienen stock_actual<stock_minimo de un campo desactualizado.
function renderMPAlerts(){
  var banner=document.getElementById('mp-alert-banner');
  var text=document.getElementById('mp-alert-text');
  var list=document.getElementById('mp-alert-list');
  if(!banner) return;
  var _nMee = (_ALERTAS_MEE||[]).length;
  if((!_ALERTAS_MP||!_ALERTAS_MP.length) && !_nMee){ banner.style.display='none'; return; }
  var total_def=_ALERTAS_MP.reduce(function(s,a){ return s+parseFloat(a.deficit||0); },0);
  var n_china = _ALERTAS_MP.filter(function(a){ return a.es_china; }).length;
  banner.style.display='block';
  var resumen = _ALERTAS_MP.length+' MPs en déficit real (Centro de Programación) — Faltante total: '+Math.round(total_def).toLocaleString('es-CO')+' g';
  if(n_china > 0) resumen += ' · ⚠ '+n_china+' de China (lead 60d)';
  if(_nMee > 0) resumen += ' · 📦 '+_nMee+' envase'+(_nMee>1?'s':'')+' en déficit';
  text.textContent=resumen;
  var mpChips=_ALERTAS_MP.slice(0,8).map(function(a){
    var col = a.es_china ? '#b91c1c' : '#d97706';
    var deficit_g = Math.round(a.deficit||0);
    var deficit_str = deficit_g.toLocaleString('es-CO')+' g';
    var stock_str = a.stock_actual === Infinity ? '∞' :
                    Math.round(a.stock_actual||0).toLocaleString('es-CO')+' g';
    var prov_str = a.proveedor ? ' · '+a.proveedor : '';
    var china_mark = a.es_china ? '🇨🇳 ' : '';
    return '<span style="background:#fff;border:1px solid '+col+';color:'+col
      +';border-radius:4px;padding:2px 8px;font-size:11px;font-weight:600;" title="Stock: '+stock_str+prov_str+'">'
      +china_mark+esc(a.nombre.substring(0,28))+' (faltan '+deficit_str+')</span>';
  });
  // Envases (MEE) en déficit · color teal para distinguir de MPs · 18-jun
  var meeChips=(_ALERTAS_MEE||[]).slice(0,8).map(function(m){
    var def_str=Math.round(m.deficit||0).toLocaleString('es-CO')+' u';
    var prov=m.proveedor?' · '+m.proveedor:'';
    return '<span style="background:#fff;border:1px solid #0f766e;color:#0f766e;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:600;" title="Envase'+prov+'">📦 '+esc((m.nombre||m.codigo||'').substring(0,28))+' (faltan '+def_str+')</span>';
  });
  list.innerHTML=mpChips.concat(meeChips).join('');
}

// ─── MP: Nueva OC con catálogo ───────────────────────────
function openNuevaOCMP(prefillItems){
  MP_ITMS=0;
  document.getElementById('nmp-tbody').innerHTML='';
  document.getElementById('nmp-prov').value='';
  document.getElementById('nmp-ibox').style.display='none';
  document.getElementById('nmp-fent').value='';
  document.getElementById('nmp-obs').value='';
  document.getElementById('nmp-tot').textContent='$0';
  fillProvSelect('nmp-prov');
  var dl=document.getElementById('mp-codes-dl');
  dl.innerHTML=_MPCAT.map(function(m){
    return '<option value="'+esc(m.codigo_mp)+'">'+esc(m.nombre_inci||m.nombre_comercial||m.codigo_mp)+'</option>';
  }).join('');
  var info=document.getElementById('nmp-alert-info');
  if(_ALERTAS_MP&&_ALERTAS_MP.length){
    info.style.display='block';
    info.textContent='⚠️ '+_ALERTAS_MP.length+' MPs bajo stock mínimo. Al escribir un código verás stock en tiempo real.';
  } else { info.style.display='none'; }
  if(prefillItems&&prefillItems.length){
    prefillItems.forEach(function(it){ addRowMP(it); });
  } else { addRowMP(null); addRowMP(null); }
  openModal('m-noc-mp');
}
function addRowMP(prefill){
  MP_ITMS++;
  var n=MP_ITMS;
  var cod=(prefill&&prefill.codigo_mp)||'';
  var nom=(prefill&&prefill.nombre_mp)||'';
  var qty=(prefill&&prefill.cantidad_g)||'';
  var prc=(prefill&&prefill.precio_unitario)||'';
  var tr=document.createElement('tr');
  tr.id='mpr'+n;
  tr.innerHTML=
    '<td style="padding:3px;">'
      +'<input id="mprc'+n+'" list="mp-codes-dl" placeholder="COD" value="'+esc(cod)+'"'
      +' style="width:95px;padding:5px;border:1px solid #d6d3d1;border-radius:4px;font-size:12px;"'
      +' onchange="mpLookup('+n+')" oninput="mpLookupDebounce('+n+')">';
  tr.innerHTML+=
    '</td>'
    +'<td style="padding:3px;min-width:150px;">'
      +'<input id="mprn'+n+'" placeholder="Descripcion" value="'+esc(nom)+'"'
      +' style="width:100%;padding:5px;border:1px solid #d6d3d1;border-radius:4px;font-size:12px;">'
      +'<div id="mpri'+n+'" style="font-size:10px;margin-top:2px;"></div>'
    +'</td>'
    +'<td style="padding:3px;">'
      +'<input id="mprq'+n+'" type="number" value="'+esc(qty)+'" min="0" placeholder="g"'
      +' oninput="calcTotMP()" style="width:80px;padding:5px;border:1px solid #d6d3d1;border-radius:4px;font-size:12px;text-align:right;">'
    +'</td>'
    +'<td style="padding:3px;">'
      +'<input id="mprp'+n+'" type="number" value="'+esc(prc)+'" min="0" step="0.001" placeholder="$/g"'
      +' oninput="calcTotMP()" style="width:85px;padding:5px;border:1px solid #d6d3d1;border-radius:4px;font-size:12px;text-align:right;">'
    +'</td>'
    +'<td id="mprs'+n+'" style="padding:3px 6px;text-align:right;white-space:nowrap;font-size:12px;">$0</td>'
    +'<td style="padding:3px 2px;">'
      +'<button class="btn bo" style="padding:2px 6px;font-size:11px;" onclick="rmRowMP('+n+')">x</button>'
    +'</td>';
  document.getElementById('nmp-tbody').appendChild(tr);
  if(prefill) calcTotMP();
}
function rmRowMP(n){ var e=document.getElementById('mpr'+n); if(e){ e.remove(); calcTotMP(); } }
var _mpLT={};
function mpLookupDebounce(n){
  if(_mpLT[n]) clearTimeout(_mpLT[n]);
  _mpLT[n]=setTimeout(function(){ mpLookup(n); },300);
}
function mpLookup(n){
  var codEl=document.getElementById('mprc'+n);
  var namEl=document.getElementById('mprn'+n);
  var infEl=document.getElementById('mpri'+n);
  var prcEl=document.getElementById('mprp'+n);
  if(!codEl||!infEl) return;
  var cod=(codEl.value||'').trim();
  if(!cod){ infEl.textContent=''; return; }
  var mp=_MPCAT.find(function(m){ return m.codigo_mp===cod; });
  if(!mp&&cod.length>=4){
    var q=cod.toLowerCase();
    mp=_MPCAT.find(function(m){
      return (m.nombre_comercial||'').toLowerCase().indexOf(q)>=0
          ||(m.nombre_inci||'').toLowerCase().indexOf(q)>=0;
    });
  }
  if(!mp){
    // Codigo NO existe en maestro_mps · ofrecer crear MP nueva
    if(cod.length >= 2){
      infEl.style.color='#dc2626';
      // Usa data attribute + event delegation para evitar quoting issues
      infEl.innerHTML = '⚠ Código <b>'+esc(cod)+'</b> no existe en maestro · '
        +'<a href="#" data-action="crear-mp-rapida" data-codigo="'+esc(cod)+'" '
        +'style="color:#10b981;font-weight:700;text-decoration:underline;">crear MP nueva</a>';
    } else {
      infEl.textContent='';
      infEl.style.color='#78716c';
    }
    return;
  }
  if(!(namEl.value||'').trim()) namEl.value=mp.nombre_comercial||mp.nombre_inci||cod;
  if((!prcEl.value||parseFloat(prcEl.value)===0)&&mp.precio_referencia&&mp.precio_referencia>0){
    prcEl.value=parseFloat(mp.precio_referencia).toFixed(4);
    calcTotMP();
  }
  var alerta=_ALERTAS_MP.find(function(a){ return a.codigo_mp===mp.codigo_mp; });
  if(alerta){
    infEl.style.color='#dc2626';
    infEl.textContent='⚠ Stock: '+Math.round(alerta.stock_actual)+'g / Min: '+Math.round(mp.stock_minimo)+'g | Deficit: '+Math.round(alerta.deficit)+'g';
  } else {
    infEl.style.color='#16a34a';
    infEl.textContent='✓ Stock OK | Min: '+Math.round(mp.stock_minimo||0)+'g'+(mp.precio_referencia?' | Ref: $'+parseFloat(mp.precio_referencia).toFixed(2)+'/g':'');
  }
}
function calcTotMP(){
  var tot=0;
  for(var i=1;i<=MP_ITMS;i++){
    var q=document.getElementById('mprq'+i),p=document.getElementById('mprp'+i);
    if(!q||!p) continue;
    var s=parseFloat(q.value||0)*parseFloat(p.value||0);
    var el=document.getElementById('mprs'+i); if(el) el.textContent=fmt(s);
    tot+=s;
  }
  var totEl=document.getElementById('nmp-tot'); if(totEl) totEl.textContent=fmt(tot);
}
// ────────────────────────────────────────────────────────────────
// Nueva MP rapida (Catalina · 4-may-2026)
// ────────────────────────────────────────────────────────────────
// Event delegation: cualquier <a data-action="crear-mp-rapida" data-codigo="X">
// dentro de la pagina dispara abrirNuevaMP. Evita problemas de escape.
document.addEventListener('click', function(ev){
  var el = ev.target.closest('[data-action="crear-mp-rapida"]');
  if (!el) return;
  ev.preventDefault();
  var cod = el.getAttribute('data-codigo') || '';
  abrirNuevaMP(cod);
});

function abrirNuevaMP(prefillCodigo){
  // Reset campos
  document.getElementById('nmp-codigo').value = (prefillCodigo||'').toUpperCase();
  document.getElementById('nmp-nomcomer').value = '';
  document.getElementById('nmp-nominci').value = '';
  document.getElementById('nmp-tipo').value = '';
  document.getElementById('nmp-prov-pref').value = '';
  document.getElementById('nmp-stockmin').value = '';
  document.getElementById('nmp-precio').value = '';
  document.getElementById('nmp-tipomat').value = 'MP';
  document.getElementById('nmp-msg').textContent = '';
  // Pre-llenar proveedor con el de la OC actual
  var provOC = document.getElementById('nmp-prov');
  if (provOC && provOC.value) {
    document.getElementById('nmp-prov-pref').value = provOC.value;
  }
  var _w=document.getElementById('nmp-inci-warn'); if(_w) _w.textContent='';
  openModal('m-nueva-mp');
  // Auto-código (igual que recepción de planta · evita adivinar/duplicar el código)
  if(!prefillCodigo){
    var ci=document.getElementById('nmp-codigo');
    if(ci){ ci.value='⏳...'; ci.disabled=true;
      fetch('/api/maestro-mps/next-codigo').then(function(r){return r.json();}).then(function(d){
        ci.disabled=false; ci.value=(d&&d.siguiente)?d.siguiente:'';
        var h=document.getElementById('nmp-msg');
        if(h&&d&&d.siguiente){ h.style.color='#16a34a'; h.textContent='Código auto-asignado: '+d.siguiente+' · '+(d.total_en_catalogo||0)+' MPs en catálogo'; }
      }).catch(function(){ ci.disabled=false; ci.value=''; ci.placeholder='MP00350'; });
    }
  }
  setTimeout(function(){ var f=document.getElementById('nmp-nomcomer'); if(f) f.focus(); }, 120);
}
// Check INCI existente (igual a recepción: te dice si ese INCI ya está en el catálogo → evita duplicar)
function checkInciNuevaMP(){
  var inci=((document.getElementById('nmp-nominci')||{}).value||'').trim().toLowerCase();
  var w=document.getElementById('nmp-inci-warn'); if(!w) return;
  if(inci.length<3){ w.textContent=''; return; }
  var hit=(typeof _MPCAT!=='undefined'?_MPCAT:[]).filter(function(m){return ((m.nombre_inci||'').trim().toLowerCase())===inci;})[0];
  if(hit){ w.style.color='#b45309'; w.innerHTML='&#9888;&#65039; Ya existe <b>'+_esc(hit.codigo_mp||'')+'</b> con ese INCI'+(hit.nombre_comercial?' ('+_esc(hit.nombre_comercial)+')':'')+' — mejor usá esa, no crees un duplicado.'; }
  else{ w.style.color='#16a34a'; w.textContent='✓ INCI nuevo · no existe en el catálogo.'; }
}

async function guardarNuevaMP(){
  var codigo = (document.getElementById('nmp-codigo').value||'').toUpperCase().trim();
  var nomcomer = (document.getElementById('nmp-nomcomer').value||'').trim();
  var nominci = (document.getElementById('nmp-nominci').value||'').trim();
  var msg = document.getElementById('nmp-msg');
  if (!codigo) { msg.style.color='#dc2626'; msg.textContent='⚠ Codigo MP obligatorio'; return; }
  if (!nomcomer && !nominci) { msg.style.color='#dc2626'; msg.textContent='⚠ Al menos un nombre (comercial o INCI)'; return; }

  var payload = {
    codigo_mp: codigo,
    nombre_comercial: nomcomer,
    nombre_inci: nominci,
    tipo: (document.getElementById('nmp-tipo').value||'').trim(),
    proveedor: (document.getElementById('nmp-prov-pref').value||'').trim(),
    stock_minimo: parseFloat(document.getElementById('nmp-stockmin').value||0),
    precio_referencia: parseFloat(document.getElementById('nmp-precio').value||0),
    tipo_material: document.getElementById('nmp-tipomat').value,
  };
  msg.style.color='#0e7490';
  msg.textContent='Guardando...';
  try{
    var r = await fetch('/api/maestro-mps', _fetchOpts('POST', payload));
    var d = await r.json();
    if (r.status === 409) {
      msg.style.color='#dc2626';
      msg.innerHTML='⚠ '+d.error+' '+
        '<a href="#" onclick="event.preventDefault();forzarActualizarMP();" style="color:#0e7490;text-decoration:underline;">Sobrescribir</a>';
      return;
    }
    if (!r.ok || d.error) {
      msg.style.color='#dc2626';
      msg.textContent='⚠ ' + (d.error || 'Error');
      return;
    }
    msg.style.color='#16a34a';
    msg.textContent='✓ ' + (d.message || 'MP creada');
    // Refrescar catalogo + datalist
    await refrescarCatalogoMP();
    // Si el usuario habia escrito un codigo en una fila de OC, re-validar
    setTimeout(function(){
      closeModal('m-nueva-mp');
      // Re-trigger lookup en filas existentes con este codigo
      for (var i = 1; i <= MP_ITMS; i++) {
        var el = document.getElementById('mprc' + i);
        if (el && (el.value||'').toUpperCase() === codigo) mpLookup(i);
      }
    }, 700);
  }catch(e){
    msg.style.color='#dc2626';
    msg.textContent='⚠ Error red: '+e.message;
  }
}

async function forzarActualizarMP(){
  var msg = document.getElementById('nmp-msg');
  var payload = {
    codigo_mp: (document.getElementById('nmp-codigo').value||'').toUpperCase().trim(),
    nombre_comercial: (document.getElementById('nmp-nomcomer').value||'').trim(),
    nombre_inci: (document.getElementById('nmp-nominci').value||'').trim(),
    tipo: (document.getElementById('nmp-tipo').value||'').trim(),
    proveedor: (document.getElementById('nmp-prov-pref').value||'').trim(),
    stock_minimo: parseFloat(document.getElementById('nmp-stockmin').value||0),
    precio_referencia: parseFloat(document.getElementById('nmp-precio').value||0),
    tipo_material: document.getElementById('nmp-tipomat').value,
    forzar_actualizar: true,
  };
  if (!confirm('Sobrescribir MP existente con estos datos? Esta accion queda en audit_log.')) return;
  try{
    var r = await fetch('/api/maestro-mps', _fetchOpts('POST', payload));
    var d = await r.json();
    if (!r.ok || d.error) {
      msg.style.color='#dc2626';
      msg.textContent='⚠ ' + (d.error || 'Error');
      return;
    }
    msg.style.color='#16a34a';
    msg.textContent='✓ MP actualizada';
    await refrescarCatalogoMP();
    setTimeout(function(){ closeModal('m-nueva-mp'); }, 700);
  }catch(e){
    msg.style.color='#dc2626';
    msg.textContent='⚠ Error red: '+e.message;
  }
}

async function refrescarCatalogoMP(){
  // Recargar _MPCAT y datalist mp-codes-dl
  try{
    var r = await fetch('/api/maestro-mps');
    var d = await r.json();
    _MPCAT = d.mps || d || [];
    var dl = document.getElementById('mp-codes-dl');
    if (dl) {
      dl.innerHTML = _MPCAT.map(function(m){
        return '<option value="'+esc(m.codigo_mp)+'">'+esc(m.nombre_inci||m.nombre_comercial||m.codigo_mp)+'</option>';
      }).join('');
    }
  }catch(e){ console.error('refrescarCatalogoMP fallo:', e); }
}

async function crearOCMP(){
  var prov=document.getElementById('nmp-prov').value;
  var obs=document.getElementById('nmp-obs').value;
  var fent=document.getElementById('nmp-fent').value;
  if(!prov){ alert('Selecciona un proveedor'); return; }
  var items=[];
  for(var i=1;i<=MP_ITMS;i++){
    var n=document.getElementById('mprn'+i);
    if(!n||(n.value||'').trim()==='') continue;
    items.push({
      codigo_mp:(document.getElementById('mprc'+i)||{value:''}).value,
      nombre_mp:n.value.trim(),
      cantidad_g:parseFloat((document.getElementById('mprq'+i)||{value:1}).value||1),
      precio_unitario:parseFloat((document.getElementById('mprp'+i)||{value:0}).value||0)
    });
  }
  if(!items.length){ alert('Agrega al menos un item con descripcion'); return; }
  try{
    var body={proveedor:prov,categoria:'MP',observaciones:obs,items:items,creado_por:'{usuario}'};
    if(fent) body.fecha_entrega_est=fent;
    var r=await fetch('/api/ordenes-compra',_fetchOpts('POST', body));
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    // 1-clic · Catalina: autorizar al crear → va directo a Por Pagar (reusa el autorizar canónico
    // con su chequeo de límite + CAS · si excede el monto, queda en Borrador para gerencia).
    var _auto=document.getElementById('noc-mp-autorizar');
    var _msg='OC creada: '+d.numero_oc;
    if(_auto && _auto.checked && d.numero_oc){
      try{
        var ra=await fetch('/api/ordenes-compra/'+encodeURIComponent(d.numero_oc)+'/autorizar',_fetchOpts('PATCH', {}));
        var da=await ra.json();
        if(ra.ok && !da.error){ _msg='✓ OC '+d.numero_oc+' creada y enviada a Por Pagar'; }
        else{ _msg='OC '+d.numero_oc+' creada · quedó en Borrador (no se autorizó: '+(da.error||'monto/permiso')+')'; }
      }catch(e){}
    }
    closeModal('m-noc-mp');
    await loadData();
    renderDash();
    alert(_msg);
  }catch(e){ alert('Error de conexion: '+e); }
}

// ─── MP: OC Sugerida desde alertas ───────────────────────
function openOCSugerida(){
  if(!_ALERTAS_MP||!_ALERTAS_MP.length){ alert('No hay MPs bajo stock minimo'); return; }
  var tbody=document.getElementById('sug-tbody');
  tbody.innerHTML=_ALERTAS_MP.map(function(a,i){
    var mp=_MPCAT.find(function(m){ return m.codigo_mp===a.codigo_mp; });
    var pref=(mp&&mp.precio_referencia>0)?parseFloat(mp.precio_referencia).toFixed(4):'';
    var qty=Math.ceil(a.deficit*1.2/100)*100;
    var provOpts='<option value="">-- Proveedor --</option>';
    if(a.proveedor){ provOpts+='<option value="'+esc(a.proveedor)+'" selected>'+esc(a.proveedor)+'</option>'; }
    PROVS.forEach(function(p){
      if(p.nombre!==a.proveedor) provOpts+='<option value="'+esc(p.nombre)+'">'+esc(p.nombre)+'</option>';
    });
    return '<tr id="sugr'+i+'">'
      +'<td style="padding:5px 8px;">'
        +'<div style="font-weight:600;font-size:12px;">'+esc(a.nombre.substring(0,35))+'</div>'
        +'<div style="font-size:10px;color:#78716c;">'+esc(a.codigo_mp)+'</div>'
      +'</td>'
      +'<td style="padding:5px 4px;text-align:right;font-size:12px;">'+Math.round(a.stock_actual)+'g</td>'
      +'<td style="padding:5px 4px;text-align:right;font-size:12px;color:#dc2626;font-weight:600;">'+Math.round(a.deficit)+'g</td>'
      +'<td style="padding:5px 4px;">'
        +'<input id="sugq'+i+'" type="number" value="'+qty+'" min="0" oninput="calcTotSug()"'
        +' style="width:88px;padding:4px;border:1px solid #d6d3d1;border-radius:4px;font-size:12px;text-align:right;">'
      +'</td>'
      +'<td style="padding:5px 4px;">'
        +'<input id="sugp'+i+'" type="number" value="'+pref+'" min="0" step="0.001" placeholder="$/g" oninput="calcTotSug()"'
        +' style="width:72px;padding:4px;border:1px solid #d6d3d1;border-radius:4px;font-size:12px;text-align:right;">'
      +'</td>'
      +'<td style="padding:5px 4px;">'
        +'<select id="sugprov'+i+'" style="width:100%;padding:3px 4px;border:1px solid #d6d3d1;border-radius:4px;font-size:11px;">'+provOpts+'</select>'
      +'</td>'
      +'<td id="sugs'+i+'" style="padding:5px 4px;text-align:right;font-size:12px;white-space:nowrap;">$0</td>'
      +'<td style="padding:5px 4px;text-align:center;" id="sugact'+i+'">'
        +'<button onclick="crearOCFila('+i+')" style="padding:3px 8px;font-size:11px;background:#2563eb;color:#fff;border:none;border-radius:4px;cursor:pointer;white-space:nowrap;">Crear OC</button>'
      +'</td>'
      +'</tr>';
  }).join('');
  calcTotSug();
  openModal('m-oc-sug');
}
function calcTotSug(){
  var tot=0;
  for(var i=0;i<_ALERTAS_MP.length;i++){
    var q=document.getElementById('sugq'+i),p=document.getElementById('sugp'+i);
    if(!q||!p) continue;
    var s=parseFloat(q.value||0)*parseFloat(p.value||0);
    var el=document.getElementById('sugs'+i); if(el) el.textContent=fmt(s);
    tot+=s;
  }
  var totEl=document.getElementById('sug-tot'); if(totEl) totEl.textContent=fmt(tot);
}
async function crearOCSugerida(){
  // Group items by their per-row selected provider; skip zero-qty rows
  var grupos={};
  for(var i=0;i<_ALERTAS_MP.length;i++){
    var a=_ALERTAS_MP[i];
    var q=parseFloat((document.getElementById('sugq'+i)||{value:0}).value||0);
    var p=parseFloat((document.getElementById('sugp'+i)||{value:0}).value||0);
    var prov=(document.getElementById('sugprov'+i)||{value:''}).value;
    if(q<=0) continue;
    if(!prov){ alert('Falta proveedor para: '+a.nombre); return; }
    if(!grupos[prov]) grupos[prov]=[];
    grupos[prov].push({codigo_mp:a.codigo_mp,nombre_mp:a.nombre,cantidad_g:q,precio_unitario:p});
  }
  var provList=Object.keys(grupos);
  if(!provList.length){ alert('Todas las cantidades son 0 — ajusta antes de crear'); return; }
  var creadas=[]; var errores=[];
  for(var pi=0;pi<provList.length;pi++){
    var prov=provList[pi]; var items=grupos[prov];
    try{
      var r=await fetch('/api/ordenes-compra',_fetchOpts('POST', {proveedor:prov,categoria:'MP',creado_por:'{usuario}',
          observaciones:'OC sugerida — MPs bajo stock ('+new Date().toLocaleDateString('es-CO')+')',
          items:items}));
      var res=null; try{res=await r.json();}catch(_){res=null;}
      if(r.ok&&res&&!res.error){ creadas.push(res.numero_oc||prov); }
      else{ errores.push(prov+': '+((res&&res.error)||'Error '+r.status)); }
    }catch(e){ errores.push(prov+': '+e.message); }
  }
  await loadData(); renderDash(); renderDashHome2(); if(typeof renderKpisGrandes==='function') renderKpisGrandes(); if(typeof renderAlertasBanner==='function') renderAlertasBanner(); if(typeof renderMisSolicWidget==='function') renderMisSolicWidget();
  if(errores.length){
    alert('Creadas: '+creadas.join(', ')+'\\nErrores:\\n'+errores.join('\\n'));
  } else {
    closeModal('m-oc-sug');
    alert('OCs creadas (agrupadas por proveedor): '+creadas.join(', '));
  }
}
async function crearOCFila(i){
  var a=_ALERTAS_MP[i];
  var q=parseFloat((document.getElementById('sugq'+i)||{value:0}).value||0);
  var p=parseFloat((document.getElementById('sugp'+i)||{value:0}).value||0);
  var prov=(document.getElementById('sugprov'+i)||{value:''}).value;
  if(q<=0){ alert('Ingresa una cantidad mayor a 0'); return; }
  if(!prov){ alert('Selecciona un proveedor para: '+a.nombre); return; }
  var actEl=document.getElementById('sugact'+i);
  if(actEl) actEl.innerHTML='<span style="font-size:11px;color:#78716c;">Enviando...</span>';
  try{
    var r=await fetch('/api/ordenes-compra',_fetchOpts('POST', {proveedor:prov,categoria:'MP',creado_por:'{usuario}',
        observaciones:'OC sugerida — '+a.nombre+' ('+new Date().toLocaleDateString('es-CO')+')',
        items:[{codigo_mp:a.codigo_mp,nombre_mp:a.nombre,cantidad_g:q,precio_unitario:p}]}));
    var res=null; try{res=await r.json();}catch(_){res=null;}
    if(r.ok&&res&&!res.error){
      if(actEl) actEl.innerHTML='<span style="color:#16a34a;font-size:13px;">&#x2713; '+esc(res.numero_oc||'OK')+'</span>';
      var row=document.getElementById('sugr'+i);
      if(row) row.style.background='#f0fdf4';
      await loadData(); renderDash(); renderDashHome2(); if(typeof renderKpisGrandes==='function') renderKpisGrandes(); if(typeof renderAlertasBanner==='function') renderAlertasBanner(); if(typeof renderMisSolicWidget==='function') renderMisSolicWidget();
    } else {
      var msg=(res&&res.error)?res.error:'Error '+r.status;
      if(actEl) actEl.innerHTML='<span style="color:#dc2626;font-size:11px;">'+esc(msg)+'</span>';
    }
  }catch(e){
    if(actEl) actEl.innerHTML='<span style="color:#dc2626;font-size:11px;">'+esc(e.message)+'</span>';
  }
}

// ─── Revisar ──────────────────────────────────────────────────────
function openRev(num,prov,val,obs,conIva,valBase){
  var oc=OCS.find(function(o){ return o.numero_oc===num; })||{};
  var ivaActivo=conIva!==undefined ? !!conIva : !!(oc.con_iva);
  var base=valBase!==undefined ? valBase : (oc.valor_sin_iva>0 ? oc.valor_sin_iva : (ivaActivo ? parseFloat(val||0)/1.19 : parseFloat(val||0)));
  document.getElementById('rev-num').value=num;
  document.getElementById('rev-info').innerHTML='<strong>'+num+'</strong><br><span style="color:#78716c;">'+esc(obs||'-')+'</span>';
  document.getElementById('rev-val').value=base>0 ? base.toFixed(0) : (val||'');
  document.getElementById('rev-iva-chk').checked=ivaActivo;
  document.getElementById('rev-obs').value='';
  document.getElementById('rev-fent').value='';
  document.getElementById('rev-ibox').style.display='none';
  fillProvSelect('rev-prov');
  document.getElementById('rev-prov').value=prov;
  if(prov) fillProv('rev-prov','rev-ibox');
  calcRevIva();
  openModal('m-rev');
}
function calcRevIva(){
  var base=parseFloat(document.getElementById('rev-val').value)||0;
  var chk=document.getElementById('rev-iva-chk').checked;
  var bd=document.getElementById('rev-iva-breakdown');
  if(chk && base>0){
    var iva=base*0.19;
    var tot=base+iva;
    var fmt2=function(n){ return '$'+Math.round(n).toLocaleString('es-CO'); };
    document.getElementById('rev-iva-sub').textContent=fmt2(base);
    document.getElementById('rev-iva-monto').textContent=fmt2(iva);
    document.getElementById('rev-iva-total').textContent=fmt2(tot);
    bd.style.display='block';
  } else {
    bd.style.display='none';
  }
}
async function confirmarRev(){
  var num=document.getElementById('rev-num').value;
  var prov=document.getElementById('rev-prov').value;
  var val=document.getElementById('rev-val').value;
  var obs=document.getElementById('rev-obs').value;
  var fent=document.getElementById('rev-fent').value;
  if(!prov){ alert('Selecciona proveedor'); return; }
  if(!val||parseFloat(val)<=0){ alert('Ingresa el valor total'); return; }
  try{
    var conIva=document.getElementById('rev-iva-chk').checked;
    var baseVal=parseFloat(val)||0;
    var totalVal=conIva ? Math.round(baseVal*1.19*100)/100 : baseVal;
    var body={proveedor:prov,valor_total:totalVal,observaciones:obs,con_iva:conIva,valor_sin_iva:baseVal};
    if(fent) body.fecha_entrega_est=fent;
    var r=await fetch('/api/ordenes-compra/'+num+'/revisar',_fetchOpts('PATCH', body));
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    closeModal('m-rev');
    await loadData();
  }catch(e){ alert('Error: '+e); }
}

// ─── Autorizar ────────────────────────────────────────────────────
// ─── Autorizar (abre modal con opcion rechazar) ───────────────────
function autorizarOC(num){
  var oc=OCS.find(function(o){ return o.numero_oc===num; })||{};
  // Fallback: si se autoriza desde la vista agrupada, OCS puede no tener la OC → busca en
  // _consolCache para mostrar proveedor/valor en el modal (la autorización funciona igual).
  if(!oc.numero_oc && typeof _consolCache!=='undefined'){
    (_consolCache||[]).forEach(function(p){ (p.ocs||[]).forEach(function(o){
      if(o.numero_oc===num) oc={numero_oc:num, proveedor:p.proveedor, valor_total:o.valor_total||p.valor_total}; }); });
  }
  document.getElementById('aut-num').value=num;
  document.getElementById('aut-motivo').value='';
  document.getElementById('m-aut-info').innerHTML=
    '<strong>'+esc(num)+'</strong> &mdash; '+esc(oc.proveedor||'-')+
    '<br><span style="color:#78716c;font-size:12px;">Valor: <strong>'+fmt(oc.valor_total)+'</strong>'+
    (oc.observaciones?' &nbsp;|&nbsp; '+esc((oc.observaciones||'').substring(0,80)):'')+
    '</span>';
  openModal('m-aut');
}
async function decidirOC(decision){
  var num=document.getElementById('aut-num').value;
  var motivo=document.getElementById('aut-motivo').value.trim();
  if(decision==='Rechazada' && !motivo){
    // Gap #5 · 21-may-2026 · motivo OBLIGATORIO (≥10 chars · queda audit)
    motivo = prompt('Motivo de rechazo (≥10 chars · el solicitante verá esto):');
    if(!motivo) return;
    motivo = motivo.trim();
    if(motivo.length < 10){ alert('Motivo debe tener ≥10 chars'); return; }
  }
  if(decision==='Autorizada'){
    try{
      var r=await fetch('/api/ordenes-compra/'+num+'/autorizar',_fetchOpts('PATCH', {motivo:motivo}));
      var d=await r.json();
      if(d.error){ alert('Error: '+d.error); return; }
    }catch(e){ alert('Error: '+e); return; }
  } else {
    try{
      var r2=await fetch('/api/ordenes-compra/'+num,_fetchOpts('PUT', {estado:'Rechazada',motivo:motivo}));
      var d2=await r2.json();
      if(d2.error){ alert('Error: '+d2.error); return; }
    }catch(e){ alert('Error: '+e); return; }
  }
  closeModal('m-aut');
  await loadData();
  renderDash();
  // refrescar la vista agrupada por proveedor si está activa (autorizar desde ahí · 18-jun)
  if(typeof loadConsolidado==='function'){ try{ await loadConsolidado(); }catch(e){} }
}

function openPago(num,val,prov){
  document.getElementById('pago-num').value=num;
  document.getElementById('pago-monto').value=val||'';
  document.getElementById('pago-obs').value='';
  document.getElementById('pago-info').innerHTML='<strong>'+num+'</strong> &mdash; '+esc(prov)+'<br>Valor autorizado: <strong>'+fmt(val)+'</strong>';
  openModal('m-pago');
}
function previewPagoImg(){
  var f=document.getElementById('pago-img-file').files[0];
  var prev=document.getElementById('pago-img-preview');
  if(f){ var rd=new FileReader(); rd.onload=function(e){ prev.src=e.target.result; prev.style.display='block'; }; rd.readAsDataURL(f); }
  else { prev.src=''; prev.style.display='none'; }
}
async function confirmarPago(){
  var num=document.getElementById('pago-num').value;
  var monto=document.getElementById('pago-monto').value;
  var medio=document.getElementById('pago-medio').value;
  var obs=document.getElementById('pago-obs').value;
  var factura=(document.getElementById('pago-factura').value||'').trim().toUpperCase();
  // Bug #1 fix · 21-may-2026 · validar monto explícitamente (no vacío)
  if(monto==='' || monto==null){
    alert('⚠ Ingresá el monto del pago · si querés pagar el saldo completo, escribilo explícito.');
    return;
  }
  if(parseFloat(monto)<=0){ alert('Monto debe ser >0'); return; }
  // Bug #1 fix · confirmación adicional si pagás el saldo completo de la OC
  var saldoSpan=document.getElementById('pago-saldo-info');
  var saldoTxt=saldoSpan?saldoSpan.textContent:'';
  // Heurística · si saldo info dice "saldo: $X" y monto coincide en magnitud
  var saldoMatch=saldoTxt.match(/\\$([\\d.,]+)/);
  if(saldoMatch){
    var saldoNum=parseFloat(saldoMatch[1].replace(/[.,]/g,''));
    if(saldoNum>1000000 && Math.abs(parseFloat(monto)-saldoNum)<saldoNum*0.01){
      if(!confirm('⚠ Estás pagando el saldo COMPLETO: $'+saldoNum.toLocaleString('es-CO')+'\\n\\n¿Es correcto?')) return;
    }
  }
  var imgData=null;
  var imgFile=document.getElementById('pago-img-file').files[0];
  if(imgFile){
    imgData=await new Promise(function(res){
      var rd=new FileReader(); rd.onload=function(e){ res(e.target.result); }; rd.readAsDataURL(imgFile);
    });
  }
  try{
    var payload={monto:parseFloat(monto),medio:medio,observaciones:obs};
    if(factura) payload.numero_factura_proveedor=factura;
    if(imgData) payload.comprobante_imagen=imgData;
    // Toggles fiscales — si están activos, el comprobante PDF se genera con retenciones/IVA
    var rf=document.getElementById('pago-aplicar-retefuente');
    var ri=document.getElementById('pago-aplicar-retica');
    var iv=document.getElementById('pago-aplicar-iva');
    if(rf && rf.checked) payload.aplicar_retefuente=true;
    if(ri && ri.checked) payload.aplicar_retica=true;
    if(iv && iv.checked) payload.aplicar_iva=true;
    var r=await fetch('/api/ordenes-compra/'+num+'/pagar',_fetchOpts('PATCH', payload));
    var d=await r.json();
    if(r.status===409 && d.codigo==='FACTURA_DUPLICADA'){
      alert('⚠ Factura duplicada\\n\\n'+d.error+'\\n\\n'+d.detail);
      return;
    }
    if(r.status===403 && d.codigo==='EXCEDE_LIMITE_APROBACION'){
      alert('⚠ Excede tu límite\\n\\n'+d.error+'\\n\\n'+d.detail);
      return;
    }
    if(d.error){ alert('Error: '+d.error); return; }
    // Mensaje claro de pago parcial vs total + comprobante de egreso
    var msg = '';
    if(d.estado==='Parcial' && typeof d.pendiente==='number'){
      msg = 'Pago registrado. Estado: PARCIAL\\nPagado total: $'+(d.total_pagado_acumulado||0).toLocaleString('es-CO')+'\\nPendiente: $'+d.pendiente.toLocaleString('es-CO');
    } else if(d.estado==='Pagada'){
      msg = '✓ Pago completo registrado.';
    }
    // Si se generó comprobante, ofrecer descarga
    if(d.comprobante && d.comprobante.numero_ce){
      var ce = d.comprobante;
      msg += '\\n\\nComprobante: '+ce.numero_ce;
      msg += '\\nSubtotal: $'+(ce.subtotal||0).toLocaleString('es-CO');
      if(ce.iva > 0) msg += '\\nIVA: $'+ce.iva.toLocaleString('es-CO');
      if(ce.retefuente > 0) msg += '\\nReteFuente: -$'+ce.retefuente.toLocaleString('es-CO');
      if(ce.retica > 0) msg += '\\nReteICA: -$'+ce.retica.toLocaleString('es-CO');
      msg += '\\nTotal pagado: $'+(ce.total_pagado||0).toLocaleString('es-CO');
      if(confirm(msg + '\\n\\n¿Descargar el PDF del comprobante de egreso?')){
        window.open('/api/comprobantes-pago/'+ce.comprobante_id+'/pdf', '_blank');
      }
    } else if(msg){
      alert(msg);
    }
    closeModal('m-pago');
    // Reset image + toggles
    document.getElementById('pago-img-file').value='';
    document.getElementById('pago-img-preview').style.display='none';
    var rf=document.getElementById('pago-aplicar-retefuente'); if(rf) rf.checked=false;
    var ri=document.getElementById('pago-aplicar-retica'); if(ri) ri.checked=false;
    var iv=document.getElementById('pago-aplicar-iva'); if(iv) iv.checked=false;
    await loadData();
    renderDash();
    if(PAGOS.length) loadPagos();
    // refrescar vista agrupada si está activa (pagar desde ahí · 18-jun)
    if(typeof loadConsolidado==='function'){ try{ await loadConsolidado(); }catch(e){} }
  }catch(e){ alert('Error: '+e); }
}

// ─── Recibir · Fase 3 · 21-may-2026 · modal completo INVIMA ────────
async function marcarRecibida(num){
  // Abrir modal con items + campos COA/lote_proveedor (mig 151)
  // Antes era un confirm() simple · ahora cumple GMP cosmético.
  var ex = document.getElementById('m-recepcion'); if(ex) ex.remove();
  var m = document.createElement('div');
  m.id = 'm-recepcion';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
  m.innerHTML = '<div style="background:#fff;border-radius:14px;padding:24px;max-width:920px;width:100%;max-height:90vh;overflow-y:auto">'+
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">'+
      '<h3 style="margin:0;color:#0e7490">📦 Recibir OC '+esc(num)+'</h3>'+
      '<button id="rec-close" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>'+
    '<div style="background:#fef3c7;color:#78350f;padding:10px 14px;border-radius:6px;margin-bottom:14px;font-size:12px"><b>⚠ INVIMA:</b> ingresá lote del proveedor + link al COA · queda en audit · dossier auditoría se arma solo.</div>'+
    '<div id="rec-items" style="text-align:center;color:#94a3b8;padding:14px">Cargando items…</div>'+
    '<div style="margin-top:14px;display:flex;gap:8px;justify-content:flex-end">'+
      '<button id="rec-cancel" style="background:#94a3b8;color:#fff;padding:8px 18px;border:none;border-radius:6px;cursor:pointer">Cancelar</button>'+
      '<button id="rec-confirm" style="background:#16a34a;color:#fff;padding:8px 22px;border:none;border-radius:6px;font-weight:700;cursor:pointer">✓ Confirmar recepción</button>'+
    '</div></div>';
  document.body.appendChild(m);
  document.getElementById('rec-close').onclick = function(){ m.remove(); };
  document.getElementById('rec-cancel').onclick = function(){ m.remove(); };
  m.addEventListener('click', function(e){ if(e.target === m) m.remove(); });
  try{
    var r = await fetch('/api/ordenes-compra/'+encodeURIComponent(num));
    var d = await r.json();
    if(!r.ok){ document.getElementById('rec-items').innerHTML = '<div style="color:#dc2626">Error: '+(d.error||r.status)+'</div>'; return; }
    var items = d.items || d.ordenes_compra_items || [];
    if(!items.length){
      document.getElementById('rec-items').innerHTML = '<div style="color:#64748b;padding:14px">Esta OC no tiene items</div>';
      return;
    }
    var html = '<div style="display:flex;flex-direction:column;gap:14px">';
    items.forEach(function(it, idx){
      html += '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px" data-rec-idx="'+idx+'" data-codigo="'+esc(it.codigo_mp||'')+'">'+
        '<div style="font-weight:700;color:#0f172a;margin-bottom:6px">'+esc(it.nombre_mp||it.codigo_mp||'item '+idx)+' <span style="font-size:11px;color:#94a3b8">'+esc(it.codigo_mp||'')+'</span></div>'+
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px">'+
          '<div><label style="font-size:11px;color:#64748b;font-weight:600">Cantidad recibida (g)</label><input type="number" step="any" class="rec-cant" data-idx="'+idx+'" value="'+(it.cantidad_g||0)+'" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:5px;font-size:13px"></div>'+
          '<div><label style="font-size:11px;color:#64748b;font-weight:600">Lote interno</label><input type="text" class="rec-lote" data-idx="'+idx+'" placeholder="auto si vacío" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:5px;font-size:13px"></div>'+
          '<div><label style="font-size:11px;color:#7c3aed;font-weight:700">📋 Lote proveedor *</label><input type="text" class="rec-lote-prov" data-idx="'+idx+'" placeholder="según etiqueta proveedor" style="width:100%;padding:6px 8px;border:1px solid #7c3aed;border-radius:5px;font-size:13px"></div>'+
          '<div><label style="font-size:11px;color:#64748b;font-weight:600">Fecha vencimiento</label><input type="date" class="rec-fv" data-idx="'+idx+'" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:5px;font-size:13px"></div>'+
          '<div style="grid-column:span 2"><label style="font-size:11px;color:#dc2626;font-weight:700">📑 Link al COA (Drive/Dropbox) *</label><input type="url" class="rec-coa-url" data-idx="'+idx+'" placeholder="https://drive.google.com/file/..." style="width:100%;padding:6px 8px;border:1px solid #dc2626;border-radius:5px;font-size:13px"></div>'+
          '<div style="grid-column:span 2"><label style="font-size:11px;color:#64748b;font-weight:600">Link ficha seguridad (MSDS · opcional)</label><input type="url" class="rec-ficha" data-idx="'+idx+'" placeholder="https://..." style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:5px;font-size:13px"></div>'+
          '<div style="grid-column:span 2"><label style="font-size:11px;color:#64748b;font-weight:600">Notas / discrepancias</label><input type="text" class="rec-notas" data-idx="'+idx+'" placeholder="opcional" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:5px;font-size:13px"></div>'+
        '</div>'+
      '</div>';
    });
    html += '</div>';
    document.getElementById('rec-items').innerHTML = html;
  }catch(e){
    document.getElementById('rec-items').innerHTML = '<div style="color:#dc2626;padding:14px">Error red: '+esc(e.message)+'</div>';
  }
  document.getElementById('rec-confirm').onclick = async function(){
    var btn = this;
    btn.disabled = true; btn.textContent = 'Procesando...';
    // Recolectar items
    var cards = m.querySelectorAll('[data-rec-idx]');
    var items_rec = [];
    var falta_coa = [];
    var falta_lote_prov = [];
    cards.forEach(function(card, idx){
      var codigo = card.getAttribute('data-codigo');
      var get = function(sel){ var el = card.querySelector(sel); return el ? el.value.trim() : ''; };
      var cant = parseFloat(get('.rec-cant')) || 0;
      if(cant <= 0) return;
      var lote_prov = get('.rec-lote-prov');
      var coa = get('.rec-coa-url');
      if(!lote_prov) falta_lote_prov.push(codigo||idx);
      if(!coa) falta_coa.push(codigo||idx);
      items_rec.push({
        codigo_mp: codigo,
        cantidad_recibida: cant,
        lote: get('.rec-lote'),
        lote_proveedor: lote_prov,
        fecha_vencimiento: get('.rec-fv'),
        coa_url: coa,
        ficha_seguridad_url: get('.rec-ficha'),
        notas: get('.rec-notas'),
        estado: 'OK',
      });
    });
    if(falta_lote_prov.length || falta_coa.length){
      var msg = '⚠ INVIMA · faltan campos obligatorios:';
      if(falta_lote_prov.length) msg += '\\n• Lote proveedor en: '+falta_lote_prov.join(', ');
      if(falta_coa.length) msg += '\\n• Link COA en: '+falta_coa.join(', ');
      msg += '\\n\\n¿Continuar igual? (queda como excepción para auditoría)';
      if(!confirm(msg)){
        btn.disabled = false; btn.textContent = '✓ Confirmar recepción';
        return;
      }
    }
    try{
      var rr = await fetch('/api/ordenes-compra/'+encodeURIComponent(num)+'/recibir',
        _fetchOpts('POST', {items: items_rec, forzar: (falta_lote_prov.length || falta_coa.length) > 0,
          recepcion_id: ((window.crypto && crypto.randomUUID) ? crypto.randomUUID()
                         : ('rcp-'+Date.now()+'-'+Math.random().toString(36).slice(2)))}));
      var dd = await rr.json();
      if(!rr.ok){
        alert('Error: '+(dd.error||rr.status));
        btn.disabled = false; btn.textContent = '✓ Confirmar recepción';
        return;
      }
      var lotes_sint = dd.lotes_sinteticos || [];
      var aviso = 'Recepción OK · '+dd.ingresos+' items · estado: '+dd.estado;
      if(lotes_sint.length) aviso += '\\n\\n⚠ '+lotes_sint.length+' lotes sintéticos · pedir lote real al proveedor';
      alert(aviso);
      m.remove();
      await loadData();
      if(typeof loadConsolidado === 'function') loadConsolidado();
    }catch(e){
      alert('Error red: '+e.message);
      btn.disabled = false; btn.textContent = '✓ Confirmar recepción';
    }
  };
}

// ─── Nuevo proveedor ──────────────────────────────────────────────
async function crearProv(){
  var nom=document.getElementById('np-nom').value.trim();
  if(!nom){ alert('Nombre requerido'); return; }
  var body={nombre:nom,nit:document.getElementById('np-nit').value,
    categoria:document.getElementById('np-cat').value,condiciones_pago:document.getElementById('np-cond').value,
    contacto:document.getElementById('np-ctc').value,telefono:document.getElementById('np-tel').value,
    email:document.getElementById('np-email').value,direccion:document.getElementById('np-dir').value,
    banco:document.getElementById('np-banco').value,tipo_cuenta:document.getElementById('np-tcta').value,
    num_cuenta:document.getElementById('np-ncta').value,concepto_compra:document.getElementById('np-conc').value};
  try{
    var r=await fetch('/api/proveedores-compras',_fetchOpts('POST', body));
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    closeModal('m-nprov');
    await loadData();
    renderProv();
    alert('Proveedor creado: '+nom);
  }catch(e){ alert('Error: '+e); }
}

// Sprint Compras N2 · 21-may-2026 · split SOL mixta en N hijas
async function splitSolicitud(numero){
  if(!numero) return;
  if(!confirm('Dividir SOL '+numero+' en N solicitudes hijas, una por cada proveedor distinto?\\n\\nLa SOL original quedará "Reemplazada" (no se borra · histórico).')) return;
  try{
    var r = await fetch('/api/solicitudes-compra/'+encodeURIComponent(numero)+'/split',
      _fetchOpts('POST', {por_campo: 'proveedor_sugerido'}));
    var d = await r.json();
    if(!r.ok){
      alert('No se puede dividir: '+(d.error||r.status)+(d.proveedor_unico?'\\n\\nProveedor único: '+d.proveedor_unico:''));
      return;
    }
    var lines = ['✓ '+d.mensaje];
    (d.hijas_creadas||[]).forEach(function(h){
      lines.push('• '+h.numero+' → '+h.proveedor+' · '+h.items_count+' MP(s)');
    });
    alert(lines.join('\\n'));
    // MEDIA-8 fix · 21-may-2026 · refrescar también Solicitudes Agrupadas
    // si Catalina hizo split desde esa pestaña (no solo Planta)
    if(typeof loadPlanta==='function') loadPlanta();
    if(typeof renderSolicitudesAgrupadas==='function') renderSolicitudesAgrupadas();
  }catch(e){ alert('Error red: '+e.message); }
}

// ─── Event delegation para botones de OC ────────────────────
document.addEventListener('click',function(e){
  var btn=e.target.closest('[data-act]');
  if(!btn) return;
  var act=btn.getAttribute('data-act');
  var oc=btn.getAttribute('data-oc');
  if(act==='aut') autorizarOC(oc);
  else if(act==='pago') openPago(oc,parseFloat(btn.getAttribute('data-val')||0),btn.getAttribute('data-prov')||'');
  else if(act==='rev') openRev(oc,btn.getAttribute('data-prov')||'',parseFloat(btn.getAttribute('data-val')||0),btn.getAttribute('data-obs')||'');
  else if(act==='rec') marcarRecibida(oc);
  else if(act==='det') openOCDetail(oc);
  else if(act==='sdet') openSolicitudDetail(btn.getAttribute('data-sol')||'');
  else if(act==='del-sol') eliminarSolicitud(btn.getAttribute('data-sol')||'');
  else if(act==='split-sol') splitSolicitud(btn.getAttribute('data-sol')||'');
  else if(act==='edit') editarOC(oc);
  else if(act==='del') eliminarOC(oc);
});

// ─── Globals para modales de detalle (evita escaping de quotes) ───
var _detOC={};  // OC abierta en modal detalle
var _detSol={estado:''}; // Solicitud abierta en modal detalle

// Wrappers sin argumentos para botones de footer (sin riesgo de escaping)
function _ocDetClose(){ closeModal('m-oc-det'); }
function _ocDetAut(){ closeModal('m-oc-det'); autorizarOC(_detOC.numero_oc||''); }
function _ocDetPago(){ closeModal('m-oc-det'); openPago(_detOC.numero_oc||'',parseFloat(_detOC.valor_total||0),_detOC.proveedor||''); }
function _ocDetRev(){ closeModal('m-oc-det'); openRev(_detOC.numero_oc||'',_detOC.proveedor||'',parseFloat(_detOC.valor_total||0),(_detOC.observaciones||'').substring(0,80),_detOC.con_iva,parseFloat(_detOC.valor_sin_iva||0)); }
function _solDetClose(){ closeModal('m-sol-det'); }

// ─── Editar proveedor de UNA MP del catálogo (per-item en solicitud) ─────────
// Event delegation para evitar problemas de escape de quotes en el HTML render.
// Se hookea una sola vez en DOMContentLoaded — captura clicks en cualquier
// boton .btn-edit-prov-mp de la tabla items.
var _epmActual = null;
document.addEventListener('click', function(e){
  var btn = e.target.closest && e.target.closest('.btn-edit-prov-mp');
  if (!btn) return;
  var td = btn.closest('.td-prov');
  if (!td) return;
  var cod = td.getAttribute('data-cod') || '';
  var nom = td.getAttribute('data-nom') || '';
  var prov = td.getAttribute('data-prov') || '';
  abrirEditarProvItem(cod, nom, prov);
});

function abrirEditarProvItem(cod, nom, provActual){
  if(!cod){alert('Codigo MP requerido'); return;}
  _epmActual = {cod: cod, nom: nom||'', provActual: provActual||''};
  document.getElementById('epm-info').textContent = (nom||'(sin nombre)') + ' · ' + cod;
  document.getElementById('epm-prov-actual').textContent = 'Proveedor actual: ' + (provActual || '(vacio)');
  document.getElementById('epm-input').value = provActual || '';
  document.getElementById('epm-msg').innerHTML = '';
  // Asegurar prov-dl populated (PROVS variable global)
  try {
    var dl = document.getElementById('prov-dl');
    if (dl && typeof PROVS !== 'undefined' && (!dl.children || dl.children.length === 0)) {
      dl.innerHTML = PROVS.map(function(p){
        return '<option value="'+esc(p.nombre)+'">';
      }).join('');
    }
  } catch(e) {}
  openModal('m-edit-prov-mp');
  setTimeout(function(){var el=document.getElementById('epm-input');if(el)el.focus();},120);
}

async function guardarProvItemMP(){
  if(!_epmActual)return;
  var msg = document.getElementById('epm-msg');
  var nuevo = (document.getElementById('epm-input').value || '').trim();
  if (nuevo.length < 2){
    msg.innerHTML = '<span style="color:#dc2626;">Proveedor invalido (min 2 chars).</span>';
    return;
  }
  if (nuevo === (_epmActual.provActual || '')){
    msg.innerHTML = '<span style="color:#64748b;">Sin cambios.</span>';
    return;
  }
  msg.innerHTML = '<span style="color:#64748b;">Guardando...</span>';
  try {
    await _ensureCsrf();  // /api/maestro-mps/ exige X-CSRF-Token (FIX 1-jun-2026)
    var r = await fetch('/api/maestro-mps/' + encodeURIComponent(_epmActual.cod) + '/proveedor', _fetchOpts('PUT', {proveedor: nuevo}));
    var d = await r.json();
    if (r.ok) {
      msg.innerHTML = '<span style="color:#16a34a;font-weight:700;">&#10003; ' + (d.message || 'Proveedor actualizado') + '</span>';
      // Actualiza la celda + atributo data-prov para futuras ediciones
      try {
        var celda = document.querySelector('.td-prov[data-cod="'+_epmActual.cod+'"]');
        if (celda) {
          celda.setAttribute('data-prov', nuevo);
          var span = celda.firstChild;
          if (span && span.nodeType === Node.TEXT_NODE) {
            celda.removeChild(span);
          } else if (celda.firstElementChild && celda.firstElementChild.tagName === 'SPAN') {
            celda.removeChild(celda.firstElementChild);
          }
          var txt = document.createTextNode(nuevo + ' ');
          celda.insertBefore(txt, celda.firstChild);
        }
      } catch(e){}
      setTimeout(function(){closeModal('m-edit-prov-mp');}, 900);
    } else {
      msg.innerHTML = '<span style="color:#dc2626;">Error: ' + (d.error || r.status) + (d.detail ? ' &mdash; ' + d.detail : '') + '</span>';
    }
  } catch(e) {
    msg.innerHTML = '<span style="color:#dc2626;">Error de red: ' + e.message + '</span>';
  }
}
function _solDetApr(){ gestionarSol('Aprobada'); }
function _solDetRech(){ gestionarSol('Rechazada'); }
function _solFillProv(){
  var v=(document.getElementById('sol-prov-sel')||{value:''}).value;
  var tb=document.getElementById('sol-tercero-box');
  var nb=document.getElementById('sol-nuevo-prov-box');
  if(tb) tb.style.display = v==='__tercero__' ? 'block' : 'none';
  if(nb) nb.style.display = v==='__nuevo__' ? 'block' : 'none';
  if(v!=='__tercero__'&&v!=='__nuevo__') fillProv('sol-prov-sel','sol-prov-ibox');
}
async function _guardarNuevoProv(){
  var nombre=(document.getElementById('snp-nombre')||{value:''}).value.trim();
  if(!nombre){ alert('El nombre del proveedor es obligatorio'); return; }
  var banco=(document.getElementById('snp-banco')||{value:''}).value.trim();
  var tipo=(document.getElementById('snp-tipo')||{value:'Ahorros'}).value;
  var cuenta=(document.getElementById('snp-cuenta')||{value:''}).value.trim();
  var nit=(document.getElementById('snp-nit')||{value:''}).value.trim();
  var body={nombre:nombre,nit:nit,banco:banco,tipo_cuenta:tipo,numero_cuenta:cuenta,categoria:'Cuenta de Cobro',condiciones_pago:'Inmediato'};
  try{
    var r=await fetch('/api/proveedores-compras',_fetchOpts('POST', body));
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    PROVS.push({nombre:nombre,nit:nit,banco:banco,tipo_cuenta:tipo,numero_cuenta:cuenta});
    var sel=document.getElementById('sol-prov-sel');
    var opt=document.createElement('option');
    opt.value=nombre; opt.textContent=nombre; opt.selected=true;
    var nuevoOpt=sel.querySelector('option[value="__nuevo__"]');
    if(nuevoOpt) sel.insertBefore(opt, nuevoOpt); else sel.appendChild(opt);
    var nb=document.getElementById('sol-nuevo-prov-box');
    if(nb) nb.style.display='none';
    fillProv('sol-prov-sel','sol-prov-ibox');
    alert('Proveedor guardado y seleccionado.');
  }catch(e){ alert('Error: '+e); }
}

// ─── Confirmar / Cambiar proveedor desde el detalle de SOL ──────
// El user pidió: en lugar del bloque de abajo "Gestionar Solicitud", poner
// arriba la opción de Confirmar (sigue igual el proveedor) o Cambiar.
// Cuando confirma o cambia, alimenta el catálogo de proveedores y la OC.
async function confirmarProveedorOC(numOC){
  var btn = document.getElementById('btn-confirmar-prov');
  var nameEl = document.getElementById('prov-card-name');
  if (!nameEl) return;
  var prov = nameEl.textContent.trim();
  if (!prov) { alert('No hay proveedor para confirmar'); return; }
  if (btn) { btn.disabled = true; btn.textContent = 'Confirmando...'; }
  try {
    var r = await fetch('/api/ordenes-compra/'+encodeURIComponent(numOC)+'/proveedor', _fetchOpts('PATCH', {proveedor: prov}));
    var d = await r.json();
    if (!d.ok) { alert('Error: '+(d.error||'no se pudo confirmar')); return; }
    if (btn) {
      btn.style.background = '#065f46';
      btn.textContent = '✓ Confirmado';
      setTimeout(function(){ if(btn) btn.disabled = false; }, 1500);
    }
  } catch (e) {
    alert('Error de red: '+e.message);
    if (btn) { btn.disabled = false; btn.textContent = '✓ Confirmar'; }
  }
}

function abrirCambiarProveedor(){
  var box = document.getElementById('prov-cambiar-box');
  if (!box) return;
  box.style.display = box.style.display === 'none' ? 'block' : 'none';
  if (box.style.display === 'block') {
    var input = document.getElementById('prov-cambiar-input');
    if (input) {
      // Pre-poblar con el proveedor actual para que el user solo edite
      var cur = document.getElementById('prov-card-name');
      if (cur && !input.value) input.value = cur.textContent.trim();
      input.focus();
      input.select();
    }
  }
}

async function guardarCambioProveedor(numOC){
  var input = document.getElementById('prov-cambiar-input');
  if (!input) return;
  var nuevo = (input.value||'').trim();
  if (!nuevo) { alert('Ingresá un nombre de proveedor'); return; }
  try {
    var r = await fetch('/api/ordenes-compra/'+encodeURIComponent(numOC)+'/proveedor', _fetchOpts('PATCH', {proveedor: nuevo}));
    var d = await r.json();
    if (!d.ok) { alert('Error: '+(d.error||'no se pudo cambiar')); return; }
    // Update UI: nombre nuevo + ocultar selector + recargar lista de provs
    var nameEl = document.getElementById('prov-card-name');
    if (nameEl) nameEl.textContent = nuevo;
    var box = document.getElementById('prov-cambiar-box');
    if (box) box.style.display = 'none';
    if (d.creado_en_catalogo) {
      alert('Proveedor cambiado a "'+nuevo+'" — agregado al catálogo para próximos pedidos.');
      // Recargar proveedores en cache global
      try { await loadData(); } catch(e){}
    } else {
      // No alert if just confirmed existing — silent success
    }
  } catch (e) {
    alert('Error de red: '+e.message);
  }
}

// ─── Guardar TODO (cantidad + proveedor + precio) por SOL ─────────────
// Catalina puede editar A PEDIR, PROVEEDOR y PRECIO. Al guardar se persiste:
//   1. solicitudes_compra_items (cantidad, precio_unit_g, proveedor_sugerido)
//   2. maestro_mps.proveedor (normalizado para futuras compras)
//   3. precio_historico_mp (memoria de precios -> alertas de aumento)
async function guardarPreciosItems(numOC, solNumero){
  var rows = document.querySelectorAll('#sol-items-table tbody tr[data-itemid]');
  if (!rows.length) { alert('No hay items para actualizar'); return; }
  var btn = document.getElementById('btn-guardar-precios');
  if (btn) { btn.disabled = true; btn.textContent = 'Guardando...'; }
  var items = [];
  rows.forEach(function(tr){
    var iid = tr.getAttribute('data-itemid');
    var inpPrecio = tr.querySelector('input.precio-unit');
    var inpCant = tr.querySelector('input.cant-edit');
    var inpProv = tr.querySelector('input.prov-edit');
    if (!iid) return;
    var precio = inpPrecio ? parseFloat((inpPrecio.value||'').replace(/[^\\d.]/g,'')) : 0;
    var cantidad = inpCant ? parseFloat((inpCant.value||'').replace(/[^\\d.]/g,'')) : null;
    var prov = inpProv ? (inpProv.value||'').trim() : null;
    var item = {id: parseInt(iid)};
    if (isFinite(precio) && precio > 0) item.precio_unit_g = precio;
    if (cantidad != null && isFinite(cantidad) && cantidad > 0) item.cantidad_g = cantidad;
    if (prov != null) item.proveedor = prov;
    items.push(item);
  });
  if (!items.length || !solNumero) {
    alert('Nada que guardar — ¿faltan datos?');
    if (btn) { btn.disabled = false; btn.textContent = '💾 Guardar cambios'; }
    return;
  }
  try {
    // Endpoint nuevo: PATCH /api/solicitudes-compra/<numero>/items
    // Persiste cantidad/proveedor/precio + actualiza maestro_mps + alimenta historico
    var r = await fetch('/api/solicitudes-compra/'+encodeURIComponent(solNumero)+'/items', _fetchOpts('PATCH', {items: items}));
    var d = await r.json();
    if (!d.ok) { alert('Error: '+(d.error||'no se pudo guardar')); }
    else {
      var totalEl = document.getElementById('sol-valor-total');
      if (totalEl && d.valor_total != null) totalEl.textContent = fmt(d.valor_total);
      // Feedback visual con resumen de cambios
      var msg = '✓ '+d.items_actualizados+' items';
      if (d.maestro_mps_actualizados>0) msg += ' · '+d.maestro_mps_actualizados+' provs';
      if (d.precios_historicos_insertados>0) msg += ' · '+d.precios_historicos_insertados+' precios al hist.';
      if (btn) { btn.style.background = '#065f46'; btn.textContent = msg; }
      setTimeout(function(){
        if (btn) { btn.disabled = false; btn.style.background = '#0f766e'; btn.textContent = '💾 Guardar cambios'; }
      }, 2500);
    }
  } catch (e) {
    alert('Error de red: '+e.message);
    if (btn) { btn.disabled = false; btn.textContent = '💾 Guardar cambios'; }
  }
}

// Recalcula valor estimado en la celda VALOR EST. al editar precio o cantidad
function recalcularValorEst(input){
  try {
    var tr = input.closest('tr');
    if (!tr) return;
    var cant = parseFloat((tr.querySelector('input.cant-edit')||{}).value||0);
    var precio = parseFloat((tr.querySelector('input.precio-unit')||{}).value||0);
    var celdaValor = tr.querySelector('.td-valor-est');
    if (!celdaValor) return;
    if (cant > 0 && precio > 0) {
      var v = Math.round(cant * precio);
      celdaValor.innerHTML = '<strong style="color:#1F5F5B;">$'+v.toLocaleString('es-CO')+'</strong>';
    } else {
      celdaValor.innerHTML = '<span style="color:#a8a29e;font-size:11px;">—</span>';
    }
  } catch(e) {}
}

// Modal de histórico de precios para una MP
async function verHistoricoPrecio(codigoMp){
  if (!codigoMp) return;
  try {
    var r = await fetch('/api/precio-historico/'+encodeURIComponent(codigoMp));
    var d = await r.json();
    var serie = d.serie || [];
    var stats = d.stats || {};
    var alertaColor = {
      'estable':'#15803d','subiendo':'#f59e0b','subiendo_fuerte':'#dc2626',
      'bajando':'#15803d','volatil':'#a16207','sin_datos':'#78716c'
    };
    var color = alertaColor[stats.alerta] || '#6d28d9';
    var modalId = 'cx-hist-' + Date.now();
    var html = '<div id="'+modalId+'" style="position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px;" onclick="if(event.target===this)document.getElementById(&quot;'+modalId+'&quot;).remove()">';
    html += '<div style="background:#fff;border-radius:12px;max-width:720px;width:100%;max-height:85vh;overflow-y:auto;padding:24px;">';
    html += '<div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:16px;">';
    html += '<div><div style="font-size:11px;color:#78716c;text-transform:uppercase;letter-spacing:.5px;">Histórico de precios</div>';
    html += '<div style="font-size:18px;font-weight:700;color:#1c1917;font-family:monospace;">'+esc(d.codigo_mp)+'</div>';
    html += '<div style="font-size:13px;color:#57534e;">'+esc(d.nombre_mp||'')+'</div></div>';
    html += '<button onclick="document.getElementById(&quot;'+modalId+'&quot;).remove()" style="background:transparent;border:none;font-size:22px;cursor:pointer;color:#78716c;">×</button>';
    html += '</div>';
    if (!serie.length) {
      html += '<div style="text-align:center;padding:40px;color:#78716c;">Sin histórico aún. Cuando guardes precios en SOLs/OCs irán quedando aquí.</div>';
    } else {
      // Stats
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:16px;">';
      html += '<div style="background:#fafaf9;border-radius:8px;padding:10px;"><div style="font-size:10px;color:#78716c;text-transform:uppercase;">Último precio</div><div style="font-size:18px;font-weight:800;">$'+(stats.ultimo_precio||0).toLocaleString('es-CO')+'/g</div></div>';
      html += '<div style="background:#fafaf9;border-radius:8px;padding:10px;"><div style="font-size:10px;color:#78716c;text-transform:uppercase;">Variación</div><div style="font-size:18px;font-weight:800;color:'+color+';">'+(stats.variacion_pct>=0?'+':'')+(stats.variacion_pct||0)+'%</div></div>';
      html += '<div style="background:#fafaf9;border-radius:8px;padding:10px;"><div style="font-size:10px;color:#78716c;text-transform:uppercase;">Promedio 90d</div><div style="font-size:18px;font-weight:800;">$'+(stats.promedio_90d||0).toLocaleString('es-CO')+'</div></div>';
      html += '<div style="background:#fafaf9;border-radius:8px;padding:10px;"><div style="font-size:10px;color:#78716c;text-transform:uppercase;">Proveedores</div><div style="font-size:18px;font-weight:800;">'+(stats.n_proveedores_distintos||0)+'</div></div>';
      html += '</div>';
      if (stats.alerta_msg) {
        html += '<div style="background:'+color+'1a;border-left:4px solid '+color+';padding:10px 14px;border-radius:0 6px 6px 0;margin-bottom:14px;color:'+color+';font-size:13px;font-weight:600;">'+esc(stats.alerta_msg)+'</div>';
      }
      // Tabla
      html += '<table style="width:100%;border-collapse:collapse;font-size:12px;">';
      html += '<thead style="background:#f5f3ff;color:#4c1d95;"><tr>';
      html += '<th style="text-align:left;padding:8px 10px;font-size:10px;text-transform:uppercase;letter-spacing:.5px;">Fecha</th>';
      html += '<th style="text-align:left;padding:8px 10px;font-size:10px;text-transform:uppercase;letter-spacing:.5px;">Proveedor</th>';
      html += '<th style="text-align:right;padding:8px 10px;font-size:10px;text-transform:uppercase;letter-spacing:.5px;">Precio/g</th>';
      html += '<th style="text-align:left;padding:8px 10px;font-size:10px;text-transform:uppercase;letter-spacing:.5px;">Origen</th>';
      html += '</tr></thead><tbody>';
      serie.slice(0,40).forEach(function(s){
        html += '<tr style="border-top:1px solid #f5f5f4;">';
        html += '<td style="padding:7px 10px;font-family:monospace;font-size:11px;">'+esc((s.fecha||'').substring(0,10))+'</td>';
        html += '<td style="padding:7px 10px;">'+esc(s.proveedor||'-')+'</td>';
        html += '<td style="padding:7px 10px;text-align:right;font-weight:700;">$'+(s.precio_unit_g||0).toLocaleString('es-CO')+'</td>';
        html += '<td style="padding:7px 10px;font-size:10px;color:#78716c;">'+esc(s.fuente||'')+(s.sol_numero?' '+esc(s.sol_numero):'')+(s.oc_numero?' '+esc(s.oc_numero):'')+'</td>';
        html += '</tr>';
      });
      html += '</tbody></table>';
    }
    html += '</div></div>';
    var box = document.createElement('div');
    box.innerHTML = html;
    document.body.appendChild(box.firstElementChild);
  } catch(e){ alert('Error cargando histórico: '+e.message); }
}

// ─── Detalle OC ─────────────────────────────────────────────────
async function openOCDetail(num){
  openModal('m-oc-det');
  var body=document.getElementById('oc-det-body');
  var footer=document.getElementById('oc-det-footer');
  body.innerHTML='<div style="text-align:center;padding:40px;color:#78716c;">Cargando...</div>';
  footer.innerHTML='<button class="btn bo" onclick="_ocDetClose()">Cerrar</button>';
  _detOC={};
  try{
    var r=await fetch('/api/ordenes-compra/'+encodeURIComponent(num));
    var d=await r.json();
    if(d.error){ body.innerHTML='<p style="color:#dc2626;">'+esc(d.error)+'</p>'; return; }
    var o=d.oc||{}; _detOC=o;
    var items=d.items||[];
    var estColor={'Borrador':'#78716c','Revisada':'#d97706','Autorizada':'#2563eb','Pagada':'#16a34a','Recibida':'#14532d','Rechazada':'#dc2626'}[o.estado]||'#78716c';
    var h='<div style="padding:16px 20px;">';
    h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">';
    h+='<div><div style="font-weight:800;font-size:16px;font-family:monospace;">'+esc(o.numero_oc||num)+'</div>';
    h+='<div style="color:#57534e;font-size:13px;">'+esc(o.proveedor||'-')+'</div></div>';
    h+='<span class="badge" style="background:'+estColor+'22;color:'+estColor+';font-size:12px;">'+esc(o.estado||'')+'</span></div>';
    h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;margin-bottom:12px;background:#f9f8f7;border-radius:6px;padding:10px;">';
    h+='<div><span style="color:#78716c;">Fecha:</span> '+fdate(o.fecha)+'</div>';
    h+='<div><span style="color:#78716c;">Entrega est.:</span> '+(o.fecha_entrega_est?fdate(o.fecha_entrega_est):'-')+'</div>';
    h+='<div><span style="color:#78716c;">Creado por:</span> '+esc(o.creado_por||'-')+'</div>';
    h+='<div><span style="color:#78716c;">Autorizado por:</span> '+esc(o.autorizado_por||'-')+'</div>';
    if(o.valor_total){
      var ivaTxt='';
      if(o.con_iva && o.valor_sin_iva>0){
        var ivaAmt=Math.round(o.valor_sin_iva*0.19);
        ivaTxt=' <span style="font-size:11px;background:#fde047;color:#92400e;border-radius:3px;padding:1px 6px;margin-left:4px;">+IVA incl.</span>'
          +'<div style="color:#78716c;font-size:11px;margin-top:2px;">Subtotal: '+fmt(o.valor_sin_iva)+' &nbsp;|&nbsp; IVA 19%: '+fmt(ivaAmt)+'</div>';
      }
      h+='<div style="grid-column:span 2;"><span style="color:#78716c;">Valor total:</span> <strong style="font-size:15px;">'+fmt(o.valor_total)+'</strong>'+ivaTxt+'</div>';
    }
    if(o.observaciones) h+='<div style="grid-column:span 2;"><span style="color:#78716c;">Observaciones:</span> '+esc(o.observaciones)+'</div>';
    h+='</div>';
    if(items.length){
      h+='<div style="font-weight:700;font-size:12px;color:#44403c;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">Items del pedido</div>';
      h+='<div style="overflow-x:auto;"><table class="itbl"><thead><tr><th>Codigo</th><th>Descripcion</th><th>Cantidad</th><th style="text-align:right;">Precio U.</th><th style="text-align:right;">Subtotal</th></tr></thead><tbody>';
      items.forEach(function(it){
        var cant=it[3]||it.cantidad_g||0;
        var pu=it[4]||it.precio_unitario||0;
        var sub=it[5]||it.subtotal||0;
        var nom=it[2]||it.nombre_mp||'';
        var cod=it[1]||it.codigo_mp||'';
        h+='<tr><td style="font-family:monospace;font-size:11px;">'+esc(cod)+'</td><td>'+esc(nom)+'</td>';
        h+='<td>'+Number(cant).toLocaleString('es-CO')+'</td>';
        h+='<td style="text-align:right;">'+(pu?fmt(pu):'-')+'</td>';
        h+='<td style="text-align:right;font-weight:700;">'+(sub?fmt(sub):'-')+'</td></tr>';
      });
      h+='</tbody></table></div>';
    } else { h+='<div style="color:#78716c;font-size:13px;">Sin items registrados</div>'; }
    // ── Datos de Pago ──
    var _pd=d.prov_data||null;
    if(!_pd&&o.proveedor){
      var _pf=PROVS.find(function(x){ return x.nombre===o.proveedor; });
      if(_pf) _pd={banco:_pf.banco,tipo_cuenta:_pf.tipo_cuenta,num_cuenta:_pf.num_cuenta,nit:_pf.nit,email:_pf.email,telefono:_pf.telefono};
    }
    // Fallback: parse observaciones for CC orders with inline banking data
    if(!_pd&&o.observaciones&&o.observaciones.indexOf('BANCO:')>=0){
      var _ob=o.observaciones;
      function _xob(key){
        var idx=_ob.indexOf(key+':'); if(idx<0) return '';
        var rest=_ob.slice(idx+key.length+1).trim();
        var end=rest.indexOf(' | '); return end>=0?rest.slice(0,end).trim():rest.trim();
      }
      var _bancoRaw=_xob('BANCO');
      if(_bancoRaw){
        var _bparts=_bancoRaw.split(' ');
        _pd={banco:_bparts[0]||_bancoRaw,tipo_cuenta:_bparts.slice(1).join(' ')||'',
          num_cuenta:_xob('CUENTA/CEL'),nit:_xob('CED/NIT')};
      }
    }
    if(_pd&&(_pd.banco||_pd.num_cuenta)){
      h+='<div style="margin-top:14px;background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:12px;">';
      h+='<div style="font-weight:800;font-size:12px;color:#166534;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">&#x1F4B3; Datos de Pago</div>';
      h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;font-size:12px;">';
      if(_pd.banco) h+='<div><span style="color:#166534;font-weight:600;">Banco:</span> <strong>'+esc(_pd.banco)+'</strong></div>';
      if(_pd.tipo_cuenta) h+='<div><span style="color:#166534;font-weight:600;">Tipo cuenta:</span> '+esc(_pd.tipo_cuenta)+'</div>';
      if(_pd.num_cuenta) h+='<div style="grid-column:span 2;"><span style="color:#166534;font-weight:600;">N\u00BA cuenta:</span> <strong style="font-family:monospace;font-size:13px;letter-spacing:.5px;">'+esc(_pd.num_cuenta)+'</strong></div>';
      if(_pd.nit) h+='<div><span style="color:#166534;font-weight:600;">NIT / CC:</span> '+esc(_pd.nit)+'</div>';
      if(_pd.email) h+='<div><span style="color:#166534;font-weight:600;">Email:</span> '+esc(_pd.email)+'</div>';
      if(_pd.telefono) h+='<div><span style="color:#166534;font-weight:600;">Tel:</span> '+esc(_pd.telefono)+'</div>';
      h+='</div>';
      if(o.valor_total){
        h+='<div style="margin-top:10px;padding-top:8px;border-top:1px solid #bbf7d0;">';
        if(o.con_iva&&o.valor_sin_iva>0){
          var _iva=Math.round(o.valor_sin_iva*0.19);
          h+='<div style="font-size:11px;color:#166534;">Subtotal: '+fmt(o.valor_sin_iva)+'</div>';
          h+='<div style="font-size:11px;color:#166534;">IVA 19%: '+fmt(_iva)+'</div>';
        }
        h+='<div style="font-size:15px;font-weight:800;color:#15803d;margin-top:3px;">Total a pagar: '+fmt(o.valor_total)+'</div>';
      }
      h+='</div>';
    }
    h+='</div>';
    body.innerHTML=h;
    var fbtns='<button class="btn bo" onclick="_ocDetClose()">Cerrar</button>';
    if((o.estado==='Revisada'||o.estado==='Borrador')&&ES_AUTORIZA) fbtns+='<button class="btn bi" onclick="_ocDetAut()">Autorizar / Rechazar</button>';
    if(o.estado==='Autorizada'&&ES_AUTORIZA) fbtns+='<button class="btn bg" onclick="_ocDetPago()">Registrar Pago</button>';
    if(o.estado==='Borrador'&&ES_C) fbtns+='<button class="btn bw" onclick="_ocDetRev()">Revisar &amp; Asignar</button>';
    footer.innerHTML=fbtns;
  }catch(e){ body.innerHTML='<p style="color:#dc2626;">Error: '+e.message+'</p>'; }
}

// ─── Solicitudes para Catalina ────────────────────────────────────────
var SOLIC=[];
var INFLUENCERS=[];
var CC_SOLIC=[];
var _SOLIC_CAT_FILTER='ALL';
function descargarSolicitudesPDF(){
  // Filtra por el estado seleccionado en el dropdown si lo hay; si no, baja
  // Pendientes+Aprobadas (lo más útil para que Gerencia revise lo que falta).
  var estados = (document.getElementById('s-solic')||{value:''}).value;
  var qs = estados ? '?estados='+encodeURIComponent(estados) : '?estados=Pendiente,Aprobada';
  window.open('/api/compras/solicitudes/pdf'+qs, '_blank');
}

// ────────────────────────────────────────────────────────────────
// Sebastian 4-may-2026 (Catalina): consolidar AUTO-XXXX legacy
// ────────────────────────────────────────────────────────────────
// Ejecuta /api/compras/consolidar-auto-pendientes en 2 pasos:
//   1. dry_run=true para mostrar el plan a Catalina
//   2. confirm + dry_run=false para ejecutar
async function consolidarAutoPendientes(){
  // Step 1: dry-run
  try{
    var rDry = await fetch('/api/compras/consolidar-auto-pendientes',
      _fetchOpts('POST', {dry_run: true}));
    var dDry = await rDry.json();
    if(!rDry.ok){
      alert('Error preview: '+(dDry.error || rDry.status));
      return;
    }
    if(dDry.antes === 0){
      alert('✓ No hay AUTO-XXXX pendientes para consolidar.');
      return;
    }
    if(!dDry.grupos || !dDry.grupos.length){
      alert('Nada que consolidar — '+dDry.intactas+' AUTO-XXXX ya estan agrupadas.');
      return;
    }
    var detalle = dDry.grupos.slice(0,8).map(function(g){
      return '  · '+g.proveedor_label+' ('+g.categoria+'): '+
             g.sols_origen.length+' SOLs → '+g.items_count+' MPs · '+
             fmt(g.total_g)+' g';
    }).join('\\n');
    if(dDry.grupos.length > 8) detalle += '\\n  ... y '+(dDry.grupos.length-8)+' grupos mas';
    var msg = 'CONSOLIDAR AUTO-XXXX pendientes\\n\\n'+
      'Antes: '+dDry.antes+' solicitudes (1 MP cada una)\\n'+
      'Despues: '+dDry.despues+' solicitudes (agrupadas por proveedor)\\n'+
      'Intactas (ya consolidadas): '+dDry.intactas+'\\n\\n'+
      'Plan:\\n'+detalle+'\\n\\n'+
      'Las solicitudes legacy se reemplazan por las consolidadas. '+
      'No se borran datos: los items se trasladan tal cual.\\n\\n'+
      'Confirmar?';
    if(!confirm(msg)) return;

    // Step 2: ejecutar
    var btn = document.getElementById('btn-consolidar-auto');
    if(btn){ btn.disabled = true; btn.textContent = 'Consolidando...'; }
    var r = await fetch('/api/compras/consolidar-auto-pendientes',
      _fetchOpts('POST', {dry_run: false}));
    var d = await r.json();
    if(btn){ btn.disabled = false; btn.innerHTML = '&#x1F517; Consolidar AUTO'; }
    if(!r.ok){
      alert('Error: '+(d.error || r.status));
      return;
    }
    alert('✓ '+d.mensaje+'\\n\\n'+
          'Eliminadas: '+d.eliminadas+'\\n'+
          'Creadas: '+d.creadas+'\\n'+
          'Total ahora: '+d.despues+' solicitudes');
    // Refrescar
    await loadSolicitudes();
    if(_VISTA_AGRUPADA) await renderSolicitudesAgrupadas();
  }catch(e){
    alert('Error red: '+e.message);
    var btn = document.getElementById('btn-consolidar-auto');
    if(btn){ btn.disabled = false; btn.innerHTML = '&#x1F517; Consolidar AUTO'; }
  }
}

// ────────────────────────────────────────────────────────────────
// Sebastian 4-may-2026 (Catalina): SOLO limpiar AUTO-XXXX
// Deja que el cron de planta regenere agrupado en la proxima corrida.
// Util cuando Catalina quiere "borron y cuenta nueva" sin disparar
// regeneracion inmediata.
// ────────────────────────────────────────────────────────────────
async function soloLimpiarAuto(){
  try{
    var rDry = await fetch('/api/compras/limpiar-y-regenerar-auto-plan',
      _fetchOpts('POST', {dry_run: true, regenerar: false}));
    var dDry = await rDry.json();
    if(!rDry.ok){
      alert('Error preview: '+(dDry.error || rDry.status));
      return;
    }
    if(dDry.eliminaria === 0){
      alert('✓ No hay solicitudes auto-generadas Pendientes que limpiar.');
      return;
    }
    var msg = 'LIMPIAR SOLICITUDES AUTO-GENERADAS (sin regenerar)\\n\\n'+
      'Va a BORRAR:\\n'+
      '  • '+dDry.eliminaria+' solicitudes auto-generadas Pendientes\\n'+
      '    (AUTO-XXXX del cron + SOL-YYYY-XXXX de Regenerar)\\n'+
      '  • '+(dDry.eliminaria_ocs_borrador||0)+' OCs en Borrador asociadas\\n\\n'+
      'NO toca las que tienen OC Autorizada/Pagada (eso es historico).\\n\\n'+
      'Cuando el cron de planta corra (o uses Regenerar manual), las\\n'+
      'nuevas solicitudes vendran agrupadas por proveedor con la\\n'+
      'logica corregida (COALESCE a maestro_mps + nombres normalizados).\\n\\n'+
      'Confirmar?';
    if(!confirm(msg)) return;

    var btn = document.getElementById('btn-solo-limpiar-auto');
    if(btn){ btn.disabled = true; btn.textContent = 'Limpiando...'; }
    var r = await fetch('/api/compras/limpiar-y-regenerar-auto-plan',
      _fetchOpts('POST', {dry_run: false, regenerar: false}));
    var d = await r.json();
    if(btn){ btn.disabled = false; btn.innerHTML = '&#x1F5D1;&#xFE0F; Solo limpiar'; }
    if(!r.ok){
      alert('Error: '+(d.error || r.status));
      return;
    }
    alert('✓ '+d.mensaje);
    await loadSolicitudes();
    if(_VISTA_AGRUPADA) await renderSolicitudesAgrupadas();
  }catch(e){
    alert('Error red: '+e.message);
    var btn = document.getElementById('btn-solo-limpiar-auto');
    if(btn){ btn.disabled = false; btn.innerHTML = '&#x1F5D1;&#xFE0F; Solo limpiar'; }
  }
}

// ────────────────────────────────────────────────────────────────
// Sebastian 4-may-2026 (Catalina): limpiar TODOS los AUTO-XXXX y
// regenerar desde planta con la logica nueva (proveedor real desde
// maestro_mps si mp_lead_time_config esta vacio)
// ────────────────────────────────────────────────────────────────
async function limpiarYRegenerarAutoPlan(){
  // Step 1: dry-run para mostrar cuantos van a borrar
  try{
    var rDry = await fetch('/api/compras/limpiar-y-regenerar-auto-plan',
      _fetchOpts('POST', {dry_run: true, horizonte_dias: 60}));
    var dDry = await rDry.json();
    if(!rDry.ok){
      alert('Error preview: '+(dDry.error || rDry.status));
      return;
    }
    var msg = 'LIMPIAR Y REGENERAR AUTO-PLAN\\n\\n'+
      'Esto va a:\\n'+
      ' • BORRAR '+dDry.eliminaria+' solicitudes AUTO-XXXX Pendientes\\n'+
      ' • REGENERAR desde planta con horizonte '+dDry.horizonte_dias+' dias\\n'+
      ' • Las nuevas leen proveedor de maestro_mps si mp_lead_time_config\\n'+
      '   esta vacio → ya NO aparecen "sin proveedor"\\n'+
      ' • Quedan agrupadas por proveedor (1 SOL × proveedor con N items)\\n\\n'+
      'NO toca AUTO-XXXX que ya tienen OC vinculada (esas son historico).\\n\\n'+
      'Confirmar?';
    if(!confirm(msg)) return;

    // Step 2: ejecutar
    var btn = document.getElementById('btn-limpiar-regenerar-auto');
    if(btn){ btn.disabled = true; btn.textContent = 'Procesando...'; }
    var r = await fetch('/api/compras/limpiar-y-regenerar-auto-plan',
      _fetchOpts('POST', {dry_run: false, horizonte_dias: 60}));
    var d = await r.json();
    if(btn){ btn.disabled = false; btn.innerHTML = '&#x1F525; Limpiar y regenerar'; }
    if(!r.ok){
      alert('Error: '+(d.error || r.status)+
            (d.eliminadas !== undefined ? '\\n(Eliminadas '+d.eliminadas+' antes del fallo)' : ''));
      return;
    }
    var detalle = (d.grupos||[]).slice(0,8).map(function(g){
      return '  · '+(g.proveedor||'(Sin proveedor)')+': '+g.items_count+' MPs · '+fmt(g.total_g)+' g';
    }).join('\\n');
    if((d.grupos||[]).length > 8) detalle += '\\n  ... y '+(d.grupos.length-8)+' grupos mas';
    alert('✓ '+d.mensaje+'\\n\\n'+
          (detalle ? 'Top grupos:\\n'+detalle : ''));
    await loadSolicitudes();
    if(_VISTA_AGRUPADA) await renderSolicitudesAgrupadas();
  }catch(e){
    alert('Error red: '+e.message);
    var btn = document.getElementById('btn-limpiar-regenerar-auto');
    if(btn){ btn.disabled = false; btn.innerHTML = '&#x1F525; Limpiar y regenerar'; }
  }
}

// ────────────────────────────────────────────────────────────────
// Sebastian 4-may-2026 (Catalina): consolidar AUTO-XXXX legacy
// ────────────────────────────────────────────────────────────────
// Ejecuta /api/compras/consolidar-auto-pendientes en 2 pasos:
//   1. dry_run=true para mostrar el plan a Catalina
//   2. confirm + dry_run=false para ejecutar
async function regenerarSolicitudesAuto(){
  if(!confirm('REGENERAR solicitudes auto-generadas?\\n\\n' +
              'Esto va a:\\n' +
              ' • Borrar todas las solicitudes Pendiente que digan "Auto-generada Centro Programación"\\n' +
              ' • Borrar sus OCs Borrador asociadas\\n' +
              ' • Crear nuevas con los déficits ACTUALES de Programación\\n\\n' +
              'NO toca solicitudes Aprobadas ni Pagadas.\\n\\n' +
              '¿Confirmás?')) return;
  try{
    var r = await fetch('/api/programacion/regenerar-oc', _fetchOpts('POST'));
    var d = await r.json();
    if(!r.ok){
      alert('Error: ' + (d.error || 'desconocido') + (d.detalle ? '\\n' + d.detalle : ''));
      return;
    }
    alert(d.mensaje || 'Regeneración completa');
    await loadSolicitudes();
  }catch(e){
    alert('Error de red: ' + e.message);
  }
}

async function loadSolicitudes(){
  // Sebastian 5-may-2026: Tab "Solicitudes" SOLO carga las solicitudes de
  // usuarios (Papelería, Servicios, EPP, Mantenimiento, etc).
  //
  // Las de planta (MP + Empaque) viven en su propio tab "Planta" y las
  // de influencers/marketing en su tab "Influencers". Esto evita que
  // Catalina las confunda y procese mal.
  //
  // El backend interpreta ?fuente=usuarios como "todas las categorias
  // EXCEPTO Materia Prima, Empaque, Material de Empaque, Influencer/
  // Marketing Digital, Cuenta de Cobro".
  try{
    var r=await fetch('/api/solicitudes-compra?fuente=usuarios&_t='+Date.now(),
      {cache:'no-store'});
    var d=await r.json();
    SOLIC=d.solicitudes||[];
  }catch(e){ SOLIC=[]; }
  renderSolicitudes();
}
// Limpiar SOLs influencer/CC NO pagadas — dry-run primero
window.limpiarSolsNoPagadas = async function(){
  try{
    var r = await fetch('/api/compras/influencer/limpiar-no-pagadas', _fetchOpts('POST', {}));  // sin confirm = dry-run
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    if(d.a_borrar === 0){
      alert('✓ Nada que limpiar — no hay SOLs Influencer/Marketing/CC sin pagar.');
      return;
    }
    var lista = d.candidatos.slice(0, 30).map(function(x){
      var nm = x.beneficiario || x.solicitante || '(sin nombre)';
      var v = x.valor>0 ? ' $'+Number(x.valor).toLocaleString('es-CO') : '';
      return '  · '+x.numero+' '+nm+v+' ['+x.estado+']';
    }).join('\\n');
    if(d.a_borrar > 30) lista += '\\n  ... y '+(d.a_borrar-30)+' más';
    var msg = 'Vas a ELIMINAR '+d.a_borrar+' SOLs Influencer/Marketing/CC sin pagar.\\n\\n'+lista;
    if(d.omitidos_por_pagos>0){
      msg += '\\n\\n('+d.omitidos_por_pagos+' omitidas porque tienen pagos efectivos — quedan intactas)';
    }
    msg += '\\n\\n¿Confirmar eliminación PERMANENTE?';
    if(!confirm(msg)) return;
    var r2 = await fetch('/api/compras/influencer/limpiar-no-pagadas', _fetchOpts('POST', {confirm: true}));
    var d2 = await r2.json();
    if(d2.ok){
      alert('✓ Eliminadas '+d2.total_eliminados+' solicitudes. ('+d2.omitidos_por_pagos+' preservadas con pago)');
      loadInfluencers();
    } else {
      alert('Error: '+(d2.error||'?'));
    }
  }catch(e){ alert('Error de red: '+e.message); }
};

// ─── Tab PLANTA · MP + Empaque agrupado por proveedor ─────────────
// Sebastian 5-may-2026: separación de fuentes de SOLs.
//
// Carga /api/compras/solicitudes-agrupadas-por-proveedor?fuente=planta
// que devuelve grupos por proveedor con items consolidados (codigo_mp →
// suma de cantidad_g + valor_estimado).
//
// Cada item se puede editar inline: proveedor (datalist), cantidad_g,
// valor_estimado · al guardar usa PATCH /api/solicitudes-compra/<num>/items
// que sincroniza globalmente:
//   · maestro_mps.proveedor
//   · mp_lead_time_config.proveedor_principal
//   · maestro_mps.precio_referencia
// (lo que aplican en TODA la app: Programación, Calendar, etc.)
var PLANTA_GRUPOS=[];   // grupos[i] = {proveedor, items_consolidados, solicitudes, ...}
var PLANTA_PROVEEDORES_LIST=[];

async function loadPlanta(){
  var estado = (document.getElementById('s-planta-estado')||{value:'Pendiente'}).value;
  document.getElementById('planta-body').innerHTML =
    '<div style="color:#94a3b8;text-align:center;padding:40px;">Cargando...</div>';
  try{
    var r = await fetch('/api/compras/solicitudes-agrupadas-por-proveedor?fuente=planta&estado='
      + encodeURIComponent(estado) + '&_t='+Date.now(), {cache:'no-store'});
    var d = await r.json();
    if(!r.ok){
      document.getElementById('planta-body').innerHTML =
        '<div style="color:#dc2626;padding:20px;">Error: '+esc(d.error||r.status)+'</div>';
      return;
    }
    // CRITICA-1 fix · sin_proveedor son SOLs sueltas con shape distinto a grupos.
    // Antes se concatenaban directo → cards rotos. Ahora se envuelven en
    // grupos sintéticos con items_consolidados + solicitudes para que
    // _plantaCardHTML las renderice igual que un grupo real.
    var _gruposReales = d.grupos || [];
    var _huerfanas = (d.sin_proveedor || []).map(function(s){
      return {
        proveedor: s._motivo_sin_grupo || '(sin proveedor sugerido)',
        es_sin_proveedor: true,
        solicitudes_count: 1,
        items_count: (s.items||[]).length,
        urgencia_max: s.urgencia || 'Normal',
        valor_total: s.valor || 0,
        items_consolidados: s.items || [],
        solicitudes: [s],
      };
    });
    PLANTA_GRUPOS = _gruposReales.concat(_huerfanas);
  }catch(e){
    document.getElementById('planta-body').innerHTML =
      '<div style="color:#dc2626;padding:20px;">Error de red: '+esc(e.message)+'</div>';
    return;
  }
  // Cargar lista de proveedores desde maestro_mps + movimientos (datalist)
  try{
    var rp = await fetch('/api/proveedores-unicos');
    var dp = await rp.json();
    PLANTA_PROVEEDORES_LIST = (dp.proveedores||[]).map(function(p){ return p.nombre || p; });
  }catch(_){ PLANTA_PROVEEDORES_LIST = []; }
  // Sprint Compras N2 · 21-may-2026 · auto-fill precio histórico
  // Prefetch en bulk de todos los códigos visibles · 1 round-trip vs N
  try{
    var codigos = [];
    PLANTA_GRUPOS.forEach(function(g){
      (g.items_consolidados||[]).forEach(function(it){
        if(it.codigo_mp && codigos.indexOf(it.codigo_mp) < 0) codigos.push(it.codigo_mp);
      });
    });
    if(codigos.length){
      var rb = await fetch('/api/compras/sugerir-mp-bulk',
        _fetchOpts('POST', {codigos: codigos}));
      var db = await rb.json();
      window.PLANTA_PRECIOS_HIST = db.datos || {};
    } else {
      window.PLANTA_PRECIOS_HIST = {};
    }
  }catch(_){ window.PLANTA_PRECIOS_HIST = {}; }
  renderPlanta();
}

function renderPlanta(){
  var q = (document.getElementById('q-planta')||{value:''}).value.toLowerCase().trim();
  var body = document.getElementById('planta-body');
  if(!body) return;
  var grupos = PLANTA_GRUPOS;
  if(q){
    grupos = grupos.filter(function(g){
      if((g.proveedor||'').toLowerCase().indexOf(q) >= 0) return true;
      var hits = (g.items_consolidados||[]).some(function(it){
        return ((it.nombre_mp||'')+' '+(it.codigo_mp||'')).toLowerCase().indexOf(q) >= 0;
      });
      if(hits) return true;
      var hits2 = (g.solicitudes||[]).some(function(s){
        return (s.numero||'').toLowerCase().indexOf(q) >= 0;
      });
      return hits2;
    });
  }
  // ALTA-6 fix · 21-may-2026 · KPIs claros (totales reales vs filtrados)
  // + parseFloat guards para evitar NaN propagado por items sin_proveedor.
  var kpis = document.getElementById('planta-kpis');
  if(kpis){
    var totalGrupos = grupos.length;
    var totalSols = 0, totalValor = 0, totalGr = 0;
    grupos.forEach(function(g){
      totalSols += (g.solicitudes||[]).length;
      totalValor += parseFloat(g.valor_total||0) || 0;
      (g.items_consolidados||[]).forEach(function(it){
        totalGr += parseFloat(it.cantidad_g||0) || 0;
      });
    });
    // Totales reales (sin filtro)
    var globalGrupos = (PLANTA_GRUPOS||[]).length;
    var globalSols = 0, globalValor = 0;
    (PLANTA_GRUPOS||[]).forEach(function(g){
      globalSols += (g.solicitudes||[]).length;
      globalValor += parseFloat(g.valor_total||0) || 0;
    });
    var filtroActivo = (q && q.length > 0);
    var sufijo = filtroActivo
      ? '<span style="color:#94a3b8;font-size:11px;margin-left:8px">(filtrado · total: '+globalGrupos+' grupos · '+globalSols+' SOLs · '+fmt(globalValor)+')</span>'
      : '';
    kpis.innerHTML =
      '<span><b>'+totalGrupos+'</b> proveedores</span> · ' +
      '<span><b>'+totalSols+'</b> SOLs</span> · ' +
      '<span><b>'+(totalGr.toLocaleString('es-CO',{maximumFractionDigits:0}))+' g</b> total</span> · ' +
      '<span><b>'+fmt(totalValor)+'</b> valor estimado</span>' + sufijo;
  }
  if(!grupos.length){
    body.innerHTML = '<div style="color:#94a3b8;text-align:center;padding:40px;">' +
      'No hay solicitudes de planta pendientes.</div>';
    return;
  }
  body.innerHTML = grupos.map(function(g, idx){ return _plantaCardHTML(g, idx); }).join('');
  // Wire datalist global de proveedores (1 sola lista compartida)
  if(!document.getElementById('planta-prov-datalist')){
    var dl = document.createElement('datalist');
    dl.id = 'planta-prov-datalist';
    PLANTA_PROVEEDORES_LIST.forEach(function(p){
      var o = document.createElement('option'); o.value = p; dl.appendChild(o);
    });
    document.body.appendChild(dl);
  }
}

function _plantaCardHTML(g, idx){
  var prov = g.proveedor || '(sin proveedor)';
  var label = g.proveedor_label || prov;
  var solCount = (g.solicitudes||[]).length;
  var itemCount = (g.items_consolidados||[]).length;
  var totalGr = 0;
  (g.items_consolidados||[]).forEach(function(it){ totalGr += parseFloat(it.cantidad_g||0); });
  var hdrColor = (prov === '(sin proveedor)' || prov === '__SIN_PROVEEDOR__') ? '#dc2626' : '#0e7490';

  var itemsHTML = (g.items_consolidados||[]).map(function(it){
    return _plantaItemRowHTML(g, it);
  }).join('');

  return '<div class="planta-card" data-prov="'+esc(label)+'" style="background:#fff;border:1px solid #e7e5e4;border-radius:8px;overflow:hidden;">' +
    '<div style="background:'+hdrColor+';color:#fff;padding:10px 14px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">' +
      '<div style="font-weight:700;font-size:14px;flex:1;">&#x1F3ED; '+esc(label)+'</div>' +
      '<span style="background:rgba(255,255,255,.2);padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;">'+solCount+' SOLs</span>' +
      '<span style="background:rgba(255,255,255,.2);padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;">'+itemCount+' items</span>' +
      '<span style="background:rgba(255,255,255,.2);padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;">'+totalGr.toLocaleString('es-CO',{maximumFractionDigits:0})+' g</span>' +
      '<span style="background:rgba(255,255,255,.2);padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;">'+fmt(g.valor_total||0)+'</span>' +
      // CRITICA-3 fix · 21-may-2026 · botones Crear OC + Pedir cotización
      // Antes solo existían en tab "Solicitudes Agrupadas" · ahora visibles
      // donde Catalina realmente está (Planta).
      (!g.es_sin_proveedor ?
        '<button onclick="abrirCrearOCDesdeGrupoPlanta('+idx+')" style="background:#fff;color:#0e7490;border:none;border-radius:6px;padding:6px 14px;font-size:11px;font-weight:700;cursor:pointer;margin-left:8px" title="Crear UNA OC con todos los items del grupo · preview con Δ% precios">&#x1F6D2; Crear OC</button>' +
        '<button onclick="abrirPedirCotizacionPlanta('+idx+')" style="background:rgba(255,255,255,0.15);color:#fff;border:1px solid rgba(255,255,255,0.4);border-radius:6px;padding:6px 12px;font-size:10px;font-weight:700;cursor:pointer;margin-left:4px" title="Pedir 3 cotizaciones a top proveedores históricos">&#x1F4AC; Cotizar</button>'
      : '<span style="font-size:10px;color:#fff;opacity:.8;margin-left:6px">⚠ asignar proveedor</span>') +
    '</div>' +
    '<div style="padding:10px 14px;font-size:11px;color:#64748b;">SOLs incluidas: ' +
      (g.solicitudes||[]).map(function(s){ return '<span style="background:#f1f5f9;padding:2px 6px;border-radius:4px;margin-right:4px;font-weight:600;color:#334155;">'+esc(s.numero)+'</span>'; }).join('') +
      // Botón split inline si es sin_proveedor (mixto)
      (g.es_sin_proveedor && (g.solicitudes||[])[0] ?
        '<button data-act="split-sol" data-sol="'+esc(g.solicitudes[0].numero)+'" style="background:#9a3412;color:#fff;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:700;margin-left:6px" title="Dividir esta SOL en N hijas, una por proveedor distinto">&#x2702; Split</button>'
      : '') +
    '</div>' +
    '<div style="padding:0 14px 14px;">' +
      '<table style="width:100%;border-collapse:collapse;font-size:12px;">' +
        '<thead><tr style="background:#f8fafc;border-bottom:1px solid #e2e8f0;">' +
          '<th style="text-align:left;padding:6px;font-weight:700;color:#64748b;">MP</th>' +
          '<th style="text-align:left;padding:6px;font-weight:700;color:#64748b;width:160px;">Proveedor</th>' +
          '<th style="text-align:right;padding:6px;font-weight:700;color:#64748b;width:120px;">Cantidad (g)</th>' +
          '<th style="text-align:right;padding:6px;font-weight:700;color:#64748b;width:120px;">Valor</th>' +
          '<th style="text-align:right;padding:6px;font-weight:700;color:#64748b;width:80px;">SOL</th>' +
          '<th style="width:100px;"></th>' +
        '</tr></thead>' +
        '<tbody>'+itemsHTML+'</tbody>' +
      '</table>' +
    '</div>' +
  '</div>';
}

function _plantaItemRowHTML(g, it){
  // BUG #3 fix · Sprint Compras N1 · 21-may-2026 ·
  // Sebastián: agente detectó que el código solo editaba el PRIMER item
  // cuando hay varias SOLs con mismo codigo_mp. Si planta envió 2 SOLs
  // separadas del mismo MP, una queda intocada.
  // FIX: recolectar TODAS las refs (numero, item_id) y guardarlas en
  // data-refs como JSON. plantaGuardarItem itera y manda N PATCH.
  var refs = [];
  (g.solicitudes||[]).forEach(function(s){
    (s.items||[]).forEach(function(x){
      if((x.codigo_mp||'')===(it.codigo_mp||'')){
        refs.push({numero: s.numero, item_id: x.id});
      }
    });
  });
  var refsCount = refs.length;
  var sigla = refsCount === 0 ? '-' : (refsCount === 1 ? refs[0].numero : (refsCount + ' SOLs'));
  var refsAttr = encodeURIComponent(JSON.stringify(refs));
  var rowId = 'planta-row-'+(it.codigo_mp || Math.random().toString(36).slice(2));
  return '<tr id="'+rowId+'" style="border-bottom:1px solid #f1f5f9;" data-refs="'+refsAttr+'" data-codigo-mp="'+esc(it.codigo_mp||'')+'">' +
    '<td style="padding:6px;">' +
      '<div style="font-weight:600;color:#1e293b;">'+esc(it.nombre_mp||it.codigo_mp||'')+'</div>' +
      '<div style="font-size:10px;color:#94a3b8;">'+esc(it.codigo_mp||'')+'</div>' +
    '</td>' +
    '<td style="padding:6px;">' +
      '<input type="text" class="planta-prov-inp" value="'+esc((it.proveedor_sugerido)||g.proveedor||'')+'" list="planta-prov-datalist" placeholder="(sin proveedor)" style="width:100%;padding:4px 6px;border:1px solid #cbd5e1;border-radius:4px;font-size:12px;">' +
    '</td>' +
    '<td style="padding:6px;text-align:right;">' +
      // MEDIA-9 fix · 21-may-2026 · readonly cantidad si hay >1 SOL (no se
      // puede redistribuir cantidad entre SOLs sin lógica explícita)
      '<input type="number" step="any" class="planta-cant-inp" value="'+(parseFloat(it.cantidad_g||0))+'"' +
      (refsCount > 1 ? ' readonly title="Cantidad consolidada de '+refsCount+' SOLs · solo modificable individualmente"' : '') +
      ' style="width:100%;padding:4px 6px;border:1px solid '+(refsCount>1?'#cbd5e1;background:#f1f5f9':'#cbd5e1')+';border-radius:4px;font-size:12px;text-align:right;">' +
    '</td>' +
    '<td style="padding:6px;text-align:right;">' +
      (function(){
        // CRITICA-2 fix · 21-may-2026: precios_mp_historico.precio_kg está en $/kg
        // pero antes se multiplicaba por gramos directamente · inflaba OC ×1000.
        // Ahora: precio_por_g = precio_kg / 1000 · todo en $/g para sumar consistente.
        var hist = (window.PLANTA_PRECIOS_HIST||{})[it.codigo_mp];
        var valActual = parseFloat(it.valor_estimado||0);
        var cantActual = parseFloat(it.cantidad_g||0);
        var valFinal = valActual;
        var badgeHtml = '';
        if(hist && hist.precio_ultimo > 0){
          var precioPorGramo = hist.precio_ultimo / 1000;  // $/kg → $/g
          if(valActual <= 0 && cantActual > 0){
            valFinal = (precioPorGramo * cantActual).toFixed(2);
          }
          var dias = hist.dias_atras != null ? hist.dias_atras + 'd' : '?';
          var oc = hist.oc_ultima ? ' · '+hist.oc_ultima : '';
          var color = (hist.dias_atras != null && hist.dias_atras > 180) ? '#dc2626' :
                      ((hist.dias_atras != null && hist.dias_atras > 60) ? '#ca8a04' : '#16a34a');
          badgeHtml = '<div style="font-size:9px;color:'+color+';margin-top:2px;line-height:1.2" title="Precio último: $'+Number(hist.precio_ultimo).toFixed(0)+'/kg · OC '+(hist.oc_ultima||'?')+'">$'+(Number(hist.precio_ultimo).toLocaleString('es-CO',{maximumFractionDigits:0}))+'/kg · hace '+dias+oc+'</div>';
        }
        return '<input type="number" step="any" class="planta-val-inp" value="'+valFinal+'" style="width:100%;padding:4px 6px;border:1px solid #cbd5e1;border-radius:4px;font-size:12px;text-align:right;">' + badgeHtml;
      })() +
    '</td>' +
    '<td style="padding:6px;text-align:right;font-size:11px;color:#64748b;font-weight:600;" title="'+esc(refs.map(function(r){return r.numero;}).join(', '))+'">'+esc(sigla)+'</td>' +
    '<td style="padding:6px;text-align:right;">' +
      (refsCount > 0 ? '<button class="btn" onclick="plantaGuardarItem(this)" style="padding:4px 10px;font-size:11px;background:#16a34a;color:#fff;" title="'+(refsCount > 1 ? 'Guarda los '+refsCount+' items relacionados' : 'Guardar')+'">&#x1F4BE; Guardar'+(refsCount > 1 ? ' ('+refsCount+')' : '')+'</button>' :
             '<span style="font-size:10px;color:#94a3b8;">—</span>') +
    '</td>' +
  '</tr>';
}

window.plantaGuardarItem = async function(btn){
  var tr = btn.closest('tr');
  if(!tr) return;
  // BUG #3 fix · iterar TODAS las refs · antes solo guardaba la primera
  var refs = [];
  try{ refs = JSON.parse(decodeURIComponent(tr.dataset.refs || '%5B%5D')); }catch(_){ refs = []; }
  if(!refs.length){ alert('Item sin referencia · no se puede guardar'); return; }
  var prov = (tr.querySelector('.planta-prov-inp')||{value:''}).value.trim();
  var cant = parseFloat((tr.querySelector('.planta-cant-inp')||{value:'0'}).value) || 0;
  var val = parseFloat((tr.querySelector('.planta-val-inp')||{value:'0'}).value) || 0;
  var precioUnit = cant > 0 ? (val / cant) : 0;
  // Distribución proporcional si hay múltiples SOLs:
  // dejamos cada item con SU cantidad_g original, pero proveedor y precio_unit_g
  // van uniformes (es lo que la card del grupo representa).
  btn.disabled = true; btn.textContent = '...';
  // Agrupar items por numero de SOL · cada SOL recibe un PATCH con sus ítems
  var porSol = {};
  refs.forEach(function(r){ (porSol[r.numero] = porSol[r.numero] || []).push(r.item_id); });
  // Si hay varias SOLs, la "cantidad" del input es el TOTAL · no la tocamos
  // (sería tricky redistribuir); solo actualizamos proveedor + precio_unit_g.
  // Si es 1 SOL · permitimos cambiar la cantidad también.
  var soloUnaSol = (Object.keys(porSol).length === 1 && refs.length === 1);
  try{
    var resultados = await Promise.all(Object.keys(porSol).map(function(num){
      var items = porSol[num].map(function(itemId){
        var patch = {
          id: parseInt(itemId, 10),
          proveedor: prov,
          precio_unit_g: precioUnit,
        };
        if(soloUnaSol){ patch.cantidad_g = cant; }
        return patch;
      });
      return fetch('/api/solicitudes-compra/'+encodeURIComponent(num)+'/items',
        _fetchOpts('PATCH', {items: items}))
        .then(function(r){ return r.ok ? {ok:true, num:num} : r.json().then(function(d){return {ok:false, num:num, err:d.error||r.status};}); });
    }));
    var fallos = resultados.filter(function(x){ return !x.ok; });
    if(fallos.length){
      alert('Errores en '+fallos.length+' SOL(s): '+fallos.map(function(f){return f.num+': '+f.err;}).join(' · '));
      btn.disabled = false; btn.innerHTML = '&#x1F4BE; Guardar'+(refs.length > 1 ? ' ('+refs.length+')' : '');
      return;
    }
    btn.style.background = '#0e7490';
    btn.innerHTML = '&#x2713; '+(refs.length > 1 ? refs.length+' OK' : 'Guardado');
    setTimeout(function(){
      loadPlanta();
    }, 600);
  }catch(e){
    alert('Error de red: '+e.message);
    btn.disabled = false; btn.innerHTML = '&#x1F4BE; Guardar'+(refs.length > 1 ? ' ('+refs.length+')' : '');
  }
};

window.limpiarSolsPlantaLegacy = async function(){
  // 2 pasos: dry_run para preview, luego confirm + ejecutar
  try{
    var rDry = await fetch('/api/compras/limpiar-solicitudes-planta',
      _fetchOpts('POST', {dry_run: true}));
    var dDry = await rDry.json();
    if(!rDry.ok){ alert('Error preview: '+(dDry.error||rDry.status)); return; }
    var nElim = dDry.eliminaria || dDry.eliminadas || 0;
    if(nElim === 0){
      alert('✓ No hay SOLs de planta Pendientes sin OC para limpiar.');
      return;
    }
    var msg = 'LIMPIAR SOLs de PLANTA legacy\\n\\n' +
      'Va a borrar:\\n' +
      '  · '+nElim+' solicitudes Pendientes (categoría MP / Empaque · sin OC)\\n\\n' +
      'NO toca solicitudes con OC vinculada (Aprobadas / Pagadas / Recibidas).\\n\\n' +
      'Esto te deja un piso limpio para que el Centro de Programación\\n' +
      'regenere las solicitudes con las reglas nuevas.\\n\\n' +
      '¿Confirmar eliminación?';
    if(!confirm(msg)) return;
    var r = await fetch('/api/compras/limpiar-solicitudes-planta',
      _fetchOpts('POST', {dry_run: false, confirm: true}));
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    alert('✓ '+d.mensaje);
    loadPlanta();
  }catch(e){
    alert('Error de red: '+e.message);
  }
};

async function loadInfluencers(){
  try{
    // Sebastian (30-abr-2026): cache-bust con timestamp para evitar que el
    // browser sirva una respuesta vieja despues de pagar.
    var r=await fetch('/api/solicitudes-compra?categoria=Influencer%2FMarketing+Digital&_t='+Date.now(),
      {cache:'no-store'});
    var d=await r.json();
    INFLUENCERS=d.solicitudes||[];
  }catch(e){ INFLUENCERS=[]; }
  renderInfluencers();
}

// Helpers para ordenar — usados por renderInfluencers()
// Sebastián 27-may-2026 PM · prioriza vence_pago_at (promesa 30d desde
// fecha_contenido · mig 195). Lo más cerca a vencer arriba.
function _infFechaOrden(s){
  return (s.vence_pago_at && String(s.vence_pago_at).trim())
      || (s.fecha_requerida && String(s.fecha_requerida).trim())
      || (s.fecha && String(s.fecha).trim())
      || '9999-12-31';
}
// Devuelve {nivel, dias, vence} para badge visual de urgencia.
// nivel: 'vencido' | 'urgente' | 'proximo' | 'normal' | ''
function _infUrgencia(s){
  if(s.estado === 'Pagada') return {nivel:'', dias:null, vence:''};
  var v = s.vence_pago_at && String(s.vence_pago_at).trim();
  if(!v) return {nivel:'', dias:null, vence:''};
  var d = new Date(v + 'T00:00:00');
  if(isNaN(d.getTime())) return {nivel:'', dias:null, vence:v};
  var hoy = new Date(); hoy.setHours(0,0,0,0);
  var dias = Math.round((d - hoy)/(24*3600*1000));
  if(dias < 0) return {nivel:'vencido', dias:dias, vence:v};
  if(dias <= 7) return {nivel:'urgente', dias:dias, vence:v};
  if(dias <= 15) return {nivel:'proximo', dias:dias, vence:v};
  return {nivel:'normal', dias:dias, vence:v};
}
function _infEstadoRank(e){
  if(e==='Aprobada')  return 0;
  if(e==='Pendiente') return 1;
  if(e==='Pagada')    return 2;
  return 3;
}
function _infSortFn(criterio){
  // Devuelve la función de comparación según el criterio elegido por el user.
  if(criterio==='urgente'){
    return function(a,b){
      var fa=_infFechaOrden(a), fb=_infFechaOrden(b);
      if(fa!==fb) return fa<fb?-1:1;
      return (a.numero||'').localeCompare(b.numero||'');
    };
  }
  if(criterio==='valor_desc'){
    return function(a,b){ return (b.valor||0)-(a.valor||0); };
  }
  if(criterio==='valor_asc'){
    return function(a,b){ return (a.valor||0)-(b.valor||0); };
  }
  if(criterio==='reciente'){
    return function(a,b){
      var fa=(a.fecha||''), fb=(b.fecha||'');
      if(fa!==fb) return fa<fb?1:-1; // descendente
      return (a.numero||'').localeCompare(b.numero||'');
    };
  }
  if(criterio==='antiguo'){
    return function(a,b){
      var fa=(a.fecha||'9999'), fb=(b.fecha||'9999');
      if(fa!==fb) return fa<fb?-1:1;
      return (a.numero||'').localeCompare(b.numero||'');
    };
  }
  // default: estado_fecha (Aprobadas → Pendientes → Pagadas → resto, fecha asc)
  return function(a,b){
    var ra=_infEstadoRank(a.estado), rb=_infEstadoRank(b.estado);
    if(ra!==rb) return ra-rb;
    var fa=_infFechaOrden(a), fb=_infFechaOrden(b);
    if(fa!==fb) return fa<fb?-1:1;
    return (a.numero||'').localeCompare(b.numero||'');
  };
}
function fmoney(v){ return '$'+Number(v||0).toLocaleString('es-CO'); }
function renderInfluencers(){
  var q=(document.getElementById('q-influencer')||{value:''}).value.toLowerCase();
  // Sebastian (29-abr-2026): default 'ACCION' = Pendiente + Aprobada — todo
  // lo que requiere su atencion. Antes era solo 'Aprobada' y se perdian las
  // SOL Pendientes que Jefferson creo desde /solicitudes con valor=0.
  var st=(document.getElementById('s-influencer')||{value:'ACCION'}).value;
  var ordCriterio=(document.getElementById('order-influencer')||{value:'urgente'}).value;
  // Sort defensivo: aplicamos el criterio elegido SIEMPRE antes de filtrar/render
  if(Array.isArray(INFLUENCERS) && INFLUENCERS.length){
    INFLUENCERS.sort(_infSortFn(ordCriterio));
  }
  // Mostrar al user el criterio activo + diagnóstico de fechas
  var helpEl=document.getElementById('pills-influencer-help');
  if(helpEl){
    var labels={
      estado_fecha:'Por pagar primero (Aprobadas → Pendientes → Pagadas, luego fecha más vieja)',
      urgente:'Fecha de pago debido — más antiguas arriba',
      valor_desc:'Mayor valor de pago primero',
      valor_asc:'Menor valor de pago primero',
      reciente:'Fecha de creación — más reciente arriba',
      antiguo:'Fecha de creación — más antiguo arriba',
    };
    // Cuántas tienen fecha_requerida (para que vea por qué a veces parece desordenado)
    var con_fecha_req = INFLUENCERS.filter(function(s){return s.fecha_requerida && String(s.fecha_requerida).trim();}).length;
    var msg='Orden: <strong>'+(labels[ordCriterio]||ordCriterio)+'</strong>';
    if((ordCriterio==='estado_fecha' || ordCriterio==='urgente') && INFLUENCERS.length){
      msg += ' · '+con_fecha_req+'/'+INFLUENCERS.length+' tienen fecha de pago debido';
      if(con_fecha_req===0){
        msg += ' <span style="color:#b94400;font-weight:600;">→ todas usan fecha de creación, prueba "Mayor valor" para mejor orden</span>';
      }
    }
    helpEl.innerHTML=msg;
  }

  // ── Parse beneficiary block from observaciones text ──────────────────────
  function parseBenef(obs){
    var out={nombre:'',banco:'',cuenta:'',cedNit:'',valor:''};
    if(!obs) return out;
    var m;
    m=obs.match(/BENEFICIARIO:\\s*([^|]+)/i); if(m) out.nombre=m[1].trim();
    m=obs.match(/BANCO:\\s*([^|]+)/i);        if(m) out.banco=m[1].trim();
    m=obs.match(/CUENTA\\/CEL:\\s*([^|]+)/i);  if(m) out.cuenta=m[1].trim();
    m=obs.match(/CED\\/NIT:\\s*([^|]+)/i);     if(m) out.cedNit=m[1].trim();
    m=obs.match(/VALOR:\\s*([^|]+)/i);        if(m) out.valor=m[1].trim();
    return out;
  }

  var pendAll=INFLUENCERS.filter(function(s){ return s.estado==='Aprobada'; });
  var pagaAll=INFLUENCERS.filter(function(s){ return s.estado==='Pagada'; });
  var totalPend=pendAll.reduce(function(a,s){ return a+(s.valor||0); },0);
  var totalPaga=pagaAll.reduce(function(a,s){ return a+(s.valor||0); },0);

  // ── KPI cards ────────────────────────────────────────────────────────────
  var kpiEl=document.getElementById('kpi-influencer');
  if(kpiEl){
    kpiEl.innerHTML=
      '<div style="background:#7c3aed;color:#fff;padding:14px 22px;border-radius:10px;min-width:170px;box-shadow:0 2px 8px rgba(124,58,237,.2)">'
      +'<div style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Por pagar</div>'
      +'<div style="font-size:26px;font-weight:700;margin-top:4px;">'+pendAll.length+' OCs</div>'
      +'<div style="font-size:13px;opacity:.9;margin-top:2px;">'+fmoney(totalPend)+'</div>'
      +'</div>'
      +'<div style="background:#059669;color:#fff;padding:14px 22px;border-radius:10px;min-width:170px;box-shadow:0 2px 8px rgba(5,150,105,.2)">'
      +'<div style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Pagadas este ciclo</div>'
      +'<div style="font-size:26px;font-weight:700;margin-top:4px;">'+pagaAll.length+'</div>'
      +'<div style="font-size:13px;opacity:.9;margin-top:2px;">'+fmoney(totalPaga)+'</div>'
      +'</div>'
      +'<div style="background:#374151;color:#fff;padding:14px 22px;border-radius:10px;min-width:170px;box-shadow:0 2px 8px rgba(55,65,81,.15)">'
      +'<div style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:.6px;font-weight:600;">Total influencers</div>'
      +'<div style="font-size:26px;font-weight:700;margin-top:4px;">'+INFLUENCERS.length+'</div>'
      +'</div>';
  }

  // ── Filter list ──────────────────────────────────────────────────────────
  var list=INFLUENCERS.filter(function(s){
    // Filtro especial 'ACCION' = Pendiente + Aprobada (todo lo que requiere atencion)
    if(st === 'ACCION'){
      if(s.estado !== 'Pendiente' && s.estado !== 'Aprobada') return false;
    } else if(st && s.estado!==st){
      return false;
    }
    if(q){
      var hay=(s.numero||'')+(s.solicitante||'')+(s.observaciones||'')+(s.numero_oc||'');
      if(hay.toLowerCase().indexOf(q)<0) return false;
    }
    return true;
  });

  var el=document.getElementById('pills-influencer');
  if(el) el.innerHTML='<span class="pill">'+list.length+' mostradas</span>';

  // ── Card builder ─────────────────────────────────────────────────────────
  function buildCard(s){
    var b=parseBenef(s.observaciones||'');
    // Fallback: si los datos NO vienen en observaciones, usar los del
    // influencer linkado (nuevo enriquecimiento desde marketing_influencers
    // via influencer_id). Así "Luisa" deja de aparecer sin datos cuando la
    // solicitud fue creada sin el bloque BENEFICIARIO en obs.
    if(!b.nombre && s.inf_nombre) b.nombre = s.inf_nombre;
    if(!b.banco && s.inf_banco) {
      b.banco = s.inf_banco + (s.inf_tipo_cuenta ? ' ' + s.inf_tipo_cuenta : '');
    }
    if(!b.cuenta && s.inf_cuenta) b.cuenta = s.inf_cuenta;
    if(!b.cedNit && s.inf_cedula) b.cedNit = s.inf_cedula;
    var isPagada=s.estado==='Pagada';
    var isRech=s.estado==='Rechazada';
    var borderColor=isPagada?'#059669':isRech?'#dc2626':'#7c3aed';
    var headerBg=isPagada?'#f0fdf4':isRech?'#fef2f2':'#faf5ff';

    // Badge
    var badgeMap={'Aprobada':{bg:'#ede9fe',fg:'#5b21b6',txt:'💸 Lista para pagar'},
                  'Pagada':{bg:'#d1fae5',fg:'#065f46',txt:'✅ Pagada'},
                  'Rechazada':{bg:'#fee2e2',fg:'#991b1b',txt:'❌ Rechazada'},
                  'Pendiente':{bg:'#fef3c7',fg:'#92400e',txt:'⏳ Pendiente'}};
    var cfg=badgeMap[s.estado]||{bg:'#f3f4f6',fg:'#374151',txt:s.estado};

    // Badge urgencia · promesa 30d desde fecha_contenido (mig 195)
    var urg=_infUrgencia(s);
    var urgBadge='';
    if(urg.nivel==='vencido'){
      urgBadge='<span style="background:#dc2626;color:#fff;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;border:1.5px solid #991b1b;" title="ATRASADO · pago vencido hace '+Math.abs(urg.dias)+' días. Promesa: 30d desde el contenido. Vencía '+esc(urg.vence)+'">🔴 ATRASADO '+Math.abs(urg.dias)+'d</span>';
    } else if(urg.nivel==='urgente'){
      urgBadge='<span style="background:#f59e0b;color:#fff;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;" title="Vence en '+urg.dias+' días ('+esc(urg.vence)+')">🟡 Vence en '+urg.dias+'d</span>';
    } else if(urg.nivel==='proximo'){
      urgBadge='<span style="background:#bfdbfe;color:#1e40af;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;" title="Vence '+esc(urg.vence)+'">🔵 '+urg.dias+'d</span>';
    } else if(urg.nivel==='normal'){
      urgBadge='<span style="background:#dcfce7;color:#166534;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;" title="Al día · vence '+esc(urg.vence)+'">🟢 '+urg.dias+'d</span>';
    }

    // Bank info row — only show if parsed
    var bankRow='';
    if(b.nombre||b.banco||b.cuenta){
      bankRow='<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px;margin:10px 0;display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;font-size:12px;">'
        +(b.nombre?'<div><span style="color:#64748b;font-weight:600;text-transform:uppercase;font-size:10px;">Beneficiario</span><div style="color:#1e293b;font-weight:600;margin-top:1px;">'+esc(b.nombre)+'</div></div>':'')
        +(b.banco?'<div><span style="color:#64748b;font-weight:600;text-transform:uppercase;font-size:10px;">Banco</span><div style="color:#1e293b;margin-top:1px;">'+esc(b.banco)+'</div></div>':'')
        +(b.cuenta?'<div><span style="color:#64748b;font-weight:600;text-transform:uppercase;font-size:10px;">Cuenta / Cel</span><div style="color:#1e293b;font-family:monospace;margin-top:1px;">'+esc(b.cuenta)+'</div></div>':'')
        +(b.cedNit?'<div><span style="color:#64748b;font-weight:600;text-transform:uppercase;font-size:10px;">Cédula / NIT</span><div style="color:#1e293b;font-family:monospace;margin-top:1px;">'+esc(b.cedNit)+'</div></div>':'')
        +'</div>';
    }

    // Action buttons
    var btns='';
    if(s.estado==='Aprobada'){
      btns='<button class="btn inf-pagar" data-oc="'+esc(s.numero_oc||'')+'" data-sol="'+esc(s.numero)+'" data-val="'+Number(s.valor||0)+'" style="background:#7c3aed;color:#fff;padding:7px 18px;font-size:13px;font-weight:600;">💸 Pagar ahora</button>'
          +'<button class="btn inf-rechazar" data-oc="'+esc(s.numero_oc||'')+'" data-sol="'+esc(s.numero)+'" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;padding:7px 14px;font-size:13px;">✕ Rechazar</button>'
          +'<button class="btn inf-eliminar" data-sol="'+esc(s.numero)+'" data-nombre="'+esc((b.nombre||s.solicitante||s.numero))+'" style="background:#f3f4f6;color:#6b7280;border:1px solid #d1d5db;padding:7px 12px;font-size:12px;" title="Eliminar definitivamente esta solicitud (no genera comprobante)">🗑 Eliminar</button>';
    } else if(s.estado==='Pendiente'){
      // Sebastian (29-abr-2026): si la SOL ya viene con valor desde Marketing
      // (Jefferson cargo todo), boton directo "Pagar". Si valor=0 (form
      // generico de /solicitudes), pedir el valor antes de pagar.
      var valSol = Number(s.valor||0);
      var btnPagar = valSol > 0
        ? '<button class="btn inf-pagar-pendiente" data-sol="'+esc(s.numero)+'" data-val="'+valSol+'" data-nombre="'+esc((b.nombre||s.solicitante||''))+'" style="background:#7c3aed;color:#fff;padding:7px 18px;font-size:13px;font-weight:600;">💸 Pagar</button>'
        : '<button class="btn inf-pagar-pendiente" data-sol="'+esc(s.numero)+'" data-val="0" data-nombre="'+esc((b.nombre||s.solicitante||''))+'" style="background:#0891b2;color:#fff;padding:7px 14px;font-size:12px;font-weight:600;">✏️ Definir valor &amp; pagar</button>';
      btns = btnPagar
          +'<button class="btn inf-rechazar-pendiente" data-sol="'+esc(s.numero)+'" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;font-size:12px;">✕ Rechazar</button>'
          +'<button class="btn" data-act="del-sol" data-sol="'+esc(s.numero)+'" style="background:#f3f4f6;color:#6b7280;border:1px solid #d1d5db;font-size:11px;">🗑 Eliminar</button>';
    } else if(s.estado==='Rechazada'){
      btns='<button class="btn" data-act="del-sol" data-sol="'+esc(s.numero)+'" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;font-size:11px;padding:3px 8px;">🗑</button>';
    }

    return '<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+borderColor+';border-radius:10px;padding:0;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.06);overflow:hidden;">'
      // Header
      +'<div style="background:'+headerBg+';padding:12px 16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">'
        +'<div style="display:flex;align-items:center;gap:10px;">'
          +'<div style="font-family:monospace;font-size:13px;font-weight:700;color:#374151;">'+esc(s.numero)+'</div>'
          +(s.numero_oc?'<div style="font-family:monospace;font-size:11px;color:#7c3aed;background:#ede9fe;padding:2px 8px;border-radius:4px;">'+esc(s.numero_oc)+'</div>':'')
        +'</div>'
        +'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">'
          +'<div style="font-size:18px;font-weight:700;color:'+borderColor+';">'+fmoney(s.valor)+'</div>'
          +urgBadge
          +'<span style="background:'+cfg.bg+';color:'+cfg.fg+';padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;">'+cfg.txt+'</span>'
        +'</div>'
      +'</div>'
      // Body
      +'<div style="padding:12px 16px;">'
        +'<div style="display:flex;gap:16px;font-size:12px;color:#64748b;margin-bottom:8px;flex-wrap:wrap;align-items:center;">'
          +'<span>👤 '+esc(s.solicitante||'-')+'</span>'
          +(s.fecha_requerida && String(s.fecha_requerida).trim()
              ? '<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:6px;font-weight:600;">📅 Pago debido: '+fdate(s.fecha_requerida)+'</span>'
              : '<span>📅 Solicitud: '+fdate(s.fecha)+'</span>')
          +'<span>🏢 '+esc(s.area||'Marketing/ANIMUS')+'</span>'
        +'</div>'
        +bankRow
        +(btns?'<div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;">'+btns+'</div>':'')
      +'</div>'
    +'</div>';
  }

  // ── Render pending grid ───────────────────────────────────────────────────
  var gel=document.getElementById('grid-influencer');
  var gpag=document.getElementById('grid-influencer-pagadas');
  if(!gel) return;

  if(!list.length){
    gel.innerHTML='<div class="empty">No hay resultados para el filtro seleccionado</div>';
  } else {
    // Badge "#N en la cola" solo para Aprobadas (los Por pagar)
    var rank=0;
    var cards=list.map(function(s){
      var c=buildCard(s);
      if(s.estado==='Aprobada'){
        rank++;
        var badge='<div style="display:inline-block;background:#7c3aed;color:#fff;font-size:11px;font-weight:700;padding:3px 10px;border-radius:6px;margin-bottom:6px;">#'+rank+' en cola</div>';
        // Insertar el badge dentro del header de la card
        c=c.replace('<div style="font-family:monospace;font-size:13px;font-weight:700;color:#374151;">',
                    badge+'<div style="font-family:monospace;font-size:13px;font-weight:700;color:#374151;">');
      }
      return c;
    });
    gel.innerHTML=cards.join('');
  }

  // ── Paid section (always shown when filter is not "Pagada") ───────────────
  if(gpag){
    if(st==='' || st==='Aprobada'){
      // Show a collapsible paid section below
      if(pagaAll.length>0){
        gpag.innerHTML='<details style="margin-top:20px;">'
          +'<summary style="cursor:pointer;font-size:13px;font-weight:600;color:#059669;padding:10px 14px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;list-style:none;display:flex;align-items:center;gap:8px;">'
          +'✅ '+pagaAll.length+' pago'+(pagaAll.length>1?'s':'')+' realizados — '+fmoney(totalPaga)
          +' <span style="font-size:11px;color:#64748b;font-weight:400;margin-left:4px;">(click para ver)</span>'
          +'</summary>'
          +'<div style="margin-top:10px;">'+pagaAll.map(buildCard).join('')+'</div>'
          +'</details>';
      } else {
        gpag.innerHTML='';
      }
    } else {
      gpag.innerHTML='';
    }
  }

  // ── Event delegation ──────────────────────────────────────────────────────
  function attachEvents(container){
    if(!container) return;
    container.onclick=function(e){
      var bp=e.target.closest('.inf-pagar');
      var br=e.target.closest('.inf-rechazar');
      var bd=e.target.closest('[data-act="del-sol"]');
      var be=e.target.closest('.inf-eliminar');
      var bpd=e.target.closest('.inf-pagar-pendiente');
      var bx=e.target.closest('.inf-rechazar-pendiente');
      if(bp) pagarInfluencer(bp.dataset.oc, bp.dataset.sol, Number(bp.dataset.val));
      if(br) rechazarInfluencer(br.dataset.oc, br.dataset.sol);
      if(bd) eliminarSolicitud(bd.dataset.sol);
      if(be) eliminarSolicitudAprobada(be.dataset.sol, be.dataset.nombre);
      if(bpd) pagarPendienteInfluencer(bpd.dataset.sol, Number(bpd.dataset.val), bpd.dataset.nombre);
      if(bx) rechazarPendienteInfluencer(bx.dataset.sol);
    };
  }

  // Pagar SOL Pendiente en UN SOLO CLICK:
  //   1. Si valor=0, pedirlo al usuario.
  //   2. Aprobar SOL + crear OC vinculada (endpoint aprobar-influencer).
  //   3. Pagar la OC recien creada (endpoint /pagar) — esto:
  //      - registra pago en pagos_oc
  //      - cambia OC a 'Pagada'
  //      - sincroniza solicitudes_compra → 'Pagada'
  //      - sincroniza pagos_influencers → 'Pagada' (visible para Jefferson)
  //      - inserta en flujo_egresos (Tesoreria)
  //      - genera Comprobante de Egreso PDF
  //      - manda email automatico a Jefferson confirmando pago
  // Sebastian (29-abr-2026): "le doy pagar le sale a el pagada y ya, porque
  // catalina no tiene nada que ver con esto".
  window.pagarPendienteInfluencer = async function(sol, valActual, nombre){
    var monto = valActual;
    if(!monto || monto <= 0){
      var v = prompt('Valor a pagar a "' + (nombre||sol) + '" (COP, sin puntos):', '');
      if(v === null) return;
      monto = parseFloat(String(v).replace(/[^\\d.]/g,''));
      if(!monto || monto <= 0){ alert('Valor inválido. Cancelado.'); return; }
    }
    if(!confirm('¿Confirmar pago de $'+monto.toLocaleString('es-CO')+' a '+(nombre||sol)+'?\\n\\nEsto crea la OC, registra el pago, genera comprobante y notifica a Jefferson.')) return;
    try {
      // Paso 1: aprobar (crea OC + entrada pagos_influencers)
      var r1 = await fetch('/api/solicitudes-compra/'+encodeURIComponent(sol)+'/aprobar-influencer',_fetchOpts('POST', {valor: monto}));
      var raw1 = await r1.text();
      var d1 = null; try { d1 = JSON.parse(raw1); } catch(_){}
      if(!r1.ok){
        alert('Error al aprobar SOL: '+(d1&&d1.error || raw1.substring(0,200)));
        return;
      }
      var ocNum = d1.numero_oc;
      if(!ocNum){ alert('OC no fue creada. Abort.'); loadInfluencers(); return; }
      // Paso 2: pagar la OC recién creada
      var r2 = await fetch('/api/ordenes-compra/'+encodeURIComponent(ocNum)+'/pagar',_fetchOpts('PATCH', {monto: monto, medio: 'Transferencia', sol_numero: sol}));
      var raw2 = await r2.text();
      var d2 = null; try { d2 = JSON.parse(raw2); } catch(_){}
      if(!r2.ok){
        alert('OC '+ocNum+' creada pero pago fallo: '+(d2&&d2.error || raw2.substring(0,200))+'\\n\\nPuedes pagarla manualmente desde el filtro "Por pagar".');
        loadInfluencers();
        return;
      }
      alert('✅ Pagado: '+ocNum+' — Jefferson recibirá email + notif in-app');
      // Sebastian (30-abr-2026): "le doy pagar no desaparece" — bulletproof
      // refresh: esperar la recarga y forzar fresh fetch (no cache).
      try { await loadInfluencers(); } catch(_){}
    } catch(e){ alert('Error de red: '+e.message); }
  };

  // Rechazar SOL Pendiente (no autoriza el pago).
  window.rechazarPendienteInfluencer = async function(sol){
    var razon = prompt('Razón del rechazo (se notifica al solicitante):', '');
    if(razon === null) return;
    try {
      var r = await fetch('/api/solicitudes-compra/'+encodeURIComponent(sol)+'/rechazar',_fetchOpts('POST', {motivo: razon||'Rechazada sin motivo'}));
      var raw = await r.text();
      var d = null; try { d = JSON.parse(raw); } catch(_){}
      if(!r.ok){ alert('Error '+r.status+': '+ (d&&d.error || raw.substring(0,200))); return; }
      alert('Rechazada');
      loadInfluencers();
    } catch(e){ alert('Error de red: '+e.message); }
  };
  attachEvents(gel);
  attachEvents(gpag);
}

function eliminarSolicitudAprobada(sol_num, nombre){
  // Confirmación más fuerte porque la solicitud está Aprobada (lista para
  // pagar). Si la borrás se pierde la cola de pago.
  var msg = 'ELIMINAR ' + (nombre || sol_num) + '?\\n\\n'
          + 'Esta solicitud está APROBADA (lista para pagar). Si la eliminas se '
          + 'borra del sistema y NO podrás generar comprobante después.\\n\\n'
          + 'Solo confirma si:\\n'
          + ' · Ya pagaste por fuera y no necesitas comprobante en la app\\n'
          + ' · La cargaste por error\\n\\n'
          + '¿Eliminar definitivamente?';
  if(!confirm(msg)) return;
  fetch('/api/solicitudes-compra/'+encodeURIComponent(sol_num),
        _fetchOpts('DELETE'))
    .then(function(r){return r.json();})
    .then(function(d){
      if(d.ok || d.message){
        loadInfluencers();
      } else {
        alert('Error: ' + (d.error || 'no se pudo eliminar'));
      }
    })
    .catch(function(){ alert('Error de conexión'); });
}
// ─── Pagar influencer ───────────────────────────────────────────────
function pagarInfluencer(oc_num, sol_num, valor){
  if(!oc_num){
    // Sin OC vinculada (legacy/link fallido): en vez de abortar, crear la OC y
    // pagar en un paso (flujo Pendiente). Antes esto dejaba el item pegado.
    if(window.pagarPendienteInfluencer){ return pagarPendienteInfluencer(sol_num, valor, sol_num); }
    alert('Esta solicitud no tiene OC vinculada. Contacta a Sebastian.'); return;
  }
  var confirmado=confirm('Confirmar pago ' + fmoney(valor) + ' para ' + sol_num + ' | OC: ' + oc_num + ' | Se registrará en Finanzas.');
  if(!confirmado) return;
  fetch('/api/ordenes-compra/'+encodeURIComponent(oc_num)+'/pagar',_fetchOpts('PATCH', {monto:valor,medio:'Transferencia',observaciones:'Pago influencer '+sol_num,sol_numero:sol_num})).then(function(r){return r.json();}).then(function(d){
    if(d.ok){
      alert('Pago registrado. La OC quedó como Pagada y el egreso fue enviado a Finanzas.');
      loadInfluencers();
    } else { alert('Error: '+(d.error||'desconocido')); }
  }).catch(function(){ alert('Error de conexión'); });
}
// ─── Rechazar influencer ────────────────────────────────────────────
var _rechazarOC='', _rechazarSol='';
function rechazarInfluencer(oc_num, sol_num){
  if(!oc_num){ alert('Esta solicitud no tiene OC vinculada.'); return; }
  _rechazarOC=oc_num; _rechazarSol=sol_num;
  var m=document.getElementById('motivo-rechazo-inf');
  if(m) m.value='';
  var sub=document.getElementById('m-rechazar-inf-sub');
  if(sub) sub.textContent=sol_num ? 'Solicitud '+sol_num : '';
  openModal('m-rechazar-inf');
  var btn=document.getElementById('btn-confirmar-rechazo');
  if(btn){
    btn.onclick=function(){
      var motivo=(document.getElementById('motivo-rechazo-inf')||{value:''}).value.trim();
      if(!motivo){ alert('El motivo es obligatorio para rechazar.'); return; }
      fetch('/api/compras/oc/'+encodeURIComponent(_rechazarOC)+'/rechazar',_fetchOpts('POST', {motivo:motivo})).then(function(r){return r.json();}).then(function(d){
        if(d.ok){
          closeModal('m-rechazar-inf');
          alert('OC rechazada. La solicitud volvió a estado Pendiente con el motivo registrado.');
          loadInfluencers();
        } else { alert('Error: '+(d.error||'desconocido')); }
      }).catch(function(){ alert('Error de conexión'); });
    };
  }
}

function renderSolicitudes(){
  var q=(document.getElementById('q-solic')||{value:''}).value.toLowerCase();
  var st=(document.getElementById('s-solic')||{value:''}).value;
  var cat=_SOLIC_CAT_FILTER||'ALL';

  // Build OC lookup map for inline display
  var ocMap={};
  (OCS||[]).forEach(function(o){ ocMap[o.numero_oc]=o; });

  var list=SOLIC.filter(function(s){
    // Always exclude Influencer/Marketing (has its own tab), unless cat filter is 'inf'
    if(cat==='ALL'||(cat!=='inf')){
      if((s.categoria||'').indexOf('Influencer')>=0) return false;
    }
    // Category filter
    if(cat==='ALL'){
      // show all except influencer (already excluded above)
    } else if(cat==='cc'){
      if((s.categoria||'').indexOf('Cuenta de Cobro')<0) return false;
    } else if(cat==='inf'){
      if((s.categoria||'').indexOf('Influencer')<0) return false;
    } else {
      if(!inGroup(s.categoria,cat)) return false;
    }
    // Estado filter
    if(st&&s.estado!==st) return false;
    // Search
    var oc=ocMap[s.numero_oc];
    var ocNum=oc?oc.numero_oc:'';
    if(q&&(s.numero||'').toLowerCase().indexOf(q)<0
        &&(s.solicitante||'').toLowerCase().indexOf(q)<0
        &&(s.observaciones||'').toLowerCase().indexOf(q)<0
        &&ocNum.toLowerCase().indexOf(q)<0) return false;
    return true;
  });

  var pend=list.filter(function(s){ return s.estado==='Pendiente'; }).length;
  var apro=list.filter(function(s){ return s.estado==='Aprobada'; }).length;
  var rech=list.filter(function(s){ return s.estado==='Rechazada'; }).length;
  var paga=list.filter(function(s){ return s.estado==='Pagada'; }).length;
  var pills='<span class="pill">'+list.length+' solicitudes</span>';
  if(pend) pills+='<span class="pill y">Pendiente: '+pend+'</span>';
  if(apro) pills+='<span class="pill g">Aprobada: '+apro+'</span>';
  if(rech) pills+='<span class="pill" style="background:#fee2e2;color:#991b1b;">Rechazada: '+rech+'</span>';
  if(paga) pills+='<span class="pill" style="background:#e0f2fe;color:#075985;">Pagada: '+paga+'</span>';
  document.getElementById('pills-solic').innerHTML=pills;

  if(!list.length){
    document.getElementById('grid-solic').innerHTML='<div class="empty">No hay solicitudes'+(cat!=='ALL'?' en esta categoría':'')+'</div>';
    return;
  }

  var urgColor={'Normal':'#16a34a','Urgente':'#d97706','Critico':'#dc2626','Alta':'#dc2626','Media':'#d97706'};
  var stBg={'Pendiente':'#fef3c7','Aprobada':'#dcfce7','Rechazada':'#fee2e2','Pagada':'#e0f2fe'};
  var stFg={'Pendiente':'#92400e','Aprobada':'#166534','Rechazada':'#991b1b','Pagada':'#075985'};

  document.getElementById('grid-solic').innerHTML=list.map(function(s){
    var urg=s.urgencia||'Normal';
    var urgC=urgColor[urg]||'#78716c';
    var stB=stBg[s.estado]||'#f3f4f6';
    var stF=stFg[s.estado]||'#374151';
    // OC inline badge
    var oc=ocMap[s.numero_oc];
    var ocBadge='';
    if(oc){
      var ocStBg={'Revisada':'#fef3c7','Autorizada':'#d1fae5','Pagada':'#e0f2fe','Recibida':'#f3e8ff'}[oc.estado]||'#f3f4f6';
      var ocStFg={'Revisada':'#92400e','Autorizada':'#065f46','Pagada':'#075985','Recibida':'#6b21a8'}[oc.estado]||'#374151';
      ocBadge='<span style="font-family:monospace;font-size:10px;background:'+ocStBg+';color:'+ocStFg+';border-radius:4px;padding:1px 6px;margin-left:6px;" title="Orden de Compra vinculada">'+esc(oc.numero_oc)+'</span>';
    } else if(s.numero_oc){
      ocBadge='<span style="font-family:monospace;font-size:10px;background:#f3f4f6;color:#9ca3af;border-radius:4px;padding:1px 6px;margin-left:6px;">'+esc(s.numero_oc)+'</span>';
    }
    return '<div class="card" data-num="'+esc(s.numero)+'">'
      +'<div class="ch"><div><div class="cnum" style="font-family:monospace;">'+esc(s.numero)+ocBadge+'</div>'
      +'<div class="cprov">'+esc(s.solicitante||'-')+' &mdash; '+esc(s.area||'-')+'</div></div>'
      +'<span class="badge" style="background:'+stB+';color:'+stF+';">'+s.estado+'</span></div>'
      +'<div class="cmeta"><span>'+fdate(s.fecha)+'</span><span>'+esc(s.empresa||'Espagiria')+'</span>'
      +'<span>'+esc(s.categoria||'-')+'</span>'
      +'<span style="color:'+urgC+';font-weight:700;">'+esc(urg)+'</span></div>'
      +(s.observaciones?'<div class="cobs">'+esc((s.observaciones||'').substring(0,100))+'</div>':'')
      +'<div class="acts" style="gap:6px;"><button class="btn bo bs" data-act="sdet" data-sol="'+esc(s.numero)+'">&#128203; Ver &amp; Gestionar</button>'+'<button class="btn" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;padding:4px 10px;font-size:11px;" data-act="del-sol" data-sol="'+esc(s.numero)+'">&#x1F5D1;</button>'+'</div>'
      +'</div>';
  }).join('');
}
function setSolicCat(btn){
  _SOLIC_CAT_FILTER=(btn&&btn.getAttribute('data-scat'))||'ALL';
  document.querySelectorAll('.ocs-cpill').forEach(function(b){ b.classList.remove('on'); });
  if(btn) btn.classList.add('on');
  if(_VISTA_AGRUPADA){ renderSolicitudesAgrupadas(); }
  else { renderSolicitudes(); }
}

// ────────────────────────────────────────────────────────────────
// Sebastian 4-may-2026 (Catalina): vista agrupada de solicitudes por proveedor
// ────────────────────────────────────────────────────────────────
// Catalina recibe 200+ AUTO-PLAN cada uno con 1 MP. Procesarlas una por una
// es lento. Esta vista las agrupa por proveedor sugerido y permite generar
// UNA OC con TODAS las MPs del mismo proveedor en un solo paso.
var _VISTA_AGRUPADA = false;
var _GRUPOS_CACHE = null;

async function toggleVistaSolicitudes(){
  _VISTA_AGRUPADA = !_VISTA_AGRUPADA;
  var btn = document.getElementById('btn-toggle-vista');
  var gridFlat = document.getElementById('grid-solic');
  var gridGrp  = document.getElementById('grid-solic-grouped');
  if(_VISTA_AGRUPADA){
    if(btn){ btn.style.background='#dc2626'; btn.innerHTML='&#x1F4CB; Vista plana'; }
    if(gridFlat) gridFlat.style.display='none';
    if(gridGrp)  gridGrp.style.display='block';
    await renderSolicitudesAgrupadas();
  } else {
    if(btn){ btn.style.background='#0e7490'; btn.innerHTML='&#x1F4E6; Agrupar por proveedor'; }
    if(gridFlat) gridFlat.style.display='';
    if(gridGrp)  gridGrp.style.display='none';
    renderSolicitudes();
  }
}

async function renderSolicitudesAgrupadas(){
  var grid = document.getElementById('grid-solic-grouped');
  if(!grid) return;
  var st = (document.getElementById('s-solic')||{value:'Pendiente'}).value || 'Pendiente';
  // Si filtran "Todos los estados" usamos Pendiente (no tiene sentido agrupar Aprobada/Pagada)
  var estadoQ = st || 'Pendiente';
  var catUI = _SOLIC_CAT_FILTER || 'ALL';
  // Mapear nombre de UI → categoria DB
  var catMap = {'mp':'Materia Prima','mee':'Empaque','svc':'Servicios',
                 'adm':'Administrativo','inf':'Infraestructura'};
  var catDB = catMap[catUI] || '';

  grid.innerHTML = '<div class="empty" style="padding:20px;text-align:center;color:#94a3b8;">Cargando agrupamiento...</div>';
  try{
    var qs = '?estado='+encodeURIComponent(estadoQ);
    if(catDB) qs += '&categoria='+encodeURIComponent(catDB);
    var r = await fetch('/api/compras/solicitudes-agrupadas-por-proveedor'+qs);
    if(!r.ok){
      grid.innerHTML = '<div class="empty" style="padding:20px;text-align:center;color:#dc2626;">Error '+r.status+' cargando agrupamiento</div>';
      return;
    }
    var d = await r.json();
    _GRUPOS_CACHE = d;
    if(!d.grupos.length && !(d.sin_proveedor||[]).length){
      grid.innerHTML = '<div class="empty" style="padding:30px;text-align:center;color:#86efac;font-size:14px;">&#10003; No hay solicitudes pendientes para agrupar</div>';
      return;
    }
    var html = '';
    // Header resumen
    html += '<div style="background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:12px 16px;margin-bottom:12px;display:flex;gap:16px;align-items:center;flex-wrap:wrap;">'+
      '<div><span style="font-size:24px;font-weight:800;color:#0e7490;">'+d.total_grupos+'</span> <span style="font-size:11px;color:#78716c;">proveedores</span></div>'+
      '<div><span style="font-size:24px;font-weight:800;color:#1c1917;">'+d.total_solicitudes+'</span> <span style="font-size:11px;color:#78716c;">solicitudes pendientes</span></div>'+
      '<div style="font-size:11px;color:#78716c;flex:1;text-align:right;">Click "Crear OC con todos" para procesar todas las MPs de un proveedor en una sola OC consolidada.</div>'+
    '</div>';
    // Render grupos (con proveedor)
    d.grupos.forEach(function(g, gi){
      html += _renderGrupoCard(g, gi);
    });
    // Render sin_proveedor (cards individuales agrupadas en un bloque)
    if((d.sin_proveedor||[]).length){
      html += '<div style="background:#fff7ed;border:1px solid #fdba74;border-radius:10px;padding:12px 16px;margin-top:8px;">'+
        '<div style="font-weight:700;color:#9a3412;font-size:14px;margin-bottom:8px;">'+
          '&#x26A0;&#xFE0F; '+d.sin_proveedor.length+' solicitudes sin proveedor sugerido o con proveedores mezclados'+
        '</div>'+
        '<div style="font-size:11px;color:#9a3412;margin-bottom:10px;">Estas requieren gestion manual: clic en "Ver & Gestionar" para asignar proveedor.</div>'+
        '<div style="display:flex;flex-wrap:wrap;gap:8px;">'+
          d.sin_proveedor.map(function(s){
            // Sprint Compras N2 · 21-may-2026 · botón Split visible al lado
            return '<div style="display:inline-flex;gap:4px;align-items:center;background:#fff;border:1px solid #fdba74;border-radius:6px;padding:4px 8px;font-size:11px;">'+
              '<span data-act="sdet" data-sol="'+esc(s.numero)+'" style="cursor:pointer;font-family:monospace" title="'+esc(s.urgencia||'Normal')+'">'+esc(s.numero)+' · '+esc((s.area||'-').substring(0,20))+'</span>'+
              '<button data-act="split-sol" data-sol="'+esc(s.numero)+'" style="background:#9a3412;color:#fff;border:none;padding:2px 7px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:700" title="Dividir esta SOL en N hijas, una por proveedor distinto">✂ Split</button>'+
            '</div>';
          }).join(' ')+
        '</div>'+
      '</div>';
    }
    grid.innerHTML = html;
  }catch(e){
    grid.innerHTML = '<div class="empty" style="padding:20px;text-align:center;color:#dc2626;">Error red: '+esc(e.message)+'</div>';
  }
}

function _renderGrupoCard(g, gi){
  var urgColor = {'Critico':'#dc2626','Urgente':'#d97706','Alta':'#dc2626','Media':'#d97706','Normal':'#16a34a'}[g.urgencia_max] || '#78716c';
  var totalGr = 0;
  (g.items_consolidados||[]).forEach(function(it){ totalGr += parseFloat(it.cantidad_g||0); });
  var html = '<div style="background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:0;margin-bottom:10px;overflow:hidden;">'+
    // Header
    '<div style="background:linear-gradient(90deg,#0e7490,#0891b2);color:#fff;padding:10px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;">'+
      '<div style="flex:1;">'+
        '<div style="font-weight:800;font-size:15px;">'+esc(g.proveedor)+'</div>'+
        '<div style="font-size:11px;opacity:0.9;">'+
          g.solicitudes_count+' solicitud'+(g.solicitudes_count===1?'':'es')+' &middot; '+
          g.items_count+' MPs &middot; '+
          fmt(totalGr)+' g total'+
        '</div>'+
      '</div>'+
      '<div style="background:'+urgColor+';color:#fff;padding:3px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;">'+esc(g.urgencia_max)+'</div>'+
      '<button onclick="abrirCrearOCDesdeGrupo('+gi+')" style="background:#fff;color:#0e7490;border:none;border-radius:6px;padding:8px 16px;font-size:12px;font-weight:700;cursor:pointer;">&#x1F6D2; Crear OC con todos</button>'+
      '<button onclick="abrirPedirCotizacion('+gi+')" style="background:rgba(255,255,255,0.15);color:#fff;border:1px solid rgba(255,255,255,0.4);border-radius:6px;padding:8px 14px;font-size:11px;font-weight:700;cursor:pointer" title="Pedir 3 cotizaciones a los top proveedores históricos · IA elige los mejores">&#x1F4AC; Pedir cotización</button>'+
      '<button onclick="toggleGrupo('+gi+')" id="btnTg'+gi+'" style="background:rgba(255,255,255,0.2);color:#fff;border:none;border-radius:6px;width:32px;height:32px;cursor:pointer;font-size:13px;font-weight:700;" title="Mostrar/ocultar items">&#x25BC;</button>'+
    '</div>'+
    // Body — items consolidados (oculto por defecto)
    '<div id="grpBody'+gi+'" style="display:none;padding:10px 16px;">'+
      '<div style="font-size:11px;color:#78716c;font-weight:600;margin-bottom:6px;">MATERIAS PRIMAS A COMPRAR (consolidadas):</div>'+
      '<table style="width:100%;font-size:12px;border-collapse:collapse;">'+
        '<thead><tr style="background:#f5f4f2;"><th style="text-align:left;padding:6px 8px;">Codigo</th><th style="text-align:left;padding:6px 8px;">Nombre</th><th style="text-align:right;padding:6px 8px;">Cantidad</th><th style="text-align:right;padding:6px 8px;">Valor est.</th><th style="text-align:center;padding:6px 8px;">Solicitudes</th></tr></thead>'+
        '<tbody>'+
        (g.items_consolidados||[]).map(function(it){
          var origenes = (it.solicitudes_origen||[]);
          var origStr = origenes.length<=2 ? origenes.join(', ') : origenes.length+' SOLs';
          return '<tr style="border-top:1px solid #e7e5e4;">'+
            '<td style="padding:6px 8px;font-family:monospace;font-size:11px;color:#475569;">'+esc(it.codigo_mp||'-')+'</td>'+
            '<td style="padding:6px 8px;">'+esc((it.nombre_mp||'').substring(0,50))+'</td>'+
            '<td style="padding:6px 8px;text-align:right;font-weight:600;">'+fmt(it.cantidad_g)+' g</td>'+
            '<td style="padding:6px 8px;text-align:right;color:#78716c;">'+(it.valor_estimado>0?fmt(it.valor_estimado):'-')+'</td>'+
            '<td style="padding:6px 8px;text-align:center;font-size:10px;color:#78716c;font-family:monospace;" title="'+esc((it.solicitudes_origen||[]).join(', '))+'">'+esc(origStr)+'</td>'+
          '</tr>';
        }).join('')+
        '</tbody>'+
      '</table>'+
      '<div style="font-size:11px;color:#78716c;margin-top:8px;font-style:italic;">Solicitudes incluidas: '+
        (g.solicitudes||[]).map(function(s){ return esc(s.numero); }).join(', ')+
      '</div>'+
    '</div>'+
  '</div>';
  return html;
}

function toggleGrupo(gi){
  var body = document.getElementById('grpBody'+gi);
  var btn = document.getElementById('btnTg'+gi);
  if(!body) return;
  if(body.style.display==='none'){
    body.style.display='block';
    if(btn) btn.innerHTML='&#x25B2;';
  } else {
    body.style.display='none';
    if(btn) btn.innerHTML='&#x25BC;';
  }
}

// Fase 3 · 21-may-2026 · Scorecard live de proveedor (5 métricas + score 0-100)
if(typeof document !== 'undefined' && !window._SCORECARD_DELEG){
  window._SCORECARD_DELEG = true;
  document.addEventListener('click', function(e){
    var btn = e.target.closest('[data-scorecard]');
    if(!btn) return;
    abrirScorecardProveedor(btn.getAttribute('data-scorecard'));
  });
}
async function abrirScorecardProveedor(nombre){
  var ex = document.getElementById('m-scorecard'); if(ex) ex.remove();
  var m = document.createElement('div');
  m.id = 'm-scorecard';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
  m.innerHTML = '<div style="background:#fff;border-radius:14px;padding:24px;max-width:680px;width:100%;max-height:90vh;overflow-y:auto">'+
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">'+
      '<h3 style="margin:0;color:#7c3aed">🎯 Scorecard · '+esc(nombre)+'</h3>'+
      '<button id="sc-close" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>'+
    '<div id="sc-body" style="text-align:center;color:#94a3b8;padding:30px">Calculando métricas live…</div>'+
    '</div>';
  document.body.appendChild(m);
  document.getElementById('sc-close').onclick = function(){ m.remove(); };
  m.addEventListener('click', function(e){ if(e.target === m) m.remove(); });
  try{
    var r = await fetch('/api/compras/proveedor-scorecard/'+encodeURIComponent(nombre));
    if(!r.ok){ document.getElementById('sc-body').innerHTML = '<div style="color:#dc2626;padding:20px">Error: '+r.status+'</div>'; return; }
    var d = await r.json();
    var col = d.score_color === 'verde' ? '#16a34a' : (d.score_color === 'amarillo' ? '#ca8a04' : '#dc2626');
    var html = '';
    // Header score grande
    html += '<div style="background:linear-gradient(135deg,'+col+',rgba(0,0,0,.15));color:#fff;padding:20px;border-radius:10px;margin-bottom:14px;text-align:center">';
    html += '<div style="font-size:11px;opacity:.85;text-transform:uppercase;font-weight:700">Score global</div>';
    html += '<div style="font-size:3em;font-weight:800;line-height:1;margin:6px 0">'+d.score_global+'<span style="font-size:.5em;opacity:.8">/100</span></div>';
    html += '<div style="font-size:13px;font-weight:600;opacity:.95">'+esc(d.recomendacion||'')+'</div>';
    html += '</div>';
    // 5 métricas en grid
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:14px">';
    var metricas = [
      {l:'📦 OCs 12m', v:d.ocs_total_12m, suf:''},
      {l:'💰 Monto 12m', v:'$'+(d.monto_12m||0).toLocaleString('es-CO'), suf:''},
      {l:'✅ Cumplimiento', v:d.cumplimiento_pct, suf:'%', col:d.cumplimiento_pct>=80?'#16a34a':(d.cumplimiento_pct>=50?'#ca8a04':'#dc2626')},
      {l:'⏱ On-time (≤30d)', v:d.on_time_pct, suf:'%', col:d.on_time_pct>=80?'#16a34a':(d.on_time_pct>=50?'#ca8a04':'#dc2626')},
      {l:'❌ Rechazo QC', v:d.rechazo_qc_pct, suf:'%', col:d.rechazo_qc_pct<=2?'#16a34a':(d.rechazo_qc_pct<=10?'#ca8a04':'#dc2626'), nota:d.lotes_evaluados+' lotes evaluados'},
      {l:'📈 Variación precio', v:(d.variacion_precio_12m_pct>0?'+':'')+d.variacion_precio_12m_pct, suf:'%', col:Math.abs(d.variacion_precio_12m_pct)<=10?'#16a34a':(Math.abs(d.variacion_precio_12m_pct)<=25?'#ca8a04':'#dc2626')},
      {l:'🚚 Lead time real', v:d.lead_time_real_dias, suf:'d'},
    ];
    metricas.forEach(function(m){
      var bg = m.col ? m.col : '#475569';
      html += '<div style="background:#f8fafc;border-left:4px solid '+bg+';padding:10px 12px;border-radius:6px">';
      html += '<div style="font-size:10px;color:#64748b;text-transform:uppercase;font-weight:700">'+m.l+'</div>';
      html += '<div style="font-size:1.4em;font-weight:800;color:#0f172a;margin-top:2px">'+m.v+'<span style="font-size:.65em;color:#64748b">'+(m.suf||'')+'</span></div>';
      if(m.nota) html += '<div style="font-size:9px;color:#94a3b8;margin-top:2px">'+m.nota+'</div>';
      html += '</div>';
    });
    html += '</div>';
    // Ponderación
    html += '<div style="background:#f1f5f9;padding:10px 14px;border-radius:6px;font-size:11px;color:#475569">';
    html += '<b>Ponderación score:</b> Cumplimiento 30% · On-time 25% · Sin rechazo QC 30% · Precio estable 15%';
    html += '</div>';
    document.getElementById('sc-body').innerHTML = html;
  }catch(e){
    document.getElementById('sc-body').innerHTML = '<div style="color:#dc2626;padding:20px">Error red: '+esc(e.message)+'</div>';
  }
}

// Gap bonus · 21-may-2026 · ROI proveedores 12m
// Sebastián 25-may-2026 · detector + fusionador de proveedores duplicados
async function abrirProvDuplicados(){
  var ex = document.getElementById('m-prov-dup'); if(ex) ex.remove();
  var m = document.createElement('div');
  m.id = 'm-prov-dup';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
  m.innerHTML = '<div style="background:#fff;border-radius:12px;padding:20px;max-width:900px;width:100%;max-height:90vh;overflow-y:auto">'+
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h3 style="margin:0;color:#dc2626">🔗 Detector de proveedores duplicados</h3><button id="dup-close" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>'+
    '<div style="font-size:12px;color:#64748b;margin-bottom:14px">Agrupa proveedores con el mismo nombre normalizado (mayúsculas + espacios). El destino sugerido es el que más datos tiene (NIT, banco, contacto).</div>'+
    '<div id="dup-body" style="text-align:center;color:#94a3b8;padding:30px">Cargando…</div>'+
  '</div>';
  document.body.appendChild(m);
  document.getElementById('dup-close').onclick = function(){ m.remove(); };
  try{
    var r = await fetch('/api/admin/proveedores-duplicados');
    var d = await r.json();
    if(!r.ok){ document.getElementById('dup-body').innerHTML = '<span style="color:#dc2626">Error: '+esc(d.error||r.status)+'</span>'; return; }
    if(!d.grupos || !d.grupos.length){
      document.getElementById('dup-body').innerHTML = '<div style="padding:30px;color:#15803d;font-weight:700">✓ Sin duplicados · catálogo limpio</div>';
      return;
    }
    var html = '<div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;padding:10px 14px;margin-bottom:12px;font-size:12px;color:#92400e"><b>'+d.total_grupos+'</b> grupos duplicados · <b>'+d.total_huerfanos+'</b> proveedores huérfanos para fusionar</div>';
    d.grupos.forEach(function(g, gi){
      html += '<div style="border:1px solid #e2e8f0;border-radius:8px;margin-bottom:12px;padding:12px 14px;background:#fafafa">';
      html += '<div style="font-weight:700;color:#dc2626;margin-bottom:8px">'+esc(g.key_normalizada)+' <span style="font-size:11px;color:#64748b;font-weight:400">('+g.count+' registros)</span></div>';
      html += '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#f1f5f9"><th style="text-align:left;padding:5px 8px">Nombre</th><th style="text-align:left;padding:5px 8px">NIT</th><th style="text-align:left;padding:5px 8px">Banco</th><th style="text-align:left;padding:5px 8px">Contacto</th><th style="text-align:center;padding:5px 8px">Score</th><th style="text-align:center;padding:5px 8px">Acción</th></tr></thead><tbody>';
      g.proveedores.forEach(function(p){
        var bg = p.es_destino_sugerido ? '#dcfce7' : '#fff';
        var badge = p.es_destino_sugerido ? '<span style="background:#16a34a;color:#fff;font-size:10px;padding:2px 8px;border-radius:6px;font-weight:700">DESTINO</span>' : '';
        html += '<tr style="background:'+bg+';border-bottom:1px solid #f1f5f9">';
        html += '<td style="padding:6px 8px;font-weight:600">'+esc(p.nombre)+' '+badge+'</td>';
        html += '<td style="padding:6px 8px;font-family:monospace">'+esc(p.nit||'-')+'</td>';
        html += '<td style="padding:6px 8px;font-size:11px">'+esc(p.banco||'-')+'</td>';
        html += '<td style="padding:6px 8px;font-size:11px">'+esc(p.contacto||'-')+'</td>';
        html += '<td style="padding:6px 8px;text-align:center;font-weight:700">'+p.score_completitud+'</td>';
        html += '<td style="padding:6px 8px;text-align:center">';
        if(!p.es_destino_sugerido){
          html += '<button onclick="_provFusionar(&quot;'+esc(g.destino_sugerido).replace(/"/g,'&quot;')+'&quot;,&quot;'+esc(p.nombre).replace(/"/g,'&quot;')+'&quot;)" style="background:#dc2626;color:#fff;border:0;padding:4px 10px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">→ Fusionar a destino</button>';
        }
        html += '</td></tr>';
      });
      html += '</tbody></table></div>';
    });
    document.getElementById('dup-body').innerHTML = html;
  }catch(e){
    document.getElementById('dup-body').innerHTML = '<span style="color:#dc2626">Error red: '+e.message+'</span>';
  }
}

async function _provFusionar(keeper, mergeFrom){
  if(!confirm('Fusionar "'+mergeFrom+'" → "'+keeper+'"?\\n\\nEsto:\\n· Traspasa todas las OCs, SOLs, cotizaciones, lead_times de "'+mergeFrom+'" a "'+keeper+'"\\n· Si "'+keeper+'" no tiene NIT, le copia el del huérfano\\n· Da de baja a "'+mergeFrom+'"\\n\\nIrreversible (audit log queda)')) return;
  try{
    await _ensureCsrf();  // /api/admin/* exige X-CSRF-Token (FIX 31-may)
    var r, d;
    if((keeper||'').trim().toLowerCase() === (mergeFrom||'').trim().toLowerCase()){
      // Mismo nombre exacto (2 filas, distinto id) · no se puede fusionar por
      // nombre · deduplicar por id (FIX 31-may · caso Agenquimicos)
      r = await fetch('/api/admin/proveedores-dedup-nombre', _fetchOpts('POST', {nombre: keeper}));
      d = await r.json();
      if(!r.ok || d.error){ alert('Error: '+(d.error||r.status)); return; }
      alert('✅ Duplicado exacto resuelto · se conservó 1 fila y se dio de baja '+d.n_baja+' con el mismo nombre.');
    } else {
      r = await fetch('/api/admin/proveedores-fusionar', _fetchOpts('POST', {keeper: keeper, merge_from: mergeFrom}));
      d = await r.json();
      if(!r.ok || d.error){ alert('Error: '+(d.error||r.status)); return; }
      alert('✅ Fusionado · '+d.total_filas_movidas+' filas movidas\\n\\n'+JSON.stringify(d.contadores_filas_actualizadas, null, 2));
    }
    abrirProvDuplicados();  // refresh
    loadData();
  }catch(e){ alert('Error red: '+e.message); }
}

async function abrirROIProveedores(){
  var ex = document.getElementById('m-roi-prov'); if(ex) ex.remove();
  var m = document.createElement('div');
  m.id = 'm-roi-prov';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
  m.innerHTML = '<div style="background:#fff;border-radius:12px;padding:20px;max-width:880px;width:100%;max-height:90vh;overflow-y:auto">'+
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h3 style="margin:0;color:#0e7490">📊 ROI Proveedores · últimos 12 meses</h3><button id="roi-close" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>'+
    '<div id="roi-body" style="text-align:center;color:#94a3b8;padding:20px">Cargando…</div>'+
    '</div>';
  document.body.appendChild(m);
  document.getElementById('roi-close').onclick = function(){ m.remove(); };
  m.addEventListener('click', function(e){ if(e.target === m) m.remove(); });
  try{
    var r = await fetch('/api/compras/roi-proveedores');
    var d = await r.json();
    if(!r.ok){ document.getElementById('roi-body').innerHTML = '<div style="color:#dc2626">Error: '+(d.error||r.status)+'</div>'; return; }
    var items = d.proveedores || [];
    if(!items.length){ document.getElementById('roi-body').innerHTML = '<div>Sin datos en 12 meses</div>'; return; }
    var html = '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#0f172a;color:#fff">'+
      '<th style="padding:7px;text-align:left">Proveedor</th>'+
      '<th style="padding:7px;text-align:right">OCs 12m</th>'+
      '<th style="padding:7px;text-align:right">Monto 12m</th>'+
      '<th style="padding:7px;text-align:right">Pagadas</th>'+
      '<th style="padding:7px;text-align:right">Recibidas</th>'+
      '<th style="padding:7px;text-align:right">Cumpl %</th>'+
      '<th style="padding:7px;text-align:left">Última</th>'+
    '</tr></thead><tbody>';
    items.forEach(function(p){
      var colCump = p.cumplimiento_pct >= 80 ? '#16a34a' : (p.cumplimiento_pct >= 50 ? '#ca8a04' : '#dc2626');
      html += '<tr style="border-bottom:1px solid #e2e8f0">'+
        '<td style="padding:6px;font-weight:600">'+esc(p.proveedor)+'</td>'+
        '<td style="padding:6px;text-align:right">'+p.ocs_12m+'</td>'+
        '<td style="padding:6px;text-align:right;font-weight:700">'+fmt(p.monto_12m.toFixed(0))+'</td>'+
        '<td style="padding:6px;text-align:right">'+p.pagadas+'</td>'+
        '<td style="padding:6px;text-align:right">'+p.recibidas+'</td>'+
        '<td style="padding:6px;text-align:right;color:'+colCump+';font-weight:700">'+p.cumplimiento_pct+'%</td>'+
        '<td style="padding:6px;font-size:11px;color:#64748b">'+esc((p.ultima_compra||'').substring(0,10))+'</td>'+
      '</tr>';
    });
    html += '</tbody></table>';
    html += '<div style="margin-top:10px;font-size:11px;color:#64748b">Verde >=80% · Ámbar 50-79% · Rojo <50% cumplimiento (recibidas/total)</div>';
    document.getElementById('roi-body').innerHTML = html;
  }catch(e){ document.getElementById('roi-body').innerHTML = '<div style="color:#dc2626">Error red: '+e.message+'</div>'; }
}

// Gap #3 · 21-may-2026 · OCR factura proveedor con Claude Vision
function abrirOCRFactura(){
  var ex = document.getElementById('m-ocr-fact'); if(ex) ex.remove();
  var m = document.createElement('div');
  m.id = 'm-ocr-fact';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
  m.innerHTML = '<div style="background:#fff;border-radius:12px;padding:20px;max-width:720px;width:100%;max-height:90vh;overflow-y:auto">'+
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><h3 style="margin:0;color:#7c3aed">📤 Subir factura del proveedor</h3>'+
    '<button id="ocr-close" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>'+
    '<div style="background:#faf5ff;border:1px solid #7c3aed;padding:10px 12px;border-radius:6px;margin-bottom:12px;font-size:12px;color:#5b21b6">La IA Vision (Claude 4.6) extraerá automáticamente: proveedor · NIT · número factura · items · totales · IVA. Después sugiere match con OC pendiente.</div>'+
    '<input type="file" id="ocr-file" accept="image/jpeg,image/png" style="margin-bottom:12px">'+
    '<button id="ocr-process" style="background:#7c3aed;color:#fff;padding:10px 20px;border:none;border-radius:6px;font-weight:700;cursor:pointer">🔍 Procesar factura</button>'+
    '<div id="ocr-result" style="margin-top:16px"></div>'+
    '</div>';
  document.body.appendChild(m);
  document.getElementById('ocr-close').onclick = function(){ m.remove(); };
  m.addEventListener('click', function(e){ if(e.target === m) m.remove(); });
  document.getElementById('ocr-process').onclick = async function(){
    var fp = document.getElementById('ocr-file');
    if(!fp.files.length){ alert('Elegí una imagen primero'); return; }
    var file = fp.files[0];
    if(file.size > 5 * 1024 * 1024){ alert('Imagen muy grande · max 5MB'); return; }
    var btn = this; btn.disabled = true; btn.textContent = 'Procesando…';
    var resultDiv = document.getElementById('ocr-result');
    resultDiv.innerHTML = '<div style="text-align:center;padding:20px;color:#7c3aed">⏳ La IA está leyendo la factura · ~15-30s...</div>';
    var reader = new FileReader();
    reader.onload = async function(e){
      var b64 = e.target.result.split(',')[1];
      var tipo = file.type.includes('png') ? 'png' : 'jpeg';
      try{
        var r = await fetch('/api/compras/ocr-factura', _fetchOpts('POST', {
          imagen_base64: b64, tipo: tipo,
        }));
        var d = await r.json();
        if(!r.ok){
          resultDiv.innerHTML = '<div style="background:#fee2e2;color:#991b1b;padding:12px;border-radius:6px">Error: '+esc(d.error||r.status)+'</div>';
          btn.disabled = false; btn.textContent = '🔍 Procesar factura';
          return;
        }
        var f = d.factura || {};
        var ocs = d.ocs_sugeridas || [];
        // Bug #5 fix · 21-may-2026 · alerta visual según confianza
        var conf = f.confianza_pct || 0;
        var confBg, confColor, confLabel;
        if(conf >= 80){ confBg='#dcfce7'; confColor='#166534'; confLabel='✓ Factura procesada'; }
        else if(conf >= 50){ confBg='#fef3c7'; confColor='#78350f'; confLabel='⚠ REVISAR MANUAL · datos pueden estar incompletos'; }
        else{ confBg='#fee2e2'; confColor='#991b1b'; confLabel='🚨 BAJA CONFIANZA · validar TODO antes de usar'; }
        var html = '<div style="background:'+confBg+';color:'+confColor+';padding:10px;border-radius:6px;margin-bottom:12px;font-weight:700">'+confLabel+' · confianza '+conf+'%</div>';
        html += '<div style="background:#f8fafc;padding:12px;border-radius:6px;margin-bottom:12px"><b>Datos extraídos:</b>';
        html += '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:6px;margin-top:6px;font-size:12px">';
        html += '<div><b>Proveedor:</b><br>'+esc(f.proveedor||'—')+'</div>';
        html += '<div><b>NIT:</b><br>'+esc(f.nit||'—')+'</div>';
        html += '<div><b>N° Factura:</b><br><span style="font-family:monospace;color:#7c3aed;font-weight:700">'+esc(f.numero_factura||'—')+'</span></div>';
        html += '<div><b>Fecha:</b><br>'+esc(f.fecha_emision||'—')+'</div>';
        html += '<div><b>Subtotal:</b><br>'+fmt((f.subtotal||0).toFixed(0))+'</div>';
        html += '<div><b>IVA:</b><br>'+fmt((f.iva||0).toFixed(0))+'</div>';
        html += '<div style="grid-column:span 2"><b>Total:</b><br><span style="font-size:20px;font-weight:800;color:#7c3aed">'+fmt((f.total||0).toFixed(0))+'</span></div>';
        html += '</div></div>';
        if((f.items||[]).length){
          html += '<div style="background:#fff;border:1px solid #e2e8f0;padding:10px;border-radius:6px;margin-bottom:12px"><b style="font-size:12px">Items ('+f.items.length+'):</b>';
          html += '<table style="width:100%;font-size:11px;margin-top:6px;border-collapse:collapse">';
          html += '<thead><tr style="background:#f1f5f9"><th style="padding:4px 6px;text-align:left">Desc</th><th style="padding:4px 6px;text-align:right">Cant</th><th style="padding:4px 6px;text-align:right">$ unit</th><th style="padding:4px 6px;text-align:right">Sub</th></tr></thead><tbody>';
          f.items.forEach(function(it){
            html += '<tr><td style="padding:3px 6px">'+esc(it.descripcion||'')+'</td><td style="padding:3px 6px;text-align:right">'+(it.cantidad||0)+' '+esc(it.unidad||'')+'</td><td style="padding:3px 6px;text-align:right">'+fmt((it.precio_unitario||0).toFixed(0))+'</td><td style="padding:3px 6px;text-align:right;font-weight:700">'+fmt((it.subtotal||0).toFixed(0))+'</td></tr>';
          });
          html += '</tbody></table></div>';
        }
        if(ocs.length){
          html += '<div style="background:#fef3c7;border:1px solid #ca8a04;padding:12px;border-radius:6px"><b style="color:#78350f;font-size:13px">🔗 OCs pendientes del mismo proveedor:</b>';
          ocs.forEach(function(oc){
            var colMatch = oc.match_score === 'alto' ? '#16a34a' : (oc.match_score === 'medio' ? '#ca8a04' : '#94a3b8');
            html += '<div style="background:#fff;border-left:3px solid '+colMatch+';padding:8px 10px;margin-top:6px;display:flex;justify-content:space-between;align-items:center"><div><b style="font-family:monospace">'+esc(oc.numero_oc)+'</b> · '+esc(oc.proveedor)+' · estado '+esc(oc.estado)+'<br><span style="font-size:10px;color:#94a3b8">OC: '+fmt(oc.valor_total.toFixed(0))+' vs Factura: '+fmt((f.total||0).toFixed(0))+' · Δ '+oc.delta_vs_factura_pct+'%</span></div><span style="background:'+colMatch+';color:#fff;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700">match '+oc.match_score+'</span></div>';
          });
          html += '</div>';
        } else {
          html += '<div style="background:#fef2f2;color:#991b1b;padding:10px;border-radius:6px;font-size:12px">⚠ No se encontraron OCs pendientes con el proveedor "'+esc(f.proveedor||'')+'" · revisar manualmente.</div>';
        }
        resultDiv.innerHTML = html;
        btn.disabled = false; btn.textContent = '🔍 Procesar otra factura';
      }catch(e){
        resultDiv.innerHTML = '<div style="background:#fee2e2;color:#991b1b;padding:12px;border-radius:6px">Error red: '+esc(e.message)+'</div>';
        btn.disabled = false; btn.textContent = '🔍 Procesar factura';
      }
    };
    reader.readAsDataURL(file);
  };
}

// CRITICA-3 fix · 21-may-2026 · wrappers para Planta que usan PLANTA_GRUPOS
// (no _GRUPOS_CACHE que vive en otra pestaña).
window.abrirCrearOCDesdeGrupoPlanta = async function(idx){
  if(!PLANTA_GRUPOS || !PLANTA_GRUPOS[idx]){ alert('Card no disponible · recargá Planta'); return; }
  // Inyectar temporalmente en _GRUPOS_CACHE para reusar la función existente
  _GRUPOS_CACHE = _GRUPOS_CACHE || {grupos: []};
  _GRUPOS_CACHE.grupos = _GRUPOS_CACHE.grupos || [];
  _GRUPOS_CACHE.grupos[idx] = PLANTA_GRUPOS[idx];
  return abrirCrearOCDesdeGrupo(idx);
};
window.abrirPedirCotizacionPlanta = async function(idx){
  if(!PLANTA_GRUPOS || !PLANTA_GRUPOS[idx]){ alert('Card no disponible · recargá Planta'); return; }
  _GRUPOS_CACHE = _GRUPOS_CACHE || {grupos: []};
  _GRUPOS_CACHE.grupos = _GRUPOS_CACHE.grupos || [];
  _GRUPOS_CACHE.grupos[idx] = PLANTA_GRUPOS[idx];
  return abrirPedirCotizacion(idx);
};

// Gap #2 · 21-may-2026 · Pedir cotización a top 3 proveedores históricos
async function abrirPedirCotizacion(gi){
  if(!_GRUPOS_CACHE || !_GRUPOS_CACHE.grupos[gi]) return;
  var g = _GRUPOS_CACHE.grupos[gi];
  var items = (g.items_consolidados||[]).map(function(it){
    return {codigo_mp: it.codigo_mp, nombre_mp: it.nombre_mp, cantidad_g: parseFloat(it.cantidad_g||0)};
  });
  if(!items.length){ alert('Sin items en este grupo'); return; }
  // Abrir modal preview
  var ex = document.getElementById('m-cot-preview'); if(ex) ex.remove();
  var m = document.createElement('div');
  m.id = 'm-cot-preview';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
  m.innerHTML = '<div style="background:#fff;border-radius:12px;padding:20px;max-width:600px;width:100%;max-height:90vh;overflow-y:auto">'+
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><h3 style="margin:0;color:#0e7490">💬 Pedir cotización · 3 proveedores</h3><button id="cot-close" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>'+
    '<div style="background:#f0f9ff;border:1px solid #0891b2;padding:10px 12px;border-radius:6px;margin-bottom:12px;font-size:12px;color:#0c4a6e">La IA detecta los top 3 proveedores históricos que han vendido los MPs del grupo · creará una ronda y vos enviás manualmente (email/WhatsApp) y registrás las respuestas cuando vuelvan.</div>'+
    '<div style="background:#f8fafc;padding:10px 12px;border-radius:6px;margin-bottom:12px;font-size:12px">'+
      '<b style="color:#475569">Grupo: '+esc(g.proveedor)+'</b><br>'+
      g.solicitudes_count+' SOLs · '+g.items_count+' MPs · '+items.length+' productos'+
    '</div>'+
    '<div><label style="font-size:12px;font-weight:600;color:#475569">Observaciones para la cotización (opcional)</label>'+
    '<textarea id="cot-obs" rows="2" placeholder="Ej: necesito entrega antes del 15-jun · piden volumen X" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:5px;margin-top:4px;font-size:12px"></textarea></div>'+
    '<div id="cot-preview" style="margin-top:12px"></div>'+
    '<div style="margin-top:14px;display:flex;gap:8px;justify-content:flex-end">'+
      '<button id="cot-cancel" style="background:#94a3b8;color:#fff;padding:8px 16px;border:none;border-radius:6px;cursor:pointer">Cancelar</button>'+
      '<button id="cot-crear" style="background:#0e7490;color:#fff;padding:8px 20px;border:none;border-radius:6px;font-weight:700;cursor:pointer">💬 Crear ronda con top 3</button>'+
    '</div></div>';
  document.body.appendChild(m);
  document.getElementById('cot-close').onclick = function(){ m.remove(); };
  document.getElementById('cot-cancel').onclick = function(){ m.remove(); };
  m.addEventListener('click', function(e){ if(e.target === m) m.remove(); });
  document.getElementById('cot-crear').onclick = async function(){
    var btn = this; btn.disabled = true; btn.textContent = 'Creando...';
    var obs = (document.getElementById('cot-obs')||{value:''}).value.trim();
    try{
      var r = await fetch('/api/compras/cotizaciones/desde-grupo', _fetchOpts('POST', {
        proveedor_sugerido: g.proveedor,
        items: items,
        observaciones: obs,
      }));
      var d = await r.json();
      if(!r.ok){
        var det = '';
        if((d.top_encontrados||[]).length) det = '\\n\\nProveedores en histórico: '+(d.top_encontrados||[]).map(function(p){return p.nombre;}).join(', ')+'\\n\\nNecesitás al menos 2 proveedores con histórico.';
        alert('Error: '+(d.error||r.status)+det);
        btn.disabled = false; btn.textContent = '💬 Crear ronda con top 3';
        return;
      }
      // Mostrar preview de ronda creada
      var prevHtml = '<div style="background:#dcfce7;color:#166534;padding:12px;border-radius:6px;margin-top:10px;font-weight:700">✓ Ronda '+d.ronda_id+' creada</div>';
      prevHtml += '<div style="margin-top:10px;font-size:12px"><b>Proveedores a contactar:</b><br>';
      (d.cotizaciones||[]).forEach(function(c){
        prevHtml += '<div style="background:#fff;border:1px solid #cbd5e1;padding:6px 10px;border-radius:5px;margin-top:4px;display:flex;justify-content:space-between"><span><b>'+esc(c.proveedor)+'</b></span><span style="color:#94a3b8;font-size:10px">COT-ID '+c.id+'</span></div>';
      });
      prevHtml += '</div>';
      prevHtml += '<div style="margin-top:10px;background:#fef3c7;color:#78350f;padding:10px;border-radius:6px;font-size:12px"><b>📧 Siguiente paso:</b><br>Enviar a cada proveedor el detalle de items · pedir precio · plazo · cuando respondan, vas a "Cotizaciones" para registrar las respuestas y elegir ganadora.</div>';
      document.getElementById('cot-preview').innerHTML = prevHtml;
      btn.style.display = 'none';
      document.getElementById('cot-cancel').textContent = 'Cerrar';
    }catch(e){
      alert('Error red: '+e.message);
      btn.disabled = false; btn.textContent = '💬 Crear ronda con top 3';
    }
  };
}

// Sprint Compras N2 · 21-may-2026 · modal preview con comparador precios
async function abrirCrearOCDesdeGrupo(gi){
  if(!_GRUPOS_CACHE || !_GRUPOS_CACHE.grupos[gi]) return;
  var g = _GRUPOS_CACHE.grupos[gi];
  var nums = (g.solicitudes||[]).map(function(s){ return s.numero; });
  // Preview modal con tabla items + delta precio vs histórico
  var hist = window.PLANTA_PRECIOS_HIST || {};
  var totalOC = 0;
  var rowsHtml = (g.items_consolidados||[]).map(function(it){
    var cant = parseFloat(it.cantidad_g||0);
    var val = parseFloat(it.valor_estimado||0);
    var pu = cant > 0 ? (val / cant) : 0;
    totalOC += val;
    var h = hist[it.codigo_mp];
    var deltaCell = '<span style="color:#cbd5e1">—</span>';
    if(h && h.precio_promedio_90d > 0 && pu > 0){
      var delta = ((pu - h.precio_promedio_90d) / h.precio_promedio_90d) * 100;
      var color = delta > 15 ? '#dc2626' : (delta > 5 ? '#ca8a04' : (delta < -5 ? '#16a34a' : '#475569'));
      var sign = delta > 0 ? '+' : '';
      deltaCell = '<span style="color:'+color+';font-weight:700">'+sign+delta.toFixed(1)+'%</span>';
    }
    var histPrice = (h && h.precio_promedio_90d > 0) ? ('$'+h.precio_promedio_90d.toFixed(3)+'/g') : '<span style="color:#cbd5e1">sin hist.</span>';
    return '<tr style="border-bottom:1px solid #f1f5f9">'+
      '<td style="padding:5px 8px;font-size:11px"><b>'+esc(it.nombre_mp||'')+'</b><br><span style="color:#94a3b8;font-family:monospace;font-size:10px">'+esc(it.codigo_mp||'')+'</span></td>'+
      '<td style="padding:5px 8px;text-align:right;font-size:11px">'+fmt(cant)+' g</td>'+
      '<td style="padding:5px 8px;text-align:right;font-size:11px">$'+pu.toFixed(3)+'/g</td>'+
      '<td style="padding:5px 8px;text-align:right;font-size:11px">'+histPrice+'</td>'+
      '<td style="padding:5px 8px;text-align:right">'+deltaCell+'</td>'+
      '<td style="padding:5px 8px;text-align:right;font-size:11px;font-weight:700">'+fmt(val.toFixed(0))+'</td>'+
    '</tr>';
  }).join('');
  // Modal
  var ex = document.getElementById('m-oc-preview'); if(ex) ex.remove();
  var m = document.createElement('div');
  m.id = 'm-oc-preview';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9998;display:flex;align-items:center;justify-content:center;padding:20px';
  m.innerHTML = '<div style="background:#fff;border-radius:12px;padding:20px;max-width:900px;width:100%;max-height:90vh;overflow-y:auto">'+
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h3 style="margin:0;color:#0e7490">🛒 Confirmar OC · '+esc(g.proveedor)+'</h3>'+
    '<button id="oc-prev-close" style="background:none;border:none;font-size:1.4em;cursor:pointer">×</button></div>'+
    '<div style="background:#f0f9ff;border:1px solid #0891b2;padding:8px 12px;border-radius:6px;margin-bottom:12px;font-size:12px;color:#0c4a6e">'+
      '<b>'+g.solicitudes_count+' SOLs</b> · <b>'+g.items_count+' MPs</b> · vincular y aprobar'+
    '</div>'+
    '<table style="width:100%;border-collapse:collapse">'+
      '<thead><tr style="background:#0f172a;color:#fff"><th style="padding:6px 8px;text-align:left">MP</th><th style="padding:6px 8px;text-align:right">Cant</th><th style="padding:6px 8px;text-align:right">$ nuevo</th><th style="padding:6px 8px;text-align:right">$ prom 90d</th><th style="padding:6px 8px;text-align:right">Δ%</th><th style="padding:6px 8px;text-align:right">Subtotal</th></tr></thead>'+
      '<tbody>'+rowsHtml+'</tbody>'+
      '<tfoot><tr style="background:#f1f5f9;font-weight:700"><td colspan="5" style="padding:8px;text-align:right">TOTAL OC</td><td style="padding:8px;text-align:right">'+fmt(totalOC.toFixed(0))+'</td></tr></tfoot>'+
    '</table>'+
    '<div style="margin-top:10px;font-size:11px;color:#64748b;display:flex;gap:14px;flex-wrap:wrap">'+
      '<span><span style="color:#16a34a;font-weight:700">verde</span>: precio bajó 5%+</span>'+
      '<span><span style="color:#ca8a04;font-weight:700">ámbar</span>: subió 5-15%</span>'+
      '<span><span style="color:#dc2626;font-weight:700">rojo</span>: subió >15% (revisar)</span>'+
    '</div>'+
    '<div style="margin-top:14px;display:flex;gap:8px;justify-content:flex-end">'+
      '<button id="oc-prev-cancel" style="background:#94a3b8;color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer">Cancelar</button>'+
      '<button id="oc-prev-confirm" style="background:#0e7490;color:#fff;border:none;padding:8px 20px;border-radius:6px;font-weight:700;cursor:pointer">✓ Confirmar y crear OC</button>'+
    '</div>'+
    '</div>';
  document.body.appendChild(m);
  document.getElementById('oc-prev-close').onclick = function(){ m.remove(); };
  document.getElementById('oc-prev-cancel').onclick = function(){ m.remove(); };
  m.addEventListener('click', function(e){ if(e.target === m) m.remove(); });
  document.getElementById('oc-prev-confirm').onclick = async function(){
    var btn = this; btn.disabled = true; btn.textContent = 'Creando...';
    try{
      var r = await fetch('/api/compras/oc-desde-solicitudes', _fetchOpts('POST', {
        proveedor: g.proveedor,
        solicitudes: nums,
        consolidar_iguales: true,
        categoria: 'MP',
      }));
      var d = await r.json();
      if(!r.ok || d.error){
        var det = '';
        if(d.codigo === 'EXCEDE_LIMITE_APROBACION'){
          det = '\\n\\nMonto solicitado: '+fmt(d.monto_solicitado||0)+'\\nTu límite: '+fmt(d.limite_usuario||0)+'\\n\\nPedíle a un admin que la cree o autorice.';
        }
        if(d.detalle) det += '\\n\\n'+d.detalle;
        alert('Error creando OC: '+(d.error || 'codigo '+r.status)+det);
        btn.disabled = false; btn.textContent = '✓ Confirmar y crear OC';
        return;
      }
      alert('✓ OC '+d.numero_oc+' creada\\n'+(d.solicitudes_vinculadas||0)+' SOLs vinculadas\\n'+(d.items_creados||0)+' items\\nTotal: '+fmt(d.valor_total||0));
      m.remove();
      if(typeof loadData==='function') await loadData();
      if(typeof renderSolicitudesAgrupadas==='function') await renderSolicitudesAgrupadas();
      if(typeof loadPlanta==='function') await loadPlanta();
    }catch(e){
      alert('Error red: '+e.message);
      btn.disabled = false; btn.textContent = '✓ Confirmar y crear OC';
    }
  };
}

function renderCCSolicitudes(){
  var pend=CC_SOLIC.filter(function(s){ return s.estado==='Pendiente'; });
  var badge=document.getElementById('cc-solic-badge');
  if(badge) badge.textContent=pend.length;
  var pills=document.getElementById('pills-cc-solic');
  var grid=document.getElementById('grid-cc-solic');
  if(!grid) return;
  if(!pend.length){
    if(pills) pills.innerHTML='';
    grid.innerHTML='<div class="empty" style="color:#86efac;">&#10003; Sin solicitudes pendientes</div>';
    return;
  }
  if(pills) pills.innerHTML='<span class="pill y">Pendiente: '+pend.length+'</span>';
  var urgColor={'Normal':'#16a34a','Urgente':'#d97706','Critico':'#dc2626'};
  grid.innerHTML=pend.map(function(s){
    var urg=s.urgencia||'Normal';
    var urgC=urgColor[urg]||'#78716c';
    var obs=(s.observaciones||'').substring(0,100);
    var val=s.valor>0?(' &mdash; '+fmoney(s.valor)):'';  
    return '<div class="card" style="border-left:3px solid #f59e0b;">'
      +'<div class="ch"><div><div class="cnum" style="font-family:monospace;">'+esc(s.numero)+'</div>'
      +'<div class="cprov">'+esc(s.solicitante||'-')+' &mdash; '+esc(s.area||'-')+'</div></div>'
      +'<span class="badge" style="background:#fef3c7;color:#92400e;">Pendiente</span></div>'
      +'<div class="cmeta"><span>'+fdate(s.fecha)+'</span><span>'+esc(s.empresa||'Espagiria')+'</span>'
      +'<span style="color:'+urgC+';font-weight:700;">'+esc(urg)+'</span>'
      +(s.fecha_requerida?'<span>Req: '+fdate(s.fecha_requerida)+'</span>':'')+'</div>'
      +(obs?'<div class="cobs">'+esc(obs)+'</div>':'')
      +'<div class="acts" style="gap:6px;"><button class="btn bo bs" data-act="sdet" data-sol="'+esc(s.numero)+'">&#x1F4CB; Revisar &amp; Aprobar</button><button class="btn" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;padding:4px 10px;font-size:11px;" data-act="del-sol" data-sol="'+esc(s.numero)+'">&#x1F5D1;</button></div>'
      +'</div>';
  }).join('');
}
async function openSolicitudDetail(num){

  openModal('m-sol-det');
  var body=document.getElementById('sol-det-body');
  var footer=document.getElementById('sol-det-footer');
  body.innerHTML='<div style="text-align:center;padding:40px;color:#78716c;">Cargando...</div>';
  footer.innerHTML='<button class="btn bo" onclick="_solDetClose()">Cerrar</button>';
  try{
    var r=await fetch('/api/solicitudes-compra/'+encodeURIComponent(num));
    var d=await r.json();
    if(d.error){ body.innerHTML='<p style="color:#dc2626;">'+esc(d.error)+'</p>'; return; }
    var s=d.solicitud||{};
    var items=d.items||[];
    var oc=d.oc||null;
    var stBg={'Pendiente':'#fef3c7','Aprobada':'#dcfce7','Rechazada':'#fee2e2','Pagada':'#dbeafe'};
    var stFg={'Pendiente':'#92400e','Aprobada':'#166534','Rechazada':'#991b1b','Pagada':'#1e40af'};
    var urgColor={'Alta':'#dc2626','Urgente':'#b91c1c','Normal':'#0891b2','Baja':'#6b7280'};

    var h='<div style="padding:0;background:#fff;">';
    // Header con paleta teal HHA
    h+='<div style="background:linear-gradient(135deg,#1F5F5B 0%,#10464a 100%);padding:18px 22px;color:#fff;">';
    h+='<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">';
    h+='<div style="display:flex;align-items:center;gap:14px;">';
    h+='<div style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:1px;">SOLICITUD DE COMPRA</div>';
    h+='</div>';
    h+='<span style="background:'+(stBg[s.estado]||'#f3f4f6')+';color:'+(stFg[s.estado]||'#374151')+';font-size:11px;font-weight:700;padding:5px 12px;border-radius:14px;letter-spacing:.4px;">'+esc((s.estado||'').toUpperCase())+'</span>';
    h+='</div>';
    h+='<div style="font-weight:800;font-size:24px;font-family:monospace;letter-spacing:.5px;margin-top:4px;">'+esc(s.numero||num)+'</div>';
    h+='<div style="display:flex;gap:18px;flex-wrap:wrap;font-size:12px;opacity:.92;margin-top:4px;">';
    h+='<span>👤 '+esc(s.solicitante||'-')+'</span>';
    h+='<span>🏭 '+esc(s.area||'-')+' · '+esc(s.empresa||'Espagiria')+'</span>';
    h+='<span>📅 '+fdate(s.fecha)+'</span>';
    h+='<span style="background:rgba(255,255,255,.15);padding:1px 8px;border-radius:6px;color:'+(urgColor[s.urgencia]||'#fff')+';background:rgba(255,255,255,.18);">⚡ '+esc(s.urgencia||'Normal')+'</span>';
    h+='</div>';
    h+='</div>';

    // Cuerpo
    h+='<div style="padding:24px 28px;">';

    // ── PROVEEDOR INTERACTIVO ─────────────────────────────────────────
    // Card del proveedor con acciones inline: Confirmar (verde) / Cambiar.
    // Esto reemplaza al "selector + valor + fecha" que vivía abajo.
    // Sirve para alimentar el sistema cuando Catalina valida/corrige.
    var provName = (oc && oc.proveedor) ? oc.proveedor : '';
    var ocNum = oc ? esc(oc.numero_oc) : '';
    if(provName && oc){
      h+='<div id="prov-card" data-oc="'+ocNum+'" style="background:linear-gradient(135deg,#f0fdfa 0%,#ccfbf1 100%);border:1px solid #5eead4;border-radius:12px;padding:16px 22px;margin-bottom:18px;box-shadow:0 1px 3px rgba(15,118,110,.08);">';
      h+='<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">';
      h+='<div style="display:flex;align-items:center;gap:14px;">';
      h+='<div style="font-size:34px;line-height:1;">🏢</div>';
      h+='<div>';
      h+='<div style="font-size:10px;color:#0f766e;text-transform:uppercase;letter-spacing:1px;font-weight:700;">PROVEEDOR SUGERIDO</div>';
      h+='<div id="prov-card-name" style="font-size:22px;font-weight:800;color:#0f766e;letter-spacing:.3px;margin-top:2px;">'+esc(provName)+'</div>';
      h+='</div>';
      h+='</div>';
      // Acciones (solo si la SOL está pendiente) + Valor total
      if(s.estado === 'Pendiente'){
        h+='<div style="display:flex;gap:8px;align-items:center;">';
        h+='<button id="btn-confirmar-prov" onclick="confirmarProveedorOC(&quot;'+ocNum+'&quot;)" style="background:#16a34a;color:#fff;border:none;border-radius:8px;padding:8px 14px;font-size:12px;font-weight:700;cursor:pointer;">✓ Confirmar</button>';
        h+='<button onclick="abrirCambiarProveedor()" style="background:#fff;color:#0f766e;border:1px solid #5eead4;border-radius:8px;padding:8px 14px;font-size:12px;font-weight:700;cursor:pointer;">↻ Cambiar</button>';
        h+='</div>';
      } else if(oc.valor_total > 0){
        h+='<div style="text-align:right;">';
        h+='<div style="font-size:10px;color:#0f766e;text-transform:uppercase;letter-spacing:.6px;font-weight:700;">Valor total OC</div>';
        h+='<div style="font-size:24px;font-weight:800;color:#0f766e;">'+fmt(oc.valor_total)+'</div>';
        h+='</div>';
      }
      h+='</div>';
      // Selector inline (oculto por defecto)
      h+='<div id="prov-cambiar-box" style="display:none;margin-top:12px;padding-top:12px;border-top:1px dashed #5eead4;">';
      h+='<div style="font-size:11px;color:#0f766e;font-weight:700;text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px;">Cambiar proveedor</div>';
      h+='<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">';
      h+='<input id="prov-cambiar-input" list="prov-dl-detail" placeholder="Nombre del proveedor..." style="flex:1;min-width:200px;padding:8px 12px;border:1px solid #5eead4;border-radius:8px;font-size:13px;">';
      h+='<datalist id="prov-dl-detail">';
      PROVS.forEach(function(p){ h+='<option value="'+esc(p.nombre)+'">'; });
      h+='</datalist>';
      h+='<button onclick="guardarCambioProveedor(&quot;'+ocNum+'&quot;)" style="background:#0f766e;color:#fff;border:none;border-radius:8px;padding:8px 16px;font-size:12px;font-weight:700;cursor:pointer;">Guardar</button>';
      h+='<button onclick="document.getElementById(&quot;prov-cambiar-box&quot;).style.display=&quot;none&quot;" style="background:#fff;color:#64748b;border:1px solid #cbd5e1;border-radius:8px;padding:8px 14px;font-size:12px;cursor:pointer;">Cancelar</button>';
      h+='</div>';
      h+='<div style="font-size:11px;color:#64748b;margin-top:6px;">Si el proveedor no existe se crea automáticamente y queda en el catálogo para próximos pedidos.</div>';
      h+='</div>';
      h+='</div>';
    } else if(oc){
      // OC existe pero sin proveedor asignado — selector grande para asignar
      h+='<div id="prov-card" style="background:#fef2f2;border:1px solid #fca5a5;border-radius:12px;padding:14px 22px;margin-bottom:18px;">';
      h+='<div style="font-size:11px;color:#991b1b;text-transform:uppercase;letter-spacing:.6px;font-weight:700;margin-bottom:8px;">⚠ Sin proveedor asignado</div>';
      if(s.estado==='Pendiente'){
        h+='<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">';
        h+='<input id="prov-cambiar-input" list="prov-dl-detail" placeholder="Asigna un proveedor..." style="flex:1;min-width:240px;padding:8px 12px;border:1px solid #fca5a5;border-radius:8px;font-size:13px;">';
        h+='<datalist id="prov-dl-detail">';
        PROVS.forEach(function(p){ h+='<option value="'+esc(p.nombre)+'">'; });
        h+='</datalist>';
        h+='<button onclick="guardarCambioProveedor(&quot;'+esc(oc.numero_oc)+'&quot;)" style="background:#dc2626;color:#fff;border:none;border-radius:8px;padding:8px 16px;font-size:12px;font-weight:700;cursor:pointer;">Asignar y guardar</button>';
        h+='</div>';
      } else {
        h+='<div style="font-size:13px;color:#7f1d1d;">Definir proveedor antes de avanzar la OC '+esc(oc.numero_oc)+'</div>';
      }
      h+='</div>';
    }

    // ── INFO COMPACTA (categoria, tipo, OC, fecha req) en 1 línea ────
    h+='<div style="display:flex;gap:24px;flex-wrap:wrap;font-size:12px;margin-bottom:18px;padding:8px 14px;background:#fafaf9;border-radius:6px;">';
    h+='<span><span style="color:#78716c;">Categoría:</span> <strong>'+esc(s.categoria||'-')+'</strong></span>';
    if(oc && oc.numero_oc) h+='<span><span style="color:#78716c;">OC:</span> <strong style="font-family:monospace;color:#0f766e;">'+esc(oc.numero_oc)+'</strong></span>';
    if(s.aprobado_por) h+='<span><span style="color:#78716c;">Gestionado por:</span> <strong>'+esc(s.aprobado_por)+'</strong></span>';
    if(s.fecha_requerida) h+='<span><span style="color:#78716c;">Fecha req:</span> <strong>'+esc(s.fecha_requerida)+'</strong></span>';
    h+='</div>';
    // Detalle/justificación de la solicitud (la nota que escribió el solicitante · 18-jun:
    // antes el modal no la mostraba → Catalina no veía QUÉ se pide). No se muestra si las
    // observaciones son metadatos de pago (BANCO:...) · eso va en el resumen de pago abajo.
    if(s.observaciones && s.observaciones.indexOf('BANCO:')<0){
      h+='<div style="margin-bottom:16px;background:#f8fafc;border-left:3px solid #1F5F5B;border-radius:6px;padding:12px 14px;">';
      h+='<div style="font-size:10px;color:#1F5F5B;text-transform:uppercase;letter-spacing:.6px;font-weight:700;margin-bottom:4px;">&#x1F4DD; Detalle de la solicitud</div>';
      h+='<div style="font-size:13px;color:#44403c;white-space:pre-wrap;">'+esc(s.observaciones)+'</div></div>';
    }
    // ── Payment summary for non-pending solicitudes ──
    if(s.estado!=='Pendiente'&&s.observaciones&&s.observaciones.indexOf('BANCO:')>=0){
      var _obs=s.observaciones;
      function _xtr(key){
        var idx=_obs.indexOf(key+':');
        if(idx<0) return '';
        var rest=_obs.slice(idx+key.length+1).trim();
        var end=rest.indexOf(' | ');
        return end>=0?rest.slice(0,end).trim():rest.trim();
      }
      var _ben=_xtr('BENEFICIARIO')||_xtr('BENEFICIARIO');
      var _ban=_xtr('BANCO');
      var _cta=_xtr('CUENTA/CEL');
      var _ced=_xtr('CED/NIT');
      var _val=_xtr('VALOR');
      if(_ban||_cta){
        h+='<div style="margin-top:12px;background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:12px;">';
        h+='<div style="font-weight:800;font-size:12px;color:#166534;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">&#x1F4B3; Datos de Pago</div>';
        h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;font-size:12px;">';
        if(_ben) h+='<div style="grid-column:span 2;"><span style="color:#166534;font-weight:600;">Beneficiario:</span> <strong>'+esc(_ben)+'</strong></div>';
        if(_ban) h+='<div><span style="color:#166534;font-weight:600;">Banco:</span> <strong>'+esc(_ban)+'</strong></div>';
        if(_cta) h+='<div><span style="color:#166534;font-weight:600;">Cuenta/Cel:</span> <strong style="font-family:monospace;">'+esc(_cta)+'</strong></div>';
        if(_ced) h+='<div><span style="color:#166534;font-weight:600;">NIT/CC:</span> '+esc(_ced)+'</div>';
        if(_val) h+='<div><span style="color:#166534;font-weight:600;">Valor:</span> <strong>$'+esc(_val)+'</strong></div>';
        if(s.numero_oc) h+='<div style="grid-column:span 2;"><span style="color:#166534;font-weight:600;">OC:</span> <strong style="color:#2563eb;">'+esc(s.numero_oc)+'</strong></div>';
        h+='</div></div>';
      }
    }
    if(items.length){
      // Solo mostrar input de precio si la SOL está pendiente Y es categoría
      // tangible (MPs/MEE/Servicios). Influencers/CC tienen su propio flujo.
      var puedeEditarPrecios = (s.estado === 'Pendiente') &&
        ['Materia Prima','MP','MEE','Insumos','Servicio','SVC','Acondicionamiento'].indexOf(s.categoria||'') >= 0;
      h+='<div style="font-weight:800;font-size:11px;color:#1F5F5B;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px;">📦 Items solicitados ('+items.length+')'+(puedeEditarPrecios?' <span style="color:#0f766e;font-weight:600;text-transform:none;letter-spacing:0;">— editá los precios y guardá para alimentar el histórico</span>':'')+'</div>';
      h+='<div style="border:1px solid #e7e5e4;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04);">';
      h+='<table id="sol-items-table" style="width:100%;border-collapse:collapse;font-size:13px;">';
      h+='<thead style="background:#1F5F5B;color:#fff;">';
      h+='<tr>';
      h+='<th style="text-align:left;padding:11px 14px;font-weight:700;font-size:11px;letter-spacing:.5px;width:10%;">CÓDIGO</th>';
      h+='<th style="text-align:left;padding:11px 14px;font-weight:700;font-size:11px;letter-spacing:.5px;width:'+(puedeEditarPrecios?'22':'30')+'%;">MATERIAL</th>';
      h+='<th style="text-align:left;padding:11px 14px;font-weight:700;font-size:11px;letter-spacing:.5px;width:'+(puedeEditarPrecios?'15':'14')+'%;">PROVEEDOR</th>';
      h+='<th style="text-align:right;padding:11px 14px;font-weight:700;font-size:11px;letter-spacing:.5px;width:11%;">EN ESTANTERÍA</th>';
      h+='<th style="text-align:right;padding:11px 14px;font-weight:700;font-size:11px;letter-spacing:.5px;width:'+(puedeEditarPrecios?'12':'13')+'%;">A PEDIR'+(puedeEditarPrecios?' <span style="font-size:9px;font-weight:400;opacity:.85">editable</span>':'')+'</th>';
      if(puedeEditarPrecios){
        h+='<th style="text-align:right;padding:11px 14px;font-weight:700;font-size:11px;letter-spacing:.5px;width:13%;">PRECIO UNIT (g)</th>';
      }
      h+='<th style="text-align:right;padding:11px 14px;font-weight:700;font-size:11px;letter-spacing:.5px;width:'+(puedeEditarPrecios?'13':'15')+'%;">VALOR EST.</th>';
      h+='</tr></thead><tbody>';
      // Formatea cantidades preservando decimales en péptidos (< 10g):
      // 0.4g → "0.4 g", 7g → "7 g", 1500g → "1.5 kg"
      // Antes Math.round() truncaba 0.4 → 0, ocultando las cantidades reales
      // de péptidos que cuestan caro pero se usan en pequeñas cantidades.
      function fmtCant(g, unidad){
        var n = parseFloat(g||0);
        if(unidad && unidad !== 'g') {
          // unidades distintas a g: 1 decimal si necesario
          var dec = (n % 1 === 0) ? 0 : 2;
          return n.toLocaleString('es-CO',{maximumFractionDigits:dec}) + ' ' + unidad;
        }
        // Normalizado: SIEMPRE gramos con separador de miles (acordado con Alejandro).
        if(n >= 10) return Math.round(n).toLocaleString('es-CO') + ' g';
        if(n >= 1) return n.toLocaleString('es-CO',{maximumFractionDigits:1}) + ' g';
        if(n > 0) return n.toLocaleString('es-CO',{maximumFractionDigits:2}) + ' g';
        return '0 g';
      }
      var totalValorEst = 0;
      var totalCantPedir = 0;
      var justificacionesUnicas = {};
      items.forEach(function(it, idx){
        var bg = (idx % 2 === 0) ? '#fff' : '#fafaf9';
        var stock = parseFloat(it.stock_actual_g||0);
        var pedir = parseFloat(it.cantidad_g||0);
        totalCantPedir += pedir;
        // Color y etiqueta de stock
        var stockColor, stockLbl;
        if(stock <= 0){
          stockColor='#dc2626'; stockLbl='⚠ Agotado';
        } else if(stock < pedir){
          stockColor='#d97706'; stockLbl=fmtCant(stock, it.unidad)+' (insuf.)';
        } else {
          stockColor='#16a34a'; stockLbl=fmtCant(stock, it.unidad);
        }
        var valor = parseFloat(it.valor_estimado||0) || parseFloat(it.valor_estimado_calculado||0) || 0;
        if(valor > 0) totalValorEst += valor;
        var valorHtml = valor > 0 ? '<strong style="color:#1F5F5B;">'+fmt(valor)+'</strong>'
                                  : '<span style="color:#a8a29e;font-size:11px;">—</span>';
        // Acumular justificaciones únicas (productos que necesitan estos MPs)
        if(it.justificacion){
          justificacionesUnicas[it.justificacion] = (justificacionesUnicas[it.justificacion]||0) + 1;
        }
        // precio unitario actual (si ya hay) para pre-poblar el input
        var precioActual = parseFloat(it.precio_unit_g || it.precio_unitario || 0) || 0;
        var provActual = it.proveedor_sugerido || it.proveedor || '';
        var itemId = it.id || '';
        h+='<tr data-cod="'+esc(it.codigo_mp||'')+'" data-itemid="'+esc(itemId)+'" data-nombre="'+esc(it.nombre_mp||'')+'" style="background:'+bg+';border-bottom:1px solid #f0edec;">';
        h+='<td style="padding:11px 14px;font-family:monospace;font-size:11px;color:#78716c;">'+esc(it.codigo_mp||'—')+'</td>';
        h+='<td style="padding:11px 14px;font-weight:600;color:#1c1917;">'+esc(it.nombre_inci||it.nombre_mp||'—')+((it.nombre_inci&&it.nombre_mp&&it.nombre_inci!==it.nombre_mp)?'<span style="font-weight:400;color:#a8a29e;font-size:11px"> ('+esc(it.nombre_mp)+')</span>':'')+'</td>';
        // PROVEEDOR — input directo (con datalist de proveedores conocidos)
        if(puedeEditarPrecios){
          h+='<td style="padding:8px 10px;">';
          h+='<input class="prov-edit" type="text" list="prov-dl-detail" value="'+esc(provActual)+'" placeholder="Proveedor..." style="width:100%;padding:6px 8px;border:1px solid #d6d3d1;border-radius:6px;font-size:12px;">';
          h+='</td>';
        } else {
          var provHtml = provActual ? esc(provActual) : '<span style="color:#cbd5e1;font-style:italic;">— sin asignar —</span>';
          h+='<td style="padding:11px 14px;font-size:12px;color:#475569;">'+provHtml+'</td>';
        }
        h+='<td style="padding:11px 14px;text-align:right;color:'+stockColor+';font-weight:700;">'+stockLbl+'</td>';
        // A PEDIR editable
        if(puedeEditarPrecios){
          h+='<td style="padding:8px 10px;text-align:right;">';
          h+='<input class="cant-edit" type="number" min="0" step="any" value="'+pedir+'" placeholder="g" style="width:100%;max-width:110px;text-align:right;padding:6px 8px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;font-family:monospace;font-weight:700;color:#1F5F5B;" oninput="recalcularValorEst(this)">';
          h+='</td>';
        } else {
          h+='<td style="padding:11px 14px;text-align:right;font-weight:800;color:#1F5F5B;font-size:14px;">'+fmtCant(pedir, it.unidad)+'</td>';
        }
        if(puedeEditarPrecios){
          h+='<td style="padding:8px 10px;text-align:right;">';
          h+='<input class="precio-unit" type="number" min="0" step="0.01" value="'+(precioActual||'')+'" placeholder="$/g" style="width:100%;max-width:110px;text-align:right;padding:6px 8px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;font-family:monospace;" oninput="recalcularValorEst(this)">';
          h+='</td>';
        }
        h+='<td class="td-valor-est" style="padding:11px 14px;text-align:right;">'+valorHtml+'</td>';
        // Histórico de precios redundante quitado (1-jul): el precio vive en el catálogo
        // (maestro_mps.precio_referencia · "Ref: $/g") · una sola fuente (M9).
        h+='</tr>';
      });
      // Fila de total — colspan 3 para cubrir CÓDIGO + MATERIAL + PROVEEDOR
      var colspanTotal = 3;
      h+='<tr style="background:#f0fdfa;border-top:2px solid #1F5F5B;">';
      h+='<td colspan="'+colspanTotal+'" style="padding:12px 14px;font-weight:700;color:#0f766e;text-transform:uppercase;font-size:11px;letter-spacing:.5px;">📊 Total: '+items.length+' items</td>';
      h+='<td style="padding:12px 14px;text-align:right;color:#0f766e;font-size:11px;text-transform:uppercase;font-weight:700;">cantidad total</td>';
      h+='<td style="padding:12px 14px;text-align:right;font-weight:800;color:#1F5F5B;font-size:14px;">'+fmtCant(totalCantPedir,'g')+'</td>';
      if(puedeEditarPrecios){
        h+='<td style="padding:8px 10px;text-align:right;">';
        h+='<button id="btn-guardar-precios" onclick="guardarPreciosItems(&quot;'+esc((oc&&oc.numero_oc)||'')+'&quot;,&quot;'+esc(s.numero||num)+'&quot;)" style="background:#0f766e;color:#fff;border:none;border-radius:8px;padding:7px 14px;font-size:11px;font-weight:700;cursor:pointer;width:100%;">💾 Guardar cambios</button>';
        h+='</td>';
      }
      h+='<td style="padding:12px 14px;text-align:right;font-weight:800;color:#1F5F5B;font-size:14px;" id="sol-valor-total">'+(totalValorEst > 0 ? fmt(totalValorEst) : '—')+'</td>';
      h+='</tr>';
      h+='</tbody></table></div>';

      // ── BLOQUE OBSERVACIONES debajo del total ──────────────────────
      // Productos que necesitan estos MPs (deducidos de las justificaciones de cada item)
      var justifList = Object.keys(justificacionesUnicas);
      h+='<div style="margin-top:18px;background:#fffbeb;border:1px solid #fcd34d;border-radius:10px;padding:14px 18px;">';
      h+='<div style="font-size:11px;color:#92400e;font-weight:800;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px;">📝 Razón / Productos a fabricar</div>';
      if(justifList.length){
        h+='<ul style="margin:0;padding-left:20px;font-size:13px;color:#44403c;line-height:1.7;">';
        justifList.slice(0,10).forEach(function(j){
          h+='<li>'+esc(j)+'</li>';
        });
        if(justifList.length > 10) h+='<li style="color:#78716c;font-style:italic;">+'+(justifList.length-10)+' más...</li>';
        h+='</ul>';
      }
      // Observaciones libres del solicitante (si las hay y no son auto-generadas redundantes)
      var obs = (s.observaciones||'').trim();
      // Filtrar la línea auto-generada que ya está implícita arriba (proveedor + MPs listados)
      var obsLimpia = obs;
      if(obs.indexOf('Centro Programación') >= 0 || obs.indexOf('Centro Programacion') >= 0 || obs.indexOf('Planificación Estratégica') >= 0){
        // Es auto-generada — extraer solo la parte 'ACCIÓN:' si existe
        var ix = obs.indexOf('ACCIÓN:');
        if(ix >= 0){
          obsLimpia = obs.slice(ix);
        } else {
          obsLimpia = '';  // toda es redundante
        }
      }
      if(obsLimpia){
        h+='<div style="margin-top:10px;padding-top:10px;border-top:1px dashed #fcd34d;font-size:13px;color:#44403c;line-height:1.5;">';
        h+='<strong style="color:#92400e;font-size:11px;text-transform:uppercase;letter-spacing:.4px;">Comentario adicional:</strong> '+esc(obsLimpia);
        h+='</div>';
      }
      h+='</div>';
    }
    if(s.estado==='Pendiente'){
      // Bloque inferior reducido: solo textarea de motivo + hidden state.
      // El proveedor se confirma/cambia desde la card de arriba.
      // Los precios se editan inline en cada item de la tabla.
      // Esto elimina la duplicación que tenía el modal antes.
      h+='<div style="margin-top:16px;background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:14px;">';
      // Sebastián 18-jun: una SOL del módulo (sin OC con proveedor confirmado) no tenía dónde
      // asignar proveedor ni datos de OC → Catalina solo podía aprobar a ciegas ('Por definir',
      // $0). Ahora, si no hay proveedor confirmado arriba, mostramos los CAMPOS DE LA OC aquí
      // (proveedor + valor + fecha entrega), que gestionarSol envía con crear_oc → la OC nace
      // completa, tipo orden de compra como todas. Si ya hay OC con proveedor, van ocultos.
      var _tieneProvOC = !!(provName && oc);
      if(!_tieneProvOC){
        h+='<div style="font-weight:800;font-size:11px;color:#92400e;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;">&#x1F9FE; Datos de la orden de compra</div>';
        h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">';
        h+='<div style="grid-column:span 2;"><label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:4px;">Proveedor</label>';
        h+='<input id="sol-prov-sel" list="prov-dl-sol" placeholder="Escribe o elige el proveedor..." style="width:100%;padding:8px 12px;border:1px solid #fcd34d;border-radius:6px;font-size:13px;">';
        h+='<datalist id="prov-dl-sol">'; PROVS.forEach(function(p){ h+='<option value="'+esc(p.nombre)+'">'; }); h+='</datalist></div>';
        h+='<div><label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:4px;">Valor total estimado ($)</label>';
        h+='<input id="sol-valor" type="number" min="0" step="1000" placeholder="0" style="width:100%;padding:8px 12px;border:1px solid #fcd34d;border-radius:6px;font-size:13px;"></div>';
        h+='<div><label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:4px;">Fecha entrega estimada</label>';
        h+='<input id="sol-fent" type="date" style="width:100%;padding:8px 12px;border:1px solid #fcd34d;border-radius:6px;font-size:13px;"></div>';
        h+='</div>';
      }
      h+='<div class="fg" style="margin-bottom:0;"><label style="font-size:11px;font-weight:700;color:#44403c;display:block;margin-bottom:4px;">Motivo / Comentario (opcional)</label>';
      h+='<textarea id="sol-motivo" placeholder="Comentario al aprobar o motivo del rechazo..." rows="2" style="width:100%;padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px;resize:vertical;"></textarea></div>';
      h+='<input type="hidden" id="sol-det-num" value="'+esc(s.numero||num)+'">';
      h+='<input type="hidden" id="sol-det-cat" value="'+esc(s.categoria||'MP')+'">';
      h+='<input type="hidden" id="sol-det-area" value="'+esc(s.area||'')+'">';
      h+='<input type="hidden" id="sol-tercero-txt" value="">';
      // Si ya hay proveedor confirmado en la card de arriba, estos van ocultos (se usan los de arriba).
      if(_tieneProvOC){
        h+='<input type="hidden" id="sol-prov-sel" value="">';
        h+='<input type="hidden" id="sol-valor" value="0">';
        h+='<input type="hidden" id="sol-fent" value="">';
      }
      h+='</div>';
    }
    h+='</div>';
    body.innerHTML=h;
    var fbtns='<button class="btn bo" onclick="_solDetClose()">Cerrar</button>';
    if(s.estado==='Pendiente'){
      fbtns+='<button class="btn" style="background:#dc2626;color:#fff;font-weight:700;" onclick="_solDetRech()">&#10005; Rechazar</button>';
      if(s.categoria==='Influencer/Marketing Digital'){
        fbtns+='<button class="btn bg" onclick="_solDetApr()" style="background:#7c3aed;">&#x1F4B8; Pagar directamente</button>';
      } else if(s.categoria==='Cuenta de Cobro'){
        fbtns+='<button class="btn bg" onclick="_solDetApr()" style="background:#d97706;">&#x1F4B3; Aprobar Cuenta de Cobro</button>';
      } else {
        fbtns+='<button class="btn bg" onclick="_solDetApr()" style="background:#16a34a;">&#9989; Aprobar Solicitud</button>';
      }
    }
    footer.innerHTML=fbtns;
  }catch(e){ body.innerHTML='<p style="color:#dc2626;">Error: '+e.message+'</p>'; }
}
async function gestionarSol(decision){
  var num=document.getElementById('sol-det-num').value;
  // Bloque de campos viejos (selector + valor + fecha) ya no existe
  // visualmente pero los hidden quedan vacíos. El proveedor lo tomamos
  // de la card de arriba (donde se confirma/cambia). El valor de la OC
  // ya está calculado por items (no lo sobrescribimos). Esto reemplaza
  // el flujo viejo que duplicaba campos arriba/abajo.
  var _provSel=(document.getElementById('sol-prov-sel')||{value:''}).value;
  if(_provSel==='__nuevo__'){ alert('Primero guarda el nuevo proveedor antes de continuar.'); return; }
  var prov=_provSel==='__tercero__'
    ? ((document.getElementById('sol-tercero-txt')||{value:''}).value.trim()||'Pago a Terceros')
    : _provSel;
  // Fallback: si no hay selector activo, leer del card top (caso usual ahora)
  if (!prov) {
    var nameEl = document.getElementById('prov-card-name');
    if (nameEl) prov = (nameEl.textContent||'').trim();
  }
  var valor=parseFloat((document.getElementById('sol-valor')||{value:0}).value||0);
  var motivo=(document.getElementById('sol-motivo')||{value:''}).value.trim();
  var fent=(document.getElementById('sol-fent')||{value:''}).value;
  if(decision==='Rechazada' && !motivo){
    // Gap #5 · 21-may-2026 · motivo OBLIGATORIO (≥10 chars · queda audit)
    motivo = prompt('Motivo de rechazo (≥10 chars · el solicitante verá esto):');
    if(!motivo) return;
    motivo = motivo.trim();
    if(motivo.length < 10){ alert('Motivo debe tener ≥10 chars'); return; }
  }
  var _areaEl=document.getElementById('sol-det-area');
  var _esProduccion=(_areaEl&&_areaEl.value.trim()==='Produccion');
  var body={estado:decision,observaciones:motivo};
  if(decision==='Aprobada'){
    if(_esProduccion){ body.crear_oc=false; } else { body.crear_oc=true;
    body.proveedor=prov||'Por definir';
    if(valor>0) body.valor_total=valor;
    if(fent) body.fecha_entrega_est=fent;
    var catEl=document.getElementById('sol-det-cat');
    if(catEl) body.categoria=catEl.value;
    body.observaciones_oc=motivo||('Generado desde '+num);
    }
  }
  try{
    var r=await fetch('/api/solicitudes-compra/'+encodeURIComponent(num)+'/estado',_fetchOpts('PATCH', body));
    var d=await r.json();
    if(d.error){ alert('Error: '+d.error); return; }
    closeModal('m-sol-det');
    await Promise.all([loadData(),loadSolicitudes(),loadInfluencers(),loadCCSolicitudes()]);
    // Sebastián 24-may-2026 · UX hint del próximo paso · backend agrega
    // d.siguiente_paso si OC quedó en Borrador (requiere autorizar) o
    // fast-track Autorizada (lista para pagar). Antes Catalina aprobaba y
    // no sabía si tenía que volver a tab OCs para autorizar.
    if(decision==='Aprobada'){
      var msg='✓ Solicitud aprobada.';
      if(d.numero_oc) msg+='\\nOC generada: '+d.numero_oc;
      if(d.oc_estado) msg+=' ('+d.oc_estado+')';
      if(d.siguiente_paso) msg+='\\n\\n→ '+d.siguiente_paso;
      alert(msg);
    } else {
      alert('Solicitud rechazada.');
    }
  }catch(e){ alert('Error: '+e); }
}


// ─── Solicitudes de Producción (cola de Catalina) ─────────────────
async function loadSolicitudesProduccion(){
  var estado = (document.getElementById('solprod-filtro-estado')||{}).value || 'pendiente';
  var lista = document.getElementById('solprod-lista');
  var empty = document.getElementById('solprod-empty');
  if(!lista) return;
  lista.innerHTML = '<div style="color:#94a3b8;text-align:center;padding:20px;font-size:12px">Cargando...</div>';
  empty.style.display = 'none';
  try {
    var r = await fetch('/api/compras/solicitudes-produccion?estado='+encodeURIComponent(estado));
    var d = await r.json();
    if(!r.ok){ lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+(d.error||r.status)+'</div>'; return; }
    var items = d.items || [];
    // Badge en el tab
    var badge = document.getElementById('solprod-badge');
    if(badge){
      var nPend = d.pendientes || 0;
      if(nPend > 0){ badge.textContent = nPend; badge.style.display = 'inline-block'; }
      else { badge.style.display = 'none'; }
    }
    if(!items.length){ lista.innerHTML=''; empty.style.display='block'; return; }
    var rutaColors = {inventario:'#16a34a', oc:'#1e40af', serigrafia:'#7c3aed', tampografia:'#7c3aed', etiqueta_adhesiva:'#0891b2'};
    var rutaLabels = {inventario:'📦 Sacar de inventario', oc:'🛒 Crear OC', serigrafia:'🎨 Mandar a serigrafía', tampografia:'🖋️ Mandar a tampografía', etiqueta_adhesiva:'🏷️ OC etiquetas adhesivas'};
    lista.innerHTML = items.map(function(it){
      var ruta = it.ruta_sugerida || 'oc';
      var stockTxt = (it.stock_actual||0).toLocaleString('es-CO');
      var cantTxt = Math.round(it.cantidad_unidades||0).toLocaleString('es-CO');
      var fechaObj = it.fecha_objetivo ? '<span style="color:#dc2626;font-size:11px;font-weight:600">📅 '+it.fecha_objetivo+'</span>' : '';
      var decoBadge = it.decoracion_tipo ? '<span style="background:#f3e8ff;color:#7c3aed;font-size:10px;font-weight:700;padding:2px 6px;border-radius:6px;margin-left:6px">'+it.decoracion_tipo+'</span>' : '';
      var estadoBadge = '';
      if(it.estado==='pendiente') estadoBadge = '<span style="background:#fef3c7;color:#92400e;font-size:10px;font-weight:700;padding:2px 8px;border-radius:8px">PENDIENTE</span>';
      else if(it.estado==='decidida') estadoBadge = '<span style="background:#dbeafe;color:#1e40af;font-size:10px;font-weight:700;padding:2px 8px;border-radius:8px">DECIDIDA: '+_esc(it.decision||'')+'</span>';
      else estadoBadge = '<span style="background:#dcfce7;color:#166534;font-size:10px;font-weight:700;padding:2px 8px;border-radius:8px">'+_esc(it.estado||'')+'</span>';
      var acciones = '';
      if(it.estado === 'pendiente'){
        acciones = '<button onclick="solprodDecidir('+it.id+')" style="background:'+(rutaColors[ruta]||'#1e40af')+';color:#fff;border:none;border-radius:6px;padding:7px 14px;font-size:12px;font-weight:700;cursor:pointer">Decidir →</button>';
      }
      var oc_o_tarea = '';
      if(it.oc_numero) oc_o_tarea += '<div style="font-size:10px;color:#1e40af;margin-top:2px">📄 '+_esc(it.oc_numero)+'</div>';
      if(it.tarea_operativa_id) oc_o_tarea += '<div style="font-size:10px;color:#15803d;margin-top:2px">🎯 Tarea operativa #'+it.tarea_operativa_id+'</div>';
      return '<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(rutaColors[ruta]||'#94a3b8')+';border-radius:10px;padding:14px 18px;display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center">'+
        '<div>'+
          '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'+
            '<span style="font-weight:700;color:#0f172a;font-size:14px">'+_esc(it.producto_nombre||'')+'</span>'+
            decoBadge + estadoBadge +
          '</div>'+
          '<div style="font-size:13px;color:#1e293b;margin-top:4px"><b>'+_esc(it.tipo_item||'')+'</b> · '+_esc(it.descripcion||it.mee_codigo||'')+'</div>'+
          '<div style="font-size:11px;color:#64748b;margin-top:4px">'+
            '🔢 <b>'+cantTxt+' und</b> · '+
            '📦 stock: <b style="color:'+(it.stock_actual>=it.cantidad_unidades?'#16a34a':'#dc2626')+'">'+stockTxt+'</b> · '+
            (fechaObj?fechaObj+' · ':'')+
            '<i>'+rutaLabels[ruta]+'</i>'+
          '</div>'+
          (it.observaciones?'<div style="font-size:11px;color:#78716c;margin-top:4px;font-style:italic">"'+_esc(it.observaciones)+'"</div>':'')+
          oc_o_tarea +
        '</div>'+
        '<div style="text-align:right">'+acciones+'</div>'+
      '</div>';
    }).join('');
  } catch(e){
    lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
  }
}

async function solprodDecidir(solId){
  // Modal con opciones de decision
  var html = '<div id="solprod-modal" style="position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:99999;display:flex;align-items:center;justify-content:center;padding:20px">'+
    '<div style="background:#fff;border-radius:14px;padding:24px;width:520px;max-width:100%">'+
      '<div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:14px">'+
        '<h3 style="margin:0">Decidir solicitud #'+solId+'</h3>'+
        '<button onclick="document.getElementById(&quot;solprod-modal&quot;).remove()" style="background:transparent;border:1px solid #d6d3d1;border-radius:6px;width:32px;height:32px;cursor:pointer;font-size:16px;color:#1c1917;font-weight:700">&#10005;</button>'+
      '</div>'+
      '<label style="font-size:12px;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Ruta</label>'+
      '<select id="sp-decision" style="width:100%;padding:8px 10px;border:1px solid #d1d5db;border-radius:6px;margin:6px 0 14px;font-size:13px">'+
        '<option value="inventario">📦 Sacar de inventario (genera tarea operativa)</option>'+
        '<option value="oc">🛒 Crear OC (compras nuevas)</option>'+
        '<option value="serigrafia">🎨 Mandar a serigrafía (saca envases + tarea)</option>'+
        '<option value="tampografia">🖋️ Mandar a tampografía (saca envases + tarea)</option>'+
        '<option value="etiqueta_adhesiva">🏷️ OC etiquetas adhesivas</option>'+
      '</select>'+
      '<label style="font-size:12px;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Proveedor (si aplica)</label>'+
      '<input id="sp-prov" type="text" placeholder="Ej. Cromaroma / nombre del serigrafista..." style="width:100%;padding:8px 10px;border:1px solid #d1d5db;border-radius:6px;margin:6px 0 14px;font-size:13px">'+
      '<label style="font-size:12px;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Fecha objetivo</label>'+
      '<input id="sp-fecha" type="date" style="width:100%;padding:8px 10px;border:1px solid #d1d5db;border-radius:6px;margin:6px 0 14px;font-size:13px">'+
      '<label style="font-size:12px;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Asignado a (CSV)</label>'+
      '<input id="sp-asign" type="text" value="luz,operarios" placeholder="luz,miguel,luis..." style="width:100%;padding:8px 10px;border:1px solid #d1d5db;border-radius:6px;margin:6px 0 14px;font-size:13px">'+
      '<label style="font-size:12px;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Observaciones</label>'+
      '<textarea id="sp-obs" rows="2" style="width:100%;padding:8px 10px;border:1px solid #d1d5db;border-radius:6px;margin:6px 0 14px;font-size:13px;font-family:inherit"></textarea>'+
      '<div style="display:flex;gap:8px;justify-content:flex-end">'+
        '<button onclick="document.getElementById(&quot;solprod-modal&quot;).remove()" style="background:#fff;color:#475569;border:1px solid #cbd5e1;border-radius:6px;padding:8px 16px;font-size:13px;font-weight:600;cursor:pointer">Cancelar</button>'+
        '<button onclick="solprodEnviarDecision('+solId+')" style="background:#16a34a;color:#fff;border:none;border-radius:6px;padding:8px 16px;font-size:13px;font-weight:700;cursor:pointer">✅ Confirmar</button>'+
      '</div>'+
    '</div></div>';
  document.body.insertAdjacentHTML('beforeend', html);
}

async function solprodEnviarDecision(solId){
  var body = {
    decision: document.getElementById('sp-decision').value,
    proveedor: document.getElementById('sp-prov').value,
    fecha_objetivo: document.getElementById('sp-fecha').value,
    asignado_a: document.getElementById('sp-asign').value,
    observaciones: document.getElementById('sp-obs').value,
  };
  try {
    var r = await fetch('/api/compras/solicitudes-produccion/'+solId+'/decidir', _fetchOpts('POST', body));
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    document.getElementById('solprod-modal').remove();
    alert(d.mensaje||'Decisión guardada');
    loadSolicitudesProduccion();
  } catch(e){ alert('Error: '+e.message); }
}

// Auto-cargar badge al cargar la página
setTimeout(function(){
  fetch('/api/compras/solicitudes-produccion?estado=pendiente').then(function(r){return r.json();}).then(function(d){
    var badge = document.getElementById('solprod-badge');
    if(badge && d.pendientes>0){ badge.textContent = d.pendientes; badge.style.display='inline-block'; }
  }).catch(function(){});
  // Badge de Mis Solicitudes — cuenta abiertas del usuario logueado
  fetch('/api/solicitudes-compra/mis?estado=abiertas').then(function(r){return r.json();}).then(function(d){
    var badge = document.getElementById('mis-sol-badge');
    if(badge && d.abiertas>0){ badge.textContent = d.abiertas; badge.style.display='inline-block'; }
  }).catch(function(){});
}, 1500);

// ─── Mis Solicitudes (vista para el solicitante con ciclo completo) ─────
async function loadMisSolicitudes(){
  var estado = (document.getElementById('mis-sol-filtro')||{}).value || 'abiertas';
  var body = document.getElementById('mis-sol-body');
  if(!body) return;
  body.innerHTML = '<div style="color:#94a3b8;text-align:center;padding:30px;font-size:12px">Cargando...</div>';
  try {
    var r = await fetch('/api/solicitudes-compra/mis?estado='+encodeURIComponent(estado));
    var d = await r.json();
    if(!r.ok){ body.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+(d.error||r.status)+'</div>'; return; }
    var sols = d.solicitudes || [];
    // Actualizar badge
    var badge = document.getElementById('mis-sol-badge');
    if(badge){
      if(d.abiertas>0){ badge.textContent = d.abiertas; badge.style.display='inline-block'; }
      else badge.style.display = 'none';
    }
    if(!sols.length){
      body.innerHTML = '<div style="color:#94a3b8;text-align:center;padding:40px;font-size:13px">No tienes solicitudes '+(estado==='abiertas'?'abiertas':estado==='cerradas'?'cerradas':'')+'.</div>';
      return;
    }
    body.innerHTML = sols.map(function(s){
      var paso = s.paso || 0;
      // Stepper visual de 6 pasos
      var pasos = [
        {n:1, label:'Pendiente', icon:'⏳'},
        {n:2, label:'Aprobada / OC', icon:'📝'},
        {n:3, label:'Autorizada', icon:'🟢'},
        {n:4, label:'Pagada', icon:'💸'},
        {n:5, label:'En tránsito', icon:'🚚'},
        {n:6, label:'Recibida', icon:'✅'},
      ];
      var stepper = '<div style="display:flex;gap:4px;margin:10px 0">' +
        pasos.map(function(p){
          var done = paso >= p.n;
          var bg = done ? s.paso_color : '#f1f5f9';
          var fg = done ? '#fff' : '#94a3b8';
          return '<div title="'+_esc(p.label)+'" style="flex:1;background:'+bg+';color:'+fg+';font-size:10px;font-weight:700;padding:4px 6px;border-radius:4px;text-align:center">'+p.icon+'</div>';
        }).join('') +
        '</div>';
      var btnRecibir = s.puede_marcar_recibido
        ? '<button onclick="marcarRecibidoSolicitante(\\''+_esc(s.numero)+'\\')" style="background:#16a34a;color:#fff;border:none;border-radius:6px;padding:7px 14px;font-size:12px;font-weight:700;cursor:pointer">✅ Marcar Recibido</button>'
        : '';
      var ocLine = s.numero_oc
        ? '<div style="font-size:11px;color:#1e40af;margin-top:2px;font-family:monospace">'+_esc(s.numero_oc)+(s.oc_proveedor?' · '+_esc(s.oc_proveedor):'')+'</div>'
        : '';
      var fechas = [];
      if(s.fecha_pago) fechas.push('💸 pagado '+s.fecha_pago.substring(0,10));
      if(s.fecha_entrega_est) fechas.push('📅 entrega est. '+s.fecha_entrega_est);
      if(s.fecha_recepcion) fechas.push('✅ recibido '+s.fecha_recepcion.substring(0,10));
      var fechaLine = fechas.length ? '<div style="font-size:10px;color:#64748b;margin-top:4px">'+fechas.join(' · ')+'</div>' : '';
      return '<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+s.paso_color+';border-radius:10px;padding:14px 18px;margin-bottom:10px;display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center">'+
        '<div>'+
          '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">'+
            '<span style="font-weight:700;font-family:monospace;color:#0f172a">'+_esc(s.numero)+'</span>'+
            '<span style="background:'+s.paso_color+';color:#fff;font-size:11px;font-weight:700;padding:2px 10px;border-radius:10px">'+_esc(s.paso_label)+'</span>'+
            (s.urgencia==='Alta'||s.urgencia==='Urgente'?'<span style="background:#fee2e2;color:#dc2626;font-size:10px;font-weight:700;padding:1px 6px;border-radius:6px">'+_esc(s.urgencia)+'</span>':'')+
          '</div>'+
          '<div style="font-size:13px;color:#1e293b;margin-top:4px">'+_esc(s.observaciones||s.categoria||'(sin descripción)')+'</div>'+
          ocLine + fechaLine + stepper +
        '</div>'+
        '<div>'+ btnRecibir +'</div>'+
      '</div>';
    }).join('');
  } catch(e){
    body.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
  }
}

async function marcarRecibidoSolicitante(numero){
  var obs = prompt('¿Algo que anotar de esta recepción? (opcional)\\n\\nEsto cierra la solicitud '+numero+' marcando la OC como Recibida.', '');
  if(obs===null) return;
  try {
    var r = await fetch('/api/solicitudes-compra/'+encodeURIComponent(numero)+'/marcar-recibido-solicitante', _fetchOpts('POST', {observaciones: obs||''}));
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    alert(d.mensaje||'Recibido confirmado');
    loadMisSolicitudes();
  } catch(e){ alert('Error: '+e.message); }
}

// ─── Consolidado por Proveedor ────────────────────────────────────
var _consolCache = [];  // cache indexado por posición

async function loadConsolidado(){
  var body = document.getElementById('consol-body');
  body.innerHTML = '<div style="color:#94a3b8;text-align:center;padding:40px;">Cargando...</div>';
  var estados = Array.from(document.querySelectorAll('.consol-est:checked')).map(function(el){return el.value;});
  if(!estados.length){
    body.innerHTML = '<div style="color:#f59e0b;padding:16px;">Selecciona al menos un estado.</div>';
    return;
  }
  try{
    var qs = estados.map(function(e){return 'estados='+encodeURIComponent(e);}).join('&');
    var r = await fetch('/api/compras/consolidado-proveedor?'+qs);
    var d = await r.json();
    _consolCache = d.proveedores || [];
    if(!_consolCache.length){
      body.innerHTML = '<div style="color:#4ade80;text-align:center;padding:40px;">&#x2705; No hay OCs pendientes.</div>';
      return;
    }
    body.innerHTML = _consolCache.map(function(p, i){ return renderConsolCard(p, i); }).join('');
  }catch(e){
    body.innerHTML = '<div style="color:#f87171;padding:16px;">Error: '+e+'</div>';
  }
}

// Cache global del modo edit por idx de proveedor en el consolidado.
// _consolEditMode[idx] = true significa que el render usa modo edit.
var _consolEditMode = {};

function renderConsolCard(p, idx){
  if (_consolEditMode[idx]) return renderConsolCardEdit(p, idx);
  // Compras PRO · 21-may-2026 · UI unifica 8 estados → 5 buckets visuales
  // Borrador/Revisada → mismo color (etapa pre-autorización)
  // Recibida/Parcial → mismo color (con detalle parcial inline)
  // Cancelada/Rechazada → mismo color (terminal negativo)
  var estadoColors = {
    'Borrador':'#94a3b8','Revisada':'#94a3b8',
    'Autorizada':'#22c55e',
    'Recibida':'#0891b2','Parcial':'#0891b2',
    'Pagada':'#16a34a',
    'Cancelada':'#dc2626','Rechazada':'#dc2626',
  };

  // Contenido principal: ítems si los hay, OCs con observaciones si no
  var contenidoHtml;
  if(p.items && p.items.length > 0){
    var rows = p.items.map(function(it){
      var cant = Math.round(it.cantidad_total_g||0).toLocaleString('es-CO')+' g';
      var sub = it.subtotal_total > 0
        ? '$'+Number(it.subtotal_total).toLocaleString('es-CO',{maximumFractionDigits:0})
        : '—';
      var ocs = it.ocs_origen.length > 1 ? it.ocs_origen.join(', ') : (it.ocs_origen[0]||'');
      return '<tr>'
        +'<td style="padding:5px 8px;color:#1e293b;">'+escConH(it.nombre_inci||it.nombre_mp)+((it.nombre_inci&&it.nombre_mp&&it.nombre_inci!==it.nombre_mp)?'<span style="color:#a8a29e;font-size:11px"> ('+escConH(it.nombre_mp)+')</span>':'')+'</td>'
        +'<td style="padding:5px 8px;font-weight:600;">'+cant+'</td>'
        +'<td style="padding:5px 8px;color:#64748b;">'+sub+'</td>'
        +'<td style="padding:5px 8px;font-size:11px;color:#94a3b8;">'+ocs+'</td>'
        +'</tr>';
    }).join('');
    contenidoHtml = '<table style="width:100%;border-collapse:collapse;">'
      +'<thead><tr>'
        +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">Producto</th>'
        +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">Cantidad total</th>'
        +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">Subtotal</th>'
        +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">OCs</th>'
      +'</tr></thead>'
      +'<tbody>'+rows+'</tbody>'
      +'</table>';
  } else {
    // Fallback: mostrar OCs con su descripción/observaciones
    var rows = p.ocs.map(function(o){
      var col = estadoColors[o.estado] || '#94a3b8';
      var desc = o.observaciones || o.categoria || '—';
      return '<tr>'
        // Bug #11 fix · 21-may-2026 · escape numero_oc + estado (consistencia XSS)
        +'<td style="padding:5px 8px;font-weight:600;color:#0f172a;">'+escConH(o.numero_oc||'')+'</td>'
        +'<td style="padding:5px 8px;"><span style="color:'+col+';">'+escConH(o.estado||'')+'</span></td>'
        +'<td style="padding:5px 8px;color:#475569;">'+escConH(desc)+'</td>'
        +'<td style="padding:5px 8px;color:#0f172a;">$'+Number(o.valor_total).toLocaleString('es-CO',{maximumFractionDigits:0})+'</td>'
        +'</tr>';
    }).join('');
    contenidoHtml = '<div style="font-size:11px;color:#94a3b8;margin-bottom:6px;">Esta OC no tiene ítems detallados. Se muestra el resumen por orden.</div>'
      +'<table style="width:100%;border-collapse:collapse;">'
        +'<thead><tr>'
          +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">N° OC</th>'
          +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">Estado</th>'
          +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">Descripción / Concepto</th>'
          +'<th style="text-align:left;font-size:11px;color:#94a3b8;padding:4px 8px;border-bottom:1px solid #f1f5f9;">Valor</th>'
        +'</tr></thead>'
        +'<tbody>'+rows+'</tbody>'
      +'</table>';
  }

  var ocsHtml = p.ocs.map(function(o){
    var col = estadoColors[o.estado] || '#94a3b8';
    var ivaTag = o.con_iva ? ' <span style="color:#0891b2;font-weight:700;font-size:10px;">+IVA</span>' : '';
    return '<span style="font-size:11px;background:#f1f5f9;border-radius:4px;padding:2px 8px;margin-right:4px;">'
      +escConH(o.numero_oc||'')+' <span style="color:'+col+';">'+escConH(o.estado||'')+'</span>'+ivaTag+'</span>';
  }).join('');

  var totalFmt = p.valor_total > 0 ? '$'+Number(p.valor_total).toLocaleString('es-CO',{maximumFractionDigits:0}) : '--';
  var metaLine = p.n_items > 0
    ? p.n_ocs+' OC'+(p.n_ocs>1?'s':'')+' &bull; '+p.n_items+' producto'+(p.n_items>1?'s':'')+' &bull; Total: <strong>'+totalFmt+'</strong>'
    : p.n_ocs+' OC'+(p.n_ocs>1?'s':'')+' &bull; Total: <strong>'+totalFmt+'</strong>';

  return '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;margin-bottom:16px;overflow:hidden;">'
    +'<div style="background:#f8fafc;padding:14px 18px;display:flex;align-items:flex-start;gap:12px;border-bottom:1px solid #e2e8f0;">'
      +'<span style="font-size:22px;margin-top:2px;">&#x1F3ED;</span>'
      +'<div style="flex:1;min-width:0;">'
        +'<div style="font-weight:700;font-size:16px;color:#0f172a;">'+escConH(p.proveedor)+'</div>'
        +'<div style="font-size:12px;color:#64748b;margin-top:2px;">'+metaLine+'</div>'
        +(p.nit||p.contacto||p.telefono
          ? '<div style="font-size:11px;color:#94a3b8;margin-top:3px;">'
            +(p.nit?'NIT: '+esc(p.nit)+' &nbsp;':'')
            +(p.contacto?'&#x1F464; '+escConH(p.contacto)+' &nbsp;':'')
            +(p.telefono?'&#x1F4DE; '+p.telefono:'')
            +'</div>'
          : '')
        +'<div style="margin-top:6px;">'+ocsHtml+'</div>'
      +'</div>'
      +'<div style="display:flex;gap:8px;flex-shrink:0;flex-wrap:wrap;">'
        +'<button class="btn" data-consol-idx="'+idx+'" onclick="toggleConsolEdit(parseInt(this.dataset.consolIdx))"'
          +' style="padding:8px 14px;font-size:12px;white-space:nowrap;background:#7c3aed;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600;">&#x270F;&#xFE0F; Editar</button>'
        // Autorizar (Sebastián 18-jun): faltaba aquí · una OC en Borrador/Revisada no se podía
        // recepcionar porque nadie la autorizaba desde esta vista. Visible solo a autorizadores
        // (admin/Catalina · ES_AUTORIZA). Un botón por cada OC del grupo que lo necesite.
        +(ES_AUTORIZA ? (p.ocs||[]).filter(function(o){ return o.estado==='Borrador'||o.estado==='Revisada'; }).map(function(o){
            return '<button class="btn" data-aut-oc="'+esc(o.numero_oc)+'" onclick="autorizarOC(this.dataset.autOc)"'
              +' style="padding:8px 14px;font-size:12px;white-space:nowrap;background:#16a34a;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600;" title="Autorizar para poder recepcionar">&#10003; Autorizar '+esc(o.numero_oc)+'</button>';
          }).join('') : '')
        // Pagar (18-jun): para OCs ya Autorizadas, desde la misma vista agrupada · ES_AUTORIZA
        +(ES_AUTORIZA ? (p.ocs||[]).filter(function(o){ return o.estado==='Autorizada'; }).map(function(o){
            return '<button class="btn" data-pago-oc="'+esc(o.numero_oc)+'" data-pago-val="'+parseFloat(o.valor_total||p.valor_total||0)+'" data-pago-prov="'+esc(p.proveedor||'')+'"'
              +' onclick="openPago(this.dataset.pagoOc, parseFloat(this.dataset.pagoVal), this.dataset.pagoProv)"'
              +' style="padding:8px 14px;font-size:12px;white-space:nowrap;background:#0f766e;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600;" title="Registrar pago">&#x1F4B8; Pagar '+esc(o.numero_oc)+'</button>';
          }).join('') : '')
        // Eliminar una OC AUTORIZADA por error (Sebastián 1-jul · Catalina) · solo autorizadores ·
        // el backend solo la borra si NO tiene pago ni recepción · revierte la SOL a Pendiente.
        +(ES_AUTORIZA ? (p.ocs||[]).filter(function(o){ return o.estado==='Autorizada'; }).map(function(o){
            return '<button class="btn" data-del-oc="'+esc(o.numero_oc)+'" onclick="eliminarOCAutorizada(this.dataset.delOc)"'
              +' style="padding:8px 14px;font-size:12px;white-space:nowrap;background:#dc2626;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600;" title="Eliminar esta OC autorizada por error (solo si no tiene pago ni recepción)">&#x1F5D1; Eliminar '+esc(o.numero_oc)+'</button>';
          }).join('') : '')
        +'<button class="btn" data-consol-idx="'+idx+'" onclick="copiarPedido(parseInt(this.dataset.consolIdx))"'
          +' style="padding:8px 14px;font-size:12px;white-space:nowrap;background:#3b82f6;border-radius:8px;">&#x1F4CB; Copiar</button>'
        +'<button class="btn bp" data-print-idx="'+idx+'" onclick="imprimirPedido(parseInt(this.dataset.printIdx))"'
          +' style="padding:8px 14px;font-size:12px;white-space:nowrap;border-radius:8px;">&#x1F5A8; Imprimir</button>'
        // Eliminar · solo si el grupo tiene OCs en Borrador/Rechazada (backend valida igual)
        +((p.ocs||[]).some(function(o){ return o.estado==='Borrador'||o.estado==='Rechazada'; })
          ? '<button class="btn" data-consol-idx="'+idx+'" onclick="eliminarOCsGrupo(parseInt(this.dataset.consolIdx))"'
            +' style="padding:8px 14px;font-size:12px;white-space:nowrap;background:#dc2626;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600;">&#x1F5D1; Eliminar</button>'
          : '')
      +'</div>'
    +'</div>'
    +'<div style="padding:12px 18px;">'+contenidoHtml+'</div>'
  +'</div>';
}

// Modo EDIT: items individuales por OC con inputs editables, IVA toggle por OC,
// observaciones editables, total recalculado en vivo. "Guardar" persiste todo
// con los endpoints PATCH existentes.
function renderConsolCardEdit(p, idx){
  var pid = 'consol-edit-'+idx;
  var ocsHtml = (p.ocs||[]).map(function(o, oi){
    var ocId = pid+'-oc-'+oi;
    var itemsRows = (o.items_raw||[]).map(function(it, ii){
      var rid = ocId+'-it-'+ii;
      return '<tr data-item-id="'+it.id+'" data-row-id="'+rid+'">'
        +'<td style="padding:6px 8px;font-size:12px;color:#1e293b;">'+escConH(it.nombre_inci||it.nombre_mp||it.codigo_mp||'?')+((it.nombre_inci&&it.nombre_mp&&it.nombre_inci!==it.nombre_mp)?'<span style="color:#a8a29e;font-size:11px"> ('+escConH(it.nombre_mp)+')</span>':'')+'</td>'
        +'<td style="padding:4px 8px;"><input type="number" step="any" min="0" value="'+(it.cantidad_g||0)+'" '
          +'data-field="cantidad_g" oninput="recalcConsolOCFromEl(this)" '
          +'style="width:90px;padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;text-align:right;"></td>'
        +'<td style="padding:4px 8px;"><input type="number" step="any" min="0" value="'+(it.precio_unitario||0)+'" '
          +'data-field="precio_unitario" oninput="recalcConsolOCFromEl(this)" '
          +'style="width:100px;padding:4px 6px;border:1px solid #d1d5db;border-radius:5px;font-size:12px;text-align:right;"></td>'
        +'<td style="padding:6px 8px;font-size:12px;color:#475569;text-align:right;" class="row-subtotal">'
          +'$'+Number(it.subtotal||0).toLocaleString('es-CO',{maximumFractionDigits:0})+'</td>'
        +'</tr>';
    }).join('');

    return '<div data-oc-id="'+ocId+'" data-oc-num="'+o.numero_oc+'" '
      +'style="background:#fafaf9;border:1px solid #e7e5e4;border-radius:10px;padding:12px;margin-bottom:10px;">'
      +'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">'
        +'<div style="font-weight:700;font-family:monospace;color:#1e293b;">'+escConH(o.numero_oc||'')+' <span style="font-size:11px;color:#64748b;font-weight:500;">('+escConH(o.estado||'')+')</span></div>'
        +'<label style="font-size:12px;color:#0891b2;display:inline-flex;align-items:center;gap:6px;cursor:pointer;">'
          +'<input type="checkbox" data-field="con_iva" '+(o.con_iva?'checked':'')+' '
          +'onchange="recalcConsolOCFromEl(this)"> Con IVA 19%</label>'
      +'</div>'
      +(itemsRows
        ? '<table style="width:100%;border-collapse:collapse;margin-top:8px;">'
            +'<thead><tr>'
              +'<th style="text-align:left;font-size:10px;color:#94a3b8;padding:4px 8px;text-transform:uppercase;letter-spacing:.5px;">Producto</th>'
              +'<th style="text-align:right;font-size:10px;color:#94a3b8;padding:4px 8px;text-transform:uppercase;letter-spacing:.5px;">Cantidad (g)</th>'
              +'<th style="text-align:right;font-size:10px;color:#94a3b8;padding:4px 8px;text-transform:uppercase;letter-spacing:.5px;">Precio unit.</th>'
              +'<th style="text-align:right;font-size:10px;color:#94a3b8;padding:4px 8px;text-transform:uppercase;letter-spacing:.5px;">Subtotal</th>'
            +'</tr></thead><tbody>'+itemsRows+'</tbody></table>'
        : '<div style="font-size:11px;color:#94a3b8;padding:8px 0;">Sin items detallados en esta OC.</div>')
      +'<div style="margin-top:10px;font-size:12px;font-weight:700;color:#0f172a;text-align:right;" class="oc-total">'
        +'Total OC: $'+Number(o.valor_total||0).toLocaleString('es-CO',{maximumFractionDigits:0})+'</div>'
      +'<div style="margin-top:10px;">'
        +'<label style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.4px;">Observaciones</label>'
        +'<textarea data-field="observaciones" rows="2" placeholder="Notas, justificación, condiciones especiales..." '
        +'style="width:100%;padding:6px 8px;margin-top:4px;border:1px solid #d1d5db;border-radius:6px;font-size:12px;font-family:inherit;resize:vertical;">'
        +escConH(o.observaciones||'')+'</textarea>'
      +'</div>'
    +'</div>';
  }).join('');

  return '<div id="'+pid+'" data-prov-idx="'+idx+'" '
    +'style="background:#fff;border:2px solid #7c3aed;border-radius:12px;margin-bottom:16px;overflow:hidden;">'
    +'<div style="background:#faf5ff;padding:14px 18px;display:flex;align-items:flex-start;gap:12px;border-bottom:1px solid #e9d5ff;">'
      +'<span style="font-size:22px;margin-top:2px;">&#x270F;&#xFE0F;</span>'
      +'<div style="flex:1;min-width:0;">'
        +'<div style="font-weight:700;font-size:16px;color:#5b21b6;">'+escConH(p.proveedor)+' <span style="font-size:12px;color:#7c3aed;font-weight:500;">— Modo edición</span></div>'
        +'<div style="font-size:11px;color:#7c3aed;margin-top:2px;">Edita cantidades, precios, IVA y observaciones. Click "Guardar" para persistir.</div>'
      +'</div>'
      +'<div style="display:flex;gap:8px;flex-shrink:0;">'
        +'<button class="btn" data-prov-idx="'+idx+'" onclick="saveConsolEdits(parseInt(this.dataset.provIdx))" '
          +'style="padding:8px 14px;font-size:12px;background:#16a34a;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:700;">&#x1F4BE; Guardar</button>'
        +'<button class="btn" data-prov-idx="'+idx+'" onclick="cancelConsolEdit(parseInt(this.dataset.provIdx))" '
          +'style="padding:8px 14px;font-size:12px;background:#fff;color:#64748b;border:1px solid #cbd5e1;border-radius:8px;cursor:pointer;font-weight:600;">Cancelar</button>'
      +'</div>'
    +'</div>'
    +'<div style="padding:12px 18px;">'+ocsHtml+'</div>'
  +'</div>';
}

function toggleConsolEdit(idx){
  _consolEditMode[idx] = !_consolEditMode[idx];
  var body = document.getElementById('consol-body');
  body.innerHTML = _consolCache.map(function(p, i){ return renderConsolCard(p, i); }).join('');
}

function cancelConsolEdit(idx){
  _consolEditMode[idx] = false;
  var body = document.getElementById('consol-body');
  body.innerHTML = _consolCache.map(function(p, i){ return renderConsolCard(p, i); }).join('');
}

// Recalcula el total de UNA OC en modo edit cuando cambian inputs.
// Aplica IVA 19% si el checkbox está marcado.
function recalcConsolOCFromEl(el){
  var box = el.closest('[data-oc-id]');
  if(box) recalcConsolOC(box.dataset.ocId);
}
function recalcConsolOC(ocId){
  var ocBox = document.querySelector('[data-oc-id="'+ocId+'"]');
  if(!ocBox) return;
  var conIva = ocBox.querySelector('[data-field="con_iva"]').checked;
  var subtotal = 0;
  ocBox.querySelectorAll('tr[data-item-id]').forEach(function(tr){
    var cant = parseFloat(tr.querySelector('[data-field="cantidad_g"]').value)||0;
    var prec = parseFloat(tr.querySelector('[data-field="precio_unitario"]').value)||0;
    var st = cant * prec;
    tr.querySelector('.row-subtotal').textContent = '$'+Number(st).toLocaleString('es-CO',{maximumFractionDigits:0});
    subtotal += st;
  });
  var total = conIva ? subtotal * 1.19 : subtotal;
  var totEl = ocBox.querySelector('.oc-total');
  if(totEl){
    var ivaLine = conIva
      ? ' <span style="font-size:10px;color:#0891b2;font-weight:500;">(subtotal $'+Number(subtotal).toLocaleString('es-CO',{maximumFractionDigits:0})+' + IVA)</span>'
      : '';
    totEl.innerHTML = 'Total OC: $'+Number(total).toLocaleString('es-CO',{maximumFractionDigits:0})+ivaLine;
  }
}

// Persiste TODOS los cambios de una card de proveedor:
//   - Por cada item modificado: PATCH /api/ordenes-compra/<oc>/items/<id>
//   - Por cada OC: PATCH /api/ordenes-compra/<oc>/editar (con_iva + observaciones)
async function saveConsolEdits(idx){
  var p = _consolCache[idx];
  if(!p) return;
  var card = document.getElementById('consol-edit-'+idx);
  if(!card) return;

  var errors = [];
  var ocBoxes = card.querySelectorAll('[data-oc-id]');
  for(var oi = 0; oi < ocBoxes.length; oi++){
    var ocBox = ocBoxes[oi];
    var ocNum = ocBox.dataset.ocNum;

    // 1) Items: detectar cambios vs original y PATCH
    var origOC = p.ocs.find(function(x){return x.numero_oc===ocNum;});
    var origItems = (origOC && origOC.items_raw) || [];
    var rows = ocBox.querySelectorAll('tr[data-item-id]');
    for(var ri = 0; ri < rows.length; ri++){
      var tr = rows[ri];
      var itemId = parseInt(tr.dataset.itemId, 10);
      var newCant = parseFloat(tr.querySelector('[data-field="cantidad_g"]').value)||0;
      var newPrec = parseFloat(tr.querySelector('[data-field="precio_unitario"]').value)||0;
      var orig = origItems.find(function(it){return it.id===itemId;});
      if(!orig) continue;
      if(Math.abs(newCant-(orig.cantidad_g||0))>0.001 || Math.abs(newPrec-(orig.precio_unitario||0))>0.001){
        try {
          var rr = await fetch('/api/ordenes-compra/'+encodeURIComponent(ocNum)+'/items/'+itemId, _fetchOpts('PATCH', {cantidad_g:newCant, precio_unitario:newPrec}));
          if(!rr.ok){ var dd = await rr.json().catch(function(){return{};}); errors.push(ocNum+' item '+itemId+': '+(dd.error||rr.status)); }
        } catch(e){ errors.push(ocNum+' item '+itemId+': '+e.message); }
      }
    }

    // 2) OC: con_iva + observaciones (PATCH parcial — el backend mantiene proveedor/categoria/etc. si no van).
    //    Aun asi enviamos proveedor explicitamente como defensa en profundidad.
    var conIva = ocBox.querySelector('[data-field="con_iva"]').checked;
    var obs = ocBox.querySelector('[data-field="observaciones"]').value || '';
    if(origOC && (conIva !== !!origOC.con_iva || obs !== (origOC.observaciones||''))){
      try {
        var rr2 = await fetch('/api/ordenes-compra/'+encodeURIComponent(ocNum)+'/editar', _fetchOpts('PATCH', {
            proveedor: p.proveedor || origOC.proveedor || '',
            con_iva: conIva?1:0,
            observaciones: obs
          }));
        if(!rr2.ok){ var dd2 = await rr2.json().catch(function(){return{};}); errors.push(ocNum+' OC: '+(dd2.error||rr2.status)); }
      } catch(e){ errors.push(ocNum+' OC: '+e.message); }
    }
  }

  if(errors.length){
    alert('Errores al guardar: '+errors.join(' | '));
  } else {
    alert('Cambios guardados correctamente.');
  }
  _consolEditMode[idx] = false;
  loadConsolidado();
}

async function copiarPedido(idx){
  var p = _consolCache[idx];
  if(!p){ alert('Error: proveedor no encontrado'); return; }
  var fecha = new Date().toLocaleDateString('es-CO',{day:'2-digit',month:'long',year:'numeric'});
  var lines = [];
  lines.push('SOLICITUD DE COMPRA — '+p.proveedor);
  if(p.nit) lines.push('NIT: '+p.nit);
  if(p.contacto) lines.push('Contacto: '+p.contacto);
  if(p.telefono) lines.push('Tel: '+p.telefono);
  lines.push('Fecha: '+fecha);
  lines.push('');
  if(p.items && p.items.length > 0){
    p.items.forEach(function(it){
      var cant = Math.round(it.cantidad_total_g||0).toLocaleString('es-CO')+' g';
      var sub = it.subtotal_total > 0
        ? '  ($'+Number(it.subtotal_total).toLocaleString('es-CO',{maximumFractionDigits:0})+')'
        : '';
      var _nom = (it.nombre_inci && it.nombre_mp && it.nombre_inci!==it.nombre_mp)
        ? it.nombre_inci+' ('+it.nombre_mp+')'
        : (it.nombre_inci||it.nombre_mp||'');
      lines.push('- '+_nom+': '+cant+sub);
    });
  } else {
    p.ocs.forEach(function(o){
      var desc = o.observaciones || o.categoria || '';
      lines.push('- '+o.numero_oc+' ('+o.estado+'): '+(desc?desc+' — ':'')+
        '$'+Number(o.valor_total).toLocaleString('es-CO',{maximumFractionDigits:0}));
    });
  }
  lines.push('');
  lines.push('Total: $'+Number(p.valor_total).toLocaleString('es-CO',{maximumFractionDigits:0}));
  lines.push('OCs: '+p.ocs.map(function(o){return o.numero_oc;}).join(', '));
  var texto = lines.join('\\n');
  try{
    await navigator.clipboard.writeText(texto);
    var btn = document.querySelector('[data-consol-idx="'+idx+'"]');
    if(btn){ var orig=btn.innerHTML; btn.innerHTML='&#x2705; Copiado!'; btn.style.background='#22c55e';
      setTimeout(function(){btn.innerHTML=orig;btn.style.background='#3b82f6';},2000); }
  }catch(e){
    var ta = document.createElement('textarea');
    ta.value = texto; document.body.appendChild(ta); ta.select();
    document.execCommand('copy'); document.body.removeChild(ta);
    alert('Copiado al portapapeles.');
  }
}

async function eliminarOCsGrupo(idx){
  var p = _consolCache[idx];
  if(!p) return;
  // Solo Borrador/Rechazada (el backend valida lo mismo · no toca Autorizada/Recibida/Pagada).
  var dels = (p.ocs||[]).filter(function(o){ return o.estado==='Borrador'||o.estado==='Rechazada'; });
  if(!dels.length){ alert('Solo se pueden eliminar OCs en Borrador o Rechazada.'); return; }
  var nums = dels.map(function(o){ return o.numero_oc; });
  if(!confirm('¿Eliminar '+nums.length+' OC(s) en Borrador/Rechazada de '+(p.proveedor||'')+'?\\n\\n'
              +nums.join(', ')+'\\n\\nSe revierten las solicitudes vinculadas (vuelven a Pendiente). No se puede deshacer.')) return;
  var fail = [];
  for(var i=0;i<nums.length;i++){
    try{
      var r = await fetch('/api/ordenes-compra/'+encodeURIComponent(nums[i]), _fetchOpts('DELETE'));
      if(!r.ok){ var d = await r.json().catch(function(){return {};}); fail.push(nums[i]+': '+(d.error||('codigo '+r.status))); }
    }catch(e){ fail.push(nums[i]+': '+e); }
  }
  if(fail.length) alert('No se pudieron eliminar:\\n'+fail.join('\\n'));
  else alert('\\u2713 '+nums.length+' OC(s) eliminada(s).');
  if(typeof loadConsolidado==='function') await loadConsolidado();
  if(typeof loadData==='function') await loadData();
}

// Eliminar UNA OC autorizada por error (Catalina) · el backend rechaza si ya tiene pago/recepción.
async function eliminarOCAutorizada(num){
  if(!num) return;
  if(!confirm('¿Eliminar la OC AUTORIZADA '+num+'?\\n\\nUsala solo si la autorizaste por error. Solo se puede si la OC NO tiene pago ni recepción.\\nLa solicitud vinculada vuelve a Pendiente. No se puede deshacer.')) return;
  try{
    var r = await fetch('/api/ordenes-compra/'+encodeURIComponent(num), _fetchOpts('DELETE'));
    var d = await r.json().catch(function(){ return {}; });
    if(!r.ok){ alert('No se pudo eliminar '+num+':\\n'+(d.error||('codigo '+r.status))); return; }
    alert('\\u2713 OC '+num+' eliminada. La solicitud volvió a Pendiente.');
  }catch(e){ alert('Error eliminando '+num+': '+e); }
  if(typeof loadConsolidado==='function') await loadConsolidado();
  if(typeof loadData==='function') await loadData();
}

function _pedidoDocHtml(idx){
  var p = _consolCache[idx];
  if(!p) return '';
  var hoy = new Date();
  var fechaStr = hoy.toLocaleDateString('es-CO',{year:'numeric',month:'2-digit',day:'2-digit'});
  var numDoc = String(hoy.getFullYear()).slice(-2)
    +String(hoy.getMonth()+1).padStart(2,'0')
    +String(hoy.getDate()).padStart(2,'0')
    +'-'+(idx+1);

  // ── Calcular subtotal, IVA, total ──────────────────────────────────────
  var subtotal = 0;
  if(p.items && p.items.length > 0){
    p.items.forEach(function(it){ subtotal += it.subtotal_total || 0; });
  } else {
    p.ocs.forEach(function(o){ subtotal += o.valor_total || 0; });
  }
  if(subtotal === 0) subtotal = p.valor_total || 0;
  // IVA 19% si el total registrado sugiere que ya lo incluye, no lo sumamos doble
  // En el doc manual el IVA se muestra separado; aquí calculamos desde subtotal
  var iva = 0;  // Por defecto sin IVA; usuario puede editar al imprimir
  var total = subtotal + iva;
  var fmtCOP = function(n){ return '$'+Number(n||0).toLocaleString('es-CO',{minimumFractionDigits:0,maximumFractionDigits:0})+',00'; };

  // ── Filas de detalle ───────────────────────────────────────────────────
  var detalleRows = '';
  if(p.items && p.items.length > 0){
    p.items.forEach(function(it){
      var cant = Math.round(it.cantidad_total_g||0).toLocaleString('es-CO')+' g';
      detalleRows += '<tr>'
        +'<td>'+escConH(it.codigo_mp||'')+'</td>'
        +'<td>'+escConH(it.nombre_inci||it.nombre_mp)+((it.nombre_inci&&it.nombre_mp&&it.nombre_inci!==it.nombre_mp)?'<span style="color:#a8a29e;font-size:11px"> ('+escConH(it.nombre_mp)+')</span>':'')+'</td>'
        +'<td class="c">'+cant+'</td>'
        +'<td class="r">'+(it.precio_unitario>0?fmtCOP(it.precio_unitario):'$0,00')+'</td>'
        +'<td class="r">'+(it.subtotal_total>0?fmtCOP(it.subtotal_total):'$0,00')+'</td>'
        +'</tr>';
    });
  } else {
    p.ocs.forEach(function(o){
      var desc = o.observaciones || o.categoria || '';
      detalleRows += '<tr>'
        +'<td></td>'
        +'<td>'+escConH(desc||o.numero_oc)+'</td>'
        +'<td class="c">1</td>'
        +'<td class="r">'+fmtCOP(o.valor_total)+'</td>'
        +'<td class="r">'+fmtCOP(o.valor_total)+'</td>'
        +'</tr>';
    });
  }
  // Filas vacías para completar mínimo 6 filas (como en el doc manual)
  var filledRows = p.items.length || p.ocs.length;
  for(var z=filledRows; z<6; z++){
    detalleRows += '<tr><td></td><td></td><td></td><td class="r">$0,00</td><td class="r">$0,00</td></tr>';
  }

  // ── Datos de pago del proveedor ────────────────────────────────────────
  var infoPago = p.banco && p.num_cuenta
    ? p.banco+'   '+escConH(p.proveedor)+'   '+p.num_cuenta+'   '+(p.tipo_cuenta||'')
    : '';

  // ── Observaciones consolidadas ─────────────────────────────────────────
  var justLines = [];
  p.ocs.forEach(function(o){ if(o.observaciones) justLines.push(o.numero_oc+': '+o.observaciones); });
  var justif = justLines.join(' | ') || p.ocs.map(function(o){return o.numero_oc;}).join(', ');
  // Justificación por MP: dónde se gasta cada cantidad / en qué producción
  // (viene de la SOLICITUD vinculada · texto "usada por N producto(s): ...").
  var justifItemsHtml = '';
  (p.items||[]).forEach(function(it){
    if(it.justificacion){
      var cantTxt = Math.round(it.cantidad_total_g||0).toLocaleString('es-CO')+' g';
      justifItemsHtml += '<div style="margin-bottom:3px;">&bull; <b>'+escConH(it.nombre_inci||it.nombre_mp)+'</b> ('+cantTxt+'): '+escConH(it.justificacion)+'</div>';
    }
  });

  var html = `<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<title>Orden de Compra ${numDoc}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:Arial,sans-serif;font-size:11px;color:#000;background:#fff;}
.page{width:900px;margin:0 auto;padding:24px 28px;}
/* Encabezado empresa */
.hdr-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;}
.oc-title{font-size:22px;font-weight:900;color:#1a1a1a;letter-spacing:0.5px;text-transform:uppercase;}
.oc-lote{font-size:28px;font-weight:900;color:#1a6bbf;letter-spacing:1px;}
.oc-logo img{height:78px !important;width:auto !important;max-width:280px;}
/* Tabla principal de estructura */
table.main{width:100%;border-collapse:collapse;}
table.main td, table.main th{border:1px solid #bbb;padding:4px 7px;vertical-align:middle;}
.label-cell{font-weight:700;text-align:right;background:#f0f0f0;width:140px;font-size:10px;}
.blue{color:#1a6bbf;font-weight:700;}
.hdr-company{font-size:12px;font-weight:700;color:#1a6bbf;}
.section-title{background:#1a1a1a;color:#fff;font-weight:700;font-size:11px;padding:5px 8px;text-align:center;letter-spacing:1px;}
/* Tabla de ítems */
table.items{width:100%;border-collapse:collapse;margin:0;}
table.items th{background:#3a3a3a;color:#fff;padding:5px 7px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;}
table.items td{border:1px solid #ccc;padding:4px 7px;font-size:11px;}
table.items td.c{text-align:center;}
table.items td.r{text-align:right;}
/* Totales */
.tot-label{font-weight:700;text-align:right;padding:4px 8px;border:1px solid #ccc;background:#f5f5f5;}
.tot-val{font-weight:700;text-align:right;padding:4px 10px;border:1px solid #ccc;}
.tot-bold{font-size:13px;font-weight:900;background:#1a1a1a;color:#fff;}
/* Info pago */
.info-row td{background:#e8f0fb;font-size:10px;padding:4px 7px;border:1px solid #bbb;}
/* Firma */
.firma-row td{padding:6px 8px;border:1px solid #ccc;font-size:10px;font-weight:700;}
.firma-val{height:28px;}
/* Botones */
.no-print{text-align:right;margin-bottom:16px;}
.no-print button{padding:9px 22px;border:none;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer;}
.btn-print{background:#1a6bbf;color:#fff;margin-right:8px;}
.btn-close{background:#e2e8f0;color:#333;}
@media print{
  .no-print{display:none!important;}
  .page{padding:12px 16px;width:100%;}
  @page{size:A4;margin:12mm 8mm;}
}
</style>
</head>
<body>
<div class="page">

<div class="no-print">
  <button class="btn-print" onclick="window.print()">&#x1F5A8; Imprimir / Guardar PDF</button>
  <button class="btn-close" onclick="window.close()">Cerrar</button>
</div>

<!-- TÍTULO -->
<table class="main" style="margin-bottom:2px;">
  <tr>
    <td colspan="2" class="oc-logo" style="border:none;padding-bottom:4px;vertical-align:middle;">
      <img src="data:image/png;base64,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" alt="HHA Group" style="height:72px;width:auto;display:block;margin-bottom:6px;">
    </td>
    <td style="text-align:right;border:none;vertical-align:middle;">
      <div class="oc-title">ORDEN DE COMPRA</div>
      <div class="oc-lomdte" style="font-size:20px;font-weight:900;color:#2d7a74;">${numDoc}</div>
      <div style="font-size:10px;color:#64748b;margin-top:4px;">Generado por Sistema HHA &bull; ${fechaStr}</div>
    </td>
  </tr>
</table>

<!-- DATOS ESPAGIRIA + FECHAS -->
<table class="main" style="margin-bottom:2px;">
  <tr>
    <td colspan="4" class="hdr-company">ESPAGIRIA LABORATORIO S.A.S</td>
    <td colspan="2" class="blue" style="text-align:center;background:#e8f0fb;">FECHA</td>
  </tr>
  <tr>
    <td class="label-cell">NIT:</td>
    <td colspan="3">901.622.676-6</td>
    <td colspan="2" style="text-align:center;">${fechaStr}</td>
  </tr>
  <tr>
    <td class="label-cell">DIRECCIÓN:</td>
    <td colspan="3">CARRERA 1 #32-46  SAN FRANCISCO, Cali</td>
    <td class="blue" style="text-align:center;background:#e8f0fb;">NÚMERO DE ORDEN</td>
    <td style="text-align:center;font-weight:700;">${numDoc}</td>
  </tr>
  <tr>
    <td class="label-cell">TELÉFONO:</td>
    <td colspan="3">3235180113</td>
    <td class="blue" style="text-align:center;background:#e8f0fb;"># PROVEEDOR</td>
    <td style="text-align:center;">${escConH(p.nit||'—')}</td>
  </tr>
  <tr>
    <td class="label-cell">EMAIL:</td>
    <td colspan="3">catalina.erazoa.el@gmail.com</td>
    <td colspan="2"></td>
  </tr>
</table>

<!-- DATOS PROVEEDOR + SOLICITADO POR -->
<table class="main" style="margin-bottom:2px;">
  <tr>
    <td colspan="4" class="hdr-company">${escConH(p.proveedor)}</td>
    <td colspan="2" class="blue" style="text-align:center;background:#e8f0fb;">SOLICITADO POR:</td>
  </tr>
  <tr>
    <td class="label-cell">DIRECCIÓN</td>
    <td colspan="3">${escConH(p.direccion||'')||'&nbsp;'}</td>
    <td colspan="2" style="text-align:center;font-weight:700;">${escConH(p.solicitado_por||'—')}</td>
  </tr>
  <tr>
    <td class="label-cell">CORREO</td>
    <td colspan="3">${escConH(p.email||'')}</td>
    <td class="blue" style="text-align:center;background:#e8f0fb;">FECHA LÍMITE PAGO</td>
    <td style="text-align:center;">${escConH(p.condiciones_pago||'')}</td>
  </tr>
  <tr>
    <td class="label-cell">CONTACTO VENTAS</td>
    <td colspan="3">${escConH(p.contacto||'')}</td>
    <td colspan="2"></td>
  </tr>
  <tr>
    <td class="label-cell">TELÉFONO</td>
    <td colspan="3">${escConH(p.telefono||'')}</td>
    <td colspan="2"></td>
  </tr>
</table>

<!-- TABLA ÍTEMS -->
<table class="items" style="margin-bottom:0;">
  <thead>
    <tr>
      <th style="width:90px;">CÓDIGO</th>
      <th>DESCRIPCIÓN</th>
      <th style="width:90px;">CANTIDAD</th>
      <th style="width:120px;">PRECIO UNITARIO</th>
      <th style="width:120px;">TOTAL</th>
    </tr>
  </thead>
  <tbody>
    ${detalleRows}
  </tbody>
</table>

<!-- JUSTIFICACIÓN + TOTALES -->
<table class="main" style="margin-top:0;">
  <tr>
    <td rowspan="4" colspan="3" style="vertical-align:top;width:55%;">
      <div style="font-weight:700;font-size:10px;margin-bottom:4px;">JUSTIFICACIÓN · DESTINO EN PRODUCCIÓN:</div>
      <div style="font-size:10px;">${justifItemsHtml || escConH(justif)}</div>
    </td>
    <td class="tot-label">SUBTOTAL</td>
    <td class="tot-val">${fmtCOP(subtotal)}</td>
  </tr>
  <tr>
    <td class="tot-label">IVA</td>
    <td class="tot-val" id="iva-val">${fmtCOP(iva)}</td>
  </tr>
  <tr>
    <td class="tot-label">SALDO A FAVOR</td>
    <td class="tot-val">$0,00</td>
  </tr>
  <tr>
    <td class="tot-label tot-bold">TOTAL</td>
    <td class="tot-val tot-bold" id="total-val">${fmtCOP(total)}</td>
  </tr>
</table>

<!-- INFORMACIÓN DE PAGO -->
<table class="main" style="margin-top:2px;">
  <tr>
    <td class="label-cell blue" style="background:#d0e4fa;width:140px;">INFORMACIÓN DE PAGO</td>
    <td colspan="4" style="font-size:11px;">${infoPago}</td>
  </tr>
  <tr>
    <td class="label-cell blue" style="background:#d0e4fa;">CONDICIONES DE ENTREGA</td>
    <td colspan="4"></td>
  </tr>
  <tr>
    <td class="label-cell blue" style="background:#d0e4fa;">TIEMPO DE LLEGADA DESPUÉS PAGO</td>
    <td colspan="4"></td>
  </tr>
</table>

<!-- FIRMAS -->
<table class="main" style="margin-top:8px;">
  <tr>
    <td class="firma-row" style="width:25%;">REVISADO POR (DIR. TÉCNICA):</td>
    <td class="firma-row firma-val" style="width:25%;"></td>
    <td class="firma-row" style="width:25%;">REVISADO POR (CONTADORA):</td>
    <td class="firma-row firma-val" style="width:25%;">Contadora</td>
  </tr>
  <tr>
    <td class="firma-row">FECHA</td>
    <td class="firma-row firma-val"></td>
    <td class="firma-row">FECHA</td>
    <td class="firma-row firma-val"></td>
  </tr>
  <tr>
    <td class="firma-row">APROBADO POR (REPRESENTANTE LEGAL):</td>
    <td class="firma-row firma-val">Representante Legal</td>
    <td class="firma-row">FECHA</td>
    <td class="firma-row firma-val"></td>
  </tr>
</table>

<!-- IVA selector (no se imprime) -->
<div class="no-print" style="margin-top:16px;padding:12px;background:#f0f4ff;border-radius:8px;display:flex;align-items:center;gap:16px;">
  <span style="font-weight:700;font-size:13px;">&#9432; Ajustar IVA:</span>
  <label><input type="radio" name="iva_opt" value="0" checked onchange="recalcIVA(this.value,${subtotal})"> Sin IVA</label>
  <label><input type="radio" name="iva_opt" value="0.19" onchange="recalcIVA(this.value,${subtotal})"> 19%</label>
  <label><input type="radio" name="iva_opt" value="0.05" onchange="recalcIVA(this.value,${subtotal})"> 5%</label>
  <label style="display:flex;align-items:center;gap:4px;">
    Otro %: <input type="number" id="iva-custom" min="0" max="100" step="1" style="width:56px;border:1px solid #ccc;border-radius:4px;padding:3px 6px;"
      oninput="recalcIVA(document.getElementById('iva-custom').value/100,${subtotal})">
  </label>
  <span style="font-size:11px;color:#64748b;">Ajusta y luego imprime</span>
</div>

</div>
<script>
function recalcIVA(rate,sub){
  var r = parseFloat(rate)||0;
  var iva = Math.round(sub*r);
  var tot = sub+iva;
  var fmt = function(n){ return '$'+Number(n).toLocaleString('es-CO',{minimumFractionDigits:0,maximumFractionDigits:0})+',00'; };
  var iv = document.getElementById('iva-val');
  var tv = document.getElementById('total-val');
  if(iv) iv.textContent = fmt(iva);
  if(tv) tv.textContent = fmt(tot);
}
<\\/script>
</body>
</html>`;
  return html;
}

function _abrirImpresion(html){
  var win = window.open('', '_blank', 'width=980,height=860');
  if(!win){ alert('Permite las ventanas emergentes para este sitio e intenta de nuevo.'); return; }
  win.document.write(html);
  win.document.close();
}

function imprimirPedido(idx){
  var html = _pedidoDocHtml(idx);
  if(html) _abrirImpresion(html);
}

// Imprime TODAS las órdenes consolidadas en UN solo documento, cada proveedor en
// su propia hoja (page-break). Reutiliza el generador por-proveedor: extrae el bloque
// .page de cada doc (con indexOf, sin regex/backslashes para no romper el escape Python)
// y los concatena bajo un único shell con el mismo CSS. Mantiene el botón por-proveedor.
function imprimirTodas(){
  if(!_consolCache || !_consolCache.length){ alert('No hay órdenes para imprimir.'); return; }
  var docs = [];
  for(var i=0;i<_consolCache.length;i++){
    var h = _pedidoDocHtml(i);
    if(h) docs.push(h);
  }
  if(!docs.length){ alert('No hay órdenes para imprimir.'); return; }
  // CSS del primer documento (todos comparten el mismo)
  var css = '';
  var s0 = docs[0].indexOf('<style>');
  var s1 = docs[0].indexOf('</style>');
  if(s0>=0 && s1>s0) css = docs[0].slice(s0+7, s1);
  // Cada .page (incluye su toolbar .no-print y su script recalcIVA · ambos ocultos al imprimir)
  var pages = [];
  for(var k=0;k<docs.length;k++){
    var a = docs[k].indexOf('<div class="page">');
    var b = docs[k].indexOf('</body>');
    if(a>=0 && b>a) pages.push(docs[k].slice(a, b));
  }
  if(!pages.length){ alert('No se pudo preparar la impresión.'); return; }
  var saltos = pages.join('<div style="page-break-after:always;"></div>');
  var barra = '<div class="no-print" style="position:sticky;top:0;background:#0f766e;padding:10px;text-align:center;z-index:99;">'
    +'<button onclick="window.print()" style="padding:9px 22px;border:none;border-radius:5px;font-weight:700;cursor:pointer;background:#fff;color:#0f766e;margin:0 6px;">&#x1F5A8; Imprimir las '+pages.length+' &oacute;rdenes</button>'
    +'<button onclick="window.close()" style="padding:9px 22px;border:none;border-radius:5px;font-weight:700;cursor:pointer;background:#e2e8f0;color:#333;margin:0 6px;">Cerrar</button>'
    +'</div>';
  var html = '<!DOCTYPE html><html lang="es" translate="no"><head><meta charset="UTF-8">'
    +'<title>Ordenes de compra - '+pages.length+'</title><style>'+css+'</style></head><body>'
    +barra+saltos+'</body></html>';
  _abrirImpresion(html);
}


function escConH(s){
  var d = document.createElement('div');
  d.appendChild(document.createTextNode(s||''));
  return d.innerHTML;
}


async function eliminarSolicitud(num){
  if(!confirm('Eliminar solicitud '+num+'?')) return;
  try{
    var r=await fetch('/api/solicitudes-compra/'+encodeURIComponent(num),_fetchOpts('DELETE'));
    var d=await r.json();
    if(d.ok){
      // Remove card from DOM immediately for snappy UX
      var card=document.querySelector('[data-sol="'+num+'"]');
      if(card){var parent=card.closest('.card');if(parent)parent.remove();}
      // Reload all relevant data
      if(typeof loadSolicitudes==='function') loadSolicitudes();
      if(typeof loadCCSolicitudes==='function') loadCCSolicitudes();
      if(typeof loadMarketing==='function') loadMarketing();
      else if(typeof renderMarketing==='function') renderMarketing();
    } else {
      alert('No se pudo eliminar: '+(d.error||'error desconocido'));
    }
  }catch(e){alert('Error: '+e.message);}
}

// ════════════════════════════════════════════════════════════════════════
// Tab "Por Pagar" — vista unificada de pendientes de pago
// ════════════════════════════════════════════════════════════════════════

// ALTA-5 fix · _esc duplicado borrado (ya está declarado en línea 1730)
function _money(n){return '$'+Number(n||0).toLocaleString('es-CO');}

// Abre el modal de pago con info de la OC + historial de pagos previos.
async function payOC(numero_oc){
  // Reset modal
  document.getElementById('pago-num').value = numero_oc;
  document.getElementById('pago-monto').value = '';
  document.getElementById('pago-medio').value = 'Transferencia';
  document.getElementById('pago-obs').value = '';
  document.getElementById('pago-factura').value = '';
  document.getElementById('pago-img-file').value = '';
  document.getElementById('pago-img-preview').style.display = 'none';

  // Cargar info de la OC + historial de pagos
  try{
    var r = await fetch('/api/ordenes-compra/'+encodeURIComponent(numero_oc)+'/pagos');
    if(r.ok){
      var d = await r.json();
      var info = document.getElementById('pago-info');
      if(info){
        info.innerHTML = '<div><strong>'+_esc(numero_oc)+'</strong> · valor total '+_money(d.valor_total_oc)+
          ' · pagado '+_money(d.total_pagado)+' · pendiente <strong style="color:#dc2626;">'+_money(d.pendiente)+'</strong></div>';
      }
      // Pre-llenar con el monto pendiente
      if(d.pendiente > 0) document.getElementById('pago-monto').value = d.pendiente;

      // Historial de pagos previos (pagos parciales)
      var hist = document.getElementById('pago-historial');
      var histList = document.getElementById('pago-historial-list');
      if((d.pagos||[]).length){
        hist.style.display = 'block';
        histList.innerHTML = d.pagos.map(function(p){
          return '<div style="padding:4px 0;border-bottom:1px solid #e5e7eb;">'+
            (p.fecha_pago||'').replace('T',' ').slice(0,16)+' · '+_money(p.monto)+' · '+_esc(p.medio)+
            (p.numero_factura_proveedor ? ' · fac '+_esc(p.numero_factura_proveedor) : '')+
            ' · <em>'+_esc(p.registrado_por||'?')+'</em></div>';
        }).join('');
      } else {
        hist.style.display = 'none';
      }
    }
  }catch(e){}

  openModal('m-pago');
}

// ═══════════════════════════════════════════════════════════════════
// Tab "Atrasadas" · Sebastián 23-may-2026 · cierre flujo Compras
// OCs Autorizada/Parcial sin recibir tras lead_time + buffer
// ═══════════════════════════════════════════════════════════════════
async function cargarOcsAtrasadas(){
  var div = document.getElementById('atrasadas-contenido');
  var resumen = document.getElementById('atrasadas-resumen');
  var bufferEl = document.getElementById('atrasadas-buffer');
  var buffer = bufferEl ? parseInt(bufferEl.value, 10) : 7;
  if(isNaN(buffer) || buffer < 0) buffer = 7;
  div.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px">Cargando…</div>';
  resumen.innerHTML = '';
  try{
    var r = await fetch('/api/compras/ocs-atrasadas?buffer_dias=' + buffer);
    if(r.status === 401){ window.location.href = '/login'; return; }
    if(!r.ok){
      div.innerHTML = '<div style="color:#dc2626;padding:20px">Error HTTP ' + r.status + '</div>';
      return;
    }
    var d = await r.json();
    // Resumen
    var n = d.total || 0;
    resumen.innerHTML = '<span style="background:' + (n>0?'#fee2e2':'#dcfce7') + ';color:' + (n>0?'#991b1b':'#15803d') + ';padding:6px 12px;border-radius:8px;font-weight:700;font-size:13px">' +
      (n>0 ? ('🚨 ' + n + ' OC(s) atrasada(s)') : '✓ Sin OCs atrasadas · todo al día') +
      '</span>' +
      '<span style="color:#64748b">Buffer ' + d.buffer_dias + 'd sobre lead_time del proveedor · medido hoy ' + d.hoy + '</span>';
    // Badge en tab
    var badge = document.getElementById('atrasadas-badge');
    if(badge){
      if(n > 0){ badge.style.display = 'inline-block'; badge.textContent = n; }
      else { badge.style.display = 'none'; }
    }
    if(n === 0){
      div.innerHTML = '<div style="text-align:center;color:#15803d;padding:30px;background:#f0fdf4">✓ Sin OCs atrasadas · todo al día</div>';
      return;
    }
    // Tabla
    var html = '<table style="width:100%;border-collapse:collapse;font-size:13px">';
    html += '<thead><tr style="background:#f8fafc;color:#475569;border-bottom:1px solid #e2e8f0">';
    html += '<th style="text-align:left;padding:10px 12px;font-weight:700">OC</th>';
    html += '<th style="text-align:left;padding:10px 12px;font-weight:700">Proveedor</th>';
    html += '<th style="text-align:left;padding:10px 12px;font-weight:700">Creador</th>';
    html += '<th style="text-align:center;padding:10px 12px;font-weight:700">Estado</th>';
    html += '<th style="text-align:right;padding:10px 12px;font-weight:700">Días OC</th>';
    html += '<th style="text-align:right;padding:10px 12px;font-weight:700">Lead time</th>';
    html += '<th style="text-align:right;padding:10px 12px;font-weight:700">Atraso</th>';
    html += '<th style="text-align:right;padding:10px 12px;font-weight:700">Valor</th>';
    html += '</tr></thead><tbody>';
    function _esc(s){
      if(s == null) return '';
      return String(s).replace(/[&<>"\']/g, function(c){
        return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
      });
    }
    function _fmtCop(n){
      if(!n) return '—';
      return '$' + Math.round(n).toLocaleString('es-CO');
    }
    (d.ocs || []).forEach(function(oc){
      var sev = oc.dias_atraso > 30 ? '#fef2f2' : (oc.dias_atraso > 14 ? '#fff7ed' : '#fefce8');
      var sevTc = oc.dias_atraso > 30 ? '#991b1b' : (oc.dias_atraso > 14 ? '#9a3412' : '#854d0e');
      html += '<tr style="border-bottom:1px solid #f1f5f9;background:' + sev + '">';
      html += '<td style="padding:8px 12px;font-family:ui-monospace;font-weight:700">' + _esc(oc.numero_oc) + '</td>';
      html += '<td style="padding:8px 12px">' + _esc(oc.proveedor) + '</td>';
      html += '<td style="padding:8px 12px;color:#64748b">' + _esc(oc.creador || '—') + '</td>';
      html += '<td style="padding:8px 12px;text-align:center;font-size:11px;font-weight:700;color:' + (oc.estado==='Parcial'?'#9a3412':'#1e40af') + '">' + _esc(oc.estado) + '</td>';
      html += '<td style="padding:8px 12px;text-align:right;font-family:ui-monospace">' + oc.dias_desde_oc + 'd</td>';
      html += '<td style="padding:8px 12px;text-align:right;font-family:ui-monospace;color:#64748b">' + oc.lead_time_dias + 'd</td>';
      html += '<td style="padding:8px 12px;text-align:right;font-family:ui-monospace;color:' + sevTc + ';font-weight:700">+' + oc.dias_atraso + 'd</td>';
      html += '<td style="padding:8px 12px;text-align:right;font-family:ui-monospace">' + _fmtCop(oc.valor_total) + '</td>';
      html += '</tr>';
    });
    html += '</tbody></table>';
    html += '<div style="font-size:11px;color:#64748b;padding:10px 12px;background:#f8fafc;border-top:1px solid #e2e8f0">💡 <strong>Cómo leer:</strong> "Atraso" = días sobre el lead_time del proveedor + buffer. Rojo &gt;30d, naranja &gt;14d, amarillo el resto. El lead_time se aprende automáticamente con cada recepción completa (EWMA 70/30).</div>';
    div.innerHTML = html;
  }catch(e){
    div.innerHTML = '<div style="color:#dc2626;padding:20px">Error red: ' + e.message + '</div>';
  }
}


// ═══════════════════════════════════════════════════════════════════
// Tab "Calidad recepción" · Sebastián 23-may-2026
// Histórico OCs con discrepancia + ranking proveedores
// ═══════════════════════════════════════════════════════════════════
async function cargarDiscrepancias(){
  var div = document.getElementById('discrep-contenido');
  var resumen = document.getElementById('discrep-resumen');
  var ranking = document.getElementById('discrep-ranking');
  var diasEl = document.getElementById('discrep-dias');
  var dias = diasEl ? parseInt(diasEl.value, 10) : 30;
  if(isNaN(dias) || dias < 1) dias = 30;
  div.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px">Cargando…</div>';
  ranking.innerHTML = 'Cargando…';
  resumen.innerHTML = '';
  try{
    var r = await fetch('/api/compras/recepciones-discrepancias?dias=' + dias);
    if(r.status === 401){ window.location.href = '/login'; return; }
    if(!r.ok){
      div.innerHTML = '<div style="color:#dc2626;padding:20px">Error HTTP ' + r.status + '</div>';
      return;
    }
    var d = await r.json();
    function _esc(s){
      if(s == null) return '';
      return String(s).replace(/[&<>"\']/g, function(c){
        return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
      });
    }
    function _fmtCop(n){
      if(!n) return '—';
      return '$' + Math.round(n).toLocaleString('es-CO');
    }
    // Resumen
    var n = d.total_ocs_con_discrepancia || 0;
    resumen.innerHTML = '<span style="background:' + (n>0?'#fee2e2':'#dcfce7') + ';color:' + (n>0?'#991b1b':'#15803d') + ';padding:6px 12px;border-radius:8px;font-weight:700;font-size:13px">' +
      (n>0 ? ('⚠ ' + n + ' OC(s) con discrepancia en ' + dias + 'd') : '✓ Sin discrepancias en ' + dias + 'd') +
      '</span>' +
      '<span style="color:#64748b">Hoy ' + d.hoy + '</span>';
    var badge = document.getElementById('discrep-badge');
    if(badge){
      if(n > 0){ badge.style.display = 'inline-block'; badge.textContent = n; }
      else { badge.style.display = 'none'; }
    }
    // Ranking proveedores
    var rk = d.ranking_proveedores || [];
    if(!rk.length){
      ranking.innerHTML = '<div style="color:#94a3b8">Sin recepciones en la ventana</div>';
    } else {
      var rkHtml = '<table style="width:100%;border-collapse:collapse;font-size:12px">';
      rkHtml += '<thead><tr style="color:#475569;border-bottom:1px solid #e2e8f0"><th style="text-align:left;padding:5px 6px">Proveedor</th><th style="text-align:right;padding:5px 6px">Recibidas</th><th style="text-align:right;padding:5px 6px">Discrep.</th><th style="text-align:right;padding:5px 6px">Tasa</th></tr></thead><tbody>';
      rk.forEach(function(p){
        var tasaCol = p.tasa_discrepancia_pct > 30 ? '#dc2626' : (p.tasa_discrepancia_pct > 10 ? '#ea580c' : (p.tasa_discrepancia_pct > 0 ? '#ca8a04' : '#16a34a'));
        rkHtml += '<tr style="border-bottom:1px solid #f1f5f9">';
        rkHtml += '<td style="padding:6px;font-weight:600">' + _esc(p.proveedor) + '</td>';
        rkHtml += '<td style="padding:6px;text-align:right;font-family:ui-monospace">' + p.total_recibidas + '</td>';
        rkHtml += '<td style="padding:6px;text-align:right;font-family:ui-monospace">' + p.con_discrepancia + '</td>';
        rkHtml += '<td style="padding:6px;text-align:right;font-family:ui-monospace;color:' + tasaCol + ';font-weight:700">' + p.tasa_discrepancia_pct + '%</td>';
        rkHtml += '</tr>';
      });
      rkHtml += '</tbody></table>';
      ranking.innerHTML = rkHtml;
    }
    // Tabla OCs con discrepancia
    if(n === 0){
      div.innerHTML = '<div style="text-align:center;color:#15803d;padding:30px;background:#f0fdf4">✓ Sin OCs con discrepancia en últimos ' + dias + 'd</div>';
      return;
    }
    var html = '<table style="width:100%;border-collapse:collapse;font-size:13px">';
    html += '<thead><tr style="background:#f8fafc;color:#475569;border-bottom:1px solid #e2e8f0">';
    html += '<th style="text-align:left;padding:10px 12px;font-weight:700">OC</th>';
    html += '<th style="text-align:left;padding:10px 12px;font-weight:700">Proveedor</th>';
    html += '<th style="text-align:left;padding:10px 12px;font-weight:700">Fecha recep.</th>';
    html += '<th style="text-align:left;padding:10px 12px;font-weight:700">Recibió</th>';
    html += '<th style="text-align:center;padding:10px 12px;font-weight:700">Items con faltante</th>';
    html += '<th style="text-align:right;padding:10px 12px;font-weight:700">Valor</th>';
    html += '<th style="text-align:left;padding:10px 12px;font-weight:700">Observaciones</th>';
    html += '</tr></thead><tbody>';
    (d.ocs || []).forEach(function(oc){
      var maxPct = 0;
      (oc.items_faltantes || []).forEach(function(it){ if(it.pct_faltante > maxPct) maxPct = it.pct_faltante; });
      var bg = maxPct > 30 ? '#fef2f2' : (maxPct > 10 ? '#fff7ed' : '#fefce8');
      html += '<tr style="border-bottom:1px solid #f1f5f9;background:' + bg + '">';
      html += '<td style="padding:8px 12px;font-family:ui-monospace;font-weight:700">' + _esc(oc.numero_oc) + '</td>';
      html += '<td style="padding:8px 12px">' + _esc(oc.proveedor) + '</td>';
      html += '<td style="padding:8px 12px">' + _esc(oc.fecha_recepcion) + '</td>';
      html += '<td style="padding:8px 12px;color:#64748b">' + _esc(oc.recibido_por || '—') + '</td>';
      // Items faltantes · expandible
      var itemsHtml = '<span style="font-weight:700;color:#dc2626">' + oc.n_items_faltantes + '</span>';
      if(oc.items_faltantes && oc.items_faltantes.length){
        itemsHtml += '<div style="font-size:11px;color:#64748b;margin-top:3px">';
        oc.items_faltantes.slice(0, 3).forEach(function(it){
          itemsHtml += '<div>' + _esc(it.codigo_mp) + ': ' + it.recibido + '/' + it.pedido + 'g (-' + it.pct_faltante + '%)</div>';
        });
        if(oc.items_faltantes.length > 3){
          itemsHtml += '<div style="color:#94a3b8">+' + (oc.items_faltantes.length - 3) + ' más</div>';
        }
        itemsHtml += '</div>';
      }
      html += '<td style="padding:8px 12px;text-align:center">' + itemsHtml + '</td>';
      html += '<td style="padding:8px 12px;text-align:right;font-family:ui-monospace">' + _fmtCop(oc.valor_total) + '</td>';
      html += '<td style="padding:8px 12px;font-size:11px;color:#64748b;max-width:280px">' + _esc(oc.observaciones_recepcion || '—') + '</td>';
      html += '</tr>';
    });
    html += '</tbody></table>';
    html += '<div style="font-size:11px;color:#64748b;padding:10px 12px;background:#f8fafc;border-top:1px solid #e2e8f0">💡 Filas rojas = faltante &gt;30%, naranja &gt;10%, ámbar el resto. Usá el ranking arriba para identificar proveedores recurrentes.</div>';
    div.innerHTML = html;
  }catch(e){
    div.innerHTML = '<div style="color:#dc2626;padding:20px">Error red: ' + e.message + '</div>';
  }
}


// ═══════════════════════════════════════════════════════════════════
// Tab "Mailbox facturas" · Sebastián 23-may-2026 · MBX UI
// ═══════════════════════════════════════════════════════════════════
async function cargarMailbox(){
  var div = document.getElementById('mailbox-contenido');
  var resumen = document.getElementById('mailbox-resumen');
  var diasEl = document.getElementById('mailbox-dias');
  var dias = diasEl ? parseInt(diasEl.value, 10) : 30;
  if(isNaN(dias) || dias < 1) dias = 30;
  div.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px">Cargando…</div>';
  resumen.innerHTML = '';
  try{
    var r = await fetch('/api/compras/mailbox-facturas?dias=' + dias);
    if(r.status === 401){ window.location.href = '/login'; return; }
    if(!r.ok){
      div.innerHTML = '<div style="color:#dc2626;padding:20px">Error HTTP ' + r.status + '</div>';
      return;
    }
    var d = await r.json();
    function _esc(s){
      if(s == null) return '';
      return String(s).replace(/[&<>"\']/g, function(c){
        return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
      });
    }
    function _money(n){
      if(!n) return '—';
      return '$' + Math.round(n).toLocaleString('es-CO');
    }
    var n = d.total || 0;
    var pend = d.n_pendientes || 0;
    resumen.innerHTML = '<span style="background:' + (pend>0?'#ede9fe':'#dcfce7') + ';color:' + (pend>0?'#5b21b6':'#15803d') + ';padding:6px 12px;border-radius:8px;font-weight:700;font-size:13px">' +
      (pend>0 ? ('📧 ' + pend + ' factura(s) pendiente(s) de completar') : ('✓ Sin pendientes (' + n + ' procesadas)')) +
      '</span><span style="color:#64748b">Ventana ' + dias + 'd</span>';
    var badge = document.getElementById('mailbox-badge');
    if(badge){
      if(pend > 0){ badge.style.display = 'inline-block'; badge.textContent = pend; }
      else { badge.style.display = 'none'; }
    }
    if(n === 0){
      div.innerHTML = '<div style="text-align:center;color:#15803d;padding:30px;background:#f0fdf4">📭 Mailbox vacío en últimos ' + dias + 'd</div>';
      return;
    }
    var html = '<table style="width:100%;border-collapse:collapse;font-size:13px">';
    html += '<thead><tr style="background:#f8fafc;color:#475569;border-bottom:1px solid #e2e8f0">';
    html += '<th style="text-align:left;padding:10px 12px;font-weight:700">Detectado</th>';
    html += '<th style="text-align:left;padding:10px 12px;font-weight:700">OC asociada</th>';
    html += '<th style="text-align:left;padding:10px 12px;font-weight:700">Proveedor</th>';
    html += '<th style="text-align:left;padding:10px 12px;font-weight:700">Factura</th>';
    html += '<th style="text-align:right;padding:10px 12px;font-weight:700">Valor OC</th>';
    html += '<th style="text-align:center;padding:10px 12px;font-weight:700">Estado</th>';
    html += '<th style="text-align:center;padding:10px 12px;font-weight:700">Acciones</th>';
    html += '</tr></thead><tbody>';
    (d.items || []).forEach(function(it){
      var bg = it.pendiente ? '#faf5ff' : '#fff';
      html += '<tr style="border-bottom:1px solid #f1f5f9;background:' + bg + '">';
      html += '<td style="padding:8px 12px">' + _esc(it.fecha) + '</td>';
      html += '<td style="padding:8px 12px;font-family:ui-monospace;font-weight:700">' + _esc(it.numero_oc) + '</td>';
      html += '<td style="padding:8px 12px">' + _esc(it.proveedor || '—') + '</td>';
      html += '<td style="padding:8px 12px;font-family:ui-monospace">' + _esc(it.numero_factura || '—') + '</td>';
      html += '<td style="padding:8px 12px;text-align:right;font-family:ui-monospace">' + _money(it.valor_oc) + '</td>';
      var estCol = it.pendiente ? '#5b21b6' : '#15803d';
      var estTxt = it.pendiente ? 'PENDIENTE' : it.medio;
      html += '<td style="padding:8px 12px;text-align:center;font-weight:700;font-size:11px;color:' + estCol + '">' + _esc(estTxt) + '</td>';
      html += '<td style="padding:8px 12px;text-align:center">';
      html += '<a href="/api/compras/mailbox-facturas/' + it.pago_id + '/comprobante" target="_blank" style="padding:4px 10px;background:#1e40af;color:#fff;text-decoration:none;border-radius:5px;font-size:11px;font-weight:700;margin-right:4px">👁 Ver</a>';
      // Sebastián 24-may-2026 · botón Completar · solo si pendiente · llena
      // monto + medio + factura · cambia row a pago real auditado y recalcula
      // estado OC (Pagada/Parcial según SUM)
      if(it.pendiente){
        html += '<button onclick="_mailboxCompletar(' + it.pago_id + ',' + (it.valor_oc||0) + ',&quot;' + _esc(it.numero_oc) + '&quot;)" style="padding:4px 10px;background:#16a34a;color:#fff;border:0;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer;margin-right:4px">✅ Completar</button>';
      }
      html += '<button onclick="_mailboxDescartar(' + it.pago_id + ')" style="padding:4px 10px;background:#fff;color:#dc2626;border:1px solid #dc2626;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">✕ Descartar</button>';
      html += '</td></tr>';
    });
    html += '</tbody></table>';
    html += '<div style="font-size:11px;color:#64748b;padding:10px 12px;background:#f8fafc;border-top:1px solid #e2e8f0">💡 El cron <code>job_mailbox_factura_proveedor</code> revisa el inbox cada día a las 7:15 AM y crea pagos PENDIENTE. Click <strong>Ver</strong> abre la factura adjunta. <strong>Descartar</strong> elimina la entrada (no afecta la OC).</div>';
    div.innerHTML = html;
  }catch(e){
    div.innerHTML = '<div style="color:#dc2626;padding:20px">Error red: ' + e.message + '</div>';
  }
}

async function _mailboxDescartar(pagoId){
  if(!confirm('¿Descartar esta factura del mailbox?\\n\\nNo afecta la OC, solo elimina la entrada del cron.')) return;
  try{
    var r = await fetch('/api/compras/mailbox-facturas/' + pagoId + '/descartar', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
    });
    if(!r.ok){ alert('Error: HTTP ' + r.status); return; }
    cargarMailbox();
  }catch(e){
    alert('Error red: ' + e.message);
  }
}

// Sebastián 24-may-2026 · completar factura PENDIENTE del mailbox · pide
// monto + medio + factura · backend UPDATE row + recalcula estado OC.
async function _mailboxCompletar(pagoId, valorOC, numeroOC){
  var sugMonto = valorOC > 0 ? valorOC : '';
  var monto = prompt('Monto del pago para OC ' + numeroOC + ' (sugerido: $' + Number(sugMonto).toLocaleString('es-CO') + '):', sugMonto);
  if(monto === null) return;
  monto = parseFloat(String(monto).replace(/[,.\\s$]/g,''));
  if(!monto || monto <= 0){ alert('Monto inválido'); return; }
  var medio = prompt('Medio de pago (Transferencia/Nequi/Daviplata/Efectivo/Bancolombia/...):', 'Transferencia');
  if(!medio) return;
  var fact = prompt('Número de factura del proveedor (opcional · vacío = mantener actual):', '');
  if(fact === null) return;
  var obs = prompt('Observaciones (opcional):', '');
  if(obs === null) obs = '';
  if(!confirm('Completar factura OC ' + numeroOC + '\\n\\nMonto: $' + monto.toLocaleString('es-CO') + '\\nMedio: ' + medio + '\\nFactura: ' + (fact||'(sin)') + '\\n\\nEsto recalcula el estado de la OC.')) return;
  try{
    var r = await fetch('/api/compras/mailbox-facturas/' + pagoId + '/completar', _fetchOpts('POST', {
      monto: monto, medio_pago: medio.trim(),
      numero_factura_proveedor: fact.trim(),
      observaciones: obs.trim()
    }));
    var d = await r.json();
    if(r.ok && d.ok){
      alert('✅ ' + numeroOC + ' · estado ' + d.estado_oc_anterior + ' → ' + d.estado_oc_nuevo + '\\n\\n' + (d.hint||''));
      cargarMailbox();
      loadData();
    } else {
      alert('Error: ' + (d.error || 'desconocido'));
    }
  }catch(e){ alert('Error red: ' + e.message); }
}


// ════════ COT COMPARADOR · Sebastián 23-may-2026 PM ════════
// Backend ya tenía 6 endpoints (mig 29, compras.py:10168+). UI nueva.
async function cargarCotizaciones(){
  var div = document.getElementById('cotiz-contenido');
  var resumen = document.getElementById('cotiz-resumen');
  div.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px">Cargando…</div>';
  try{
    var r = await fetch('/api/compras/cotizaciones/rondas');
    if(!r.ok){ div.innerHTML='<div style="color:#dc2626;padding:20px">Error '+r.status+'</div>'; return; }
    var d = await r.json();
    var rondas = d.rondas || d.items || [];
    var pend = rondas.filter(function(x){ return (x.estado||'').toLowerCase()==='abierta' || (x.estado||'').toLowerCase()==='pendiente'; }).length;
    var cerr = rondas.filter(function(x){ return (x.estado||'').toLowerCase()==='cerrada'; }).length;
    resumen.innerHTML =
      '<span style="background:#fef3c7;color:#92400e;padding:4px 10px;border-radius:6px;font-weight:700">🟡 Abiertas: '+pend+'</span>'+
      '<span style="background:#dcfce7;color:#166534;padding:4px 10px;border-radius:6px;font-weight:700;margin-left:6px">✓ Cerradas: '+cerr+'</span>'+
      '<span style="background:#f1f5f9;color:#475569;padding:4px 10px;border-radius:6px;margin-left:6px">Total últimas 50: '+rondas.length+'</span>';
    if(!rondas.length){
      div.innerHTML = '<div style="text-align:center;color:#64748b;padding:40px"><div style="font-size:14px;font-weight:700;margin-bottom:6px">No hay rondas de cotizaciones aún</div><div style="font-size:12px">Crea una desde la pestaña Planta → SOL agrupada → 💬 Cotizar</div></div>';
      return;
    }
    var html = '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#f1f5f9;color:#475569;font-weight:700">';
    html += '<th style="padding:8px 12px;text-align:left">Ronda #</th>';
    html += '<th style="padding:8px 12px;text-align:left">MP / Item</th>';
    html += '<th style="padding:8px 12px;text-align:left">Creada</th>';
    html += '<th style="padding:8px 12px;text-align:center">Recibidas / Solic</th>';
    html += '<th style="padding:8px 12px;text-align:right">Mejor precio</th>';
    html += '<th style="padding:8px 12px;text-align:center">Estado</th>';
    html += '<th style="padding:8px 12px;text-align:center">Acción</th>';
    html += '</tr></thead><tbody>';
    rondas.forEach(function(r2){
      var est = (r2.estado||'').toLowerCase();
      var bgEst = est==='cerrada' ? '#dcfce7' : (est==='cancelada'?'#fee2e2':'#fef3c7');
      var fgEst = est==='cerrada' ? '#166534' : (est==='cancelada'?'#991b1b':'#92400e');
      html += '<tr style="border-bottom:1px solid #f1f5f9">';
      html += '<td style="padding:8px 12px;font-family:ui-monospace;font-weight:700">#'+(r2.ronda_id||r2.id)+'</td>';
      html += '<td style="padding:8px 12px">'+_esc(r2.material_nombre||r2.descripcion||r2.material_id||'—')+'</td>';
      html += '<td style="padding:8px 12px;color:#64748b">'+_esc((r2.creada_en||'').slice(0,10))+'</td>';
      html += '<td style="padding:8px 12px;text-align:center"><span style="background:#f1f5f9;padding:2px 8px;border-radius:6px;font-weight:700">'+(r2.recibidas||r2.respuestas||0)+' / '+(r2.solicitadas||r2.total||0)+'</span></td>';
      html += '<td style="padding:8px 12px;text-align:right;font-weight:700;color:#15803d">'+(r2.mejor_precio ? _money(r2.mejor_precio) : '—')+'</td>';
      html += '<td style="padding:8px 12px;text-align:center"><span style="background:'+bgEst+';color:'+fgEst+';padding:3px 10px;border-radius:10px;font-size:11px;font-weight:700;text-transform:uppercase">'+_esc(r2.estado||'?')+'</span></td>';
      html += '<td style="padding:8px 12px;text-align:center"><button onclick="abrirCotizDrawer('+(r2.ronda_id||r2.id)+')" style="background:#0891b2;color:#fff;border:none;padding:5px 12px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">📊 Comparar</button></td>';
      html += '</tr>';
    });
    html += '</tbody></table>';
    html += '<div style="font-size:11px;color:#64748b;padding:10px 12px;background:#f8fafc;border-top:1px solid #e2e8f0">💡 Click <strong>📊 Comparar</strong> para ver las 3 cotizaciones lado a lado y elegir ganadora · al elegir, se genera la OC automáticamente vinculada.</div>';
    div.innerHTML = html;
    // Update badge
    var b = document.getElementById('cotiz-badge');
    if(b){ if(pend>0){ b.textContent = pend; b.style.display='inline-block'; } else b.style.display='none'; }
  } catch(e){
    div.innerHTML = '<div style="color:#dc2626;padding:20px">Error red: '+e.message+'</div>';
  }
}
async function abrirCotizDrawer(rondaId){
  var existing = document.getElementById('cotiz-drawer');
  if(existing) existing.remove();
  var modal = document.createElement('div');
  modal.id = 'cotiz-drawer';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
  modal.innerHTML = '<div style="background:#fff;border-radius:12px;max-width:1000px;width:100%;max-height:92vh;overflow:auto;box-shadow:0 12px 40px rgba(0,0,0,0.25)">'+
    '<div style="padding:18px 22px;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;justify-content:space-between">'+
      '<div><h3 style="margin:0;font-size:16px;color:#1e293b">📊 Comparar cotizaciones · Ronda #'+rondaId+'</h3><div id="cot-ronda-meta" style="font-size:12px;color:#64748b;margin-top:2px"></div></div>'+
      '<button onclick="document.getElementById(\\'cotiz-drawer\\').remove()" style="background:#e5e7eb;color:#475569;border:none;width:32px;height:32px;border-radius:50%;font-size:18px;cursor:pointer">×</button>'+
    '</div>'+
    '<div id="cot-drawer-body" style="padding:20px"><div style="text-align:center;color:#94a3b8;padding:40px">Cargando…</div></div>'+
    '</div>';
  document.body.appendChild(modal);
  try{
    var r = await fetch('/api/compras/cotizaciones/rondas/'+rondaId);
    var d = await r.json();
    if(!r.ok){ document.getElementById('cot-drawer-body').innerHTML='<div style="color:#dc2626">Error: '+(d.error||r.status)+'</div>'; return; }
    var ronda = d.ronda || {};
    var cots = d.cotizaciones || d.items || [];
    var meta = document.getElementById('cot-ronda-meta');
    if(meta) meta.textContent = (ronda.material_nombre||ronda.descripcion||'?') + ' · creada '+(ronda.creada_en||'').slice(0,10);
    if(!cots.length){
      document.getElementById('cot-drawer-body').innerHTML = '<div style="text-align:center;color:#64748b;padding:40px">Sin cotizaciones registradas aún. Cuando los proveedores respondan, usá el botón ✏️ Registrar respuesta abajo.</div>';
      return;
    }
    // Ordenar por valor_total ascendente (mejor primero)
    cots.sort(function(a,b){ return (parseFloat(a.valor_total||0)||9e15) - (parseFloat(b.valor_total||0)||9e15); });
    var html = '<div style="display:grid;grid-template-columns:repeat('+Math.min(cots.length,3)+',1fr);gap:14px">';
    cots.slice(0,3).forEach(function(c, i){
      var esGanadora = !!c.ganadora;
      var cerrada = (ronda.estado||'').toLowerCase()==='cerrada';
      var borde = esGanadora ? '#16a34a' : (i===0 ? '#0891b2' : '#cbd5e1');
      var bg = esGanadora ? '#dcfce7' : (i===0?'#ecfeff':'#fff');
      html += '<div style="background:'+bg+';border:2px solid '+borde+';border-radius:10px;padding:14px">';
      if(esGanadora){
        html += '<div style="background:#16a34a;color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:800;display:inline-block;margin-bottom:6px">🏆 GANADORA</div>';
      } else if(i===0 && !cerrada){
        html += '<div style="background:#0891b2;color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:800;display:inline-block;margin-bottom:6px">💰 MEJOR PRECIO</div>';
      }
      html += '<div style="font-weight:800;font-size:14px;color:#1e293b;margin-bottom:8px">'+_esc(c.proveedor||'?')+'</div>';
      html += '<table style="width:100%;font-size:12px;border-collapse:collapse">';
      html += '<tr><td style="color:#64748b;padding:3px 0">Precio total:</td><td style="text-align:right;font-weight:800;color:#1e293b">'+(c.valor_total?_money(c.valor_total):'—')+'</td></tr>';
      html += '<tr><td style="color:#64748b;padding:3px 0">Tiempo entrega:</td><td style="text-align:right;font-weight:700">'+(c.tiempo_entrega_dias!=null?c.tiempo_entrega_dias+' días':'—')+'</td></tr>';
      html += '<tr><td style="color:#64748b;padding:3px 0">Estado:</td><td style="text-align:right;font-weight:700;color:'+(c.valor_total?'#15803d':'#94a3b8')+'">'+(c.valor_total?'✓ Respondió':'⏳ Pendiente')+'</td></tr>';
      html += '<tr><td style="color:#64748b;padding:3px 0">Condiciones:</td><td style="text-align:right;font-size:11px">'+_esc(c.condiciones||'—')+'</td></tr>';
      if(c.numero_oc){
        html += '<tr><td style="color:#64748b;padding:3px 0">OC generada:</td><td style="text-align:right;font-weight:700;color:#0891b2">'+_esc(c.numero_oc)+'</td></tr>';
      }
      html += '</table>';
      html += '<div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">';
      if(!cerrada){
        if(!c.valor_total){
          html += '<button onclick="cotRegistrarRespuesta('+c.id+',\\''+_esc((c.proveedor||'').replace(/\\x27/g,"\\\\\\x27"))+'\\')" style="background:#0891b2;color:#fff;border:none;padding:5px 10px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">✏️ Registrar respuesta</button>';
        } else if(!esGanadora){
          html += '<button onclick="cotElegirGanadora('+c.id+','+rondaId+',\\''+_esc((c.proveedor||'').replace(/\\x27/g,"\\\\\\x27"))+'\\')" style="background:#16a34a;color:#fff;border:none;padding:5px 10px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">🏆 Elegir ganadora</button>';
        }
      }
      html += '</div>';
      html += '</div>';
    });
    html += '</div>';
    document.getElementById('cot-drawer-body').innerHTML = html;
  } catch(e){
    document.getElementById('cot-drawer-body').innerHTML = '<div style="color:#dc2626">Error red: '+e.message+'</div>';
  }
}
async function cotRegistrarRespuesta(cotId, proveedor){
  var precio = prompt('Precio total cotizado por '+proveedor+':\\n(valor numérico · solo COP)');
  if(!precio || isNaN(parseFloat(precio))) return;
  var dias = prompt('Tiempo de entrega en días (default 15):', '15');
  if(!dias || isNaN(parseInt(dias,10))) dias = '15';
  var cond = prompt('Condiciones (forma de pago, MOQ, etc.) · puede ser vacío:', '');
  try{
    var r = await fetch('/api/compras/cotizaciones/'+cotId, {
      method:'PATCH',
      headers:{'Content-Type':'application/json','X-CSRF-Token':window._csrfTok||''},
      body: JSON.stringify({valor_total:parseFloat(precio), tiempo_entrega_dias:parseInt(dias,10), condiciones:cond}),
    });
    var d = await r.json();
    if(!r.ok || d.error){ alert('Error: '+(d.error||r.status)); return; }
    var dr = document.getElementById('cotiz-drawer');
    if(dr) dr.remove();
    cargarCotizaciones();
    // Re-abrir drawer mismo · necesita rondaId
    var rondaIdMatch = (d.ronda_id || d.cotizacion?.ronda_id);
    if(rondaIdMatch) setTimeout(function(){ abrirCotizDrawer(rondaIdMatch); }, 200);
  } catch(e){ alert('Error red: '+e.message); }
}
async function cotElegirGanadora(cotId, rondaId, proveedor){
  if(!confirm('¿Elegir a '+proveedor+' como ganadora?\\n\\nEsto:\\n· marca esta cotización como ganadora\\n· cierra las otras\\n· genera OC automática\\n· cierra la ronda')) return;
  try{
    var r = await fetch('/api/compras/cotizaciones/'+cotId+'/elegir-ganadora', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRF-Token':window._csrfTok||''},
    });
    var d = await r.json();
    if(!r.ok || d.error){ alert('Error: '+(d.error||r.status)); return; }
    alert('✓ Ganadora elegida'+(d.numero_oc?'\\n\\nOC generada: '+d.numero_oc:''));
    var dr = document.getElementById('cotiz-drawer');
    if(dr) dr.remove();
    cargarCotizaciones();
  } catch(e){ alert('Error red: '+e.message); }
}

function exportOcsConsolidado(){
  // Sebastián 23-may-2026 · descarga Excel con TODAS las OCs activas
  // y datos bancarios visibles · para que Catalina envíe a Sebas/Alejandro
  // o tenga un consolidado físico de pagos pendientes
  var estados = prompt('Estados a incluir (CSV) · Enter para los default:\\n\\nBorrador,Autorizada,Parcial,Recibida,Pagada', 'Borrador,Autorizada,Parcial,Recibida,Pagada');
  if(!estados) return;
  var dias = prompt('OCs creadas en últimos N días (default 90):', '90');
  if(!dias) return;
  var url = '/api/compras/ocs-consolidado-excel?estados=' + encodeURIComponent(estados) + '&dias=' + parseInt(dias,10);
  window.open(url, '_blank');
}


async function loadPorPagar(){
  try{
    var r = await fetch('/api/compras/por-pagar');
    if(!r.ok){ document.getElementById('por-pagar-merc-list').innerHTML='<div style="color:#dc2626;padding:20px;">Error '+r.status+'</div>'; return; }
    var d = await r.json();
    var desg = d.desglose || {};
    document.getElementById('por-pagar-total').textContent = _money(d.total_valor);
    document.getElementById('por-pagar-merc').textContent = _money((desg.mercancia_recibida||{}).valor) + ' · ' + ((desg.mercancia_recibida||{}).count||0)+' OCs';
    document.getElementById('por-pagar-svc').textContent = _money((desg.pagos_directos_servicios||{}).valor) + ' · ' + ((desg.pagos_directos_servicios||{}).count||0)+' OCs';

    var directos = (d.items||[]).filter(function(x){return x.pago_directo===true;});
    var fisicas = (d.items||[]).filter(function(x){return !x.pago_directo;});

    // Sección destacada de pagos directos
    var dirWrap = document.getElementById('por-pagar-directos-wrap');
    var dirEl = document.getElementById('por-pagar-directos');
    if(directos.length){
      dirWrap.style.display = 'block';
      dirEl.innerHTML = directos.map(function(o){
        var prov = (o.proveedor||'').trim();
        var esIncompleta = (!prov || prov.toLowerCase()==='por definir' || !(o.valor_total>0));
        return '<div style="background:#fffbeb;border:2px solid '+(esIncompleta?'#dc2626':'#f59e0b')+';border-radius:10px;padding:12px;">'+
          '<div style="font-weight:700;font-family:monospace;color:#92400e;font-size:13px;">'+_esc(o.numero_oc)+'</div>'+
          '<div style="font-size:13px;color:'+(esIncompleta?'#dc2626':'#1e293b')+';margin-top:4px;">'+_esc(prov||'(sin proveedor)')+'</div>'+
          '<div style="font-size:11px;color:#78350f;margin-top:2px;">'+_esc(o.categoria||'')+'</div>'+
          // FIX 23-may · datos bancarios visibles para admin
          ((o.banco||o.num_cuenta||o.nit)?(
            '<div style="background:#fff7ed;border:1px dashed #fbbf24;border-radius:6px;padding:6px 8px;margin-top:6px;font-size:11px;font-family:monospace;color:#78350f">'+
              (o.banco? '<div>🏦 '+_esc(o.banco)+(o.tipo_cuenta?' · '+_esc(o.tipo_cuenta):'')+'</div>':'')+
              (o.num_cuenta? '<div>💳 '+_esc(o.num_cuenta)+'</div>':'')+
              (o.nit? '<div>🆔 NIT '+_esc(o.nit)+'</div>':'')+
            '</div>'
          ):'')+
          '<div style="font-size:18px;font-weight:800;color:'+(esIncompleta?'#dc2626':'#059669')+';margin-top:8px;">'+_money(o.valor_total)+'</div>'+
          (esIncompleta?'<div style="font-size:11px;color:#dc2626;margin-top:4px;">&#9888;&#65039; Datos incompletos. Pulsa &#x1F527; Reparar para jalar de la solicitud.</div>':'')+
          '<div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;">'+
          (esIncompleta?'<button class="btn" style="padding:6px 10px;font-size:12px;background:#fef3c7;color:#92400e;border:1px solid #f59e0b;border-radius:6px;cursor:pointer;font-weight:700;" onclick="repararOC(\\''+_esc(o.numero_oc)+'\\')" title="Sincronizar proveedor y valor desde la solicitud asociada">&#x1F527; Reparar</button>':'<button class="btn bs" style="flex:1;padding:6px 10px;font-size:12px;background:#059669;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:700;" onclick="payOC(\\''+_esc(o.numero_oc)+'\\')">&#x1F4B5; Pagar</button>')+
          '<button class="btn" style="padding:6px 10px;font-size:12px;background:#fff;color:#dc2626;border:1px solid #dc2626;border-radius:6px;cursor:pointer;font-weight:700;" onclick="rechazarPorPagar(\\''+_esc(o.numero_oc)+'\\')" title="Devolver a la SOL de origen">&#10005; Rechazar</button></div>'+
        '</div>';
      }).join('');
    } else {
      dirWrap.style.display = 'none';
    }

    // Mercancía física
    var mercEl = document.getElementById('por-pagar-merc-list');
    if(!fisicas.length){
      mercEl.innerHTML = '<div style="color:#94a3b8;padding:20px;text-align:center;">Sin mercanc&iacute;a recibida pendiente de pago.</div>';
    } else {
      mercEl.innerHTML = fisicas.map(function(o){
        var estCol = o.estado==='Parcial' ? '#d97706' : '#16a34a';
        var prov = (o.proveedor||'').trim();
        var esIncompleta = (!prov || prov.toLowerCase()==='por definir' || !(o.valor_total>0));
        return '<div style="background:#fff;border:1px solid '+(esIncompleta?'#dc2626':'#d1d5db')+';border-radius:10px;padding:12px;">'+
          '<div style="display:flex;justify-content:space-between;align-items:center;">'+
            '<div style="font-weight:700;font-family:monospace;font-size:13px;">'+_esc(o.numero_oc)+'</div>'+
            '<span style="background:'+estCol+';color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;">'+_esc(o.estado)+'</span>'+
          '</div>'+
          '<div style="font-size:13px;color:'+(esIncompleta?'#dc2626':'#1e293b')+';margin-top:4px;">'+_esc(prov||'(sin proveedor)')+'</div>'+
          '<div style="font-size:11px;color:#64748b;margin-top:2px;">'+_esc(o.categoria||'')+'</div>'+
          (o.items_resumen? '<div style="font-size:12px;color:#334155;margin-top:5px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:5px;padding:5px 8px;"><b>&#129534; Paga:</b> '+_esc(o.items_resumen)+'</div>':'')+
          // FIX 23-may · datos bancarios visibles para admin · evita
          // abrir ficha del proveedor antes de pagar (Sebas: "que aparezca
          // numero de cuenta proveedor")
          ((o.banco||o.num_cuenta||o.nit)?(
            '<div style="background:#f1f5f9;border:1px dashed #cbd5e1;border-radius:6px;padding:6px 8px;margin-top:6px;font-size:11px;font-family:monospace;color:#1e293b">'+
              (o.banco? '<div>🏦 '+_esc(o.banco)+(o.tipo_cuenta?' · '+_esc(o.tipo_cuenta):'')+'</div>':'')+
              (o.num_cuenta? '<div>💳 '+_esc(o.num_cuenta)+'</div>':'')+
              (o.nit? '<div>🆔 NIT '+_esc(o.nit)+'</div>':'')+
            '</div>'
          ):'')+
          '<div style="font-size:18px;font-weight:800;color:'+(esIncompleta?'#dc2626':'#1e293b')+';margin-top:8px;">'+_money(o.valor_total)+'</div>'+
          (esIncompleta?'<div style="font-size:11px;color:#dc2626;margin-top:4px;">&#9888;&#65039; Datos incompletos. Pulsa &#x1F527; Reparar para jalar de la solicitud.</div>':'')+
          '<div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;">'+
          (esIncompleta?'<button class="btn" style="padding:6px 10px;font-size:12px;background:#fef3c7;color:#92400e;border:1px solid #f59e0b;border-radius:6px;cursor:pointer;font-weight:700;" onclick="repararOC(\\''+_esc(o.numero_oc)+'\\')" title="Sincronizar proveedor y valor desde la solicitud asociada">&#x1F527; Reparar</button>':'<button class="btn bs" style="flex:1;padding:6px 10px;font-size:12px;background:#3b82f6;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:700;" onclick="payOC(\\''+_esc(o.numero_oc)+'\\')">&#x1F4B5; Pagar</button>')+
          '<button class="btn" style="padding:6px 10px;font-size:12px;background:#fff;color:#dc2626;border:1px solid #dc2626;border-radius:6px;cursor:pointer;font-weight:700;" onclick="rechazarPorPagar(\\''+_esc(o.numero_oc)+'\\')" title="Devolver a la SOL de origen">&#10005; Rechazar</button></div>'+
        '</div>';
      }).join('');
    }
  }catch(e){
    document.getElementById('por-pagar-merc-list').innerHTML = '<div style="color:#dc2626;padding:20px;">Error: '+_esc(e.message)+'</div>';
  }
}

// Rechazar OC desde Por Pagar — devuelve la SOL al estado Pendiente para que
// el solicitante pueda corregir o reenviar. Marca la OC como Rechazada con
// el motivo en observaciones. Reusa endpoint /api/compras/oc/<num>/rechazar.
async function rechazarPorPagar(numOC){
  var motivo = prompt('Motivo del rechazo (se devolverá a la SOL de origen):');
  if(motivo===null) return;          // cancelado
  motivo = (motivo||'').trim();
  if(!motivo){ alert('Indica un motivo.'); return; }
  try{
    var r = await fetch('/api/compras/oc/'+encodeURIComponent(numOC)+'/rechazar', _fetchOpts('POST', {motivo: motivo}));
    var d = await r.json().catch(function(){return {};});
    if(!r.ok){ alert('Error al rechazar: '+(d.error||r.status)); return; }
    alert('OC '+numOC+' rechazada. La solicitud de origen volvió a estado Pendiente.');
    if(typeof loadPorPagar==='function') loadPorPagar();
    if(typeof loadOCs==='function') loadOCs();
  }catch(e){ alert('Error de red: '+e.message); }
}

// Sebastian (29-abr-2026): cuando una OC sale "Por definir / $0" pero la
// solicitud sí tiene valor (caso 0119), este botón fuerza la sincronización.
async function repararOC(numOC){
  try{
    var r = await fetch('/api/compras/oc/'+encodeURIComponent(numOC)+'/reparar-desde-solicitud', _fetchOpts('POST'));
    var d = await r.json().catch(function(){return {};});
    if(!r.ok){ alert('No se pudo reparar: '+(d.error||r.status)); return; }
    if(d.reparada){
      alert('OC '+numOC+' reparada. Datos actualizados desde la solicitud.');
    } else {
      alert(d.mensaje||'Sin cambios.');
    }
    if(typeof loadPorPagar==='function') loadPorPagar();
  }catch(e){ alert('Error de red: '+e.message); }
}

// ════════════════════════════════════════════════════════════════════════
// Tab "Alertas" — 4 categorías de alertas vivas
// ════════════════════════════════════════════════════════════════════════

async function loadAlertasCompras(){
  try{
    var r = await fetch('/api/compras/alertas-vivas');
    if(!r.ok){ return; }
    var d = await r.json();

    // Severidad pill
    var sevPill = document.getElementById('alertas-sev-pill');
    var sev = d.severidad_max || 'ok';
    var sevColors = {critico:'#dc2626',alto:'#f59e0b',medio:'#3b82f6',bajo:'#71717a',ok:'#16a34a'};
    sevPill.style.background = sevColors[sev] || '#71717a';
    sevPill.style.color = '#fff';
    sevPill.textContent = sev==='ok' ? 'Sin alertas' : 'Severidad max: '+sev;

    // 1. OCs sin recibir
    var sr = d.ocs_sin_recibir || [];
    document.getElementById('alertas-sin-recibir-count').textContent = sr.length;
    document.getElementById('alertas-sin-recibir').innerHTML = sr.length === 0
      ? '<div style="color:#94a3b8;text-align:center;padding:14px;">Sin alertas</div>'
      : sr.map(function(o){
          return '<div style="border-bottom:1px solid #f1f5f9;padding:8px 0;">'+
            '<div style="display:flex;justify-content:space-between;"><strong style="font-family:monospace;font-size:11px;">'+_esc(o.numero_oc)+'</strong>'+
            '<span style="font-size:10px;color:#92400e;font-weight:700;">'+(o.dias_sin_recibir||'?')+' d</span></div>'+
            '<div style="font-size:11px;color:#64748b;">'+_esc(o.proveedor)+' · '+_money(o.valor_total)+'</div>'+
          '</div>';
        }).join('');

    // 2. Pagos por vencer
    var pv = d.pagos_por_vencer || [];
    document.getElementById('alertas-pagos-vencer-count').textContent = pv.length;
    document.getElementById('alertas-pagos-vencer').innerHTML = pv.length === 0
      ? '<div style="color:#94a3b8;text-align:center;padding:14px;">Sin alertas</div>'
      : pv.map(function(o){
          var dias = o.dias_restantes;
          var diasTxt = dias === null ? '?' : (dias < 0 ? Math.abs(dias)+' d en mora' : dias+' d restantes');
          var col = dias < 0 ? '#dc2626' : (dias <= 3 ? '#f59e0b' : '#3b82f6');
          return '<div style="border-bottom:1px solid #f1f5f9;padding:8px 0;">'+
            '<div style="display:flex;justify-content:space-between;"><strong style="font-family:monospace;font-size:11px;">'+_esc(o.numero_oc)+'</strong>'+
            '<span style="font-size:10px;color:'+col+';font-weight:700;">'+diasTxt+'</span></div>'+
            '<div style="font-size:11px;color:#64748b;">'+_esc(o.proveedor)+' · pendiente '+_money(o.pendiente)+'</div>'+
          '</div>';
        }).join('');

    // 3. Solicitudes pendientes
    var sp = d.solicitudes_pendientes || [];
    document.getElementById('alertas-solic-count').textContent = sp.length;
    document.getElementById('alertas-solic').innerHTML = sp.length === 0
      ? '<div style="color:#94a3b8;text-align:center;padding:14px;">Sin alertas</div>'
      : sp.map(function(s){
          var col = s.urgencia === 'Urgente' ? '#dc2626' : '#3b82f6';
          return '<div style="border-bottom:1px solid #f1f5f9;padding:8px 0;">'+
            '<div style="display:flex;justify-content:space-between;"><strong style="font-family:monospace;font-size:11px;">'+_esc(s.numero)+'</strong>'+
            '<span style="font-size:10px;color:'+col+';font-weight:700;">'+_esc(s.urgencia||'Normal')+'</span></div>'+
            '<div style="font-size:11px;color:#64748b;">'+_esc(s.solicitante||'')+' · '+(s.dias_pendiente||'?')+' d · '+_esc(s.area||'')+'</div>'+
          '</div>';
        }).join('');

    // 4. Borradores estancados
    var bb = d.ocs_borrador_estancadas || [];
    document.getElementById('alertas-borrador-count').textContent = bb.length;
    document.getElementById('alertas-borrador').innerHTML = bb.length === 0
      ? '<div style="color:#94a3b8;text-align:center;padding:14px;">Sin alertas</div>'
      : bb.map(function(o){
          return '<div style="border-bottom:1px solid #f1f5f9;padding:8px 0;">'+
            '<div style="display:flex;justify-content:space-between;"><strong style="font-family:monospace;font-size:11px;">'+_esc(o.numero_oc)+'</strong>'+
            '<span style="font-size:10px;color:#71717a;font-weight:700;">'+_esc(o.creado_por||'?')+'</span></div>'+
            '<div style="font-size:11px;color:#64748b;">'+_esc(o.proveedor)+' · '+_money(o.valor_total)+'</div>'+
          '</div>';
        }).join('');
  }catch(e){ console.error(e); }
}

// Stub no-op: el tab Cuentas de Cobro fue absorbido por Solicitudes en el
// refactor del Centro de Mando, pero quedaron 2 callsites sin protección
// (líneas init + post-decisión). El ReferenceError tiraba TODO el init
// async — todos los handlers quedaban sin engancharse. Stub idempotente
// = compras vuelve a la vida.
async function loadCCSolicitudes(){ /* no-op: tab absorbido en Solicitudes */ }

// ─── Init ─────────────────────────────────────────────────────────────
loadData();
// Sebastián 24-may-2026 · landing directo en Dashboard al cargar /compras.
// Antes: pestañas se veían pero el contenido del dashboard estaba vacío
// porque renderKpisGrandes/renderDashHome2/etc solo corren al hacer click.
// Ahora disparamos el click programáticamente para que el panel arranque
// poblado y el usuario aterrice en la vista consolidada de una.
(function(){
  try{
    var dashBtn = document.getElementById('tn-dash');
    if(dashBtn){
      // El handler .tn click hace removeClass('on') a todos y addClass al
      // clicked · idempotente · seguro aunque ya tenga .on en el HTML.
      dashBtn.click();
    }
  }catch(e){ console.warn('init dash click:', e); }
})();
</script>

<!-- Widget "Mi contraseña" removido 24-may-2026 · Sebastián · estaba en
     8 templates distintos · cluttereaba el bottom-left de cada vista ·
     ahora vive solo en /modulos y /hub (puntos de entrada del sistema) -->

</body>
</html>"""
