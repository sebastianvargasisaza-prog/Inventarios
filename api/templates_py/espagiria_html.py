"""HTML del modulo Espagiria - panel de control para Luz Adriana."""

HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Espagiria — Panel Asistente Gerencia</title>
<link rel="stylesheet" href="/static/cortex.css?v=cortex3">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
  * { box-sizing: border-box; }
  body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#0f172a; color:#e2e8f0; }
  .header { background:linear-gradient(135deg,#0c4a6e,#0e7490); padding:18px 28px; display:flex;align-items:center;justify-content:space-between; }
  .header h1 { margin:0; font-size:1.4em; font-weight:700; }
  .header a { color:#a5f3fc; font-size:0.85em; text-decoration:none; }
  .container { max-width:1400px; margin:0 auto; padding:24px; }
  .grid { display:grid; gap:16px; }
  .grid-4 { grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); }
  .card { background:#1e293b; border:1px solid #334155; border-radius:10px; padding:18px; }
  .card h3 { margin:0 0 8px; font-size:0.78em; color:#94a3b8; text-transform:uppercase; letter-spacing:0.06em; font-weight:600; }
  .card .val { font-size:1.9em; font-weight:700; color:#fff; }
  .card .sub { font-size:0.8em; color:#64748b; margin-top:4px; }
  .section-title { font-size:1.05em; font-weight:700; color:#fff; margin:28px 0 12px; padding-bottom:6px; border-bottom:2px solid #334155; }
  .alert { background:#3f0f0f; border-left:4px solid #dc2626; padding:10px 14px; margin-bottom:8px; border-radius:6px; font-size:13px; }
  .alert.media { background:#1e1b3b; border-left-color:#f59e0b; }
  .alert .title { font-weight:600; color:#fca5a5; margin-bottom:3px; }
  .alert.media .title { color:#fbbf24; }
  .alert .accion { font-size:11px; color:#94a3b8; margin-top:4px; font-style:italic; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { background:#0f172a; color:#94a3b8; font-weight:600; text-align:left; padding:8px 10px; font-size:11px; text-transform:uppercase; }
  td { padding:8px 10px; border-bottom:1px solid #334155; }
  .badge { padding:2px 8px; border-radius:10px; font-size:10px; font-weight:700; }
  .badge.alta { background:#7f1d1d; color:#fca5a5; }
  .badge.media { background:#78350f; color:#fcd34d; }
  .badge.baja { background:#064e3b; color:#34d399; }
  .badge.estado-asig { background:#1e293b; color:#94a3b8; }
  .badge.estado-prog { background:#1e3a8a; color:#93c5fd; }
  .badge.estado-bloq { background:#7f1d1d; color:#fca5a5; }
  .badge.estado-hecha { background:#064e3b; color:#34d399; }
  .empty { color:#64748b; font-style:italic; padding:20px; text-align:center; }
  .grid-2 { grid-template-columns:1fr 1fr; }

  /* ─── MOBILE RESPONSIVE ─── */
  @media (max-width:900px) { .grid-2 { grid-template-columns:1fr; } }
  @media (max-width:768px) {
    .header { padding:14px 16px; flex-wrap:wrap; gap:8px; }
    .header h1 { font-size:1.15em; }
    .container { padding:14px; }
    .grid-4 { grid-template-columns:repeat(2,1fr); gap:10px; }
    .card { padding:12px; }
    .card .val { font-size:1.4em; }
    .card h3 { font-size:0.7em; }
    .section-title { font-size:0.95em; margin:18px 0 10px; }
    /* Tablas → cards apilados */
    table thead { display:none; }
    table, table tbody, table tr, table td { display:block; width:100%; }
    table tr { background:#0f172a; border-radius:8px; padding:10px; margin-bottom:8px; border:1px solid #334155; }
    table td { border-bottom:none; padding:4px 0; font-size:12px; }
    table td:first-child { font-weight:700; color:#fff; font-size:13px; padding-bottom:6px; }
    .alert { padding:10px 12px; font-size:12px; }
    .alert .title { font-size:13px; }
  }
  @media (max-width:480px) {
    .grid-4 { grid-template-columns:1fr; }
    .container { padding:10px; }
  }
</style>
</head>
<body>
  <div class="header">
    <div>
      <h1>🌿 Espagiria — Panel de Asistente</h1>
      <div style="font-size:11px;color:#a5f3fc;margin-top:3px;">Vista consolidada para coordinación operativa de planta</div>
    </div>
    <a href="/modulos">← Volver a módulos</a>
  </div>

  <div class="container">
    <!-- KPIs principales -->
    <div class="grid grid-4">
      <div class="card"><h3>📦 Producciones del mes</h3><div class="val" id="kpi-prod">—</div><div class="sub" id="kpi-prod-sub"></div></div>
      <div class="card"><h3>⚠️ MPs bajo mínimo</h3><div class="val" id="kpi-mps" style="color:#fca5a5;">—</div><div class="sub">Necesitan reposición</div></div>
      <div class="card"><h3>📅 Lotes vencen 30 días</h3><div class="val" id="kpi-venc" style="color:#fcd34d;">—</div><div class="sub" id="kpi-venc-sub"></div></div>
      <div class="card"><h3>🛒 OCs activas</h3><div class="val" id="kpi-ocs">—</div><div class="sub" id="kpi-ocs-sub"></div></div>
    </div>

    <div class="grid grid-4" style="margin-top:14px;">
      <div class="card"><h3>📋 Solicitudes pendientes</h3><div class="val" id="kpi-sol">—</div><div class="sub">Esperan aprobación</div></div>
      <div class="card"><h3>🔬 NCs abiertas</h3><div class="val" id="kpi-ncs" style="color:#fbbf24;">—</div><div class="sub">Calidad sin cerrar</div></div>
      <div class="card"><h3>🟡 Lotes en cuarentena</h3><div class="val" id="kpi-cuar">—</div><div class="sub">Por liberar</div></div>
      <div class="card"><h3>🚚 Pedidos activos</h3><div class="val" id="kpi-ped">—</div><div class="sub">En proceso o despacho</div></div>
    </div>

    <!-- Alertas -->
    <div class="section-title">🔔 Alertas que requieren atención</div>
    <div id="alertas-list"><div class="empty">Cargando...</div></div>

    <!-- Mis tareas + Comité -->
    <div class="grid grid-2" style="margin-top:24px;">
      <div>
        <div class="section-title">📋 Mis tareas pendientes</div>
        <div id="tareas-list"><div class="empty">Cargando...</div></div>
      </div>
      <div>
        <div class="section-title">📑 Compromisos último comité</div>
        <div id="comite-info" style="font-size:12px;color:#64748b;margin-bottom:8px;"></div>
        <div id="comite-list"><div class="empty">Cargando...</div></div>
      </div>
    </div>

    <!-- Resumen pre-comité -->
    <div class="section-title">🔄 Pre-comité (preparación viernes)</div>
    <div class="grid grid-2">
      <div class="card">
        <h3>♻️ Reincidentes (>14 días)</h3>
        <div id="reincidentes-list"><div class="empty">Cargando...</div></div>
      </div>
      <div class="card">
        <h3>✅ Completadas esta semana</h3>
        <div id="completadas-list"><div class="empty">Cargando...</div></div>
      </div>
    </div>
  </div>

<script>
function fmtNum(n) { return (n||0).toLocaleString('es-CO'); }
function _esc(s) { return String(s||'').replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c])); }

async function cargar() {
  // Dashboard KPIs
  try {
    const d = await fetch('/api/espagiria/dashboard').then(r=>r.json());
    document.getElementById('kpi-prod').textContent = d.producciones_mes.lotes;
    document.getElementById('kpi-prod-sub').textContent = fmtNum(Math.round(d.producciones_mes.total_g/1000)) + ' kg producidos';
    document.getElementById('kpi-mps').textContent = (d.mps_bajo_minimo||[]).length;
    document.getElementById('kpi-venc').textContent = d.vencen_30d;
    document.getElementById('kpi-venc-sub').textContent = (d.vencen_60d - d.vencen_30d) + ' adicionales en 60d';
    document.getElementById('kpi-ocs').textContent = (d.ocs_activas.aprobadas||0) + (d.ocs_activas.en_proceso||0);
    document.getElementById('kpi-ocs-sub').textContent = d.ocs_activas.pagadas_mes + ' pagadas mes';
    document.getElementById('kpi-sol').textContent = d.solicitudes_pendientes;
    document.getElementById('kpi-ncs').textContent = d.calidad_ncs;
    document.getElementById('kpi-cuar').textContent = d.lotes_cuarentena;
    document.getElementById('kpi-ped').textContent = d.pedidos_activos;

    // Mis tareas
    const tList = document.getElementById('tareas-list');
    if (!d.mis_tareas_pendientes || d.mis_tareas_pendientes.length === 0) {
      tList.innerHTML = '<div class="empty">Sin tareas pendientes asignadas 🎉</div>';
    } else {
      tList.innerHTML = '<table><thead><tr><th>Tarea</th><th>Comprom.</th><th>Prio</th><th>Estado</th></tr></thead><tbody>' +
        d.mis_tareas_pendientes.map(t =>
          '<tr><td>' + _esc(t.titulo) + '<div style="font-size:10px;color:#64748b;">'+(t.area||'')+'</div></td>' +
          '<td style="color:#fbbf24;font-size:11px;">'+(t.fecha_compromiso||'sin fecha')+'</td>' +
          '<td><span class="badge '+(t.prioridad||'baja').toLowerCase()+'">'+(t.prioridad||'-')+'</span></td>' +
          '<td><span class="badge estado-'+(t.estado||'').toLowerCase().substring(0,4)+'">'+_esc(t.estado||'-')+'</span></td></tr>'
        ).join('') + '</tbody></table>';
    }

    // Comite
    const cInfo = document.getElementById('comite-info');
    const cList = document.getElementById('comite-list');
    if (d.ultimo_comite_fecha) {
      cInfo.textContent = 'Último comité: ' + d.ultimo_comite_fecha + ' · ' + (d.compromisos_ultimo_comite||[]).length + ' compromisos';
      if (d.compromisos_ultimo_comite.length === 0) {
        cList.innerHTML = '<div class="empty">Sin compromisos registrados de ese comité</div>';
      } else {
        cList.innerHTML = '<table><thead><tr><th>Compromiso</th><th>Resp.</th><th>Estado</th></tr></thead><tbody>' +
          d.compromisos_ultimo_comite.map(t =>
            '<tr><td>' + _esc(t.titulo) + '</td>' +
            '<td style="font-size:11px;color:#a5f3fc;">'+_esc(t.responsables||'-')+'</td>' +
            '<td><span class="badge estado-'+(t.estado||'').toLowerCase().substring(0,4)+'">'+_esc(t.estado||'-')+'</span></td></tr>'
          ).join('') + '</tbody></table>';
      }
    } else {
      cInfo.textContent = 'No hay actas de comité registradas todavía';
      cList.innerHTML = '<div class="empty">El módulo Comunicación parseará las actas automáticamente</div>';
    }
  } catch(e) {
    console.error('Dashboard error:', e);
  }

  // Alertas
  try {
    const a = await fetch('/api/espagiria/alertas').then(r=>r.json());
    const aList = document.getElementById('alertas-list');
    if (!a.alertas || a.alertas.length === 0) {
      aList.innerHTML = '<div class="empty">Sin alertas críticas hoy ✅</div>';
    } else {
      aList.innerHTML = a.alertas.map(al =>
        '<div class="alert '+(al.severidad||'media')+'">' +
        '<div class="title">'+_esc(al.titulo)+'</div>' +
        '<div style="font-size:12px;color:#cbd5e1;">'+_esc(al.detalle||'')+'</div>' +
        (al.accion_sugerida ? '<div class="accion">→ '+_esc(al.accion_sugerida)+'</div>' : '') +
        '</div>'
      ).join('');
    }
  } catch(e) { console.error('Alertas error:', e); }

  // Pre-comité
  try {
    const p = await fetch('/api/espagiria/resumen-pre-comite').then(r=>r.json());
    const rList = document.getElementById('reincidentes-list');
    if (!p.reincidentes || p.reincidentes.length === 0) {
      rList.innerHTML = '<div class="empty">Sin reincidentes 🎉</div>';
    } else {
      rList.innerHTML = '<table><thead><tr><th>Tarea</th><th>Resp.</th><th>Días</th></tr></thead><tbody>' +
        p.reincidentes.map(t =>
          '<tr><td style="font-size:12px;">'+_esc(t.titulo)+'</td>' +
          '<td style="font-size:11px;color:#a5f3fc;">'+_esc(t.responsables||'-')+'</td>' +
          '<td style="color:#fca5a5;font-weight:700;">'+Math.round(t.dias_abierta)+'</td></tr>'
        ).join('') + '</tbody></table>';
    }

    const cList = document.getElementById('completadas-list');
    if (!p.completadas_semana || p.completadas_semana.length === 0) {
      cList.innerHTML = '<div class="empty">Sin tareas completadas aún esta semana</div>';
    } else {
      cList.innerHTML = '<table><thead><tr><th>Tarea</th><th>Área</th><th>Fecha</th></tr></thead><tbody>' +
        p.completadas_semana.slice(0,15).map(t =>
          '<tr><td style="font-size:12px;">'+_esc(t.titulo)+'</td>' +
          '<td style="font-size:11px;color:#94a3b8;">'+_esc(t.area||'-')+'</td>' +
          '<td style="font-size:11px;color:#34d399;">'+_esc((t.fecha_completada||'').substring(0,10))+'</td></tr>'
        ).join('') + '</tbody></table>';
    }
  } catch(e) { console.error('Pre-comite error:', e); }
}

cargar();
setInterval(cargar, 5*60*1000); // refresh cada 5 min
</script>
</body>
</html>
"""
