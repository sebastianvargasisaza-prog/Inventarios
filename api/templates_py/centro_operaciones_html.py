"""Centro de Operaciones - Vista ejecutiva CEO.
Dashboard unificado con TODO de cada area en un solo vistazo."""

HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Centro de Operaciones — HHA Group</title>
<style>
  * { box-sizing: border-box; }
  body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#f5f4f0; color:#1c1917; }
  .header { background:linear-gradient(135deg,#0f3a1f 0%,#15803d 100%); padding:18px 28px; display:flex;align-items:center;justify-content:space-between; color:#fff; }
  .header h1 { margin:0; font-size:1.4em; font-weight:700; color:#fff; }
  .header a { color:#bbf7d0; font-size:0.85em; text-decoration:none; }
  .header a:hover { color:#fff; }
  .live-dot { display:inline-block; width:8px; height:8px; background:#fbbf24; border-radius:50%; margin-right:6px; animation:pulse 2s infinite; vertical-align:middle; }
  @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.4;} }
  .container { max-width:1600px; margin:0 auto; padding:18px; }
  .grid { display:grid; gap:14px; }
  .grid-6 { grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); }
  .grid-2 { grid-template-columns:1fr 1fr; }
  .card { background:#fff; border:1px solid #e7e5e4; border-radius:12px; padding:16px; transition:.15s; }
  .card:hover { border-color:#a8a29e; transform:translateY(-1px); box-shadow:0 4px 12px rgba(0,0,0,0.05); }
  .card .label { font-size:0.7em; color:#78716c; text-transform:uppercase; letter-spacing:0.06em; font-weight:700; margin-bottom:8px; }
  .card .val { font-size:1.8em; font-weight:800; color:#1c1917; line-height:1; }
  .card .sub { font-size:0.78em; color:#a8a29e; margin-top:6px; }
  .card .delta { font-size:0.7em; padding:2px 8px; border-radius:8px; font-weight:700; display:inline-block; }
  .delta-pos { background:#064e3b; color:#34d399; }
  .delta-neg { background:#7f1d1d; color:#fca5a5; }
  .delta-warn { background:#78350f; color:#fcd34d; }
  .delta-neutral { background:#1e3a5f; color:#93c5fd; }
  .area-title { font-size:0.78em; font-weight:700; color:#15803d; text-transform:uppercase; letter-spacing:0.1em; margin:24px 0 8px; padding-bottom:6px; border-bottom:1px solid #e7e5e4; display:flex; align-items:center; }
  .area-title-icon { margin-right:8px; }
  .panel { background:#fff; border:1px solid #e7e5e4; border-radius:12px; padding:18px; }
  .panel h3 { margin:0 0 12px; font-size:0.95em; color:#1c1917; display:flex; align-items:center; gap:8px; }
  .activity { font-size:0.82em; max-height:280px; overflow-y:auto; }
  .activity-row { padding:8px 0; border-bottom:1px solid #f5f5f4; display:flex; gap:10px; align-items:start; }
  .activity-row:last-child { border-bottom:none; }
  .activity-icon { font-size:14px; flex-shrink:0; }
  .activity-content { flex:1; min-width:0; }
  .activity-title { font-weight:600; color:#1c1917; font-size:12px; }
  .activity-detail { font-size:11px; color:#78716c; margin-top:2px; }
  .activity-time { font-size:10px; color:#a8a29e; white-space:nowrap; }
  .quick-link { display:inline-flex; align-items:center; gap:6px; padding:5px 10px; background:#dcfce7; color:#15803d; border-radius:6px; text-decoration:none; font-size:11px; font-weight:600; margin-left:8px; }
  .quick-link:hover { background:#bbf7d0; }
  .empty { color:#a8a29e; font-style:italic; padding:20px; text-align:center; font-size:13px; }
  .refresh-btn { background:transparent; border:1px solid #d6d3d1; color:#57534e; border-radius:6px; padding:6px 12px; cursor:pointer; font-size:12px; }
  .refresh-btn:hover { border-color:#15803d; color:#15803d; }
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
  <div class="header">
    <div>
      <h1><span class="live-dot"></span>HOY · qué pasa ahora</h1>
      <div style="font-size:11px;color:#64748b;margin-top:3px;">Tiempo real operativo · refresh cada 60 seg · para mes/YTD ver <a href="/gerencia" style="color:#22d3ee">Gerencia</a> · para P&L y caja ver <a href="/financiero" style="color:#34d399">Financiero</a></div>
    </div>
    <div style="display:flex;align-items:center;gap:14px">
      <button class="refresh-btn" onclick="cargar(true)" title="Refresh ahora">↻</button>
      <a href="/modulos">← Módulos</a>
    </div>
  </div>

  <div class="container">

    <!-- ÁREA: CAJA HOY (solo del día — el mes vive en Financiero) -->
    <div class="area-title"><span class="area-title-icon">💰</span>Caja del día <a class="quick-link" href="/financiero" style="margin-left:auto;">Ver mes en Financiero →</a></div>
    <div class="grid grid-6">
      <div class="card"><div class="label">Ingresos hoy</div><div class="val" id="caja-ing-hoy">—</div><div class="sub" style="color:#64748b">solo hoy</div></div>
      <div class="card"><div class="label">Egresos hoy</div><div class="val" style="color:#fca5a5" id="caja-egr-hoy">—</div><div class="sub" style="color:#64748b">solo hoy</div></div>
      <div class="card"><div class="label">Neto hoy</div><div class="val" id="caja-neto-hoy">—</div><div class="sub" style="color:#64748b">ing − egr del día</div></div>
    </div>

    <!-- ÁREA: PRODUCCIÓN + INVENTARIO -->
    <div class="area-title"><span class="area-title-icon">🏭</span>Producción & Inventario <a class="quick-link" href="/inventarios">Ver Planta</a></div>
    <div class="grid grid-6">
      <div class="card"><div class="label">Lotes mes</div><div class="val" id="prod-lotes">—</div><div class="sub" id="prod-kg"></div></div>
      <div class="card"><div class="label">Programados 30d</div><div class="val" id="prod-prog">—</div><div class="sub">próximas producciones</div></div>
      <div class="card"><div class="label">MPs en cero</div><div class="val" style="color:#fca5a5" id="inv-cero">—</div><div class="sub">stock crítico</div></div>
      <div class="card"><div class="label">MPs bajo mín.</div><div class="val" style="color:#fcd34d" id="inv-bajo">—</div><div class="sub">requieren reposición</div></div>
      <div class="card"><div class="label">Lotes vencen 7d</div><div class="val" style="color:#fcd34d" id="inv-venc">—</div><div class="sub">acción urgente</div></div>
      <div class="card"><div class="label">NCs abiertas</div><div class="val" style="color:#fbbf24" id="ncs">—</div><div class="sub">calidad sin cerrar</div></div>
    </div>

    <!-- ÁREA: COMERCIAL -->
    <div class="area-title"><span class="area-title-icon">🛍️</span>Comercial <a class="quick-link" href="/animus">ÁNIMUS</a><a class="quick-link" href="/clientes">Clientes B2B</a></div>
    <div class="grid grid-6">
      <div class="card"><div class="label">Ventas Shopify hoy</div><div class="val" id="sh-hoy">—</div><div class="sub" id="sh-hoy-count"></div></div>
      <div class="card"><div class="label">Ventas Shopify mes</div><div class="val" id="sh-mes">—</div><div class="sub" id="sh-mes-count"></div></div>
      <div class="card"><div class="label">Pedidos B2B activos</div><div class="val" id="ped-b2b">—</div><div class="sub">en proceso/listos</div></div>
    </div>

    <!-- ÁREA: PAGOS -->
    <div class="area-title"><span class="area-title-icon">💳</span>Pagos pendientes <a class="quick-link" href="/compras">Compras</a><a class="quick-link" href="/contabilidad">Contabilidad</a></div>
    <div class="grid grid-6">
      <div class="card"><div class="label">OCs por pagar</div><div class="val" id="oc-pend">—</div><div class="sub" id="oc-pend-val"></div></div>
      <div class="card"><div class="label">Facturas con saldo</div><div class="val" id="fac-pend">—</div><div class="sub" id="fac-pend-val"></div></div>
      <div class="card"><div class="label">Influencers a pagar</div><div class="val" id="mkt-toca">—</div><div class="sub">ciclo cumplido</div></div>
    </div>

    <!-- ÁREA: DIRECCIÓN TÉCNICA -->
    <div class="area-title"><span class="area-title-icon">🔧</span>Dirección Técnica <a class="quick-link" href="/tecnica">Ver módulo</a></div>
    <div class="grid grid-6">
      <div class="card"><div class="label">Fórmulas vigentes</div><div class="val" id="t-formulas">—</div><div class="sub">activas en producción</div></div>
      <div class="card"><div class="label">Registros INVIMA</div><div class="val" id="t-invima">—</div><div class="sub">vigentes</div></div>
      <div class="card"><div class="label">SGDs vencen 30d</div><div class="val" style="color:#fbbf24" id="t-sgd">—</div><div class="sub">SOPs por revisar</div></div>
    </div>

    <!-- ÁREA: PERSONAS / RRHH -->
    <div class="area-title"><span class="area-title-icon">👤</span>Personas <a class="quick-link" href="/rrhh">RRHH</a></div>
    <div class="grid grid-6">
      <div class="card"><div class="label">Empleados activos</div><div class="val" id="rrhh-act">—</div><div class="sub">en planilla</div></div>
      <div class="card"><div class="label">Ausencias pendientes</div><div class="val" style="color:#fbbf24" id="rrhh-aus">—</div><div class="sub">por aprobar</div></div>
    </div>

    <!-- ÁREA: EQUIPO / COMUNICACIÓN -->
    <div class="area-title"><span class="area-title-icon">💬</span>Comunicación <a class="quick-link" href="/comunicacion">Compromisos &amp; Chat</a></div>
    <div class="grid grid-6">
      <div class="card"><div class="label">Compromisos vencidos</div><div class="val" style="color:#fca5a5" id="t-venc">—</div><div class="sub">todas las áreas</div></div>
      <div class="card"><div class="label">Mensajes sin leer</div><div class="val" style="color:#fbbf24" id="msg-sin">—</div><div class="sub">en mi bandeja</div></div>
      <div class="card"><div class="label">Quejas Alta/Crítica</div><div class="val" style="color:#fca5a5" id="quejas">—</div><div class="sub">requieren acción</div></div>
      <div class="card"><div class="label">Campañas activas</div><div class="val" id="camp">—</div><div class="sub">marketing</div></div>
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
          <a href="/financiero" class="card" style="text-decoration:none;text-align:center;color:#34d399"><div style="font-size:24px;margin-bottom:4px">💵</div><div style="font-size:12px;font-weight:600">Financiero</div></a>
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

    // CAJA — solo HOY (el mes vive en /financiero)
    const c = d.caja || {};
    document.getElementById('caja-ing-hoy').textContent = fmtM(c.ingresos_hoy);
    document.getElementById('caja-egr-hoy').textContent = fmtM(c.egresos_hoy);
    const neto = c.neto_hoy || 0;
    const eN = document.getElementById('caja-neto-hoy');
    eN.textContent = (neto>=0?'+':'')+fmtM(Math.abs(neto));
    eN.style.color = neto>=0 ? '#34d399' : '#fca5a5';

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

cargar();
setInterval(cargar, 60*1000);
</script>
</body>
</html>
"""
