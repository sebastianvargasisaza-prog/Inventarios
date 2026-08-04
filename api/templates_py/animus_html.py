"""ÁNIMUS Lab - Panel administrativo (Caja Menor + Inventario Cíclico).

Reemplaza el panel anterior que duplicaba funcionalidad con marketing
(productos / clientes / IG / contenido / agentes IA / calendario). Ahora
está enfocado en lo que Daniela necesita en la tienda:

  1. Caja menor: registrar ingresos (efectivo de ventas contraentrega) +
     egresos (gastos del local), ver saldo acumulado, KPIs hoy/mes.
  2. Inventario cíclico: contar físicamente cada producto, comparar con
     lo vendido en Shopify, registrar diferencias con explicación.

Si en el futuro el user pide volver a tener marketing en /animus, hay que
crear un redirect de vuelta a /marketing.
"""

ANIMUS_HTML = r"""<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ÁNIMUS Lab - Panel Administrativo</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:var(--cx-bg-alt);color:var(--cx-text);min-height:100vh;font-size:14px;}
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:var(--cx-card);}
::-webkit-scrollbar-thumb{background:var(--cx-text-soft);border-radius:3px;}

.hdr{background:var(--cx-card);border-bottom:1px solid var(--cx-border);padding:14px 20px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}
.hdr-brand{display:flex;align-items:center;gap:10px;}
.hdr-brand h1{font-size:16px;font-weight:800;color:var(--cx-text);}
.hdr-brand span{font-size:11px;color:var(--cx-text-mute);background:var(--cx-bg-alt);padding:2px 8px;border-radius:20px;border:1px solid var(--cx-border);}
.hdr-user{font-size:12px;color:var(--cx-text-mute);}
.hdr-user strong{color:var(--cx-text);}
.back-link{font-size:12px;color:var(--cx-primary-text);text-decoration:none;display:flex;align-items:center;gap:4px;}
.back-link:hover{text-decoration:underline;}

.tabs-bar{background:var(--cx-card);border-bottom:1px solid var(--cx-border);display:flex;overflow-x:auto;padding:0 20px;}
.tab-btn{padding:12px 20px;font-size:13px;font-weight:600;color:var(--cx-text-mute);border:none;background:none;cursor:pointer;white-space:nowrap;border-bottom:3px solid transparent;transition:.15s;}
.tab-btn:hover{color:var(--cx-text);}
.tab-btn.active{color:var(--cx-success-text);border-bottom-color:var(--cx-success);}
.sub-btn{padding:9px 18px;font-size:13px;font-weight:700;color:var(--cx-text-mute);border:none;background:none;cursor:pointer;border-bottom:3px solid transparent;border-radius:8px 8px 0 0;transition:.15s;}
.sub-btn:hover{color:var(--cx-text);background:var(--cx-bg-alt);}
.sub-btn.active{color:var(--cx-primary-text);border-bottom-color:var(--cx-primary);}
.tab-panel{display:none;padding:24px 20px;}
.tab-panel.active{display:block;}

.page-title{font-size:18px;font-weight:700;color:var(--cx-text);margin-bottom:4px;}
.page-sub{font-size:13px;color:var(--cx-text-mute);margin-bottom:18px;}

.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:20px;}
.kpi-card{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:12px;padding:16px;}
.kpi-card .label{font-size:10px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.08em;font-weight:700;}
.kpi-card .val{font-size:24px;font-weight:800;margin-top:6px;}
.kpi-card .sub{font-size:11px;color:var(--cx-text-mute);margin-top:4px;}
.kpi-green .val{color:var(--cx-success-text);}
.kpi-red .val{color:var(--cx-danger-text);}
.kpi-blue .val{color:var(--cx-info-text);}
.kpi-yellow .val{color:var(--cx-warn-text);}
.kpi-purple .val{color:var(--cx-primary-text);}

.card{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:12px;padding:18px;margin-bottom:16px;}
.card-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;}
.card-title{font-size:14px;font-weight:700;color:var(--cx-text);}

.btn{padding:8px 14px;border:none;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;transition:.15s;}
.btn-primary{background:linear-gradient(135deg,#10b981,#059669);color:#fff;}
.btn-primary:hover{filter:brightness(1.1);}
.btn-outline{background:transparent;border:1px solid var(--cx-text-soft);color:var(--cx-text-soft);}
.btn-outline:hover{background:var(--cx-border);}
.btn-danger{background:var(--cx-danger-pale);color:var(--cx-danger-text);border:1px solid var(--cx-danger);}
.btn-sm{padding:5px 10px;font-size:11px;}

.input,.select,.textarea{background:var(--cx-bg-alt);border:1px solid var(--cx-border);color:var(--cx-text);padding:8px 12px;border-radius:8px;font-size:13px;font-family:inherit;width:100%;}
.input:focus,.select:focus,.textarea:focus{outline:none;border-color:var(--cx-success);}
.textarea{min-height:60px;resize:vertical;}
.label{display:block;font-size:11px;color:var(--cx-text-mute);font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;}

.form-row{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;}
.form-row.full{grid-template-columns:1fr;}

table{width:100%;border-collapse:collapse;font-size:13px;}
table thead th{text-align:left;padding:8px 10px;color:var(--cx-text-mute);font-size:11px;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid var(--cx-border);background:var(--cx-bg-alt);}
table tbody td{padding:8px 10px;color:var(--cx-text);border-bottom:1px solid var(--cx-hairline);}
table tbody tr:hover{background:var(--cx-bg-alt);}


/* ── Caja Menor premium (4-ago) ──────────────────────────────────────────────
   El saldo es EL numero de una caja: va grande y solo. Los otros tres lo
   acompanan en una fila secundaria. Cuatro tarjetas iguales obligaban a leer
   las cuatro para encontrar la que importa. */
.caja-hero{display:grid;grid-template-columns:minmax(280px,1.15fr) 2fr;gap:16px;align-items:stretch;margin-bottom:18px;}
@media (max-width:900px){.caja-hero{grid-template-columns:1fr;}}
.caja-saldo{position:relative;overflow:hidden;background:var(--cx-primary-grad,linear-gradient(135deg,var(--cx-primary),var(--cx-primary-dark,var(--cx-primary))));border-radius:16px;padding:22px 24px;color:#fff;box-shadow:0 10px 30px rgba(0,0,0,.16);}
.caja-saldo::after{content:'';position:absolute;right:-40px;top:-40px;width:170px;height:170px;border-radius:50%;background:rgba(255,255,255,.10);}
.caja-saldo .rot{font-size:11px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;opacity:.85;}
.caja-saldo .cifra{font-size:2.6em;font-weight:800;line-height:1.05;margin:6px 0 2px;font-variant-numeric:tabular-nums;letter-spacing:-.02em;}
.caja-saldo .pie{font-size:12px;opacity:.85;}
.caja-mini{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}
@media (max-width:640px){.caja-mini{grid-template-columns:1fr;}}
.caja-mini .m{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:14px;padding:16px 18px;display:flex;flex-direction:column;justify-content:center;}
.caja-mini .rot{font-size:10.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--cx-text-mute);}
.caja-mini .cifra{font-size:1.55em;font-weight:800;line-height:1.15;margin-top:4px;font-variant-numeric:tabular-nums;}
.caja-mini .pie{font-size:11.5px;color:var(--cx-text-mute);margin-top:2px;}
/* Los montos de una tabla se comparan de arriba abajo: sin ancho fijo de cifra
   las columnas bailan renglon a renglon y hay que leer numero por numero. */
table td.monto,table th.monto{text-align:right;font-variant-numeric:tabular-nums;}

/* ── formularios con jerarquia ─────────────────────────────────────────────── */
.fm-seccion{font-size:10.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--cx-text-mute);margin:16px 0 8px;padding-bottom:5px;border-bottom:1px solid var(--cx-border);}
.fm-seccion:first-child{margin-top:0;}
.fm-destacado input,.fm-destacado select{font-size:1.05em;font-weight:600;}
.inv-btn{background:none;border:none;border-bottom:2px solid transparent;padding:8px 14px;font-size:13px;font-weight:600;color:var(--cx-text-mute);cursor:pointer;}
.inv-btn:hover{color:var(--cx-text);}
.inv-btn.active{color:var(--cx-primary-text);border-bottom-color:var(--cx-primary);}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;letter-spacing:.05em;}
.badge-green{background:var(--cx-success-pale);color:var(--cx-success-text);}
.badge-red{background:var(--cx-danger-pale);color:var(--cx-danger-text);}
.badge-yellow{background:var(--cx-warn-pale);color:var(--cx-warn-text);}
.badge-blue{background:var(--cx-info-pale);color:var(--cx-info-text);}
.badge-gray{background:var(--cx-bg-alt);color:var(--cx-text-mute);border:1px solid var(--cx-border);}

.diff-pos{color:var(--cx-success-text);font-weight:700;}
.diff-neg{color:var(--cx-danger-text);font-weight:700;}
.diff-zero{color:var(--cx-text-mute);}

#js-error-banner{display:none;position:fixed;top:0;left:0;right:0;z-index:10000;background:var(--cx-danger-pale);color:var(--cx-danger-text);padding:10px 16px;font-size:12px;font-family:monospace;border-bottom:2px solid var(--cx-danger);}
#toast-container{position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none;}
.toast{background:var(--cx-card);border:1px solid var(--cx-text-soft);color:var(--cx-text);padding:12px 18px;border-radius:8px;font-size:13px;font-weight:600;min-width:220px;max-width:360px;box-shadow:0 4px 20px rgba(0,0,0,.4);pointer-events:auto;}
.toast.success{background:var(--cx-success-pale);border-color:var(--cx-success);}
.toast.error{background:var(--cx-danger-pale);border-color:var(--cx-danger);}
</style>
</head>

<div id="js-error-banner"></div>
<div id="toast-container"></div>
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

// M63 - una accion que INSERTA no puede dispararse dos veces: el doble click en
// "Registrar movimiento" creaba DOS recibos y descuadraba el saldo de la caja.
// Se llavea por metodo+URL y se suelta apenas responde el servidor.
var _enVuelo = {};
async function _fetchUna(url, opts) {
  var k = ((opts && opts.method) || 'GET') + ' ' + url;
  if (_enVuelo[k]) return null;
  _enVuelo[k] = true;
  try { return await fetch(url, opts); } finally { delete _enVuelo[k]; }
}
fetch('/api/csrf-token', {credentials: 'same-origin'}).catch(function(){});
function showToast(msg, type){
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = 'toast ' + (type||'');
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(function(){ t.style.opacity='0'; t.style.transition='opacity .4s'; setTimeout(function(){t.remove();}, 400); }, 3200);
}
window.addEventListener('error', function(ev){
  try{
    const b = document.getElementById('js-error-banner');
    if (!b) return;
    const msg = (ev.message||(ev.error && ev.error.message)||'?') + ' @ ' + (ev.filename||'').split('/').pop() + ':' + (ev.lineno||'?');
    b.style.display='block';
    b.innerHTML = '! Error JS: ' + msg.substring(0,280);
  }catch(e){}
});
</script>

<body>

<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:var(--cx-primary-text);"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
  <div>
    <div class="cx-mod-header__title">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M12 3l1.9 5.4L19 10l-5.1 1.6L12 17l-1.9-5.4L5 10l5.1-1.6L12 3z"/><path d="M19 17l.6 1.7L21 19l-1.4.3L19 21l-.6-1.7L17 19l1.4-.3z"/></svg>
      ÁNIMUS Lab
    </div>
    <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; marca DTC &middot; Shopify &middot; <span style="color:var(--cx-text-faint)">{usuario}</span></div>
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
  <button class="tab-btn active" data-tab="caja" onclick="switchTab('caja')">&#128176; Caja Menor</button>
  <button class="tab-btn" data-tab="solic" onclick="switchTab('solic')">&#128203; Solicitudes</button>
  <button class="tab-btn" data-tab="novedades" onclick="switchTab('novedades')">&#128100; Novedades</button>
  <button class="tab-btn" data-tab="pqr" onclick="switchTab('pqr')">&#128233; PQR Clientes</button>
</div>

<!-- TAB: CAJA MENOR (incluye Contraentrega · 3-ago)
     La contraentrega no es otro modulo: es de DONDE viene el efectivo de esta caja. Cobrar un
     pedido ya asentaba el movimiento aca (mismo correlativo de recibo, enlazado por caja_mov_id),
     asi que a nivel de datos siempre fueron una sola cosa; lo unico separado era la pantalla.
     Junto, el tablero contesta las tres preguntas de una caja: cuanto tengo, cuanto me deben,
     y como lo cobro -- que separadas exigian ir y volver entre pestanas. -->
<div id="tab-caja" class="tab-panel active">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;margin-bottom:8px;">
    <div>
      <div class="page-title">&#128176; Caja Menor</div>
      <div class="page-sub">El efectivo del local: lo que entra por contraentrega, lo que sale, y lo que todavía está en la calle.</div>
    </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <button class="btn btn-outline" onclick="abrirArqueo()"
                title="Contar el efectivo real y cuadrar la caja contra la realidad">&#129518; Arquear</button>
        <button class="btn btn-outline" onclick="cerrarPeriodo()"
                title="Congelar todo hasta una fecha · despues de cerrar, corregir exige un movimiento nuevo">&#128274; Cerrar periodo</button>
        <button class="btn btn-primary" onclick="abrirRegistro('ingreso')">+ Registrar ingreso</button>
      </div>
  </div>

  <div id="caja-aviso-arqueo"></div>
  <div class="kpi-grid" id="caja-kpis"></div>


  <div class="subtabs" style="display:flex;gap:4px;border-bottom:1px solid var(--cx-border);margin:18px 0 18px;">
    <button class="sub-btn active" data-sub="cod" onclick="subTab('cod')">&#128666; Contraentrega</button>
    <button class="sub-btn" data-sub="mov" onclick="subTab('mov')">&#128184; La caja</button>
  </div>

  <div id="sub-cod" class="sub-panel">
  <!-- CONTRAENTREGA · la plata que todavia no entro, y el boton para hacerla entrar -->
  <div class="card">
    <div class="card-hdr">
      <div>
        <span class="card-title">&#128666; Contraentrega por cobrar</span>
        <div style="font-size:12px;color:var(--cx-text-mute);margin-top:2px;">
          Pedidos que se cobran al entregar. Al marcarlos, la plata entra a esta misma caja con su recibo.
        </div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <select id="cod-filtro" class="select" style="width:auto;" onchange="loadCod()">
          <option value="pendiente">Falta cobrar</option>
          <option value="">Todos</option>
          <option value="cobrado">Ya cobrados</option>
          <option value="descuadre">Con descuadre</option>
        </select>
        <input id="cod-desde" type="date" class="input" style="width:auto;" onchange="loadCod()">
        <input id="cod-hasta" type="date" class="input" style="width:auto;" onchange="loadCod()">
        <button class="btn btn-outline btn-sm" onclick="abrirMarcaCod()"
                title="Elegir con que etiqueta o medio de pago se marca la contraentrega en Shopify">&#9881; Marca</button>
        <button class="btn btn-primary btn-sm" onclick="importarPagados()"
                title="Asienta en caja las contraentregas que Shopify ya da por pagadas">&#128181; Registrar cobrados</button>
        <button class="btn btn-outline btn-sm" onclick="traerPedidos()"
                title="Trae de Shopify los pedidos de los ultimos 7 dias. El cron ya lo hace solo a las 6 AM: esto es para no esperar">&#128260; Traer pedidos</button>
        <button class="btn btn-outline btn-sm" onclick="syncBorradores()"
                title="Trae de Shopify los pedidos que todavia son BORRADOR: la contraentrega se crea asi y se completa recien cuando entra la plata">&#128229; Borradores</button>
      </div>
    </div>
    <div class="kpi-grid" id="cod-kpis" style="margin-bottom:14px;"></div>
    <div id="cod-aviso"></div>
    <div style="overflow-x:auto;">
      <table>
        <thead><tr>
          <th>Pedido</th>
          <th>Fecha</th>
          <th style="text-align:right;">En la calle</th>
          <th>Ciudad</th>
          <th style="text-align:right;">Valor</th>
          <th>Marca</th>
          <th>Origen</th>
          <th>Estado</th>
          <th></th>
        </tr></thead>
        <tbody id="cod-body"><tr><td colspan="9" style="color:var(--cx-text-mute);text-align:center;padding:24px;">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>

  </div>

  <div id="sub-mov" class="sub-panel" style="display:none;">
  <!-- PAGOS DESDE CAJA (3-ago) · solicitar -> autorizar -> pagar
       La caja no solo recibe: paga. Quien pide (Catalina/Luz), quien autoriza (gerencia) y
       quien paga (Daniela) son tres personas distintas, y el registro es UNO que cambia de
       estado. El saldo baja al PAGAR, no al autorizar: una autorizacion no es plata que salio. -->
  <div class="card">
    <div class="card-hdr">
      <div>
        <span class="card-title">&#128184; Pagos desde caja</span>
        <div style="font-size:12px;color:var(--cx-text-mute);margin-top:2px;">
          Lo que se pide, se autoriza y se paga con el efectivo de la caja.
        </div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <select id="sp-filtro" class="select" style="width:auto;" onchange="loadPagosCaja()">
          <option value="">Todas</option>
          <option value="solicitada">Esperan autorizacion</option>
          <option value="autorizada">Listas para pagar</option>
          <option value="pagada">Pagadas</option>
          <option value="rechazada">Rechazadas</option>
        </select>
        <button class="btn btn-primary btn-sm" onclick="abrirSolicitudPago()">+ Solicitar pago</button>
        <button class="btn btn-success btn-sm" onclick="abrirPagoDirecto()"
                title="Ya se pagó porque alguien lo pidió de palabra: sale de la caja y queda con su recibo">&#128179; Registrar pago</button>
        <button class="btn btn-outline btn-sm" onclick="abrirTraslado()"
                title="Consignar efectivo de la caja a la cuenta. NO es un gasto: la plata cambia de bolsillo">&#127974; Consignar</button>
      </div>
    </div>
    <div id="sp-aviso"></div>
    <div class="kpi-grid" id="sp-kpis" style="margin-bottom:14px;"></div>
    <div style="overflow-x:auto;">
      <table>
        <thead><tr>
          <th>N&deg;</th>
          <th>Fecha</th>
          <th>Concepto</th>
          <th>Empresa</th>
          <th style="text-align:right;">Monto</th>
          <th>Pidio</th>
          <th>Estado</th>
          <th>Respaldo</th>
          <th></th>
        </tr></thead>
        <tbody id="sp-body"><tr><td colspan="9" style="color:var(--cx-text-mute);text-align:center;padding:24px;">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <div class="card-hdr">
      <span class="card-title">&#128210; Movimientos de caja</span>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <select id="caja-filtro-tipo" class="select" style="width:auto;" onchange="loadCaja()">
          <option value="">Todos</option>
          <option value="ingreso">Solo ingresos</option>
          <option value="egreso">Solo egresos</option>
        </select>
        <input id="caja-filtro-q" class="input" style="width:200px;" placeholder="Buscar concepto..." oninput="loadCaja()">
        <button class="btn btn-outline btn-sm" onclick="abrirRegistro('egreso')">+ Egreso</button>
      </div>
    </div>
    <div style="overflow-x:auto;">
      <table>
        <thead><tr>
          <th>Recibo</th>
          <th>Fecha</th>
          <th>Tipo</th>
          <th>Concepto</th>
          <th style="text-align:right;">Monto</th>
          <th>Método</th>
          <th>Ref.</th>
          <th>Por</th>
          <th></th>
        </tr></thead>
        <tbody id="caja-body"><tr><td colspan="9" style="color:var(--cx-text-mute);text-align:center;padding:24px;">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

</div>   <!-- cierra tab-caja · faltaba desde antes de la fusion -->



<!-- MODAL: Baseline -->


<!-- MODAL: Entrada -->


<!-- MODAL: Salida -->


<!-- MODAL: Registrar conteo de SKU asignado -->


<!-- MODAL: Registro caja menor -->
<!-- MARCA DE CONTRAENTREGA (3-ago)
     La marca la escribe una PERSONA en Shopify, asi que nadie puede afirmar de memoria con que
     palabra la escribe -- y el detector traia 4 de 7.032 pedidos porque buscaba "contraentrega"
     y en los datos reales las etiquetas dicen otra cosa. En vez de pedir que alguien recuerde la
     etiqueta, se muestran las que EXISTEN con cuantos pedidos y cuanta plata lleva cada una, y
     se elige mirando numeros. Lo elegido se SUMA al patron (no lo reemplaza): siguen valiendo la
     nota "contraentrega" y lo que ya estaba. -->
<div id="modal-marca" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;">
  <div style="background:var(--cx-card);border:1px solid var(--cx-text-soft);border-radius:14px;padding:22px;width:820px;max-width:94vw;max-height:88vh;overflow-y:auto;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
      <h3 style="font-size:16px;color:var(--cx-text);">&#9881; Como se marca la contraentrega</h3>
      <button onclick="cerrarModal('modal-marca')" style="background:none;border:none;color:var(--cx-text-mute);font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div style="font-size:12px;color:var(--cx-text-mute);margin-bottom:14px;">
      Estas son las etiquetas y medios de pago que Shopify manda de verdad, con lo que representa cada uno.
      Marca el que significa contraentrega: los pedidos entran a la caja al instante, sin desplegar nada.
    </div>
    <div id="marca-cuerpo" style="font-size:13px;">Cargando...</div>
  </div>
</div>

<!-- SOLICITAR PAGO DESDE CAJA -->
<div id="modal-sp" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;">
  <div style="background:var(--cx-card);border:1px solid var(--cx-text-soft);border-radius:14px;padding:22px;width:520px;max-width:92vw;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <h3 style="font-size:16px;color:var(--cx-text);">&#128184; Solicitar pago desde caja</h3>
      <button onclick="cerrarModal('modal-sp')" style="background:none;border:none;color:var(--cx-text-mute);font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div class="form-row full">
      <div><label class="label">Concepto</label>
        <input id="sp-concepto" class="input" placeholder="Que se va a pagar"></div>
    </div>
    <div class="form-row">
      <div><label class="label">Monto</label>
        <input id="sp-monto" type="number" class="input" placeholder="0" oninput="spAvisarTope()"></div>
      <div><label class="label">Empresa</label>
        <select id="sp-empresa" class="select">
          <option value="ANIMUS">ANIMUS</option>
          <option value="ESPAGIRIA">Espagiria</option>
        </select></div>
    </div>
    <div class="form-row full">
      <div><label class="label">A quien se le paga</label>
        <input id="sp-beneficiario" class="input" placeholder="Proveedor o persona"></div>
    </div>
    <div class="form-row full">
      <div><label class="label">Cotizacion o pantallazo del precio</label>
        <input id="sp-cotiz" class="input" placeholder="Enlace de la cotizacion (opcional pero recomendado)">
        <div style="font-size:11px;color:var(--cx-text-mute);margin-top:4px;">
          Justifica el monto ANTES de autorizar &middot; sin esto se aprueba una cifra que nadie respaldo
        </div></div>
    </div>
    <div class="form-row full">
      <div><label class="label">Observaciones</label>
        <textarea id="sp-obs" class="textarea" placeholder="Opcional"></textarea></div>
    </div>
    <div id="sp-saldo-aviso" style="font-size:12px;margin-bottom:8px;"></div>
    <div id="sp-tope-aviso" style="font-size:12px;margin-bottom:12px;"></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-sp')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarSolicitudPago()">Enviar solicitud</button>
    </div>
  </div>
</div>

<!-- CONSIGNAR A LA CUENTA -->
<div id="modal-traslado" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;">
  <div style="background:var(--cx-card);border:1px solid var(--cx-text-soft);border-radius:14px;padding:22px;width:460px;max-width:92vw;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <h3 style="font-size:16px;color:var(--cx-text);">&#127974; Consignar a la cuenta</h3>
      <button onclick="cerrarModal('modal-traslado')" style="background:none;border:none;color:var(--cx-text-mute);font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div style="font-size:12px;color:var(--cx-text-mute);margin-bottom:14px;">
      Sale de la caja pero NO es un gasto: la plata cambia de bolsillo. Se registra aparte para
      que no infle los gastos del mes.
    </div>
    <div class="form-row">
      <div><label class="label">Monto</label>
        <input id="tr-monto" type="number" class="input" placeholder="0"></div>
      <div><label class="label">Empresa</label>
        <select id="tr-empresa" class="select">
          <option value="ANIMUS">ANIMUS</option>
          <option value="ESPAGIRIA">Espagiria</option>
        </select></div>
    </div>
    <div class="form-row full">
      <div><label class="label">Cuenta</label>
        <input id="tr-cuenta" class="input" placeholder="Banco y numero"></div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-traslado')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarTraslado()">Consignar</button>
    </div>
  </div>
</div>

<!-- PEDIR DATO · modal reusable (3-ago) · reemplaza los prompt()/confirm() nativos.
     Un prompt del navegador no se puede estilar, no muestra contexto y bloquea el hilo.
     Este devuelve una promesa, asi que el codigo que lo llama se lee igual que antes. -->
<div id="modal-pedir" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1200;align-items:center;justify-content:center;">
  <div style="background:var(--cx-card);border:1px solid var(--cx-border);border-radius:16px;padding:24px;width:460px;max-width:92vw;box-shadow:0 20px 60px rgba(0,0,0,.35);">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:6px;">
      <h3 id="pedir-titulo" style="font-size:17px;font-weight:800;color:var(--cx-text);margin:0;letter-spacing:-.01em;"></h3>
      <button onclick="_pedirCerrar(null)" style="background:none;border:none;color:var(--cx-text-mute);font-size:22px;cursor:pointer;line-height:1;">&times;</button>
    </div>
    <div id="pedir-sub" style="font-size:12.5px;color:var(--cx-text-mute);margin-bottom:16px;line-height:1.5;"></div>
    <div id="pedir-campo" style="margin-bottom:8px;"></div>
    <div id="pedir-error" style="font-size:12px;color:var(--cx-danger-text);min-height:16px;margin-bottom:10px;"></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn btn-outline" onclick="_pedirCerrar(null)">Cancelar</button>
      <button class="btn btn-primary" id="pedir-ok" onclick="_pedirAceptar()">Confirmar</button>
    </div>
  </div>
</div>

<!-- ARQUEO · contar el efectivo real (3-ago)
     El saldo era una SUMA que nadie habia contado nunca contra la gaveta: si faltaba plata,
     el sistema seguia diciendo su numero. El efectivo FISICO es la verdad. -->
<div id="modal-arqueo" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1100;align-items:center;justify-content:center;">
  <div style="background:var(--cx-card);border:1px solid var(--cx-border);border-radius:16px;padding:24px;width:520px;max-width:92vw;box-shadow:0 20px 60px rgba(0,0,0,.35);">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
      <h3 style="font-size:17px;font-weight:800;color:var(--cx-text);margin:0;">&#129518; Arqueo de caja</h3>
      <button onclick="cerrarModal('modal-arqueo')" style="background:none;border:none;color:var(--cx-text-mute);font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div style="font-size:12.5px;color:var(--cx-text-mute);margin-bottom:16px;line-height:1.5;">
      Conta el efectivo que hay en la gaveta y escribilo tal cual. Si no coincide con el
      sistema, la diferencia queda registrada con su motivo y los libros se ajustan a la
      realidad &mdash; porque la plata que esta es la verdad, no la que el sistema calculo.
    </div>
    <div style="background:var(--cx-bg-alt);border-radius:10px;padding:14px;margin-bottom:14px;">
      <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;">
        <span style="color:var(--cx-text-mute);">El sistema dice</span>
        <span id="arq-sistema" style="font-weight:800;color:var(--cx-text);">-</span>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:13px;">
        <span style="color:var(--cx-text-mute);">Ultimo arqueo</span>
        <span id="arq-ultimo" style="color:var(--cx-text-soft);">-</span>
      </div>
    </div>
    <div class="form-row">
      <div><label class="label">Cuanto contaste</label>
        <input id="arq-fisico" type="number" class="input" placeholder="0" oninput="arqAvisarDif()"></div>
      <div><label class="label">Fecha</label>
        <input id="arq-fecha" type="date" class="input"></div>
    </div>
    <div id="arq-dif" style="font-size:13px;margin:4px 0 10px;min-height:20px;"></div>
    <div class="form-row full">
      <div><label class="label">Motivo de la diferencia</label>
        <textarea id="arq-motivo" class="textarea" placeholder="Obligatorio si no cuadra"></textarea></div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-arqueo')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarArqueo()">Registrar arqueo</button>
    </div>
  </div>
</div>

<!-- TRAZABILIDAD · todo el recorrido de un recibo en una vista -->
<div id="modal-traza" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1100;align-items:center;justify-content:center;">
  <div style="background:var(--cx-card);border:1px solid var(--cx-border);border-radius:16px;padding:24px;width:720px;max-width:94vw;max-height:88vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.35);">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;">
      <h3 id="traza-titulo" style="font-size:17px;font-weight:800;color:var(--cx-text);margin:0;">Recorrido</h3>
      <button onclick="cerrarModal('modal-traza')" style="background:none;border:none;color:var(--cx-text-mute);font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div id="traza-cuerpo" style="font-size:13px;">Cargando...</div>
  </div>
</div>

<!-- COBRAR UNA CONTRAENTREGA (3-ago · Daniela)
     "a veces van y dicen 'yo transferi, le mande por Nequi', entonces no entregan efectivo".
     Esa plata entro de verdad, pero al BANCO. Si se registrara como efectivo, el arqueo nunca
     cuadraria: el sistema diria que hay billetes en la gaveta que nadie va a encontrar. -->
<!-- PAGO DIRECTO · lo que ya se autorizo de palabra (Sebastian 3-ago)
     "se le dijo pague papel burbuja, cualquier cosa que sea de Animus, entonces registra el
     pago con comprobante, concepto y demas". El flujo largo (pedir-autorizar-pagar) es para lo
     que se decide con tiempo; esto es el caso del dia. Lo unico que no se afloja es decir
     QUIEN lo autorizo: sin eso el pago no se puede verificar despues. -->
<!-- PEDIR ALGO · crea una solicitud que Catalina ve en su bandeja de usuarios -->
<!-- CAUSA RAIZ · "si hay menos o mas de una le genera una causa raiz, deben buscar por que"
     Una diferencia sin explicacion, a las dos semanas, ya no se puede reconstruir: nadie
     recuerda si fue un despacho sin registrar, una devolucion o un faltante real. -->
<!-- GESTIONAR UN PQR · que sirva para algo
     Antes solo cambiaba el estado, y habia que TECLEARLO. Ahora trae el PEDIDO del cliente
     (cruzado por correo, telefono o direccion), deja responder, y deja el rastro de quien
     respondio y cuando. -->
<div id="modal-pqrges" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1150;align-items:center;justify-content:center;">
  <div style="background:var(--cx-card);border:1px solid var(--cx-border);border-radius:16px;padding:24px;width:720px;max-width:95vw;max-height:92vh;overflow:auto;box-shadow:0 20px 60px rgba(0,0,0,.35);">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
      <h3 id="pq-titulo" style="font-size:17px;font-weight:800;color:var(--cx-text);margin:0;"></h3>
      <button onclick="cerrarModal('modal-pqrges')" style="background:none;border:none;color:var(--cx-text-mute);font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div id="pq-contacto" style="font-size:12.5px;color:var(--cx-text-mute);margin-bottom:14px;line-height:1.5;"></div>

    <div style="padding:12px 14px;background:var(--cx-bg-alt);border-radius:10px;font-size:13px;color:var(--cx-text-soft);line-height:1.55;margin-bottom:16px;">
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--cx-text-mute);margin-bottom:5px;">Lo que escribió</div>
      <div id="pq-desc"></div>
    </div>

    <div style="font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--cx-text-mute);margin-bottom:6px;">Su pedido</div>
    <div id="pq-pedidos" style="margin-bottom:16px;">
      <div style="color:var(--cx-text-mute);font-size:12.5px;">Buscando sus pedidos...</div>
    </div>

    <div class="form-row">
      <div><label class="label">Número de pedido</label>
        <input id="pq-pedido" class="input" placeholder="Se llena al elegir arriba, o se escribe"></div>
      <div><label class="label">Estado</label>
        <select id="pq-estado" class="select">
          <option value="nuevo">Nuevo</option>
          <option value="en_proceso">En proceso</option>
          <option value="resuelto">Resuelto</option>
          <option value="cerrado">Cerrado</option>
        </select></div>
    </div>
    <div class="form-row">
      <div><label class="label">Prioridad</label>
        <select id="pq-prioridad" class="select">
          <option value="alta">Alta</option>
          <option value="media">Media</option>
          <option value="baja">Baja</option>
        </select></div>
      <div><label class="label">Quién lo atiende</label>
        <input id="pq-asignado" class="input" placeholder="Quién se hace cargo"></div>
    </div>
    <div class="form-row full">
      <div><label class="label">Respuesta al cliente</label>
        <textarea id="pq-respuesta" class="textarea" style="min-height:90px;" placeholder="Lo que se le contestó · queda con quién respondió y cuándo"></textarea></div>
    </div>
    <div id="pq-hist" style="font-size:11.5px;color:var(--cx-text-mute);margin-bottom:12px;"></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-pqrges')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarPqrGestion()">Guardar</button>
    </div>
  </div>
</div>



<div id="modal-solic" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1150;align-items:center;justify-content:center;">
  <div style="background:var(--cx-card);border:1px solid var(--cx-border);border-radius:16px;padding:24px;width:640px;max-width:94vw;max-height:92vh;overflow:auto;box-shadow:0 20px 60px rgba(0,0,0,.35);">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
      <h3 style="font-size:17px;font-weight:800;color:var(--cx-text);margin:0;">&#128203; Pedir algo para ÁNIMUS</h3>
      <button onclick="cerrarModal('modal-solic')" style="background:none;border:none;color:var(--cx-text-mute);font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div style="font-size:12.5px;color:var(--cx-text-mute);margin-bottom:16px;line-height:1.5;">
      Va a la bandeja de Compras. Vas a ver acá mismo cuándo se autoriza, cuándo se paga y
      cuándo va en camino, y marcás vos misma que llegó.
    </div>
    <div class="fm-seccion">Qué se necesita</div>
    <div class="form-row fm-destacado">
      <div><label class="label">Qué se necesita</label>
        <input id="so-nombre" class="input" placeholder="Papel burbuja, cinta, resma de papel..."></div>
      <div><label class="label">Categoría</label>
        <select id="so-cat" class="select">
          <option value="Consumibles">Consumibles</option>
          <option value="Papelería">Papelería</option>
          <option value="Aseo">Aseo</option>
          <option value="EPP">Dotación / EPP</option>
          <option value="Servicios">Servicio</option>
          <option value="Otro">Otro</option>
        </select></div>
    </div>
    <div class="form-row">
      <div><label class="label">Cuánto</label>
        <input id="so-cant" type="number" class="input" value="1"></div>
      <div><label class="label">Unidad</label>
        <select id="so-unidad" class="select">
          <option value="und">Unidades</option>
          <option value="rollo">Rollos</option>
          <option value="caja">Cajas</option>
          <option value="paquete">Paquetes</option>
          <option value="servicio">Servicio</option>
          <option value="g">Gramos</option>
        </select></div>
    </div>
    <div class="fm-seccion">Para cuándo y para qué</div>
    <div class="form-row">
      <div><label class="label">Urgencia</label>
        <select id="so-urg" class="select">
          <option value="Normal">Normal</option>
          <option value="Alta">Alta</option>
          <option value="Urgente">Urgente</option>
        </select></div>
      <div><label class="label">Para cuándo</label>
        <input id="so-fecha" type="date" class="input"></div>
    </div>
    <div class="form-row full">
      <div><label class="label">Para qué es</label>
        <textarea id="so-just" class="textarea" placeholder="Sin esto Compras no sabe si priorizarlo"></textarea></div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-solic')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarSolicitud()">Enviar la solicitud</button>
    </div>
  </div>
</div>

<!-- REGISTRAR UNA NOVEDAD DEL EQUIPO -->
<div id="modal-novedad" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1150;align-items:center;justify-content:center;">
  <div style="background:var(--cx-card);border:1px solid var(--cx-border);border-radius:16px;padding:24px;width:640px;max-width:94vw;max-height:92vh;overflow:auto;box-shadow:0 20px 60px rgba(0,0,0,.35);">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
      <h3 style="font-size:17px;font-weight:800;color:var(--cx-text);margin:0;">&#128100; Registrar una novedad</h3>
      <button onclick="cerrarModal('modal-novedad')" style="background:none;border:none;color:var(--cx-text-mute);font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div style="font-size:12.5px;color:var(--cx-text-mute);margin-bottom:16px;line-height:1.5;">
      Le llega a Recursos Humanos y a Gerencia por la campana, y queda registrado quién la
      escribió y quién la resolvió.
    </div>
    <div id="nv-aviso-gente"></div>
    <div class="form-row">
      <div><label class="label">De quién es</label>
        <select id="nv-empleado" class="select"><option value="">Cargando...</option></select></div>
      <div><label class="label">Tipo</label>
        <select id="nv-tipo" class="select">
          <option value="permiso">Permiso</option>
          <option value="cita_medica">Cita médica</option>
          <option value="enfermedad">Incapacidad</option>
          <option value="licencia">Licencia</option>
          <option value="salud">Salud</option>
          <option value="otro">Administrativa / otra</option>
        </select></div>
    </div>
    <div class="form-row full">
      <div><label class="label">Asunto</label>
        <input id="nv-asunto" class="input" placeholder="Permiso de dos horas el jueves"></div>
    </div>
    <div class="form-row">
      <div><label class="label">Desde</label>
        <input id="nv-desde" type="date" class="input"></div>
      <div><label class="label">Hasta</label>
        <input id="nv-hasta" type="date" class="input"></div>
    </div>
    <div class="form-row full">
      <div><label class="label">Detalle</label>
        <textarea id="nv-desc" class="textarea" placeholder="Lo que Recursos Humanos necesita saber para decidir"></textarea></div>
    </div>
    <div class="form-row full">
      <div><label class="label">Soporte (incapacidad, orden médica...)</label>
        <input id="nv-foto" type="file" class="input" accept="image/*,.pdf"
               capture="environment" onchange="subirSoporte()"
               style="padding:9px 12px;">
        <input type="hidden" id="nv-adjunto">
        <div id="nv-foto-estado" style="font-size:12px;color:var(--cx-text-mute);margin-top:6px;">
          Sacale una foto o eligela del celular &middot; la ve Recursos Humanos y gerencia
        </div>
      </div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-novedad')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarNovedad()">Registrar y avisar</button>
    </div>
  </div>
</div>

<div id="modal-pagodir" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1150;align-items:center;justify-content:center;">
  <div style="background:var(--cx-card);border:1px solid var(--cx-border);border-radius:16px;padding:24px;width:600px;max-width:94vw;max-height:92vh;overflow:auto;box-shadow:0 20px 60px rgba(0,0,0,.35);">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
      <h3 style="font-size:17px;font-weight:800;color:var(--cx-text);margin:0;">&#128179; Registrar un pago de la caja</h3>
      <button onclick="cerrarModal('modal-pagodir')" style="background:none;border:none;color:var(--cx-text-mute);font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div style="font-size:12.5px;color:var(--cx-text-mute);margin-bottom:16px;line-height:1.5;">
      Para lo que ya se pagó porque alguien lo pidió de palabra. Sale de la caja en el momento
      y queda con su recibo. <b id="pd-saldo" style="color:var(--cx-text-soft);"></b>
    </div>
    <div class="form-row">
      <div><label class="label">Qué se pagó</label>
        <input id="pd-concepto" class="input" placeholder="Papel burbuja, domicilio, cinta..."></div>
      <div><label class="label">Cuánto</label>
        <input id="pd-monto" type="number" class="input" oninput="pdChequearSaldo()"></div>
    </div>
    <div id="pd-alerta" style="font-size:12.5px;margin:2px 0 10px;min-height:18px;"></div>
    <div class="form-row">
      <div><label class="label">A quién se le pagó</label>
        <input id="pd-beneficiario" class="input" placeholder="Proveedor o persona"></div>
      <div><label class="label">Empresa</label>
        <select id="pd-empresa" class="select">
          <option value="ANIMUS">ANIMUS Lab</option>
          <option value="ESPAGIRIA">Espagiria</option>
        </select></div>
    </div>
    <div class="form-row">
      <div><label class="label">Quién lo autorizó</label>
        <select id="pd-quien" class="select">
          <option value="Sebastian">Sebastián (gerencia)</option>
          <option value="Catalina">Catalina (compras)</option>
          <option value="Luz">Luz (Espagiria)</option>
          <option value="Alejandro">Alejandro</option>
        </select></div>
      <div><label class="label">Fecha del pago</label>
        <input id="pd-fecha" type="date" class="input"></div>
    </div>
    <div class="form-row full">
      <div><label class="label">Comprobante (foto del recibo o enlace)</label>
        <input id="pd-comprobante" class="input" placeholder="Se puede subir después, pero queda contado como pago sin respaldo"></div>
    </div>
    <div class="form-row full">
      <div><label class="label">Observaciones</label>
        <textarea id="pd-obs" class="textarea" placeholder="Lo que haga falta recordar de este pago"></textarea></div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-pagodir')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarPagoDirecto()">Registrar el pago</button>
    </div>
  </div>
</div>

<div id="modal-cobro" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1150;align-items:center;justify-content:center;">
  <div style="background:var(--cx-card);border:1px solid var(--cx-border);border-radius:16px;padding:24px;width:520px;max-width:92vw;box-shadow:0 20px 60px rgba(0,0,0,.35);">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
      <h3 id="cob-titulo" style="font-size:17px;font-weight:800;color:var(--cx-text);margin:0;"></h3>
      <button onclick="cerrarModal('modal-cobro')" style="background:none;border:none;color:var(--cx-text-mute);font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <div id="cob-sub" style="font-size:12.5px;color:var(--cx-text-mute);margin-bottom:16px;line-height:1.5;"></div>
    <div class="form-row">
      <div><label class="label">Cuanto entro</label>
        <input id="cob-monto" type="number" class="input" oninput="cobAvisarDif()"></div>
      <div><label class="label">Como pago</label>
        <select id="cob-metodo" class="select" onchange="cobCambiaMetodo()">
          <option value="efectivo">Efectivo</option>
          <option value="transferencia">Transferencia</option>
          <option value="nequi">Nequi</option>
          <option value="daviplata">Daviplata</option>
        </select></div>
    </div>
    <div id="cob-dif" style="font-size:12.5px;margin:2px 0 10px;min-height:18px;"></div>
    <div id="cob-no-efectivo" style="display:none;">
      <div style="padding:10px 14px;background:var(--cx-info-pale);border-left:3px solid var(--cx-info);border-radius:8px;font-size:12px;color:var(--cx-text-soft);margin-bottom:12px;">
        Esta plata entra al <b>banco</b>, no a la gaveta: no suma al efectivo de la caja y queda
        registrada en Tesoreria.
      </div>
      <div class="form-row full">
        <div><label class="label">Numero de la transferencia</label>
          <input id="cob-ref" class="input" placeholder="Sin esto no se puede conciliar contra el extracto"></div>
      </div>
      <div class="form-row full">
        <div><label class="label">Comprobante (foto o enlace)</label>
          <input id="cob-comprobante" class="input" placeholder="https://..."></div>
      </div>
    </div>
    <div class="form-row full">
      <div><label class="label">Observaciones</label>
        <textarea id="cob-obs" class="textarea" placeholder="Obligatorio si el monto no coincide"></textarea></div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-cobro')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarCobro()">Registrar cobro</button>
    </div>
  </div>
</div>

<div id="modal-caja" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;">
  <div style="background:var(--cx-card);border:1px solid var(--cx-text-soft);border-radius:14px;padding:22px;width:480px;max-width:92vw;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <h3 id="modal-caja-title" style="font-size:16px;color:var(--cx-text);">Registrar movimiento</h3>
      <button onclick="cerrarModal('modal-caja')" style="background:none;border:none;color:var(--cx-text-mute);font-size:22px;cursor:pointer;">&times;</button>
    </div>
    <input type="hidden" id="caja-tipo">
    <div class="form-row">
      <div><div class="label">Fecha</div><input id="caja-fecha" type="date" class="input"></div>
      <div><div class="label">Monto (COP) *</div><input id="caja-monto" type="number" min="0" step="100" class="input" placeholder="0"></div>
    </div>
    <div class="form-row full"><div><div class="label">Concepto *</div><input id="caja-concepto" class="input" placeholder="Ej: Pago contraentrega orden #1234"></div></div>
    <div class="form-row">
      <div><div class="label">Método</div>
        <select id="caja-metodo" class="select"><option>efectivo</option><option>transferencia</option><option>tarjeta</option><option>otro</option></select>
      </div>
      <div><div class="label">Referencia (opcional)</div><input id="caja-referencia" class="input" placeholder="N orden, factura, etc."></div>
    </div>
    <div class="form-row full"><div><div class="label">Observaciones</div><textarea id="caja-obs" class="textarea" placeholder="Notas adicionales..."></textarea></div></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px;">
      <button class="btn btn-outline" onclick="cerrarModal('modal-caja')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarCaja()">Guardar</button>
    </div>
  </div>
</div>

<!-- MODAL: Conteo ciclico -->


<!-- TAB: PQR CLIENTES (comercial · llega del triaje de Aseguramiento o manual) -->
<!-- TAB: SOLICITUDES · pedir, seguir el estado, y recibir en el mismo lugar
     El ciclo (pendiente -> OC autorizada -> pagada/en transito -> recibida) lo calcula
     /api/solicitudes-compra/mis, que existe desde el 29-abr para esta misma necesidad. Aca
     solo se muestra: reimplementar el calculo del paso habria creado un segundo criterio que
     diverge del que ve Catalina (M5). -->
<div id="tab-solic" class="tab-panel">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;margin-bottom:8px;">
    <div>
      <div class="page-title">&#128203; Solicitudes</div>
      <div class="page-sub">Lo que se pide para ÁNIMUS: en qué va cada cosa y dónde se marca que llegó.</div>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <select id="sol-filtro" class="select" style="width:auto;" onchange="loadSolicitudes()">
        <option value="abiertas">En curso</option>
        <option value="cerradas">Cerradas</option>
        <option value="todas">Todas</option>
      </select>
      <button class="btn btn-primary btn-sm" onclick="abrirSolicitud()">+ Pedir algo</button>
    </div>
  </div>

  <div class="kpi-grid" id="sol-kpis"></div>

  <div class="card" style="margin-top:14px;">
    <div style="overflow-x:auto;">
      <table>
        <thead><tr>
          <th>N&deg;</th><th>Fecha</th><th>Qué se pidió</th><th>Urgencia</th>
          <th>En qué va</th><th>Proveedor</th><th></th>
        </tr></thead>
        <tbody id="sol-body"><tr><td colspan="7" style="color:var(--cx-text-mute);text-align:center;padding:24px;">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- TAB: NOVEDADES DE PERSONAL
     Daniela es la encargada del equipo de ANIMUS: registra permisos, citas medicas,
     incapacidades y novedades administrativas de su gente. Se apoya en las notificaciones de
     bienestar (mismo circuito que RRHH ya aprueba) para que el numero de ausencias de RRHH sea
     el real y no uno paralelo. -->
<div id="tab-novedades" class="tab-panel">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;margin-bottom:8px;">
    <div>
      <div class="page-title">&#128100; Novedades del equipo</div>
      <div class="page-sub">Permisos, citas médicas, incapacidades y novedades administrativas. Le llega a Recursos Humanos y a Gerencia, y queda el rastro de quién la registró y quién la resolvió.</div>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <select id="nov-filtro" class="select" style="width:auto;" onchange="loadNovedades()">
        <option value="">Todas</option>
        <option value="pendiente">Sin resolver</option>
        <option value="aprobada">Aprobadas</option>
        <option value="rechazada">Rechazadas</option>
      </select>
      <button class="btn btn-primary btn-sm" onclick="abrirNovedad()">+ Registrar novedad</button>
    </div>
  </div>

  <div class="kpi-grid" id="nov-kpis"></div>

  <div class="card" style="margin-top:14px;">
    <div style="overflow-x:auto;">
      <table>
        <thead><tr>
          <th>De quién</th><th>Tipo</th><th>Asunto</th><th>Desde</th><th>Hasta</th>
          <th>Estado</th><th>Resolvió</th>
        </tr></thead>
        <tbody id="nov-body"><tr><td colspan="7" style="color:var(--cx-text-mute);text-align:center;padding:24px;">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<div id="tab-pqr" class="tab-panel">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;margin-bottom:8px;">
    <div>
      <div class="page-title">&#128233; PQR Clientes</div>
      <div class="page-sub">Peticiones, quejas y reclamos <b>comerciales</b> de ÁNIMUS: envíos, producto equivocado, faltantes, devoluciones, servicio. Los de calidad del producto los maneja Aseguramiento (Espagiria).</div>
    </div>
    <button class="btn btn-primary" onclick="abrirPqrManual()">+ Registrar PQR</button>
  </div>
  <div class="kpi-grid" id="pqr-ani-kpis"></div>

  <!-- INDICADOR (Sebastian 3-ago: "PQR debe dar finalmente un indicador que se refleje en el
       dashboard de ANIMUS y sume a CEO para saber que esta pasando")
       El numero que importa no es CUANTAS quejas hay -- eso sube solo si se vende mas -- sino
       cuantas por cada 100 pedidos: eso si dice si el servicio empeoro. -->
  <div class="card" id="pqr-indicador" style="margin:14px 0;">
    <div style="color:var(--cx-text-mute);font-size:12.5px;">Cargando el indicador...</div>
  </div>
  <div style="margin:8px 0;display:flex;gap:6px;flex-wrap:wrap">
    <select id="pqr-ani-festado" onchange="loadAnimusPqr()" style="padding:6px 10px;border:1px solid var(--cx-hairline,#cbd5e1);border-radius:6px">
      <option value="">Todos los estados</option>
      <option value="nuevo">Nuevos</option>
      <option value="en_proceso">En proceso</option>
      <option value="resuelto">Resueltos</option>
      <option value="cerrado">Cerrados</option>
    </select>
    <button class="btn btn-outline" onclick="loadAnimusPqr()">&#x21BB; Refrescar</button>
  </div>
  <div id="pqr-ani-list"><p style="color:var(--cx-text-faint);text-align:center;padding:14px">Cargando...</p></div>
</div>

<!-- Modal registrar PQR manual -->
<div id="modal-pqr-ani" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;">
  <div style="background:var(--cx-card);border:1px solid var(--cx-text-soft);border-radius:14px;padding:22px;width:520px;max-width:92vw;">
    <h3 style="margin-top:0;color:var(--cx-text)">Registrar PQR comercial</h3>
    <label style="font-size:12px;color:var(--cx-text-soft)">Tipo</label>
    <select id="pqr-ani-tipo" style="width:100%;padding:8px;border:1px solid var(--cx-border);border-radius:6px;margin-bottom:8px">
      <option value="envio">Envío</option><option value="producto_equivocado">Producto equivocado</option>
      <option value="faltante">Faltante</option><option value="devolucion">Devolución</option>
      <option value="servicio">Servicio</option><option value="facturacion">Facturación</option>
      <option value="comercial">Comercial</option><option value="otro">Otro</option>
    </select>
    <label style="font-size:12px;color:var(--cx-text-soft)">Cliente</label>
    <input id="pqr-ani-cliente" style="width:100%;padding:8px;border:1px solid var(--cx-border);border-radius:6px;margin-bottom:8px" placeholder="Nombre del cliente">
    <label style="font-size:12px;color:var(--cx-text-soft)">Descripción</label>
    <textarea id="pqr-ani-desc" rows="3" style="width:100%;padding:8px;border:1px solid var(--cx-border);border-radius:6px;margin-bottom:8px" placeholder="Qué pasó..."></textarea>
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button class="btn btn-outline" onclick="cerrarModal('modal-pqr-ani')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarPqrManual()">Guardar</button>
    </div>
  </div>
</div>

<script>
// Tabs
const _loaded = {};
function switchTab(name){
  document.querySelectorAll('.tab-btn').forEach(function(b){
    b.classList.toggle('active', b.dataset.tab === name);
  });
  document.querySelectorAll('.tab-panel').forEach(function(p){p.classList.remove('active');});
  const panel = document.getElementById('tab-' + name);
  if (panel) panel.classList.add('active');
  if (!_loaded[name]) { _loaded[name] = true; loadTab(name); }
}
// Sub-pestanas de Caja Menor (3-ago · Sebastian: "deberia ir caja menor en dos subpestanas").
// Dos trabajos distintos -cobrar lo que esta en la calle y manejar la plata que hay- obligaban
// a scrollear 46 filas para pasar de uno al otro.
// Conmutador PROPIO: `switchTab` apaga todos los `.tab-panel` y dejaria la pantalla en blanco.
function subTab(name){
  document.querySelectorAll('.sub-btn').forEach(function(b){
    b.classList.toggle('active', b.dataset.sub === name);
  });
  document.querySelectorAll('.sub-panel').forEach(function(p){
    p.style.display = (p.id === 'sub-' + name) ? '' : 'none';
  });
  try { localStorage.setItem('caja-sub', name); } catch(e){}
}

function loadTab(name){
  // Caja Menor trae las dos mitades: lo que YA entro (movimientos) y lo que falta entrar
  // (contraentrega en la calle). Sin la segunda, el saldo se lee como si no faltara nada.
  if (name === 'caja') {
    loadCaja(); loadCod(); loadPagosCaja(); cargarAvisoArqueo();
    try { var _sb = localStorage.getItem('caja-sub'); if (_sb) subTab(_sb); } catch(e){}
  }
  else if (name === 'solic') loadSolicitudes();
  else if (name === 'novedades') loadNovedades();
  else if (name === 'pqr') { loadAnimusPqr(); cargarPqrIndicador(); }
}

function fmtCOP(n){
  if (n == null) return '$ 0';
  return '$ ' + Number(n).toLocaleString('es-CO', {maximumFractionDigits:0});
}
function fmtFecha(s){
  if (!s) return '-';
  return s.slice(0, 10);
}
function esc(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function abrirModal(id){ const m=document.getElementById(id); if(m) m.style.display='flex'; }
function cerrarModal(id){ const m=document.getElementById(id); if(m) m.style.display='none'; }

// Caja Menor
// Helpers de presentacion para las pestanas nuevas. Emiten las clases que el modulo YA
// tiene (.kpi-grid/.kpi-card/.badge): inventar clases propias deja la pantalla sin estilo y
// sin un solo error a la vista.
function _kpiHtml(cards){
  return cards.map(function(c){
    var col = {success:'kpi-green', danger:'kpi-red', info:'kpi-blue',
               warn:'kpi-yellow', primary:'kpi-blue'}[c.tono] || '';
    return '<div class="kpi-card ' + col + '">'
      + '<div class="label">' + esc(c.label) + '</div>'
      + '<div class="val">' + c.val + '</div>'
      + (c.sub ? '<div class="sub">' + esc(c.sub) + '</div>' : '')
      + '</div>';
  }).join('');
}

function _badge(txt, tono){
  var cl = {success:'badge-green', danger:'badge-red', info:'badge-blue',
            warn:'badge-yellow', primary:'badge-blue'}[tono] || 'badge-gray';
  return '<span class="badge ' + cl + '">' + esc(txt || '') + '</span>';
}

// "Hoy" en Colombia, para pre-llenar fechas.
// NO se usa `new Date().toISOString()`: eso da la fecha UTC, y despues de las 19:00 en Colombia
// ya rodo al dia siguiente -- el modal de caja llego a pre-llenar el dia de MANANA (M106/M24).
// Se corre el reloj -5h y recien ahi se toma la fecha.
function hoyCol(){
  var d = new Date(Date.now() - 5 * 3600 * 1000);
  return d.toISOString().slice(0, 10);
}

// ═══ PQR · indicador, pedido del cliente y gestionar ════════════════════════
var _PQR_ACTUAL = null;

// El vocabulario de tipos YA existe en la pagina (_PQR_TIPO_LBL): un segundo diccionario
// diverge en cuanto alguien agregue un tipo, y la pantalla mostraria dos nombres distintos.
function _pqrTipo(t){ return (window._PQR_TIPO_LBL || {})[t] || t; }

async function cargarPqrIndicador(){
  var el = document.getElementById('pqr-indicador');
  if (!el) return;
  try {
    var r = await fetch('/api/animus/pqr/indicador?dias=30', {credentials:'same-origin'});
    var d = await r.json();
    if (!d.ok) { el.style.display = 'none'; return; }
    // Sin pedidos la tasa NO es cero: es "no se puede calcular". Un cero se leeria como
    // "el servicio esta perfecto", que es lo contrario de lo que pasa (M124).
    var tasa = (d.tasa_por_100 === null || d.tasa_por_100 === undefined)
      ? '<span style="color:var(--cx-text-mute);font-size:.5em;">sin datos</span>'
      : d.tasa_por_100;
    var resp = (d.dias_respuesta_promedio === null || d.dias_respuesta_promedio === undefined)
      ? '<span style="color:var(--cx-text-mute);font-size:.5em;">sin responder</span>'
      : d.dias_respuesta_promedio + ' d';
    var tipos = (d.por_tipo || []).slice(0,4).map(function(t){
      return '<span class="badge badge-gray" style="margin-right:5px;">' + esc(_pqrTipo(t.tipo)) + ' ' + t.n + '</span>';
    }).join('');
    // Un aviso que no ENVEJECE a la vista se vuelve ruido (M129): el mas viejo lleva su edad.
    var viejo = d.mas_viejo
      ? '<div style="margin-top:10px;font-size:12.5px;color:' + ((d.mas_viejo.dias > 7) ? 'var(--cx-danger-text)' : 'var(--cx-text-mute)') + ';">'
        + 'El más viejo sin resolver: <b>' + esc(d.mas_viejo.codigo) + '</b>'
        + ((d.mas_viejo.dias != null) ? ' · lleva <b>' + d.mas_viejo.dias + ' días</b>' : '')
        + '</div>'
      : '';
    function _bloque(rot, val, sub, color){
      return '<div><div style="font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--cx-text-mute);">' + rot + '</div>'
        + '<div style="font-size:1.9em;font-weight:800;line-height:1.2;color:' + (color || 'var(--cx-text)') + ';">' + val + '</div>'
        + '<div style="font-size:11.5px;color:var(--cx-text-mute);">' + sub + '</div></div>';
    }
    el.style.display = '';
    el.innerHTML =
      '<div style="display:flex;flex-wrap:wrap;gap:26px;align-items:flex-start;">'
      + _bloque('PQR por cada 100 pedidos', tasa, d.pqr + ' quejas sobre ' + d.pedidos + ' pedidos (30 días)')
      + _bloque('Tardamos en responder', resp, d.respondidos + ' respondidas')
      + _bloque('Sin tocar', d.sin_tocar, d.abiertos + ' abiertas en total',
                d.sin_tocar ? 'var(--cx-warn-text)' : 'var(--cx-success-text)')
      + '<div style="flex:1;min-width:210px;"><div style="font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--cx-text-mute);margin-bottom:6px;">Por qué se quejan</div>'
      + (tipos || '<span style="color:var(--cx-text-mute);font-size:12px;">sin datos</span>') + '</div>'
      + '</div>' + viejo
      + (d.aviso ? '<div style="margin-top:8px;font-size:12px;color:var(--cx-warn-text);">' + esc(d.aviso) + '</div>' : '');
  } catch(e) { el.style.display = 'none'; }
}

function gestionarPqr(id){
  var p = (window._PQR_ROWS || []).filter(function(x){ return x.id === id; })[0];
  if (!p) return;
  _PQR_ACTUAL = p;
  document.getElementById('pq-titulo').textContent = (p.codigo || p.id) + ' · ' + _pqrTipo(p.tipo);
  document.getElementById('pq-contacto').innerHTML =
    '<b>' + esc(p.contacto_nombre || 'Sin nombre') + '</b>'
    + (p.contacto_email ? ' · ' + esc(p.contacto_email) : '')
    + (p.contacto_telefono ? ' · ' + esc(p.contacto_telefono) : '')
    + (p.canal ? ' · llegó por ' + esc(p.canal) : '');
  document.getElementById('pq-desc').textContent = p.descripcion || '';
  document.getElementById('pq-pedido').value = p.pedido_numero || '';
  document.getElementById('pq-estado').value = p.estado || 'nuevo';
  document.getElementById('pq-prioridad').value = p.prioridad || 'media';
  document.getElementById('pq-asignado').value = p.asignado_a || '';
  document.getElementById('pq-respuesta').value = p.respuesta || '';
  document.getElementById('pq-hist').innerHTML = p.respondido_por
    ? 'Respondió ' + esc(p.respondido_por) + (p.respondido_en ? ' el ' + esc(p.respondido_en) : '')
    : '';
  document.getElementById('pq-pedidos').innerHTML =
    '<div style="color:var(--cx-text-mute);font-size:12.5px;">Buscando sus pedidos...</div>';
  document.getElementById('modal-pqrges').style.display = 'flex';
  cargarPedidosDelCliente(id);
}

async function cargarPedidosDelCliente(id){
  var el = document.getElementById('pq-pedidos');
  try {
    var r = await fetch('/api/animus/pqr/' + id + '/pedidos-cliente', {credentials:'same-origin'});
    var d = await r.json();
    var cand = d.candidatos || [];
    if (!cand.length) {
      el.innerHTML = '<div style="color:var(--cx-text-mute);font-size:12.5px;">'
        + esc(d.aviso || 'No encontré pedidos de este cliente') + '</div>';
      return;
    }
    // Se MUESTRAN como candidatos y no se adjudica solo: adjudicarle el pedido equivocado a una
    // queja termina respondiendole a alguien sobre el pedido de otro (M19).
    el.innerHTML = cand.map(function(x){
      return '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;'
        + 'padding:8px 12px;border:1px solid var(--cx-border);border-radius:8px;margin-bottom:6px;">'
        + '<div><b>' + esc(x.pedido) + '</b> <span style="color:var(--cx-text-mute);font-size:11.5px;">'
        + esc(x.fecha) + ' · ' + fmtCOP(x.total) + ' · cruzó por ' + esc(x.cruzo_por) + '</span></div>'
        + '<button class="btn btn-outline btn-sm" onclick="elegirPedidoPqr(&quot;' + esc(x.pedido) + '&quot;)">Es este</button>'
        + '</div>';
    }).join('');
  } catch(e) {
    el.innerHTML = '<div style="color:var(--cx-text-mute);font-size:12.5px;">No pude buscar sus pedidos</div>';
  }
}

function elegirPedidoPqr(num){
  document.getElementById('pq-pedido').value = num;
  showToast('Pedido ' + num + ' · se guarda al dar Guardar', 'success');
}

async function guardarPqrGestion(){
  if (!_PQR_ACTUAL) return;
  var body = {
    estado: document.getElementById('pq-estado').value,
    prioridad: document.getElementById('pq-prioridad').value,
    asignado_a: document.getElementById('pq-asignado').value.trim(),
    pedido_numero: document.getElementById('pq-pedido').value.trim()
  };
  var resp = document.getElementById('pq-respuesta').value.trim();
  if (resp && resp !== (_PQR_ACTUAL.respuesta || '')) body.respuesta = resp;
  // Cerrar sin haber escrito nada deja al cliente sin respuesta y el caso marcado como resuelto.
  if ((body.estado === 'resuelto' || body.estado === 'cerrado') && !resp) {
    showToast('Escribí qué se le contestó antes de cerrarlo', 'error'); return;
  }
  try {
    var r = await _fetchUna('/api/animus/pqr/' + _PQR_ACTUAL.id, _fetchOpts('PATCH', body));
    if (!r) return;
    var d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    showToast('Guardado · ' + (_PQR_ACTUAL.codigo || ''), 'success');
    cerrarModal('modal-pqrges');
    loadAnimusPqr(); cargarPqrIndicador();
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

// ═══ INVENTARIO · sub-pestanas ══════════════════════════════════════════════
// Conmutador PROPIO: `switchTab` apaga TODOS los .tab-panel y dejaria la pantalla en blanco.


// ═══ EXISTENCIAS · lo que dice Shopify contra lo que espera EOS ══════════════
// Sebastian: "que aparezcan todos los SKU de Shopify con la cantidad que dice Shopify que hay".
// Antes solo se comparaba el esperado de EOS contra el conteo: un SKU podia estar bien en EOS y
// mal en Shopify -- que es el numero con el que se VENDE -- y nadie lo veia.
var _EXI = [];





// ═══ CAUSA RAIZ ═════════════════════════════════════════════════════════════
var _CR_ID = null;





// ═══ SOLICITUDES · pedir, seguir y recibir ═══════════════════════════════════
// El paso del ciclo lo calcula el backend (/api/solicitudes-compra/mis). Aca NO se recalcula:
// si la pantalla dedujera su propio estado, Daniela y Catalina verian cosas distintas del
// mismo pedido (M5 · el numero mostrado tiene que ser el que decide).
// El COLOR sale del paso, no del hex que manda el backend: esos hex estan fijos y en tema
// oscuro quedarian ilegibles (M104).
var _SOL_ROWS = [];

function _solTono(paso){
  if (paso === 6) return 'success';
  if (paso === 0) return 'danger';
  if (paso === 4 || paso === 5) return 'info';
  if (paso === 3) return 'primary';
  return 'warn';
}

async function loadSolicitudes(){
  var tb = document.getElementById('sol-body');
  try {
    var filtro = document.getElementById('sol-filtro').value;
    var r = await fetch('/api/solicitudes-compra/mis?ambito=animus&estado='
                        + encodeURIComponent(filtro),
                        {credentials:'same-origin'});
    var d = await r.json();
    if (d.error) { tb.innerHTML = '<tr><td colspan="7" class="empty">' + esc(d.error) + '</td></tr>'; return; }
    _SOL_ROWS = d.solicitudes || [];
    window._SOL_ROWS = _SOL_ROWS;

    var enCurso = _SOL_ROWS.filter(function(x){ return !x.cerrado; }).length;
    var porRecibir = _SOL_ROWS.filter(function(x){ return x.puede_marcar_recibido; }).length;
    var recibidas = _SOL_ROWS.filter(function(x){ return x.paso === 6; }).length;
    var esperando = _SOL_ROWS.filter(function(x){ return x.paso === 1; }).length;
    document.getElementById('sol-kpis').innerHTML = _kpiHtml([
      {label:'En curso', val:enCurso, sub:'pedidos abiertos'},
      {label:'Esperando autorización', val:esperando, sub:'Compras todavía no las tomó', tono:esperando?'warn':''},
      {label:'Por recibir', val:porRecibir, sub:'ya vienen en camino', tono:porRecibir?'info':''},
      {label:'Recibidas', val:recibidas, sub:'cerradas', tono:'success'}
    ]);

    if (!_SOL_ROWS.length) {
      tb.innerHTML = '<tr><td colspan="7" class="empty">Nada por acá. Con <b>Pedir algo</b> arrancás una solicitud.</td></tr>';
      return;
    }
    tb.innerHTML = _SOL_ROWS.map(function(x, i){
      var acc = x.puede_marcar_recibido
        ? '<button class="btn btn-primary btn-sm" onclick="marcarRecibido(' + i + ')">Ya llegó</button>'
        : (x.paso === 6 ? '<span style="color:var(--cx-success-text);font-size:12px;">recibida</span>' : '');
      return '<tr>'
        + '<td><b>' + esc(x.numero||'') + '</b>'
          + (x.numero_oc ? '<div style="font-size:11px;color:var(--cx-text-mute);">' + esc(x.numero_oc) + '</div>' : '')
        + '</td>'
        + '<td>' + esc((x.fecha||'').slice(0,10)) + '</td>'
        + '<td>' + esc(x.observaciones || '-') + '</td>'
        + '<td>' + _badge(x.urgencia || 'Normal', x.urgencia === 'Urgente' ? 'danger' : (x.urgencia === 'Alta' ? 'warn' : '')) + '</td>'
        + '<td>' + _badge(x.paso_label || '', _solTono(x.paso)) + '</td>'
        + '<td>' + esc(x.oc_proveedor || '-') + '</td>'
        + '<td style="text-align:right;">' + acc + '</td>'
        + '</tr>';
    }).join('');
  } catch(e) {
    tb.innerHTML = '<tr><td colspan="7" class="empty">No pude cargar: ' + esc(e.message) + '</td></tr>';
  }
}

function abrirSolicitud(){
  document.getElementById('so-nombre').value = '';
  document.getElementById('so-cant').value = 1;
  document.getElementById('so-just').value = '';
  document.getElementById('so-fecha').value = '';
  document.getElementById('modal-solic').style.display = 'flex';
}

async function guardarSolicitud(){
  var nombre = document.getElementById('so-nombre').value.trim();
  if (!nombre) { showToast('Falta qué se necesita', 'error'); return; }
  var just = document.getElementById('so-just').value.trim();
  var cant = parseFloat(document.getElementById('so-cant').value || 1) || 1;
  var unidad = document.getElementById('so-unidad').value;
  var body = {
    empresa: 'Animus',
    categoria: document.getElementById('so-cat').value,
    tipo: 'Compra',
    area: 'ANIMUS',
    urgencia: document.getElementById('so-urg').value,
    fecha_requerida: document.getElementById('so-fecha').value,
    // El resumen va en observaciones porque es lo que la lista y la bandeja de Compras muestran.
    observaciones: nombre + ' · ' + cant + ' ' + unidad + (just ? ' · ' + just : ''),
    items: [{ codigo_mp: '', nombre_mp: nombre, cantidad_g: cant,
              unidad: unidad, justificacion: just }]
  };
  try {
    var r = await _fetchUna('/api/solicitudes-compra', _fetchOpts('POST', body));
    if (!r) return;
    var d = await r.json();
    if (d.error) { showToast('Error: ' + d.error, 'error'); return; }
    showToast('Solicitud ' + (d.numero || '') + ' enviada a Compras', 'success');
    cerrarModal('modal-solic');
    loadSolicitudes();
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

async function marcarRecibido(i){
  var x = _SOL_ROWS[i];
  if (!x) return;
  var ok = await pedirDato({
    titulo: 'Marcar como recibido',
    tipo: 'confirmar',
    sub: '¿Ya llegó lo de <b>' + esc(x.numero) + '</b>?<br>'
       + '<span style="color:var(--cx-text-mute);">' + esc(x.observaciones || '') + '</span>',
    confirmar: 'Sí, llegó'});
  if (!ok) return;
  try {
    var r = await _fetchUna('/api/solicitudes-compra/' + encodeURIComponent(x.numero) + '/marcar-recibido-solicitante',
                            _fetchOpts('POST', {}));
    if (!r) return;
    var d = await r.json();
    if (d.error) { showToast('Error: ' + d.error, 'error'); return; }
    showToast('Listo · ' + x.numero + ' queda como recibida', 'success');
    loadSolicitudes();
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

// ═══ NOVEDADES DEL EQUIPO ════════════════════════════════════════════════════
// Se apoya en las notificaciones de bienestar: mismo circuito que RRHH ya aprueba, para que
// el conteo de ausencias de RRHH sea el real y no uno paralelo (M37).
var _NOV_ROWS = [];
var _NOV_TIPOS = {permiso:'Permiso', cita_medica:'Cita médica', enfermedad:'Incapacidad',
                  licencia:'Licencia', salud:'Salud', otro:'Administrativa'};

async function loadNovedades(){
  var tb = document.getElementById('nov-body');
  try {
    var f = document.getElementById('nov-filtro').value;
    var r = await fetch('/api/bienestar/notificaciones' + (f ? '?estado=' + encodeURIComponent(f) : ''),
                        {credentials:'same-origin'});
    var d = await r.json();
    if (d.error) { tb.innerHTML = '<tr><td colspan="7" class="empty">' + esc(d.error) + '</td></tr>'; return; }
    _NOV_ROWS = d.notificaciones || [];

    var pend = _NOV_ROWS.filter(function(x){ return x.estado === 'pendiente'; }).length;
    var apr = _NOV_ROWS.filter(function(x){ return x.estado === 'aprobada'; }).length;
    var rech = _NOV_ROWS.filter(function(x){ return x.estado === 'rechazada'; }).length;
    document.getElementById('nov-kpis').innerHTML = _kpiHtml([
      {label:'Sin resolver', val:pend, sub:'esperan a Recursos Humanos', tono:pend?'warn':''},
      {label:'Aprobadas', val:apr, sub:'con visto bueno', tono:'success'},
      {label:'Rechazadas', val:rech, sub:'', tono:rech?'danger':''},
      {label:'Registradas', val:_NOV_ROWS.length, sub:'en total'}
    ]);

    if (!_NOV_ROWS.length) {
      tb.innerHTML = '<tr><td colspan="7" class="empty">Sin novedades registradas.</td></tr>';
      return;
    }
    tb.innerHTML = _NOV_ROWS.map(function(x){
      var tono = x.estado === 'aprobada' ? 'success'
               : (x.estado === 'rechazada' ? 'danger'
               : (x.estado === 'vista' ? 'info' : 'warn'));
      return '<tr>'
        + '<td><b>' + esc(x.empleado_nombre || x.empleado_username || '') + '</b>'
          + (x.registrado_por ? '<div style="font-size:11px;color:var(--cx-text-mute);">la registró ' + esc(x.registrado_por) + '</div>' : '')
        + '</td>'
        + '<td>' + esc(_NOV_TIPOS[x.tipo] || x.tipo || '') + '</td>'
        + '<td>' + esc(x.asunto || '')
          + (x.adjunto_url ? ' <a href="' + esc(x.adjunto_url) + '" target="_blank" style="color:var(--cx-info-text);font-size:11px;">ver soporte</a>' : '')
        + '</td>'
        + '<td>' + esc(x.fecha_inicio || '-') + '</td>'
        + '<td>' + esc(x.fecha_fin || '-') + '</td>'
        + '<td>' + _badge(x.estado || '', tono) + '</td>'
        + '<td>' + esc(x.resuelto_por || '-')
          + (x.comentario_jefe ? '<div style="font-size:11px;color:var(--cx-text-mute);">' + esc(x.comentario_jefe) + '</div>' : '')
        + '</td>'
        + '</tr>';
    }).join('');
  } catch(e) {
    tb.innerHTML = '<tr><td colspan="7" class="empty">No pude cargar: ' + esc(e.message) + '</td></tr>';
  }
}

async function abrirNovedad(){
  document.getElementById('nv-asunto').value = '';
  document.getElementById('nv-desc').value = '';
  document.getElementById('nv-adjunto').value = '';
  document.getElementById('nv-desde').value = hoyCol();
  document.getElementById('nv-hasta').value = '';
  document.getElementById('nv-foto').value = '';
  document.getElementById('nv-foto-estado').innerHTML =
    'Sacale una foto o eligela del celular &middot; la ve Recursos Humanos y gerencia';
  var sel = document.getElementById('nv-empleado');
  // La lista sale del maestro de empleados: escribir el nombre a mano crearia una persona
  // distinta por cada forma de escribirla y RRHH no podria agrupar nada (M115).
  try {
    var r = await fetch('/api/animus/empleados', {credentials:'same-origin'});
    var d = await r.json();
    var gente = d.empleados || [];
    sel.innerHTML = gente.length
      ? gente.map(function(e){
          return '<option value="' + esc(e.username || '') + '" data-nombre="' + esc(e.nombre || '') + '">'
               + esc(e.nombre || e.username) + (e.cargo ? ' · ' + esc(e.cargo) : '') + '</option>';
        }).join('')
      : '<option value="">Sin empleados cargados</option>';
    // A quien no se encontro en el maestro se DICE: si no, esa persona simplemente no aparece
    // en el desplegable y nadie sabe por que.
    var av = document.getElementById('nv-aviso-gente');
    if (av) av.innerHTML = d.aviso
      ? '<div style="padding:8px 12px;background:var(--cx-warn-pale);border-left:3px solid var(--cx-warn);border-radius:8px;font-size:12px;color:var(--cx-warn-text);margin-bottom:12px;">'
        + esc(d.aviso) + '</div>' : '';
  } catch(e) {
    sel.innerHTML = '<option value="">No pude cargar la lista</option>';
  }
  document.getElementById('modal-novedad').style.display = 'flex';
}

async function subirSoporte(){
  var inp = document.getElementById('nv-foto');
  var est = document.getElementById('nv-foto-estado');
  var f = inp.files && inp.files[0];
  if (!f) { document.getElementById('nv-adjunto').value = ''; return; }
  est.innerHTML = 'Subiendo <b>' + esc(f.name) + '</b>...';
  try {
    var fd = new FormData();
    fd.append('foto', f);
    var t = await (await fetch('/api/csrf-token', {credentials:'same-origin'})).json();
    var r = await fetch('/api/animus/novedades/soporte',
      {method:'POST', credentials:'same-origin', body: fd,
       headers: {'X-CSRF-Token': t.csrf_token}});
    var d = await r.json();
    if (!d.ok) {
      // Un "subido" que no subio nada es peor que un error: el soporte se daria por guardado.
      document.getElementById('nv-adjunto').value = '';
      inp.value = '';
      est.innerHTML = '<span style="color:var(--cx-danger-text);">' + esc(d.error || 'No se pudo subir') + '</span>';
      return;
    }
    document.getElementById('nv-adjunto').value = d.url;
    est.innerHTML = '<span style="color:var(--cx-success-text);">Listo</span> &middot; '
      + '<a href="' + esc(d.url) + '" target="_blank" style="color:var(--cx-info-text);">ver la foto</a>';
  } catch(e) {
    document.getElementById('nv-adjunto').value = '';
    est.innerHTML = '<span style="color:var(--cx-danger-text);">Error de red al subir</span>';
  }
}

async function guardarNovedad(){
  var asunto = document.getElementById('nv-asunto').value.trim();
  if (!asunto) { showToast('Falta el asunto', 'error'); return; }
  var sel = document.getElementById('nv-empleado');
  var opt = sel.options[sel.selectedIndex];
  if (!sel.value) { showToast('Falta de quién es la novedad', 'error'); return; }
  var body = {
    empleado_username: sel.value,
    empleado_nombre: opt ? (opt.getAttribute('data-nombre') || opt.textContent) : '',
    tipo: document.getElementById('nv-tipo').value,
    asunto: asunto,
    descripcion: document.getElementById('nv-desc').value.trim(),
    fecha_inicio: document.getElementById('nv-desde').value,
    fecha_fin: document.getElementById('nv-hasta').value,
    adjunto_url: document.getElementById('nv-adjunto').value.trim()
  };
  try {
    var r = await _fetchUna('/api/bienestar/notificaciones', _fetchOpts('POST', body));
    if (!r) return;
    var d = await r.json();
    if (d.error) { showToast('Error: ' + d.error, 'error'); return; }
    showToast(d.aviso || 'Novedad registrada', 'success');
    cerrarModal('modal-novedad');
    loadNovedades();
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

async function loadCaja(){
  const tipo = document.getElementById('caja-filtro-tipo').value;
  const q    = document.getElementById('caja-filtro-q').value.trim();
  const qs = [];
  if (tipo) qs.push('tipo=' + encodeURIComponent(tipo));
  if (q)    qs.push('q=' + encodeURIComponent(q));
  const url = '/api/animus/caja' + (qs.length ? '?' + qs.join('&') : '');
  try {
    const r = await fetch(url);
    const d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    renderCajaKPIs(d.kpis||{});
    renderCajaMovs(d.movimientos||[]);
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
  }
}

function renderCajaKPIs(k){
  const saldo = k.saldo_total || 0;
  window._CAJA_SALDO = saldo;   // lo leen el pago directo y el arqueo
  const neto  = (k.ingreso_mes||0) - (k.egreso_mes||0);
  const cards = [
    { label: 'Saldo en caja', val: fmtCOP(saldo),
      color: saldo >= 0 ? 'kpi-green' : 'kpi-red',
      sub: (k.n_total||0) + ' movimientos con recibo' },
    { label: 'Entro hoy', val: fmtCOP(k.ingreso_hoy||0), color:'kpi-green', sub: '' },
    { label: 'Salio hoy', val: fmtCOP(k.egreso_hoy||0), color:'kpi-red', sub: '' },
    // El NETO del mes es el numero que dice si la caja crecio o se comio la plata; entro y
    // salio por separado no lo contestan de un vistazo.
    { label: 'Neto del mes', val: fmtCOP(neto),
      color: neto >= 0 ? 'kpi-blue' : 'kpi-red',
      sub: fmtCOP(k.ingreso_mes||0) + ' entro &middot; ' + fmtCOP(k.egreso_mes||0) + ' salio' },
  ];
  // El SALDO va solo y grande: es el numero por el que se abre una caja. Los otros tres
  // acompanan. Cuatro tarjetas identicas obligaban a leer las cuatro para encontrar esa.
  var _p = cards[0], _r = cards.slice(1);
  document.getElementById('caja-kpis').innerHTML =
    '<div class="caja-hero">'
    + '<div class="caja-saldo">'
    +   '<div class="rot">' + _p.label + '</div>'
    +   '<div class="cifra">' + _p.val + '</div>'
    +   '<div class="pie">' + (_p.sub || '') + '</div>'
    + '</div>'
    + '<div class="caja-mini">'
    +   _r.map(function(c){
          var col = c.color === 'kpi-red' ? 'var(--cx-danger-text)'
                  : (c.color === 'kpi-green' ? 'var(--cx-success-text)' : 'var(--cx-text)');
          return '<div class="m"><div class="rot">' + c.label + '</div>'
               + '<div class="cifra" style="color:' + col + ';">' + c.val + '</div>'
               + (c.sub ? '<div class="pie">' + c.sub + '</div>' : '') + '</div>';
        }).join('')
    + '</div></div>';
}

function renderCajaMovs(rows){
  const body = document.getElementById('caja-body');
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="9" style="color:var(--cx-text-mute);text-align:center;padding:24px;">Sin movimientos registrados.</td></tr>';
    return;
  }
  body.innerHTML = rows.map(function(m){
    // Un recibo ANULADO se sigue viendo (por eso se anula en vez de borrar): tachado, con quien
    // lo anulo y por que. El hueco en el correlativo es justamente lo que se quiere poder ver.
    const anul = !!m.anulado;
    const tipoBadge = m.tipo === 'ingreso'
      ? '<span class="badge badge-green">+ Ingreso</span>'
      : '<span class="badge badge-red">- Egreso</span>';
    const monto = m.tipo === 'ingreso'
      ? '<span class="diff-pos">+' + fmtCOP(m.monto) + '</span>'
      : '<span class="diff-neg">-' + fmtCOP(m.monto) + '</span>';
    const recibo = m.recibo_numero
      ? '<a href="#" onclick="verTraza(&quot;'+esc(m.recibo_numero)+'&quot;);return false;"'
        + ' title="Ver todo el recorrido de este movimiento"'
        + ' style="font-family:ui-monospace,monospace;font-weight:700;font-size:12px;color:var(--cx-primary-text);text-decoration:none;">'
        + esc(m.recibo_numero)+'</a>'
      : '<span style="color:var(--cx-text-mute);font-size:11px;">sin numero</span>';
    const motivo = anul
      ? '<div style="font-size:10px;color:var(--cx-danger-text);margin-top:2px;">Anulado por '
        + esc(m.anulado_por||'?') + (m.anulado_motivo ? ' &middot; ' + esc(m.anulado_motivo) : '') + '</div>'
      : '';
    const accion = anul
      ? '<span class="badge badge-gray" title="Anulado">ANULADO</span>'
      : '<button class="btn btn-outline btn-sm" onclick="anularCaja('+m.id+')" title="Anular recibo">Anular</button>';
    return '<tr style="' + (anul ? 'opacity:.55;text-decoration:line-through;' : '') + '">' +
      '<td>'+recibo+'</td>' +
      '<td>'+fmtFecha(m.fecha)+'</td>' +
      '<td>'+tipoBadge+'</td>' +
      '<td style="text-decoration:none;">'+esc(m.concepto||'')+motivo+'</td>' +
      '<td style="text-align:right;font-weight:700;">'+monto+'</td>' +
      '<td><span class="badge badge-gray">'+esc(m.metodo||'efectivo')+'</span></td>' +
      '<td style="font-size:11px;color:var(--cx-text-mute);">'+esc(m.referencia||'-')+'</td>' +
      '<td style="font-size:11px;color:var(--cx-text-mute);">'+esc(m.registrado_por||'-')+'</td>' +
      '<td style="text-decoration:none;">'+accion+'</td>' +
    '</tr>';
  }).join('');
}

function abrirRegistro(tipo){
  document.getElementById('caja-tipo').value = tipo;
  document.getElementById('modal-caja-title').textContent =
    tipo === 'ingreso' ? '+ Registrar ingreso' : '- Registrar egreso';
  // toISOString() da UTC: despues de las 19:00 en Colombia pre-llenaba el dia SIGUIENTE y el
  // movimiento quedaba con la fecha equivocada (mismo M24 que el backend). Se ancla a Colombia.
  document.getElementById('caja-fecha').value =
    new Date(Date.now() - 5*3600*1000).toISOString().slice(0,10);
  ['monto','concepto','referencia','obs'].forEach(function(f){
    const el = document.getElementById('caja-'+f);
    if (el) el.value = '';
  });
  document.getElementById('caja-metodo').value = 'efectivo';
  abrirModal('modal-caja');
}

async function guardarCaja(){
  const body = {
    tipo: document.getElementById('caja-tipo').value,
    fecha: document.getElementById('caja-fecha').value,
    monto: parseFloat(document.getElementById('caja-monto').value || 0),
    concepto: document.getElementById('caja-concepto').value.trim(),
    metodo: document.getElementById('caja-metodo').value,
    referencia: document.getElementById('caja-referencia').value.trim(),
    observaciones: document.getElementById('caja-obs').value.trim(),
  };
  if (!body.monto || body.monto <= 0) { showToast('Monto debe ser mayor a 0', 'error'); return; }
  if (!body.concepto) { showToast('Concepto requerido', 'error'); return; }
  try {
    const r = await _fetchUna('/api/animus/caja', _fetchOpts('POST', body));
    if (!r) return;   // ya habia uno en vuelo (doble click)
    const d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    showToast('Movimiento registrado', 'success');
    cerrarModal('modal-caja');
    loadCaja();
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
  }
}

async function anularCaja(id){
  // El recibo NO se borra: se anula y queda a la vista. Por eso se pide el motivo, que se
  // guarda en el recibo y en la auditoria (un correlativo con hojas arrancadas no prueba nada).
  const motivo = await pedirDato({
    titulo: 'Anular el cobro',
    sub: 'El recibo NO se borra: queda anulado y a la vista, con el motivo. Asi un hueco en la numeracion nunca puede pasar desapercibido.',
    tipo: 'texto', requerido: true, msgRequerido: 'El motivo es obligatorio',
    confirmar: 'Anular'
  });
  if (motivo === null) return;
  try {
    const r = await _fetchUna('/api/animus/caja/' + id, _fetchOpts('DELETE', {motivo: motivo.trim()}));
    if (!r) return;   // ya habia uno en vuelo (doble click)
    const d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    showToast('Recibo ' + (d.recibo_numero||'') + ' anulado', 'success');
    loadCaja();
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
  }
}

// Contraentrega
async function loadCod(){
  const qs = [];
  const d1 = document.getElementById('cod-desde').value;
  const d2 = document.getElementById('cod-hasta').value;
  const st = document.getElementById('cod-filtro').value;
  if (d1) qs.push('desde=' + d1);
  if (d2) qs.push('hasta=' + d2);
  if (st) qs.push('estado=' + st);
  try {
    const r = await fetch('/api/animus/contraentrega' + (qs.length ? '?' + qs.join('&') : ''));
    const d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    renderCodKPIs(d.kpis||{});
    renderCodPedidos(d.pedidos||[]);
    // Si no aparece NINGUN pedido, casi siempre es que la marca se escribe distinta a lo que
    // el detector busca. Decirlo aca evita que alguien concluya "no hay contraentregas".
    const av = document.getElementById('cod-aviso');
    av.innerHTML = (d.pedidos||[]).length ? '' :
      '<div style="padding:14px 16px;background:var(--cx-warn-pale);border-left:3px solid var(--cx-warn);'
      + 'border-radius:8px;margin:0 0 12px;font-size:13px;color:var(--cx-text-soft);">'
      + 'Sin pedidos contraentrega en este rango. Si deberia haber, revisa como se esta escribiendo '
      + 'la marca en Shopify: el detector busca <code>' + esc(d.patron||'') + '</code> en la nota, '
      + 'las etiquetas y el medio de pago.</div>';
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
  }
}

function renderCodKPIs(k){
  const anejo = k.anejo_21d || 0;
  const porReg = k.por_registrar || 0;
  const cards = [
    // Shopify ya lo da por PAGADO: el mensajero cobro y alguien lo marco. Esa plata ya entro,
    // lo unico que falta es dejarla en la caja con su recibo. Mezclarla con "en la calle"
    // mostraba como por cobrar algo que ya se cobro.
    { label: 'Ya cobrado, falta registrar', val: fmtCOP(porReg),
      color: porReg > 0 ? 'kpi-green' : 'kpi-blue',
      sub: porReg > 0 ? (k.n_por_registrar||0) + ' pedidos &middot; usa el boton Registrar'
                      : 'nada por registrar' },
    { label: 'En la calle', val: fmtCOP(k.esperado_pendiente||0), color:'kpi-yellow',
      sub: (k.n_pendientes||0) + ' sin cobrar todavia' },
    // El anejo lo calculaba el backend desde el primer dia y la pantalla no lo mostraba: sin
    // separarlo, el total "en la calle" mezcla lo de ayer con lo que probablemente no vuelve,
    // y no se puede actuar sobre ninguno de los dos.
    { label: 'Anejo +21 dias', val: fmtCOP(anejo),
      color: anejo > 0 ? 'kpi-red' : 'kpi-blue',
      sub: anejo > 0 ? (k.n_anejos_21d||0) + ' pedidos &middot; revisar con la transportadora'
                     : 'nada viejo en la calle' },
    { label: 'Cobrado este mes', val: fmtCOP(k.cobrado_mes||0), color:'kpi-green',
      sub: (k.n_cobrados||0) + ' pedidos &middot; ' + fmtCOP(k.cobrado_hoy||0) + ' hoy' },
    { label: 'Descuadre', val: fmtCOP(k.descuadre||0),
      color: (k.n_descuadres||0) ? 'kpi-red' : 'kpi-blue',
      sub: (k.n_descuadres||0) + ' con diferencia' },
  ];
  document.getElementById('cod-kpis').innerHTML = cards.map(function(c){
    return '<div class="kpi-card '+c.color+'"><div class="label">'+c.label+'</div>'
      + '<div class="val">'+c.val+'</div>'
      + (c.sub ? '<div class="sub">'+c.sub+'</div>' : '') + '</div>';
  }).join('');
}

function renderCodPedidos(rows){
  // Las filas quedan accesibles por INDICE: los botones pasan el indice y no el id ni el nombre,
  // asi no hay texto del usuario interpolado dentro del onclick (nada que escapar, nada que
  // romper si un nombre de pedido trae una comilla).
  window._COD_ROWS = rows;
  const body = document.getElementById('cod-body');
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="7" style="color:var(--cx-text-mute);text-align:center;padding:24px;">Sin pedidos en este filtro.</td></tr>';
    return;
  }
  body.innerHTML = rows.map(function(p, i){
    const dif = p.diferencia || 0;
    let estado;
    if (!p.cobrado) {
      estado = '<span class="badge badge-yellow">Falta cobrar</span>';
    } else if (Math.abs(dif) >= 1) {
      estado = '<span class="badge badge-red">Descuadre ' + fmtCOP(dif) + '</span>'
        + '<div style="font-size:10px;color:var(--cx-text-mute);margin-top:2px;">'
        + esc(p.cobrado_por||'') + ' &middot; recibio ' + fmtCOP(p.valor_recibido||0) + '</div>';
    } else {
      estado = '<span class="badge badge-green">Cobrado</span>'
        + '<div style="font-size:10px;color:var(--cx-text-mute);margin-top:2px;">'
        + esc(p.cobrado_por||'') + ' &middot; ' + esc((p.cobrado_at||'').slice(0,10)) + '</div>';
    }
    const accion = p.cobrado
      ? '<button class="btn btn-outline btn-sm" onclick="codAnular(' + i + ')">Anular</button>'
      : '<button class="btn btn-primary btn-sm" onclick="codCobrar(' + i + ')">Si entro</button>';
    // Dias en la calle: un contraentrega normal se cobra en dias. A las tres semanas o la
    // transportadora ya consigno y nadie lo registro, o esa plata no vuelve -- asi que el dato
    // se muestra por fila, no solo agregado en el KPI, que es donde se decide a quien llamar.
    var _dias = p.cobrado ? null : (p.dias_en_calle == null ? null : Number(p.dias_en_calle));
    var _calle = '<span style="color:var(--cx-text-mute);">-</span>';
    if (_dias != null) {
      var _cl = _dias >= 21 ? 'badge-red' : (_dias >= 10 ? 'badge-yellow' : 'badge-gray');
      _calle = '<span class="badge ' + _cl + '">' + _dias + ' d</span>';
    }
    return '<tr>'
      + '<td style="font-weight:700;">'+esc(p.pedido||'')+'</td>'
      + '<td>'+fmtFecha(p.fecha)+'</td>'
      + '<td style="text-align:right;">'+_calle+'</td>'
      + '<td style="font-size:12px;">'+esc(p.ciudad||'-')+'</td>'
      + '<td style="text-align:right;font-weight:700;">'+fmtCOP(p.valor_esperado||0)+'</td>'
      + '<td><span class="badge badge-gray" title="'+esc(p.nota||'')+'">'+esc(p.detectado_por||'')+'</span></td>'
      + '<td>' + (p.origen === 'borrador'
          ? '<span class="badge badge-yellow" title="Todavia es un borrador en Shopify: se completa cuando entra la plata">borrador</span>'
          : '<span class="badge badge-blue">orden</span>') + '</td>'
      + '<td>'+estado+'</td>'
      + '<td>'+accion+'</td>'
      + '</tr>';
  }).join('');
}

// ---- Marca de contraentrega -------------------------------------------------------------
// El detector busca UN patron en la nota, las etiquetas y el medio de pago. Elegir aca agrega
// el valor elegido al patron; nunca lo reemplaza, para no perder la nota "contraentrega" que
// tambien se usa. Todo pasa por app_settings, asi que no hace falta desplegar.
// Trae de Shopify los pedidos que todavia son BORRADOR. Es un recurso DISTINTO de las
// ordenes (draft_orders), y ahi es donde vive la contraentrega antes de cobrarse: EOS leia
// solo orders.json, asi que de 7.032 pedidos el detector encontraba 4 -- y no era el patron.
// Asienta en caja las contraentregas que Shopify YA da por pagadas. Se pregunta ANTES con
// la misma lista que se va a aplicar: es plata, y un boton que escribe sin mostrar que va a
// escribir no se puede verificar.
async function importarPagados(){
  try {
    const rp = await fetch('/api/animus/contraentrega/importar-pagados');
    const prev = await rp.json();
    if (!prev.ok) { showToast('Error: ' + (prev.error||'?'), 'error'); return; }
    if (!prev.n) { showToast('No hay contraentregas pagadas sin registrar', 'success'); return; }
    const lista = (prev.pedidos||[]).slice(0, 6).map(function(x){
      return x.pedido + ' (' + fmtCOP(x.valor) + ')'; }).join(', ');
    if (!await pedirDato({
      titulo: 'Registrar ' + prev.n + ' cobros en la caja',
      sub: '<b>' + fmtCOP(prev.monto) + '</b> que Shopify ya da por pagados.<br>'
         + '<span style="color:var(--cx-text-mute);">' + esc(lista)
         + (prev.n > 6 ? ' y ' + (prev.n - 6) + ' mas' : '') + '</span>'
         + '<br>Cada uno entra con su recibo y la fecha del pedido.',
      tipo: 'confirmar', confirmar: 'Registrar ' + prev.n})) return;
    const r = await _fetchUna('/api/animus/contraentrega/importar-pagados', _fetchOpts('POST', {}));
    if (!r) return;   // ya habia uno en vuelo (doble click)
    const d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    showToast(d.registrados + ' registrados por ' + fmtCOP(d.monto)
      + ((d.ya_estaban||[]).length ? ' (' + d.ya_estaban.length + ' ya estaban)' : ''), 'success');
    loadCod(); loadCaja();
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
  }
}

// Trae los pedidos recientes de Shopify sin esperar al cron de las 6 AM. Ventana CORTA a
// proposito: 90 dias son 7.000+ pedidos y mas de 45s reteniendo uno de los 3 workers, y un
// endpoint pesado llamado un par de veces satura la app entera (M43/M89).
async function traerPedidos(){
  showToast('Trayendo pedidos de Shopify...', 'info');
  try {
    const r = await _fetchUna('/api/animus/sync/shopify?dias=7', _fetchOpts('POST', {dias: 7}));
    if (!r) return;   // ya habia uno en vuelo (doble click)
    const d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    showToast((d.synced||0) + ' pedidos actualizados', 'success');
    loadCod(); loadCaja();
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
  }
}

// ── PAGOS DESDE CAJA ──────────────────────────────────────────────────────────
// Un solo registro que cambia de estado y tres personas distintas tocandolo. Cada boton
// aparece SOLO para quien puede ejecutarlo: un boton que responde 403 es peor que no tenerlo,
// porque quien lo aprieta cree que hizo algo.
var _SP_ROWS = [], _SP_TOPE = 200000, _SP_DISPONIBLE = null;

// ── PEDIR DATO · reemplaza prompt()/confirm() ─────────────────────────────────
// Un prompt del navegador no se puede estilar, no deja mostrar el contexto al lado (el valor
// esperado, el saldo, de que pedido se trata) y bloquea el hilo. Este devuelve una PROMESA,
// asi que quien lo llama se lee igual que antes: `var v = await pedirDato({...})`.
var _pedirResolver = null;

function pedirDato(opt){
  opt = opt || {};
  document.getElementById('pedir-titulo').textContent = opt.titulo || '';
  document.getElementById('pedir-sub').innerHTML = opt.sub || '';
  document.getElementById('pedir-error').textContent = '';
  document.getElementById('pedir-ok').textContent = opt.confirmar || 'Confirmar';
  var campo = document.getElementById('pedir-campo');
  if (opt.tipo === 'confirmar') {
    campo.innerHTML = '';
  } else if (opt.tipo === 'texto') {
    campo.innerHTML = '<textarea id="pedir-texto" class="textarea" placeholder="'
      + esc(opt.placeholder || '') + '"></textarea>';
  } else {
    campo.innerHTML = '<input id="pedir-input" type="' + (opt.tipo === 'numero' ? 'number' : 'text')
      + '" class="input" value="' + esc(opt.valor == null ? '' : String(opt.valor)) + '"'
      + ' placeholder="' + esc(opt.placeholder || '') + '">';
  }
  document.getElementById('modal-pedir').style.display = 'flex';
  var inp = _pedirCampo();
  if (inp) { inp.focus(); if (inp.select) inp.select(); }
  // Enter confirma y Escape cancela: es lo que hacia el prompt nativo y se espera que siga.
  window._pedirKey = function(ev){
    if (ev.key === 'Enter' && opt.tipo !== 'texto') { ev.preventDefault(); _pedirAceptar(); }
    if (ev.key === 'Escape') _pedirCerrar(null);
  };
  document.addEventListener('keydown', window._pedirKey);
  window._pedirOpt = opt;
  return new Promise(function(res){ _pedirResolver = res; });
}

// El campo es un input o un textarea segun el tipo · nunca los dos a la vez.
function _pedirCampo(){
  return document.getElementById('pedir-input') || document.getElementById('pedir-texto');
}

function _pedirAceptar(){
  var opt = window._pedirOpt || {};
  if (opt.tipo === 'confirmar') { _pedirCerrar(true); return; }
  var inp = _pedirCampo();
  var v = inp ? inp.value.trim() : '';
  // La validacion vive ACA y no en cada caller: un dato invalido no cierra el modal, para no
  // perder lo que la persona ya escribio.
  if (opt.requerido && !v) {
    document.getElementById('pedir-error').textContent = opt.msgRequerido || 'Este dato es obligatorio';
    return;
  }
  if (opt.tipo === 'numero' && v !== '') {
    var n = parseFloat(String(v).replace(/[^0-9.-]/g, ''));
    if (isNaN(n) || n < 0) {
      document.getElementById('pedir-error').textContent = 'Escribi un numero valido';
      return;
    }
    _pedirCerrar(n); return;
  }
  _pedirCerrar(v);
}

function _pedirCerrar(valor){
  document.getElementById('modal-pedir').style.display = 'none';
  if (window._pedirKey) { document.removeEventListener('keydown', window._pedirKey); window._pedirKey = null; }
  var r = _pedirResolver; _pedirResolver = null;
  if (r) r(valor);
}

// ── ARQUEO · CIERRE · TRAZABILIDAD ────────────────────────────────────────────
// El saldo era una SUMA de movimientos que nadie habia contado nunca contra la gaveta. El
// arqueo lo cuenta: si no cuadra, la diferencia queda con su motivo y los libros se ajustan a
// la realidad (el efectivo fisico es la verdad, igual que el conteo ciclico contra el kardex).
var _ARQ_SISTEMA = 0;

async function cargarAvisoArqueo(){
  var el = document.getElementById('caja-aviso-arqueo');
  if (!el) return;
  try {
    var d = await (await fetch('/api/caja/arqueos')).json();
    if (!d.ok) { el.innerHTML = ''; return; }
    _ARQ_SISTEMA = d.saldo_actual || 0;
    var dias = d.dias_sin_arqueo;
    var partes = [];
    // Una caja que lleva semanas sin arquear tiene un saldo que nadie verifico, y eso tiene
    // que verse sin abrir el historial.
    if (dias == null) {
      partes.push('<b>La caja nunca se ha arqueado.</b> El saldo es un calculo que nadie conto contra la gaveta.');
    } else if (dias >= 7) {
      partes.push('Hace <b>' + dias + ' dias</b> que no se cuenta el efectivo.');
    }
    if (d.cerrada_hasta) {
      partes.push('Cerrada hasta <b>' + esc(d.cerrada_hasta) + '</b>: lo anterior no se toca.');
    }
    if (!partes.length) { el.innerHTML = ''; return; }
    var urgente = (dias == null || dias >= 7);
    el.innerHTML = '<div style="padding:12px 16px;border-radius:10px;margin-bottom:14px;font-size:13px;'
      + 'background:' + (urgente ? 'var(--cx-warn-pale)' : 'var(--cx-info-pale)') + ';'
      + 'border-left:3px solid ' + (urgente ? 'var(--cx-warn)' : 'var(--cx-info)') + ';'
      + 'color:var(--cx-text-soft);">' + partes.join(' &middot; ')
      + (urgente ? ' <a href="#" onclick="abrirArqueo();return false;" style="color:var(--cx-primary-text);font-weight:700;">Arquear ahora</a>' : '')
      + '</div>';
  } catch(e) { el.innerHTML = ''; }
}

// Cerrar el periodo: lo anterior queda congelado. No es un boton de todos los dias, pero sin
// el la feature no existe -- el backend estaba y nadie podia usarlo (M94).
async function cerrarPeriodo(){
  var hasta = await pedirDato({
    titulo: 'Cerrar la caja hasta una fecha',
    sub: 'Todo lo anterior queda congelado: corregir algo cerrado va a exigir un movimiento '
       + 'NUEVO, no editar el viejo.<br>Conviene arquear antes: cerrar sin contar el efectivo '
       + 'es sellar un numero que nadie verifico.',
    tipo: 'texto', valor: new Date(Date.now() - 5*3600*1000).toISOString().slice(0,10),
    placeholder: 'AAAA-MM-DD', requerido: true, confirmar: 'Cerrar'
  });
  if (hasta === null) return;
  try {
    var r = await _fetchUna('/api/caja/cierres', _fetchOpts('POST', {hasta_fecha: hasta}));
    if (!r) return;   // ya habia uno en vuelo (doble click)
    var d = await r.json();
    if (!d.ok) {
      // Si falta el arqueo, el backend ofrece forzar · se pregunta en vez de fallar seco.
      if (d.puede_forzar) {
        var ok = await pedirDato({
          titulo: 'No hay ningun arqueo hasta esa fecha',
          sub: 'Cerrar sin contar el efectivo sella un numero que nadie verifico. '
             + '&iquest;Cerrar igual?',
          tipo: 'confirmar', confirmar: 'Cerrar sin arquear'});
        if (!ok) return;
        var r2 = await _fetchUna('/api/caja/cierres',
                                 _fetchOpts('POST', {hasta_fecha: hasta, forzar: true}));
        if (!r2) return;
        var d2 = await r2.json();
        if (!d2.ok) { showToast('Error: ' + (d2.error||'?'), 'error'); return; }
        showToast('Cerrada hasta ' + d2.hasta_fecha + ' con saldo ' + fmtCOP(d2.saldo_cierre), 'success');
        loadCaja(); cargarAvisoArqueo();
        return;
      }
      showToast('Error: ' + (d.error||'?'), 'error'); return;
    }
    showToast('Cerrada hasta ' + d.hasta_fecha + ' con saldo ' + fmtCOP(d.saldo_cierre), 'success');
    loadCaja(); cargarAvisoArqueo();
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

async function abrirArqueo(){
  document.getElementById('arq-fisico').value = '';
  document.getElementById('arq-motivo').value = '';
  document.getElementById('arq-dif').innerHTML = '';
  document.getElementById('arq-fecha').value = new Date(Date.now() - 5*3600*1000)
    .toISOString().slice(0,10);
  document.getElementById('modal-arqueo').style.display = 'flex';
  try {
    var d = await (await fetch('/api/caja/arqueos')).json();
    _ARQ_SISTEMA = d.saldo_actual || 0;
    document.getElementById('arq-sistema').textContent = fmtCOP(_ARQ_SISTEMA);
    document.getElementById('arq-ultimo').textContent = d.ultimo
      ? (d.ultimo.numero + ' · ' + (d.ultimo.fecha || '') +
         (d.dias_sin_arqueo != null ? ' (' + d.dias_sin_arqueo + ' dias)' : ''))
      : 'nunca se ha arqueado';
  } catch(e) {
    document.getElementById('arq-sistema').textContent = '?';
  }
}

function arqAvisarDif(){
  // La diferencia se muestra MIENTRAS se escribe: si hay que explicarla, que se sepa antes de
  // darle a guardar y no despues de un error.
  var v = document.getElementById('arq-fisico').value;
  var el = document.getElementById('arq-dif');
  if (v === '') { el.innerHTML = ''; return; }
  var dif = parseFloat(v) - _ARQ_SISTEMA;
  if (Math.abs(dif) < 1) {
    el.innerHTML = '<span style="color:var(--cx-success-text);font-weight:700;">Cuadra exacto.</span>';
  } else if (dif < 0) {
    el.innerHTML = '<span style="color:var(--cx-danger-text);font-weight:700;">Faltan '
      + fmtCOP(Math.abs(dif)) + '</span> <span style="color:var(--cx-text-mute);">· explica que paso</span>';
  } else {
    el.innerHTML = '<span style="color:var(--cx-warn-text);font-weight:700;">Sobran '
      + fmtCOP(dif) + '</span> <span style="color:var(--cx-text-mute);">· explica de donde salieron</span>';
  }
}

async function guardarArqueo(){
  var fisico = document.getElementById('arq-fisico').value;
  if (fisico === '') { showToast('Escribi cuanto contaste', 'error'); return; }
  var body = {
    conteo_fisico: parseFloat(fisico),
    fecha: document.getElementById('arq-fecha').value,
    motivo: document.getElementById('arq-motivo').value.trim()
  };
  try {
    var r = await _fetchUna('/api/caja/arqueos', _fetchOpts('POST', body));
    if (!r) return;   // ya habia uno en vuelo (doble click)
    var d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    showToast(d.numero + ' · ' + (d.aviso||''), d.diferencia === 0 ? 'success' : 'error');
    cerrarModal('modal-arqueo');
    loadCaja(); cargarAvisoArqueo();
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

// ── TRAZABILIDAD ─────────────────────────────────────────────────────────────
// Los datos siempre estuvieron, pero repartidos en cinco tablas. Lo que cuesta reconstruir en
// la practica no se audita nunca.
async function verTraza(recibo){
  document.getElementById('traza-titulo').textContent = 'Recorrido de ' + recibo;
  document.getElementById('traza-cuerpo').innerHTML = 'Cargando...';
  document.getElementById('modal-traza').style.display = 'flex';
  try {
    var r = await fetch('/api/caja/trazabilidad/' + encodeURIComponent(recibo));
    var d = await r.json();
    if (!d.ok) {
      document.getElementById('traza-cuerpo').innerHTML =
        '<div style="color:var(--cx-danger-text);">' + esc(d.error || 'No se pudo leer') + '</div>';
      return;
    }
    document.getElementById('traza-cuerpo').innerHTML = renderTraza(d);
  } catch(e) {
    document.getElementById('traza-cuerpo').innerHTML =
      '<div style="color:var(--cx-danger-text);">Error: ' + esc(e.message) + '</div>';
  }
}

function renderTraza(d){
  function bloque(titulo, filas){
    if (!filas.length) return '';
    var h = '<div style="font-weight:800;font-size:13px;color:var(--cx-text);margin:16px 0 6px;">' + titulo + '</div>'
          + '<div style="background:var(--cx-bg-alt);border-radius:10px;padding:12px;">';
    filas.forEach(function(f){
      h += '<div style="display:flex;justify-content:space-between;gap:12px;padding:3px 0;font-size:12.5px;">'
        + '<span style="color:var(--cx-text-mute);">' + f[0] + '</span>'
        + '<span style="color:var(--cx-text);text-align:right;">' + f[1] + '</span></div>';
    });
    return h + '</div>';
  }
  function val(x){ return (x == null || x === '') ? '<span style="color:var(--cx-text-mute);">-</span>' : esc(String(x)); }
  var m = d.movimiento || {};
  var h = bloque('&#128181; El movimiento', [
    ['Recibo', '<b>' + val(m.recibo_numero) + '</b>'],
    ['Fecha', val((m.fecha||'').slice(0,10))],
    ['Tipo', val(m.tipo) + (m.subtipo ? ' · ' + val(m.subtipo) : '')],
    ['Concepto', val(m.concepto)],
    ['Monto', '<b>' + fmtCOP(m.monto || 0) + '</b>'],
    ['Empresa', val(m.empresa)],
    ['Registro', val(m.registrado_por)],
    ['Anulado', m.anulado ? '<span style="color:var(--cx-danger-text);font-weight:700;">si · ' + val(m.anulado_motivo) + '</span>' : 'no']
  ]);
  var s = d.solicitud;
  if (s) {
    h += bloque('&#128203; La solicitud que lo origino', [
      ['Numero', '<b>' + val(s.numero) + '</b>'],
      ['Pidio', val(s.solicitado_por) + ' · ' + val((s.solicitado_at||'').slice(0,16))],
      ['Autorizo', val(s.autorizado_por) + (s.autorizacion_via ? ' (' + val(s.autorizacion_via) + ')' : '')],
      ['Pago', val(s.pagado_por) + ' · ' + val((s.pagado_at||'').slice(0,16))],
      ['Cotizacion', s.cotizacion_url ? '<a href="' + esc(s.cotizacion_url) + '" target="_blank" style="color:var(--cx-primary-text);">ver</a>' : '<span style="color:var(--cx-danger-text);">sin cotizacion</span>'],
      ['Comprobante', s.comprobante_url ? '<a href="' + esc(s.comprobante_url) + '" target="_blank" style="color:var(--cx-primary-text);">ver</a>' : '<span style="color:var(--cx-danger-text);">falta</span>']
    ]);
  }
  var p = d.pedido;
  if (p) {
    h += bloque('&#128666; El pedido de contraentrega', [
      ['Pedido', '<b>' + val(p.pedido) + '</b>'],
      ['Esperado', fmtCOP(p.valor_esperado || 0)],
      ['Recibido', fmtCOP(p.valor_recibido || 0)],
      ['Diferencia', (Math.abs((p.valor_recibido||0) - (p.valor_esperado||0)) < 1)
        ? 'sin diferencia'
        : '<span style="color:var(--cx-danger-text);">' + fmtCOP((p.valor_recibido||0) - (p.valor_esperado||0)) + ' · ' + val(p.observaciones) + '</span>'],
      ['Cobro', val(p.cobrado_por) + ' · ' + val((p.cobrado_at||'').slice(0,16))]
    ]);
  }
  var a = d.arqueo;
  if (a) {
    h += bloque('&#129518; El arqueo que lo genero', [
      ['Arqueo', '<b>' + val(a.numero) + '</b> · ' + val(a.fecha)],
      ['El sistema decia', fmtCOP(a.saldo_sistema || 0)],
      ['Se conto', fmtCOP(a.conteo_fisico || 0)],
      ['Diferencia', fmtCOP(a.diferencia || 0)],
      ['Motivo', val(a.motivo)],
      ['Lo hizo', val(a.realizado_por)]
    ]);
  }
  var t = d.tesoreria;
  h += bloque('&#127974; En Tesoreria', t ? [
    ['Movimiento', val(t.tipo) + ' · ' + fmtCOP(t.monto || 0)],
    ['Categoria', val(t.categoria)],
    ['Periodo', val(t.periodo)]
  ] : [['Espejo', '<span style="color:var(--cx-text-mute);">este movimiento no espeja a Tesoreria</span>']]);

  var au = d.auditoria || [];
  if (au.length) {
    var f = '<div style="font-weight:800;font-size:13px;color:var(--cx-text);margin:16px 0 6px;">&#128220; Quien toco que</div>'
          + '<div style="background:var(--cx-bg-alt);border-radius:10px;padding:12px;">';
    au.forEach(function(x){
      f += '<div style="padding:4px 0;font-size:12px;border-bottom:1px solid var(--cx-hairline);">'
        + '<b style="color:var(--cx-text);">' + esc(x.usuario||'') + '</b> '
        + '<span style="color:var(--cx-primary-text);">' + esc(x.accion||'') + '</span> '
        + '<span style="color:var(--cx-text-mute);">' + esc((x.fecha||'').slice(0,16)) + '</span>'
        + (x.detalle ? '<div style="color:var(--cx-text-soft);">' + esc(x.detalle) + '</div>' : '')
        + '</div>';
    });
    h += f + '</div>';
  }
  return h;
}

async function loadPagosCaja(){
  var est = (document.getElementById('sp-filtro')||{value:''}).value;
  try {
    var r = await fetch('/api/caja/solicitudes' + (est ? '?estado=' + est : ''));
    var d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    _SP_ROWS = d.solicitudes || [];
    _SP_TOPE = d.tope || 200000;
    _SP_DISPONIBLE = d.disponible == null ? null : d.disponible;
    renderPagosKPIs(d);
    renderPagosBody();
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
  }
}

function renderPagosKPIs(d){
  var k = d.kpis || {}, sc = d.sin_comprobante || {n:0, monto:0};
  var esperan = k.solicitada || {n:0, monto:0};
  var listas  = k.autorizada || {n:0, monto:0};
  var pagadas = k.pagada || {n:0, monto:0};
  var cards = [
    { label: 'Esperan autorizacion', val: fmtCOP(esperan.monto), color: esperan.n ? 'kpi-yellow' : 'kpi-blue',
      sub: esperan.n + ' solicitudes' },
    { label: 'Listas para pagar', val: fmtCOP(listas.monto), color: listas.n ? 'kpi-green' : 'kpi-blue',
      sub: listas.n + ' autorizadas' },
    { label: 'Pagado', val: fmtCOP(pagadas.monto), color: 'kpi-blue',
      sub: pagadas.n + ' pagos' },
    // Lo que no tiene respaldo se muestra siempre: un egreso sin comprobante es una salida
    // que nadie puede verificar, asi que tiene que incomodar hasta que se cierre.
    { label: 'Sin comprobante', val: fmtCOP(sc.monto), color: sc.n ? 'kpi-red' : 'kpi-blue',
      sub: sc.n ? sc.n + ' pagos sin respaldo' : 'todo respaldado' }
  ];
  document.getElementById('sp-kpis').innerHTML = cards.map(function(c){
    return '<div class="kpi-card '+c.color+'"><div class="label">'+c.label+'</div>'
      + '<div class="val">'+c.val+'</div><div class="sub">'+c.sub+'</div></div>';
  }).join('');
}

function renderPagosBody(){
  var body = document.getElementById('sp-body');
  if (!_SP_ROWS.length) {
    body.innerHTML = '<tr><td colspan="9" style="color:var(--cx-text-mute);text-align:center;padding:24px;">Sin solicitudes de pago.</td></tr>';
    return;
  }
  body.innerHTML = _SP_ROWS.map(function(s, i){
    var badge = {solicitada:'badge-yellow', autorizada:'badge-green', pagada:'badge-blue',
                 rechazada:'badge-red', anulada:'badge-gray'}[s.estado] || 'badge-gray';
    var etiqueta = {solicitada:'espera autorizacion', autorizada:'lista para pagar',
                    pagada:'pagada', rechazada:'rechazada'}[s.estado] || s.estado;
    var acc = '';
    if (s.estado === 'solicitada') {
      acc += '<button class="btn btn-primary btn-sm" onclick="spAutorizar('+i+')">Autorizar</button> ';
      acc += '<button class="btn btn-outline btn-sm" onclick="spRechazar('+i+')">Rechazar</button>';
    } else if (s.estado === 'autorizada') {
      acc += '<button class="btn btn-primary btn-sm" onclick="spPagar('+i+')">Pagar</button>';
    } else if (s.estado === 'pagada' && !s.comprobante_url) {
      acc += '<button class="btn btn-outline btn-sm" onclick="spComprobante('+i+')">Subir respaldo</button>';
    }
    var cot = s.cotizacion_url
      ? ' <a href="' + esc(s.cotizacion_url) + '" target="_blank" class="badge badge-blue" title="Cotizacion">cotiz</a>' : '';
    var resp = '<span style="color:var(--cx-text-mute);">-</span>';
    if (s.estado === 'pagada') {
      resp = s.comprobante_url
        ? '<a href="'+esc(s.comprobante_url)+'" target="_blank" class="badge badge-green">ver</a>'
        : '<span class="badge badge-red" title="Este pago no tiene respaldo">falta</span>';
    }
    // La via de autorizacion se muestra: si paso por el tope en vez de por gerencia, tiene
    // que poder verse sin abrir la base.
    var via = (s.estado !== 'solicitada' && s.autorizacion_via)
      ? '<div style="font-size:10px;color:var(--cx-text-mute);">'+esc(s.autorizacion_via)+'</div>' : '';
    return '<tr>'
      + '<td style="font-weight:700;">'+esc(s.numero||'')+'</td>'
      + '<td>'+fmtFecha(s.solicitado_at)+'</td>'
      + '<td>'+esc(s.concepto||'')+(s.beneficiario?'<div style="font-size:11px;color:var(--cx-text-mute);">'+esc(s.beneficiario)+'</div>':'')+'</td>'
      + '<td><span class="badge badge-gray">'+esc(s.empresa||'')+'</span></td>'
      + '<td style="text-align:right;font-weight:700;">'+fmtCOP(s.monto||0)+'</td>'
      + '<td style="font-size:12px;">'+esc(s.solicitado_por||'')+'</td>'
      + '<td><span class="badge '+badge+'">'+etiqueta+'</span>'+via+'</td>'
      + '<td>'+resp+cot+'</td>'
      + '<td>'+acc+'</td>'
      + '</tr>';
  }).join('');
}

function abrirSolicitudPago(){
  document.getElementById('sp-concepto').value = '';
  document.getElementById('sp-monto').value = '';
  document.getElementById('sp-beneficiario').value = '';
  document.getElementById('sp-obs').value = '';
  document.getElementById('sp-cotiz').value = '';
  document.getElementById('sp-tope-aviso').innerHTML = '';
  document.getElementById('sp-saldo-aviso').innerHTML = '';
  document.getElementById('modal-sp').style.display = 'flex';
}

function spAvisarTope(){
  // Se dice ANTES de enviar dos cosas: si va a necesitar autorizacion, y si la caja tiene con
  // que pagarlo. Sin lo segundo alguien pide un pago que la caja no cubre y se entera recien
  // cuando quien paga se lo rechaza.
  var m = parseFloat(document.getElementById('sp-monto').value || 0);
  var el = document.getElementById('sp-tope-aviso');
  var es = document.getElementById('sp-saldo-aviso');
  if (es) {
    if (!m || _SP_DISPONIBLE == null) es.innerHTML = '';
    else if (m <= _SP_DISPONIBLE)
      es.innerHTML = '<span style="color:var(--cx-success-text);">La caja tiene '
        + fmtCOP(_SP_DISPONIBLE) + ' disponible: alcanza.</span>';
    else
      es.innerHTML = '<span style="color:var(--cx-danger-text);">La caja solo tiene '
        + fmtCOP(_SP_DISPONIBLE) + ' disponible (ya descontado lo autorizado sin pagar). '
        + 'Se puede pedir igual, pero no se va a poder pagar hasta que entre plata.</span>';
  }
  if (!m) { el.innerHTML = ''; return; }
  el.innerHTML = m <= _SP_TOPE
    ? '<span style="color:var(--cx-success-text);">Bajo el tope de ' + fmtCOP(_SP_TOPE) + ': queda lista para pagar sin esperar autorizacion.</span>'
    : '<span style="color:var(--cx-warn-text);">Supera el tope de ' + fmtCOP(_SP_TOPE) + ': va a gerencia para autorizar.</span>';
}

async function guardarSolicitudPago(){
  var body = {
    concepto: document.getElementById('sp-concepto').value.trim(),
    monto: parseFloat(document.getElementById('sp-monto').value || 0),
    empresa: document.getElementById('sp-empresa').value,
    beneficiario: document.getElementById('sp-beneficiario').value.trim(),
    observaciones: document.getElementById('sp-obs').value.trim(),
    cotizacion_url: document.getElementById('sp-cotiz').value.trim(),
    modulo_origen: 'caja'
  };
  if (!body.concepto) { showToast('Concepto requerido', 'error'); return; }
  if (!body.monto || body.monto <= 0) { showToast('Monto debe ser mayor a 0', 'error'); return; }
  try {
    var r = await _fetchUna('/api/caja/solicitudes', _fetchOpts('POST', body));
    if (!r) return;   // ya habia uno en vuelo (doble click)
    var d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    showToast(d.numero + ' - ' + (d.aviso||''), 'success');
    cerrarModal('modal-sp');
    loadPagosCaja(); loadCaja();
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

async function spAutorizar(i){
  var s = _SP_ROWS[i]; if (!s) return;
  if (!await pedirDato({titulo: 'Autorizar el pago',
    sub: '<b>' + fmtCOP(s.monto) + '</b> &middot; ' + esc(s.concepto)
       + (s.beneficiario ? '<br>A: ' + esc(s.beneficiario) : '')
       + '<br>Pidio: ' + esc(s.solicitado_por || '') + ' &middot; ' + esc(s.empresa || '')
       + '<br><span style="color:var(--cx-text-mute);">Autorizar no saca la plata: la saca quien pague.</span>',
    tipo: 'confirmar', confirmar: 'Autorizar'})) return;
  await _spAccion('/api/caja/solicitudes/' + s.id + '/autorizar', {}, 'Autorizada');
}

async function spRechazar(i){
  var s = _SP_ROWS[i]; if (!s) return;
  // El motivo es obligatorio: sin el, quien pidio no sabe que corregir y quien audita no sabe
  // por que no se pago.
  var motivo = await pedirDato({
    titulo: 'Rechazar ' + (s.numero || ''),
    sub: 'Quien lo pidio va a ver este motivo en su pantalla, asi que decile que corregir.',
    tipo: 'texto', requerido: true, msgRequerido: 'El motivo es obligatorio',
    confirmar: 'Rechazar'
  });
  if (motivo === null) return;
  await _spAccion('/api/caja/solicitudes/' + s.id + '/rechazar', {motivo: motivo.trim()}, 'Rechazada');
}

async function spPagar(i){
  var s = _SP_ROWS[i]; if (!s) return;
  if (!await pedirDato({titulo: 'Pagar desde la caja',
    sub: '<b>' + fmtCOP(s.monto) + '</b> &middot; ' + esc(s.concepto)
       + (s.beneficiario ? '<br>A: ' + esc(s.beneficiario) : '')
       + '<br><span style="color:var(--cx-warn-text);">El saldo baja ahora. El comprobante lo podes subir despues.</span>',
    tipo: 'confirmar', confirmar: 'Pagar'})) return;
  await _spAccion('/api/caja/solicitudes/' + s.id + '/pagar', {}, 'Pagada');
}

async function spComprobante(i){
  var s = _SP_ROWS[i]; if (!s) return;
  var url = await pedirDato({
    titulo: 'Respaldo de ' + (s.numero || ''),
    sub: 'Pega el enlace de la foto o el archivo del pago (' + fmtCOP(s.monto) + ').',
    tipo: 'texto', requerido: true, msgRequerido: 'Falta el enlace',
    placeholder: 'https://...', confirmar: 'Guardar respaldo'
  });
  if (url === null) return;
  await _spAccion('/api/caja/solicitudes/' + s.id + '/comprobante', {url: url.trim()}, 'Respaldo guardado');
}

async function _spAccion(url, body, ok){
  try {
    var r = await _fetchUna(url, _fetchOpts('POST', body));
    if (!r) return;   // ya habia uno en vuelo (doble click)
    var d = await r.json();
    if (!d.ok) {
      // El backend responde con el saldo cuando no alcanza: se muestra para poder decidir.
      var msg = d.error || '?';
      if (d.saldo != null) msg += ' (saldo: ' + fmtCOP(d.saldo) + ')';
      showToast(msg, 'error');
      return;
    }
    showToast(ok + (d.recibo_numero ? ' - recibo ' + d.recibo_numero : ''), 'success');
    loadPagosCaja(); loadCaja();
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

function abrirTraslado(){
  document.getElementById('tr-monto').value = '';
  document.getElementById('tr-cuenta').value = '';
  document.getElementById('modal-traslado').style.display = 'flex';
}

async function guardarTraslado(){
  var body = {
    monto: parseFloat(document.getElementById('tr-monto').value || 0),
    empresa: document.getElementById('tr-empresa').value,
    cuenta: document.getElementById('tr-cuenta').value.trim()
  };
  if (!body.monto || body.monto <= 0) { showToast('Monto debe ser mayor a 0', 'error'); return; }
  try {
    var r = await _fetchUna('/api/caja/traslado', _fetchOpts('POST', body));
    if (!r) return;   // ya habia uno en vuelo (doble click)
    var d = await r.json();
    if (!d.ok) {
      var msg = d.error || '?';
      if (d.saldo != null) msg += ' (saldo: ' + fmtCOP(d.saldo) + ')';
      showToast(msg, 'error'); return;
    }
    showToast('Consignados ' + fmtCOP(body.monto) + ' - recibo ' + d.recibo_numero, 'success');
    cerrarModal('modal-traslado');
    loadPagosCaja(); loadCaja();
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

async function syncBorradores(){
  showToast('Trayendo borradores de Shopify...', 'info');
  try {
    const r = await _fetchUna('/api/animus/contraentrega/borradores/sync', _fetchOpts('POST', {}));
    if (!r) return;   // ya habia uno en vuelo (doble click)
    const d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    // Si se corto por presupuesto, se DICE: un numero parcial que se lea como total haria
    // concluir que no hay mas borradores, que es lo contrario de la verdad.
    showToast(d.guardados + ' borradores traidos'
      + (d.se_corto_por ? ' (parcial: ' + d.se_corto_por + ', corre de nuevo)' : ''),
      d.se_corto_por ? 'error' : 'success');
    loadCod(); loadCaja();
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
  }
}

async function abrirMarcaCod(){
  document.getElementById('modal-marca').style.display = 'flex';
  document.getElementById('marca-cuerpo').innerHTML = 'Cargando...';
  try {
    const r = await fetch('/api/animus/contraentrega/diagnostico');
    const d = await r.json();
    if (!d.ok) {
      document.getElementById('marca-cuerpo').innerHTML =
        '<div style="color:var(--cx-danger-text);">' + esc(d.error || 'No se pudo leer') + '</div>';
      return;
    }
    window._MARCA_PATRON = d.patron || '';
    renderMarca(d);
  } catch(e) {
    document.getElementById('marca-cuerpo').innerHTML =
      '<div style="color:var(--cx-danger-text);">Error de red: ' + esc(e.message) + '</div>';
  }
}

function renderMarca(d){
  function tabla(titulo, filas, campo){
    if (!filas || !filas.length) return '';
    var h = '<div style="font-weight:700;margin:16px 0 6px;">' + titulo + '</div>'
          + '<div style="overflow-x:auto;"><table><thead><tr>'
          + '<th>Valor</th><th style="text-align:right;">Pedidos</th>'
          + '<th style="text-align:right;">Plata</th>'
          + '<th style="text-align:right;" title="Pedidos que Shopify NO da por pagados. '
          + 'Si casi todos estan sin pagar, esa plata esta en la calle = contraentrega. '
          + 'Si ya estan pagados, entro por otro lado y NO va a esta caja.">Sin pagar</th>'
          + '<th>Hoy</th><th></th></tr></thead><tbody>';
    for (var i = 0; i < filas.length; i++) {
      var f = filas[i];
      var yaEsta = f.detecta
        ? '<span class="badge badge-green">entra a la caja</span>'
        : '<span class="badge badge-gray">no entra</span>';
      var boton = f.detecta ? '' :
        '<button class="btn btn-primary btn-sm" onclick="usarMarca(' + i + ',&quot;' + campo + '&quot;)">Es esta</button>';
      // La senal que decide, con color: verde = casi todo sin pagar (plata en la calle),
      // gris = ya pagados (esa plata entro por otro lado y no va a esta caja).
      var pct = f.pct_sin_pagar == null ? null : Number(f.pct_sin_pagar);
      var cel = pct == null ? '<span style="color:var(--cx-text-mute);">-</span>'
        : '<span class="badge ' + (pct >= 80 ? 'badge-green' : (pct >= 30 ? 'badge-yellow' : 'badge-gray'))
          + '" title="' + (f.sin_pagar||0) + ' de ' + f.pedidos + ' sin pagar">' + pct + '%</span>';
      h += '<tr>'
        + '<td style="font-weight:600;">' + esc(f.valor) + '</td>'
        + '<td style="text-align:right;">' + f.pedidos + '</td>'
        + '<td style="text-align:right;font-weight:700;">' + fmtCOP(f.monto || 0) + '</td>'
        + '<td style="text-align:right;">' + cel + '</td>'
        + '<td>' + yaEsta + '</td><td>' + boton + '</td></tr>';
    }
    return h + '</tbody></table></div>';
  }
  window._MARCA_TAGS = d.etiquetas || [];
  window._MARCA_GW   = d.medios_pago || [];
  var res = '<div style="padding:12px 14px;background:var(--cx-bg-alt);border-radius:8px;margin-bottom:6px;">'
    + '<b>' + (d.detectados || 0) + '</b> de <b>' + (d.pedidos_en_rango || 0) + '</b> pedidos '
    + 'entran hoy a la caja (desde ' + esc(d.desde || '') + ').'
    + '<div style="font-size:12px;color:var(--cx-text-mute);margin-top:4px;">'
    + 'Por nota ' + ((d['por_señal'] || {})['nota'] || 0)
    + ' &middot; por etiqueta ' + ((d['por_señal'] || {})['etiqueta'] || 0)
    + ' &middot; por medio de pago ' + ((d['por_señal'] || {})['medio de pago'] || 0)
    + '</div></div>';
  document.getElementById('marca-cuerpo').innerHTML = res
    + tabla('Etiquetas de Shopify (' + (d.etiquetas_distintas || 0) + ' distintas)', window._MARCA_TAGS, 'tag')
    + tabla('Medios de pago', window._MARCA_GW, 'gw');
}

async function usarMarca(i, campo){
  var f = (campo === 'tag' ? window._MARCA_TAGS : window._MARCA_GW)[i];
  if (!f) return;
  // El valor se escapa como literal: una etiqueta con parentesis o + seria una expresion
  // regular distinta de la que el usuario ve, y terminaria metiendo a la caja pedidos que no son.
  // En MINUSCULAS porque el detector compara contra el texto ya normalizado (_norm_txt): un
  // patron con mayusculas nunca matchea y la eleccion no hace nada, sin un solo error a la vista.
  var lit = String(f.valor).toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  // Anclado a la etiqueta COMPLETA: sin esto, "vmc" matchearia dentro de "vmcx" y meteria
  // plata que no es contraentrega -- que es justo lo que esta caja tiene que evitar.
  var nuevo = campo === 'tag' ? '(^|,)\\s*' + lit + '\\s*(,|$)' : '^' + lit + '$';
  var patron = (window._MARCA_PATRON || '').trim();
  patron = patron ? patron + '|' + nuevo : nuevo;
  // Mensaje de UNA sola linea a proposito: un salto real dentro de un confirm rompe el bloque
  // <script> entero y deja la pantalla muerta sin un error visible.
  if (!await pedirDato({
    titulo: 'Marcar como contraentrega',
    sub: (campo === 'tag' ? 'La etiqueta' : 'El medio de pago') + ' <b>' + esc(f.valor) + '</b>'
       + '<br><b>' + f.pedidos + '</b> pedidos entrarian a la caja (' + fmtCOP(f.monto || 0) + ').'
       + '<br><span style="color:var(--cx-text-mute);">Se SUMA a lo que ya detecta, no lo reemplaza.</span>',
    tipo: 'confirmar', confirmar: 'Usar esta marca'})) return;
  try {
    const r = await _fetchUna('/api/animus/contraentrega/patron', _fetchOpts('PUT', {patron: patron}));
    if (!r) return;   // ya habia uno en vuelo (doble click)
    const d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    showToast('Listo: ' + f.valor + ' ya cuenta como contraentrega', 'success');
    abrirMarcaCod(); loadCod(); loadCaja();
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
  }
}

// Cobrar una contraentrega. El MEDIO decide donde aterriza la plata: efectivo va a la gaveta,
// transferencia o Nequi van al banco. Daniela (3-ago): "a veces van y dicen 'yo transferi, le
// mande por Nequi', entonces no entregan efectivo" -- y contarlo como efectivo haria que el
// arqueo nunca cuadre.
var _COB = null;

function codCobrar(i){
  var p = (window._COD_ROWS || [])[i];
  if (!p) return;
  _COB = p;
  document.getElementById('cob-titulo').textContent = 'Cobrar el pedido ' + (p.pedido || '');
  document.getElementById('cob-sub').innerHTML =
    'El pedido dice <b>' + fmtCOP(p.valor_esperado || 0) + '</b>'
    + (p.ciudad ? ' &middot; ' + esc(p.ciudad) : '')
    + (p.dias_en_calle != null ? ' &middot; ' + p.dias_en_calle + ' dias en la calle' : '')
    + '<br>Escribi lo que entro DE VERDAD y como pagaron.';
  document.getElementById('cob-monto').value = p.valor_esperado || 0;
  document.getElementById('cob-metodo').value = 'efectivo';
  document.getElementById('cob-ref').value = '';
  document.getElementById('cob-comprobante').value = '';
  document.getElementById('cob-obs').value = '';
  document.getElementById('cob-dif').innerHTML = '';
  cobCambiaMetodo();
  document.getElementById('modal-cobro').style.display = 'flex';
}

function cobCambiaMetodo(){
  var m = document.getElementById('cob-metodo').value;
  document.getElementById('cob-no-efectivo').style.display = (m === 'efectivo') ? 'none' : '';
}

function cobAvisarDif(){
  // La diferencia se ve MIENTRAS se escribe: si hay que explicarla, que se sepa antes.
  if (!_COB) return;
  var v = document.getElementById('cob-monto').value;
  var el = document.getElementById('cob-dif');
  if (v === '') { el.innerHTML = ''; return; }
  var dif = parseFloat(v) - (_COB.valor_esperado || 0);
  el.innerHTML = (Math.abs(dif) < 1)
    ? '<span style="color:var(--cx-success-text);">Coincide con el pedido.</span>'
    : '<span style="color:var(--cx-warn-text);font-weight:700;">Diferencia de ' + fmtCOP(dif)
      + '</span> <span style="color:var(--cx-text-mute);">&middot; explica que paso en observaciones</span>';
}

// ── PAGO DIRECTO · lo que ya se pago porque alguien lo pidio de palabra ──────
// Sebastian (3-ago): "se le dijo pague papel burbuja ... entonces registra el pago con
// comprobante, concepto y demas". Sale de la caja en el acto, con recibo y con quien autorizo.
function abrirPagoDirecto(){
  document.getElementById('pd-concepto').value = '';
  document.getElementById('pd-monto').value = '';
  document.getElementById('pd-beneficiario').value = '';
  document.getElementById('pd-comprobante').value = '';
  document.getElementById('pd-obs').value = '';
  document.getElementById('pd-alerta').innerHTML = '';
  document.getElementById('pd-fecha').value = hoyCol();
  var s = (window._CAJA_SALDO != null) ? window._CAJA_SALDO : 0;
  document.getElementById('pd-saldo').textContent = 'En la caja hay ' + fmtCOP(s) + '.';
  document.getElementById('modal-pagodir').style.display = 'flex';
}

function pdChequearSaldo(){
  // El aviso va MIENTRAS se escribe: enterarse de que no alcanza al apretar Registrar,
  // despues de llenar seis campos, es la peor forma de enterarse.
  var v = parseFloat(document.getElementById('pd-monto').value || 0);
  var s = (window._CAJA_SALDO != null) ? window._CAJA_SALDO : 0;
  var el = document.getElementById('pd-alerta');
  if (!v) { el.innerHTML = ''; return; }
  el.innerHTML = (v > s)
    ? '<span style="color:var(--cx-warn-text);font-weight:700;">Eso supera el efectivo de la caja ('
      + fmtCOP(s) + ')</span> <span style="color:var(--cx-text-mute);">&middot; si la plata está y el saldo no lo refleja, falta registrar un ingreso</span>'
    : '<span style="color:var(--cx-text-mute);">Quedarían ' + fmtCOP(s - v) + ' en la caja.</span>';
}

async function guardarPagoDirecto(){
  var concepto = document.getElementById('pd-concepto').value.trim();
  var monto = parseFloat(document.getElementById('pd-monto').value || 0);
  if (!concepto) { showToast('Falta qué se pagó', 'error'); return; }
  if (!monto || monto <= 0) { showToast('Falta el monto', 'error'); return; }
  var body = {
    concepto: concepto, monto: monto,
    beneficiario: document.getElementById('pd-beneficiario').value.trim(),
    empresa: document.getElementById('pd-empresa').value,
    autorizado_por: document.getElementById('pd-quien').value,
    fecha: document.getElementById('pd-fecha').value,
    comprobante_url: document.getElementById('pd-comprobante').value.trim(),
    observaciones: document.getElementById('pd-obs').value.trim()
  };
  try {
    var r = await _fetchUna('/api/caja/pago-directo', _fetchOpts('POST', body));
    if (!r) return;                       // ya habia uno en vuelo (doble click)
    var d = await r.json();
    if (r.status === 409 && d.puede_forzar) {
      var ok = await pedirDato({
        titulo: 'La caja no alcanza',
        tipo: 'confirmar',
        sub: 'El saldo es <b>' + fmtCOP(d.saldo) + '</b> y el pago es <b>' + fmtCOP(d.monto)
           + '</b>.<br>Si el efectivo está de verdad, registralo igual y después cuadrás con un arqueo.',
        confirmar: 'Registrar igual'});
      if (!ok) return;
      body.forzar = true;
      var r2 = await _fetchUna('/api/caja/pago-directo', _fetchOpts('POST', body));
      if (!r2) return;
      d = await r2.json();
      if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    } else if (!d.ok) {
      showToast('Error: ' + (d.error||'?'), 'error'); return;
    }
    showToast(d.aviso || ('Registrado · ' + d.numero), 'success');
    cerrarModal('modal-pagodir');
    loadCaja(); loadSolicitudes();
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

async function guardarCobro(){
  if (!_COB) return;
  var monto = parseFloat(document.getElementById('cob-monto').value || 0);
  if (isNaN(monto) || monto < 0) { showToast('Valor invalido', 'error'); return; }
  var metodo = document.getElementById('cob-metodo').value;
  var ref = document.getElementById('cob-ref').value.trim();
  var obs = document.getElementById('cob-obs').value.trim();
  // Una transferencia sin numero no se puede conciliar despues contra el extracto.
  if (metodo !== 'efectivo' && !ref) {
    showToast('Falta el numero de la transferencia', 'error'); return;
  }
  // Un descuadre sin explicacion es el dato que despues nadie puede reconstruir.
  if (Math.abs(monto - (_COB.valor_esperado || 0)) >= 1 && !obs) {
    showToast('La diferencia necesita explicacion', 'error'); return;
  }
  try {
    var r = await _fetchUna('/api/animus/contraentrega/' + encodeURIComponent(_COB.shopify_id) + '/cobrar',
      _fetchOpts('POST', {valor_recibido: monto, observaciones: obs, metodo: metodo,
                          referencia_pago: ref,
                          comprobante_url: document.getElementById('cob-comprobante').value.trim()}));
    if (!r) return;   // ya habia uno en vuelo (doble click)
    var d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    showToast('Recibo ' + d.recibo_numero + ' · ' + (d.aviso || ''), 'success');
    cerrarModal('modal-cobro');
    loadCod(); loadCaja();
  } catch(e) { showToast('Error de red: ' + e.message, 'error'); }
}

async function codAnular(i){
  const p = (window._COD_ROWS || [])[i];
  if (!p) return;
  const sid = p.shopify_id;
  const motivo = await pedirDato({
    titulo: 'Anular el cobro de ' + (p.pedido || ''),
    sub: 'El recibo NO se borra: queda anulado y a la vista con su motivo. Un hueco en la numeracion nunca puede pasar desapercibido.',
    tipo: 'texto', requerido: true, msgRequerido: 'El motivo es obligatorio', confirmar: 'Anular'
  });
  if (motivo === null) return;
  try {
    const r = await _fetchUna('/api/animus/contraentrega/' + encodeURIComponent(sid) + '/anular',
                          _fetchOpts('POST', {motivo: motivo.trim()}));
    if (!r) return;   // ya habia uno en vuelo (doble click)
    const d = await r.json();
    if (!d.ok) { showToast('Error: ' + (d.error||'?'), 'error'); return; }
    showToast('Cobro anulado', 'success');
    loadCod(); loadCaja();
  } catch(e) {
    showToast('Error de red: ' + e.message, 'error');
  }
}

// Inventario Cíclico
let _SKUS_CACHE = [];















// ════════════════════════════════════════════════════════════════
// INVENTARIO FISICO (Fase 1 UI)
// ════════════════════════════════════════════════════════════════
var INVFIS_DATA = [];


















// ════════════════════════════════════════════════════════════════
// CONTEO CICLICO Fase 2 (asignaciones + registro)
// ════════════════════════════════════════════════════════════════








var CONTEO_DESGLOSE = null;




// ════════════════════════════════════════════════════════════════
// DIAGNOSTICO Fase 3
// ════════════════════════════════════════════════════════════════



// ── PQR Clientes (comercial) ──────────────────────────────────────────
var _PQR_TIPO_LBL = {envio:'Envío',producto_equivocado:'Producto equivocado',faltante:'Faltante',devolucion:'Devolución',servicio:'Servicio',facturacion:'Facturación',comercial:'Comercial',otro:'Otro'};
var _PQR_EST_LBL = {nuevo:['Nuevo','#d97706'],en_proceso:['En proceso','#0ea5e9'],resuelto:['Resuelto','#16a34a'],cerrado:['Cerrado','#64748b']};
window._PQR_TIPO_LBL = _PQR_TIPO_LBL;

async function loadAnimusPqr(){
  var box = document.getElementById('pqr-ani-list');
  var est = (document.getElementById('pqr-ani-festado')||{}).value || '';
  try{
    var r = await fetch('/api/animus/pqr' + (est?('?estado='+est):''), {credentials:'same-origin'});
    var d = await r.json();
    if(!r.ok) throw new Error(d.error||'error');
    var s = d.resumen||{};
    document.getElementById('pqr-ani-kpis').innerHTML =
      '<div class="kpi-card"><div class="label">Nuevos</div><div class="val" style="color:var(--cx-warn-text)">'+(s.nuevo||0)+'</div></div>'+
      '<div class="kpi-card"><div class="label">En proceso</div><div class="val" style="color:var(--cx-info-text)">'+(s.en_proceso||0)+'</div></div>'+
      '<div class="kpi-card"><div class="label">Resueltos</div><div class="val" style="color:var(--cx-success-text)">'+(s.resuelto||0)+'</div></div>'+
      '<div class="kpi-card"><div class="label">Cerrados</div><div class="val">'+(s.cerrado||0)+'</div></div>';
    var items = d.pqr||[];
    window._PQR_ROWS = items;   // el modal las busca por id
    if(!items.length){ box.innerHTML='<p style="color:var(--cx-text-faint);text-align:center;padding:14px">Sin PQR.</p>'; return; }
    box.innerHTML = '<table style="width:100%;border-collapse:collapse;font-size:0.86em"><thead><tr style="text-align:left;color:var(--cx-text-faint);font-size:0.85em"><th style="padding:6px">Código</th><th>Tipo</th><th>Cliente</th><th>Descripción</th><th>Estado</th><th>Acción</th></tr></thead><tbody>'
      + items.map(function(p){
        var est = _PQR_EST_LBL[p.estado]||[p.estado,'#64748b'];
        var pr = p.prioridad==='alta'?' 🔴':(p.prioridad==='baja'?'':' 🟡');
        return '<tr style="border-top:1px solid var(--cx-hairline,#e2e8f0)">'
          +'<td style="padding:6px"><b>'+(p.codigo||p.id)+'</b>'+pr+'</td>'
          +'<td>'+(_PQR_TIPO_LBL[p.tipo]||p.tipo)+'</td>'
          +'<td>'+(p.contacto_nombre||'-')+'</td>'
          +'<td style="max-width:320px">'+(p.descripcion||'').replace(/</g,'&lt;')+(p.pedido_numero?'<div style="font-size:0.82em;color:var(--cx-info-text)">📦 Pedido '+String(p.pedido_numero).replace(/</g,'&lt;')+'</div>':'')+'</td>'
          +'<td><span style="color:'+est[1]+';font-weight:700">'+est[0]+'</span></td>'
          +'<td><button class="btn btn-outline" style="padding:3px 8px;font-size:0.8em" onclick="gestionarPqr('+p.id+')">Gestionar</button></td>'
          +'</tr>';
      }).join('') + '</tbody></table>';
  }catch(e){ box.innerHTML='<p style="color:var(--cx-danger-text);text-align:center;padding:14px">Error: '+e.message+'</p>'; }
}
function abrirPqrManual(){ abrirModal('modal-pqr-ani'); }
async function guardarPqrManual(){
  var desc = document.getElementById('pqr-ani-desc').value.trim();
  if(desc.length<5){ alert('Describe el PQR'); return; }
  var body = {tipo:document.getElementById('pqr-ani-tipo').value, contacto_nombre:document.getElementById('pqr-ani-cliente').value.trim(), descripcion:desc};
  try{
    var r = await _fetchUna('/api/animus/pqr', _fetchOpts('POST', body));
    if (!r) return;   // ya habia uno en vuelo (doble click)
    var d = await r.json();
    if(r.ok && d.ok){ cerrarModal('modal-pqr-ani'); document.getElementById('pqr-ani-desc').value=''; document.getElementById('pqr-ani-cliente').value=''; loadAnimusPqr(); }
    else alert('Error: '+(d.error||'?'));
  }catch(e){ alert('Error red: '+e.message); }
}

// Init
// Arranca por el MISMO despachador que usan las pestanas, no llamando a un cargador suelto.
// Al fusionar Contraentrega dentro de Caja Menor actualice `loadTab` y deje este `loadCaja()`
// directo: la pestana abria con el saldo cargado y la contraentrega en "Cargando..." para
// siempre, porque `loadCod()` solo corria si te ibas a otra pestana y volvias.
_loaded['caja'] = true;
loadTab('caja');
</script>

<!-- Widget "Mi contraseña" removido 24-may-2026 · vive en /modulos y /hub -->
</body>
</html>"""
