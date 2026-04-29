# Auto-extraído de index.py — Fase A refactor
GERENCIA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Gerencia — HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=cortex4">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#1C2B30;min-height:100vh;color:white;}
.topbar{background:rgba(0,0,0,0.3);padding:14px 28px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,0.1);}
.topbar-left{display:flex;align-items:center;gap:16px;}
.logo{font-size:0.95em;font-weight:900;letter-spacing:3px;color:white;}
.badge-ceo{background:rgba(43,122,120,0.5);color:#7ACFCC;padding:3px 12px;border-radius:20px;font-size:0.72em;font-weight:700;letter-spacing:1px;}
.topbar a{color:rgba(255,255,255,0.5);text-decoration:none;font-size:0.8em;padding:6px 14px;border:1px solid rgba(255,255,255,0.15);border-radius:6px;}
.topbar a:hover{color:white;border-color:rgba(255,255,255,0.4);}
.periodo-badge{background:rgba(43,122,120,0.3);padding:4px 14px;border-radius:20px;font-size:0.78em;color:#7ACFCC;}
.main{padding:28px;max-width:1300px;margin:0 auto;}
.section-title{font-size:0.72em;text-transform:uppercase;letter-spacing:2px;color:rgba(255,255,255,0.4);margin-bottom:14px;margin-top:28px;}
.section-title:first-child{margin-top:0;}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:8px;}
.kpi{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:20px 22px;position:relative;overflow:hidden;transition:all 0.2s;}
.kpi:hover{background:rgba(255,255,255,0.08);transform:translateY(-2px);}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--ac,#2B7A78);}
.kpi.rojo::before{background:#ef4444;}.kpi.amarillo::before{background:#f59e0b;}.kpi.verde::before{background:#10b981;}
.kpi-val{font-size:2.2em;font-weight:900;line-height:1;color:white;}
.kpi-val.rojo{color:#fca5a5;}.kpi-val.amarillo{color:#fcd34d;}.kpi-val.verde{color:#6ee7b7;}
.kpi-lbl{font-size:0.72em;color:rgba(255,255,255,0.45);text-transform:uppercase;letter-spacing:1px;margin-top:8px;}
.kpi-sub{font-size:0.8em;color:rgba(255,255,255,0.3);margin-top:4px;}
.sem{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle;}
.sem.verde{background:#10b981;box-shadow:0 0 8px #10b981;}.sem.amarillo{background:#f59e0b;box-shadow:0 0 8px #f59e0b;}.sem.rojo{background:#ef4444;box-shadow:0 0 8px #ef4444;}
.alertas-panel{background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:12px;padding:20px;margin-bottom:28px;display:none;}
.alertas-panel.visible{display:block;}
.alerta-item{display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid rgba(239,68,68,0.15);}
.alerta-item:last-child{border-bottom:none;}
.alerta-icon{font-size:1.2em;margin-top:1px;}
.alerta-texto{font-size:0.88em;color:rgba(255,255,255,0.8);line-height:1.5;}
.two-cols{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px;}
.panel{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:22px;}
.panel-title{font-size:0.82em;font-weight:700;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:16px;display:flex;align-items:center;gap:8px;}
.data-row{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid rgba(255,255,255,0.06);}
.data-row:last-child{border-bottom:none;}
.data-lbl{font-size:0.85em;color:rgba(255,255,255,0.5);}
.data-val{font-size:0.92em;font-weight:700;color:white;}
.data-val.rojo{color:#fca5a5;}.data-val.amarillo{color:#fcd34d;}.data-val.verde{color:#6ee7b7;}
.input-panel{background:rgba(43,122,120,0.1);border:1px solid rgba(43,122,120,0.3);border-radius:12px;padding:22px;margin-top:20px;}
.input-panel-title{font-size:0.85em;font-weight:700;color:#7ACFCC;margin-bottom:16px;display:flex;align-items:center;gap:8px;}
.inp-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:14px;}
.inp-group label{display:block;font-size:0.72em;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:5px;}
.inp-group input{width:100%;padding:9px 12px;background:rgba(255,255,255,0.08);border:1.5px solid rgba(255,255,255,0.15);border-radius:7px;color:white;font-size:0.9em;transition:border 0.2s;}
.inp-group input:focus{outline:none;border-color:#2B7A78;background:rgba(255,255,255,0.12);}
.inp-group input::placeholder{color:rgba(255,255,255,0.25);}
.btn-save{background:#2B7A78;color:white;border:none;padding:10px 24px;border-radius:8px;font-size:0.88em;font-weight:700;cursor:pointer;transition:all 0.2s;}
.btn-save:hover{background:#1d5c5a;transform:translateY(-1px);}
.msg-ok-dark{background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);color:#6ee7b7;padding:9px 14px;border-radius:8px;font-size:0.85em;margin-top:10px;}
.msg-err-dark{background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#fca5a5;padding:9px 14px;border-radius:8px;font-size:0.85em;margin-top:10px;}
.finanzas-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:8px;}
.fin-card{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:16px 18px;text-align:center;}
.fin-val{font-size:1.6em;font-weight:900;color:#7ACFCC;}
.fin-lbl{font-size:0.72em;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:1px;margin-top:5px;}
.refresh-btn{background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:6px 14px;border-radius:6px;font-size:0.8em;cursor:pointer;transition:all 0.2s;}
.refresh-btn:hover{background:rgba(255,255,255,0.15);color:white;}
.ultima-act{font-size:0.72em;color:rgba(255,255,255,0.25);margin-left:10px;}
.prog-bar-wrap{background:rgba(255,255,255,0.08);border-radius:20px;height:10px;overflow:hidden;margin:6px 0 3px;}
.prog-bar{height:100%;border-radius:20px;transition:width 0.8s ease;background:linear-gradient(90deg,#2B7A78,#7ACFCC);}
.prog-bar.danger{background:linear-gradient(90deg,#ef4444,#f87171);}
.prog-bar.warn{background:linear-gradient(90deg,#f59e0b,#fcd34d);}
.churn-item{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);}
.churn-item:last-child{border-bottom:none;}
.badge-crit{background:rgba(239,68,68,0.2);color:#fca5a5;padding:2px 8px;border-radius:10px;font-size:0.75em;font-weight:700;}
.badge-atenc{background:rgba(245,158,11,0.2);color:#fcd34d;padding:2px 8px;border-radius:10px;font-size:0.75em;font-weight:700;}
</style>
</head>
<body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
  <div>
    <div class="cx-mod-header__title">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M3 9l9-6 9 6"/><path d="M5 21V11M19 21V11M9 21v-8M15 21v-8M2 21h20"/></svg>
      Panel Gerencial
    </div>
    <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; metas YTD · estrategia · KPIs ejecutivos &middot; <span class="periodo-badge" id="periodo-label" style="color:#a8a29e">Cargando...</span></div>
  </div>
  <div class="cx-mod-header__nav">
    <button class="cx-btn cx-btn-ghost cx-btn-sm" onclick="loadKPIs()">&#x21bb; Actualizar</button>
    <span class="ultima-act" id="ultima-actualizacion" style="font-size:11px;color:#a8a29e;"></span>
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">&larr; Módulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
    </button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>

<div class="main">

  <!-- ALERTAS CRÍTICAS -->
  <div class="alertas-panel" id="alertas-panel">
    <div style="font-size:0.82em;font-weight:700;color:#fca5a5;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">⚠ Alertas que requieren acción</div>
    <div id="alertas-list"></div>
  </div>

  <!-- FINANCIERO (inputs manuales) -->
  <div class="section-title">💰 Financiero del mes</div>
  <div class="finanzas-grid" style="grid-template-columns:repeat(auto-fit,minmax(160px,1fr));">
    <div class="fin-card"><div class="fin-val" id="fin-caja">—</div><div class="fin-lbl">Saldo de caja</div></div>
    <div class="fin-card"><div class="fin-val" id="fin-animus">—</div><div class="fin-lbl">Ingresos ÁNIMUS</div></div>
    <div class="fin-card"><div class="fin-val" id="fin-maquila">—</div><div class="fin-lbl">Ingresos Maquila</div></div>
    <div class="fin-card"><div class="fin-val" id="fin-nomina" style="color:#fcd34d;">—</div><div class="fin-lbl">Nomina mes</div><div style="font-size:0.65em;color:rgba(255,255,255,0.3);margin-top:3px;" id="fin-nomina-emp"></div></div>
  </div>

  <!-- ESPAGIRIA -->
  <div class="section-title">🏭 Espagiria Laboratorios</div>
  <div class="kpi-grid">
    <div class="kpi" id="kpi-mps-bajos">
      <div class="kpi-val" id="val-mps-bajos">—</div>
      <div class="kpi-lbl">MPs bajo mínimo</div>
      <div class="kpi-sub" id="sub-deficit">—</div>
    </div>
    <div class="kpi" id="kpi-vencen30">
      <div class="kpi-val" id="val-vencen30">—</div>
      <div class="kpi-lbl">Lotes vencen en 30 días</div>
      <div class="kpi-sub" id="sub-vencen60">—</div>
    </div>
    <div class="kpi" id="kpi-produccion">
      <div class="kpi-val" id="val-lotes-mes">—</div>
      <div class="kpi-lbl">Lotes producción mes</div>
      <div class="kpi-sub" id="sub-kg-mes">—</div>
    </div>
    <div class="kpi" id="kpi-ocs">
      <div class="kpi-val" id="val-ocs">—</div>
      <div class="kpi-lbl">OCs pendientes aprobación</div>
      <div class="kpi-sub" id="sub-ocs-val">—</div>
    </div>
    <div class="kpi" id="kpi-sol-pend" style="cursor:pointer;" onclick="location.href='/compras'">
      <div class="kpi-val" id="val-sol-pend">—</div>
      <div class="kpi-lbl">Solicitudes a Compras</div>
      <div class="kpi-sub" style="font-size:0.78em;opacity:0.6;">Pendientes de aprobar → /compras</div>
    </div>
    <div class="kpi" id="kpi-mee-bajos">
      <div class="kpi-val" id="val-mee-bajos">—</div>
      <div class="kpi-lbl">MEE bajo mínimo</div>
      <div class="kpi-sub" id="sub-mee">Envases y empaques</div>
    </div>
  </div>

  <!-- ÁNIMUS -->
  <div class="section-title">✨ ÁNIMUS Lab</div>
  <div class="kpi-grid">
    <div class="kpi verde">
      <div class="kpi-val verde" id="val-uds-pt">—</div>
      <div class="kpi-lbl">Unidades PT disponibles</div>
      <div class="kpi-sub" id="sub-skus-pt">—</div>
    </div>
    <div class="kpi" id="kpi-pedidos-act">
      <div class="kpi-val" id="val-pedidos-act">—</div>
      <div class="kpi-lbl">Pedidos activos</div>
      <div class="kpi-sub" id="sub-pedidos-val">—</div>
    </div>
    <div class="kpi" id="kpi-fm">
      <div class="kpi-val" id="val-fm-dias">—</div>
      <div class="kpi-lbl">Días desde último pedido FM</div>
      <div class="kpi-sub">Ciclo promedio: ~62 días</div>
    </div>
  </div>

  <!-- DETALLE DOS COLUMNAS -->
  <div class="two-cols">
    <div class="panel">
      <div class="panel-title"><span class="sem verde" id="sem-inv"></span>Planta Espagiria</div>
      <div id="detalle-inventario"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title"><span class="sem verde" id="sem-animus"></span>ÁNIMUS Lab</div>
      <div id="detalle-animus"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
  </div>

  <!-- INPUT MANUAL MENSUAL -->
  <div class="input-panel">
    <div class="input-panel-title">📝 Input manual mensual <span style="font-weight:400;color:rgba(255,255,255,0.3);font-size:0.85em;">— actualizar en 5 minutos al inicio de cada mes</span></div>
    <div class="inp-grid">
      <div class="inp-group"><label>Saldo de caja ($COP)</label><input type="number" id="inp-caja" placeholder="354800000"></div>
      <div class="inp-group"><label>Ingresos ÁNIMUS mes ($COP)</label><input type="number" id="inp-animus" placeholder="189000000"></div>
      <div class="inp-group"><label>Ingresos Maquila mes ($COP)</label><input type="number" id="inp-maquila" placeholder="30000000"></div>
      <div class="inp-group"><label>Nómina total mes ($COP)</label><input type="number" id="inp-nomina" placeholder="16100000"></div>
    </div>
    <div class="inp-group" style="margin-bottom:14px;"><label>Notas del período</label><input type="text" id="inp-notas" placeholder="Ej: Mes de lanzamiento NIAC, pago nómina atrasado..."></div>
    <button class="btn-save" onclick="guardarInputs()">💾 Guardar inputs del mes</button>
    <div id="inp-msg"></div>
  </div>

  <!-- FLUJO OPERACIONAL -->
  <div class="section-title" style="margin-top:32px;">🔄 Flujo Operacional — Vista Ejecutiva</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-bottom:20px;">
    <div class="panel">
      <div class="panel-title">📦 Compras pendientes de recibir
        <a href="/recepcion" style="margin-left:auto;font-size:0.75em;color:#7ACFCC;text-decoration:none;font-weight:600;">→ Recepción</a>
      </div>
      <div id="g-ocs-transito"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">⚠ Recepciones con discrepancias</div>
      <div id="g-disc"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">🚚 Pedidos listos para despachar
        <a href="/hub-salida" style="margin-left:auto;font-size:0.75em;color:#7ACFCC;text-decoration:none;font-weight:600;">→ Hub Salida</a>
      </div>
      <div id="g-pedidos-listos"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">✅ Despachos recientes</div>
      <div id="g-despachos"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
  </div>

  <!-- QUICK NAV -->
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:28px;">
    <a href="/hub" style="background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.35);color:#fff;padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:700;">🏠 Panel Central</a>
    <a href="/recepcion" style="background:rgba(43,122,120,0.2);border:1px solid rgba(43,122,120,0.4);color:#7ACFCC;padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">📥 Recepción de Mercancía</a>
    <a href="/hub-salida" style="background:rgba(74,103,65,0.2);border:1px solid rgba(74,103,65,0.4);color:#8BC98A;padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">📤 Hub de Salida</a>
    <a href="/compras" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">🛒 Módulo Compras</a>
    <a href="/clientes" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">👤 Módulo Clientes</a>
    <a href="/financiero" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">💰 Financiero</a>
    <a href="/calidad" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">🔬 Calidad</a>
    <a href="/rrhh" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">👥 RRHH</a>
    <a href="/tecnica" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">🔧 Técnica</a>
  </div>



  <!-- INDICADORES EJECUTIVOS — solo metas/estrategicos. Caja, AR/AP, P&L viven en /financiero -->
  <div class="section-title" style="margin-top:32px;">📊 Metas estratégicas <a href="/financiero" style="font-size:0.65em;font-weight:600;color:#7ACFCC;text-decoration:none;margin-left:12px;">→ Para caja, AR/AP, P&L: ir a Financiero</a> · <a href="/hoy" style="font-size:0.65em;font-weight:600;color:#fbbf24;text-decoration:none;">→ Para hoy: ir a HOY</a></div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:20px;">
    <div class="panel">
      <div class="panel-title">🏭 Pipeline Maquila activo</div>
      <div id="gx-maquila"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">📊 Meta Maquila 2026</div>
      <div id="gx-maquila-target"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin-bottom:12px;">
    <div class="panel">
      <div class="panel-title">💄 Inversion Influencers YTD</div>
      <div id="gx-influencer"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">📦 Valor Inventario MP (COP)</div>
      <div id="gx-inv-cop"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">&#128276; Alertas recompra clientes</div>
      <div id="gx-churn"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin-bottom:28px;">
    <div class="panel">
      <div class="panel-title">⚠ Stock Critico — MPs bajo minimo</div>
      <div id="gx-stock"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">✅ SGSST — Proximos vencimientos</div>
      <div id="gx-sgsst"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">🔒 Accesos recientes</div>
      <div id="gx-sec"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
  </div>


  <!-- Capa 4: Feed Aliados → Gerencia -->
  <div class="section-title" style="margin-top:32px;">🤝 Canal Aliados — Vista Gerencia</div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:14px;">

    <!-- Mix de canales -->
    <div class="panel">
      <div class="panel-title">📊 Mix canales · este mes</div>
      <div id="g4-mix">
        <div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div>
      </div>
    </div>

    <!-- Concentración de riesgo -->
    <div class="panel">
      <div class="panel-title">⚠️ Concentración de riesgo</div>
      <div id="g4-riesgo">
        <div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div>
      </div>
    </div>

    <!-- Estado del canal -->
    <div class="panel">
      <div class="panel-title">🔋 Estado del canal</div>
      <div id="g4-estado">
        <div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div>
      </div>
    </div>
  </div>

  <!-- Tendencia ticket por mes -->
  <div class="panel" style="margin-bottom:28px;">
    <div class="panel-title">📈 Tendencia ticket promedio — canal aliados (6 meses)</div>
    <div id="g4-trend" style="display:flex;gap:8px;align-items:flex-end;padding:8px 0;min-height:80px;">
      <div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div>
    </div>
  </div>

</div><!-- /main -->

<script>
function fmt(n,prefix){if(n==null||n===undefined)return '—';var v=Math.abs(parseFloat(n));var s=v>=1000000?(v/1000000).toFixed(1)+'M':(v>=1000?(v/1000).toFixed(0)+'K':v.toLocaleString('es-CO'));return (prefix||'$')+s;}
function fmtN(n){return n!=null?parseFloat(n).toLocaleString('es-CO'):'—';}
function setSemaforo(id,color){var el=document.getElementById(id);if(el){el.className='sem '+color;}}
function setKPIColor(kpiId,valId,color){
  var k=document.getElementById(kpiId),v=document.getElementById(valId);
  if(k) k.className='kpi '+(color||'');
  if(v) v.className='kpi-val '+(color||'');
}

async function loadKPIs(){
  try{
    var d=await fetch('/api/gerencia/kpis').then(function(r){return r.json();});
    if(d.error){document.querySelector('.main').innerHTML='<div style="color:#fca5a5;padding:40px;text-align:center;">'+d.error+'</div>';return;}

    var e=d.espagiria||{}; var a=d.animus||{}; var f=d.inputs_manuales||{}; var sem=d.semaforos||{};

    // Periodo
    document.getElementById('periodo-label').textContent=d.periodo||'';
    document.getElementById('ultima-actualizacion').textContent='Actualizado: '+new Date().toLocaleTimeString('es-CO');

    // Financiero
    document.getElementById('fin-caja').textContent=fmt(f.saldo_caja);
    document.getElementById('fin-animus').textContent=fmt(f.ingresos_animus);
    document.getElementById('fin-maquila').textContent=fmt(f.ingresos_maquila);
    var nom=d.nomina||{};
    document.getElementById('fin-nomina').textContent=nom.total&&nom.total>0?fmt(nom.total):'—';
    document.getElementById('fin-nomina-emp').textContent=nom.empleados?nom.empleados+' activos':'';

    // Espagiria KPIs
    var mpsBajos=e.mps_bajo_minimo||0;
    document.getElementById('val-mps-bajos').textContent=mpsBajos;
    document.getElementById('sub-deficit').textContent='Déficit: '+Math.round((e.deficit_total_kg||0)*1000).toLocaleString('es-CO')+' g';
    setKPIColor('kpi-mps-bajos','val-mps-bajos',mpsBajos>5?'rojo':(mpsBajos>0?'amarillo':'verde'));

    var meeBajos=e.mee_bajo_minimo||0;
    document.getElementById('val-mee-bajos').textContent=meeBajos;
    setKPIColor('kpi-mee-bajos','val-mee-bajos',meeBajos>3?'rojo':(meeBajos>0?'amarillo':'verde'));

    var v30=e.lotes_vence_30||0;
    document.getElementById('val-vencen30').textContent=v30;
    document.getElementById('sub-vencen60').textContent='En 60 dias: '+(e.lotes_vence_60||0)+' lotes';
    setKPIColor('kpi-vencen30','val-vencen30',v30>0?'rojo':'verde');

    document.getElementById('val-lotes-mes').textContent=e.prod_mes||0;
    document.getElementById('sub-kg-mes').textContent=parseFloat(e.kg_mes||0).toFixed(1)+' kg producidos';

    var ocs=e.ocs_pendientes||0;
    document.getElementById('val-ocs').textContent=ocs;
    document.getElementById('sub-ocs-val').textContent='';
    setKPIColor('kpi-ocs','val-ocs',ocs>3?'amarillo':'verde');
    var solPend=e.sol_pendientes||0;
    document.getElementById('val-sol-pend').textContent=solPend;
    setKPIColor('kpi-sol-pend','val-sol-pend',solPend>0?'amarillo':'verde');

    // ÁNIMUS KPIs
    document.getElementById('val-uds-pt').textContent=fmtN(a.uds_pt||0);
    document.getElementById('sub-skus-pt').textContent=(a.skus_stock||0)+' SKUs con stock';

    var pedAct=a.pedidos_activos||0;
    document.getElementById('val-pedidos-act').textContent=pedAct;
    document.getElementById('sub-pedidos-val').textContent='Valor: '+fmt(a.valor_pedidos_activos||0);

    var diasFM=a.dias_desde_fm;
    var diasFMEl=document.getElementById('val-fm-dias');
    diasFMEl.textContent=diasFM!=null?diasFM+' días':'Sin pedidos';
    setKPIColor('kpi-fm','val-fm-dias',diasFM>62?'amarillo':'verde');

    // Semáforos
    setSemaforo('sem-inv',sem.inventario||'verde');
    setSemaforo('sem-animus',sem.fm||'verde');

    // Detalle inventario
    var di='';
    di+='<div class="data-row"><span class="data-lbl">MPs bajo mínimo</span><span class="data-val '+(mpsBajos>0?'rojo':'verde')+'">'+mpsBajos+'</span></div>';
    di+='<div class="data-row"><span class="data-lbl">MEE bajo mínimo</span><span class="data-val '+(meeBajos>0?'amarillo':'verde')+'">'+meeBajos+'</span></div>';
    di+='<div class="data-row"><span class="data-lbl">Déficit total</span><span class="data-val '+(e.deficit_total_kg>0?'amarillo':'verde')+'">'+((e.deficit_total_kg||0).toFixed(1))+' kg</span></div>';
    di+='<div class="data-row"><span class="data-lbl">Lotes vencen 30d</span><span class="data-val '+(v30>0?'rojo':'verde')+'">'+v30+'</span></div>';
    di+='<div class="data-row"><span class="data-lbl">Lotes vencen 60d</span><span class="data-val '+(e.lotes_vence_60>0?'amarillo':'verde')+'">'+(e.lotes_vence_60||0)+'</span></div>';
    di+='<div class="data-row"><span class="data-lbl">Producción este mes</span><span class="data-val">'+( e.prod_mes||0)+' lotes / '+parseFloat(e.kg_mes||0).toFixed(1)+' kg</span></div>';
    di+='<div class="data-row"><span class="data-lbl">OCs pendientes</span><span class="data-val '+(ocs>0?'amarillo':'verde')+'">'+ocs+' ('+fmt(e.valor_ocs_pendientes||0)+')</span></div>';
    di+='<div class="data-row"><span class="data-lbl">Solicitudes a Compras</span><span class="data-val '+(solPend>0?'amarillo':'verde')+'">'+solPend+' <a href="/compras" style="color:rgba(255,255,255,0.5);font-size:0.82em;">→ ver</a></span></div>';
    document.getElementById('detalle-inventario').innerHTML=di;

    // Detalle ÁNIMUS
    var da='';
    da+='<div class="data-row"><span class="data-lbl">Unidades PT disponibles</span><span class="data-val verde">'+fmtN(a.uds_pt||0)+'</span></div>';
    da+='<div class="data-row"><span class="data-lbl">SKUs con stock</span><span class="data-val">'+(a.skus_stock||0)+'</span></div>';
    da+='<div class="data-row"><span class="data-lbl">Pedidos activos</span><span class="data-val">'+(a.pedidos_activos||0)+' ('+fmt(a.valor_pedidos_activos||0)+')</span></div>';
    da+='<div class="data-row"><span class="data-lbl">Último pedido FM</span><span class="data-val">'+(a.ultimo_pedido_fm||'Sin datos')+'</span></div>';
    da+='<div class="data-row"><span class="data-lbl">Días desde pedido FM</span><span class="data-val '+(diasFM>55?'amarillo':'verde')+'">'+(diasFM!=null?diasFM+' días':'—')+'</span></div>';
    document.getElementById('detalle-animus').innerHTML=da;

    // Alertas
    var alertas=[];
    if(mpsBajos>0) alertas.push({icon:'🔴',txt:'<strong>'+mpsBajos+' MPs bajo mínimo</strong> — Déficit total: '+((e.deficit_total_kg||0).toFixed(1))+' kg. Generar OC desde Compras.'});
    if(meeBajos>0) alertas.push({icon:'🟡',txt:'<strong>'+meeBajos+' materiales de envase/empaque bajo mínimo</strong> — Revisar stock MEE en módulo Compras.'});
    if(v30>0) alertas.push({icon:'🔴',txt:'<strong>'+v30+' lotes vencen en los próximos 30 días</strong> — Revisar y usar en próximas producciones (FEFO).'});
    if(ocs>3) alertas.push({icon:'🟡',txt:'<strong>'+ocs+' órdenes de compra</strong> esperando aprobación — Valor total: '+fmt(e.valor_ocs_pendientes||0)+'.'});
    if(solPend>0) alertas.push({icon:'🟡',txt:'<strong>'+solPend+' solicitud'+(solPend>1?'es':'')+' de compra pendiente'+(solPend>1?'s':'')+' de aprobar</strong> — Catalina debe revisar en <a href="/compras" style="color:rgba(255,255,255,0.75);">Módulo Compras</a> para convertirlas en órdenes de compra.'});
    if(diasFM!=null&&diasFM>55) alertas.push({icon:'🟡',txt:'<strong>Fernando Mesa: '+diasFM+' días sin pedir</strong> — Ciclo normal ~62 días. Próximo pedido inminente.'});
    var nomVal=(nom&&nom.total)||0; if(f.saldo_caja>0&&nomVal>0&&f.saldo_caja<nomVal*2) alertas.push({icon:'&#128308;',txt:'<strong>Caja baja:</strong> Saldo '+fmt(f.saldo_caja)+' cubre menos de 2 nominas (nomina: '+fmt(nomVal)+')'});

    var panel=document.getElementById('alertas-panel');
    if(alertas.length>0){
      panel.classList.add('visible');
      document.getElementById('alertas-list').innerHTML=alertas.map(function(a){
        return '<div class="alerta-item"><span class="alerta-icon">'+a.icon+'</span><span class="alerta-texto">'+a.txt+'</span></div>';
      }).join('');
    } else {
      panel.classList.remove('visible');
    }

    // Pre-cargar inputs en el formulario
    if(f.saldo_caja) document.getElementById('inp-caja').value=f.saldo_caja;
    if(f.ingresos_animus) document.getElementById('inp-animus').value=f.ingresos_animus;
    if(f.ingresos_maquila) document.getElementById('inp-maquila').value=f.ingresos_maquila;
    if(nom.total) document.getElementById('inp-nomina').value=nom.total;
    if(f.notas) document.getElementById('inp-notas').value=f.notas;

  }catch(e){console.error(e);}
}

async function guardarInputs(){
  var data={
    saldo_caja:parseFloat(document.getElementById('inp-caja').value)||0,
    ingresos_animus:parseFloat(document.getElementById('inp-animus').value)||0,
    ingresos_maquila:parseFloat(document.getElementById('inp-maquila').value)||0,
    nomina_total:parseFloat(document.getElementById('inp-nomina').value)||0,
    notas:document.getElementById('inp-notas').value
  };
  try{
    var r=await fetch('/api/gerencia/input-manual',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    document.getElementById('inp-msg').innerHTML=r.ok?'<div class="msg-ok-dark">'+res.message+'</div>':'<div class="msg-err-dark">'+(res.error||'Error')+'</div>';
    if(r.ok) setTimeout(loadKPIs,500);
  }catch(e){document.getElementById('inp-msg').innerHTML='<div class="msg-err-dark">Error</div>';}
}

async function loadFlujoOperacional() {
  try {
    var d = await fetch('/api/gerencia/flujo-operacional').then(function(r){ return r.json(); });
    var nil = '<div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Sin datos</div>';

    // OCs en tránsito
    var elt = document.getElementById('g-ocs-transito');
    if (elt) {
      var ocs = d.ocs_transito || [];
      if (!ocs.length) { elt.innerHTML = '<div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Sin OCs pendientes ✓</div>'; }
      else {
        elt.innerHTML = ocs.slice(0,4).map(function(o) {
          return '<div class="data-row"><span class="data-lbl">' + o.numero_oc + ' — ' + (o.proveedor||'') + '</span>'
            + '<span class="data-val amarillo">' + (o.dias_transito||0) + 'd</span></div>';
        }).join('') + (ocs.length > 4 ? '<div style="color:rgba(255,255,255,0.3);font-size:0.8em;padding:6px 0;">+' + (ocs.length-4) + ' más</div>' : '');
      }
    }

    // Discrepancias
    var eld = document.getElementById('g-disc');
    if (eld) {
      var discs = d.recepciones_disc || [];
      if (!discs.length) { eld.innerHTML = '<div style="color:#6ee7b7;font-size:0.85em;">Sin discrepancias ✓</div>'; }
      else {
        eld.innerHTML = discs.slice(0,4).map(function(r) {
          return '<div class="data-row"><span class="data-lbl">' + r.numero_oc + '</span>'
            + '<span class="data-val rojo">DISC</span></div>';
        }).join('');
      }
    }

    // Pedidos listos
    var elp = document.getElementById('g-pedidos-listos');
    if (elp) {
      var peds = d.pedidos_listos || [];
      if (!peds.length) { elp.innerHTML = '<div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Sin pedidos pendientes</div>'; }
      else {
        elp.innerHTML = peds.slice(0,4).map(function(p) {
          return '<div class="data-row"><span class="data-lbl">' + p.numero + ' — ' + (p.cliente||'') + '</span>'
            + '<span class="data-val amarillo">$' + Number(p.valor_total||0).toLocaleString() + '</span></div>';
        }).join('') + (peds.length > 4 ? '<div style="color:rgba(255,255,255,0.3);font-size:0.8em;padding:6px 0;">+' + (peds.length-4) + ' más</div>' : '');
      }
    }

    // Despachos recientes
    var elsp = document.getElementById('g-despachos');
    if (elsp) {
      var desps = d.despachos_recientes || [];
      if (!desps.length) { elsp.innerHTML = '<div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Sin despachos recientes</div>'; }
      else {
        elsp.innerHTML = desps.slice(0,4).map(function(ds) {
          return '<div class="data-row"><span class="data-lbl">' + ds.numero + ' — ' + (ds.cliente||'') + '</span>'
            + '<span class="data-val verde">' + (ds.fecha||'').slice(0,10) + '</span></div>';
        }).join('');
      }
    }
  } catch(e) { console.error('loadFlujoOperacional:', e); }
}

// Cargar al iniciar
loadKPIs();
loadFlujoOperacional();
// Auto-refresh cada 5 minutos
setInterval(loadKPIs, 300000);
setInterval(loadFlujoOperacional, 300000);

async function loadGerenciaExtra() {
  try {
    var d = await fetch('/api/gerencia/dashboard-extra').then(function(r){ return r.json(); });
    var nil = '<div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Sin datos</div>';
    var fmtV = function(n){ return n==null?'—':'$'+Number(n).toLocaleString('es-CO',{maximumFractionDigits:0}); };
    var clr = function(v,warn,danger){ return v>=danger?'rojo':(v>=warn?'amarillo':'verde'); };

    // Ingresos del mes
    var ig = d.ingresos_mes||{};
    var elI = document.getElementById('gx-ingresos');
    if(elI){
      var shpMom = ig.shopify>0 ? ' <span style="font-size:10px;color:#34d399;">Shopify ✓</span>' : '';
      elI.innerHTML =
        '<div class="data-row"><span class="data-lbl">Aliados B2B</span><span class="data-val verde">'+fmtV(ig.aliados||ig.animus)+'</span></div>'
        +'<div class="data-row"><span class="data-lbl">Shopify DTC'+shpMom+'</span><span class="data-val verde">'+fmtV(ig.shopify)+'</span></div>'
        +'<div class="data-row" style="border-top:1px solid rgba(255,255,255,0.08);margin-top:3px;padding-top:3px;"><span class="data-lbl">ÁNIMUS total</span><span class="data-val verde">'+fmtV(ig.animus_total)+'</span></div>'
        +'<div class="data-row"><span class="data-lbl">Maquila</span><span class="data-val verde">'+fmtV(ig.maquila)+'</span></div>'
        +'<div class="data-row" style="border-top:1px solid rgba(255,255,255,0.1);margin-top:4px;padding-top:4px;"><span class="data-lbl"><strong>Grand Total</strong></span><span class="data-val verde"><strong>'+fmtV(ig.total)+'</strong></span></div>';
    }

    // AR
    var ar = d.ar||{};
    var elAR = document.getElementById('gx-ar');
    var arClr = ar.total>0?'amarillo':'verde';
    if(elAR) elAR.innerHTML =
      '<div class="data-row"><span class="data-lbl">Total</span><span class="data-val '+arClr+'">'+fmtV(ar.total)+'</span></div>'
      +'<div class="data-row"><span class="data-lbl"># Pedidos</span><span class="data-val">'+( ar.count||0)+'</span></div>'
      +'<div class="data-row"><span class="data-lbl">> 30 dias</span><span class="data-val '+(ar.vencido_30>0?'rojo':'verde')+'">'+fmtV(ar.vencido_30)+'</span></div>'
      +'<div class="data-row"><span class="data-lbl">> 60 dias</span><span class="data-val '+(ar.vencido_60>0?'rojo':'verde')+'">'+fmtV(ar.vencido_60)+'</span></div>';

    // AP
    var ap = d.ap||{};
    var elAP = document.getElementById('gx-ap');
    var apClr = ap.total>500000?'amarillo':'verde';
    if(elAP) elAP.innerHTML =
      '<div class="data-row"><span class="data-lbl">Total</span><span class="data-val '+apClr+'">'+fmtV(ap.total)+'</span></div>'
      +'<div class="data-row"><span class="data-lbl"># OCs</span><span class="data-val">'+( ap.count||0)+'</span></div>'
      +'<div class="data-row"><span class="data-lbl">> 30 dias</span><span class="data-val '+(ap.vencido_30>0?'rojo':'verde')+'">'+fmtV(ap.vencido_30)+'</span></div>'
      +'<div class="data-row"><span class="data-lbl">> 60 dias</span><span class="data-val '+(ap.vencido_60>0?'rojo':'verde')+'">'+fmtV(ap.vencido_60)+'</span></div>';

    // Maquila pipeline
    var mqs = d.maquila_pipeline||[];
    var elM = document.getElementById('gx-maquila');
    if(elM){
      if(!mqs.length){ elM.innerHTML='<div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Sin ordenes activas</div>'; }
      else{
        elM.innerHTML = mqs.slice(0,4).map(function(m){
          return '<div class="data-row"><span class="data-lbl">'+m.numero+' — '+(m.cliente_nombre||'')+'</span><span class="data-val amarillo">'+fmtV(m.precio_lote)+'</span></div>';
        }).join('');
        if(mqs.length>4) elM.innerHTML += '<div style="color:rgba(255,255,255,0.3);font-size:0.8em;padding:4px 0;">+'+(mqs.length-4)+' mas</div>';
      }
    }

    // Stock critico
    var sc = d.stock_critico||[];
    var elSC = document.getElementById('gx-stock');
    if(elSC){
      if(!sc.length){ elSC.innerHTML='<div style="color:#6ee7b7;font-size:0.85em;">Stock OK en todos los MPs</div>'; }
      else{
        elSC.innerHTML = sc.slice(0,6).map(function(mp){
          var pct = mp.stock_minimo>0?Math.round(mp.stock_actual/mp.stock_minimo*100):0;
          return '<div class="data-row"><span class="data-lbl">'+mp.codigo_mp+' '+mp.nombre+'</span>'
            +'<span class="data-val rojo">'+mp.stock_actual.toFixed(0)+'/'+mp.stock_minimo.toFixed(0)+' g ('+pct+'%)</span></div>';
        }).join('');
        if(sc.length>6) elSC.innerHTML += '<div style="color:rgba(255,255,255,0.3);font-size:0.8em;">+'+(sc.length-6)+' MPs mas</div>';
      }
    }

    // SGSST
    var ss = d.sgsst_proximos||[];
    var elSS = document.getElementById('gx-sgsst');
    if(elSS){
      if(!ss.length){ elSS.innerHTML='<div style="color:#6ee7b7;font-size:0.85em;">Sin vencimientos proximos</div>'; }
      else{
        elSS.innerHTML = ss.slice(0,5).map(function(s){
          var c=s.dias_restantes<=15?'rojo':(s.dias_restantes<=30?'amarillo':'verde');
          return '<div class="data-row"><span class="data-lbl">'+s.descripcion.slice(0,30)+'</span><span class="data-val '+c+'">'+s.dias_restantes+'d</span></div>';
        }).join('');
      }
    }

    // Security
    var sec = d.security||{};
    var elSec = document.getElementById('gx-sec');
    if(elSec){
      var secH = '<div class="data-row"><span class="data-lbl">Logins exitosos (7d)</span><span class="data-val verde">'+(sec.success_7d||0)+'</span></div>';
      secH += '<div class="data-row"><span class="data-lbl">Intentos fallidos (7d)</span><span class="data-val '+(sec.fail_7d>5?'rojo':(sec.fail_7d>0?'amarillo':'verde'))+'">'+( sec.fail_7d||0)+'</span></div>';
      if(sec.last_event) secH += '<div class="data-row"><span class="data-lbl">Ultimo evento</span><span class="data-val" style="font-size:0.75em;">'+(sec.last_event||'').slice(0,16)+'</span></div>';
      elSec.innerHTML = secH;
    }


    // Maquila target
    var mt=d.maquila_target||{}; var elMT=document.getElementById('gx-maquila-target');
    if(elMT){
      var pctE=Math.min(mt.pct_espagiria||0,100); var pctH=Math.min(mt.pct_hha||0,100);
      elMT.innerHTML='<div class="data-row"><span class="data-lbl">Meta Espagiria $30M</span><span class="data-val '+(pctE>=80?'verde':(pctE>=40?'amarillo':'rojo'))+'">'+pctE+'%</span></div>'
        +'<div class="prog-bar-wrap"><div class="prog-bar '+(pctE<40?'danger':(pctE<80?'warn':''))+'" style="width:'+pctE+'%"></div></div>'
        +'<div class="data-row" style="margin-top:8px;"><span class="data-lbl">Meta HHA $76M</span><span class="data-val '+(pctH>=80?'verde':(pctH>=40?'amarillo':'rojo'))+'">'+pctH+'%</span></div>'
        +'<div class="prog-bar-wrap"><div class="prog-bar '+(pctH<40?'danger':(pctH<80?'warn':''))+'" style="width:'+pctH+'%"></div></div>'
        +'<div style="font-size:0.75em;color:rgba(255,255,255,0.35);margin-top:6px;">YTD: '+fmtV(mt.ytd||0)+'</div>';
    }
    // Influencer spend
    var inf=d.influencer_spend||{}; var elInf=document.getElementById('gx-influencer');
    if(elInf){
      var infV=inf.ytd||0;
      elInf.innerHTML='<div class="data-row"><span class="data-lbl">Total YTD</span><span class="data-val '+(infV>5000000?'amarillo':'verde')+'">'+fmtV(infV)+'</span></div>'
        +'<div class="data-row"><span class="data-lbl">OCs generadas</span><span class="data-val">'+(inf.ocs||0)+'</span></div>'
        +'<div style="font-size:0.75em;color:rgba(255,255,255,0.3);margin-top:6px;">Categorias: Influencer + Marketing</div>';
    }
    // Inventory COP
    var invC=d.inventory_cop||0; var elIC=document.getElementById('gx-inv-cop');
    if(elIC){
      elIC.innerHTML='<div style="font-size:1.8em;font-weight:900;color:#7ACFCC;padding:8px 0 4px;">'+fmtV(invC)+'</div>'
        +'<div style="font-size:0.75em;color:rgba(255,255,255,0.35);">Precio promedio OC x lotes activos</div>';
    }
    // Churn alerts
    var churns=d.churn_alerts||[]; var elCh=document.getElementById('gx-churn');
    if(elCh){
      if(!churns.length){ elCh.innerHTML='<div style="color:#6ee7b7;font-size:0.85em;">Todos los clientes activos &#10003;</div>'; }
      else{
        elCh.innerHTML=churns.slice(0,5).map(function(ch){
          return '<div class="churn-item"><div><div style="font-size:0.85em;color:rgba(255,255,255,0.8);">'+(ch.nombre||'')+'</div>'
            +'<div style="font-size:0.72em;color:rgba(255,255,255,0.35);">Ultimo: '+(ch.ultimo_pedido||'—')+'</div></div>'
            +'<span class="'+(ch.nivel==='critico'?'badge-crit':'badge-atenc')+'">'+(ch.dias||0)+'d</span></div>';
        }).join('');
        if(churns.length>5) elCh.innerHTML+='<div style="font-size:0.75em;color:rgba(255,255,255,0.3);padding:4px 0;">+'+(churns.length-5)+' mas</div>';
      }
    }
  } catch(e){ console.error('loadGerenciaExtra:', e); }
}

loadGerenciaExtra();
setInterval(loadGerenciaExtra, 300000);
loadAliados4();
setInterval(loadAliados4, 300000);

async function loadAliados4() {
  try {
    var d = await fetch('/api/gerencia/aliados-feed').then(function(r){ return r.json(); });
    if(d.error){ console.error('aliados-feed:', d.error); return; }
    var fv = function(n){ if(n==null) return '—'; var v=Math.abs(n); return '$'+(v>=1000000?(v/1000000).toFixed(1)+'M':v>=1000?(v/1000).toFixed(0)+'K':v.toLocaleString('es-CO')); };

    // Mix canales
    var canal = d.canal || {};
    var g4mix = document.getElementById('g4-mix');
    if(g4mix){
      var momTxt = canal.mom_aliados>0 ? '▲'+canal.mom_aliados+'%' : canal.mom_aliados<0 ? '▼'+Math.abs(canal.mom_aliados)+'%' : '=0%';
      var momClr = canal.mom_aliados>0 ? 'verde' : canal.mom_aliados<0 ? 'rojo' : '';
      // Mini bar aliados vs shopify
      var pctA = canal.pct_ali_mes || 0;
      var pctS = canal.pct_shp_mes || 0;
      g4mix.innerHTML =
        '<div style="margin-bottom:8px;">'
        +'<div style="display:flex;height:10px;border-radius:5px;overflow:hidden;margin-bottom:6px;">'
        +'<div style="width:'+pctA+'%;background:#a78bfa;" title="Aliados '+pctA+'%"></div>'
        +'<div style="width:'+pctS+'%;background:#34d399;" title="Shopify '+pctS+'%"></div>'
        +'</div>'
        +'<div style="display:flex;justify-content:space-between;font-size:10px;">'
        +'<span style="color:#a78bfa;">■ Aliados '+pctA+'%</span>'
        +'<span style="color:#34d399;">■ Shopify '+pctS+'%</span>'
        +'</div>'
        +'</div>'
        +'<div class="data-row"><span class="data-lbl">Aliados</span><span class="data-val verde">'+fv(canal.aliados_mes)+'</span></div>'
        +'<div class="data-row"><span class="data-lbl">Shopify</span><span class="data-val verde">'+fv(canal.shopify_mes)+'</span></div>'
        +'<div class="data-row"><span class="data-lbl">MoM canal</span><span class="data-val '+momClr+'">'+momTxt+'</span></div>'
        +'<div class="data-row" style="border-top:1px solid rgba(255,255,255,0.1);margin-top:4px;padding-top:4px;"><span class="data-lbl">Total mes</span><span class="data-val verde"><strong>'+fv(canal.total_mes)+'</strong></span></div>';
    }

    // Concentración de riesgo
    var riesgo = d.riesgo || {};
    var g4riesgo = document.getElementById('g4-riesgo');
    if(g4riesgo){
      var c1 = riesgo.concentracion_top1 || 0;
      var c3 = riesgo.concentracion_top3 || 0;
      var riesgoClr = c1 >= 50 ? 'rojo' : c1 >= 30 ? 'amarillo' : 'verde';
      var top3html = (riesgo.top3_aliados || []).map(function(a,i){
        return '<div class="data-row"><span class="data-lbl">'+(i+1)+'. '+a.nombre+'</span><span class="data-val">'+a.pct+'%</span></div>';
      }).join('');
      g4riesgo.innerHTML =
        '<div class="data-row"><span class="data-lbl">Top 1 aliado</span><span class="data-val '+riesgoClr+'">'+c1+'%</span></div>'
        +'<div class="data-row"><span class="data-lbl">Top 3 aliados</span><span class="data-val '+(c3>=70?'amarillo':'verde')+'">'+c3+'%</span></div>'
        +'<div style="margin:8px 0 4px;font-size:10px;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:.05em;">Top 3 detalle</div>'
        + top3html;
    }

    // Estado del canal
    var g4estado = document.getElementById('g4-estado');
    if(g4estado){
      var vrClr = (riesgo.valor_en_riesgo||0) > 1000000 ? 'rojo' : (riesgo.valor_en_riesgo||0) > 0 ? 'amarillo' : 'verde';
      var vcClr = (riesgo.aliados_vencidos_prediccion||0) > 0 ? 'amarillo' : 'verde';
      g4estado.innerHTML =
        '<div class="data-row"><span class="data-lbl">Activos (&lt;60d)</span><span class="data-val verde">'+(riesgo.aliados_activos||0)+'</span></div>'
        +'<div class="data-row"><span class="data-lbl">Dormidos (&gt;60d)</span><span class="data-val '+(riesgo.aliados_dormidos>0?'rojo':'verde')+'">'+(riesgo.aliados_dormidos||0)+'</span></div>'
        +'<div class="data-row"><span class="data-lbl">Valor en riesgo</span><span class="data-val '+vrClr+'">'+fv(riesgo.valor_en_riesgo)+'</span></div>'
        +'<div class="data-row"><span class="data-lbl">Compra vencida</span><span class="data-val '+vcClr+'">'+(riesgo.aliados_vencidos_prediccion||0)+' aliados</span></div>';
    }

    // Tendencia ticket SVG
    var g4trend = document.getElementById('g4-trend');
    var trend = d.ticket_trend || [];
    if(g4trend && trend.length){
      var maxT = Math.max.apply(null, trend.map(function(t){ return t.ticket; })) || 1;
      var barH = 70;
      g4trend.innerHTML = trend.map(function(t){
        var h = Math.round((t.ticket / maxT) * barH);
        var mes = t.mes ? t.mes.slice(5) : ''; // MM
        var meses = ['','Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
        var mesN = parseInt(mes,10);
        var mesNm = meses[mesN] || mes;
        return '<div style="display:flex;flex-direction:column;align-items:center;gap:4px;flex:1;">'
          +'<div style="font-size:9px;color:rgba(255,255,255,0.5);">'+fv(t.ticket)+'</div>'
          +'<div style="width:100%;max-width:40px;height:'+h+'px;background:linear-gradient(180deg,#a78bfa,#7c3aed);border-radius:4px 4px 0 0;align-self:flex-end;"></div>'
          +'<div style="font-size:10px;color:rgba(255,255,255,0.6);">'+mesNm+'</div>'
          +'<div style="font-size:9px;color:rgba(255,255,255,0.3);">'+t.pedidos+'p</div>'
          +'</div>';
      }).join('');
    } else if(g4trend){
      g4trend.innerHTML = '<div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Sin historial suficiente</div>';
    }

  } catch(e){ console.error('loadAliados4:', e); }
}

</script>
</body>
</html>"""
