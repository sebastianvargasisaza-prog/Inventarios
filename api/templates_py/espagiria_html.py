"""HTML del modulo Espagiria - panel de control para Luz Adriana."""

HTML = r"""
<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Espagiria - Panel Asistente Gerencia</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<!-- MODAL · solicitar pago desde caja (Espagiria) -->
<div id="modal-ep" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;">
  <div style="background:var(--cx-card);border:1px solid var(--cx-text-soft);border-radius:14px;padding:22px;width:520px;max-width:92vw;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <h3 style="font-size:16px;color:var(--cx-text);margin:0;">&#128184; Solicitar pago con caja menor</h3>
      <button onclick="document.getElementById('modal-ep').style.display='none'"
              style="background:none;border:none;color:var(--cx-text-mute);font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div style="margin-bottom:10px;">
      <label style="display:block;font-size:11px;color:var(--cx-text-mute);font-weight:600;text-transform:uppercase;margin-bottom:4px;">Concepto</label>
      <input id="ep-concepto" style="width:100%;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);padding:8px 12px;border-radius:8px;font-size:13px;" placeholder="Qu&eacute; se va a pagar">
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">
      <div>
        <label style="display:block;font-size:11px;color:var(--cx-text-mute);font-weight:600;text-transform:uppercase;margin-bottom:4px;">Monto</label>
        <input id="ep-monto" type="number" oninput="epAvisarTope()" style="width:100%;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);padding:8px 12px;border-radius:8px;font-size:13px;" placeholder="0">
      </div>
      <div>
        <label style="display:block;font-size:11px;color:var(--cx-text-mute);font-weight:600;text-transform:uppercase;margin-bottom:4px;">Empresa</label>
        <select id="ep-empresa" style="width:100%;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);padding:8px 12px;border-radius:8px;font-size:13px;">
          <option value="ESPAGIRIA">Espagiria</option>
          <option value="ANIMUS">ANIMUS</option>
        </select>
      </div>
    </div>
    <div style="margin-bottom:10px;">
      <label style="display:block;font-size:11px;color:var(--cx-text-mute);font-weight:600;text-transform:uppercase;margin-bottom:4px;">A qui&eacute;n se le paga</label>
      <input id="ep-benef" style="width:100%;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);padding:8px 12px;border-radius:8px;font-size:13px;" placeholder="Proveedor o persona">
    </div>
    <div style="margin-bottom:10px;">
      <label style="display:block;font-size:11px;color:var(--cx-text-mute);font-weight:600;text-transform:uppercase;margin-bottom:4px;">Cotizacion o pantallazo del precio</label>
      <input id="ep-cotiz" style="width:100%;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);padding:8px 12px;border-radius:8px;font-size:13px;" placeholder="Enlace de la cotizacion (opcional pero recomendado)">
      <div style="font-size:11px;color:var(--cx-text-mute);margin-top:4px;">Justifica el monto ANTES de autorizar</div>
    </div>
    <div style="margin-bottom:10px;">
      <label style="display:block;font-size:11px;color:var(--cx-text-mute);font-weight:600;text-transform:uppercase;margin-bottom:4px;">Observaciones</label>
      <textarea id="ep-obs" style="width:100%;min-height:60px;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);padding:8px 12px;border-radius:8px;font-size:13px;" placeholder="Opcional"></textarea>
    </div>
    <div id="ep-tope-aviso" style="font-size:12px;margin-bottom:12px;"></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button onclick="document.getElementById('modal-ep').style.display='none'"
              style="background:transparent;border:1px solid var(--cx-text-soft);color:var(--cx-text-soft);border-radius:8px;padding:8px 16px;cursor:pointer;">Cancelar</button>
      <button onclick="epGuardar()"
              style="background:var(--cx-primary-grad);color:var(--cx-text);border:none;border-radius:8px;padding:8px 18px;font-weight:700;cursor:pointer;">Enviar solicitud</button>
    </div>
  </div>
</div>

<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
  * { box-sizing: border-box; }
  body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--cx-bg-alt); color:var(--cx-text); }
  .header { background:linear-gradient(135deg,#0c4a6e,#7c3aed); padding:18px 28px; display:flex;align-items:center;justify-content:space-between; }
  .header h1 { margin:0; font-size:1.4em; font-weight:700; }
  .header a { color:var(--cx-primary-text); font-size:0.85em; text-decoration:none; }
  .container { max-width:1400px; margin:0 auto; padding:24px; }
  .grid { display:grid; gap:16px; }
  .grid-4 { grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); }
  .card { background:var(--cx-card); border:1px solid var(--cx-border); border-radius:10px; padding:18px; }
  .card h3 { margin:0 0 8px; font-size:0.78em; color:var(--cx-text-mute); text-transform:uppercase; letter-spacing:0.06em; font-weight:600; }
  .card .val { font-size:1.9em; font-weight:700; color:var(--cx-text); }
  .card .sub { font-size:0.8em; color:var(--cx-text-mute); margin-top:4px; }
  .section-title { font-size:1.05em; font-weight:700; color:var(--cx-text); margin:28px 0 12px; padding-bottom:6px; border-bottom:2px solid var(--cx-border); }
  .alert { background:var(--cx-danger-pale); border-left:4px solid var(--cx-danger); padding:10px 14px; margin-bottom:8px; border-radius:6px; font-size:13px; }
  .alert.media { background:var(--cx-warn-pale); border-left-color:var(--cx-warn); }
  .alert .title { font-weight:600; color:var(--cx-danger-text); margin-bottom:3px; }
  .alert.media .title { color:var(--cx-warn-text); }
  .alert .accion { font-size:11px; color:var(--cx-text-mute); margin-top:4px; font-style:italic; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { background:var(--cx-bg-alt); color:var(--cx-text-mute); font-weight:600; text-align:left; padding:8px 10px; font-size:11px; text-transform:uppercase; }
  td { padding:8px 10px; border-bottom:1px solid var(--cx-border); }
  .badge { padding:2px 8px; border-radius:10px; font-size:10px; font-weight:700; }
  .badge.alta { background:var(--cx-danger-pale); color:var(--cx-danger-text); }
  .badge.media { background:var(--cx-warn-pale); color:var(--cx-warn-text); }
  .badge.baja { background:var(--cx-success-pale); color:var(--cx-success-text); }
  .badge.estado-asig { background:var(--cx-card); color:var(--cx-text-mute); }
  .badge.estado-prog { background:var(--cx-info-pale); color:var(--cx-info-text); }
  .badge.estado-bloq { background:var(--cx-danger-pale); color:var(--cx-danger-text); }
  .badge.estado-hecha { background:var(--cx-success-pale); color:var(--cx-success-text); }
  .empty { color:var(--cx-text-mute); font-style:italic; padding:20px; text-align:center; }
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
    table tr { background:var(--cx-bg-alt); border-radius:8px; padding:10px; margin-bottom:8px; border:1px solid var(--cx-border); }
    table td { border-bottom:none; padding:4px 0; font-size:12px; }
    table td:first-child { font-weight:700; color:var(--cx-text); font-size:13px; padding-bottom:6px; }
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
  <header class="cx-mod-header cx-fade-in">
    <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:var(--cx-primary-text);"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
    <div>
      <div class="cx-mod-header__title">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M12 21V8M12 8c-3 0-6-2-6-5 3 0 6 2 6 5z"/><path d="M12 8c3 0 6-2 6-5-3 0-6 2-6 5zM8 14c-2 0-4-1-4-3 2 0 4 1 4 3zM16 14c2 0 4-1 4-3-2 0-4 1-4 3z"/></svg>
        Espagiria - Panel Asistente
      </div>
      <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; vista consolidada para coordinación operativa de planta</div>
    </div>
    <div class="cx-mod-header__nav">
      <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">Módulos</a>
      <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
      </button>
    </div>
  </header>
  <script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>

  <!-- TABS -->
  <div style="background:var(--cx-card);border-bottom:1px solid var(--cx-border);padding:0 28px;display:flex;gap:0;overflow-x:auto;">
    <button class="esp-tab active" data-tab="inicio" onclick="esw('inicio')" style="background:none;border:none;color:var(--cx-primary-text);padding:14px 20px;font-size:13px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;cursor:pointer;border-bottom:3px solid #06b6d4;white-space:nowrap;">⚡ Inicio</button>
    <button class="esp-tab" data-tab="dash" onclick="esw('dash')" style="background:none;border:none;color:var(--cx-text-mute);padding:14px 20px;font-size:13px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;">📊 Dashboard</button>
    <button class="esp-tab" data-tab="lab" onclick="esw('lab')" style="background:none;border:none;color:var(--cx-text-mute);padding:14px 20px;font-size:13px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;">🔬 Lab en Vivo</button>
    <button class="esp-tab" data-tab="clientes" onclick="esw('clientes')" style="background:none;border:none;color:var(--cx-text-mute);padding:14px 20px;font-size:13px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;">👥 Clientes 360</button>
    <button class="esp-tab" data-tab="cartera" onclick="esw('cartera')" style="background:none;border:none;color:var(--cx-text-mute);padding:14px 20px;font-size:13px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;">💰 Cartera</button>
    <button class="esp-tab" data-tab="cajapagos" onclick="esw('cajapagos')" style="background:none;border:none;color:var(--cx-text-mute);padding:14px 20px;font-size:13px;font-weight:600;cursor:pointer;border-bottom:3px solid transparent;" title="Pedir un pago con el efectivo de la caja menor">&#128184; Pagos de caja</button>
  </div>

  <div class="container">
    <!-- TAB INICIO · Quick Actions -->
    <div id="esp-tab-inicio" class="esp-pane">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;flex-wrap:wrap;gap:12px;">
        <div>
          <div style="font-size:1.4em;font-weight:700;color:var(--cx-text);">⚡ Lo urgente del día</div>
          <div style="font-size:13px;color:var(--cx-text-mute);">Resumen de lo que necesita tu acción ahora</div>
        </div>
        <div style="display:flex;gap:8px;">
          <button onclick="abrirPedidoRapido()" style="background:var(--cx-success-pale);border:1px solid var(--cx-success);color:var(--cx-success-text);padding:10px 16px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;">+ Pedido rápido</button>
          <button onclick="cargarQA()" style="background:var(--cx-primary-soft);border:1px solid var(--cx-primary);color:var(--cx-primary-text);padding:10px 14px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;">↻</button>
        </div>
      </div>
      <div id="qa-content"><div class="empty">Cargando...</div></div>
    </div>

    <!-- TAB DASHBOARD -->
    <div id="esp-tab-dash" class="esp-pane" style="display:none;">
    <!-- KPIs principales -->
    <div class="grid grid-4">
      <div class="card"><h3>📦 Producciones del mes</h3><div class="val" id="kpi-prod">-</div><div class="sub" id="kpi-prod-sub"></div></div>
      <div class="card"><h3>⚠️ MPs bajo mínimo</h3><div class="val" id="kpi-mps" style="color:var(--cx-danger-text);">-</div><div class="sub">Necesitan reposición</div></div>
      <div class="card"><h3>📅 Lotes vencen 30 días</h3><div class="val" id="kpi-venc" style="color:var(--cx-warn-text);">-</div><div class="sub" id="kpi-venc-sub"></div></div>
      <div class="card"><h3>🛒 OCs activas</h3><div class="val" id="kpi-ocs">-</div><div class="sub" id="kpi-ocs-sub"></div></div>
    </div>

    <div class="grid grid-4" style="margin-top:14px;">
      <div class="card"><h3>📋 Solicitudes pendientes</h3><div class="val" id="kpi-sol">-</div><div class="sub">Esperan aprobación</div></div>
      <div class="card"><h3>🔬 NCs abiertas</h3><div class="val" id="kpi-ncs" style="color:var(--cx-warn-text);">-</div><div class="sub">Calidad sin cerrar</div></div>
      <div class="card"><h3>🟡 Lotes en cuarentena</h3><div class="val" id="kpi-cuar">-</div><div class="sub">Por liberar</div></div>
      <div class="card"><h3>🚚 Pedidos activos</h3><div class="val" id="kpi-ped">-</div><div class="sub">En proceso o despacho</div></div>
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
        <div id="comite-info" style="font-size:12px;color:var(--cx-text-mute);margin-bottom:8px;"></div>
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
    </div><!-- /tab dash -->

    <!-- TAB LAB EN VIVO -->
    <div id="esp-tab-lab" class="esp-pane" style="display:none;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px;">
        <div>
          <div style="font-size:1.2em;font-weight:700;color:var(--cx-text);">🔬 Lab en Vivo</div>
          <div style="font-size:12px;color:var(--cx-text-mute);">Snapshot de la planta espagiría AHORA · auto-refresh cada 60s</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <span id="lab-ts" style="font-size:11px;color:var(--cx-text-mute);"></span>
          <button onclick="cargarLab()" style="background:var(--cx-primary-soft);border:1px solid var(--cx-primary);color:var(--cx-primary-text);padding:8px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;">↻ Refrescar</button>
        </div>
      </div>

      <!-- KPIs lab -->
      <div class="grid grid-4">
        <div class="card"><h3>⚙️ En curso</h3><div class="val" id="lab-kpi-curso">-</div><div class="sub">Producciones activas</div></div>
        <div class="card"><h3>📅 Hoy</h3><div class="val" id="lab-kpi-hoy">-</div><div class="sub">Programadas hoy</div></div>
        <div class="card"><h3>🟡 Cuarentena</h3><div class="val" id="lab-kpi-cuar" style="color:var(--cx-warn-text);">-</div><div class="sub">Lotes</div></div>
        <div class="card"><h3>⚠️ OOS abiertos</h3><div class="val" id="lab-kpi-oos" style="color:var(--cx-danger-text);">-</div><div class="sub">En investigación</div></div>
      </div>

      <div class="grid grid-2" style="margin-top:18px;">
        <div>
          <div class="section-title">⚙️ Producciones en curso</div>
          <div id="lab-curso-list"><div class="empty">Cargando...</div></div>
        </div>
        <div>
          <div class="section-title">📅 Programadas hoy</div>
          <div id="lab-hoy-list"><div class="empty">Cargando...</div></div>
        </div>
      </div>

      <div class="grid grid-2" style="margin-top:18px;">
        <div>
          <div class="section-title">🟡 Lotes en cuarentena</div>
          <div id="lab-cuar-list"><div class="empty">Cargando...</div></div>
        </div>
        <div>
          <div class="section-title">⚠️ OOS abiertos</div>
          <div id="lab-oos-list"><div class="empty">Cargando...</div></div>
        </div>
      </div>

      <div class="grid grid-2" style="margin-top:18px;">
        <div>
          <div class="section-title">🔧 Equipos · próximos a vencer (15d)</div>
          <div id="lab-eq-list"><div class="empty">Cargando...</div></div>
        </div>
        <div>
          <div class="section-title">📢 Desviaciones abiertas</div>
          <div id="lab-desv-list"><div class="empty">Cargando...</div></div>
        </div>
      </div>

      <div class="grid grid-2" style="margin-top:18px;">
        <div class="card">
          <h3>💧 Sistema de agua hoy</h3>
          <div class="val" id="lab-agua-val">-</div>
          <div class="sub" id="lab-agua-sub"></div>
        </div>
        <div class="card">
          <h3>🎓 Capacitaciones pendientes</h3>
          <div class="val" id="lab-cap" style="color:var(--cx-warn-text);">-</div>
          <div class="sub">Empleados sin firmar SOPs</div>
        </div>
      </div>
    </div><!-- /tab lab -->

    <!-- TAB CLIENTES 360 -->
    <div id="esp-tab-clientes" class="esp-pane" style="display:none;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px;">
        <div>
          <div style="font-size:1.2em;font-weight:700;color:var(--cx-text);">👥 Clientes Maquila 360</div>
          <div style="font-size:12px;color:var(--cx-text-mute);">Vista completa de cada cliente · click en uno para ver ficha 360</div>
        </div>
        <input id="cli-search" type="text" placeholder="Buscar cliente..." oninput="filtrarClientes()" style="background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);padding:8px 12px;border-radius:6px;font-size:13px;max-width:240px;">
      </div>

      <div id="cli-grid" class="grid grid-4"><div class="empty">Cargando clientes...</div></div>

      <!-- Modal ficha 360 -->
      <div id="cli-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:1000;align-items:center;justify-content:center;padding:20px;">
        <div style="background:var(--cx-card);border:1px solid var(--cx-text-soft);border-radius:14px;padding:24px;width:900px;max-width:95vw;max-height:90vh;overflow-y:auto;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <h2 id="cli-modal-title" style="margin:0;font-size:1.3em;color:var(--cx-text);">Cliente</h2>
            <button onclick="cerrarCliModal()" style="background:none;border:none;color:var(--cx-text-mute);font-size:24px;cursor:pointer;">&times;</button>
          </div>
          <div id="cli-modal-body"><div class="empty">Cargando...</div></div>
        </div>
      </div>
    </div><!-- /tab clientes -->

    <!-- TAB CARTERA -->
    <div id="esp-tab-cajapagos" class="esp-pane" style="display:none;">
      <!-- SOLICITAR PAGO DESDE CAJA MENOR (3-ago · Sebastián: "lo mismo a luz en su modulo
           de espagiria"). Luz PIDE acá; gerencia autoriza y quien maneja la caja paga.
           Los botones de autorizar y pagar NO van acá: un botón que responde 403 es peor que
           no tenerlo, porque quien lo aprieta cree que hizo algo. -->
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;margin-bottom:14px;">
        <div>
          <div style="font-weight:800;font-size:17px;color:var(--cx-text);">&#128184; Pagos con caja menor</div>
          <div style="font-size:12px;color:var(--cx-text-mute);margin-top:3px;">
            Ped&iacute; un pago con el efectivo de la caja &middot; lo autoriza gerencia y lo paga
            quien maneja la caja &middot; ac&aacute; segu&iacute;s en qu&eacute; va cada uno
          </div>
        </div>
        <button onclick="epAbrir()"
                style="background:var(--cx-primary-grad);color:var(--cx-text);border:none;
                       border-radius:8px;padding:10px 20px;font-size:14px;font-weight:700;cursor:pointer;">
          &#10133; Solicitar pago</button>
      </div>
      <div id="ep-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:16px;"></div>
      <div id="ep-body"><div style="color:var(--cx-text-mute);text-align:center;padding:40px;">Cargando...</div></div>
    </div>

    <div id="esp-tab-cartera" class="esp-pane" style="display:none;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:12px;">
        <div>
          <div style="font-size:1.4em;font-weight:700;color:var(--cx-text);">💰 Cartera Maquila</div>
          <div style="font-size:12px;color:var(--cx-text-mute);">Pedidos entregados con estado de pago · cruza con flujo_ingresos por número</div>
        </div>
        <button onclick="cargarCartera()" style="background:var(--cx-primary-soft);border:1px solid var(--cx-primary);color:var(--cx-primary-text);padding:8px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;">↻ Refrescar</button>
      </div>
      <div class="grid grid-4" id="cart-kpis"></div>
      <div class="section-title" style="margin-top:18px;">📊 Por cliente</div>
      <div id="cart-por-cliente"><div class="empty">Cargando...</div></div>
      <div class="section-title" style="margin-top:18px;">📋 Detalle por pedido</div>
      <div id="cart-detalle"><div class="empty">Cargando...</div></div>
    </div><!-- /tab cartera -->

    <!-- MODAL PEDIDO RAPIDO -->
    <div id="pr-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:1000;align-items:center;justify-content:center;padding:20px;">
      <div style="background:var(--cx-card);border:1px solid var(--cx-text-soft);border-radius:14px;padding:24px;width:560px;max-width:95vw;max-height:90vh;overflow-y:auto;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
          <h2 style="margin:0;font-size:1.2em;color:var(--cx-text);">📦 Nuevo pedido maquila</h2>
          <button onclick="cerrarPedidoRapido()" style="background:none;border:none;color:var(--cx-text-mute);font-size:24px;cursor:pointer;">&times;</button>
        </div>
        <div style="margin-bottom:14px;">
          <label style="display:block;font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;margin-bottom:6px;">Cliente *</label>
          <select id="pr-cliente" style="width:100%;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);padding:10px;border-radius:6px;font-size:14px;">
            <option value="">- Seleccionar cliente -</option>
          </select>
        </div>
        <div style="margin-bottom:14px;">
          <label style="display:block;font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;margin-bottom:6px;">Producto *</label>
          <input id="pr-producto" type="text" placeholder="Ej: Hydra Balance 30ml" style="width:100%;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);padding:10px;border-radius:6px;font-size:14px;">
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;">
          <div>
            <label style="display:block;font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;margin-bottom:6px;">Unidades *</label>
            <input id="pr-uds" type="number" min="1" placeholder="0" style="width:100%;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);padding:10px;border-radius:6px;font-size:14px;">
          </div>
          <div>
            <label style="display:block;font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;margin-bottom:6px;">Precio unidad (COP)</label>
            <input id="pr-precio" type="number" min="0" placeholder="0" style="width:100%;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);padding:10px;border-radius:6px;font-size:14px;">
          </div>
        </div>
        <div style="margin-bottom:14px;">
          <label style="display:block;font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;margin-bottom:6px;">Fecha entrega objetivo</label>
          <input id="pr-fecha" type="date" style="width:100%;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);padding:10px;border-radius:6px;font-size:14px;">
        </div>
        <div style="margin-bottom:14px;">
          <label style="display:block;font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;margin-bottom:6px;">Observaciones</label>
          <textarea id="pr-obs" placeholder="Detalles adicionales..." style="width:100%;background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);padding:10px;border-radius:6px;font-size:14px;min-height:60px;"></textarea>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;">
          <button onclick="cerrarPedidoRapido()" style="background:none;border:1px solid var(--cx-border);color:var(--cx-text-mute);padding:10px 16px;border-radius:6px;font-size:13px;cursor:pointer;">Cancelar</button>
          <button onclick="guardarPedidoRapido()" style="background:var(--cx-success-pale);border:1px solid var(--cx-success);color:var(--cx-success-text);padding:10px 18px;border-radius:6px;font-size:13px;font-weight:700;cursor:pointer;">Crear pedido</button>
        </div>
      </div>
    </div>
  </div>

<script>
function fmtNum(n) { return (n||0).toLocaleString('es-CO'); }
function _esc(s) { return String(s||'').replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c])); }

// CSRF defense-in-depth
function _csrf() {
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
fetch('/api/csrf-token', {credentials: 'same-origin'}).catch(function(){});

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
          '<tr><td>' + _esc(t.titulo) + '<div style="font-size:10px;color:var(--cx-text-mute);">'+(t.area||'')+'</div></td>' +
          '<td style="color:var(--cx-warn-text);font-size:11px;">'+(t.fecha_compromiso||'sin fecha')+'</td>' +
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
            '<td style="font-size:11px;color:var(--cx-info-text);">'+_esc(t.responsables||'-')+'</td>' +
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
        '<div style="font-size:12px;color:var(--cx-text-soft);">'+_esc(al.detalle||'')+'</div>' +
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
          '<td style="font-size:11px;color:var(--cx-info-text);">'+_esc(t.responsables||'-')+'</td>' +
          '<td style="color:var(--cx-danger-text);font-weight:700;">'+Math.round(t.dias_abierta)+'</td></tr>'
        ).join('') + '</tbody></table>';
    }

    const cList = document.getElementById('completadas-list');
    if (!p.completadas_semana || p.completadas_semana.length === 0) {
      cList.innerHTML = '<div class="empty">Sin tareas completadas aún esta semana</div>';
    } else {
      cList.innerHTML = '<table><thead><tr><th>Tarea</th><th>Área</th><th>Fecha</th></tr></thead><tbody>' +
        p.completadas_semana.slice(0,15).map(t =>
          '<tr><td style="font-size:12px;">'+_esc(t.titulo)+'</td>' +
          '<td style="font-size:11px;color:var(--cx-text-mute);">'+_esc(t.area||'-')+'</td>' +
          '<td style="font-size:11px;color:var(--cx-success-text);">'+_esc((t.fecha_completada||'').substring(0,10))+'</td></tr>'
        ).join('') + '</tbody></table>';
    }
  } catch(e) { console.error('Pre-comite error:', e); }
}

cargar();
setInterval(cargar, 5*60*1000); // refresh cada 5 min

// ════════════════════════════════════════════════════════════════
// TABS
// ════════════════════════════════════════════════════════════════
function esw(name) {
  document.querySelectorAll('.esp-tab').forEach(function(t){
    var on = t.dataset.tab === name;
    t.style.color = on ? 'var(--cx-primary-text)' : 'var(--cx-text-mute)';
    t.style.borderBottomColor = on ? 'var(--cx-primary)' : 'transparent';
    t.classList.toggle('active', on);
  });
  document.querySelectorAll('.esp-pane').forEach(function(p){
    p.style.display = (p.id === 'esp-tab-' + name) ? '' : 'none';
  });
  if (name === 'lab') cargarLab();
  if (name === 'clientes') cargarClientes();
  if (name === 'cajapagos') cargarPagosCaja();
}

// ════════════════════════════════════════════════════════════════
// LAB EN VIVO
// ════════════════════════════════════════════════════════════════
// ── PAGOS CON CAJA MENOR desde Espagiria (3-ago) ──────────────────────────────
// Luz PIDE acá; gerencia autoriza en su módulo y quien maneja la caja paga en el suyo.
// La lista se filtra a ESPAGIRIA: no tiene por qué ver los gastos de ÁNIMUS.
var _EP_TOPE = 200000;

function _epEsc(s){ return String(s == null ? '' : s)
  .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function _epFmt(n){ return '$ ' + Number(n || 0).toLocaleString('es-CO', {maximumFractionDigits:0}); }

async function cargarPagosCaja(){
  var body = document.getElementById('ep-body');
  if(!body) return;
  try{
    var r = await fetch('/api/caja/solicitudes?empresa=ESPAGIRIA');
    var d = await r.json();
    if(!d.ok){ body.innerHTML = '<div style="color:var(--cx-danger-text);padding:16px;">' + _epEsc(d.error||'Error') + '</div>'; return; }
    _EP_TOPE = d.tope || 200000;
    epRenderKPIs(d);
    epRenderLista(d.solicitudes || []);
  }catch(e){
    body.innerHTML = '<div style="color:var(--cx-danger-text);padding:16px;">Error: ' + _epEsc(e.message) + '</div>';
  }
}

function epRenderKPIs(d){
  var k = d.kpis || {};
  function t(lab, val, sub, color){
    return '<div style="background:var(--cx-card);border:1px solid var(--cx-border);border-radius:12px;padding:14px;">'
      + '<div style="font-size:10px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.08em;font-weight:700;">' + lab + '</div>'
      + '<div style="font-size:22px;font-weight:800;margin-top:6px;color:' + color + ';">' + val + '</div>'
      + '<div style="font-size:11px;color:var(--cx-text-mute);margin-top:4px;">' + sub + '</div></div>';
  }
  var esp = k.solicitada || {n:0,monto:0}, aut = k.autorizada || {n:0,monto:0}, pag = k.pagada || {n:0,monto:0};
  document.getElementById('ep-kpis').innerHTML =
      t('Esperan autorizacion', _epFmt(esp.monto), esp.n + ' solicitudes', 'var(--cx-warn-text)')
    + t('Listas para pagar', _epFmt(aut.monto), aut.n + ' autorizadas', 'var(--cx-success-text)')
    + t('Ya pagadas', _epFmt(pag.monto), pag.n + ' pagos', 'var(--cx-info-text)')
    + t('Tope sin autorizar', _epFmt(_EP_TOPE), 'bajo esto no espera a gerencia', 'var(--cx-text-soft)');
}

function epRenderLista(rows){
  var body = document.getElementById('ep-body');
  if(!rows.length){
    body.innerHTML = '<div style="color:var(--cx-text-mute);text-align:center;padding:40px;">Todavia no hay solicitudes de pago.</div>';
    return;
  }
  var col = {solicitada:'var(--cx-warn-text)', autorizada:'var(--cx-success-text)',
             pagada:'var(--cx-info-text)', rechazada:'var(--cx-danger-text)'};
  var etq = {solicitada:'espera autorizacion', autorizada:'lista para pagar',
             pagada:'pagada', rechazada:'rechazada'};
  var h = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr>'
    + '<th style="text-align:left;padding:8px;border-bottom:1px solid var(--cx-border);">N&deg;</th>'
    + '<th style="text-align:left;padding:8px;border-bottom:1px solid var(--cx-border);">Concepto</th>'
    + '<th style="text-align:right;padding:8px;border-bottom:1px solid var(--cx-border);">Monto</th>'
    + '<th style="text-align:left;padding:8px;border-bottom:1px solid var(--cx-border);">Estado</th>'
    + '<th style="text-align:left;padding:8px;border-bottom:1px solid var(--cx-border);">Quien</th>'
    + '</tr></thead><tbody>';
  rows.forEach(function(s){
    // El rechazo va CON su motivo: sin el, quien pidio no sabe que corregir.
    var extra = '';
    if(s.estado === 'rechazada' && s.motivo_rechazo)
      extra = '<div style="font-size:11px;color:var(--cx-danger-text);">' + _epEsc(s.motivo_rechazo) + '</div>';
    else if(s.estado === 'pagada' && s.pagado_por)
      extra = '<div style="font-size:11px;color:var(--cx-text-mute);">pago ' + _epEsc(s.pagado_por) + '</div>';
    h += '<tr>'
      + '<td style="padding:8px;font-weight:700;border-bottom:1px solid var(--cx-hairline);">' + _epEsc(s.numero) + '</td>'
      + '<td style="padding:8px;border-bottom:1px solid var(--cx-hairline);">' + _epEsc(s.concepto)
        + (s.beneficiario ? '<div style="font-size:11px;color:var(--cx-text-mute);">' + _epEsc(s.beneficiario) + '</div>' : '') + '</td>'
      + '<td style="padding:8px;text-align:right;font-weight:700;border-bottom:1px solid var(--cx-hairline);">' + _epFmt(s.monto) + '</td>'
      + '<td style="padding:8px;border-bottom:1px solid var(--cx-hairline);color:' + (col[s.estado]||'var(--cx-text-mute)') + ';font-weight:600;">'
        + _epEsc(etq[s.estado] || s.estado) + extra + '</td>'
      + '<td style="padding:8px;border-bottom:1px solid var(--cx-hairline);font-size:11px;">' + _epEsc(s.solicitado_por) + '</td>'
      + '</tr>';
  });
  body.innerHTML = h + '</tbody></table></div>';
}

function epAbrir(){
  ['ep-concepto','ep-monto','ep-benef','ep-obs','ep-cotiz'].forEach(function(id){
    var el = document.getElementById(id); if(el) el.value = '';
  });
  document.getElementById('ep-tope-aviso').innerHTML = '';
  document.getElementById('modal-ep').style.display = 'flex';
}

function epAvisarTope(){
  var m = parseFloat((document.getElementById('ep-monto')||{value:0}).value || 0);
  var el = document.getElementById('ep-tope-aviso');
  if(!m){ el.innerHTML = ''; return; }
  el.innerHTML = m <= _EP_TOPE
    ? '<span style="color:var(--cx-success-text);">Bajo el tope de ' + _epFmt(_EP_TOPE) + ': queda lista para pagar sin esperar autorizacion.</span>'
    : '<span style="color:var(--cx-warn-text);">Supera el tope de ' + _epFmt(_EP_TOPE) + ': va a gerencia para autorizar.</span>';
}

async function epGuardar(){
  var body = {
    concepto: (document.getElementById('ep-concepto')||{value:''}).value.trim(),
    monto: parseFloat((document.getElementById('ep-monto')||{value:0}).value || 0),
    empresa: (document.getElementById('ep-empresa')||{value:'ESPAGIRIA'}).value,
    beneficiario: (document.getElementById('ep-benef')||{value:''}).value.trim(),
    observaciones: (document.getElementById('ep-obs')||{value:''}).value.trim(),
    cotizacion_url: (document.getElementById('ep-cotiz')||{value:''}).value.trim(),
    modulo_origen: 'espagiria'
  };
  if(!body.concepto){ alert('Concepto requerido'); return; }
  if(!body.monto || body.monto <= 0){ alert('El monto debe ser mayor a 0'); return; }
  // Guard anti doble-click: una solicitud duplicada termina en un pago duplicado (M63).
  if(window._epBusy) return;
  window._epBusy = true;
  setTimeout(function(){ window._epBusy = false; }, 3000);
  try{
    var t = await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json();
    var r = await fetch('/api/caja/solicitudes', {method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':t.csrf_token},
      body: JSON.stringify(body)});
    var d = await r.json();
    if(!d.ok){ alert('Error: ' + (d.error||'?')); return; }
    alert(d.numero + ' - ' + (d.aviso||''));
    document.getElementById('modal-ep').style.display = 'none';
    cargarPagosCaja();
  }catch(e){ alert('Error de red: ' + e.message); }
  finally { window._epBusy = false; }
}

var _labInterval = null;
async function cargarLab() {
  try {
    var d = await fetch('/api/espagiria/lab/en-vivo').then(function(r){return r.json();});
    document.getElementById('lab-ts').textContent = 'Actualizado: ' + new Date().toLocaleTimeString('es-CO');
    document.getElementById('lab-kpi-curso').textContent = (d.producciones_en_curso||[]).length;
    document.getElementById('lab-kpi-hoy').textContent = (d.producciones_hoy||[]).length;
    document.getElementById('lab-kpi-cuar').textContent = (d.lotes_cuarentena||[]).length;
    document.getElementById('lab-kpi-oos').textContent = (d.oos_abiertos||[]).length;

    var curso = document.getElementById('lab-curso-list');
    if (!d.producciones_en_curso || !d.producciones_en_curso.length) {
      curso.innerHTML = '<div class="empty">Sin producciones en curso ahora</div>';
    } else {
      curso.innerHTML = '<table><thead><tr><th>Producto</th><th>Sala</th><th>Operario</th><th>Inicio</th></tr></thead><tbody>' +
        d.producciones_en_curso.map(function(p){
          return '<tr><td>' + _esc(p.producto||'') + '<div style="font-size:10px;color:var(--cx-text-mute);">' + (p.lotes||1) + ' lote' + ((p.lotes||1)===1?'':'s') + ' · ' + (p.cantidad_kg||0) + 'kg</div></td>' +
            '<td><span class="badge estado-prog">' + (p.area_codigo||'-') + '</span></td>' +
            '<td style="font-size:11px;color:var(--cx-info-text);">' + _esc(p.operario_elaboracion || p.operario_dispensacion || '-') + '</td>' +
            '<td style="font-size:10px;color:var(--cx-text-mute);">' + _esc((p.inicio_real_at||'').substring(11,16)) + '</td></tr>';
        }).join('') + '</tbody></table>';
    }

    var hoy = document.getElementById('lab-hoy-list');
    if (!d.producciones_hoy || !d.producciones_hoy.length) {
      hoy.innerHTML = '<div class="empty">Sin producciones programadas hoy</div>';
    } else {
      hoy.innerHTML = '<table><thead><tr><th>Producto</th><th>Sala</th><th>Lotes</th><th>Estado</th></tr></thead><tbody>' +
        d.producciones_hoy.map(function(p){
          return '<tr><td>' + _esc(p.producto||'') + '</td>' +
            '<td><span class="badge estado-prog">' + (p.area_codigo||'-') + '</span></td>' +
            '<td>' + (p.lotes||1) + '</td>' +
            '<td style="font-size:11px;">' + _esc(p.estado||'') + '</td></tr>';
        }).join('') + '</tbody></table>';
    }

    var cuar = document.getElementById('lab-cuar-list');
    if (!d.lotes_cuarentena || !d.lotes_cuarentena.length) {
      cuar.innerHTML = '<div class="empty">Sin lotes en cuarentena</div>';
    } else {
      cuar.innerHTML = '<table><thead><tr><th>Material</th><th>Lote</th><th>Cantidad</th><th>Días</th></tr></thead><tbody>' +
        d.lotes_cuarentena.map(function(l){
          var dias = Math.round(l.dias_cuarentena||0);
          var col = dias > 14 ? '#f87171' : dias > 7 ? '#fbbf24' : '#94a3b8';
          return '<tr><td>' + _esc(l.material_nombre||l.material_id||'') + '</td>' +
            '<td style="font-family:monospace;font-size:11px;">' + _esc(l.lote||'-') + '</td>' +
            '<td>' + (l.cantidad||0) + '</td>' +
            '<td style="color:' + col + ';font-weight:700;">' + dias + 'd</td></tr>';
        }).join('') + '</tbody></table>';
    }

    var oos = document.getElementById('lab-oos-list');
    if (!d.oos_abiertos || !d.oos_abiertos.length) {
      oos.innerHTML = '<div class="empty">Sin OOS abiertos ✅</div>';
    } else {
      oos.innerHTML = '<table><thead><tr><th>Código</th><th>Lote/Producto</th><th>Estado</th></tr></thead><tbody>' +
        d.oos_abiertos.map(function(o){
          return '<tr><td><b>' + _esc(o.codigo||'') + '</b></td>' +
            '<td>' + _esc(o.lote||'') + '<div style="font-size:10px;color:var(--cx-text-mute);">' + _esc(o.parametro||'') + '</div></td>' +
            '<td><span class="badge alta">' + _esc(o.estado||'') + '</span></td></tr>';
        }).join('') + '</tbody></table>';
    }

    var eq = document.getElementById('lab-eq-list');
    if (!d.equipos_estado || !d.equipos_estado.length) {
      eq.innerHTML = '<div class="empty">Equipos al día ✓</div>';
    } else {
      eq.innerHTML = '<table><thead><tr><th>Código</th><th>Equipo</th><th>Días</th></tr></thead><tbody>' +
        d.equipos_estado.map(function(e){
          var dias = Math.round(e.dias||0);
          var col = dias < 0 ? '#f87171' : dias < 7 ? '#fbbf24' : '#94a3b8';
          return '<tr><td><b>' + _esc(e.codigo||'') + '</b></td>' +
            '<td>' + _esc(e.nombre||'') + '<div style="font-size:10px;color:var(--cx-text-mute);">' + _esc(e.area_codigo||'') + '</div></td>' +
            '<td style="color:' + col + ';font-weight:700;">' + (dias < 0 ? 'VENCIDO ' + Math.abs(dias) : dias) + 'd</td></tr>';
        }).join('') + '</tbody></table>';
    }

    var desv = document.getElementById('lab-desv-list');
    if (!d.desviaciones_abiertas || !d.desviaciones_abiertas.length) {
      desv.innerHTML = '<div class="empty">Sin desviaciones abiertas ✅</div>';
    } else {
      desv.innerHTML = '<table><thead><tr><th>Código</th><th>Tipo</th><th>Sev.</th><th>Días</th></tr></thead><tbody>' +
        d.desviaciones_abiertas.map(function(x){
          var dias = Math.round(x.dias_abierta||0);
          var col = dias > 5 ? '#f87171' : dias > 2 ? '#fbbf24' : '#94a3b8';
          var sev = (x.severidad||'').toLowerCase();
          var sevC = sev === 'critica' ? 'alta' : sev === 'mayor' ? 'media' : 'baja';
          return '<tr><td><b>' + _esc(x.codigo||'') + '</b></td>' +
            '<td style="font-size:11px;">' + _esc(x.tipo||'') + '</td>' +
            '<td><span class="badge ' + sevC + '">' + _esc(x.severidad||'-') + '</span></td>' +
            '<td style="color:' + col + ';font-weight:700;">' + dias + 'd</td></tr>';
        }).join('') + '</tbody></table>';
    }

    var ahoy = d.agua_hoy || {};
    document.getElementById('lab-agua-val').textContent = (ahoy.registros||0) === 0 ? '⚠ Sin registro' : '✓ ' + ahoy.registros;
    document.getElementById('lab-agua-val').style.color = (ahoy.registros||0) === 0 ? '#fca5a5' : '#34d399';
    document.getElementById('lab-agua-sub').textContent = ahoy.ultima ? ('Último: ' + ahoy.ultima.substring(11,16)) : 'Pendiente registrar conductividad/cloro';
    document.getElementById('lab-cap').textContent = d.capacitaciones_pendientes || 0;
  } catch(e) { console.error('Lab error:', e); }
  // auto-refresh
  if (!_labInterval) {
    _labInterval = setInterval(function(){
      var pane = document.getElementById('esp-tab-lab');
      if (pane && pane.style.display !== 'none') cargarLab();
    }, 60*1000);
  }
}

// ════════════════════════════════════════════════════════════════
// CLIENTES 360
// ════════════════════════════════════════════════════════════════
var CLIENTES_DATA = [];
async function cargarClientes() {
  try {
    var d = await fetch('/api/espagiria/clientes-maquila').then(function(r){return r.json();});
    CLIENTES_DATA = d.clientes || [];
    renderClientes();
  } catch(e) {
    document.getElementById('cli-grid').innerHTML = '<div class="empty">Error: ' + e.message + '</div>';
  }
}
function filtrarClientes() { renderClientes(); }
function renderClientes() {
  var q = (document.getElementById('cli-search')||{value:''}).value.toLowerCase();
  var data = q ? CLIENTES_DATA.filter(function(c){
    return (c.nombre||'').toLowerCase().indexOf(q)>=0 ||
           (c.empresa_grupo||'').toLowerCase().indexOf(q)>=0;
  }) : CLIENTES_DATA;
  var grid = document.getElementById('cli-grid');
  if (!data.length) { grid.innerHTML = '<div class="empty">' + (q?'Sin coincidencias':'Sin clientes registrados') + '</div>'; return; }
  grid.innerHTML = data.map(function(c){
    var marca = c.es_marca_propia ? '<span class="badge baja" style="margin-left:6px;">MARCA</span>' : '';
    var act = (c.pedidos_activos||0) > 0 ? '<span class="badge media" style="margin-left:6px;">' + c.pedidos_activos + ' activos</span>' : '';
    var ult = c.ultimo_ped ? ('Último: ' + (c.ultimo_ped||'').substring(0,10)) : 'Sin pedidos';
    return '<div class="card" style="cursor:pointer;border-left:4px solid #06b6d4;" onclick="verCli360(' + c.id + ')">' +
      '<h3 style="text-transform:none;letter-spacing:0;color:var(--cx-text);font-size:0.95em;margin-bottom:6px;">' + _esc(c.nombre||'') + marca + act + '</h3>' +
      '<div style="font-size:11px;color:var(--cx-text-mute);">' + _esc(c.empresa_grupo||'-') + '</div>' +
      '<div style="margin-top:10px;display:flex;gap:14px;flex-wrap:wrap;">' +
        '<div><div style="font-size:10px;color:var(--cx-text-mute);">PEDIDOS</div><div style="font-size:1.1em;font-weight:700;color:var(--cx-text);">' + (c.total_pedidos||0) + '</div></div>' +
        '<div><div style="font-size:10px;color:var(--cx-text-mute);">VALOR TOTAL</div><div style="font-size:1.1em;font-weight:700;color:var(--cx-success-text);">$' + fmtNum(Math.round(c.valor_total||0)) + '</div></div>' +
      '</div>' +
      '<div style="font-size:11px;color:var(--cx-text-mute);margin-top:8px;">' + ult + '</div>' +
      '</div>';
  }).join('');
}
async function verCli360(id) {
  document.getElementById('cli-modal').style.display = 'flex';
  document.getElementById('cli-modal-body').innerHTML = '<div class="empty">Cargando ficha 360...</div>';
  try {
    var d = await fetch('/api/espagiria/clientes-maquila/' + id + '/360').then(function(r){return r.json();});
    if (d.error) { document.getElementById('cli-modal-body').innerHTML = '<div class="empty">Error: ' + _esc(d.error) + '</div>'; return; }
    document.getElementById('cli-modal-title').textContent = d.cliente.nombre;
    var s = d.stats || {};
    var html = '';
    // Datos
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:18px;">';
    html += '<div><div style="font-size:10px;color:var(--cx-text-mute);">NIT</div><div>' + _esc(d.cliente.nit_cedula||'-') + '</div></div>';
    html += '<div><div style="font-size:10px;color:var(--cx-text-mute);">EMAIL</div><div>' + _esc(d.cliente.email||'-') + '</div></div>';
    html += '<div><div style="font-size:10px;color:var(--cx-text-mute);">TELÉFONO</div><div>' + _esc(d.cliente.telefono||'-') + '</div></div>';
    html += '<div><div style="font-size:10px;color:var(--cx-text-mute);">EMPRESA GRUPO</div><div>' + _esc(d.cliente.empresa_grupo||'-') + '</div></div>';
    if (d.cliente.es_marca_propia) html += '<div style="grid-column:1/-1;"><span class="badge baja">MARCA PROPIA HHA</span></div>';
    if (d.cliente.comparte_formula_con) html += '<div style="grid-column:1/-1;font-size:11px;color:var(--cx-info-text);">📋 Comparte fórmula con: ' + _esc(d.cliente.comparte_formula_con) + '</div>';
    if (d.cliente.notas) html += '<div style="grid-column:1/-1;font-size:11px;color:var(--cx-text-mute);font-style:italic;">' + _esc(d.cliente.notas) + '</div>';
    html += '</div>';
    // KPIs
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:18px;">';
    html += '<div class="card"><h3>📦 Pedidos</h3><div class="val">' + s.total_pedidos + '</div></div>';
    html += '<div class="card"><h3>💵 Valor total</h3><div class="val" style="color:var(--cx-success-text);">$' + fmtNum(Math.round(s.valor_total||0)) + '</div></div>';
    html += '<div class="card"><h3>🎯 Ticket prom</h3><div class="val">$' + fmtNum(Math.round(s.ticket_promedio||0)) + '</div></div>';
    html += '<div class="card"><h3>🔥 Pipeline</h3><div class="val" style="color:var(--cx-warn-text);">' + (s.pipeline_activos||0) + '</div></div>';
    html += '<div class="card"><h3>⏱️ Días sin pedido</h3><div class="val" style="color:' + (s.dias_sin_pedido > 60 ? '#f87171' : '#fff') + ';">' + (s.dias_sin_pedido!=null ? s.dias_sin_pedido : '-') + '</div></div>';
    html += '</div>';
    // Pipeline activo
    html += '<div class="section-title">🔥 Pipeline activo</div>';
    if (!d.pipeline_activo || !d.pipeline_activo.length) {
      html += '<div class="empty">Sin pedidos activos</div>';
    } else {
      html += '<table><thead><tr><th>Número</th><th>Producto</th><th>Unidades</th><th>Estado</th><th>Entrega</th></tr></thead><tbody>' +
        d.pipeline_activo.map(function(p){
          return '<tr><td><b>' + _esc(p.numero||'') + '</b></td>' +
            '<td>' + _esc(p.producto_nombre||'') + '</td>' +
            '<td>' + (p.unidades||0) + '</td>' +
            '<td><span class="badge media">' + _esc(p.estado||'') + '</span></td>' +
            '<td style="font-size:11px;">' + _esc(p.fecha_entrega_objetivo||'-') + '</td></tr>';
        }).join('') + '</tbody></table>';
    }
    // Top productos
    html += '<div class="section-title" style="margin-top:18px;">⭐ Top productos solicitados</div>';
    if (!d.top_productos || !d.top_productos.length) {
      html += '<div class="empty">Sin historial</div>';
    } else {
      html += '<table><thead><tr><th>Producto</th><th>Veces</th><th>Total uds</th><th>Total kg</th><th>Último</th></tr></thead><tbody>' +
        d.top_productos.map(function(t){
          return '<tr><td>' + _esc(t.producto_nombre||'') + '</td>' +
            '<td>' + t.veces_pedido + '</td>' +
            '<td>' + fmtNum(t.total_uds||0) + '</td>' +
            '<td>' + (t.total_kg||0).toFixed(1) + '</td>' +
            '<td style="font-size:11px;color:var(--cx-text-mute);">' + _esc((t.ultimo||'').substring(0,10)) + '</td></tr>';
        }).join('') + '</tbody></table>';
    }
    // Pedidos recientes
    html += '<div class="section-title" style="margin-top:18px;">📋 Pedidos recientes</div>';
    if (!d.pedidos_recientes || !d.pedidos_recientes.length) {
      html += '<div class="empty">Sin pedidos</div>';
    } else {
      html += '<table><thead><tr><th>Número</th><th>Producto</th><th>Uds</th><th>Estado</th><th>Fecha</th><th>Valor</th></tr></thead><tbody>' +
        d.pedidos_recientes.map(function(p){
          return '<tr><td><b>' + _esc(p.numero||'') + '</b></td>' +
            '<td>' + _esc(p.producto_nombre||'') + '</td>' +
            '<td>' + (p.unidades||0) + '</td>' +
            '<td style="font-size:11px;">' + _esc(p.estado||'') + '</td>' +
            '<td style="font-size:11px;">' + _esc((p.fecha_pedido||'').substring(0,10)) + '</td>' +
            '<td style="text-align:right;">$' + fmtNum(Math.round(p.valor_total||0)) + '</td></tr>';
        }).join('') + '</tbody></table>';
    }
    document.getElementById('cli-modal-body').innerHTML = html;
  } catch(e) {
    document.getElementById('cli-modal-body').innerHTML = '<div class="empty">Error: ' + e.message + '</div>';
  }
}
function cerrarCliModal() {
  document.getElementById('cli-modal').style.display = 'none';
}
// Cerrar modal por click fuera
document.addEventListener('click', function(ev){
  var m = document.getElementById('cli-modal');
  if (m && ev.target === m) cerrarCliModal();
  var pr = document.getElementById('pr-modal');
  if (pr && ev.target === pr) cerrarPedidoRapido();
});

// ════════════════════════════════════════════════════════════════
// QUICK ACTIONS HOME
// ════════════════════════════════════════════════════════════════
async function cargarQA() {
  try {
    var d = await fetch('/api/espagiria/quick-actions').then(function(r){return r.json();});
    var c = document.getElementById('qa-content');
    if (!d.secciones || !d.secciones.length) {
      c.innerHTML = '<div class="card" style="text-align:center;padding:40px;border-left:4px solid var(--cx-success);"><div style="font-size:3em;">✅</div><div style="font-size:1.2em;color:var(--cx-success-text);font-weight:700;margin-top:12px;">Todo bajo control</div><div style="color:var(--cx-text-mute);margin-top:6px;">Sin acciones urgentes pendientes hoy</div></div>';
      return;
    }
    var html = '<div style="background:var(--cx-danger-pale);color:var(--cx-danger-text);padding:14px 18px;border-radius:8px;margin-bottom:16px;font-weight:700;">' +
               '⚠ ' + d.total_urgentes + ' acciones requieren tu atención</div>';
    d.secciones.forEach(function(s){
      var col = s.severidad === 'alta' ? '#dc2626' : '#f59e0b';
      var bgc = s.severidad === 'alta' ? '#3f0f0f' : '#1e1b3b';
      html += '<div class="card" style="border-left:4px solid ' + col + ';background:' + bgc + 'aa;margin-bottom:14px;">' +
              '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:10px;">' +
                '<div><div style="font-size:1.05em;font-weight:700;color:var(--cx-text);">' + _esc(s.titulo) + '</div>' +
                '<div style="font-size:11px;color:var(--cx-text-mute);margin-top:3px;">→ ' + _esc(s.accion) + '</div></div>' +
                '<a href="' + _esc(s.link) + '" style="background:var(--cx-bg-alt);color:var(--cx-text);padding:6px 12px;border-radius:6px;text-decoration:none;font-size:11px;font-weight:700;">Ir &rarr;</a>' +
              '</div>';
      // Mini lista
      if (s.items && s.items.length) {
        html += '<div style="font-size:12px;color:var(--cx-text-soft);border-top:1px solid var(--cx-border);padding-top:8px;">';
        s.items.slice(0, 5).forEach(function(it){
          var label = it.numero || it.codigo || it.titulo || it.lote || it.material_nombre || it.cliente_nombre || '?';
          var sub = it.cliente_nombre || it.producto_nombre || it.area || it.parametro || it.dias_vencido || it.dias || '';
          html += '<div style="padding:4px 0;border-bottom:1px solid var(--cx-border);">' +
                  '<b>' + _esc(label) + '</b>' +
                  (sub ? ' <span style="color:var(--cx-text-mute);">· ' + _esc(String(sub).substring(0,80)) + '</span>' : '') +
                  '</div>';
        });
        if (s.items.length > 5) html += '<div style="padding:4px 0;color:var(--cx-text-mute);font-style:italic;">y ' + (s.items.length - 5) + ' más...</div>';
        html += '</div>';
      }
      html += '</div>';
    });
    c.innerHTML = html;
  } catch(e) {
    document.getElementById('qa-content').innerHTML = '<div class="empty">Error: ' + e.message + '</div>';
  }
}

// ════════════════════════════════════════════════════════════════
// PEDIDO MAQUILA RAPIDO
// ════════════════════════════════════════════════════════════════
async function abrirPedidoRapido() {
  // Cargar lista de clientes en el select
  try {
    var d = await fetch('/api/espagiria/clientes-maquila').then(function(r){return r.json();});
    var sel = document.getElementById('pr-cliente');
    var opts = '<option value="">- Seleccionar cliente -</option>';
    (d.clientes||[]).forEach(function(c){
      opts += '<option value="' + c.id + '">' + _esc(c.nombre) + '</option>';
    });
    sel.innerHTML = opts;
  } catch(e) { console.error(e); }
  // Reset campos
  document.getElementById('pr-producto').value = '';
  document.getElementById('pr-uds').value = '';
  document.getElementById('pr-precio').value = '';
  document.getElementById('pr-fecha').value = '';
  document.getElementById('pr-obs').value = '';
  document.getElementById('pr-modal').style.display = 'flex';
}
function cerrarPedidoRapido() {
  document.getElementById('pr-modal').style.display = 'none';
}
async function guardarPedidoRapido() {
  var cliente_id = parseInt(document.getElementById('pr-cliente').value, 10);
  var producto = (document.getElementById('pr-producto').value || '').trim();
  var unidades = parseInt(document.getElementById('pr-uds').value, 10);
  var precio = parseFloat(document.getElementById('pr-precio').value);
  var fecha = document.getElementById('pr-fecha').value || null;
  var obs = document.getElementById('pr-obs').value || '';
  if (!cliente_id) { alert('Selecciona un cliente'); return; }
  if (!producto) { alert('Producto obligatorio'); return; }
  if (isNaN(unidades) || unidades <= 0) { alert('Unidades debe ser > 0'); return; }
  var payload = {
    cliente_id: cliente_id,
    producto_nombre: producto,
    unidades: unidades,
    fecha_entrega_objetivo: fecha,
    observaciones: obs,
  };
  if (!isNaN(precio) && precio >= 0) payload.precio_unidad = precio;
  try {
    var r = await fetch('/api/espagiria/pedido-rapido', _fetchOpts('POST', payload));
    var d = await r.json();
    if (r.ok && d.ok) {
      alert('✅ Pedido ' + d.numero + ' creado para ' + d.cliente);
      cerrarPedidoRapido();
      cargarQA();  // refrescar por si pasa de "sin asignar" a "necesita produccion"
    } else {
      alert('Error: ' + (d.error || 'No se pudo crear'));
    }
  } catch(e) { alert('Error red: ' + e.message); }
}

// ════════════════════════════════════════════════════════════════
// CARTERA MAQUILA
// ════════════════════════════════════════════════════════════════
async function cargarCartera() {
  try {
    var d = await fetch('/api/espagiria/cartera-maquila').then(function(r){return r.json();});
    var k = d.kpis || {};
    document.getElementById('cart-kpis').innerHTML =
      '<div class="card"><h3>📋 Pedidos entregados</h3><div class="val">' + (k.total_pedidos||0) + '</div></div>' +
      '<div class="card"><h3>💵 Total facturado</h3><div class="val" style="color:var(--cx-text);">$' + fmtNum(Math.round(k.total_facturado||0)) + '</div></div>' +
      '<div class="card"><h3>✅ Pagado</h3><div class="val" style="color:var(--cx-success-text);">$' + fmtNum(Math.round(k.total_pagado||0)) + '</div></div>' +
      '<div class="card"><h3>🚨 Vencido +30d</h3><div class="val" style="color:var(--cx-danger-text);">$' + fmtNum(Math.round(k.total_vencido_30d||0)) + '</div></div>';
    // Por cliente
    var pcDiv = document.getElementById('cart-por-cliente');
    if (!d.por_cliente || !d.por_cliente.length) {
      pcDiv.innerHTML = '<div class="empty">Sin pedidos entregados</div>';
    } else {
      pcDiv.innerHTML = '<table><thead><tr><th>Cliente</th><th style="text-align:right;">Pedidos</th><th style="text-align:right;">Facturado</th><th style="text-align:right;">Pagado</th><th style="text-align:right;">Saldo</th><th style="text-align:right;">Vencido +30d</th></tr></thead><tbody>' +
        d.por_cliente.map(function(c){
          var col = c.vencido_30d > 0 ? '#fca5a5' : (c.saldo > 0 ? '#fbbf24' : '#34d399');
          return '<tr><td><b>' + _esc(c.cliente) + '</b></td>' +
            '<td style="text-align:right;">' + c.pedidos + '</td>' +
            '<td style="text-align:right;">$' + fmtNum(Math.round(c.facturado||0)) + '</td>' +
            '<td style="text-align:right;color:var(--cx-success-text);">$' + fmtNum(Math.round(c.pagado||0)) + '</td>' +
            '<td style="text-align:right;color:' + col + ';font-weight:700;">$' + fmtNum(Math.round(c.saldo||0)) + '</td>' +
            '<td style="text-align:right;color:var(--cx-danger-text);font-weight:700;">$' + fmtNum(Math.round(c.vencido_30d||0)) + '</td></tr>';
        }).join('') + '</tbody></table>';
    }
    // Detalle
    var dtDiv = document.getElementById('cart-detalle');
    if (!d.pedidos || !d.pedidos.length) {
      dtDiv.innerHTML = '<div class="empty">Sin pedidos en cartera</div>';
    } else {
      dtDiv.innerHTML = '<table><thead><tr><th>Pedido</th><th>Cliente</th><th>Producto</th><th style="text-align:right;">Valor</th><th style="text-align:right;">Pagado</th><th style="text-align:right;">Saldo</th><th>Estado</th><th>Días</th></tr></thead><tbody>' +
        d.pedidos.map(function(p){
          var ec = p.estado_pago === 'pagado' ? 'baja' :
                   p.estado_pago === 'parcial' ? 'media' :
                   p.estado_pago === 'vencido_mayor_30d' ? 'alta' :
                   p.estado_pago === 'vencido_15d' ? 'media' : 'estado-asig';
          return '<tr><td><b>' + _esc(p.numero||'') + '</b></td>' +
            '<td>' + _esc(p.cliente_nombre||'') + '</td>' +
            '<td style="font-size:11px;">' + _esc((p.producto_nombre||'').substring(0,40)) + '</td>' +
            '<td style="text-align:right;">$' + fmtNum(Math.round(p.valor_total||0)) + '</td>' +
            '<td style="text-align:right;color:var(--cx-success-text);">$' + fmtNum(Math.round(p.pagado||0)) + '</td>' +
            '<td style="text-align:right;font-weight:700;">$' + fmtNum(Math.round(p.saldo||0)) + '</td>' +
            '<td><span class="badge ' + ec + '">' + _esc(p.estado_pago||'') + '</span></td>' +
            '<td>' + (p.dias_desde_pedido||0) + 'd</td></tr>';
        }).join('') + '</tbody></table>';
    }
  } catch(e) {
    document.getElementById('cart-detalle').innerHTML = '<div class="empty">Error: ' + e.message + '</div>';
  }
}

// Hook tab switcher para cargar al entrar
var _origEsw = esw;
esw = function(name) {
  _origEsw(name);
  if (name === 'inicio') cargarQA();
  if (name === 'cartera') cargarCartera();
};

// Cargar quick actions al entrar a la página (tab inicio es default)
cargarQA();
</script>
</body>
</html>
"""
