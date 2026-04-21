# Auto-extraído de index.py — Fase A refactor
GERENCIA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Gerencia — HHA Group</title>
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
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-left">
    <a href="/" style="color:#a8a29e;text-decoration:none;font-size:12px;margin-right:4px;">&#8592; Inicio</a>
    <span class="logo">HHA GROUP</span>
    <span class="badge-ceo">PANEL GERENCIAL</span>
    <span class="periodo-badge" id="periodo-label">Cargando...</span>
  </div>
  <div style="display:flex;align-items:center;gap:12px;">
    <button class="refresh-btn" onclick="loadKPIs()">⟳ Actualizar</button>
    <span class="ultima-act" id="ultima-actualizacion"></span>
    <a href="/" style="font-size:12px;color:#a8a29e;text-decoration:none;">&#8592; Inicio</a>
  </div>
</div>

<div class="main">

  <!-- ALERTAS CRÍTICAS -->
  <div class="alertas-panel" id="alertas-panel">
    <div style="font-size:0.82em;font-weight:700;color:#fca5a5;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">⚠ Alertas que requieren acción</div>
    <div id="alertas-list"></div>
  </div>

  <!-- FINANCIERO (inputs manuales) -->
  <div class="section-title">💰 Financiero del mes</div>
  <div class="finanzas-grid">
    <div class="fin-card"><div class="fin-val" id="fin-caja">—</div><div class="fin-lbl">Saldo de caja</div></div>
    <div class="fin-card"><div class="fin-val" id="fin-animus">—</div><div class="fin-lbl">Ingresos ÁNIMUS</div></div>
    <div class="fin-card"><div class="fin-val" id="fin-maquila">—</div><div class="fin-lbl">Ingresos Maquila</div></div>
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
      <div class="panel-title"><span class="sem verde" id="sem-inv"></span>Inventario Espagiria</div>
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
    <a href="/recepcion" style="background:rgba(43,122,120,0.2);border:1px solid rgba(43,122,120,0.4);color:#7ACFCC;padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">📥 Recepción de Mercancía</a>
    <a href="/hub-salida" style="background:rgba(74,103,65,0.2);border:1px solid rgba(74,103,65,0.4);color:#8BC98A;padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">📤 Hub de Salida</a>
    <a href="/compras" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">🛒 Módulo Compras</a>
    <a href="/clientes" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">👤 Módulo Clientes</a>
    <a href="/financiero" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.6);padding:9px 18px;border-radius:8px;text-decoration:none;font-size:0.85em;font-weight:600;">💰 Financiero</a>
  </div>



  <!-- INDICADORES EJECUTIVOS -->
  <div class="section-title" style="margin-top:32px;">📊 Indicadores Ejecutivos — Tiempo Real</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:20px;">
    <div class="panel">
      <div class="panel-title">💰 Ingresos del mes (real)</div>
      <div id="gx-ingresos"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">📥 Cuentas por cobrar (AR)</div>
      <div id="gx-ar"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">📤 Cuentas por pagar (AP)</div>
      <div id="gx-ap"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">🏭 Pipeline Maquila activo</div>
      <div id="gx-maquila"><div style="color:rgba(255,255,255,0.3);font-size:0.85em;">Cargando...</div></div>
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

    // Espagiria KPIs
    var mpsBajos=e.mps_bajo_minimo||0;
    document.getElementById('val-mps-bajos').textContent=mpsBajos;
    document.getElementById('sub-deficit').textContent='Déficit: '+((e.deficit_total_kg||0).toFixed(1))+' kg';
    setKPIColor('kpi-mps-bajos','val-mps-bajos',mpsBajos>5?'rojo':(mpsBajos>0?'amarillo':'verde'));

    var meeBajos=e.mee_bajo_minimo||0;
    document.getElementById('val-mee-bajos').textContent=meeBajos;
    setKPIColor('kpi-mee-bajos','val-mee-bajos',meeBajos>3?'rojo':(meeBajos>0?'amarillo':'verde'));

    var v30=e.lotes_vencen_30d||0;
    document.getElementById('val-vencen30').textContent=v30;
    document.getElementById('sub-vencen60').textContent='En 60 días: '+(e.lotes_vencen_60d||0)+' lotes';
    setKPIColor('kpi-vencen30','val-vencen30',v30>0?'rojo':'verde');

    document.getElementById('val-lotes-mes').textContent=e.lotes_produccion_mes||0;
    document.getElementById('sub-kg-mes').textContent=(e.kg_producidos_mes||0)+' kg producidos';

    var ocs=e.ocs_pendientes_aprobacion||0;
    document.getElementById('val-ocs').textContent=ocs;
    document.getElementById('sub-ocs-val').textContent='Valor: '+fmt(e.valor_ocs_pendientes||0);
    setKPIColor('kpi-ocs','val-ocs',ocs>3?'amarillo':'verde');
    var solPend=e.sol_pendientes||0;
    document.getElementById('val-sol-pend').textContent=solPend;
    setKPIColor('kpi-sol-pend','val-sol-pend',solPend>0?'amarillo':'verde');

    // ÁNIMUS KPIs
    document.getElementById('val-uds-pt').textContent=fmtN(a.unidades_pt_disponibles||0);
    document.getElementById('sub-skus-pt').textContent=(a.skus_con_stock_pt||0)+' SKUs con stock';

    var pedAct=a.pedidos_activos||0;
    document.getElementById('val-pedidos-act').textContent=pedAct;
    document.getElementById('sub-pedidos-val').textContent='Valor: '+fmt(a.valor_pedidos_activos||0);

    var diasFM=a.dias_desde_ultimo_pedido_fm;
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
    di+='<div class="data-row"><span class="data-lbl">Lotes vencen 60d</span><span class="data-val '+(e.lotes_vencen_60d>0?'amarillo':'verde')+'">'+(e.lotes_vencen_60d||0)+'</span></div>';
    di+='<div class="data-row"><span class="data-lbl">Producción este mes</span><span class="data-val">'+(e.lotes_produccion_mes||0)+' lotes / '+(e.kg_producidos_mes||0)+' kg</span></div>';
    di+='<div class="data-row"><span class="data-lbl">OCs pendientes</span><span class="data-val '+(ocs>0?'amarillo':'verde')+'">'+ocs+' ('+fmt(e.valor_ocs_pendientes||0)+')</span></div>';
    di+='<div class="data-row"><span class="data-lbl">Solicitudes a Compras</span><span class="data-val '+(solPend>0?'amarillo':'verde')+'">'+solPend+' <a href="/compras" style="color:rgba(255,255,255,0.5);font-size:0.82em;">→ ver</a></span></div>';
    document.getElementById('detalle-inventario').innerHTML=di;

    // Detalle ÁNIMUS
    var da='';
    da+='<div class="data-row"><span class="data-lbl">Unidades PT disponibles</span><span class="data-val verde">'+fmtN(a.unidades_pt_disponibles||0)+'</span></div>';
    da+='<div class="data-row"><span class="data-lbl">SKUs con stock</span><span class="data-val">'+(a.skus_con_stock_pt||0)+'</span></div>';
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
    if(f.saldo_caja>0&&f.nomina_total>0&&f.saldo_caja<f.nomina_total*2) alertas.push({icon:'🔴',txt:'<strong>Caja baja:</strong> Saldo '+fmt(f.saldo_caja)+' cubre menos de 2 nóminas.'});

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
    if(f.nomina_total) document.getElementById('inp-nomina').value=f.nomina_total;
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
    if(elI) elI.innerHTML =
      '<div class="data-row"><span class="data-lbl">ANIMUS</span><span class="data-val verde">'+fmtV(ig.animus)+'</span></div>'
      +'<div class="data-row"><span class="data-lbl">Maquila</span><span class="data-val verde">'+fmtV(ig.maquila)+'</span></div>'
      +'<div class="data-row" style="border-top:1px solid rgba(255,255,255,0.1);margin-top:4px;padding-top:4px;"><span class="data-lbl"><strong>Total</strong></span><span class="data-val verde"><strong>'+fmtV(ig.total)+'</strong></span></div>';

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

  } catch(e){ console.error('loadGerenciaExtra:', e); }
}

loadGerenciaExtra();
setInterval(loadGerenciaExtra, 300000);
</script>
</body>
</html>"""
