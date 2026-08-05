# Auto-extraído de index.py - Fase A refactor
GERENCIA_HTML = """<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Gerencia - HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--cx-bg);min-height:100vh;color:var(--cx-text);}
.topbar{background:var(--cx-hero-grad);padding:14px 28px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--cx-hairline);}
.topbar-left{display:flex;align-items:center;gap:16px;}
.logo{font-size:0.95em;font-weight:900;letter-spacing:3px;color:var(--cx-primary-text);}
.badge-ceo{background:rgba(109,40,217,0.5);color:var(--cx-primary-text);padding:3px 12px;border-radius:20px;font-size:0.72em;font-weight:700;letter-spacing:1px;}
.topbar a{color:var(--cx-text-mute);text-decoration:none;font-size:0.8em;padding:6px 14px;border:1px solid var(--cx-hairline);border-radius:6px;}
.topbar a:hover{color:var(--cx-text);border-color:var(--cx-text-mute);}
.periodo-badge{background:rgba(109,40,217,0.3);padding:4px 14px;border-radius:20px;font-size:0.78em;color:var(--cx-primary-text);}
.main{padding:28px;max-width:1300px;margin:0 auto;}
.section-title{font-size:0.72em;text-transform:uppercase;letter-spacing:2px;color:var(--cx-text-mute);margin-bottom:14px;margin-top:28px;}
.section-title:first-child{margin-top:0;}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:8px;}
.kpi{background:var(--cx-card);border:1px solid var(--cx-hairline);box-shadow:var(--cx-sh-card);border-radius:14px;padding:20px 22px;position:relative;overflow:hidden;transition:box-shadow .2s ease,transform .2s ease;}
.kpi:hover{box-shadow:var(--cx-sh-card-hover);transform:translateY(-2px);}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--ac,#6d28d9);}
.kpi.rojo::before{background:var(--cx-danger);}.kpi.amarillo::before{background:var(--cx-warn);}.kpi.verde::before{background:var(--cx-success);}
.kpi-val{font-size:2.2em;font-weight:900;line-height:1;color:var(--cx-text);}
.kpi-val.rojo{color:var(--cx-danger-text);}.kpi-val.amarillo{color:var(--cx-warn-text);}.kpi-val.verde{color:var(--cx-success-text);}
.kpi-lbl{font-size:0.72em;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:1px;margin-top:8px;}
.kpi-sub{font-size:0.8em;color:var(--cx-text-faint);margin-top:4px;}
.sem{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle;}
.ceo-dec-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:14px;margin-bottom:26px;}
.ceo-dec-cargando{color:var(--cx-text-faint);font-size:.9em;padding:18px;}
.ceo-card{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:14px;padding:16px 18px;
  box-shadow:0 1px 2px rgba(24,24,27,.04);display:flex;flex-direction:column;}
.ceo-card.urge{border-left:5px solid var(--cx-danger);}
.ceo-card.ok{border-left:5px solid var(--cx-success);}
.ceo-card.espera{border-left:5px solid var(--cx-warn);}
.ceo-card-h{display:flex;align-items:baseline;justify-content:space-between;gap:10px;margin-bottom:9px;}
.ceo-card-t{font-size:.76em;font-weight:800;letter-spacing:.09em;text-transform:uppercase;color:var(--cx-text-mute);}
.ceo-card-n{font-size:1.65em;font-weight:800;color:var(--cx-text);letter-spacing:-.02em;line-height:1.1;}
.ceo-card-s{font-size:.78em;color:var(--cx-text-mute);margin-top:3px;}
.ceo-lista{margin-top:11px;border-top:1px solid var(--cx-hairline,var(--cx-border));padding-top:9px;}
.ceo-li{display:flex;justify-content:space-between;gap:10px;padding:6px 0;font-size:.84em;
  border-bottom:1px solid var(--cx-hairline,var(--cx-border));}
.ceo-li:last-child{border-bottom:none;}
.ceo-li-n{color:var(--cx-text);font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.ceo-li-q{font-size:.86em;color:var(--cx-text-mute);font-weight:400;}
.ceo-li-v{color:var(--cx-text);font-weight:800;white-space:nowrap;font-variant-numeric:tabular-nums;}
.ceo-vacio{font-size:.84em;color:var(--cx-success-text);padding:4px 0;}
.ceo-aviso{font-size:.8em;color:var(--cx-danger-text);padding:4px 0;}
.ceo-mas{font-size:.76em;color:var(--cx-text-faint);margin-top:7px;}
.ceo-ir{margin-top:11px;display:inline-block;font-size:.8em;font-weight:700;color:var(--cx-primary-text);
  text-decoration:none;border:1px solid var(--cx-primary-soft,var(--cx-border));border-radius:8px;padding:6px 12px;}
.ceo-ir:hover{background:var(--cx-primary-pale,var(--cx-bg-alt));}
.sem.verde{background:var(--cx-success);box-shadow:0 0 8px #10b981;}.sem.amarillo{background:var(--cx-warn);box-shadow:0 0 8px #f59e0b;}.sem.rojo{background:var(--cx-danger);box-shadow:0 0 8px #ef4444;}
.alertas-panel{background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:12px;padding:20px;margin-bottom:28px;display:none;}
.alertas-panel.visible{display:block;}
.alerta-item{display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid rgba(239,68,68,0.15);}
.alerta-item:last-child{border-bottom:none;}
.alerta-icon{font-size:1.2em;margin-top:1px;}
.alerta-texto{font-size:0.88em;color:var(--cx-text-soft);line-height:1.5;}
.two-cols{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px;}
.panel{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:12px;padding:22px;}
.panel-title{font-size:0.82em;font-weight:700;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:16px;display:flex;align-items:center;gap:8px;}
.data-row{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid var(--cx-hairline);}
.data-row:last-child{border-bottom:none;}
.data-lbl{font-size:0.85em;color:var(--cx-text-mute);}
.data-val{font-size:0.92em;font-weight:700;color:var(--cx-text);}
.data-val.rojo{color:var(--cx-danger-text);}.data-val.amarillo{color:var(--cx-warn-text);}.data-val.verde{color:var(--cx-success-text);}
.input-panel{background:rgba(109,40,217,0.1);border:1px solid rgba(109,40,217,0.3);border-radius:12px;padding:22px;margin-top:20px;}
.input-panel-title{font-size:0.85em;font-weight:700;color:var(--cx-primary-text);margin-bottom:16px;display:flex;align-items:center;gap:8px;}
.inp-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:14px;}
.inp-group label{display:block;font-size:0.72em;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:5px;}
.inp-group input{width:100%;padding:9px 12px;background:var(--cx-bg-alt);border:1.5px solid var(--cx-hairline);border-radius:7px;color:var(--cx-text);font-size:0.9em;transition:border 0.2s;}
.inp-group input:focus{outline:none;border-color:var(--cx-primary);background:var(--cx-bg-alt);}
.inp-group input::placeholder{color:var(--cx-text-faint);}
.btn-save{background:var(--cx-primary);color:var(--cx-text);border:none;padding:10px 24px;border-radius:8px;font-size:0.88em;font-weight:700;cursor:pointer;transition:all 0.2s;}
.btn-save:hover{background:#1d5c5a;transform:translateY(-1px);}
.msg-ok-dark{background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);color:var(--cx-success-text);padding:9px 14px;border-radius:8px;font-size:0.85em;margin-top:10px;}
.msg-err-dark{background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:var(--cx-danger-text);padding:9px 14px;border-radius:8px;font-size:0.85em;margin-top:10px;}
.finanzas-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:8px;}
.fin-card{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:10px;padding:16px 18px;text-align:center;}
.fin-val{font-size:1.6em;font-weight:900;color:var(--cx-primary-text);}
.fin-lbl{font-size:0.72em;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:1px;margin-top:5px;}
.refresh-btn{background:var(--cx-bg-alt);border:1px solid var(--cx-hairline);color:var(--cx-text-mute);padding:6px 14px;border-radius:6px;font-size:0.8em;cursor:pointer;transition:all 0.2s;}
.refresh-btn:hover{background:var(--cx-hairline);color:var(--cx-text);}
.ultima-act{font-size:0.72em;color:var(--cx-text-faint);margin-left:10px;}
.prog-bar-wrap{background:var(--cx-bg-alt);border-radius:20px;height:10px;overflow:hidden;margin:6px 0 3px;}
.prog-bar{height:100%;border-radius:20px;transition:width 0.8s ease;background:linear-gradient(90deg,#6d28d9,#6d28d9);}
.prog-bar.danger{background:linear-gradient(90deg,#ef4444,#f87171);}
.prog-bar.warn{background:linear-gradient(90deg,#f59e0b,#b45309);}
.churn-item{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--cx-hairline);}
.churn-item:last-child{border-bottom:none;}
.badge-crit{background:rgba(239,68,68,0.2);color:var(--cx-danger-text);padding:2px 8px;border-radius:10px;font-size:0.75em;font-weight:700;}
.badge-atenc{background:rgba(245,158,11,0.2);color:var(--cx-warn-text);padding:2px 8px;border-radius:10px;font-size:0.75em;font-weight:700;}
/* Mobile responsive · 27-may-2026 */
@media (max-width: 768px) {
  .two-cols { grid-template-columns: 1fr !important; }
  .finanzas-grid { grid-template-columns: 1fr !important; }
}
@media (max-width: 480px) {
  .finanzas-grid { grid-template-columns: 1fr !important; }
}
</style>
</head>
<body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:var(--cx-primary-text);"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
  <div>
    <div class="cx-mod-header__title">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M3 9l9-6 9 6"/><path d="M5 21V11M19 21V11M9 21v-8M15 21v-8M2 21h20"/></svg>
      Panel Gerencial
    </div>
    <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; metas YTD · estrategia · KPIs ejecutivos &middot; <span class="periodo-badge" id="periodo-label" style="color:var(--cx-text-faint)">Cargando...</span></div>
  </div>
  <div class="cx-mod-header__nav">
    <button class="cx-btn cx-btn-ghost cx-btn-sm" onclick="loadKPIs()">&#x21bb; Actualizar</button>
    <span class="ultima-act" id="ultima-actualizacion" style="font-size:11px;color:var(--cx-text-faint);"></span>
    <a href="/planta/analitica-batch" class="cx-btn cx-btn-sm" style="background:var(--cx-primary,#6d28d9);color:#fff" title="Tiempos de ciclo, cuellos de botella, rendimiento y productividad del batch (privado)">&#128202; Analítica del Batch</a>
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">Módulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
    </button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>

<div class="main">

  <!-- ═══ LO QUE ESPERA TU FIRMA ═══════════════════════════════════════════
       Va PRIMERO porque un tablero de CEO se abre para decidir, no para mirar.
       Todo lo de aca lo calcula su modulo dueño (caja: `caja_saldo` de Animus ·
       creadores: `_pagos_influencer_pendientes` del hub) · el tablero no
       recalcula nada: dos calculos del mismo hecho divergen siempre. -->
  <div class="section-title">✍️ Espera tu decisión</div>
  <div id="ceo-decisiones" class="ceo-dec-grid">
    <div class="ceo-dec-cargando">Cargando…</div>
  </div>

  <!-- ALERTAS CRÍTICAS -->
  <div class="alertas-panel" id="alertas-panel">
    <div style="font-size:0.82em;font-weight:700;color:var(--cx-danger-text);text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">⚠ Alertas que requieren acción</div>
    <div id="alertas-list"></div>
  </div>

  <!-- FINANCIERO (inputs manuales) -->
  <div class="section-title">💰 Financiero del mes</div>
  <div class="finanzas-grid" style="grid-template-columns:repeat(auto-fit,minmax(160px,1fr));">
    <div class="fin-card"><div class="fin-val" id="fin-caja">-</div><div class="fin-lbl">Saldo de caja</div></div>
    <div class="fin-card"><div class="fin-val" id="fin-animus">-</div><div class="fin-lbl">Ingresos ÁNIMUS</div></div>
    <div class="fin-card"><div class="fin-val" id="fin-maquila">-</div><div class="fin-lbl">Ingresos Maquila</div></div>
    <div class="fin-card"><div class="fin-val" id="fin-nomina" style="color:var(--cx-warn-text);">-</div><div class="fin-lbl">Nomina mes</div><div style="font-size:0.65em;color:var(--cx-text-faint);margin-top:3px;" id="fin-nomina-emp"></div></div>
  </div>

  <!-- ESPAGIRIA -->
  <div class="section-title">🏭 Espagiria Laboratorios</div>
  <div class="kpi-grid">
    <div class="kpi" id="kpi-mps-bajos">
      <div class="kpi-val" id="val-mps-bajos">-</div>
      <div class="kpi-lbl">MPs bajo mínimo</div>
      <div class="kpi-sub" id="sub-deficit">-</div>
    </div>
    <div class="kpi" id="kpi-vencen30">
      <div class="kpi-val" id="val-vencen30">-</div>
      <div class="kpi-lbl">Lotes vencen en 30 días</div>
      <div class="kpi-sub" id="sub-vencen60">-</div>
    </div>
    <div class="kpi" id="kpi-produccion">
      <div class="kpi-val" id="val-lotes-mes">-</div>
      <div class="kpi-lbl">Lotes producción mes</div>
      <div class="kpi-sub" id="sub-kg-mes">-</div>
    </div>
    <div class="kpi" id="kpi-ocs">
      <div class="kpi-val" id="val-ocs">-</div>
      <div class="kpi-lbl">OCs pendientes aprobación</div>
      <div class="kpi-sub" id="sub-ocs-val">-</div>
    </div>
    <div class="kpi" id="kpi-sol-pend" style="cursor:pointer;" onclick="location.href='/compras'">
      <div class="kpi-val" id="val-sol-pend">-</div>
      <div class="kpi-lbl">Solicitudes a Compras</div>
      <div class="kpi-sub" style="font-size:0.78em;opacity:0.6;">Pendientes de aprobar → /compras</div>
    </div>
    <div class="kpi" id="kpi-mee-bajos">
      <div class="kpi-val" id="val-mee-bajos">-</div>
      <div class="kpi-lbl">MEE bajo mínimo</div>
      <div class="kpi-sub" id="sub-mee">Envases y empaques</div>
    </div>
  </div>

  <!-- ÁNIMUS -->
  <div class="section-title">✨ ÁNIMUS Lab</div>
  <div class="kpi-grid">
    <div class="kpi verde">
      <div class="kpi-val verde" id="val-uds-pt">-</div>
      <div class="kpi-lbl">Unidades PT disponibles</div>
      <div class="kpi-sub" id="sub-skus-pt">-</div>
    </div>
    <div class="kpi" id="kpi-pedidos-act">
      <div class="kpi-val" id="val-pedidos-act">-</div>
      <div class="kpi-lbl">Pedidos activos</div>
      <div class="kpi-sub" id="sub-pedidos-val">-</div>
    </div>
    <div class="kpi" id="kpi-fm">
      <div class="kpi-val" id="val-fm-dias">-</div>
      <div class="kpi-lbl">Días desde último pedido FM</div>
      <div class="kpi-sub">Ciclo promedio: ~62 días</div>
    </div>
  </div>

  <!-- DETALLE DOS COLUMNAS -->
  <div class="two-cols">
    <div class="panel">
      <div class="panel-title"><span class="sem verde" id="sem-inv"></span>Planta Espagiria</div>
      <div id="detalle-inventario"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title"><span class="sem verde" id="sem-animus"></span>ÁNIMUS Lab</div>
      <div id="detalle-animus"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
  </div>

  <!-- INPUT MANUAL MENSUAL -->
  <div class="input-panel">
    <div class="input-panel-title">📝 Input manual mensual <span style="font-weight:400;color:var(--cx-text-faint);font-size:0.85em;">- actualizar en 5 minutos al inicio de cada mes</span></div>
    <div class="inp-grid">
      <div class="inp-group"><label>Saldo de caja ($COP)</label><input type="number" id="inp-caja" placeholder="354800000"></div>
      <div class="inp-group"><label>Ingresos ÁNIMUS mes ($COP)</label><input type="number" id="inp-animus" placeholder="189000000"></div>
      <div class="inp-group"><label>Ingresos Maquila mes ($COP)</label><input type="number" id="inp-maquila" placeholder="30000000"></div>
      <!-- La NÓMINA no se teclea: sale de lo que RRHH aprobó en `nomina_registros`. Tener acá
           un campo manual sería un segundo origen del mismo número, y dos orígenes divergen
           siempre (M99). Encima lo que se escribía se descartaba en silencio: la tabla no tiene
           esa columna. El valor derivado se muestra abajo, con su período. -->
      <div class="inp-group"><label>Nómina del período</label>
        <div id="inp-nomina-vista" style="padding:9px 0;font-weight:700;color:var(--cx-text);">-</div>
        <div style="font-size:11px;color:var(--cx-text-mute);">sale de RRHH · no se edita acá</div></div>
    </div>
    <div class="inp-group" style="margin-bottom:14px;"><label>Notas del período</label><input type="text" id="inp-notas" placeholder="Ej: Mes de lanzamiento NIAC, pago nómina atrasado..."></div>
    <button class="btn-save" onclick="guardarInputs()">💾 Guardar inputs del mes</button>
    <div id="inp-msg"></div>
  </div>

  <!-- FLUJO OPERACIONAL -->
  <div class="section-title" style="margin-top:32px;">🔄 Flujo Operacional - Vista Ejecutiva</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-bottom:20px;">
    <div class="panel">
      <div class="panel-title">📦 Compras pendientes de recibir
        <a href="/recepcion" style="margin-left:auto;font-size:0.75em;color:var(--cx-primary-text);text-decoration:none;font-weight:600;">→ Recepción</a>
      </div>
      <div id="g-ocs-transito"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">⚠ Recepciones con discrepancias</div>
      <div id="g-disc"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">🚚 Pedidos listos para despachar
        <a href="/hub-salida" style="margin-left:auto;font-size:0.75em;color:var(--cx-primary-text);text-decoration:none;font-weight:600;">→ Hub Salida</a>
      </div>
      <div id="g-pedidos-listos"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">✅ Despachos recientes</div>
      <div id="g-despachos"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
  </div>

  <!-- QUICK NAV -->
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:28px;">
    <a href="/hub" style="background:var(--cx-bg-alt);border:1px solid var(--cx-text-faint);color:#fff;padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:700;">🏠 Panel Central</a>
    <!-- `/mi-bandeja` era una pantalla HUÉRFANA: 230 líneas de pendientes cross-módulo (recalls,
         hallazgos, cola de liberación, quejas, control de cambios) alcanzables sólo tecleando la
         URL — ningún menú ni botón de toda la app la enlazaba. Una feature a la que no se puede
         llegar es una feature que no existe (M121). -->
    <a href="/mi-bandeja" style="background:var(--cx-primary-pale, #f5f3ff);border:1px solid var(--cx-primary-soft, #ddd6fe);color:var(--cx-primary-text);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:700;">📋 Mi bandeja de pendientes</a>
    <a href="/hoy" style="background:var(--cx-primary-pale, #f5f3ff);border:1px solid var(--cx-primary-soft, #ddd6fe);color:var(--cx-primary-text);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:700;">⚡ Centro de Mando · HOY</a>
    <a href="/recepcion" style="background:rgba(109,40,217,0.2);border:1px solid rgba(109,40,217,0.4);color:var(--cx-primary-text);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">📥 Recepción de Mercancía</a>
    <a href="/hub-salida" style="background:rgba(74,103,65,0.2);border:1px solid rgba(74,103,65,0.4);color:#8BC98A;padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">📤 Hub de Salida</a>
    <a href="/compras" style="background:var(--cx-card);border:1px solid var(--cx-hairline);color:var(--cx-text-mute);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">🛒 Módulo Compras</a>
    <a href="/clientes" style="background:var(--cx-card);border:1px solid var(--cx-hairline);color:var(--cx-text-mute);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">👤 Módulo Clientes</a>
    <a href="/financiero" style="background:var(--cx-card);border:1px solid var(--cx-hairline);color:var(--cx-text-mute);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">💰 Financiero</a>
    <a href="/calidad" style="background:var(--cx-card);border:1px solid var(--cx-hairline);color:var(--cx-text-mute);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">🔬 Calidad</a>
    <a href="/rrhh" style="background:var(--cx-card);border:1px solid var(--cx-hairline);color:var(--cx-text-mute);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">👥 RRHH</a>
    <a href="/tecnica" style="background:var(--cx-card);border:1px solid var(--cx-hairline);color:var(--cx-text-mute);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">🔧 Técnica</a>
  </div>



  <!-- INDICADORES EJECUTIVOS - solo metas/estrategicos. Caja, AR/AP, P&L viven en /financiero -->
  <div class="section-title" style="margin-top:32px;">📊 Metas estratégicas <a href="/financiero" style="font-size:0.65em;font-weight:600;color:var(--cx-primary-text);text-decoration:none;margin-left:12px;">→ Para caja, AR/AP, P&L: ir a Financiero</a> · <a href="/hoy" style="font-size:0.65em;font-weight:600;color:var(--cx-accent);text-decoration:none;">→ Para hoy: ir a HOY</a></div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:20px;">
    <div class="panel">
      <!-- Los ingresos por canal YA se calculaban y no se pintaban: el contenedor `gx-ingresos`
           no existia en el HTML, asi que las tres consultas corrian cada 5 minutos para nadie.
           Es el numero que contesta "de donde vino la plata este mes". -->
      <div class="panel-title">&#128176; Ingresos del mes por canal</div>
      <div id="gx-ingresos"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">🏭 Pipeline Maquila activo</div>
      <div id="gx-maquila"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">📊 Meta Maquila 2026</div>
      <div id="gx-maquila-target"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin-bottom:12px;">
    <div class="panel">
      <div class="panel-title">💄 Inversion Influencers YTD</div>
      <div id="gx-influencer"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">📦 Valor Inventario MP (COP)</div>
      <div id="gx-inv-cop"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">&#128276; Alertas recompra clientes</div>
      <div id="gx-churn"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin-bottom:28px;">
    <div class="panel">
      <div class="panel-title">⚠ Stock Critico - MPs bajo minimo</div>
      <div id="gx-stock"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">✅ SGSST - Proximos vencimientos</div>
      <div id="gx-sgsst"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">🔒 Accesos recientes</div>
      <div id="gx-sec"><div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div></div>
    </div>
  </div>


  <!-- Capa 4: Feed Aliados → Gerencia -->
  <div class="section-title" style="margin-top:32px;">🤝 Canal Aliados - Vista Gerencia</div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:14px;">

    <!-- Mix de canales -->
    <div class="panel">
      <div class="panel-title">📊 Mix canales · este mes</div>
      <div id="g4-mix">
        <div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div>
      </div>
    </div>

    <!-- Concentración de riesgo -->
    <div class="panel">
      <div class="panel-title">⚠️ Concentración de riesgo</div>
      <div id="g4-riesgo">
        <div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div>
      </div>
    </div>

    <!-- Estado del canal -->
    <div class="panel">
      <div class="panel-title">🔋 Estado del canal</div>
      <div id="g4-estado">
        <div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div>
      </div>
    </div>
  </div>

  <!-- Tendencia ticket por mes -->
  <div class="panel" style="margin-bottom:28px;">
    <div class="panel-title">📈 Tendencia ticket promedio - canal aliados (6 meses)</div>
    <div id="g4-trend" style="display:flex;gap:8px;align-items:flex-end;padding:8px 0;min-height:80px;">
      <div style="color:var(--cx-text-faint);font-size:0.85em;">Cargando...</div>
    </div>
  </div>

</div><!-- /main -->

<script>

// CSRF defense-in-depth - Sebastian 3-may-2026
function _csrf() {
  var m = document.cookie.match(/(?:^|;[ \t]*)csrf_token=([^;]+)/);
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
function fmt(n,prefix){if(n==null||n===undefined)return '-';var v=Math.abs(parseFloat(n));var s=v>=1000000?(v/1000000).toFixed(1)+'M':(v>=1000?(v/1000).toFixed(0)+'K':v.toLocaleString('es-CO'));return (prefix||'$')+s;}
function fmtN(n){return n!=null?parseFloat(n).toLocaleString('es-CO'):'-';}
function esc(s){return (s==null?'':String(s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
function setSemaforo(id,color){var el=document.getElementById(id);if(el){el.className='sem '+color;}}
function setKPIColor(kpiId,valId,color){
  var k=document.getElementById(kpiId),v=document.getElementById(valId);
  if(k) k.className='kpi '+(color||'');
  if(v) v.className='kpi-val '+(color||'');
}

async function loadKPIs(){
  try{
    var d=await fetch('/api/gerencia/kpis').then(function(r){return r.json();});
    if(d.error){document.querySelector('.main').innerHTML='<div style="color:var(--cx-danger-text);padding:40px;text-align:center;">'+d.error+'</div>';return;}

    var e=d.espagiria||{}; var a=d.animus||{}; var f=d.inputs_manuales||{}; var sem=d.semaforos||{};

    // Periodo
    // `d.periodo` no existe en la respuesta · el periodo real es el del input manual, que si
    // viene. La pildora quedaba vacia desde siempre.
    document.getElementById('periodo-label').textContent = (f && f.periodo) ? f.periodo : '';
    document.getElementById('ultima-actualizacion').textContent='Actualizado: '+new Date().toLocaleTimeString('es-CO');

    // Financiero
    document.getElementById('fin-caja').textContent=fmt(f.saldo_caja);
    document.getElementById('fin-animus').textContent=fmt(f.ingresos_animus);
    document.getElementById('fin-maquila').textContent=fmt(f.ingresos_maquila);
    var nom=d.nomina||{};
    document.getElementById('fin-nomina').textContent=nom.total&&nom.total>0?fmt(nom.total):'-';
    document.getElementById('fin-nomina-emp').textContent=nom.empleados?nom.empleados+' activos':'';

    // Espagiria KPIs
    var mpsBajos=e.mps_bajo_minimo||0;
    document.getElementById('val-mps-bajos').textContent=mpsBajos;
    // `deficit_total_kg` NUNCA lo devolvio el endpoint: mostraba "Déficit: 0 g" siempre.
    // Calcular el deficit real exige el motor de abastecimiento (caro · vive en Planta), asi que
    // acá se dice lo que SI se sabe y se manda al lugar donde el numero existe.
    document.getElementById('sub-deficit').textContent =
      (e.mps_bajo_minimo||0) > 0 ? 'de ' + (e.mps_total||'?') + ' materias primas activas' : 'todas por encima del mínimo';
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
    document.getElementById('sub-pedidos-val').textContent =
      (a.dias_desde_fm != null) ? ('último pedido hace ' + a.dias_desde_fm + ' d') : '';

    var diasFM=a.dias_desde_fm;
    var diasFMEl=document.getElementById('val-fm-dias');
    diasFMEl.textContent=diasFM!=null?diasFM+' días':'Sin pedidos';
    setKPIColor('kpi-fm','val-fm-dias',diasFM>62?'amarillo':'verde');

    // Semáforos
    // El endpoint manda `mps/mee/vencimientos/pt/pedidos/solicitudes`; esto leia `inventario` y
    // `fm`, que no existen -> los dos semaforos caian al default y estaban SIEMPRE en verde, o
    // sea que eran decoracion. Ahora el de inventario toma lo PEOR de sus tres componentes
    // (materias primas, envases, vencimientos): un semaforo que promedia esconde el problema.
    var _peor = function(){
      var v = [sem.mps, sem.mee, sem.vencimientos];
      return v.indexOf('rojo') >= 0 ? 'rojo' : (v.indexOf('amarillo') >= 0 ? 'amarillo' : 'verde');
    };
    setSemaforo('sem-inv', _peor());
    setSemaforo('sem-animus', sem.pt || 'verde');

    // Detalle inventario
    var di='';
    di+='<div class="data-row"><span class="data-lbl">MPs bajo mínimo</span><span class="data-val '+(mpsBajos>0?'rojo':'verde')+'">'+mpsBajos+'</span></div>';
    di+='<div class="data-row"><span class="data-lbl">MEE bajo mínimo</span><span class="data-val '+(meeBajos>0?'amarillo':'verde')+'">'+meeBajos+'</span></div>';
    // (se retiro "Déficit total": el endpoint nunca lo calculo, asi que decia 0.0 kg siempre)
    di+='<div class="data-row"><span class="data-lbl">Lotes vencen 30d</span><span class="data-val '+(v30>0?'rojo':'verde')+'">'+v30+'</span></div>';
    di+='<div class="data-row"><span class="data-lbl">Lotes vencen 60d</span><span class="data-val '+(e.lotes_vence_60>0?'amarillo':'verde')+'">'+(e.lotes_vence_60||0)+'</span></div>';
    di+='<div class="data-row"><span class="data-lbl">Producción este mes</span><span class="data-val">'+( e.prod_mes||0)+' lotes / '+parseFloat(e.kg_mes||0).toFixed(1)+' kg</span></div>';
    // El VALOR de las OCs pendientes tampoco venia del endpoint: mostraba "($0)" al lado de un
    // conteo real, que es la peor combinacion -- el conteo le daba credibilidad al cero.
    di+='<div class="data-row"><span class="data-lbl">OCs pendientes</span><span class="data-val '+(ocs>0?'amarillo':'verde')+'">'+ocs+'</span></div>';
    di+='<div class="data-row"><span class="data-lbl">Solicitudes a Compras</span><span class="data-val '+(solPend>0?'amarillo':'verde')+'">'+solPend+' <a href="/compras" style="color:var(--cx-text-mute);font-size:0.82em;">→ ver</a></span></div>';
    document.getElementById('detalle-inventario').innerHTML=di;

    // Detalle ÁNIMUS
    var da='';
    da+='<div class="data-row"><span class="data-lbl">Unidades PT disponibles</span><span class="data-val verde">'+fmtN(a.uds_pt||0)+'</span></div>';
    da+='<div class="data-row"><span class="data-lbl">SKUs con stock</span><span class="data-val">'+(a.skus_stock||0)+'</span></div>';
    da+='<div class="data-row"><span class="data-lbl">Pedidos activos</span><span class="data-val">'+(a.pedidos_activos||0)+'</span></div>';
    // (se retiraron el valor en $ de los pedidos y "Último pedido FM": ninguno de los dos lo
    //  devuelve el endpoint · el segundo decia "Sin datos" desde que se escribio)
    da+='<div class="data-row"><span class="data-lbl">Días desde pedido FM</span><span class="data-val '+(diasFM>55?'amarillo':'verde')+'">'+(diasFM!=null?diasFM+' días':'-')+'</span></div>';
    document.getElementById('detalle-animus').innerHTML=da;

    // Alertas
    var alertas=[];
    // Una alerta ROJA que afirma "Déficit total: 0.0 kg" grita y se contradice sola. El hecho
    // (hay N materias primas bajo el minimo) es real y basta; el numero que no se midio, no va.
    if(mpsBajos>0) alertas.push({icon:'🔴',txt:'<strong>'+mpsBajos+' materias primas bajo el mínimo</strong> · revisalas en Abastecimiento antes de que frenen una producción.'});
    if(meeBajos>0) alertas.push({icon:'🟡',txt:'<strong>'+meeBajos+' materiales de envase/empaque bajo mínimo</strong> - Revisar stock MEE en módulo Compras.'});
    if(v30>0) alertas.push({icon:'🔴',txt:'<strong>'+v30+' lotes vencen en los próximos 30 días</strong> - Revisar y usar en próximas producciones (FEFO).'});
    if(ocs>3) alertas.push({icon:'🟡',txt:'<strong>'+ocs+' órdenes de compra</strong> esperando aprobación.'});
    if(solPend>0) alertas.push({icon:'🟡',txt:'<strong>'+solPend+' solicitud'+(solPend>1?'es':'')+' de compra pendiente'+(solPend>1?'s':'')+' de aprobar</strong> - Catalina debe revisar en <a href="/compras" style="color:rgba(255,255,255,0.75);">Módulo Compras</a> para convertirlas en órdenes de compra.'});
    if(diasFM!=null&&diasFM>55) alertas.push({icon:'🟡',txt:'<strong>Fernando Mesa: '+diasFM+' días sin pedir</strong> - Ciclo normal ~62 días. Próximo pedido inminente.'});
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
    var _nv = document.getElementById('inp-nomina-vista');
    if(_nv) _nv.textContent = nom.total
      ? (fmt(nom.total) + '  ·  ' + (nom.empleados||0) + ' personas' + (nom.periodo ? ' · ' + nom.periodo : ''))
      : 'sin nómina registrada este período';
    if(f.notas) document.getElementById('inp-notas').value=f.notas;

  }catch(e){console.error(e);}
}

async function guardarInputs(){
  var data={
    saldo_caja:parseFloat(document.getElementById('inp-caja').value)||0,
    ingresos_animus:parseFloat(document.getElementById('inp-animus').value)||0,
    ingresos_maquila:parseFloat(document.getElementById('inp-maquila').value)||0,
    notas:document.getElementById('inp-notas').value
  };
  try{
    var r=await fetch('/api/gerencia/input-manual',_fetchOpts('POST', data));
    var res=await r.json();
    document.getElementById('inp-msg').innerHTML=r.ok?'<div class="msg-ok-dark">'+res.message+'</div>':'<div class="msg-err-dark">'+(res.error||'Error')+'</div>';
    if(r.ok) setTimeout(loadKPIs,500);
  }catch(e){document.getElementById('inp-msg').innerHTML='<div class="msg-err-dark">Error</div>';}
}

async function loadFlujoOperacional() {
  try {
    var d = await fetch('/api/gerencia/flujo-operacional').then(function(r){ return r.json(); });
    var nil = '<div style="color:var(--cx-text-faint);font-size:0.85em;">Sin datos</div>';

    // OCs en tránsito
    var elt = document.getElementById('g-ocs-transito');
    if (elt) {
      var ocs = d.ocs_transito || [];
      if (!ocs.length) { elt.innerHTML = '<div style="color:var(--cx-text-faint);font-size:0.85em;">Sin OCs pendientes ✓</div>'; }
      else {
        elt.innerHTML = ocs.slice(0,4).map(function(o) {
          return '<div class="data-row"><span class="data-lbl">' + esc(o.numero_oc) + ' - ' + esc(o.proveedor||'') + '</span>'
            + '<span class="data-val amarillo">' + (o.dias_transito||0) + 'd</span></div>';
        }).join('') + (ocs.length > 4 ? '<div style="color:var(--cx-text-faint);font-size:0.8em;padding:6px 0;">+' + (ocs.length-4) + ' más</div>' : '');
      }
    }

    // Discrepancias
    var eld = document.getElementById('g-disc');
    if (eld) {
      var discs = d.recepciones_disc || [];
      if (!discs.length) { eld.innerHTML = '<div style="color:var(--cx-success-text);font-size:0.85em;">Sin discrepancias ✓</div>'; }
      else {
        eld.innerHTML = discs.slice(0,4).map(function(r) {
          return '<div class="data-row"><span class="data-lbl">' + esc(r.numero_oc) + '</span>'
            + '<span class="data-val rojo">DISC</span></div>';
        }).join('');
      }
    }

    // Pedidos listos
    var elp = document.getElementById('g-pedidos-listos');
    if (elp) {
      var peds = d.pedidos_listos || [];
      if (!peds.length) { elp.innerHTML = '<div style="color:var(--cx-text-faint);font-size:0.85em;">Sin pedidos pendientes</div>'; }
      else {
        elp.innerHTML = peds.slice(0,4).map(function(p) {
          return '<div class="data-row"><span class="data-lbl">' + esc(p.numero) + ' - ' + esc(p.cliente||'') + '</span>'
            + '<span class="data-val amarillo">$' + Number(p.valor_total||0).toLocaleString() + '</span></div>';
        }).join('') + (peds.length > 4 ? '<div style="color:var(--cx-text-faint);font-size:0.8em;padding:6px 0;">+' + (peds.length-4) + ' más</div>' : '');
      }
    }

    // Despachos recientes
    var elsp = document.getElementById('g-despachos');
    if (elsp) {
      var desps = d.despachos_recientes || [];
      if (!desps.length) { elsp.innerHTML = '<div style="color:var(--cx-text-faint);font-size:0.85em;">Sin despachos recientes</div>'; }
      else {
        elsp.innerHTML = desps.slice(0,4).map(function(ds) {
          return '<div class="data-row"><span class="data-lbl">' + esc(ds.numero) + ' - ' + esc(ds.cliente||'') + '</span>'
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
// ── Lo que espera la firma del CEO ────────────────────────────────────────────
// Cada bloque se pinta por separado: si uno falla, deja su aviso y NO se lleva el resto de la
// pantalla. Y lo que no se pudo medir se DICE -- un cero que nadie calculo se lee como "no hay
// nada que hacer" y significa lo contrario (M154).
function _ceoEsc(x){
  return String(x==null?'':x).replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function _ceoCard(cls, titulo, numero, sub, cuerpo, ir){
  return '<div class="ceo-card '+cls+'">'
    + '<div class="ceo-card-h"><span class="ceo-card-t">'+titulo+'</span></div>'
    + '<div class="ceo-card-n">'+numero+'</div>'
    + (sub ? '<div class="ceo-card-s">'+sub+'</div>' : '')
    + (cuerpo || '')
    + (ir ? '<a class="ceo-ir" href="'+ir[1]+'">'+ir[0]+'</a>' : '')
    + '</div>';
}

function _ceoFilas(items, pinta, vacio, tope){
  if(!items || !items.length) return '<div class="ceo-lista"><div class="ceo-vacio">'+vacio+'</div></div>';
  var n = tope || 5;
  var h = '<div class="ceo-lista">' + items.slice(0, n).map(pinta).join('');
  if(items.length > n) h += '<div class="ceo-mas">y '+(items.length-n)+' más</div>';
  return h + '</div>';
}

async function loadDecisionesCEO(){
  var box = document.getElementById('ceo-decisiones');
  if(!box) return;
  try{
    var r = await fetch('/api/gerencia/decisiones-ceo', {credentials:'same-origin'});
    var d = await r.json();
    if(!d.ok){ box.innerHTML = '<div class="ceo-aviso">'+_ceoEsc(d.error||'No pude cargar')+'</div>'; return; }
    var h = '';

    // CAJA MENOR · el efectivo REAL. Lo que el veia antes era el numero que el mismo teclea
    // una vez al mes en el input de abajo, no lo que hay en la gaveta.
    if(d.caja){
      var cj = d.caja;
      var cuerpo = _ceoFilas(cj.pendientes, function(x){
        return '<div class="ceo-li"><span class="ceo-li-n">'+_ceoEsc(x.concepto)
          + ' <span class="ceo-li-q">· '+_ceoEsc(x.solicitado_por)+'</span></span>'
          + '<span class="ceo-li-v">'+fmt(x.monto)+'</span></div>';
      }, 'Nadie espera tu autorización', 5);
      var sub = 'disponible ' + fmt(cj.disponible)
        + (cj.comprometido > 0 ? ' · ' + fmt(cj.comprometido) + ' ya comprometido' : '');
      if(cj.sin_comprobante_n > 0)
        sub += ' · <span style="color:var(--cx-danger-text)">' + cj.sin_comprobante_n + ' pagos sin comprobante</span>';
      h += _ceoCard(cj.esperan_n > 0 ? 'espera' : 'ok', '💵 Caja menor',
                    fmt(cj.saldo) + ' <span style="font-size:.5em;font-weight:600;color:var(--cx-text-mute)">en la gaveta</span>',
                    sub, cuerpo, ['Ir a la caja', '/animus']);
    } else {
      h += _ceoCard('urge', '💵 Caja menor', '—', '', '<div class="ceo-aviso">No pude leerla</div>', null);
    }

    // CREADORES · con nombre y monto, no dos agregados
    if(d.influencers){
      var inf = d.influencers;
      var cuerpoI = _ceoFilas(inf.pendientes, function(x){
        var urg = (x.urgencia === 'vencido') ? ' style="color:var(--cx-danger-text)"' : '';
        return '<div class="ceo-li"><span class="ceo-li-n"'+urg+'>'+_ceoEsc(x.influencer_nombre || x.nombre || '?')
          + (x.urgencia === 'vencido' ? ' <span class="ceo-li-q">· vencido</span>' : '')
          + '</span><span class="ceo-li-v">'+fmt(x.monto)+'</span></div>';
      }, 'Ningún creador esperando pago', 5);
      h += _ceoCard(inf.vencidos_n > 0 ? 'urge' : (inf.n > 0 ? 'espera' : 'ok'),
                    '📣 Pagos a creadores', fmt(inf.monto),
                    inf.n + ' esperando' + (inf.vencidos_n > 0 ? ' · ' + inf.vencidos_n + ' VENCIDOS' : ''),
                    cuerpoI, ['Ir a pagar', '/hoy']);
    } else {
      h += _ceoCard('urge', '📣 Pagos a creadores', '—', '', '<div class="ceo-aviso">No pude leerlos</div>', null);
    }

    // COMPRAS que esperan su firma
    if(d.ocs_por_autorizar){
      var oc = d.ocs_por_autorizar;
      var tot = oc.reduce(function(a,x){ return a + (x.valor||0); }, 0);
      var cuerpoO = _ceoFilas(oc, function(x){
        return '<div class="ceo-li"><span class="ceo-li-n">'+_ceoEsc(x.proveedor||'?')
          + ' <span class="ceo-li-q">· '+_ceoEsc(x.numero_oc)+'</span></span>'
          + '<span class="ceo-li-v">'+fmt(x.valor)+'</span></div>';
      }, 'Ninguna orden esperando tu firma', 5);
      h += _ceoCard(oc.length > 0 ? 'espera' : 'ok', '🛒 Compras por autorizar',
                    fmt(tot), oc.length + ' órdenes revisadas', cuerpoO, ['Ir a Compras', '/compras']);
    }

    // CALIDAD · un lote sin liberar es plata parada en el estante
    if(d.calidad){
      var q = d.calidad;
      var tq = (q.lotes_por_liberar||0) + (q.mbr_por_aprobar||0);
      h += _ceoCard(tq > 0 ? 'espera' : 'ok', '🔬 Tu firma como Director Técnico',
                    fmtN(tq),
                    (q.lotes_por_liberar||0) + ' lotes por liberar · ' + (q.mbr_por_aprobar||0) + ' procedimientos por aprobar',
                    '<div class="ceo-lista"><div class="ceo-vacio">'
                    + (tq > 0 ? 'Un lote sin liberar es producto terminado que no se puede vender.'
                              : 'Nada esperando tu firma.') + '</div></div>',
                    ['Ir a la bandeja', '/mi-bandeja']);
    }

    box.innerHTML = h;
    if(d.avisos && d.avisos.length)
      box.innerHTML += '<div class="ceo-aviso">⚠ ' + d.avisos.map(_ceoEsc).join(' · ') + '</div>';
  }catch(e){
    box.innerHTML = '<div class="ceo-aviso">No pude cargar lo que espera tu decisión: '+_ceoEsc(e.message)+'</div>';
  }
}
loadDecisionesCEO();
setInterval(loadDecisionesCEO, 300000);

setInterval(loadKPIs, 300000);
setInterval(loadFlujoOperacional, 300000);

async function loadGerenciaExtra() {
  try {
    var d = await fetch('/api/gerencia/dashboard-extra').then(function(r){ return r.json(); });
    var nil = '<div style="color:var(--cx-text-faint);font-size:0.85em;">Sin datos</div>';
    var fmtV = function(n){ return n==null?'-':'$'+Number(n).toLocaleString('es-CO',{maximumFractionDigits:0}); };
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
        +'<div class="data-row" style="border-top:1px solid var(--cx-hairline);margin-top:4px;padding-top:4px;"><span class="data-lbl"><strong>Grand Total</strong></span><span class="data-val verde"><strong>'+fmtV(ig.total)+'</strong></span></div>';
    }

    // (AR/AP retirados: sus contenedores no existian y los conceptos eran inventados ·
    //  el AR/AP real vive en Compras y Contabilidad, adonde el encabezado ya manda)

    // Maquila pipeline
    var mqs = d.maquila_pipeline||[];
    var elM = document.getElementById('gx-maquila');
    if(elM){
      if(!mqs.length){ elM.innerHTML='<div style="color:var(--cx-text-faint);font-size:0.85em;">Sin ordenes activas</div>'; }
      else{
        elM.innerHTML = mqs.slice(0,4).map(function(m){
          return '<div class="data-row"><span class="data-lbl">'+esc(m.numero)+' - '+esc(m.cliente_nombre||'')+'</span><span class="data-val amarillo">'+fmtV(m.precio_lote)+'</span></div>';
        }).join('');
        if(mqs.length>4) elM.innerHTML += '<div style="color:var(--cx-text-faint);font-size:0.8em;padding:4px 0;">+'+(mqs.length-4)+' mas</div>';
      }
    }

    // Stock critico
    var sc = d.stock_critico||[];
    var elSC = document.getElementById('gx-stock');
    if(elSC){
      if(!sc.length){ elSC.innerHTML='<div style="color:var(--cx-success-text);font-size:0.85em;">Stock OK en todos los MPs</div>'; }
      else{
        elSC.innerHTML = sc.slice(0,6).map(function(mp){
          var pct = mp.stock_minimo>0?Math.round(mp.stock_actual/mp.stock_minimo*100):0;
          return '<div class="data-row"><span class="data-lbl">'+esc(mp.codigo_mp)+' '+esc(mp.nombre)+'</span>'
            +'<span class="data-val rojo">'+mp.stock_actual.toFixed(0)+'/'+mp.stock_minimo.toFixed(0)+' g ('+pct+'%)</span></div>';
        }).join('');
        if(sc.length>6) elSC.innerHTML += '<div style="color:var(--cx-text-faint);font-size:0.8em;">+'+(sc.length-6)+' MPs mas</div>';
      }
    }

    // SGSST
    var ss = d.sgsst_proximos||[];
    var elSS = document.getElementById('gx-sgsst');
    if(elSS){
      if(!ss.length){ elSS.innerHTML='<div style="color:var(--cx-success-text);font-size:0.85em;">Sin vencimientos proximos</div>'; }
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
        +'<div style="font-size:0.75em;color:var(--cx-text-faint);margin-top:6px;">YTD: '+fmtV(mt.ytd||0)+'</div>';
    }
    // Influencer spend
    var inf=d.influencer_spend||{}; var elInf=document.getElementById('gx-influencer');
    if(elInf){
      var infV=inf.ytd||0;
      elInf.innerHTML='<div class="data-row"><span class="data-lbl">Total YTD</span><span class="data-val '+(infV>5000000?'amarillo':'verde')+'">'+fmtV(infV)+'</span></div>'
        +'<div class="data-row"><span class="data-lbl">OCs generadas</span><span class="data-val">'+(inf.ocs||0)+'</span></div>'
        +'<div style="font-size:0.75em;color:var(--cx-text-faint);margin-top:6px;">Categorias: Influencer + Marketing</div>';
    }
    // Inventory COP
    var invC=d.inventory_cop||0; var elIC=document.getElementById('gx-inv-cop');
    if(elIC){
      elIC.innerHTML='<div style="font-size:1.8em;font-weight:900;color:var(--cx-primary-text);padding:8px 0 4px;">'+fmtV(invC)+'</div>'
        +'<div style="font-size:0.75em;color:var(--cx-text-faint);">Precio promedio OC x lotes activos</div>';
    }
    // Churn alerts
    var churns=d.churn_alerts||[]; var elCh=document.getElementById('gx-churn');
    if(elCh){
      if(!churns.length){ elCh.innerHTML='<div style="color:var(--cx-success-text);font-size:0.85em;">Todos los clientes activos &#10003;</div>'; }
      else{
        elCh.innerHTML=churns.slice(0,5).map(function(ch){
          return '<div class="churn-item"><div><div style="font-size:0.85em;color:var(--cx-text-soft);">'+esc(ch.nombre||'')+'</div>'
            +'<div style="font-size:0.72em;color:var(--cx-text-faint);">Ultimo: '+esc(ch.ultimo_pedido||'-')+'</div></div>'
            +'<span class="'+(ch.nivel==='critico'?'badge-crit':'badge-atenc')+'">'+(ch.dias||0)+'d</span></div>';
        }).join('');
        if(churns.length>5) elCh.innerHTML+='<div style="font-size:0.75em;color:var(--cx-text-faint);padding:4px 0;">+'+(churns.length-5)+' mas</div>';
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
    var fv = function(n){ if(n==null) return '-'; var v=Math.abs(n); return '$'+(v>=1000000?(v/1000000).toFixed(1)+'M':v>=1000?(v/1000).toFixed(0)+'K':v.toLocaleString('es-CO')); };

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
        +'<div style="width:'+pctA+'%;background:var(--cx-primary-light);" title="Aliados '+pctA+'%"></div>'
        +'<div style="width:'+pctS+'%;background:#34d399;" title="Shopify '+pctS+'%"></div>'
        +'</div>'
        +'<div style="display:flex;justify-content:space-between;font-size:10px;">'
        +'<span style="color:var(--cx-primary-light);">■ Aliados '+pctA+'%</span>'
        +'<span style="color:#34d399;">■ Shopify '+pctS+'%</span>'
        +'</div>'
        +'</div>'
        +'<div class="data-row"><span class="data-lbl">Aliados</span><span class="data-val verde">'+fv(canal.aliados_mes)+'</span></div>'
        +'<div class="data-row"><span class="data-lbl">Shopify</span><span class="data-val verde">'+fv(canal.shopify_mes)+'</span></div>'
        +'<div class="data-row"><span class="data-lbl">MoM canal</span><span class="data-val '+momClr+'">'+momTxt+'</span></div>'
        +'<div class="data-row" style="border-top:1px solid var(--cx-hairline);margin-top:4px;padding-top:4px;"><span class="data-lbl">Total mes</span><span class="data-val verde"><strong>'+fv(canal.total_mes)+'</strong></span></div>';
    }

    // Concentración de riesgo
    var riesgo = d.riesgo || {};
    var g4riesgo = document.getElementById('g4-riesgo');
    if(g4riesgo){
      var c1 = riesgo.concentracion_top1 || 0;
      var c3 = riesgo.concentracion_top3 || 0;
      var riesgoClr = c1 >= 50 ? 'rojo' : c1 >= 30 ? 'amarillo' : 'verde';
      var top3html = (riesgo.top3_aliados || []).map(function(a,i){
        return '<div class="data-row"><span class="data-lbl">'+(i+1)+'. '+esc(a.nombre)+'</span><span class="data-val">'+a.pct+'%</span></div>';
      }).join('');
      g4riesgo.innerHTML =
        '<div class="data-row"><span class="data-lbl">Top 1 aliado</span><span class="data-val '+riesgoClr+'">'+c1+'%</span></div>'
        +'<div class="data-row"><span class="data-lbl">Top 3 aliados</span><span class="data-val '+(c3>=70?'amarillo':'verde')+'">'+c3+'%</span></div>'
        +'<div style="margin:8px 0 4px;font-size:10px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.05em;">Top 3 detalle</div>'
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
          +'<div style="font-size:9px;color:var(--cx-text-mute);">'+fv(t.ticket)+'</div>'
          +'<div style="width:100%;max-width:40px;height:'+h+'px;background:linear-gradient(180deg,#a78bfa,#7c3aed);border-radius:4px 4px 0 0;align-self:flex-end;"></div>'
          +'<div style="font-size:10px;color:var(--cx-text-mute);">'+mesNm+'</div>'
          +'<div style="font-size:9px;color:var(--cx-text-faint);">'+t.pedidos+'p</div>'
          +'</div>';
      }).join('');
    } else if(g4trend){
      g4trend.innerHTML = '<div style="color:var(--cx-text-faint);font-size:0.85em;">Sin historial suficiente</div>';
    }

  } catch(e){ console.error('loadAliados4:', e); }
}

</script>
</body>
</html>"""
