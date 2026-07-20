"""Centro de Operaciones - Vista ejecutiva CEO.
Dashboard unificado con TODO de cada area en un solo vistazo."""

HTML = r"""
<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Centro de Operaciones - HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
  * { box-sizing: border-box; }
  body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#f5f4f0; color:#1c1917; }
  .header { background:linear-gradient(135deg,#4c1d95 0%,#6d28d9 100%); padding:18px 28px; display:flex;align-items:center;justify-content:space-between; color:#fff; }
  .header h1 { margin:0; font-size:1.4em; font-weight:700; color:#fff; }
  .header a { color:#ddd6fe; font-size:0.85em; text-decoration:none; }
  .header a:hover { color:#fff; }
  .live-dot { display:inline-block; width:8px; height:8px; background:#fbbf24; border-radius:50%; margin-right:6px; animation:pulse 2s infinite; vertical-align:middle; }
  @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.4;} }
  .container { max-width:1600px; margin:0 auto; padding:18px; }
  .grid { display:grid; gap:14px; }
  .grid-6 { grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); }
  .grid-2 { grid-template-columns:1fr 1fr; }
  .card { background:var(--cx-card); border:1px solid var(--cx-hairline); border-radius:14px; padding:16px; box-shadow:var(--cx-sh-card); transition:box-shadow .2s ease,transform .2s ease; }
  .card:hover { transform:translateY(-2px); box-shadow:var(--cx-sh-card-hover); }
  .card .label { font-size:0.7em; color:#78716c; text-transform:uppercase; letter-spacing:0.06em; font-weight:700; margin-bottom:8px; }
  .card .val { font-size:1.8em; font-weight:800; color:#1c1917; line-height:1; }
  .card .sub { font-size:0.78em; color:#a8a29e; margin-top:6px; }
  .card .delta { font-size:0.7em; padding:2px 8px; border-radius:8px; font-weight:700; display:inline-block; }
  .delta-pos { background:var(--cx-success-pale); color:var(--cx-success); }
  .delta-neg { background:var(--cx-danger-pale); color:var(--cx-danger); }
  .delta-warn { background:var(--cx-warn-pale); color:var(--cx-warn-dark,#b45309); }
  .delta-neutral { background:var(--cx-info-pale); color:var(--cx-info); }
  .area-title { font-size:0.78em; font-weight:700; color:var(--cx-text-mute); text-transform:uppercase; letter-spacing:0.1em; margin:24px 0 8px; padding-bottom:6px; border-bottom:1px solid var(--cx-hairline); display:flex; align-items:center; }
  .area-title-icon { margin-right:8px; }
  .panel { background:var(--cx-card); border:1px solid var(--cx-hairline); border-radius:14px; padding:18px; box-shadow:var(--cx-sh-card); }
  .panel h3 { margin:0 0 12px; font-size:0.95em; color:#1c1917; display:flex; align-items:center; gap:8px; }
  .activity { font-size:0.82em; max-height:280px; overflow-y:auto; }
  .activity-row { padding:8px 0; border-bottom:1px solid #f5f5f4; display:flex; gap:10px; align-items:start; }
  .activity-row:last-child { border-bottom:none; }
  .activity-icon { font-size:14px; flex-shrink:0; }
  .activity-content { flex:1; min-width:0; }
  .activity-title { font-weight:600; color:#1c1917; font-size:12px; }
  .activity-detail { font-size:11px; color:#78716c; margin-top:2px; }
  .activity-time { font-size:10px; color:#a8a29e; white-space:nowrap; }
  .quick-link { display:inline-flex; align-items:center; gap:6px; padding:5px 10px; background:var(--cx-primary-soft); color:var(--cx-primary); border-radius:6px; text-decoration:none; font-size:11px; font-weight:600; margin-left:8px; }
  .quick-link:hover { background:#ddd6fe; }
  .empty { color:#a8a29e; font-style:italic; padding:20px; text-align:center; font-size:13px; }
  .refresh-btn { background:transparent; border:1px solid #d6d3d1; color:#57534e; border-radius:6px; padding:6px 12px; cursor:pointer; font-size:12px; }
  .refresh-btn:hover { border-color:var(--cx-primary); color:var(--cx-primary); }
  /* Mobile responsive */
  @media (max-width:768px) {
    .header { padding:12px 14px; flex-wrap:wrap; gap:8px; }
    .header h1 { font-size:1.05em; }
    .container { padding:10px; }
    .grid-6 { grid-template-columns:repeat(2,1fr); gap:8px; }
    .grid-2 { grid-template-columns:1fr; }
    .card { padding:12px; }
    .card .val { font-size:1.4em; }
    .card .label { font-size:0.65em; }
    .area-title { font-size:0.7em; margin:16px 0 6px; }
    .panel { padding:14px; }
  }
  @media (max-width:480px) {
    .grid-6 { grid-template-columns:1fr 1fr; }
    .header h1 { font-size:0.95em; }
  }
</style>
</head>
<body>
  <header class="cx-mod-header cx-fade-in">
    <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
    <div>
      <div class="cx-mod-header__title">
        <span class="live-dot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#dc2626;margin-right:8px;animation:pulse 1.5s infinite;"></span>
        Centro de Mando
      </div>
      <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; tus decisiones de hoy y el pulso de la empresa · refresh cada 60s · <a href="/gerencia" style="color:#6d28d9">Gerencia</a> (mes/YTD) · <a href="/financiero" style="color:#6d28d9">Financiero</a> (P&amp;L)</div>
    </div>
    <div class="cx-mod-header__nav">
      <button class="cx-btn cx-btn-ghost cx-btn-sm" onclick="cargar(true)" title="Refresh">&#x21bb; Refresh</button>
      <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">&larr; Módulos</a>
      <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
      </button>
    </div>
  </header>
  <script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>

  <div class="container">

    <!-- ÁREA: DECISIONES (lo que puedo atacar HOY) -->
    <div class="area-title"><span class="area-title-icon">🎯</span>Decisiones · atacá de una
      <span id="dec-resumen" style="margin-left:auto;font-size:12px;font-weight:600;color:#78716c"></span>
    </div>
    <div id="dec-chips" style="display:flex;gap:6px;flex-wrap:wrap;margin:0 0 12px 0"></div>
    <div id="decisiones"><div class="empty" style="padding:14px;color:#78716c">Cargando decisiones...</div></div>

    <!-- ÁREA: CAJA HOY (solo del día - el mes vive en Financiero) -->
    <div class="area-title"><span class="area-title-icon">💰</span>Caja del día <a class="quick-link" href="/financiero" style="margin-left:auto;">Ver mes en Financiero →</a></div>
    <div class="grid grid-6">
      <div class="card"><div class="label">Ingresos hoy</div><div class="val" id="caja-ing-hoy">-</div><div class="sub" style="color:#64748b">solo hoy</div></div>
      <div class="card"><div class="label">Egresos hoy</div><div class="val" style="color:#fca5a5" id="caja-egr-hoy">-</div><div class="sub" style="color:#64748b">solo hoy</div></div>
      <div class="card"><div class="label">Neto hoy</div><div class="val" id="caja-neto-hoy">-</div><div class="sub" style="color:#64748b">ing − egr del día</div></div>
    </div>

    <!-- ÁREA: PRODUCCIÓN + INVENTARIO -->
    <div class="area-title"><span class="area-title-icon">🏭</span>Producción & Inventario <a class="quick-link" href="/inventarios">Ver Planta</a></div>
    <div class="grid grid-6">
      <div class="card"><div class="label">Lotes mes</div><div class="val" id="prod-lotes">-</div><div class="sub" id="prod-kg"></div></div>
      <div class="card"><div class="label">Programados 30d</div><div class="val" id="prod-prog">-</div><div class="sub">próximas producciones</div></div>
      <div class="card"><div class="label">MPs en cero</div><div class="val" style="color:#fca5a5" id="inv-cero">-</div><div class="sub">stock crítico</div></div>
      <div class="card"><div class="label">MPs bajo mín.</div><div class="val" style="color:#fcd34d" id="inv-bajo">-</div><div class="sub">requieren reposición</div></div>
      <div class="card"><div class="label">Lotes vencen 7d</div><div class="val" style="color:#fcd34d" id="inv-venc">-</div><div class="sub">acción urgente</div></div>
      <div class="card"><div class="label">NCs abiertas</div><div class="val" style="color:#fbbf24" id="ncs">-</div><div class="sub">calidad sin cerrar</div></div>
    </div>

    <!-- ÁREA: COMERCIAL -->
    <div class="area-title"><span class="area-title-icon">🛍️</span>Comercial <a class="quick-link" href="/animus">ÁNIMUS</a><a class="quick-link" href="/clientes">Clientes B2B</a></div>
    <div class="grid grid-6">
      <div class="card"><div class="label">Ventas Shopify hoy</div><div class="val" id="sh-hoy">-</div><div class="sub" id="sh-hoy-count"></div></div>
      <div class="card"><div class="label">Ventas Shopify mes</div><div class="val" id="sh-mes">-</div><div class="sub" id="sh-mes-count"></div></div>
      <div class="card"><div class="label">Pedidos B2B activos</div><div class="val" id="ped-b2b">-</div><div class="sub">en proceso/listos</div></div>
    </div>

    <!-- ÁREA: PAGOS -->
    <div class="area-title"><span class="area-title-icon">💳</span>Pagos pendientes <a class="quick-link" href="/compras">Compras</a><a class="quick-link" href="/contabilidad">Contabilidad</a></div>
    <div class="grid grid-6">
      <div class="card"><div class="label">OCs por pagar</div><div class="val" id="oc-pend">-</div><div class="sub" id="oc-pend-val"></div></div>
      <div class="card"><div class="label">Facturas con saldo</div><div class="val" id="fac-pend">-</div><div class="sub" id="fac-pend-val"></div></div>
      <div class="card"><div class="label">Influencers a pagar</div><div class="val" id="mkt-toca">-</div><div class="sub">ciclo cumplido</div></div>
    </div>

    <!-- ÁREA: DIRECCIÓN TÉCNICA -->
    <div class="area-title"><span class="area-title-icon">🔧</span>Dirección Técnica <a class="quick-link" href="/tecnica">Ver módulo</a></div>
    <div class="grid grid-6">
      <div class="card"><div class="label">Fórmulas vigentes</div><div class="val" id="t-formulas">-</div><div class="sub">activas en producción</div></div>
      <div class="card"><div class="label">Registros INVIMA</div><div class="val" id="t-invima">-</div><div class="sub">vigentes</div></div>
      <div class="card"><div class="label">SGDs vencen 30d</div><div class="val" style="color:#fbbf24" id="t-sgd">-</div><div class="sub">SOPs por revisar</div></div>
    </div>

    <!-- ÁREA: PERSONAS / RRHH -->
    <div class="area-title"><span class="area-title-icon">👤</span>Personas <a class="quick-link" href="/rrhh">RRHH</a></div>
    <div class="grid grid-6">
      <div class="card"><div class="label">Empleados activos</div><div class="val" id="rrhh-act">-</div><div class="sub">en planilla</div></div>
      <div class="card"><div class="label">Ausencias pendientes</div><div class="val" style="color:#fbbf24" id="rrhh-aus">-</div><div class="sub">por aprobar</div></div>
    </div>

    <!-- ÁREA: EQUIPO / COMUNICACIÓN -->
    <div class="area-title"><span class="area-title-icon">💬</span>Comunicación <a class="quick-link" href="/comunicacion">Compromisos &amp; Chat</a></div>
    <div class="grid grid-6">
      <div class="card"><div class="label">Compromisos vencidos</div><div class="val" style="color:#fca5a5" id="t-venc">-</div><div class="sub">todas las áreas</div></div>
      <div class="card"><div class="label">Mensajes sin leer</div><div class="val" style="color:#fbbf24" id="msg-sin">-</div><div class="sub">en mi bandeja</div></div>
      <div class="card"><div class="label">Quejas Alta/Crítica</div><div class="val" style="color:#fca5a5" id="quejas">-</div><div class="sub">requieren acción</div></div>
      <div class="card"><div class="label">Campañas activas</div><div class="val" id="camp">-</div><div class="sub">marketing</div></div>
    </div>

    <!-- ACTIVIDAD RECIENTE -->
    <div class="grid grid-2" style="margin-top:24px">
      <div class="panel">
        <h3>⚡ Actividad última hora</h3>
        <div class="activity" id="actividad"><div class="empty">Cargando...</div></div>
      </div>
      <div class="panel">
        <h3>🎯 Acceso rápido</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px">
          <a href="/gerencia" class="card" style="text-decoration:none;text-align:center;color:#fbbf24"><div style="font-size:24px;margin-bottom:4px">🏛️</div><div style="font-size:12px;font-weight:600">Gerencia</div></a>
          <a href="/financiero" class="card" style="text-decoration:none;text-align:center;color:#15803d"><div style="font-size:24px;margin-bottom:4px">💵</div><div style="font-size:12px;font-weight:600">Financiero</div></a>
          <a href="/programacion" class="card" style="text-decoration:none;text-align:center;color:#22d3ee"><div style="font-size:24px;margin-bottom:4px">📅</div><div style="font-size:12px;font-weight:600">Programación</div></a>
          <a href="/marketing" class="card" style="text-decoration:none;text-align:center;color:#a78bfa"><div style="font-size:24px;margin-bottom:4px">📣</div><div style="font-size:12px;font-weight:600">Marketing</div></a>
          <a href="/calidad" class="card" style="text-decoration:none;text-align:center;color:#f87171"><div style="font-size:24px;margin-bottom:4px">🔬</div><div style="font-size:12px;font-weight:600">Calidad</div></a>
          <a href="/tecnica" class="card" style="text-decoration:none;text-align:center;color:#fbbf24"><div style="font-size:24px;margin-bottom:4px">🔧</div><div style="font-size:12px;font-weight:600">Técnica</div></a>
        </div>
      </div>
    </div>
  </div>

<script>
function fmtM(n) { n = parseFloat(n||0); if(n>=1e6) return '$'+(n/1e6).toFixed(1)+'M'; if(n>=1e3) return '$'+(n/1e3).toFixed(0)+'K'; return '$'+Math.round(n).toLocaleString('es-CO'); }
function fmtN(n) { return (n||0).toLocaleString('es-CO'); }
function _esc(s){return String(s||'').replace(/[<>&"]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));}

async function cargar(forzado) {
  try {
    const d = await fetch('/api/centro/operaciones').then(r=>r.json());
    if(d.error) return;

    // CAJA - solo HOY (el mes vive en /financiero)
    const c = d.caja || {};
    document.getElementById('caja-ing-hoy').textContent = fmtM(c.ingresos_hoy);
    document.getElementById('caja-egr-hoy').textContent = fmtM(c.egresos_hoy);
    const neto = c.neto_hoy || 0;
    const eN = document.getElementById('caja-neto-hoy');
    eN.textContent = (neto>=0?'+':'')+fmtM(Math.abs(neto));
    eN.style.color = neto>=0 ? '#15803d' : '#fca5a5';

    // PRODUCCION
    const p = d.produccion || {};
    document.getElementById('prod-lotes').textContent = fmtN(p.lotes_mes);
    document.getElementById('prod-kg').textContent = fmtN(Math.round((p.kg_mes||0)/1000)) + ' kg';
    document.getElementById('prod-prog').textContent = fmtN(p.programados_30d);

    // INVENTARIO
    const i = d.inventario || {};
    document.getElementById('inv-cero').textContent = fmtN(i.mps_cero);
    document.getElementById('inv-bajo').textContent = fmtN(i.mps_bajo);
    document.getElementById('inv-venc').textContent = fmtN(i.lotes_vencen_7d);

    // COMERCIAL
    const co = d.comercial || {};
    document.getElementById('sh-hoy').textContent = fmtM(co.shopify_hoy_total);
    document.getElementById('sh-hoy-count').textContent = fmtN(co.shopify_hoy_count) + ' pedidos';
    document.getElementById('sh-mes').textContent = fmtM(co.shopify_mes_total);
    document.getElementById('sh-mes-count').textContent = fmtN(co.shopify_mes_count) + ' pedidos';
    document.getElementById('ped-b2b').textContent = fmtN(co.pedidos_b2b_activos);

    // PAGOS
    const pg = d.pagos || {};
    document.getElementById('oc-pend').textContent = fmtN(pg.ocs_pendientes_count);
    document.getElementById('oc-pend-val').textContent = fmtM(pg.ocs_pendientes_valor);
    document.getElementById('fac-pend').textContent = fmtN(pg.facturas_pendientes_count);
    document.getElementById('fac-pend-val').textContent = fmtM(pg.facturas_saldo_total);

    // MARKETING
    const m = d.marketing || {};
    document.getElementById('mkt-toca').textContent = fmtN(m.influencers_toca_pagar);
    document.getElementById('camp').textContent = fmtN(m.campanas_activas);

    // EQUIPO
    const eq = d.equipo || {};
    document.getElementById('t-venc').textContent = fmtN(eq.tareas_vencidas_total);
    document.getElementById('msg-sin').textContent = fmtN(eq.mensajes_sin_leer);
    document.getElementById('quejas').textContent = fmtN(eq.quejas_alta_critica);
    document.getElementById('ncs').textContent = fmtN(eq.ncs_abiertas);

    // DIRECCIÓN TÉCNICA
    const tc = d.tecnica || {};
    document.getElementById('t-formulas').textContent = fmtN(tc.formulas_vigentes);
    document.getElementById('t-invima').textContent = fmtN(tc.invima_vigentes);
    document.getElementById('t-sgd').textContent = fmtN(tc.sgd_vencen_30d);

    // RRHH
    const rh = d.rrhh || {};
    document.getElementById('rrhh-act').textContent = fmtN(rh.empleados_activos);
    document.getElementById('rrhh-aus').textContent = fmtN(rh.ausencias_pendientes);

    // ACTIVIDAD
    const act = d.actividad_reciente || [];
    const aDiv = document.getElementById('actividad');
    if(!act.length) {
      aDiv.innerHTML = '<div class="empty">Sin actividad en la última hora</div>';
    } else {
      const icons = {movimiento:'📦', oc:'🛒', tarea:'📋'};
      aDiv.innerHTML = act.map(a => {
        const ic = icons[a.tipo] || '•';
        const t = (a.fecha||'').substring(11,16);
        return '<div class="activity-row">' +
          '<div class="activity-icon">'+ic+'</div>' +
          '<div class="activity-content">' +
            '<div class="activity-title">'+_esc(a.titulo||'-')+'</div>' +
            '<div class="activity-detail">'+_esc(a.detalle||'')+'</div>' +
          '</div>' +
          '<div class="activity-time">'+t+'</div>' +
        '</div>';
      }).join('');
    }
  } catch(e) { console.error('Centro error:', e); }
}

// ── DECISIONES: cola priorizada de lo que puedo atacar hoy ──
var _DEC = [];
var _DEC_FILTRO = 'todas';
var _GRP_META = {compras:['🛒','Compras'], discrepancia:['📊','Discrepancias'], inventario:['📦','Inventario'], calidad:['🧪','Calidad'], equipo:['👥','Equipo']};
function _decColor(n){ return n==='critico' ? '#dc2626' : (n==='atencion' ? '#d97706' : '#0891b2'); }
function pintarDecisiones(){
  var cont = document.getElementById('decisiones');
  var lista = _DEC_FILTRO==='todas' ? _DEC : _DEC.filter(function(d){return d.nivel===_DEC_FILTRO;});
  if(!lista.length){
    cont.innerHTML = '<div class="empty" style="padding:16px;color:#16a34a;font-weight:600">✓ Nada urgente que atacar ahora mismo.</div>';
    return;
  }
  cont.innerHTML = lista.map(function(d){
    var col = _decColor(d.nivel);
    var gm = _GRP_META[d.grupo] || ['•', d.grupo||''];
    return '<a href="'+_esc(d.accion||'#')+'" style="display:flex;align-items:center;gap:12px;text-decoration:none;'+
      'background:var(--cx-surface,#fff);border:1px solid var(--cx-border,#e7e5e4);border-left:4px solid '+col+';'+
      'border-radius:10px;padding:12px 16px;margin-bottom:8px;transition:box-shadow .15s" '+
      'onmouseover="this.style.boxShadow=\'0 4px 14px rgba(0,0,0,.08)\'" onmouseout="this.style.boxShadow=\'none\'">'+
      '<span style="font-size:20px;line-height:1">'+gm[0]+'</span>'+
      '<div style="flex:1;min-width:0">'+
        '<div style="font-weight:700;color:var(--cx-text,#1c1917);font-size:14px">'+_esc(d.titulo||'-')+'</div>'+
        '<div style="color:#78716c;font-size:12.5px;margin-top:2px;overflow:hidden;text-overflow:ellipsis">'+_esc(d.detalle||'')+'</div>'+
      '</div>'+
      '<span style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:'+col+';background:'+col+'18;padding:3px 8px;border-radius:20px;white-space:nowrap">'+_esc(gm[1])+'</span>'+
      '<span style="color:'+col+';font-size:18px">→</span>'+
    '</a>';
  }).join('');
}
var _DEC_RES = {};
function setFiltroDec(f){ _DEC_FILTRO = f; pintarChips(); pintarDecisiones(); }
function pintarChips(){
  var res = _DEC_RES || {};
  var c = document.getElementById('dec-chips');
  var defs = [['todas','Todas',(res.total||0)], ['critico','Críticas',(res.critico||0)], ['atencion','Atención',(res.atencion||0)]];
  c.innerHTML = defs.map(function(x){
    var act = _DEC_FILTRO===x[0];
    var col = x[0]==='critico' ? '#dc2626' : (x[0]==='atencion' ? '#d97706' : '#6d28d9');
    return '<button onclick="setFiltroDec(\''+x[0]+'\')" '+
      'style="border:1px solid '+(act?col:'#d6d3d1')+';background:'+(act?col:'transparent')+';color:'+(act?'#fff':'#57534e')+';'+
      'border-radius:20px;padding:5px 14px;font-size:12px;font-weight:600;cursor:pointer">'+x[1]+' ('+x[2]+')</button>';
  }).join('');
}
async function cargarDecisiones(){
  try{
    var d = await fetch('/api/centro/decisiones').then(function(r){return r.json();});
    if(d.error){ document.getElementById('decisiones').innerHTML='<div class="empty" style="padding:14px;color:#78716c">'+_esc(d.error)+'</div>'; return; }
    _DEC = d.decisiones||[];
    _DEC_RES = d.resumen||{};
    var rz = document.getElementById('dec-resumen');
    rz.textContent = (_DEC_RES.critico||0)+' críticas · '+(_DEC_RES.atencion||0)+' de atención';
    rz.style.color = (_DEC_RES.critico>0) ? '#dc2626' : '#78716c';
    pintarChips();
    pintarDecisiones();
  }catch(e){ console.error('Decisiones error:', e); }
}

cargar();
cargarDecisiones();
setInterval(function(){ cargar(); cargarDecisiones(); }, 60*1000);
</script>
</body>
</html>
"""
